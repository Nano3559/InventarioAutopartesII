"""Dobles exclusivos de pruebas. No crean modelos, experimentos o datasets."""
import json
import math
import unittest
from copy import deepcopy
from dataclasses import replace

from streamlit.testing.v1 import AppTest

from simulator_inputs import FEATURE_NAMES, HERE, InputError, build_inputs, load_reference, offset_month
from .test_simulator_ui import protected_hashes
from ui_analysis import comparison_table, evaluate, group_errors, metric_values, monitor, parse_comparison, update_uploaded_comparison
from ui_runtime import ClosedObservation, ModelInfo, ObservationJournal, checked_number, issue_forecast, model_info


def metadata(version="TEST-v1", digest="a", role="ACTIVE"):
    return {"name": "DOBLE DE PRUEBA", "version": version, "artifact_hash": digest*64,
            "trained_through": "2026-06", "origin": "SIMULACION", "feature_names": list(FEATURE_NAMES), "role": role}


class FakeRuntime:
    """No es un algoritmo para la demo. Solo verifica la interfaz en unittest."""
    def __init__(self):
        self.calls = []
        self.metadata = metadata()
        self.result = {"prediction": 17.5, "reason": ""}

    def get_active_model(self):
        return deepcopy(self.metadata)

    def predict(self, features):
        self.calls.append(deepcopy(features))
        return deepcopy(self.result)

    def fit(self, *_):
        raise AssertionError("La UI nunca debe entrenar")


def observed_rows(predictions, observed=None, baseline=10):
    model = model_info(metadata())
    result = []
    for index, pred in enumerate(predictions):
        month = offset_month("2026-07", index)
        f = issue_template(model, month, pred, baseline)
        result.append(ClosedObservation(f, 10 if observed is None else observed[index], "después", "MEDIA"))
    return result


def issue_template(model, month, prediction, baseline):
    from ui_runtime import Forecast
    return Forecast(1, 5, month, (baseline, 10, 10, 0, 1), prediction, baseline, model, "", "antes")


def report_payload():
    return {
        "schema_version": "h4-comparison-1", "origin": "SIMULACION", "purpose": "COMPARACION_LOCAL",
        "decision": "PENDIENTE", "reason": "Reporte exclusivo de unittest",
        "models": [metadata(), metadata("TEST-v2", "b", "CANDIDATE")],
        "rows": [{"productId": 1, "locationId": 5, "mes_objetivo": "2026-07", "observed": 10,
                  "predictions": {"a"*64: 8, "b"*64: 9}},
                 {"productId": 1, "locationId": 5, "mes_objetivo": "2026-08", "observed": 20,
                  "predictions": {"a"*64: 16, "b"*64: 18}}],
    }


class RuntimeContractTest(unittest.TestCase):
    def setUp(self):
        self.reference = load_reference()
        self.features = build_inputs(self.reference, 1, 5, "2026-10", [8, 12, 25])
        self.provider = FakeRuntime()

    def issue(self, **changes):
        args = dict(reference=self.reference, product_id=1, location_id=5, month="2026-10",
                    features=self.features, runtime=self.provider)
        args.update(changes)
        return issue_forecast(**args)

    def test_only_five_features_reach_predict(self):
        forecast = self.issue()
        self.assertEqual(self.provider.calls, [self.features])
        self.assertEqual(forecast.prediction, 17.5)
        self.assertEqual(forecast.baseline, 25)
        self.assertNotIn("productId", self.provider.calls[0])
        self.assertNotIn("target_ventas_mes", self.provider.calls[0])

    def test_no_model_is_abstention_not_fake_prediction(self):
        result = self.issue(runtime=None)
        self.assertIsNone(result.prediction)
        self.assertIsNone(result.model)
        self.assertEqual(result.reason, "MODELO NO DISPONIBLE")

    def test_incomplete_input_never_calls_predict(self):
        result = self.issue(features=None, reason="DATOS INCOMPLETOS")
        self.assertIsNone(result.prediction)
        self.assertEqual(self.provider.calls, [])
        self.assertIsNotNone(result.model)

    def test_provider_abstention_keeps_safe_quality_reason(self):
        self.provider.result = {"prediction": None, "reason": "DATOS INCOMPLETOS"}
        self.assertEqual(self.issue().reason, "DATOS INCOMPLETOS")
        self.provider.result["reason"] = "texto interno del proveedor"
        self.assertEqual(self.issue().reason, "ABSTENCIÓN DEL MODELO")

    def test_future_training_cut_is_blocked(self):
        self.provider.metadata["trained_through"] = "2026-10"
        with self.assertRaisesRegex(InputError, "entrenar"):
            self.issue()
        self.assertEqual(self.provider.calls, [])

    def test_incompatible_metadata(self):
        for key, value in [("origin", "REAL"), ("feature_names", ["target"]), ("artifact_hash", "x")]:
            bad = metadata()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(InputError):
                model_info(bad)

    def test_candidate_cannot_serve_as_active(self):
        self.provider.metadata["role"] = "CANDIDATE"
        with self.assertRaisesRegex(InputError, "ACTIVE"):
            self.issue()
        self.assertEqual(self.provider.calls, [])

    def test_invalid_output_and_negative_policy(self):
        for value in [math.nan, math.inf, True, "17", 2**54]:
            self.provider.result["prediction"] = value
            with self.subTest(value=value), self.assertRaises(InputError):
                self.issue()
        self.provider.result["prediction"] = -2.5
        self.assertEqual(self.issue().prediction, -2.5)

    def test_huge_integer_output_is_rejected_without_overflow(self):
        with self.assertRaises(InputError):
            checked_number(10**1000)

    def test_wrong_feature_order_or_calendar_is_blocked(self):
        with self.assertRaises(InputError):
            self.issue(features=dict(reversed(list(self.features.items()))))
        bad = {**self.features, "mes_cos": 1}
        with self.assertRaises(InputError):
            self.issue(features=bad)

    def test_model_cannot_mutate_frozen_inputs(self):
        original = deepcopy(self.features)
        def mutate(features):
            features["ventas_mes_anterior"] = 999
            return {"prediction": 17, "reason": ""}
        self.provider.predict = mutate
        forecast = self.issue()
        self.assertEqual(self.features, original)
        self.assertEqual(forecast.features[0], 25)

    def test_active_change_during_inference_is_rejected(self):
        def mutate(features):
            self.provider.metadata["version"] = "otra"
            return {"prediction": 17, "reason": ""}
        self.provider.predict = mutate
        with self.assertRaisesRegex(InputError, "cambió"):
            self.issue()

    def test_close_is_immutable_and_no_double_observed(self):
        journal = ObservationJournal()
        forecast = self.issue()
        with self.assertRaises(InputError):
            journal.close(forecast.key, 17)
        journal.issue(forecast)
        row = journal.close(forecast.key, 29)
        self.assertEqual(row.forecast.prediction, 17.5)
        self.assertEqual(row.forecast.features[0], 25)
        with self.assertRaises(InputError):
            journal.close(forecast.key, 0)
        with self.assertRaises(InputError):
            journal.issue(forecast)

    def test_revealed_observed_locks_emission_before_close(self):
        journal = ObservationJournal()
        forecast = self.issue()
        journal.issue(forecast)
        journal.reveal(forecast.key, 20)
        self.assertTrue(journal.is_locked(forecast.key))
        for operation in [lambda: journal.issue(forecast), lambda: journal.discard_pending(forecast.key),
                          lambda: journal.reveal(forecast.key, 99), lambda: journal.close(forecast.key, 99)]:
            with self.assertRaises(InputError):
                operation()
        self.assertEqual(journal.close(forecast.key, 20).observed, 20)


class AnalysisTest(unittest.TestCase):
    def test_metrics_known_units_and_r2(self):
        result = metric_values([(10, 8), (20, 16)])
        self.assertEqual(result["MAE"], 3)
        self.assertAlmostEqual(result["RMSE"], math.sqrt(10))
        self.assertAlmostEqual(result["R2"], .6)

    def test_constant_target_or_one_case_has_no_r2(self):
        self.assertIsNone(metric_values([(10, 10)])["R2"])
        self.assertIsNone(metric_values([(10, 8), (10, 16)])["R2"])
        self.assertLess(metric_values([(0, 20), (1, 20)])["R2"], 0)

    def test_abstention_affects_coverage_not_error_zero(self):
        stats = evaluate(observed_rows([8, None], observed=[10, 20]))
        self.assertEqual(stats["MAE"], 2)
        self.assertEqual(stats["coverage"], .5)
        self.assertEqual(stats["baseline"]["n"], 1)
        self.assertEqual(stats["abstentions"], 1)

    def test_empty_metrics_are_unavailable(self):
        self.assertIsNone(evaluate([])["MAE"])
        self.assertIsNone(evaluate([])["coverage"])
        self.assertIsNone(evaluate(observed_rows([None]))["MAE"])

    def test_mixed_versions_not_pooled(self):
        rows = observed_rows([8, 9])
        other = replace(rows[1].forecast.model, version="v2")
        rows[1] = replace(rows[1], forecast=replace(rows[1].forecast, model=other))
        with self.assertRaises(InputError):
            evaluate(rows)
        with self.assertRaises(InputError):
            monitor(rows)

    def test_group_error_support(self):
        rows = observed_rows([8, 9])
        rows[1] = replace(rows[1], forecast=replace(rows[1].forecast, location_id=6), rotation="BAJA")
        self.assertEqual(len(group_errors(rows, "Tienda")), 2)
        self.assertEqual(len(group_errors(rows, "Rotación")), 2)
        self.assertEqual(group_errors(rows, "Producto")[0]["Casos"], 2)

    def test_monitor_requires_six_consecutive_months(self):
        self.assertEqual(monitor(observed_rows([10]*5))["status"], "EVIDENCIA INSUFICIENTE")
        rows = observed_rows([10]*6)
        rows[-1] = replace(rows[-1], forecast=replace(rows[-1].forecast, month="2027-02"))
        self.assertEqual(monitor(rows)["status"], "EVIDENCIA INSUFICIENTE")

    def test_monitor_stable_and_single_outlier(self):
        self.assertEqual(monitor(observed_rows([10]*6))["status"], "NORMAL")
        self.assertEqual(monitor(observed_rows([10, 10, 10, 10, 10, 100]))["status"], "NORMAL")

    def test_monitor_persistent_error_or_baseline_superior(self):
        self.assertEqual(monitor(observed_rows([10, 10, 10, 13, 14, 15]))["status"], "REVISIÓN RECOMENDADA")
        self.assertEqual(monitor(observed_rows([12]*6))["status"], "REVISIÓN RECOMENDADA")

    def test_quality_precedes_retraining_recommendation(self):
        rows = observed_rows([None])
        rows[0] = replace(rows[0], forecast=replace(rows[0].forecast, reason="DATOS INCOMPLETOS"))
        self.assertEqual(monitor(rows)["status"], "PROBLEMA DE DATOS")

    def test_inconsistent_lags_do_not_produce_drift_recommendation(self):
        rows = observed_rows([10]*6)
        rows[3] = replace(rows[3], forecast=replace(rows[3].forecast, features=(999, 10, 10, 0, 1)))
        result = monitor(rows)
        self.assertEqual(result["status"], "PROBLEMA DE DATOS")
        self.assertIn("lags", result["reason"])


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        self.reference = load_reference()

    def parse(self, payload):
        return parse_comparison(json.dumps(payload).encode(), self.reference)

    def test_metrics_recomputed_and_roles_preserved(self):
        table = comparison_table(self.parse(report_payload()))
        self.assertEqual(table[0]["MAE común"], 3)
        self.assertEqual(table[1]["MAE común"], 1.5)
        self.assertEqual(table[1]["Papel"], "CANDIDATE")

    def test_common_rows_and_coverage(self):
        report = report_payload()
        report["rows"][1]["predictions"]["b"*64] = None
        table = comparison_table(self.parse(report))
        self.assertEqual(table[0]["MAE común"], 2)
        self.assertEqual(table[1]["MAE común"], 1)
        self.assertEqual(table[1]["Cobertura"], .5)
        self.assertEqual(table[0]["Casos comunes"], 1)

    def test_no_common_prediction_does_not_invent_winner(self):
        report = report_payload()
        for row in report["rows"]:
            row["predictions"]["b"*64] = None
        self.assertIsNone(comparison_table(self.parse(report))[0]["MAE común"])

    def test_duplicate_keys_and_rows_rejected(self):
        with self.assertRaises(InputError):
            parse_comparison(b'{"origin":"SIMULACION","origin":"REAL"}', self.reference)
        report = report_payload()
        report["rows"].append(deepcopy(report["rows"][0]))
        with self.assertRaises(InputError):
            self.parse(report)

    def test_invalid_report_preconditions(self):
        mutations = [
            lambda d: d.update(origin="REAL"),
            lambda d: d["models"][0].update(trained_through="2026-07"),
            lambda d: d["rows"][0].update(locationId=999),
            lambda d: d["rows"][0].update(observed=-1),
            lambda d: d["rows"][0]["predictions"].pop("b"*64),
            lambda d: d.update(purpose="TEST_FINAL", frozen_selection=False),
        ]
        for mutate in mutations:
            report = report_payload()
            mutate(report)
            with self.subTest(report=report), self.assertRaises(InputError):
                self.parse(report)

    def test_nonfinite_size_and_malformed_json(self):
        for payload in [b'{"x":NaN}', b'not json', b' '* (2*1024*1024+1), b'['*1500+b']'*1500]:
            with self.subTest(length=len(payload)), self.assertRaises(InputError):
                parse_comparison(payload, self.reference)

    def test_huge_integer_in_report_is_safe(self):
        report = report_payload()
        report["rows"][0]["predictions"]["a"*64] = 10**1000
        with self.assertRaises(InputError):
            self.parse(report)

    def test_unchanged_upload_does_not_replace_runtime_report(self):
        state = {}
        payload = json.dumps(report_payload()).encode()
        update_uploaded_comparison(state, payload, self.reference)
        state["comparison_report"] = "reporte del runtime"
        state["comparison_source"] = "RUNTIME LOCAL"
        update_uploaded_comparison(state, payload, self.reference)
        self.assertEqual(state["comparison_report"], "reporte del runtime")
        self.assertEqual(state["comparison_source"], "RUNTIME LOCAL")

    def test_removing_file_clears_file_report_but_not_runtime_report(self):
        payload = json.dumps(report_payload()).encode()
        for source in ["ARCHIVO IMPORTADO", "RUNTIME LOCAL"]:
            state = {}
            update_uploaded_comparison(state, payload, self.reference)
            state["comparison_source"] = source
            update_uploaded_comparison(state, None, self.reference)
            self.assertEqual("comparison_report" in state, source == "RUNTIME LOCAL")

    def test_changed_or_invalid_upload_replaces_old_result_explicitly(self):
        state = {}
        update_uploaded_comparison(state, json.dumps(report_payload()).encode(), self.reference)
        newer = report_payload()
        newer["reason"] = "nuevo archivo"
        update_uploaded_comparison(state, json.dumps(newer).encode(), self.reference)
        self.assertEqual(state["comparison_report"]["reason"], "nuevo archivo")
        self.assertIsNotNone(update_uploaded_comparison(state, b'invalid', self.reference))
        self.assertNotIn("comparison_report", state)
        self.assertIsNotNone(update_uploaded_comparison(state, b'invalid', self.reference))


class WorkflowInterfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = protected_hashes()

    @classmethod
    def tearDownClass(cls):
        if cls.before != protected_hashes():
            raise AssertionError("Se modificó el dataset o el generador")

    def app(self):
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30)
        app.session_state["h4_runtime"] = FakeRuntime()
        app.run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, name):
        return next(b for b in app.button if b.label == name)

    def test_inference_uses_edited_values_and_never_runs_on_rerun(self):
        app = self.app()
        app.number_input[2].set_value(25).run()
        self.assertEqual(app.session_state["h4_runtime"].calls, [])
        self.button(app, "PREDECIR").click().run()
        provider = app.session_state["h4_runtime"]
        self.assertEqual(provider.calls[0]["ventas_mes_anterior"], 25)
        app.run()
        self.assertEqual(len(provider.calls), 1)
        self.assertFalse(app.exception)

    def test_close_observed_and_show_metrics_without_leakage(self):
        app = self.app()
        self.button(app, "PREDECIR").click().run()
        app.number_input[-1].set_value(20).run()
        app.checkbox[-1].check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)
        rows = list(app.session_state["observation_journal"].closed.values())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].forecast.prediction, 17.5)
        self.assertEqual(evaluate(rows)["MAE"], 2.5)
        self.assertEqual(len(app.session_state["h4_runtime"].calls), 1)
        self.assertTrue(app.number_input[0].disabled)
        self.assertTrue(self.button(app, "PREDECIR").disabled)

    def test_edits_discard_open_emission(self):
        app = self.app()
        self.button(app, "PREDECIR").click().run()
        self.assertTrue(app.session_state["observation_journal"].pending)
        app.number_input[0].set_value(123).run()
        self.assertFalse(app.session_state["observation_journal"].pending)
        self.assertEqual(len(app.number_input), 3)

    def test_observed_reveal_blocks_edits_and_second_prediction(self):
        app = self.app()
        self.button(app, "PREDECIR").click().run()
        app.number_input[-1].set_value(20).run()
        self.assertTrue(self.button(app, "PREDECIR").disabled)
        self.assertTrue(all(w.disabled for w in app.number_input))
        self.assertTrue(app.selectbox[3].disabled)
        self.assertEqual(len(app.session_state["h4_runtime"].calls), 1)
        self.assertFalse(app.exception)

    def test_revealed_value_survives_switching_series(self):
        app = self.app()
        self.button(app, "PREDECIR").click().run()
        app.number_input[-1].set_value(20).run()
        app.selectbox[1].set_value(6).run()
        app.selectbox[1].set_value(5).run()
        self.assertEqual(app.number_input[-1].value, 20)
        self.assertTrue(app.number_input[-1].disabled)
        app.checkbox[-1].check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)

    def test_missing_model_can_record_abstention_and_coverage(self):
        app = self.app()
        app.session_state["h4_runtime"] = None
        app.run()
        self.button(app, "REGISTRAR ABSTENCIÓN").click().run()
        app.number_input[-1].set_value(10).run()
        app.checkbox[-1].check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)
        stats = evaluate(list(app.session_state["observation_journal"].closed.values()))
        self.assertEqual(stats["coverage"], 0)
        self.assertIsNone(stats["MAE"])

    def test_comparison_screen_uses_real_report_contract(self):
        app = self.app()
        app.session_state["comparison_report"] = parse_comparison(json.dumps(report_payload()).encode(), load_reference())
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("CANDIDATE menor" in m.value for m in app.markdown))

    def test_runtime_failure_is_recorded_as_abstention(self):
        app = self.app()
        app.session_state["h4_runtime"].result["prediction"] = math.nan
        self.button(app, "PREDECIR").click().run()
        pending = list(app.session_state["observation_journal"].pending.values())
        self.assertEqual(len(pending), 1)
        self.assertIsNone(pending[0].prediction)
        self.assertEqual(pending[0].reason, "ERROR DE INFERENCIA")
        self.assertIsNotNone(pending[0].model)
        self.assertTrue(app.error)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
