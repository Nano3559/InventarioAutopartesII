# Artefactos locales de demanda H4

La única guía oficial de diseño, columnas, fases, evaluación y límites es [H4_IMPLEMENTACION_MODELO_PREDICTIVO.md](../../docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md).

La versión guardada vigente está en [data/escenarios_v1_1](data/escenarios_v1_1). Se conservan [data/escenarios_v1](data/escenarios_v1) y el generador anterior en [versions/generate_v1_0_0.py](versions/generate_v1_0_0.py). El catálogo de referencia está en [catalog_reference.json](catalog_reference.json).

El generador y sus pruebas requieren Python 3.10 o posterior, sin dependencias externas. Su manifiesto conserva la versión usada en la generación guardada. Para una reproducción futura autorizada, desde la raíz se utiliza `python ml/demand/generate_synthetic.py --output RUTA_NUEVA`, sin sobrescribir versiones anteriores. Las pruebas se ejecutan con `python -m unittest discover -s ml/demand -p "test_*.py" -v` y algunas generan copias temporales.

Esta consolidación no ejecuta esos comandos. No hay entrenamiento, modelo guardado ni conexión a bases de datos en estos artefactos. No se mezclan metadatos, inválidos o grises con el CSV supervisado.

La interfaz de Ross está en streamlit_app.py, con ui_runtime.py para conectar inferencia y registrar emisiones, ui_analysis.py para métricas y monitoreo y ui_panels.py para las vistas. Incluye edición, observados posteriores, errores por grupos, drift demostrativo y comparación visual. El motor y modelos de Erika todavía no existen en estos archivos. No se muestran resultados de ejemplo como si fueran modelos reales.

Desde la raíz, con Python 3.11:

```powershell
python -m venv ml/demand/.venv
.\ml\demand\.venv\Scripts\python.exe -m pip install -r ml/demand/requirements-ui.lock.txt
.\ml\demand\.venv\Scripts\python.exe -m streamlit run ml/demand/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Crear el entorno e instalar solo es necesario la primera vez. Para probar exclusivamente esta interfaz sin regenerar datasets:

```powershell
.\ml\demand\.venv\Scripts\python.exe -m unittest discover -s ml/demand -p 'test_*ui*.py' -v
```

No se entrena, avanza el reloj ni escribe en Neon desde esta entrega. PREDECIR se habilita con el ACTIVE compatible de Erika. GENERAR SIGUIENTE MES y AVANZAR MES siguen pendientes de su motor. La guía oficial define create_runtime(), get_active_model(), predict(features) y el reporte JSON de comparación. Registrar un observado o descargar una sesión no modifica el CSV guardado. requirements-ui.txt y requirements-ui.lock.txt se mantienen sin dependencias ML nuevas.

La referencia source_document del catálogo conserva la ruta histórica. Su original exacto y el mapa de ubicación actual están en [los traslados documentales](../../docs/H4/historico/traslados_documentales.json). Los hashes y archivos del dataset no se modificaron.
