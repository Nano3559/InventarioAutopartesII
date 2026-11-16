"""Ross scenario generator 1.0.1, dataset 3.0.0, separate from frozen V2.

No inference, training, database access or external observation transplantation.
Economic response parameters are assumptions, not estimated causal elasticities.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import random
import re

ROOT = Path(__file__).resolve().parents[1]
LP = timezone(timedelta(hours=-4))
CSV_NAMES = {"supervised_monthly": "dataset_supervisado", "monthly_outcomes": "base_mensual", "scenario_metadata": "escenarios_metadatos"}
VARIANTS = ("PRICE_UP", "PRICE_DOWN", "MID_MONTH_PRICE", "FX_ONLY", "COST_ONLY",
            "NO_OPENING_STOCK", "WHOLESALE_BULK", "LATE_RECEIPT", "LONG_LEAD",
            "RETAIL_COMMITMENT", "FUTURE_RESERVATION", "UNCHANGED", "IMPORT_USD")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def rng(*key):
    return random.Random(int.from_bytes(hashlib.sha256(canonical([42, *key])).digest(), "big"))


def month(i):
    n = 2026 * 12 + 9 + i
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


def start(m):
    return datetime.fromisoformat(m + "-01T00:00:00-04:00")


def stamp(d):
    return d.isoformat(timespec="seconds")


def money(n):
    return str(Decimal(str(n)).quantize(Decimal("0.0001")))


def dependencies(root=ROOT):
    path = root / "v2/contracts/generator.scenarios.v1.json"
    recipe = json.loads(path.read_text(encoding="utf-8"))
    if recipe["seed"] != 42 or recipe["generator_version"] != "scenario-generator-1.0.1":
        raise ValueError("This version implements seed 42 and the pinned 1.0.1 mechanism only")
    for key in ("dictionary", "sources", "catalog", "calibration", "base_calibration"):
        bound = recipe[key]
        if not (root / bound["path"]).is_file() or sha(root / bound["path"]) != bound["sha256"]:
            raise ValueError(f"Dependency changed: {key}")
    return recipe


def demand_stream(pid, lid, world, i, level, occurrence):
    """Independent simulated daily shocks shared only inside a paired family."""
    m = month(i)
    days = calendar.monthrange(int(m[:4]), int(m[5:]))[1]
    r = rng("demand", pid, lid, world, i)
    active = r.random() < occurrence
    seasonal = 1 + .18 * math.sin(2 * math.pi * (i % 12) / 12)
    total = int(round(level * seasonal * (1 + .008 * i) * r.uniform(.65, 1.35))) if active else 0
    retail = [0] * days
    wholesale = [0] * days
    for _ in range(total):
        (wholesale if r.random() < .25 else retail)[r.randrange(days)] += 1
    return retail, wholesale


def fulfil(retail, wholesale, opening, arrival_day, incoming, future_reserved=0,
           retail_ratio=1., wholesale_ratio=1., elasticity=0., price_day=1,
           commitment_units=0, commitment_day=10, commitment_mode="POR_MAYOR", rounding_shocks=None):
    physical = opening
    history = []
    sold_retail = sold_wholesale = latent = zero_days = 0
    for day, (a, b) in enumerate(zip(retail, wholesale), 1):
        received = incoming if day == arrival_day else 0
        opening_day = physical
        physical += received
        factor_a = retail_ratio ** elasticity if day >= price_day else 1
        factor_b = wholesale_ratio ** elasticity if day >= price_day else 1
        # Common rounding shocks allow one-unit intermittent orders to respond
        # without forcing every fractional expected unit up or down.
        noise = rounding_shocks[day - 1] if rounding_shocks is not None else .5
        need_a, need_b = math.floor(a * factor_a + noise), math.floor(b * factor_b + noise)
        if day == commitment_day:
            if commitment_mode == "POR_MAYOR":
                need_b += commitment_units
            else:
                need_a += commitment_units
        latent += need_a + need_b
        available = max(0, physical - future_reserved)
        zero_days += int(available == 0 or available < need_a + need_b)
        # Known commitments have priority, with the same rule for every variant.
        b_sold = min(available, need_b)
        a_sold = min(available - b_sold, need_a)
        sold_retail += a_sold
        sold_wholesale += b_sold
        physical -= a_sold + b_sold
        history.append({"day": day, "opening_units": opening_day, "received_units": received,
                        "sold_units": a_sold + b_sold, "closing_units": physical,
                        "future_reserved_units": future_reserved})
    return {"retail": sold_retail, "wholesale": sold_wholesale, "target": sold_retail + sold_wholesale,
            "latent": latent, "zero_days": zero_days, "closing": physical, "daily": history}


def simulate(recipe, root=ROOT, products_limit=None, *, recorded_at):
    datetime.fromisoformat(recorded_at)
    dictionary = json.loads((root / recipe["dictionary"]["path"]).read_text(encoding="utf-8"))
    catalog = json.loads((root / recipe["catalog"]["path"]).read_text(encoding="utf-8"))
    calibration = json.loads((root / recipe["calibration"]["path"]).read_text(encoding="utf-8"))
    tables = {name: [] for name in dictionary["tables"]}
    tables["daily_ledger"] = []
    tables["scenario_metadata"] = []
    products = [p for p in catalog["products"] if p["id"] in catalog["included_product_ids"]]
    if products_limit is not None:
        products = products[:products_limit]
    # Monash's aggregate intermittence informs the reference profile, not a claim
    # that every RepuestoPro item shares the same turnover or currency.
    basecal = json.loads((root / recipe["base_calibration"]["path"]).read_text(encoding="utf-8"))
    # Find the approved scalar without interpreting unrelated missing cells as zero.
    def find(node, key):
        if isinstance(node, dict):
            if key in node:
                return node[key]
            for value in node.values():
                result = find(value, key)
                if result is not None:
                    return result
        return None
    reference_occurrence = find(basecal, "occurrence_probability")
    if reference_occurrence is None:
        reference_occurrence = 1 - find(basecal, "zero_probability")
    change_probability = calibration["parameters"]["weekly_price_change_probability"]["value"]
    for p in products:
        pid = p["id"]
        for loc in catalog["locations"]:
            lid = loc["id"]
            profile = rng("profile", pid, lid)
            level = profile.choice([4, 12, 35, 90])
            occurrence = min(.95, reference_occurrence + profile.choice([0, .25, .6]))
            elasticity = profile.choice(recipe["elasticities"])
            initial_price = profile.choice([80, 120, 250, 600])
            for world, bounds in recipe["splits"].items():
                histories = []
                closing_price = initial_price
                for i in range(24):
                    m, t0 = month(i), start(month(i))
                    end = start(month(i + 1))
                    ndays = (end - t0).days
                    state = rng("state", pid, lid, world, i)
                    if state.random() < 1 - (1 - change_probability) ** 4:
                        closing_price *= state.choice([.95, 1.05])
                    retail_price = float(money(closing_price))
                    wholesale_price = float(money(.85 * closing_price))
                    cost = float(money(.55 * closing_price))
                    quote = state.choice([7., 9., 11., 13.])
                    quote_age = state.choice(recipe["quote_age_days"])
                    opening = state.choice([0, 5, 20, 70, 150])
                    incoming = state.choice([0, 10, 50, 150])
                    arrival_day = state.choice([1, 10, ndays])
                    lead = state.choice(recipe["lead_days"])
                    retail, wholesale = demand_stream(pid, lid, world, i, level, occurrence)
                    shocks = [rng("price-rounding", pid, lid, world, i, j).random() for j in range(ndays)]
                    basic = fulfil(retail, wholesale, opening, arrival_day, incoming, rounding_shocks=shocks)
                    if not (bounds[0] <= m <= bounds[1]):
                        histories.append({**basic, "price": retail_price, "major_price": wholesale_price,
                                          "quote": quote, "month": m})
                        continue
                    family = f"family-{world}-{pid}-{lid}-{m}"
                    kind = VARIANTS[(pid * 7 + lid * 3 + i) % len(VARIANTS)]
                    for variant in ["BASE", kind]:
                        sid = family + "-" + variant
                        new_price = retail_price
                        new_major = wholesale_price
                        new_quote = quote
                        new_cost = cost
                        changed_day = 1
                        new_opening, new_arrival, new_incoming, new_lead = opening, arrival_day, incoming, lead
                        committed = 0
                        commitment_mode = "POR_MAYOR"
                        future_reserved = 0
                        if variant in ("PRICE_UP", "MID_MONTH_PRICE"):
                            new_price, new_major = retail_price * 1.25, wholesale_price * 1.25
                            changed_day = (ndays // 2 + 1) if variant == "MID_MONTH_PRICE" else 1
                        elif variant == "PRICE_DOWN":
                            new_price, new_major = retail_price * .85, wholesale_price * .85
                        elif variant == "FX_ONLY":
                            new_quote = quote * 1.2
                        elif variant == "COST_ONLY":
                            new_cost = cost * 1.1
                        elif variant == "IMPORT_USD":
                            new_quote = quote * 1.2
                            new_cost = float(money((cost - 2) / quote)) * new_quote + 2
                        elif variant == "NO_OPENING_STOCK":
                            new_opening = 0
                        elif variant == "WHOLESALE_BULK":
                            committed = state.choice([100, 250, 500])
                        elif variant == "LATE_RECEIPT":
                            new_arrival = ndays + 5
                        elif variant == "LONG_LEAD":
                            new_lead = 60
                        elif variant == "RETAIL_COMMITMENT":
                            committed, commitment_mode = 10, "POR_MENOR"
                        elif variant == "FUTURE_RESERVATION":
                            future_reserved = min(new_opening, 5)
                        result = fulfil(retail, wholesale, new_opening, new_arrival, new_incoming,
                                         future_reserved, new_price / retail_price, new_major / wholesale_price,
                                         elasticity, changed_day, committed, 10, commitment_mode, shocks)
                        available = stamp(t0)
                        outcome_at = stamp(end)
                        common = {"scenario_id": sid, "productId": pid, "locationId": lid}
                        event = {**common, "available_at": available, "origin": "SYNTHETIC_ASSUMPTION",
                                 "source_snapshot_id": family}
                        effective = t0 + timedelta(days=changed_day - 1)
                        weight = (end - effective).total_seconds() / (end - t0).total_seconds()
                        request = {"family": family, "variant": variant, "retail": money(new_price),
                                   "major": money(new_major), "opening": new_opening, "quote": money(new_quote),
                                   "commitment": committed, "commitment_mode": commitment_mode,
                                   "arrival": new_arrival, "cost": money(new_cost), "future_reserved": future_reserved,
                                   "lead_days": new_lead, "price_effective_at": stamp(effective)}
                        tables["scenario_context"].append({**common, "target_month": m,
                            "scenario_family_id": family, "realization_id": world,
                            "base_snapshot_id": family, "feature_cutoff_at": available,
                            "assumed_as_of": available, "recorded_at": recorded_at,
                            "contract_version": "demand-scenarios-1.0.0", "input_sha256": hashlib.sha256(canonical(request)).hexdigest(),
                            "dataset_release_id": recipe["dataset_version"], "scenario_class": "NORMAL" if variant in ("BASE", "UNCHANGED") else "ADVERSE",
                            "source_status": "SYNTHETIC_NOT_REAL_HISTORY", "client_request_id": sid,
                            **{k + "_edit_mode": "KEEP" for k in ["cost", "history", "logistics", "orders", "prices", "quote", "stock"]},
                            "scenario_mode": "HYPOTHETICAL_SCENARIO"})
                        edits = tables["scenario_context"][-1]
                        for field, modes in {
                            "prices": ({"PRICE_UP", "PRICE_DOWN", "MID_MONTH_PRICE"}, "SET_PRICES"),
                            "quote": ({"FX_ONLY", "IMPORT_USD"}, "SET_HYPOTHETICAL_QUOTE"),
                            "cost": ({"COST_ONLY"}, "SET_LANDED_COST_BS"),
                            "stock": ({"NO_OPENING_STOCK"}, "SET_SELLABLE_STOCK"),
                            "orders": ({"WHOLESALE_BULK", "RETAIL_COMMITMENT", "FUTURE_RESERVATION"}, "REPLACE_OPEN_ORDER_PLAN"),
                            "logistics": ({"LATE_RECEIPT", "LONG_LEAD"}, "SET_LOGISTICS_PLAN"),
                        }.items():
                            if variant in modes[0]:
                                edits[field + "_edit_mode"] = modes[1]
                        if variant == "IMPORT_USD":
                            edits["cost_edit_mode"] = "SIMULATE_IMPORT_USD"
                        for h in histories[-3:]:
                            tables["closed_history_monthly"].append({**event, "mes": h["month"],
                                "unidades_por_menor": h["retail"], "unidades_por_mayor": h["wholesale"],
                                "unidades_modalidad_desconocida": 0, "unidades_vendidas_brutas": h["target"], "mes_completo": True})
                        # Baseline price plan remains explicit when a later event is added.
                        for ix, (a, b, lo, hi) in enumerate([(retail_price, wholesale_price, t0, effective),
                                                             (new_price, new_major, effective, end)]):
                            if lo == hi:
                                continue
                            tables["price_plan_events"].append({**event, "price_event_id": sid + f"-p{ix}",
                                "precio_menor_bs": money(a), "precio_mayor_bs": money(b),
                                "effective_from": stamp(lo), "effective_to": stamp(hi), "is_applied_or_proposed": "PROPOSED"})
                        tables["exchange_quote_events"].append({**{k:v for k,v in event.items() if k not in ("productId", "locationId")}, "quote_id": sid + "-q", "bs_per_usd": money(new_quote),
                            "observed_at": stamp(t0 - timedelta(days=quote_age)), "quote_source_id": "ACADEMIC_ASSUMPTION",
                            "rate_kind": "HYPOTHETICAL_BS_USD"})
                        tables["cost_plan_events"].append({**event, "cost_event_id": sid + "-c", "cost_basis": "SIMULATE_IMPORT_USD" if variant == "IMPORT_USD" else "SET_LANDED_COST_BS",
                            "unit_cost_usd": money((cost - 2) / quote) if variant == "IMPORT_USD" else None,
                            "freight_per_unit_bs": "2.0000" if variant == "IMPORT_USD" else None,
                            "other_per_unit_bs": "0.0000" if variant == "IMPORT_USD" else None,
                            "quote_id": sid + "-q" if variant == "IMPORT_USD" else None,
                            "unit_cost_landed_bs": money(new_cost), "effective_from": available,
                            "source_percentage": None})
                        tables["opening_stock_snapshot"].append({**event, "sellable_physical_units": new_opening, "snapshot_at": available})
                        if committed or future_reserved:
                            tables["open_order_plan"].append({**event, "order_id": sid + "-o", "sale_mode": commitment_mode,
                                "outstanding_units_at_cutoff": committed or future_reserved,
                                "reserved_units_at_cutoff": future_reserved,
                                "due_at": stamp(end + timedelta(days=5)) if future_reserved else stamp(t0 + timedelta(days=9))})
                        arrival = t0 + timedelta(days=new_arrival - 1)
                        if new_incoming:
                            tables["pending_shipment_plan"].append({**event, "shipment_id": sid + "-s",
                                "pending_units_at_cutoff": new_incoming, "reserved_after_horizon_units": 0,
                                "expected_arrival_at": stamp(arrival)})
                            if arrival < end:
                                tables["receipt_outcomes"].append({**common, "receipt_id": sid + "-r", "shipment_id": sid + "-s",
                                    "actual_received_at": stamp(arrival), "received_units": new_incoming,
                                    "available_at": stamp(arrival), "origin": "SYNTHETIC_OUTCOME", "source_snapshot_id": family})
                        tables["logistics_policy"].append({**event, "supplier_lead_time_days": new_lead,
                            "internal_restock_days": 2, "planned_order_at": available})
                        tables["replenishment_policy"].append({"scenario_id": sid, "requested": True, "safety_stock_units": 5,
                            "minimum_order_units": 0, "order_multiple_units": 1, "review_period_days": 0,
                            "policy_version": "MONTH_END_COMMITMENT_FLOOR_V1"})
                        tables["monthly_outcomes"].append({**common, "mes_objetivo": m, "target_ventas_mes": result["target"],
                            "outcome_complete": True, "outcome_available_at": outcome_at, "outcome_version": "simulated-1",
                            "latent_demand_units": result["latent"], "actual_stockout_days": result["zero_days"]})
                        last = histories[-1]
                        prev = histories[-2]
                        fields = {f["name"]: None for f in dictionary["tables"]["supervised_monthly"]["fields"]}
                        fields.update({**common, "mes_objetivo": m, "scenario_family_id": family, "realization_id": world,
                            "ventas_mes_anterior": last["target"], "ventas_hace_2_meses": prev["target"], "ventas_hace_3_meses": histories[-3]["target"],
                            "mes_sin": math.sin(2 * math.pi * int(m[5:]) / 12), "mes_cos": math.cos(2 * math.pi * int(m[5:]) / 12),
                            "proporcion_por_mayor_mes_anterior": last["wholesale"] / last["target"] if last["target"] else None,
                            "cobertura_modalidad_mes_anterior": 1, "precio_menor_cierre_anterior_bs": money(last["price"]),
                            "precio_mayor_cierre_anterior_bs": money(last["major_price"]),
                            "variacion_precio_menor_conocida": retail_price / last["price"] - 1,
                            "variacion_precio_mayor_conocida": wholesale_price / last["major_price"] - 1,
                            "tipo_cambio_bs_usd_conocido": money(new_quote), "variacion_tipo_cambio_ultimo_mes": new_quote / last["quote"] - 1,
                            "antiguedad_tipo_cambio_dias": quote_age, "dias_sin_stock_mes_anterior": last["zero_days"],
                            "cobertura_stock_mes_anterior": 1, "categoryId": p["categoryId"], "target_ventas_mes": result["target"],
                            "feature_cutoff_at": available, "history_snapshot_id": family, "quality_status": "ELIGIBLE_SYNTHETIC",
                            "precio_menor_base_corte_bs": money(retail_price), "precio_mayor_base_corte_bs": money(wholesale_price),
                            "precio_menor_plan_ponderado_bs": money(retail_price * (1 - weight) + new_price * weight),
                            "precio_mayor_plan_ponderado_bs": money(wholesale_price * (1 - weight) + new_major * weight),
                            "variacion_precio_menor_plan_ponderada": (new_price / retail_price - 1) * weight,
                            "variacion_precio_mayor_plan_ponderada": (new_major / wholesale_price - 1) * weight,
                            "dias_vigencia_nuevo_precio_plan": ndays - changed_day + 1 if variant in ("PRICE_UP", "PRICE_DOWN", "MID_MONTH_PRICE") else 0,
                            "stock_vendible_al_corte_unidades": new_opening,
                            "compromisos_por_menor_horizonte_unidades": committed if commitment_mode == "POR_MENOR" else 0,
                            "compromisos_por_mayor_horizonte_unidades": committed if commitment_mode == "POR_MAYOR" else 0,
                            "reservas_horizonte_unidades": 0, "reservas_posteriores_unidades": future_reserved,
                            "entradas_plan_horizonte_unidades": new_incoming if arrival < end else 0,
                            "dias_hasta_primera_entrada_plan": new_arrival - 1 if new_incoming and arrival < end else None,
                            "plazo_proveedor_plan_dias": new_lead, "plazo_interno_plan_dias": 2})
                        tables["supervised_monthly"].append(fields)
                        tables["daily_ledger"].extend({**common, "date": stamp(t0 + timedelta(days=x["day"] - 1)), **x} for x in result["daily"])
                        tables["scenario_metadata"].append({"scenario_id": sid, "scenario_family_id": family,
                            "partition": world, "intervention": variant, "assumed_elasticity": elasticity,
                            "evidence_kind": "ASSUMED_NOT_ESTIMATED", "eligible_for_X": False})
                    histories.append({**basic, "price": retail_price, "major_price": wholesale_price, "quote": quote, "month": m})
    return tables, dictionary


def write_tables(destination, tables, dictionary):
    for name, rows in tables.items():
        names = [f["name"] for f in dictionary["tables"][name]["fields"]] if name in dictionary["tables"] else list(rows[0])
        with (destination / (CSV_NAMES.get(name, name) + ".csv")).open("x", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=names, extrasaction="raise")
            writer.writeheader()
            writer.writerows({k: "" if v is None else v for k, v in row.items()} for row in rows)


def build(build_id, root=ROOT, *, recorded_at=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", build_id):
        raise ValueError("Invalid build ID")
    recipe = dependencies(root)
    final = root / "data/repuestopro_v2" / recipe["dataset_version"] / build_id
    temp = root / "tmp" / build_id
    if final.exists() or temp.exists():
        raise FileExistsError("Never overwrite a published or staged build")
    temp.mkdir(parents=True)
    recorded_at = recorded_at or stamp(datetime.now(timezone.utc))
    tables, dictionary = simulate(recipe, root, recorded_at=recorded_at)
    write_tables(temp, tables, dictionary)
    def write(name, value):
        with (temp / name).open("x", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
    # Keep the R01 design immutable, while making the build schema truthful.
    schema = json.loads(json.dumps(dictionary))
    schema["design_reference_status"] = schema["status"]
    schema["status"] = "GENERATED_SYNTHETIC_FEATURE_SELECTION_PENDING_E04"
    schema["dataset_version"] = recipe["dataset_version"]
    schema["no_dataset_generated"] = False
    schema["design_reference"] = recipe["dictionary"]
    for name, table in schema["tables"].items():
        table["status"] = "HEADER_ONLY_NO_MODEL_OUTPUT" if name == "decision_outputs" else "GENERATED_SYNTHETIC"
        for field in table["fields"]:
            field["implementation_status"] = table["status"]
            if field["role"] == "FEATURE":
                field["model_input_status"] = "CANDIDATE_PENDING_E04"
    write("schema.json", schema)
    write("catalog_reference.json", json.loads((root / recipe["catalog"]["path"]).read_text(encoding="utf-8")))
    write("split_manifest.json", {"splits": recipe["splits"], "warmup": recipe["warmup"],
          "world_policy": recipe["world_policy"], "test_status": "SEALED_NOT_SCORED", "random_split": False})
    write("scenario_cases.json", {"normal": list(VARIANTS), "ambiguous_excluded_from_supervised": [
        {"case": x, "expected": "ABSTAIN_OR_PARTIAL_NO_INVENTED_VALUE"} for x in [
            "NEW_PRODUCT_NO_HISTORY", "NEW_STORE", "INCOMPLETE_HISTORY_MONTH", "UNKNOWN_QUOTE",
            "UNKNOWN_LANDED_COST", "OUTSIDE_ONE_MONTH_HORIZON", "UNCONFIRMED_RECEIPT", "UNCERTAIN_PROMOTION"]],
        "invalid_rejected": ["NEGATIVE_QUANTITY", "WHOLESALE_ABOVE_RETAIL", "PRICE_BELOW_COST",
            "QUOTE_AFTER_CUTOFF", "DUPLICATE_ORDER", "RESERVATIONS_ABOVE_PHYSICAL", "FUTURE_TARGET_AS_FEATURE"]})
    write("manifest.json", {"dataset_version": recipe["dataset_version"], "build_id": build_id,
          "origin": "ACADEMIC_SYNTHETIC_NOT_REAL_REPUESTOPRO_SALES", "seed": 42,
          "recorded_at": recorded_at, "generator_version": recipe["generator_version"],
          "generator": {"path": "v2/generate_scenarios_v1.py", "sha256": sha(root / "v2/generate_scenarios_v1.py")},
          "recipe": {"path": "v2/contracts/generator.scenarios.v1.json", "sha256": sha(root / "v2/contracts/generator.scenarios.v1.json")},
          "row_counts": {k: len(v) for k, v in tables.items()}, "automotive": "EXCLUDED_LICENSE_PENDING",
          "csv_table_names": CSV_NAMES,
          "artifact": None, "training_performed": False, "test_scored": False,
          "economic_effects": "ASSUMED_NOT_CAUSALLY_ESTIMATED", "publication_scope": "PRIVATE_ACADEMIC_REVIEW",
          "notes": ["No statistical predictions in decision_outputs: header only until Erika supplies an accepted artifact.",
                    "14 dictionary tables plus daily ledger and metadata. Structural validation may read TEST but never score a model.",
                    "Decision flags, latent quantities, partitions, family IDs and outcomes are excluded from X."]})
    from v2.validate_scenarios_v1 import validate
    result = validate(temp)
    write("validation.json", result)
    if not result["valid"]:
        raise ValueError(result["errors"][:10])
    files = sorted(temp.iterdir())
    with (temp / "checksums.sha256").open("x", encoding="ascii") as f:
        f.write("".join(f"{sha(p)}  {p.name}\n" for p in files if p.is_file()))
    final.parent.mkdir(parents=True, exist_ok=True)
    temp.rename(final)
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--recorded-at", help="Replay only: original manifest timestamp, to reproduce audit bytes")
    args = parser.parse_args()
    print(build(args.build_id, recorded_at=args.recorded_at))
