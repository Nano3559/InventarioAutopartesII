"""Ejemplo optativo reproducible de Tarea 12; solo observaciones SIMULADAS.

Ejecutar explícitamente crea un CANDIDATE nuevo y conserva los anteriores.
No activa V1 ni evalúa reservas o TEST. Los números son entradas manuales
demostrativas, nunca ventas comerciales.
"""
from datetime import datetime, timezone
import json

from demand_engine import create_session
from simulator_inputs import load_reference
from ui_runtime import Forecast, ObservationJournal
from retraining import RetrainingSession


def run():
    engine = create_session(load_reference())
    journal = ObservationJournal()
    engine.bind_journal(journal.session_id)
    engine.select(1, 5)
    for observed in range(10, 22):
        month = engine.status()["open_month"]
        forecast = Forecast(1, 5, month, None, None, None, None,
                            "MODELO NO DISPONIBLE", datetime.now(timezone.utc).isoformat())
        journal.issue(forecast)
        engine.set_manual_observed(observed)
        engine.close_month()
        journal.close(forecast.key, observed)
        engine.advance_month()
    result = RetrainingSession(engine.session_id).train(engine, journal)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    run()
