# RepuestoPro 4.1.0 experimental

Esta carpeta ejecuta experimentos offline. Los candidatos quedan aislados y sin activar. La API y el runtime oficiales siguen usando el release 4.0.0.

Desde la raíz del repositorio en PowerShell:

```powershell
& ml/demand/.venv/Scripts/python.exe -B ml/demand/experiments/model_4_1_0/training/run_experiment.py --run-id exploratorio-01
```

El comando usa datos de desarrollo publicados en solo lectura. Cada ejecución requiere un identificador nuevo. Los artefactos locales se escriben en `candidates/<id>/` y las métricas pareadas y por grupo en `evaluation/<id>.json`. El protocolo vive en `configs/protocolo.json`. El informe de la primera ejecución vive en `reports/COMPARACION_EXPERIMENTAL.md`.

Los paquetes joblib son artefactos experimentales locales. Cargar únicamente paquetes de procedencia verificada. En cada paquete, `strategy` identifica cómo combinar las predicciones en `estimators` con los lags. El resultado se evalúa en unidades continuas con piso cero.
