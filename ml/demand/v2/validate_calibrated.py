"""Validación independiente 2.2.0. Sin ejecutar generador o entrenar.

Conserva verificaciones físicas 2.1 con adaptación explícita de snapshots.
El costo de un plan se comprueba en su propio corte, no con costo del mes previo.
"""
from collections import Counter,defaultdict
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
import json
import math
from .structure import ROOT
from .validate_build import canonical_hash,close,cutoff,instant,month_offset,strict_json,training_statistics,split_issues

def check_rows(base, rows, ledger, catalog):
    """Contrasta fuentes y fórmulas, no la función validate_generated de V2-06."""
    failures=[]
    def check(condition, code):
        if not condition:failures.append(code)
    ids=set(catalog["included_product_ids"])
    stores={s["id"] for s in catalog["locations"] if s["type"]=="TIENDA"}
    products={p["id"]:p for p in catalog["products"]}
    def key(r,m):return r["productId"],r["locationId"],r[m]
    index={key(r,"mes"):r for r in base}
    check(len(index)==len(base),"DUPLICATE_BASE")
    month0="2024-10"
    expected={(p,s,month_offset(month0,i)) for p in ids for s in stores for i in range(24)}
    check(set(index)==expected,"BASE_GRID_OR_ENTITY")
    target_index={key(r,"mes_objetivo"):r for r in rows}
    check(len(target_index)==len(rows),"DUPLICATE_SUPERVISED")
    check(set(target_index)=={(p,s,month_offset(month0,i)) for p in ids for s in stores for i in range(3,24)},"SUPERVISED_GRID_OR_ENTITY")
    led={key(r,"mes"):r for r in ledger}
    check(len(led)==len(ledger) and set(led)==set(index),"LEDGER_KEYS")
    fx_by_month={}
    for k,r in index.items():
        month=r["mes"];end=cutoff(month_offset(month,1));days=(end-cutoff(month)).days
        check(all(isinstance(r[n],int) and r[n]>=0 for n in ["unidades_vendidas_brutas","unidades_por_menor","unidades_por_mayor","unidades_modalidad_desconocida"]),"INVALID_UNITS")
        check(r["unidades_por_menor"]+r["unidades_por_mayor"]+r["unidades_modalidad_desconocida"]==r["unidades_vendidas_brutas"],"MODALITY_TOTAL")
        check(0<=r["dias_sin_stock_observados"]<=r["dias_observados_stock"]<=days,"STOCK_CALENDAR")
        check(0<r["costo_unitario_bs"]<=r["precio_mayor_cierre_bs"]<=r["precio_menor_cierre_bs"],"PRICE_ORDER")
        for major,minor in [(r["precio_mayor_inicio_siguiente_conocido_bs"],r["precio_menor_inicio_siguiente_conocido_bs"])]:
            check((major is None)==(minor is None),"PARTIAL_PRICE_PLAN")
            if major is not None:check(0<major<=minor,"PRICE_PLAN_ORDER")
        check(r["categoryId"]==products.get(r["productId"],{}).get("categoryId"),"CATEGORY_CHANGED")
        check(r["quality_status"]=="TRAINABLE","BASE_QUALITY")
        check(instant(r["ventas_disponibles_at"])==end,"MONTH_NOT_CLOSED")
        for field in ["precios_disponibles_at","plan_precios_disponible_at","stock_disponible_at"]:
            if r[field] is not None:check(instant(r[field])<=end,"FUTURE_SOURCE")
        check(instant(r["cotizacion_observada_at"])<=instant(r["cotizacion_disponible_at"])<=end,"FX_AVAILABILITY")
        fx=(r["tipo_cambio_bs_usd"],r["cotizacion_fuente_id"],r["cotizacion_observada_at"],r["cotizacion_disponible_at"])
        check(fx_by_month.get(month,fx)==fx,"FX_NOT_COMMON")
        fx_by_month[month]=fx
        body={n:v for n,v in r.items() if n!="history_snapshot_id"}
        check(r["history_snapshot_id"]=="synth-retail-v2_2-"+canonical_hash(body)[:24],"BASE_SNAPSHOT_HASH")
        if k in led:
            q=led[k]
            check(all(isinstance(q[n],int) and q[n]>=0 for n in q if n not in ["mes","productId","locationId"]),"LEDGER_NEGATIVE_OR_FRACTIONAL")
            check(q["sold_units"]==r["unidades_vendidas_brutas"] and q["sold_units"]<=q["latent_units"],"LEDGER_SALES")
            check(q["opening_stock"]+q["received_units"]-q["sold_units"]==q["closing_stock"],"STOCK_CONSERVATION")
            check(q["transit_opening"]+q["sent_units"]-q["received_units"]==q["transit_closing"],"TRANSIT_CONSERVATION")
            prev=led.get((k[0],k[1],month_offset(month,-1)))
            if prev:check(q["opening_stock"]==prev["closing_stock"] and q["transit_opening"]==prev["transit_closing"],"LEDGER_CONTINUITY")
            check(q["observed_stock_days"]==r["dias_observados_stock"] and r["dias_sin_stock_observados"]<=q["zero_stock_days"]<=days,"OBSERVED_STOCK_VS_LEDGER")
    for k,r in target_index.items():
        history=[index.get((k[0],k[1],month_offset(k[2],-lag))) for lag in (1,2,3)]
        if any(x is None for x in history):
            failures.append("MISSING_LAG");continue
        last,prior,_=history
        at=cutoff(k[2]);check(instant(r["feature_cutoff_at"])==at,"CUTOFF_LOCAL_MONTH")
        for n,h in zip(["ventas_mes_anterior","ventas_hace_2_meses","ventas_hace_3_meses"],history):
            check(r[n]==h["unidades_vendidas_brutas"] and instant(h["ventas_disponibles_at"])<=at,"LAG_OR_CLOCK")
        current=index.get(k)
        check(current is not None and r["target_ventas_mes"]==current["unidades_vendidas_brutas"],"TARGET")
        units=last["unidades_vendidas_brutas"]
        check(close(r["proporcion_por_mayor_mes_anterior"],last["unidades_por_mayor"]/units if units else None),"WHOLESALE_RATIO")
        check(close(r["cobertura_modalidad_mes_anterior"],(units-last["unidades_modalidad_desconocida"])/units if units else None),"MODALITY_COVERAGE")
        for prefix in ["menor","mayor"]:
            price=last[f"precio_{prefix}_cierre_bs"];plan=last[f"precio_{prefix}_inicio_siguiente_conocido_bs"]
            check(close(r[f"precio_{prefix}_cierre_anterior_bs"],price),"HISTORICAL_PRICE")
            check(close(r[f"variacion_precio_{prefix}_conocida"],None if plan is None else plan/price-1),"PRICE_CHANGE")
        check(close(r["tipo_cambio_bs_usd_conocido"],last["tipo_cambio_bs_usd"]),"KNOWN_FX")
        check(close(r["variacion_tipo_cambio_ultimo_mes"],last["tipo_cambio_bs_usd"]/prior["tipo_cambio_bs_usd"]-1),"FX_CHANGE")
        check(r["antiguedad_tipo_cambio_dias"]==(at-instant(last["cotizacion_observada_at"])).days,"FX_AGE")
        days=(cutoff(k[2])-cutoff(month_offset(k[2],-1))).days
        check(close(r["cobertura_stock_mes_anterior"],last["dias_observados_stock"]/days),"STOCK_COVERAGE")
        check(r["dias_sin_stock_mes_anterior"]==(last["dias_sin_stock_observados"] if last["dias_observados_stock"] else None),"UNKNOWN_STOCK_NOT_ZERO")
        check(r["categoryId"]==last["categoryId"] and r["quality_status"]=="TRAINABLE","ROW_QUALITY")
        month=int(k[2][-2:])
        check(close(r["mes_sin"],math.sin(2*math.pi*month/12)) and close(r["mes_cos"],math.cos(2*math.pi*month/12)),"CALENDAR_FEATURES")
        check(r["history_snapshot_id"]=="history-retail-v2_2-"+canonical_hash([x["history_snapshot_id"] for x in reversed(history)])[:24],"HISTORY_SNAPSHOT")
    return sorted(set(failures))


def physical_checks(bundle,schema,catalog,config,legacy,case_registry=None):
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


def rounded(value):return float(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def validate_tables(bundle,schema,catalog,config,legacy,recipe,calibration,registry):
    report=physical_checks(bundle,schema,catalog,config,legacy,registry)
    failures=report['failures'];audit={};base={(r['productId'],r['locationId'],r['mes']):r for r in bundle['base']}
    def check(test,code):
        if not test:failures.append(code)
    pairs={(p,s) for p,s,_ in base};quotes=bundle['quotes']
    for row in bundle['pricing_audit']:
        key=(row['productId'],row['locationId'],row['mes']);check(key not in audit,'PRICING_AUDIT_DUPLICATE');audit[key]=row
        at=cutoff(row['mes']);check(instant(row['available_at'])==at,'PRICING_AVAILABLE_CLOCK')
        check(row['cost_changed_by_review'] is False,'COST_CHANGED_BY_REVIEW')
        check(row['scale'] in [.8,1,1.2],'INITIAL_PRICE_SCALE')
        observed=[q for q in quotes if instant(q['available_at'])<=at]
        chosen=max(observed,key=lambda x:(instant(x['observed_at']),instant(x['available_at'])))
        expected_cost=rounded(80*row['scale']*chosen['value']/10)
        check(close(row['cost_bs'],expected_cost),'COST_FORMULA')
        needs=not 0<row['cost_bs']<=row['proposed_major_bs']<=row['proposed_minor_bs']
        check(row['administrative_review']==needs,'ADMIN_REVIEW_FLAG')
        if needs:
            check(row['reason']=='SIMULATED_ADMIN_REVIEW_COST_RULE','ADMIN_REASON')
            check(close(row['retail_bs'],rounded(row['cost_bs']*recipe['economic_review']['retail_cost_multiplier'])) and close(row['wholesale_bs'],rounded(row['cost_bs']*recipe['economic_review']['wholesale_cost_multiplier'])),'ADMIN_PRICE_FORMULA')
        else:
            check(row['reason']=='REFERENCE_INFORMED_MONTHLY_PROPOSAL','PRICE_REASON')
            check(close(row['retail_bs'],row['proposed_minor_bs']) and close(row['wholesale_bs'],row['proposed_major_bs']),'SILENT_PRICE_CORRECTION')
        check(0<row['cost_bs']<=row['wholesale_bs']<=row['retail_bs'],'PRICE_AUDIT_ECONOMICS')
    expected={(p,s,month_offset('2024-10',i)) for p,s in pairs for i in range(25)}
    check(set(audit)==expected,'PRICING_AUDIT_GRID')
    for key,row in audit.items():
        prev=audit.get((*key[:2],month_offset(key[2],-1)))
        if prev:
            ratio=row['reference_index']/prev['reference_index']*row['fx_factor']/prev['fx_factor']
            minor=rounded(prev['retail_bs']*ratio);major=rounded(prev['wholesale_bs']*ratio)
        else:minor=rounded(120*row['scale']);major=rounded(108*row['scale'])
        check(close(row['proposed_minor_bs'],minor) and close(row['proposed_major_bs'],major),'PRICE_PROPOSAL_FORMULA')
    seen=set();event_index=defaultdict(list)
    magnitude=calibration['parameters']['conditional_absolute_price_change']['value']
    for e in bundle['price_events']:
        key=(e['productId'],e['locationId'],e['week_start']);check(key not in seen,'DUPLICATE_WEEKLY_EVENT');seen.add(key)
        start=instant(e['week_start']);available=instant(e['available_at'])
        check(start.weekday()==0 and (start.hour,start.minute,start.second)==(0,0,0),'WEEK_CLOCK')
        check(available==start+timedelta(days=7),'WEEK_PRICE_AVAILABLE')
        check(close(abs(e['relative_change']),magnitude) and e['relative_change']>-1,'WEEK_PRICE_MAGNITUDE')
        check((key[0],key[1]) in pairs,'WEEK_EVENT_ORPHAN')
        event_index[key[:2]].append(e)
    for key,row in audit.items():
        at=cutoff(key[2]);factor=math.prod(1+e['relative_change'] for e in event_index[key[:2]] if instant(e['available_at'])<=at)
        check(close(factor,row['reference_index']),'PRICE_INDEX_ASOF')
        prior_month=month_offset(key[2],-1) if key[2]>'2024-10' else key[2]
        q=max([q for q in quotes if instant(q['available_at'])<=cutoff(prior_month)],key=lambda q:(instant(q['observed_at']),instant(q['available_at'])))
        check(close(row['fx_factor'],1+.5*(q['value']/10-1)),'PRICE_FX_FACTOR')
    for key,row in base.items():
        current=audit[key];nxt=audit[(*key[:2],month_offset(key[2],1))]
        check(close(row['precio_menor_cierre_bs'],current['retail_bs']) and close(row['precio_mayor_cierre_bs'],current['wholesale_bs']) and close(row['costo_unitario_bs'],current['cost_bs']),'BASE_PRICE_AUDIT')
        check(close(row['precio_menor_inicio_siguiente_conocido_bs'],nxt['retail_bs']) and close(row['precio_mayor_inicio_siguiente_conocido_bs'],nxt['wholesale_bs']),'PLAN_PRICE_AUDIT')
    controls={};burst_counts=Counter()
    for a in bundle['calibration_audit']:
        key=(a['productId'],a['locationId'],a['mes']);check(key not in controls,'CALIBRATION_DUPLICATE');controls[key]=a
        check(instant(a['audit_available_at'])==cutoff(month_offset(a['mes'],1)),'BURST_AUDIT_CLOCK')
        check(a['volume_factor']>0 and a['store_factor']>0 and a['seasonal_factor']>0,'POSITIVE_VOLUME_FACTORS')
        check(a['price_effect_on_demand']==0 and a['burst_mode']=='POR_MENOR','INVENTED_ELASTICITY_OR_MODE')
        minor=[o for o in bundle['orders'] if o['productId']==key[0] and o['locationId']==key[1] and o['mes']==key[2] and o['mode']=='POR_MENOR']
        check(a['minor_order_present']==bool(minor),'BURST_ORDER_PRESENCE')
        check(sum(o['requested_units'] for o in minor)==a['calibrated_minor_requested_units'],'BURST_REQUESTED_COUNT')
        check(a['calibrated_minor_requested_units']==math.ceil(a['baseline_minor_requested_units']*a['burst_multiplier']),'BURST_MULTIPLIER')
        if a['burst_applied'] and a['mes']<='2026-06':burst_counts[a['burst_case']]+=1
    check(set(controls)==set(base),'CALIBRATION_AUDIT_GRID')
    check(burst_counts['P95']>0 and burst_counts['P99']>0,'BURST_COVERAGE')
    report['failures']=sorted(set(failures));report['status']='PASSED_CALIBRATED_2_2_GATE' if not report['failures'] else 'FAILED'
    report['administrative_price_reviews']=sum(x['administrative_review'] for x in audit.values())
    report['weekly_price_proposals']=len(bundle['price_events'])
    report['applied_minor_bursts_train_validation']=dict(burst_counts)
    report['dataset_version']='2.2.0';report['old_test_repeated']=False
    return report
