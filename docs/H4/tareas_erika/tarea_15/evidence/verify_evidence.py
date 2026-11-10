"""Comprueba integridad y consistencia del cierre acotado T15; no ajusta modelos."""
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
after = {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in before}
assert before == after
old = json.loads((ROOT/"docs/H4/tareas_erika/tarea_10/evidence/integrity_before.json").read_text())
assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in old.items())
folder = HERE/"data/escenarios_v1_1"
manifest = json.loads((folder/"manifest.json").read_text())
assert all(content_sha256((folder/n).read_bytes())==h for n,h in manifest["hashes"].items())
assert content_sha256((HERE/"catalog_reference.json").read_bytes())==manifest["catalog_snapshot_hash"]
assert content_sha256((HERE/"generate_synthetic.py").read_bytes())==manifest["generator_hash"]
raw = (HERE/"models/random_forest_candidate.joblib").read_bytes()
assert hashlib.sha256(raw).hexdigest()==V1_BINARY_SHA256
assert content_sha256(raw)==V1_NORMALIZED_SHA256
archived_run()
(OUT/"integrity_after.json").write_text(json.dumps(dict(protected_count=len(before),unchanged=True,
    files=after,dataset_manifest_verified=True,catalog_verified=True,generator_verified=True,
    v1_binary_and_normalized_verified=True,archived_candidate_verified=True,
    official_test_reevaluated=False,v1_retrained=False),indent=2),encoding="utf-8")
result = json.loads((OUT/"functional_validation.json").read_text(encoding="utf-8"))
assert result["normal_streamlit"]["activation"]["action"]=="ACTIVATE_V1"
assert result["normal_streamlit"]["activation"]["model"]["artifact_hash"]==V1_BINARY_SHA256
assert result["normal_streamlit"]["fit_calls"]==0
assert result["normal_streamlit"]["final_active"] is None
assert result["diagnostics_after"]["per_pair_rng"]["independent"] is True
assert result["diagnostics_after"]["manual_close"]["advance_disabled"] is True
matrix=json.loads((OUT/"matrix.json").read_text(encoding="utf-8"))
assert matrix["summary"]["changed_ids"]==["R17","R20","R69"]
assert matrix["summary"]["aplicables"]==68 and matrix["summary"]["total"]==73
methods=sum(isinstance(n,ast.FunctionDef) and n.name.startswith("test_")
            for f in HERE.glob("test_*.py") for n in ast.walk(ast.parse(f.read_text(encoding="utf-8-sig"))))
assert methods==394
log=(OUT/"full_tests.txt").read_bytes()
assert b"Ran 394 tests" in log and log.rstrip().endswith(b"OK")
for name in ("H4_TAREA_15_CORRECCIONES_FUNCIONALES.md","H4_GUIA_EJECUCION_WINDOWS.md",
             "H4_INFORME_FINAL.md","H4_MATRIZ_CUMPLIMIENTO.md"):
    path=relocated_path(ROOT/"docs/H4"/name)
    for link in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf-8")):
        if not link.startswith(("http:","https:")):
            assert (path.parent/link).exists(), link
(OUT/"audit_checks.json").write_text(json.dumps(dict(test_methods=methods,old_tests=375,new_tests=19,
    protected_unchanged=len(before),evidence_links_exist=True,changed_matrix_ids=["R17","R20","R69"]),indent=2),encoding="utf-8")
print(json.dumps(dict(protected_files=len(before),unchanged=True,tests=methods,links="OK",matrix=matrix["summary"])))
