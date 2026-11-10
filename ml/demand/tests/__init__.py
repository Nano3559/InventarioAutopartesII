"""Pruebas H4: imports únicos del paquete y registros de sesión temporales.

El descubrimiento debe usar -t ml/demand. Este bootstrap no altera el código
productivo: solo redirige el destino de evidencia generado por AppTest.
"""
import atexit
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

DEMAND_DIR = Path(__file__).resolve().parent.parent
if str(DEMAND_DIR) not in sys.path:
    sys.path.insert(0, str(DEMAND_DIR))

_temporary = tempfile.TemporaryDirectory(prefix="h4-tests-")
_lifecycle_patch = patch("lifecycle_registry.DEFAULT_ROOT", Path(_temporary.name) / "lifecycle")
_lifecycle_patch.start()


def _cleanup():
    _lifecycle_patch.stop()
    _temporary.cleanup()


atexit.register(_cleanup)
