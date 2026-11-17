"""Deterministic baselines from explicitly supplied, as-of monthly sales history."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re


VERSION = "1.0.0"
LOCAL = timezone(timedelta(hours=-4))
MAX_UNITS = 10**9
METHODS = {
    "lag1": set(), "moving_average": {"k"}, "sba": {"alpha"},
    "tsb": {"alpha", "beta"}, "seasonal_naive": set(),
}
IDENTITY = ("productId", "locationId", "targetMonth", "familyId")
HISTORY_FIELDS = {
    "productId", "locationId", "month", "observationId", "observed",
    "closureStatus", "complete", "availableAt", "provenance",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value) is not None


def _sha256(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _instant(value):
    _require(isinstance(value, str) and "T" in value, "Expected an ISO 8601 timestamp with timezone")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(timestamp.utcoffset() is not None, "Timestamp requires a timezone")
    return timestamp


def _month(value):
    _require(isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", value), "Invalid month")
    year, month = map(int, value.split("-"))
    return year * 12 + month - 1


def _start(index):
    year, month = divmod(index, 12)
    return datetime(year, month + 1, 1, tzinfo=LOCAL)


def _valid_id(value):
    return type(value) is int and 1 <= value <= 2**31 - 1


def _validate_parameters(method, parameters):
    _require(isinstance(method, str) and method in METHODS, "Unknown baseline method")
    _require(parameters.keys() == METHODS[method], f"Expected parameters: {sorted(METHODS[method])}")
    if method == "moving_average":
        _require(type(parameters["k"]) is int and parameters["k"] > 0, "k must be a positive integer")
    else:
        for value in parameters.values():
            _require(type(value) in (int, float) and 0 < value <= 1, "Smoothing parameters must be in (0, 1]")


def _history(request):
    fields = set(IDENTITY) | {"cutoffAt", "history"}
    _require(type(request) is dict and request.keys() == fields, "Missing or unknown request fields")
    _require(all(_valid_id(request[k]) for k in IDENTITY[:2]), "Invalid product or location ID")
    _require(_identifier(request["familyId"]), "Invalid target familyId")
    target = _month(request["targetMonth"])
    cutoff = _instant(request["cutoffAt"])
    _require(cutoff == _start(target), "Cutoff must be month start in UTC-04:00")
    _require(type(request["history"]) is list, "History must be a list")
    indexed, identities = {}, set()
    for row in request["history"]:
        _require(type(row) is dict and HISTORY_FIELDS <= row.keys() <= HISTORY_FIELDS | {"stockAvailable"},
                 "Missing or unknown history fields")
        for key in IDENTITY[:2]:
            _require(_valid_id(row[key]) and row[key] == request[key], "Mixed or invalid product/location")
        month = _month(row["month"])
        _require(month < target, "History contains the target or a future month")
        _require(month not in indexed, "Duplicate history month")
        identity = row["observationId"]
        _require(_identifier(identity) and identity not in identities, "Invalid or duplicate observationId")
        identities.add(identity)
        _require(row["closureStatus"] in ("CLOSED", "OPEN"), "Invalid closure status")
        _require(type(row["complete"]) is bool, "complete must be a boolean")
        _require(row.get("stockAvailable") is None or type(row["stockAvailable"]) is bool, "Invalid stockAvailable")
        units = row["observed"]
        _require(units is None or (type(units) is int and 0 <= units <= MAX_UNITS), "Invalid observed units")
        provenance = row["provenance"]
        _require(type(provenance) is dict and provenance.keys() == {"sourceId", "sha256"}
                 and _identifier(provenance["sourceId"]) and _sha256(provenance["sha256"]), "Invalid provenance")
        available = None if row["availableAt"] is None else _instant(row["availableAt"])
        if available is not None and row["closureStatus"] == "CLOSED":
            _require(available >= _start(month + 1), "Closed outcome available before the month ended")
        if row["closureStatus"] != "CLOSED" or not row["complete"]:
            reason = "MONTH_NOT_COMPLETE"
        elif units is None:
            reason = "OBSERVED_MISSING"
        elif available is None:
            reason = "AVAILABILITY_UNKNOWN"
        elif available > cutoff:
            reason = "AVAILABLE_AFTER_CUTOFF"
        else:
            reason = None
        indexed[month] = row, reason
    return indexed, target


def _window(indexed, target, count=None):
    """Read backwards without bridging gaps. With no count, return the valid suffix."""
    rows = []
    month = target - 1
    while count is None or len(rows) < count:
        row, reason = indexed.get(month, (None, "MONTH_MISSING"))
        if reason:
            return list(reversed(rows)), reason
        rows.append(row)
        month -= 1
    return list(reversed(rows)), None


def _sba(values, positives, alpha):
    first, second = positives[:2]
    size = values[first] + alpha * (values[second] - values[first])
    interval = second - first
    previous = second
    for i in positives[2:]:
        size += alpha * (values[i] - size)
        interval += alpha * (i - previous - interval)
        previous = i
    return (1 - alpha / 2) * size / interval


def _tsb(values, first, alpha, beta):
    probability, size = 1.0, values[first]
    for value in values[first + 1:]:
        probability += beta * ((1 if value > 0 else 0) - probability)
        if value > 0:
            size += alpha * (value - size)
    return probability * size


def forecast(request, method, **parameters):
    """Return a versioned result, with no inferred zero when history is unusable."""
    _validate_parameters(method, parameters)
    indexed, target = _history(request)
    value, reason, used = None, None, []
    if not indexed:
        reason = "NO_HISTORY"
    elif method in ("lag1", "seasonal_naive"):
        anchor = target - (12 if method == "seasonal_naive" else 1)
        row, reason = indexed.get(anchor, (None, "SEASONAL_ANCHOR_MISSING" if method == "seasonal_naive" else "MONTH_MISSING"))
        if reason is None:
            value, used = row["observed"], [row]
    elif method == "moving_average":
        window, reason = _window(indexed, target, parameters["k"])
        if reason is None:
            value, used = math.fsum(row["observed"] for row in window) / len(window), window
    else:
        window, stop_reason = _window(indexed, target)
        values = [row["observed"] for row in window]
        positives = [i for i, value in enumerate(values) if value > 0]
        if not window:
            reason = stop_reason
        elif len(positives) < (2 if method == "sba" else 1):
            reason = "INSUFFICIENT_POSITIVE_MONTHS"
        else:
            if method == "sba":
                value = _sba(values, positives, parameters["alpha"])
            else:
                value = _tsb(values, positives[0], parameters["alpha"], parameters["beta"])
            # The full suffix also establishes eligibility and absence of later occurrences.
            used = window
    if value is not None:
        _require(math.isfinite(value) and value >= 0, "Baseline produced an invalid forecast")
    return {
        **{key: request[key] for key in (*IDENTITY, "cutoffAt")},
        "method": method, "version": VERSION, "parameters": dict(parameters),
        "forecast": value, "status": "COVERED" if reason is None else "ABSTAINED",
        "abstentionReason": reason, "observationsUsed": deepcopy(used),
    }


def attach_to_cohort(cohort, emissions):
    """Project one baseline configuration into a copy of an M41-01 cohort.

    Each emission carries result, issuedAt and sourceId. The source must be
    registered in the cohort. Keep the original emissions for coverage audits.
    """
    result = deepcopy(cohort)
    _require(cohort.get("baselineId") is None, "Cohort already has a baseline")
    keyed = {}
    for row in result["rows"]:
        key = tuple(row[k] for k in IDENTITY)
        _require(key not in keyed, "Duplicate evaluation row")
        _require(row.get("baseline") is None and row.get("baselineIssuedAt") is None
                 and "baseline" not in row["provenance"], "Row already carries a baseline")
        keyed[key] = row
    identities, baseline_id = set(), None
    for emission in emissions:
        baseline = emission["result"]
        method, version, parameters = (baseline[k] for k in ("method", "version", "parameters"))
        _validate_parameters(method, parameters)
        _require(version == VERSION, "Unsupported baseline version")
        raw = json.dumps(parameters, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
        identity = f"{method}:{version}:{hashlib.sha256(raw).hexdigest()}"
        _require(baseline_id is None or baseline_id == identity, "One baseline configuration per cohort")
        baseline_id = identity
        key = tuple(baseline[k] for k in IDENTITY)
        _require(key in keyed and key not in identities, "Unmatched or duplicate baseline emission")
        identities.add(key)
        row = keyed[key]
        _require(row["status"] in ("COVERED", "ABSTAINED"), "Baseline emission for an ineligible row")
        cutoff = _instant(row["cutoffAt"])
        _require(_instant(baseline["cutoffAt"]) == cutoff, "Baseline cutoff does not match evaluation row")
        issued_at = _instant(emission["issuedAt"])
        _require(issued_at <= cutoff, "Baseline was issued after cutoff")
        source = emission["sourceId"]
        _require(_identifier(source) and _sha256(cohort["sources"].get(source)), "Unregistered baseline evidence")
        value = baseline["forecast"]
        if baseline["status"] == "ABSTAINED":
            _require(value is None and _identifier(baseline["abstentionReason"]), "Invalid baseline abstention")
            continue
        _require(baseline["status"] == "COVERED" and baseline["abstentionReason"] is None
                 and type(value) in (int, float) and 0 <= value <= MAX_UNITS, "Invalid baseline forecast")
        _require(all(_instant(obs["availableAt"]) <= issued_at for obs in baseline["observationsUsed"]),
                 "Baseline history was not available at issuance")
        row.update(baseline=value, baselineIssuedAt=emission["issuedAt"])
        row["provenance"]["baseline"] = source
    if baseline_id is not None:
        result["baselineId"] = baseline_id
    return result
