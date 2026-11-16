"""Generador ampliado separado. Simulación en memoria, sin autorización de publicación.

Flujo físico derivado de generate_expanded.simulate 2.1.0. Se conserva el original.
Las modificaciones se limitan a mecanismos de referencia y trazabilidad.
"""
import json
import math
from datetime import timedelta
from pathlib import Path
from .structure import ROOT,sha256_file
from .generate_expanded import inputs as baseline_inputs
from .generate import month_start,stamp,partition,geometric
from .validate_build import canonical_hash,instant
from .experiment_preparation import quote_asof,supply_plan
from .retail_mechanisms import VERSION,Mechanisms,money,validate_prices


def inputs(root=ROOT):
    root=Path(root).resolve()
    recipe=json.loads((root/'v2/contracts/generator.retail_extension.v1.json').read_text(encoding='utf-8'))
    for relative,expected in recipe.get('implementation_sha256',{}).items():
        target=(root/relative).resolve()
        if not target.is_relative_to(root) or sha256_file(target)!=expected:raise ValueError('Implementación alterada')
    for path,key in [('baseline_generator_path','baseline_generator_sha256'),('calibration_path','calibration_sha256'),('schema_path','schema_sha256')]:
        target=(root/recipe[path]).resolve()
        if not target.is_relative_to(root) or sha256_file(target)!=recipe[key]:raise ValueError('Dependencia fijada alterada: '+path)
    for relative,expected in recipe.get('dependencies_sha256',{}).items():
        target=(root/relative).resolve()
        if not target.is_relative_to(root) or sha256_file(target)!=expected:raise ValueError('Dependencia compartida alterada')
    calibration=json.loads((root/recipe['calibration_path']).read_text(encoding='utf-8'))
    if calibration['base_calibration_sha256']!=sha256_file(root/'v2/contracts/calibration.v2.json'):raise ValueError('Calibración base alterada')
    if recipe['dataset_version'] is not None or recipe['publication_authorized'] or recipe['training_authorized']:raise ValueError('Esta etapa no autoriza build o entrenamiento')
    base=baseline_inputs(root)
    if canonical_hash(base[-1]['scenario_design'])!=recipe['scenario_design_canonical_sha256']:raise ValueError('Escenarios base alterados')
    return (*base,calibration,recipe)


def build(*args,**kwargs):
    raise PermissionError('BUILD_NOT_AUTHORIZED: generador preparado, sin permiso para crear un dataset.')


import random

def simulate(config,legacy,schema,catalog,preparation,calibration,recipe,*,months=24):
    if config["dataset_version"]!="2.1.0" or config["seed"]!=42:raise ValueError("Configuración no admitida")
    if not isinstance(months,int) or isinstance(months,bool) or not 1<=months<=24:raise ValueError("Horizonte inválido")
    profiles=config["profiles"]
    if any(not math.isfinite(p["weight"]) or p["weight"]<=0 for p in profiles) or not math.isclose(sum(p["weight"] for p in profiles),1):
        raise ValueError("Pesos de cobertura inválidos")
    if (not isinstance(config["lot_size"],int) or isinstance(config["lot_size"],bool) or config["lot_size"]<=0
        or not isinstance(config["safety_units"],int) or isinstance(config["safety_units"],bool) or config["safety_units"]<0):
        raise ValueError("Abastecimiento inválido")
    if len(config["quote_ages_days"])!=4 or any(not isinstance(a,int) or isinstance(a,bool) or a<0 for a in config["quote_ages_days"]):
        raise ValueError("Edades inválidas")
    def rng(stream,*keys):return random.Random(int(canonical_hash([VERSION,config["seed"],stream,*keys]),16))
    quote_events=[]
    for i in range(months+1):
        at=month_start(i);age=config["quote_ages_days"][i%4]
        observed=at-timedelta(days=age);published=observed+timedelta(days=min(age,1))
        quote_events.append(dict(quote_id="q-"+canonical_hash([VERSION,i])[:24],
            value=10*config["quote_value_factors"][i%8],unit=config["unit"],
            source_id=config["quote_source"],rate_kind=config["rate_kind"],
            observed_at=stamp(observed),available_at=stamp(published)))
    quotes=[quote_asof(quote_events,stamp(month_start(i)),config["quote_source"],config["rate_kind"]) for i in range(months+1)]
    if [q["age_days"] for q in quotes]!=[config["quote_ages_days"][i%4] for i in range(months+1)]:
        raise ValueError("La secuencia de publicaciones no produce las edades declaradas")
    products={p["id"]:p for p in catalog["products"]};ids=sorted(catalog["included_product_ids"])
    stores=sorted(s["id"] for s in catalog["locations"] if s["type"]=="TIENDA")
    if set(ids)&set(catalog["reserved_product_ids"]) or not set(ids)<=products.keys():raise ValueError("Selección inválida")
    cases={c["scenario_id"]:c for c in preparation["scenario_design"]["scenarios"]}
    bundle={name:[] for name in ["base","supervised","audit","ledger","daily","orders","shipments","receipts","plans"]}
    bundle["quotes"]=quote_events
    runtime=Mechanisms(calibration,recipe,stores)
    price_cache={}
    applied_bursts={}
    def prices(pid,sid,i):
        key=(pid,sid,i)
        if key in price_cache:return price_cache[key]
        role=rng("product-price",pid).randrange(2**32);scale=[.8,1,1.2][role%3]
        factor,events=runtime.price_state(pid,sid,month_start(i))
        prior=quotes[max(0,i-1)]["value"];current=quotes[i]["value"]
        inherited_cost_factor=1+.5*(prior/10-1)
        result=validate_prices(money(120*scale*inherited_cost_factor*factor),money(108*scale*inherited_cost_factor*factor),money(80*scale*current/10))
        price_cache[key]=result
        return result
    for pid in ids:
        for sid in stores:
            allocation=rng("assignment",pid,sid)
            profile=allocation.choices([p["name"] for p in profiles],weights=[p["weight"] for p in profiles])[0]
            group=allocation.choices(legacy["reference_statistics"]["monash"]["complete_series"]["rotation_groups"],
                weights=[legacy["simulation_recipe"]["rotation_weights"][g["label"]] for g in legacy["reference_statistics"]["monash"]["complete_series"]["rotation_groups"]])[0]
            stock=0;queue=[];history=[];shipment_index={}
            for i in range(months):
                start,end=month_start(i),month_start(i+1);month=start.strftime("%Y-%m");days=(end-start).days
                retail,wholesale,cost=prices(pid,sid,i)
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
                        runtime.volume_factor(sid,start.month))
                    baseline_quantity=geometric(r,mean)
                    q,burst_metadata=runtime.retail_quantity(baseline_quantity,pid,sid,i)
                    applied_bursts[(pid,sid,month)]=dict(baseline=baseline_quantity,requested=q,case=burst_metadata["case"])
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
                next_retail,next_wholesale,_=prices(pid,sid,i+1);q=quotes[i+1]
                row=dict(mes=month,productId=pid,locationId=sid,unidades_vendidas_brutas=sold,
                    unidades_por_menor=minor,unidades_por_mayor=major,unidades_modalidad_desconocida=unknown,
                    precio_menor_cierre_bs=retail,precio_mayor_cierre_bs=wholesale,
                    precio_menor_inicio_siguiente_conocido_bs=next_retail,precio_mayor_inicio_siguiente_conocido_bs=next_wholesale,
                    costo_unitario_bs=cost,tipo_cambio_bs_usd=q["value"],cotizacion_fuente_id=config["quote_source"],
                    cotizacion_observada_at=q["observed_at"],cotizacion_disponible_at=q["available_at"],
                    precios_disponibles_at=stamp(end-timedelta(seconds=1)),plan_precios_disponible_at=stamp(end),
                    dias_observados_stock=observed,dias_sin_stock_observados=zero_observed,ventas_disponibles_at=stamp(end),
                    stock_disponible_at=stamp(end),categoryId=products[pid]["categoryId"],quality_status="TRAINABLE")
                row["history_snapshot_id"]="synth-retail-extension-"+canonical_hash(row)[:24];bundle["base"].append(row)
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
                        reason="Instancia sintética de generador ampliado: "+case["name"],history_snapshot_id=row["history_snapshot_id"],
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
                        history_snapshot_id="history-retail-extension-"+canonical_hash([h["history_snapshot_id"] for h in history[-3:]])[:24],quality_status="TRAINABLE")
                    bundle["supervised"].append(supervised)
                history.append(row)
    for name,rows in bundle.items():
        if name=="quotes":continue
        month_key="date" if name=="daily" else "mes_objetivo" if name in ["supervised","audit"] else "mes" if name in ["base","ledger","plans","orders"] else "sent_at" if name=="shipments" else "received_at"
        rows.sort(key=lambda x:(x[month_key],x["productId"],x["locationId"],x.get("order_id",x.get("scenario_id",""))))
    audit=[];events=[]
    for pid in ids:
        for sid in stores:
            _,history_events=runtime.price_state(pid,sid,month_start(months))
            events.extend(history_events)
            for i in range(months):
                _,meta=runtime.retail_quantity(0,pid,sid,i)
                observed_burst=applied_bursts.get((pid,sid,month_start(i).strftime("%Y-%m")))
                audit.append(dict(productId=pid,locationId=sid,mes=month_start(i).strftime("%Y-%m"),feature_cutoff_at=stamp(month_start(i)),
                    audit_available_at=stamp(month_start(i+1)),minor_order_present=observed_burst is not None,
                    burst_applied=observed_burst is not None and meta["case"]!="NONE",
                    baseline_minor_requested_units=observed_burst["baseline"] if observed_burst else 0,
                    calibrated_minor_requested_units=observed_burst["requested"] if observed_burst else 0,
                    volume_factor=runtime.volume_factor(sid,month_start(i).month),store_factor=runtime.store_factors[sid],
                    seasonal_factor=runtime.seasonal_factor(month_start(i).month),burst_case=meta["case"],burst_multiplier=meta["multiplier"],
                    burst_mode="POR_MENOR",price_effect_on_demand=0,parameter_origin="REFERENCE_INFORMED_AND_EXPLICIT_ACADEMIC_MECHANISMS"))
    bundle["calibration_audit"]=audit;bundle["price_events"]=events
    return bundle

