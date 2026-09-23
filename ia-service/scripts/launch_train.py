import subprocess
from pathlib import Path

IA = Path(__file__).resolve().parents[1]

PY = str(IA / ".venv/Scripts/python.exe")
TRAIN = str(Path(__file__).resolve())
LOG = str(IA / "artifacts/diagnostico_v3/entrenamiento_v3.log")

DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

with open(LOG, "w") as so, open(LOG + ".err", "w") as se:
    p = subprocess.Popen(
        [PY, TRAIN],
        stdout=so,
        stderr=se,
        creationflags=DETACHED,
        close_fds=True,
    )
    print(f"PID={p.pid}")