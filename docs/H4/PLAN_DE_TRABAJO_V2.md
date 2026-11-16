# Plan de trabajo V2

## Cierre del calendario unificado 4.0.0. 16 de noviembre de 2026

Estado vigente: Ross completó el nuevo dataset, su validación y la presentación del historial hasta octubre de 2026. Se integró el backend necesario para usar el mismo historial al predecir noviembre. Los estados anteriores de 2.2.0 y 3.0.0 que siguen en este documento son históricos, no pendientes activos de esta entrega.

| Trabajo | Responsable del plan | Resultado de esta revisión |
|---|---|---|
| Dataset versionado, contrato temporal y validación | Ross | 4.0.0 publicado sin sobrescribir versiones anteriores |
| Gráficas, selectores y comparación de escenarios | Ross | Enero a octubre como historia, noviembre como pronóstico, selección compartida |
| Entrenamiento, selección y evaluación independiente | Erika | Ejecutado con la autorización ampliada del equipo, TEST nuevo evaluado una vez |
| API, artefacto fijado, errores y permisos | Erika | API integrada con 4.0.0, ADMIN protegido, abstenciones conservadas |
| Evidencia y pruebas locales | Ambos | Python, backend, frontend, builds y revisión visual con API real |

La entrega técnica no promete predicciones comerciales perfectas. De las 168 combinaciones con historia, 136 admiten una inferencia base y 32 se abstienen por stock fuera de TRAIN. Esa limitación sigue abierta para una futura versión con cobertura justificada, no se oculta para declarar un porcentaje de cierre. No ajustar el modelo con el TEST ya consumido.

La [guía oficial](H4_IMPLEMENTACION_MODELO_PREDICTIVO.md) contiene el periodo, split, métricas, supuestos, rutas y explicación completa de esta versión. No se utilizó Neon ni se modificaron RAW. Automotive sigue pendiente de licencia. No hay compras automáticas ni validación comercial con historia real certificada.

RepuestoPro. Ampliación de la predicción de ventas y preparación de la reposición. Elaborado el 10 de noviembre de 2026, America/La_Paz.

**Estado vigente: referencia 2.2.0 conservada. Ross entregó el dataset ampliado 3.0.0 y la interfaz por contrato. La comparación real de escenarios sigue pendiente del backend de Erika.** La revisión del audio del anexo 46 corrige el alcance de los cierres anteriores. El anexo 45 registra README, recuperación y dashboard local. Ningún cierre de replay debe interpretarse como cumplimiento de cambios interactivos de precio, cotización, cantidades o logística.

Estado histórico del anexo 29: Estado: V2-11 cerrado para la pantalla administrativa de replay académico. Controles de producto, tienda, mes aprobado y horizonte fijo, gráfico y tabla, métricas guardadas, límites y trazabilidad implementados. Pasaron 12 pruebas de interfaz y dos controles con la respuesta real del adaptador, además de tipos y build. Se revisó el componente con fixtures en escritorio y a 390 píxeles. TEST permanece consumido e intacto. Los anexos 29 y 30 explican el cierre y cuándo ampliar el dataset sin sobrescribir 2.1.0.

## 1. Objetivo y significado de una entrega completa

La versión actual predice ventas mensuales con tres meses anteriores y dos variables del calendario. V2 estudiará precios, modalidad de venta, disponibilidad, tipo de cambio y características del producto. Además preparará la información necesaria para decidir cuándo reponer. La consulta permanecerá en el administrador. El simulador editable seguirá separado.

No existe una predicción con 100 % de aciertos garantizados. Una entrega completa significa que todos los requisitos aprobados tienen una implementación comprobada, errores controlados, evidencia y aceptación del equipo. La confiabilidad predictiva se evaluará con datos separados, métricas y límites explícitos. Un buen resultado sintético no certifica funcionamiento comercial.

La pregunta principal seguirá siendo: ¿cuántas unidades podrían venderse el próximo mes de un producto en una tienda? El target inicial seguirá siendo ventas brutas observadas válidas, no demanda perdida. La pregunta de reposición será distinta: ¿cuánto pedir y cuándo, considerando ventas previstas, stock, compromisos y tiempo de espera?

## 2. Punto de partida comprobado en el código

Esta revisión es de archivos locales. No certifica que los campos estén completos en la base real ni que las migraciones locales estén aplicadas allí. Las fuentes principales son el [schema](../../backend/prisma/schema.prisma), las [rutas de ventas](../../backend/src/modules/sales/sales.routes.ts), las [rutas de costos](../../backend/src/modules/costs/costs.routes.ts) y la [pantalla de costos](../../frontend/src/pages/CostsPage.tsx).

| Tema | Evidencia actual | Consecuencia para V2 |
|---|---|---|
| Venta histórica | Sale.saleDate, Sale.status, Sale.locationId y SaleItem.quantity, unitPrice, subtotal | Existe base para agrupar operaciones válidas por producto, tienda y mes. Debe comprobarse su calidad |
| Modalidad comercial | Sale.type distingue NORMAL y MAYOR. El flujo NORMAL admite priceMode POR_MAYOR. SaleItem no tiene priceMode | NORMAL no equivale automáticamente a por menor. No clasificar el historial comparando importes actuales |
| Precios | Product.price1 respalda por menor, Product.wholesalePrice por mayor. Product.price2 es legacy | Los valores actuales no reconstruyen el precio publicado de cada mes. El precio vendido tampoco registra ofertas sin ventas |
| Moneda y costo | Cost.exchangeRate es opcional. Existen costPrice, percentage, supplierId y date | Revisar unidades, fecha, correcciones y significado de la cotización. No asumir una serie diaria del mercado |
| Valor por defecto | CostsPage usa 6.96 inicialmente y en una reconstrucción cuando falta cotización | Ese valor de interfaz no demuestra una cotización histórica real. No rellenar faltantes silenciosamente |
| Disponibilidad | Inventory.stock y minStock representan el estado actual | No utilizarlos como stock de meses pasados. La reconstrucción debe incluir todas las entradas, salidas y ajustes |
| Tránsito interno | Movement.date, receivedAt, status y receivedQuantity | Puede estudiarse el traslado entre ubicaciones con registros completos. No equivale a importación desde proveedor |
| Reposición interna | ProductRequest.expectedDate e historial de estados | Separar fecha prevista de recepción real. Revisar estados legacy, cancelaciones y entregas parciales |
| Proveedor e importación | Supplier, Cost y PurchaseInvoice. No se observa un ciclo completo explícito de pedido internacional, despacho y llegada | Identificar la información faltante antes de calcular tiempos de importación |
| Devoluciones | Return.date, quantity, disposition, inspectedAt y restockedQuantity | No toda devolución vuelve a stock vendible. No restar devoluciones futuras a las entradas de una predicción pasada |

## 3. Cobertura de las vistas del administrador

Revisar una vista no obliga a convertir todos sus campos en variables del modelo. Algunos datos sirven para validación, permisos o reposición. Los reportes no deben duplicarse como fuentes independientes de las mismas ventas.

| Vista o información relacionada | Trabajo necesario | Uso previsto |
|---|---|---|
| Dashboard | Resolver y certificar su error pendiente mediante un entorno autorizado. Contrastar periodos y totales | Verificación del sistema. No sustituir fallos por estadísticas ficticias |
| Predicción de ventas | Revisar consulta actual, origen, mes objetivo, métricas, permisos y errores | Mantener V1 disponible mientras se valida V2, sin presentarla como V2 |
| Inventario y catálogo | Stock por ubicación, mínimos, ajustes, productos nuevos, incompletos o descontinuados | Disponibilidad, selección y controles. La descontinuación no se presume registrada |
| Ventas | Fecha de negocio, cantidades, precio histórico, duplicados, estado y anulación | Fuente principal de ventas observadas válidas |
| Ventas por mayor | Modalidad real por línea, pedidos excepcionales y compromisos conocidos | Variables históricas o tratamiento de pedidos firmes, sin doble conteo |
| Devoluciones | Cantidad, fecha, motivo, inspección y destino | Reporte separado, calidad y stock recuperable |
| Solicitudes | Tiempos previstos y reales, estados, cancelación y recepción parcial | Reposición interna y seguimiento |
| Movimientos | Ubicación de salida y llegada, tránsito, recepción y reintentos | Stock disponible y tiempo de traslado |
| Costos y proveedores | Moneda, tipo de cambio, costo en bolivianos, porcentaje y datos de factura | Historia de compra y reglas de costo. Revisar si flete, seguros o aduana están incluidos para no sumarlos dos veces |
| Precios | Precios por menor y mayor, vigencia, descuentos y promociones | Cambios conocidos antes de predecir. No confundir reducción puntual con precio de lista |
| Reportes | Ventas por producto, tienda, categoría, marca, vehículo, proveedor y modalidad | Conciliación y análisis de errores con las mismas reglas de negocio |
| Configuración y ubicaciones | ADMIN, TIENDA, INVENTARIO, permisos y ubicación | Seguridad y alcance. Evitar datos personales como features |
| Clientes, pagos y entrega | Pedidos firmes, crédito, pagos pendientes y entrega | Definir compromisos. No duplicar ventas por cada pago ni usar nombres, NIT o referencias bancarias |
| Importación, exportación y búsqueda por imagen | Trazabilidad de importaciones, formatos, selección correcta y disponibilidad | Evitar duplicados y regresiones. No agregar imágenes al modelo tabular sin otro objetivo aprobado |

## 4. Orden de trabajo y reparto

Reparto acordado por el equipo: **Erika se encarga del backend. Ross se encarga del frontend y del dataset.** Ambos trabajan juntos en reglas, evaluación e integración. Esta asignación sustituye el reparto anterior únicamente para V2, sin cambiar la autoría del trabajo histórico. No implica generar o entrenar durante esta tarea documental.

La ampliación interactiva tiene tareas detalladas y dependencias en el **anexo 47**. Es el reparto vigente para lo pedido en el audio. Los identificadores V2 anteriores se conservan para trazabilidad y no deben sumarse otra vez como tareas independientes. El contrato documental está preparado, la API y el motor nuevos todavía no están implementados.

### Parte 1. Backend — Erika

- [x] **V2-01. Auditar las fuentes del backend para el alcance académico.** La revisión local del 14 de noviembre identificó modelos, campos, fechas, estados, fuentes editables y faltantes de las vistas administrativas. La matriz del anexo 11 conserva la evidencia del código. Se cierra la auditoría local de fuentes porque la primera V2 utilizará observaciones sintéticas, según aprobación del usuario. No certifica filas de Neon, calidad comercial ni una revisión personal de Erika que no se haya registrado. **Responsable de backend:** Erika. **Entrega:** matriz de fuentes y limitaciones.

- [x] **V2-09A. Definir el contrato inicial de datos e inferencia.** La especificación local contiene entradas, tipos, unidades, disponibilidad, respuestas, errores e identidad de versiones. Tiene pruebas del contrato y del validador de fechas. El usuario aprobó el alcance académico, las referencias iniciales y el criterio de evaluación. Se cierra el diseño inicial para preparar datos. No es una API V2 implementada ni un contrato final de features. Erika revisará el contrato final al implementar backend, con la consistencia real comprobada en V2-09B. **Entrega:** contrato inicial para el alcance académico. **Depende de:** V2-03.

- [x] **V2-09B. Comprobar el contrato con el modelo seleccionado.** Actualizado a 2.2.0 en el anexo 44. Cinco features utilizadas, 17 columnas transportadas, hash, preprocesamiento, unidades, corte y política comprobados. Las 504 predicciones de VALIDATION coinciden con el experimento. El contrato separado inference.v2_2.json conserva la identidad. No se repitió TEST. La evidencia 2.1.0 del anexo 27 se conserva.

- [x] **V2-10. Conectar el modelo V2 con la API.** El puente administrativo y el servicio consumen la inferencia 2.2.0 fijada. ADMIN consulta catálogo y predicción. TIENDA e INVENTARIO reciben 403. Sesión ausente, inválida o revocada recibe 401. Se verificaron snapshots, errores, integridad y cadena real HTTP/Node/Python sin Neon. admin_api.v2_2.json y anexo 44. No hay fallback automático a versiones anteriores.

- [~] **V2-12. Diseñar el cálculo de reposición.** El contrato de escenarios del anexo 47 define el cálculo explicativo H4, con reservas, compromisos, tránsito, seguridad, mínimos, múltiplos y fechas. Erika implementará las reglas y sus pruebas. La ejecución comercial de compras o movimientos sigue para H5. No se considera implementado por tener una fórmula documental.

- [ ] **V2-14. Validar el backend y revisar el dashboard.** Erika comprueba permisos, contratos, inferencia, indisponibilidad y ausencia de regresiones. Diagnostica el fallo real del dashboard únicamente en un entorno permitido. **Entrega:** pruebas backend y reporte de hallazgos. **Orden:** pruebas durante el desarrollo y cierre después de V2-10. No declarar resuelto el dashboard solo por mejorar su mensaje.

- [x] **V2-18. Preparar recuperación de versiones.** Recuperación local explícita 2.2.0 → 2.1.0 → 2.2.0 mediante DEMAND_RELEASE, con identidad de servidor y frontend, rechazo de snapshots cruzados y sin fallback automático. No modifica artefactos, datasets o TEST. Evidencia en anexo 45. No se cambió la versión de un servidor productivo.

Erika aporta la interpretación de las fuentes y los mecanismos backend para consultarlas cuando estén autorizados. No construye, genera ni mantiene el dataset. Si se requieren cambios de registro, Prisma o migraciones, primero documenta su necesidad y los presenta para aprobación. El plan no permite aplicarlos sobre Neon.

### Parte 2. Frontend y dataset — Ross

- [x] **V2-02. Auditar las pantallas del administrador.** La matriz local del anexo 11 cubre 15 áreas administrativas. El recorrido visual posterior comprobó 13 vistas del administrador más login en escritorio y pantalla estrecha con fixtures, sin backend operativo ni Neon. Se corrigieron pestañas fuera de pantalla en Reportes y Configuración. Las pruebas aisladas revisan consulta predictiva, dashboard, ventas, reportes y protección de rutas. Se cierra la auditoría local de pantallas para preparar el dataset. No certifica datos productivos, cada operación comercial ni integración V2. **Entrega:** inventario de pantallas y necesidades del dataset. Evidencia en anexo 12.

- [~] **V2-04. Definir la estructura final del dataset.** El diccionario de diseño 2.0.0 define 24 columnas de la tabla supervisada, sus tipos, unidades, origen, disponibilidad, faltantes y ejemplos. También define la base mensual y la tabla de escenarios. Contiene 17 features, 3 identificadores, 1 target y 3 controles. El origen de ventas y variables nuevas será simulado, con categoría del catálogo congelado. Se cierra el diseño, no la construcción o validación del dataset. **Entrega:** [diccionario V2](../../ml/demand/v2/contracts/dataset_columns.v2.json). **Depende de:** V2-01, V2-02, V2-03, V2-09A y V2-04D. **Revisión de alcance del anexo 46:** El diccionario 2.2.0 se conserva. Falta revisar el contrato de escenarios económicos y logísticos del audio del docente.

- [x] **V2-04A. Registrar fuentes externas.** Ross inventaría los originales ya descargados, registra tamaño, formato, SHA-256 y manifest por fuente. No descarga de nuevo ni transforma RAW. **Entrega:** trazabilidad e integridad verificadas. La estructura y el registro inicial se prepararon el 11 de noviembre de 2026. La comprobación local del 14 de noviembre confirmó los cinco manifests y la integridad de los 136 archivos RAW. Se cierra el registro técnico, sin afirmar aceptación de Erika ni aprobar el uso de todas las fuentes. Las URL y fechas de adquisición no acreditadas permanecen UNKNOWN.

- [x] **V2-04B. Revisar procedencia y licencia.** Revisión documental realizada el 11 de noviembre de 2026 sobre las cinco fuentes. La [matriz de procedencia](../../ml/demand/reports/v2/source_provenance_matrix.json) registra evidencia primaria, condiciones y puntos desconocidos. Monash Car Parts y UCI Online Retail II tienen CC BY 4.0 verificada y quedan habilitados para el siguiente perfilado académico local con atribución. Automotive sigue bloqueado por licencia de sus datos. M5 y Favorita fueron habilitados después para futuro perfilado académico por Ross, con sus confirmaciones del 15 de noviembre registradas en los anexos 32 y 33, sin autorizar procesamiento en estas tareas. La revisión terminada no significa que todas las fuentes estén aprobadas, que se conozca su descarga original o que el equipo haya firmado aceptación. No interpretar licencia de software como permiso de todos sus datos.

- [x] **V2-04C. Perfilar datasets externos del alcance inicial aprobado.** El 14 de noviembre de 2026 se completó el perfilado descriptivo autorizado de Monash y UCI, sin limpiar ni transformar originales. Los [resultados de Monash](../../ml/demand/reports/v2/profiling/profile-20261114-01/monash_car_parts_profile.json) y los [resultados de UCI](../../ml/demand/reports/v2/profiling/profile-20261114-01/uci_online_retail_ii_profile.json) conservan hashes y estadísticas. Después del perfilado, el usuario aprobó excluir Automotive, M5 y Favorita del alcance inicial, conservándolos bloqueados e intactos. Por eso se cierra el perfilado del alcance aprobado, no el de las cinco fuentes. Perfilar no crea por sí mismo una versión curated. **Entrega:** perfil y reporte de calidad. **Depende de:** V2-04B y autorización de procesamiento.

La revisión V2-04B no ejecutó V2-04C. El perfilado posterior de Monash y UCI confirmó la cobertura documentada, pero encontró faltantes en Monash, repeticiones entre hojas de UCI, cancelaciones, precios no positivos y valores extremos. No se eliminaron registros. Antes de utilizarlos se requieren decisiones de compatibilidad y tratamiento. Automotive y M5 solo pueden continuar con revisión documental de permisos, no análisis de sus valores. Favorita requiere confirmar aceptación previa y acceso conforme a sus reglas, sin compartir RAW con personas no autorizadas. No se aceptaron términos en nombre del equipo. Ninguna de estas decisiones autoriza uso comercial del proyecto con datos de Kaggle ni mezcla con Product.id.

La [verificación de requisitos previos](../../ml/demand/reports/v2/profiling/profile-20261114-01/prerequisite_audit.json) distingue preparación técnica de cierre del plan. El anexo 11 registra el avance local posterior a esa verificación. No corresponde afirmar que todos los puntos anteriores están al 100 %. Falta el cierre formal de la auditoría de pantallas V2-02, las reglas conjuntas V2-03, la estructura final V2-04 y el contrato inicial V2-09A. El contrato del dataset sigue en DRAFT. El perfilado autorizado no aprueba esas decisiones ni habilita la construcción de V2.

- [x] **V2-04D. Crear la matriz de compatibilidad.** Se compararon dominio, frecuencia, periodo, moneda, unidades, geografía, producto y tienda, modalidad, disponibilidad y tiempos. Monash queda como referencia directa de dominio e intermitencia. UCI queda como referencia complementaria de transacciones, precios y cancelaciones. No se unirán sus filas ni se reasignarán IDs. No se calculó calibración. **Entrega:** [matriz de compatibilidad](../../ml/demand/reports/v2/compatibility/compatibility-20261114-01/source_compatibility_matrix.json), con límites y reglas para un procesamiento posterior. La consistencia con el backend implementado sigue correspondiendo a Erika en V2-09B. **Depende de:** V2-04C.

- [~] **V2-05. Diseñar los escenarios de datos.** Se definieron 57 escenarios, con 12 normales, 25 adversos y 20 ambiguos, además de ocho combinaciones obligatorias. Cada caso registra supuestos, variables relacionadas, reloj, tratamiento, elegibilidad y evidencia futura. Los niveles numéricos son supuestos de diseño, no calibración empírica. No se ejecutó simulación. **Entrega:** anexo 14 y registro estructurado en preparation.v2.json, apartado scenario_design. **Depende de:** V2-03, V2-04 y V2-04D, comprobados antes de iniciar esta etapa. **Revisión de alcance del anexo 46:** Se conservan los 57 escenarios diseñados. Falta concretar y probar las intervenciones de precio y su relación con ventas, costo, cotización y disponibilidad.

- [~] **V2-05A. Calibrar o justificar el simulador con patrones aprobados.** Se fijó una configuración académica reproducible. Monash fundamenta intermitencia y tamaño positivo. UCI justifica estudiar colas y alertas de calidad, sin trasladar precios o tasas comerciales. Los otros parámetros son supuestos explícitos o reglas del contrato. No se ajustó un simulador comercial ni se generaron observaciones. **Entrega:** anexo 15 y [configuración V2](../../ml/demand/v2/contracts/calibration.v2.json). **Depende de:** V2-04D y V2-05, verificados. **Revisión de alcance del anexo 46:** La calibración anterior se conserva. No existe una elasticidad de precio identificada. Falta justificar esos mecanismos sin atribuirlos falsamente a M5 o Favorita.

- [~] **V2-06. Construir el dataset V2.** Se implementó el generador aislado y se publicó el primer build académico 2.0.0/academic-20261114-03. Incluye 4.032 filas mensuales, 3.528 supervisadas, 4.413 registros de auditoría, ledger de stock y tránsito, contratos, split y hashes. La reproducción y las reglas mínimas de publicación pasaron. Es una variante declarada, no la ejecución de los 57 escenarios completos. No habilita entrenamiento. **Entrega:** anexo 16 y manifest del build. **Depende de:** V2-04, V2-05 y V2-05A, verificados. **Revisión de alcance del anexo 46:** El dataset 2.2.0 existe y permanece intacto. Todavía no hay un nuevo build que demuestre todos los mecanismos interactivos ampliados.

- [~] **V2-07. Preparar y validar el dataset.** Validación independiente del build y sus 24 columnas, 17 features, fórmulas, snapshots, disponibilidad, inventario, split y hashes. Se comprobaron 57 fixtures de política y ocho combinaciones. Estadísticas solo de TRAIN y VALIDATION. Hay advertencias por antigüedad de cotización constante, trayectoria económica única y ventas observadas de bajo volumen. Se valida integridad de la variante inicial, no cobertura dinámica completa ni funcionamiento de backend. No se ajustaron transformaciones ni se autorizó entrenamiento. **Entrega:** anexo 17 y reportes inmutables de revisión. **Depende de:** V2-06. **Revisión de alcance del anexo 46:** La validación 2.2.0 sigue siendo válida. Falta comprobar una nueva realización coherente con los escenarios económicos ampliados, cuando se autorice.

- [~] **V2-11. Implementar la pantalla administrativa V2.** Cierre local actualizado a 2.2.0 en el anexo 44. El contrato, artefacto y política son los aceptados. Hay consulta real Node/Python, revisión visual a 1280 y 390 px, manejo de respuestas tardías y pruebas de roles. Streamlit permanece separado. Se conserva el cierre histórico 2.1.0. No certifica una sesión productiva o previsión comercial en vivo. **Revisión de alcance del anexo 46:** El replay 2.2.0 está implementado. Faltan controles de escenarios, edición validada y comparación base/escenario solicitados en el audio.

- [~] **V2-13. Diseñar la presentación de reposición.** La ampliación del docente incluye una explicación interactiva de reposición en H4. Ross implementará la vista con cantidad, stock, reservas, tránsito, compromisos, llegada y límites del cálculo, según H4-R09. Depende del cálculo de Erika en H4-E06. Compras y cambios operativos quedan para H5.

- [~] **V2-15. Validar frontend y dataset.** Cierre local del alcance H4 2.2.0. El dataset validado permanece intacto. Pasaron las 248 pruebas frontend, incluidas rutas y menú por rol, además de tipos y build. Se comprobaron tres meses a través del adaptador real y revisión visual aislada con la API y el artefacto 2.2.0. Sin conexión de base de datos. No certifica operaciones comerciales sobre Neon. Evidencia en anexo 44. **Revisión de alcance del anexo 46:** Las regresiones del replay están comprobadas. Falta validar el flujo interactivo ampliado, sus efectos y casos adversos.

Ross es responsable del dataset completo, no solo del CSV final. Incluye fuentes identificadas, escenarios, generador, preparación de variables, split, validaciones, documentación y reproducción. Trabaja con el contrato acordado con Erika para que el backend utilice las mismas entradas.

**Tareas que completan juntos.** Cada una requiere revisión de ambos, sin cambiar la propiedad del backend o del dataset.

- [x] **V2-03. Acordar las reglas del alcance académico.** La especificación fija tratamiento conservador de faltantes, modalidades no persistidas, anulaciones, ceros, pagos y devoluciones. El usuario aprobó ventas y variables nuevas simuladas, Monash y UCI como referencias, selección con VALIDATION y TEST nuevo. No se exige una tolerancia comercial en unidades para este experimento. Los plazos de proveedor se mantienen separados para reposición. La aprobación quedó registrada en el anexo 12. No sustituye un acuerdo comercial de la empresa. **Entrega:** reglas académicas, límites y ejemplos. **Depende de:** V2-01 y V2-02.

- [~] **V2-08. Comparar y seleccionar modelos, alcance académico.** El usuario aceptó el bosque de cinco entradas 2.2.0 y sus límites antes de abrir TEST. Se fijaron artefacto y política. Una única evaluación final obtuvo MAE 9,2046 frente a 12,8690 del baseline, sin ajustes posteriores. Los anexos 42 a 44 conservan comparación, diagnóstico, selección y evaluación. El cierre 2.1.0 del anexo 26 permanece intacto. **Revisión de alcance del anexo 46:** La selección y TEST únicos de 2.2.0 se conservan como referencia. La selección de un modelo que cumpla el alcance interactivo ampliado queda pendiente, sin reutilizar TEST consumido.

- [ ] **V2-16. Probar la integración y preparar la defensa.** Ambos recorren administrador, backend y modelo, verifican casos normales, errores y recuperación. Ensayan la presentación y registran aceptación cuando realmente ocurra. **Entrega:** evidencia conjunta y pendientes explícitos. **Depende de:** V2-10, V2-11, V2-14, V2-15 y V2-18. V2-12 y V2-13 forman parte ahora de la demostración explicativa ampliada de H4. Su operación comercial automática continúa fuera de H4.

- [~] **V2-17. Registrar el trabajo.** Los registros y decisiones se actualizan durante cada etapa. Su cierre final depende de terminar el alcance aprobado.  Cada integrante documenta sus decisiones, pruebas y prompts. Ambos mantienen el registro de experimentos y la guía oficial, sin inventar resultados ni sobrescribir historia. **Entrega:** trazabilidad actualizada. **Orden:** desde el inicio hasta el cierre.

El orden de Ross será auditoría → reglas y contrato → registro de fuentes → revisión de fuentes → profiling → compatibilidad → escenarios → calibración → dataset V2 → validación → experimentos → integración administrativa → cierre. La reposición explicativa se incorpora al alcance interactivo H4. La ejecución comercial permanece para H5. Erika puede avanzar en backend y Ross en interfaz con fixtures después de acordar el contrato. Esas pruebas no certifican la integración hasta conectar ambos componentes. No entrenar con el dataset incompleto ni integrar un modelo sin versión identificada.

Antes de editar, acordar los archivos que tocará cada integrante. El contrato debe fijar nombres, tipos, unidades, campos opcionales, errores, versión y ejemplos. Cada cambio del dataset que afecte a las entradas se comunica a Erika antes de usarlo en inferencia. Cada cambio de respuesta backend se comunica a Ross antes de conectarlo a la interfaz. Ninguna tarea se marca completa únicamente porque existe un test.

## 5. Datos que debemos preparar

La ampliación necesita tres estructuras relacionadas. Solo la segunda es la tabla que recibe el modelo. Los nombres nuevos de esta sección son propuestas, no campos existentes de Prisma.

Esta sección conserva los grupos conceptuales. La selección final del primer diseño está en el anexo 13. Costo, marca, modelo, año, proveedor y reposición no se convierten automáticamente en features por aparecer en una vista administrativa.

**Registro de operaciones e información externa.** Mantener ventas y líneas, cambios de precios con vigencia, compras, cotizaciones, disponibilidad y recepciones. Cada registro necesita identificar cuándo ocurrió y cuándo estuvo disponible para el sistema. Los cambios posteriores no deben reescribir silenciosamente la historia usada por un experimento. Si la fuente actual es editable y no conserva versiones, documentar que la reconstrucción no está certificada.

**Dataset mensual predictivo.** Una fila por producto, tienda y mes objetivo. Clave propuesta: productId + locationId + mes_objetivo. El target será target_ventas_mes. No debe contener duplicados de esa clave. El mes objetivo debe estar cerrado para tener target de entrenamiento. Una solicitud de inferencia futura no tiene ese target.

| Grupo y columnas conceptuales | Función | Regla de disponibilidad |
|---|---|---|
| productId, locationId, mes_objetivo | Identificación y agrupación | IDs categóricos, nunca cantidades. Evaluar codificación solo si se aprueba incorporarlos como features |
| ventas_mes_anterior, ventas_hace_2_meses, ventas_hace_3_meses | Features iniciales | Meses completos anteriores. Cero confirmado no equivale a dato faltante |
| mes_sin, mes_cos | Calendario | Mes objetivo conocido al emitir |
| unidades anteriores por menor y por mayor, número de operaciones y concentración de pedidos | Features candidatas | Solo después de resolver la modalidad histórica. Mantener desconocidos cuando no se pueda certificar |
| precio vendido histórico por modalidad y precio publicado histórico, si existe | Features candidatas distintas | El promedio vendido puede ponderarse por unidades, pero depende de qué se vendió. Sin ventas no existe ese promedio, no se inventa |
| precio planificado por modalidad y variación porcentual | Features opcionales de escenario | Solo si estaba aprobado y disponible en el corte. Si falta, usar una ruta declarada sin esa entrada o abstenerse |
| cotización última conocida, antigüedad y variación comparable | Features candidatas | Fuente, moneda, unidad Bs/USD y fecha explícitas. No usar promedio futuro ni rellenar con 6.96 por defecto |
| costo histórico en bolivianos y antigüedad | Feature experimental | Confirmar costo unitario, fecha y disponibilidad. Nunca sustituirlo por Product.cost actual para meses anteriores |
| días sin stock y días con datos válidos del mes anterior | Features y controles candidatos | Exigen historia verificable. No reconstruir a partir del stock actual si faltan operaciones |
| categoría, marca y otras características del producto | Features opcionales | Campos confiables al corte. Categorías nuevas con tratamiento explícito. No interpretar Product.year como un año numérico simple sin revisar rangos |
| target_ventas_mes | Target | Cantidad bruta de ventas válidas del mes objetivo. Devoluciones aparte. Revisar anulaciones y su fecha para evitar reconstrucciones con información posterior no declarada |
| origen, escenario, fuente, versión, corte y calidad | Metadatos de auditoría | No son entradas del modelo. Escenario sintético, demanda latente y parámetros del generador quedan fuera de features |

No todos estos candidatos deben entrar en la versión final. promedio_3_meses seguirá excluido inicialmente por ser derivable de los tres lags. Eliminar datos personales, IDs de vendedor, referencias de pago y cualquier resultado futuro. La cotización de mercado y la utilizada en una compra son series distintas. No mezclarlas sin identificar su significado.

**Información para reposición.** Usar stock vendible a la fecha de consulta, unidades pendientes de recibir, reservas o compromisos válidos, devoluciones inspeccionadas, tiempo de proveedor, tiempo de traslado interno, margen de seguridad, frecuencia de revisión, presentación y compra mínima. Distinguir lo existente en el sistema de lo que falta registrar. Evitar contar dos veces una solicitud y su movimiento asociado. Las devoluciones en inspección no son stock vendible. Las recepciones parciales solo habilitan lo recibido.

La necesidad se calculará para el tiempo de espera y, si corresponde, el periodo entre revisiones. Restar de esa necesidad la posición de inventario definida por stock vendible, entradas firmes pendientes y compromisos, sin duplicar pedidos ya incluidos en el pronóstico. Ajustar a presentaciones aprobadas y nunca sugerir una cantidad negativa. El anexo 47 fija una política académica mensual explicativa. No sustituye la definición de una política comercial definitiva.

Si el proveedor tarda dos meses, una predicción a un mes no resuelve todo el horizonte. No multiplicar automáticamente por dos ni sumar predicciones sucesivas sin comprobar su error. La ampliación de horizonte se evaluará aparte, con incertidumbre y validación propias.

## 6. Origen del dataset y escenarios

V1 y sus archivos congelados se conservan. V2 tendrá una carpeta y versión diferentes cuando se autorice implementarla. El primer dataset ampliado será sintético mientras no exista historia real suficiente y certificada. Utilizará el catálogo de referencia válido y tiendas de referencia, indicando su fecha. No presentarlos como catálogo actual consultado en Neon.

Partir de octubre 2024 a septiembre 2026, 24 meses, con seed 42 para reproducibilidad. Revisar si ese periodo basta para las nuevas variables antes de fijarlo. La cantidad de productos no crea años adicionales de historia económica. Una cotización compartida por mes tampoco representa cientos de observaciones económicas independientes.

El diseño incluirá rotación alta, media y baja, ceros válidos, efecto tienda, tendencia moderada, estacionalidad y ruido controlado. La moneda debe tener una serie coherente por fuente y fecha. Probar aumentos como Bs 120 a Bs 150, sin programar que todas las ventas deban caer un porcentaje fijo. Separar costo en dólares, conversión y precio al cliente. Revisar fletes, porcentajes y moneda para evitar doble conversión.

| Escenario | Riesgo que cubre | Respuesta prevista |
|---|---|---|
| Precio estable y stock suficiente | Caso normal | Comparar con baseline y conservar trazabilidad |
| Aumento de precio, descuento o promoción | Cambio de comportamiento | Usar información conocida. Describir relaciones simuladas como supuestos, no como efectos comerciales probados |
| Variación de moneda y cotización antigua | Costo distinto o información desactualizada | Registrar fuente y antigüedad. No simular precios futuros como si fueran conocidos |
| Pedido mayorista excepcional | Picos no recurrentes | Revisar error y concentración. No eliminar automáticamente ventas legítimas |
| Sin stock o recepción tardía | Venta observada inferior a demanda | Identificar limitación y disponibilidad. No fabricar demanda perdida como target real |
| Producto o tienda nuevos | Falta de historia | Ruta explícita de referencia, agregación justificada o abstención. Nunca completar meses inexistentes con ceros |
| Descontinuado o nueva categoría | Producto fuera del alcance aprendido | Revisar estado y codificación. No recomendar compra automática |
| Mes incompleto, duplicado o faltante | Historia inválida | Bloquear entrenamiento válido o separar para revisión. No cortar meses silenciosamente |
| Devolución posterior, anulación o inspección pendiente | Confusión entre venta, caja y stock | Tratar fechas, cantidades y destinos por separado |
| Entrega parcial, tránsito cancelado o reintento | Doble conteo de disponibilidad | Considerar cantidades realmente pendientes y estados válidos |
| Tipo de cambio o modalidad desconocidos | Caso ambiguo | Marcar desconocido y limitar el alcance. No inferir mediante el precio actual |
| Registro inválido, fuga o mezcla real/sintética | Resultado engañoso | Separar casos adversos de validación del dataset entrenable. No introducir ventas brutas negativas |

Probar distintas intensidades y mecanismos de simulación. Reservar escenarios o ejecuciones independientes para comprobar que el modelo no solo reproduce la fórmula del generador. No reutilizar sus parámetros internos como entradas. Se podrá variar la seed en pruebas adicionales, manteniendo un manifiesto por ejecución. Ningún resultado sintético sustituirá un piloto real posterior.

## 7. Experimentos y prevención de información futura

Comparar primero la referencia que repite el último mes. Evaluar después LinearRegression y RandomForestRegressor. MLP seguirá siendo opcional, sin arquitectura obligatoria. Random Forest no tiene la victoria garantizada. Un modelo más complejo se conserva solo si aporta utilidad dentro de los criterios acordados.

Construir una referencia con las cinco features de V1 sobre las mismas filas de evaluación de V2, sin sobrescribir el artefacto V1. Agregar por etapas modalidad, precios, disponibilidad, moneda y características. Comparar también sin cada grupo para comprobar su aporte. Mantener el mismo target, periodos y población comparable. Una mejora causada por excluir casos difíciles debe explicarse con cobertura, no presentarse como avance general.

Como punto de partida, tres meses de historia y 21 meses objetivo permiten 15 meses TRAIN, tres VALIDATION y tres TEST. Si se mantiene el periodo inicial, corresponden a enero 2025–marzo 2026, abril–junio 2026 y julio–septiembre 2026. Sin embargo, ese TEST ya fue observado en V1. No puede declararse una reserva nueva e independiente para seleccionar V2. Antes de experimentar se definirá otra reserva de datos o una ejecución sintética independiente no inspeccionada. Si no existe reserva válida, informar esa limitación y no afirmar evaluación final independiente.

Nunca dividir filas al azar. Todas las filas del mismo mes permanecen juntas. Ajustar imputación, codificación y escalado únicamente en TRAIN. Comprobar validación temporal por bloques mensuales dentro de TRAIN, no mediante cortes que separen filas del mismo mes. Para evaluación de un paso se admite el observado anterior solo cuando ese mes ya habría cerrado. La evaluación de varios meses desde un único corte requiere otro procedimiento.

El modelo lineal puede utilizar escalado. Random Forest no lo necesita. La MLP sí requiere preparar cuidadosamente las escalas. Ninguna transformación aprende de VALIDATION o TEST. No introducir como features el target, total del mes objetivo, precios medios futuros, devoluciones futuras, cotizaciones futuras ni stock posterior.

La métrica principal será MAE en unidades. RMSE mostrará el peso de errores grandes. R² será complementaria y no se llamará precisión. MAPE no será principal por los ceros. Analizar error firmado, cobertura, ceros, mayoristas excepcionales, rotación, producto y tienda. Definir antes de seleccionar modelos qué error es tolerable por grupo y qué mejora mínima justifica complejidad. No inventar esos límites ahora ni ajustarlos mirando TEST.

## 8. Integración, seguridad y seguimiento

Conservar `/panel/prediccion` como consulta administrativa y Streamlit como laboratorio editable. La pantalla V2 deberá indicar origen, versión de dataset y modelo, corte del historial, horizonte, entradas disponibles, variables faltantes, predicción y límites. Distinguir métricas históricas de un error futuro todavía desconocido. Si se permite simular otro precio, mostrarlo como escenario hipotético, no como prueba de que el aumento causará un cambio exacto de ventas.

Mantener autenticación y permisos reales de API. ADMIN tendrá alcance autorizado. Un acceso futuro por tienda requerirá control backend de su propia ubicación. No exponer costos o datos sensibles a roles no autorizados. No generar datos, entrenar, promover o escribir inventario al pulsar consultar. Modelos incompatibles o entradas insuficientes producen una respuesta explícita, no un cero inventado. Las versiones del contrato deben acordarse antes de modificar respuestas existentes.

El seguimiento incluirá errores en meses cerrados, cobertura, cambios en distribución, retrasos y faltantes. Una señal de cambio pide revisión, no demuestra por sí sola drift ni autoriza reentrenamiento automático. Los candidatos se comparan con datos reservados y V1 se conserva como respaldo. No desbloquear promoción por presión de presentación.

Guardar dataset, hashes, configuración, features, split, seed, versiones, parámetros, métricas, tiempo, origen y observaciones. Registrar experimentos de V2 de forma identificable sin editar registros congelados. Conservar los prompts en el [log existente](PROMPTS_MODELO_PREDICTIVO_H4.md). Añadir resultados solo después de ejecutarlos.

## 9. Criterios de aceptación

Las casillas siguientes corresponden a la aceptación completa de V2. El avance técnico parcial registrado arriba no implica su cierre. Aprobar este plan no certifica que las tareas ya se ejecutaron.

- [ ] Las vistas de administración tienen una fuente y una regla documentadas, incluso si sus campos no serán features.
- [ ] Modalidad, precios, moneda, fechas y tiempos están definidos sin confundir campos actuales con historia.
- [ ] Cada variable tiene tipo, unidad, fuente, vigencia, disponibilidad al corte, faltantes y uso autorizado.
- [ ] Existe una decisión explícita para datos que requieren nuevos registros o futuras migraciones, sin aplicar cambios productivos en esta planificación.
- [ ] Dataset real y sintético permanecen separados. Los casos inválidos no forman parte del entrenamiento válido.
- [ ] Se comprueban claves, cantidades, ceros, meses completos, duplicados, origen y ausencia de información futura.
- [ ] Las transformaciones se ajustan solo en TRAIN. La evaluación final reservada no dirige ajustes.
- [ ] El modelo cumple los límites de error acordados y se compara con baseline por grupos, además del promedio.
- [ ] Se registra la cobertura. Los casos desconocidos o fuera de alcance no se presentan como predicciones confiables.
- [ ] Pruebas backend, frontend, datos, inferencia y regresión de Streamlit pasan en un entorno aislado. Los fixtures no escriben en producción.
- [ ] Existe revisión visual de escritorio y pantalla estrecha. Si no se modifica móvil, se declara su alcance sin afirmar integración móvil nueva.
- [ ] Ventas, precios, stock, devoluciones, movimientos y búsqueda por imagen conservan sus contratos y permisos.
- [ ] El problema real del dashboard tiene diagnóstico certificado en un entorno permitido. No se marca resuelto solo por mejorar el mensaje.
- [ ] La consulta administrativa V2 muestra versión, origen y mes correctos, con errores de servicio controlados y sin resultados antiguos tras cambiar selección.
- [ ] Las evidencias, recuperación de V1, documentación, ensayo y aceptación de Erika y Ross están registrados.

Si falta un dato imprescindible, detener esa parte o reducir explícitamente el alcance. Si V2 no mejora, conservar la referencia y explicar el resultado. No ocultar pendientes para declarar un funcionamiento al 100 %.

## 10. Cómo empezamos

El orden de dependencias comienza por V2-01 y V2-02. La revisión local de fuentes y pantallas ya está registrada. La asignación se mantiene: Erika desarrolla backend, Ross prepara frontend y dataset. El alcance de esta revisión no acredita una consulta nueva a producción ni una revisión personal de Erika.

La primera V2 es académica y sintética. Se completaron registro, procedencia, perfilado, compatibilidad, diccionario, escenarios, justificación, construcción y validación de integridad de la primera variante. La evaluación de modelos, ampliación de cobertura dinámica, revisión con Erika y certificación comercial siguen pendientes. No existe modelo V2 entrenado.

No comenzar generando columnas supuestas ni entrenando otro modelo. El avance inicial se mide por decisiones verificadas y datos comprendidos. El objetivo final es una predicción evaluada y una aplicación comprobada, con límites honestos para su uso comercial.

## 11. Cierre de dependencias revisado el 14 de noviembre de 2026

La [matriz de administración y fuentes](../../ml/demand/reports/v2/preparation/prerequisites-20261114-01/admin_source_audit.json) registra 15 áreas, sus rutas, campos físicos, función para V2, faltantes y evidencia del código con hash. Cubre dashboard, predicción, inventario, producto, venta, mayorista, devolución, solicitud, movimiento, costos, precios, reportes, configuración, clientes y pagos, importaciones y búsqueda por imagen. Es una auditoría local de estructura y contratos. No acredita un recorrido visual completo ni consulta datos de Neon.

La [especificación técnica](../../ml/demand/v2/contracts/preparation.v2.json) reúne las reglas, las nueve columnas iniciales, siete grupos candidatos y el diseño de inferencia. Este último describe cómo consultar el modelo, no implementa una API V2. Conserva los endpoints V1 existentes. El servidor deberá calcular entradas desde una historia autorizada y comprobar versiones. El cliente no enviará target, stock actual ni precios para sustituir historia. Los errores por falta de datos serán explícitos.

| Dependencia | Trabajo local realizado | Condición que todavía impide su cierre completo |
|---|---|---|
| V2-01 y V2-02 | Matriz de pantallas, fuentes y faltantes contrastada con código actual | Revisión de Erika, recorrido visual completo y calidad real no certificada en esta tarea |
| V2-03 | Reglas de fechas, venta válida, anulaciones, modalidad, pagos, devoluciones, precios, moneda y disponibilidad | Aceptación conjunta y tolerancias de error por grupo |
| V2-04 | Diccionario inicial con rol, tipo, unidad, origen y disponibilidad. Variables nuevas separadas como candidatas | Fuentes y supuestos sintéticos de las variables nuevas todavía no aprobados |
| V2-04A y V2-04B | Registro técnico cerrado. Integridad de 136 RAW, cinco manifests y revisión documental comprobadas | Tres fuentes bloqueadas por condiciones de uso no resueltas. No se declara conocida la adquisición original |
| V2-04C | Perfilado de Monash y UCI terminado. Sus reportes anteriores se conservan | No autoriza perfilar las otras tres fuentes ni sumar las hojas de UCI sin resolver solapamiento |
| V2-09A | Diseño de entradas, errores, responsabilidades y versiones, con pruebas del contrato propuesto | Aceptación conjunta. No equivale a endpoints V2 implementados |
| V2-09B | Dependencia separada de V2-09A | Solo puede comprobarse después de V2-08, con un artefacto real |

Ejemplos de aplicación de las reglas: una venta NORMAL que eligió POR_MAYOR no se clasifica históricamente como minorista. Un producto sin registros completos durante un mes no recibe automáticamente ventas cero. Una devolución de febrero no cambia las entradas conocidas al predecir enero. Si una compra convirtió USD a bolivianos e incluyó gastos en costPrice, no se vuelve a multiplicar por la cotización. Un movimiento recibido parcialmente solo habilita la cantidad recibida. Una anulación posterior exige declarar el corte y la revisión del target, no reconstruir silenciosamente el pasado.

Los intervalos mensuales serán de inicio inclusivo a inicio del mes siguiente exclusivo en America/La_Paz. Por ejemplo, enero de 2026 comprende desde 2026-01-01T04:00:00Z hasta antes de 2026-02-01T04:00:00Z. El stock actual no permite explicar por sí solo los ceros de ese periodo. Monash aporta referencia de ventas intermitentes, mientras UCI aporta transacciones de otro dominio en GBP. Ninguno resuelve el historial Bs/USD, la modalidad de cada línea propia ni los plazos del proveedor.

Se ejecutaron 33 pruebas de estructura, procedencia, perfilado y contrato, 28 pruebas seleccionadas del frontend, 8 del backend y las comprobaciones de tipos de ambos proyectos. Todas las ejecuciones finales pasaron. La primera ejecución HTTP fue bloqueada por permisos de conexión local. La repetición con acceso a localhost pasó, manteniendo una dirección de base deshabilitada. No se ejecutaron suites de integración que escriban en base de datos. Esta selección de pruebas no acredita toda la plataforma ni sustituye la revisión visual.

El [reporte de cierre](../../ml/demand/reports/v2/preparation/prerequisites-20261114-01/closure_report.json) conserva estados y resultados. No se avanzó a compatibilidad, curated, calibración, generación del dataset o entrenamiento. Para cerrar completamente la preparación hace falta resolver las condiciones de la tabla. No se anotó una aceptación de Erika ni una certificación de producción que no ocurrieron.

La continuación del 14 de noviembre amplió la especificación con un esquema de respuesta. Un resultado correcto exige versiones de modelo, dataset, build y snapshot. Una abstención lleva motivo y prediction null, nunca cero inventado ni métricas de una consulta anterior. La simulación exige el modo académico y una advertencia explícita. Se separa el origen de las métricas del origen de la consulta. Estas son reglas del contrato propuesto, no una API V2 implementada. Las comprobaciones semánticas de cortes, versiones, fechas disponibles y coincidencia de IDs siguen declaradas para la futura implementación.

Las pruebas nuevas detectaron que el formato date-time podía quedar sin comprobar cuando faltaban dependencias opcionales de jsonschema. Se corrigió el validador de metadata V2 con una comprobación local de fecha, hora y zona explícita. También rechaza fechas inexistentes, horas inválidas y offsets mal formados. El mismo control se aplica a los manifests, sin cambiar sus bytes. La ejecución final aprobó 43 pruebas de estructura, procedencia, perfilado y contrato. No repite ni reemplaza los resultados anteriores de frontend o backend.

Se propuso además una regla académica de selección: comparar las mismas filas de VALIDATION, revisar MAE, RMSE, cobertura y grupos. Ante empate se prefiere la alternativa más simple. Si ningún modelo mejora, se conserva el baseline y se registra el resultado. Esto no fija una tolerancia comercial en unidades ni garantiza que Random Forest gane.

Se preparó un servidor temporal en ml/demand/tmp/visual-20261114-01 para revisar las pantallas reales con una API de prueba. No utiliza el backend operativo, bloquea rutas /api/ y deshabilita escrituras. El navegador agotó la conexión local y después bloqueó la continuación desde su página de error. Por eso no se acreditó ninguna pantalla ni tamaño de pantalla como revisado. No se cambió el firewall ni se usó Neon para superar el bloqueo. El servidor temporal se detuvo. Los objetos de prueba son solo fixtures de interfaz, no dataset V2, ventas propias ni resultados de modelos.

El [resultado de la continuación](../../ml/demand/reports/v2/preparation/visual-20261114-01/review.json) separa el fallo del entorno visual del error original del dashboard. El recorrido visual, la aceptación conjunta, las fuentes de variables nuevas y los permisos pendientes siguen abiertos. No se avanzó a V2-04D ni se declararon todos los requisitos completos.

## 12. Revisión visual resuelta y alcance inicial aprobado

Esta sección registra la continuación posterior del 14 de noviembre de 2026. Actualiza el estado de los pendientes descritos en el anexo 11, sin borrar sus reportes históricos. Se comprobó que el servidor aislado responde HTTP 200. El navegador logró abrir una pestaña nueva. La carga de Tailwind requirió iniciar el servidor de prueba desde el directorio de frontend. No se cambió el firewall ni se redujeron controles del sistema. No fue necesario consultar Neon.

Se revisaron 13 vistas administrativas más login, en escritorio de 1280 × 720 y pantalla estrecha de 390 × 844. Las vistas fueron dashboard, predicción, inventario, detalle de producto, ventas, ventas por mayor, devoluciones, solicitudes, movimientos, costos, precios, reportes y configuración. Se utilizaron componentes reales con respuestas de prueba, sin backend operativo. Las capturas y observaciones quedan bajo ml/demand/tmp/visual-20261114-01. Esto comprueba presentación y controles del recorrido descrito. No certifica operaciones comerciales en producción, cada modal o la aplicación Expo.

El recorrido encontró pestañas fuera de pantalla en Reportes y Configuración. Se ajustaron para distribuirse en varias filas en pantallas estrechas, manteniendo el diseño de escritorio. En Reportes, el botón Mensual por Tienda llegaba hasta el píxel 492,67 en una pantalla de 390. Después de corregirlo, queda entre los píxeles 153,75 y 344,53. Se comprobó su apertura, además de la pestaña Auditoría de Configuración. Las tablas conservan desplazamiento horizontal dentro de sus contenedores cuando corresponde.

Se comprobó que el precio de prueba por menor es Bs 150 y por mayor Bs 120. Elegir POR MAYOR desde la venta normal dejó el carrito en Bs 120 por una unidad. No se confirmó una venta. Cambiar de producto limpió el resultado predictivo anterior. El rol TIENDA fue redirigido al dashboard al intentar abrir la predicción y no mostró su enlace administrativo. El error simulado del dashboard conservó un enlace funcional hacia predicción, sin inventar cifras como reemplazo del error. Las cifras de predicción utilizadas en este recorrido son fixtures, no resultados de un experimento nuevo.

| Decisión consultada | Respuesta explícita del usuario | Consecuencia |
|---|---|---|
| Origen de la primera V2 y sus variables nuevas | Primera V2 académica y sintética | Documentar supuestos de precios, cotización y disponibilidad. No llamarlos historia real ni calibración comercial certificada |
| Alcance inicial de fuentes externas | Monash y UCI | Automotive, M5 y Favorita quedan fuera del alcance inicial. Sus RAW permanecen intactos y sus permisos siguen pendientes |
| Criterio de evaluación | MAE en VALIDATION frente al baseline, RMSE y errores por grupo, preferencia por la opción simple ante empate, TEST nuevo | No seleccionar con TEST ni exigir ahora una tolerancia comercial no acordada |

Las respuestas se registran como aprobación del usuario en el chat, sin atribuir una revisión técnica personal a Erika. La especificación conserva esa diferencia. Los supuestos numéricos y parámetros de simulación se definirán en escenarios y calibración, con trazabilidad. Los plazos de proveedor se revisarán aparte para reposición. No se ha aprobado uso de fuentes bloqueadas ni entrenamiento en esta etapa.

Con este alcance se cierran V2-01 como auditoría local de fuentes, V2-02 como auditoría local de pantallas, V2-03 para reglas académicas y V2-09A como diseño inicial. V2-04A, V2-04B y V2-04C ya tienen evidencia suficiente para continuar con V2-04D únicamente sobre Monash y UCI. V2-04 permanece en proceso porque el diccionario final necesita esa revisión de compatibilidad. V2-09B espera al modelo seleccionado. No tiene sentido exigir esos resultados posteriores para autorizar la revisión de fuentes que los precede.

La ejecución final aprobó 43 pruebas de estructura, procedencia, perfilado y contrato, además de 28 pruebas seleccionadas del frontend. La compilación frontend, que incluye comprobación de tipos, terminó correctamente. No se ejecutaron pruebas que escriban en una base de datos. La verificación de integridad conserva los 136 archivos RAW y los 44 archivos protegidos de V1/V1.1. Las correcciones de interfaz se limitaron a la distribución de pestañas de ReportsPage.tsx y SettingsPage.tsx.

El [cierre actualizado](../../ml/demand/reports/v2/preparation/visual-closed-20261114-01/review.json) conserva las verificaciones, las correcciones y las decisiones, junto con 28 capturas seleccionadas. No se ejecutó V2-04D, no se procesaron RAW ni se construyó el dataset. No se entrenó. La preparación para revisar compatibilidad está cerrada dentro del alcance aprobado. El proyecto V2 completo sigue pendiente de sus fases posteriores. No hace falta otra decisión de alcance para comenzar V2-04D. La revisión del contrato final con Erika, los parámetros de simulación y la definición del TEST nuevo corresponden a sus fases posteriores.

## 13. Compatibilidad y diccionario final de diseño V2

La revisión V2-04D utiliza los manifests y perfiles existentes. La [matriz de compatibilidad](../../ml/demand/reports/v2/compatibility/compatibility-20261114-01/source_compatibility_matrix.json) conserva hashes, snapshots, citas, doce dimensiones de comparación y reglas de uso futuro. No se descargó, limpió, convirtió o combinó ninguna fuente. Los reportes anteriores permanecen como evidencia histórica.

Monash contiene 2.674 series mensuales de repuestos, con 51 posiciones por serie entre enero de 1998 y marzo de 2002. Es la referencia más cercana al dominio. El perfil encontró 6.122 faltantes y un 74,78 % de ceros entre los valores observados. Es útil para estudiar intermitencia, no para deducir stock, precio, tienda, descontinuación o demanda perdida. Los faltantes no son ceros. Las trayectorias iguales no prueban productos duplicados. Su geografía y periodo no representan el comercio boliviano actual.

UCI contiene líneas de transacción de otro sector, con precios en GBP. Puede orientar el estudio de pedidos grandes, dispersión de precios y cancelaciones. No trae una etiqueta completa de modalidad por línea. Country no es una sucursal, Price no es precio publicado ni costo. No permite estimar cotización Bs/USD o elasticidad causal de RepuestoPro. Las dos hojas tienen 22.523 repeticiones entre hojas. Su futura preparación debe tratarlas por separado o resolver el solapamiento mediante una regla explícita. Como primera ventana de referencia mensual se propone enero a noviembre de 2011 de Year 2010-2011, sin extraerla ahora. Evita el solapamiento de diciembre 2010 y el cierre parcial de diciembre 2011. Once meses no prueban estacionalidad anual recurrente. Las repeticiones dentro de la hoja, los ajustes, precios no positivos y cancelaciones siguen requiriendo tratamiento trazable.

El diseño final se llama DATOS_SINTETICOS_DEMANDA_H4_V2, versión 2.0.0. Su unidad es producto, tienda y mes objetivo. Se define en [dataset_columns.v2.json](../../ml/demand/v2/contracts/dataset_columns.v2.json). Los nombres derivados de esta tabla son columnas del futuro dataset, no campos nuevos de Prisma. El contrato inicial de nueve columnas se conserva como referencia V1. El nuevo diccionario contiene lo siguiente.

| Columna | Función | Tipo y unidad | Regla principal |
|---|---|---|---|
| mes_objetivo | Identificador | Mes YYYY-MM | Mes completo a predecir |
| productId | Identificador | Entero | Catálogo congelado, no cantidad ni feature inicial |
| locationId | Identificador | Entero | Solo tiendas de referencia, no almacenes |
| ventas_mes_anterior | Feature | Entero, unidades | Mes anterior completo conocido al corte |
| ventas_hace_2_meses | Feature | Entero, unidades | Dos meses antes |
| ventas_hace_3_meses | Feature | Entero, unidades | Tres meses antes |
| mes_sin | Feature | Número, adimensional | sin(2 × pi × mes / 12) |
| mes_cos | Feature | Número, adimensional | cos(2 × pi × mes / 12) |
| proporcion_por_mayor_mes_anterior | Feature | Número entre 0 y 1 | Unidades explícitamente por mayor sobre ventas brutas anteriores. Null si no hubo ventas |
| cobertura_modalidad_mes_anterior | Feature | Número entre 0 y 1 | Unidades con modalidad conocida sobre total. Null si no hubo ventas |
| precio_menor_cierre_anterior_bs | Feature | Número positivo, Bs/unidad | Lista simulada vigente al cierre anterior |
| precio_mayor_cierre_anterior_bs | Feature | Número positivo, Bs/unidad | Lista simulada vigente al cierre anterior |
| variacion_precio_menor_conocida | Feature | Proporción mayor que -1 | Cambio aprobado y conocido al corte, no cambio futuro observado |
| variacion_precio_mayor_conocida | Feature | Proporción mayor que -1 | Misma regla para POR MAYOR |
| tipo_cambio_bs_usd_conocido | Feature | Número positivo, Bs/USD | Última cotización simulada disponible, con fuente explícita |
| variacion_tipo_cambio_ultimo_mes | Feature | Proporción mayor que -1 | Comparación entre cotizaciones disponibles en cortes consecutivos y de la misma fuente |
| antiguedad_tipo_cambio_dias | Feature | Entero no negativo, días | Días desde observación de la cotización hasta el corte |
| dias_sin_stock_mes_anterior | Feature | Entero no negativo, días | Días observados sin stock vendible. Con cobertura parcial es un mínimo observado |
| cobertura_stock_mes_anterior | Feature | Número entre 0 y 1 | Días con disponibilidad conocida sobre días del mes |
| categoryId | Feature categórica | Entero nullable | Etiqueta del catálogo congelado. Se codifica como categoría, no escala numérica |
| target_ventas_mes | Target | Entero no negativo, unidades | Ventas brutas observadas del mes objetivo cerrado |
| feature_cutoff_at | Control | Fecha y hora con zona | Inicio del mes objetivo en America/La_Paz. No feature |
| history_snapshot_id | Control | Texto | Identidad reproducible de la historia utilizada. No feature |
| quality_status | Control | Texto | TRAINABLE en la tabla supervisada. No feature |

Son 17 features, 3 identificadores, 1 target y 3 controles. El JSON explica para cada columna origen, disponibilidad, faltantes, derivación, restricciones y ejemplo aislado. También define 25 columnas de base_mensual.csv. La tabla escenarios_metadatos.csv tenía diez columnas al cierre de V2-04 y se amplió a catorce en V2-05, solo para auditar instancias, reloj y parámetros. La base conserva conteos por modalidad, precios conocidos, disponibilidad de cada dato, cotización y controles de costo. La tabla de escenarios conserva casos normales, adversos y ambiguos, con su respuesta esperada. No crea ejemplos de entrenamiento en esta fase.

Un aumento de Bs 120 a Bs 150 se representa como variación 0,25. Solo se usa si el plan estaba aprobado y disponible al corte. Sin plan o base conocidos se conserva null. Cero exige confirmar que no hay cambio. Tampoco se reemplaza una cotización faltante por 6.96. Un mes sin registros no se completa como venta cero. Los tres lags completos son obligatorios para una fila entrenable. Las features opcionales pueden conservar null, con imputación e indicadores preparados solo con TRAIN. Si un grupo carece de información en TRAIN, se rechaza esa variante o se usa un conjunto menor identificado, sin cambiar columnas en silencio.

Los datos de modalidad se conservan como conocidos o desconocidos. Una compra grande no basta para llamarla mayorista. La proporción mayorista conocida debe ser menor o igual a la cobertura de modalidad. Los días sin stock no se calculan desde ventas cero. Si no se observó disponibilidad ningún día, dias_sin_stock es null y cobertura_stock vale cero. Las categorías nuevas tienen tratamiento UNKNOWN ajustado con TRAIN. No se infiere una categoría.

Se compararán conjuntos de 5, 7, 11, 14, 16 y 17 features, agregando modalidad, precios, moneda, disponibilidad y categoría por etapas. Todas las variantes utilizarán las mismas filas de evaluación y reportarán cobertura. No se agrega promedio_3_meses porque se deriva de los lags. Los IDs de producto y tienda quedan para agrupar y evaluar errores, sin entrar como números al modelo inicial. Costo sirve para verificar coherencia económica. Marca, modelo y año no están incluidos en el catálogo congelado utilizado y no se inventan. Plazo de proveedor y reposición son otra decisión.

Se mantiene el diseño temporal de 24 meses, octubre de 2024 a septiembre de 2026, con seed raíz 42. Octubre a diciembre de 2024 preparan historia. TRAIN tiene enero de 2025 a marzo de 2026, VALIDATION abril a junio de 2026 y TEST julio a septiembre de 2026. Se respetan meses completos, aproximadamente 71,43 %, 14,29 % y 14,29 %. V2 debe usar una ejecución nueva con streams aleatorios separados por versión y partición, sin copiar los targets o streams de V1. El hash del TEST nuevo sigue null porque ese archivo todavía no existe. Antes de seleccionar modelos deberá quedar reservado y no inspeccionado para ajustes. Reutilizar fechas no equivale a reutilizar el mismo TEST.

La simulación no certificará ventas reales de la empresa. Monash y UCI no se unirán entre sí ni con Product.id. Sus futuros patrones aprobados pueden orientar supuestos, con atribución y versiones. Una cotización compartida por mes no crea observaciones económicas independientes por cada producto. El modelo seguirá estimando ventas observadas bajo los supuestos simulados, no demanda perdida ni causalidad comercial.

Se cierran V2-04D y V2-04 como revisión de compatibilidad y diccionario de diseño. **Todavía no existe el dataset V2.** No se creó ningún build, CSV, archivo curated o modelo. El siguiente punto es V2-05, diseño de escenarios y supuestos numéricos. Después se atenderán calibración, construcción y validación cuando se autoricen. El diccionario aprobado no autoriza entrenamiento ni acredita calidad de un dataset todavía inexistente.

La revisión terminó con 58 pruebas de estructura, procedencia, perfilado y contratos aprobadas, sin fallos ni omisiones. Las pruebas nuevas comprueban el diccionario, la disponibilidad previa de las features, la separación del target, la codificación categórica, las unidades de precio y moneda, además de la prohibición de mapear filas externas. El [cierre de integridad](../../ml/demand/reports/v2/compatibility/compatibility-20261114-01/closure.json) registra hashes y confirma que data/repuestopro_v2, external_curated y models/v2 siguen sin archivos publicados.

## 14. Escenarios y supuestos de V2-05

Antes de iniciar esta etapa se comprobaron los nueve requisitos previos del alcance académico. El diccionario y la matriz coincidieron con los hashes del cierre anterior. Se verificó que V2 todavía no tiene archivos de datos, modelos o curated. Esto cierra requisitos de diseño, no todas las fases del proyecto.

El registro estructurado está en [preparation.v2.json](../../ml/demand/v2/contracts/preparation.v2.json), apartado scenario_design. Se definieron 57 escenarios y ocho combinaciones obligatorias. Cada caso tiene supuestos, grupos de variables, momento de conocimiento, tratamiento, elegibilidad y evidencia futura. Una lista finita no puede cubrir toda situación posible de una tienda real. Este catálogo cubre las familias acordadas y debe ampliarse si aparecen casos nuevos.

Conservar significa mantener un caso válido sujeto a las comprobaciones del futuro build. Null opcionales permite conservar desconocidos solo en variables opcionales, con una ruta del modelo que los admita. Revisión excluye el ejemplo entrenable hasta resolver la causa. Rechazo identifica una entrada inválida que solo puede usarse como prueba negativa del validador. Un escenario adverso no es automáticamente un dato inválido. Los picos legítimos y los errores grandes no se eliminan para mejorar métricas.

Los casos de contexto se registran para auditoría o reposición. No agregan variables al modelo ni descartan automáticamente las ventas válidas asociadas. La falta de historia obligatoria sí bloquea una fila predictiva, aunque otras variables puedan tratarse como opcionales.

**Casos normales.**

| ID | Escenario | Supuesto principal | Tratamiento |
|---|---|---|---|
| N01 | Venta por menor estable | Mes completo, precio conocido, unidades enteras y stock suficiente. La venta observada puede variar por ruido. | Conservar |
| N02 | Pedidos por mayor recurrentes | Modalidad explícita POR_MAYOR. Frecuencia y tamaño varían, con stock suficiente y precio mayor no superior al menor. | Conservar |
| N03 | Mezcla de modalidades conocida | Cada unidad se asigna a menor, mayor o desconocida. Los tres conteos suman ventas brutas. | Conservar |
| N04 | Baja rotación con ceros válidos | Existen meses completos observados con cero ventas y meses con pequeñas cantidades. Cero no implica dato faltante. | Conservar |
| N05 | Rotación media y alta | Cada producto tiene un nivel simulado propio. El grupo generativo oculto no entra al modelo. | Conservar |
| N06 | Tendencia moderada | El nivel puede crecer, mantenerse o disminuir de forma moderada. No se fija una pendiente universal. | Conservar |
| N07 | Estacionalidad heterogénea | El calendario es conocido. La intensidad y el mes de mayor actividad pueden diferir entre productos. | Conservar |
| N08 | Diferencias entre tiendas | Las tiendas de referencia tienen niveles distintos. El ID no determina por sí mismo cuál vende más. | Conservar |
| N09 | Aumento de precio conocido | Un plan aprobado antes del corte eleva el precio de inicio. Bs 120 a Bs 150 es variación 0.25. | Conservar |
| N10 | Descuento conocido con margen válido | La reducción respeta costo y orden menor/mayor. El plan estaba disponible al corte. | Conservar |
| N11 | Cotización estable y conocida | Una cotización ficticia con fuente y fechas es común a todos los productos y tiendas del mismo corte. | Conservar |
| N12 | Disponibilidad completa y recepción oportuna | Las entradas simuladas habilitan stock solo cuando son recibidas. La disponibilidad se observa de manera independiente de las ventas. | Conservar |

**Casos adversos.**

| ID | Escenario | Supuesto principal | Tratamiento |
|---|---|---|---|
| A01 | Cambio de precio no anunciado | El precio cambia dentro del mes objetivo y nadie podía conocerlo al corte. | Conservar |
| A02 | Subida fuerte del dólar antes del corte | La subida es conocida. Su transmisión al costo y al precio puede ser parcial o demorada. | Conservar |
| A03 | Caída de cotización sin baja inmediata del precio | La cotización cae, pero la empresa puede mantener precios por costos anteriores o decisión comercial simulada. | Conservar |
| A04 | Precios económicamente incoherentes | Mayor supera menor o un precio queda debajo del costo sin excepción explícita y auditada. | Rechazo |
| A05 | Precio o cotización inválidos | Precio o cotización no positivos, NaN, infinito o unidad conocida incorrecta. | Rechazo |
| A06 | Falta parcial de stock observada | Se conocen días sin stock. La venta observada está limitada por unidades vendibles, no por demanda latente. | Conservar |
| A07 | Sin stock todo el mes objetivo | El mes está completamente observado. No hubo unidades vendibles aunque pudo existir demanda. | Conservar |
| A08 | Recepción tardía o parcial | Solo lo recibido habilita venta. Cantidad enviada, pendiente y recibida no se cuentan dos veces. | Conservar |
| A09 | Plazo de proveedor mayor al horizonte | Un plazo hipotético puede superar un mes. No existe historia propia certificada para ajustarlo. | Contexto, revisión |
| A10 | Pedido mayorista excepcional | Pedido legítimo varias veces mayor al tamaño habitual simulado, limitado por stock disponible. No se asume repetición mensual. | Conservar |
| A11 | Cambio brusco de tendencia | El régimen cambia y no está completamente explicado por los tres lags. No se revela el parámetro generativo. | Conservar |
| A12 | Interrupción operativa no anunciada | La tienda deja de vender durante parte del objetivo, pero sus registros y el cierre del mes siguen completos. | Conservar |
| A13 | Clave mensual duplicada | Dos filas comparten producto, tienda y mes objetivo. | Rechazo |
| A14 | Cantidad o target inválidos | Ventas brutas negativas, fraccionarias, no finitas o imposibles según unidades vendibles. | Rechazo |
| A15 | Entidad fuera del catálogo permitido | Producto o ubicación inexistentes en la referencia, o ALMACEN usado como tienda. | Rechazo |
| A16 | Información posterior usada como entrada | Se introduce target, cotización futura, precio no conocido, stock posterior, escenario o parámetros internos como features. | Rechazo |
| A17 | Mezcla de ventas reales y externas con simulación | Filas externas se renombran con IDs propios o se mezclan sin separar origen y autorización. | Rechazo |
| A18 | Fecha inválida o mes mal asignado | Fecha imposible, zona ausente o mes calculado en UTC en lugar del calendario local establecido para simulación. | Rechazo |
| A19 | Precio, dólar y stock cambian juntos | Los factores interactúan con distintos retrasos. Solo sus valores conocidos antes del corte entran al modelo. | Conservar |
| A20 | Contaminación de TRAIN y TEST | Se separan filas del mismo mes, se reutiliza TEST de V1, se ajusta un scaler con todo o se elige con TEST. | Rechazo |
| A21 | Devolución posterior y venta a crédito | La devolución reduce primero deuda y solo reintegra excedente cobrado. Stock vendible exige inspección. Ventas brutas no son cobros ni ventas netas. | Contexto, conservar |
| A22 | Anulación posterior al cierre | Una venta puede anularse después del corte con el que se congeló una etiqueta o una entrada. | Revisión |
| A23 | Promoción sin reducción del precio | Una campaña puede aumentar exposición sin modificar el precio. El diccionario inicial no incluye una feature de marketing. | Conservar |
| A24 | Anulación conocida antes del cierre | La anulación ocurre y se conoce antes del snapshot que cierra el mes objetivo. | Conservar |
| A25 | Salida predictiva inválida sin política | Una predicción futura es no finita o negativa y no existe una política de posprocesamiento previamente definida y evaluada. | Contexto, rechazo |

**Casos ambiguos.**

| ID | Escenario | Supuesto principal | Tratamiento |
|---|---|---|---|
| G01 | Producto nuevo sin tres meses completos | El producto existe en la referencia pero empieza a operar dentro del mundo simulado. No hay ventas antes de su alta. | Revisión |
| G02 | Tienda nueva sin historial suficiente | Una tienda de referencia se activa tarde en la simulación. Sus meses anteriores no son observaciones con cero. | Revisión |
| G03 | Mes histórico faltante | Falta un mes de cualquiera de los tres lags, aunque existan otros registros. | Revisión |
| G04 | Mes todavía abierto | No existe target definitivo del mes objetivo abierto. Una consulta futura de inferencia no necesita target. | Revisión |
| G05 | Modalidad parcial o desconocida | Parte o todas las unidades no tienen modalidad certificada. NORMAL no equivale a minorista y precio no resuelve el modo. | Null opcionales |
| G06 | Cero ventas con disponibilidad desconocida | El mes de ventas está observado, pero no toda la historia de stock. Cero puede ocultar demanda no atendida. | Null opcionales |
| G07 | Cotización conocida pero antigua | Existe una cotización anterior con fuente y fecha válidas, sin garantía de vigencia actual. | Null opcionales |
| G08 | Cotización faltante o no comparable | Falta la observación, su fuente, unidad o comparabilidad con el corte anterior. Cotización de compra no equivale a mercado. | Null opcionales |
| G09 | Plan de precio publicado después del corte | El cambio puede haber sido aprobado, pero no era conocido en el corte utilizado. | Null opcionales |
| G10 | Precio actual sin historia de lista | Solo existe Product actual o precio vendido. No demuestra lista vigente de meses anteriores ni precio sin ventas. | Null opcionales |
| G11 | Categoría faltante o nueva | La categoría no está informada o no apareció en TRAIN. El entero es una etiqueta, no una cantidad. | Null opcionales |
| G12 | Detalle repetido de procedencia dudosa | Dos líneas históricas iguales pueden ser repetición técnica u operaciones legítimas. No existe identidad suficiente para decidir. | Revisión |
| G13 | Fecha sin zona o conocimiento incierto | No se sabe a qué zona pertenece una fecha o cuándo estuvo disponible. Las fechas UCI no traen zona certificada. | Revisión |
| G14 | Precios menor y mayor iguales | Igualdad de precios es comercialmente posible. El importe por sí solo no identifica modalidad. | Null opcionales |
| G15 | Precio sube y ventas también | Tendencia, ruido, preferencia o pedidos pueden compensar el efecto supuesto del precio. | Conservar |
| G16 | Fuente disponible pero no autorizada o incompatible | Descargar un archivo no aprueba su uso. Automotive, M5 y Favorita no forman parte del alcance inicial. | Contexto, revisión |
| G17 | Fecha prevista confundida con llegada real | ProductRequest.expectedDate es una previsión y Movement.receivedAt describe traslado interno, no importación de proveedor. | Contexto, revisión |
| G18 | Catálogo congelado aplicado a años simulados | La referencia fue observada en 2026. Su uso en 2024–2026 es una suposición del mundo sintético, no historia real certificada. | Null opcionales |
| G19 | Producto descontinuado sin estado certificado | El catálogo congelado no contiene una marca de descontinuación. No se deduce una baja a partir de ceros o faltantes. | Contexto, revisión |
| G20 | Cierre de tienda planificado sin variable propia | Se conoce un cierre o interrupción planificada, pero no existe una feature de calendario operativo en las 17 entradas aprobadas. | Contexto, revisión |

**Combinaciones obligatorias.**

Las pruebas futuras combinarán los siguientes casos. Un error de integridad o una fuga domina la combinación afectada. La ausencia de lags domina sobre la posibilidad de imputar features opcionales. En contexto operativo, revisar una recepción o una devolución no significa descartar toda venta mensual válida.

| ID | Casos | Regla esperada | Tratamiento |
|---|---|---|---|
| C01 | N09, A02, A06 | Precio, cotización y disponibilidad pueden interactuar. No sumar efectos fijos ni usar información no conocida. | Conservar |
| C02 | N04, A10, A08 | Pedido grande en producto intermitente con recepción parcial. Conservar pico legítimo, sin sobreventa o repetición mensual forzada. | Conservar |
| C03 | G01, G11, G03 | La falta de lags obligatorios domina aunque una categoría admita UNKNOWN. No entrenar ni inventar historia. | Revisión |
| C04 | G07, G10, G06 | Solo si los tres lags son válidos. Features opcionales desconocidas no se convierten en cero y la ruta del modelo debe admitirlas. | Null opcionales |
| C05 | G09, A16, A18 | Un valor futuro inyectado como conocido o un mes mal fechado bloquean el caso, incluso si otros valores son válidos. | Rechazo |
| C06 | A21, A08, G17 | Contexto operativo de pagos, inspección y recepción. No crear variables nuevas ni contaminar ventas brutas con caja o stock pendiente. | Contexto, revisión |
| C07 | A13, A17 | Duplicados de clave y mezcla de procedencia impiden publicar un build válido. | Rechazo |
| C08 | N06, N07, G15 | Conservar respuestas distintas al mismo cambio de precio. Ninguna dirección de ventas es obligatoria por sí sola. | Conservar |

**Supuestos numéricos y sus límites.**

Los niveles siguientes son propuestas hipotéticas para diseñar pruebas. No son estadísticas calculadas de Monash o UCI, tasas actuales de Bolivia ni calibración de ventas reales. Las frecuencias de aparición, proporciones de rotación, coeficientes y pesos del generador siguen sin fijarse. V2-05A deberá calibrarlos o justificarlos, con fuentes y versiones. No se elegirá ningún valor mirando TEST.

| Parámetro | Unidad | Niveles de diseño | Significado |
|---|---|---|---|
| noise | mecanismo | CONTEOS, SOBREDISPERSION, INTERMITENCIA | Familias de ruido propuestas. Intensidades y pesos se definirán en V2-05A, sin escogerlos por TEST. |
| trend_annual | variacion_anual | -0.1, 0, 0.2 | Niveles hipotéticos de diseño para tendencia moderada. No son tasas observadas de la empresa. |
| seasonality | multiplicador | 0.8, 1, 1.2 | Intensidades ilustrativas. La forma y fase varían por producto, sin crear una festividad real no verificada. |
| store_level | multiplicador | 0.75, 1, 1.25 | Heterogeneidad ilustrativa. No se asigna por orden numérico de Location.id. |
| price_change | proporcion | -0.1, 0, 0.1, 0.25, 0.5 | Reducciones y aumentos hipotéticos. Solo casos válidos respetan costo y relación mayor <= menor. |
| fx_change | proporcion | -0.15, 0, 0.15, 0.3 | Cambios ficticios, no una serie real Bs/USD ni pronóstico monetario. |
| fx_age | dias | 0, 2, 7, 30 | Antigüedad para pruebas. No constituye umbral comercial de vigencia. |
| pass_through | proporcion | 0, 0.5, 1 | Transmisión hipotética del cambio de costo al precio. No elasticidad causal estimada. |
| pass_through_delay | meses | 0, 1, 2 | Retrasos hipotéticos. Una decisión futura de precio no se vuelve conocida antes de su publicación. |
| bulk_size | multiplicador_pedido_habitual | 2, 4, 8 | Tamaño de pedido hipotético, no múltiplo obligatorio del target mensual. Ventas atendidas no superan unidades vendibles. |
| stockout | dias | 0, 1, 7, MES_COMPLETO | MES_COMPLETO se resuelve con calendario. Un conteo observado mayor que días del mes es inválido, no se recorta para repararlo. |
| stock_coverage | cobertura | NINGUNA, PARCIAL, COMPLETA | Días observados enteros entre cero y días reales del mes. No se deriva de la cantidad vendida. |
| receipt_fraction | proporcion | 0.25, 0.5, 1 | Recepción parcial ilustrativa. Registrar unidades enteras y conservar total recibido más pendiente. |
| supplier_lead_days | dias | 0, 7, 30, 60 | Contexto hipotético para reposición. No calibrado ni feature inicial. |
| regime_change | multiplicador | 0.5, 0.75, 1.25, 1.5 | Cambios estructurales de prueba. El efecto observado depende también de disponibilidad y ruido. |
| entity_age | meses_completos | 0, 1, 2, 3 | Menos de tres meses completos no habilita el modelo de tres lags. |
| modality_coverage | proporcion_objetivo | 0, 0.5, 1 | Objetivo ilustrativo de conocimiento. Los conteos son enteros y la proporción publicada se calcula a partir de ellos, sin fabricar medias unidades. |
| boundary_clock | posicion_relativa_al_corte | ANTES, EN_EL_CORTE, DESPUES | Corte mensual en America/La_Paz con fecha disponible explícita. Usar fechas válidas y considerar bisiestos y año nuevo. |

No se impondrá una regla universal de precio arriba y ventas abajo. Se consideran respuestas nulas, compensación por tendencia, ruido e interacción. El traslado de costo a precio puede ser parcial y demorado. Una cotización conocida al corte no autoriza utilizar la cotización futura del mes objetivo. Los parámetros internos, el grupo generativo y la demanda latente permanecerán fuera de las features.

El ruido deberá producir conteos no negativos, con mecanismos distintos de intermitencia o dispersión. No se programará el target como una copia exacta de una sola fórmula fácil de aprender. Las ventas atendidas respetarán unidades vendibles. Demanda latente y pedidos no atendidos solo podrán aparecer como metadata, sin sustituir el target de ventas observadas.

El reloj distingue event_at, momento del hecho, de available_at, momento en que podía conocerse. El corte es el inicio del mes objetivo en America/La_Paz. Información posterior no se incorpora a entradas previas. Se probarán 23:59, 00:00, fin de mes, año nuevo, febrero bisiesto y cambio entre UTC y UTC-4. Una etiqueta se congela con el primer cierre completo del objetivo y los estados conocidos en ese snapshot. Una anulación posterior exige revisión versionada, sin reescribir los snapshots de entradas usados antes.

La cobertura deberá registrar el universo activo de consultas, los casos con historia suficiente, las predicciones y las abstenciones. Se compararán variantes sobre las mismas filas. Los casos sin ruta predictiva no desaparecerán del reporte. El TEST nuevo mantendrá mecanismos o combinaciones reservados y no servirá para elegir parámetros o modelos.

Para auditar cada ejecución futura se añadieron cuatro campos a escenarios_metadatos.csv: scenario_instance_id, event_at, available_at y parameters_json. scenario_id sigue identificando la definición. La instancia tiene identidad única dentro del build, tiempos separados y parámetros JSON estrictos. Los shocks compartidos pueden enlazarse mediante un event_group_id en sus parámetros. Son controles o metadata, nunca features. El resto del diccionario conserva las 24 columnas supervisadas y las 17 features. No se crearon filas de estas tablas.

Las pruebas de esta etapa verifican metadata, referencias, clases, tratamientos, trazabilidad y separación de información futura. No prueban un simulador que todavía no está implementado. Su ejecución se comprobará en V2-06 y V2-07. El [cierre de V2-05](../../ml/demand/reports/v2/scenarios/scenarios-20261114-01/closure.json) registra los resultados y la integridad.

Se añadieron explícitamente promociones sin cambio de precio, anulaciones conocidas antes del cierre, salidas predictivas inválidas como contexto futuro, productos descontinuados sin estado certificado y cierres de tienda planificados sin una feature propia. No se promete que el modelo inicial anticipe información que no recibe. Los riesgos de sobreajuste, aprendizaje de la fórmula sintética y buen promedio con mal desempeño por grupo quedan como comprobaciones obligatorias de la evaluación posterior.

V2-05 queda completo como diseño. V2-05A sigue pendiente. No se procesaron fuentes externas, no se ejecutó calibración, no se generó dataset ni se entrenó. El siguiente paso es calibrar o justificar los supuestos antes de construir observaciones.

La ejecución final aprobó 73 pruebas de contratos y metadata, sin fallos ni omisiones. No son pruebas de ejecución de un generador o un modelo V2. La ampliación auxiliar de escenarios pasó la validación del diccionario y no cambió las 24 columnas supervisadas. Los reportes históricos y las fuentes originales se conservaron.

## 15. Justificación de parámetros V2-05A

Revisión del 14 de noviembre de 2026. Se autoriza justificar el diseño, no generar ventas. Se verificaron los cierres de compatibilidad y escenarios. Las referencias siguen siendo Monash y UCI. Las otras tres fuentes permanecen fuera del alcance inicial. No se necesitó Internet ni otra lectura de RAW para esta etapa. Se utilizaron sus perfiles congelados, con hashes vinculados a los manifests existentes.

La [configuración vigente](../../ml/demand/v2/contracts/calibration.v2.json) reúne parámetros, fórmulas, procedencia y límites. La utilidad v2/calibration.py permite recalcular las estadísticas desde esos perfiles. No es un generador de ventas, no usa números aleatorios ni escribe archivos. El [reporte de cierre](../../ml/demand/reports/v2/calibration/calibration-20261114-01/closure.json) registra pruebas e integridad. El anexo 14 conserva los niveles propuestos antes de esta justificación. Si indica que V2-05A estaba pendiente, corresponde al estado de esa revisión anterior.

### Evidencia que sí podemos utilizar

Monash contiene 130.252 valores observados, con 97.398 ceros. La fracción de cero es 74,78%. Los 6.122 faltantes no entran en ese denominador. La media del tamaño positivo es aproximadamente 2,015 unidades. Se obtiene dividiendo la suma de unidades por los 32.854 meses positivos, sin convertir un faltante en cero.

Para definir grupos se toman las 2.509 series completas de 51 meses. Se excluyen de este cálculo las 165 incompletas, sin borrarlas ni convertir sus meses finales en ceros. Se clasifica frecuencia baja hasta un tercio de meses positivos, media hasta dos tercios, alta por encima. Esta clasificación no mide valor comercial ni coincide necesariamente con la rotación de RepuestoPro.

| Frecuencia de meses positivos | Series | Peso de referencia | Probabilidad mensual positiva del grupo |
| --- | ---: | ---: | ---: |
| BAJA | 1792 | 71.42% | 15.75% |
| MEDIA | 690 | 27.50% | 47.54% |
| ALTA | 27 | 1.08% | 71.17% |

Los pesos suman uno. Su combinación reproduce la frecuencia positiva de las series completas, aproximadamente 25,09%. La cifra global de positivos es 25,22% porque incluye meses observados de series incompletas. No se mezclan esos denominadores como si fueran la misma población. Los grupos orientarán asignaciones sintéticas con seed 42, sin vincular una serie externa con Product.id. No se eliminaron trayectorias iguales por mera similitud.

Se propone un mecanismo en dos pasos. Primero se decide si existe una venta positiva. Después se obtiene un tamaño entero mayor o igual a uno. La media positiva se apoya en Monash. Una distribución geométrica positiva será el mecanismo inicial, con una Poisson truncada en cero como alternativa. Las formas de distribución e independencia temporal son hipótesis, no resultados estadísticos probados. Las rachas máximas de cero tienen mediana 16 meses, percentil 90 de 28 y percentil 95 de 31 en las series completas. Se conservarán como referencias descriptivas. No son límites obligatorios para una simulación de 24 meses.

UCI tiene 1.067.371 líneas. Entre las cantidades positivas, mediana 3, percentil 95 de 30 y percentil 99 de 108. Las razones respecto a la mediana son 10 y 36. Esto respalda revisar pedidos con cola larga, pero no autoriza etiquetarlos como mayoristas ni trasladar esas cantidades a autopartes. Hay 34.335 repeticiones exactas después de la primera aparición, incluidas 22.523 ocurrencias entre hojas. Las 22.950 líneas con cantidad negativa tampoco constituyen una tasa limpia de devoluciones. Se conserva la advertencia sobre esos registros sin procesarlos ni limpiarlos.

Los perfiles y la configuración conservan las citas, enlaces de procedencia y licencia CC BY 4.0 comprobada en V2-04B. Monash corresponde a repuestos de otra empresa y época. UCI corresponde a comercio británico en GBP. No se trasladarán productos, precios nominales, geografía ni identificadores a la historia de RepuestoPro.

### Parámetros y límites de aplicación

| Parámetro | Decisión vigente | Justificación |
| --- | --- | --- |
| noise | Intermitencia por grupo y media positiva 2,015. Geométrica como mecanismo inicial, Poisson truncada como alternativa | Frecuencia y media provienen de Monash. Distribución y dependencia son supuestos |
| trend_annual | −10%, 0%, +20% al año | Sensibilidad a caída, estabilidad y crecimiento moderado. No tendencia estimada para Bolivia |
| seasonality | Multiplicadores entre 0,8 y 1,2 | Amplitud máxima 20% y fase por serie supuestas. No trasladar fiestas extranjeras |
| store_level | 0,75, 1 y 1,25 | Diferencias moderadas supuestas. No asignar por orden de Location.id |
| price_change | −10%, 0%, +10%, +25%, +50% | Pruebas de sensibilidad. 120 a 150 Bs equivale a +25%, no a un cambio observado |
| fx_change | −15%, 0%, +15%, +30% | Trayectorias ficticias compartidas por ejecución, sin afirmar cotización vigente |
| fx_age | 0, 2, 7, 30 días | Casos de información reciente o antigua. No umbral comercial aprobado |
| pass_through | 0%, 50%, 100% | Transmisión hipotética del costo al precio. No elasticidad estimada |
| pass_through_delay | 0, 1, 2 meses | Respuesta inmediata o retrasada. Mantener fecha de conocimiento |
| bulk_size | 2, 4, 8 veces un pedido habitual simulado | Estrés moderado motivado por colas de UCI. No multiplicar todo el target mensual |
| stockout | 0, 1, 7 días o mes completo | Casos operativos supuestos, ajustados al calendario real |
| stock_coverage | Ninguna, parcial, completa | Medición independiente de ventas. Una venta cero no prueba falta de stock |
| receipt_fraction | 25%, 50%, 100% | Recepciones parciales, conservando unidades enteras recibidas y pendientes |
| supplier_lead_days | 0, 7, 30, 60 días | Contexto de reposición separado. No feature inicial ni plazo real certificado |
| regime_change | 0,5, 0,75, 1,25, 1,5 | Cambios estructurales de prueba, sin frecuencia comercial atribuida |
| entity_age | 0, 1, 2, 3 meses completos | Regla del modelo: se requieren tres lags completos |
| modality_coverage | 0%, 50%, 100% | Proporciones de conocimiento que se calculan desde conteos enteros |
| boundary_clock | Antes, en el corte, después | Regla de disponibilidad en America/La_Paz, con fechas válidas |

Las elasticidades de sensibilidad serán 0, −0,5 y −1. Son hipótesis para representar ausencia de efecto o una reducción del tamaño positivo al aumentar el precio. No indican causalidad comprobada. El comportamiento observado también depende de calendario, disponibilidad, ruido y modalidad, por lo que un precio más alto no obliga a observar menos ventas en cada caso.

Para evitar una especificación incompleta se fijan anclas ficticias de precio menor 120 Bs, mayor 108 Bs y costo 80 Bs. La cotización inicial ficticia será 10 Bs/USD. Son constantes de demostración, no precios actuales ni cotizaciones oficiales o paralelas. La hipótesis primaria trata el costo como totalmente importado. Los escenarios deben identificar estas anclas en sus parámetros de auditoría, sin presentarlas como historia de Product.

El costo variará con la razón de cotizaciones. El precio responderá una sola vez a ese cambio mediante transmisión y retraso. La relación entre precio y ventas utilizará el precio vigente por modalidad, sin sumar un segundo efecto directo del dólar sobre ventas. Toda combinación válida debe conservar costo <= precio mayor <= precio menor. Una combinación que lo incumpla se rechaza como fixture inválido o requiere una decisión de precio explícita y fechada, nunca una reparación silenciosa.

La proporción mayorista se estudiará con niveles ficticios 0%, 25%, 75% y 100%, conservando unidades enteras. El modo se asignará de forma explícita. El tamaño de un pedido o la igualdad de precios no permiten inferirlo. Los multiplicadores de escala 1, 3 y 10 permitirán comparar sensibilidad de magnitud, en variantes separadas. No representan volumen real ni ponderaciones aprendidas.

### Aplicación posterior y pendientes

Los 57 escenarios y ocho combinaciones constituyen una suite de cobertura forzada, no una distribución comercial. Cada caso debe ejecutarse al menos una vez cuando exista el generador. No se asignan frecuencias inventadas a errores, devoluciones o quiebres de stock. Los registros inválidos, ambiguos sin resolver y contextos operativos no se mezclan automáticamente con entrenamiento. Una mezcla de estrés se publicará como variante separada con su manifiesto.

La configuración especifica fórmulas, seed 42 y flujos aleatorios independientes derivados con SHA-256. No se utilizará hash() de Python para semillas. Las ventas atendidas se limitarán por stock vendible y recepciones efectivas. Los pedidos latentes solo sirven como control de simulación. No serán target ni feature. Las devoluciones habilitarán venta después de inspección. Se mantendrán separados evento, conocimiento, cierre del mes y snapshot de historia.

V2-05A queda cerrado como justificación académica de los 18 parámetros. Esto no significa que exista un simulador V2 ejecutado ni una calibración comercial validada. No se midió elasticidad real, cotización boliviana, plazo del proveedor ni demanda perdida. Los límites de adquisición manual señalados en procedencia permanecen documentados y no se convierten en certificación de descarga oficial.

El siguiente punto es V2-06, pendiente de autorización. Después corresponderá validar filas y simulación en V2-07. Se revisarán distribución, ceros, cola, errores por grupo, sensibilidad y conservación de unidades. Las estadísticas externas serán referencias, no objetivos que deban copiarse exactamente. No se escogerán parámetros para favorecer un modelo o mirando TEST. V2-08 deberá congelar una ejecución independiente no inspeccionada antes de seleccionar modelos. El TEST ya observado en V1 no será una nueva prueba de V2. La revisión del contrato real con Erika permanece en V2-09B.

No se construyó dataset, no se creó curated, no se entrenó ni se modificó Neon. RAW, V1/V1.1, modelos y reportes anteriores permanecen protegidos. Las pruebas de esta etapa comprueban derivación, contratos e integridad, no ejecución predictiva.

La verificación de V2-05A aprobó 86 pruebas, sin fallos ni omisiones. Incluye 13 pruebas nuevas de derivación, conservación de probabilidades, trazabilidad, límites y ausencia de supuestos comerciales presentados como estimaciones. La integridad se contrastó antes y después sobre los 136 RAW, 44 archivos protegidos, 44 reportes previos, dos modelos y cinco manifests. No se creó ningún archivo Markdown nuevo.

## 16. Primer build académico V2-06

Ejecución del 14 de noviembre de 2026, posterior a V2-05A. Esta sección actualiza el estado vigente. Las afirmaciones anteriores sobre un dataset todavía inexistente corresponden a revisiones previas y no se alteran como evidencia histórica.

Se publicó [academic-20261114-03](../../ml/demand/data/repuestopro_v2/2.0.0/academic-20261114-03/manifest.json), versión 2.0.0. Su origen es SYNTHETIC. Utiliza los 56 productos incluidos en el catálogo congelado y las tiendas 5, 6 y 7. Los productos reservados 57 a 62 permanecen fuera. No hubo otra consulta de catálogo, ninguna lectura de Neon ni cambio de identificadores externos. Las referencias Monash y UCI orientan parámetros, no aportan filas de ventas al build.

El generador está en ml/demand/v2/generate.py. La ejecución desde la raíz es:

```powershell
.\ml\demand\.venv\Scripts\python.exe -B ml/demand/v2/generate.py --build-id IDENTIFICADOR_NUEVO
```

El identificador debe ser nuevo. El comando rechaza sobrescrituras. Primero construye en tmp, aplica una puerta mínima de validación y reserva una ruta exclusiva. El manifest se copia al final para distinguir una publicación completa de una interrupción. No importar este módulo ejecuta una generación. No hay conexión a bases de datos ni entrenamiento en el generador.

El panel completo cubre octubre de 2024 a septiembre de 2026. Hay 4.032 filas en base_mensual.csv. Las 3.528 filas de dataset_supervisado.csv comienzan en enero de 2025, después de tres meses de historia. Conservan las 24 columnas acordadas, incluidas 17 features. Las variables opcionales desconocidas se escriben vacías en CSV, equivalentes a null, sin reemplazarlas por ceros.

| Conjunto | Meses objetivo | Filas |
| --- | --- | ---: |
| TRAIN | Enero 2025 a marzo 2026 | 2.520 |
| VALIDATION | Abril a junio 2026 | 504 |
| TEST | Julio a septiembre 2026 | 504 |

Todas las filas del mismo mes permanecen juntas. No se hizo split aleatorio. TEST tiene flujo de conteos y disponibilidad separado por versión y partición, con hash de contenido en split_manifest.json. Se generó y verificó su integridad. No se utilizó para elegir modelos o ajustar parámetros, no se publicaron sus métricas ni se presentó como un archivo que nunca fue accedido. La evaluación seguirá siendo mensual de un paso, con historia disponible al corte. Los lags de agosto pueden incluir julio ya cerrado, sin reentrenar con TEST.

La variante inicial implementa conteos intermitentes con tamaño positivo geométrico, grupos de frecuencia de Monash, tendencia moderada, estacionalidad, efecto tienda, sensibilidad al precio, modalidad explícita, cotización ficticia común, precios conocidos o no anunciados y disponibilidad observada completa o parcial. La asignación de políticas utiliza claves aleatorias reproducibles, sin tratar Product.id o Location.id como cantidades. Los streams de modalidad, conteos y stock están separados.

El precio y el costo parten de las anclas ficticias acordadas. Los cambios son escenarios, no historial real ni cotización vigente. La configuración aplicada concreta transmisión de costo 50%, retraso de un mes y una trayectoria ficticia de cotización que repite factores 1, 1, 1,15, 1,15, 1, 1, 0,85, 0,85. El manifest registra las decisiones específicas de esta variante. No se afirman relaciones económicas estimadas.

El ledger adicional conserva stock inicial, recibido, vendido, final, tránsito inicial, enviado y tránsito final. Solo las recepciones efectivas habilitan venta. Las unidades solicitadas que no se atienden permanecen como control de simulación, fuera de las features y del target. El conteo diario de disponibilidad se observa después de recepciones y antes del pedido del día. Es una convención de esta simulación diaria, no una medición intradía real. No se simularon devoluciones en este primer build y no se afirma haber validado su inspección mediante estas filas.

Los snapshots de la base identifican el contenido mensual. Cada fila supervisada identifica la combinación de sus tres snapshots históricos. Los planes conocidos se utilizan únicamente cuando estaban disponibles al corte. Los cambios no anunciados afectan el resultado simulado, pero no se incorporan como información futura en la predicción.

La publicación contiene los ocho archivos obligatorios: base_mensual.csv, dataset_supervisado.csv, escenarios_metadatos.csv, manifest.json, schema.json, split_manifest.json, validation.json y checksums.sha256. Añade simulation_ledger.csv, generator_config.json y catalog_reference.json para conservar contabilidad y reproducción. El schema del build refleja que existe una publicación pendiente de V2-07. El contrato fuente conserva su función de plantilla de diseño. No se modificaron las columnas ni se autorizó entrenamiento.

La tabla de auditoría tiene 4.413 instancias. Los IDs observados en esta variante son: A06, A07, A08, A10, G05, G06, G18, N01, N02, N04. Son marcas de eventos o propiedades simuladas. No equivalen a pruebas de aceptación de todos los escenarios del registro. El manifest lista también los IDs que no aparecen. Ninguna combinación obligatoria queda certificada por el simple hecho de publicar estos archivos. Los casos inválidos no se insertaron como filas de entrenamiento. V2-07 debe comprobarlos mediante fixtures separados, revisar los ambiguos y contrastar los 57 escenarios con sus ocho combinaciones.

Durante la primera publicación se detectó que el contrato formal solo admitía el estado de diseño previo. Se añadió el estado explícito de build generado pendiente de validación, sin admitir estados arbitrarios ni declarar un modelo entrenado. El intento academic-20261114-01 no llegó a publicarse y permanece en tmp como evidencia del fallo. El primer build publicado fue academic-20261114-02. La revisión final publicó academic-20261114-03 para que el schema generado también refleje el cierre de V2-06 y la referencia estadística ya realizada. Los cuatro CSV son idénticos en ambas publicaciones. El build 02 permanece intacto como revisión anterior de metadata. La referencia vigente es 03. No se sobrescribió ningún intento anterior.

Pasaron 110 pruebas, sin fallos ni omisiones. Incluyen 15 pruebas de generación, rechazo de duplicados, meses faltantes, lags alterados, precios inválidos, disponibilidad futura, contabilidad de stock, rutas, reproducción y publicación sin sobrescritura. También se ejecutó la regresión de integridad V1. Dos publicaciones temporales con IDs distintos produjeron CSV idénticos. Los manifests pueden variar por ID y hora, sin cambiar las observaciones. El [reporte de ejecución](../../ml/demand/reports/v2/builds/academic-20261114-03/closure.json) registra hashes, resultados y límites.

V2-06 cierra la construcción del primer build. El estado vigente es BUILT_PENDING_V2_07_NOT_FOR_TRAINING. V2-07 queda pendiente para revisión exhaustiva de datos, distribuciones, sensibilidad, reglas de disponibilidad y cobertura completa de escenarios. No se ajustaron scalers ni codificadores. Tampoco se seleccionó un modelo. Erika debe revisar después el contrato de inferencia real en V2-09B. No se modificaron RAW, V1/V1.1, modelos, reports anteriores ni Neon. No se creó un archivo Markdown nuevo.

## 17. Validación de datos y política offline V2-07

Revisión del 14 de noviembre de 2026, posterior a la construcción. El estado actual es integridad aprobada para la primera variante académica, sin autorización para entrenar. Los anexos anteriores conservan sus estados fechados. No se modificaron los once archivos del build vigente ni los de su revisión anterior.

La comprobación independiente está en v2/validate_build.py. No reutiliza la función de validación del generador. Lee los CSV publicados mediante el diccionario, contrasta hashes y el manifest registrado fuera del build, comprueba referencias de catálogo, reconstruye las fórmulas de las 17 features, valida snapshots y revisa la contabilidad de stock y tránsito. También comprueba meses completos, fechas con zona, orden de conocimiento, planes conocidos al corte y conservación de modalidades. El split mantiene meses completos, con sus cantidades y hashes originales. No hubo errores bloqueantes.

La revisión no se limita a probar que los archivos abren. Las pruebas introducen duplicados, alteraciones de precios, ratios, lags, stock, snapshots, filas, split y fechas. También comprueban que cambiar manifest y checksums juntos no sustituye la identidad registrada en el contrato activo. Estas alteraciones se realizan en memoria o bajo tmp, nunca en el dataset publicado.

Los [reportes vigentes](../../ml/demand/reports/v2/2.0.0/academic-20261114-03/validation-20261114-02/closure.json) están separados del build. Contienen calidad.json, estadisticas.json, distribuciones.csv y scenario_policy_fixtures.json. El registro validation-20261114-01 permanece intacto como primera revisión. La revisión 02 incorpora explícitamente el límite de volumen observado. El reporte original de construcción no se reescribió para aparentar que ya había ejecutado V2-07.

La revisión puede reproducirse desde la raíz, con un identificador nuevo:

```powershell
.\ml\demand\.venv\Scripts\python.exe -B ml/demand/v2/validate.py --build-id academic-20261114-03 --run-id IDENTIFICADOR_NUEVO
```

El comando publica exclusivamente en reports/v2/2.0.0/<build_id>/<run_id>. Rechaza identificadores repetidos. No genera un dataset ni modifica el existente. Cada revisión conserva hashes de entradas, implementación y resultados. La aprobación posterior se registra en el contrato activo mediante el hash del reporte. El manifest y validation.json del build mantienen su estado original de construcción.

### Qué quedó comprobado

Se definieron 57 fixtures de hechos, uno por escenario aprobado, más ocho combinaciones. La política offline de v2/scenario_checks.py decide sin recibir scenario_id ni expected_action. Comprueba cantidades, origen, entidades, fechas, precios, historia, conocimiento de variables, prioridades de rechazo o revisión, datos opcionales y contexto operativo. Los 65 casos obtuvieron la acción prevista.

Las pruebas adicionales comprueban que un aumento de precio no obliga a reducir el target, que un precio anunciado después del corte no entra a las features, que precios actuales no reconstruyen listas históricas, que una categoría nueva sigue la ruta UNKNOWN y que modalidad o stock desconocidos no se convierten en certezas. Las fechas cubren 23:59, 00:00, año nuevo, febrero bisiesto y el cambio UTC frente a UTC-4. Una fecha de origen sin zona queda en revisión si no se afirma un mes certificado. Una asignación mensual incorrecta presentada como válida se rechaza.

Las anulaciones conocidas antes del cierre se excluyen del agregado válido del fixture. Las posteriores exigen revisión de la etiqueta congelada, sin reescribir snapshots. La devolución a crédito reduce deuda primero y devuelve solo el excedente. El reintegro vendible espera inspección. Son comprobaciones offline de reglas. No certifican que el backend haya ejecutado una devolución, un pago o un movimiento real. Esa verificación corresponde a Erika y la integración posterior.

La falta de lags o de un target cerrado impide admitir una fila supervisada. Una inferencia con tres lags disponibles puede seguir siendo válida aunque el mes objetivo esté abierto y no exista target. Una revisión de plazo de proveedor tampoco excluye automáticamente ventas mensuales válidas. Se mantiene la diferencia entre datos predictivos y contexto de reposición.

El build conserva diez IDs observados de escenarios. Los 57 fixtures no convierten los otros 47 en eventos ejecutados por el generador. Los casos inválidos deben permanecer fuera de entrenamiento. Los controles de fechas, fuente o salidas futuras pueden probarse como fixtures sin insertarlos como ventas. Los casos que requieren medir respuesta de un modelo permanecen ligados a experimentos futuros. No se afirma cobertura dinámica completa ni aceptación de backend.

### Distribución y límites encontrados

| Conjunto | Filas | Ceros | Positivos | Rango observado | Media de unidades |
| --- | ---: | ---: | ---: | --- | ---: |
| TRAIN | 2.520 | 1.913 | 607 | 0 a 9 | 0,467 |
| VALIDATION | 504 | 385 | 119 | 0 a 8 | 0,423 |

No se calcularon distribuciones del target de TEST ni métricas predictivas. TEST solo se leyó para comprobar integridad, fórmulas y su hash congelado. Una prueba modifica sus targets en memoria y comprueba que las estadísticas publicadas de TRAIN y VALIDATION no cambian.

Los ceros de TRAIN representan aproximadamente 75,91%. Monash tenía 74,78% entre sus observaciones. La cercanía no demuestra exactitud comercial y no se forzó mediante ajustes. Hay poblaciones distintas, disponibilidad simulada y unidades solicitadas que no siempre pueden atenderse. No se calibraron parámetros mirando TEST ni resultados de un modelo.

Las 17 features tienen valores conocidos en TRAIN. Las proporciones de modalidad presentan 1.920 nulls por ausencia de ventas anteriores, que es un caso previsto. No se sustituyeron por cero. Las variaciones conocidas de precio tienen 18 nulls por planes no demostrados y días sin stock tiene 12 nulls por falta de observación. Son variables opcionales. Sus imputaciones e indicadores, si se utilizan, se aprenderán exclusivamente con TRAIN de cada fold durante los experimentos, sin aplicar el preparador V1 que exige otras columnas.

La antigüedad de cotización tiene un único valor en TRAIN. Puede mantenerse como columna constante con esa advertencia o excluirse mediante un feature set identificado en V2-08. No hay evidencia en este build para aprender su efecto. El contrato completo sigue teniendo 17 features. No se cambió en silencio.

La cotización solo toma tres niveles ficticios y es común a todas las parejas. Las 2.520 filas de TRAIN contienen 15 meses, no 2.520 observaciones económicas independientes. El calendario y la trayectoria simulada pueden confundirse con el efecto de precio o moneda. La variable económica es una hipótesis del experimento, no una relación causal estimada.

La disponibilidad limita el volumen vendido. Los pedidos latentes grandes y un fixture mayorista de 40 unidades no demuestran que el dataset represente ventas atendidas de ese tamaño. Esta variante sirve para un experimento de baja rotación. Para afirmar cobertura de mayoristas de gran volumen se necesitará una variante posterior con escalas y abastecimiento coherentes, identificada por configuración y build. No se modificó stock para inflar ventas ni se cambió este dataset después de revisar su distribución.

V2-07 cierra integridad y política offline del alcance inicial. No certifica precisión comercial, respuesta correcta de modelos todavía no entrenados ni cobertura de todas las variantes del generador. V2-08 debe conservar baseline, comparar modelos con VALIDATION, revisar errores por grupo, tratar la variable constante y documentar el alcance de volumen. TEST no se usará para seleccionar. La revisión del contrato con Erika permanece en V2-09B. El entrenamiento sigue sin autorización.

La verificación final aprobó 133 pruebas, sin fallos ni omisiones. Incluye 23 pruebas nuevas de revisión independiente y política, además de las suites previas de contratos, generación e integridad V1. La reproducción de generación usada por las pruebas se limita a copias temporales. No se publicó otro build. Los 22 archivos de los dos builds existentes, 136 RAW, 46 reportes anteriores, dos modelos, cinco manifests y 44 archivos protegidos permanecen intactos. No se ejecutó Git.

## 18. Preparación de experimentos V2-08

Revisión del 14 de noviembre de 2026. Esta tarea prepara experimentos y la ampliación futura, sin entrenar. No hace falta consultar Neon para resolver un parámetro constante o una capacidad fijada por el generador sintético. Una consulta de precios o stock actuales tampoco demostraría sus valores históricos. Se mantiene el alcance académico aprobado.

El [contrato de experimentos](../../ml/demand/v2/contracts/experiments.v2.json) fija decisiones antes de obtener resultados. El [preflight](../../ml/demand/reports/v2/experiments_preparation/experiments-preparation-20261114-02/preflight.json) verifica el build, su revisión V2-07, las columnas de TRAIN y los folds, sin procesar etiquetas ni valores de features de VALIDATION o TEST. La utilidad está en v2/experiment_preparation.py. No implementa entrenadores ni escribe ventas.

### Variable constante y entrada de los modelos

La antigüedad de cotización vale dos días en todo TRAIN. Se excluye explícitamente de los grupos que la contienen. No se altera el CSV, el diccionario original de 17 features ni los builds publicados. La variante completa del experimento utiliza 16 features. El nombre, las columnas y la exclusión se conservarán en cada experimento y artefacto. Una constante nueva o una columna sin datos TRAIN bloquea el preflight y requiere revisión, sin eliminarla en silencio.

| Grupo de comparación | Features efectivas | Propósito |
| --- | ---: | --- |
| Historia y calendario | 5 | Referencia comparable con la información inicial |
| Más modalidad | 7 | Revisar el aporte de ventas por menor o mayor |
| Más precios | 11 | Añadir listas históricas y cambios conocidos |
| Más tipo de cambio | 13 | Añadir nivel y variación, excluyendo edad constante |
| Más disponibilidad | 15 | Añadir observación de stock y faltantes |
| Más categoría | 16 | Variante completa sin usar IDs como cantidades |

Los precios, cotizaciones y disponibilidad siguen siendo simulados. Esta comparación no demostrará causalidad comercial. Tampoco permite concluir que la antigüedad no sirve en general, solo que esta versión no contiene variación para estudiarla.

En un build futuro la edad debe salir de eventos de cotización. Cada evento tendrá observación, publicación, fuente, tipo y unidad Bs/USD. Para cada corte se tomará la observación más reciente ya disponible. La selección será común a productos y tiendas, sin ruido por fila. Una actualización posterior al corte no puede cambiar la información anterior. Se probarán edades de referencia 0, 2, 7 y 30 días, sin presentarlas como frecuencias comerciales. Si no hay información comparable se conservará null. No se sustituirá por 6,96, una cotización de compra u otra moneda.

Las pruebas comprueban que esas edades se derivan de fechas, que los eventos futuros no alteran el valor disponible, que una cotización de otro tipo no se mezcla y que las observaciones contradictorias o unidades invertidas se rechazan. El helper está preparado para la futura implementación. No se aplicó a las filas del dataset vigente.

### Ventas mayoristas grandes y abastecimiento simulado

El límite actual viene de envíos de seis unidades con stock inicial cero. Multiplicar pedidos sin cambiar abastecimiento solo crea demanda no atendida. Una futura variante debe cambiar conjuntamente los mecanismos de cantidad y capacidad, conservando un escenario de escasez. No se aumentará el target ni se escribirá stock después de conocer las ventas para forzar un buen resultado.

Se especificaron casos de referencia de 20, 40 y 80 unidades por mayor, con escalas 1, 3 y 10. Son pruebas académicas de cobertura, no cuantiles automotrices de UCI ni ventas reales de RepuestoPro. Deben incluir recurrencia, pedidos excepcionales conocidos, pedidos inesperados, mezcla con venta por menor, recepciones parciales y retrasos. La modalidad será explícita. El tamaño o precio no la determinará por inferencia.

El prototipo de abastecimiento solo acepta tres meses cerrados, stock vendible, reservas identificadas, entradas firmes conocidas, pedidos conocidos antes del corte, margen y lote. No acepta target ni cantidad futura realizada. Utiliza un piso basado en el máximo de historia y compromisos conocidos, sin sumarlos como si fueran demandas distintas. Descuenta las reservas de la misma ventana sin volver a comprarlas. No cuenta entradas posteriores al vencimiento del pedido como si permitieran atenderlo antes. Las ventanas son meses calendario, incluido febrero bisiesto.

Este cálculo es un fixture de capacidad del simulador, no una regla comercial de reposición aprobada ni una implementación de H5. Tener una orden planificada tampoco garantiza recibirla a tiempo. La venta depende de la recepción efectiva, unidades enteras y stock vendible. Se conserva tránsito pendiente. Las reservas ambiguas o repetidas se rechazan para revisión.

En una prueba controlada, un pedido conocido de 40 unidades con cinco disponibles genera una planificación de 42 unidades adicionales al ajustar a lote de seis. Si llegan todas, se venden 40 y quedan siete. Si solo llegan 21, se venden 26, quedan 21 en tránsito y 14 unidades solicitadas no atendidas. Si el pedido se conoce después del corte, no provoca abastecimiento anterior artificial. Estos valores se conservan como fixtures, no como nuevas filas de entrenamiento.

El futuro build ampliado tiene como versión propuesta 2.1.0, todavía no registrada ni construida. Requiere generador y configuración propios, edades variables verificadas en TRAIN, volúmenes por mayor efectivamente atendidos, precio mayor <= menor, ambos >= costo, conservación de unidades, revisión V2-07 y una reserva TEST nueva antes de seleccionar modelos. Los pedidos conocidos se utilizarán como controles de abastecimiento, no como una feature nueva de las 17 aprobadas. Sin una variable autorizada o una regla separada, el modelo no puede prometer anticipar un pedido excepcional aunque el simulador prepare stock para atenderlo. Ese límite también se evaluará. El generador 2.0.0, sus archivos y el dataset actual permanecen intactos.

### Comparación futura, preparación y límites

Se mantienen baseline ingenuo, LinearRegression y RandomForestRegressor. Random Forest es candidato, no ganador. MLP queda opcional fuera de la primera matriz. Los parámetros se contrastaron con las clases instaladas de scikit-learn 1.9.1, sin llamar a fit.

Los folds se agrupan por meses completos dentro de TRAIN:

| Fold | Entrenamiento | Validación interna | Filas TRAIN | Filas validación |
| --- | --- | --- | ---: | ---: |
| F1 | Enero a junio 2025 | Julio a septiembre 2025 | 1.008 | 504 |
| F2 | Enero a septiembre 2025 | Octubre a diciembre 2025 | 1.512 | 504 |
| F3 | Enero a diciembre 2025 | Enero a marzo 2026 | 2.016 | 504 |

Por grupo de variables se probará una configuración lineal y cuatro de Random Forest. El bosque fija 200 árboles, seed 42, profundidad 4 u 8 y mínimo de 2 o 5 muestras por hoja. La configuración se elegirá con MAE medio de los folds internos. Después se ajustarán las seis alternativas lineales y seis bosques seleccionados con TRAIN completo. VALIDATION de abril a junio de 2026 comparará esos doce candidatos frente al baseline. TEST de julio a septiembre se mantendrá reservado para una única selección final. Los 102 ajustes del presupuesto son previstos, no ejecutados.

El tratamiento numérico usará mediana e indicadores de faltante aprendidos solo con TRAIN de cada fold. No habrá imputación previa sobre todo el CSV. La categoría se tratará como etiqueta, con vocabulario de TRAIN y una ruta UNKNOWN para faltantes o categorías nuevas. LinearRegression utilizará escalado numérico StandardScaler en ese mismo TRAIN. El bosque no requiere escalado. Se guardará un único pipeline de columnas, transformaciones y modelo para que Erika pueda utilizar el mismo contrato en inferencia. No se ajustó ninguno de esos componentes ahora.

MAE será principal, con RMSE, R², cobertura y errores por grupo. R² indefinido se registrará como null con motivo, no como porcentaje de precisión. MAPE no será principal por los ceros. El empate numérico se define con tolerancia 1e-9 para favorecer baseline, luego modelo lineal, luego bosque. No es un umbral comercial de mejora. Un deterioro relevante de RMSE o grupos requiere revisión, sin promoción automática. Predicciones faltantes o inválidas impiden comparar una muestra favorable contra el baseline completo como si la cobertura fuera igual.

La política propuesta de salida rechaza valores no finitos. Los valores negativos se recortarán a cero antes de las métricas de la política, registrando también su cantidad y métricas originales. No habrá redondeo entero antes de evaluar. Es una decisión previa al experimento, no una corrección posterior mirando TEST. No se produjo ninguna predicción en esta preparación.

El registro futuro será reports/v2/2.0.0/academic-20261114-03/experiments.csv. No se creó todavía porque no existen experimentos ejecutados. Cada fila futura tendrá dataset y hashes, columnas, split, fold, modelo, parámetros, transformaciones, política de salida, métricas, cobertura, tiempos, seed y versiones. No se agregarán planes ni resultados inventados al log V1.

Para reproducir la preparación desde la raíz:

```powershell
.\ml\demand\.venv\Scripts\python.exe -B ml/demand/v2/experiment_preparation.py --run-id IDENTIFICADOR_NUEVO
```

La preparación de V2-08 queda lista para el alcance de bajo volumen. V2-08 completo sigue en proceso porque faltan autorización, adaptador de preprocesamiento, entrenamiento, comparación, selección y evaluación final. La cobertura de gran volumen sigue especificada y probada mediante fixtures, pendiente de un nuevo generador y build. Erika conserva modelos y backend. Ross conserva dataset, frontend, visualización y trazabilidad. No se registró una revisión conjunta que no ocurrió.

La verificación final aprobó 150 pruebas, sin fallos ni omisiones. Incluye 17 pruebas nuevas de preparación, selección temporal de cotización, abastecimiento, reservas, tránsito y publicación de preflight. Una prueba bloquea fit de LinearRegression y RandomForest durante el preflight. Se mantuvieron intactos RAW, builds, modelos, logs y reportes anteriores. No se consultó Neon, no se publicaron datos nuevos y no se creó ningún Markdown. El preflight 01 queda como registro anterior. El 02 añade explícitamente la limitación de pedidos conocidos fuera de las features. No hay experimentos ejecutados ni métricas nuevas.

## 19. Build ampliado 2.1.0 con evidencia física

Trabajo iniciado después de la preparación V2-08 y completado en la continuación del 15 de noviembre de 2026. Se implementó un generador separado y se publicó [expanded-20261115-01](../../ml/demand/data/repuestopro_v2/2.1.0/expanded-20261115-01/manifest.json). Su origen es SYNTHETIC. Conserva seed 42, 56 productos del catálogo congelado y las tiendas 5, 6 y 7. No certifica ventas reales, cotizaciones actuales ni historia comercial. No se modificaron los generadores, datasets o reportes anteriores.

El código está en v2/generate_expanded.py, con revisión independiente en v2/validate_expanded.py. Se reutilizan funciones revisadas de calendario, lectura y contabilidad sin editar 2.0.0. Los contratos nuevos dataset_columns.v2_1.json, dataset_schema.v2_1.schema.json y expanded.v2_1.json separan versión, supuestos y validación. Las columnas predictivas mantienen sus nombres, tipos y funciones. No se añadieron features ocultas de perfil, pedido conocido, seed, stock posterior o demanda latente.

### Cotizaciones y variables

La fuente de cotización es una secuencia ficticia de 25 eventos. Cada uno identifica valor Bs/USD, fuente, tipo, observación y publicación. En cada corte se selecciona la observación más reciente ya publicada. La edad se calcula desde esas fechas. Las 168 parejas producto-tienda comparten la misma información económica en cada corte. No se añadió ruido independiente a la columna de antigüedad.

TRAIN contiene edades de 0, 2, 7 y 30 días. Los planes de precio se conocen en el corte mensual, después de la publicación disponible y antes de la predicción. La fecha puede coincidir exactamente con el corte porque la regla aprobada admite conocimiento anterior o igual al momento de emisión. El cierre de precios del mes anterior se registra por separado. El target nunca entra en esas decisiones.

Las 17 features presentan variación en TRAIN. La variante completa 2.1 vuelve a utilizar antiguedad_tipo_cambio_dias. El [plan experimental 2.1](../../ml/demand/v2/contracts/experiments.v2_1.json) define seis grupos de 5, 7, 11, 14, 16 y 17 columnas. Se mantiene el plan 2.0.0 con exclusión explícita de edad constante para reproducir aquella versión. El [preflight final](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/validation-20261115-01/preflight-final.json) enlaza build, contrato y revisión mediante hashes. No se ajustó un scaler, encoder o modelo.

### Mayoristas, recepción y datos de control

El simulador incluye perfiles de baja rotación, rotación media, mayorista recurrente, mezcla de modalidades, pedido excepcional conocido, pedido inesperado y recepción parcial o tardía. Sus pesos son supuestos de cobertura académica, no proporciones estimadas de una tienda real. Monash sigue orientando la intermitencia y tamaño de fondo. UCI sigue como referencia complementaria de colas y problemas de calidad. No se incorporaron filas externas ni se mapearon sus productos.

Los pedidos conocidos antes del corte pueden orientar la planificación de abastecimiento. Esta usa meses ya cerrados, stock disponible, compromisos conocidos e ingresos firmes previstos dentro de plazo. No utiliza las ventas futuras realizadas. El primer periodo tiene una política explícita de compra inicial, sin fabricar tres meses anteriores con cero. Una vez disponibles tres meses cerrados, se utiliza esa historia. Todas las compras se redondean a lotes enteros.

El stock vendible aumenta solamente al registrar una recepción. El tránsito pendiente no se vende. Cada pedido descuenta como máximo lo disponible a su fecha. Una entrega tardía no se utiliza para atender retrospectivamente un pedido vencido. Las recepciones parciales conservan sus unidades pendientes. No se reinicia stock cada mes ni se modifica para obtener un target deseado.

La evidencia de TRAIN es:

| Comprobación de pedidos POR_MAYOR con modalidad registrada | Cantidad |
| --- | ---: |
| Pedidos | 847 |
| Completamente atendidos | 786 |
| Parcialmente atendidos o no atendidos | 61 |
| Con al menos 20 unidades atendidas | 808 |
| Con al menos 40 unidades atendidas | 544 |
| Con al menos 80 unidades atendidas | 263 |

Los umbrales de 20, 40 y 80 son acumulados, no grupos independientes. Se cuentan unidades vendidas, no solo pedidos solicitados. Se conservaron los 61 casos con demanda no atendida. No se cambió su target para simular una venta inexistente. VALIDATION conserva 164 pedidos mayoristas, incluidos 11 parcialmente atendidos o no atendidos. No se publicaron distribuciones ni resultados predictivos de TEST.

Los pedidos conocidos son controles del abastecimiento simulado, no una nueva feature. Poder atender 80 unidades no demuestra que el modelo anticipe ese pedido con sus entradas actuales. La valoración de esa capacidad requerirá experimentos posteriores. Las ventas observadas siguen siendo distintas de la demanda total.

### Publicación, reproducción y validación

El build mantiene 4.032 filas mensuales y 3.528 supervisadas entre octubre de 2024 y septiembre de 2026. TRAIN conserva 2.520 filas, VALIDATION 504 y TEST 504. Las primeras tres observaciones mensuales construyen los lags. Los streams de 2.1.0 incluyen versión, configuración, mecanismo y partición. El hash de TEST difiere del de 2.0.0. No se usó TEST para seleccionar, ajustar parámetros o medir modelos.

La publicación contiene base_mensual.csv, dataset_supervisado.csv, escenarios_metadatos.csv, manifest.json, schema.json, split_manifest.json, validation.json y checksums.sha256. Añade catálogo, configuración, ledger mensual, quote_events.csv, orders.csv, shipments.csv, receipts.csv, daily_stock.csv y supply_plans.csv. También incluye copias del código utilizado con hashes de componentes.

Hay 2.887 pedidos, 1.811 envíos, 1.840 recepciones, 4.032 decisiones de compra y 122.640 registros diarios de inventario. Las 8.146 instancias de escenarios son controles mensuales o eventos de cotización, con sus fechas y snapshots. No equivalen a comprobar los 57 escenarios dinámicos completos. Los perfiles internos y unidades latentes quedan fuera del CSV supervisado.

La revisión independiente reconstruye cada día desde stock inicial, recepciones y pedidos. Contrasta lo solicitado, vendido, no atendido, pendiente de recibir y disponible al cierre. Verifica listas de pedidos conocidos, fechas de planificación, historia utilizada, bootstrap y cálculo de envíos. También reconstruye cotizaciones al corte, lags, proporciones, precios, márgenes, cobertura de observación, snapshots y hashes de los bloques temporales. La revisión de los CSV publicados pasó sin errores bloqueantes.

| Conjunto | Rango del target mensual observado | Media de unidades | Ceros |
| --- | --- | ---: | ---: |
| TRAIN | 0 a 92 | 16,640 | 1.123 |
| VALIDATION | 0 a 89 | 16,163 | 227 |

Estas cifras describen la nueva simulación. No son métricas de precisión ni estadísticas reales del negocio. Los [reportes de calidad y estadísticas](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/validation-20261115-01/calidad.json) conservan evidencia. No hubo entrenamientos ni predicciones de modelos.

Para generar otra publicación autorizada desde la raíz:

```powershell
.\ml\demand\.venv\Scripts\python.exe -B ml/demand/v2/generate_expanded.py --build-id IDENTIFICADOR_NUEVO
```

Para revisar un build, utilizar validate_expanded.py con --build-id, --run-id y --expected-manifest-sha256. El hash esperado debe venir del registro de confianza y no de un archivo recibido sin verificar. Los identificadores existentes se rechazan. Las áreas temporales permanecen bajo tmp. Los scripts anteriores conservan sus bindings 2.0.0. El contrato activo incluye un registro por versión y active_dataset_version identifica 2.1.0, sin cambiar dataset_build de 2.0.0 ni romper su reproducción.

El alcance cumplido es cotización de edad variable y cobertura física de ventas mayoristas grandes en una primera variante académica. Sigue existiendo una trayectoria económica compartida y una fórmula sintética que un modelo podría memorizar. No se certificó causalidad, precisión comercial, demanda perdida o integración de backend. La revisión de Erika, el adaptador, los modelos y sus métricas siguen pendientes. El entrenamiento continúa sin autorización. No se utilizó Neon, no se modificó RAW y no se creó un archivo Markdown nuevo.

La suite de implementación aprobó 169 pruebas, sin fallos ni omisiones. Tras registrar el build se aprobaron dos comprobaciones adicionales de contratos y hashes, con 171 comprobaciones en total. Las pruebas incluyen reproducción, serialización y revisión independiente, edad alterada, publicación futura, recepción duplicada, venta sin existencia, historia inventada, modalidad falsa, stock reescrito, pedidos desconocidos y trazabilidad de escenarios. Se verificaron los hashes de 136 RAW, 36 archivos anteriores de data, 60 reportes, dos modelos, cinco manifests y 44 archivos protegidos. Todos permanecieron intactos. Los seis componentes anteriores fijados al inicio también conservaron sus bytes. No se ejecutó Git.

## 20. Adaptador de preprocesamiento 2.1.0

Implementación del 15 de noviembre de 2026. El componente está en [v2/preprocessing.py](../../ml/demand/v2/preprocessing.py), con contrato propio preprocessing.v2_1.json. Implementa DemandPreprocessor y load_feature_partition. No incorpora regresores ni ejecuta entrenamiento. La revisión mantiene intactos los archivos del dataset 2.1.0, sus versiones anteriores, RAW y modelos existentes.

El preprocesamiento convierte los datos en la matriz numérica que utilizarán los modelos. Aprende medianas, vocabulario y escalas solo cuando recibe un conjunto TRAIN válido. En esta tarea esos ajustes se probaron con ejemplos controlados. El dataset publicado se leyó para comprobar estructura, tipos, particiones, identidad y restricciones, sin aprender parámetros sobre él. No se generó un modelo, un artefacto productivo o un nuevo experimento.

### Contrato de entrada y selección

El DataFrame de entrada contiene las 17 features canónicas y mes_objetivo como contexto. El mes sirve para revisar calendario, ventanas y disponibilidad temporal. No entra como una columna directa del modelo. Se rechazan target, IDs como columnas, controles, perfiles generativos o cualquier nombre ajeno al contrato. El target puede acompañar la firma estándar fit(X, y), necesaria para un pipeline futuro, pero el adaptador no lo lee ni utiliza.

Los grupos aprobados mantienen 5, 7, 11, 14, 16 y 17 features. Se seleccionan por nombre y orden canónico, no por posición recibida. Cambiar el orden del DataFrame no cambia la matriz. Omitir una columna canónica provoca error. Un dato opcional desconocido debe expresarse como null, no desaparecer del contrato. Un grupo menor explícito puede utilizarse cuando una variable opcional de otro grupo no tenga información suficiente, sin eliminar columnas de forma silenciosa.

La carga load_feature_partition verifica hashes de plan, manifest, schema y CSV antes de interpretar las features. No acepta rutas de archivos arbitrarias. No extrae targets ni aprende transformaciones. Conserva productId, locationId y mes_objetivo en un índice compuesto para que una futura rutina de entrenamiento alinee X con y por identidad de fila. Los IDs no se incorporan a la matriz numérica. Las predicciones y reportes deberán conservar esa misma asociación.

El componente comprueba tipos, números finitos, enteros, límites, orden de precios, coherencia de proporciones, días observados y calendario. No reemplaza valores inválidos por otros que permitan continuar. La verificación de origen y eventos completos sigue correspondiendo al loader y a la revisión del build. Un DataFrame manual no demuestra por sí mismo la procedencia de sus valores.

### Aprendizaje restringido a TRAIN

Cada instancia permite un solo fit. Los folds utilizan instancias nuevas o clones. El adaptador reconoce los prefijos TRAIN aprobados de seis, nueve, doce y quince meses, siempre dentro de la ventana máxima configurada. Esto permite integrarlo con un pipeline y una validación agrupada por meses. No admite aprender con VALIDATION, TEST, meses faltantes o un intervalo no aprobado.

Cuando el índice proviene del loader, exige todas las parejas de productos y tiendas para cada mes del fold. Una división aleatoria por filas o la pérdida de una fila de esa cohorte se rechaza antes de calcular medianas o escalas. Transformar una fila individual en inferencia sí es válido. Una transformación no necesita la cohorte completa porque no aprende parámetros.

Los métodos son fit, transform, fit_transform y get_feature_names_out. Transform utiliza solamente el estado ya aprendido. Nunca actualiza medianas, categorías o escalas a partir de datos nuevos. Intentar ajustar de nuevo una instancia falla y conserva su estado. Los tests verifican que valores extremos o categorías nuevas en ejemplos de VALIDATION y TEST no cambian los parámetros.

### Faltantes, categorías y escalado

| Componente | Decisión |
| --- | --- |
| Faltantes numéricos opcionales | Mediana del TRAIN del fold |
| Indicadores de faltante | Una columna binaria fija por feature numérica nullable, aunque no tenga faltantes en ese TRAIN |
| Columna seleccionada totalmente vacía o constante | Rechazar el grupo para revisión, sin eliminarla automáticamente |
| categoryId | Etiqueta categórica, con vocabulario exclusivo de TRAIN y bucket UNKNOWN reservado |
| Categoría nueva o faltante | UNKNOWN, sin crear columnas durante transform |
| Ruta LinearRegression | StandardScaler únicamente sobre variables numéricas imputadas |
| Ruta RandomForest | Valores numéricos imputados sin escalado |
| Indicadores y categorías codificadas | Permanecen en cero o uno, sin escalado |

Los indicadores permiten distinguir una observación real de un valor imputado. La mediana no se escribe en el dataset ni se presenta como historia reconstruida. El valor desconocido permanece null en su fuente. Una columna sin ningún dato TRAIN no recibe un cero o una constante arbitraria para hacerla utilizable.

La salida combina variables numéricas, indicadores y codificación one-hot de categorías. En la variante completa hay 16 variables numéricas, diez indicadores fijos y las categorías conocidas en ese TRAIN más UNKNOWN. El número de columnas transformadas puede superar las 17 features originales. Se fija en fit y permanece estable durante inferencia, incluso cuando aparecen nuevas categorías. get_feature_names_out proporciona los nombres para interpretar coeficientes o importancias posteriormente.

Los tests usan tres categorías conocidas y producen 30 columnas en el ejemplo completo. Esa dimensión pertenece a los fixtures, no a un modelo ajustado con el catálogo completo. No se entrenó ningún modelo con esas matrices ni se publicaron los estados de prueba como artefactos productivos.

### Estado compartido y evidencia

El adaptador es compatible con clone y Pipeline de scikit-learn. to_state y from_state permiten comprobar una representación JSON con versión, columnas, orden, medianas, vocabulario, medias, escalas, ventana y hashes. La restauración conserva las transformaciones y puede ejecutarlas sin volver a leer el repositorio. El estado no contiene un regresor. No se cargó o guardó ningún archivo joblib.

Se distingue el hash del build que define el contrato del hash del DataFrame utilizado para ajustar parámetros. En los tests ese DataFrame es un fixture de 15 filas o un prefijo de seis, nueve o doce meses. No se registra como si fueran las 2.520 filas de TRAIN del dataset sintético. El estado incluye la ventana efectiva y, cuando existe, el hash de las identidades de fila. La futura rutina experimental deberá enlazar ese estado con el dataset y el modelo del mismo run.

El adaptador queda implementado para 2.1.0. Falta conectar la rutina experimental y, únicamente cuando se autorice, ajustar un pipeline con el TRAIN real, entrenar los modelos, comparar VALIDATION y evaluar la selección final en TEST. La revisión del artefacto con Erika permanece pendiente. No se midió MAE, RMSE o R², no se eligió ganador y no se modificó Neon.

La suite final aprobó 201 pruebas, sin fallos ni omisiones. Incluye 30 pruebas nuevas del adaptador. Los [resultados y hashes](../../ml/demand/reports/v2/preprocessing/preprocessing-20261115-01/validation.json) distinguen ajustes de fixtures, lectura del build y cero entrenamientos de regresores. Se conservaron 59 archivos de data, 136 RAW, 65 reportes anteriores, dos modelos, cinco manifests y 44 archivos protegidos. No se ejecutó Git. Los contratos de planificación anteriores conservan sus TODO fechados. El estado de implementación vigente se registra en preprocessing_adapter dentro del contrato activo.

## 21. Integración de la rutina experimental 2.1.0

Continuación del 15 de noviembre de 2026. [v2/experiments.py](../../ml/demand/v2/experiments.py) conecta el adaptador con la rutina de comparación. El contrato runner.v2_1.json enlaza mediante hashes el plan experimental, el contrato de preprocesamiento y su implementación. No se modificaron esos componentes anteriores ni el dataset. Esta entrega prepara la ejecución, no registra resultados de modelos.

### Entrada, comparación y límites

load_xy entrega features y target separados. Los alinea con la clave productId, locationId, mes_objetivo. El orden original de y puede cambiar, pero sus identidades deben coincidir exactamente con X. Faltantes, claves sobrantes, duplicados o cantidades inválidas detienen la carga. El target no entra en las features. Los IDs se conservan como identidad fuera de la matriz numérica.

La preparación sobre el build publicado verificó TRAIN con 2.520 filas, VALIDATION con 504 y seis particiones internas. F1 utiliza enero a junio de 2025 para aprender y julio a septiembre para validar. F2 amplía TRAIN hasta septiembre de 2025 y valida octubre a diciembre. F3 amplía TRAIN hasta diciembre de 2025 y valida enero a marzo de 2026. Cada mes conserva sus 168 parejas producto-tienda. La rutina rechaza cargar TEST. Las etiquetas de TRAIN y VALIDATION solo se leyeron para comprobar alineación.

Las seis familias de features producen 30 configuraciones. El presupuesto futuro máximo es de 90 ajustes internos más 12 ajustes con todo TRAIN. El baseline no requiere ajuste. Cada fold crea un pipeline nuevo para que medianas, categorías y escalas aprendan exclusivamente de su TRAIN. Una configuración con un fold fallido no puede seleccionarse promediando solo los folds restantes. Los pipelines internos no se guardan como modelos finales.

La lógica de selección conserva MAE como criterio principal. Ante empate numérico prefiere baseline, modelo lineal, menos features o un bosque más simple, según el plan. Mantiene RMSE, R² y errores por producto, tienda, pareja, rotación y condiciones históricas. La rotación se define únicamente con TRAIN. Una mejora global que empeore grupos o RMSE exige revisión y no provoca promoción automática.

Las predicciones negativas se conservan para diagnóstico y se limitan a cero para la política de salida. No se redondean al calcular métricas. Los resultados no finitos invalidan la evaluación completa, sin publicar métricas favorables sobre un subconjunto. R² queda sin valor cuando el target es constante o solo existe una observación. Un error de ajuste o predicción queda registrado de forma explícita.

### Ejecución segura y evidencia

La acción predeterminada de run_experiments.py es prepare. Publica solo un plan nuevo bajo reports/v2/experiment_runner, sin ajustes, predicciones, métricas de modelos, experiments.csv o artefactos. El [plan comprobado](../../ml/demand/reports/v2/experiment_runner/runner-20261115-01/run_plan.json) registra ocho particiones, 30 configuraciones y cero ajustes reales. Intentar reutilizar el identificador falla para conservar evidencia.

La acción execute permanece bloqueada por model_training_authorized false antes de cargar targets o construir modelos. No existe un argumento para saltar ese control. Cuando se autorice, la ruta preparada separará reportes, log y candidatos V2 de los archivos V1. El registro comprueba encabezados, evita repetir un run y utiliza reemplazo atómico con bloqueo del log. Los tests de escritura utilizan exclusivamente carpetas temporales y resultados de prueba.

Las pruebas de comparación usan dobles que devuelven valores controlados, sin aprender relaciones. Sus 102 llamadas de prueba a fit no son entrenamientos de regresores ni resultados académicos. La carga y la preparación usan el build únicamente en lectura. Las factorías de LinearRegression y RandomForest se comprobaron sin ajustar sus modelos. Falta autorizar entrenamiento, comprobar la ejecución con modelos reales, revisar la serialización del artefacto con Erika, seleccionar con VALIDATION y evaluar TEST al final. V2-08 continúa en proceso. No se declara ganador o precisión comercial.

La suite de cierre aprobó 222 pruebas, sin fallos ni omisiones, con 21 pruebas nuevas de la rutina. Los [resultados de validación](../../ml/demand/reports/v2/experiment_runner/runner-20261115-01/validation.json) conservan hashes de implementación y el log de pruebas. Se comprobaron intactos 59 archivos de data, 136 RAW, 68 reportes previos, dos modelos, cinco manifests y 44 archivos protegidos. No se crearon Markdown nuevos ni se utilizó Neon o Git. El registro activo experiment_runner distingue esta entrega de los estados históricos de planificación.

## 22. Entrenamiento autorizado y comparación con VALIDATION

El 15 de noviembre de 2026 se autorizó entrenar con el dataset 2.1.0, sin evaluar TEST. El run training-20261115-01 conserva la seed 42 y las configuraciones ya fijadas. No se cambió el plan para favorecer un modelo. El contrato de ejecución se habilitó temporalmente y se restauró con sus bytes originales al terminar. La autorización y las llamadas reales quedan en execution_audit.json, dentro del reporte del run. Los contratos anteriores mantienen su estado histórico de planificación. El registro vigente training_run del contrato activo identifica esta ejecución.

Se completaron los 90 ajustes de validación interna y los 12 ajustes finales sobre TRAIN, sin fallos. Cada uno utilizó un preprocesador nuevo. Los únicos intervalos de aprendizaje fueron los prefijos aprobados de enero de 2025 a junio, septiembre o diciembre de 2025, además del TRAIN completo hasta marzo de 2026. Los 102 regresores y sus 102 preprocesadores terminaron correctamente. El baseline no requiere ajuste. Ningún ajuste incluyó meses de VALIDATION o TEST.

La selección interna del bosque utilizó únicamente los tres folds dentro de TRAIN. Después se compararon seis modelos lineales, seis bosques y el baseline con las mismas 504 filas de abril a junio de 2026. El resultado es un pronóstico de un mes con historia actualizada a partir de meses ya cerrados. No es una predicción simultánea de tres meses desde marzo. TEST, de julio a septiembre de 2026, no se cargó como partición ni se evaluó.

| Referencia | Features del mejor grupo | MAE, unidades | RMSE, unidades | R² |
| --- | ---: | ---: | ---: | ---: |
| Baseline, ventas del mes anterior | 1 | 11,0456 | 21,6854 | 0,3050 |
| LinearRegression | 14 | 8,7904 | 15,3852 | 0,6502 |
| RandomForestRegressor | 14 | 8,5379 | 14,6629 | 0,6823 |

RandomForest obtuvo el menor MAE global con expanded_with_exchange. Utiliza 200 árboles, profundidad máxima 4, mínimo de dos observaciones por hoja, max_features 1.0, bootstrap y seed 42. Sus 14 features incluyen los tres lags, calendario, modalidad, precios y cotización. Las variantes de 16 y 17 features también se entrenaron, pero no mejoraron ese MAE. Esto no demuestra que stock o categoría carezcan de utilidad comercial. La diferencia pertenece a este experimento sintético y no mide efectos causales.

La reducción del MAE frente al baseline es de 22,70 %. El MAE del candidato en TRAIN fue 8,5081. Las métricas se calcularon sin redondear predicciones y con la política de salida no negativa ya fijada. El mejor modelo lineal produjo 31 predicciones negativas antes de aplicar esa política, con métricas originales conservadas. El bosque seleccionado no produjo valores negativos.

### Revisión por grupos y estado del candidato

El resultado permanece REVIEW_REQUIRED. El bosque mejora globalmente, pero empeora el MAE de 17 productos entre 56 y de 74 parejas producto-tienda entre 168. También empeora baja rotación, historia sin ventas y modalidad desconocida o parcial. No hay deterioro global de RMSE. Los grupos producto-tienda tienen solo tres observaciones mensuales de VALIDATION, por lo que no permiten afirmar diferencias estables o significativas por sí solos.

En baja rotación el MAE pasa de 1,1852 a 1,6340. En historia sin ventas pasa de 0,4444 a 1,1119, sobre nueve filas. En alta rotación mejora de 28,2381 a 20,6900. El producto 20 empeora de 2,6667 a 9,7560 en nueve filas. Estas diferencias deben revisarse antes de aceptar una política global. No se eliminaron filas difíciles, no se cambiaron targets y no se ajustaron configuraciones mirando esos errores.

La siguiente decisión es revisar estos grupos con el equipo y Erika. No corresponde corregir una predicción sustituyendo la historia sintética, abrir TEST para resolver el desacuerdo o afirmar precisión comercial. Cualquier cambio de política o búsqueda adicional deberá quedar registrado porque reutilizar VALIDATION para muchas decisiones puede sobreajustar la selección. No se implementó una mezcla de modelos por grupo ni se promovió el candidato.

### Archivos y comprobación

El [reporte de comparación](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/training-20261115-01/comparison.json) conserva 103 evaluaciones: 90 internas y 13 externas. validation_comparison.csv reúne las opciones finales. group_review.json compara errores por grupo. El experiments.csv propio de V2 conserva tiempos, parámetros, versiones, hashes, cobertura y métricas originales. No se añadió ninguna fila al log V1.

El candidato se guardó en models/v2/training-20261115-01/candidate.joblib, junto con preprocessing.json y manifest.json. Es un candidato académico, sin referencia ACTIVE o despliegue. Los controles posteriores verifican su hash, la recuperación del preprocesamiento y la reproducción de métricas exclusivamente con VALIDATION, sin repetir entrenamiento. La revisión del contrato de inferencia con Erika y el TEST final siguen pendientes. V2-08 continúa en proceso.

Se revisaron 230 pruebas distintas. La primera suite aprobó 229 y detectó una comprobación anterior que exigía la ausencia de experiments.csv. Se actualizó para exigir autorización, evidencia del run, hashes y bloqueo posterior, en lugar de negar la nueva ejecución autorizada. Las 50 pruebas de las suites afectadas pasaron al repetirlas, sin fallos ni omisiones. Las ocho pruebas nuevas comprueban el resultado guardado sin entrenar otra vez. El [cierre de validación](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/training-20261115-01/closure.json) conserva ambos logs.

Se conservaron intactos 59 archivos de data, 136 RAW, 71 reportes previos, dos modelos anteriores, cinco manifests, cinco archivos de candidates, cuatro de decisions y trece de lifecycle. También se verificaron los 44 archivos protegidos. Solo se añadieron los tres archivos del candidato dentro de models/v2/training-20261115-01. No se utilizó Neon, no se ejecutó Git y no se crearon Markdown nuevos.

## 23. Por qué el candidato empeora en algunos grupos

Revisión posterior del 15 de noviembre de 2026. Se utilizó el candidato ya guardado para analizar TRAIN y las mismas 504 filas de VALIDATION. No hubo ajustes, búsqueda de configuraciones o evaluación de TEST. El [diagnóstico por filas y grupos](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/training-20261115-01/diagnosis-20261115-01/error_diagnosis.json) amplía la explicación del anexo 22. Es un análisis descriptivo de resultados ya observados, no otra validación independiente o una nueva selección.

### Ceros, rotación y promedio de los árboles

El bosque utiliza squared_error. Cada árbol devuelve un promedio de las ventas de su hoja y el bosque promedia los 200 resultados. Una hoja es un grupo de ejemplos que siguen las mismas decisiones del árbol. En este candidato de profundidad máxima 4, las hojas que reciben filas de poca venta suelen reunir ejemplos con cero y con ventas positivas. Sus promedios quedan por encima de cero. Se comprobó la salida directamente con los valores de las hojas, sin reentrenar. Las proporciones de ejemplos de TRAIN que comparten hoja son descriptivas y no sustituyen los pesos bootstrap usados al entrenar.

Las 504 predicciones fueron positivas. En las 111 filas que tenían los tres lags en cero, todos los árboles devolvieron valores positivos. De esas filas, 86 terminaron con cero ventas. El baseline acertó cero en esas 86, mientras el bosque predijo 1,318 unidades en promedio. Esto explica parte del deterioro, sin demostrar que toda historia de ceros deba recibir cero automáticamente. En otras 25 filas con los mismos tres lags en cero sí hubo ventas, con 95 unidades en total.

| Grupo definido con TRAIN | Filas VALIDATION | Filas con target cero | MAE baseline | MAE candidato |
| --- | ---: | ---: | ---: | ---: |
| Alta rotación | 168 | 4 | 28,2381 | 20,6900 |
| Rotación media | 165 | 87 | 3,8000 | 3,3482 |
| Baja rotación | 162 | 129 | 1,1852 | 1,6340 |
| Sin ventas durante TRAIN | 9 | 7 | 0,4444 | 1,1119 |

En baja rotación, la mediana de las ventas observadas es cero y la mediana de la predicción es 1,324. La venta media pasa de 0,696 en TRAIN a 0,673 en VALIDATION. Estas medias no muestran un cambio grande de nivel que explique por sí solo el deterioro. El patrón observado es principalmente una sobreestimación de meses sin venta. MAE favorece una mediana condicional, mientras el criterio del bosque aprende promedios. Esa diferencia puede ser importante en ventas intermitentes, con muchos ceros y pocos pedidos grandes. No se probó otra función de pérdida, por lo que no se afirma que cambiarla resuelva el problema.

El beneficio global se concentra en alta rotación, que reduce aproximadamente 1.268 unidades de error absoluto acumulado. Baja rotación añade unas 72,7 y el grupo sin ventas añade unas 6,0. Por eso una mejora global puede coexistir con perjuicios locales. El bosque mejora el MAE agregado en los tres meses y en las tres tiendas, pero eso tampoco garantiza mejor desempeño en cada producto.

### Productos concretos y modalidad

Los 17 productos con MAE mayor que el baseline son 3, 4, 5, 10, 12, 15, 17, 19, 20, 21, 29, 32, 41, 43, 44, 45 y 47. El archivo worsened_products.csv conserva para cada uno el error, la dirección del sesgo, el aporte de meses con cero, la tienda y el mes que más contribuyen al deterioro. validation_row_errors.csv permite revisar las 504 filas, no solo ejemplos elegidos.

El producto 20 muestra una caída que el bosque sigue con retraso. En la tienda 5 vendió 41, 81 y 40 unidades de enero a marzo. En abril, mayo y junio vendió 25, 21 y 20. El modelo predijo 47,16, 50,24 y 48,81. El baseline utilizó 40, 25 y 21. El error adicional de este producto se concentra en esa tienda. No sería correcto explicar este caso únicamente como baja rotación o como un dato faltante.

Los productos 43, 3 y 32 presentan también picos y cambios entre tiendas. El producto 43 vendió 80, 84 y 81 unidades en la tienda 6. El producto 32 pasó de 20 en marzo a 80, 81 y 80 en la tienda 7. El promedio compartido del bosque no reproduce todos esos cambios. Sus importancias internas se concentran en ventas de hace dos y tres meses, con aproximadamente 65,56 % y 28,88 %. Son importancias del ajuste, sensibles a correlaciones, no porcentajes de causalidad o pruebas de que una variable sea innecesaria.

La variante seleccionada no incorpora productId o locationId como features. Tampoco incluye frecuencia de meses con venta, tiempo desde la última venta o pedidos firmes. Por eso combina comportamientos de varias parejas a partir de los 14 valores disponibles. Las variantes con stock y categoría ya se compararon en el run original y no mejoraron el MAE global. No se puede afirmar que añadir más columnas de forma automática solucionaría estos casos.

El grupo de modalidad desconocida o parcial necesita una interpretación más precisa. Contiene 258 filas. En 227, la proporción mayorista está vacía porque el mes anterior no hubo ventas. No es prueba de un registro comercial incompleto. En esas filas el MAE pasa de 1,5066 a 2,3822. En las otras 31, con cobertura de modalidad menor que uno, el MAE mejora de 16,6452 a 10,4590. El grupo conjunto empeora solo de 3,3256 a 3,3527. No corresponde atribuir ese deterioro a todos los datos parciales ni rellenar una proporción indefinida con cero.

Se contrastaron los pedidos simulados de VALIDATION como evidencia posterior. Sus cantidades efectivamente atendidas coinciden con las ventas del target. Hay 162 filas mensuales con pedidos mayoristas conocidos al corte. En el producto 20, tienda 5, constaban pedidos de 20 unidades antes de cada mes de VALIDATION. Es información que el candidato actual no recibe. Las cantidades finalmente atendidas y los pedidos conocidos después del corte solo sirven para explicar resultados. No deben convertirse en features futuras disponibles antes de tiempo. Un pedido solicitado tampoco garantiza venta si se cancela o no existe stock vendible.

### Qué podemos hacer antes de cerrar la selección

| Opción | Qué puede hacerse ahora | Qué exigiría después |
| --- | --- | --- |
| Conservar el candidato para la demo académica | Explicar MAE global, grupos perjudicados y origen sintético. Mantenerlo sin promoción | Aceptación explícita del alcance, revisión con Erika y autorización independiente para TEST |
| Mantener el baseline como referencia operativa | Reconocer que resulta más adecuado en varios grupos de ventas escasas, sin cambiar el modelo guardado | Una regla de uso por grupo debe definirse con información de TRAIN y validarse antes de utilizarla |
| Diseñar una ruta para ventas intermitentes | Especificar frecuencia de venta, tiempo desde la última venta y una alternativa que distinga ocurrencia de cantidad | Nuevo contrato, disponibilidad temporal, folds internos y entrenamiento autorizado. No se implementó esa ruta |
| Revisar criterio y capacidad del bosque | Documentar el desacuerdo entre promedio y MAE, además del suavizado de cambios de nivel | Evaluar otra pérdida, profundidad o alternativa solo con búsqueda predefinida dentro de TRAIN. No se promete mejora |
| Incorporar pedidos y compromisos conocidos | Auditar qué se conocía antes del corte, cancelaciones, fechas, stock y entrega | Contrato nuevo. Separar pedidos comprometidos del componente no comprometido para evitar contarlos dos veces |
| Revisar precio, cotización y disponibilidad | Mantener unidades, vigencia y límites de observación ya acordados | Más evidencia temporal para evaluar su utilidad. Estas métricas no justifican afirmar elasticidad o efecto causal |

No se recomienda activar el bosque para todos los productos todavía. La salida más defendible hoy es conservarlo como candidato académico con revisión pendiente. El equipo debe decidir si acepta ese alcance o si requiere una protección explícita para baja rotación antes de cerrar la selección. También debe acordar qué deterioro local es aceptable. Esa tolerancia aún no existe y no debe inventarse a partir del resultado que convenga.

Si se propone una mezcla de baseline y bosque, no se debe elegir qué usar mirando cuál acertó el target de cada fila. Eso usaría información futura. La regla debe depender de historia disponible al corte, quedar fijada antes de evaluarse y comprobarse en folds temporales. Este diagnóstico no autoriza una nueva mezcla, ajuste, búsqueda o evaluación de TEST. Tampoco debe abrirse TEST para decidir umbrales o resolver los grupos difíciles.

VALIDATION ya se utilizó para elegir entre varias opciones y ahora se analiza para entender errores. Más cambios guiados por estos mismos resultados aumentarían el riesgo de adaptar el sistema a ese bloque. Una ampliación requerirá un protocolo de comparación documentado y evidencia temporal suficiente. No se modifican las particiones actuales para aparentar una prueba nueva. La limitación general se mantiene: el target son ventas observadas, no demanda perdida cuando faltó stock.

La comprobación del candidato conservado aprobó sus ocho pruebas, sin fallos u omisiones. Se verificaron además 15 controles de consistencia del diagnóstico, incluidos identidad, grupos, cantidades atendidas, meses y métricas originales. El [cierre del diagnóstico](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/training-20261115-01/diagnosis-20261115-01/closure.json) conserva los hashes y resultados. Permanecieron intactos todos los datasets, RAW, modelos, reportes y decisiones anteriores. No hubo entrenamiento, uso de TEST, conexión a Neon, operaciones Git o Markdown nuevos. Solo se añadieron evidencias de diagnóstico y se actualizó la documentación activa.

## 24. Comparación exploratoria de alternativas

El equipo autorizó una nueva comparación con TRAIN y VALIDATION, sin abrir TEST. El run alternatives-20261115-01 conserva el dataset 2.1.0 y el candidato anterior. Se añadió v2/alternatives.py como componente experimental separado. Antes de entrenar se fijaron 14 configuraciones en alternatives.v2_1.json, con hashes de código, datos, contratos y referencia anterior. El plan copiado en el reporte permite comprobar qué se decidió antes de esta ejecución.

Se evaluaron las 14 configuraciones en los tres folds temporales de TRAIN. La media de MAE de los tres folds eligió una configuración por familia. Después se compararon ocho alternativas con las mismas 504 filas de VALIDATION, más el bosque anterior sin reentrenarlo. Hubo 25 ajustes reales de bosques y 25 ajustes de sus preprocesadores. Las reglas sencillas no entrenan regresores. TSB conserva y actualiza un estado de historia mediante parámetros fijados en la búsqueda. Las 50 llamadas de preparación de alternativas, 42 internas y ocho finales, no deben presentarse como 50 entrenamientos de Random Forest.

### Opciones y control temporal

Se conservaron lag1 como baseline, mediana de los tres lags y una media con pesos 0,6, 0,3 y 0,1 para dar más importancia al mes reciente. Para ventas intermitentes se probó TSB. Este método combina una probabilidad de que ocurra una venta con el tamaño esperado de una venta positiva. La probabilidad se actualiza cada mes cerrado y el tamaño solo cuando hubo ventas. Se compararon alpha y beta en 0,1 o 0,3. La configuración elegida dentro de TRAIN fue 0,1 para ambos. No utiliza observaciones del mes que intenta predecir.

Los bosques mantienen 200 árboles, seed 42 y las 14 features del candidato anterior. Se comparó absolute_error con profundidad 4 u 8 y mínimo de cinco ejemplos por hoja. Este criterio utiliza medianas en las hojas, a diferencia de los promedios de squared_error. Otra familia añadió cuatro transformaciones de los lags: número de meses con venta, racha de ceros, cambio entre el mes anterior y el de hace dos meses, más media de tres meses. Son valores calculados en memoria. Esa media se estudió como representación experimental para árboles, aunque sea derivable de los lags. No se incorporó una columna nueva al dataset ni se cambió la decisión del esquema publicado.

También se probó predecir la diferencia respecto al último mes. El bosque aprende target menos lag1 y después suma lag1 a la corrección estimada. Un residuo negativo representa una disminución, no una venta negativa. El target original del CSV sigue siendo ventas brutas no negativas. La salida y sus métricas mantienen la política de limitar predicciones negativas a cero, sin redondear.

La última opción utiliza mediana3 en parejas con baja rotación o sin ventas en TRAIN. El resto utiliza el mismo bosque cuadrático de profundidad 4 del run anterior. La regla depende de la frecuencia de meses positivos de TRAIN, con el límite ya existente de un tercio. No cambia según el target de VALIDATION. Su clasificación queda fija durante cada fold. Los parámetros y la identidad del producto o tienda no se eligen observando qué modelo acertó cada fila.

### Resultados con el bloque VALIDATION reutilizado

| Alternativa | MAE global | RMSE | MAE baja rotación | MAE sin ventas TRAIN |
| --- | ---: | ---: | ---: | ---: |
| Baseline lag1 | 11,0456 | 21,6854 | 1,1852 | 0,4444 |
| Mediana3 | 9,7004 | 19,2891 | 0,7346 | 0,2222 |
| Media con mayor peso reciente | 9,6448 | 17,7235 | 1,0858 | 0,3889 |
| TSB | 8,7639 | 15,2295 | 1,3313 | 0,2779 |
| Bosque con error absoluto | 7,6174 | 15,1752 | 0,7612 | 0,2617 |
| Bosque con variables derivadas | 8,4743 | 14,5848 | 1,5423 | 0,9774 |
| Bosque de corrección sobre lag1 | 8,6569 | 14,8864 | 1,6735 | 0,9237 |
| Mediana en baja rotación, bosque en el resto | 8,2329 | 14,6514 | 0,7346 | 0,2222 |
| Bosque anterior, referencia congelada | 8,5379 | 14,6629 | 1,6340 | 1,1119 |

El bosque con error absoluto y profundidad 4 obtuvo el menor MAE global. Reduce ese error un 31,04 % frente al baseline y un 10,78 % frente al bosque anterior. El MAE mejora en las cuatro clases de rotación y en las tres tiendas respecto al anterior. En meses con target cero, baja de 2,1361 a 0,6905. Produce 276 predicciones positivas entre 504, frente a las 504 del anterior. El resultado respalda que el promedio de hojas contribuía a la sobreestimación, aunque esta comparación no aísla causalmente cada decisión del modelo.

La mejora no es uniforme. El RMSE aumenta un 3,49 % frente al bosque anterior y R² pasa de 0,6823 a 0,6597. Los errores ante subidas de volumen aumentan: el MAE de las 155 filas con más ventas que el mes previo pasa de 13,3626 a 15,0212. En las 166 con caída, mejora de 9,8520 a 7,1734. Estos grupos se definen con el target observado solo para diagnóstico posterior. No pueden usarse para escoger qué modelo aplicar antes de conocer las ventas.

El nuevo bosque mejora 15 de los 17 productos que antes empeoraban. Once dejan de ser peores que el baseline. Quedan siete productos con MAE mayor que el baseline: 3, 15, 17, 20, 32, 43 y 50. El 50 es un nuevo caso perjudicado. Los productos 32 y 43 empeoran también respecto al bosque anterior. El producto 20 mejora de 9,7560 a 6,9836, pero el baseline sigue siendo mejor, con 2,6667. No se declara cerrado ese problema.

Como ejemplo de error grande, el producto 39 en tienda 6 vendió 82 unidades en junio. El bosque anterior estimó 11,03 y el de error absoluto 3,70. Ambos fallaron, pero el segundo aumentó el error. Este caso y otros picos explican por qué un MAE menor puede coexistir con un RMSE mayor. No se eliminaron esas filas ni se cambiaron sus cantidades.

### Qué alternativa conviene conservar

Hay dos opciones prácticas para discutir. Si se prioriza MAE y reducir sobreestimaciones en baja rotación, el bosque de error absoluto ofrece la mejora mayor. Si se busca una mejora más moderada con RMSE semejante al anterior, la ruta de mediana en baja rotación resulta más conservadora. Su RMSE es 14,6514 y mejora el MAE global un 3,57 % frente al anterior. Mantiene exactamente sus predicciones para las parejas de rotación media o alta. Aun así, empeora cinco productos respecto al anterior y once frente al baseline. No es una protección perfecta por producto.

El bosque con variables derivadas tiene el menor RMSE de esta comparación, pero la mejora global de MAE es pequeña y la baja rotación sigue siendo peor que el baseline. TSB y la corrección sobre lag1 tampoco resolvieron simultáneamente los objetivos. No se recomienda añadir complejidad solo porque exista otra técnica disponible.

Ninguna opción se activó. Se conservan las alternativas y el candidato anterior. El equipo debe acordar si prefiere la reducción de MAE o una penalización mayor de errores grandes, además de revisar los siete productos pendientes del bosque absoluto. No existe una tolerancia comercial aprobada que permita decidir automáticamente ese intercambio. Una eventual regla que combine otra vez estos resultados sería un experimento nuevo, no una mejora ya demostrada.

VALIDATION ya había servido para seleccionar y diagnosticar. Esta nueva comparación, aunque ajuste configuraciones dentro de TRAIN, sigue siendo exploratoria por reutilizar ese bloque. No demuestra precisión independiente o comercial. No se modificó el TEST ni se utilizó para buscar parámetros. Antes de una evaluación final deben fijarse opción, política, alcance y criterios de aceptación, sin utilizar TEST para resolver estas decisiones.

Los [resultados completos](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01/comparison.json) conservan las 42 evaluaciones internas y las nueve comparaciones finales. tradeoff_review.json reúne límites y errores por grupos. validation_predictions.json conserva claves y resultados por fila. validation_comparison.csv y product_comparison.csv permiten revisar todas las opciones y productos. El experiments.csv de este run es independiente de los logs anteriores. Los ocho artefactos locales y su manifest están en models/v2/alternatives-20261115-01. No se modificó el modelo anterior ni se integró una alternativa al backend o al panel.

Las 46 pruebas relevantes de contratos, resultados congelados, recarga y regresión pasaron, sin fallos u omisiones. Hay 17 pruebas nuevas para estas alternativas. Se comprobó que repetir el run no sobrescribe resultados ni inicia nuevos ajustes. El [cierre de comparación](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01/closure.json) conserva ambos logs y la revisión de integridad. Todos los datasets, RAW, modelos, reportes, candidates, decisions y lifecycle anteriores conservaron sus hashes. Los archivos nuevos de modelos quedan exclusivamente bajo el identificador de este run. No se utilizó Neon o Git y no se crearon Markdown nuevos.

## 25. Revisión de los siete productos y recomendación para H4

Se revisaron nuevamente las predicciones ya guardadas, sin ajustar modelos o leer TEST. La revisión utiliza exclusivamente las 504 observaciones de VALIDATION y sus reportes congelados. Los siete productos corresponden a los que todavía tienen MAE mayor que el baseline con el bosque de error absoluto. No son necesariamente los siete productos más difíciles de toda la plataforma. Cada producto tiene nueve observaciones, tres por tienda, por lo que la explicación es descriptiva y no demuestra diferencias estables.

| Product.id | MAE baseline | MAE bosque absoluto | MAE ruta combinada | Patrón observado |
| --- | ---: | ---: | ---: | --- |
| 3 | 10,4444 | 13,3258 | 14,8496 | Pedidos grandes persistentes subestimados en tienda 6 y variación en tienda 7 |
| 15 | 1,1111 | 1,1478 | 1,2772 | Venta aislada de ocho unidades después de tres meses en cero |
| 17 | 9,2222 | 9,8028 | 9,9250 | Ventas próximas a 80 unidades en tienda 5, suavizadas a unas 40 a 50 |
| 20 | 2,6667 | 6,9836 | 9,7560 | Caída de volumen en tienda 5 que ambos modelos siguen con retraso |
| 32 | 7,5556 | 13,9253 | 11,6560 | Subida y permanencia cerca de 80 unidades en tienda 7, todavía subestimada |
| 43 | 15,5556 | 21,0728 | 20,1521 | Pedidos altos en tienda 6 y cambios de volumen en tienda 7 |
| 50 | 8,8889 | 8,9306 | 8,8800 | Diferencia media pequeña, con un pedido grande mal previsto en tienda 6 |

El bosque absoluto resulta menos malo en cuatro de estos productos y la ruta en tres. Ninguno domina todas las tiendas de un mismo producto. En el 20, el bosque absoluto reduce el error de la tienda 5, pero el baseline sigue mejor la caída. En el 15, ambas candidatas predicen cero cuando aparece la venta aislada de ocho unidades. No sería correcto prometer que una regla de ceros puede anticipar toda reaparición de ventas.

Las diferencias frente al baseline de los productos 15 y 50 son de aproximadamente 0,037 y 0,042 unidades de MAE. Son diferencias observadas pequeñas, no pruebas de un perjuicio comercial importante. Aun así se conservan porque no existe un umbral de aceptación aprobado. El error de algunos pedidos grandes sigue siendo relevante aunque el promedio del producto parezca próximo al baseline.

### Qué ocurre con los errores grandes

| Medida en las mismas 504 filas | Bosque absoluto | Ruta combinada |
| --- | ---: | ---: |
| MAE, unidades | 7,6174 | 8,2329 |
| RMSE, unidades | 15,1752 | 14,6514 |
| Percentil 95 del error absoluto | 39,7750 | 32,8637 |
| Error absoluto máximo | 78,3025 | 70,9661 |
| Filas con error superior a 40 unidades | 21 | 5 |
| Suma de unidades previstas | 6.738,86 | 8.088,75 |
| Diferencia de esa suma frente a las 8.146 observadas | −17,27 % | −0,70 % |

El límite de 40 unidades se utiliza para describir los errores, no como tolerancia comercial o regla para seleccionar. Se revisó la misma unión de 21 filas difíciles para ambas candidatas, evitando comparar subconjuntos distintos. Los 21 casos tenían pedidos mayoristas conocidos antes del corte, información que ninguno de estos modelos recibe como feature. Esto identifica una limitación de información disponible, pero no demuestra que añadir la cantidad solicitada elimine el error. Algunos pedidos pueden no atenderse por completo. En el producto 51, tienda 5, había una solicitud de 80 unidades y se atendieron 69 en abril.

El caso más extremo corresponde al producto 39, tienda 6, en junio. Las ventas fueron 82 unidades y existía un pedido conocido de 80. Sus lags eran 0, 0 y 40. El bosque absoluto predijo 3,70 y la ruta 11,03. Ambos subestiman el pico. La ruta usa el bosque anterior en esa pareja porque su rotación TRAIN era media, por lo que su regla para baja rotación tampoco resuelve este caso. La futura incorporación de compromisos deberá distinguir pedidos conocidos, ventas no comprometidas, cancelaciones y disponibilidad. No se debe sumar el pedido a una predicción que ya incluya ese componente.

La suma prevista por el bosque absoluto queda un 17,27 % por debajo de las ventas observadas del bloque. Es una señal importante si se pensara usarlo para abastecimiento. MAE se calcula fila por fila, por lo que una mejor predicción de casos típicos no garantiza acertar la suma de unidades o los picos. La ruta tiene una suma más cercana, pero eso puede incluir compensación entre sobreestimaciones y subestimaciones. Ninguna suma debe presentarse como garantía de reposición correcta.

### Recomendación y límites de la decisión

Para el alcance académico de H4 se recomienda el bosque con error absoluto, absolute_forest-d4, como candidato a cerrar. Se mantiene MAE como criterio principal, acordado antes de esta comparación. Tiene un MAE un 7,48 % menor que la ruta, resulta mejor en los tres meses y en las tres tiendas de VALIDATION y deja siete productos peores que el baseline, frente a once con la ruta. En la comparación de los 56 productos, mejora el MAE de 38 frente a la ruta, empeora 17 y empata uno. No se está afirmando que sea mejor para cualquier costo del negocio.

La recomendación acepta explícitamente un RMSE mayor y más subestimaciones extremas. La ruta se conserva como alternativa si el equipo decide priorizar errores grandes o necesidades de stock por encima del MAE. Cambiar esa prioridad requiere registrarlo como un objetivo distinto, no cambiar silenciosamente el criterio después de ver qué opción conviene. El análisis actual no cuenta con costos aprobados de falta de stock, exceso de inventario o tolerancias por producto para resolver una decisión comercial.

No se recomienda ninguno para compra automática o uso comercial todavía. El bosque absoluto es la propuesta para la demostración académica, con advertencias visibles de ventas sintéticas, error típico, pedidos extraordinarios y revisión humana. No se reemplazó una referencia ACTIVE, no se cambió el artefacto guardado y no se cerró TEST. La recomendación no equivale a aceptación del equipo o evaluación independiente.

Antes de evaluar TEST deben quedar fijados el artefacto elegido, su hash, la política no negativa, las variables, el protocolo de inferencia y el alcance académico. Falta la revisión con Erika. No se introducirán excepciones para los siete IDs a partir de estos errores de VALIDATION. La historia disponible, no el target observado, debe determinar cualquier regla futura. VALIDATION ya fue reutilizado y los resultados siguen siendo exploratorios. Una nueva comparación no puede venderse como precisión confirmada por la empresa.

El [reporte pareado](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01/candidate-review-20261115-01/paired_review.json) conserva las nueve filas y el detalle por tienda de cada producto. seven_products.csv resume los siete casos. large_errors.csv contiene las 21 filas difíciles. recommendation.json identifica el artefacto propuesto y sus límites, sin modificar los resultados anteriores.

Las 17 pruebas de artefactos y resultados congelados pasaron, sin fallos u omisiones. Se reprodujeron los MAE y RMSE desde las predicciones guardadas y se comprobó la revisión de nueve filas por cada uno de los siete productos. El [cierre de revisión](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01/candidate-review-20261115-01/closure.json) conserva hashes, comprobaciones y el log. Los datasets, RAW, 14 archivos de modelos y todos los reportes y decisiones anteriores permanecieron intactos. No hubo entrenamiento, uso de TEST, conexión a Neon, operaciones Git o Markdown nuevos.

## 26. Selección aceptada y evaluación final única de TEST

El equipo aceptó expresamente absolute_forest-d4 para H4 y autorizó una sola evaluación final de TEST. Esta aceptación cierra la elección académica entre las alternativas. No autoriza reentrenar, cambiar datos, activar el modelo o desplegarlo. La selección y la política se fijaron antes de cargar TEST en [selection.v2_1.json](../../ml/demand/v2/contracts/selection.v2_1.json), con fecha, configuración, versiones y hashes. El bloque final no se utilizó para elegir otro modelo después de conocer sus resultados.

### Artefacto y política fijados

El artefacto aceptado es models/v2/alternatives-20261115-01/absolute_forest-d4.joblib. Su SHA-256 completo es e53cdb53f296b38098639f7dd7d748d5ecd088ea6353993d8d3f911ba32b6dfc. No se copió o reescribió. Contiene el bosque de 200 árboles, criterion absolute_error, profundidad máxima 4, mínimo de cinco ejemplos por hoja, bootstrap, max_features 1.0, seed 42 y n_jobs 1. El estado del preprocesamiento también tiene un hash fijado en la selección.

Se conservan las 14 features de expanded_with_exchange: tres lags, seno y coseno del mes, proporción y cobertura de modalidad, precios anteriores por menor y mayor, sus variaciones conocidas, tipo de cambio conocido, su variación y antigüedad. Los nombres exactos, parámetros, contratos y hashes están en la selección. Los IDs identifican las filas, no entran como cantidades numéricas. El preprocesamiento sigue ajustado exclusivamente con las 2.520 filas de TRAIN, de enero de 2025 a marzo de 2026. No se amplió TRAIN con VALIDATION, no se recalcularon medianas y el bosque continúa sin escalado numérico.

La política queda fijada como NONNEGATIVE_V1. Se rechaza una salida no finita o incompleta, sin publicar métricas de un subconjunto favorable. Las predicciones negativas se limitan a cero. Se conservan sus valores originales y el número de negativos para diagnóstico. No se redondea antes de evaluar. En esta ejecución no aparecieron predicciones negativas o no finitas.

El target sigue siendo ventas brutas observadas de producto y tienda durante el mes objetivo. TEST comprende julio, agosto y septiembre de 2026, con 504 filas y 168 parejas por mes. Se evalúa un mes hacia adelante con historia de meses cerrados. Agosto puede utilizar ventas de julio como lag porque ya se conocen al comenzar agosto. Esto no es una predicción simultánea de tres meses desde junio. El modelo y las transformaciones permanecen fijos durante todo el bloque.

### Resultado final

| Referencia fijada antes de TEST | MAE, unidades | RMSE, unidades | R² |
| --- | ---: | ---: | ---: |
| Baseline lag1 | 11,7639 | 23,0553 | 0,2022 |
| Bosque absoluto aceptado | 7,6327 | 15,4253 | 0,6429 |

El MAE baja un 35,12 % frente al baseline. Esa cifra es reducción de error en este bloque sintético, no porcentaje de precisión. El MAE fue 7,6174 en VALIDATION y 7,6327 en TEST. La similitud no demuestra precisión comercial, pero el resultado final conserva la mejora frente a la referencia fijada. R² no se presenta como accuracy.

| Mes TEST | MAE modelo | MAE baseline |
| --- | ---: | ---: |
| Julio de 2026 | 9,1159 | 12,5060 |
| Agosto de 2026 | 7,0424 | 11,1905 |
| Septiembre de 2026 | 6,7400 | 11,5952 |

En alta rotación, el MAE es 19,0371 frente a 29,4524 del baseline. En rotación media es 2,6091 frente a 4,2000. En baja rotación es 1,3467 frente a 1,7778. Las nueve filas de parejas sin ventas en TRAIN tienen cero ventas en TEST y ambos obtienen MAE cero. El R² de un grupo con target constante queda sin valor y con motivo explícito, en lugar de presentar un cero como precisión.

El MAE de baja rotación empeora frente a su 0,7612 en VALIDATION, aunque sigue siendo mejor que el baseline de TEST. Siete productos y 26 parejas producto-tienda tienen MAE mayor que el baseline en el bloque final. No se supone que sean exactamente los mismos siete productos examinados antes. Los reportes conservan todos los grupos, incluidos los desfavorables, sin crear excepciones a partir de TEST.

Persisten errores grandes. Hay 18 filas con error absoluto superior a 40 unidades. El percentil 95 es 39,775 y el máximo es 80. Se observaron 8.035 unidades y se predijeron 6.793,15, una diferencia de −15,46 %. El sesgo medio es de −2,464 unidades por fila. Estos resultados mantienen la advertencia sobre subestimación y pedidos extraordinarios. No se modificó la política para corregirlos después de ver TEST y no se recomienda compra automática.

### Ejecución única, evidencia y alcance

Se añadió v2/final_evaluation.py como rutina separada del comparador, que continúa rechazando TEST. Antes del acceso se creó evaluation_started.json bajo el único directorio final_test de este build. La reserva se comparte entre selecciones e identificadores de ejecución. Una repetición se rechaza antes de cargar modelo o datos. Si falla después de reservar, la reserva sigue consumida y no existe un reintento automático. No se debe borrar ese registro para repetir o mejorar el resultado.

La auditoría registra una carga de TEST y una llamada de predicción del modelo aceptado. El baseline se calcula con lag1 sobre esas mismas filas, sin entrenar o evaluar otras candidatas. Hubo cero ajustes de modelos o preprocesadores. Las funciones fit estuvieron bloqueadas durante la ejecución. Los parámetros aprendidos y el archivo del artefacto conservaron sus hashes. Las métricas por mes y grupo pertenecen a ese mismo evento, no a ejecuciones nuevas.

El [resultado final](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/final_test/result.json) conserva métricas, cobertura, grupos, sesgo y limitaciones. predictions.csv conserva las 504 predicciones originales, la salida aplicada, el target y el baseline. selection_frozen.json contiene la selección previa al acceso. evaluation_started.json, prediction_started.json, verification.json y execution_audit.json permiten revisar el orden y los conteos. Las comprobaciones posteriores solo leen esa evidencia guardada o utilizan fixtures temporales. No repiten predicción sobre TEST.

Queda cerrado V2-08 para el experimento académico: comparación, aceptación, artefacto y política fijados, evaluación final única. No equivale a completar la integración comercial de H4/H5. V2-09B sigue pendiente de la revisión de inferencia con Erika. El modelo no se activó en backend o frontend. No se registró una revisión conjunta que no ocurrió.

La evidencia corresponde a otro bloque temporal del mismo generador sintético. No prueba ventas reales, mecanismos nunca vistos o efectos causales de precios y cotizaciones. TEST queda consumido para este experimento. Si más adelante se cambian modelo, variables o política, estos resultados no pueden volver a presentarse como una prueba nueva independiente. Se necesitará otro protocolo y evidencia realmente separada, sin generar nada en esta tarea. Los manifests y contratos históricos mantienen sus estados originales. La selección y la evaluación vigentes se registran por separado en el contrato activo.

Las 15 pruebas de cierre pasaron, sin fallos u omisiones. Siete utilizan fixtures temporales para comprobar autorización y bloqueo de repetición. Ocho verifican hashes, fechas, cobertura, política y métricas desde el resultado guardado, sin cargar nuevamente TEST o predecirlo. El [cierre final](../../ml/demand/reports/v2/2.1.0/expanded-20261115-01/final_test/closure.json) registra estos controles. Los 59 archivos de data, 136 RAW, 14 archivos de modelos, todos los reportes y decisiones anteriores conservaron sus hashes. También permanecieron intactos los 44 archivos protegidos. No hubo ajustes, conexión a Neon, operaciones Git o Markdown nuevos.

## 27. Consistencia de inferencia con el artefacto aceptado, V2-09B

La revisión del 15 de noviembre de 2026 encontró que el endpoint administrativo actual sigue ejecutando admin_prediction.py con V1. No existía una rutina V2 que consultara la selección aceptada. Eso no significa que V1 estuviera usando por error el modelo nuevo. V2-10 es la tarea pendiente para conectar la API. En esta etapa se implementó y comprobó el contrato local de inferencia, sin cambiar backend, frontend, el simulador o los endpoints existentes. No se afirma que Erika haya realizado una revisión personal que no está registrada.

El componente está en [v2/inference.py](../../ml/demand/v2/inference.py). Su contrato formal es inference.v2_1.json, versión v2-inference-2.1-1. Incluye esquemas de solicitud y respuesta, unidades, razones de abstención, origen, disponibilidad y hashes. El código fija el hash de ese contrato y el de la selección aceptada. Verifica el artefacto, las dependencias, los parámetros del bosque y el estado del preprocesamiento antes de inferir. Deserializa los mismos bytes que verificó. Un error de integridad no activa V1 ni carga otro candidato como reemplazo silencioso.

### Entradas, transformaciones y política

El bosque consume exactamente las 14 features aceptadas, en el orden aprendido. El artefacto original valida un transporte de 17 columnas más mes_objetivo. Las tres columnas adicionales son dias_sin_stock_mes_anterior, cobertura_stock_mes_anterior y categoryId. Se conservan para respetar la validación original del objeto congelado, pero no se incorporan a la matriz del bosque elegido. No se rellenan con valores inventados para eludir esa validación. Cambiar el artefacto para quitar esa dependencia sería una modificación posterior, fuera del modelo ya evaluado.

El proveedor local obtiene esas columnas del snapshot aprobado del build 2.1.0, exclusivamente para abril a junio de 2026. El origen es SYNTHETIC y el modo es ACADEMIC_REPLAY. Comprueba hash del CSV, catálogo, informe de calidad, clave producto-tienda-mes, history_snapshot_id y feature_cutoff_at. La evidencia temporal proviene del build previamente auditado. No se inventaron fechas de publicación por columna ni se certificó historia comercial real. Se comprueba además una huella de cada fila y su metadata para detectar cambios en la caché antes de predecir.

| Componente | Regla comprobada |
| --- | --- |
| Cantidades | Unidades enteras no negativas en la historia. Sin convertir IDs en magnitudes |
| Precios y cotización | Precios históricos en bolivianos y cotización en Bs por USD, sin convertir otra vez |
| Proporciones | Fracciones, no porcentajes multiplicados por cien |
| Faltantes | Permanecen desconocidos en origen. Se aplica la mediana y los indicadores ya aprendidos en TRAIN |
| Escalado del bosque | No se aplica StandardScaler ni se calculan nuevas escalas |
| Calendario y corte | Mes válido y corte al inicio del mes objetivo, con zona UTC−4 correspondiente a America/La_Paz |
| Política de salida | NONNEGATIVE_V1. Limitar negativos a cero, rechazar no finitos o forma incorrecta y no redondear |
| Versiones | Selección, artefacto, dataset 2.1.0 y build expanded-20261115-01 identificados en la respuesta |

La solicitud local solo admite contractVersion, productId, locationId, targetMonth e historySnapshotId. Rechaza campos adicionales, incluido target, precios, features, rutas de archivos o selección de otro modelo. No convierte cadenas o booleanos en IDs. El proveedor resuelve la historia aprobada dentro del servidor o proceso de confianza. Este contrato no crea un endpoint público que permita enviar historia arbitraria desde el navegador.

La respuesta identifica origen sintético, modo de reproducción, horizonte de un mes, fecha de emisión, corte histórico, versión de modelo, hash, política y snapshot. Puede devolver OK o ABSTAINED. Una entidad desconocida produce UNKNOWN_ENTITY. Un snapshot incorrecto, un mes fuera del replay o una historia no disponible producen UNAVAILABLE_REQUIRED_FEATURE antes de llamar al modelo. Una salida inválida produce MODEL_UNAVAILABLE, con prediction null. Los errores de entrada e integridad son explícitos. Las respuestas de consola no muestran rutas internas o detalles de excepciones.

evaluationContext muestra las métricas del reporte TEST ya guardado y verificado para ese mismo artefacto. Es contexto de una evaluación pasada, no error conocido de una venta futura o un nuevo cálculo de TEST. Esta rutina no importa el evaluador final ni llama a su loader. Las solicitudes para julio a septiembre se abstienen porque este proveedor solo reproduce VALIDATION. Una fuente real o una consulta futura requiere otra implementación de proveedor en el alcance autorizado, no usar estos datos simulados como historia del negocio.

### Comprobación con el artefacto real

Las 504 respuestas de VALIDATION coinciden exactamente con las 504 predicciones guardadas del bosque absoluto durante la comparación. Se comprobó el caso individual, su identidad y la estabilidad del estado aprendido. La prueba incluye filas con faltantes reales del build, que pasan por los mismos indicadores y medianas de entrenamiento. No se ajustó ningún preprocesador o regresor. Las funciones fit permanecen bloqueadas durante carga y predicción.

También se probaron IDs inválidos, versión V1 en una solicitud V2, campos extra, mes incorrecto, snapshot de otra referencia, JSON con claves repetidas, NaN, infinito y entrada demasiado grande. Se verificó la abstención ante meses TEST o no disponibles antes de la inferencia. Los controles detectan cambios de parámetros, binarios y valores almacenados en caché. Con salidas controladas se verificaron recorte de negativos, ausencia de redondeo y rechazo de valores no finitos, booleanos, complejos o vectores de longitud incorrecta. Esas salidas controladas son fixtures, no resultados del modelo real.

La consola admite una solicitud JSON por entrada estándar. Desde la raíz se verificó este ejemplo real del replay:

```powershell
'{"contractVersion":"v2-inference-2.1-1","productId":1,"locationId":5,"targetMonth":"2026-04","historySnapshotId":"history-v2-883588abb2728fb06df5a197"}' | .\ml\demand\.venv\Scripts\python.exe -B ml/demand/v2/inference.py
```

Ese ejemplo predice cero unidades y devuelve los identificadores fijados. No prueba que siempre deba predecirse cero. La segunda prueba de consola utilizó JSON inválido y verificó el código de error, la salida de proceso y la ausencia de detalles internos.

### Cierre y entrega a V2-10

Se aprobaron 42 pruebas Python y cinco pruebas HTTP del módulo administrativo existente, sin fallos finales u omisiones. Doce pruebas nuevas corresponden al contrato local V2. Las otras comprueban artefactos, resultados congelados, guardas de evaluación y ausencia de regresión V1. Las pruebas HTTP iniciales fallaron por EACCES al conectar con 127.0.0.1 dentro del aislamiento. Las mismas cinco pasaron fuera de esa restricción. No fue necesario modificar el backend o consultar una base de datos. Las dos comprobaciones de consola también pasaron.

V2-09B queda cerrado en su entrega técnica: variables, unidades, columnas, transformaciones, identidad, política y errores comprobados con el artefacto real. La API actual sigue mostrando V1 correctamente identificado como V1. No se declara que el panel ya use V2. V2-10 deberá conectar la nueva rutina, resolver snapshots en backend, aplicar autenticación ADMIN, mapear errores a sus estados HTTP y respetar el origen del dataset. Las cinco pruebas de permisos actuales pertenecen a V1, no certifican permisos de una API V2 que todavía no existe.

No se habilitó LIVE_FORECAST, reposición automática, lectura de Neon, entrenamiento o generación de datos. No se repitió TEST. El resultado final, la reserva de acceso único, la selección y los artefactos anteriores conservan sus hashes. La preparación deja un contrato y una implementación local listos para integrar, sin presentar esa integración futura como terminada.

El [cierre técnico](../../ml/demand/reports/v2/inference/inference-20261115-01/closure.json) y binding.json conservan contratos, hashes, paridad y logs. Permanecieron intactos los 59 archivos de data, 136 RAW, 14 archivos de modelos, los reportes previos, el endpoint V1, candidates, decisions y lifecycle. La selección fijada conserva su hash y la auditoría TEST sigue registrando una sola carga y una sola predicción final. No se ejecutó Git por la restricción de esta sesión.

## 28. API administrativa conectada a V2, V2-10

La API del administrador utiliza ahora la inferencia V2 fijada. Se modificaron exclusivamente el router, el servicio y las pruebas del módulo predictions, con un adaptador Python nuevo, admin_prediction_v2.py. La ruta global existente sigue montada en /api/predictions. No se cambió la arquitectura, los permisos compartidos, Prisma, el simulador o la base operativa. El archivo admin_prediction.py y las referencias V1 se conservaron como evidencia, pero ya no son la ruta de consulta de esta API.

GET /api/predictions/catalog devuelve los 56 productos aprobados, las tiendas 5, 6 y 7, la fecha del catálogo congelado, las versiones y los meses disponibles. POST /api/predictions/demand admite productId y locationId. Para conservar la consulta del panel existente, si no se indica un mes, el servidor utiliza junio de 2026, último mes del replay aprobado. También admite targetMonth y, de forma opcional, historySnapshotId. Un snapshot explícito exige indicar el mes. No se interpreta la consulta como pronóstico del mes actual.

El contrato está en [admin_api.v2_1.json](../../ml/demand/v2/contracts/admin_api.v2_1.json), versión v2-admin-api-2.1-1. La solicitud pública no es la solicitud interna del modelo. El servidor resuelve el snapshot por producto, tienda y mes e incorpora la versión interna ya acordada. Los únicos meses aprobados son abril, mayo y junio de 2026. Un cliente no puede suministrar features, target, rol, precios, ruta de archivo o un modelo alternativo. Tampoco puede usar un snapshot de otra selección. Una consulta para julio a septiembre se rechaza antes de la predicción porque ese proveedor no ofrece TEST.

### Permisos, integridad y errores

Ambas rutas utilizan los middlewares centrales authenticate y authorize con ADMIN, antes de validar la consulta o iniciar Python. No se utiliza RoleRoute como única seguridad. Se verificó que los roles TIENDA e INVENTARIO no pueden consultar catálogo o demanda. Las pruebas con authenticate real rechazan ausencia de token y token inválido antes de consultar el modelo. Otra prueba utiliza claims y lecturas Prisma simulados en memoria para comprobar el rol vigente y la revocación. No se firmaron tokens con secretos reales o consultaron usuarios de Neon.

| Estado HTTP | Situación comprobada |
| --- | --- |
| 401 | Sesión ausente, token inválido o sesión revocada |
| 403 | Rol vigente distinto de ADMIN |
| 400 | IDs, formato o campos inválidos, entidad fuera del catálogo o snapshot sin mes |
| 409 | Snapshot que no corresponde al producto, tienda y mes aprobados |
| 422 | Mes sin snapshot aprobado, incluido un mes de TEST |
| 503 | Artefacto incompatible, inferencia indisponible, fallo del proceso o respuesta inválida |

El servicio ejecuta el intérprete local y admin_prediction_v2.py, con espera máxima de 25 segundos y salida limitada. No devuelve stderr, rutas internas o detalles de excepciones. El resultado debe identificar V2.1.0, el dataset 2.1.0, la selección aceptada, su hash y NONNEGATIVE_V1. Node también comprueba valores finitos, estado OK, identidad de producto y tienda, mes, snapshot, corte UTC−4 y tres meses de historia consecutiva. Una respuesta V1 o un hash distinto se rechaza. No existe fallback automático a V1.

### Respuesta y panel

El adaptador utiliza FrozenDemandInference sin modificar su código verificado en V2-09B. Se mantiene el artefacto con SHA-256 e53cdb53f296b38098639f7dd7d748d5ecd088ea6353993d8d3f911ba32b6dfc y la política de limitar negativos a cero, rechazar valores inválidos y no redondear. No se recalculan transformaciones. El JSON contiene la versión de contrato, selección, modelo, dataset, build, hash, política, corte, origen, modo y advertencias.

Para conservar los campos que consume la pantalla se agregan version, model, baseline, history y metrics. La historia contiene exactamente los tres meses previos extraídos de los lags del mismo snapshot. No incluye la venta observada del mes objetivo ni filas de TEST. Las métricas son las del reporte final guardado y verificado para ese artefacto. No se vuelve a predecir TEST para responder una solicitud ni se presenta MAE como error conocido de esa predicción individual.

La pantalla existente conserva sus controles y gráfico. Se corrigieron los textos que hablaban de V1 o de pronosticar desde septiembre de 2026. Ahora identifica V2 y la reproducción de abril a junio de 2026. Muestra el mes de reproducción predeterminado, la versión devuelta, el resultado y las métricas guardadas. No se añadió un proveedor real, stock actual como historia o compra automática. La interfaz completa y la revisión visual de V2-11 y V2-15 siguen siendo tareas separadas, sin declararlas terminadas por estos cambios de compatibilidad.

### Pruebas y alcance de cierre

La prueba HTTP completa ejecutó Express, Node y Python con el artefacto real, sin BD. Para el producto 20 y tienda 5, la consulta por defecto devuelve junio de 2026, 40,8725 unidades previstas y baseline de 21. La historia incluye marzo, abril y mayo. Consultar explícitamente el snapshot devuelto produce el mismo resultado. Un snapshot incorrecto devuelve 409, un mes de TEST devuelve 422 y una entidad desconocida devuelve 400. Son llamadas de replay, no nuevas evaluaciones del modelo sobre TEST.

Pasaron 40 pruebas Python, diez HTTP del módulo predictions y dos de la pantalla administrativa. Se comprobaron también tipos backend, tipos frontend y build frontend. Las pruebas Python cubren el nuevo adaptador, la inferencia fijada, el legado preservado y la evidencia final sin repetirla. Las HTTP prueban permisos, entrada, snapshots, errores y rechazo de salidas V1, no finitas o con identidad incorrecta. Las de pantalla comprueban origen sintético, llamada, versión, resultado, limpieza al cambiar producto y manejo de errores. No sustituyen la revisión visual pendiente.

El build se guardó bajo tmp en un directorio nuevo, sin desplegar la aplicación. Vite advirtió que el destino estaba fuera de la raíz frontend y no sería vaciado. Es una advertencia esperada por usar un área temporal. No se utilizó la opción de borrar el destino ni se hizo un refactor ajeno para eliminarla.

V2-10 queda cerrado para la API administrativa de replay académico, conectada al artefacto aceptado y a snapshots aprobados. Se puede consultar desde el panel sin entregar variables al cliente para que invente la historia. No se certifica una predicción comercial en vivo o permisos contra registros reales de Neon. La verificación de sesión y revocación de esta tarea utiliza los middlewares reales con lecturas simuladas. No se afirma una revisión personal o despliegue de Erika que no haya ocurrido.

El [cierre de API](../../ml/demand/reports/v2/api/api-v2-20261115-01/closure.json) y binding.json conservan hashes, contrato, logs, permisos y casos HTTP comprobados. Se aprobaron 52 pruebas finales en total. Los 59 archivos de data, 136 RAW, 14 archivos de modelos, todos los reportes y decisiones anteriores conservaron sus hashes. La inferencia V2-09B, la selección aceptada, el legado V1 y la auditoría de TEST permanecieron intactos. No hubo entrenamiento, nueva evaluación TEST, conexión a Neon, migraciones, operaciones Git o Markdown nuevos.

## 29. Pantalla administrativa V2 completa para el replay, V2-11

Se completó PredictionsPage para utilizar el contrato administrativo ya conectado. El alcance sigue siendo una reproducción académica por producto, tienda y mes. No se añadió una fuente comercial, se alteró el modelo o se habilitaron compras. Streamlit continúa separado. El componente conserva la ruta administrativa existente y sus permisos.

### Controles, resultados y advertencias

La pantalla ofrece producto, tienda y mes de reproducción. Los meses proceden del catálogo aprobado de la API, no de un calendario abierto. El horizonte muestra un mes y no se puede editar. La solicitud envía solo productId, locationId y targetMonth. El servidor resuelve el snapshot. No se envían features, precios, cotización, stock o target calculados en el navegador.

Consultar predicción muestra la cantidad prevista y el baseline del mes anterior. Una predicción de cero se presenta como resultado válido. Se identifica RandomForestRegressor, V2.1.0 y el criterio de error absoluto. Los decimales se limitan para lectura, sin cambiar la salida de la API. La pantalla no convierte esa cantidad en una orden de compra o en una reposición recomendada.

El gráfico contiene tres meses cerrados, la predicción del mes objetivo y el baseline como referencia. La última observación conecta visualmente con ambas líneas, pero el mes objetivo no tiene un punto de venta observada. No se inventó una comparación contra un target que la API no entrega. Una tabla desplegable muestra los mismos valores para lectura accesible. Las leyendas distinguen historia simulada, predicción y referencia.

Las tarjetas MAE, RMSE y R² describen la evaluación TEST guardada, no un error conocido de esa consulta. Se explica que R² no es porcentaje de precisión, que no se recalcula TEST y que no existe una banda de confianza validada para dibujar. No se añadieron métricas o intervalos inventados.

El origen sintético permanece visible antes de consultar. Las advertencias recuerdan que no se predice el mes actual, que pueden subestimarse pedidos grandes, que los compromisos mayoristas conocidos no son una feature explícita y que ventas observadas no equivalen a demanda total. No se calcula reposición o modifica inventario. Si la API informa un recorte de salida negativa, se muestra esa condición en lugar de ocultarla.

El detalle Modelo y snapshot de la consulta identifica snapshot, corte de historia, fecha de emisión, selección, dataset, build, hash del artefacto, huella de variables y política. Los tiempos se muestran en America/La_Paz. Los hashes largos se ajustan al ancho de pantalla. No se incluyen credenciales, datos personales o rutas del servidor.

### Coherencia de solicitudes y errores

Se añadió services/demandView.ts para comprobar el catálogo y las respuestas antes de presentarlos. Rechaza un catálogo vacío, duplicado, V1 o con meses fuera del replay. También rechaza resultados de otro producto, tienda o mes, hash ajeno, valores no finitos, predicción negativa sin política aplicada, historia incompleta, corte incorrecto o métricas que no coincidan con su contexto guardado. No se sustituye una respuesta incompatible por un valor de ejemplo.

Cambiar producto, tienda o mes limpia resultados y errores anteriores. La petición pendiente se cancela del lado del cliente. Un identificador de solicitud impide aplicar una respuesta o error tardío aunque el transporte no respete la cancelación. Actualizar referencias invalida la consulta y vuelve a cargar el catálogo. Desmontar el componente cancela las solicitudes y evita actualizar una pantalla que ya no está activa. No se promete que cancelar en el navegador detenga un proceso Python que el servidor ya inició.

Los mensajes distinguen sesión inválida, falta de permisos, selección incorrecta, snapshot desactualizado, ausencia de historia y modelo indisponible. Se puede reintentar la consulta o actualizar referencias, sin mostrar resultados antiguos como si pertenecieran a otra selección. No se muestran directamente excepciones arbitrarias o mensajes técnicos del servidor.

### Pruebas y revisión visual

Pasaron 12 pruebas de interfaz. Cubren controles y mes enviado, horizonte fijo, gráfico y tabla, trazabilidad, cambio de selección, cero, recuperación de catálogo, respuestas incompatibles, errores HTTP, respuestas y errores tardíos, recarga y desmontaje. También pasaron tipos y build frontend. La prueba inicial de texto de zona horaria se ajustó para admitir sus varias apariciones correctas, sin cambiar el comportamiento de la pantalla.

Se verificaron además catálogo y respuesta reales de admin_prediction_v2 para abril de 2026 con el validador del frontend. Son dos controles de compatibilidad del contrato. La inferencia pertenece a VALIDATION y no modifica datos o parámetros. No se repitió TEST, cuyo registro sigue consumido.

La revisión visual usó el componente y Recharts reales con fixtures explícitos, sin backend ni sesión comercial. Se comprobó escritorio a 1280 píxeles y pantalla estrecha a 390. Los controles, cantidades, gráfico, tarjetas y trazabilidad se leen sin desbordamiento horizontal. En 390 píxeles se comprobó scrollWidth igual a clientWidth. Las capturas se identifican como pruebas de interfaz, no como predicciones obtenidas del modelo real. Las líneas del gráfico se verificaron también en su representación SVG después del cambio de tamaño.

La superficie nativa de Windows detectaba interacción del usuario, por lo que no se insistió en escribir en su navegador. Se utilizó una pestaña aislada en segundo plano. El preview temporal necesitó ajustes de rutas Unicode, dependencias y sustitución del cliente API antes de la revisión final. No se modificó la aplicación para adaptarla a un fallo del preview. El servidor temporal se detuvo al terminar. No se instalaron extensiones o herramientas.

V2-11 queda cerrado para esta pantalla de replay académico. La validación global de V2-15, la revisión de otras pantallas y la aceptación conjunta de V2-16 continúan separadas. No se afirma una revisión de la app Expo o una sesión real de Neon. Se conservan las restricciones de V2-10, el artefacto fijado y sus límites comerciales.

## 30. Cuándo ampliar el dataset con las otras fuentes

El dataset 2.1.0 ya existe, fue validado, entrenado y evaluado dentro del alcance académico aprobado. Tiene ventas sintéticas del catálogo y tiendas de referencia. Monash y UCI aportaron referencias de patrones, no ventas trasladadas directamente a Product.id. Este build no es una unión de los cinco archivos externos. La decisión inicial del equipo dejó Automotive, M5 y Favorita fuera de esa primera versión.

La ampliación puede abrirse después de V2-11, con autorización expresa, en paralelo con los pendientes de validación de interfaz si el equipo lo organiza. No es obligatorio esperar a H5. Debe realizarse antes de entrenar una nueva versión, sin reemplazar el dataset o modelo de H4 que ya tiene resultados cerrados. No se construye esa ampliación en esta tarea.

Según la matriz de procedencia y las aprobaciones locales existentes, Automotive mantiene pendiente la licencia de los datos concretos, M5 tiene condiciones no verificadas y Favorita requiere acreditar condiciones de acceso. Tener un archivo descargado no resuelve esas comprobaciones. La siguiente etapa debe revisar la evidencia primaria actual y dejar registrados permisos, atribución, límites y procedencia. No se garantiza que todas las fuentes puedan o deban terminar en el experimento.

El orden recomendado es revisar condiciones de las fuentes pendientes, perfilar solo las aprobadas, actualizar la matriz de compatibilidad, preparar transformaciones reproducibles fuera de RAW, revisar el contrato de variables, calibrar patrones autorizados y publicar un build nuevo. Después corresponderá validar calidad, unidades, disponibilidad temporal, duplicados, escenarios y trazabilidad. El nombre o número de esa versión se decidirá al aprobar su contrato. No se asignó una versión oficial nueva todavía.

M5 y Favorita son comercio general, no autopartes de RepuestoPro. Pueden aportar patrones de precio, calendario, tiendas o promociones cuando se apruebe su uso. Monash aporta series de autopartes y UCI patrones transaccionales con límites de dominio. Automotive requiere identificar qué archivos y datasets concretos son pertinentes. No se mezclarán filas de empresas distintas, monedas o periodicidades solo para aumentar el tamaño, ni se cambiarán sus IDs para presentarlas como ventas reales propias.

Un dataset más completo significa cubrir mejor las variables y escenarios aprobados con fuentes válidas. No significa incluir obligatoriamente cada archivo disponible. Los plazos de proveedor, por ejemplo, necesitan evidencia propia y no aparecen automáticamente por unir ventas externas. Si una fuente no aporta una variable utilizable al corte, no debe fingirse que esa variable quedó respaldada.

Antes de nuevos experimentos se fijarán criterios, split temporal y una prueba verdaderamente separada. TEST de 2.1.0 ya fue observado y no puede reutilizarse como evaluación nueva independiente. Construir o entrenar esa ampliación requiere autorización posterior. En esta tarea no se descargaron, perfilaron, limpiaron o combinaron fuentes y no se modificó ningún dataset.

El [cierre de V2-11](../../ml/demand/reports/v2/ui/ui-v2-20261115-01/closure.json) y review.json conservan pruebas, controles, capturas y hashes. Las capturas de escritorio y pantalla estrecha son fixtures de interfaz, identificados como tales. Los 59 archivos de data, 136 RAW, 14 archivos de modelos, todos los reportes anteriores y el módulo backend conservaron sus hashes. TEST sigue registrando una sola carga y una sola predicción final. No se ejecutó Git ni se creó un Markdown nuevo.

## 31. Revisión de las fuentes pendientes para ampliar V2

El 15 de noviembre de 2026 se retomó la revisión documental de Automotive, M5 y Favorita. El [reporte de continuidad](../../ml/demand/reports/v2/source_reviews/source-review-20261115-01/review.json) reúne las fuentes primarias, las condiciones verificadas y los requisitos pendientes. La matriz del 11 de noviembre se conserva como evidencia histórica. Esta revisión no amplía todavía el alcance de datos aprobado.

| Fuente | Qué quedó comprobado | Qué impide incorporarla ahora |
| --- | --- | --- |
| Automotive | El paquete fable.intermittent contiene Auto, RAF, pasta y tinyM5. El artículo de Türkmen et al. enlaza Auto y RAF. Auto tiene 3000 series de 24 meses según el artículo. | No se encontró un permiso específico de datos para Auto o RAF. LGPL del paquete, la licencia del artículo y la licencia de Monash no acreditan ese permiso. |
| M5 | La página oficial describe ventas de Walmart por producto y tienda, calendario y precios. Su licencia remite a las reglas de la competición. | El texto específico de las reglas no resultó legible. No se habilita por referencias secundarias, por disponibilidad pública o por licencias de notebooks. |
| Favorita | Las reglas 7.A permiten investigación académica y educación después de aceptarlas. Las secciones 7.B y 8.A establecen límites para compartir datos y código. | Falta acreditar el acceso de quienes usarán los archivos. También debe aclararse el alcance de publicar fuera de Kaggle código, parámetros, modelos o datos sintéticos derivados. |

Ross y Erika deben revisar las reglas desde sus cuentas de Kaggle, confirmar el acceso autorizado de cada persona y conservar la evidencia de aceptación sin registrar credenciales. Esto no requiere descargar de nuevo los archivos. Para Auto hace falta una declaración del responsable aplicable a los datos concretos. No se enviaron consultas a terceros ni se aceptaron condiciones en nombre del equipo.

La pasta del paquete tiene una licencia primaria CC BY-NC 3.0, distinta de CC BY 4.0 declarada por su documentación R. Puede ser una referencia no comercial con atribución, pero no es automotriz ni habilita todo Automotive. No se añadió al alcance aprobado. Auto y Monash Car Parts tampoco son el mismo conjunto.

Se corrigió una frase genérica en los tres manifests que podía interpretarse como aprobación de perfilado. Las tres fuentes siguen pendientes. Monash y UCI mantienen la aprobación académica previa. La elegibilidad de una fuente para estudiarla no equivale a permiso para redistribuir sus filas o utilizar sus derivados comercialmente.

Cuando se resuelvan los permisos, el siguiente paso será perfilar solo los subconjuntos autorizados y revisar su compatibilidad. Después se decidirá qué patrones aportan al nuevo contrato. No se unirán todas las filas por tener más archivos. Estas fuentes no acreditan por sí mismas el tipo de cambio boliviano, los plazos de proveedor o un efecto causal del precio en RepuestoPro.

El dataset 2.1.0 y el modelo fijado permanecen cerrados. La ampliación necesita un build nuevo, sin repetir el TEST ya utilizado. Esta revisión no descargó datasets, procesó RAW, generó datos, entrenó modelos o utilizó Neon. No se crearon nuevos Markdown.

## 32. Confirmación de M5 y pendientes de acceso

El 15 de noviembre de 2026 Ross aportó las reglas de M5 Forecasting Accuracy, con actualización declarada del 24 de marzo de 2020. Confirmó que las copió de la página oficial, aceptó sus condiciones y descargó los archivos desde su cuenta. El [registro de confirmación](../../ml/demand/reports/v2/source_reviews/source-access-20261115-02/review.json) conserva la base de esa decisión. Es evidencia declarada por el usuario, sin verificación independiente de su cuenta o de la identidad de los archivos frente al proveedor. La fecha real de descarga sigue desconocida.

M5 pasa de bloqueo por licencia a APPROVED_FOR_PROFILING para un futuro análisis académico no comercial por Ross. La sección B.7.A permite ese propósito. B.7.B limita el acceso y la redistribución. No se afirma aceptación de Erika ni de otras personas. Esta habilitación documental no ejecuta perfilado, no añade datos al dataset ni autoriza entrenar. Monash y UCI siguen como referencias del build 2.1.0, que permanece intacto.

La prohibición de compartir código privado de B.8.A corresponde al periodo de la competición. No se interpreta como una prohibición indefinida. B.8.B contiene condiciones de publicación en Kaggle. La licencia abierta de una entrega ganadora no licencia los datos originales. Antes de distribuir un nuevo dataset sintético, parámetros o artefactos basados en M5 se debe revisar el alcance de esos derivados. No se presume que estén permitidos o prohibidos de forma automática.

Favorita sigue pendiente. Ross debe confirmar por separado si aceptó las reglas de favorita-grocery-sales-forecasting y obtuvo sus archivos desde esa competición de 2017. Su aceptación de M5 no cubre Favorita ni la competición Store Sales de 2021. La revisión primaria mantiene el permiso académico condicionado y las restricciones de acceso y distribución.

La documentación primaria de Auto identifica el conjunto y su origen, pero no resolvió su licencia específica. El siguiente paso es obtener una declaración del responsable sobre el análisis académico, la publicación de derivados, la atribución y posibles tarifas. No se enviaron mensajes a terceros. No se atribuye LGPL del paquete a los datos Auto o RAF.

Las reglas aportadas de M5 y las reglas oficiales consultadas de Favorita no exigen compra para participar o ganar. No se identificó una tarifa por el uso académico descrito. Esto no habilita cualquier uso de los datos. Para Automotive las condiciones económicas siguen sin verificarse. No se contrató ningún servicio de pago. El cómputo o almacenamiento de pago serían servicios separados.

La responsabilidad de Ross sigue siendo frontend y dataset completo, incluidas fuentes, escenarios, preparación, división temporal, validación y reproducción. Erika conserva backend. No se descargaron o procesaron datos, entrenaron modelos, modificaron RAW o utilizaron bases de datos. Se actualizaron metadata, documentación existente y pruebas de procedencia. No se crearon Markdown nuevos.

## 33. Confirmación de Favorita y licencia pendiente de Auto

El 15 de noviembre de 2026 Ross confirmó que aceptó las reglas de Corporación Favorita Grocery Sales Forecasting, competición de 2017, y descargó sus archivos desde su cuenta. El [registro de acceso](../../ml/demand/reports/v2/source_reviews/source-access-20261115-03/review.json) conserva esta confirmación. Se trata de evidencia declarada por Ross, sin consulta a su cuenta, fecha original de descarga o comparación de bytes contra el proveedor.

Favorita queda APPROVED_FOR_PROFILING para un futuro análisis académico no comercial por Ross. Se mantienen las restricciones de acceso y redistribución de la sección 7.B. No se afirma aceptación de Erika o del docente. La publicación externa de derivados y el uso comercial requieren revisar sus condiciones específicas. Esta habilitación no ejecuta perfilado ni incorpora datos al dataset.

Monash, UCI, M5 y Favorita tienen habilitación documental para el alcance académico indicado por sus respectivas condiciones. Solo Monash y UCI forman parte de las referencias del dataset 2.1.0 ya cerrado. No se construyó una ampliación. M5 y Favorita necesitan después perfilado autorizado, compatibilidad y selección de patrones pertinentes. Sus ventas no se convertirán en historia propia de RepuestoPro.

La revisión adicional de la documentación de Auto no encontró una licencia específica de los datos. La documentación identifica 3000 series mensuales y su procedencia, pero eso no acredita permisos. El archivo LICENSE del repositorio de distribución no resultó legible. Tampoco se atribuye LGPL del paquete a Auto o RAF. Ambos siguen pendientes.

El registro incluye una consulta preparada en inglés para el mantenedor de fable.intermittent. Solicita identificar al titular, la licencia de Auto y RAF, el permiso académico local, la publicación de estadísticas, parámetros, código, modelos o datos sintéticos derivados, la atribución y posibles tarifas. Puede enviarse mediante Issues del repositorio oficial. El mantenedor puede remitir al titular, pero una respuesta debe identificar una autorización aplicable a los datos. No se envió ningún mensaje ni se abrió una incidencia.

El pendiente de Auto es independiente de las otras cuatro fuentes. No impide planificar su siguiente revisión de compatibilidad, pero impide utilizar Auto hasta aclarar sus derechos. Esta tarea solo actualizó metadata, documentación existente y pruebas de procedencia. No descargó o procesó datasets, entrenó modelos, modificó RAW, utilizó Neon o creó Markdown nuevos.

## 34. Perfilado de M5 y Favorita para ampliar las referencias

El 15 de noviembre de 2026 se ejecutó el perfilado autorizado de los cinco CSV de M5 y los ocho archivos 7Z de Favorita. Los [reportes descriptivos](../../ml/demand/reports/v2/profiling/profile-retail-20261115-01/) y la [matriz de compatibilidad](../../ml/demand/reports/v2/compatibility/profile-retail-20261115-01/source_compatibility_matrix.json) conservan los resultados. La lectura de 7Z se realizó mediante un flujo de descompresión en memoria por bloques, sin archivos extraídos persistentes, modificaciones de RAW o instalación de herramientas. Las tablas pequeñas se leyeron completas.

M5 contiene 3049 productos, 10 tiendas y 30490 series producto-tienda. El histórico más largo cubre 2011-01-29 a 2016-05-22, con 1941 días. Los primeros 1913 días coinciden exactamente con el otro histórico. Concatenarlos duplicaría observaciones. Se observaron 40241819 ceros de 59181090 valores, sin negativos, fracciones o valores numéricos faltantes. No hubo claves producto-tienda duplicadas. Cero ventas no certifica ausencia de demanda.

La tabla M5 de precios tiene 6841121 registros semanales. No se encontraron claves producto-tienda-semana repetidas, precios cero, negativos o faltantes. Un reporte adicional describe cambios entre precios semanales observados del mismo producto y tienda, sin unirlos con ventas o estimar causalidad. M5 aporta un precio, no dos modalidades comerciales. El calendario llega más lejos que las ventas etiquetadas y las plantillas de envío no son ventas observadas.

Favorita contiene 125497040 líneas históricas entre 2013-01-01 y 2017-08-15. El perfil registra 7795 cantidades negativas, 0 ceros y 8191095 cantidades fraccionarias. La columna de promociones contiene 21657651 faltantes. No se reemplazaron por False. Se revisaron catálogos de tiendas y productos, petróleo, eventos y transacciones. El archivo test externo no contiene unit_sales. Se describe como entrada de la competición, sin usar el TEST cerrado de RepuestoPro. La plantilla de envío tampoco aporta observaciones reales.

Los conteos, sumas, mínimos y máximos se calcularon sobre todos los registros. Los percentiles son aproximaciones de una muestra sistemática cada 997 valores. Esa muestra no se utiliza para entrenar o calibrar, no es aleatoria y puede tener sesgo por el orden. El reporte lo identifica. Para claves se verificó orden dentro de los bloques y entre sus límites. Cuando el orden global no permite certificar duplicados no adyacentes, se informa la comprobación como incompleta en lugar de afirmar ausencia de duplicados.

Ambas fuentes son compatibles como referencias condicionadas de patrones, no como filas históricas propias. M5 puede aportar patrones de precio, calendario y tienda. Favorita puede aportar promociones, calendario y volumen por tienda, con una política previa para devoluciones y unidades fraccionarias. Ninguna acredita stock histórico de RepuestoPro, modalidad mayorista o minorista, costo, cotización Bs/USD o plazos de proveedor. oil no sustituye esas variables. Promociones solo quedan como candidata para un contrato futuro, sin cambiar las features del modelo fijado.

La matriz contrasta las 24 columnas vigentes del diseño 2.1.0, distingue referencias externas de controles propios y mantiene los IDs originales separados de Product.id y Location.id. No se modificó el diccionario, el dataset, la selección del modelo o el TEST consumido. Las reglas de meses completos, disponibilidad al corte y permisos de publicación deben resolverse antes de construir derivados.

Automotive continúa pendiente de licencia y sin perfilado analítico. El siguiente paso es aprobar las reglas de transformación y el alcance de patrones utilizables. Después podrá autorizarse una versión curated y la calibración ampliada. No se construyó un dataset nuevo, entrenó, utilizó Neon o creó Markdown nuevo.

La ejecución completó 32 pruebas de procedencia, estructura y perfilado con fixtures, sin entrenamiento. Los cuantiles de las tablas pequeñas oil y transactions se recalcularon de forma exacta en favorita_small_table_statistics.json, que debe preferirse a las estimaciones por muestra del reporte principal. Se registraron un aviso de tipos mixtos en onpromotion y un aviso de obsolescencia de pandas en la inspección auxiliar de precios. No provocaron pérdida de filas ni escritura sobre RAW. Los recuentos de promociones cubren todas las líneas.

## 35. Reglas de transformación y patrones seleccionados

El 15 de noviembre de 2026 se definió el [contrato de transformación de referencias](../../ml/demand/v2/contracts/retail_transformations.v2.json). Es una especificación para la siguiente etapa de Ross, no una transformación ejecutada. Conserva los snapshots originales, las reglas de calidad, las ventanas de referencia y los criterios de aceptación. No modifica el dataset 2.1.0, sus columnas, la política del modelo o el TEST ya evaluado.

| Fuente | Patrones seleccionados | Límite de interpretación |
| --- | --- | --- |
| M5 | Ceros observados, variación de volumen, diferencias entre tiendas, cambios relativos de precio y variación de calendario | Describen ventas del comercio original. No demuestran falta de stock, demanda perdida, elasticidad o comportamiento boliviano. |
| Favorita | Cola de cantidades positivas registradas, cobertura y frecuencia de promociones conocidas, variabilidad dentro de cohortes de unidades | Se calculan sobre registros existentes. No equivalen a una serie diaria completa, pedidos mayoristas o efecto causal de una promoción. |
| Favorita, solo diagnóstico | Cobertura temporal de registros y contexto de eventos | No trasladar una estacionalidad aparente o feriados ecuatorianos al simulador propio como si estuvieran comprobados. |

M5 utilizará sales_train_evaluation.csv como única tabla histórica. sales_train_validation.csv queda fuera porque repite su prefijo. Las plantillas de envío no son ventas. El enlace con calendar debe ser de varias observaciones a una fecha por clave d, con unicidad comprobada. Los precios se relacionan por producto, tienda y semana, controlando la cantidad de filas para no multiplicar unidades. No se ejecutaron esos enlaces en esta tarea.

La agregación futura de M5 admitirá solo meses calendario completos, con todos los días de la serie presentes. Se conservarán sus ceros explícitos como ventas observadas, sin deducir stock. Enero de 2011 y mayo de 2016 quedan fuera de los patrones mensuales completos. Para cambios de precio se exigirán semanas realmente adyacentes según calendar, ambos precios positivos y la misma clave producto-tienda. Restar códigos de semana o comparar simplemente el siguiente registro no basta. No se rellenarán precios ausentes. Tampoco se copiarán importes nominales USD a Bs o se inventarán dos modalidades a partir de un único precio.

Los archivos externos no certifican cuándo se publicó o recibió cada precio. En una simulación posterior, la disponibilidad del precio se asumirá al cerrar su semana y se identificará como supuesto. Una semana todavía abierta al corte no podrá aportar su precio como dato conocido. Ese criterio no convierte la fecha supuesta en un registro comercial real.

En Favorita se conservarán las cantidades positivas registradas. Los negativos irán a una tabla separada de ajustes o devoluciones no vinculados, con signo y fecha originales. No se usará valor absoluto ni se restarán a la etiqueta bruta del simulador. La suma positiva más la negativa deberá reconciliar el total original, con tolerancia numérica documentada. Una fila positiva tampoco certifica una venta bruta transaccional si la fuente ya contiene agregación.

Las fracciones no se redondearán. Para estudiar conteos enteros se definirán cohortes, es decir, grupos de ítems según la unidad observada durante la ventana de referencia. Un ítem con alguna fracción queda fuera de ese grupo de conteos. Sin historia suficiente su cohorte será desconocida. Una fracción observada después se señalará sin cambiar retroactivamente la clasificación. Los patrones adimensionales de unidades fraccionarias se estudiarán por separado. Ninguna cohorte se convierte en catálogo de repuestos por esa clasificación.

Las fechas producto-tienda ausentes permanecerán desconocidas. No se completará el panel con ceros ni se calculará intermitencia a partir de ausencias de Favorita. Sus resúmenes mensuales describirán cantidades positivas y ajustes registrados, junto con cobertura, sin declararlos targets mensuales completos. Agosto de 2017 queda fuera por ser parcial. test.csv.7z y sample_submission.csv.7z no aportan etiquetas para completar ese mes.

onpromotion conservará tres estados: TRUE, FALSE y UNKNOWN. La frecuencia será TRUE dividido entre promociones conocidas en filas registradas. También se informará la cobertura de valores conocidos. No se llamará porcentaje de días en promoción. Sin fecha verificable de publicación, las promociones del mes objetivo no son features futuras conocidas. Un calendario simulado solo será utilizable si queda fijado antes de su corte. No se calculará automáticamente un efecto causal o descuento porque Favorita no incluye precio unitario del producto.

items y stores permiten comprobar referencias externas mediante relaciones de varias filas a una clave única. No sustituyen Product.id, Location.id o categoryId. Los eventos pueden compartir fecha y tener ámbitos distintos, por lo que no se deduplicarán por fecha ni se unirán multiplicando ventas. transactions permanecerá como diagnóstico tienda-fecha, sin repartirlo a productos o modalidades. oil queda excluido de features y de la calibración inicial. No representa cotización, costo o precio de repuesto.

| Fuente | Ventana para estimar referencias futuras | Ventana de comparación descriptiva |
| --- | --- | --- |
| M5 | Febrero de 2011 a diciembre de 2014 | Enero de 2015 a abril de 2016 |
| Favorita | Enero de 2013 a diciembre de 2015 | Enero de 2016 a julio de 2017 |

Estas ventanas quedan definidas ahora. Los perfiles globales ya se observaron, por lo que la comparación externa no es un test ciego. No es el split de entrenamiento del futuro dataset sintético ni una nueva evaluación de RepuestoPro. Se fijará la receta del simulador antes de crear su nueva ejecución de evaluación. El TEST 2.1.0 no se reutilizará como prueba independiente.

Los conteos y sumas futuros cubrirán todas las filas elegibles. Para fijar parámetros se exigirán cuantiles exactos o una aproximación con error y configuración documentados. La muestra sistemática cada 997 valores del perfil no se utilizará directamente para calibrar. Las estadísticas por fila y por serie se mantendrán separadas. Para resumir parámetros se dará el mismo peso a cada serie dentro de una cohorte, registrando su tamaño. No se mezclarán porcentajes de M5 y Favorita con denominadores distintos.

Las claves duplicadas idénticas podrán reducirse a una observación solo en derivados, registrando multiplicidad y procedencia. Si una clave tiene valores contradictorios, irá a cuarentena sin sumarlos o elegir uno arbitrariamente. Fechas inválidas, referencias inexistentes y valores no finitos también se separarán para revisión. Los extremos válidos se conservarán con indicador de revisión, sin recorte automático. Todas las filas deben reconciliarse entre aceptadas, duplicados y cuarentena. Ningún cambio será silencioso.

Las salidas futuras irán a sources/external_curated por fuente, snapshot y versión de procesamiento. Una ejecución tendrá identidad única, manifiesto, hashes, script, parámetros, reglas y conteos de auditoría. No se sobrescribirán salidas existentes. La autorización académica de Ross no acredita acceso de otras personas ni permite publicar automáticamente datos o derivados. Antes de distribuirlos debe revisarse su alcance.

El tipo de cambio Bs/USD, la disponibilidad histórica, las dos modalidades comerciales, los costos y los plazos de proveedor continúan sin respaldo en estas fuentes. Los supuestos académicos correspondientes deben permanecer identificados o sustituirse por evidencia propia autorizada. Promociones sigue siendo candidata de un contrato futuro, no una nueva feature activa. Automotive continúa pendiente de licencia.

El diseño de reglas queda definido. La siguiente ejecución requiere autorizar la transformación a curated, validar sus salidas y luego fijar la calibración ampliada. No se ejecutó transformación, se construyó un dataset, se entrenó o utilizó Neon. No se crearon Markdown nuevos.

Se comprobaron 22 pruebas de contrato, procedencia y estructura. Los 427 archivos protegidos conservaron sus hashes, incluidos RAW, datos, modelos, reportes anteriores y contratos fijados. No se ejecutó el perfilador o una transformación durante esta definición. La evidencia está en [validation.json](../../ml/demand/reports/v2/transformation_rules/transformation-rules-20261115-01/validation.json). Las razones con denominador cero quedan sin valor calculado. Un perfil anual requiere dos años distintos con observaciones elegibles para cada mes. Las referencias insuficientes no se sustituyen silenciosamente por otra fuente.

## 36. Transformaciones privadas y validación de M5 y Favorita

El 15 de noviembre de 2026 se ejecutó la transformación autorizada hacia external_curated. La [ejecución](../../ml/demand/reports/v2/curation/curate-retail-20261115-01/execution.json) identifica las rutas de ambas fuentes. La [validación independiente](../../ml/demand/reports/v2/curation/curate-retail-20261115-01/validation.json) verifica los archivos, las cantidades, las claves y la cobertura. El estado validado autoriza considerarlas referencias privadas, sin afirmar calibración o aptitud comercial.

Las salidas se guardaron bajo sources/external_curated por fuente, snapshot y processing-1-curate-retail-20261115-01. Cada carpeta contiene manifest.json con hashes de originales y derivados, versión de procesamiento, script, dependencias, reglas y parámetros. audit.json conserva la reconciliación. El estado de escritura de audit.json es anterior a la validación y no se reescribió para aparentar otro momento. La aprobación final está en el reporte independiente. Las notas de los manifests RAW señalan esa evidencia, sin convertir el registro original en una transformación nueva.

M5 produjo 1981850 filas mensuales, de las cuales 1920870 corresponden a meses completos y 60980 a extremos parciales. Se conservaron 59181090 valores diarios originales en sus resúmenes, con suma de 66927173.0 unidades. No se completaron días ausentes ni se duplicó el histórico de validación. Los extremos parciales permanecen identificados y fuera de las ventanas mensuales elegibles.

La tabla de precios conserva 6841121 filas semanales. Se verificaron 6780141 pares elegibles para cambio relativo, exigiendo semanas adyacentes del mismo producto y tienda y calendario completo. Un hueco no produce un cambio calculado. La fecha de disponibilidad es una suposición del simulador al día siguiente del cierre semanal, sin zona horaria o publicación bancaria certificada. Los precios conservan su unidad original y no se convirtieron a Bs o a modalidades comerciales.

Favorita conservó las 125497040 líneas del histórico seleccionado. Se separaron 125489245 positivas, 7795 negativas y 0 de cantidad cero. Las cantidades fraccionarias permanecen sin redondeo y las 21657651 promociones desconocidas mantienen el estado UNKNOWN. La tabla de cero observaciones tiene esquema pero ninguna fila porque el original no contiene esos casos. No representa datos inventados.

El resumen mensual contiene 5813304 combinaciones observadas. Informa cantidades positivas, ajustes negativos, número de registros, días observados y cobertura de promociones. Ningún panel producto-tienda se certifica como completo. No se añadieron combinaciones ausentes. Los catálogos de productos y tiendas, los eventos y las transacciones permanecen en tablas separadas. Se conservaron eventos múltiples en una misma fecha sin unirlos a las ventas. oil, test y la plantilla de envío quedaron fuera de estas salidas analíticas por las reglas acordadas.

Las cohortes de unidades se calcularon solo con la ventana de referencia. Su resultado fue {"OBSERVED_INTEGER": 3172, "UNKNOWN": 643, "OBSERVED_FRACTIONAL": 285}. Un ítem entero observado no se declara repuesto real ni unidad física certificada. Las observaciones posteriores no cambian retroactivamente esa clasificación. Las columnas source_row y source_series_row identifican el ordinal de la fila de datos original, comenzando en uno después de la cabecera.

El validador volvió a leer todos los Parquet y comprobó hashes, esquema de manifest, conteos originales, sumas, signos, fracciones, promociones, cohortes, claves y ventanas. En Favorita usó una marca exacta por fila original para verificar que cada una aparezca una sola vez entre las particiones por signo. El control mensual de M5 utilizó hashes de claves de 64 bits, rechazando también una eventual colisión en lugar de aceptar duplicados. Las sumas de coma flotante se comprobaron con tolerancia relativa 1e-12 y absoluta 0,01.

Las anomalías inesperadas producen detención y un marcador FAILED, sin declarar la carpeta válida. No se publica una salida parcialmente corregida. En esta ejecución no hubo filas inválidas, claves repetidas o conflictos que exigieran cuarentena o eliminación. Se mantiene la regla de no resolver contradicciones silenciosamente. Si aparecieran en otra versión, requerirían una revisión y una salida de cuarentena explícita antes de aprobar esa versión.

Pasaron 41 pruebas locales con fixtures y la validación completa de ambas fuentes. Se conservaron los hashes de 429 archivos protegidos, incluidos RAW, datasets, modelos, reportes anteriores y contratos fijados. No se ejecutaron calibración, generación del dataset final, entrenamiento, inferencia o evaluación TEST. No se utilizó Neon o Git. No se crearon Markdown nuevos.

Automotive sigue pendiente de licencia y no se creó una carpeta procesada para esa fuente. Las condiciones de acceso académico y las restricciones de distribución se mantienen. El próximo paso es revisar las referencias válidas para una calibración ampliada autorizada. El dataset 2.1.0 y su modelo no incorporan automáticamente estas tablas.

## 37. Decisiones vigentes para los cinco riesgos de ampliación

Esta revisión del 15 de noviembre de 2026 confirma las decisiones del contrato retail_transformations.v2.json. No lo modifica porque las salidas privadas del anexo 36 ya registran su hash. Se distingue ese procesamiento externo previo de la construcción de un dataset nuevo de RepuestoPro, que no se realizó. Esta tarea solo revisa las reglas y actualiza documentación, sin ejecutar transformaciones o calibración.

| Riesgo | Decisión vigente | Comprobación requerida |
| --- | --- | --- |
| Prefijo compartido de M5 | Usar sales_train_evaluation.csv como único histórico. Excluir sales_train_validation.csv y sample_submission.csv de cualquier suma de ventas. | Una clave producto-tienda-día por observación. Conservar la comparación del prefijo como evidencia, sin sumar ambas versiones. |
| Ausencias de Favorita | Mantener las combinaciones no registradas como desconocidas. No crear un panel con ceros. | Informar filas y días observados. No estimar frecuencia de ventas cero, intermitencia o falta de stock mediante ausencias. |
| Negativos y fracciones | Separar positivos y ajustes negativos con su signo. Conservar decimales. Congelar cohortes de unidad observada usando solo la ventana de referencia. | Reconciliar la suma original. No usar abs(), redondear, recortar negativos o crear correspondencias con ventas anteriores. |
| Variables sin fuente | Usar supuestos académicos identificados para cotización, stock y modalidades si el nuevo diseño los mantiene. Mantener costos y plazos sin respaldo fuera de la estimación externa. | Cada parámetro debe declarar fuente o supuesto, unidad, momento de disponibilidad y versión. No llamar dato real a un valor simulado. |
| Dominios distintos | Conservar las identidades externas y estudiar patrones por fuente. El simulador propio usará su catálogo congelado, sin reasignar filas externas a Product.id o Location.id. | Ningún cambio de ID debe convertir ventas de otra empresa en historia RepuestoPro. Separar monedas, unidades, geografía y población. |

Un ejemplo de ausencia es una fecha sin fila para un producto de Favorita. Su cantidad seguirá sin conocerse. Un registro de -2 permanecerá como ajuste negativo no vinculado. Una cantidad de 1,5 conservará su unidad externa y no se convertirá en dos repuestos. Una fila positiva tampoco acredita venta bruta transaccional cuando la fuente ya está agregada. Estas reglas resuelven el tratamiento, no recuperan hechos comerciales que los archivos no contienen.

Los patrones elegidos de M5 son ceros explícitos, variación mensual de volumen, diferencias entre tiendas, cambios relativos de precio y variación de calendario. Los de Favorita son la cola de cantidades positivas registradas, su variabilidad y la frecuencia de promociones entre filas con valor conocido. El contexto de eventos de Favorita es solo diagnóstico. No se estimará una probabilidad de mayorista a partir de cantidades grandes, elasticidad a partir de correlaciones o demanda perdida a partir de ceros.

La referencia mensual de M5 utiliza febrero de 2011 a abril de 2016, con todos los días esperados por serie. Enero de 2011 y mayo de 2016 son parciales. Para estimar patrones se reserva febrero de 2011 a diciembre de 2014. Enero de 2015 a abril de 2016 sirve para comparación descriptiva. Favorita utiliza enero de 2013 a julio de 2017 como meses calendario completos, sin afirmar cobertura completa por producto-tienda. Su referencia es enero de 2013 a diciembre de 2015 y su comparación, enero de 2016 a julio de 2017. Agosto de 2017 no se completa con test, plantillas o extrapolaciones. Estas ventanas externas ya se han observado y no constituyen una evaluación ciega.

Los cambios de precio M5 solo son elegibles entre semanas realmente adyacentes, según calendar, con precios positivos de la misma serie. No se rellenan huecos. Un precio de 120 a 150 supone un cambio relativo del 25 %, pero ese cálculo no demuestra cuánto variarán las ventas. Tampoco identifica un precio minorista o mayorista. El uso futuro de un precio como conocido al cerrar su semana será un supuesto de disponibilidad, no una fecha de publicación certificada. Una semana abierta al corte no aporta su precio como información conocida.

Las promociones de Favorita mantienen TRUE, FALSE y UNKNOWN. Su frecuencia es TRUE entre valores conocidos, acompañada por la cobertura de esos valores. No equivale a porcentaje de días promocionados. Las promociones del mes objetivo no se consideran conocidas sin una programación previa al corte. Introducirlas como nueva feature requiere otro contrato. oil queda fuera porque no es precio de repuesto ni cotización. transactions permanece como contexto de tienda, sin repartirlo a productos o modalidades.

La cotización Bs/USD, su antigüedad, las variaciones monetarias, los días sin stock y las proporciones comerciales no se medirán con M5 o Favorita. Si se mantienen en la siguiente simulación, su manifest debe identificarlas como SUPUESTO_ACADEMICO, con parámetros fijados antes de generar datos y sin atribuirles respaldo externo. No se fijan nuevos números en esta tarea. Los precios por menor y por mayor seguirán siendo dos decisiones propias. La regla precioMayor <= precioMenor y la relación con costos, cuando existan, son reglas del dominio, no resultados de M5. Los plazos de proveedor y reposición continúan separados del target de ventas y del alcance comercial de H5.

Los patrones se resumirán por serie y cohorte, con denominadores explícitos y peso igual por serie dentro de cada cohorte. No se mezclarán porcentajes de poblaciones distintas. Un denominador cero, una historia insuficiente o un cambio a través de un hueco no produce un parámetro inventado. Se conserva un resultado sin estimación y su motivo. Las estimaciones sistemáticas del perfil cada 997 valores no fijarán parámetros de calibración. Se exigirán cuantiles exactos o aproximaciones con error y configuración documentados.

El contrato existente ya distingue referencias, supuestos y variables excluidas. No se cambiaron las 24 columnas del diseño 2.1.0, las 14 entradas del artefacto fijado o el target target_ventas_mes. Este target sigue representando unidades brutas observadas del mes objetivo dentro del mundo sintético propio. No representa demanda total o ventas externas transformadas en repuestos. Automotive permanece pendiente de licencia. La publicación de derivados requiere revisar sus condiciones de uso.

La siguiente etapa de Ross será revisar qué referencias procesadas cumplen estos requisitos y, con autorización, fijar la calibración ampliada. Después corresponderán otro build reproducible, su validación y un experimento independiente. No se repite TEST 2.1.0 ni se declara completo un nuevo dataset antes de construirlo. Esta revisión no desarrolla backend, modifica RAW o Neon, construye datos o entrena modelos.

## 38. Calibración ampliada de referencias M5 y Favorita

El 15 de noviembre de 2026 se revisaron los manifests, snapshots, hashes y la validación de las referencias privadas procesadas. La [configuración ampliada](../../ml/demand/reports/v2/calibration/calibration-retail-20261115-03/calibration.json) conserva parámetros, fuentes, método, límites y hash del código. Los reportes m5_reference_statistics.json y favorita_reference_statistics.json contienen las estadísticas por ventana. Esta configuración no modifica la calibración base, el generador, el dataset 2.1.0 o el modelo fijado.

La estimación utiliza solo REFERENCE. M5 cubre febrero de 2011 a diciembre de 2014, 47 meses completos. Favorita cubre enero de 2013 a diciembre de 2015. Las ventanas DESCRIPTIVE_COMPARISON se calcularon por separado. Ya habían sido observadas globalmente y no son un test independiente. No se utilizaron para elegir o ajustar los parámetros.

| Referencia o parámetro | Resultado | Uso autorizado de la configuración |
| --- | --- | --- |
| Cambio semanal de precio | Frecuencia media entre series: 1.2048 % por semana elegible | Escenario representativo de cambios, con mecanismo temporal identificado como supuesto. No probabilidad mensual ni estimación boliviana. |
| Magnitud típica de cambio | Mediana entre series que cambiaron: 8.5930 % | Cambio relativo de referencia. No respuesta causal de ventas. Una bajada debe ser menor que 100 %. |
| Dirección del cambio | Participación media de subidas entre series con cambios: 58.6963 % | Mezcla representativa de signos. No reconstruye una distribución conjunta de precios y ventas. |
| Cola positiva de Favorita | Mediana entre series de p95/mediana: 2.8000. Para p99/mediana: 4.0000 | Escenarios de picos condicionados a registros positivos de la cohorte entera. No identifica pedidos mayoristas. |

Los ceros mensuales, la variabilidad, las diferencias de tienda y el calendario de M5 se conservan como rangos de referencia y sensibilidad. No se promedian con Monash o UCI ni sustituyen la base automotriz. Cada producto-tienda tiene el mismo peso dentro de su cohorte. Los valores monetarios nominales, IDs y eventos extranjeros no se trasladan a RepuestoPro.

Se recorrieron 125489245 observaciones positivas de Favorita. Se mantuvieron 66454992 en referencia y 53787100 en comparación para las cohortes conocidas. Se separaron 1570850 fuera de ventana y 3676303 de cohorte desconocida. La reconciliación conserva todas las observaciones. Se excluyeron de los patrones enteros las fracciones posteriores cuando correspondía, sin cambiar retroactivamente las cohortes.

La cohorte entera de referencia contiene 131551 series positivas. Las series con una sola observación permanecen identificadas, pero no aportan CV porque no permiten estimar variabilidad. Los cuantiles se calcularon exactamente con todos los valores elegibles de cada serie y luego se resumieron con igual peso por serie. No se utilizó la muestra sistemática de los perfiles para fijar parámetros. Las particiones binarias auxiliares permanecen privadas bajo tmp, sin escribir RAW o nuevas tablas de entrenamiento.

La cobertura media de promociones conocidas de esa cohorte pasa de 77.63 % en referencia a 100.00 % en comparación. Es un cambio de cobertura, no prueba de un cambio causal de comportamiento. La frecuencia condicionada a registros conocidos no se transforma en probabilidad diaria de promoción. Un calendario simulado requerirá un supuesto explícito conocido antes del corte.

La amplitud de calendario M5 es una medida de diferencias entre meses. Puede superar uno y no debe copiarse como coeficiente de una onda sinusoidal que produzca ventas negativas. Su fase y los meses de mayor demanda en Bolivia siguen sin estar identificados. La ventana de comparación M5 no tiene dos años para cada uno de los doce meses, por lo que su perfil anual se informa como insuficiente. Los rangos entre series son cuantiles empíricos, no intervalos de confianza o límites comerciales garantizados.

La elasticidad del precio, la cotización Bs/USD, el stock, las modalidades de venta, los costos y los plazos de proveedor no se estiman con estas fuentes. Permanecen como supuestos académicos versionados o pendientes de evidencia propia. Los plazos de proveedor siguen separados de la predicción de ventas. Automotive continúa pendiente de licencia. Se mantienen las restricciones de acceso y publicación de derivados.

La primera ejecución se detuvo por una diferencia entre la etiqueta esperada de comparación y DESCRIPTIVE_COMPARISON. Se corrigió el lector y se añadió una prueba. La agregación preliminar se conserva como reemplazada. La ejecución vigente recalculó los resúmenes excluyendo series de una observación del CV, reutilizando las mismas particiones temporales con comprobación de hashes. No se sobrescribió evidencia ni se cambió un dato de las fuentes.

La calibración ampliada queda calculada como configuración de referencias académicas, sin activarla en el simulador. El siguiente paso, con autorización, será implementar su consumo en un generador versionado, comprobar disponibilidad temporal, unidades, signos y restricciones económicas. Después podrá generarse y validarse otro build. En esta tarea no se construyó un dataset nuevo, se entrenó, repitió TEST, modificó RAW o Neon, ni se creó Markdown nuevo.

La verificación final aprobó 58 pruebas, incluidas ocho nuevas. De los 472 archivos registrados al inicio, 471 conservaron sus hashes y solo preparation.v2.json cambió como metadata activa autorizada. RAW, curated, datasets, modelos y reportes anteriores permanecieron intactos. La configuración aceptada y sus comprobaciones están en validation.json del run calibration-retail-20261115-03. No se utilizó Git.

## 39. Generador versionado con calibración ampliada

Se implementó retail-reference-generator-1.0.0 en [generate_calibrated.py](../../ml/demand/v2/generate_calibrated.py), con mecanismos en [retail_mechanisms.py](../../ml/demand/v2/retail_mechanisms.py). La [receta fijada](../../ml/demand/v2/contracts/generator.retail_extension.v1.json) registra la calibración aceptada, las dependencias y sus hashes. Conserva dataset_version sin asignar, publicación deshabilitada y entrenamiento no autorizado. No cambia generate_expanded.py ni los generadores anteriores.

La nueva función de simulación deriva el flujo físico de la versión 2.1.0 porque ese motor tiene precios y demanda definidos dentro de su función, sin puntos de extensión. Se conservó el original como evidencia. La versión separada reutiliza funciones de calendario, abastecimiento, cotizaciones y hashes. Los cambios del motor quedan limitados a los mecanismos de referencia y su auditoría. No se copió su publicador. La función build de la nueva versión rechaza la ejecución antes de crear carpetas o archivos.

Los cambios de precio se sortean por semana con seed 42 y claves independientes por producto, tienda y semana. Solo se incorporan después del cierre de la semana simulada. La facturación conserva una revisión mensual de precios, usando los eventos disponibles al inicio del mes. Este mecanismo es académico, no una independencia temporal medida en M5. Las dos modalidades conservan su relación de precios propia. Una trayectoria que incumpla costo <= POR MAYOR <= POR MENOR se detiene con PRICE_RULE. No se ajusta el precio, el costo o el margen silenciosamente.

Los factores de tienda utilizan los percentiles p10, p50 y p90 de la referencia, repartidos como escenarios entre las tiendas propias y normalizados a media uno. No describen sucursales reales ni trasladan IDs externos. El calendario usa beta = log1p de la amplitud de referencia y un factor exponencial normalizado sobre doce meses. Así permanece positivo incluso cuando la medida original supera uno. La fase es un supuesto explícito. No se copiaron feriados, meses pico bolivianos o una curva medida de elasticidad.

Los picos de Favorita se aplican como multiplicadores 2,8 y 4 sobre conteos sintéticos minoristas propios. El ciclo NONE, NONE, P95, NONE, P99, NONE busca cobertura de escenarios, sin afirmar una frecuencia comercial. El redondeo corresponde al conteo propio generado, no a cantidades externas. Un pico no cambia POR MENOR a POR MAYOR. La auditoría distingue caso asignado, pedido realmente creado y pico aplicado. Los conteos observados de esa auditoría solo se declaran disponibles al cierre del mes, no como features conocidas al inicio.

Monash conserva el mecanismo base de intermitencia. Las cantidades mayoristas, cotización, costo y recepción continúan como supuestos académicos heredados. La variabilidad y los ceros M5 son referencias de contraste, sin convertirlos automáticamente en otra distribución de ruido o falta de stock. Las promociones permanecen como diagnóstico. No se inventó un efecto causal del precio sobre la demanda. Tampoco se añadieron features a las 24 columnas del diseño o a las 14 entradas del modelo fijado.

Se aprobaron 74 pruebas locales, incluidas 16 nuevas. Se comprobaron cierre semanal, determinismo, ausencia de reescritura del pasado, factores positivos, precios y costos, picos minoristas, lags, target atendido, stock, tránsito, recepciones parciales y pedidos no atendidos. Las pruebas del motor usan un producto y una tienda durante cuatro o cinco meses en memoria. No ejecutaron el catálogo completo, escribieron CSV o publicaron un dataset. La [verificación](../../ml/demand/reports/v2/generator/generator-retail-20261115-01/validation.json) conserva alcance y hashes.

La implementación está preparada para la siguiente etapa, pero no certifica todavía la cobertura o las distribuciones de un build completo. La futura ejecución deberá comprobar todas las trayectorias de precios, restricciones económicas, cobertura de escenarios y disponibilidad temporal. También requiere asignar la versión del dataset y fijar una realización de evaluación independiente. No se reutiliza el TEST 2.1.0. No se generó un build, entrenó, modificó RAW o Neon, ejecutó Git o creó Markdown nuevo. Automotive sigue pendiente de licencia.

## 40. Dataset 2.2.0 construido, validado y publicado localmente

El 15 de noviembre de 2026 se asignó la versión 2.2.0 para distinguir la ampliación de referencias y mecanismos del dataset 2.1.0. Las 24 columnas supervisadas conservan su significado. Cambian la receta de simulación y su trazabilidad, no la unidad producto-tienda-mes o el target de ventas brutas observadas. No se mezclaron filas de empresas externas. La ampliación aporta mecanismos y escenarios, no millones de ventas ajenas al catálogo propio.

El build [calibrated-20261115-01](../../ml/demand/data/repuestopro_v2/2.2.0/calibrated-20261115-01/manifest.json) utiliza los 56 productos incluidos y las tres tiendas del catálogo congelado. Su fecha de observación es 28 de octubre de 2026. No se consultó Neon para actualizarlo en esta tarea. El origen de las ventas es SINTÉTICO. Monash, UCI, M5 y Favorita son referencias de patrones con las condiciones registradas. Automotive no participa porque su licencia sigue pendiente.

| Conjunto o tabla | Periodo o alcance | Filas |
| --- | --- | --- |
| Base mensual | Octubre de 2024 a septiembre de 2026 | 4.032 |
| Dataset supervisado | Enero de 2025 a septiembre de 2026 | 3.528 |
| TRAIN | Enero de 2025 a marzo de 2026 | 2.520 |
| VALIDATION | Abril a junio de 2026 | 504 |
| TEST | Julio a septiembre de 2026 | 504 |
| Stock diario | 168 series durante 730 días | 122.640 |

La primera corrida completa con el generador 1.0.0 se detuvo porque una trayectoria propuesta dejó el precio por mayor debajo del costo. No se publicó una salida fallida ni se cambiaron los parámetros para favorecer resultados predictivos. El generador 1.0.0 y su receta se conservaron. La revisión retail-reference-generator-1.1.0 incorpora una política administrativa sintética explícita para ese caso, sin cambiar los streams físicos o los parámetros M5.

La propuesta mensual parte del precio aplicado anterior, los cambios relativos de referencia y el factor económico académico conocido al corte. Si incumple la regla de costo, se rechaza esa propuesta y se registra una revisión administrativa disponible en ese corte. El costo no se modifica. Los nuevos precios utilizan los multiplicadores iniciales del escenario: precio por menor = costo por 1,5 y precio por mayor = costo por 1,35. El siguiente mes parte de los precios realmente aplicados. Estos multiplicadores no son estimaciones de M5 ni decisiones sobre precios productivos.

pricing_audit.csv conserva 4.200 cortes de precio, incluidos los planes para el mes siguiente. Registra la propuesta, el costo, los importes aplicados, el motivo y si hubo intervención. En este build hubo seis revisiones administrativas simuladas, separadas de las 207 propuestas semanales de referencia. Ninguna corrección fue silenciosa. La revisión económica de un precio propuesto no se presenta como un evento empírico M5 o una elasticidad estimada.

La [validación del build](../../ml/demand/data/repuestopro_v2/2.2.0/calibrated-20261115-01/validation.json) aprobó cantidades, target atendido, modalidades, precios, lags, cotizaciones conocidas al corte, stock diario, tránsito, recepción, pedidos no atendidos, picos minoristas y snapshots. El costo de un plan se comprueba en el corte de ese plan, con su propio costo conocido, no con el costo del mes anterior. Las comprobaciones previas se conservaron en una versión independiente del validador, sin modificar las reglas de los datasets históricos.

El generador se ejecutó dos veces para contrastar el contenido completo. Después se escribieron los archivos en tmp. Se releyeron tablas tipadas y todos los CSV, se repitió la validación sin ejecutar el generador y se comprobaron los hashes. Solo entonces se renombró la carpeta al destino final, sin sobrescribir un build existente. Una comprobación posterior confirmó los 29 archivos inventariados, además del propio checksums.sha256.

Se conservaron base_mensual.csv, dataset_supervisado.csv, escenarios_metadatos.csv, manifest.json, schema.json, split_manifest.json, validation.json y checksums.sha256. También se incluyen controles físicos, auditorías de calibración y precios, tablas tipadas para verificación, la receta, el catálogo y copias de los componentes de generación. Los controles latentes y administrativos no son features. El hash del manifest es 1147c89cc832d35fc1a29dfe65478ff118eb079a30237ee1c07aef5ca4118a5e.

Pasaron 83 pruebas: nueve nuevas de publicación y corrupción controlada, junto con las 74 anteriores del alcance. Se comprobó que no se publica si falla la validación, no se sobrescribe un destino existente y los checksums detectan cambios o archivos no inventariados. Los avisos de pesos académicos, trayectoria económica compartida y ventas limitadas por stock permanecen documentados. El build no demuestra precisión comercial ni cobertura dinámica de todos los escenarios posibles.

La publicación es local y privada bajo data/repuestopro_v2/2.2.0, sin distribución pública, commit o push. La validación incluye integridad de filas TEST, pero no métricas predictivas, selección de modelos o entrenamiento. El TEST de 2.1.0 no se volvió a evaluar. El administrador continúa utilizando su artefacto 2.1.0 fijado. No existe un modelo 2.2.0 y el nuevo dataset no lo sustituye automáticamente.

La siguiente etapa requiere autorizar la preparación del experimento para 2.2.0 y su entrenamiento con TRAIN y VALIDATION, manteniendo TEST separado. No se modificaron RAW, curated, Neon, Prisma, modelos o datasets anteriores. No se crearon Markdown nuevos.

## 41. Preparación de experimentos 2.2.0, sin entrenamiento

Al cierre de esta etapa se preparó V2-08 para el dataset 2.2.0. El entrenamiento posterior está registrado en el anexo 42. La construcción y validación del build ya terminaron. Todavía no se compararon modelos, seleccionó un ganador o entrenó un artefacto 2.2.0. El [plan de ejecución preparado](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/preparation/prepare-2.2-20261115-01/run_plan.json) registra esta separación.

Se añadieron data_v2_2.py, preprocessing_v2_2.py y experiments_v2_2.py, con contratos propios. No se modificaron los módulos 2.1.0 utilizados por el modelo fijado. Se reutilizan sus validaciones y transformaciones puras, con hashes comprobados, pero el contexto, las rutas y el estado serializado del adaptador son de 2.2.0. Un estado 2.1.0 no se acepta como estado del nuevo adaptador.

El cargador rechaza TEST antes de abrir el contexto o los datos. Para TRAIN lee exactamente 2.520 filas supervisadas. Para VALIDATION solo recorre el prefijo de 3.024 filas que termina en junio de 2026. No solicita la siguiente fila. La base mensual se lee únicamente hasta el mes permitido, incluyendo el histórico necesario de los lags. Se consultan las fechas, cantidades declaradas y hashes del split como metadata. Los hashes de bytes cubren el archivo congelado completo por integridad, sin interpretar las filas, features o targets de TEST.

Los targets TRAIN y VALIDATION se alinean por productId, locationId y mes_objetivo. Se contrastan con unidades_vendidas_brutas de la base mensual. Los tres lags se comprueban con meses anteriores cerrados y snapshots. La fecha de corte debe coincidir con el inicio del mes objetivo. Se rechazan identidades duplicadas, targets faltantes, negativos, fraccionarios o desalineados. Los IDs permanecen en el índice de filas, fuera de la matriz numérica.

| Conjunto | Entrenamiento permitido en el futuro | Validación |
| --- | --- | --- |
| Principal | Enero de 2025 a marzo de 2026, 2.520 filas | Abril a junio de 2026, 504 filas |
| F1 dentro de TRAIN | Enero a junio de 2025, 1.008 filas | Julio a septiembre de 2025, 504 filas |
| F2 dentro de TRAIN | Enero a septiembre de 2025, 1.512 filas | Octubre a diciembre de 2025, 504 filas |
| F3 dentro de TRAIN | Enero a diciembre de 2025, 2.016 filas | Enero a marzo de 2026, 504 filas |

Cada mes conserva todos los productos y tiendas. No hay split aleatorio. TEST mantiene julio a septiembre de 2026, con 504 filas declaradas, sin cargarse en esta etapa. Ningún fold interno sale de TRAIN. Las revisiones de columnas encontraron variación en las 17 features de cada ventana TRAIN, sin columnas totalmente vacías o constantes que exigieran eliminación. Los resultados están en feature_review.json junto al plan preparado.

El preprocesamiento futuro usa medianas TRAIN con indicadores fijos de faltantes, categoryId como categoría y una salida UNKNOWN para valores nuevos. LinearRegression utilizará StandardScaler solo en columnas numéricas. RandomForest no utilizará escalado. Cada fold necesitará una instancia nueva. El mes es contexto, no feature adicional. Targets, IDs, snapshots y controles administrativos quedan fuera de X. El ajuste sobre el dataset real está bloqueado durante esta preparación.

Se prepararon seis grupos de 5, 7, 11, 14, 16 y 17 features. El baseline será ventas del mes anterior. Se compararán LinearRegression y RandomForest con squared_error y absolute_error, sin heredar el ganador de 2.1.0. Hay 54 candidatos entrenables. Los tres folds requieren 162 ajustes futuros. Los doce reajustes principales suman un máximo de 174. Son un presupuesto, no ajustes ejecutados. MLP sigue fuera de la comparación inicial.

La preparación real se ejecutó con bloqueos que habrían detenido cualquier llamada a fit de regresores, del adaptador o de StandardScaler. Registró cero ajustes reales, predicciones o métricas predictivas. Las pruebas de escalado usaron únicamente fixtures artificiales marcados, sin guardar artefactos. Pasaron 35 pruebas del alcance, incluidas 13 nuevas. Cubren lectura acotada, bloqueo de TEST, alineación, lags, folds, constantes, faltantes, escalado, UNKNOWN y estados de otra versión.

No se añadió ninguna fila a experiments.csv ni se creó un modelo. Ese registro solo recibirá resultados de experimentos realmente autorizados. La ejecución de entrenamiento se rechaza antes de cargar datos o crear rutas. La siguiente etapa requiere autorización y una habilitación versionada para entrenar con TRAIN, comparar con VALIDATION y conservar TEST separado hasta una selección final. El administrador continúa usando 2.1.0. No se modificaron datasets, RAW, curated, Neon o modelos, ni se crearon Markdown nuevos.

## 42. Entrenamiento 2.2.0 con TRAIN y comparación en VALIDATION

El 15 de noviembre de 2026 se ejecutó train-2.2-20261115-01 mediante autorización expresa. Se utilizó el build congelado calibrated-20261115-01. Los anexos 40 y 41 conservan la publicación y preparación anteriores. Su descripción de ausencia de modelos corresponde a esas etapas, no al estado posterior a esta ejecución. La habilitación utiliza un contrato, adaptador y ejecutor nuevos. Los componentes preparados y los de 2.1.0 se conservaron.

Se entrenó con enero de 2025 a marzo de 2026, 2.520 filas. VALIDATION conserva abril a junio de 2026, 504 filas. Los tres folds internos usan únicamente meses de TRAIN. Se compararon seis conjuntos de variables. Cada uno incluyó LinearRegression y ocho configuraciones de RandomForest. Los 54 candidatos necesitaron 162 ajustes internos. Después se reajustaron doce finalistas sobre todo TRAIN, elegidos por modelo y conjunto de variables mediante el MAE interno. El baseline no requiere ajuste. Hubo 174 ajustes, cero candidatos fallidos y aproximadamente 237 segundos de ejecución. No se cargaron features o targets de TEST.

Cada ajuste tuvo su propio preprocesamiento. Las medianas, categorías y escalado de LinearRegression se aprendieron solo con el TRAIN correspondiente. RandomForest no utilizó escalado numérico. Se compararon las predicciones continuas con mínimo cero, sin redondear. También se conservaron predicciones originales y errores. La mejor regresión lineal produjo 16 predicciones originales negativas en VALIDATION, corregidas por esa política declarada. El bosque y el baseline no produjeron negativas.

| Opción con menor MAE de su familia en VALIDATION | Features | MAE TRAIN, diagnóstico | MAE VALIDATION | RMSE VALIDATION | R² VALIDATION |
| --- | --- | --- | --- | --- | --- |
| Baseline, último mes | Última venta mensual | 11,8937 | 12,7480 | 23,4697 | 0,3310 |
| LinearRegression | 14, hasta cotización | 10,3596 | 10,7059 | 17,3132 | 0,6359 |
| RandomForest, error absoluto | 5, tres lags y calendario | 8,6986 | 9,7604 | 17,1857 | 0,6413 |

La mejor candidata por MAE es candidate-2.2-1202b43393aac05173a4f603. Utiliza 200 árboles, profundidad máxima 4, mínimo de cinco observaciones por hoja y seed 42. Reduce el MAE del baseline un 23,44 %. El bosque con modalidad tiene MAE 9,7956 y RMSE 17,1057. Su RMSE es algo menor, pero su MAE no mejora al candidato principal. El bosque con las 17 features obtiene MAE 9,9902. Añadir variables no garantizó una mejora en esta realización sintética. Estos resultados no demuestran que precio, cotización o stock sean irrelevantes para una tienda real, ni estiman efectos causales de esas variables.

La selección queda en REVIEW_REQUIRED. Trece de los 56 productos y 36 de las 168 combinaciones producto-tienda empeoran su MAE frente al baseline. Estos grupos se solapan, no representan 49 productos diferentes. Las tres tiendas mejoran al agruparse. También mejoran los grupos de rotación definidos únicamente con TRAIN. En baja rotación el MAE baja de 1,5417 a 0,9560, pero esa media no elimina los casos particulares desfavorables.

| Producto con mayor deterioro | MAE baseline | MAE candidata | Diferencia |
| --- | --- | --- | --- |
| 41 | 10,0000 | 20,3192 | +10,3192 |
| 54 | 8,6667 | 15,7431 | +7,0764 |
| 28 | 4,6667 | 9,4258 | +4,7592 |
| 25 | 8,4444 | 12,7600 | +4,3156 |
| 32 | 8,1111 | 11,8725 | +3,7614 |

Cada producto tiene solo nueve observaciones de VALIDATION. Antes de cerrar la selección corresponde revisar sus trayectorias, picos, disponibilidad y errores firmados. No se atribuye todavía una causa a esos errores. Si se comparan nuevas alternativas, deben registrarse antes de ejecutarlas y utilizar TRAIN/VALIDATION. TEST seguirá separado hasta aceptar y fijar una política final. No se debe elegir retrospectivamente un modelo distinto para cada producto usando estos nueve resultados como si fueran una regla validada.

Los [resultados completos](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/runs/train-2.2-20261115-01/comparison.json) conservan las configuraciones, métricas y grupos. El [registro de experimentos](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/experiments.csv) contiene 175 entradas reales, incluidos 162 ajustes internos, doce finalistas y el baseline. Los doce pipelines y sus estados se guardaron en models/v2/train-2.2-20261115-01. Se recargaron todos, se verificaron sus hashes, ventana de ajuste y 504 predicciones de VALIDATION por artefacto. Coincidieron con las predicciones registradas con tolerancia absoluta de 1e-12. La [verificación](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/runs/train-2.2-20261115-01/verification.json) registra esta comprobación sin ajustes adicionales.

Pasaron 40 pruebas estructurales, de procedencia, transformación, preparación y entrenamiento, incluidas cinco nuevas. TEST 2.2.0 no se interpretó o evaluó. No se repitió TEST 2.1.0. El administrador y la API siguen usando el artefacto 2.1.0 fijado. No se promueve automáticamente la candidata 2.2.0. La evidencia sigue siendo académica y sintética, sin certificación de precisión comercial.

**Estado de Ross para el alcance actualizado 2.2.0.** Hay 13 tareas exclusivas, sin contar las compartidas o las de Erika. Diez están completas dentro del alcance académico aprobado: V2-02, V2-04, V2-04A, V2-04B, V2-04C, V2-04D, V2-05, V2-05A, V2-06 y V2-07. Los anexos posteriores amplían las primeras entregas con M5 y Favorita, calibración, publicación y validación de 2.2.0. Automotive sigue bloqueado por licencia y fuera del alcance aprobado, sin impedir el cierre de las cuatro referencias autorizadas.

V2-11 y V2-15 continúan en progreso para 2.2.0. La pantalla 2.1.0 ya tiene entrega y revisión aislada, pero faltan el enlace a una candidata 2.2.0 aceptada y la validación global correspondiente. V2-13 está pendiente para H5 o ampliación aprobada, sujeta a las reglas de reposición de Erika en V2-12. Por tanto son diez completas, dos en progreso y una pendiente. No corresponde afirmar que toda la parte de Ross está al 100 %.

V2-08 es compartida: la comparación está ejecutada, falta revisar grupos, aceptar y fijar una candidata antes del TEST final único. V2-16 requiere integración y defensa conjunta. V2-17 sigue abierto como registro continuo. Las tareas backend de Erika no se suman al conteo exclusivo de Ross. El siguiente paso recomendado es revisar los trece productos desfavorables, sin abrir TEST, antes de aceptar el nuevo modelo.

## 43. Revisión de los trece productos y las 36 combinaciones desfavorables

La revisión del 15 de noviembre de 2026 terminó sin entrenar, modificar datos o abrir TEST. Se analizaron las predicciones congeladas de los trece finalistas, los lags y las observaciones mensuales hasta junio de 2026. Los datos del mes objetivo solo se utilizaron para explicar errores ya ocurridos, nunca como entradas del modelo. La [revisión reproducible](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/reviews/review-groups-20261115-01/review.json) y sus CSV registran cada caso.

El dataset 2.2.0 ya está construido y validado. Esta tarea no requiere regenerarlo ni añadir fuentes. Contiene 4.032 filas mensuales y 3.528 supervisadas. Es un dataset académico sintético, no historia comercial certificada. Su publicación está registrada en el anexo 40. El modelo ya fue entrenado y comparado en el anexo 42. La revisión actual completa el diagnóstico previo a fijar una política, no la evaluación final o la integración administrativa.

### Alcance y resultados comprobados

Los trece productos representan 117 observaciones. En ese subconjunto, el MAE del bosque es 9,0884 frente a 6,0940 del baseline. Las 36 combinaciones representan 108 observaciones y tienen MAE 15,6646 frente a 10,2778 del baseline. Cada producto tiene nueve observaciones y cada combinación solo tres. Los subconjuntos se solapan, no deben sumarse. Además, 18 de los productos que contienen una combinación desfavorable mejoran cuando se agrupan sus tres tiendas. El resultado global puede ocultar un problema local.

| Product.id | MAE baseline | MAE bosque | Deterioro |
| --- | --- | --- | --- |
| 41 | 10.0000 | 20.3192 | +10.3192 |
| 54 | 8.6667 | 15.7431 | +7.0764 |
| 28 | 4.6667 | 9.4258 | +4.7592 |
| 25 | 8.4444 | 12.7600 | +4.3156 |
| 32 | 8.1111 | 11.8725 | +3.7614 |
| 55 | 2.1111 | 3.8850 | +1.7739 |
| 21 | 11.3333 | 12.7253 | +1.3919 |
| 48 | 6.2222 | 7.5214 | +1.2992 |
| 13 | 0.8889 | 2.0697 | +1.1808 |
| 23 | 0.1111 | 1.1725 | +1.0614 |
| 11 | 10.5556 | 11.5414 | +0.9858 |
| 46 | 6.0000 | 6.8492 | +0.8492 |
| 1 | 2.1111 | 2.2647 | +0.1536 |

Las [36 combinaciones](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/reviews/review-groups-20261115-01/product_store.csv) se documentaron por separado con ubicación, rotación TRAIN, errores, ceros, saltos y stock observado. La [tabla mensual](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/reviews/review-groups-20261115-01/validation_diagnostics.csv) conserva las 504 observaciones, sin leer TEST.

### Qué explica el deterioro

El patrón principal no son únicamente los saltos inesperados. En 70 de las 108 observaciones de las combinaciones desfavorables, el target queda a cinco unidades o menos del último mes. En esas filas el baseline resulta difícil de superar. Acumulan 762,8475 unidades de exceso de error absoluto del bosque. El exceso neto de las 108 filas es 581,775 porque otras filas compensan parte del deterioro. La estabilidad de algunos niveles es importante para esta comparación.

El bosque global reúne todas las series mediante cinco entradas: tres lags y calendario. No distingue explícitamente cada producto o tienda. Sus árboles de profundidad cuatro, con error absoluto, favorecen valores centrales dentro de las hojas. Al promediar 200 árboles, ciertos niveles altos se acercan a niveles intermedios. Esto es un mecanismo numérico comprobado, no una prueba causal sobre clientes, precios o proveedores.

Para el producto 28, tienda 5, abril de 2026, el último mes y el target son 80. El bosque predice 40,96 y las predicciones de sus árboles van de 40 a 46. Para el producto 41, tienda 7, mayo, el último mes es 84 y el target 86. El bosque predice 42,335. La mediana de las predicciones de sus árboles es 41. Son ejemplos concretos de subestimación de un nivel persistente.

Los productos 54, 25, 32 y 11 también presentan meses mayoristas de unas 80 unidades con predicciones próximas a niveles intermedios. En el sentido contrario, el producto 48, tienda 5, junio, vende 21 tras vender 20, pero el bosque predice 48,0475. El producto 46 en esa tienda vende 21 tras vender 24 y recibe 47,8825. El producto 23 tiene una secuencia cercana a 40 que el baseline reproduce mejor. Los productos 55 y 1 presentan subestimación de cantidades pequeñas. No todos los errores requieren la misma respuesta.

En el producto 13, tienda 7, abril, el target y el baseline son cero, pero el bosque predice 8,7925. Esto muestra la dificultad de separar actividad de ausencia de venta en series intermitentes. No significa que el bosque falle en todos los ceros: sobre las 219 filas con target cero mejora el MAE de 2,8539 a 1,2130. Tampoco toda baja rotación empeora. Se debe distinguir el promedio de un grupo de sus excepciones.

Los pedidos mayoristas concentran parte del deterioro local. Dentro de las 36 combinaciones, hay 56 filas con al menos 20 unidades mayoristas y una participación de al menos 50 %. Su MAE pasa de 15,5536 a 25,4978. En las 171 filas de ese tipo del conjunto completo ocurre lo contrario: el bosque mejora de 29,3333 a 23,2083. Por tanto no puede afirmarse que toda venta mayorista perjudique al modelo. Los umbrales son descriptivos de esta revisión, no reglas comerciales o políticas de selección.

La falta de stock es otra asociación que requiere cuidado. En las once filas de las combinaciones desfavorables con siete o más días sin stock del mes objetivo, el MAE pasa de 15,7273 a 26,8427. Ese dato se conoce después del corte. No puede introducirse retrospectivamente como feature. Ventas observadas y demanda total siguen siendo conceptos distintos. Esta revisión no identifica cuánto se perdió por falta de stock ni demuestra que el stock haya causado el error.

Los errores absolutos más grandes tampoco coinciden siempre con los productos que empeoran en promedio. El producto 51, tienda 7, mayo, vende 80 unidades mayoristas tras vender cero. El bosque predice 0,01 y el baseline cero. Ambos fallan casi por igual. Ese pedido nuevo no puede anticiparse con certeza a partir de lags bajos si no existe una señal disponible antes del mes objetivo. Un modelo más complejo no elimina información desconocida.

### Alternativas existentes y mejoras razonables

Se contrastaron las alternativas ya entrenadas, sin ajustes adicionales. Añadir modalidad al bosque mejora siete de los trece productos respecto al bosque principal, pero empeora otros. Su MAE global es 9,7956 y el del subconjunto desfavorable 9,0913. El bosque de cinco entradas tiene 9,7604 y 9,0884, respectivamente. El bosque con cotización mejora apenas el MAE del subconjunto a 9,0768, pero empeora el global a 9,9904. El bosque completo obtiene 9,9902 global y 9,0916 en ese subconjunto. Ninguna alternativa demuestra una solución general. Elegir una opción distinta para cada producto después de ver VALIDATION produciría una ventaja retrospectiva que no está validada.

La recomendación inmediata es conservar el bosque de cinco entradas como candidata principal, con baseline visible y advertencias sobre intermitencia y pedidos grandes. El diagnóstico queda terminado. Falta aceptar expresamente sus límites y fijar artefacto, política de no negativos y alcance antes de la evaluación final única. No se fija o promociona automáticamente durante esta revisión.

Si el equipo decide mejorar antes de fijar, el siguiente experimento debe declararse por adelantado y comprobarse primero en los folds de TRAIN. Las opciones prioritarias son aprender una corrección sobre el baseline para conservar mejor niveles persistentes y comparar una combinación de baseline y bosque con peso elegido solo dentro de TRAIN. Después se compararía una configuración candidata en VALIDATION. Los cortes por rotación o nivel solo se aceptarían si se definen con TRAIN, cuentan con observaciones suficientes y funcionan en las ventanas internas. No se deben diseñar trece excepciones con estos resultados.

Separar probabilidad de venta y cantidad positiva puede estudiarse para intermitencia, con mayor costo y riesgo de ajuste excesivo. Las señales de pedidos confirmados, promociones o disponibilidad planificada solo pueden añadirse en una versión posterior si tienen contrato y fecha de disponibilidad previa al corte. No se promete recuperar pedidos aleatorios o demanda perdida. No hace falta ampliar ahora el dataset para justificar estas limitaciones. Tampoco corresponde cambiar el generador para que gane un algoritmo.

Se comprobó la cohorte de 504 filas, claves únicas, nueve filas por producto, tres por combinación, los trece productos, las 36 combinaciones, la reproducción del MAE congelado y la concordancia entre la predicción del bosque y sus árboles en cuatro casos representativos. El [control del mecanismo](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/reviews/review-groups-20261115-01/mechanism_checks.json) conserva los resultados. No hubo ajustes de parámetros, entrenamiento, nuevas métricas TEST o cambios del modelo activo.

La revisión de errores está completa dentro del alcance solicitado. V2-08 continúa abierta hasta aceptar y fijar una política, evaluar TEST una sola vez y documentar esa evaluación. Ross mantiene diez tareas exclusivas completas, dos en progreso para la integración y validación global de 2.2.0, una pendiente de H5. No se declara el sistema comercial al 100 % ni precisión garantizada. Para presentar ahora puede mostrarse el dataset validado, la comparación TRAIN/VALIDATION y este diagnóstico, explicando que la evaluación final 2.2.0 sigue pendiente.

## 44. Aceptación 2.2.0, TEST único e integración administrativa

El usuario aceptó expresamente el bosque actual para H4, sus límites documentados y la conexión al administrador. Se congeló la selección accepted-absolute-2.2-20261115-01 antes de interpretar TEST. No se reentrenó, cambió de candidata o ajustó la política después de conocer el resultado. La evaluación 2.1.0 se conserva como evidencia de otro dataset, sin repetirse o compararse como si ambas versiones tuvieran la misma dificultad.

El artefacto es candidate-2.2-1202b43393aac05173a4f603.joblib, guardado en models/v2/train-2.2-20261115-01. Su SHA-256 es def5a93dcabf27916d1120af0160d2910dc7737f4036ec2507f60eb7d5670f35. Utiliza 200 árboles con criterio absolute_error, profundidad máxima cuatro, mínimo de cinco filas por hoja y seed 42. Sus entradas son los tres lags y mes_sin, mes_cos. El dataset conserva las 17 features candidatas, pero el modelo elegido no utiliza todas. Los IDs identifican filas, no son cantidades del modelo.

La [selección fijada](../../ml/demand/v2/contracts/selection.v2_2.json) registra hashes de entradas, versiones de bibliotecas, parámetros y estado del preprocesamiento. La política NONNEGATIVE_CONTINUOUS_1 rechaza resultados no finitos, limita negativos a cero y conserva la salida continua sin redondeo. La interfaz muestra dos decimales por presentación. No convierte la predicción en una orden de compra. Se aceptaron antes de TEST los trece productos y las 36 combinaciones desfavorables de VALIDATION.

### Evaluación final reservada

El evaluador crea una reserva exclusiva antes de cargar TEST. Si ya existe, se detiene antes de abrir datos o predecir. Una falla posterior consume la reserva, no permite borrarla para reintentar. Las pruebas de ese comportamiento usan carpetas temporales y datos ficticios. La rutina de preparación continúa rechazando TEST y no fue desbloqueada para otros experimentos.

TEST comprende julio a septiembre de 2026, 504 filas. Se comprobó su hash, cohorte, target contra ventas brutas, lags y fechas de corte. Hubo una carga final y una llamada predict del modelo, sin fit. Los resultados por mes y grupo se calculan de ese mismo vector guardado, sin nuevas consultas predictivas.

| Métrica final | Bosque 2.2.0 | Baseline último mes |
| --- | --- | --- |
| MAE | 9,2046 | 12,8690 |
| RMSE | 16,9085 | 23,6926 |
| R² | 0,6466 | 0,3061 |

La reducción del MAE es 28,47 %. No es un porcentaje de precisión. La suma prevista es 7.793,2575 frente a 9.748 unidades observadas, aproximadamente 20,05 % menos. El sesgo medio es -3,8785 unidades. El error absoluto máximo es 72,57 y hay 106 filas con error superior a 20. Estos límites se conservan, no se cambia el modelo para mejorar TEST. La [evaluación final](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/final_test/result.json) permanece como registro de un evento único.

El horizonte es un mes con historia cerrada actualizada antes de cada pronóstico. Agosto puede usar julio cerrado y septiembre puede usar agosto cerrado, sin reajustar el modelo. No es una predicción simultánea de tres meses realizada desde junio. No acredita precisión comercial sobre la tienda real.

### Integración y permisos

La ruta es /panel/prediccion, dentro del administrador. El frontend consume GET /api/predictions/catalog y POST /api/predictions/demand. El servicio Node ejecuta el puente Python y verifica identidad, selección, artefacto, política y respuesta. La inferencia verifica hashes y el estado del preprocesamiento, obtiene snapshots del servidor y utiliza únicamente los meses aprobados de VALIDATION para la demostración. Los valores de TEST no se utilizan como entradas de las consultas del administrador. La pantalla lee sus métricas guardadas, no vuelve a evaluar TEST.

| Sesión o rol | Catálogo | Predicción | Menú y ruta |
| --- | --- | --- | --- |
| ADMIN válido | 200 | 200 | Acceso permitido |
| TIENDA válido | 403 | 403 | Sin enlace, ruta bloqueada |
| INVENTARIO válido | 403 | 403 | Sin enlace, ruta bloqueada |
| Rol desconocido | 403 | 403 | Sin enlace, ruta bloqueada |
| Sin sesión, token inválido o revocado | 401 | 401 | Debe iniciar sesión |

Los permisos se aplican en API, no solo en la pantalla. Las pruebas del middleware real simulan únicamente sus lecturas de sesión y no abren la base. También comprueban que el rol vigente prevalece sobre claims anteriores. Se verificaron errores de solicitud 400, snapshot 409, ausencia de mes aprobado 422 y modelo no disponible 503. No se permite enviar features, targets, rutas de archivos o elegir otro modelo desde la petición. Una respuesta 2.1.0 se rechaza como incompatible. No hay fallback automático.

El contrato real pasó por Node, Python y los validadores del frontend en abril, mayo y junio. Para el producto 28, tienda 5, produjo 40,96, 41,015 y 45,8075, respectivamente. La pantalla real se abrió mediante una sesión local ficticia. Su consulta utilizó la API, el puente y el artefacto reales. Se revisaron escritorio de 1280 px y celular de 390 px, sin desbordamiento horizontal. Los módulos operativos ajenos a predicción estaban aislados de la base, por eso esa revisión no certifica su operación comercial. Streamlit sigue separado.

### Pruebas, conservación y alcance del cierre

Pasaron 84 pruebas Python del alcance, 173 backend y 248 frontend. Son 505 pruebas de esas suites, no un recuento de todos los tests posibles del repositorio. Se comprobaron tipos backend y build frontend. También pasó el control real de contrato entre Node, Python y el validador frontend. Las pruebas de inferencia reprodujeron las 504 predicciones VALIDATION del entrenamiento. Las pruebas históricas de inferencia 2.1.0 siguen pasando, sin repetir su TEST.

Los primeros intentos backend dentro del entorno restringido fallaron por EACCES al conectar a servidores HTTP locales. Se repitió la suite con acceso al bucle local y un DATABASE_URL ficticio dirigido a un puerto local inválido. Pasó completa sin conexión a Neon. Los avisos frontend restantes son limitaciones de jsdom para navegación y canvas, además de advertencias act en tests de otros componentes. No bloquearon pruebas o build. No se refactorizaron módulos ajenos para ocultarlos.

La [evidencia de integración](../../ml/demand/reports/v2/integration/admin-2.2-20261115-01/binding.json) registra hashes, permisos, pruebas, alcance visual y ausencia de entrenamiento durante inferencia. Conserva capturas de escritorio y celular, logs y el control de contrato. La validación no escribe en ventas, inventario, dataset o RAW.

Ross cierra doce de sus trece tareas exclusivas en el alcance local académico H4. V2-11 y V2-15 quedan actualizadas a 2.2.0. V2-13 corresponde a reposición de H5 y sigue pendiente. V2-08, V2-09B y V2-10 tienen evidencia técnica de cierre para 2.2.0. El ensayo y aceptación conjunta de V2-16 no se inventan. V2-14 conserva la comprobación operativa de dashboard con base permitida como alcance separado. V2-18 conserva el cierre formal de recuperación entre versiones como tarea del plan, aunque los artefactos e inferencia 2.1.0 permanecen funcionales offline.

La entrega solicitada de modelo fijado, TEST único y conexión administrativa está implementada y comprobada localmente. No se declara toda la plataforma o producción al 100 %. No se verificó una sesión real contra Neon, el estado productivo del esquema, cada operación comercial o Expo. Eso no impide presentar esta reproducción académica H4 con su alcance explícito.

Para recuperación se conservan selección, artefactos, inferencia y evaluación 2.1.0, además de V1. Una falla del nuevo modelo produce indisponibilidad explícita, sin inventar otra predicción. Un retorno completo a 2.1.0 exige restaurar coordinadamente la identidad en puente, servicio y guard del frontend, verificar sus contratos y registrar la decisión. No se modifica un artefacto o elimina una reserva TEST. No se ofrece ese retorno manual como rollback automático ya implementado.

Para la exposición, iniciar la aplicación local con su procedimiento habitual, entrar con ADMIN y abrir Predicción de ventas. Explicar origen sintético, elegir producto, tienda y uno de los meses aprobados, consultar y mostrar histórico, baseline, predicción, métricas guardadas y snapshot. Las cuentas ficticias de revisión no son cuentas del sistema operativo. No se deben utilizar para acceder a producción.

## 45. README, recuperación de versiones y dashboard local

El README técnico activo de ml/demand se actualizó para identificar 2.2.0, su modelo de cinco entradas, los contratos vigentes y el TEST consumido. Las secciones anteriores se conservaron como historia. La recuperación admite DEMAND_RELEASE=2.2.0 o DEMAND_RELEASE=2.1.0 exclusivamente en el servidor. No acepta versiones o rutas desde el cliente. No modifica archivos .env o secretos. Sin variable, se utiliza 2.2.0.

Se comprobó la cadena real Node → Python → frontend durante el recorrido 2.2.0 → 2.1.0 → 2.2.0. Para producto 20, tienda 5 y junio de 2026 se obtuvieron 0, 40,8725 y 0 unidades, con sus propios hashes y políticas. Son realizaciones distintas, no un contraste de calidad. Un snapshot de 2.2.0 no se acepta en 2.1.0. La pantalla valida la versión de su catálogo y rechaza respuestas mezcladas. Cuando se activa 2.1.0 muestra un aviso de recuperación. Una configuración desconocida falla, sin sustitución automática.

Para recuperar, detener el proceso backend, definir DEMAND_RELEASE en su terminal y reiniciarlo. Actualizar las referencias del navegador antes de consultar. Para volver, repetir el procedimiento con 2.2.0. El frontend no necesita reconstruirse para estas dos versiones expresamente permitidas. El control no habilita otros modelos o LIVE_FORECAST.

La inspección inicial autorizada de Neon fue READ ONLY y confirmó el error P2022 en Sale.status. Faltan 19 columnas en cinco tablas y dos tablas completas relacionadas con controles físicos y comerciales. El historial de migraciones tampoco coincide con todos los cambios físicos, por lo que no procede ejecutar migrate deploy a ciegas. Esa consulta observó 62 productos, 247 ventas, 414 registros de inventario, 41 movimientos y 12 devoluciones. Son conteos de este diagnóstico, no una certificación del historial para entrenamiento.

El usuario indicó después preparar y probar solo localmente. No hubo más consultas o cambios en Neon. Se creó un fixture PostgreSQL 16 local, sin datos personales o comerciales reales. Con las ocho primeras migraciones se reprodujo el 503 del dashboard para ADMIN, INVENTARIO y dos tiendas. Se aplicaron únicamente allí las dos migraciones aditivas existentes de noviembre. El resultado pasó a 200 y se conservaron las huellas de las columnas y filas originales en seis tablas del fixture. Esto no equivale a restaurar una copia exacta de Neon ni a aprobar su reconciliación completa.

También se corrigieron problemas de código: los productos de otra tienda ya no se cuentan como sin stock en la tienda actual, los productos sin inventario se incluyen como sin stock en la vista global y la cantidad de solicitudes pendientes se obtiene con count, separada de las diez filas recientes. TIENDA sin ubicación se rechaza antes de consultar. El fixture validó 14 productos globales, 12 de la primera tienda y uno de la segunda. Las doce solicitudes pendientes se informan como doce aunque la lista muestre diez. Las ventas conservan el filtro CONFIRMED.

La [evidencia del cierre técnico local](../../ml/demand/reports/v2/closure/close-h4-20261115-01/recovery-smoke.json) registra la recuperación. Los archivos local-before.json y local-after.json de esa carpeta conservan la reproducción y conservación del fixture. El diagnóstico inicial está en diagnosis.json. El dashboard de la captura no queda reparado en producción mientras su base continúe sin las columnas requeridas. La reconciliación requiere una rama aislada, punto de recuperación y revisión de los efectos ya presentes antes de cualquier aplicación o migrate resolve.

En esta ronda pasaron 86 pruebas Python, 174 backend y 249 frontend, un total de 509, además de ambos builds. La comparación del schema local terminó sin diferencias. Estas pruebas verifican los cambios locales y la referencia congelada, no completan las nuevas funciones interactivas.

## 46. Revisión del alcance tras el audio del docente

Se revisó completo correccionesH4.ogg, de aproximadamente 3 minutos y 42 segundos, mediante dos transcripciones locales. La [matriz de requisitos](../../ml/demand/reports/v2/closure/close-h4-20261115-01/audio_scope_review.json) conserva hash, tiempos y diferencias. Algunas palabras son ambiguas y no se presentan como citas certificadas. Las voces no se separaron automáticamente. No se atribuyen todas las intervenciones a una sola persona.

El cierre anterior fue demasiado amplio: comprobar replay y elegir el menor MAE no demuestra que el sistema permita los cambios interactivos pedidos. El bosque 2.2.0 usa tres lags y calendario. Tener precios o cotización en el dataset no significa que esa configuración los utilice. Tampoco existe una elasticidad causal de precio identificada en el generador. No se debe simular un efecto visual que el modelo no calcula ni cambiar una etiqueta para presentar otra versión como completa.

| Requisito vigente | Qué existe | Qué falta |
| --- | --- | --- |
| Activar cambio de precio, mostrar actual y nuevo | Precios simulados y reglas económicas | Control de escenario y comparación antes/después. Audio 00:00 a 00:17 |
| Costo y cotización Bs/USD de compra | Variables y supuestos académicos | Coherencia costo → precio y disponibilidad temporal. El modelo activo los excluye. Audio 01:24 a 02:04 |
| Tiempo de llegada y reposición | Tablas simuladas de envíos y recepciones | Control de fechas y retrasos, tránsito, recepción parcial y disponibilidad. Audio 01:33 a 01:41 |
| Precios y venta mayorista/minorista | POR MENOR=price1 y POR MAYOR=wholesalePrice | Entradas de modalidad y cantidades conocidas al corte. No crear un tercer precio por una frase ambigua del audio |
| Cantidades y fechas de escenario | Editor de lags y reloj previo en Streamlit, replay administrativo fijo | Adaptación V2 con meses consecutivos, corte America/La_Paz y target no editable. Requisito también presente en los mensajes del usuario |
| Crecimiento, caída, pico mayorista, stockout y producto nuevo | Escenarios previos y fixtures | Intervenciones económicas y logísticas combinadas y comportamiento verificable. Audio 00:18 a 00:33 |
| Gráfica que compare el cambio | Histórico, predicción y baseline de un snapshot | Escenario base frente a modificado, diferencias y supuestos visibles |
| Justificación de una tienda real | Validación técnica sintética | Evaluar necesidad, fuente, disponibilidad, utilidad y límites de cada variable. Audio 01:11 a 01:53 y 02:39 a 03:24 |

La cantidad debe tener un significado claro: ventas históricas simuladas, stock disponible, pedido confirmado o cantidad a reponer. No son intercambiables. El target del mes que queremos predecir no puede convertirse en entrada editable. Cambiar una cantidad de escenario no debe modificar ventas, inventario o precios operativos.

Las fechas requieren separar momento del cambio, momento conocido por el sistema, inicio del mes objetivo, fecha prevista y recepción real. Los lags deben proceder de meses cerrados consecutivos. Que el usuario pueda escoger una fecha no habilita un pronóstico diario si el modelo es mensual. Tampoco puede usarse la recepción real futura para predecir un corte anterior.

El costo o el dólar pueden afectar el precio y la disponibilidad, pero no corresponde imponer una relación universal sobre las ventas. Una simulación puede declarar sensibilidad al precio como supuesto, con perfiles sensibles o poco sensibles, sin afirmar que fue estimada de una tienda real. Las fuentes externas no aportan una elasticidad boliviana certificada. No se debe obligar a que toda variable administrativa sea feature, incluir datos personales o duplicar variables sin justificación.

El tiempo de proveedor debe intervenir en la disponibilidad prevista y la explicación de reposición. Eso no obliga a entrenar las unidades vendidas con información futura. Deben separarse pronóstico de ventas, evaluación de disponibilidad y cálculo de reposición. Una demostración logística puede formar parte del alcance H4 exigido por el docente. La ejecución comercial de compras o movimientos automáticos sigue fuera de este alcance.

El orden corregido es definir el contrato funcional y las reglas de escenarios, revisar diccionario y mecanismos del generador, diseñar una nueva realización versionada, validar coherencia y después solicitar autorización para construir o entrenar. Los datos y modelos 2.2.0 se conservan como referencia. Su TEST ya observado no servirá como evaluación independiente de un modelo nuevo o una selección revisada.

Backend y frontend deben distinguir consulta histórica de escenario hipotético. La segunda necesita entradas de negocio validadas, escenario base, cambios solicitados, corte y procedencia, además de respuesta con versión y advertencias. No se propone enviar features libres o rutas de modelos desde el cliente. El simulador editable permanece separado, con contratos coherentes entre ambos recorridos.

No se generó un dataset nuevo, entrenó, repitió TEST o modificó RAW. Las tareas de diccionario, escenarios, calibración, construcción, validación, selección e interfaz se reabren para el alcance interactivo, conservando el cierre técnico de la referencia 2.2.0. No se presenta H4 completo ni toda la parte de Ross al 100 % mientras falten estos requisitos. Tampoco se exige rehacer desde cero lo que ya tiene evidencia válida.

## 47. Contrato de escenarios y reparto vigente del H4 interactivo

El contrato documental [scenarios.v1.json](../../ml/demand/v2/contracts/scenarios.v1.json), versión demand-scenarios-1.0.0, define solicitudes, respuestas, unidades, errores y 21 reglas de negocio. Su estado es DESIGN_READY_IMPLEMENTATION_PENDING. Las rutas de capabilities y preview son propuestas, no endpoints ya disponibles. Los controles actuales de replay no se cambiaron durante esta tarea. La referencia 2.2.0, sus datos, modelos y TEST consumido se conservan intactos.

**Responsabilidades.** Ross realiza todo el frontend y todo el dataset: diccionario, fuentes, supuestos, calibración, generador, eventos, features, split, validación, publicación y documentación de datos. Erika realiza backend y servicio del modelo: API, proveedor de snapshots, reglas semánticas, motor de escenarios, cálculo de reposición, preprocesamiento del modelo, experimentos, inferencia, permisos y versiones. Ross entrega las variables y el split. Erika ajusta imputación, codificación y escalado únicamente sobre TRAIN dentro del pipeline, sin reescribir el dataset. La revisión conjunta no deja tareas sin responsable principal.

### Contenido del contrato

Cada solicitud identifica producto, tienda, mes objetivo y snapshot base. Los cambios tienen un modo KEEP o una edición explícita. No se admiten rutas, modelos, features libres o target enviados desde el navegador. El backend resuelve los valores base y devuelve valores antes/después, unidades, procedencia, función de cada campo y advertencias. Las cantidades o precios propuestos son hipótesis, no modificaciones de Product, Sale o Inventory.

| Grupo | Entradas de escenario | Regla principal |
| --- | --- | --- |
| Historia y cantidades | Tres meses completos, unidades por menor, por mayor y modalidad desconocida | Meses consecutivos anteriores al objetivo. Sin negativos, fracciones o target editable. Producto sin historia no se rellena con ceros |
| Precios | Interruptor de cambio, precio base consultado al servidor, nuevos precios por menor y por mayor, fecha de vigencia | Costo conocido ≤ por mayor ≤ por menor. Product.price1 respalda POR MENOR, wholesalePrice respalda POR MAYOR. price2 sigue LEGACY |
| Cotización | Bs por USD y fecha de observación de una cotización hipotética | Mostrar antigüedad y fuente. No presentar un valor simulado como cotización real o usar un valor posterior al corte |
| Costo | Costo puesto en Bs o compra nueva hipotética en USD, flete y otros costos por unidad | Costo Bs = costo USD × cotización + componentes Bs. Un cambio de cotización no revaloriza compras históricas |
| Stock y pedidos | Stock físico vendible, pedidos pendientes, modalidad, cantidad, reserva y fecha de entrega | Excluir cuarentena y tránsito del stock físico. Separar reservas para este horizonte y para fechas posteriores |
| Llegada y reposición | Plazo de proveedor, traslado interno, fecha prevista del pedido y entradas pendientes | Días calendario en esta versión. Separar fecha prevista de recepción real. No habilitar stock antes de recibirlo |
| Política de reposición | Seguridad, mínimo de compra, múltiplo y periodo de revisión | Son supuestos explícitos de la demo si no existe una regla auditada del proveedor. No inventar mínimos o presentaciones |

Las fechas se interpretan en America/La_Paz. El corte es el inicio del mes objetivo. Los cambios de precio o costo dentro del mes deben conservar sus intervalos. Si el mecanismo mensual utiliza una exposición ponderada, se calculará con días calendario conocidos al corte, no con ventas futuras. Si el modelo no soporta esa intervención temporal, debe informarlo. No convertir en silencio un cambio del día 15 en un precio aplicado durante todo el mes.

El contrato distingue ventas estadísticas, disponibilidad y reposición. Una nueva cotización puede modificar el costo de una compra hipotética. Esa regla no demuestra por sí sola un efecto causal sobre ventas. Ross debe justificar los mecanismos del generador y Erika debe comprobar qué usa el modelo. Si una variable no se utiliza como feature, debe declararse su papel: validación, derivación, disponibilidad o reposición. El bosque 2.2.0 no puede presentarse como sensible al precio cuando solo usa lags y calendario.

La respuesta de comparación usa el mismo producto, tienda, mes, corte, artefacto y política. Solo cambian las hipótesis declaradas. Si el escenario no está soportado, sus unidades y diferencia serán null con una razón. Puede conservarse la predicción base y mostrar estado PARTIAL. No se devuelve el mismo número como si se hubiera evaluado un cambio económico. Las métricas guardadas describen el modelo, no un error conocido de ese escenario hipotético.

La política mensual inicial evita sumar dos veces pedidos y reservas. Se calcula necesidad = techo del mayor entre pronóstico total y compromisos del horizonte, más seguridad. Los compromisos son un mínimo del requerimiento, no una suma automática al total previsto. La posición = stock físico vendible menos reservas para fechas posteriores, más entradas elegibles antes del cierre. Las reservas del propio horizonte ya están incluidas en los pedidos y no se restan otra vez. Esta política académica es un mínimo de cobertura, no demuestra cuánto pedido mayorista es adicional al pronóstico. Si ese solapamiento no se conoce, debe advertirse. Combinar una venta mayorista incremental con una predicción minorista separada requerirá componentes validados, sin adivinar cantidades.

La necesidad bruta de reposición es el máximo entre cero y necesidad menos posición. Si es positiva, se aplica el mínimo de compra y se redondea hacia arriba al múltiplo declarado. Una necesidad cero no activa una compra solo por cumplir el mínimo. Con pronóstico 18, seguridad 5 y stock 9, sin otras entradas o restricciones, son 14 unidades. Si el mínimo fuera 20 y el múltiplo seis, serían 24, bajo ese supuesto comercial explícito.

La llegada prevista del nuevo pedido combina fecha de pedido, plazo de proveedor y traslado interno. El fin de protección añade el periodo de revisión. Si supera el mes cubierto por el pronóstico, el cálculo completo queda OUTSIDE_FORECAST_HORIZON y no devuelve una sugerencia completa inventada. No se divide por 30 o extrapola meses sin validación. Un balance al cierre tampoco garantiza que no haya una falta de stock antes de una recepción tardía. Esa limitación debe verse en la pantalla. El detalle diario requiere un mecanismo temporal validado aparte.

### Tareas de Erika: backend y servicio del modelo

La tabla conserva la distribución del alcance ampliado. Sus estados se actualizaron con el cierre técnico del anexo 51. La planificación inicial no se utiliza como evidencia de ejecución.

| ID | Tarea | Entrega y límite | Dependencias |
| --- | --- | --- | --- |
| H4-E01 | Contrato API y capacidades | **IMPLEMENTADO.** Endpoints de escenarios, contrato y capacidades reales. Acceso ADMIN mediante los middlewares existentes. Ver anexo 51. | Contrato documental |
| H4-E02 | Reglas de negocio y validación semántica | **IMPLEMENTADO Y PROBADO.** Decimal, fechas válidas, precios por intervalo, historia cerrada, cotizaciones, cantidades y planes. Sin completar faltantes con datos inventados. Ver anexo 51. | Contrato documental |
| H4-E03 | Proveedor de snapshots | **IMPLEMENTADO.** Snapshots de entradas BASE de VALIDATION 3.0.0, firmados mediante hashes fijados. No contienen targets o resultados futuros. No dependen de Neon como fuente predictiva. Ver anexo 51. | H4-E01, H4-R01 |
| H4-E04 | Preprocesamiento y experimentos del modelo | **IMPLEMENTADO.** Adaptador y comparación con TRAIN/VALIDATION. Baseline, LinearRegression y dos bosques. Selección por MAE, con escalado e imputación ajustados solo en TRAIN. Ver anexo 51. | H4-R06, H4-E02, adaptador ampliado y revisión de Erika |
| H4-E05 | Motor de comparación base y escenario | **IMPLEMENTADO.** Misma referencia y artefacto para base e hipótesis. Efectos directos, derivados, de validación o solo reposición explícitos. Sin fit durante consulta. Ver anexo 51. | H4-E02, H4-E03, H4-R03 |
| H4-E06 | Disponibilidad y reposición explicativa | **IMPLEMENTADO.** Reposición explicativa, compromisos como mínimo, reservas disjuntas, entradas elegibles y comprobación de llegada dentro del horizonte. Sin compras automáticas. Ver anexo 51. | H4-E02, H4-E03 |
| H4-E07 | Endpoints, snapshots e idempotencia | **IMPLEMENTADO Y PROBADO.** Identidad de snapshot, permisos, concurrencia e idempotencia por actor y petición. Cache atómico en tmp, sin escrituras en Neon. Ver anexo 51. | H4-E01, H4-E05, H4-E06 |
| H4-E08 | Versiones, recuperación y evaluación final | **COMPLETO en el alcance local.** Artefacto y política fijados antes del TEST nuevo 3.0.0, evaluado una sola vez. 2.2.0 y 2.1.0 conservados. Sin fallback silencioso de escenarios. Ver anexo 51. | H4-E04, autorización posterior de evaluación final |
| H4-E09 | Pruebas backend e integración técnica | **COMPLETO técnicamente.** 526 pruebas aprobadas entre backend, frontend y suites de escenarios. Ambos builds correctos. Dashboard contrastado con Neon en READ ONLY. Ensayo personal del equipo pendiente. Ver anexo 51. | H4-E07, H4-E08 |

### Tareas de Ross: frontend y dataset

Ross conserva todo el trabajo útil de las versiones previas. La nueva versión se construirá en otra carpeta cuando se autorice. No se reabre desde cero la revisión de licencias ya comprobada ni se incorporará Automotive sin resolver su permiso.

| ID | Tarea | Entrega y límite | Dependencias |
| --- | --- | --- | --- |
| H4-R01 | Diccionario y estructura ampliados | **COMPLETO como contrato de datos.** Diccionario original conservado, selección efectiva de 19 entradas documentada en el contrato de ejecución 3.0.0. Ver anexo 51. | Contrato documental |
| H4-R02 | Fuentes y supuestos | **COMPLETO para el alcance sintético académico.** Cuatro referencias autorizadas. Automotive permanece excluido por licencia, sin bloquear ese alcance. Ver anexo 51. | H4-R01 |
| H4-R03 | Diseño y calibración del generador | **COMPLETO técnicamente.** Mecanismos sintéticos revisados contra las reglas implementadas. No se afirma elasticidad comercial medida ni aceptación personal del equipo. Ver anexo 51. | H4-R02, H4-E02 |
| H4-R04 | Generador y escenarios versionados | **COMPLETO.** Generador versionado conservado y escenarios normales, adversos, ambiguos e inválidos con respuestas de API probadas. Ver anexo 51. | H4-R03 |
| H4-R05 | Construcción del dataset nuevo | **COMPLETO.** Dataset 3.0.0, build scenarios-20261115-02, utilizado sin modificarlo. Modelo nuevo separado de 2.2.0. Ver anexo 51. | H4-R04, autorización posterior de construcción |
| H4-R06 | Validación y entrega del dataset | **COMPLETO técnicamente.** Validación y entrega aceptadas por el adaptador implementado. Familias emparejadas conservadas, constantes y resultados futuros excluidos. Ver anexo 51. | H4-R05 |
| H4-R07 | Controles frontend | **COMPLETO local.** Controles conectados a capabilities, snapshot y preview reales. Precios, cantidades, fechas, cotización, costos, pedidos y stock sin escrituras operativas. Ver anexo 51. | Contrato documental, H4-E01 |
| H4-R08 | Gráficos, tabla y exportación | **COMPLETO local.** Comparación, gráfico, tabla, trazabilidad y exportación con respuestas reales. Datos sintéticos visibles. Ver anexo 51. | H4-R07, H4-E07 |
| H4-R09 | Vista de reposición | **COMPLETO local.** Vista conectada a la política de reposición. Reservas sin doble conteo, llegadas, mínimos, múltiplos y límites del horizonte comprobados. Ver anexo 51. | H4-R07, H4-E06, H4-E07 |
| H4-R10 | Pruebas frontend y evidencia | **COMPLETO para el cierre técnico local.** Pruebas, escritorio y celular de 390 px con API/modelo reales y sesión local de prueba. Falta únicamente el ensayo personal del equipo, que no se declara realizado. Ver anexo 51. | H4-R08, H4-R09, H4-E09 |

El orden será: contrato → diccionario y fuentes → reglas y mecanismos → generador y escenarios → nuevo dataset → validación → experimentos autorizados → modelo fijado → integración real → defensa. Erika puede preparar validadores y proveedor mientras Ross trabaja en diccionario y supuestos. Ross puede diseñar controles con fixtures después del contrato, sin afirmar que ya existe una predicción sensible a las ediciones.

Ambos revisan H4-J01, las reglas, fuentes y criterios antes de ejecutar la construcción o entrenamiento. H4-J02 es el recorrido real y ensayo conjunto. No se registra una revisión personal o ensayo de Erika y Ross que no haya ocurrido. La implementación debe mantener una fuente acordada de reglas y fixtures independientes para comprobarla, evitando copiar fórmulas distintas en generador, API y pantalla.

Las pruebas de aceptación deben cubrir cambio nulo, precio mayor o menor, cotización antigua o ausente, costos incoherentes, pico mayorista conocido o inesperado, cantidades cero e inválidas, mes incompleto, producto nuevo, recepción parcial, reservas, pedido tardío y combinaciones. Deben probar además cambio de mes, respuestas tardías, modelo incompatible y roles. La comparación base/escenario tiene que ser reproducible. No se exige que cualquier cambio de precio fuerce una caída fija de ventas, se exige un comportamiento justificado o una respuesta de falta de soporte.

El contrato se comprobó con once pruebas estructurales. Se verificaron esquemas, ejemplos conceptuales, tipos, decimales, fechas con zona, campos prohibidos y estructura de historia y logística. Se corrigió la falta de una restricción explícita de zona horaria detectada por esas pruebas. La aritmética entre campos, las fechas reales, los permisos y la idempotencia siguen siendo responsabilidad del backend pendiente. JSON Schema no implementa por sí solo esas reglas. No se confunde aprobar un schema con tener una API funcional.

En H4 se presentarán edición y comparación de escenarios, explicación de entradas y una sugerencia de reposición con límites. En H5 quedan compras, recepciones y movimientos operativos automáticos, integración comercial definitiva y seguimiento con datos reales. La sensibilidad económica, los nuevos parámetros y columnas finales siguen pendientes de justificación antes de construir otro dataset. Esta tarea no entrena, genera observaciones, modifica Neon o Prisma ni crea nuevos Markdown.

La [verificación del contrato](../../ml/demand/reports/v2/contracts/scenario-contract-20261115-01/validation.json) registra once pruebas nuevas y diez de arquitectura, 21 aprobadas en total. Se contrastaron los hashes de 607 archivos protegidos. Solo cambió metadata activa permitida, sin tocar datasets, RAW, modelos o reportes anteriores. No se accedió a Neon, ejecutaron migraciones o comandos Git.

## 48. H4-R01 de Ross: diccionario ampliado completado

Se completó el diseño del [diccionario ampliado](../../ml/demand/v2/contracts/dataset_dictionary.scenarios.v1.json), versión scenario-dictionary-1.0.0, según el contrato demand-scenarios-1.0.0. Ambos contratos quedan vinculados por hash, sin cambiar el contrato de escenarios o el diccionario anterior. No se creó un CSV, build o versión nueva del dataset. R01 cierra definiciones, no certificación de todas las fuentes, calibración o implementación.

El diccionario cubre los 48 campos de entrada del contrato, incluidas las ramas KEEP y de edición. Cada campo identifica tipo, unidad, origen, rol, disponibilidad y tratamiento de faltantes. Los nombres propuestos son del contrato y de futuras tablas de datos. No son campos nuevos de Prisma ni columnas cuya existencia se haya comprobado en Neon. Los campos físicos citados se contrastaron con el schema local, sin conectarse a la base.

| Tabla propuesta | Función y límite |
| --- | --- |
| scenario_context | Identidad, mundo de simulación, familia, mes, corte, modo de edición y procedencia. Nunca features numéricas |
| closed_history_monthly | Tres meses anteriores completos, con unidades por menor, por mayor y modalidad desconocida |
| price_plan_events | Precio base o propuesto y sus intervalos de vigencia. Diferenciar propuesta rechazada de precio aplicado |
| exchange_quote_events | Bs/USD, fuente, momento observado y momento conocido. No asumir 6.96 |
| cost_plan_events | Costo puesto en Bs, componentes de importación USD y recargo de origen cuando exista. No duplicar componentes |
| opening_stock_snapshot | Stock físico vendible al corte. No incluye cuarentena o tránsito |
| open_order_plan | Pedidos pendientes conocidos, modalidad, reservas y vencimiento |
| pending_shipment_plan | Cantidades aún pendientes al corte y llegada prevista. No saldo final conocido después |
| logistics_policy | Plazo de proveedor, plazo interno y fecha planificada de pedido |
| replenishment_policy | Seguridad, mínimo, múltiplo, revisión y versión de la política |
| receipt_outcomes | Recepciones reales. Solo pueden reconstruir un corte si ya ocurrieron y se conocían entonces |
| monthly_outcomes | Target bruto, completitud, fecha de certificación y controles de simulación posteriores |
| supervised_monthly | Proyección candidata de identificadores, features, target y controles |
| decision_outputs | Pronóstico, diferencias y reposición. No volver a tratarlos como ventas observadas o features |

Hay 195 definiciones de columnas entre las tablas, con identificadores comunes repetidos donde corresponde. No son 195 variables independientes del modelo. La proyección supervisada tiene 43 campos: conserva los 24 nombres de referencia, añade 16 features candidatas y tres controles de identidad del escenario. En total hay 33 candidatas FEATURE, cuatro IDENTIFIER, cinco CONTROL y un TARGET. No se seleccionan automáticamente todas las candidatas para el modelo.

Las nuevas candidatas cubren precio base por menor y mayor, precios planificados ponderados por tiempo, sus variaciones, duración del precio nuevo, stock vendible al corte, compromisos por modalidad, reservas del horizonte y posteriores, entradas previstas, tiempo a la primera entrada y plazos de proveedor e internos. El costo puesto y sus componentes permanecen como controles económicos y fuentes de derivación, no como una feature directa aprobada sin justificar su utilidad. No se reintroduce promedio_3_meses.

Los cambios dentro del mes se ponderan por duración de intervalos conocidos, con fracciones de día si ocurren a mediodía. No se ponderan por ventas futuras. El plan debe cubrir todo el mes. Con huecos o planes desconocidos el resultado es null, no un promedio parcial dividido por el mes completo. KEEP conserva la base, pero no prueba que no habrá cambios. Un precio constante todo el mes necesita un plan o una hipótesis explícita.

**Tipos y unidades.** Las cantidades son enteros no negativos. Las predicciones son continuas y la diferencia entre escenarios puede ser negativa. Los importes del contrato son cadenas decimales con unidad Bs/unidad o USD/unidad, procesadas con Decimal. La cotización es Bs/USD. El recargo Cost.percentage usa escala 0 a 100, distinta de una proporción de variación como 0,25. El paso a números del modelo será controlado dentro del pipeline de Erika y no reescribirá los CSV congelados. categoryId es una etiqueta categórica, no una cantidad.

**Costos contrastados con el código.** CostsPage presenta entrada USD y muestra el costo guardado en Bs. El backend calcula costo puesto = money(unitCost × exchangeRate × (1 + percentage/100)) y sincroniza Product.cost con el último Cost.costPrice. El contrato de escenarios propone otra descomposición explícita para compras nuevas: USD × cotización + flete Bs + otros costos Bs. Ambas representaciones se distinguen en el diccionario. No volver a convertir o añadir recargo sobre un costPrice que ya es costo puesto.

La fórmula actual no permite reconstruir un USD histórico confiable cuando faltan sus componentes. El código de interfaz usa 6.96 como valor inicial o de reconstrucción. El backend admite 1 como fallback en una ruta con unitCost sin exchangeRate. Ninguno certifica una cotización histórica. Se documentan como riesgos de fuente para R02, sin corregir código o datos en esta tarea. El origen de costos antiguos o editados todavía requiere revisión.

**Fechas de disponibilidad.** El corte t0 es el inicio del mes objetivo en America/La_Paz. Un evento antiguo no basta, su versión también debe estar disponible en o antes del corte. Un plan puede tener efecto después de t0 si ya se conocía o se supone conocido entonces. recorded_at guarda el momento real de registro y assumed_as_of identifica conocimiento hipotético. Una hipótesis no se convierte en un hecho histórico por asignarle una fecha pasada.

La antigüedad de cotización conserva el cálculo real de 2.2.0: floor de segundos transcurridos entre observación y corte dividido por 86400. No se cambia por resta de etiquetas de fecha. Los tres lags requieren meses completos consecutivos. El target requiere el cierre y certificación del mes objetivo. Si una venta fue anulada o corregida después, se necesita reconstrucción as-of o una versión nueva de etiquetas, sin reescribir el conocimiento pasado.

Las cantidades pendientes de pedidos o envíos se reconstruyen a t0. No se usa fulfilled_units, unmet_units o el saldo final de un envío como si fuera información previa. Solo se descuentan recepciones anteriores al corte cuya disponibilidad esté certificada. Stock actual no equivale a stock histórico. Los días reales sin stock del mes objetivo, la demanda latente y los resultados del modelo quedan fuera de X.

**Faltantes y elegibilidad.** Se distingue UNKNOWN de cero observado y de no aplicable. Por ejemplo, USD puede ser no aplicable al fijar un costo ya puesto en Bs. No equivale a compra gratis. Un producto sin historia no recibe tres ceros inventados. Un mes incompleto no es una fila entrenable. Los payloads negativos o inválidos se conservan solo como fixtures o rechazos de validación, separados del entrenamiento válido.

Cada ejemplo entrenable necesita target entero observado, identidad única, historia completa y variables admitidas por una política explícita. Los escenarios de interfaz sin resultado observado no se incorporan automáticamente al entrenamiento. La familia y realización controlan dependencia entre variantes, no son features. La separación temporal será por meses completos, sin split aleatorio ni reutilización del TEST consumido 2.2.0.

R01 queda completado como diseño. Ross continúa con R02 para confirmar fuentes y supuestos, después R03 para justificar mecanismos. No se deduce una elasticidad real a partir de estas definiciones. Erika puede continuar E01/E02 con tipos API y reglas semánticas. La selección final de variables, el generador nuevo, la construcción y el entrenamiento siguen pendientes de sus etapas. No se consultó Neon, generó dataset, entrenó o creó otro Markdown.

La [verificación de H4-R01](../../ml/demand/reports/v2/contracts/dictionary-scenarios-20261115-01/validation.json) registra doce pruebas nuevas y 33 aprobadas al incluir contrato y arquitectura. Se comprobaron 609 archivos protegidos. Solo cambió metadata activa permitida, sin modificar los contratos previos, datos, RAW, modelos o reportes históricos.

## 49. Entrega ampliada de Ross: fuentes, dataset e interfaz

La autorización de esta ronda permite construir un dataset nuevo cuando sea necesario. No implica sustituir el modelo aceptado, volver a evaluar TEST 2.2.0 o implementar las tareas de Erika. Ross conserva frontend y dataset. El backend, el adaptador de entrenamiento, el motor de comparación y la inferencia ampliada pertenecen a Erika.

El [registro vigente de fuentes y supuestos](../../ml/demand/v2/contracts/scenario_sources.v1.json) cierra R02 para el alcance académico sintético. La matriz inicial se conserva como evidencia histórica. Su bloqueo antiguo de M5 y Favorita fue reemplazado por las confirmaciones de acceso posteriores y sus manifests vigentes. Monash y UCI mantienen su atribución. M5 y Favorita conservan las restricciones académicas de sus competiciones. Automotive sigue fuera por licencia pendiente. No se revisaron nuevos permisos comerciales ni se redistribuyeron datos originales.

| Información | Respaldo disponible | Decisión aplicada |
|---|---|---|
| Productos y tiendas | Catálogo congelado con 56 productos válidos y tiendas 5, 6, 7 | Solo identidades. No se afirma que sea el estado actual de Neon |
| Intermitencia | Probabilidad agregada de ocurrencia de Monash | Referencia del generador, con perfiles de rotación adicionales identificados como supuestos |
| Frecuencia de cambios de precio | Estadística agregada aprobada de M5 | Referencia de frecuencia. No estima elasticidad ni traslada precios USD a Bs |
| Pedidos y cancelaciones | Semántica revisada de UCI | Referencia conceptual. El generador nuevo no ajusta un coeficiente UCI |
| Promociones y calendario | Revisión de Favorita | Límites de interpretación. El generador nuevo no ajusta un coeficiente Favorita |
| Sensibilidad al precio | No existe estimación causal propia | Perfiles asumidos 0, −0,4, −0,8 y −1,2. Son hipótesis, no elasticidades comerciales comprobadas |
| Cotización, costos, stock y plazos | No hay historia propia certificada al corte | Valores sintéticos explícitos. Nunca se rellena una cotización real con 6.96 o 1 |

El generador versionado implementa pares base e hipótesis con el mismo ruido. Incluye aumentos, reducciones y cambios de precio a mitad de mes, cotización aislada, costo aislado, importación USD con gastos Bs, stock inicial cero, compromisos mayoristas de 100 a 500 unidades, compromisos minoristas, reservas posteriores, recepción tardía y plazos largos. Un compromiso grande puede quedar sin atender por falta de stock. Su cantidad solicitada no se convierte automáticamente en ventas. Un cambio aislado de costo o cotización no fuerza un efecto en ventas si no cambian precios o disponibilidad. En importación se comprueba USD × Bs/USD + gastos Bs, sin doble conversión.

El [dataset 3.0.0](../../ml/demand/data/repuestopro_v2/3.0.0/scenarios-20261115-02/manifest.json) tiene 7.056 filas supervisadas, agrupadas en 3.528 familias de comparación. Conserva 43 columnas, de las cuales 33 son candidatas a features. No se afirma que todas deban entrar al modelo. Las 14 tablas del diccionario están representadas. `decision_outputs.csv` contiene solo la cabecera porque todavía no existe un artefacto ampliado aceptado. Se agregan un registro diario de stock y metadata de escenarios. El catálogo sigue siendo una referencia congelada, las ventas son simuladas.

El periodo simulado nuevo es octubre de 2026 a septiembre de 2028. No representa ventas futuras observadas. Octubre a diciembre de 2026 permiten formar lags. TRAIN usa enero de 2027 a marzo de 2028, con 5.040 filas. VALIDATION usa abril a junio de 2028, con 1.008. TEST nuevo queda reservado de julio a septiembre de 2028, con 1.008. Cada conjunto tiene su propio mundo de simulación y su historia previa. Todos los pares de una familia permanecen juntos. Las 7.056 filas no son 7.056 observaciones independientes. La división conserva meses completos, aproximadamente 71,43/14,29/14,29.

El build `scenarios-20261115-01` se conserva sin cambios, pero no debe usarse para entrenamiento. En la revisión se detectó que su schema mantenía marcas de diseño R01 y que la fecha de registro era un marcador fijo. El build `scenarios-20261115-02` corrige esa metadata, con generador 1.0.1, fecha real de construcción y schema materializado. La fuente exacta del primer generador y su receta se archivaron en `versions/`. No se ajustaron ventas para obtener mejores métricas. La metadata de auditoría puede reproducirse usando el `recorded_at` original del manifiesto.

La validación independiente comprueba claves, cantidades, lags consecutivos, corte temporal, cobertura de precios, costo, cotización, fórmula de importación, disponibilidad de planes, relaciones entre tablas, recepción y conservación diaria de stock. También comprueba que los efectos aislados no produzcan cambios espurios en ventas. El TEST nuevo solo recibió controles estructurales, sin predicciones, métricas o selección de modelos. Los casos ambiguos, como producto nuevo, mes incompleto o cotización desconocida, están especificados para abstención o respuesta parcial. Los casos inválidos deben rechazarse. No se inventaron targets para ellos ni se declaró que la API ya los ejecutó.

En el administrador se añadió **Preparar escenario ampliado**. Ross implementó controles para los siete grupos de cambios, política de reposición, comparación visual, tabla antes/después, advertencias, métricas guardadas y exportación JSON. Se validan cantidades, decimales, fechas America/La_Paz, reservas, pedidos y reglas económicas comprobables con entradas explícitas. La API sigue siendo la autoridad final, especialmente cuando un valor base no fue editado. Las respuestas se comprueban contra selección, snapshot, contrato, artefacto y política. Los cambios de selección o edición descartan respuestas antiguas. Un valor no disponible se conserva nulo, nunca se presenta como cero.

La interfaz usa el [contrato propuesto de capacidades](../../ml/demand/v2/contracts/scenario_capabilities.schema.json). No se implementaron esas rutas en backend. Hasta que Erika entregue capacidades y snapshots válidos, **Comparar base e hipótesis** permanece deshabilitado. No se reutiliza el bosque 2.2.0 fingiendo que considera precios o cotización. La reproducción histórica actual permanece disponible por separado. El cálculo de reposición no se ejecuta en frontend ni crea compras.

Pasaron 48 pruebas Python de diccionario, fuentes, contrato, arquitectura y generación, 270 pruebas de la suite frontend, además de 10 pruebas HTTP de predicciones y permisos. El build frontend, que incluye TypeScript, terminó correctamente. Las pruebas HTTP utilizaron una URL ficticia e inaccesible de PostgreSQL. No hubo conexión a Neon. La primera ejecución HTTP falló por una restricción de sockets del entorno y pasó al permitir únicamente la ejecución local de pruebas.

Se resolvió la revisión visual con un entorno local de fixtures. Se revisaron controles y comparación parcial en escritorio de 1280 × 720 y celular de 390 × 844. En celular, el ancho del documento coincidió con el área disponible, 382 píxeles al descontar la barra vertical. La tabla tiene desplazamiento propio. Se comprobó el mensaje de API no disponible y el botón deshabilitado. Las [capturas de escritorio](../../ml/demand/reports/v2/contracts/ross-scenarios-20261115-01/desktop-fixture.jpg) y [celular](../../ml/demand/reports/v2/contracts/ross-scenarios-20261115-01/mobile-fixture.jpg) muestran respuestas ficticias, no una integración real ni métricas de un modelo nuevo.

El [traspaso a Erika](../../ml/demand/reports/v2/contracts/ross-scenarios-20261115-01/handoff.json) identifica el build, hashes, candidatas, split y pendientes. Debe revisar SC01–SC21, adaptar las 43 columnas, seleccionar variables, entrenar con TRAIN y comparar VALIDATION. Después deberá implementar escenarios y reposición, fijar un artefacto compatible e integrar la API. Solo tras seleccionar el modelo podrá evaluar una vez el TEST nuevo. Finalmente se realizará el ensayo conjunto con roles reales. Por estas dependencias no se declara toda la ampliación de Ross ni H4 al 100 %.

No se entrenó, repitió TEST 2.2.0, tocó Neon, modificó RAW, cambió Prisma o creó otro Markdown. Se actualizaron documentos existentes y metadata activa. No se ejecutó Git, por lo que no se presenta `git status` ni `git diff --stat`. La integridad de los archivos previos se verifica con hashes.

La [revisión de candidatas en TRAIN](../../ml/demand/reports/v2/contracts/ross-scenarios-20261115-01/train_feature_review.json) encontró cuatro constantes: `cobertura_modalidad_mes_anterior`, `cobertura_stock_mes_anterior`, `reservas_horizonte_unidades` y `plazo_interno_plan_dias`. Deben excluirse del ajuste estadístico de este build. Las dos coberturas completas son controles de calidad, las reservas y el plazo interno también tienen un papel en reposición. No se supone que todo control visible deba ser un predictor. Las 33 columnas siguen siendo candidatas del diccionario, no 33 features seleccionadas.

El retraso de recepción de esta versión es un cambio de plan conocido al corte, no una distribución estimada de retrasos imprevistos. Los casos ambiguos e inválidos están definidos para el backend, todavía no ejecutados de extremo a extremo. Estas limitaciones deben conservarse al revisar R03/R04 con Erika. El dataset puede entregarse para esa revisión, pero no se declara listo para activar automáticamente un modelo ampliado.

## 50. Dashboard y diseño de predicciones

La revisión se registró el 15 de noviembre de 2026. La [evidencia técnica](../../ml/demand/reports/v2/ui/dashboard-design-20261115-01/review.json) separa la prueba del handler con Neon real de la revisión visual con fixtures. No se confunden ambas comprobaciones.

Se confirmó mediante una transacción READ ONLY que faltan `Sale.status` y `Movement.status`. El dashboard fallaba completo al filtrar ventas confirmadas. Ahora comprueba la disponibilidad de esa sección antes de consultarla. Si ventas no puede leerse por incompatibilidad de estructura, conserva inventario, movimientos y solicitudes. Devuelve `availability.sales = SCHEMA_UNAVAILABLE` y cuatro valores de ventas nulos. Las listas vacías de esa sección van acompañadas del estado de indisponibilidad. No se elimina el filtro CONFIRMED ni se muestran ceros como si fueran cifras conocidas. Los fallos de conexión y los errores ajenos a esa sección siguen devolviendo un error explícito. Una falla del catálogo básico tampoco se disfraza como éxito parcial.

El handler respondió 200 para ADMIN, TIENDA e INVENTARIO contra Neon real, dentro de una transacción con `transaction_read_only = on`. TIENDA conservó su alcance. Se verificaron el endpoint de salud local y la recarga automática del backend. La revisión de la ventana real de Brave no pudo completarse porque estaba minimizada y la interfaz de control no logró restaurarla. Las capturas visuales corresponden a un entorno de pruebas claramente identificado.

Predicciones usa ahora dos modos: **Consulta histórica** y **Escenarios**. La consulta principal reúne selectores, resultado y gráfico. La etiqueta de datos simulados permanece visible. Las limitaciones, métricas explicadas y hashes se consultan bajo demanda. Si el servicio de escenarios no está habilitado, se ocultan sus formularios inactivos y se ofrece un aviso breve con reintento. Cuando existe un contrato válido, los grupos de cambios usan etiquetas cortas y ayudas desplegables. No se retiran reglas económicas, unidades, validaciones o advertencias necesarias.

Pasaron 177 pruebas backend y 272 frontend. Una revisión final de 23 pruebas de las pantallas también pasó. Ambas compilaciones fueron correctas. Se comprobó escritorio y celular de 390 píxeles, sin desbordamiento horizontal. Los fixtures de visualización son coherentes entre sus contadores y listas, no son registros comerciales. Los 610 archivos históricos protegidos comprobados permanecen intactos, además de los checksums de los builds 3.0.0.

La reparación evita el bloqueo total del dashboard, pero no reconcilia producción. Hay diez migraciones locales y cuatro distintas registradas como aplicadas en Neon. Las consultas previas encontraron cero AuditLog con userId nulo, cero targetType nulos, cero usuarios huérfanos en auditoría y cero grupos de solicitudes abiertas duplicadas. Product.quality permanece sin valores no nulos. Dos migraciones aplicadas coinciden en bytes, otras dos coinciden al normalizar CRLF a LF. No se modificaron sus archivos.

El usuario indicó que abriría la consola de Neon. Se abrió una pestaña para que inicie sesión. Aún no se creó rama de prueba o respaldo. No se aplicó DDL, backfill, migrate deploy o migrate resolve. Primero deben comprobarse en una rama aislada todos los efectos de las migraciones parcialmente presentes. No corresponde ejecutar deploy directamente sobre producción. El cierre del dashboard con cifras de ventas completas depende de esa reconciliación. El cierre interactivo de H4 también depende de la API y del artefacto ampliado, no de este cambio visual.

No hubo entrenamiento, evaluación de TEST, cambios de datasets, RAW, modelos, Prisma o migraciones. No se crearon nuevos Markdown ni se ejecutó Git.

### Continuación de la reconciliación en rama aislada

Tras el inicio de sesión se creó la rama `pre-h4-migration-reconcile-20261115`, con datos y esquema de producción, sin eliminación automática. El [ensayo documentado](../../ml/demand/reports/v2/closure/neon-reconcile-20261115-01/review.json) registra 87 comprobaciones aprobadas y valores originales preservados en 20 tablas. Solo se completaron restricciones, defaults e índices en la rama aislada. Producción no recibió cambios.

Antes de registrar `20260909_close_schema_drift` se pidió una decisión explícita sobre conservar Product.quality vacío como LEGACY. Product.detalles ya existe. La equivalencia del destino no se presenta como un renombrado físico exacto. migrate resolve, migrate deploy, las pruebas posteriores y el respaldo productivo siguen pendientes de esa decisión y del ensayo. Esto no implementa el modelo ampliado ni cambia el dataset de H4.

### Cierre de la reconciliación productiva

La decisión pendiente del apartado anterior fue aprobada por el usuario. Se conservó Product.quality vacío como LEGACY. La rama aislada aprobó 58 comprobaciones, sin cambios de valores originales en 20 tablas. Antes de aplicar el mismo procedimiento a producción se creó el respaldo `pre-h4-production-backup-20261115`, ID `br-withered-rain-aylwpqtb`, sin eliminación automática.

Producción tiene ahora las diez migraciones aplicadas. Se registró la equivalencia aprobada de close_schema_drift con resolve y se aplicaron cinco migraciones con deploy. Las 46 comprobaciones de lectura posteriores pasaron. El dashboard devuelve ventas disponibles para ADMIN, TIENDA e INVENTARIO. La predicción conserva acceso exclusivo de ADMIN. El backend local activo responde ready. El diff solo contiene quality y la clave foránea extra de RequestHistory, ambas conservadas como excepciones conocidas. El [reporte final](../../ml/demand/reports/v2/closure/neon-reconcile-20261115-01/review.json) conserva evidencia del ensayo, aprobación, respaldo y producción.

Este cierre elimina el bloqueo de esquema del dashboard. No cierra E04 ni la API de escenarios ampliados. El modelo 2.2.0 sigue fijado, sin nuevos entrenamientos o evaluación de TEST. El dataset ampliado 3.0.0 permanece separado. Tampoco certifica los datos comerciales históricos. Se observaron lecturas del dashboard de 17 a 18 segundos, pendientes de optimización. La revisión visual con fixtures no se presenta como navegación autenticada del usuario en producción.

## 51. Cierre funcional local de escenarios 3.0.0

El usuario autorizó completar las tareas necesarias, incluidas las de backend asignadas a Erika. La responsabilidad del plan se mantiene: Ross tiene frontend y dataset, Erika tiene backend y servicio del modelo. La implementación técnica de esta continuación no se atribuye personalmente a ninguno de los dos. El estado actual de R01–R10 y E01–E09 es el de este anexo. Las entregas anteriores con estados pendientes se conservan como historia.

El [reporte de cierre](../../ml/demand/reports/v2/closure/scenario-integration-20261115-01/review.json) registra pruebas, archivos y límites. El dataset 3.0.0 ya publicado se utilizó sin cambiar sus bytes. Tiene 7.056 filas, 3.528 familias emparejadas, 56 productos y tres tiendas. No son ventas comerciales de RepuestoPro. Automotive sigue fuera por licencia. No se regeneró el dataset ni se modificaron RAW.

Se preparó un adaptador independiente. Utiliza 18 entradas numéricas y categoryId como categoría, no como una cantidad. Excluye las cuatro candidatas constantes, identificadores, controles y resultados futuros. Cotización y costo se resuelven con Decimal para validar precios o una compra USD hipotética. No se atribuye un efecto causal de esas variables sobre ventas. El plazo de proveedor y el traslado interno se usan en reposición. Los planes de llegada aportan disponibilidad y tiempo de entrada al modelo.

La imputación aprende únicamente TRAIN. LinearRegression incorpora StandardScaler ajustado en TRAIN. Los bosques no usan escalado numérico. Cada familia de dos filas tiene peso total uno. Las tres comprobaciones temporales internas usan bloques de meses completos dentro de TRAIN. VALIDATION elige la candidata, TEST no interviene en esa selección.

| Candidata | MAE en VALIDATION | RMSE | R² |
|---|---:|---:|---:|
| Baseline, último mes | 17,1071 | 33,9425 | -0,4507 |
| LinearRegression | 14,9055 | 23,3458 | 0,3137 |
| Bosque con error cuadrático | 10,8905 | 18,7816 | 0,5558 |
| Bosque con error absoluto, seleccionado | 10,4301 | 20,7903 | 0,4557 |

El bosque absoluto fue elegido por MAE, conforme al criterio académico acordado. El bosque cuadrático tiene mejor RMSE y R², por lo que esa diferencia queda visible. No se afirma que el elegido sea mejor en todas las métricas o todos los grupos. Cinco grupos de VALIDATION empeoran frente al baseline. Su detalle está en release.json.

Se fijaron artefacto, selección y política antes de abrir el TEST independiente de 3.0.0. Se evaluaron una sola vez sus 1.008 filas, agrupadas en 504 familias, de julio a septiembre de 2028. MAE fue 10,1649 unidades, RMSE 19,4837 y R² 0,4507. El baseline tuvo MAE 15,5655. La política de rangos se abstiene en seis filas. El reporte conserva tanto las métricas globales como la cobertura de 1.002 filas. No hubo ajuste posterior utilizando TEST. Los TEST anteriores no se repitieron.

El artefacto está en `ml/demand/models/v2/scenarios-model-20261115-01/model.joblib`. La selección, configuración, métricas, snapshots y experiments.csv están en `ml/demand/reports/v2/3.0.0/scenarios-model-20261115-01/`. El contrato activo es `ml/demand/v2/contracts/scenario_runtime.v1.json`. Se conservó el contrato de diseño original con su hash exacto. El contrato de ejecución permite una traza mayor para mostrar todos los campos de hasta cien pedidos y cien envíos. El manifiesto del dataset describe el estado de su publicación, anterior al entrenamiento. El estado actual del modelo se consulta en los reportes de esta entrega, sin reescribir esa evidencia histórica.

La API implementa capabilities, snapshots y preview. Solo ADMIN tiene acceso. La misma selección mantiene producto, tienda, mes, corte, artefacto y política para las dos estimaciones. Las peticiones no aceptan targets, rutas de modelos o columnas libres. Los JSON con claves duplicadas se rechazan. La idempotencia usa actor, identificador y hash canónico. Una repetición devuelve la respuesta original, un contenido distinto con la misma clave da 409. El cache de respuestas sintéticas se publica de forma atómica bajo tmp. No cambia la base operativa.

La interfaz recibe los precios base desde el servidor. Permite elegir producto, tienda y mes, editar hipótesis y comparar. Muestra qué cambios llegan al modelo y cuáles sirven para validación o reposición. Una cotización nueva no modifica automáticamente el precio de venta. Un bosque puede mantener la misma estimación ante un cambio pequeño o producir respuestas no monotónicas. La pantalla lo explica sin forzar un resultado. Fuera del rango de TRAIN se abstiene en lugar de mostrar cero.

Reposición aplica `ceil(max(pronóstico, compromisos)) + seguridad`. La posición disponible descuenta solo reservas posteriores y añade entradas elegibles. No vuelve a descontar las reservas del mismo horizonte. El mínimo y múltiplo se aplican únicamente si existe necesidad. Si la llegada del nuevo pedido o su periodo de protección supera el mes, la sugerencia queda nula. Una llegada prevista no se trata como stock recibido. El cálculo mensual no garantiza disponibilidad diaria o demanda perdida.

El dashboard añade filtros de mes y ubicación, unidades brutas y productos más vendidos. El inventario sigue siendo actual, aunque se consulte un mes anterior de ventas. Las consultas independientes se agruparon para reducir esperas, sin prometer una latencia final que no se haya medido. Neon se utilizó solo dentro de una transacción READ ONLY para contrastar los agregados. En septiembre de 2026, ADMIN filtrado a Tienda 1 y TIENDA obtuvieron diez ventas, 19 unidades y Bs 3.371. INVENTARIO global obtuvo 24 ventas, 72 unidades y Bs 26.606. Coinciden con consultas independientes. No se insertaron ventas para llenar gráficos.

Pasaron 184 pruebas backend, 274 frontend y 68 de escenarios, contrato, diccionario, generador y estructura. Total: 526. Ambos builds fueron correctos. Se revisó la interfaz con la API y el artefacto reales, usando una sesión local de prueba. Se comprobó el cambio de Bs 120 a Bs 150, la regla por mayor <= por menor, la recuperación tras un error y la reposición. En el ejemplo, la estimación pasó de 22,52 a 22,405 unidades. Es una demostración de funcionamiento, no una medición comercial o una selección de modelo. Escritorio y celular de 390 píxeles no presentaron desbordamiento horizontal. Los servidores auxiliares de revisión se detuvieron. No se afirma haber probado la sesión personal del usuario en su navegador.

R01–R10 y E01–E09 quedan implementadas y comprobadas dentro del alcance técnico local. H4-J02, el ensayo personal de Erika y Ross, debe realizarlo el equipo. Tampoco se declara aceptación del docente. H5 conserva la integración comercial definitiva, compras operativas, historia real certificada, seguimiento comercial y reentrenamiento bajo control. No se garantiza exactitud del 100 %. La limitación principal sigue siendo que ventas observadas no equivalen a demanda total.

Los 199 archivos protegidos comparados permanecieron intactos. Se conservaron datasets anteriores, modelos previos, evidencia V1 y los diez SQL de migración. No se modificó Prisma, Neon, secretos o dependencias. No hubo nuevos Markdown, Git, commit, push o despliegue de aplicación.


## Verificación en la sesión ADMIN de Ross, 16 de noviembre de 2026

Se completó el recorrido en Brave con la sesión real del usuario, sin sustituirla por una sesión de prueba. La recarga del navegador conservó ADMIN y recuperó el dashboard. La consulta histórica 2.2.0 respondió. Escenarios cargó las capacidades y referencias 3.0.0. Se verificaron cambios de producto y tienda, cantidades por modalidad, precios con vigencia, cotización con fecha, costo, stock, un pedido por mayor de diez unidades con dos reservadas, entregas y reposición.

El ejemplo de Depósito de Expansión, Tienda 3, abril de 2028, produjo 27,57 unidades tanto en la base como en la hipótesis. La pantalla explicó que el modelo puede mantener su estimación pese a cambios válidos. Al reducir el plazo del proveedor de 35 a siete días, con dos días internos, la reposición pasó de fuera del horizonte a estimación mensual. Mostró 33 unidades requeridas, 175 de posición disponible y cero sugeridas. Las 150 unidades previstas en tránsito se distinguieron del stock físico. La llegada calculada del nuevo pedido fue el 10 de abril, en America/La_Paz. Son hipótesis sintéticas, no cambios comerciales ni una nueva evaluación del modelo.

El precio por mayor de 800 frente a 750 por menor fue rechazado. El resultado anterior se retiró. Tras restaurar 637,5, la comparación volvió a responder. Se corrigió un aviso inicial prematuro de indisponibilidad para mostrar carga mientras se reciben las capacidades. Una prueba nueva cubre esa transición.

Pasaron las 278 pruebas frontend y su compilación con TypeScript. Las 184 pruebas backend y 68 de Python del cierre anterior siguen como evidencia previa, no como suites repetidas en esta revisión. Los 199 archivos protegidos conservaron sus hashes. No se modificó Neon, datasets, RAW o modelos. No se entrenó ni se repitió TEST.

Exportar abrió el diálogo de guardado JSON de Brave. La herramienta no consiguió dirigir entradas a ese diálogo nativo, por lo que se canceló. Se comprobó la generación del Blob en las pruebas automatizadas, pero no se afirma haber guardado esa descarga en el recorrido manual. Las capturas y el registro están en `ml/demand/reports/v2/closure/scenario-integration-20261115-01/actual-admin-walkthrough-20261116.json`, desde la raíz del proyecto. Esta revisión sustituye únicamente el pendiente de comprobación en la sesión personal. El ensayo conjunto del equipo y la aceptación del docente conservan su función propia.


La revisión de coherencia del 16 de noviembre de 2026 reemplaza el selector interno que mezclaba la demostración de 2026 con la inferencia de 2028. El acceso normal abre «Explorar ventas», donde producto, tienda y mes corresponden exclusivamente a los ejemplos de enero a octubre de 2026. Cambiar el mes limita la curva a ese periodo, actualiza las unidades del mes y el acumulado. La búsqueda y el orden por ventas usan esa misma tienda y mes. No se llama a inferencia desde este recorrido.

«Predecir y comparar» conserva el modelo 3.0.0 con sus meses aprobados de abril a junio de 2028. Muestra solo su historia de entrada y los pronósticos del modelo. Los datos ilustrativos de 2026 no entran en sus controles, cálculos, gráfica o peticiones. La consulta 2.2.0 permanece en «Versiones anteriores». Incorporar octubre de 2026 como mes predictivo requeriría otras entradas aprobadas. No se simula ese soporte cambiando fechas del experimento.

Se comprobaron las 168 combinaciones aprobadas de 56 productos por tres tiendas, con diez meses, enteros no negativos, reproducibilidad y suma de modalidades. Los 1.680 puntos son ilustraciones calculadas en memoria, no filas añadidas al dataset publicado. Pasaron 292 pruebas frontend y la compilación. La tabla de cambios se oculta cuando está vacía y sus detalles se despliegan a pedido. El contenedor administrativo limita el desplazamiento a su área de contenido. La revisión visual local con fixtures confirmó el fin de la página sin el espacio desplazable excesivo. No equivale a una nueva prueba de la sesión personal del usuario.

Los 203 archivos protegidos comparados conservaron sus hashes. No hubo entrenamiento, evaluación de TEST, cambios de dataset, modelos, RAW, Prisma o Neon. No se crearon Markdown. El registro de esta revisión está en `ml/demand/tmp/ux-coherence-review.json`.
