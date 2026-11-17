"""Project one pinned DEMO snapshot onto the two training schemas."""

from datetime import datetime
from math import isfinite

from model_loader import FEATURES
from features.lag_features import LAGS, lag_features
from v2.scenario_data import NUMERIC, frame


def select_snapshot(snapshots, month, product_id=None, location_id=None, snapshot_id=None):
    if snapshot_id is None and (product_id is None or location_id is None or month is None):
        raise ValueError("Indica el snapshot o producto, tienda y mes")
    matching = [
        entry for key, entry in snapshots.items()
        if (snapshot_id is None or key == snapshot_id)
        and (month is None or entry["targetMonth"] == month)
        and (product_id is None or entry["productId"] == product_id)
        and (location_id is None or entry["locationId"] == location_id)
    ]
    if len(matching) != 1:
        raise ValueError("SNAPSHOT_MISMATCH_OR_UNAVAILABLE")
    return matching[0]


def prior_months(month):
    target = datetime.strptime(month, "%Y-%m")
    index = target.year * 12 + target.month - 1
    offsets = (index - delta for delta in (3, 2, 1))
    return [f"{i // 12:04d}-{i % 12 + 1:02d}" for i in offsets]


def adapt(snapshot):
    values = snapshot["features"]
    if set(values) != set(FEATURES) or not isinstance(values["categoryId"], str) or not values["categoryId"]:
        raise ValueError("INCOMPATIBLE_SNAPSHOT_FEATURES")
    for key in NUMERIC:
        value = values[key]
        if value != "" and (isinstance(value, bool) or not isfinite(float(value))):
            raise ValueError("INVALID_SNAPSHOT_VALUE")
    x = frame([values])
    history = snapshot.get("history", [])
    required = prior_months(snapshot["targetMonth"])
    if (len(history) != 3 or [row["mes"] for row in history] != required
            or any(values[key] == "" for key in LAGS)):
        return x, None, "UNAVAILABLE_REQUIRED_FEATURE"
    for row, feature in zip(history, LAGS):
        components = [row[key] for key in ("unidades_por_menor", "unidades_por_mayor", "unidades_modalidad_desconocida")]
        if any(type(value) is not int or value < 0 for value in components) or sum(components) != float(values[feature]):
            raise ValueError("INCONSISTENT_SNAPSHOT_HISTORY")
    return x, lag_features(x), None


def outside_range(snapshot, bounds):
    return [key for key in NUMERIC if snapshot["features"][key] != ""
            and not bounds[key][0] <= float(snapshot["features"][key]) <= bounds[key][1]]
