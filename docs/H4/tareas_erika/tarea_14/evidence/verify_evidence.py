"""Verificaciones de consistencia del cierre, sin entrenamiento ni evaluación."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/"ml/demand"))
from simulator_inputs import HERE, content_sha256
sys.path.insert(0, str(ROOT / "docs/H4/tareas_erika"))
from document_paths import relocated_path
from demand_runtime import V1_BINARY_SHA256, V1_NORMALIZED_SHA256
from model_comparison import archived_run

before = json.loads((OUT/"integrity_before.json").read_text())
current = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in before}
changed = [n for n in before if current[n] != before[n]]
assert not changed, changed
frozen = json.loads((ROOT/"docs/H4/tareas_erika/tarea_10/evidence/integrity_before.json").read_text())
assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest() == h for n,h in frozen.items())
data = HERE/"data/escenarios_v1_1"
manifest = json.loads((data/"manifest.json").read_text())
assert all(content_sha256((data/n).read_bytes()) == h for n,h in manifest["hashes"].items())
assert content_sha256((HERE/"catalog_reference.json").read_bytes()) == manifest["catalog_snapshot_hash"]
assert content_sha256((HERE/"generate_synthetic.py").read_bytes()) == manifest["generator_hash"]
raw = (HERE/"models/random_forest_candidate.joblib").read_bytes()
assert hashlib.sha256(raw).hexdigest() == V1_BINARY_SHA256
assert content_sha256(raw) == V1_NORMALIZED_SHA256
archived_run()
(OUT/"integrity_after.json").write_text(json.dumps(dict(protected_count=len(before),
    changed=changed,unchanged=True,files=current,compared_with_task10=True,
    dataset_manifest_verified=True,catalog_verified=True,generator_verified=True,
    v1_binary_and_normalized_verified=True,archived_candidate_manifest_verified=True,
    interval_calibration_performed=False,official_test_evaluation_performed=False),indent=2),encoding="utf-8")
integral = json.loads((OUT/"integral.json").read_text(encoding="utf-8"))
assert integral["status"] == "PASS"
assert integral["inference_fit_calls"] == 0 and not integral["forbidden_fit_attempts"]
assert len(integral["fit_calls"]) == 1 and integral["fit_calls"][0]["n_rows"] == 6
assert len(integral["main_flow"]["months"]) == 12
assert len(integral["scenarios"]) == 8
assert all(r["status"] == "PASS" and len(r["months"]) == 6 for r in integral["scenarios"])
assert integral["diagnostics"]["per_pair_rng"]["independent"] is False
assert integral["diagnostics"]["manual_close"] == dict(complete_checkbox=False, closed_without_confirmation=True)
matrix = json.loads((OUT/"matrix.json").read_text(encoding="utf-8"))
for row in matrix["requirements"]:
    for column in ("archivos", "evidencia"):
        for path in row[column].split("; "):
            if path != "—":
                assert relocated_path(ROOT/path).exists(), (row["id"], path)
for path in (ROOT/"docs/H4/H4_INFORME_FINAL.md",ROOT/"docs/H4/H4_GUIA_EJECUCION_WINDOWS.md"):
    for link in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf-8")):
        if not link.startswith(("http:", "https:")):
            assert (path.parent/link).exists(), (path,link)
tests = sum(isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
            for f in HERE.glob("test_*.py") for n in ast.walk(ast.parse(f.read_text(encoding="utf-8-sig"))))
assert tests == 375
log = (OUT/"full_tests.txt").read_bytes()
assert b"Ran 375 tests" in log and log.rstrip().endswith(b"OK")
(OUT/"audit_checks.json").write_text(json.dumps(dict(matrix_evidence_files_exist=True,
    report_links_exist=True,test_methods=tests,integral_months=60,original_files_unchanged=len(before),
    main_flow="PASS",diagnostic_defects=["D01","D02"],visual_review="PENDING"),indent=2),encoding="utf-8")
print(json.dumps(dict(protected_files_unchanged=len(before),test_methods=tests,integral="PASS",
                     matrix=matrix["summary"],evidence_links="OK"),ensure_ascii=False))
