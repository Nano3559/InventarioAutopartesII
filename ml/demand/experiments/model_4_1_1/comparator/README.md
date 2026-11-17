# Comparador local de RepuestoPro

Desde la raíz del repositorio, en PowerShell:

```powershell
$comparador = 'ml/demand/experiments/model_4_1_1/comparator'
& ml/demand/.venv/Scripts/python.exe -B -m streamlit run "$comparador/streamlit_app.py" --server.address 127.0.0.1 --browser.gatherUsageStats false
```

La misma función de comparación está disponible por CLI:

```powershell
& ml/demand/.venv/Scripts/python.exe -B "$comparador/compare_models.py" --list
& ml/demand/.venv/Scripts/python.exe -B "$comparador/compare_models.py" --product 53 --store 6 --month 2026-11
& ml/demand/.venv/Scripts/python.exe -B "$comparador/compare_models.py" --snapshot calendar-2026-6-5-november
& ml/demand/.venv/Scripts/python.exe -B -m unittest discover -v -s "$comparador/tests"
```

Los ID numéricos son los del catálogo. Los selectores de Streamlit muestran los nombres. El comparador admite solo los snapshots DEMO publicados de noviembre de 2026. Todas las lecturas se hacen localmente. La aplicación no activa modelos ni exporta datos a servicios comerciales.

El registro fijado de 4.1.1 conserva el artefacto D. La variante C se muestra como `UNAVAILABLE / ARTIFACT_NOT_PERSISTED`. Para incorporarla se necesita un artefacto C ya entrenado con evidencia verificable y una actualización explícita de este cargador. El comparador no permite cargar archivos externos.

Ver el [informe de compatibilidad y ejemplos](reports/COMPARACION_LOCAL.md).
