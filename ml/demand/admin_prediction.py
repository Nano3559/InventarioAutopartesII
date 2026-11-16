"""Consulta administrativa de demostración. Solo lee archivos locales."""
import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_SHA256 = "a0c621c4550259342b6c328608918499097f4e03ef014eea011b2e26ba4d0ccb"
CATALOG_SHA256 = "3cb0c9c1f733d565dcacb33f7a33f9911ed0931b19e1740034289c38a5368404"
TEST_REPORT_SHA256 = "f244f3209e3143eeeebd9a7f798f86a198582573e8d761930e3870c1a0a5351d"


class InvalidSelection(ValueError):
    pass


def validate_history(history):
    if len(history) < 3:
        raise ValueError("Historial insuficiente.")
    from simulator_inputs import parse_month
    def ordinal(value):
        parse_month(value)
        y, m = map(int, value.split("-"))
        return y * 12 + m
    if any(type(r["units"]) is not int or r["units"] < 0 for r in history):
        raise ValueError("Cantidades inválidas.")
    if any(ordinal(b["month"]) != ordinal(a["month"]) + 1 for a, b in zip(history, history[1:])):
        raise ValueError("Hay meses faltantes o duplicados.")


def query(payload):
    from simulator_inputs import verified_bytes
    catalog = json.loads(verified_bytes(HERE / "catalog_reference.json", CATALOG_SHA256, "catálogo"))
    products = [p for p in catalog["products"] if p["id"] in catalog["included_product_ids"]]
    locations = [p for p in catalog["locations"] if p["type"] == "TIENDA"]
    common = dict(origin="DATOS SINTÉTICOS", catalogObservedAt=catalog["observed_at"],
                  horizon=1, model="RandomForestRegressor", version="V1")
    if payload.get("action") == "catalog":
        return dict(**common, products=products, locations=locations)
    pid, lid = payload.get("productId"), payload.get("locationId")
    if type(pid) is not int or type(lid) is not int or pid not in {p["id"] for p in products} or lid not in {p["id"] for p in locations}:
        raise InvalidSelection("Producto o tienda fuera del catálogo de referencia.")
    from simulator_inputs import content_sha256
    if content_sha256((HERE / "data/escenarios_v1_1/base_mensual.csv").read_bytes()) != BASE_SHA256:
        raise ValueError("Dataset no verificado.")
    with (HERE / "data/escenarios_v1_1/base_mensual.csv").open(encoding="utf-8", newline="") as f:
        history = [dict(month=r["mes"], units=int(r["ventas_mes"])) for r in csv.DictReader(f)
                   if int(r["productId"]) == pid and int(r["locationId"]) == lid]
    history.sort(key=lambda r: r["month"])
    validate_history(history)
    year, month = map(int, history[-1]["month"].split("-"))
    target = f"{year + (month == 12):04d}-{month % 12 + 1:02d}"
    from simulator_inputs import FEATURE_NAMES
    from demand_runtime import create_runtime
    values = [history[-i]["units"] for i in (1, 2, 3)] + [math.sin(2 * math.pi * int(target[5:]) / 12), math.cos(2 * math.pi * int(target[5:]) / 12)]
    runtime = create_runtime()
    runtime.activate_v1("Consulta administrativa sintética autorizada, sin promoción de candidatos")
    result = runtime.predict(dict(zip(FEATURE_NAMES, values)))
    if result["prediction"] is None or result["prediction"] < 0:
        raise ValueError(result.get("reason") or "Predicción fuera de cobertura.")
    test = json.loads(verified_bytes(HERE / "reports/v1_test_evaluation.json", TEST_REPORT_SHA256, "reporte TEST"))
    return dict(**common, productId=pid, locationId=lid, targetMonth=target,
                prediction=result["prediction"], baseline=history[-1]["units"], history=history,
                features=dict(zip(FEATURE_NAMES, values)), metrics=test["metrics"])


if __name__ == "__main__":
    try:
        print(json.dumps(query(json.load(sys.stdin)), ensure_ascii=True, allow_nan=False))
    except InvalidSelection:
        print(json.dumps({"code": "INVALID_SELECTION"}))
        sys.exit(1)
    except Exception:
        print(json.dumps({"error": "No se pudo consultar V1. Revise el entorno Python, los archivos y su integridad."}))
        sys.exit(1)
