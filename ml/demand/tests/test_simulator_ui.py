"""Pruebas de Ross: entradas e interacción sin generar datos ni entrenar."""
import hashlib
import math
import unittest
from pathlib import Path

from simulator_inputs import (
    FEATURE_NAMES, HERE, InputError, MAX_UI_QUANTITY,
    build_inputs, load_reference, offset_month, parse_month, validate_quantity,
)
from streamlit.testing.v1 import AppTest


def protected_hashes():
    paths = list((HERE / "data").rglob("*")) + [
        HERE / "catalog_reference.json", HERE / "generate_synthetic.py",
    ]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths if p.is_file()}


class InputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_reference()

    def test_exact_contract_and_lag_order(self):
        result = build_inputs(self.reference, 1, 5, "2025-01", [8, 10, 12])
        self.assertEqual(tuple(result), FEATURE_NAMES)
        self.assertEqual(list(result.values())[:3], [12, 10, 8])
        self.assertEqual(result["mes_sin"], 0)
        self.assertEqual(result["mes_cos"], 1)
        self.assertNotIn("target_ventas_mes", result)

    def test_reference_and_stores(self):
        self.assertEqual(len(self.reference.products), 56)
        self.assertEqual(set(self.reference.stores), {5, 6, 7})
        self.assertEqual(self.reference.recent(1, 5, "2025-01"),
                         (("2024-10", 28), ("2024-11", 21), ("2024-12", 24)))

    def test_invalid_quantities(self):
        for value in [-1, 1.5, True, False, math.nan, math.inf, "2", MAX_UI_QUANTITY + 1]:
            with self.subTest(value=value), self.assertRaises(InputError):
                validate_quantity(value)
        self.assertEqual(validate_quantity(0), 0)
        self.assertEqual(validate_quantity(MAX_UI_QUANTITY), MAX_UI_QUANTITY)

    def test_invalid_ids_and_reserved_products(self):
        for product, store in [(57, 5), (999, 5), (1, 1), (True, 5), (1, True)]:
            with self.subTest(product=product, store=store), self.assertRaises(InputError):
                build_inputs(self.reference, product, store, "2025-01", [1, 2, 3])

    def test_calendar_boundaries(self):
        self.assertEqual(offset_month("2025-12", 1), "2026-01")
        self.assertEqual(offset_month("2025-01", -1), "2024-12")
        for month in ["2025-13", "2025-00", "2025-1", "0000-01", "no", None]:
            with self.subTest(month=month), self.assertRaises(InputError):
                parse_month(month)
        with self.assertRaises(InputError):
            offset_month("0001-01", -1)

    def test_incomplete_or_missing_history(self):
        for month, values, complete in [
            ("2025-01", [None, 1, 2], True),
            ("2025-01", [1, 2, 3], False),
            ("2027-01", [1, 2, 3], True),
        ]:
            with self.subTest(month=month), self.assertRaises(InputError):
                build_inputs(self.reference, 1, 5, month, values, complete)

    def test_new_product_cannot_bypass_history_with_manual_values(self):
        with self.assertRaisesRegex(InputError, "HISTORIAL INSUFICIENTE"):
            build_inputs(self.reference, 1, 5, "2025-01", [8, 10, 12], scenario="PRODUCTO NUEVO")

    def test_ids_and_scenario_are_not_features(self):
        first = build_inputs(self.reference, 1, 5, "2025-01", [8, 10, 12])
        second = build_inputs(self.reference, 2, 6, "2025-01", [8, 10, 12], scenario="CRECIMIENTO")
        self.assertEqual(first, second)


class InterfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = protected_hashes()

    @classmethod
    def tearDownClass(cls):
        if cls.before != protected_hashes():
            raise AssertionError("La interfaz modificó datos o el generador histórico")

    def app(self):
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        return app

    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def test_initial_screen_and_pending_actions(self):
        app = self.app()
        self.assertEqual(len(app.selectbox[0].options), 56)
        self.assertEqual(len(app.selectbox[1].options), 3)
        self.assertEqual(len(app.number_input), 3)
        for label in ["PREDECIR", "GENERAR SIGUIENTE MES", "AVANZAR MES"]:
            self.assertTrue(self.button(app, label).disabled)
        self.assertTrue(any("MODELO NO DISPONIBLE" in w.value for w in app.warning))

    def test_edit_and_validate_actual_values(self):
        app = self.app()
        for widget, value in zip(app.number_input, [8, 12, 25]):
            widget.set_value(value)
        app.run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        self.assertEqual(len(app.exception), 0)
        result = next(iter(app.session_state["validated"].values()))
        self.assertEqual(list(result.values())[:3], [25, 12, 8])
        self.assertEqual(len(result), 5)
        self.assertEqual(len(app.success), 1)

    def test_edit_invalidates_confirmation(self):
        app = self.app()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        self.assertTrue(app.session_state["validated"])
        app.number_input[0].set_value(99).run()
        self.assertFalse(app.session_state["validated"])
        self.assertEqual(len(app.success), 0)

    def test_pair_drafts_are_independent_and_restored(self):
        app = self.app()
        app.number_input[0].set_value(123).run()
        app.selectbox[1].set_value(6).run()
        self.assertNotEqual(app.number_input[0].value, 123)
        app.selectbox[1].set_value(5).run()
        self.assertEqual(app.number_input[0].value, 123)
        self.assertEqual(len(app.exception), 0)

    def test_month_reloads_appropriate_history_and_calendar(self):
        app = self.app()
        app.selectbox[2].set_value("2025-01").run()
        self.assertEqual([n.value for n in app.number_input], [28, 21, 24])
        self.button(app, "VALIDAR ENTRADAS").click().run()
        result = next(iter(app.session_state["validated"].values()))
        self.assertEqual(result["mes_cos"], 1)

    def test_ambiguous_cases_block_validation(self):
        app = self.app()
        app.selectbox[3].set_value("PRODUCTO NUEVO").run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        self.assertFalse(app.session_state["validated"])
        self.assertTrue(any("HISTORIAL INSUFICIENTE" in w.value for w in app.warning))
        app.selectbox[3].set_value("NORMAL").run()
        app.checkbox[0].uncheck().run()
        self.assertTrue(any("DATOS INCOMPLETOS" in w.value for w in app.warning))

    def test_sessions_are_independent(self):
        first, second = self.app(), self.app()
        original = second.number_input[0].value
        first.number_input[0].set_value(321).run()
        second.run()
        self.assertEqual(second.number_input[0].value, original)

    def test_reset_restores_original_reference(self):
        app = self.app()
        original = [n.value for n in app.number_input]
        app.number_input[0].set_value(987).run()
        app.selectbox[1].set_value(6).run()
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertEqual([n.value for n in app.number_input], original)
        self.assertEqual(app.selectbox[1].value, 5)
        self.assertFalse(app.session_state["validated"])
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
