"""Simulación 2.1.0 aislada: cotizaciones fechadas, pedidos y recepción física.

No modifica 2.0.0, no usa datos operativos y no entrena modelos.
"""
from __future__ import annotations
import argparse
import copy
import csv
from datetime import datetime,timedelta,timezone
import json
import math
from pathlib import Path
import random
import shutil
import sys

if __package__ in (None,""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jsonschema import Draft202012Validator
from v2.structure import ROOT,new_build_directory,sha256_file,token
from v2.generate import month_start,stamp,partition,geometric,write_csv
from v2.validate_build import canonical_hash,instant
from v2.experiment_preparation import quote_asof,supply_plan

VERSION="expanded-generator-2.1.0"


def read(root,name):return json.loads((Path(root)/name).read_text(encoding="utf-8"))


def validate_schema(document,root=ROOT):
    Draft202012Validator(read(root,"v2/contracts/dataset_schema.v2_1.schema.json")).validate(document)
    approved=read(root,"v2/contracts/dataset_columns.v2.json")
    if document["columns"]!=approved["columns"]:raise ValueError("Cambió la definición aprobada de las 17 features")
    for name,table in approved["design"]["supporting_tables"].items():
        if document["design"]["supporting_tables"][name]["columns"]!=table["columns"]:
            raise ValueError("Columnas auxiliares no aprobadas")


def inputs(root=ROOT):
    config=read(root,"v2/contracts/expanded.v2_1.json")
    legacy=read(root,"v2/contracts/calibration.v2.json")
    if config["legacy_config_sha256"]!=sha256_file(Path(root)/"v2/contracts/calibration.v2.json"):
        raise ValueError("Referencia de calibración cambiada")
    schema=read(root,"v2/contracts/dataset_columns.v2_1.json");validate_schema(schema,root)
    return config,legacy,schema,read(root,"catalog_reference.json"),read(root,"v2/contracts/preparation.v2.json")


def simulate(config,legacy,schema,catalog,preparation):
    if config["dataset_version"]!="2.1.0" or config["seed"]!=42:raise ValueError("Configuración no admitida")
    profiles=config["profiles"]
    if any(not math.isfinite(p["weight"]) or p["weight"]<=0 for p in profiles) or not math.isclose(sum(p["weight"] for p in profiles),1):
        raise ValueError("Pesos de cobertura inválidos")
    if (not isinstance(config["lot_size"],int) or isinstance(config["lot_size"],bool) or config["lot_size"]<=0
        or not isinstance(config["safety_units"],int) or isinstance(config["safety_units"],bool) or config["safety_units"]<0):
        raise ValueError("Abastecimiento inválido")
    if len(config["quote_ages_days"])!=4 or any(not isinstance(a,int) or isinstance(a,bool) or a<0 for a in config["quote_ages_days"]):
        raise ValueError("Edades inválidas")
    salt=canonical_hash(config)
    def rng(stream,*keys):return random.Random(int(canonical_hash([VERSION,config["seed"],salt,stream,*keys]),16))
    quote_events=[]
    for i in range(25):
        at=month_start(i);age=config["quote_ages_days"][i%4]
        observed=at-timedelta(days=age);published=observed+timedelta(days=min(age,1))
        quote_events.append(dict(quote_id="q-"+canonical_hash([VERSION,i])[:24],
            value=10*config["quote_value_factors"][i%8],unit=config["unit"],
            source_id=config["quote_source"],rate_kind=config["rate_kind"],
            observed_at=stamp(observed),available_at=stamp(published)))
    quotes=[quote_asof(quote_events,stamp(month_start(i)),config["quote_source"],config["rate_kind"]) for i in range(25)]
    if [q["age_days"] for q in quotes]!=[config["quote_ages_days"][i%4] for i in range(25)]:
        raise ValueError("La secuencia de publicaciones no produce las edades declaradas")
    products={p["id"]:p for p in catalog["products"]};ids=sorted(catalog["included_product_ids"])
    stores=sorted(s["id"] for s in catalog["locations"] if s["type"]=="TIENDA")
    if set(ids)&set(catalog["reserved_product_ids"]) or not set(ids)<=products.keys():raise ValueError("Selección inválida")
    cases={c["scenario_id"]:c for c in preparation["scenario_design"]["scenarios"]}
    bundle={name:[] for name in ["base","supervised","audit","ledger","daily","orders","shipments","receipts","plans"]}
    bundle["quotes"]=quote_events
    def prices(pid,i):
        role=rng("product-price",pid).randrange(2**32);scale=[.8,1,1.2][role%3]
        shock=1.25 if role%5==0 and i>=6 else .9 if role%7==0 and i>=12 else 1
        prior=quotes[max(0,i-1)]["value"];current=quotes[i]["value"]
        factor=1+.5*(prior/10-1)
        retail,wholesale,cost=round(120*scale*factor*shock,2),round(108*scale*factor*shock,2),round(80*scale*current/10,2)
        if not 0<cost<=wholesale<=retail:raise ValueError("Precio simulado viola margen. No se corrige silenciosamente.")
        return retail,wholesale,cost
    for pid in ids:
        for sid in stores:
            allocation=rng("assignment",pid,sid)
            profile=allocation.choices([p["name"] for p in profiles],weights=[p["weight"] for p in profiles])[0]
            group=allocation.choices(legacy["reference_statistics"]["monash"]["complete_series"]["rotation_groups"],
                weights=[legacy["simulation_recipe"]["rotation_weights"][g["label"]] for g in legacy["reference_statistics"]["monash"]["complete_series"]["rotation_groups"]])[0]
            stock=0;queue=[];history=[];shipment_index={}
            for i in range(24):
                start,end=month_start(i),month_start(i+1);month=start.strftime("%Y-%m");days=(end-start).days
                retail,wholesale,cost=prices(pid,i)
                r=rng("orders",pid,sid,partition(i),month)
                orders=[]
                bulk=(profile in ["RECURRENT_WHOLESALE","MIXED","PARTIAL_LATE"] or
                      profile in ["EXCEPTIONAL_KNOWN","UNEXPECTED"] and r.random()<.35)
                if bulk:
                    q=r.choice(config["wholesale_sizes"])
                    orders.append(dict(mode="POR_MAYOR",requested_units=q,
                        known_at=stamp(start+timedelta(days=7)) if profile=="UNEXPECTED" else stamp(start-timedelta(days=2)),
                        due_at=stamp(start+timedelta(days=config["wholesale_due_day"]-1))))
                probability=group["occurrence_probability"]
                if profile=="MEDIUM":probability=max(probability,.475)
                if profile=="MIXED":probability=1
                if r.random()<probability:
                    scale=3 if profile in ["MEDIUM","MIXED"] else 1
                    mean=max(1,legacy["reference_statistics"]["monash"]["all_observed"]["positive_mean"]*scale*
                        (1+.1*math.sin(2*math.pi*start.month/12))*(retail/prices(pid,0)[0])**-.5)
                    q=geometric(r,mean)
                    day=r.randint(12,days)
                    orders.append(dict(mode="POR_MENOR",requested_units=q,
                        known_at=stamp(start+timedelta(days=day-1)),due_at=stamp(start+timedelta(days=day-1))))
                for n,o in enumerate(orders):
                    o.update(order_id="o-"+canonical_hash([VERSION,pid,sid,month,n])[:24],productId=pid,locationId=sid,
                        mes=month,profile=profile,unit_price_bs=wholesale if o["mode"]=="POR_MAYOR" else retail,
                        recorded_mode="UNKNOWN" if o["mode"]=="POR_MENOR" and rng("observation-mode",pid,sid,month,n).random()<.15 else o["mode"])
                known=[dict(id=o["order_id"],units=o["requested_units"],known_at=o["known_at"],due_at=o["due_at"])
                       for o in orders if instant(o["known_at"])<=start]
                incoming=[dict(id=key,pending_units=sum(q["quantity"] for q in queue if q["shipment_id"]==key),
                    status="IN_TRANSIT",known_at=shipment_index[key]["sent_at"],expected_at=shipment_index[key]["expected_at"])
                    for key in sorted({q["shipment_id"] for q in queue})]
                opening=stock;transit_open=sum(q["quantity"] for q in queue)
                if len(history)>=3:
                    plan=supply_plan(at=stamp(start),sellable=stock,reserved=0,
                        history_units=[h["unidades_vendidas_brutas"] for h in history[-3:]],firm_orders=known,incoming=incoming,
                        safety_units=config["safety_units"],lot_size=config["lot_size"])
                    bootstrap=0
                else:
                    # No se fabrican meses previos con cero. Compra inicial por compromiso conocido.
                    committed=sum(o["units"] for o in known);deadline=min([instant(o["due_at"]) for o in known]+[end])
                    inbound=sum(x["pending_units"] for x in incoming if start<=instant(x["expected_at"])<end and instant(x["expected_at"])<=deadline)
                    need=max(0,committed+config["safety_units"]-stock-inbound)
                    plan=dict(order_units=math.ceil(need/config["lot_size"])*config["lot_size"],known_commitments=committed,
                        position=stock+inbound,required_units=committed+config["safety_units"])
                    bootstrap=1
                sent=plan["order_units"]
                bundle["plans"].append(dict(productId=pid,locationId=sid,mes=month,planned_at=stamp(start),
                    known_order_ids=json.dumps([o["id"] for o in known],separators=(",",":")),
                    history_months=json.dumps([h["mes"] for h in history[-3:]],separators=(",",":")),
                    history_units=json.dumps([h["unidades_vendidas_brutas"] for h in history[-3:]],separators=(",",":")),
                    opening_stock=stock,bootstrap=bootstrap,known_commitments=plan["known_commitments"],
                    position=plan["position"],required_units=plan["required_units"],sent_units=sent))
                if sent:
                    shipment_id="s-"+canonical_hash([VERSION,pid,sid,month])[:24]
                    expected=start+timedelta(days=config["timely_receipt_day"]-1)
                    shipment=dict(shipment_id=shipment_id,productId=pid,locationId=sid,sent_at=stamp(start),
                        expected_at=stamp(expected),sent_units=sent,received_units=0,pending_units=sent,profile=profile)
                    bundle["shipments"].append(shipment);shipment_index[shipment_id]=shipment
                    if profile=="PARTIAL_LATE" and i%2==0:
                        first=int(sent*config["partial_fraction"])
                        arrivals=[(expected,first),(end+timedelta(days=config["remainder_receipt_next_month_day"]-1),sent-first)]
                    elif profile=="PARTIAL_LATE":
                        arrivals=[(start+timedelta(days=config["late_receipt_day"]-1),sent)]
                    else:arrivals=[(expected,sent)]
                    for piece,(at,quantity) in enumerate(arrivals):
                        if quantity:queue.append(dict(shipment_id=shipment_id,piece=piece,at=at,quantity=quantity))
                sensor=rng("stock-observation",pid,sid,month).random()
                observed=days if sensor<.85 else days//2 if sensor<.93 else 0
                received=sold=latent=zero_actual=zero_observed=0;minor=major=unknown=0
                for day in range(days):
                    at=start+timedelta(days=day);day_open=stock;day_received=day_sold=0
                    arrivals=[q for q in queue if q["at"]<=at]
                    for item in arrivals:
                        stock+=item["quantity"];received+=item["quantity"];day_received+=item["quantity"]
                        shipment=shipment_index[item["shipment_id"]]
                        shipment["received_units"]+=item["quantity"];shipment["pending_units"]-=item["quantity"]
                        bundle["receipts"].append(dict(receipt_id=item["shipment_id"]+"-"+str(item["piece"]),
                            shipment_id=item["shipment_id"],productId=pid,locationId=sid,received_at=stamp(at),quantity=item["quantity"]))
                    queue=[q for q in queue if q["at"]>at]
                    zero=int(stock==0);zero_actual+=zero
                    if day<observed:zero_observed+=zero
                    for order in sorted([o for o in orders if instant(o["due_at"])==at],key=lambda x:(x["mode"]!="POR_MAYOR",x["order_id"])):
                        fulfil=min(stock,order["requested_units"]);stock-=fulfil;sold+=fulfil;day_sold+=fulfil;latent+=order["requested_units"]
                        order.update(fulfilled_units=fulfil,unmet_units=order["requested_units"]-fulfil)
                        if order["recorded_mode"]=="POR_MENOR":minor+=fulfil
                        elif order["recorded_mode"]=="POR_MAYOR":major+=fulfil
                        else:unknown+=fulfil
                        bundle["orders"].append(order)
                    bundle["daily"].append(dict(productId=pid,locationId=sid,date=at.strftime("%Y-%m-%d"),
                        opening_stock=day_open,received_units=day_received,sold_units=day_sold,closing_stock=stock,
                        zero_before_orders=zero,observed=int(day<observed)))
                next_retail,next_wholesale,_=prices(pid,i+1);q=quotes[i+1]
                row=dict(mes=month,productId=pid,locationId=sid,unidades_vendidas_brutas=sold,
                    unidades_por_menor=minor,unidades_por_mayor=major,unidades_modalidad_desconocida=unknown,
                    precio_menor_cierre_bs=retail,precio_mayor_cierre_bs=wholesale,
                    precio_menor_inicio_siguiente_conocido_bs=next_retail,precio_mayor_inicio_siguiente_conocido_bs=next_wholesale,
                    costo_unitario_bs=cost,tipo_cambio_bs_usd=q["value"],cotizacion_fuente_id=config["quote_source"],
                    cotizacion_observada_at=q["observed_at"],cotizacion_disponible_at=q["available_at"],
                    precios_disponibles_at=stamp(end-timedelta(seconds=1)),plan_precios_disponible_at=stamp(end),
                    dias_observados_stock=observed,dias_sin_stock_observados=zero_observed,ventas_disponibles_at=stamp(end),
                    stock_disponible_at=stamp(end),categoryId=products[pid]["categoryId"],quality_status="TRAINABLE")
                row["history_snapshot_id"]="synth-v2-"+canonical_hash(row)[:24];bundle["base"].append(row)
                bundle["ledger"].append(dict(mes=month,productId=pid,locationId=sid,opening_stock=opening,
                    received_units=received,sold_units=sold,closing_stock=stock,transit_opening=transit_open,
                    sent_units=sent,transit_closing=sum(x["quantity"] for x in queue),latent_units=latent,
                    observed_stock_days=observed,zero_stock_days=zero_actual))
                observed_cases={"N01"} if minor else {"N04"} if sold==0 and zero_actual==0 else set()
                if major:observed_cases.add("N02" if profile in ["RECURRENT_WHOLESALE","MIXED","PARTIAL_LATE"] else "A10")
                if minor and major:observed_cases.add("N03")
                if q["age_days"]>=7:observed_cases.add("G07")
                if unknown:observed_cases.add("G05")
                if zero_actual:observed_cases.add("A07" if zero_actual==days else "A06")
                if observed<days and sold==0:observed_cases.add("G06")
                if profile=="PARTIAL_LATE" and sent:observed_cases.add("A08")
                if i==0:observed_cases.add("G18")
                for case_id in sorted(observed_cases):
                    case=cases[case_id]
                    bundle["audit"].append(dict(scenario_id=case_id,productId=pid,locationId=sid,mes_objetivo=month,
                        case_class=case["case_class"],issue_code=case["issue_code"],expected_action=case["expected_action"],
                        reason="Instancia sintética 2.1.0: "+case["name"],history_snapshot_id=row["history_snapshot_id"],
                        latent_demand_units=latent,scenario_instance_id=canonical_hash([row["history_snapshot_id"],case_id])[:32],
                        event_at=q["observed_at"] if case_id=="G07" else stamp(end),
                        available_at=q["available_at"] if case_id=="G07" else stamp(end),
                        parameters_json=json.dumps(dict(profile=profile,event_kind="QUOTE" if case_id=="G07" else "MONTHLY_SUMMARY",scope="SYNTHETIC_INSTANCE_NOT_VALIDATED_SCENARIO_TEST"),sort_keys=True,separators=(",",":"))))
                if i>=3:
                    last,prior=history[-1],history[-2];total=last["unidades_vendidas_brutas"]
                    supervised=dict(mes_objetivo=month,productId=pid,locationId=sid,ventas_mes_anterior=total,
                        ventas_hace_2_meses=history[-2]["unidades_vendidas_brutas"],ventas_hace_3_meses=history[-3]["unidades_vendidas_brutas"],
                        mes_sin=math.sin(2*math.pi*start.month/12),mes_cos=math.cos(2*math.pi*start.month/12),
                        proporcion_por_mayor_mes_anterior=last["unidades_por_mayor"]/total if total else None,
                        cobertura_modalidad_mes_anterior=(total-last["unidades_modalidad_desconocida"])/total if total else None,
                        precio_menor_cierre_anterior_bs=last["precio_menor_cierre_bs"],precio_mayor_cierre_anterior_bs=last["precio_mayor_cierre_bs"],
                        variacion_precio_menor_conocida=last["precio_menor_inicio_siguiente_conocido_bs"]/last["precio_menor_cierre_bs"]-1,
                        variacion_precio_mayor_conocida=last["precio_mayor_inicio_siguiente_conocido_bs"]/last["precio_mayor_cierre_bs"]-1,
                        tipo_cambio_bs_usd_conocido=last["tipo_cambio_bs_usd"],
                        variacion_tipo_cambio_ultimo_mes=last["tipo_cambio_bs_usd"]/prior["tipo_cambio_bs_usd"]-1,
                        antiguedad_tipo_cambio_dias=(start-instant(last["cotizacion_observada_at"])).days,
                        dias_sin_stock_mes_anterior=last["dias_sin_stock_observados"] if last["dias_observados_stock"] else None,
                        cobertura_stock_mes_anterior=last["dias_observados_stock"]/(start-month_start(i-1)).days,
                        categoryId=row["categoryId"],target_ventas_mes=sold,feature_cutoff_at=stamp(start),
                        history_snapshot_id="history-v2-"+canonical_hash([h["history_snapshot_id"] for h in history[-3:]])[:24],quality_status="TRAINABLE")
                    bundle["supervised"].append(supervised)
                history.append(row)
    for name,rows in bundle.items():
        if name=="quotes":continue
        month_key="date" if name=="daily" else "mes_objetivo" if name in ["supervised","audit"] else "mes" if name in ["base","ledger","plans","orders"] else "sent_at" if name=="shipments" else "received_at"
        rows.sort(key=lambda x:(x[month_key],x["productId"],x["locationId"],x.get("order_id",x.get("scenario_id",""))))
    return bundle


FILES={"base":"base_mensual.csv","supervised":"dataset_supervisado.csv","audit":"escenarios_metadatos.csv",
       "ledger":"simulation_ledger.csv","daily":"daily_stock.csv","quotes":"quote_events.csv","orders":"orders.csv",
       "shipments":"shipments.csv","receipts":"receipts.csv","plans":"supply_plans.csv"}


def build(build_id,root=ROOT):
    root=Path(root).resolve();token(build_id)
    destination=root/"data/repuestopro_v2/2.1.0"/build_id
    if destination.exists():raise FileExistsError("Build existente. No se sobrescribe.")
    staging=root/"tmp"/token("expanded-"+build_id)
    if not staging.resolve().is_relative_to(root/"tmp"):raise ValueError("Temporal inseguro")
    staging.mkdir(parents=True,exist_ok=False)
    config,legacy,schema,catalog,prep=inputs(root);bundle=simulate(config,legacy,schema,catalog,prep)
    from v2.validate_expanded import validate_tables
    quality=validate_tables(bundle,schema,catalog,config,legacy,prep["scenario_design"]["scenarios"])
    if quality["failures"]:raise ValueError("No publicar: "+str(quality["failures"]))
    for name,filename in FILES.items():
        rows=bundle[name]
        columns=([c["name"] for c in schema["columns"]] if name=="supervised" else
                 [c["name"] for c in schema["design"]["supporting_tables"][filename]["columns"]] if name in ["base","audit"] else list(rows[0]))
        write_csv(staging/filename,rows,columns)
    split=dict(origin="SYNTHETIC",root_seed=42,new_v2_streams=True,random_split=False,training_authorized=False,
        test_access_status="GENERATED_AND_INTEGRITY_CHECKED_NOT_USED_FOR_SELECTION",sets={})
    for name,start,end in [("TRAIN","2025-01","2026-03"),("VALIDATION","2026-04","2026-06"),("TEST","2026-07","2026-09")]:
        selected=[r for r in bundle["supervised"] if start<=r["mes_objetivo"]<=end]
        split["sets"][name]=dict(start=start,end=end,rows=len(selected),row_content_sha256=canonical_hash(selected))
    published_schema=copy.deepcopy(schema);published_schema["design"]["definition_status"]="BUILD_GENERATED_PENDING_EXHAUSTIVE_V2_07"
    published_schema["design"]["publication"]["build_created"]=True
    published_schema["design"]["split_design"]["test_hash"]=split["sets"]["TEST"]["row_content_sha256"]
    published_schema["design"]["split_design"]["test_status"]=split["test_access_status"]
    published_schema["design"]["future_work"]=["Experimentos solo tras autorización","Revisión de backend y artefacto seleccionado con Erika"]
    validate_schema(published_schema,root)
    components=["v2/generate_expanded.py","v2/validate_expanded.py","v2/experiment_preparation.py","v2/generate.py","v2/validate_build.py","v2/structure.py"]
    manifest=dict(dataset_version="2.1.0",build_id=build_id,origin="SYNTHETIC",dataset_name="DATOS_SINTETICOS_DEMANDA_H4_V2_EXPANDED",
        status="EXPANDED_BUILD_VALIDATED_DATA_ONLY_NOT_TRAINING_AUTHORIZED",root_seed=42,generator_version=VERSION,
        generator_sha256=sha256_file(Path(__file__)),component_hashes={p:sha256_file(root/p) for p in components},
        config_id=config["config_version"],config_sha256=sha256_file(root/"v2/contracts/expanded.v2_1.json"),
        catalog_reference_sha256=sha256_file(root/"catalog_reference.json"),catalog_observed_at=catalog["observed_at"],
        selected_product_ids=catalog["included_product_ids"],selected_store_ids=[s["id"] for s in catalog["locations"] if s["type"]=="TIENDA"],
        reference_source_ids=[x["source_id"] for x in legacy["input_evidence"]],
        reference_snapshot_ids={x["source_id"]:x["snapshot_id"] for x in legacy["input_evidence"]},
        reference_raw_sha256={x["source_id"]:x["raw_sha256"] for x in legacy["input_evidence"]},
        reference_citations=legacy["input_evidence"],
        source_columns_sha256=sha256_file(root/"v2/contracts/dataset_columns.v2.json"),
        compatibility_report_sha256=sha256_file(root/"reports/v2/compatibility/compatibility-20261114-01/source_compatibility_matrix.json"),
        processing_versions_if_any=[],assumptions=config["assumptions"],feature_sets=schema["design"]["feature_sets"],
        created_at=stamp(datetime.now(timezone.utc)),split_design=split,test_access_status=split["test_access_status"],
        environment_versions={"python":sys.version.split()[0]},training_authorized=False,
        coverage_meaning="Eventos físicos y cotizaciones auditables. No certifica los 57 escenarios dinámicos o precisión comercial.")
    required=schema["design"]["publication"]["manifest_required"]
    if not set(required)<=manifest.keys():raise ValueError("Manifest incompleto")
    for name,data in {"manifest.json":manifest,"schema.json":published_schema,"split_manifest.json":split,
        "validation.json":quality,"generator_config.json":config,"catalog_reference.json":catalog}.items():
        with (staging/name).open("x",encoding="utf-8",newline="\n") as f:json.dump(data,f,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False);f.write("\n")
    for relative in components:
        shutil.copyfile(root/relative,staging/("source_"+Path(relative).name))
    hashes={p.name:sha256_file(p) for p in staging.iterdir() if p.is_file()}
    with (staging/"checksums.sha256").open("x",encoding="utf-8",newline="\n") as f:
        f.write("".join(f"{value}  {name}\n" for name,value in sorted(hashes.items())))
    target=new_build_directory("2.1.0",build_id,root=root)
    for p in sorted(staging.iterdir(),key=lambda x:(x.name=="manifest.json",x.name)):
        with p.open("rb") as src,(target/p.name).open("xb") as dst:shutil.copyfileobj(src,dst)
    if any(sha256_file(target/name)!=value for name,value in hashes.items()):raise ValueError("Publicación incompleta")
    return target,quality


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--build-id",required=True);args=p.parse_args()
    path,result=build(args.build_id)
    print(json.dumps({"path":str(path),"status":result["status"],"counts":result["counts"]},ensure_ascii=True))
