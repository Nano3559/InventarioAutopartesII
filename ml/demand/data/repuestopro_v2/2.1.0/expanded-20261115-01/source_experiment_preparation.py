"""Preflight y prototipos de preparación V2-08. No contiene fit o entrenamiento.

No genera CSV de ventas, no modifica el generador publicado y no usa Neon.
Las funciones de abastecimiento son fixtures del futuro simulador, no H5.
"""
import argparse
import calendar
import csv
from datetime import timedelta
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v2.structure import ROOT, sha256_file, token
from v2.validate_build import cutoff, instant


def training_feature_profile(path, schema, start, end):
    """No procesa targets ni valores de features fuera de TRAIN."""
    columns=[c for c in schema["columns"] if c["role"]=="FEATURE"]
    known={c["name"]:set() for c in columns};nulls={c["name"]:0 for c in columns}
    months={};count=0
    with Path(path).open(encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            month=row["mes_objetivo"]
            if not start<=month<=end:continue
            count+=1;months[month]=months.get(month,0)+1
            for c in columns:
                name=c["name"];value=row[name]
                if value=="":nulls[name]+=1;continue
                if c["type"] in ("integer","number"):
                    value=float(value)
                    if not math.isfinite(value):raise ValueError("Feature TRAIN no finita")
                known[name].add(value)
    if count==0:raise ValueError("TRAIN vacío")
    return {"rows":count,"months":months,"columns":{
        c["name"]:{"unique_nonnull":len(known[c["name"]]),"nulls":nulls[c["name"]],
                   "constant_value":next(iter(known[c["name"]])) if len(known[c["name"]])==1 else None}
        for c in columns},"labels_processed":False,"validation_features_processed":False,"test_features_processed":False}


def quote_asof(events, at, source_id="SYNTHETIC_REFERENCE", rate_kind="SIMULATED_MARKET_REFERENCE"):
    """Elige un evento disponible. No inventa edad o valor de una cotización."""
    at=instant(at);candidates=[]
    for e in events:
        available=instant(e["available_at"])
        if available>at or e["source_id"]!=source_id or e["rate_kind"]!=rate_kind:continue
        observed=instant(e["observed_at"])
        if observed>available:raise ValueError("Observación posterior a publicación")
        value=e["value"]
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<=0:
            raise ValueError("Cotización inválida")
        if e["unit"]!="Bs/USD":raise ValueError("Unidad no comparable")
        if e["source_id"]==source_id and e["rate_kind"]==rate_kind and available<=at:
            candidates.append((observed,available,e))
    if not candidates:return {"value":None,"age_days":None,"observed_at":None,"available_at":None,"status":"UNKNOWN"}
    latest=max((o,a) for o,a,_ in candidates)
    matches=[e for o,a,e in candidates if (o,a)==latest]
    if len({e["value"] for e in matches})!=1:raise ValueError("Cotizaciones contradictorias")
    e=matches[0]
    return {"value":e["value"],"age_days":(at-latest[0]).days,"observed_at":e["observed_at"],
            "available_at":e["available_at"],"status":"KNOWN_WITH_AGE"}


def integer(value):
    if not isinstance(value,int) or isinstance(value,bool) or value<0:raise ValueError("Se requieren unidades enteras no negativas")
    return value


def supply_plan(*,at,sellable,reserved,history_units,firm_orders,incoming,safety_units=5,lot_size=6,coverage_months=1):
    """Prototipo del simulador: no acepta target ni unidades futuras realizadas.

    No duplica demanda histórica y pedidos conocidos: usa su máximo como piso.
    Los compromisos ya descontados del stock NO deben repetirse en firm_orders.
    """
    at=instant(at);sellable=integer(sellable);reserved=integer(reserved)
    if reserved>sellable:raise ValueError("Reservas exceden stock: revisar compromisos, no duplicarlos")
    if len(history_units)!=3:raise ValueError("Se requieren tres meses completos")
    history=[integer(x) for x in history_units];safety_units=integer(safety_units)
    if integer(lot_size)==0 or integer(coverage_months)==0:raise ValueError("Lote y horizonte deben ser positivos")
    absolute=at.year*12+at.month-1+coverage_months
    year,month=absolute//12,absolute%12+1
    window=at.replace(year=year,month=month,day=min(at.day,calendar.monthrange(year,month)[1]))
    committed=allocated_reservations=0;order_ids=set();deadlines=[]
    for order in firm_orders:
        if order["id"] in order_ids:raise ValueError("Pedido repetido")
        order_ids.add(order["id"]);quantity=integer(order["units"])
        if reserved and "reserved_units" not in order:raise ValueError("Reserva por pedido no identificada")
        order_reserved=integer(order.get("reserved_units",0))
        if order_reserved>quantity:raise ValueError("Reserva mayor al pedido")
        if instant(order["known_at"])<=at and at<=instant(order["due_at"])<window:
            committed+=quantity;allocated_reservations+=order_reserved;deadlines.append(instant(order["due_at"]))
        elif order_reserved:raise ValueError("Reserva fuera del horizonte: revisar posición")
    if allocated_reservations>reserved:raise ValueError("Reservas duplicadas o sin stock asignado")
    inbound=0;shipment_ids=set();deadline=min(deadlines) if deadlines else window
    for item in incoming:
        if item["id"] in shipment_ids:raise ValueError("Entrada repetida")
        shipment_ids.add(item["id"]);pending=integer(item["pending_units"])
        if (item["status"]=="IN_TRANSIT" and instant(item["known_at"])<=at
            and at<=instant(item["expected_at"])<window and instant(item["expected_at"])<=deadline):inbound+=pending
    historical=sum(history)/3*coverage_months
    required=max(max(0,historical-reserved),committed-allocated_reservations)+safety_units
    position=sellable-reserved+inbound
    quantity=math.ceil(max(0,required-position)/lot_size)*lot_size
    return dict(order_units=quantity,position=position,incoming_firm_pending=inbound,
        known_commitments=committed,reference_units=historical,required_units=required,
        known_unreserved_commitments=committed-allocated_reservations,
        sellable_now=sellable,reserved_units=reserved,
        required_by=deadline.isoformat(),fulfillment_guaranteed=False,
        rule="MAX_HISTORY_OR_COMMITMENTS_NOT_SUM",commercial_replenishment_rule_approved=False,
        warning="Fixtures de simulación. Reservas de esta ventana identificadas sin duplicarlas como demanda nueva. No cambia features ni stock real.")


def receive_and_fulfil(*,sellable,pending,received,requested):
    sellable,pending,received,requested=map(integer,(sellable,pending,received,requested))
    if received>pending:raise ValueError("Recepción mayor que pendiente")
    available=sellable+received;sold=min(requested,available)
    return dict(sold=sold,closing_stock=available-sold,remaining_transit=pending-received,
                unmet_simulated_units=requested-sold)


def preparation_examples():
    at="2026-02-01T00:00:00-04:00";date=instant(at)
    quote_cases=[]
    for age in [0,2,7,30]:
        observed=(date-timedelta(days=age)).isoformat()
        events=[dict(value=10,observed_at=observed,available_at=observed,unit="Bs/USD",
                     source_id="SYNTHETIC_REFERENCE",rate_kind="SIMULATED_MARKET_REFERENCE")]
        quote_cases.append({"expected_age":age,"selected":quote_asof(events,at)})
    order=dict(id="FIXTURE_WHOLESALE_40",units=40,known_at="2026-01-31T00:00:00-04:00",due_at="2026-02-15T00:00:00-04:00")
    plan=supply_plan(at=at,sellable=5,reserved=0,history_units=[1,2,3],firm_orders=[order],incoming=[])
    fulfilled=receive_and_fulfil(sellable=5,pending=plan["order_units"],received=plan["order_units"],requested=40)
    partial=receive_and_fulfil(sellable=5,pending=plan["order_units"],received=plan["order_units"]//2,requested=40)
    return dict(scope="PREPARATION_FIXTURES_NOT_A_NEW_DATASET",quote_ages=quote_cases,
        planned_order=plan,full_receipt=fulfilled,partial_receipt=partial,
        sampled_sales_dataset_created=False)


def preflight(run_id,root=ROOT):
    root=Path(root).resolve();token(run_id)
    contract_path=root/"v2/contracts/experiments.v2.json"
    contract=json.loads(contract_path.read_text(encoding="utf-8"))
    prep=json.loads((root/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
    source=root/contract["input_build"]["relative_path"]
    if not source.resolve().is_relative_to(root/"data/repuestopro_v2"):raise ValueError("Build fuera de V2")
    if sha256_file(source/"manifest.json")!=contract["input_build"]["manifest_sha256"]:raise ValueError("Build cambió")
    evidence=root/Path(prep["dataset_validation"]["report"]).relative_to("ml/demand")
    if sha256_file(evidence)!=prep["dataset_validation"]["report_sha256"]:raise ValueError("Revisión V2-07 cambió")
    gate=json.loads(evidence.read_text(encoding="utf-8"))
    if gate["status"]!="PASSED_FOR_DATA_INTEGRITY_AND_OFFLINE_POLICY":raise ValueError("V2-07 no pasó")
    if gate["manifest_sha256"]!=contract["input_build"]["manifest_sha256"]:raise ValueError("Revisión pertenece a otro build")
    for name,h in gate["input_files_sha256"].items():
        if sha256_file(source/name)!=h:raise ValueError("Entrada V2-07 modificada")
    schema=json.loads((source/"schema.json").read_text(encoding="utf-8"))
    profile=training_feature_profile(source/"dataset_supervisado.csv",schema,"2025-01","2026-03")
    constant=[n for n,v in profile["columns"].items() if v["unique_nonnull"]<=1]
    if constant!=contract["constant_policy"]["expected_constants_for_this_build"]:raise ValueError("Constantes no revisadas")
    declared={c["name"] for c in schema["columns"] if c["role"]=="FEATURE"}
    for group in contract["feature_sets"]:
        if not set(group["columns"])<=declared or set(group["columns"])&set(constant):raise ValueError("Feature set no revisado")
        if any(profile["columns"][c]["unique_nonnull"]==0 for c in group["columns"]):raise ValueError("Feature sin dato TRAIN")
    folds=[]
    for fold in contract["temporal_validation"]["folds"]:
        train,valid=fold["train"],fold["validation"]
        if not train[0]<=train[1]<valid[0]<=valid[1]<=contract["temporal_validation"]["outer_train"][1]:raise ValueError("Fold fuera de TRAIN")
        folds.append({**fold,"train_rows":sum(n for m,n in profile["months"].items() if train[0]<=m<=train[1]),
                      "validation_rows":sum(n for m,n in profile["months"].items() if valid[0]<=m<=valid[1])})
    result=dict(stage="V2-08_PREPARATION",status="PREPARED_NOT_TRAINED",constant_features=constant,
        training_feature_profile=profile,folds=folds,feature_set_sizes={g["id"]:len(g["columns"]) for g in contract["feature_sets"]},
        current_build_suitable_scope="INITIAL_LOW_VOLUME_ACADEMIC_EXPERIMENTS_ONLY",expanded_volume_build_exists=False,
        planned_fit_count=contract["execution_budget"]["maximum_planned_fits"],actual_fit_count=0,
        training_authorized=False,neon_used=False,new_dataset_created=False,
        input_manifest_sha256=contract["input_build"]["manifest_sha256"],contract_sha256=sha256_file(contract_path),
        implementation_sha256=sha256_file(Path(__file__)),versions={"python":sys.version.split()[0],"scikit_learn":version("scikit-learn")},
        simulations=preparation_examples(),pending=contract["pending"])
    dest=root/"reports/v2/experiments_preparation"/run_id
    if not dest.resolve().is_relative_to(root/"reports/v2"):raise ValueError("Reporte fuera de V2")
    dest.mkdir(parents=True,exist_ok=False)
    with (dest/"preflight.json").open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    return dest,result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--run-id",required=True)
    args=parser.parse_args();path,result=preflight(args.run_id)
    print(json.dumps({"path":str(path),"status":result["status"],"actual_fit_count":result["actual_fit_count"]},ensure_ascii=True))
