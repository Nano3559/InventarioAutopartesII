"""Streamlit con el proveedor real y artefactos exclusivamente temporales."""
import unittest

from streamlit.testing.v1 import AppTest
from . import test_demand_runtime as fixtures
from simulator_inputs import HERE


class RuntimeStreamlitTests(unittest.TestCase):
    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def app(self):
        return AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30)

    def test_real_provider_fixture_prediction_reset_and_isolation(self):
        fixture = fixtures.RuntimeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.promote()
        app = self.app()
        app.session_state["h4_runtime"] = fixture.runtime
        app.run()
        self.assertFalse(app.exception)
        self.button(app, "PREDECIR").click().run()
        self.assertFalse(app.exception)
        journal = app.session_state["observation_journal"]
        forecast = next(iter(journal.pending.values()))
        self.assertIsNotNone(forecast.prediction)
        fixture.runtime.rollback("revertir fixture")
        self.assertIsNotNone(forecast.prediction)
        self.assertIsNotNone(forecast.model)
        other = self.app().run()
        self.assertIsNone(other.session_state["h4_runtime"].get_active_model())
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        self.assertIsNot(app.session_state["h4_runtime"], fixture.runtime)
        self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
        self.assertFalse(app.session_state["observation_journal"].pending)
        self.assertIsNotNone(forecast.prediction)

    def test_reconnect_starts_inactive(self):
        app = self.app().run()
        previous = app.session_state["h4_runtime"]
        self.button(app, "RECONECTAR RUNTIME").click().run()
        self.assertFalse(app.exception)
        self.assertIsNot(app.session_state["h4_runtime"], previous)
        self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
