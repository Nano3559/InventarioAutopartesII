"""Evaluate pre-issued monthly forecasts without opening datasets or models."""

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re


SCHEMA = "demand-offline-evaluation-1"
MAX_UNITS = 10**9
LOCAL = timezone(timedelta(hours=-4))
GROUPS = ("productId", "locationId", "targetMonth", "volume", "intermittency", "availability", "incident")
COHORT_FIELDS = {"schema", "kind", "cohortId", "datasetVersion", "modelId", "modelSha256", "sources", "rows"}
ROW_FIELDS = {"productId", "locationId", "targetMonth", "cutoffAt", "familyId", "observed", "forecast",
              "status", "provenance"}
OPTIONAL = {"observedAt", "issuedAt", "abstentionReason", "ineligibilityReason", "baseline", "baselineIssuedAt",
            "groups", "classifiedAt"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _fields(value, required, optional):
    _require(type(value) is dict and required <= value.keys() <= required | optional, "Missing or unknown fields")


def _identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value) is not None


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _timestamp(value):
    _require(isinstance(value, str) and "T" in value, "Timestamp must be ISO 8601 with timezone")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(result.tzinfo is not None, "Timestamp must be ISO 8601 with timezone")
    return result


def _units(value, integer=False):
    _require(type(value) in ((int,) if integer else (int, float)) and 0 <= value <= MAX_UNITS,
             "Units must be finite, nonnegative and within the supported limit")


def _row(row, cohort):
    _fields(row, ROW_FIELDS, OPTIONAL)
    for field in ("productId", "locationId"):
        _require(type(row[field]) is int and 1 <= row[field] <= 2**31 - 1, "Invalid product or location ID")
    _require(_identifier(row["familyId"]), "Invalid familyId")
    month = row["targetMonth"]
    _require(isinstance(month, str) and re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", month), "Invalid targetMonth")
    _require(month >= "2026-11", "Only months after the frozen TEST are supported")
    year, number = map(int, month.split("-"))
    _require((year, number) != (9999, 12), "Closing date out of range")
    cutoff = datetime(year, number, 1, tzinfo=LOCAL)
    close = datetime(year + (number == 12), number % 12 + 1, 1, tzinfo=LOCAL)
    _require(_timestamp(row["cutoffAt"]) == cutoff, "Cutoff must equal target month start in America/La_Paz")
    status = row["status"]
    _require(status in ("COVERED", "ABSTAINED", "INELIGIBLE"), "Invalid coverage status")
    observed, forecast, baseline = row["observed"], row["forecast"], row.get("baseline")
    observed_at, issued_at, baseline_at = (row.get(k) for k in ("observedAt", "issuedAt", "baselineIssuedAt"))
    if observed is not None:
        _units(observed, integer=True)
        _require(_timestamp(observed_at) >= close, "Outcome available before monthly close")
    else:
        _require(status == "INELIGIBLE" and observed_at is None, "Eligible observation needs a closed outcome")
    if status == "COVERED":
        _units(forecast)
    else:
        _require(forecast is None, "Unserved observations must retain a null forecast")
    for actual, expected in (("abstentionReason", "ABSTAINED"), ("ineligibilityReason", "INELIGIBLE")):
        reason = row.get(actual)
        _require(_identifier(reason) if status == expected else reason is None, f"Invalid {actual} for {status}")
    if status == "INELIGIBLE":
        _require(issued_at is None and baseline is None, "Ineligible observations cannot be scored")
    else:
        _require(_timestamp(issued_at) <= cutoff, "Forecast issued after cutoff")
    if baseline is not None:
        _units(baseline)
        _require(_timestamp(baseline_at) <= cutoff, "Baseline issued after cutoff")
        _require(cohort.get("baselineId") is not None, "Baseline identity required")
    else:
        _require(baseline_at is None, "Missing baseline must have no issuance timestamp")

    groups = row.get("groups", {})
    _fields(groups, set(), set(GROUPS[3:]))
    _require(all(value is None or _identifier(value) for value in groups.values()), "Invalid group label")
    as_of_groups = any(groups.get(k) is not None for k in ("volume", "intermittency"))
    if as_of_groups:
        _require(_timestamp(row.get("classifiedAt")) <= cutoff, "Volume or intermittency classified after cutoff")
    else:
        _require(row.get("classifiedAt") is None, "Classification date without an as-of group")

    sources = row["provenance"]
    expected = {label for label, present in (("observed", observed is not None), ("forecast", status != "INELIGIBLE"),
                ("baseline", baseline is not None), ("grouping", any(v is not None for v in groups.values()))) if present}
    _fields(sources, expected, set())
    _require(all(isinstance(ref, str) and ref in cohort["sources"] for ref in sources.values()), "Unknown source reference")
    error = forecast - observed if status == "COVERED" else None
    return {**deepcopy(row), "cohortId": cohort["cohortId"], "datasetVersion": cohort["datasetVersion"],
            "modelId": cohort["modelId"], "signedError": error, "absoluteError": abs(error) if error is not None else None}


def _quantile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    lo, hi = math.floor(position), math.ceil(position)
    return sorted_values[lo] + (position - lo) * (sorted_values[hi] - sorted_values[lo])


def _errors(errors, observed):
    n = len(errors)
    absolute = sorted(map(abs, errors))
    total = sum(observed)
    abs_total = math.fsum(absolute)
    return {
        "n": n, "observedUnits": total,
        "mae": abs_total / n if n else None,
        "rmse": math.sqrt(math.fsum(e * e for e in errors) / n) if n else None,
        "signedBias": math.fsum(errors) / n if n else None,
        "wape": abs_total / total if total else None,
        "p90AbsoluteError": _quantile(absolute, .90) if n else None,
        "p95AbsoluteError": _quantile(absolute, .95) if n else None,
    }


def _summary(rows):
    covered = [r for r in rows if r["status"] == "COVERED"]
    abstained = sum(r["status"] == "ABSTAINED" for r in rows)
    eligible = len(covered) + abstained
    paired = [r for r in covered if r.get("baseline") is not None]
    observed = [r["observed"] for r in paired]
    model = _errors([r["signedError"] for r in paired], observed)
    baseline = _errors([r["baseline"] - r["observed"] for r in paired], observed)
    return {
        "total": len(rows), "eligible": eligible, "covered": len(covered), "abstained": abstained,
        "ineligible": len(rows) - eligible, "coverage": len(covered) / eligible if eligible else None,
        "metrics": _errors([r["signedError"] for r in covered], [r["observed"] for r in covered]),
        "paired": {"n": len(paired), "model": model, "baseline": baseline,
                   "deltaMae": model["mae"] - baseline["mae"] if paired else None},
    }


def evaluate(cohort):
    """Return deterministic evidence and summaries from a validated in-memory cohort."""
    _fields(cohort, COHORT_FIELDS, {"authorizationRef", "baselineId"})
    _require(cohort["schema"] == SCHEMA, "Unsupported evaluation schema")
    for key in ("cohortId", "datasetVersion", "modelId"):
        _require(_identifier(cohort[key]), f"Invalid {key}")
    _require(_sha(cohort["modelSha256"]), "Invalid model SHA256")
    kind = cohort["kind"]
    _require(kind in ("FIXTURE", "AUTHORIZED_FUTURE"), "Only fixtures and authorized future cohorts are supported")
    if kind == "FIXTURE":
        _require(cohort["datasetVersion"].startswith("fixture-") and cohort.get("authorizationRef") is None,
                 "Fixtures need their own dataset identity and no authorization reference")
    else:
        _require(_identifier(cohort.get("authorizationRef")) and cohort["datasetVersion"] != "4.0.0"
                 and not cohort["datasetVersion"].startswith("fixture-"),
                 "Future cohorts require prior authorization and an independent dataset identity")
    _require(cohort.get("baselineId") is None or _identifier(cohort["baselineId"]), "Invalid baselineId")
    sources = cohort["sources"]
    _require(type(sources) is dict and all(_identifier(k) and _sha(v) for k, v in sources.items()), "Invalid sources")
    _require(type(cohort["rows"]) is list, "Rows must be a list")
    rows = []
    seen = set()
    for original in cohort["rows"]:
        row = _row(original, cohort)
        key = (row["productId"], row["locationId"], row["targetMonth"], row["familyId"])
        _require(key not in seen, "Duplicate product/location/month/family in cohort")
        seen.add(key)
        rows.append(row)
    rows.sort(key=lambda r: (r["targetMonth"], r["productId"], r["locationId"], r["familyId"]))
    groups = {}
    for name in GROUPS:
        buckets = defaultdict(list)
        for row in rows:
            buckets[row.get(name) if name in GROUPS[:3] else row.get("groups", {}).get(name)].append(row)
        groups[name] = [{"value": value, **_summary(items)} for value, items in
                        sorted(buckets.items(), key=lambda pair: (pair[0] is None, pair[0]))]
    metadata = {k: deepcopy(v) for k, v in cohort.items() if k != "rows"}
    fingerprint = hashlib.sha256(json.dumps({"metadata": metadata, "rows": rows}, sort_keys=True,
                                            ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()
    return {"schema": SCHEMA, "inputSha256": fingerprint, "metadata": metadata, "summary": _summary(rows),
            "groups": groups, "rows": rows}


def _unique_keys(pairs):
    data = {}
    for key, value in pairs:
        _require(key not in data, "Duplicate JSON key")
        data[key] = value
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Independent evaluation cohort JSON")
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8") as handle:
            cohort = json.load(handle, object_pairs_hook=_unique_keys)
        print(json.dumps(evaluate(cohort), indent=2, sort_keys=True, allow_nan=False))
    except (ValueError, OSError) as error:
        parser.exit(2, f"Evaluation rejected: {error}\n")


if __name__ == "__main__":
    main()
