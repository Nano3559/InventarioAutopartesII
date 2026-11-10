"""R52: exportación de evidencia compatible. No hay importador de modelos.

h4-session-1 conserva nombres/tipos. h4-traceability-1 añade snapshots y
procedencia; SHA256 comprueba integridad, nunca autoriza operaciones.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path

from lifecycle_registry import canonical, digest, source_reference
from pair_contexts import contexts_for_export
from session_trace import utc_now
from simulator_inputs import HERE, InputError, parse_month, validate_quantity
from ui_runtime import model_info
from simulator_inputs import FEATURE_NAMES


def git_branch_at_export():
    """Lectura local; worktrees/detached HEAD no se convierten en ramas inventadas."""
    try:
        head = (HERE.parent.parent / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        prefix = "ref: refs/heads/"
        return head[len(prefix):] if head.startswith(prefix) else None
    except OSError:
        return None


def _check_binding(service, session_id, pair):
    if getattr(service, "session_id", session_id) != session_id:
        raise InputError("Servicio de exportación de otra sesión.")
    binding = getattr(service, "_lifecycle", None)
    if binding and (binding.session_id != session_id or binding.pair != pair):
        raise InputError("Servicio de exportación de otro par.")


def _context_snapshot(context, session_id, pair):
    provider = context.get("h4_runtime")
    if provider is None:
        references = dict(active=None, previous_references=None, verification="UNKNOWN_NO_PROVIDER")
    else:
        _check_binding(provider, session_id, pair)
        if callable(getattr(provider, "export_references", None)):
            references = provider.export_references()
        else:
            references = dict(active=provider.get_active_model(), previous_references=None,
                              verification="UNKNOWN_EXTERNAL_PROVIDER")
    training = context.get("retraining_session")
    runs = []
    if training is not None:
        _check_binding(training, session_id, pair)
        for run in training.export_runs():
            if (run["product_id"], run["location_id"]) != pair:
                raise InputError("Candidato registrado en otro par.")
            folder = Path(run["folder"])
            source = source_reference(run["run_id"], folder / "manifest.json", digest(run))
            for name, expected in run["files"].items():
                if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
                    raise InputError("Artefacto o datos de candidato alterados.")
            runs.append(dict(manifest=run, source=source, verification="VERIFIED_LOCAL_RUN"))
    current = context.get("retraining_result")
    if current is not None and (training is None or training.trusted_run(current["run_id"]) != current):
        raise InputError("Candidato visible fuera del registro de confianza.")
    comparison = context.get("candidate_comparison_session")
    evidence = []
    if comparison is not None:
        _check_binding(comparison, session_id, pair)
        evidence = comparison.export_evidence()
    reference_service = context.get("reference_comparison_session")
    reference_predictions = []
    if reference_service is not None:
        _check_binding(reference_service, session_id, pair)
        if reference_service.pair != pair:
            raise InputError("Emisiones REFERENCE de otro par.")
        reference_predictions = reference_service.export_evidence()
        visible = context.get("reference_comparison_result")
        if visible is not None and not any(r == visible for r in reference_predictions):
            raise InputError("Emisión REFERENCE ajena a su registro local.")
    return dict(product_id=pair[0], location_id=pair[1], references=references,
                current_candidate_id=current["run_id"] if current else None,
                candidates=runs, decisions=evidence, reference_predictions=reference_predictions,
                imported_comparison_is_authority=False)


def _check_sources(engine, journal, snapshot):
    if snapshot["journal_id"] != journal.session_id:
        raise InputError("Motor y diario pertenecen a sesiones distintas.")
    pair_states = {(p["product_id"], p["location_id"]): p for p in snapshot["pairs"]}
    for key, row in journal.closed.items():
        engine._reference.check_ids(*key[:2])
        parse_month(key[2])
        if key != row.forecast.key:
            raise InputError("Clave de cierre contradictoria.")
        validate_quantity(row.observed)
        if datetime.fromisoformat(row.observed_at) < datetime.fromisoformat(row.forecast.issued_at):
            raise InputError("Cierre anterior a la emisión.")
        if key in journal.pending:
            raise InputError("Mes simultáneamente pendiente y cerrado.")
        closure_events = [r for r in getattr(journal, "revisions", [])
                          if r["type"] == "OBSERVATION_CLOSED"
                          and (r["product_id"], r["location_id"], r["month"]) == key]
        if closure_events:
            original = closure_events[-1]
            if (original["forecast"] != asdict(row.forecast) or original["observed"] != row.observed
                    or original["observed_at"] != row.observed_at):
                raise InputError("Cierre alterado respecto a su revisión registrada.")
        if key[2] >= snapshot["first_simulable_month"]:
            pair = pair_states.get(key[:2])
            record = next((r for r in pair["closed_observations"] if r["month"] == key[2]), None) if pair else None
            if record is None or record["observed"] != row.observed:
                raise InputError("Cierres inconsistentes entre motor y diario.")
    for pair in snapshot["pairs"]:
        key_pair = pair["product_id"], pair["location_id"]
        for row in pair["closed_observations"]:
            key = (*key_pair, row["month"])
            if key not in journal.closed or journal.closed[key].observed != row["observed"]:
                raise InputError("Cierres inconsistentes entre motor y diario.")
            if row["source"] not in (None, "MANUAL", "GENERATED"):
                raise InputError("Procedencia de cierre inválida.")
            logged = [r for r in snapshot["revisions"] if r["type"] == "MONTH_CLOSED"
                      and (r["product_id"], r["location_id"], r["month_closed"]) == key]
            if logged and (logged[-1]["observed"] != row["observed"] or logged[-1]["source"] != row["source"]):
                raise InputError("Procedencia o cierre alterados respecto al motor.")
        pending_key = (*key_pair, pair["calendar"]["open_month"])
        if pending_key in journal.revealed and pending_key not in journal.closed:
            if pair["pending_observation"]["value"] != journal.revealed[pending_key]:
                raise InputError("Observado pendiente contradictorio.")
    for key, forecast in journal.pending.items():
        engine._reference.check_ids(*key[:2])
        parse_month(key[2])
        if key != forecast.key:
            raise InputError("Clave de emisión contradictoria.")
        issued = [r for r in getattr(journal, "revisions", []) if r["type"] == "FORECAST_ISSUED"
                  and (r["product_id"], r["location_id"], r["month"]) == key]
        if issued and issued[-1]["forecast"] != asdict(forecast):
            raise InputError("Emisión alterada respecto a su revisión registrada.")
    for forecast in [*journal.pending.values(), *(r.forecast for r in journal.closed.values())]:
        if forecast.model is not None:
            model_info(dict(**asdict(forecast.model), origin="SIMULACION", feature_names=list(FEATURE_NAMES)))
    for key, value in journal.revealed.items():
        if key not in journal.pending and key not in journal.closed:
            raise InputError("Observado revelado sin emisión.")
        if key in journal.closed and journal.closed[key].observed != value:
            raise InputError("Observado revelado y cierre contradictorios.")


def build_session_export(engine, journal, state=None, registry=None, archives=(), phase="CURRENT"):
    """Solo lecturas y verificaciones; no selecciona pares ni consume RNG."""
    snapshot = engine.export_state()
    _check_sources(engine, journal, snapshot)
    contexts = contexts_for_export(state or {}, engine.session_id)
    known_pairs = {(p["product_id"], p["location_id"]) for p in snapshot["pairs"]}
    if set(contexts) - known_pairs:
        raise InputError("Contexto sin par en el motor.")
    model_contexts = [_context_snapshot(contexts.get(pair, {}), engine.session_id, pair)
                      for pair in sorted(known_pairs)]
    lifecycle = None
    if registry is not None:
        if registry.session_id != engine.session_id:
            raise InputError("Registro de modelos de otra sesión.")
        registry.verify_sources()
        events = registry.records()
        if any((r["product_id"], r["location_id"]) not in known_pairs for r in events):
            raise InputError("Evento de otro par sin contexto de motor.")
        lifecycle = dict(session_id=registry.session_id, events=events,
                         head_sha256=events[-1]["event_sha256"] if events else "0"*64,
                         verification="VERIFIED_CHAIN_AND_SOURCES_AT_EXPORT")
    observations = []
    by_pair = {(p["product_id"], p["location_id"]): p for p in snapshot["pairs"]}
    for key, row in sorted(journal.closed.items()):
        pair = by_pair.get(key[:2])
        record = next((r for r in pair["closed_observations"] if r["month"] == key[2]), None) if pair else None
        observations.append(dict(product_id=key[0], location_id=key[1], month=key[2],
            observed=row.observed, source=record["source"] if record else None,
            provenance_status="KNOWN" if record and record["source"] else "UNKNOWN_NOT_RECORDED",
            consistency="ENGINE_AND_JOURNAL" if record else "LEGACY_JOURNAL_ONLY",
            observed_at=row.observed_at))
    prior = deepcopy(list(archives))
    for archive in prior:
        if archive.get("status") == "UNVERIFIED":
            continue
        verify_session_export(archive)
    captured_ids = {a["extensions"]["h4_traceability"]["engine"]["engine_session_id"]
                    for a in prior if a.get("status") != "UNVERIFIED"}
    historical_lifecycle = []
    for older in (state or {}).get("lifecycle_archives", []):
        if older.session_id in captured_ids or older.session_id == engine.session_id:
            continue
        # Registros T18 anteriores a la captura de snapshots R52: no inventar su diario/RNG.
        try:
            old_events = older.records()
            try:
                older.verify_sources()
                source_status = "VERIFIED_AT_EXPORT"
            except (InputError, OSError):
                source_status = "UNKNOWN_SOURCE_UNAVAILABLE_OR_CHANGED"
            historical_lifecycle.append(dict(session_id=older.session_id, events=old_events,
                head_sha256=old_events[-1]["event_sha256"] if old_events else "0"*64,
                sources=source_status, simulation_history="UNKNOWN_NOT_CAPTURED"))
        except (InputError, OSError, ValueError, KeyError):
            historical_lifecycle.append(dict(session_id=older.session_id, events=None,
                verification="UNVERIFIED", simulation_history="UNKNOWN_NOT_CAPTURED"))
    document = dict(schema_version="h4-session-1", origin="SIMULACION",
        session_id=journal.session_id, generator_seed=None,
        records=[asdict(row) for row in journal.closed.values()],
        extensions=dict(h4_traceability=dict(schema_version="h4-traceability-1",
            authority="EVIDENCE_ONLY", authorizes_model_changes=False,
            exported_at=utc_now(), snapshot_phase=phase,
            simulation_context=dict(id=engine.session_id, kind="DEMAND_SESSION",
                git_branch_at_export=git_branch_at_export(), parent_context_id=None,
                parent_context_status="UNKNOWN_NOT_RECORDED"),
            engine=snapshot, observations=observations,
            journal=dict(session_id=journal.session_id,
                pending=[asdict(f) for f in journal.pending.values()],
                revealed=[dict(product_id=k[0], location_id=k[1], month=k[2], observed=v)
                          for k, v in journal.revealed.items()],
                trace_started_at=getattr(journal, "trace_started_at", None),
                revisions=deepcopy(getattr(journal, "revisions", [])), history_before_tracking="UNKNOWN"),
            model_contexts=model_contexts, lifecycle=lifecycle, prior_sessions=prior,
            prior_lifecycle_only=historical_lifecycle,
            limitations=["No model restoration or promotion from JSON", "SHA256 is not an external signature",
                         "Latent demand omitted; simulation draws are not closed observations",
                         "Historical revisions before tracking are unknown"])))
    document["extensions"]["h4_traceability"]["document_sha256"] = digest(document)
    # JSON normalizado asegura que el snapshot no conserva referencias mutables.
    return json.loads(canonical(document))


def verify_session_export(document):
    """Comprueba bytes lógicos de evidencia; no devuelve modelos ni permisos."""
    candidate = deepcopy(document)
    try:
        trace = candidate["extensions"]["h4_traceability"]
        expected = trace.pop("document_sha256")
        if (candidate["schema_version"] != "h4-session-1"
                or trace["schema_version"] != "h4-traceability-1"
                or candidate["origin"] != "SIMULACION" or candidate["generator_seed"] is not None
                or not isinstance(candidate["records"], list) or digest(candidate) != expected):
            raise InputError("Exportación alterada o incompatible.")
    except (KeyError, TypeError, ValueError) as exc:
        raise InputError("Exportación alterada o incompatible.") from exc
    return True
