"""R30: modelos reales existentes, sin ajustar ni evaluar TEST oficial."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest

import reference_runtime as rr
from demand_engine import create_session
from demand_runtime import create_runtime, V1_BINARY_SHA256
from lifecycle_registry import LifecycleRegistry
from ml_pipeline import TrainStandardizer
from pair_contexts import bind_pair_context
from session_export import build_session_export, verify_session_export
from simulator_inputs import HERE, InputError, FEATURE_NAMES, build_inputs
from ui_runtime import ObservationJournal, issue_forecast


def setup_sources():
    engine, journal = create_session(), ObservationJournal()
    engine.bind_journal(journal.session_id)
    engine.select(1, 5)
    return engine, journal


def features_for(engine):
    state = engine.status()
    return build_inputs(engine._reference, state["product_id"], state["location_id"],
                        state["viewing_month"], engine.lags(), history=engine.recent_history())


def rows(result):
    return {r["id"]: r for r in result["predictions"]}


class LRReferenceTests(unittest.TestCase):
    def setUp(self):
        self.engine, self.journal = setup_sources()
        self.features = features_for(self.engine)

    def test_load_existing_artifact_and_predict_with_frozen_scaler_no_fit(self):
        model = rr.LinearRegressionReference()
        with patch.object(LinearRegression, "fit", side_effect=AssertionError("sin fit")), patch.object(TrainStandardizer, "fit", side_effect=AssertionError("sin fit scaler")):
            first = model.predict(self.features)
            before = [s.copy() for s in (model._loaded[0].mean_, model._loaded[0].scale_)]
            self.assertEqual(model.predict(self.features), first)
        self.assertIsInstance(first["prediction"], float)
        self.assertGreaterEqual(first["prediction"], 0)
        for a, b in zip(before, (model._loaded[0].mean_, model._loaded[0].scale_)):
            self.assertTrue(a.equals(b))
        self.assertFalse(hasattr(model, "promote_candidate"))
        self.assertFalse(hasattr(model, "get_active_model"))

    def test_identity_reference_and_protected_hash(self):
        meta = rr.lr_metadata()
        self.assertEqual(meta["role"], "REFERENCE")
        self.assertEqual(meta["trained_through"], "2026-03")
        self.assertEqual(meta["feature_names"], list(FEATURE_NAMES))
        protected = json.loads((HERE.parent.parent/"docs/H4/tareas_erika/tarea_19/evidence/integrity_before.json").read_bytes())
        self.assertEqual(meta["artifact_hash"], protected[r"ml\demand\models\linear_regression_candidate.joblib"])
        self.assertFalse(meta["promotable"])

    def test_unknown_bytes_are_never_deserialized(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"unknown.joblib"; path.write_bytes(b"unknown")
            with patch.object(rr, "_LR_PATH", path), patch("joblib.load") as loader:
                with self.assertRaises(InputError): rr.LinearRegressionReference().predict(self.features)
                loader.assert_not_called()

    def test_unverified_registry_is_rejected_before_deserialization(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"experiments.csv"; path.write_bytes(b"untrusted")
            with patch.object(rr, "_EXPERIMENTS_PATH", path), patch("joblib.load") as loader:
                with self.assertRaises(InputError): rr.LinearRegressionReference().predict(self.features)
                loader.assert_not_called()

    def test_incompatible_schema_features_and_metadata_are_rejected(self):
        raw, registry = rr._verified_sources()
        for field, value in (("schema", "other"), ("feature_names", list(reversed(FEATURE_NAMES))),
                             ("trained_through", "2026-09"), ("role", "ACTIVE"), ("seed", 99)):
            with self.subTest(field=field):
                payload = joblib.load(io.BytesIO(raw)); payload[field] = value
                with self.assertRaises(InputError): rr._validate_payload(payload, registry)

    def test_versions_and_scaler_parameters_are_verified(self):
        raw, registry = rr._verified_sources()
        payload = joblib.load(io.BytesIO(raw)); payload["versions"]["scikit-learn"] = "unknown"
        with self.assertRaises(InputError): rr._validate_payload(payload, registry)
        payload = joblib.load(io.BytesIO(raw)); payload["scaler"].mean_.iloc[0] += 1
        with self.assertRaises(InputError): rr._validate_payload(payload, registry)

    def test_invalid_order_and_missing_history_do_not_load_model(self):
        with patch("joblib.load") as loader:
            with self.assertRaises(InputError):
                rr.LinearRegressionReference().predict(dict(reversed(list(self.features.items()))))
            with self.assertRaises(InputError):
                rr.LinearRegressionReference().predict(dict(self.features, ventas_mes_anterior=None))
            loader.assert_not_called()

    def test_negative_is_abstention_raw_preserved_without_clipping(self):
        with patch.object(LinearRegression, "predict", return_value=np.array([-3.5])):
            result = rr.LinearRegressionReference().predict(self.features)
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["raw_prediction"], -3.5)
        self.assertEqual(result["reason"], "PREDICCION_NEGATIVA")

    def test_nonfinite_output_is_abstention(self):
        with patch.object(LinearRegression, "predict", return_value=np.array([float("nan")])):
            result = rr.LinearRegressionReference().predict(self.features)
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["reason"], "SALIDA_NO_VALIDA")


class ReferenceComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.engine, self.journal = setup_sources()
        self.registry = LifecycleRegistry(self.engine.session_id, Path(self.temp.name)/"events")
        self.binding = self.registry.bind(1, 5)
        self.runtime = create_runtime(); self.runtime.bind_lifecycle(self.binding)
        self.service = rr.ReferenceComparisonSession(self.engine.session_id, 1, 5)
        self.service.bind_lifecycle(self.binding)
        self.features = features_for(self.engine)

    def test_baseline_and_lr_independent_of_active(self):
        result = self.service.predict(self.engine, self.features, self.runtime)
        output = rows(result)
        self.assertEqual(output["BASELINE_LAG1"]["prediction"], self.features[FEATURE_NAMES[0]])
        self.assertIsNotNone(output["LR_REFERENCE"]["prediction"])
        self.assertIsNone(output["RF_V1"]["prediction"])
        self.assertEqual(output["RF_V1"]["reason"], "V1_NO_ACTIVE")
        self.assertIsNone(self.runtime.get_active_model())

    def test_same_features_for_both_real_models_without_fit_or_test_access(self):
        self.runtime.activate_v1("acción explícita de prueba")
        seen = []
        original_lr, original_rf = LinearRegression.predict, RandomForestRegressor.predict
        original_transform = TrainStandardizer.transform
        original_inputs = []
        def transform(scaler, frame):
            original_inputs.extend(frame.to_dict("records"))
            return original_transform(scaler, frame)
        def predict_lr(model, frame):
            seen.append(list(frame.columns)); return original_lr(model, frame)
        def predict_rf(model, frame):
            original_inputs.extend(frame.to_dict("records")); seen.append(list(frame.columns))
            return original_rf(model, frame)
        before = self.runtime.get_active_model()
        with patch.object(LinearRegression, "fit", side_effect=AssertionError("sin fit")), \
             patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("sin fit")), \
             patch.object(TrainStandardizer, "fit", side_effect=AssertionError("sin fit")), \
             patch("ml_pipeline.load_supervised", side_effect=AssertionError("sin leer targets")), \
             patch("evaluate_v1.run_final_evaluation", side_effect=AssertionError("sin TEST")), \
             patch.object(TrainStandardizer, "transform", new=transform), \
             patch.object(LinearRegression, "predict", new=predict_lr), \
             patch.object(RandomForestRegressor, "predict", new=predict_rf):
            result = self.service.predict(self.engine, self.features, self.runtime)
        self.assertEqual(original_inputs, [self.features, self.features])
        self.assertEqual(seen, [list(FEATURE_NAMES), list(FEATURE_NAMES)])
        self.assertEqual(self.runtime.get_active_model(), before)
        self.assertTrue(all(r["prediction"] is not None and r["prediction"] >= 0 for r in result["predictions"]))
        self.assertIsNone(result["metrics"])

    def test_repeat_is_stable_and_does_not_add_events(self):
        first = self.service.predict(self.engine, self.features, self.runtime)
        before = self.registry.records()
        self.assertEqual(self.service.predict(self.engine, self.features, self.runtime), first)
        self.assertEqual(self.registry.records(), before)
        self.service.export_evidence()[0]["features"][FEATURE_NAMES[0]] = 12345
        self.assertEqual(self.service.export_evidence(), [first])

    def test_product_new_cannot_be_bypassed_by_filled_lags(self):
        self.engine.apply_scenario("PRODUCTO NUEVO")
        with patch("joblib.load") as loader:
            result = self.service.predict(self.engine, self.features, self.runtime)
            loader.assert_not_called()
        self.assertTrue(all(r["reason"] == "HISTORIAL INSUFICIENTE" for r in result["predictions"]))

    def test_incomplete_and_invalid_inputs_abstain(self):
        variants = [None, {}, dict(reversed(list(self.features.items()))),
                    dict(self.features, ventas_mes_anterior=True),
                    dict(self.features, ventas_mes_anterior=float("nan")),
                    dict(self.features, mes_sin=0.5)]
        with patch("joblib.load") as loader:
            for features in variants:
                result = self.service.predict(self.engine, features, self.runtime)
                self.assertTrue(all(r["prediction"] is None for r in result["predictions"]))
            incomplete = self.service.predict(self.engine, self.features, self.runtime, complete=False)
            self.assertTrue(all(r["reason"] == "DATOS INCOMPLETOS" for r in incomplete["predictions"]))
            loader.assert_not_called()

    def test_invalid_order_cannot_reuse_valid_cached_prediction(self):
        self.service.predict(self.engine, self.features, self.runtime)
        result = self.service.predict(self.engine, dict(reversed(list(self.features.items()))), self.runtime)
        self.assertTrue(all(r["prediction"] is None for r in result["predictions"]))

    def test_initial_test_period_is_not_evaluated(self):
        self.engine.select_month("2026-09")
        with patch.object(self.service._lr, "predict") as lr, patch.object(self.runtime, "predict") as rf:
            result = self.service.predict(self.engine, features_for(self.engine), self.runtime)
            lr.assert_not_called(); rf.assert_not_called()
        self.assertTrue(all(r["reason"] == "PERIODO_NO_NUEVO" for r in result["predictions"]))

    def test_foreign_pair_or_session_service_is_rejected(self):
        self.engine.select(2, 5)
        with self.assertRaises(InputError): self.service.predict(self.engine, self.features, self.runtime)
        other, _ = setup_sources()
        with self.assertRaises(InputError): self.service.predict(other, self.features, self.runtime)

    def test_active_runtime_from_another_pair_cannot_be_used(self):
        self.runtime.activate_v1("activar solo 1/5")
        self.engine.select(2, 5)
        service = rr.ReferenceComparisonSession(self.engine.session_id, 2, 5)
        result = service.predict(self.engine, features_for(self.engine), self.runtime)
        self.assertEqual(rows(result)["RF_V1"]["reason"], "RUNTIME_SIN_CONTEXTO_VERIFICADO")
        self.assertIsNotNone(rows(result)["LR_REFERENCE"]["prediction"])

    def test_observed_locks_new_emission_and_keeps_previous(self):
        first = self.service.predict(self.engine, self.features, self.runtime)
        self.engine.set_manual_observed(10)
        self.assertEqual(self.service.predict(self.engine, self.features, self.runtime), first)
        edited = dict(self.features); edited[FEATURE_NAMES[0]] += 1
        result = self.service.predict(self.engine, edited, self.runtime)
        self.assertTrue(all(r["reason"] == "OBSERVADO_YA_CONOCIDO" for r in result["predictions"]))
        self.assertEqual(self.service.export_evidence()[0], first)

    def test_lr_failure_does_not_change_active_or_baseline(self):
        self.runtime.activate_v1("activar V1")
        before = self.runtime.get_active_model()
        with patch.object(self.service._lr, "predict", side_effect=InputError("fixture rechazo")):
            result = self.service.predict(self.engine, self.features, self.runtime)
        self.assertEqual(rows(result)["LR_REFERENCE"]["reason"], "REFERENCE_NO_DISPONIBLE")
        self.assertIsNotNone(rows(result)["RF_V1"]["prediction"])
        self.assertIsNotNone(rows(result)["BASELINE_LAG1"]["prediction"])
        self.assertEqual(self.runtime.get_active_model(), before)

    def test_r52_compatible_and_reference_is_not_promotable(self):
        state = {}; bind_pair_context(state, self.engine.session_id, 1, 5)
        result = self.service.predict(self.engine, self.features, self.runtime)
        state.update(h4_runtime=self.runtime, reference_comparison_session=self.service,
                     reference_comparison_result=result)
        document = build_session_export(self.engine, self.journal, state, self.registry)
        self.assertTrue(verify_session_export(document))
        self.assertEqual(document["schema_version"], "h4-session-1")
        context = document["extensions"]["h4_traceability"]["model_contexts"][0]
        self.assertEqual(context["reference_predictions"], [result])
        self.assertEqual(context["candidates"], [])
        self.assertIsNone(context["references"]["active"])
        with self.assertRaises(InputError): self.runtime.promote_candidate(result)
        self.assertIsNone(self.runtime.get_active_model())


class ReferenceStreamlitTests(unittest.TestCase):
    def test_ross_adapter_pair_recovery_and_reset(self):
        source = '''
import sys
sys.path.insert(0, {folder!r})
import streamlit as st
from ui_panels import engine, compare_reference_models
from simulator_inputs import build_inputs
eng = engine()
product = st.selectbox("Producto", (1, 2), key="product")
eng.select(product, 5)
features = build_inputs(eng._reference, product, 5, eng.status()["viewing_month"], eng.lags(), history=eng.recent_history())
result = compare_reference_models(features)
st.json(result)
'''.format(folder=str(HERE))
        with tempfile.TemporaryDirectory() as folder, patch("lifecycle_registry.DEFAULT_ROOT", Path(folder)):
            app = AppTest.from_string(source, default_timeout=30).run()
            self.assertFalse(app.exception)
            first = app.session_state["reference_comparison_result"]
            app.run()
            self.assertEqual(app.session_state["reference_comparison_result"], first)
            app.selectbox(key="product").select(2).run()
            second = app.session_state["reference_comparison_result"]
            self.assertEqual(second["product_id"], 2)
            self.assertNotEqual(first["id"], second["id"])
            app.selectbox(key="product").select(1).run()
            self.assertEqual(app.session_state["reference_comparison_result"], first)
            # La app principal utiliza su propia sesión; no copiar estado
            # privado de AppTest desde otra aplicación.
            normal = AppTest.from_file(
                str(HERE / "streamlit_app.py"), default_timeout=30
            ).run()
            self.assertFalse(normal.exception)
            reset_buttons = [
                button for button in normal.button
                if button.label == "RESTABLECER EDICIÓN"
            ]
            self.assertTrue(reset_buttons, "No se encontró el botón de reset")
            reset_buttons[0].click().run()
            self.assertFalse(normal.exception)
            self.assertNotIn("reference_comparison_session", normal.session_state)
            self.assertIsNone(normal.session_state["h4_runtime"].get_active_model())
