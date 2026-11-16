"""Transformador 2.1.0 para futuros pipelines. No crea o ajusta regresores.

fit aprende medianas, vocabulario y escalado exclusivamente en meses TRAIN.
transform conserva esos parámetros. El mes es contexto, nunca una columna X.
"""
import copy
import csv
import json
import math
from numbers import Real
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator,TransformerMixin
from sklearn.preprocessing import StandardScaler
from sklearn.utils.validation import check_is_fitted

from v2.structure import ROOT,sha256_file
from v2.validate_build import canonical_hash,cutoff,month_offset

VERSION="preprocessing-2.1-1"
UNKNOWN="UNKNOWN"
RAW=("ventas_mes_anterior","ventas_hace_2_meses","ventas_hace_3_meses","mes_sin","mes_cos",
     "proporcion_por_mayor_mes_anterior","cobertura_modalidad_mes_anterior",
     "precio_menor_cierre_anterior_bs","precio_mayor_cierre_anterior_bs",
     "variacion_precio_menor_conocida","variacion_precio_mayor_conocida",
     "tipo_cambio_bs_usd_conocido","variacion_tipo_cambio_ultimo_mes","antiguedad_tipo_cambio_dias",
     "dias_sin_stock_mes_anterior","cobertura_stock_mes_anterior","categoryId")
GROUPS={"expanded_baseline_v1_features":5,"expanded_with_modality":7,"expanded_with_prices":11,
        "expanded_with_exchange":14,"expanded_with_availability":16,"expanded_v2_full":17}
CONTEXT="mes_objetivo"


def read_context(root):
    root=Path(root).resolve()
    p=root/"v2/contracts/preprocessing.v2_1.json"
    spec=json.loads(p.read_text(encoding="utf-8"))
    if spec["adapter_version"]!=VERSION or spec["dataset_version"]!="2.1.0":raise ValueError("Versión incompatible")
    plan_path=root/spec["experiment_contract"]
    if not plan_path.resolve().is_relative_to(root/"v2/contracts"):raise ValueError("Contrato fuera de V2")
    if sha256_file(plan_path)!=spec["experiment_contract_sha256"]:raise ValueError("Plan experimental cambió")
    plan=json.loads(plan_path.read_text(encoding="utf-8"))
    if plan["input_build"]!=spec["input_build"]:raise ValueError("Plan y adaptador apuntan a distintos builds")
    source=root/spec["input_build"]["relative_path"]
    if not source.resolve().is_relative_to(root/"data/repuestopro_v2/2.1.0"):raise ValueError("Solo datos 2.1.0")
    if sha256_file(source/"manifest.json")!=spec["input_build"]["manifest_sha256"]:raise ValueError("Manifest cambió")
    manifest=json.loads((source/"manifest.json").read_text(encoding="utf-8"))
    temporal=plan["temporal_validation"]
    for name,key in [("TRAIN","outer_train"),("VALIDATION","outer_validation"),("TEST","test")]:
        limits=manifest["split_design"]["sets"][name]
        if temporal[key]!=[limits["start"],limits["end"]]:raise ValueError("Particiones distintas del build")
    expected_windows=[temporal["outer_train"]]+[f["train"] for f in temporal["folds"]]
    if spec["fit_windows"]!=expected_windows or any(not temporal["outer_train"][0]<=a<=b<=temporal["outer_train"][1] for a,b in expected_windows):
        raise ValueError("Ventanas de fit contaminadas")
    if sha256_file(source/"schema.json")!=spec["schema_sha256"]:raise ValueError("Schema cambió")
    schema=json.loads((source/"schema.json").read_text(encoding="utf-8"))
    features=[c for c in schema["columns"] if c["role"]=="FEATURE"]
    if tuple(c["name"] for c in features)!=RAW or tuple(spec["raw_features"])!=RAW:raise ValueError("Features no canónicas")
    if {g["id"] for g in plan["feature_sets"]}!=set(GROUPS):raise ValueError("Matriz de grupos incompleta")
    for group in plan["feature_sets"]:
        if group["id"] not in GROUPS or tuple(group["columns"])!=RAW[:GROUPS[group["id"]]]:
            raise ValueError("Selección no aprobada")
    return spec,plan,features,source,sha256_file(p),manifest


def load_feature_partition(partition,*,fold_id=None,root=ROOT):
    """Carga features y contexto, sin interpretar targets. No ajusta parámetros.

    Su hash de bytes se fija fuera del dataset. El caller no cambia las fechas
    para presentar VALIDATION/TEST como TRAIN. No se acepta una ruta arbitraria.
    """
    spec,plan,features,source,_,_=read_context(root)
    path=source/"dataset_supervisado.csv"
    if sha256_file(path)!=spec["csv_sha256"]:raise ValueError("CSV modificado")
    temporal=plan["temporal_validation"]
    if fold_id is not None:
        folds=[f for f in temporal["folds"] if f["id"]==fold_id]
        if len(folds)!=1 or partition not in ("TRAIN","VALIDATION"):raise ValueError("Fold o partición inválidos")
        start,end=folds[0]["train" if partition=="TRAIN" else "validation"]
    else:
        key={"TRAIN":"outer_train","VALIDATION":"outer_validation","TEST":"test"}.get(partition)
        if key is None:raise ValueError("Partición inválida")
        start,end=temporal[key]
    rows=[];keys=[]
    with path.open(encoding="utf-8",newline="") as f:
        for raw in csv.DictReader(f):
            month=raw[CONTEXT]
            if not start<=month<=end:continue
            row={CONTEXT:month}
            for c in features:
                value=raw[c["name"]]
                row[c["name"]]=None if value=="" else int(value) if c["type"]=="integer" else float(value)
            rows.append(row)
            keys.append((int(raw["productId"]),int(raw["locationId"]),month))
    result=pd.DataFrame(rows,columns=[*RAW,CONTEXT])
    result.index=pd.MultiIndex.from_tuples(keys,names=["productId","locationId",CONTEXT])
    result.attrs.update(dataset_version="2.1.0",build_manifest_sha256=spec["input_build"]["manifest_sha256"],
                        partition=partition,fold_id=fold_id,labels_processed=False,window=[start,end])
    return result


def missing(value):
    if value is None or value is pd.NA:return True
    try:return isinstance(value,Real) and not isinstance(value,(bool,np.bool_)) and math.isnan(value)
    except OverflowError:return False


def validate_frame(frame,fields):
    if not isinstance(frame,pd.DataFrame):raise TypeError("Se requiere DataFrame con columnas nombradas")
    if frame.columns.has_duplicates or set(frame.columns)!=set(RAW)|{CONTEXT}:
        raise ValueError("Contrato X inválido: 17 features y mes, sin target, IDs o controles")
    data={};months=[]
    for value in frame[CONTEXT]:
        if not isinstance(value,str):raise ValueError("Mes no textual")
        month_offset(value,0);months.append(value)
    for field in fields:
        name=field["name"];values=[]
        for value in frame[name]:
            if missing(value):
                if not field["nullable"]:raise ValueError("Faltante obligatorio: "+name)
                values.append(None if name=="categoryId" else np.nan);continue
            try:finite=math.isfinite(value) if isinstance(value,Real) else False
            except OverflowError:finite=False
            if isinstance(value,(bool,np.bool_)) or not isinstance(value,Real) or not finite:
                raise ValueError("Número inválido: "+name)
            if field["type"]=="integer" and not float(value).is_integer():raise ValueError("Entero fraccionario: "+name)
            for bound,limit in field.get("bounds",{}).items():
                if (bound=="minimum" and value<limit or bound=="maximum" and value>limit or
                    bound=="exclusiveMinimum" and value<=limit):raise ValueError("Fuera de rango: "+name)
            values.append(str(int(value)) if name=="categoryId" else float(value))
        data[name]=values
    for i,month in enumerate(months):
        m=int(month[-2:])
        if not math.isclose(data["mes_sin"][i],math.sin(2*math.pi*m/12),abs_tol=1e-9) or not math.isclose(data["mes_cos"][i],math.cos(2*math.pi*m/12),abs_tol=1e-9):
            raise ValueError("Calendario no coincide con mes")
        p,coverage=data["proporcion_por_mayor_mes_anterior"][i],data["cobertura_modalidad_mes_anterior"][i]
        if not math.isnan(p) and not math.isnan(coverage) and p>coverage+1e-12:raise ValueError("Modalidad inconsistente")
        if data["ventas_mes_anterior"][i]==0 and (not math.isnan(p) or not math.isnan(coverage)):
            raise ValueError("Sin ventas, las proporciones son null")
        minor,major=data["precio_menor_cierre_anterior_bs"][i],data["precio_mayor_cierre_anterior_bs"][i]
        if not math.isnan(minor) and not math.isnan(major) and major>minor+1e-9:raise ValueError("Mayor supera menor")
        v1,v2=data["variacion_precio_menor_conocida"][i],data["variacion_precio_mayor_conocida"][i]
        if math.isnan(minor) and not math.isnan(v1) or math.isnan(major) and not math.isnan(v2):
            raise ValueError("Variación sin precio histórico de base")
        if all(math.isfinite(v) for v in [minor,major,v1,v2]) and major*(1+v2)>minor*(1+v1)+1e-8:
            raise ValueError("Plan mayor supera menor")
        coverage=data["cobertura_stock_mes_anterior"][i];days=data["dias_sin_stock_mes_anterior"][i]
        calendar_days=(cutoff(month)-cutoff(month_offset(month,-1))).days
        observed=coverage*calendar_days
        if not math.isclose(observed,round(observed),abs_tol=1e-8):raise ValueError("Cobertura sin días enteros")
        if coverage==0 and not math.isnan(days):raise ValueError("Stock no observado requiere null")
        if not math.isnan(days) and days>observed+1e-8:raise ValueError("Días sin stock exceden observados")
        if math.isnan(data["tipo_cambio_bs_usd_conocido"][i]) and (not math.isnan(data["variacion_tipo_cambio_ultimo_mes"][i]) or not math.isnan(data["antiguedad_tipo_cambio_dias"][i])):
            raise ValueError("Variación o edad sin cotización conocida")
    return data,months


def validate_cohort(frame,months,manifest):
    """Identidad de filas fuera de X numérico. Fixtures sin IDs no la certifican."""
    if not isinstance(frame.index,pd.MultiIndex):return None
    if list(frame.index.names)!=["productId","locationId",CONTEXT] or frame.index.has_duplicates:
        raise ValueError("Identidad de filas inválida")
    pairs={(p,s) for p in manifest["selected_product_ids"] for s in manifest["selected_store_ids"]}
    expected={(p,s,m) for p,s in pairs for m in set(months)}
    keys=list(frame.index)
    if set(keys)!=expected or any(key[2]!=month for key,month in zip(keys,months)):
        raise ValueError("Fit requiere cohortes completas por mes, sin división aleatoria de filas")
    return canonical_hash([[int(k[0]),int(k[1]),str(k[2])] for k in keys])


class DemandPreprocessor(TransformerMixin,BaseEstimator):
    """Una instancia nueva por fold. fit ignora y, transform no aprende."""
    def __init__(self,feature_set_id="expanded_v2_full",model_kind="linear_regression",
                 train_start="2025-01",train_end="2026-03",root=None):
        self.feature_set_id=feature_set_id;self.model_kind=model_kind
        self.train_start=train_start;self.train_end=train_end;self.root=root

    def fit(self,X,y=None):
        if hasattr(self,"_fitted_"):raise ValueError("Instancia ya ajustada: crear otra por fold")
        if self.feature_set_id not in GROUPS or self.model_kind not in ("linear_regression","random_forest"):
            raise ValueError("Modelo o grupo no aprobado")
        spec,plan,fields,_,spec_sha,manifest=read_context(ROOT if self.root is None else self.root)
        if [self.train_start,self.train_end] not in spec["fit_windows"]:raise ValueError("Ventana fuera de TRAIN aprobado")
        data,months=validate_frame(X,fields)
        if not months:raise ValueError("TRAIN vacío")
        actual_window=[min(months),max(months)]
        if actual_window not in spec["fit_windows"] or not self.train_start<=actual_window[0]<=actual_window[1]<=self.train_end:
            raise ValueError("Fit fuera de los prefijos TRAIN aprobados")
        expected=[];month=actual_window[0]
        while month<=actual_window[1]:expected.append(month);month=month_offset(month,1)
        if set(months)!=set(expected):raise ValueError("Fit requiere meses completos sin huecos")
        row_keys_sha=validate_cohort(X,months,manifest)
        columns=list(RAW[:GROUPS[self.feature_set_id]])
        numeric=[n for n in columns if n!="categoryId"]
        for name in columns:
            observed=[v for v in data[name] if v is not None and not (isinstance(v,float) and math.isnan(v))]
            if not observed:raise ValueError("Grupo sin datos TRAIN: "+name)
            if len(set(observed))<=1:raise ValueError("Constante TRAIN requiere revisión: "+name)
        matrix=np.array([data[n] for n in numeric],dtype=float).T
        try:
            with np.errstate(over="raise",invalid="raise"):
                medians=np.array([np.median(c[~np.isnan(c)]) for c in matrix.T])
        except FloatingPointError as exc:raise ValueError("Mediana desbordada") from exc
        if not np.isfinite(medians).all():raise ValueError("Mediana no finita")
        imputed=np.where(np.isnan(matrix),medians,matrix)
        means=scales=None
        if self.model_kind=="linear_regression":
            try:
                with np.errstate(over="raise",invalid="raise",divide="raise"):
                    scaler=StandardScaler().fit(imputed)
                means=scaler.mean_.tolist();scales=scaler.scale_.tolist()
            except FloatingPointError as exc:raise ValueError("Escalado desbordado") from exc
            if not np.isfinite(means).all() or not np.isfinite(scales).all() or any(v<=0 for v in scales):
                raise ValueError("Parámetros de escala inválidos")
        nullable={f["name"] for f in fields if f["nullable"]}
        indicators=[n for n in numeric if n in nullable]
        categories=sorted({v for v in data["categoryId"] if v is not None},key=int)+[UNKNOWN] if "categoryId" in columns else []
        outputs=numeric+["missing::"+n for n in indicators]+["categoryId::"+c for c in categories]
        fit_frame={n:[None if missing(v) else v for v in data[n]] for n in RAW}
        fit_frame[CONTEXT]=months
        state=dict(adapter_version=VERSION,feature_set_id=self.feature_set_id,model_kind=self.model_kind,
            raw_features=list(RAW),columns=columns,numeric_columns=numeric,indicator_columns=indicators,
            categories=categories,medians=medians.tolist(),means=means,scales=scales,output_columns=outputs,
            field_specs=copy.deepcopy(fields),train_window=actual_window,configured_window=[self.train_start,self.train_end],fit_rows=len(months),
            month_counts={m:months.count(m) for m in sorted(set(months))},y_used=False,
            contract_sha256=spec_sha,experiment_contract_sha256=spec["experiment_contract_sha256"],
            schema_binding_build_manifest_sha256=spec["input_build"]["manifest_sha256"],
            fit_frame_sha256=canonical_hash(fit_frame),
            fit_row_keys_sha256=row_keys_sha,
            fit_frame_origin="CALLER_FRAME_PROVENANCE_TO_BE_BOUND_BY_TRAINING_RUN")
        self._state_=state;self._fitted_=True
        self.n_features_in_=len(RAW)+1
        self.feature_names_in_=np.array([*RAW,CONTEXT],dtype=object)
        return self

    def transform(self,X):
        check_is_fitted(self,"_fitted_")
        s=self._state_;data,_=validate_frame(X,s["field_specs"])
        numeric=s["numeric_columns"]
        matrix=np.array([data[n] for n in numeric],dtype=float).T
        mask=np.isnan(matrix)
        imputed=np.where(mask,np.array(s["medians"]),matrix)
        try:
            with np.errstate(over="raise",invalid="raise",divide="raise"):
                numbers=(imputed-np.array(s["means"]))/np.array(s["scales"]) if s["model_kind"]=="linear_regression" else imputed
                indicators=mask[:,[numeric.index(n) for n in s["indicator_columns"]]].astype(float)
                category=np.zeros((len(X),len(s["categories"])),dtype=float)
                if s["categories"]:
                    vocab={c:i for i,c in enumerate(s["categories"])}
                    for i,value in enumerate(data["categoryId"]):category[i,vocab.get(value,vocab[UNKNOWN])]=1
                result=np.hstack([numbers,indicators,category])
        except FloatingPointError as exc:raise ValueError("Transformación desbordada") from exc
        if not np.isfinite(result).all():raise ValueError("Matriz transformada no finita")
        return result

    def get_feature_names_out(self,input_features=None):
        check_is_fitted(self,"_fitted_")
        if input_features is not None and set(input_features)!=set(RAW)|{CONTEXT}:
            raise ValueError("Nombres de entrada distintos del contrato")
        return np.array(self._state_["output_columns"],dtype=object)

    def to_state(self):
        check_is_fitted(self,"_fitted_")
        payload=copy.deepcopy(self._state_)
        return {"state":payload,"sha256":canonical_hash(payload)}

    @classmethod
    def from_state(cls,document,expected_sha256=None):
        s=copy.deepcopy(document["state"]);h=canonical_hash(s)
        if document["sha256"]!=h or expected_sha256 is not None and expected_sha256!=h:raise ValueError("Estado alterado")
        group=s["feature_set_id"];kind=s["model_kind"]
        if s["adapter_version"]!=VERSION or group not in GROUPS or kind not in ("linear_regression","random_forest"):
            raise ValueError("Estado de otra versión")
        columns=list(RAW[:GROUPS[group]]);numeric=[n for n in columns if n!="categoryId"]
        if s["raw_features"]!=list(RAW) or s["columns"]!=columns or s["numeric_columns"]!=numeric:raise ValueError("Selección alterada")
        if [c["name"] for c in s["field_specs"]]!=list(RAW) or any(c["role"]!="FEATURE" for c in s["field_specs"]):raise ValueError("Specs alteradas")
        indicators=[n for n in numeric if next(f for f in s["field_specs"] if f["name"]==n)["nullable"]]
        if s["indicator_columns"]!=indicators:raise ValueError("Indicadores alterados")
        cats=s["categories"]
        if "categoryId" in columns:
            if not cats or cats[-1]!=UNKNOWN or len(set(cats))!=len(cats) or any(not c.isdigit() or int(c)<=0 for c in cats[:-1]):raise ValueError("Vocabulario inválido")
        elif cats:raise ValueError("Categoría inesperada")
        if len(s["medians"])!=len(numeric) or not np.isfinite(s["medians"]).all():raise ValueError("Medianas inválidas")
        if kind=="linear_regression":
            if s["means"] is None or s["scales"] is None or len(s["means"])!=len(numeric) or len(s["scales"])!=len(numeric) or not np.isfinite(s["means"]).all() or not np.isfinite(s["scales"]).all() or any(v<=0 for v in s["scales"]):raise ValueError("Escala inválida")
        elif s["means"] is not None or s["scales"] is not None:raise ValueError("Bosque con escalado inesperado")
        outputs=numeric+["missing::"+n for n in indicators]+["categoryId::"+c for c in cats]
        if s["output_columns"]!=outputs or s["y_used"] is not False:raise ValueError("Estado incompatible")
        instance=cls(group,kind,*s["configured_window"])
        instance._state_=s;instance._fitted_=True;instance.n_features_in_=len(RAW)+1
        instance.feature_names_in_=np.array([*RAW,CONTEXT],dtype=object)
        return instance
