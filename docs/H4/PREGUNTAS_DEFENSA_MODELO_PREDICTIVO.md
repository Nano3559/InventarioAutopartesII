# Preguntas del tribunal · Modelo predictivo H4

Las respuestas se refieren al release oficial 4.0.0, salvo donde se identifique un experimento.

**1. ¿Por qué Random Forest?** En VALIDATION dio el menor MAE entre Lag1, LinearRegression y dos variantes de bosque. El bosque absoluto obtuvo 11.5168 contra 19.4067 de Lag1. El bosque cuadrático obtuvo un RMSE menor, pero la selección priorizaba MAE en unidades. [Selección](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#6-algoritmos-investigados)

**2. ¿Qué predice exactamente?** Estima las unidades de venta observadas durante el mes objetivo para un producto y una tienda, usando lo conocido al inicio del mes. La falta de stock puede limitar las ventas registradas y el objetivo no mide ese volumen perdido. [Objetivo](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#2-objetivo-del-modelo-predictivo)

**3. ¿De dónde provienen los datos?** De un generador académico reproducible y un catálogo congelado. El build 4.0.0 comprende 56 productos, tres tiendas y realizaciones sintéticas diferenciadas. [Dataset](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#4-dataset)

**4. ¿Cómo se entrenó?** Se ajustó un pipeline con 5.040 filas TRAIN y peso total uno por familia. Se compararon variantes en 1.008 filas de VALIDATION. El bosque seleccionado tiene 100 árboles, criterio absoluto, profundidad 14, mínimo cuatro por hoja y semilla 42. [Entrenamiento](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#7-entrenamiento-de-random-forest-400)

**5. ¿Qué son los rezagos?** Son las ventas observadas en los meses exactos t−1, t−2 y t−3 del mismo producto y tienda. Para noviembre se usan agosto, septiembre y octubre del mundo DEMO. [Preparación](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#5-preparación-de-datos)

**6. ¿Qué es MAE?** Es el promedio de las diferencias absolutas entre observado y pronosticado. Un MAE de 10.2010 indica un error medio de unas 10.2 unidades en el TEST sintético. [TEST guardado](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/test-evaluation.json)

**7. ¿Qué es RMSE?** Es la raíz del promedio de los errores al cuadrado. Se expresa en unidades de venta y penaliza especialmente los errores grandes. En TEST fue 18.4046. [TEST guardado](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/test-evaluation.json)

**8. ¿Qué significa R²?** Compara el error cuadrático con la variación de las ventas observadas respecto a su media. El 0.6201 de TEST corresponde a esa comparación; una proporción de aciertos exigiría definir una tolerancia y contar errores que la cumplan. [Evaluación](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#8-evaluación-oficial)

**9. ¿Por qué validar de forma temporal?** Porque al pronosticar un mes solo existe el pasado. Ajustar con meses anteriores y evaluar meses posteriores reproduce ese orden. Las variantes de una familia permanecen juntas para reducir contaminación entre grupos. [Particiones](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#4-dataset)

**10. ¿Cómo se evita la fuga de datos?** Se revisa que los lags y planes existieran al corte, se excluyen resultados posteriores y se ajustan transformaciones en TRAIN. VALIDATION selecciona y TEST se abre con el artefacto fijado. [Validador](../../ml/demand/v2/validate_scenarios_v1.py)

**11. ¿Cómo se integra al sistema?** El panel ADMIN envía el snapshot y la hipótesis a Express. El servicio llama a Python, que verifica el release y devuelve pronóstico, impactos, advertencias y reposición. El panel conserva la procedencia al exportar. [Integración](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md#9-integración-al-sistema)

**12. ¿Qué ocurre si no hay historial?** Se exige un snapshot válido con historia utilizable. La ausencia de una referencia se comunica como indisponibilidad o rechazo; el faltante no se rellena como venta cero. El caso de producto registrado sin historia requiere todavía una entrada autorizada para el ensayo conjunto. [J02B](H4_J02B_CONTINUACION_ACEPTACION.md)

**13. ¿Qué ocurre fuera de rango?** El runtime se abstiene y entrega un motivo. En noviembre DEMO hubo 32 casos fuera de rango de 168, por stock vendible superior a 150. La abstención se muestra como ausencia de pronóstico. [Revisión DEMO](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/november-inference-review.json)

**14. ¿Por qué no activar 4.1.1?** D redujo 1.24 % el MAE promedio interno y empeoró el RMSE y el resultado en alta variabilidad. Los tres folds proceden de TRAIN sintético. El candidato necesita una prueba independiente que evalúe cobertura, error y grupos críticos. [Experimento 4.1.1](../../ml/demand/experiments/model_4_1_1/reports/COMPARACION_TEMPORAL.md)

**15. ¿Cómo podría mejorarse?** Reunir una cohorte autorizada con observados cerrados, fechas de corte y datos de disponibilidad, fijar reglas pareadas frente a Lag1 y 4.0.0 y analizar error por producto y tienda. Un intervalo con cobertura objetivo del 95 % requeriría calibración temporal separada y verificación posterior. [Ficha de cohortes](H4_M41_03_FICHA_COHORTES.md)

**16. En la demo, ¿cuál acertó, 87.17 o 80.02?** El caso de noviembre carece de un observado autorizado. La diferencia de 7.15 unidades permite mostrar sensibilidad del pronóstico, pero determinar el error requiere conocer las ventas realizadas. [Comparador](../../ml/demand/experiments/model_4_1_1/comparator/reports/COMPARACION_LOCAL.md)
