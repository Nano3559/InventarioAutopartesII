"""Revisión V2-07 independiente del generador. No escribe en el build.

Se leen etiquetas TEST solo para integridad y fórmulas. No se calculan
estadísticas de sus targets, métricas predictivas ni se ajustan transformaciones.
"""
import calendar
from collections import Counter
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

from v2.structure import ROOT, sha256_file, validate_contract

LOCAL = timezone(timedelta(hours=-4))


def canonical_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False) + "\n"
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def strict_json(text):
    def invalid(value):
        raise ValueError("JSON no finito: " + value)
    return json.loads(text, parse_constant=invalid)


def instant(text):
    try:
        date = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("Fecha inválida") from exc
    if date.utcoffset() is None:
        raise ValueError("Fecha sin zona")
    return date


def month_offset(month, offset):
    if not isinstance(month,str) or not re.fullmatch(r"\d{4}-\d{2}",month):
        raise ValueError("Mes inválido")
    date=datetime.strptime(month,"%Y-%m")
    n=date.year*12+date.month-1+offset
    return f"{n//12:04}-{n%12+1:02}"


def cutoff(month):
    month_offset(month,0)
    return datetime.fromisoformat(month+"-01T00:00:00-04:00")


def read_table(path, columns):
    rows=[]
    with Path(path).open(encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames != [c["name"] for c in columns]:
            raise ValueError("Columnas incorrectas: "+Path(path).name)
        for raw in reader:
            if None in raw:
                raise ValueError("CSV con columnas sobrantes")
            row={}
            for c in columns:
                name=c["name"];value=raw[name]
                if value is None:
                    raise ValueError("CSV incompleto")
                if value=="":
                    if not c["nullable"]:
                        raise ValueError("Null obligatorio: "+name)
                    row[name]=None
                    continue
                kind=c["type"]
                if kind in ("integer","number"):
                    if kind=="integer" and not re.fullmatch(r"-?\d+",value):
                        raise ValueError("Entero inválido: "+name)
                    value=int(value) if re.fullmatch(r"-?\d+",value) else float(value)
                    if not math.isfinite(value):
                        raise ValueError("Número no finito")
                    bounds=c.get("bounds",{})
                    if ("minimum" in bounds and value < bounds["minimum"] or
                        "maximum" in bounds and value > bounds["maximum"] or
                        "exclusiveMinimum" in bounds and value <= bounds["exclusiveMinimum"]):
                        raise ValueError("Número fuera de rango: "+name)
                elif kind=="month":
                    month_offset(value,0)
                elif kind=="datetime":
                    instant(value)
                if "allowed_values" in c and value not in c["allowed_values"]:
                    raise ValueError("Valor no permitido: "+name)
                row[name]=value
            rows.append(row)
    return rows


def close(a,b):
    return a==b if a is None or b is None else math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)


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
            if major is not None:check(r["costo_unitario_bs"]<=major<=minor,"PRICE_PLAN_ORDER")
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
        check(r["history_snapshot_id"]=="synth-v2-"+canonical_hash(body)[:24],"BASE_SNAPSHOT_HASH")
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
        check(r["history_snapshot_id"]=="history-v2-"+canonical_hash([x["history_snapshot_id"] for x in reversed(history)])[:24],"HISTORY_SNAPSHOT")
    return sorted(set(failures))


def split_issues(rows, split):
    errors=[];months={};seen=set()
    ranges=split["sets"]
    if split.get("random_split") is not False or split.get("new_v2_streams") is not True:
        errors.append("SPLIT_POLICY")
    for name in ["TRAIN","VALIDATION","TEST"]:
        spec=ranges[name]
        selected=[x for x in rows if spec["start"]<=x["mes_objetivo"]<=spec["end"]]
        if len(selected)!=spec["rows"] or canonical_hash(selected)!=spec["row_content_sha256"]:
            errors.append("SPLIT_HASH_OR_COUNT")
        for row in selected:
            key=(row["productId"],row["locationId"],row["mes_objetivo"])
            if key in seen:errors.append("SPLIT_OVERLAP")
            seen.add(key)
            months.setdefault(row["mes_objetivo"],set()).add(name)
    if len(seen)!=len(rows) or any(len(v)!=1 for v in months.values()):errors.append("SPLIT_MONTH_GROUP")
    if not ranges["TRAIN"]["end"]<ranges["VALIDATION"]["start"]<=ranges["VALIDATION"]["end"]<ranges["TEST"]["start"]:
        errors.append("SPLIT_ORDER")
    return sorted(set(errors))


def training_statistics(rows, schema):
    """Excluye TEST incluso de estadística descriptiva de targets."""
    output={};warnings=[]
    for name,start,end in [("TRAIN","2025-01","2026-03"),("VALIDATION","2026-04","2026-06")]:
        subset=[x for x in rows if start<=x["mes_objetivo"]<=end]
        target=[x["target_ventas_mes"] for x in subset]
        columns={}
        for c in schema["columns"]:
            if c["role"]!="FEATURE":continue
            values=[x[c["name"]] for x in subset if x[c["name"]] is not None]
            columns[c["name"]]={"nulls":len(subset)-len(values),"unique_nonnull":len(set(values))}
            if name=="TRAIN" and len(set(values))<=1:
                warnings.append({"code":"CONSTANT_OR_EMPTY_FEATURE","feature":c["name"],"blocking":False})
        groups={}
        for field in ["productId","locationId"]:
            groups[field]={str(key):{"rows":len(group),"positive_months":sum(r["target_ventas_mes"]>0 for r in group)}
                           for key in sorted({r[field] for r in subset})
                           for group in [[r for r in subset if r[field]==key]]}
        output[name]={"rows":len(subset),"target":{"zeros":target.count(0),"positive":sum(x>0 for x in target),
            "minimum":min(target),"maximum":max(target),"mean":statistics.mean(target),"median":statistics.median(target)},
            "features":columns,"groups":groups}
    return output,warnings


def inspect_build(path, root=ROOT):
    path=Path(path).resolve();root=Path(root).resolve()
    if not path.is_relative_to(root/"data/repuestopro_v2"):
        raise ValueError("Solo builds V2")
    required={"base_mensual.csv","dataset_supervisado.csv","escenarios_metadatos.csv","manifest.json","schema.json","split_manifest.json","validation.json","checksums.sha256","simulation_ledger.csv","generator_config.json","catalog_reference.json"}
    if {p.name for p in path.iterdir()}!=required:
        raise ValueError("Inventario incompleto o inesperado")
    expected={}
    for line in (path/"checksums.sha256").read_text(encoding="utf-8").splitlines():
        sha,name=line.split("  ",1)
        if name not in required or name=="checksums.sha256" or name in expected:
            raise ValueError("Inventario de hashes inválido")
        if not re.fullmatch("[0-9a-f]{64}",sha) or sha256_file(path/name)!=sha:
            raise ValueError("Contenido alterado: "+name)
        expected[name]=sha
    if set(expected)!=required-{"checksums.sha256"}:raise ValueError("Faltan hashes")
    schema=strict_json((path/"schema.json").read_text(encoding="utf-8"));validate_contract(schema,"dataset_schema")
    manifest=strict_json((path/"manifest.json").read_text(encoding="utf-8"))
    preparation=strict_json((root/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
    active=preparation["dataset_build"]
    config=strict_json((path/"generator_config.json").read_text(encoding="utf-8"))
    catalog=strict_json((path/"catalog_reference.json").read_text(encoding="utf-8"))
    split=strict_json((path/"split_manifest.json").read_text(encoding="utf-8"))
    failures=[]
    if (active["build_id"]!=manifest["build_id"] or
        active["manifest_sha256"]!=sha256_file(path/"manifest.json")):
        failures.append("UNREGISTERED_OR_CHANGED_MANIFEST")
    if manifest["origin"]!="SYNTHETIC" or manifest.get("training_authorized") is not False:failures.append("PROVENANCE_OR_APPROVAL")
    if manifest["generator_sha256"]!=sha256_file(root/"v2/generate.py"):failures.append("GENERATOR_VERSION")
    if manifest["config_sha256"]!=sha256_file(root/"v2/contracts/calibration.v2.json"):failures.append("CONFIG_BYTES_CHANGED")
    if manifest["catalog_reference_sha256"]!=sha256_file(root/"catalog_reference.json"):failures.append("CATALOG_BYTES_CHANGED")
    if canonical_hash(config["simulation_recipe"])!=manifest["recipe_sha256"]:failures.append("RECIPE")
    if manifest["split_design"]!=split:failures.append("SPLIT_MANIFEST_DISAGREES")
    # Copias JSON canónicas no son bytes idénticos a sus fuentes formateadas.
    if config!=strict_json((root/"v2/contracts/calibration.v2.json").read_text(encoding="utf-8")):failures.append("CONFIG_CHANGED")
    if catalog!=strict_json((root/"catalog_reference.json").read_text(encoding="utf-8")):failures.append("CATALOG_CHANGED")
    base=read_table(path/"base_mensual.csv",schema["design"]["supporting_tables"]["base_mensual.csv"]["columns"])
    rows=read_table(path/"dataset_supervisado.csv",schema["columns"])
    audit=read_table(path/"escenarios_metadatos.csv",schema["design"]["supporting_tables"]["escenarios_metadatos.csv"]["columns"])
    with (path/"simulation_ledger.csv").open(encoding="utf-8",newline="") as f:
        ledger=[{k:(v if k=="mes" else int(v)) for k,v in row.items()} for row in csv.DictReader(f)]
    failures+=check_rows(base,rows,ledger,catalog)
    failures+=split_issues(rows,split)
    ids=set();cases={c["scenario_id"]:c for c in strict_json((root/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))["scenario_design"]["scenarios"]}
    base_index={(r["productId"],r["locationId"],r["mes"]):r for r in base}
    for row in audit:
        params=strict_json(row["parameters_json"])
        if row["scenario_instance_id"] in ids:failures.append("AUDIT_DUPLICATE")
        ids.add(row["scenario_instance_id"])
        source=base_index.get((row["productId"],row["locationId"],row["mes_objetivo"]))
        if source is None or row["history_snapshot_id"]!=source["history_snapshot_id"]:failures.append("AUDIT_SOURCE")
        case=cases.get(row["scenario_id"])
        if case is None or row["case_class"]!=case["case_class"] or row["expected_action"]!=case["expected_action"]:failures.append("AUDIT_CONTRACT")
        if params.get("scope")!="SYNTHETIC_INSTANCE_NOT_VALIDATED_SCENARIO_TEST":failures.append("AUDIT_CLAIM")
    stats,warnings=training_statistics(rows,schema)
    warnings.append({"code":"SYNTHETIC_DOMAIN_ONLY","blocking":False,"reason":"No evidencia comercial ni causal."})
    warnings.append({"code":"ONE_ECONOMIC_PATH","blocking":False,"reason":"15 meses TRAIN y una cotización compartida no son cientos de shocks económicos independientes."})
    warnings.append({"code":"LIMITED_OBSERVED_VOLUME","blocking_for_initial_academic_variant":False,
        "train_target_minimum":stats["TRAIN"]["target"]["minimum"],
        "train_target_maximum":stats["TRAIN"]["target"]["maximum"],
        "reason":"El stock simulado limita ventas atendidas. Pedidos latentes grandes y fixtures offline no demuestran cobertura de ventas mayoristas de gran volumen."})
    return {"status":"PASSED" if not failures else "FAILED","failures":sorted(set(failures)),
        "build_id":manifest["build_id"],"manifest_sha256":sha256_file(path/"manifest.json"),
        "counts":{"base":len(base),"supervised":len(rows),"audit":len(audit)},
        "statistics":stats,"warnings":warnings,"test_target_statistics_computed":False,
        "test_hash_verified":split["sets"]["TEST"]["row_content_sha256"],
        "training_performed":False,"training_authorized":False}
