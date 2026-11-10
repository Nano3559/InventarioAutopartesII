"""Pruebas de integración del motor de Erika con la interfaz Streamlit de Ross."""
import unittest

from demand_engine import create_session
from simulator_inputs import HERE, content_sha256, load_reference
from streamlit.testing.v1 import AppTest

from .test_ross_ui import FakeRuntime
from .test_simulator_ui import protected_hashes


def dataset_hashes():
    folder = HERE / "data" / "escenarios_v1_1"
    return {
        path.name: content_sha256(path.read_bytes())
        for path in sorted(folder.iterdir()) if path.is_file()
    }


class EngineStreamlitIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_reference()
        cls.before = protected_hashes()

    @classmethod
    def tearDownClass(cls):
        if cls.before != protected_hashes():
            raise AssertionError("La integración modificó datos o el generador histórico")

    def app(self, runtime=False):
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30)
        if runtime:
            app.session_state["h4_runtime"] = FakeRuntime()
        app.run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def engine(self, app):
        return app.session_state["demand_session"]

    def journal(self, app):
        return app.session_state["observation_journal"]

    def emit(self, app):
        """Emisión sin ACTIVE: abstención que habilita GENERAR."""
        self.button(app, "REGISTRAR ABSTENCIÓN").click().run()
        self.assertFalse(app.exception)

    def test_engine_created_and_follows_selectors(self):
        app = self.app()
        state = self.engine(app).status()
        self.assertEqual(
            (state["product_id"], state["location_id"], state["open_month"],
             state["viewing_month"], state["scenario"], state["history_status"]),
            (1, 5, "2026-10", "2026-10", "NORMAL", "COMPLETO"),
        )
        app.selectbox[2].set_value("2025-01").run()
        state = self.engine(app).status()
        self.assertEqual(state["viewing_month"], "2025-01")
        self.assertEqual(state["open_month"], "2026-10")
        app.selectbox[0].set_value(2).run()
        app.selectbox[1].set_value(6).run()
        state = self.engine(app).status()
        self.assertEqual((state["product_id"], state["location_id"]), (2, 6))
        self.assertEqual(state["open_month"], "2026-10")
        self.assertEqual(state["closed_months"], ())
        self.assertTrue(any("abierto 2026-10" in c.value for c in app.caption))

    def test_scenario_preload_drives_editor_and_engine(self):
        app = self.app()
        app.selectbox[3].set_value("CRECIMIENTO").run()
        self.assertEqual([n.value for n in app.number_input], [8, 12, 17])
        eng = self.engine(app)
        self.assertEqual(eng.status()["scenario"], "CRECIMIENTO")
        self.assertEqual(eng.lags(), (8, 12, 17))
        app.number_input[2].set_value(25).run()
        self.assertEqual(self.engine(app).lags(), (8, 12, 25))
        app.selectbox[3].set_value("NORMAL").run()
        self.assertEqual([n.value for n in app.number_input], [10, 10, 10])
        self.assertEqual(self.engine(app).lags(), (10, 10, 10))

    def test_historical_edits_do_not_move_open_month(self):
        app = self.app()
        open_lags = tuple(v for _, v in self.engine(app).recent_history())
        app.selectbox[2].set_value("2025-01").run()
        app.number_input[0].set_value(55).run()
        app.selectbox[2].set_value("2026-10").run()
        self.assertEqual(self.engine(app).lags(), open_lags)
        self.assertEqual([n.value for n in app.number_input], list(open_lags))

    def test_scenario_from_historical_month_syncs_open_month_editor(self):
        """La hipótesis elegida viendo un mes histórico actualiza el mes abierto."""
        app = self.app()
        app.selectbox[2].set_value("2026-09").run()
        app.selectbox[3].set_value("CRECIMIENTO").run()
        self.assertFalse(app.exception)
        self.assertEqual(self.engine(app).status()["scenario"], "CRECIMIENTO")
        # El motor aplica el preload al mes abierto aunque se elija viendo otro mes.
        app.selectbox[2].set_value("2026-10").run()
        eng = self.engine(app)
        self.assertEqual(eng.lags(), (8, 12, 17))
        self.assertEqual([n.value for n in app.number_input], [8, 12, 17])
        self.assertEqual(app.selectbox[3].value, "CRECIMIENTO")
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2026-10"]
        self.assertEqual(
            (features["ventas_hace_3_meses"], features["ventas_hace_2_meses"],
             features["ventas_mes_anterior"]),
            eng.lags(),
        )

    def test_generate_requires_emission_and_is_stable_across_reruns(self):
        app = self.app()
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.emit(app)
        generate = self.button(app, "GENERAR SIGUIENTE MES")
        self.assertFalse(generate.disabled)
        generate.click().run()
        self.assertFalse(app.exception)
        first = self.engine(app).pending_observed()
        self.assertIsNotNone(first)
        self.assertEqual(self.journal(app).revealed[(1, 5, "2026-10")], first)
        # Un rerun no consume azar ni cambia el resultado generado.
        app.run()
        app.run()
        self.assertEqual(self.engine(app).pending_observed(), first)
        self.assertEqual(self.journal(app).revealed[(1, 5, "2026-10")], first)
        # La misma secuencia en una sesión fresca (seed 42) reproduce el valor.
        fresh = create_session()
        fresh.select(1, 5)
        self.assertEqual(fresh.generate_observed(), first)

    def test_close_and_advance_move_clock_once_with_lag_shift(self):
        app = self.app()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        observed = self.engine(app).pending_observed()
        self.assertFalse(self.button(app, "AVANZAR MES").disabled)
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)
        eng = self.engine(app)
        state = eng.status()
        self.assertEqual(state["open_month"], "2026-11")
        self.assertEqual(state["viewing_month"], "2026-11")
        self.assertEqual(eng.closed_months(), ("2026-10",))
        self.assertIsNone(eng.pending_observed())
        self.assertEqual(self.journal(app).closed[(1, 5, "2026-10")].observed, observed)
        self.assertEqual(app.selectbox[2].value, "2026-11")
        # La historia se desplaza un mes: el observado entra como lag1 (26/18/22 → 18/22/observado).
        expected = (
            self.reference.history[(1, 5, "2026-08")],
            self.reference.history[(1, 5, "2026-09")],
            observed,
        )
        self.assertEqual(len(app.number_input), 3)
        self.assertEqual(tuple(n.value for n in app.number_input), expected)
        # El nuevo mes queda abierto: sin doble avance, cierre ni generación sola.
        self.assertTrue(self.button(app, "AVANZAR MES").disabled)
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.assertFalse(self.button(app, "REGISTRAR ABSTENCIÓN").disabled)

    def test_manual_observed_syncs_engine_and_journal_close(self):
        app = self.app()
        self.emit(app)
        app.number_input[-1].set_value(20).run()
        self.assertEqual(self.engine(app).pending_observed(), 20)
        self.assertEqual(self.journal(app).revealed[(1, 5, "2026-10")], 20)
        app.checkbox[-1].check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(self.engine(app).is_closed("2026-10"))
        self.assertEqual(self.journal(app).closed[(1, 5, "2026-10")].observed, 20)
        # AVANZAR cierra solo el reloj: el diario ya registró el cierre sin duplicar.
        self.assertFalse(self.button(app, "AVANZAR MES").disabled)
        self.button(app, "AVANZAR MES").click().run()
        self.assertEqual(self.engine(app).status()["open_month"], "2026-11")
        self.assertEqual(len(self.journal(app).closed), 1)

    def test_features_never_include_target_or_future_months(self):
        app = self.app()
        app.selectbox[2].set_value("2025-01").run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2025-01"]
        self.assertEqual(features["ventas_hace_3_meses"], self.reference.history[(1, 5, "2024-10")])
        self.assertEqual(features["ventas_hace_2_meses"], self.reference.history[(1, 5, "2024-11")])
        self.assertEqual(features["ventas_mes_anterior"], self.reference.history[(1, 5, "2024-12")])
        self.assertNotIn("target_ventas_mes", features)
        # El observado de 2026-10 solo entra como lag1 del mes siguiente, no como target.
        app.selectbox[2].set_value("2026-10").run()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        observed = self.engine(app).pending_observed()
        self.button(app, "AVANZAR MES").click().run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2026-11"]
        self.assertEqual(features["ventas_mes_anterior"], observed)
        self.assertEqual(features["ventas_hace_2_meses"], self.reference.history[(1, 5, "2026-09")])
        self.assertEqual(features["ventas_hace_3_meses"], self.reference.history[(1, 5, "2026-08")])

    def test_scenario_change_after_advance_is_rejected_with_explicit_reset(self):
        app = self.app()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        observed = self.engine(app).pending_observed()
        self.button(app, "AVANZAR MES").click().run()
        app.selectbox[3].set_value("CRECIMIENTO").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox[3].value, "NORMAL")
        self.assertEqual(self.engine(app).status()["scenario"], "NORMAL")
        self.assertTrue(any("Restablece la simulación" in e.value for e in app.error))
        # Sin precarga aplicada: los lags siguen siendo la historia de la sesión.
        self.assertEqual(
            [n.value for n in app.number_input],
            [self.reference.history[(1, 5, "2026-08")],
             self.reference.history[(1, 5, "2026-09")], observed],
        )

    def test_new_product_requires_abstention_before_generate(self):
        app = self.app()
        app.selectbox[3].set_value("PRODUCTO NUEVO").run()
        self.assertTrue(any("HISTORIAL INSUFICIENTE" in w.value for w in app.warning))
        self.assertEqual(self.engine(app).status()["history_status"], "HISTORIAL INSUFICIENTE")
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.emit(app)
        self.assertFalse(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        eng = self.engine(app)
        self.assertIsNotNone(eng.pending_observed())
        self.assertEqual(eng.status()["history_status"], "HISTORIAL INSUFICIENTE")
        self.assertEqual(eng.history_series(), ())

    def test_stockout_detail_is_shown_after_generate(self):
        app = self.app()
        app.selectbox[3].set_value("STOCKOUT").run()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        detail = self.engine(app).generation_detail()
        self.assertIsNotNone(detail)
        self.assertEqual(detail["observed"], min(detail["latent"], detail["availability"]))
        self.assertTrue(any(
            "STOCKOUT" in c.value and "disponibilidad" in c.value for c in app.caption
        ))

    def test_manual_stockout_above_availability_is_rejected_without_reveal(self):
        app = self.app()
        app.selectbox[3].set_value("STOCKOUT").run()
        self.emit(app)
        app.number_input[-1].set_value(10000).run()
        self.assertFalse(app.exception)
        self.assertIsNone(self.engine(app).pending_observed())
        self.assertFalse(self.journal(app).revealed)
        self.assertTrue(any("disponibilidad" in e.value for e in app.error))
        self.assertIsNone(app.number_input[-1].value)

    def test_emissions_survive_reruns_without_duplicate(self):
        app = self.app(runtime=True)
        self.button(app, "PREDECIR").click().run()
        pending = self.journal(app).pending
        self.assertEqual(len(pending), 1)
        issued_at = next(iter(pending.values())).issued_at
        app.run()
        app.run()
        self.assertEqual(len(self.journal(app).pending), 1)
        self.assertEqual(next(iter(self.journal(app).pending.values())).issued_at, issued_at)
        self.button(app, "PREDECIR").click().run()
        self.assertEqual(len(self.journal(app).pending), 1)

    def test_reset_restores_clock_journal_and_seed(self):
        app = self.app()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        first = self.engine(app).pending_observed()
        self.button(app, "AVANZAR MES").click().run()
        self.assertEqual(self.engine(app).status()["open_month"], "2026-11")
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        state = self.engine(app).status()
        self.assertEqual(state["open_month"], "2026-10")
        self.assertEqual(state["closed_months"], ())
        self.assertIsNone(state["pending_observed"])
        self.assertEqual(app.selectbox[2].value, "2026-10")
        self.assertFalse(self.journal(app).closed)
        self.assertFalse(self.journal(app).pending)
        self.assertEqual([n.value for n in app.number_input],
                         [self.reference.history[(1, 5, m)]
                          for m in ("2026-07", "2026-08", "2026-09")])
        # El seed reproducido vuelve a producir la misma primera muestra.
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.assertEqual(self.engine(app).pending_observed(), first)

    def test_sessions_and_pairs_stay_isolated(self):
        first, second = self.app(), self.app()
        self.assertIsNot(self.engine(first), self.engine(second))
        self.emit(first)
        self.button(first, "GENERAR SIGUIENTE MES").click().run()
        self.assertIsNotNone(self.engine(first).pending_observed())
        self.assertIsNone(self.engine(second).pending_observed())
        self.assertFalse(self.journal(second).pending)
        self.assertFalse(self.journal(second).revealed)
        # Cambiar de par no traslada reloj, cierres ni observados.
        first.selectbox[1].set_value(6).run()
        state = self.engine(first).status()
        self.assertEqual(state["location_id"], 6)
        self.assertEqual(state["open_month"], "2026-10")
        self.assertEqual(state["closed_months"], ())
        self.assertIsNone(state["pending_observed"])
        self.assertIn((1, 5, "2026-10"), self.journal(first).revealed)

    def test_full_flow_keeps_dataset_and_catalog_unchanged(self):
        before_dataset = dataset_hashes()
        before_catalog = content_sha256((HERE / "catalog_reference.json").read_bytes())
        app = self.app(runtime=True)
        app.selectbox[3].set_value("CRECIMIENTO").run()
        app.number_input[2].set_value(25).run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        self.button(app, "PREDECIR").click().run()
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.button(app, "AVANZAR MES").click().run()
        app.selectbox[3].set_value("STOCKOUT").run()
        self.assertFalse(app.exception)
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(before_dataset, dataset_hashes())
        self.assertEqual(
            before_catalog, content_sha256((HERE / "catalog_reference.json").read_bytes())
        )


if __name__ == "__main__":
    unittest.main()
