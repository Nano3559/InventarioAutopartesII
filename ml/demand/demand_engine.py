"""Motor de simulación H4: escenarios, reloj, lags y observados de sesión."""
import hashlib
import random
import uuid
from dataclasses import dataclass, field
from copy import deepcopy
import platform

from session_trace import append_revision, utc_now

from simulator_inputs import (
    InputError, SCENARIOS, load_reference, offset_month, parse_month,
    validate_quantity,
)

SESSION_SEED = 42

SCENARIO_PRELOADS = {
    "NORMAL": (10, 10, 10),
    "CRECIMIENTO": (8, 12, 17),
    "CAÍDA": (17, 12, 8),
    "PICO MAYORISTA": (10, 10, 10),
    "STOCKOUT": (10, 10, 10),
    "PRODUCTO NUEVO": (None, None, None),
    "CAMBIO PERSISTENTE": (10, 10, 10),
    "RECUPERACIÓN": (4, 6, 8),
}

_reference_cache = None


def _get_reference():
    global _reference_cache
    if _reference_cache is None:
        _reference_cache = load_reference()
    return _reference_cache


@dataclass
class PairState:
    open_month: str
    scenario: str = "NORMAL"
    simulated_only: bool = False
    closed: dict = field(default_factory=dict)
    pending_observed: int | None = None
    pending_stockout: dict | None = None
    generation_cache: dict = field(default_factory=dict)
    lags_draft: tuple | None = None
    pending_source: str | None = None
    closed_sources: dict = field(default_factory=dict)
    rng: random.Random | None = field(default=None, repr=False)


class DemandSession:
    """Sesión aislada por producto-tienda con reloj, azar y escenario propios."""

    def __init__(self, reference=None, seed=SESSION_SEED):
        self.session_id = uuid.uuid4().hex
        self.seed = seed
        self._reference = reference if reference is not None else _get_reference()
        self._pairs = {}
        self._selected = None
        self._viewing_month = None
        self._first_simulable = offset_month(self._reference.months[-1], 1)
        self._journal_id = None
        self._trace_started_at = utc_now()
        self._revisions = []

    def _record_revision(self, kind, **details):
        append_revision(self._revisions, kind, self._selected, self._viewing_month, **details)

    def export_state(self):
        """Snapshot no mutante de todos los pares; no serializa objetos ejecutables."""
        pairs = []
        for (product, location), state in sorted(self._pairs.items()):
            rng = state.rng.getstate() if state.rng is not None else None
            material = f"H4_PAIR_RNG_V1|{self.seed}|{product}|{location}".encode("utf-8")
            history = {} if state.simulated_only else {
                month: value for (p, l, month), value in self._reference.history.items()
                if (p, l) == (product, location)}
            initial_history = [dict(month=m, value=v, origin="HISTORICAL_SYNTHETIC_1_1_REFERENCE")
                               for m, v in sorted(history.items())]
            history.update(state.closed)
            chronological_lags = [history.get(offset_month(state.open_month, -lag)) for lag in (3, 2, 1)]
            pairs.append(dict(product_id=product, location_id=location,
                scenario=state.scenario, simulated_only=state.simulated_only,
                calendar=dict(open_month=state.open_month,
                    viewing_month=self._viewing_month if (product, location) == self._selected else None,
                    closed_months=sorted(state.closed)),
                hypothetical_lags=deepcopy(state.lags_draft),
                reference_history_for_simulation=initial_history,
                effective_lags_for_open_month=list(state.lags_draft) if state.lags_draft is not None else chronological_lags,
                closed_observations=[dict(month=m, observed=v, source=state.closed_sources.get(m))
                                     for m, v in sorted(state.closed.items())],
                pending_observation=dict(value=state.pending_observed, source=state.pending_source),
                rng=dict(algorithm="python.random.Random/MT19937", python_version=platform.python_version(),
                    seed_derivation="H4_PAIR_RNG_V1|seed|product_id|location_id",
                    pair_seed_sha256=hashlib.sha256(material).hexdigest(),
                    state_version=rng[0] if rng else None,
                    internal_state=list(rng[1]) if rng else None, gauss_next=rng[2] if rng else None),
                cached_generated_results=[dict(month=m, simulated_observed=r["observed"],
                    availability=r.get("availability"), classification="SIMULATION_DRAW_NOT_CLOSED_SALES")
                    for m, r in sorted(state.generation_cache.items())]))
        return deepcopy(dict(engine_session_id=self.session_id, journal_id=self._journal_id,
            generator_seed=self.seed, selected_pair=self._selected,
            first_simulable_month=self._first_simulable, origin="SIMULACION", pairs=pairs,
            trace_started_at=getattr(self, "_trace_started_at", None),
            revisions=getattr(self, "_revisions", []), history_before_tracking="UNKNOWN"))

    def bind_journal(self, journal_id):
        """Vincula la identidad del diario sin compartir estado entre sesiones."""
        if self._journal_id is not None and self._journal_id != journal_id:
            raise InputError("El diario pertenece a otra sesión.")
        self._journal_id = journal_id

    def export_closed(self):
        """Copia de cierres nuevos del par seleccionado; no incluye latentes."""
        state = self._pair_state()
        product, location = self._selected
        return {
            "session_id": self.session_id, "journal_id": self._journal_id,
            "seed": self.seed, "product_id": product, "location_id": location,
            "scenario": state.scenario, "origin": "SIMULACION",
            "records": [dict(month=month, observed=value,
                             source=state.closed_sources.get(month))
                        for month, value in sorted(state.closed.items())],
        }

    def select(self, product_id, location_id):
        self._reference.check_ids(product_id, location_id)
        self._selected = (product_id, location_id)
        state = self._pair_state()
        self._viewing_month = state.open_month

    def select_month(self, month):
        parse_month(month)
        self._require_selection()
        if month not in self.selectable_months():
            raise InputError("MES NO DISPONIBLE en esta simulación.")
        self._viewing_month = month

    def selectable_months(self):
        state = self._pair_state()
        months = []
        month = self._reference.months[0]
        while month <= state.open_month:
            months.append(month)
            month = offset_month(month, 1)
        return tuple(months)

    def _combined_value(self, month):
        product, location = self._selected
        state = self._pairs.get(self._selected)
        if state is not None and month in state.closed:
            return state.closed[month]
        if state is not None and state.simulated_only:
            return None
        return self._reference.history.get((product, location, month))

    def recent_history(self):
        self._require_selection()
        month = self._viewing_month
        return tuple(
            (offset_month(month, -lag), self._combined_value(offset_month(month, -lag)))
            for lag in (3, 2, 1)
        )

    def history_series(self):
        self._require_selection()
        product, location = self._selected
        state = self._pairs.get(self._selected)
        months = set()
        if state is None or not state.simulated_only:
            months.update(
                m for (p, l, m) in self._reference.history
                if p == product and l == location
            )
        if state is not None:
            months.update(state.closed)
        return tuple((m, self._combined_value(m)) for m in sorted(months))

    def history_status(self):
        values = [value for _, value in self.recent_history()]
        present = sum(value is not None for value in values)
        state = self._pair_state()
        if present == 3:
            return "COMPLETO"
        if state.simulated_only or present == 0:
            return "HISTORIAL INSUFICIENTE"
        return "DATOS INCOMPLETOS"

    def lags(self):
        state = self._pair_state()
        month = self._viewing_month
        if (state.lags_draft is not None and month == state.open_month
                and month not in state.closed):
            return state.lags_draft
        return tuple(value for _, value in self.recent_history())

    def edit_lags(self, lag3, lag2, lag1):
        state = self._pair_state()
        if self._viewing_month != state.open_month:
            raise InputError("La edición aplica al mes abierto de simulación.")
        if state.open_month in state.closed:
            raise InputError("El mes ya está cerrado. Sus entradas no se editan.")
        before = state.lags_draft
        state.lags_draft = (
            validate_quantity(lag3),
            validate_quantity(lag2),
            validate_quantity(lag1),
        )
        if before != state.lags_draft:
            self._record_revision("HYPOTHETICAL_LAGS_EDITED", before=before, after=state.lags_draft)

    def reset_lags(self):
        state = self._pair_state()
        if state.open_month in state.closed:
            raise InputError("El mes ya está cerrado. Sus entradas no se editan.")
        before = state.lags_draft
        state.lags_draft = None
        if before is not None:
            self._record_revision("HYPOTHETICAL_LAGS_RESET", before=before, after=None)

    def apply_scenario(self, scenario):
        if scenario not in SCENARIOS:
            raise InputError("ESCENARIO INVÁLIDO.")
        state = self._pair_state()
        if state.closed or state.pending_observed is not None:
            raise InputError(
                "Cambia de escenario solo antes de cerrar o generar. "
                "Restablece la simulación para otra hipótesis."
            )
        before = dict(scenario=state.scenario, hypothetical_lags=state.lags_draft,
                      cached_months=sorted(state.generation_cache))
        state.scenario = scenario
        state.simulated_only = scenario == "PRODUCTO NUEVO"
        state.lags_draft = SCENARIO_PRELOADS[scenario]
        state.generation_cache.clear()
        state.pending_stockout = None
        after = dict(scenario=state.scenario, hypothetical_lags=state.lags_draft, cached_months=[])
        if before != after:
            self._record_revision("SCENARIO_APPLIED", before=before, after=after)

    def _ensure_open(self):
        state = self._pair_state()
        if state.open_month in state.closed:
            raise InputError("El mes ya está cerrado.")
        return state

    def generate_observed(self):
        state = self._ensure_open()
        if state.pending_observed is not None:
            return state.pending_observed
        detail = self._generate_cached(state, state.open_month)
        state.pending_observed = detail["observed"]
        state.pending_source = "GENERATED"
        if detail.get("latent") is not None:
            state.pending_stockout = detail
        self._record_revision("OBSERVED_GENERATED", value=state.pending_observed, source="GENERATED")
        return state.pending_observed

    def set_manual_observed(self, value):
        validate_quantity(value)
        state = self._ensure_open()
        before = (state.pending_observed, state.pending_source)
        if state.scenario == "STOCKOUT":
            detail = self._generate_cached(state, state.open_month)
            if value > detail["availability"]:
                raise InputError(
                    "La venta manual supera la disponibilidad declarada. "
                    "Corrige el resultado o el supuesto de disponibilidad."
                )
            state.pending_stockout = {**detail, "observed": value}
        state.pending_observed = value
        state.pending_source = "MANUAL"
        if before != (value, "MANUAL"):
            self._record_revision("OBSERVED_MANUAL", before=before, value=value, source="MANUAL")

    def pending_observed(self):
        return self._pair_state().pending_observed

    def generation_detail(self):
        return self._pair_state().pending_stockout

    def observation_source(self):
        return self._pair_state().pending_source

    def validate_close_month(self, *, complete=True):
        """Preflight sin mutaciones. Una llamada directa de cierre confirma por defecto
        el total mensual; las fronteras UI deben pasar su confirmación explícita.
        No exige predicción ni tres lags: una abstención con observado puede cerrar.
        """
        state = self._pair_state()
        month = state.open_month
        if month in state.closed:
            raise InputError("El mes ya está cerrado. No se duplica el observado.")
        if state.pending_observed is None:
            raise InputError(
                "Sin resultado no se cierra. Genera o registra el observado primero."
            )
        if complete is not True:
            raise InputError("MES INCOMPLETO: confirma que la venta observada corresponde al mes completo antes de cerrar o avanzar.")
        validate_quantity(state.pending_observed)
        if state.pending_source not in ("MANUAL", "GENERATED"):
            raise InputError("El observado no tiene una procedencia válida.")

    def close_month(self, *, complete=True):
        self.validate_close_month(complete=complete)
        state = self._pair_state()
        month = state.open_month
        state.closed[month] = state.pending_observed
        state.closed_sources[month] = state.pending_source
        self._record_revision("MONTH_CLOSED", month_closed=month,
                              observed=state.pending_observed, source=state.pending_source)
        state.pending_observed = None
        state.pending_source = None
        state.pending_stockout = None
        state.lags_draft = None

    def advance_month(self):
        state = self._pair_state()
        month = state.open_month
        if month not in state.closed:
            raise InputError("Cierra el mes antes de avanzar el reloj.")
        state.open_month = offset_month(month, 1)
        self._record_revision("MONTH_ADVANCED", before=month, after=state.open_month)
        if self._viewing_month == month:
            self._viewing_month = state.open_month

    def status(self):
        result = {
            "session_id": self.session_id,
            "seed": self.seed,
            "origin": "SIMULACION",
            "product_id": None,
            "location_id": None,
            "scenario": None,
            "open_month": None,
            "viewing_month": None,
            "history_status": None,
            "lags": None,
            "pending_observed": None,
            "closed_months": (),
        }
        if self._selected is None:
            return result
        state = self._pair_state()
        result.update({
            "product_id": self._selected[0],
            "location_id": self._selected[1],
            "scenario": state.scenario,
            "open_month": state.open_month,
            "viewing_month": self._viewing_month,
            "history_status": self.history_status(),
            "lags": self.lags(),
            "pending_observed": state.pending_observed,
            "closed_months": tuple(sorted(state.closed)),
        })
        return result

    def is_closed(self, month):
        parse_month(month)
        return month in self._pair_state().closed

    def closed_months(self):
        return tuple(sorted(self._pair_state().closed))

    def reset(self):
        self._record_revision("ENGINE_RESET", affected_pairs=sorted(self._pairs))
        self._pairs.clear()
        self._selected = None
        self._viewing_month = None

    def _require_selection(self):
        if self._selected is None:
            raise InputError("Selecciona primero un producto y una tienda.")

    def _pair_state(self):
        self._require_selection()
        key = self._selected
        if key not in self._pairs:
            # No usar hash() (varía entre procesos) ni UUID (rompe reproducción).
            # La seed de sesión + IDs da un flujo estable e independiente por par.
            material = f"H4_PAIR_RNG_V1|{self.seed}|{key[0]}|{key[1]}".encode("utf-8")
            pair_seed = int.from_bytes(hashlib.sha256(material).digest(), "big")
            self._pairs[key] = PairState(open_month=self._first_simulable,
                                         rng=random.Random(pair_seed))
        return self._pairs[key]

    def _effective_lags(self, state, month):
        if (state.lags_draft is not None and month == state.open_month
                and month not in state.closed):
            return state.lags_draft
        return tuple(
            self._combined_value(offset_month(month, -lag))
            for lag in (3, 2, 1)
        )

    def _generate_cached(self, state, month):
        if month not in state.generation_cache:
            state.generation_cache[month] = self._generate(state, month)
            self._record_revision("SIMULATION_DRAW_CACHED", month_generated=month,
                simulated_observed=state.generation_cache[month]["observed"],
                availability=state.generation_cache[month].get("availability"),
                classification="SIMULATION_DRAW_NOT_CLOSED_SALES")
        return state.generation_cache[month]

    def _generate(self, state, month):
        rng = state.rng
        lag3, lag2, lag1 = self._effective_lags(state, month)
        scenario = state.scenario
        if lag1 is None:
            latent = rng.randint(0, 20)
        elif scenario == "CRECIMIENTO":
            step = max(1, lag1 - lag2) if lag2 is not None else 1
            latent = max(0, lag1 + step + rng.randint(0, 2))
        elif scenario == "CAÍDA":
            drop = max(1, lag2 - lag1) if lag2 is not None else 1
            latent = max(0, lag1 - drop + rng.randint(0, 1))
        elif scenario == "PICO MAYORISTA":
            latent = max(0, lag1 + rng.randint(20, 40))
        elif scenario == "CAMBIO PERSISTENTE":
            latent = max(0, lag1 + 5 + rng.randint(0, 3))
        elif scenario == "RECUPERACIÓN":
            step = max(1, (10 - lag1) // 2) if lag1 < 10 else 1
            latent = max(0, lag1 + step + rng.randint(0, 1))
        else:
            latent = max(0, round(lag1 + rng.gauss(0, 1.5)))
        if scenario == "STOCKOUT":
            availability = rng.randint(0, max(0, latent))
            return {
                "observed": min(latent, availability),
                "latent": latent,
                "availability": availability,
            }
        return {"observed": max(0, latent), "latent": None, "availability": None}


def create_session(reference=None, seed=SESSION_SEED):
    return DemandSession(reference, seed)
