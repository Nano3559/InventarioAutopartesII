"""Publica una revisión nueva V2-07. Nunca modifica el dataset ni sus hashes."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v2.structure import ROOT, sha256_file, token
from v2.validate_build import inspect_build, read_table
from v2.scenario_checks import scenario_suite


def validate(build_id, run_id, root=ROOT):
    root=Path(root).resolve();token(build_id);token(run_id)
    build=root/"data/repuestopro_v2/2.0.0"/build_id
    destination=root/"reports/v2/2.0.0"/build_id/run_id
    if not destination.resolve().is_relative_to(root/"reports/v2"):
        raise ValueError("Reporte fuera de V2")
    destination.mkdir(parents=True,exist_ok=False)
    before={p.name:sha256_file(p) for p in build.iterdir() if p.is_file()}
    quality=inspect_build(build,root=root)
    preparation=json.loads((root/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
    fixtures=scenario_suite(preparation["scenario_design"])
    fixture_failures=[r["id"] for r in fixtures if not r["passed"]]
    statistics=quality.pop("statistics")
    manifest=json.loads((build/"manifest.json").read_text(encoding="utf-8"))
    observed=manifest["scenario_coverage"]["observed_ids"]
    unobserved=manifest["scenario_coverage"]["unexecuted_ids"]
    quality.update(policy_fixture_count=len(fixtures),policy_fixture_failures=fixture_failures,
        build_scenario_ids_observed=observed,build_scenario_ids_not_observed=unobserved,
        all_57_dynamic_generator_scenarios_validated=False,
        actual_backend_or_model_acceptance_tested=False,
        coverage_meaning="57 fixtures de decisiones por hechos y 8 combinaciones. No 57 simulaciones dinámicas del generador ni integración de backend.")
    quality["warnings"].extend([
        {"code":"PARTIAL_DYNAMIC_GENERATOR_COVERAGE","blocking_for_initial_variant_data_gate":False,
         "blocks_claim_of_full_dynamic_coverage":True,"observed_ids":len(observed),"unobserved_ids":len(unobserved)},
        {"code":"OBSERVED_SALES_ARE_STOCK_CENSORED","blocking":False,"reason":"No se estima demanda perdida."},
        {"code":"POLICY_FIXTURES_ARE_NOT_BACKEND_OR_MODEL_VERIFICATION","blocking":False,
         "reason":"Devoluciones, anulaciones y reposición se prueban como reglas offline. Su integración requiere revisión con Erika."}])
    passed=quality["status"]=="PASSED" and not fixture_failures
    quality["gate"]="PASSED_FOR_DATA_INTEGRITY_AND_OFFLINE_POLICY" if passed else "FAILED"
    quality["training_authorized"]=False
    schema=json.loads((build/"schema.json").read_text(encoding="utf-8"))
    rows=read_table(build/"dataset_supervisado.csv",schema["columns"])
    distributions=[]
    for name,start,end in [("TRAIN","2025-01","2026-03"),("VALIDATION","2026-04","2026-06")]:
        counts=Counter(r["target_ventas_mes"] for r in rows if start<=r["mes_objetivo"]<=end)
        distributions.extend(dict(partition=name,target_units=target,count=count) for target,count in sorted(counts.items()))
    with (destination/"distribuciones.csv").open("x",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["partition","target_units","count"],lineterminator="\n")
        writer.writeheader();writer.writerows(distributions)
    def write(name,data):
        with (destination/name).open("x",encoding="utf-8",newline="\n") as f:
            json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    write("estadisticas.json",{"scope":"TRAIN_AND_VALIDATION_ONLY_NO_TEST_TARGET_STATISTICS","sets":statistics})
    write("calidad.json",quality)
    write("scenario_policy_fixtures.json",{"purpose":"OFFLINE_CONTROLLED_FIXTURES_NOT_TRAINING_DATA","results":fixtures})
    if before!={p.name:sha256_file(p) for p in build.iterdir() if p.is_file()}:
        raise ValueError("El build cambió durante la revisión")
    closure=dict(stage="V2-07",run_id=run_id,build_id=build_id,recorded_at=datetime.now(timezone.utc).isoformat(),
        status=quality["gate"],scope="Dataset y política offline de la variante académica inicial. No aprobación comercial o de entrenamiento.",
        manifest_sha256=before["manifest.json"],input_files_sha256=before,
        validator_sha256={name:sha256_file(root/"v2"/name) for name in ["validate.py","validate_build.py","scenario_checks.py"]},
        report_files_sha256={p.name:sha256_file(p) for p in destination.iterdir() if p.is_file()},
        rows=quality["counts"],policy_cases_passed=sum(r["passed"] for r in fixtures),policy_cases_failed=fixture_failures,
        dynamic_generator_coverage_complete=False,model_accuracy_evaluated=False,
        dataset_unchanged=True,training_performed=False,training_authorized=False,
        raw_used=False,neon_used=False,new_markdown_files=0,
        pending=["Cobertura dinámica de variantes y respuestas predictivas en experimentos futuros, sin afirmar 57 casos simulados por este build",
                 "Tratamiento o exclusión de antiguedad_tipo_cambio_dias constante en TRAIN, mediante una variante identificada",
                 "Scalers y codificadores solo se ajustarán en TRAIN al autorizar experimentos",
                 "V2-09B revisión de contrato con Erika y verificación de backend",
                 "Validación comercial con historia propia certificada"],
        next_step="Planificar V2-08 con las limitaciones de esta variante. No iniciar entrenamiento automáticamente.")
    write("closure.json",closure)
    return destination,closure


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-id",required=True);parser.add_argument("--run-id",required=True)
    args=parser.parse_args();path,result=validate(args.build_id,args.run_id)
    print(json.dumps({"path":str(path),"status":result["status"],"policy_cases_passed":result["policy_cases_passed"],
                      "training_authorized":False},ensure_ascii=True))
    sys.exit(result["status"]!="PASSED_FOR_DATA_INTEGRITY_AND_OFFLINE_POLICY")
