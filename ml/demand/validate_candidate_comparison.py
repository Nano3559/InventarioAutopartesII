"""Validación real optativa de Tarea 13. No entrena ni promueve candidatos.

Activa V1 temporalmente para comparar su inferencia y revierte al terminar.
Solo lee el candidato archivado auditado; escribe decisiones nuevas.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from unittest.mock import patch

from sklearn.ensemble import RandomForestRegressor
from demand_runtime import create_runtime
from model_comparison import ComparisonSession, archived_run
from simulator_inputs import HERE, InputError


def run():
    root = HERE.parent.parent
    out = root / "docs/H4/tareas_erika/tarea_13/evidence"
    out.mkdir(exist_ok=True)
    protected = json.loads((root/"docs/H4/tareas_erika/tarea_12/evidence/integrity.json").read_text())["files"]
    archive = archived_run()
    protected.update({str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in Path(archive["folder"]).iterdir() if p.is_file()})
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest() == h for n, h in protected.items())
    runtime = create_runtime()
    service = ComparisonSession(uuid.uuid4().hex)
    evidence = dict(session_id=service.session_id, before=runtime.get_active_model(),
                    timestamp=datetime.now(timezone.utc).isoformat())
    try:
        with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("FIT PROHIBIDO")) as fit:
            runtime.promote_v1("Tarea 13 autorizada: ACTIVE temporal para comparación técnica")
            evidence["comparison"] = service.compare_archived(runtime)
            evidence["rejection"] = service.reject(evidence["comparison"]["id"],
                                                    "Tres observaciones y seis filas de ajuste: evidencia insuficiente para promoción.")
            active_before = runtime.get_active_model()
            try:
                runtime.promote_candidate(evidence["comparison"]["ross_report"])
                raise AssertionError("La promoción real no debe estar habilitada")
            except InputError as exc:
                evidence["promotion_blocked"] = str(exc)
            assert runtime.get_active_model() == active_before
            fit.assert_not_called()
            evidence["fit_calls"] = fit.call_count
    finally:
        if runtime.get_active_model() is not None:
            runtime.rollback("Fin de validación Tarea 13: restaurar SIN ACTIVE")
        evidence["after"] = runtime.get_active_model()
        evidence["events"] = runtime.events
        evidence["protected_unchanged"] = all(hashlib.sha256((root/n).read_bytes()).hexdigest() == h for n, h in protected.items())
        evidence["protected_files"] = protected
        with (out / ("validation-"+service.session_id+".json")).open("x", encoding="utf-8") as handle:
            json.dump(evidence, handle, ensure_ascii=False, indent=2)
    assert evidence["protected_unchanged"]
    print(json.dumps(dict(session_id=service.session_id, comparison_id=evidence["comparison"]["id"],
                          eligibility=evidence["comparison"]["eligibility"],
                          metrics=evidence["comparison"]["metrics"]), indent=2))
    return evidence


if __name__ == "__main__":
    run()
