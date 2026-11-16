"""Frozen V2.1 inference contract. Local approved VALIDATION replay, no API switch."""
import csv
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v2.alternatives import AlternativeForecaster
from v2.preprocessing import RAW, CONTEXT, DemandPreprocessor, load_feature_partition, validate_frame, read_context
from v2.structure import ROOT, sha256_file
from v2.validate_build import canonical_hash, cutoff, instant, month_offset

VERSION = "v2-inference-2.1-1"
SELECTION_SHA256 = "e4881d38ec32a087904d499fc122e14953cc23946b0c4123e6ce15630ee9f3e0"
CONTRACT_SHA256 = "002a9ce65e8e40e3a1358b954ee2906455659a7ba5a0e9a19a19ca9743ff9207"
BUILD = "data/repuestopro_v2/2.1.0/expanded-20261115-01"
REPORT = "reports/v2/2.1.0/expanded-20261115-01/final_test/result.json"
GATE = "reports/v2/2.1.0/expanded-20261115-01/validation-20261115-01/calidad.json"


class InferenceError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def verified(path, expected):
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise InferenceError("MODEL_UNAVAILABLE") from exc
    if sha256(data).hexdigest() != expected:
        raise InferenceError("INCOMPATIBLE_ARTIFACT")
    return data


def validate_request(request):
    keys = {"contractVersion", "productId", "locationId", "targetMonth", "historySnapshotId"}
    if type(request) is not dict or set(request) != keys or request["contractVersion"] != VERSION:
        raise InferenceError("INVALID_INPUT")
    if any(type(request[k]) is not int or not 0 < request[k] <= 2147483647 for k in ["productId", "locationId"]):
        raise InferenceError("INVALID_INPUT")
    try:
        if not isinstance(request["targetMonth"], str) or not re.fullmatch(r"[1-9][0-9]{3}-(0[1-9]|1[0-2])", request["targetMonth"]):
            raise ValueError("month")
        month_offset(request["targetMonth"], 0)
        if not isinstance(request["historySnapshotId"], str):
            raise ValueError("snapshot")
        from v2.structure import token
        token(request["historySnapshotId"])
    except (TypeError, ValueError):
        raise InferenceError("INVALID_INPUT") from None


def snapshot_hash(row, key, meta):
    return canonical_hash(dict(key=list(key), metadata=meta,
        values={n:None if pd.isna(row[n]) else float(row[n]) for n in RAW}))


class FrozenDemandInference:
    """Trusted local provider. Requests cannot submit features, paths or models."""
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.contract = json.loads(verified(self.root / "v2/contracts/inference.v2_1.json", CONTRACT_SHA256))
        self.selection = json.loads(verified(self.root / "v2/contracts/selection.v2_1.json", SELECTION_SHA256))
        s = self.selection
        for name, digest in s["input_hashes"].items():
            path = (self.root / name).resolve()
            if not path.is_relative_to(self.root):
                raise InferenceError("INCOMPATIBLE_ARTIFACT")
            verified(path, digest)
        for package, expected in s["environment"].items():
            if version(package) != expected:
                raise InferenceError("INCOMPATIBLE_ARTIFACT")
        self.catalog = json.loads(verified(self.root / BUILD / "catalog_reference.json", self.contract["catalog_sha256"]))
        verified(self.root / GATE, self.contract["approved_gate_sha256"])
        self.evaluation = json.loads(verified(self.root / REPORT, self.contract["frozen_test_report_sha256"]))
        if self.evaluation["artifact_sha256"] != s["artifact_sha256"]:
            raise InferenceError("INCOMPATIBLE_ARTIFACT")
        from sklearn.ensemble import RandomForestRegressor
        with patch.object(AlternativeForecaster, "fit", side_effect=AssertionError("Inference forbids fit")), \
             patch.object(DemandPreprocessor, "fit", side_effect=AssertionError("Inference forbids fit")), \
             patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("Inference forbids fit")):
            self.model = joblib.load(BytesIO(verified(self.root / s["artifact"], s["artifact_sha256"])))
        if type(self.model) is not AlternativeForecaster or self.model.spec != s["model_spec"]:
            raise InferenceError("INCOMPATIBLE_ARTIFACT")
        self._check_model()
        self._features = load_feature_partition("VALIDATION", root=self.root)
        self._metadata = {}
        # Do not interpret TEST labels or TEST feature values.
        with (self.root / BUILD / "dataset_supervisado.csv").open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if not "2026-04" <= row["mes_objetivo"] <= "2026-06":
                    continue
                key = (int(row["productId"]), int(row["locationId"]), row["mes_objetivo"])
                if key in self._metadata or row["quality_status"] != "TRAINABLE" or instant(row["feature_cutoff_at"]) != cutoff(row["mes_objetivo"]):
                    raise InferenceError("UNAVAILABLE_REQUIRED_FEATURE")
                self._metadata[key] = dict(snapshot=row["history_snapshot_id"], cutoff=row["feature_cutoff_at"])
        if set(self._metadata) != set(self._features.index):
            raise InferenceError("UNAVAILABLE_REQUIRED_FEATURE")
        self._fingerprints = {k:snapshot_hash(self._features.iloc[i], k, self._metadata[k]) for i,k in enumerate(self._features.index)}
        _, _, self._fields, _, _, _ = read_context(self.root)

    def _check_model(self):
        s = self.selection
        state = self.model.preprocessor_.to_state()
        if state["sha256"] != s["preprocessing_state_sha256"] or state["state"]["columns"] != s["features"] or self.model.model_.get_params() != s["regressor_parameters"]:
            raise InferenceError("INCOMPATIBLE_ARTIFACT")
        if self.model.train_end_ != "2026-03" or state["state"]["fit_rows"] != 2520:
            raise InferenceError("INCOMPATIBLE_ARTIFACT")

    def request_for(self, product_id, location_id, month):
        """Local test/demo helper. No target or user-supplied historical values."""
        meta = self._metadata.get((product_id, location_id, month))
        if meta is None:
            raise InferenceError("UNAVAILABLE_REQUIRED_FEATURE")
        return dict(contractVersion=VERSION, productId=product_id, locationId=location_id,
                    targetMonth=month, historySnapshotId=meta["snapshot"])

    def predict(self, request):
        validate_request(request)
        self._check_model()
        verified(self.root / self.selection["artifact"], self.selection["artifact_sha256"])
        key = (request["productId"], request["locationId"], request["targetMonth"])
        response = dict(status="ABSTAINED", contractVersion=VERSION, productId=key[0], locationId=key[1],
            targetMonth=key[2], issuedAt=datetime.now(timezone.utc).isoformat(), historyCutoff=cutoff(key[2]).isoformat(),
            horizonMonths=1, prediction=None, modelVersion=self.selection["selection_id"], datasetVersion="2.1.0",
            buildId="expanded-20261115-01", historySnapshotId=request["historySnapshotId"], origin="SYNTHETIC",
            mode="ACADEMIC_REPLAY", selectionId=self.selection["selection_id"], artifactSha256=self.selection["artifact_sha256"],
            policyVersion="NONNEGATIVE_V1", warnings=["DATOS_SINTETICOS_NO_VALIDA_VENTAS_REALES", "NO_REPOSICION_AUTOMATICA", "PEDIDOS_EXTRAORDINARIOS_NO_INCLUIDOS"],
            evaluationContext=dict(origin="SYNTHETIC", split="TEST", **{k:self.evaluation["model_metrics"][k] for k in ["mae", "rmse", "r2"]}))
        if key[0] not in self.catalog["included_product_ids"] or key[1] not in {r["id"] for r in self.catalog["locations"] if r["type"]=="TIENDA"}:
            return {**response, "reason":"UNKNOWN_ENTITY"}
        meta = self._metadata.get(key)
        if meta is None or meta["snapshot"] != request["historySnapshotId"]:
            return {**response, "reason":"UNAVAILABLE_REQUIRED_FEATURE"}
        frame = self._features.loc[[key]].copy(deep=True)
        fingerprint = snapshot_hash(frame.iloc[0], key, meta)
        if fingerprint != self._fingerprints[key]:
            raise InferenceError("UNAVAILABLE_REQUIRED_FEATURE")
        validate_frame(frame, self._fields)
        if meta["cutoff"] != cutoff(key[2]).isoformat():
            # Equivalent timestamp offsets are valid, compare instants.
            if instant(meta["cutoff"]) != cutoff(key[2]):
                return {**response, "reason":"UNAVAILABLE_REQUIRED_FEATURE"}
        before = self.model.preprocessor_.to_state()
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        with patch.object(AlternativeForecaster, "fit", side_effect=AssertionError("No inference training")), \
             patch.object(DemandPreprocessor, "fit", side_effect=AssertionError("No inference training")), \
             patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("No inference training")), \
             patch.object(StandardScaler, "fit", side_effect=AssertionError("No inference training")):
            raw = np.asarray(self.model.predict(frame))
        if before != self.model.preprocessor_.to_state():
            raise InferenceError("INCOMPATIBLE_ARTIFACT")
        if raw.shape != (1,) or not np.issubdtype(raw.dtype, np.number) or np.iscomplexobj(raw) or not np.isfinite(raw).all():
            return {**response, "reason":"MODEL_UNAVAILABLE"}
        value = float(raw[0])
        if value < 0:
            response["warnings"].append("NEGATIVE_PREDICTION_CLIPPED")
        response.update(status="OK", prediction=max(0.0, value), featureSnapshotSha256=fingerprint,
                        historyCutoff=meta["cutoff"])
        json.dumps(response, allow_nan=False)
        return response


def strict_request(text):
    def pairs(values):
        out = {}
        for key, value in values:
            if key in out:
                raise ValueError("Duplicate key")
            out[key] = value
        return out
    def invalid(value):
        raise ValueError("Nonfinite JSON")
    try:
        if len(text) > 8192:
            raise ValueError("Oversized request")
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, TypeError):
        raise InferenceError("INVALID_INPUT") from None


if __name__ == "__main__":
    try:
        request = strict_request(sys.stdin.read(8193))
        validate_request(request)
        print(json.dumps(FrozenDemandInference().predict(request), allow_nan=False))
    except Exception as exc:
        print(json.dumps(dict(error=dict(code=exc.code if isinstance(exc, InferenceError) else "MODEL_UNAVAILABLE", message="No se pudo consultar la referencia V2 fijada."))))
        sys.exit(1)
