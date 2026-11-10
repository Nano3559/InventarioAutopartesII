"""Validación funcional integral del simulador H4: 21 comprobaciones obligatorias."""
import math
import unittest

import pandas as pd

from demand_engine import SCENARIO_PRELOADS, create_session
from simulator_inputs import FEATURE_NAMES, HERE, SCENARIOS, InputError, load_reference
from streamlit.testing.v1 import AppTest

from .test_engine_integration import dataset_hashes
from .test_ross_ui import FakeRuntime
from .test_simulator_ui import protected_hashes


class FitCountingRuntime(FakeRuntime):
    """Doble que cuenta fit: la interfaz nunca debe llamar a entrenar."""

    def __init__(self):
        super().__init__()
        self.fit_calls = 0

    def fit(self, *args, **kwargs):
        self.fit_calls += 1
        raise AssertionError("La UI nunca debe entrenar")


class SimulatorValidationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_reference()
        cls.before_protected = protected_hashes()
        cls.before_dataset = dataset_hashes()

    @classmethod
    def tearDownClass(cls):
        if cls.before_protected != protected_hashes():
            raise AssertionError("La validación modificó datos protegidos o el generador")
        if cls.before_dataset != dataset_hashes():
            raise AssertionError("La validación modificó el dataset 1.1")

    def app(self, runtime=False):
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30)
        if runtime:
            app.session_state["h4_runtime"] = FitCountingRuntime()
        app.run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def engine(self, app):
        return app.session_state["demand_session"]

    def journal(self, app):
        return app.session_state["observation_journal"]

    def lags(self, app):
        return [n.value for n in app.number_input[:3]]

    def emit(self, app):
        self.button(app, "REGISTRAR ABSTENCIÓN").click().run()
        self.assertFalse(app.exception)

    def chart_frame(self, app):
        for element in app.dataframe:
            frame = element.value
            if not hasattr(frame, "columns"):
                frame = pd.DataFrame(frame)
            if "Edición local" in frame.columns:
                return frame
        self.fail("La tabla del gráfico Historia/Edición no está disponible")

    def advance_cycle(self, app):
        """Emisión, generación y avance completos de un mes."""
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.assertFalse(app.exception)
        observed = self.engine(app).pending_observed()
        self.assertIsNotNone(observed)
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)
        return observed

    def test_01_la_aplicacion_abre_sin_excepciones(self):
        app = self.app()
        self.assertTrue(any("Simulador de ventas" in t.value for t in app.title))
        self.assertTrue(any("SIMULACIÓN" in c.value for c in app.caption))
        reloj = [c.value for c in app.caption if "Reloj de simulación" in c.value]
        self.assertTrue(reloj)
        self.assertIn("abierto 2026-10", reloj[0])
        self.assertIn("escenario NORMAL", reloj[0])
        self.assertEqual(len(app.selectbox), 4)
        self.assertTrue(any("origen SIMULACIÓN" in i.value for i in app.info)
                        or any("SIMULACIÓN" in c.value for c in app.caption))

    def test_02_selectores_muestran_la_serie_elegida(self):
        app = self.app()
        app.selectbox[0].set_value(4).run()
        self.assertFalse(app.exception)
        self.assertEqual(self.lags(app), [12, 12, 9])
        self.assertTrue(any(
            "productId: 4 · locationId: 5" in c.value for c in app.caption
        ))
        app.selectbox[1].set_value(6).run()
        self.assertFalse(app.exception)
        esperado = [v for _, v in self.reference.recent(4, 6, "2026-10")]
        self.assertEqual(self.lags(app), esperado)
        self.assertTrue(any(
            "productId: 4 · locationId: 6" in c.value for c in app.caption
        ))

    def test_03_los_ocho_escenarios_precargan_en_el_editor_y_el_motor(self):
        app = self.app()
        self.assertEqual(list(app.selectbox[3].options), list(SCENARIOS))
        self.assertEqual(len(app.selectbox[3].options), 8)
        orden = [
            "CRECIMIENTO", "CAÍDA", "PICO MAYORISTA", "STOCKOUT",
            "CAMBIO PERSISTENTE", "RECUPERACIÓN", "NORMAL", "PRODUCTO NUEVO",
        ]
        for scenario in orden:
            with self.subTest(scenario=scenario):
                app.selectbox[3].set_value(scenario).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox[3].value, scenario)
                eng = self.engine(app)
                self.assertEqual(eng.status()["scenario"], scenario)
                self.assertTrue(any(
                    f"escenario {scenario}" in c.value for c in app.caption
                ))
                preload = SCENARIO_PRELOADS[scenario]
                if scenario == "PRODUCTO NUEVO":
                    self.assertEqual(eng.lags(), (None, None, None))
                    self.assertEqual(eng.status()["history_status"], "HISTORIAL INSUFICIENTE")
                    self.assertEqual(self.lags(app), [10, 10, 10])
                    self.assertTrue(any(
                        "HISTORIAL INSUFICIENTE" in w.value for w in app.warning
                    ))
                else:
                    self.assertEqual(eng.lags(), preload)
                    self.assertEqual(self.lags(app), list(preload))

    def test_04_editar_tres_lags_y_validar_produce_exactamente_cinco_features(self):
        app = self.app()
        app.number_input[0].set_value(30).run()
        app.number_input[1].set_value(40).run()
        app.number_input[2].set_value(50).run()
        self.assertFalse(app.exception)
        self.button(app, "VALIDAR ENTRADAS").click().run()
        self.assertTrue(any("Entradas validadas" in s.value for s in app.success))
        features = app.session_state["validated"]["1_5_2026-10"]
        self.assertEqual(tuple(features), FEATURE_NAMES)
        self.assertEqual(len(features), 5)
        self.assertEqual(features["ventas_hace_3_meses"], 30)
        self.assertEqual(features["ventas_hace_2_meses"], 40)
        self.assertEqual(features["ventas_mes_anterior"], 50)
        self.assertAlmostEqual(features["mes_sin"], math.sin(2 * math.pi * 9 / 12), places=9)
        self.assertAlmostEqual(features["mes_cos"], math.cos(2 * math.pi * 9 / 12), places=9)
        self.assertNotIn("target_ventas_mes", features)

    def test_05_las_entradas_validadas_siempre_iguales_al_motor(self):
        app = self.app()
        app.number_input[0].set_value(31).run()
        app.number_input[1].set_value(41).run()
        app.number_input[2].set_value(51).run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2026-10"]
        self.assertEqual(
            (features["ventas_hace_3_meses"], features["ventas_hace_2_meses"],
             features["ventas_mes_anterior"]),
            self.engine(app).lags(),
        )
        app.selectbox[3].set_value("CRECIMIENTO").run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2026-10"]
        self.assertEqual(
            (features["ventas_hace_3_meses"], features["ventas_hace_2_meses"],
             features["ventas_mes_anterior"]),
            self.engine(app).lags(),
        )
        app.selectbox[2].set_value("2026-09").run()
        app.selectbox[3].set_value("CAÍDA").run()
        app.selectbox[2].set_value("2026-10").run()
        self.assertEqual(self.lags(app), [17, 12, 8])
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2026-10"]
        self.assertEqual(
            (features["ventas_hace_3_meses"], features["ventas_hace_2_meses"],
             features["ventas_mes_anterior"]),
            self.engine(app).lags(),
        )

    def test_06_el_grafico_distingue_historia_de_sesion_y_edicion_local(self):
        app = self.app()
        historia = [self.reference.history[(1, 5, m)] for m in ("2026-07", "2026-08", "2026-09")]
        frame = self.chart_frame(app)
        self.assertEqual(list(frame["Mes"]), ["2026-07", "2026-08", "2026-09"])
        self.assertEqual(list(frame["Historia de sesión"]), historia)
        self.assertEqual(list(frame["Edición local"]), historia)
        app.number_input[2].set_value(99).run()
        self.assertFalse(app.exception)
        frame = self.chart_frame(app)
        self.assertEqual(list(frame["Historia de sesión"]), historia)
        self.assertEqual(list(frame["Edición local"]), [historia[0], historia[1], 99])
        self.assertNotEqual(
            list(frame["Historia de sesión"]), list(frame["Edición local"])
        )

    def test_07_predecir_con_doble_no_entrena_y_congela_las_entradas(self):
        app = self.app(runtime=True)
        rt = app.session_state["h4_runtime"]
        self.button(app, "VALIDAR ENTRADAS").click().run()
        validated = app.session_state["validated"]["1_5_2026-10"]
        self.button(app, "PREDECIR").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(rt.fit_calls, 0)
        self.assertEqual(len(rt.calls), 1)
        self.assertEqual(rt.calls[0], validated)
        self.assertEqual(set(rt.calls[0]), set(FEATURE_NAMES))
        pending = self.journal(app).pending
        self.assertEqual(len(pending), 1)
        forecast = pending[(1, 5, "2026-10")]
        self.assertEqual(forecast.prediction, 17.5)
        self.assertEqual(forecast.model.label, "DOBLE DE PRUEBA · TEST-v1 · aaaaaaaa")
        self.assertEqual(forecast.scenario, "NORMAL")
        self.assertTrue(any(
            "Versión congelada de esta emisión" in c.value for c in app.caption
        ))
        app.run()
        self.assertEqual(len(self.journal(app).pending), 1)
        self.assertEqual(rt.fit_calls, 0)

    def test_08_sin_runtime_se_muestra_modelo_no_disponible(self):
        app = self.app()
        self.assertTrue(any("MODELO NO DISPONIBLE" in w.value for w in app.warning))
        self.assertTrue(self.button(app, "PREDECIR").disabled)
        self.assertFalse(self.button(app, "REGISTRAR ABSTENCIÓN").disabled)
        self.assertFalse(self.button(app, "RECONECTAR RUNTIME").disabled)

    def test_09_la_abstencion_se_registra_sin_prediccion_ficticia(self):
        app = self.app()
        self.emit(app)
        pending = self.journal(app).pending
        self.assertEqual(len(pending), 1)
        forecast = pending[(1, 5, "2026-10")]
        self.assertIsNone(forecast.prediction)
        self.assertIsNone(forecast.model)
        self.assertEqual(forecast.reason, "MODELO NO DISPONIBLE")
        self.assertIsNone(forecast.features)
        self.assertTrue(any(
            "Abstención registrada" in i.value for i in app.info
        ))
        self.assertTrue(self.button(app, "PREDECIR").disabled)

    def test_10_el_observado_generado_es_idempotente_y_reproducible_con_seed_42(self):
        app = self.app()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        first = self.engine(app).pending_observed()
        self.assertIsNotNone(first)
        self.assertEqual(self.journal(app).revealed[(1, 5, "2026-10")], first)
        app.run()
        app.run()
        self.assertEqual(self.engine(app).pending_observed(), first)
        self.assertEqual(self.journal(app).revealed[(1, 5, "2026-10")], first)
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        fresh = create_session()
        fresh.select(1, 5)
        self.assertEqual(fresh.generate_observed(), first)

    def test_11_el_observado_manual_se_registra_y_bloquea_las_entradas(self):
        app = self.app()
        self.emit(app)
        self.assertEqual(len(app.number_input), 4)
        app.number_input[-1].set_value(30).run()
        self.assertFalse(app.exception)
        self.assertEqual(self.engine(app).pending_observed(), 30)
        self.assertEqual(self.journal(app).revealed[(1, 5, "2026-10")], 30)
        self.assertTrue(all(n.disabled for n in app.number_input[:3]))
        self.assertTrue(app.number_input[-1].disabled)
        self.assertEqual(app.number_input[-1].value, 30)

    def test_12_cierre_explicito_y_avance_del_reloj(self):
        app = self.app()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        observed = self.engine(app).pending_observed()
        app.checkbox[-1].check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(self.engine(app).is_closed("2026-10"))
        self.assertEqual(self.journal(app).closed[(1, 5, "2026-10")].observed, observed)
        self.assertTrue(any("Mes cerrado" in s.value for s in app.success))
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.assertFalse(self.button(app, "AVANZAR MES").disabled)
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)
        state = self.engine(app).status()
        self.assertEqual(state["open_month"], "2026-11")
        self.assertEqual(state["viewing_month"], "2026-11")
        self.assertEqual(app.selectbox[2].value, "2026-11")
        self.assertEqual(self.engine(app).closed_months(), ("2026-10",))

    def test_13_al_avanzar_los_lags_se_desplazan_y_el_observado_entra_ultimo(self):
        app = self.app()
        observed = self.advance_cycle(app)
        esperado = (
            self.reference.history[(1, 5, "2026-08")],
            self.reference.history[(1, 5, "2026-09")],
            observed,
        )
        self.assertEqual(tuple(self.lags(app)), esperado)
        self.assertEqual(self.engine(app).lags(), esperado)

    def test_14_avance_de_diciembre_a_enero_con_calendario_correcto(self):
        app = self.app()
        o10 = self.advance_cycle(app)
        self.assertEqual(self.engine(app).status()["open_month"], "2026-11")
        o11 = self.advance_cycle(app)
        self.assertEqual(self.engine(app).status()["open_month"], "2026-12")
        o12 = self.advance_cycle(app)
        state = self.engine(app).status()
        self.assertEqual(state["open_month"], "2027-01")
        self.assertEqual(state["viewing_month"], "2027-01")
        self.assertEqual(state["closed_months"], ("2026-10", "2026-11", "2026-12"))
        self.assertEqual(app.selectbox[2].value, "2027-01")
        self.assertIn("Diciembre 2026", app.selectbox[2].options)
        self.assertIn("Enero 2027", app.selectbox[2].options)
        self.assertEqual(tuple(self.lags(app)), (o10, o11, o12))
        self.assertTrue(any("Diciembre 2026" in n.label for n in app.number_input[:3]))
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2027-01"]
        self.assertEqual(features["ventas_mes_anterior"], o12)
        self.assertAlmostEqual(features["mes_sin"], 0.0, places=9)
        self.assertAlmostEqual(features["mes_cos"], 1.0, places=9)

    def test_15_sin_doble_cierre_ni_segunda_muestra(self):
        app = self.app()
        self.emit(app)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        observed = self.engine(app).pending_observed()
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        app.run()
        self.assertEqual(self.engine(app).pending_observed(), observed)
        app.checkbox[-1].check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(self.journal(app).closed), 1)
        with self.assertRaises(InputError):
            self.engine(app).close_month()
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.engine(app).status()["open_month"], "2026-11")
        self.assertEqual(self.engine(app).closed_months(), ("2026-10",))
        self.assertEqual(len(self.journal(app).closed), 1)
        self.assertTrue(self.button(app, "AVANZAR MES").disabled)

    def test_16_stockout_distingue_latente_disponibilidad_y_venta(self):
        app = self.app()
        app.selectbox[3].set_value("STOCKOUT").run()
        self.emit(app)
        app.number_input[-1].set_value(10000).run()
        self.assertFalse(app.exception)
        self.assertTrue(any("disponibilidad" in e.value for e in app.error))
        self.assertIsNone(self.engine(app).pending_observed())
        self.assertFalse(self.journal(app).revealed)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.assertFalse(app.exception)
        detail = self.engine(app).generation_detail()
        self.assertIsNotNone(detail)
        self.assertEqual(detail["observed"], min(detail["latent"], detail["availability"]))
        self.assertTrue(any(
            "STOCKOUT" in c.value and "disponibilidad" in c.value for c in app.caption
        ))
        self.assertEqual(self.journal(app).revealed[(1, 5, "2026-10")], detail["observed"])

    def test_17_producto_nuevo_bloquea_por_historial_insuficiente(self):
        app = self.app()
        app.selectbox[3].set_value("PRODUCTO NUEVO").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("HISTORIAL INSUFICIENTE" in w.value for w in app.warning))
        eng = self.engine(app)
        self.assertEqual(eng.status()["history_status"], "HISTORIAL INSUFICIENTE")
        self.assertTrue(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.emit(app)
        self.assertFalse(self.button(app, "GENERAR SIGUIENTE MES").disabled)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.assertFalse(app.exception)
        self.assertIsNotNone(self.engine(app).pending_observed())
        self.assertEqual(self.engine(app).history_series(), ())
        self.assertEqual(self.engine(app).status()["history_status"], "HISTORIAL INSUFICIENTE")

    def test_18_reset_reproducible_y_sesiones_aisladas(self):
        first, second = self.app(), self.app()
        self.assertIsNot(self.engine(first), self.engine(second))
        self.emit(first)
        self.button(first, "GENERAR SIGUIENTE MES").click().run()
        original = self.engine(first).pending_observed()
        self.assertIsNotNone(original)
        self.assertIsNone(self.engine(second).pending_observed())
        self.assertFalse(self.journal(second).pending)
        self.button(first, "AVANZAR MES").click().run()
        self.assertEqual(self.engine(first).status()["open_month"], "2026-11")
        self.assertEqual(self.engine(second).status()["open_month"], "2026-10")
        self.assertFalse(self.journal(second).closed)
        self.button(first, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(first.exception)
        state = self.engine(first).status()
        self.assertEqual(state["open_month"], "2026-10")
        self.assertEqual(state["closed_months"], ())
        self.assertIsNone(state["pending_observed"])
        self.assertEqual(first.selectbox[2].value, "2026-10")
        self.assertEqual(self.lags(first), [
            self.reference.history[(1, 5, m)] for m in ("2026-07", "2026-08", "2026-09")
        ])
        self.assertFalse(self.journal(first).closed)
        self.emit(first)
        self.button(first, "GENERAR SIGUIENTE MES").click().run()
        self.assertEqual(self.engine(first).pending_observed(), original)

    def test_19_las_features_no_incluyen_el_target_ni_meses_futuros(self):
        app = self.app()
        app.selectbox[2].set_value("2025-01").run()
        self.assertFalse(app.exception)
        labels = [n.label for n in app.number_input[:3]]
        self.assertTrue(any("Octubre 2024" in label for label in labels))
        self.assertTrue(any("Noviembre 2024" in label for label in labels))
        self.assertTrue(any("Diciembre 2024" in label for label in labels))
        self.button(app, "VALIDAR ENTRADAS").click().run()
        features = app.session_state["validated"]["1_5_2025-01"]
        self.assertEqual(set(features), set(FEATURE_NAMES))
        self.assertEqual(features["ventas_hace_3_meses"], self.reference.history[(1, 5, "2024-10")])
        self.assertEqual(features["ventas_hace_2_meses"], self.reference.history[(1, 5, "2024-11")])
        self.assertEqual(features["ventas_mes_anterior"], self.reference.history[(1, 5, "2024-12")])
        self.assertNotIn("target_ventas_mes", features)
        self.assertAlmostEqual(features["mes_sin"], 0.0, places=9)
        self.assertAlmostEqual(features["mes_cos"], 1.0, places=9)

    def test_20_tras_el_cierre_prediccion_y_observado_quedan_inalterables(self):
        app = self.app(runtime=True)
        self.button(app, "VALIDAR ENTRADAS").click().run()
        validated = app.session_state["validated"]["1_5_2026-10"]
        self.button(app, "PREDECIR").click().run()
        self.assertFalse(app.exception)
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        observed = self.engine(app).pending_observed()
        app.checkbox[-1].check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)
        key = (1, 5, "2026-10")
        record = self.journal(app).closed[key]
        self.assertEqual(record.observed, observed)
        self.assertEqual(record.forecast.prediction, 17.5)
        self.assertEqual(
            record.forecast.features,
            tuple(validated[name] for name in FEATURE_NAMES),
        )
        self.assertTrue(any("Mes cerrado" in s.value for s in app.success))
        self.assertTrue(self.button(app, "PREDECIR").disabled)
        self.assertTrue(app.number_input[-1].disabled)
        self.assertEqual(app.number_input[-1].value, observed)
        app.run()
        app.selectbox[1].set_value(6).run()
        app.selectbox[1].set_value(5).run()
        self.assertFalse(app.exception)
        after = self.journal(app).closed[key]
        self.assertEqual(after.observed, observed)
        self.assertEqual(after.forecast.prediction, 17.5)
        self.assertEqual(after.forecast.issued_at, record.forecast.issued_at)
        self.assertEqual(after.forecast.features, record.forecast.features)
        self.assertEqual(self.engine(app).closed_months(), ("2026-10",))
        serie = dict(self.engine(app).history_series())
        self.assertEqual(serie["2026-10"], observed)

    def test_21_el_dataset_y_los_archivos_protegidos_conservan_sus_hashes(self):
        app = self.app(runtime=True)
        app.selectbox[3].set_value("CRECIMIENTO").run()
        app.number_input[2].set_value(33).run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        self.button(app, "PREDECIR").click().run()
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.engine(app).status()["open_month"], "2026-11")
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.before_protected, protected_hashes())
        self.assertEqual(self.before_dataset, dataset_hashes())


if __name__ == "__main__":
    unittest.main()
