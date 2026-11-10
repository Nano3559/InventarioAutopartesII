"""Evidencia reproducible T15; usa AppTest, nunca simula capturas visuales."""
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/"ml/demand"))
from demand_engine import create_session
from simulator_inputs import InputError
from tests.test_h4_functional_fixes import NormalStreamlitFixTests


def pair_sequence(interleave):
    engine = create_session()
    engine.select(1, 5)
    values = []
    for _ in range(6):
        engine.select(1, 5)
        values.append(engine.generate_observed())
        engine.close_month(); engine.advance_month()
        if interleave:
            engine.select(2, 5)
            engine.generate_observed(); engine.close_month(); engine.advance_month()
    return values


def run():
    cls = NormalStreamlitFixTests
    cls.setUpClass()
    case = cls("test_normal_v1_activation_real_inference_and_rollback")
    try:
        case.test_normal_v1_activation_real_inference_and_rollback()
        result = dict(normal_streamlit=case.evidence)
        app = case.manual_pending()
        engine = app.session_state["demand_session"]
        before = engine.status()
        try:
            engine.close_month(complete=False)
            raise AssertionError("El cierre incompleto no debe aceptarse")
        except InputError as exc:
            close_error = str(exc)
        assert before == engine.status()
        incomplete = dict(complete_checkbox=app.checkbox(key="closed_1_5_2026-10").value,
                          close_disabled=case.button(app,"REGISTRAR OBSERVADO").disabled,
                          advance_disabled=case.button(app,"AVANZAR MES").disabled,
                          backend_error=close_error, state_unchanged=True,
                          closed_count=len(app.session_state["observation_journal"].closed))
        app.checkbox(key="closed_1_5_2026-10").check().run()
        case.button(app,"AVANZAR MES").click().run()
        assert not app.exception
        assert engine.status()["open_month"] == "2026-11"
        incomplete["after_confirmation"] = dict(open_month=engine.status()["open_month"],
                                                observed=app.session_state["observation_journal"].closed[(1,5,"2026-10")].observed)
        alone, interleaved = pair_sequence(False), pair_sequence(True)
        assert alone == interleaved
        result["diagnostics_after"] = dict(per_pair_rng=dict(alone=alone,interleaved=interleaved,independent=True),
                                            manual_close=incomplete)
        (OUT/"functional_validation.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,
            default=lambda o: asdict(o) if is_dataclass(o) else str(o)),encoding="utf-8")
        print(json.dumps(dict(normal_activation="PASS",rollback="PASS",random_independence=True,
                              incomplete_rejected=True,inference_fit_calls=case.evidence["fit_calls"])))
    finally:
        case.doCleanups()
        cls.tearDownClass()


if __name__ == "__main__":
    run()
