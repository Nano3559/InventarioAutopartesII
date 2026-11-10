"""Pruebas del motor de simulación H4: reloj, escenarios, lags y observados."""
import unittest

from demand_engine import SCENARIO_PRELOADS, create_session
from simulator_inputs import HERE, SCENARIOS, content_sha256


def dataset_hashes():
    folder = HERE / "data" / "escenarios_v1_1"
    return {
        path.name: content_sha256(path.read_bytes())
        for path in sorted(folder.iterdir()) if path.is_file()
    }


class HistoryLoadingTests(unittest.TestCase):
    def test_history_loading(self):
        session = create_session()
        session.select(1, 5)
        series = session.history_series()
        self.assertEqual(len(series), 24)
        self.assertEqual(series[0][0], "2024-10")
        self.assertEqual(series[-1][0], "2026-09")
        for month, value in series:
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)
        recent = session.recent_history()
        self.assertEqual(len(recent), 3)
        self.assertEqual([m for m, _ in recent], ["2026-07", "2026-08", "2026-09"])
        for _, value in recent:
            self.assertIsInstance(value, int)
        self.assertEqual(session.history_status(), "COMPLETO")


class SelectionTests(unittest.TestCase):
    def test_selection(self):
        session = create_session()
        with self.assertRaises(Exception):
            session.select(999999, 5)
        with self.assertRaises(Exception):
            session.select(1, 1)
        with self.assertRaises(Exception):
            session.select_month("2024-10")
        session.select(1, 5)
        self.assertEqual(session.status()["product_id"], 1)
        self.assertEqual(session.status()["location_id"], 5)
        self.assertEqual(session.status()["open_month"], "2026-10")
        session.select(2, 6)
        self.assertEqual(session.status()["product_id"], 2)
        self.assertEqual(session.status()["location_id"], 6)
        self.assertIn("2026-10", session.selectable_months())
        self.assertNotIn("2026-11", session.selectable_months())
        session.select_month("2025-01")
        self.assertEqual(session.status()["viewing_month"], "2025-01")
        with self.assertRaises(Exception):
            session.select_month("2099-01")
        with self.assertRaises(Exception):
            session.select_month("no-month")


class IsolationTests(unittest.TestCase):
    def test_sessions_and_pairs_are_isolated(self):
        first = create_session()
        second = create_session()
        first.select(1, 5)
        second.select(1, 5)
        first.apply_scenario("CRECIMIENTO")
        first.edit_lags(99, 98, 97)
        first.generate_observed()
        self.assertEqual(
            second.lags(),
            tuple(value for _, value in second.recent_history()),
        )
        self.assertIsNone(second.pending_observed())
        self.assertEqual(second.closed_months(), ())
        self.assertNotEqual(first.session_id, second.session_id)
        shared = create_session()
        shared.select(1, 5)
        shared.edit_lags(5, 5, 5)
        shared.select(2, 6)
        self.assertNotEqual(shared.lags(), (5, 5, 5))
        shared.select(1, 5)
        self.assertEqual(shared.lags(), (5, 5, 5))


class ReproducibilityTests(unittest.TestCase):
    @staticmethod
    def _run_sequence():
        session = create_session()
        session.select(1, 5)
        session.apply_scenario("NORMAL")
        observed = []
        for _ in range(3):
            observed.append(session.generate_observed())
            session.close_month()
            session.advance_month()
        return observed, session.closed_months()

    def test_same_actions_reproduce_same_results(self):
        first = self._run_sequence()
        second = self._run_sequence()
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 3)
        self.assertEqual(first[1], ("2026-10", "2026-11", "2026-12"))


class ScenarioTests(unittest.TestCase):
    def test_all_eight_scenarios_apply(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                session = create_session()
                session.select(1, 5)
                session.apply_scenario(scenario)
                self.assertEqual(session.status()["scenario"], scenario)
                self.assertEqual(session.lags(), SCENARIO_PRELOADS[scenario])
                session.generate_observed()
                self.assertIsNotNone(session.pending_observed())
                session.close_month()
                self.assertEqual(session.closed_months(), ("2026-10",))
        with self.assertRaises(Exception):
            session = create_session()
            session.select(1, 5)
            session.apply_scenario("NO_EXISTE")

    def test_scenario_change_blocked_after_close_or_pending(self):
        session = create_session()
        session.select(1, 5)
        session.generate_observed()
        with self.assertRaises(Exception):
            session.apply_scenario("CAÍDA")
        session.close_month()
        with self.assertRaises(Exception):
            session.apply_scenario("NORMAL")
        session.reset()
        session.select(1, 5)
        session.apply_scenario("CAÍDA")
        self.assertEqual(session.status()["scenario"], "CAÍDA")


class LagEditingTests(unittest.TestCase):
    def test_edit_and_reset_lags(self):
        session = create_session()
        session.select(1, 5)
        original = session.lags()
        session.edit_lags(1, 2, 3)
        self.assertEqual(session.lags(), (1, 2, 3))
        session.reset_lags()
        self.assertEqual(session.lags(), original)
        session.select_month("2025-06")
        with self.assertRaises(Exception):
            session.edit_lags(4, 5, 6)
        session.select_month(session.status()["open_month"])
        session.edit_lags(7, 8, 9)
        session.generate_observed()
        session.close_month()
        with self.assertRaises(Exception):
            session.edit_lags(1, 1, 1)
        with self.assertRaises(Exception):
            session.reset_lags()


class InvalidQuantityTests(unittest.TestCase):
    def test_invalid_quantities_are_rejected(self):
        session = create_session()
        session.select(1, 5)
        invalid_lags = [
            (-1, 10, 10), (10, -1, 10), (10, 10, -1),
            (1.5, 10, 10), (10, 2.5, 10), (10, 10, 3.7),
            (True, 10, 10), (10, False, 10),
            ("10", 10, 10), (10, "8", 10), (10, 10, None),
            (float("nan"), 10, 10), (10, float("inf"), 10),
        ]
        for values in invalid_lags:
            with self.subTest(values=values):
                with self.assertRaises(Exception):
                    session.edit_lags(*values)
        for value in (-1, 1.5, True, "7", None, float("nan")):
            with self.subTest(value=value):
                with self.assertRaises(Exception):
                    session.set_manual_observed(value)
        self.assertEqual(session.lags(), tuple(v for _, v in session.recent_history()))


class MissingMonthTests(unittest.TestCase):
    def test_missing_months_report_status(self):
        session = create_session()
        session.select(1, 5)
        session.select_month("2024-10")
        self.assertEqual(session.history_status(), "HISTORIAL INSUFICIENTE")
        session.select_month("2024-11")
        self.assertEqual(session.history_status(), "DATOS INCOMPLETOS")
        session.select_month("2024-12")
        self.assertEqual(session.history_status(), "DATOS INCOMPLETOS")
        session.select_month("2025-01")
        self.assertEqual(session.history_status(), "COMPLETO")
        session.select_month("2026-10")
        self.assertEqual(session.history_status(), "COMPLETO")


class NewProductTests(unittest.TestCase):
    def test_product_new_ignores_reference_until_three_closes(self):
        session = create_session()
        session.select(1, 5)
        session.apply_scenario("PRODUCTO NUEVO")
        self.assertEqual(session.history_status(), "HISTORIAL INSUFICIENTE")
        self.assertEqual(session.history_series(), ())
        session.select_month("2025-01")
        self.assertEqual(session.history_status(), "HISTORIAL INSUFICIENTE")
        session.select_month(session.status()["open_month"])
        for _ in range(3):
            self.assertIn(
                session.history_status(),
                ("HISTORIAL INSUFICIENTE", "DATOS INCOMPLETOS"),
            )
            session.generate_observed()
            session.close_month()
            session.advance_month()
        self.assertEqual(session.status()["open_month"], "2027-01")
        self.assertEqual(session.history_status(), "COMPLETO")
        self.assertEqual(len(session.history_series()), 3)


class StockoutTests(unittest.TestCase):
    def test_stockout_separates_latent_availability_observed(self):
        session = create_session()
        session.select(1, 5)
        session.apply_scenario("STOCKOUT")
        observed = session.generate_observed()
        detail = session.generation_detail()
        self.assertIsNotNone(detail)
        self.assertEqual(detail["observed"], observed)
        self.assertLessEqual(observed, detail["availability"])
        self.assertGreaterEqual(detail["latent"], observed)
        self.assertEqual(observed, min(detail["latent"], detail["availability"]))
        with self.assertRaises(Exception):
            session.set_manual_observed(detail["availability"] + 1)
        session.set_manual_observed(detail["availability"])
        self.assertEqual(session.pending_observed(), detail["availability"])
        session.close_month()
        self.assertEqual(session.closed_months(), ("2026-10",))


class IdempotentGenerationTests(unittest.TestCase):
    def test_generate_observed_is_idempotent(self):
        session = create_session()
        session.select(1, 5)
        first = session.generate_observed()
        second = session.generate_observed()
        third = session.generate_observed()
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        fresh = create_session()
        fresh.select(1, 5)
        self.assertEqual(fresh.generate_observed(), first)
        session.close_month()
        session.advance_month()
        next_first = session.generate_observed()
        fresh.close_month()
        fresh.advance_month()
        self.assertEqual(fresh.generate_observed(), next_first)


class ManualObservedTests(unittest.TestCase):
    def test_manual_observed_registers_and_closes(self):
        session = create_session()
        session.select(1, 5)
        self.assertIsNone(session.pending_observed())
        session.set_manual_observed(7)
        self.assertEqual(session.pending_observed(), 7)
        session.set_manual_observed(8)
        self.assertEqual(session.pending_observed(), 8)
        session.close_month()
        self.assertIsNone(session.pending_observed())
        self.assertEqual(session.closed_months(), ("2026-10",))
        self.assertTrue(session.is_closed("2026-10"))
        with self.assertRaises(Exception):
            session.set_manual_observed(9)


class MonthlyAdvanceTests(unittest.TestCase):
    def test_generate_close_advance_cycle(self):
        session = create_session()
        session.select(1, 5)
        self.assertEqual(session.status()["open_month"], "2026-10")
        session.generate_observed()
        session.close_month()
        session.advance_month()
        self.assertEqual(session.status()["open_month"], "2026-11")
        self.assertEqual(session.closed_months(), ("2026-10",))
        session.set_manual_observed(4)
        session.close_month()
        session.advance_month()
        self.assertEqual(session.status()["open_month"], "2026-12")
        self.assertEqual(session.closed_months(), ("2026-10", "2026-11"))
        with self.assertRaises(Exception):
            session.close_month()
        with self.assertRaises(Exception):
            session.advance_month()


class DecemberToJanuaryTests(unittest.TestCase):
    def test_advance_from_december_to_january(self):
        session = create_session()
        session.select(1, 5)
        for expected in ("2026-10", "2026-11", "2026-12"):
            self.assertEqual(session.status()["open_month"], expected)
            session.generate_observed()
            session.close_month()
            session.advance_month()
        self.assertEqual(session.status()["open_month"], "2027-01")
        self.assertEqual(session.status()["viewing_month"], "2027-01")
        recent = session.recent_history()
        self.assertEqual([m for m, _ in recent], ["2026-10", "2026-11", "2026-12"])
        for _, value in recent:
            self.assertIsInstance(value, int)
        session.generate_observed()
        session.close_month()
        session.advance_month()
        self.assertEqual(session.status()["open_month"], "2027-02")
        self.assertIn("2027-01", session.selectable_months())


class LagShiftTests(unittest.TestCase):
    def test_lags_shift_after_close_and_advance(self):
        session = create_session()
        session.select(1, 5)
        initial = session.lags()
        self.assertEqual(len(initial), 3)
        self.assertTrue(all(isinstance(v, int) for v in initial))
        session.generate_observed()
        observed = session.pending_observed()
        session.close_month()
        session.advance_month()
        self.assertEqual(session.lags(), (initial[1], initial[2], observed))
        session.generate_observed()
        second_observed = session.pending_observed()
        session.close_month()
        session.advance_month()
        self.assertEqual(
            session.lags(),
            (initial[2], observed, second_observed),
        )


class DoubleCloseTests(unittest.TestCase):
    def test_double_close_and_double_advance_are_rejected(self):
        session = create_session()
        session.select(1, 5)
        with self.assertRaises(Exception):
            session.close_month()
        session.generate_observed()
        session.close_month()
        with self.assertRaises(Exception):
            session.close_month()
        with self.assertRaises(Exception):
            session.generate_observed()
        with self.assertRaises(Exception):
            session.set_manual_observed(1)
        session.advance_month()
        with self.assertRaises(Exception):
            session.advance_month()
        with self.assertRaises(Exception):
            session.close_month()


class ResetTests(unittest.TestCase):
    def test_reset_clears_state_and_reseeds(self):
        session = create_session()
        session.select(1, 5)
        session.apply_scenario("CRECIMIENTO")
        session.edit_lags(3, 4, 5)
        session.generate_observed()
        session.close_month()
        session.advance_month()
        session.reset()
        with self.assertRaises(Exception):
            session.pending_observed()
        with self.assertRaises(Exception):
            session.closed_months()
        self.assertIsNone(session.status()["product_id"])

        def sequence(target):
            target.select(1, 5)
            target.apply_scenario("NORMAL")
            values = []
            for _ in range(2):
                values.append(target.generate_observed())
                target.close_month()
                target.advance_month()
            return values

        first = sequence(session)
        session.reset()
        second = sequence(session)
        self.assertEqual(first, second)
        self.assertEqual(first, sequence(create_session()))


class DatasetImmutabilityTests(unittest.TestCase):
    def test_dataset_files_are_unchanged(self):
        before = dataset_hashes()
        catalog_before = content_sha256((HERE / "catalog_reference.json").read_bytes())
        session = create_session()
        session.select(1, 5)
        session.apply_scenario("CRECIMIENTO")
        session.edit_lags(11, 12, 13)
        session.generate_observed()
        session.close_month()
        session.advance_month()
        session.set_manual_observed(6)
        session.close_month()
        session.advance_month()
        session.select_month("2025-03")
        session.history_series()
        session.reset()
        session.select(56, 7)
        session.apply_scenario("STOCKOUT")
        session.generate_observed()
        after = dataset_hashes()
        catalog_after = content_sha256((HERE / "catalog_reference.json").read_bytes())
        self.assertEqual(before, after)
        self.assertEqual(catalog_before, catalog_after)


if __name__ == "__main__":
    unittest.main()
