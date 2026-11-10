"""Contextos R21 en memoria de Streamlit; no es un registro ni un importador.

Las claves históricas de Ross son una vista del par seleccionado. Se guardan
y restauran al cambiar de par, sin copiar proveedores ni compartirlos entre
sesiones. El motor y ObservationJournal conservan la autoridad sobre datos.
"""

PAIR_KEYS = (
    "h4_runtime", "runtime_error", "v1_activation_reason", "v1_activation_error",
    "retraining_session", "retraining_result", "retraining_error",
    "candidate_comparison_session", "candidate_comparison_result",
    "candidate_rejection", "candidate_decision_error", "candidate_decision_reason",
    "candidate_rollback_notice", "comparison_report", "comparison_source",
    "comparison_upload_hash", "comparison_upload_error",
    "reference_comparison_session", "reference_comparison_result",
)


def bind_pair_context(state, session_id, product_id, location_id):
    """Enlaza únicamente pares ya validados por DemandSession.select()."""
    if state.get("pair_context_owner") != session_id:
        # Primera conexión admite proveedores locales inyectados por arneses.
        # Un motor nuevo nunca hereda referencias del propietario anterior.
        if "pair_context_owner" in state:
            for key in PAIR_KEYS:
                state.pop(key, None)
        state["pair_context_owner"] = session_id
        state["pair_contexts"] = {}
        state.pop("selected_pair_context", None)
    pair = (product_id, location_id)
    previous = state.get("selected_pair_context")
    if previous == pair:
        return
    contexts = state["pair_contexts"]
    if previous is not None:
        contexts[previous] = {k: state[k] for k in PAIR_KEYS if k in state}
        for key in PAIR_KEYS:
            state.pop(key, None)
    for key, value in contexts.get(pair, {}).items():
        state[key] = value
    contexts.setdefault(pair, {})
    state["selected_pair_context"] = pair


def clear_pair_contexts(state):
    for key in (*PAIR_KEYS, "pair_context_owner", "pair_contexts", "selected_pair_context"):
        state.pop(key, None)


def contexts_for_export(state, session_id):
    """La vista actual prevalece sobre el snapshot guardado al abandonar el par."""
    from simulator_inputs import InputError
    if state.get("pair_context_owner") not in (None, session_id):
        raise InputError("Contextos de otra sesión.")
    contexts = {pair: dict(value) for pair, value in state.get("pair_contexts", {}).items()}
    selected = state.get("selected_pair_context")
    if selected is not None:
        contexts[selected] = {key: state[key] for key in PAIR_KEYS if key in state}
    return contexts
