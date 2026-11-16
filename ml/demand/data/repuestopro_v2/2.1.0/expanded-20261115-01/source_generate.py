"""Build académico V2 aislado. No entrena, importa V1 ni accede a bases de datos.

Desde la raíz: python -m v2.generate (con ml/demand en PYTHONPATH), o utilizar
python ml/demand/v2/generate.py --build-id IDENTIFICADOR_NUEVO.
"""
from __future__ import annotations

import argparse
import calendar
import copy
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import shutil
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v2.structure import ROOT, new_build_directory, sha256_file, token, validate_contract

VERSION = "v2-generator-2.0.0"
LEDGER_COLUMNS = ["mes", "productId", "locationId", "opening_stock", "received_units",
                  "sold_units", "closing_stock", "transit_opening", "sent_units",
                  "transit_closing", "latent_units", "observed_stock_days", "zero_stock_days"]


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def rng(seed, stream, *keys):
    return random.Random(int(digest([VERSION, seed, stream, *keys]), 16))


def month_start(index):
    number = 2024 * 12 + 9 + index
    return datetime(number // 12, number % 12 + 1, 1, tzinfo=timezone(timedelta(hours=-4)))


def stamp(value):
    return value.isoformat(timespec="seconds")


def partition(index):
    return "HISTORY" if index < 3 else "TRAIN" if index < 18 else "VALIDATION" if index < 21 else "TEST"


def geometric(r, mean):
    if mean <= 1:
        return 1
    return 1 + int(math.log1p(-r.random()) / math.log1p(-1 / mean))


def load_inputs(root=ROOT):
    root = Path(root)
    def read(name):
        return json.loads((root/name).read_text(encoding="utf-8"))
    config = read("v2/contracts/calibration.v2.json")
    preparation = read("v2/contracts/preparation.v2.json")
    schema = read("v2/contracts/dataset_columns.v2.json")
    catalog = read("catalog_reference.json")
    validate_contract(schema, "dataset_schema")
    if preparation["calibration"]["sha256"] != sha256_file(root/"v2/contracts/calibration.v2.json"):
        raise ValueError("La configuración no coincide con el contrato aprobado")
    if config["implementation_sha256"] != sha256_file(root/"v2/calibration.py"):
        raise ValueError("Cambió el cálculo de calibración")
    for e in config["input_evidence"]:
        # Los perfiles son evidencia congelada. Nunca abrir RAW ni tablas externas.
        path = root / Path(e["profile_path"]).relative_to("ml/demand")
        if sha256_file(path) != e["profile_sha256"]:
            raise ValueError("Cambió un perfil de referencia")
    if config["seed"] != 42 or schema["design"]["dataset_version"] != "2.0.0":
        raise ValueError("Configuración no soportada por este generador")
    return config, preparation, schema, catalog


def simulate(config, preparation, schema, catalog):
    """Genera solo memoria. Un stream por mecanismo, clave y partición temporal."""
    seed = config["seed"]
    products = {p["id"]: p for p in catalog["products"]}
    ids = sorted(catalog["included_product_ids"])
    stores = sorted(x["id"] for x in catalog["locations"] if x["type"] == "TIENDA")
    if len(ids) != len(set(ids)) or not ids or not stores or not set(ids) <= products.keys():
        raise ValueError("Catálogo inconsistente")
    if set(ids) & set(catalog["reserved_product_ids"]):
        raise ValueError("No incluir productos reservados")
    recipe = config["simulation_recipe"]
    groups = config["reference_statistics"]["monash"]["complete_series"]["rotation_groups"]
    cases = {c["scenario_id"]: c for c in preparation["scenario_design"]["scenarios"]}
    base, supervised, audit, ledger = [], [], [], []
    # FX común y prepublicado: un único valor por corte. Valores ficticios Bs/USD.
    fx_base = recipe["fx_base_bs_per_usd"]
    fx = [fx_base * x for x in [1, 1, 1.15, 1.15, 1, 1, .85, .85]] * 4
    def product_role(pid):
        return rng(seed, "product-policy", pid).randrange(2**32)
    def price(pid, index):
        role = product_role(pid)
        scale = [0.8, 1, 1.2][role % 3]
        shock = 1.25 if role % 5 == 0 and index >= 6 else 0.9 if role % 7 == 0 and index >= 12 else 1
        factor = 1 + .5 * (fx[max(index-1, 0)] / fx_base - 1)
        return (round(recipe["price_base_retail_bs"]*scale*factor*shock, 2),
                round(recipe["price_base_wholesale_bs"]*scale*factor*shock, 2),
                round(recipe["cost_base_bs"]*scale*fx[index]/fx_base, 2))
    for pid in ids:
        for sid in stores:
            role = product_role(pid)
            supply_role = rng(seed, "supply-policy", pid, sid).randrange(2**32)
            a = rng(seed, "assignment", pid, sid)
            group = a.choices(groups, weights=[g["weight"] for g in groups])[0]
            trend = a.choice([-.1, 0, .2])
            amplitude, phase = a.choice([0, .1, .2]), a.uniform(0, 2*math.pi)
            elasticity = a.choice(recipe["price_elasticity_sensitivity"])
            share = a.choice(recipe["wholesale_unit_share_sensitivity"])
            store_factor = rng(seed, "store", sid).choice([.75, 1, 1.25])
            stock = 0
            shipments = []
            history = []
            for i in range(24):
                start, end = month_start(i), month_start(i+1)
                month = start.strftime("%Y-%m")
                days = calendar.monthrange(start.year, start.month)[1]
                r = rng(seed, "counts", pid, sid, partition(i), month)
                sr = rng(seed, "stock", pid, sid, partition(i), month)
                current_retail, current_wholesale, cost = price(pid, i)
                previous_retail, previous_wholesale, _ = price(pid, max(i-1, 0))
                announced = not (role % 11 == 0 and i % 6 == 0)
                event_day = 1 if announced else 5
                opening, transit_opening = stock, sum(q for _, q in shipments)
                received, sent, sales, latent = 0, 0, 0, 0
                # No suministro en meses seleccionados: existe tránsito, no stock mágico.
                if stock <= 3:
                    sent = 6
                    delay = 60 if supply_role % 19 == 0 else sr.choice([0, 7, 30])
                    shipments.append((start + timedelta(days=delay), sent))
                observed_days = days if not (role % 13 == 0 and i % 5 == 0) else (days//2 if i % 2 else 0)
                zero_observed = zero_actual = 0
                order_day = r.randint(1, days)
                occurs = r.random() < group["occurrence_probability"]
                bulk = role % 17 == 0 and i in (9, 17)
                mode = True if bulk else rng(seed, "mode", pid, sid, partition(i), month).random() < share
                units = 0
                if occurs or bulk:
                    pr = current_wholesale if mode else current_retail
                    if order_day < event_day:
                        pr = previous_wholesale if mode else previous_retail
                    initial_retail, initial_wholesale, _ = price(pid, 0)
                    price_ratio = pr / (initial_wholesale if mode else initial_retail)
                    mean = config["reference_statistics"]["monash"]["all_observed"]["positive_mean"]
                    mean *= (1+trend)**(i/12) * store_factor
                    mean *= 1+amplitude*math.sin(2*math.pi*start.month/12+phase)
                    mean *= price_ratio**elasticity
                    units = geometric(r, max(1, mean)) * (4 if bulk else 1)
                for day in range(1, days+1):
                    now = start+timedelta(days=day-1)
                    arrivals = [(at,q) for at,q in shipments if at <= now]
                    incoming = sum(q for _,q in arrivals)
                    received += incoming
                    stock += incoming
                    shipments = [(at,q) for at,q in shipments if at > now]
                    # Disponibilidad antes de pedidos, independiente del target.
                    if stock == 0:
                        zero_actual += 1
                        if day <= observed_days:
                            zero_observed += 1
                    if day == order_day:
                        latent += units
                        fulfilled = min(units, stock)
                        sales += fulfilled
                        stock -= fulfilled
                # Descomposición por modalidad explícita, incluyendo desconocidos opcionales.
                unknown = sales//2 if role % 23 == 0 else 0
                known = sales-unknown
                wholesale = known if mode else 0
                retail = known-wholesale
                next_retail, next_wholesale, _ = price(pid, i+1)
                plan_known = not (role % 11 == 0 and (i+1) % 6 == 0)
                snapshot = "synth-v2-"+digest([VERSION, seed, pid, sid, month])[:24]
                row = dict(mes=month, productId=pid, locationId=sid,
                    unidades_vendidas_brutas=sales, unidades_por_menor=retail,
                    unidades_por_mayor=wholesale, unidades_modalidad_desconocida=unknown,
                    precio_menor_cierre_bs=current_retail, precio_mayor_cierre_bs=current_wholesale,
                    precio_menor_inicio_siguiente_conocido_bs=next_retail if plan_known else None,
                    precio_mayor_inicio_siguiente_conocido_bs=next_wholesale if plan_known else None,
                    costo_unitario_bs=cost, tipo_cambio_bs_usd=fx[i+1],
                    cotizacion_fuente_id="SYNTHETIC_FX_NOT_MARKET_RATE",
                    cotizacion_observada_at=stamp(end-timedelta(days=2)),
                    cotizacion_disponible_at=stamp(end-timedelta(days=1)),
                    precios_disponibles_at=stamp(end-timedelta(seconds=1)),
                    plan_precios_disponible_at=stamp(end-timedelta(seconds=1)) if plan_known else None,
                    dias_observados_stock=observed_days, dias_sin_stock_observados=zero_observed,
                    ventas_disponibles_at=stamp(end), stock_disponible_at=stamp(end),
                    categoryId=products[pid]["categoryId"], history_snapshot_id=snapshot, quality_status="TRAINABLE")
                row["history_snapshot_id"] = "synth-v2-"+digest({k:v for k,v in row.items() if k != "history_snapshot_id"})[:24]
                snapshot = row["history_snapshot_id"]
                base.append(row)
                ledger.append(dict(mes=month, productId=pid, locationId=sid, opening_stock=opening,
                    received_units=received, sold_units=sales, closing_stock=stock,
                    transit_opening=transit_opening, sent_units=sent,
                    transit_closing=sum(q for _,q in shipments), latent_units=latent,
                    observed_stock_days=observed_days, zero_stock_days=zero_actual))
                scenarios = ["G18"] if i == 0 else []
                if sales == 0:
                    scenarios.append("N04" if zero_actual == 0 else "A07" if zero_actual == days else "A06")
                else:
                    scenarios.append("N02" if wholesale else "N01")
                    if zero_actual:
                        scenarios.append("A06")
                if not announced and (current_retail != previous_retail or current_wholesale != previous_wholesale):
                    scenarios.append("A01")
                if bulk and wholesale > 0:
                    scenarios.append("A10")
                if observed_days < days and sales == 0:
                    scenarios.append("G06")
                if unknown:
                    scenarios.append("G05")
                if sent and not received:
                    scenarios.append("A08")
                for scenario_id in scenarios:
                    case = cases[scenario_id]
                    audit.append(dict(scenario_id=scenario_id, productId=pid, locationId=sid,
                        mes_objetivo=month, case_class=case["case_class"], issue_code=case["issue_code"],
                        expected_action=case["expected_action"], reason="Instancia de simulación. "+case["name"],
                        history_snapshot_id=snapshot, latent_demand_units=latent,
                        scenario_instance_id=digest([snapshot,scenario_id])[:32],
                        event_at=stamp(start+timedelta(days=(event_day-1 if scenario_id == "A01" else 0))),
                        available_at=stamp(start+timedelta(days=event_day-1)) if scenario_id == "A01" else stamp(end),
                        parameters_json=encoded(dict(generator=VERSION, group=group["label"],
                            occurrence_probability=group["occurrence_probability"], trend=trend,
                            amplitude=amplitude, phase=phase, store_factor=store_factor, elasticity=elasticity,
                            modality_share=share, actual_zero_days=zero_actual,
                            observation_days=observed_days, scope="SYNTHETIC_INSTANCE_NOT_VALIDATED_SCENARIO_TEST")).decode().strip()))
                if i >= 3:
                    prev = history[-1]
                    total = prev["unidades_vendidas_brutas"]
                    prev_fx = prev["tipo_cambio_bs_usd"]
                    prev_prev_fx = history[-2]["tipo_cambio_bs_usd"]
                    def variation(planned, last):
                        return None if planned is None else planned/last-1
                    supervised.append(dict(mes_objetivo=month, productId=pid, locationId=sid,
                        ventas_mes_anterior=total,
                        ventas_hace_2_meses=history[-2]["unidades_vendidas_brutas"],
                        ventas_hace_3_meses=history[-3]["unidades_vendidas_brutas"],
                        mes_sin=math.sin(2*math.pi*start.month/12), mes_cos=math.cos(2*math.pi*start.month/12),
                        proporcion_por_mayor_mes_anterior=prev["unidades_por_mayor"]/total if total else None,
                        cobertura_modalidad_mes_anterior=(total-prev["unidades_modalidad_desconocida"])/total if total else None,
                        precio_menor_cierre_anterior_bs=prev["precio_menor_cierre_bs"],
                        precio_mayor_cierre_anterior_bs=prev["precio_mayor_cierre_bs"],
                        variacion_precio_menor_conocida=variation(prev["precio_menor_inicio_siguiente_conocido_bs"],prev["precio_menor_cierre_bs"]),
                        variacion_precio_mayor_conocida=variation(prev["precio_mayor_inicio_siguiente_conocido_bs"],prev["precio_mayor_cierre_bs"]),
                        tipo_cambio_bs_usd_conocido=prev_fx,
                        variacion_tipo_cambio_ultimo_mes=prev_fx/prev_prev_fx-1,
                        antiguedad_tipo_cambio_dias=(start-datetime.fromisoformat(prev["cotizacion_observada_at"])).days,
                        dias_sin_stock_mes_anterior=prev["dias_sin_stock_observados"] if prev["dias_observados_stock"] else None,
                        cobertura_stock_mes_anterior=prev["dias_observados_stock"]/calendar.monthrange(start.year if start.month > 1 else start.year-1,start.month-1 if start.month>1 else 12)[1],
                        categoryId=products[pid]["categoryId"], target_ventas_mes=sales,
                        feature_cutoff_at=stamp(start), history_snapshot_id="history-v2-"+digest([h["history_snapshot_id"] for h in history[-3:]])[:24], quality_status="TRAINABLE"))
                history.append(row)
    for rows, month_key in [(base,"mes"),(supervised,"mes_objetivo"),(ledger,"mes"),(audit,"mes_objetivo")]:
        rows.sort(key=lambda x:(x[month_key],x["productId"],x["locationId"],x.get("scenario_id","")))
    return base, supervised, audit, ledger


def validate_generated(tables, schema):
    """Puerta mínima de publicación. V2-07 conserva la revisión exhaustiva."""
    base, supervised, audit, ledger = tables
    errors = []
    if not all(tables):
        raise ValueError("Build vacío o incompleto")
    tables_schema = [(base,schema["design"]["supporting_tables"]["base_mensual.csv"]["columns"]),
                     (supervised,schema["columns"]),
                     (audit,schema["design"]["supporting_tables"]["escenarios_metadatos.csv"]["columns"])]
    for rows, cols in tables_schema:
        names = {c["name"] for c in cols}
        for row in rows:
            if set(row) != names:
                errors.append("COLUMN_CONTRACT")
            for c in cols:
                value = row.get(c["name"])
                if value is None:
                    if not c["nullable"]:
                        errors.append("REQUIRED_NULL")
                    continue
                if c["type"] in ("integer","number"):
                    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                        errors.append("INVALID_NUMBER")
                    elif c["type"] == "integer" and not isinstance(value,int):
                        errors.append("NON_INTEGER")
                    for bound,rule in c.get("bounds",{}).items():
                        if bound == "minimum" and value < rule or bound == "maximum" and value > rule:
                            errors.append("OUT_OF_BOUNDS")
                if "allowed_values" in c and value not in c["allowed_values"]:
                    errors.append("ENUM")
    keys = [(x["productId"],x["locationId"],x["mes"]) for x in base]
    if len(keys) != len(set(keys)):
        errors.append("DUPLICATE_MONTH")
    index = dict(zip(keys,base))
    pairs = {(x["productId"],x["locationId"]) for x in base}
    expected_base = {(p,s,month_start(i).strftime("%Y-%m")) for p,s in pairs for i in range(24)}
    if set(keys) != expected_base or len(ledger) != len(base):
        errors.append("INCOMPLETE_GRID")
    fx_by_month = {}
    for row in base:
        date = datetime.strptime(row["mes"], "%Y-%m")
        days = calendar.monthrange(date.year,date.month)[1]
        if not 0 <= row["dias_sin_stock_observados"] <= row["dias_observados_stock"] <= days:
            errors.append("STOCK_CALENDAR")
        if sum(row[k] for k in ["unidades_por_menor","unidades_por_mayor","unidades_modalidad_desconocida"]) != row["unidades_vendidas_brutas"]:
            errors.append("MODALITY_ACCOUNTING")
        if not 0 <= row["costo_unitario_bs"] <= row["precio_mayor_cierre_bs"] <= row["precio_menor_cierre_bs"]:
            errors.append("PRICE_HIERARCHY")
        small,big=row["precio_mayor_inicio_siguiente_conocido_bs"],row["precio_menor_inicio_siguiente_conocido_bs"]
        if small is not None and big is not None and not row["costo_unitario_bs"] <= small <= big:
            errors.append("PLAN_PRICE_HIERARCHY")
        if row["cotizacion_observada_at"] > row["cotizacion_disponible_at"] or row["cotizacion_disponible_at"] > row["ventas_disponibles_at"]:
            errors.append("FX_CLOCK")
        current_fx = tuple(row[k] for k in ("tipo_cambio_bs_usd","cotizacion_fuente_id","cotizacion_observada_at","cotizacion_disponible_at"))
        if row["mes"] in fx_by_month and fx_by_month[row["mes"]] != current_fx:
            errors.append("FX_NOT_COMMON")
        fx_by_month[row["mes"]]=current_fx
    if len({x["scenario_instance_id"] for x in audit}) != len(audit):
        errors.append("AUDIT_DUPLICATE")
    previous_ledger={}
    for row in ledger:
        key=(row["productId"],row["locationId"])
        if key in previous_ledger:
            previous=previous_ledger[key]
            if row["opening_stock"] != previous["closing_stock"] or row["transit_opening"] != previous["transit_closing"]:
                errors.append("LEDGER_CONTINUITY")
        previous_ledger[key]=row
        if row["opening_stock"]+row["received_units"]-row["sold_units"] != row["closing_stock"] or row["closing_stock"] < 0:
            errors.append("STOCK_ACCOUNTING")
        if row["transit_opening"]+row["sent_units"]-row["received_units"] != row["transit_closing"]:
            errors.append("TRANSIT_ACCOUNTING")
        if row["sold_units"] > row["latent_units"]:
            errors.append("SALES_EXCEED_REQUESTS")
    skeys = [(x["productId"],x["locationId"],x["mes_objetivo"]) for x in supervised]
    if len(skeys) != len(set(skeys)):
        errors.append("DUPLICATE_SUPERVISED")
    if set(skeys) != {(p,s,month_start(i).strftime("%Y-%m")) for p,s in pairs for i in range(3,24)}:
        errors.append("INCOMPLETE_SUPERVISED_GRID")
    for row in supervised:
        year,month = map(int,row["mes_objetivo"].split("-"))
        absolute=year*12+month-1
        source_snapshots = []
        for lag,name in [(1,"ventas_mes_anterior"),(2,"ventas_hace_2_meses"),(3,"ventas_hace_3_meses")]:
            number=absolute-lag
            source=index.get((row["productId"],row["locationId"],f"{number//12:04}-{number%12+1:02}"))
            if source is None or source["unidades_vendidas_brutas"] != row[name]:
                errors.append("LAG_MISMATCH")
            if source is not None:
                source_snapshots.append(source["history_snapshot_id"])
            if source is not None and source["ventas_disponibles_at"] > row["feature_cutoff_at"]:
                errors.append("FUTURE_HISTORY")
            if source is not None and lag == 1:
                for field in ["precios_disponibles_at","plan_precios_disponible_at","cotizacion_disponible_at","stock_disponible_at"]:
                    if source[field] is not None and source[field] > row["feature_cutoff_at"]:
                        errors.append("FUTURE_OPTIONAL_FEATURE")

        if row["history_snapshot_id"] != "history-v2-"+digest(list(reversed(source_snapshots)))[:24]:
            errors.append("SNAPSHOT_MISMATCH")
        if index[(row["productId"],row["locationId"],row["mes_objetivo"])]["unidades_vendidas_brutas"] != row["target_ventas_mes"]:
            errors.append("TARGET_MISMATCH")
    if errors:
        raise ValueError("Build rechazado: "+", ".join(sorted(set(errors))))
    return dict(status="PASSED_BASIC_PUBLICATION_GATE_NOT_TRAINING_APPROVAL", rows_base=len(base),
                rows_supervised=len(supervised), audit_instances=len(audit), errors=0,
                exhaustive_v2_07_complete=False, training_authorized=False)


def write_csv(path, rows, columns):
    with path.open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns,lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build(build_id, root=ROOT):
    root=Path(root).resolve()
    token(build_id)
    destination=root/"data/repuestopro_v2/2.0.0"/build_id
    if destination.exists():
        raise FileExistsError("El build ya existe. No se sobrescribe.")
    config,preparation,schema,catalog=load_inputs(root)
    staging=root/"tmp"/token("build-"+build_id)
    if not staging.resolve().is_relative_to(root/"tmp"):
        raise ValueError("Temporal fuera del módulo")
    staging.mkdir(parents=True,exist_ok=False)
    tables=simulate(config,preparation,schema,catalog)
    validation=validate_generated(tables,schema)
    base,supervised,audit,ledger=tables
    write_csv(staging/"base_mensual.csv",base,[c["name"] for c in schema["design"]["supporting_tables"]["base_mensual.csv"]["columns"]])
    write_csv(staging/"dataset_supervisado.csv",supervised,[c["name"] for c in schema["columns"]])
    write_csv(staging/"escenarios_metadatos.csv",audit,[c["name"] for c in schema["design"]["supporting_tables"]["escenarios_metadatos.csv"]["columns"]])
    write_csv(staging/"simulation_ledger.csv",ledger,LEDGER_COLUMNS)
    split={"origin":"SYNTHETIC","root_seed":42,"new_v2_streams":True,
           "test_access_status":"GENERATED_AND_INTEGRITY_CHECKED_NOT_USED_FOR_SELECTION",
           "training_authorized":False,"random_split":False,"sets":{}}
    for name,start,end in [("TRAIN","2025-01","2026-03"),("VALIDATION","2026-04","2026-06"),("TEST","2026-07","2026-09")]:
        rows=[x for x in supervised if start <= x["mes_objetivo"] <= end]
        split["sets"][name]={"start":start,"end":end,"rows":len(rows),"row_content_sha256":digest(rows)}
    required=schema["design"]["publication"]["manifest_required"]
    manifest={"dataset_version":"2.0.0","build_id":build_id,"origin":"SYNTHETIC",
        "dataset_name":"DATOS_SINTETICOS_DEMANDA_H4_V2","status":"BUILT_PENDING_V2_07_NOT_FOR_TRAINING",
        "root_seed":42,"generator_version":VERSION,"generator_sha256":sha256_file(Path(__file__)),
        "config_id":config["contract_version"],"config_sha256":sha256_file(root/"v2/contracts/calibration.v2.json"),
        "catalog_reference_sha256":sha256_file(root/"catalog_reference.json"),"catalog_observed_at":catalog["observed_at"],
        "selected_product_ids":catalog["included_product_ids"],"selected_store_ids":[x["id"] for x in catalog["locations"] if x["type"]=="TIENDA"],
        "reference_source_ids":[x["source_id"] for x in config["input_evidence"]],
        "reference_snapshot_ids":{x["source_id"]:x["snapshot_id"] for x in config["input_evidence"]},
        "reference_raw_sha256":{x["source_id"]:x["raw_sha256"] for x in config["input_evidence"]},
        "compatibility_report_sha256":sha256_file(root/"reports/v2/compatibility/compatibility-20261114-01/source_compatibility_matrix.json"),
        "processing_versions_if_any":[],"assumptions":config["limitations"],
        "created_at":stamp(datetime.now(timezone.utc)),"feature_sets":schema["design"]["feature_sets"],
        "split_design":split,"test_access_status":split["test_access_status"],
        "environment_versions":{"python":platform.python_version()},"training_authorized":False,
        "implemented_variant":{"hurdle":"geometric", "fx_path":[10,10,11.5,11.5,10,10,8.5,8.5],
            "fx_path_repeat":True,"fx_delay_months":1,"cost_pass_through":.5,"price_step_up":.25,
            "price_step_down":-.1,"initial_stock":0,"shipment_units":6,"receipt_delays_days":[0,7,30,60],
            "receipt_delay_status":"ASSUMED_FIXTURE_NOT_EMPIRICALLY_ESTIMATED",
            "bulk_multiplier":4,"scale_multiplier":1,"price_known_delay_days":4,
            "note":"Una variante explícita. No ejecuta todos los mecanismos, niveles o combinaciones del contrato."},
        "scenario_coverage":{"observed_ids":sorted({x["scenario_id"] for x in audit}),
            "unexecuted_ids":sorted({c["scenario_id"] for c in preparation["scenario_design"]["scenarios"]}-{x["scenario_id"] for x in audit}),
            "all_57_scenarios_validated":False,"mandatory_combinations_validated":False},
        "audit_limit":"Cada instancia marca un evento o propiedad simulada, no prueba de aceptación del escenario completo.",
        "recipe_sha256":digest(config["simulation_recipe"]),"catalog_not_current_database":True,
        "source_schema_sha256":sha256_file(root/"v2/contracts/dataset_columns.v2.json")}
    if not set(required) <= manifest.keys():
        raise ValueError("Falta trazabilidad obligatoria")
    build_schema=copy.deepcopy(schema)
    build_schema["design"]["definition_status"]="BUILD_GENERATED_PENDING_EXHAUSTIVE_V2_07"
    build_schema["design"]["publication"]["build_created"]=True
    build_schema["design"]["split_design"]["test_status"]=split["test_access_status"]
    build_schema["design"]["split_design"]["test_hash"]=split["sets"]["TEST"]["row_content_sha256"]
    build_schema["design"]["future_work"]=[x for x in build_schema["design"]["future_work"] if not x.startswith("V2-06")]
    build_schema["design"]["reference_use"]["monash_car_parts"]="Frecuencia y media positiva de perfiles congelados utilizadas como referencia estadística en V2-05A. Distribución y efectos económicos son supuestos académicos, no calibración comercial."
    validate_contract(build_schema,"dataset_schema")
    files={"manifest.json":manifest,"schema.json":build_schema,"split_manifest.json":split,
           "validation.json":validation,"generator_config.json":config,"catalog_reference.json":catalog}
    for name,value in files.items():
        with (staging/name).open("xb") as f:f.write(encoded(value))
    inventory={p.name:sha256_file(p) for p in staging.iterdir() if p.is_file()}
    with (staging/"checksums.sha256").open("x",encoding="utf-8",newline="\n") as f:
        f.write("".join(f"{v}  {name}\n" for name,v in sorted(inventory.items())))
    # Reserva exclusiva. Manifest se copia al final para no presentar un build parcial como completo.
    target=new_build_directory("2.0.0",build_id,root=root)
    for path in sorted(staging.iterdir(),key=lambda x:(x.name=="manifest.json",x.name)):
        with path.open("rb") as source,(target/path.name).open("xb") as dest:
            shutil.copyfileobj(source,dest)
    if any(sha256_file(target/name)!=value for name,value in inventory.items()):
        raise ValueError("Publicación incompleta: no utilizar este build")
    return target,validation,manifest


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-id",required=True)
    args=parser.parse_args()
    target,validation,manifest=build(args.build_id)
    print(json.dumps({"path":str(target),"status":manifest["status"],"validation":validation},ensure_ascii=True))
