"""Cierre Ross: referencias reales, portabilidad e interfaz sin fit ni TEST oficial."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from streamlit.testing.v1 import AppTest

import model_comparison as mc
from simulator_inputs import HERE, InputError
from ui_analysis import group_errors, parse_comparison
from simulator_inputs import load_reference
from .test_ross_ui import observed_rows, report_payload


class ArchivedPortabilityTests(unittest.TestCase):
    def test_pinned_archive_uses_local_checkout_without_changing_manifest(self):
        manifest = HERE / "candidates" / mc.ARCHIVE_SESSION / mc.ARCHIVE_RUN / "manifest.json"
        before = manifest.read_bytes()
        run = mc.archived_run()
        self.assertEqual(Path(run["folder"]), manifest.parent.resolve())
        data, metadata, _ = mc.verified_bundle(run)
        self.assertEqual(metadata["version"], mc.ARCHIVE_RUN)
        self.assertEqual(len(data["reserved"]), 3)
        self.assertEqual(manifest.read_bytes(), before)

    def test_copied_checkout_resolves_only_fixed_package_and_rejects_tampering(self):
        relative = Path("candidates") / mc.ARCHIVE_SESSION / mc.ARCHIVE_RUN
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / relative
            shutil.copytree(HERE / relative, destination)
            with patch.object(mc, "HERE", Path(temp)):
                run = mc.archived_run()
                self.assertEqual(Path(run["folder"]), destination.resolve())
                mc.verified_bundle(run)
                (destination / "manifest.json").write_bytes(b"{}")
                with self.assertRaises(InputError), patch("joblib.load") as loader:
                    mc.archived_run()
                    loader.assert_not_called()


class ScenarioBreakdownTests(unittest.TestCase):
    def test_imported_scenario_is_diagnostic_and_missing_stays_unknown(self):
        payload = report_payload()
        payload["rows"][0]["scenario"] = "STOCKOUT"
        report = parse_comparison(json.dumps(payload).encode(), load_reference())
        rows = next(iter(report["groups"].values()))
        result = {r["Escenario"]: r for r in group_errors(rows, "Escenario")}
        self.assertEqual(result["STOCKOUT"]["Casos"], 1)
        self.assertEqual(result["NO REGISTRADO"]["Casos"], 1)
        payload["rows"][0]["scenario"] = "inventado"
        with self.assertRaises(InputError):
            parse_comparison(json.dumps(payload).encode(), load_reference())

    def test_each_scenario_retains_support_and_abstentions(self):
        rows = observed_rows([12, None, 8])
        rows[0] = replace(rows[0], forecast=replace(rows[0].forecast, scenario="NORMAL"))
        rows[1] = replace(rows[1], forecast=replace(rows[1].forecast, scenario="PRODUCTO NUEVO"))
        rows[2] = replace(rows[2], forecast=replace(rows[2].forecast, scenario="NORMAL"))
        result = {r["Escenario"]: r for r in group_errors(rows, "Escenario")}
        self.assertEqual(result["NORMAL"]["Casos"], 2)
        self.assertEqual(result["NORMAL"]["MAE"], 2)
        self.assertEqual(result["PRODUCTO NUEVO"]["Cobertura"], 0)
        self.assertIsNone(result["PRODUCTO NUEVO"]["MAE"])


class RealReferenceUITests(unittest.TestCase):
    def setUp(self):
        self.no_rf_fit = patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("sin fit"))
        self.no_lr_fit = patch.object(LinearRegression, "fit", side_effect=AssertionError("sin fit"))
        self.no_rf_fit.start(); self.no_lr_fit.start()
        self.addCleanup(self.no_rf_fit.stop); self.addCleanup(self.no_lr_fit.stop)

    def app(self):
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def compare(self, app):
        self.button(app, "COMPARAR TRES REFERENCIAS").click().run()
        self.assertFalse(app.exception)
        return app.session_state["reference_comparison_result"]

    def test_visible_baseline_and_real_lr_work_without_active(self):
        app = self.app()
        result = self.compare(app)
        rows = {r["id"]: r for r in result["predictions"]}
        self.assertEqual(rows["BASELINE_LAG1"]["prediction"], app.number_input[2].value)
        self.assertIsNotNone(rows["LR_REFERENCE"]["prediction"])
        self.assertEqual(rows["RF_V1"]["reason"], "V1_NO_ACTIVE")
        self.assertIsNone(app.session_state["h4_runtime"].get_active_model())

    def test_activate_real_v1_compare_and_export_preserves_references(self):
        app = self.app()
        app.text_input(key="v1_activation_reason").set_value("Verificación local Ross").run()
        self.button(app, "ACTIVAR V1 CONGELADA").click().run()
        result = self.compare(app)
        self.assertTrue(all(row["prediction"] is not None for row in result["predictions"]))
        self.assertIsNone(result["metrics"])
        self.assertEqual(app.session_state["h4_runtime"].get_active_model()["version"], "V1")
        export = app.session_state["last_session_export"]
        self.assertIn(result["id"], json.dumps(export))

    def test_edit_marks_old_reference_and_requires_explicit_new_comparison(self):
        app = self.app()
        first = self.compare(app)
        app.number_input[2].set_value(25).run()
        self.assertEqual(app.session_state["reference_comparison_result"]["id"], first["id"])
        self.assertTrue(any("Emisión anterior" in w.value for w in app.warning))
        second = self.compare(app)
        self.assertEqual(second["features"]["ventas_mes_anterior"], 25)
        self.assertNotEqual(first["id"], second["id"])

    def test_reference_comparison_cannot_be_reissued_after_revealing_observed(self):
        app = self.app()
        self.compare(app)
        self.button(app, "REGISTRAR ABSTENCIÓN").click().run()
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(self.button(app, "COMPARAR TRES REFERENCIAS").disabled)

    def test_new_product_has_explicit_abstention_for_all_references(self):
        app = self.app()
        app.selectbox[3].set_value("PRODUCTO NUEVO").run()
        result = self.compare(app)
        self.assertTrue(all(r["prediction"] is None for r in result["predictions"]))
        self.assertTrue(all(r["reason"] == "HISTORIAL INSUFICIENTE" for r in result["predictions"]))


if __name__ == "__main__":
    unittest.main()
