"""Política offline de aceptación de fixtures. No sustituye backend o modelo.

Los casos se identifican solo en los fixtures. assess() decide según hechos,
no recibe scenario_id ni expected_action y no cambia ventas históricas.
"""
import copy
from datetime import timedelta
import math

from v2.validate_build import cutoff, instant, month_offset


def base_facts():
    at=cutoff("2026-02")
    return dict(purpose="SUPERVISED_ROW", origin="SYNTHETIC", productId=1, locationId=5,
        month="2026-02", history=[{"month":month_offset("2026-02",-i),"units":q}
                                  for i,q in [(3,3),(2,5),(1,8)]],
        month_closed=True, target_units=8, label_at=cutoff("2026-03").isoformat(),
        prices={"retail":120,"wholesale":108,"cost":80,"origin":"SIMULATED_HISTORICAL_LIST"},
        plan={"retail":120,"wholesale":108,"available_at":at.isoformat()},
        fx={"value":10,"previous":10,"unit":"Bs/USD","source":"SYNTHETIC", "observed_at":at.isoformat(),"available_at":at.isoformat()},
        previous_modes={"retail":5,"wholesale":3,"unknown":0},
        stock_history={"observed_days":31,"zero_days":0},categoryId=2,train_categories=[2,3],
        inventory={"opening":20,"received":0,"sold":8,"closing":12,"transit_opening":0,"sent":0,"transit_closing":0},
        transactions=[{"quantity":8,"void_available_at":None}],
        feature_inputs={}, feature_available_at={}, panel_keys=[[1,5,"2026-02"]],
        transform_fit_partitions=["TRAIN"], model_selection_partitions=["VALIDATION"],
        split_month_assignments={"2026-01":["TRAIN"],"2026-02":["VALIDATION"]}, test_origin="NEW_V2_STREAM")


def assess(facts, products=tuple(range(1,57)), stores=(5,6,7)):
    f=copy.deepcopy(facts);errors=[];review=[];optional=[];context=[]
    # Ningún identificador de escenario participa en esta función.
    forbidden={"target_ventas_mes","total_mes_objetivo","stock_posterior","scenario_id","seed","latent_demand_units","plazo_proveedor","productId","locationId","mes_objetivo"}
    approved={"ventas_mes_anterior","ventas_hace_2_meses","ventas_hace_3_meses","mes_sin","mes_cos",
        "proporcion_por_mayor_mes_anterior","cobertura_modalidad_mes_anterior","precio_menor_cierre_anterior_bs",
        "precio_mayor_cierre_anterior_bs","variacion_precio_menor_conocida","variacion_precio_mayor_conocida",
        "tipo_cambio_bs_usd_conocido","variacion_tipo_cambio_ultimo_mes","antiguedad_tipo_cambio_dias",
        "dias_sin_stock_mes_anterior","cobertura_stock_mes_anterior","categoryId"}
    if set(f["feature_inputs"]) & forbidden or not set(f["feature_inputs"])<=approved:errors.append("FORBIDDEN_FEATURE")
    if f["origin"]!="SYNTHETIC":errors.append("ORIGIN_MIX")
    if f["productId"] not in products or f["locationId"] not in stores:errors.append("ENTITY")
    keys=[tuple(k) for k in f["panel_keys"]]
    if len(keys)!=len(set(keys)):errors.append("DUPLICATE_KEY")
    at=cutoff(f["month"])
    for value in f["feature_available_at"].values():
        try:
            if instant(value)>at:errors.append("FUTURE_FEATURE")
        except ValueError:errors.append("FEATURE_CLOCK")
    if f.get("sale_event_at"):
        try:
            event=instant(f["sale_event_at"])
            if event.astimezone(at.tzinfo).strftime("%Y-%m")!=f["sale_event_month"]:errors.append("LOCAL_MONTH")
        except ValueError:
            (errors if f.get("month_claim_certified",False) else review).append("UNKNOWN_TIMEZONE")
    if set(f["transform_fit_partitions"])!={"TRAIN"} or "TEST" in f["model_selection_partitions"]:
        errors.append("PARTITION_LEAKAGE")
    if any(len(set(v))!=1 for v in f["split_month_assignments"].values()) or f["test_origin"]!="NEW_V2_STREAM":errors.append("SPLIT_LEAKAGE")
    history={h["month"]:h["units"] for h in f["history"]}
    required=[month_offset(f["month"],-i) for i in (1,2,3)]
    if len(history)!=len(f["history"]) or any(m not in history for m in required):review.append("CORE_HISTORY_MISSING")
    if not f["month_closed"] and f["purpose"]=="SUPERVISED_ROW":review.append("OPEN_TARGET")
    if f.get("line_identity")=="UNRESOLVED_REPEATS":review.append("LEGACY_LINE_IDENTITY")
    valid_units=lambda x:isinstance(x,int) and not isinstance(x,bool) and x>=0
    if any(not valid_units(q) for q in history.values()):errors.append("HISTORY_UNITS")
    if f["purpose"]!="INFERENCE" and not valid_units(f["target_units"]):errors.append("TARGET_UNITS")
    prices=f["prices"]
    numeric=lambda x:isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
    if not all(numeric(prices[k]) and prices[k]>0 for k in ("cost","retail","wholesale")):
        errors.append("INVALID_PRICE")
    elif not prices["cost"]<=prices["wholesale"]<=prices["retail"]:errors.append("PRICE_ORDER")
    stock=f["inventory"]
    if not all(valid_units(q) for q in stock.values()) or stock["opening"]+stock["received"]-stock["sold"]!=stock["closing"] or stock["transit_opening"]+stock["sent"]-stock["received"]!=stock["transit_closing"]:
        errors.append("STOCK_ACCOUNTING")
    if f["purpose"]!="INFERENCE" and stock["sold"]!=f["target_units"]:errors.append("STOCK_SALES")
    valid_target=0
    for transaction in f["transactions"]:
        if not valid_units(transaction["quantity"]) or transaction["quantity"]==0:errors.append("TRANSACTION_UNITS");continue
        when=transaction["void_available_at"]
        if when and instant(when)>instant(f["label_at"]):review.append("LATE_VOID_REQUIRES_NEW_BUILD")
        if when is None or instant(when)>instant(f["label_at"]):valid_target+=transaction["quantity"]
    if f["purpose"]!="INFERENCE" and valid_target!=f["target_units"]:errors.append("GROSS_SALES_LABEL")
    features={"ventas_mes_anterior":history.get(required[0]),"ventas_hace_2_meses":history.get(required[1]),"ventas_hace_3_meses":history.get(required[2]),
              "mes_sin":math.sin(2*math.pi*at.month/12),"mes_cos":math.cos(2*math.pi*at.month/12)}
    total=history.get(required[0]);m=f["previous_modes"]
    if not all(valid_units(q) for q in m.values()) or total is not None and sum(m.values())!=total:errors.append("MODALITY_TOTAL")
    features["proporcion_por_mayor_mes_anterior"]=m["wholesale"]/total if total else None
    features["cobertura_modalidad_mes_anterior"]=(m["retail"]+m["wholesale"])/total if total else None
    if m["unknown"]:optional.append("UNKNOWN_MODALITY")
    historical=prices["origin"]=="SIMULATED_HISTORICAL_LIST"
    if not historical:optional.append("NO_HISTORICAL_LIST")
    plan=f["plan"]
    plan_known=plan is not None and instant(plan["available_at"])<=at and historical
    if plan_known and not all(numeric(plan[k]) and plan[k]>0 for k in ("retail","wholesale")):
        errors.append("INVALID_PLAN_PRICE");plan_known=False
    if plan is not None and not plan_known:optional.append("PLAN_NOT_KNOWN")
    for mode,key in [("menor","retail"),("mayor","wholesale")]:
        features[f"precio_{mode}_cierre_anterior_bs"]=prices[key] if historical else None
        features[f"variacion_precio_{mode}_conocida"]=plan[key]/prices[key]-1 if plan_known and prices[key]>0 else None
    if plan_known and not prices["cost"]<=plan["wholesale"]<=plan["retail"]:errors.append("PLAN_ORDER")
    fx=f["fx"]
    if fx["unit"] not in (None,"Bs/USD"):errors.append("FX_UNIT")
    fx_known=fx["value"] is not None and fx["source"] is not None and fx["unit"]=="Bs/USD" and fx["available_at"] is not None and fx["observed_at"] is not None
    if fx_known:
        if not numeric(fx["value"]) or fx["value"]<=0:errors.append("FX_VALUE");fx_known=False
        elif not instant(fx["observed_at"])<=instant(fx["available_at"])<=at:errors.append("FX_FUTURE");fx_known=False
    features["tipo_cambio_bs_usd_conocido"]=fx["value"] if fx_known else None
    features["antiguedad_tipo_cambio_dias"]=(at-instant(fx["observed_at"])).days if fx_known else None
    previous_ok=numeric(fx["previous"]) and fx["previous"]>0
    features["variacion_tipo_cambio_ultimo_mes"]=fx["value"]/fx["previous"]-1 if fx_known and previous_ok else None
    if not fx_known or not previous_ok:optional.append("FX_UNDEMONSTRATED")
    if fx_known and features["antiguedad_tipo_cambio_dias"]>0:optional.append("FX_AGE_NOTICE_NOT_REJECTION_THRESHOLD")
    prev_days=(at-cutoff(required[0])).days;observed=f["stock_history"]["observed_days"];zero=f["stock_history"]["zero_days"]
    if not valid_units(observed) or not valid_units(zero) or not 0<=zero<=observed<=prev_days:errors.append("OBSERVATION_CALENDAR")
    features["cobertura_stock_mes_anterior"]=observed/prev_days
    features["dias_sin_stock_mes_anterior"]=zero if observed else None
    if observed<prev_days:optional.append("INCOMPLETE_STOCK_OBSERVATION")
    features["categoryId"]=f["categoryId"]
    category_route="KNOWN" if f["categoryId"] in f["train_categories"] else "UNKNOWN"
    if category_route=="UNKNOWN":optional.append("CATEGORY_UNKNOWN")
    if f.get("catalog_assumption")=="FROZEN_REFERENCE_IN_SYNTHETIC_PAST":optional.append("SYNTHETIC_REFERENCE_NOT_REAL_HISTORY")
    refund=None
    if "refund" in f:
        r=f["refund"]
        if any(not numeric(r[k]) or r[k]<0 for k in ("amount","debt","paid")) or r["amount"]>r["debt"]+r["paid"]:errors.append("REFUND_AMOUNT")
        else:
            reduced=min(r["amount"],r["debt"])
            refund={"debt_reduction":reduced,"cash_refund":r["amount"]-reduced,"sellable_return_units":r["units"] if r["inspected"] else 0}
    if f.get("purpose")=="REPLENISHMENT":
        if f.get("supplier_actual_arrival") is None:context.append("NO_ACTUAL_SUPPLIER_LEAD_TIME")
        if f.get("discontinued_certified") is None and f.get("check_discontinued"):context.append("DISCONTINUATION_NOT_CERTIFIED")
    if f.get("planned_closure") and not f.get("closure_feature_approved"):context.append("NO_OPERATIONAL_CALENDAR_FEATURE")
    if f.get("external_source") not in (None,"monash_car_parts","uci_online_retail_ii"):context.append("SOURCE_NOT_APPROVED")
    if "prediction" in f:
        p=f["prediction"]
        if not numeric(p) or p<0:errors.append("INVALID_PREDICTION_POLICY")
    for name,value in f["feature_inputs"].items():
        if name in approved and value!=features.get(name):errors.append("FEATURE_VALUE_NOT_SUPPORTED_BY_HISTORY")
    core="REJECT" if errors else "REVIEW" if review else "KEEP_WITH_NULL" if optional else "KEEP"
    action="REJECT" if errors else "REVIEW" if review or context else "KEEP_WITH_NULL" if optional else "KEEP"
    return dict(action=action,core_row_action=core,features=features,category_route=category_route,
                errors=errors,review=review,optional=optional,context=context,refund=refund,
                target_units=f["target_units"],scenario_id_used_for_decision=False)


def set_target(f,quantity,opening=None,received=0,transit=0):
    f["target_units"]=quantity;f["transactions"]=[] if quantity==0 else [{"quantity":quantity,"void_available_at":None}]
    opening=quantity+10 if opening is None else opening
    f["inventory"]=dict(opening=opening,received=received,sold=quantity,closing=opening+received-quantity,
                        transit_opening=0,sent=received+transit,transit_closing=transit)


def apply_scenario(f,id_):
    """Hechos del fixture aprobados, nunca reglas de decisión por ID."""
    if id_=="N01":f["previous_modes"]={"retail":8,"wholesale":0,"unknown":0}
    elif id_=="N02":f["previous_modes"]={"retail":0,"wholesale":8,"unknown":0}
    elif id_=="N03":f["previous_modes"]={"retail":4,"wholesale":4,"unknown":0}
    elif id_=="N04":
        for h,q in zip(f["history"],[0,0,1]):h["units"]=q
        f["previous_modes"]={"retail":1,"wholesale":0,"unknown":0};set_target(f,0)
    elif id_=="N05":set_target(f,20)
    elif id_=="N06":
        for h,q in zip(f["history"],[2,4,6]):h["units"]=q
        f["previous_modes"]={"retail":4,"wholesale":2,"unknown":0}
    elif id_=="N07":f["seasonality_context"]={"amplitudes":[.1,.2],"phases":[0,1.7]}
    elif id_=="N08":f["locationId"]=6
    elif id_=="N09":f["plan"].update(retail=150,wholesale=135)
    elif id_=="N10":f["plan"].update(retail=108,wholesale=97.2)
    elif id_=="N11":f["fx"].update(value=10,previous=10)
    elif id_=="N12":set_target(f,8,opening=0,received=20)
    elif id_=="A01":f["unannounced_price_event"]={"retail":150,"available_at":"2026-02-05T00:00:00-04:00"};f["plan"]=None
    elif id_=="A02":f["fx"].update(value=13,previous=10)
    elif id_=="A03":f["fx"].update(value=8.5,previous=10)
    elif id_=="A04":f["prices"]["wholesale"]=150
    elif id_=="A05":f["fx"]["value"]=0
    elif id_=="A06":f["stock_history"]["zero_days"]=7;set_target(f,2,opening=3)
    elif id_=="A07":set_target(f,0,opening=0);f["latent_requests_context"]=10
    elif id_=="A08":set_target(f,5,opening=0,received=5,transit=5)
    elif id_=="A09":f.update(purpose="REPLENISHMENT",supplier_expected_days=60,supplier_actual_arrival=None)
    elif id_=="A10":set_target(f,40,opening=50);f["bulk_request_context"]=40
    elif id_=="A11":set_target(f,20);f["regime_context"]=1.5
    elif id_=="A12":set_target(f,0);f["unannounced_interruption_days"]=14
    elif id_=="A13":f["panel_keys"].append(f["panel_keys"][0][:])
    elif id_=="A14":f["target_units"]=-1
    elif id_=="A15":f["locationId"]=99999
    elif id_=="A16":f["feature_inputs"]["target_ventas_mes"]=8;f["feature_available_at"]["precio_menor_cierre_anterior_bs"]="2026-03-01T00:00:00-04:00"
    elif id_=="A17":f["origin"]="EXTERNAL_ROWS_RENAMED_AS_REPUESTOPRO"
    elif id_=="A18":f.update(sale_event_at="2026-03-01T02:00:00+00:00",sale_event_month="2026-03",month_claim_certified=True)
    elif id_=="A19":apply_scenario(f,"N09");apply_scenario(f,"A02");apply_scenario(f,"A06")
    elif id_=="A20":f["transform_fit_partitions"]=["TRAIN","TEST"]
    elif id_=="A21":f["refund"]={"amount":100,"debt":70,"paid":130,"units":2,"inspected":False}
    elif id_=="A22":f["transactions"][0]["void_available_at"]="2026-03-02T00:00:00-04:00"
    elif id_=="A23":set_target(f,20);f["promotion_without_price_change"]=True
    elif id_=="A24":f["transactions"].append({"quantity":4,"void_available_at":"2026-02-20T00:00:00-04:00"})
    elif id_=="A25":f["prediction"]=-1
    elif id_ in ("G01","G02"):f["history"]=f["history"][1:];f["activation_context"]="2026-01-15"
    elif id_=="G03":f["history"].pop(1)
    elif id_=="G04":f["month_closed"]=False
    elif id_=="G05":f["previous_modes"]={"retail":2,"wholesale":2,"unknown":4}
    elif id_=="G06":
        f["history"][-1]["units"]=0;f["previous_modes"]={"retail":0,"wholesale":0,"unknown":0}
        f["stock_history"]={"observed_days":0,"zero_days":0};set_target(f,0)
    elif id_=="G07":f["fx"]["observed_at"]="2026-01-01T00:00:00-04:00"
    elif id_=="G08":f["fx"].update(value=None,source=None,unit=None)
    elif id_=="G09":f["plan"]["available_at"]="2026-02-02T00:00:00-04:00"
    elif id_=="G10":f["prices"]["origin"]="CURRENT_PRODUCT_ONLY"
    elif id_=="G11":f["categoryId"]=None
    elif id_=="G12":f["line_identity"]="UNRESOLVED_REPEATS"
    elif id_=="G13":f.update(sale_event_at="2026-02-01T01:00:00",sale_event_month=None,month_claim_certified=False)
    elif id_=="G14":f["prices"]["wholesale"]=120;f["previous_modes"]={"retail":0,"wholesale":0,"unknown":8}
    elif id_=="G15":apply_scenario(f,"N09");set_target(f,15)
    elif id_=="G16":f["external_source"]="m5_walmart"
    elif id_=="G17":f.update(purpose="REPLENISHMENT",supplier_expected_at="2026-02-15",supplier_actual_arrival=None)
    elif id_=="G18":f["catalog_assumption"]="FROZEN_REFERENCE_IN_SYNTHETIC_PAST"
    elif id_=="G19":f.update(purpose="REPLENISHMENT",check_discontinued=True,discontinued_certified=None)
    elif id_=="G20":f.update(planned_closure=True,closure_feature_approved=False)
    else:raise ValueError("Fixture no definido")
    return f


def scenario_suite(design):
    results=[]
    for case in design["scenarios"]:
        facts=apply_scenario(base_facts(),case["scenario_id"])
        actual=assess(facts)
        results.append(dict(id=case["scenario_id"],expected=case["expected_action"],actual=actual,
            passed=actual["action"]==case["expected_action"],facts=facts,kind="OFFLINE_POLICY_FIXTURE_NOT_GENERATOR_OR_BACKEND_ACCEPTANCE"))
    for combo in design["mandatory_combinations"]:
        facts=base_facts()
        for member in combo["members"]:apply_scenario(facts,member)
        actual=assess(facts)
        results.append(dict(id=combo["id"],expected=combo["expected_action"],actual=actual,
            passed=actual["action"]==combo["expected_action"],facts=facts,kind="COMBINED_OFFLINE_POLICY_FIXTURE"))
    return results
