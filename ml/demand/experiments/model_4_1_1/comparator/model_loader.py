"""Load only the locally pinned model and snapshot bytes."""

import hashlib
import io
import json
from pathlib import Path
import platform
import sys

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

EXPERIMENT = Path(__file__).resolve().parents[1]
DEMAND = EXPERIMENT.parents[1]
sys.path[:0] = [str(EXPERIMENT), str(DEMAND)]
from features.lag_features import DERIVED  # noqa: E402
from v2.scenario_data import FEATURES  # noqa: E402

RELEASE_PATH = DEMAND / "reports/v2/4.0.0/calendar-model-20261116-01/release.json"
RELEASE_SHA256 = "949c55733a6818bb93e97261c28f385ee3d2e3b0fcde6c42daa8dbe7d7dde00e"
EXPERIMENT_SHA256 = "7b0e108076294f8a18798b3e3c7745385a9b7ce24999c1f9b5c4e6bcbd0c1667"


def checked_bytes(path, digest):
    contents = path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != digest:
        raise ValueError(f"INTEGRITY_MISMATCH: {path.name}")
    return contents


def check_pipeline(pipeline, columns, params):
    if not isinstance(pipeline, Pipeline) or list(pipeline.feature_names_in_) != columns:
        raise ValueError("INCOMPATIBLE_FEATURE_ORDER")
    transform, forest = [step[1] for step in pipeline.steps]
    if (not isinstance(forest, RandomForestRegressor)
            or any(forest.get_params()[key] != value for key, value in params.items())):
        raise ValueError("INCOMPATIBLE_FOREST")
    numeric, category = transform.transformers_[:2]
    if (list(numeric[2]) != [column for column in columns if column != "categoryId"]
            or list(category[2]) != ["categoryId"]
            or numeric[1].strategy != "median" or not numeric[1].add_indicator
            or category[1].handle_unknown != "ignore"):
        raise ValueError("INCOMPATIBLE_PREPROCESSING")


def load_models():
    release = json.loads(checked_bytes(RELEASE_PATH, RELEASE_SHA256))
    experiment = json.loads(checked_bytes(EXPERIMENT / "evaluation/temporal-01.json", EXPERIMENT_SHA256))
    versions = {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__}
    if (sklearn.__version__ != release["versions"]["sklearn"]
            or versions["python"].split(".")[:2] != release["versions"]["python"].split(".")[:2]
            or versions != experiment["versions"]):
        raise ValueError("INCOMPATIBLE_LIBRARY_VERSIONS")
    if (release["datasetVersion"], release["modelVersion"], release["features"]) != (
        "4.0.0", "calendar-model-20261116-01", FEATURES
    ) or experiment["winner"] != "D" or experiment["status"] != "EXPERIMENTAL_NOT_ACTIVE":
        raise ValueError("INCOMPATIBLE_MODEL_IDENTITY")
    checked_bytes(EXPERIMENT / "features/lag_features.py", experiment["codeSha256"]["features"])
    snapshots = json.loads(checked_bytes(DEMAND / release["snapshots"], release["snapshotsSha256"]))
    original = checked_bytes(DEMAND / release["artifact"], release["artifactSha256"])
    candidate = experiment["artifact"]
    candidate_bytes = checked_bytes(EXPERIMENT / candidate["file"], candidate["sha256"])
    official = joblib.load(io.BytesIO(original))
    d = joblib.load(io.BytesIO(candidate_bytes))
    columns = FEATURES + DERIVED
    if d["featureOrder"] != columns or d["variant"] != "D" or d["status"] != "EXPERIMENTAL_NOT_ACTIVE":
        raise ValueError("INCOMPATIBLE_CANDIDATE")
    original_params = {**experiment["protocol"]["forest"], "random_state": 42}
    check_pipeline(official, FEATURES, original_params)
    check_pipeline(d["pipeline"], columns, {**original_params, **experiment["protocol"]["regularization"]})
    return release, snapshots, {
        "4.0.0": {"id": release["modelVersion"], "sha256": release["artifactSha256"],
                  "pipeline": official, "features": FEATURES},
        "4.1.1 C": {"id": "4.1.1-C", "sha256": None, "pipeline": None, "features": columns},
        "4.1.1 D": {"id": "4.1.1-temporal-01-D", "sha256": candidate["sha256"],
                    "pipeline": d["pipeline"], "features": columns},
    }, versions
