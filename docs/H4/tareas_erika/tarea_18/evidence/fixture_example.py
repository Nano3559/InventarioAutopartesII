"""Evidencia R49 de la política exclusiva de unittest; la app no importa esto."""
from pathlib import Path
import hashlib
import json
import sys
import uuid

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
sys.path.insert(0, str(ROOT / "ml/demand"))
from tests import test_demand_runtime as fixtures
from tests.test_model_comparison import FixturePromotionRuntime, review_for
from lifecycle_registry import LifecycleRegistry

fixture = fixtures.RuntimeTests()
fixture.setUp()
try:
    registry = LifecycleRegistry(uuid.uuid4().hex, Path(__file__).resolve().parent / "fixture_events")
    provider = FixturePromotionRuntime(fixture.root)
    provider.bind_lifecycle(registry.bind(1, 5))
    provider.promote_candidate(fixture, review_for(provider, fixture))
    verified = hashlib.sha256(fixture.path.read_bytes()).hexdigest() == provider.get_active_model()["artifact_hash"]
    provider.rollback("Cerrar demostración exclusiva de fixture R49.")
    result = dict(scope="ISOLATED_FIXTURE", fixture_artifact_verified=verified,
                  fixture_artifact_retained=False, registry_folder=str(registry.folder),
                  events=registry.records(), final_active=provider.get_active_model())
    with (registry.folder / "../fixture-summary-{}.json".format(registry.session_id)).resolve().open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(json.dumps(dict(session_id=registry.session_id, events=[r["type"] for r in result["events"]], final_active=result["final_active"])))
finally:
    fixture.doCleanups()
