"""Suite H4 sin dejar evidencia de sesiones de prueba en la carpeta normal."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
sys.path.insert(0, str(ROOT / "ml/demand"))
with tempfile.TemporaryDirectory() as folder:
    with patch("lifecycle_registry.DEFAULT_ROOT", Path(folder) / "lifecycle"):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "ml/demand/tests"), pattern="test_*.py", top_level_dir=str(ROOT / "ml/demand"))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
