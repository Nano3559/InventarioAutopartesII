"""Adaptador separado 2.2.0. Ningún ajuste ocurre al importar o preparar datos.

Reutiliza transform y validaciones puras 2.1 sin modificar sus módulos congelados.
"""
import copy
import math
import numpy as np
from sklearn.preprocessing import StandardScaler
from .preprocessing import DemandPreprocessor as LegacyPreprocessor,RAW,GROUPS,CONTEXT,UNKNOWN,validate_frame,validate_cohort,missing
from .structure import ROOT
from .validate_build import canonical_hash,month_offset
from .data_v2_2 import read_context,load_feature_partition,VERSION

class DemandPreprocessor22(LegacyPreprocessor):
    """fit exclusivo de TRAIN o fixtures. transform heredado no aprende."""
    def fit(self,X,y=None):
        if hasattr(self,"_fitted_"):raise ValueError("Instancia ya ajustada: crear otra por fold")
        if self.feature_set_id not in GROUPS or self.model_kind not in ("linear_regression","random_forest"):
            raise ValueError("Modelo o grupo no aprobado")
        spec,plan,fields,_,spec_sha,manifest=read_context(ROOT if self.root is None else self.root)
        if X.attrs.get("dataset_version")=="2.2.0" and spec["real_dataset_fit_in_preparation"] is False:raise PermissionError("PREPROCESSING_FIT_NOT_AUTHORIZED_REAL_DATASET")
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
        if row_keys_sha is None and X.attrs.get("fixture_only") is not True:raise ValueError("Identidad completa requerida, salvo fixture explícito")
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
            fit_frame_origin="CONTROLLED_FIXTURE_ONLY" if X.attrs.get("fixture_only") else "CALLER_FRAME_PROVENANCE_TO_BE_BOUND_BY_TRAINING_RUN")
        self._state_=state;self._fitted_=True
        self.n_features_in_=len(RAW)+1
        self.feature_names_in_=np.array([*RAW,CONTEXT],dtype=object)
        return self

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
