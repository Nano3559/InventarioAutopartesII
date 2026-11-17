# INFORME CONJUNTO DE DESARROLLO, ERRORES, CORRECCIONES Y PRUEBAS DEL MÓDULO PREDICTIVO H4

**Proyecto:** InventarioAutopartesII – RepuestoPro  
**Integrantes:** Erika y Ross  
**Módulo:** Predicción de demanda y simulación de escenarios  
**Fecha:** 17 de noviembre de 2026

---

## 1. Introducción

El presente informe describe el trabajo realizado por Erika y Ross durante el desarrollo e integración del módulo predictivo H4 de RepuestoPro.

Se explican los problemas encontrados, las soluciones aplicadas, las herramientas utilizadas y las pruebas realizadas. También se presentan las instrucciones principales que utilizamos en OpenCode para organizar las actividades y realizar correcciones.

Para distinguir nuestras responsabilidades, el informe se divide en el trabajo de Ross, el trabajo de Erika y las actividades que realizamos de manera conjunta.

No todas las dificultades fueron errores de programación. Algunas correspondieron a datos incompletos, diferencias entre versiones, problemas de integración o limitaciones que debían documentarse.

## 2. Objetivo del módulo

El objetivo fue implementar una herramienta que permita estimar las ventas mensuales de repuestos según el producto, la tienda y la información disponible.

Además de mostrar una predicción, el sistema debía permitir consultar el historial, comparar escenarios y presentar sugerencias de reposición.

La herramienta busca apoyar las decisiones de inventario. No realiza compras automáticamente ni reemplaza el criterio del administrador.

El modelo trabaja con ventas observadas, que pueden estar limitadas por el stock disponible. Por esta razón, sus resultados no representan necesariamente toda la demanda potencial de los clientes.

## 3. Distribución de responsabilidades

| Área | Responsable principal | Trabajo realizado |
|---|---|---|
| Revisión de fuentes externas | Ross | Procedencia, licencias y características de los datos |
| Preparación y ampliación de datos sintéticos | Ross | Generación de datos, cobertura y coherencia |
| Integración con el sistema | Ross | Backend, dashboard y vistas administrativas |
| Interfaz predictiva | Ross | Historial, selección de productos, gráficas y escenarios |
| Modelo predictivo H4 | Erika | Revisión, validación y mejora experimental del modelo |
| Reglas de escenarios | Erika | Validaciones, consistencia y tratamiento de errores |
| Integridad del motor predictivo | Erika | Verificación de archivos y respuestas |
| Comparación de modelos | Erika | Experimentos 4.1.0, 4.1.1 y evaluación DEMO |
| Documentación y auditorías H4 | Erika, con aportes de Ross | Planes, pruebas, informes y evidencias |
| Integración y revisión final | Ambos | Comprobación del funcionamiento completo |

Esta distribución identifica las responsabilidades principales según los informes de trabajo. Algunas tareas requirieron cambios en componentes de ambos integrantes.

---

# PARTE I. TRABAJO REALIZADO POR ROSS

## 4. Preparación y revisión de los datos

### 4.1. Historial comercial insuficiente

**Problema encontrado**

Los registros disponibles en el sistema no ofrecían un historial comercial suficientemente completo y verificado para entrenar el modelo.

Existían períodos incompletos y dudas sobre el origen de algunos registros.

**Solución aplicada**

Ross trabajó con un conjunto de datos sintéticos que permitiera representar ventas, productos, tiendas y situaciones de inventario.

Se documentaron las condiciones utilizadas para generar los datos, evitando presentarlos como ventas reales de RepuestoPro.

**Prompt reconstruido de Ross:**

> Necesito revisar los datos que tenemos para la predicción. Comprueba si el historial es suficiente y si conocemos su procedencia. Si no podemos utilizarlo como información comercial real, prepara una alternativa sintética que podamos reproducir. Documenta los supuestos y no mezcles los datos simulados con las ventas del sistema.

**Resultado**

Se obtuvo una base de datos académica para desarrollar y evaluar el módulo.

### 4.2. Diferencias entre fuentes externas

**Problema encontrado**

Se revisaron fuentes como Monash, UCI, M5 y Favorita. Sin embargo, cada una representaba negocios y productos diferentes.

No era correcto tratar sus registros como si pertenecieran directamente a RepuestoPro.

**Solución aplicada**

Ross separó el propósito de cada fuente.

| Fuente | Uso |
|---|---|
| Monash Car Parts | Referencia de ventas de repuestos |
| UCI Online Retail II | Referencia de transacciones y devoluciones |
| M5 | Referencia de ventas por producto y tienda |
| Favorita | Referencia de promociones y comportamiento comercial |

También se revisaron las condiciones de uso de los datos. La fuente Automotive quedó pendiente por falta de evidencia suficiente sobre su licencia.

**Prompt reconstruido de Ross:**

> Revisa las fuentes de datos que estamos considerando. Quiero saber qué información aporta cada una y si podemos utilizarla en el proyecto. Comprueba las licencias y evita mezclar productos o identificadores que no corresponden a RepuestoPro.

### 4.3. Registros duplicados y datos faltantes

**Problemas encontrados**

Durante la revisión se identificaron situaciones que podían afectar la calidad de los datos:

- Dos históricos de M5 compartían 1.913 jornadas.
- En Favorita, la ausencia de un registro no significaba necesariamente cero ventas.
- Algunas fuentes contenían devoluciones, cancelaciones o cantidades fraccionarias.
- Faltaban datos propios del negocio, como costos, inventario histórico y plazos de proveedores.

**Soluciones aplicadas**

Se evitó duplicar períodos compartidos.

También se diferenciaron las ventas cero de los registros desconocidos. Las devoluciones y cantidades especiales se trataron según su significado.

Las variables que no estaban disponibles se representaron mediante supuestos sintéticos documentados.

**Prompt reconstruido de Ross:**

> Revisa el dataset para encontrar registros repetidos, datos faltantes y cantidades que no correspondan a ventas normales. No conviertas automáticamente los datos desconocidos en cero. Comprueba también si existen períodos repetidos entre archivos y documenta los valores que debamos generar de forma sintética.

### 4.4. Problemas en la generación de datos

**Problemas encontrados**

En una versión inicial, la antigüedad de la cotización no presentaba suficiente variación.

También faltaban ejemplos de ventas mayoristas de gran volumen.

Estas limitaciones reducían la variedad de situaciones que podía estudiar el modelo.

**Soluciones aplicadas**

Ross amplió el generador para incluir diferentes antigüedades de cotización y pedidos mayoristas más grandes.

Se mantuvieron controles sobre cantidades, disponibilidad e inventario.

**Prompt reconstruido de Ross:**

> Revisa el generador de datos porque algunas variables tienen poca variación y faltan ventas mayoristas grandes. Quiero ampliar esos casos sin perder la coherencia del inventario. Conserva las versiones anteriores y ejecuta pruebas antes de utilizar la nueva generación.

---

## 5. Integración con el backend y la base de datos

### 5.1. Error de estructura entre Prisma y Neon

**Error encontrado**

El dashboard presentó problemas porque el código esperaba campos que no estaban disponibles en la base de datos.

Uno de los errores registrados fue `P2022`, relacionado con `Sale.status`.

**Solución aplicada**

Ross revisó la estructura de la base y reprodujo el problema en PostgreSQL local.

Después probó las migraciones en un entorno separado, revisó los cambios existentes y preparó un respaldo antes de intervenir la base correspondiente.

La documentación registra 58 comprobaciones en el entorno aislado y 46 comprobaciones posteriores en producción.

**Prompt reconstruido de Ross:**

> El dashboard está fallando por diferencias entre Prisma y la base de datos. Revisa primero la estructura y encuentra los campos que faltan. Prueba cualquier corrección en un entorno aislado. Antes de modificar producción, prepara un respaldo y verifica que no se pierdan registros.

### 5.2. Diferencias entre campos de productos

**Problema encontrado**

La estructura física de la base no coincidía exactamente con el cambio esperado entre `Product.quality` y `Product.detalles`.

**Solución aplicada**

Se conservó `Product.quality` como campo antiguo y se reconoció que `detalles` ya existía.

No se eliminaron datos para forzar un cambio de nombre.

### 5.3. Dashboard sin información visible

**Problema encontrado**

En algunos períodos, el dashboard no mostraba movimientos aunque existieran ventas históricas en otros meses.

También existía el riesgo de mostrar cero cuando una consulta no estaba disponible.

**Solución aplicada**

Ross incorporó filtros por mes y ubicación, además de información de unidades vendidas y productos destacados.

Se diferenciaron los datos realmente vacíos de las consultas que no podían completarse.

No se agregaron ventas ficticias para llenar los gráficos.

**Prompt reconstruido de Ross:**

> Revisa por qué el dashboard aparece vacío cuando consultamos ciertos períodos. Comprueba las fechas, los filtros y los registros disponibles. Quiero mostrar las ventas del mes seleccionado sin inventar información. Si una consulta falla, debe indicarse que los datos no están disponibles en lugar de mostrar cero.

---

## 6. Desarrollo y correcciones de la interfaz predictiva

### 6.1. Pantalla con demasiada información

**Problema encontrado**

La interfaz mostraba instrucciones, advertencias y resultados en un mismo espacio.

Esto dificultaba comprender la predicción.

**Solución aplicada**

Ross simplificó los títulos, las tarjetas y los controles. Parte de la información secundaria pasó a secciones desplegables.

### 6.2. La primera interfaz no permitía modificar escenarios

**Problema encontrado**

Inicialmente se podían consultar predicciones guardadas, pero no comparar de forma interactiva cambios de precio, cantidad, cotización o logística.

**Solución aplicada**

Se definieron las entradas necesarias para los escenarios y su comunicación con el backend.

Se separó la consulta del historial de la comparación de hipótesis.

### 6.3. Diferencia entre calendarios de 2026 y 2028

**Problema encontrado**

Una vista utilizaba información de 2026, mientras una versión anterior del modelo trabajaba con datos sintéticos de 2028.

Esto provocaba confusión al interpretar las gráficas.

**Solución aplicada**

Se separaron temporalmente las versiones. Después se trabajó con el modelo 4.0.0, que utiliza historial hasta octubre de 2026 para estimar noviembre.

No se corrigió únicamente cambiando los textos de las fechas.

### 6.4. Cantidades poco claras en los productos

**Problema encontrado**

Algunas cantidades mostradas junto al nombre del producto no indicaban claramente a qué mes correspondían.

**Solución aplicada**

Se separó el nombre del producto de sus ventas históricas.

Para la predicción de noviembre se utilizaron agosto, septiembre y octubre como meses anteriores.

### 6.5. Resultados anteriores al cambiar de producto

**Error encontrado**

Cuando una consulta tardaba en responder, podía aparecer información de un producto seleccionado anteriormente.

**Solución aplicada**

Ross incorporó controles para cancelar solicitudes, limpiar resultados y evitar que respuestas antiguas reemplazaran la información actual.

### 6.6. Espacio vacío al final de la pantalla

**Problema encontrado**

La página presentaba un espacio excesivo después del contenido.

**Solución aplicada**

Se ajustó el desplazamiento del panel y se comprobó visualmente el resultado.

**Prompt reconstruido de Ross para la interfaz:**

> Quiero mejorar la pantalla de predicción. Necesito que sea más clara, que los productos y sus ventas se entiendan fácilmente y que las gráficas se actualicen al cambiar la selección. Revisa también las respuestas que llegan tarde y los espacios vacíos de la página. Mantén el diseño del sistema y comprueba los cambios en el navegador.

---

# PARTE II. TRABAJO REALIZADO POR ERIKA

## 7. Organización de las tareas mediante archivos `.md`

Antes de realizar cambios importantes, Erika organizó el trabajo mediante documentos Markdown.

Estos archivos permitieron registrar los objetivos, las tareas, las pruebas y los resultados esperados.

Entre los documentos principales se utilizaron:

| Documento | Función |
|---|---|
| `H4_IMPLEMENTACION_MODELO_PREDICTIVO.md` | Guía del desarrollo |
| `PLAN_DE_TRABAJO_V2.md` | Organización de actividades |
| Informes H4-E08 y H4-E09 | Registro de correcciones y pruebas |
| `AUDITORIA_DATASET_Y_PRUEBAS_MODELO.md` | Revisión de los datos |
| `AUDITORIA_INDEPENDENCIA_DEMO_HISTORICO.md` | Revisión de los datos de demostración |
| `EVALUACION_EXPLORATORIA_DEMO_4_0_0_VS_D.md` | Comparación de modelos |

Los documentos `.md` no ejecutan la predicción. Su función es conservar las instrucciones y evidencias del desarrollo.

Las reglas que debe comprobar el sistema también se implementaron en código y archivos de configuración.

**Prompt reconstruido de Erika:**

> Quiero organizar las tareas del modelo predictivo H4. Revisa la guía principal y el plan de trabajo. Identifica qué actividades están terminadas y cuáles faltan. Necesito listas de verificación, responsables y pruebas para cada tarea. No cambies los requisitos originales y evita crear documentos repetidos.

---

## 8. Validación y corrección de escenarios

### 8.1. Entradas incorrectas

**Problema encontrado**

Los escenarios podían recibir fechas, precios o cantidades que no cumplían las condiciones del sistema.

**Solución aplicada**

Erika revisó las validaciones para que las entradas incorrectas fueran rechazadas con mensajes claros.

También se comprobó que el sistema no completara información faltante con valores inventados.

**Prompt reconstruido de Erika:**

> Revisa las validaciones de los escenarios predictivos. Comprueba fechas, precios, cantidades, inventario y pedidos. Si los datos son incorrectos, quiero que el sistema muestre un mensaje claro. No debe completar información faltante automáticamente. Agrega pruebas para los casos correctos e incorrectos.

### 8.2. Cambios de precio sin efecto real

**Problema encontrado**

Algunos escenarios podían mostrar diferencias aunque el precio efectivo continuara siendo el mismo.

**Solución aplicada**

Erika corrigió la preparación de los datos para conservar las características originales cuando no existía un cambio económico real.

También se ajustó la comparación de pedidos para utilizar identificadores estables.

**Prompt reconstruido de Erika:**

> Revisa los escenarios BASE y los modificados. Si el precio no cambia realmente, no quiero que aparezca una diferencia injustificada. Comprueba también que los pedidos se comparen correctamente aunque cambie su posición. Corrige los casos encontrados y agrega pruebas.

---

## 9. Correcciones del motor predictivo

### 9.1. Archivos verificados que se leían nuevamente

**Error encontrado**

Durante la auditoría se descubrió que algunos archivos eran verificados y después se volvían a leer.

Esto podía generar diferencias entre el contenido comprobado y el contenido utilizado.

**Solución aplicada**

Erika corrigió el procedimiento para utilizar exactamente el mismo contenido que había sido verificado.

Se agregaron pruebas para comprobar el resultado.

**Prompt reconstruido de Erika:**

> Encontramos un problema en la lectura de los archivos del modelo. Algunos se verifican, pero después vuelven a leerse. Quiero que se utilice exactamente el contenido que ya fue comprobado. Revisa los archivos relacionados, agrega pruebas y no modifiques los modelos entrenados.

### 9.2. Respuestas guardadas incompletas

**Problema encontrado**

Era necesario controlar las respuestas recuperadas cuando se encontraban dañadas o incompletas.

**Tratamiento aplicado**

Se mantuvieron las comprobaciones para rechazar información incorrecta.

La recuperación automática de ciertos archivos persistentes dañados quedó documentada como mejora pendiente.

### 9.3. Respuestas nuevas y recuperadas

**Problema encontrado**

No siempre era fácil identificar si una respuesta había sido calculada nuevamente o recuperada de una operación anterior.

**Solución aplicada**

Erika incorporó información de procedencia para distinguir ambos casos.

También se conservaron datos útiles para revisar el origen de las respuestas.

**Prompt reconstruido de Erika:**

> Quiero identificar cuándo una respuesta es nueva y cuándo se recuperó de una operación anterior. Agrega esa información sin modificar el pronóstico. También debe conservarse en las evidencias que exportamos. Si no podemos verificar un dato, debe indicarse claramente.

### 9.4. Resultados cuando el modelo no podía predecir

**Problema encontrado**

En ciertos casos aparecían advertencias numéricas aunque el modelo no hubiera generado una predicción válida.

**Solución aplicada**

Erika corrigió las respuestas para mostrar un resultado vacío acompañado del motivo correspondiente.

**Prompt reconstruido de Erika:**

> Revisa los casos donde el modelo no puede predecir. Quiero que no se muestre una cantidad como si fuera válida. Debe aparecer el motivo de la abstención y el frontend tiene que interpretarlo correctamente. Agrega pruebas para estos casos.

---

## 10. Revisión del modelo oficial

### 10.1. Configuración de la predicción

El modelo oficial utilizado fue Random Forest 4.0.0.

Su configuración principal fue:

| Parámetro | Valor |
|---|---:|
| Número de árboles | 100 |
| Profundidad máxima | 14 |
| Mínimo de registros por hoja | 4 |
| Características consideradas | 0,9 |
| Semilla | 42 |
| Criterio | `absolute_error` |

La predicción utiliza información histórica, calendario, precios, inventario y otras características disponibles antes del mes que se desea estimar.

El proceso general es:

**Selección del producto y tienda → validación de datos → revisión del historial → ejecución del modelo → resultado → presentación en pantalla.**

Las sugerencias de reposición se calculan mediante reglas separadas de la predicción.

### 10.2. Evaluación del modelo oficial

Los resultados oficiales en TEST sintético fueron:

| Indicador | Resultado |
|---|---:|
| MAE | 10,2010 |
| RMSE | 18,4046 |
| R² | 0,6201 |
| Registros evaluados | 1.008 |

El modelo redujo el error absoluto medio aproximadamente un 41,23 % frente a Lag1.

Esto representa una reducción del error promedio, no un porcentaje de aciertos.

---

## 11. Problemas de precisión y modelos alternativos

### 11.1. Productos difíciles de predecir

**Problema encontrado**

Aunque el modelo oficial obtuvo resultados favorables en conjunto, algunos productos presentaban errores mayores.

Esto ocurría especialmente cuando las ventas eran poco frecuentes o cambiaban considerablemente entre meses.

**Solución aplicada**

Erika revisó los resultados por producto y tienda.

Después investigó modelos alternativos sin modificar la versión oficial.

**Prompt reconstruido de Erika:**

> Quiero analizar cómo podemos mejorar la precisión del modelo. Revisa los productos y tiendas con errores más altos. Después compara otras configuraciones de Random Forest y modelos alternativos. Trabaja en una carpeta experimental y no utilices nuevamente TEST para elegir los cambios.

### 11.2. Investigación 4.1.0

Se probaron diferentes configuraciones de Random Forest, HistGradientBoosting y estrategias para ventas intermitentes.

En esta etapa, ninguna alternativa consiguió superar al modelo oficial en MAE sobre la comparación histórica de VALIDATION.

### 11.3. Investigación 4.1.1

Posteriormente se incorporaron características obtenidas de los tres últimos meses.

Se consideraron el promedio de ventas, su variación y la proporción de meses sin ventas.

De esta investigación surgió el candidato experimental D.

**Prompt reconstruido de Erika:**

> Quiero realizar una nueva prueba para mejorar Random Forest. Agrega características basadas en los últimos tres meses y compara varias configuraciones utilizando únicamente los datos permitidos. Revisa MAE, RMSE y resultados por producto. Guarda el mejor candidato como experimental, sin reemplazar el modelo oficial.

---

## 12. Comparación de modelos

### 12.1. Interfaz de comparación

Erika preparó un comparador local con Streamlit.

Esta herramienta permitió seleccionar un producto, una tienda y un mes para observar las diferencias entre el modelo oficial y el candidato D.

Por ejemplo, para Tensador de Correa en la Tienda 2, durante noviembre de 2026:

| Modelo | Pronóstico |
|---|---:|
| Random Forest 4.0.0 | 87,17 unidades |
| Candidato D | 80,02 unidades |

La diferencia fue de 7,15 unidades.

Sin una venta observada de noviembre no era posible determinar cuál pronóstico estaba más cerca del resultado real.

**Prompt reconstruido de Erika:**

> Necesito una interfaz sencilla para comparar el modelo oficial con el candidato D. Quiero seleccionar producto, tienda y mes. Muestra las dos predicciones, su diferencia y los casos donde no se puede predecir. No entrenes modelos ni modifiques la versión oficial.

### 12.2. Auditoría de los datos DEMO

Antes de realizar una nueva evaluación, Erika revisó si los datos históricos DEMO podían utilizarse para comparar los modelos.

La auditoría concluyó **GO CON LIMITACIONES**.

Los registros pertenecían a una realización sintética separada, pero compartían productos, tiendas y el mismo proceso de generación con los datos anteriores.

Por esta razón, la evaluación debía presentarse como exploratoria.

**Prompt reconstruido de Erika:**

> Quiero comprobar si podemos utilizar los datos históricos DEMO para evaluar los modelos. Revisa su procedencia, posibles registros repetidos y disponibilidad de información antes de cada predicción. No calcules errores todavía. Primero determina si la comparación es válida y qué limitaciones tiene.

### 12.3. Evaluación exploratoria final

Se utilizaron 504 registros DEMO BASE de agosto a octubre de 2026.

Primero se guardaron las predicciones. Después se compararon con los valores observados del conjunto sintético.

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| Random Forest 4.0.0 | 10,3210 | 19,1805 | 0,3711 |
| Candidato D | 9,8026 | 19,1457 | 0,3734 |
| Lag1 | 14,9643 | 27,5775 | −0,3001 |

El candidato D obtuvo un MAE 5,02 % menor que el oficial en esta comparación.

También se revisó el resultado excluyendo un registro previamente identificado. La conclusión general no cambió.

**Prompt reconstruido de Erika:**

> Quiero comparar 4.0.0, D y Lag1 utilizando los 504 registros autorizados. Primero guarda las predicciones sin consultar los resultados observados. Después calcula MAE, RMSE, R² y cobertura. Incluye una revisión excluyendo el registro identificado en la auditoría. No entrenes nuevamente ni reemplaces el modelo oficial.

### 12.4. Decisión

Se decidió conservar Random Forest 4.0.0 como modelo oficial.

El candidato D quedó como alternativa experimental, debido a que sus resultados adicionales procedían de datos sintéticos y no demostraban una mejora general con ventas comerciales reales.

---

# PARTE III. TRABAJO CONJUNTO

## 13. Integración y pruebas finales

La integración del módulo requirió comprobar que el frontend, el backend y el servicio predictivo funcionaran correctamente.

Ross trabajó principalmente en la presentación y conexión de las vistas.

Erika se concentró en las validaciones del motor, la consistencia de las respuestas y las pruebas de los escenarios.

La auditoría H4-E09 registró 194 pruebas distintas sin fallos, con una omisión histórica.

También se realizaron recorridos técnicos mediante navegador, utilizando el backend, el servicio predictivo y PostgreSQL local.

La continuación H4-J02B incluyó 18 subcasos técnicos. No se documentaron defectos funcionales bloqueantes en ese conjunto.

**Prompt reconstruido para la revisión conjunta:**

> Queremos comprobar que el módulo H4 funcione de principio a fin. Revisa la comunicación entre el frontend, el backend y Python. Comprueba permisos, escenarios, errores, respuestas guardadas y resultados mostrados. Registra las pruebas realizadas y separa los problemas corregidos de los pendientes. No declares el cierre conjunto sin nuestra confirmación.

---

## 14. Problemas pendientes

Aunque se completaron las principales tareas de desarrollo, los informes registraron observaciones que no deben presentarse como solucionadas.

| Pendiente | Situación |
|---|---|
| Pruebas habituales del backend | Se registraron 15 fallos relacionados con la preparación de mocks |
| Pruebas HTTP alternativas | Pasaron 37 comprobaciones con el procedimiento documentado |
| Comparador experimental | Se registró una incompatibilidad de versión de Python en una ejecución |
| Enlaces de documentación | Se identificaron 63 enlaces relativos rotos en nueve documentos |
| Recuperación de ciertos archivos guardados dañados | Mejora operativa pendiente |
| Producto sin historial suficiente | Caso de verificación pendiente |
| Aceptación conjunta | Pendiente de confirmación formal de Erika y Ross |
| Precisión con ventas reales | Requiere una evaluación posterior con datos comerciales verificados |

Estos pendientes no significan que todas las funciones estén fallando. Algunos corresponden a herramientas de prueba, documentación o actividades necesarias para un cierre formal.

---

## 15. Stack tecnológico utilizado

| Tecnología | Uso principal |
|---|---|
| Python | Preparación de datos y predicción |
| pandas y NumPy | Procesamiento de información |
| scikit-learn | Entrenamiento y evaluación |
| Random Forest | Modelo oficial |
| HistGradientBoosting | Modelo alternativo |
| joblib | Almacenamiento de modelos |
| Streamlit | Comparación experimental |
| Node.js y Express | Backend |
| TypeScript | Desarrollo y validación de tipos |
| Prisma | Consultas a la base de datos |
| PostgreSQL y Neon | Información operativa |
| React 18 | Interfaz del sistema |
| Vite | Desarrollo y compilación |
| TailwindCSS | Estilos de la interfaz |
| Axios | Comunicación con la API |
| Zustand | Estado compartido |
| React Router | Navegación |
| Recharts | Gráficas |
| pytest y unittest | Pruebas Python |
| Vitest y Testing Library | Pruebas frontend |
| Node Test Runner | Pruebas backend |
| Markdown | Documentación |
| Git y GitHub | Control de versiones |
| OpenCode | Apoyo en implementación y auditorías |

Neon almacena información del sistema. El cálculo predictivo se realiza en Python y sus resultados llegan a la interfaz mediante el backend.

---

## 16. Control de versiones y entrega

El trabajo se desarrolló utilizando ramas separadas para facilitar la colaboración.

Ross realizó sus avances en la rama `ross`.

Erika trabajó en la rama `erika`, donde registró sus últimas correcciones, pruebas y documentación.

El commit final de Erika fue:

`badc284`

**Mensaje:** `feat: implementar y validar modelo predictivo de demanda H4`

Se registraron 77 archivos modificados o incorporados.

Posteriormente se preparó un Pull Request desde `erika` hacia `main` para solicitar la revisión de Ross.

La aprobación y fusión definitiva deben comprobarse en GitHub antes de considerarlas completadas.

---

## 17. Resumen de aportes

### 17.1. Aportes de Ross

Ross participó principalmente en la preparación y ampliación de los datos, la revisión de fuentes externas, la integración con la base de datos y el desarrollo de la interfaz.

Entre sus principales aportes se encuentran la corrección de problemas del dashboard, la mejora de los filtros, la presentación del historial y la integración de las consultas predictivas.

También trabajó en la coherencia de los períodos y en el comportamiento de la interfaz cuando el usuario cambia de producto o tienda.

### 17.2. Aportes de Erika

Erika se encargó principalmente de revisar y validar el funcionamiento del modelo predictivo.

Su trabajo incluyó correcciones en las reglas de escenarios, integridad de archivos, control de respuestas, pruebas de integración y documentación técnica.

También desarrolló investigaciones para mejorar la precisión, comparó modelos alternativos y realizó una evaluación exploratoria del candidato D.

### 17.3. Aportes conjuntos

Ambos integrantes participaron en la integración del módulo H4.

El trabajo conjunto permitió comprobar que las predicciones pudieran consultarse desde la interfaz, que los escenarios respetaran las reglas del sistema y que las respuestas fueran comprensibles para el usuario.

La coordinación mediante GitHub y los documentos Markdown ayudó a organizar las actividades y conservar los resultados.

---

## 18. Dificultades y aprendizajes

Durante el desarrollo encontramos dificultades relacionadas con la calidad de los datos, las diferencias entre versiones y la conexión de los componentes.

También aprendimos que una predicción puede ser técnicamente válida sin ser necesariamente precisa para todos los productos.

Por esta razón, fue importante revisar los errores por producto, mantener separadas las evaluaciones y reconocer las limitaciones de los datos sintéticos.

Los documentos `.md` facilitaron el seguimiento del trabajo. Permitieron conservar decisiones, registrar problemas y continuar las actividades sin repetir todo el proceso.

OpenCode también fue una herramienta de apoyo. Aprendimos a utilizar instrucciones específicas, indicar qué archivos podían modificarse y solicitar pruebas antes de considerar una corrección terminada.

El trabajo en equipo permitió dividir responsabilidades y revisar los cambios antes de integrarlos al proyecto.

## 19. Conclusiones

El desarrollo del módulo H4 permitió incorporar a RepuestoPro una herramienta para estimar ventas mensuales de repuestos y comparar escenarios.

Ross contribuyó principalmente con la preparación de datos, la integración del sistema y el desarrollo de las interfaces.

Erika se concentró en la validación del modelo, la corrección de las reglas predictivas, las pruebas y la investigación de alternativas para mejorar la precisión.

Durante el proceso se identificaron problemas de datos, diferencias entre versiones, errores de integración y dificultades en la presentación de resultados. Estos fueron corregidos o documentados según su alcance.

Las pruebas técnicas permitieron comprobar el funcionamiento del módulo. Además, la investigación experimental mostró oportunidades de mejora sin reemplazar la versión oficial.

La documentación y el control de versiones ayudaron a conservar las evidencias del trabajo.

En conjunto, el proyecto permitió fortalecer nuestros conocimientos sobre desarrollo de software, análisis de datos, modelos predictivos, pruebas y trabajo colaborativo.

---