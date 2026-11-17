# Diapositivas · Modelo predictivo H4

Guion de diez diapositivas. Las cifras TEST son las métricas históricas del release 4.0.0. Los valores de candidatos se rotulan como exploratorios.

## 1. Problema · Ventas y disponibilidad

**En pantalla.** La rotación de repuestos cambia por producto y tienda. Cuando falta stock, las ventas observadas pueden quedar por debajo de la demanda.

**Visual y datos.** Dos líneas conceptuales, demanda y ventas, separadas durante un quiebre. Etiquetar «esquema conceptual».

**Guion oral (35–45 s).** Un repuesto puede vender cantidades distintas según el periodo y la tienda. Una parte de esa variación viene de la demanda y otra de la disponibilidad. Cuando un producto se agota, la venta registrada deja de representar todas las unidades que podrían haberse vendido. Por eso delimitamos el objetivo a ventas observadas y usamos el contexto de inventario para explicar la estimación y las posibles necesidades de reposición.

**Fuente.** [Objetivo del informe](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#2-objetivo-del-modelo-predictivo)

## 2. Objetivo · Una estimación mensual

**En pantalla.** Estimar unidades vendidas por producto y tienda. Comparar BASE e hipótesis. Explicar cuándo corresponde abstenerse.

**Visual y datos.** Línea temporal con corte 1 de noviembre de 2026, historial agosto–octubre y horizonte de un mes.

**Guion oral (35–45 s).** La unidad de análisis es un producto en una tienda durante un mes. Al inicio de noviembre ya conocemos los tres meses anteriores y los planes que estaban disponibles al corte. Esa información alimenta la previsión. Después, el panel muestra cuánto cambia la estimación cuando se modifica una hipótesis. Si faltan datos utilizables o el escenario queda fuera del dominio, el sistema indica la causa y evita publicar una cifra.

**Fuente.** [Guía vigente 4.0.0](H4_IMPLEMENTACION_MODELO_PREDICTIVO.md)

## 3. Arquitectura · Del generador al panel

**En pantalla.** Generador Python → dataset versionado → scikit-learn → artefacto congelado → Express → React.

**Visual y datos.** Diagrama con dos ramas desde Python, pronóstico y reglas de reposición. Marcar que el comparador Streamlit es local.

**Guion oral (35–45 s).** El proceso empieza con un catálogo congelado y un generador reproducible. Después de validar los datos se ajusta un pipeline en Python y se guarda en joblib. La aplicación consume ese artefacto a través de Express y el runtime de inferencia. React presenta pronósticos, diferencias y advertencias. El cálculo de reposición utiliza también las reglas de inventario y los planes conocidos. El comparador experimental queda separado del sistema oficial.

**Fuente.** [Diagrama y arquitectura](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#3-arquitectura-del-módulo)

## 4. Dataset · Calendario sintético 4.0.0

**En pantalla.** 56 productos, 3 tiendas y 14.112 filas. TRAIN 5.040 · VALIDATION 1.008 · TEST 1.008 · DEMO 7.056.

**Visual y datos.** Línea de tiempo con los tres bloques de desarrollo y TEST. Dibujar DEMO como realización paralela. Señalar noviembre de 2026 sin objetivo.

**Guion oral (40–50 s).** El build 4.0.0 contiene cuatro realizaciones sintéticas con usos definidos. TRAIN abarca febrero de 2025 a abril de 2026. VALIDATION cubre mayo a julio y TEST agosto a octubre de 2026. DEMO está separado y aporta la referencia que mostramos en el panel. El conjunto publicado permite 168 combinaciones de producto y tienda para noviembre, pero ese mes carece de resultado observado para medir el acierto.

**Fuente.** [Manifiesto 4.0.0](../../ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/manifest.json)

## 5. Preparación · Qué se conoce al corte

**En pantalla.** 19 entradas. Tres rezagos, calendario, categoría, stock al corte, precios y compromisos conocidos.

**Visual y datos.** Diagrama de tres meses cerrados hacia el vector de variables. Colocar el objetivo a la derecha del corte con línea discontinua.

**Guion oral (40–50 s).** El corte temporal separa la información disponible del resultado que se desea predecir. Los rezagos corresponden a ventas cerradas de los tres meses exactos anteriores. Las recepciones previstas pueden entrar como planes cuando se conocían al corte. Los resultados posteriores y la demanda latente quedan fuera. El pipeline imputa faltantes numéricos admisibles y codifica la categoría, con transformaciones aprendidas dentro de TRAIN.

**Fuente.** [Validación y características](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#5-preparación-de-datos)

## 6. Entrenamiento · Selección por MAE

**En pantalla.** Random Forest absoluto: 100 árboles, profundidad 14, mínimo 4 por hoja, semilla 42. MAE VALIDATION: 11.5168 frente a 19.4067 de Lag1.

**Visual y datos.** Barras de MAE: Lag1 19.4067, Lineal 15.7254, RF cuadrático 12.4399, RF absoluto 11.5168.

**Guion oral (40–50 s).** Comparamos un baseline que copia el mes anterior, regresión lineal y dos bosques. El bosque de criterio absoluto obtuvo el menor error medio en unidades y se seleccionó antes de abrir TEST. Las variantes de una misma familia recibieron juntas un peso total de uno en el ajuste. La configuración, el orden de características y la huella del artefacto quedaron registrados para que la inferencia use siempre el mismo pipeline.

**Fuente.** [Resultados de selección](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/experiments.csv)

## 7. Evaluación oficial · TEST congelado

**En pantalla.** RF: MAE 10.2010, RMSE 18.4046 y R² 0.6201. Lag1: MAE 17.3581. Cobertura de servicio 1.002/1.008.

**Visual y datos.** Barras de MAE RF/Lag1 y una nota separada con seis abstenciones. Indicar «TEST sintético, métricas sobre 1.008 filas».

**Guion oral (40–55 s).** El modelo se evaluó una única vez con el artefacto fijado. El MAE indica alrededor de diez unidades de error absoluto promedio y el RMSE da más peso a errores grandes. R² compara el ajuste cuadrático con la variabilidad de las ventas; no puede leerse como 62 % de aciertos. Las métricas se calcularon sobre el conjunto completo. La cobertura de servicio se registró aparte y contempla seis abstenciones.

**Fuente.** [TEST oficial guardado](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/test-evaluation.json)

## 8. Integración · Escenarios trazables

**En pantalla.** Panel ADMIN · snapshot BASE · hipótesis · pronóstico y reposición · exportación.

**Visual y datos.** Captura J02 de la comparación recuperada. Resaltar fecha original y revisión del runtime.

**Guion oral (35–50 s).** El administrador elige producto y tienda y parte de un snapshot publicado. Puede cambiar condiciones hipotéticas y revisar la comparación. El backend valida cantidades, fechas y márgenes. Una repetición idéntica recupera la respuesta y mantiene su fecha de generación. La exportación conserva el origen de esa entrega. El recorrido técnico local dejó evidencia en Chrome. El equipo conserva pendiente su aceptación conjunta.

**Fuente.** [J02B y ruta a las capturas](H4_J02B_CONTINUACION_ACEPTACION.md)

## 9. Experimentos · 4.1.0 y 4.1.1

**En pantalla.** 4.1.0 no mejoró MAE de VALIDATION. 4.1.1 D: MAE interno 11.6559 frente a 11.8022 de A, con mayor RMSE.

**Visual y datos.** Dos paneles con títulos de cohorte distintos. Para 4.1.1, mostrar MAE y RMSE de A y D. Añadir la demo 87.17 frente a 80.02 si hay tiempo.

**Guion oral (45–60 s).** 4.1.0 comparó cuatro estrategias sobre VALIDATION histórica y mantuvo la referencia oficial en primer lugar por MAE. Después, 4.1.1 exploró regularización y tres resúmenes de lags en folds internos de TRAIN. D redujo ligeramente el MAE promedio, pero empeoró RMSE y el grupo de alta variabilidad. El comparador muestra cómo difieren dos predicciones para un snapshot. En noviembre carecemos del observado necesario para determinar cuál acertó.

**Fuente.** [Resultados experimentales](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#10-experimentos-410)

## 10. Conclusiones · Qué queda demostrado

**En pantalla.** 4.0.0 oficial. Mejor MAE que Lag1 en TEST sintético. Abstenciones explícitas. Candidatos sin activar.

**Visual y datos.** Tres filas: validación académica, aceptación conjunta pendiente y evaluación independiente futura. Usar 50/56 productos como dato secundario.

**Guion oral (35–50 s).** El logro del módulo es combinar un estimador verificable con un flujo de escenarios que conserva identidad, procedencia y motivos de abstención. En TEST sintético se redujo el MAE frente al baseline en 50 de 56 productos. Para extender la conclusión al uso comercial se necesitan datos autorizados, meses cerrados y un protocolo independiente. Para la defensa mantenemos 4.0.0 como versión oficial y presentamos los candidatos como investigación.

**Fuente.** [Conclusiones y matriz de evidencia](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#15-resultados-y-conclusiones)
