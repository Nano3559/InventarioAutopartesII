"""La aplicación real con eventos de auditoría separados, sin fixtures ni modelos falsos."""
from pathlib import Path
import runpy
import sys

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[3]
sys.path.insert(0, str(ROOT / "ml/demand"))
import lifecycle_registry

lifecycle_registry.DEFAULT_ROOT = FOLDER / "eventos_visual"
runpy.run_path(str(ROOT / "ml/demand/streamlit_app.py"), run_name="__main__")
