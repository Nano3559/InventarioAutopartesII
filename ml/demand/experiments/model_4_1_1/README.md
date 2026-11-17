# Random Forest experimental 4.1.1

Experimento offline y sin activar. Las carpetas `configs`, `features`, `training`, `evaluation`, `candidates` y `reports` contienen el protocolo, las transformaciones, el ejecutor, las métricas, el candidato y el informe. El release oficial y 4.1.0 conservan sus archivos.

Desde la raíz del repositorio en PowerShell:

```powershell
& ml/demand/.venv/Scripts/python.exe -B ml/demand/experiments/model_4_1_1/training/run_temporal.py --run-id temporal-01
```

Usa un identificador nuevo para repetir la ejecución. El candidato contiene un pipeline scikit-learn y su orden de entrada. Cuando usa características derivadas, aplicar primero `features/lag_features.py` a las 19 entradas oficiales. Cargar únicamente joblib de procedencia verificada. El modelo se reajusta con TRAIN después de seleccionar por folds, por lo que el informe conserva métricas de los modelos de cada fold y no del reajuste final.
