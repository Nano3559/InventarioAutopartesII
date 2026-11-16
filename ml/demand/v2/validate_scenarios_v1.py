"""Independent structural/event validator. Never fits or evaluates a model."""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import math


def validate(path):
    path = Path(path)
    errors = []
    filenames = {"supervised_monthly": "dataset_supervisado", "monthly_outcomes": "base_mensual", "scenario_metadata": "escenarios_metadatos"}
    def check(condition, message):
        if not condition and len(errors) < 200:
            errors.append(message)
    def rows(name):
        with (path / (filenames.get(name, name) + ".csv")).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    schema = json.loads((path / "schema.json").read_text(encoding="utf-8"))
    tables = {k: rows(k) for k in schema["tables"]}
    for name, table in schema["tables"].items():
        expected = [f["name"] for f in table["fields"]]
        with (path / (filenames.get(name, name) + ".csv")).open(encoding="utf-8", newline="") as f:
            check(next(csv.reader(f)) == expected, f"{name}: header differs")
        keys = set()
        for row in tables[name]:
            pk = tuple(row[k] for k in table["primary_key"])
            check(pk not in keys, f"{name}: duplicate primary key {pk}")
            keys.add(pk)
            for field in table["fields"]:
                value = row[field["name"]]
                check(value != "" or field["type"]["nullable"], f"{name}.{field['name']}: missing required")
                if value != "":
                    logical = field["type"]["logical"]
                    try:
                        if logical == "integer":
                            check(str(int(value)) == value and int(value) >= 0, f"{name}.{field['name']}: invalid nonnegative integer")
                        elif logical in ("number", "float", "decimal", "ratio", "continuous"):
                            check(math.isfinite(float(value)), f"{name}.{field['name']}: nonfinite")
                        elif logical == "boolean":
                            check(value in ("True", "False"), f"{name}.{field['name']}: boolean")
                    except (ValueError, OverflowError):
                        check(False, f"{name}.{field['name']}: invalid {logical}")
    contexts = {r["scenario_id"]: r for r in tables["scenario_context"]}
    groups = defaultdict(list)
    for name, records in tables.items():
        for r in records:
            check(r["scenario_id"] in contexts, f"{name}: orphan scenario")
            if "available_at" in r and name not in ("receipt_outcomes",):
                check(datetime.fromisoformat(r["available_at"]) <= datetime.fromisoformat(contexts[r["scenario_id"]]["feature_cutoff_at"]), f"{name}: unavailable at cutoff")
    for r in rows("scenario_metadata"):
        groups[r["scenario_family_id"]].append(r)
    for family, members in groups.items():
        check(len(members) == 2 and len({r["partition"] for r in members}) == 1, f"family split leakage: {family}")
    stocks = {r["scenario_id"]: int(r["sellable_physical_units"]) for r in tables["opening_stock_snapshot"]}
    ledgers = defaultdict(list)
    for r in rows("daily_ledger"):
        sid = r["scenario_id"]
        ledgers[sid].append(r)
        a, b, c, d = (int(r[k]) for k in ("opening_units", "received_units", "sold_units", "closing_units"))
        check(min(a, b, c, d) >= 0 and a + b - c == d, f"{sid}: stock balance")
    outcomes = {r["scenario_id"]: r for r in tables["monthly_outcomes"]}
    prices, history, quotes, shipments, costs = (defaultdict(list) for _ in range(5))
    for name, group in [("price_plan_events", prices), ("closed_history_monthly", history),
                        ("exchange_quote_events", quotes), ("pending_shipment_plan", shipments), ("cost_plan_events", costs)]:
        for r in tables[name]:
            group[r["scenario_id"]].append(r)
    splits = json.loads((path / "split_manifest.json").read_text(encoding="utf-8"))["splits"]
    partition_counts = Counter()
    seen = set()
    for r in tables["supervised_monthly"]:
        sid = r["scenario_id"]
        check(sid not in seen, f"{sid}: duplicate supervised row")
        seen.add(sid)
        context, outcome = contexts[sid], outcomes[sid]
        t0 = datetime.fromisoformat(r["feature_cutoff_at"])
        end = (t0.replace(day=28) + timedelta(days=4)).replace(day=1)
        check(outcome["outcome_available_at"] == end.isoformat(timespec="seconds"), f"{sid}: target known too early")
        check(r["target_ventas_mes"] == outcome["target_ventas_mes"], f"{sid}: misaligned target")
        check(int(r["target_ventas_mes"]) >= 0 and int(outcome["latent_demand_units"]) >= int(r["target_ventas_mes"]), f"{sid}: invalid gross target")
        partition = context["realization_id"]
        partition_counts[partition] += 1
        check(splits[partition][0] <= r["mes_objetivo"] <= splits[partition][1], f"{sid}: temporal split")
        hs = sorted(history[sid], key=lambda x: x["mes"])
        expected_months = []
        n = t0.year * 12 + t0.month - 1
        for back in [3, 2, 1]:
            z = n - back
            expected_months.append(f"{z // 12:04d}-{z % 12 + 1:02d}")
        check([x["mes"] for x in hs] == expected_months, f"{sid}: incomplete months")
        for h in hs:
            check(sum(int(h[k]) for k in ["unidades_por_menor", "unidades_por_mayor", "unidades_modalidad_desconocida"]) == int(h["unidades_vendidas_brutas"]), f"{sid}: modality total")
        for back, key in [(1, "ventas_mes_anterior"), (2, "ventas_hace_2_meses"), (3, "ventas_hace_3_meses")]:
            check(r[key] == hs[-back]["unidades_vendidas_brutas"], f"{sid}: lag mismatch")
        ps = sorted(prices[sid], key=lambda x: x["effective_from"])
        check(datetime.fromisoformat(ps[0]["effective_from"]) == t0 and datetime.fromisoformat(ps[-1]["effective_to"]) == end, f"{sid}: price coverage")
        weighted = Decimal(0)
        last_end = t0
        for p in ps:
            a, b = datetime.fromisoformat(p["effective_from"]), datetime.fromisoformat(p["effective_to"])
            check(a == last_end and b > a, f"{sid}: price gap or overlap")
            last_end = b
            minor, major = Decimal(p["precio_menor_bs"]), Decimal(p["precio_mayor_bs"])
            check(0 < major <= minor, f"{sid}: wholesale exceeds retail")
            check(Decimal(costs[sid][0]["unit_cost_landed_bs"]) <= major, f"{sid}: price below cost")
            weighted += minor * Decimal(str((b - a).total_seconds())) / Decimal(str((end - t0).total_seconds()))
        check(abs(weighted - Decimal(r["precio_menor_plan_ponderado_bs"])) <= Decimal("0.0002"), f"{sid}: plan weighting")
        q = quotes[sid][0]
        check(Decimal(q["bs_per_usd"]) > 0 and datetime.fromisoformat(q["observed_at"]) <= t0, f"{sid}: invalid quote")
        check((t0 - datetime.fromisoformat(q["observed_at"])).days == int(r["antiguedad_tipo_cambio_dias"]), f"{sid}: quote age")
        cost_event = costs[sid][0]
        if cost_event["cost_basis"] == "SIMULATE_IMPORT_USD":
            computed = Decimal(cost_event["unit_cost_usd"]) * Decimal(q["bs_per_usd"]) + Decimal(cost_event["freight_per_unit_bs"]) + Decimal(cost_event["other_per_unit_bs"])
            check(abs(computed - Decimal(cost_event["unit_cost_landed_bs"])) <= Decimal("0.0001"), f"{sid}: double conversion or wrong import cost")
        ds = sorted(ledgers[sid], key=lambda x: x["date"])
        check(len(ds) == (end - t0).days and int(ds[0]["opening_units"]) == stocks[sid], f"{sid}: incomplete ledger")
        check([x["date"] for x in ds] == [(t0 + timedelta(days=n)).isoformat(timespec="seconds") for n in range((end - t0).days)], f"{sid}: missing or duplicate ledger dates")
        for a, b in zip(ds, ds[1:]):
            check(a["closing_units"] == b["opening_units"], f"{sid}: stock discontinuity")
        check(sum(int(x["sold_units"]) for x in ds) == int(r["target_ventas_mes"]), f"{sid}: sales stock mismatch")
        planned = sum(int(x["pending_units_at_cutoff"]) for x in shipments[sid] if t0 <= datetime.fromisoformat(x["expected_arrival_at"]) < end)
        check(planned == int(r["entradas_plan_horizonte_unidades"]), f"{sid}: incoming plan mismatch")
        check(sum(int(x["received_units"]) for x in ds) == planned, f"{sid}: unconfirmed or late receipt counted in stock")
    for family, members in groups.items():
        pair = {r["intervention"]: outcomes[r["scenario_id"]]["target_ventas_mes"] for r in members}
        for unchanged in ("FX_ONLY", "COST_ONLY", "LONG_LEAD", "UNCHANGED"):
            if unchanged in pair:
                check(pair[unchanged] == pair["BASE"], f"{family}: spurious demand effect")
    check(not tables["decision_outputs"], "Predictions invented before training")
    if (path / "checksums.sha256").exists():
        for line in (path / "checksums.sha256").read_text().splitlines():
            digest, name = line.split("  ", 1)
            check(Path(name).name == name, "Unsafe checksum path")
            check(hashlib.sha256((path / name).read_bytes()).hexdigest() == digest, f"Checksum mismatch: {name}")
    return {"validator_version": "scenario-validator-1.0.0", "valid": not errors, "errors": errors,
            "families": len(groups), "supervised_rows": len(seen), "partition_counts": dict(partition_counts),
            "scope": "STRUCTURAL_ONLY_NO_MODEL_METRICS", "test_scored": False,
            "limitations": ["Not empirical commercial validation or backend API certification.",
                           "Ambiguous and invalid cases are specifications, not invented labeled observations."]}
