"""Administrator API bridge. Approved synthetic replay, no training or TEST."""
import json
import os
import sys

from v2.inference_v2_2 import FrozenDemandInference, InferenceError, strict_request
from v2.validate_build import month_offset


def query(payload):
    if type(payload) is not dict:
        raise InferenceError("INVALID_INPUT")
    catalog_action = payload == {"action": "catalog"}
    allowed = {"productId", "locationId", "targetMonth", "historySnapshotId"}
    if not catalog_action:
        if set(payload) - allowed or not {"productId", "locationId"} <= set(payload):
            raise InferenceError("INVALID_INPUT")
        if any(type(payload[k]) is not int or not 0 < payload[k] <= 2147483647 for k in ["productId", "locationId"]):
            raise InferenceError("INVALID_INPUT")
        if "historySnapshotId" in payload and "targetMonth" not in payload:
            raise InferenceError("INVALID_INPUT")
        if "targetMonth" in payload:
            import re
            if not isinstance(payload["targetMonth"], str) or not re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", payload["targetMonth"]):
                raise InferenceError("INVALID_INPUT")
        if "historySnapshotId" in payload:
            from v2.structure import token
            try:
                token(payload["historySnapshotId"])
            except ValueError:
                raise InferenceError("INVALID_INPUT") from None
    release = os.environ.get("DEMAND_RELEASE", "2.2.0")
    if release == "2.2.0":
        runtime = FrozenDemandInference()
        build, policy = "calibrated-20261115-01", "NONNEGATIVE_CONTINUOUS_1"
    elif release == "2.1.0":
        from v2.inference import FrozenDemandInference as RecoveryInference
        runtime = RecoveryInference()
        build, policy = "expanded-20261115-01", "NONNEGATIVE_V1"
    else:
        raise InferenceError("INCOMPATIBLE_ARTIFACT")
    common = dict(origin="SYNTHETIC", mode="ACADEMIC_REPLAY", version="V" + release,
        model="RandomForestRegressor", datasetVersion=release, buildId=build,
        selectionId=runtime.selection["selection_id"], artifactSha256=runtime.selection["artifact_sha256"], policyVersion=policy)
    months = sorted(set(runtime._features.mes_objetivo))
    if catalog_action:
        return dict(**common, catalogObservedAt=runtime.catalog["observed_at"], horizon=1,
            products=[p for p in runtime.catalog["products"] if p["id"] in runtime.catalog["included_product_ids"]],
            locations=[p for p in runtime.catalog["locations"] if p["type"] == "TIENDA"],
            availableTargetMonths=months, defaultTargetMonth=months[-1])
    pid, lid = payload["productId"], payload["locationId"]
    if pid not in runtime.catalog["included_product_ids"] or lid not in {p["id"] for p in runtime.catalog["locations"] if p["type"] == "TIENDA"}:
        raise InferenceError("UNKNOWN_ENTITY")
    month = payload.get("targetMonth", months[-1])
    request = runtime.request_for(pid, lid, month)
    if "historySnapshotId" in payload and request["historySnapshotId"] != payload["historySnapshotId"]:
        raise InferenceError("SNAPSHOT_MISMATCH")
    result = runtime.predict(request)
    if result["status"] != "OK":
        raise InferenceError(result["reason"])
    row = runtime._features.loc[[(pid, lid, month)]].iloc[0]
    history = [dict(month=month_offset(month, -n), units=int(row["ventas_mes_anterior" if n == 1 else f"ventas_hace_{n}_meses"])) for n in [3, 2, 1]]
    return {**result, **common, "baseline":history[-1]["units"], "history":history,
            "metrics":{k:result["evaluationContext"][k] for k in ["mae", "rmse", "r2"]}}


if __name__ == "__main__":
    try:
        print(json.dumps(query(strict_request(sys.stdin.read(8193))), ensure_ascii=True, allow_nan=False))
    except Exception as exc:
        print(json.dumps(dict(error=dict(code=exc.code if isinstance(exc, InferenceError) else "MODEL_UNAVAILABLE",
            message="No se pudo consultar la referencia V2 fijada."))))
        sys.exit(1)
