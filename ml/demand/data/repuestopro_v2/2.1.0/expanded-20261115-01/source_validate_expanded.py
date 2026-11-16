"""Verificación física independiente de 2.1.0. Sin entrenamiento o métricas TEST."""
import argparse
from collections import Counter,defaultdict
import csv
from datetime import timedelta
import json
import math
from pathlib import Path
import re
import sys

if __package__ in (None,""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v2.structure import ROOT,sha256_file,token
from v2.validate_build import (canonical_hash,check_rows,close,cutoff,instant,month_offset,
                              read_table,split_issues,strict_json,training_statistics)


def validate_tables(bundle,schema,catalog,config,legacy,case_registry=None):
    failures=check_rows(bundle["base"],bundle["supervised"],bundle["ledger"],catalog)
    def check(condition,code):
        if not condition:failures.append(code)
    base={(r["productId"],r["locationId"],r["mes"]):r for r in bundle["base"]}
    ledger={(r["productId"],r["locationId"],r["mes"]):r for r in bundle["ledger"]}
    pairs={(k[0],k[1]) for k in base}
    orders={};order_day=defaultdict(list);order_month=defaultdict(list)
    for o in bundle["orders"]:
        check(o["order_id"] not in orders,"DUPLICATE_ORDER");orders[o["order_id"]]=o
        at=instant(o["due_at"]);known=instant(o["known_at"])
        check(known<=at,"ORDER_KNOWLEDGE_AFTER_DUE")
        check(o["mode"] in ("POR_MENOR","POR_MAYOR"),"INVALID_MODE")
        check(o["recorded_mode"] in (o["mode"],"UNKNOWN"),"FABRICATED_MODE")
        check(isinstance(o["requested_units"],int) and o["requested_units"]>0,"REQUEST_UNITS")
        check(0<=o["fulfilled_units"]<=o["requested_units"] and o["unmet_units"]==o["requested_units"]-o["fulfilled_units"],"ORDER_UNITS")
        pair=(o["productId"],o["locationId"]);month=at.astimezone(cutoff(o["mes"]).tzinfo).strftime("%Y-%m")
        check(pair in pairs and month==o["mes"],"ORDER_ENTITY_OR_MONTH")
        source=base.get((*pair,month))
        if source:
            price=source["precio_mayor_cierre_bs"] if o["mode"]=="POR_MAYOR" else source["precio_menor_cierre_bs"]
            check(close(price,o["unit_price_bs"]),"HISTORICAL_UNIT_PRICE")
        order_day[(*pair,at.strftime("%Y-%m-%d"))].append(o)
        order_month[(*pair,month)].append(o)
    shipments={};sent_month=Counter();shipments_by_pair=defaultdict(list)
    for s in bundle["shipments"]:
        check(s["shipment_id"] not in shipments,"DUPLICATE_SHIPMENT");shipments[s["shipment_id"]]=s
        check(instant(s["sent_at"])<=instant(s["expected_at"]),"SHIPMENT_TIME")
        check(s["sent_units"]>0 and s["received_units"]>=0 and s["pending_units"]>=0 and s["sent_units"]==s["received_units"]+s["pending_units"],"SHIPMENT_TOTAL")
        sent_month[(s["productId"],s["locationId"],s["sent_at"][:7])]+=s["sent_units"]
        shipments_by_pair[(s["productId"],s["locationId"])].append(s)
    receipt_day=Counter();receipt_month=Counter();receipt_shipment=Counter();receipt_ids=set();received_events=defaultdict(list)
    for r in bundle["receipts"]:
        check(r["receipt_id"] not in receipt_ids,"DUPLICATE_RECEIPT");receipt_ids.add(r["receipt_id"])
        ship=shipments.get(r["shipment_id"])
        if ship is None:failures.append("ORPHAN_RECEIPT");continue
        check((r["productId"],r["locationId"])==(ship["productId"],ship["locationId"]),"RECEIPT_LOCATION")
        check(instant(ship["sent_at"])<=instant(r["received_at"]),"RECEIVED_BEFORE_SENT")
        check(isinstance(r["quantity"],int) and r["quantity"]>0,"RECEIPT_UNITS")
        receipt_day[(r["productId"],r["locationId"],r["received_at"][:10])]+=r["quantity"]
        receipt_month[(r["productId"],r["locationId"],r["received_at"][:7])]+=r["quantity"]
        receipt_shipment[r["shipment_id"]]+=r["quantity"];received_events[r["shipment_id"]].append(r)
    for id_,s in shipments.items():check(receipt_shipment[id_]==s["received_units"],"RECEIPT_SUM")
    previous={};daily_keys=set();observed=Counter();zero_observed=Counter();zero_actual=Counter();daily_sales=Counter()
    for d in bundle["daily"]:
        pair=(d["productId"],d["locationId"]);key=(*pair,d["date"]);month=(*pair,d["date"][:7])
        check(key not in daily_keys,"DUPLICATE_DAY");daily_keys.add(key)
        check(pair in pairs and month in base,"DAILY_ENTITY_OR_MONTH")
        for name in ["opening_stock","received_units","sold_units","closing_stock"]:
            check(isinstance(d[name],int) and d[name]>=0,"DAILY_NONNEGATIVE_INTEGER")
        if pair in previous:
            check(d["opening_stock"]==previous[pair]["closing_stock"],"DAILY_CONTINUITY")
            check(instant(d["date"]+"T00:00:00-04:00")-instant(previous[pair]["date"]+"T00:00:00-04:00")==timedelta(days=1),"DAILY_GAP")
        else:check(d["opening_stock"]==0,"INITIAL_STOCK")
        previous[pair]=d
        check(d["received_units"]==receipt_day[key],"DAILY_RECEIPTS")
        available=d["opening_stock"]+d["received_units"]
        check(d["zero_before_orders"]==int(available==0),"ZERO_STOCK_IS_NOT_ZERO_SALES")
        actual_sold=0
        for o in sorted(order_day[key],key=lambda o:(o["mode"]!="POR_MAYOR",o["order_id"])):
            check(o["fulfilled_units"]==min(o["requested_units"],available),"SALE_BEFORE_RECEIPT_OR_FORCED_FULFILMENT")
            available-=o["fulfilled_units"];actual_sold+=o["fulfilled_units"]
        check(actual_sold==d["sold_units"] and available==d["closing_stock"],"DAILY_CONSERVATION")
        check(d["observed"] in (0,1),"SENSOR_FLAG")
        observed[month]+=d["observed"];zero_observed[month]+=d["observed"]*d["zero_before_orders"]
        zero_actual[month]+=d["zero_before_orders"];daily_sales[month]+=actual_sold
    expected_days=(cutoff("2026-10")-cutoff("2024-10")).days*len(pairs)
    check(len(daily_keys)==expected_days,"DAILY_GRID")
    quote_ids=set()
    for e in bundle["quotes"]:
        check(e["quote_id"] not in quote_ids,"DUPLICATE_QUOTE");quote_ids.add(e["quote_id"])
        check(instant(e["observed_at"])<=instant(e["available_at"]),"QUOTE_KNOWLEDGE")
        check(isinstance(e["value"],(int,float)) and math.isfinite(e["value"]) and e["value"]>0,"QUOTE_VALUE")
        check(e["unit"]=="Bs/USD" and e["source_id"]==config["quote_source"] and e["rate_kind"]==config["rate_kind"],"QUOTE_TYPE")
    plans={}
    for p in bundle["plans"]:
        key=(p["productId"],p["locationId"],p["mes"])
        check(key not in plans,"DUPLICATE_PLAN");plans[key]=p
        at=cutoff(p["mes"]);end=cutoff(month_offset(p["mes"],1))
        check(instant(p["planned_at"])==at,"PLAN_CLOCK")
        known=[o for o in order_month[key] if instant(o["known_at"])<=at]
        known_ids=sorted(o["order_id"] for o in known)
        check(sorted(strict_json(p["known_order_ids"]))==known_ids,"PLAN_USED_UNKNOWN_FUTURE_ORDER")
        history=[base[(*key[:2],month_offset(key[2],-j))] for j in (3,2,1) if (*key[:2],month_offset(key[2],-j)) in base]
        check(strict_json(p["history_months"])==[h["mes"] for h in history] and strict_json(p["history_units"])==[h["unidades_vendidas_brutas"] for h in history],"PLAN_HISTORY")
        check(p["bootstrap"]==int(len(history)<3),"FABRICATED_BOOTSTRAP_HISTORY")
        known_units=sum(o["requested_units"] for o in known)
        check(p["known_commitments"]==known_units,"COMMITMENT_UNITS")
        deadline=min([instant(o["due_at"]) for o in known]+[end]);inbound=0
        for s in shipments_by_pair[key[:2]]:
            id_=s["shipment_id"]
            if instant(s["sent_at"])>=at:continue
            expected=instant(s["expected_at"])
            if at<=expected<end and expected<=deadline:
                inbound+=s["sent_units"]-sum(r["quantity"] for r in received_events[id_] if instant(r["received_at"])<at)
        opening=ledger[key]["opening_stock"]
        reference=sum(h["unidades_vendidas_brutas"] for h in history)/3 if len(history)==3 else 0
        required=max(reference,known_units)+config["safety_units"];position=opening+inbound
        sent=math.ceil(max(0,required-position)/config["lot_size"])*config["lot_size"]
        check(close(p["position"],position) and close(p["required_units"],required) and p["sent_units"]==sent,"PLAN_TARGET_LEAKAGE_OR_DOUBLE_COUNT")
        check(p["opening_stock"]==opening and sent_month[key]==sent,"PLAN_DISPATCH")
    check(set(plans)==set(base),"PLANS_GRID")
    for key,r in base.items():
        at=cutoff(month_offset(key[2],1))
        available=[q for q in bundle["quotes"] if instant(q["available_at"])<=at]
        selected=max(available,key=lambda q:(instant(q["observed_at"]),instant(q["available_at"])))
        check(r["tipo_cambio_bs_usd"]==selected["value"] and r["cotizacion_observada_at"]==selected["observed_at"] and r["cotizacion_disponible_at"]==selected["available_at"],"QUOTE_ASOF_NOT_JITTER")
        check(r["cotizacion_fuente_id"]==selected["source_id"],"QUOTE_SOURCE")
        o=order_month[key]
        check(sum(x["fulfilled_units"] for x in o)==r["unidades_vendidas_brutas"]==daily_sales[key],"TARGET_NOT_ACTUALLY_SOLD")
        check(sum(x["requested_units"] for x in o)==ledger[key]["latent_units"],"REQUESTED_UNITS_LEDGER")
        for field,mode in [("unidades_por_menor","POR_MENOR"),("unidades_por_mayor","POR_MAYOR"),("unidades_modalidad_desconocida","UNKNOWN")]:
            check(r[field]==sum(x["fulfilled_units"] for x in o if x["recorded_mode"]==mode),"RECORDED_MODALITY")
        check(observed[key]==r["dias_observados_stock"] and zero_observed[key]==r["dias_sin_stock_observados"],"SENSOR_SUM")
        check(zero_actual[key]==ledger[key]["zero_stock_days"],"ZERO_DAYS_SUM")
        check(receipt_month[key]==ledger[key]["received_units"] and sent_month[key]==ledger[key]["sent_units"],"MONTHLY_RECEIPTS_OR_SHIPMENTS")
    if case_registry is None:
        case_registry=json.loads((ROOT/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))["scenario_design"]["scenarios"]
    cases={c["scenario_id"]:c for c in case_registry};instances=set()
    for a in bundle["audit"]:
        key=(a["productId"],a["locationId"],a["mes_objetivo"]);source=base.get(key);case=cases.get(a["scenario_id"])
        if source is None or case is None:failures.append("AUDIT_ORPHAN");continue
        check(a["scenario_instance_id"] not in instances,"AUDIT_DUPLICATE");instances.add(a["scenario_instance_id"])
        check(a["history_snapshot_id"]==source["history_snapshot_id"] and a["scenario_instance_id"]==canonical_hash([source["history_snapshot_id"],a["scenario_id"]])[:32],"AUDIT_SNAPSHOT")
        check(all(a[n]==case[n] for n in ["case_class","issue_code","expected_action"]),"AUDIT_ACTION")
        check(a["latent_demand_units"]==ledger[key]["latent_units"],"AUDIT_LATENT_IS_CONTROL_ONLY")
        params=strict_json(a["parameters_json"])
        check(params["scope"]=="SYNTHETIC_INSTANCE_NOT_VALIDATED_SCENARIO_TEST","AUDIT_CLAIM")
        conditions={"N01":source["unidades_por_menor"]>0,"N02":source["unidades_por_mayor"]>0,
            "N03":source["unidades_por_menor"]>0 and source["unidades_por_mayor"]>0,
            "N04":source["unidades_vendidas_brutas"]==0,
            "G05":source["unidades_modalidad_desconocida"]>0,
            "G06":source["unidades_vendidas_brutas"]==0 and source["dias_observados_stock"]<(cutoff(month_offset(key[2],1))-cutoff(key[2])).days,
            "G07":(cutoff(month_offset(key[2],1))-instant(source["cotizacion_observada_at"])).days>=7,
            "G18":key[2]=="2024-10","A10":source["unidades_por_mayor"]>0,
            "A06":ledger[key]["zero_stock_days"]>0,"A07":ledger[key]["zero_stock_days"]==(cutoff(month_offset(key[2],1))-cutoff(key[2])).days,
            "A08":params["profile"]=="PARTIAL_LATE" and ledger[key]["sent_units"]>0}
        check(conditions.get(a["scenario_id"],False),"AUDIT_EVENT_NOT_OBSERVED")
        if a["scenario_id"]=="G07":
            check(a["event_at"]==source["cotizacion_observada_at"] and a["available_at"]==source["cotizacion_disponible_at"],"AUDIT_QUOTE_CLOCK")
        else:
            check(instant(a["event_at"])==cutoff(month_offset(key[2],1)) and a["event_at"]==a["available_at"],"AUDIT_SUMMARY_CLOCK")
    ages={r["antiguedad_tipo_cambio_dias"] for r in bundle["supervised"] if "2025-01"<=r["mes_objetivo"]<="2026-03"}
    check(ages=={0,2,7,30},"TRAIN_AGE_COVERAGE")
    stats,warnings=training_statistics(bundle["supervised"],schema)
    volume={}
    for part,start,end in [("TRAIN","2025-01","2026-03"),("VALIDATION","2026-04","2026-06")]:
        wholesale=[o for o in bundle["orders"] if start<=o["mes"]<=end and o["mode"]=="POR_MAYOR" and o["recorded_mode"]=="POR_MAYOR"]
        volume[part]={"orders":len(wholesale),"fully_fulfilled":sum(o["fulfilled_units"]==o["requested_units"] for o in wholesale),
            "partially_or_unfulfilled":sum(o["fulfilled_units"]<o["requested_units"] for o in wholesale),
            "fulfilled_at_least":{str(q):sum(o["fulfilled_units"]>=q for o in wholesale) for q in [20,40,80]}}
    check(all(volume["TRAIN"]["fulfilled_at_least"][str(q)]>0 for q in [20,40,80]),"WHOLESALE_COVERAGE_NOT_FULFILLED")
    check(volume["TRAIN"]["partially_or_unfulfilled"]>0,"CENSORING_CASES_MISSING")
    if any(w["code"]=="CONSTANT_OR_EMPTY_FEATURE" for w in warnings):failures.append("TRAIN_CONSTANT_FEATURE_REQUIRES_REVIEW")
    warnings.extend([
        {"code":"SYNTHETIC_ASSUMED_PROFILE_WEIGHTS","blocking":False,"reason":"No prevalencia real certificada ni precisión comercial."},
        {"code":"SHARED_SINGLE_ECONOMIC_TRAJECTORY","blocking":False,"reason":"Edades variables no crean múltiples economías independientes."},
        {"code":"KNOWN_ORDERS_NOT_FORECAST_FEATURES","blocking":False,"reason":"Capacidad para atender no demuestra capacidad para anticipar pedidos."},
        {"code":"STOCK_CENSORED_OBSERVED_SALES","blocking":False,"reason":"Target conserva unidades realmente atendidas, no demanda perdida."}])
    return dict(status="PASSED_EXPANDED_DATA_GATE" if not failures else "FAILED",failures=sorted(set(failures)),
        counts={name:len(rows) for name,rows in bundle.items()},train_quote_ages_days=sorted(ages),
        wholesale_volume=volume,statistics=stats,warnings=warnings,
        policy_scope="Physical and temporal evidence for ages and wholesale. Not all 57 dynamic scenarios or backend validation.",
        test_target_statistics_computed=False,training_performed=False,training_authorized=False,
        commercial_accuracy_certified=False)


INTEGER_FIELDS={"productId","locationId","requested_units","fulfilled_units","unmet_units","opening_stock","received_units","sold_units","closing_stock","zero_before_orders","observed","sent_units","pending_units","quantity","bootstrap","known_commitments","transit_opening","transit_closing","latent_units","observed_stock_days","zero_stock_days"}


def generic_table(path):
    with Path(path).open(encoding="utf-8",newline="") as f:
        rows=[]
        for raw in csv.DictReader(f):
            if None in raw or any(v is None for v in raw.values()):raise ValueError("CSV incompleto")
            row={}
            for name,value in raw.items():
                if name in INTEGER_FIELDS:
                    if not re.fullmatch(r"\d+",value):raise ValueError("Entero inválido "+name)
                    row[name]=int(value)
                elif name in ["value","unit_price_bs","position","required_units"]:
                    row[name]=int(value) if re.fullmatch(r"\d+",value) else float(value)
                    if not math.isfinite(row[name]):raise ValueError("No finito")
                else:row[name]=value
            rows.append(row)
    return rows


def inspect(path,root=ROOT,expected_manifest_sha256=None):
    from v2.generate_expanded import FILES,validate_schema
    root=Path(root).resolve();path=Path(path).resolve()
    if not path.is_relative_to(root/"data/repuestopro_v2/2.1.0"):raise ValueError("Ruta no es 2.1.0")
    manifest=strict_json((path/"manifest.json").read_text(encoding="utf-8"))
    if expected_manifest_sha256 and sha256_file(path/"manifest.json")!=expected_manifest_sha256:raise ValueError("Manifest no registrado")
    hashes={}
    for line in (path/"checksums.sha256").read_text(encoding="utf-8").splitlines():
        sha,name=line.split("  ",1)
        if Path(name).name!=name or name in hashes or not re.fullmatch("[0-9a-f]{64}",sha):raise ValueError("Checksum inválido")
        if sha256_file(path/name)!=sha:raise ValueError("Archivo alterado "+name)
        hashes[name]=sha
    if set(hashes)|{"checksums.sha256"}!={p.name for p in path.iterdir()}:raise ValueError("Inventario distinto")
    for relative,sha in manifest["component_hashes"].items():
        if not (root/relative).resolve().is_relative_to(root/"v2") or sha256_file(root/relative)!=sha:raise ValueError("Componente cambió")
        if sha256_file(path/("source_"+Path(relative).name))!=sha:raise ValueError("Copia de componente cambió")
    schema=strict_json((path/"schema.json").read_text(encoding="utf-8"));validate_schema(schema,root)
    config=strict_json((path/"generator_config.json").read_text(encoding="utf-8"))
    if config!=json.loads((root/"v2/contracts/expanded.v2_1.json").read_text(encoding="utf-8")):raise ValueError("Configuración distinta")
    if manifest["config_sha256"]!=sha256_file(root/"v2/contracts/expanded.v2_1.json"):raise ValueError("Hash config")
    catalog=strict_json((path/"catalog_reference.json").read_text(encoding="utf-8"))
    if manifest["catalog_reference_sha256"]!=sha256_file(root/"catalog_reference.json"):raise ValueError("Hash catálogo")
    if catalog!=strict_json((root/"catalog_reference.json").read_text(encoding="utf-8")):raise ValueError("Catálogo embebido distinto")
    bundle={}
    for name,filename in FILES.items():
        cols=schema["columns"] if name=="supervised" else schema["design"]["supporting_tables"][filename]["columns"] if name in ["base","audit"] else None
        bundle[name]=read_table(path/filename,cols) if cols else generic_table(path/filename)
    registry=strict_json((root/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))["scenario_design"]["scenarios"]
    result=validate_tables(bundle,schema,catalog,config,read_legacy(root),registry)
    split=strict_json((path/"split_manifest.json").read_text(encoding="utf-8"))
    split_errors=split_issues(bundle["supervised"],split)
    result["failures"]=sorted(set(result["failures"]+split_errors))
    if manifest["origin"]!="SYNTHETIC" or manifest["training_authorized"] is not False or manifest["split_design"]!=split:result["failures"].append("PROVENANCE_OR_SPLIT")
    result["status"]="PASSED_EXPANDED_DATA_GATE" if not result["failures"] else "FAILED"
    result["manifest_sha256"]=sha256_file(path/"manifest.json")
    result["test_hash_verified"]=split["sets"]["TEST"]["row_content_sha256"]
    return result


def read_legacy(root):return strict_json((Path(root)/"v2/contracts/calibration.v2.json").read_text(encoding="utf-8"))


def publish_review(build_id,run_id,root=ROOT,expected_manifest_sha256=None):
    root=Path(root).resolve();token(build_id);token(run_id)
    path=root/"data/repuestopro_v2/2.1.0"/build_id
    result=inspect(path,root,expected_manifest_sha256)
    destination=root/"reports/v2/2.1.0"/build_id/run_id
    if not destination.resolve().is_relative_to(root/"reports/v2"):raise ValueError("Destino inseguro")
    destination.mkdir(parents=True,exist_ok=False)
    for name,value in [("estadisticas.json",result.pop("statistics")),("calidad.json",result)]:
        with (destination/name).open("x",encoding="utf-8") as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    return destination,result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--build-id",required=True);parser.add_argument("--run-id",required=True)
    parser.add_argument("--expected-manifest-sha256",required=True)
    a=parser.parse_args();path,result=publish_review(a.build_id,a.run_id,expected_manifest_sha256=a.expected_manifest_sha256)
    print(json.dumps({"report":str(path),"status":result["status"],"failures":result["failures"]},ensure_ascii=True))
    sys.exit(bool(result["failures"]))
