# M41-03 — Ficha de adquisición y elegibilidad de cohortes

Plantilla para revisar una cohorte **antes de inferir o calcular métricas**. Crear una ficha por versión de la cohorte y propósito. Si se pretende usar una fuente tanto para desarrollo como para reserva final, registrar bloques separados, con sus propios manifiestos y controles de acceso. La aprobación de la ficha solo cubre la etapa y el propósito expresamente autorizados.

Referencias: [Plan V2 vigente](PLAN_DE_TRABAJO_V2.md), [guía H4](H4_IMPLEMENTACION_MODELO_PREDICTIVO.md), [M41-01](H4_M41_01_EVALUACION_OFFLINE.md), [evaluador offline](../../ml/demand/v2/offline_evaluation.py), [contrato de escenarios](../../ml/demand/v2/contracts/scenarios.v1.json), [contrato de capacidades](../../ml/demand/v2/contracts/scenario_capabilities.schema.json), [release 4.0.0](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/release.json), [split sellado](../../ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/split_manifest.json). El informe M41-02 se entregó en la conversación: dictaminó **NO-GO** para una evaluación independiente. Identificó DEMO de noviembre sin objetivo observado y los builds históricos 3.0.0 como posible material de desarrollo sintético, condicionado a autorización y revisión de linaje y compatibilidad.

## 1. Plantilla para copiar

Completar cada fila con un valor o una referencia a evidencia verificable. Usar **PENDIENTE**, **DESCONOCIDO** o **NO APLICA** con motivo, responsable y acción. Nunca rellenar una ausencia con cero. Los campos temporales requieren zona horaria y la fecha de revisión debe quedar registrada.

| ID | Campo | Valor / evidencia a registrar |
|---|---|---|
| 01 | Identificador y revisión | ID inmutable, versión del dataset de cohorte, versión de ficha, fecha de revisión y manifiesto. La versión de la cohorte es distinta de la del modelo. |
| 02 | Objetivo y uso autorizado | Medir unidades vendidas observadas del mes siguiente por producto y tienda, o especificar y justificar otro objetivo. Indicar desarrollo, calibración o reserva final. Registrar horizonte, tipo de prueba y etapa autorizada. |
| 03 | Fuente | Nombre, sistema de origen, ubicación o referencia bajo custodia, método y fecha de extracción, revisión de la fuente y diccionario de datos. |
| 04 | Responsable | Custodio de datos, responsable de extracción y responsable de validación técnica, con fecha y revisión. |
| 05 | Autorización | Referencia verificable, otorgante con autoridad, fecha, alcance, vigencia y operaciones permitidas. Guardar evidencia de la aprobación fuera de campos libres. |
| 06 | Tipo y origen | Sintético o comercial. Para sintético, registrar generador, versión, seed, realización, perfiles y supuestos. Para comercial, sistema, área y tratamiento de datos sensibles aplicable. |
| 07 | Período | Primer y último mes objetivo, ventana histórica previa, calendario y bloques de desarrollo, calibración y reserva. Identificar meses faltantes. |
| 08 | Corte | Regla de corte y registro por fila, con zona. Para el flujo mensual actual, inicio del mes objetivo en UTC−04:00. Registrar fecha de extracción por separado. |
| 09 | Cierre observado | Estado abierto/cerrado/incompleto, instante del cierre y primera disponibilidad de la revisión aceptada. Indicar fecha de auditoría y retraso de cierre. |
| 10 | Productos | IDs de origen y canónicos, correspondencia versionada, altas/bajas, variantes, unidades y excepciones. Conteo total y por mes. |
| 11 | Tiendas | IDs de origen y canónicos, período de vigencia y tipo de ubicación. Separar tiendas de almacenes. Conteo total y por mes. |
| 12 | Familias y filas | ID canónico de familia, claves, realizaciones y parentesco entre variantes. Conteos por bloque y reglas de deduplicación. |
| 13 | Variables al corte | Inventario con nombre, orden, tipo, unidad, disponibilidad, fuente, versión, derivación y tratamiento de nulos. Distinguir entrada predictiva, regla de escenario, reposición y contexto de evaluación. |
| 14 | Resultados observados | Definición, unidad, agregación por clave, fuentes y conciliación. Registrar revisiones, cero medido, faltante y estado de cierre por separado. |
| 15 | Disponibilidad de stock | Stock vendible al corte, ubicación, exclusiones y evidencia. Separar quiebres históricos conocidos al corte de quiebres realizados durante el mes objetivo. |
| 16 | Recepciones previstas | ID, cantidad neta elegible, fecha prevista, revisión del plan y cuándo estuvo disponible. Archivar la versión vigente al corte. |
| 17 | Recepciones realizadas | ID, cantidad efectivamente recibida, fecha de recepción y fecha de disponibilidad. Enlazar al plan si existe. Usar realizaciones posteriores al corte solo para conciliación o desglose, nunca para construir las entradas al corte. |
| 18 | Reservas y compromisos | ID, modalidad, cantidades pendientes y reservadas, vencimiento, revisión y fecha de disponibilidad. Separar dentro y fuera del horizonte y descartar doble conteo. |
| 19 | Faltantes y completitud | Conteos por campo, mes y par. Distinguir ausencia, cero confirmado, no aplicable y desconocido. Registrar motivos y regla de exclusión fijada antes de la inferencia. |
| 20 | Procedencia | Cadena de fuente, extracción, transformación, mapeo, snapshot y etiqueta. Por dato, registrar cuándo ocurrió, cuándo se registró y desde cuándo estuvo disponible la revisión usada. |
| 21 | Huellas | Tabla de archivo o registro, identificador, tamaño si aplica, SHA256 esperado, SHA256 comprobado, referencia independiente, fecha y revisor. Distinguir huellas binarias de huellas normalizadas si la fuente usa ambas. |
| 22 | Independencia y exposiciones | Comparar con TRAIN, VALIDATION, TEST sellado y demás cohortes ya vistas. Registrar intersecciones de objetivos/filas, claves, familias, realizaciones y usos previos, con evidencia. |
| 23 | Compatibilidad con 4.0.0 | ID y SHA256 del release, modelo, política, esquema y catálogo esperados. Mapeo de campos, orden, tipos y unidades. Registrar diferencias y dictamen del adaptador. |
| 24 | Licencia y restricciones | Evidencia de licencia o permiso interno, usos permitidos, límites de acceso, redistribución y conservación. Registrar términos pendientes de aclarar. |
| 25 | Estado y decisión | Estado, propósito aprobado o rechazado, alcance, fecha, aprobadores, referencia de decisión y vigencia. Adjuntar revisión de población, integridad y temporalidad. |
| 26 | Observaciones y bloqueos | ID de cada incidencia, criterio afectado, evidencia faltante, acción, dueño y condición de reapertura. Registrar cambios de adjudicación entre versiones. |

**Registro por variable o evento.** Repetir para las fuentes usadas en cada fila. Una fecha programada posterior al corte puede pertenecer a un plan conocido al corte. La ocurrencia de una recepción realizada es evidencia separada.

| Clave producto–tienda–mes–familia | Campo o evento y versión | Ocurrió en / fecha prevista | Registrado en | Disponible desde | Fuente y SHA256 | Rol al corte / exclusión |
|---|---|---|---|---|---|---|
| [clave] | [nombre, ID y revisión] | [instante y tipo de fecha] | [instante] | [instante o desconocido] | [referencia] | [entrada, escenario, reposición, observado o desglose] |

**Resumen de población.** Adjuntar por mes y total: pares esperados, pares identificados, cierres verificables, filas con entradas disponibles al corte, filas inelegibles por motivo, familias únicas y casos sin procedencia. Hacer un recuento separado de grupos críticos acordados. Congelar la lista de claves elegibles y su huella antes de que algún modelo produzca salidas. Cobertura y abstención son propiedades posteriores de cada modelo sobre esa lista.

## 2. Reglas de decisión

| Estado | Criterio verificable | Decisión para el uso declarado |
|---|---|---|
| **ELEGIBLE** | Uso y acceso autorizados, licencia compatible, huellas contrastadas, población y completitud según protocolo, observados maduros, reconstrucción al corte reproducible e independencia suficiente para el propósito. El esquema requerido es compatible. | Se habilita únicamente la etapa indicada en la aprobación. |
| **ELEGIBLE CON CONDICIONES** | La fuente y el alcance se identificaron, y la brecha es subsanable y acotada. Por ejemplo, falta comprobar un mapeo versionado de tienda. Debe haber dueño, evidencia exigida y criterio de salida para cada condición. | Mantener pendiente cualquier inferencia o métrica del uso condicionado. Verificar la evidencia y emitir una nueva decisión. |
| **INSUFICIENTE** | No existe objetivo maduro, cobertura de meses, pares o grupos suficiente, o evidencia que permita establecer procedencia, corte o independencia. Aplica también cuando faltan datos para siquiera medir la brecha. | Completar evidencia o replantear la población. Solo los usos distintos aprobados por separado pueden seguir. |
| **NO ELEGIBLE** | Hay incompatibilidad demostrada que invalida el propósito: permiso denegado, licencia incompatible, uso de TEST sellado, objetivos o familias ya usados para selección en una reserva final, datos futuros como entrada indispensable o huellas contradictorias sin procedencia verificable. | Excluir del uso declarado y conservar el motivo. Una fuente o propósito diferente requiere ficha propia. |

Aplicar primero exclusiones demostradas. Si la evidencia básica no alcanza para juzgar suficiencia, el estado es **INSUFICIENTE**. Reservar **ELEGIBLE CON CONDICIONES** para verificaciones acotadas sobre una fuente identificada. Una aprobación para desarrollo no acredita independencia como reserva final. Definir tamaños mínimos y grupos críticos con el protocolo de desarrollo antes de consultar la reserva. La cantidad de predicciones emitidas nunca cambia la elegibilidad de una fila.

## 3. Controles temporales y de independencia

1. **Modelo, corte y emisión.** En un flujo prospectivo, el artefacto debe estar disponible y la emisión o abstención registrada como máximo al corte. Registrar la hora real. En replay retrospectivo, preservar el corte de las entradas y la hora real de reconstrucción como campos distintos, con huella del archivo al corte y constancia del acceso a resultados. Declarar qué artefacto estaba disponible entonces y cualquier uso de uno posterior. Reportar ese caso como retrospectivo. El evaluador M41-01 actual exige `issuedAt ≤ cutoffAt`. Un replay posterior requiere aprobación y diseño de un flujo compatible antes de evaluarlo. El release 4.0.0 se registró después del corte del 1 de noviembre de 2026.
2. **Mes cerrado y lag1.** Verificar estado, cierre y primera disponibilidad de la revisión usada, con una fecha de auditoría que confirme que ya ocurrió. Para lag1, comprobar que existe el mes inmediatamente anterior, completo, con la misma clave y disponible al corte. Un cierre tardío o una corrección cargada posteriormente queda fuera de la reconstrucción original. Aplicar una regla previa para faltantes y conservar el motivo.
3. **Entradas frente a resultados.** Reconstruir solo con versiones disponibles a más tardar al corte. Separar el plan de recepción vigente de la recepción real, los compromisos conocidos de pedidos posteriores y el stock al corte del stock final. Usar información del mes objetivo únicamente como etiqueta o segmentación posterior, según el protocolo. Volumen e intermitencia se calculan con historia disponible al corte o reglas fijadas en desarrollo.
4. **Separación por familias.** Comparar inventarios de claves, familias, variantes, períodos, orígenes y usos previos. Documentar duplicados exactos y cercanos, reutilización de perfiles o realizaciones y versiones que solo cambian metadata. Las variantes de una familia permanecen juntas. Historia común legítimamente disponible puede servir de contexto si queda documentada. Un objetivo evaluado o su variante no vuelve a ser una observación final independiente por cambiarle el ID, la fecha o el hash.
5. **TEST y reserva.** Verificar exclusión del TEST congelado mediante registros de linaje, manifiestos y listados de exclusión autorizados. Registrar acceso previo, quién vio los resultados y si influyeron en decisiones. Mantener la reserva final sellada hasta congelar candidato, baselines y protocolo. Si hay dudas de solapamiento, suspender el uso de esa reserva hasta resolverlas.

## 4. Comprobación de compatibilidad

| Comprobación | Evidencia de aceptación |
|---|---|
| Producto y tienda | Cruce verificable de IDs fuente ↔ IDs canónicos, vigente en el mes. Revisar no encontrados, duplicados, altas/bajas y ubicaciones no comerciales. |
| Unidades y calendario | Unidades vendidas observadas por producto, tienda y mes, con conversiones justificadas. Confirmar moneda y unidades de precio y costo, y diferencia entre días, cantidades y proporciones. Corte, vencimientos, recepción y cierre se interpretan con la zona documentada. |
| Características | Contrastar nombres y orden con las **19 entradas** del release 4.0.0. Incluyen tres lags, seno/coseno del mes, mezcla mayorista previa, precios base, variaciones ponderadas y vigencia, días sin stock previos, stock al corte, reservas posteriores, compromisos minorista y mayorista, entradas y fecha de la primera entrada expresada como días al corte, y categoría. Registrar fórmulas, tipo, unidad, nulos, disponibilidad y verificación por campo. Cotización y costo validan hipótesis. Los plazos de proveedor y traslado pertenecen a reposición. |
| Versiones y contratos | Contrastar modelo `calendar-model-20261116-01`, dataset de referencia 4.0.0, política `SCENARIO_NONNEGATIVE_1`, contrato `demand-scenarios-1.0.0` y huellas fijadas. Solo se acredita 3.0.0 como fuente compatible si supera una revisión explícita de objetivos, calendario, corte, catálogo, derivaciones, nulos y versión del adaptador. La coincidencia de nombres de campos no acredita equivalencia. |
| Abstenciones | Documentar los rangos del release y los estados de salida previstos. Una abstención futura conserva `null` y motivo, con la fila todavía elegible si su observado satisface el protocolo. Nunca recortar un stock para aparentar soporte. |
| Origen y autoridad | Validar coincidencia entre fuente, revisión, permisos, uso y etapa. Contrastar bytes contra la referencia de hash registrada. Una huella valida identidad de contenido respecto de una referencia. El permiso y la disponibilidad al corte se prueban con su propia evidencia. |

Para un futuro traspaso a M41-01, el manifiesto debe entregar `cohortId`, `datasetVersion`, `authorizationRef` y `sources` verificadas, además de claves `productId/locationId/targetMonth/familyId` y `cutoffAt`. Tras la autorización de las etapas correspondientes se podrán asociar `modelId`, `modelSha256`, emisión, observado y momento de disponibilidad, estado y motivo, procedencia de cada componente y baseline opcional. Las variables predictivas van en un snapshot separado. La ficha previa no necesita fabricar predicciones ni asignar estados de cobertura.

## 5. Ejemplo ficticio de revisión, solo ilustrativo

**EJEMPLO FICTICIO · FIC-M41-03-A · revisión 0.** Supuesto de escritorio, sin cohorte ni archivos de datos creados. Propósito académico de desarrollo. Fuente ficticia «Registro de tienda simulada». Producto y tienda designados como `FIC-P1` y `FIC-T1`, sin mapeo canónico. Familia ficticia `FIC-F1`. Mes objetivo propuesto: febrero de 2027. Corte ilustrativo: `2027-02-01T00:00:00-04:00`. Fecha de revisión hipotética: `2027-03-03`. La ficha declara cierre y observado pendientes.

| Evidencia ilustrativa | Cómo se clasificaría |
|---|---|
| El mes previo terminó al inicio de febrero, pero su revisión se habría publicado el día 2. | El cierre previo habría ocurrido. Lag1 seguiría indisponible al corte ilustrativo. |
| Una recepción para el día 8 figuraría en un plan disponible el 30 de enero. Su eventual confirmación llegaría durante febrero. | La revisión del plan puede usarse al corte si se acredita. La recepción realizada pertenecería al registro posterior. |
| Stock, reservas, compromisos, entradas derivadas y observado carecen de fuente. | Desconocidos o pendientes. No asignar cero, crear etiqueta ni inferir. |
| Autorización, licencia, hashes e independencia carecen de evidencia. | Pendientes. El ejemplo no acredita compatibilidad ni permite usar la fuente, incluso para desarrollo. |

**Decisión ilustrativa: INSUFICIENTE.** Ross tendría que aportar fuente, autorización, mapeos y cierre verificable. Erika tendría que reproducir las entradas al corte y revisar independencia, completitud y compatibilidad. No se consignan valores observados, huellas ni aprobaciones ficticias.

## 6. Checklist de revisión y aprobación

- [ ] **Ross** identifica de dónde proviene cada dato y aporta fuente, versión, método de extracción y custodio.
- [ ] **Ross** aporta la decisión del titular o custodio autorizado, el alcance, licencia y restricciones de uso.
- [ ] **Ross** documenta qué meses están cerrados y qué observados se pueden conciliar. Registra revisiones, huecos y cobertura.
- [ ] **Erika** contrasta hashes, confirma qué versiones de las entradas existían al corte y verifica disponibilidad de lag1.
- [ ] **Ambos** documentan TRAIN, VALIDATION, TEST excluido, demás exposiciones y familias relacionadas, y deciden si el propósito puede ser desarrollo o reserva final.
- [ ] **Erika** reproduce la reconstrucción de entradas sin inferir, comprueba el esquema y clasifica el flujo prospectivo o retrospectivo. Verifica los registros de disponibilidad contra el corte.
- [ ] **Ambos** congelan población y grupos críticos antes de inferir. Registran qué falta, quién responde y qué evidencia cerrará cada condición.
- [ ] **Ross y Erika** firman el dictamen por propósito. Ross valida fuente, permisos, catálogo y cierre. Erika valida corte, independencia, compatibilidad y reproducibilidad. Adjuntan la aprobación del titular cuando corresponda y registran la etapa autorizada.

**Registro de decisión:** ficha y revisión [ ]; alcance y etapa [ ]; estado y fundamento [ ]; fecha [ ]; evidencias [ ]; bloqueos y responsables [ ]; aprobación de fuente [ ]; validación Ross [ ]; validación Erika [ ].

## 7. Bloqueos vigentes y dictamen

M41-02 no identificó una cohorte final autorizada con observados maduros, población suficiente y evidencia de entradas al corte y emisiones comparables de 4.0.0. DEMO de noviembre carece de objetivo observado. 3.0.0 requiere autorización, linaje y una comprobación de compatibilidad para cualquier uso distinto del histórico. Sigue pendiente definir y verificar un mecanismo offline autorizado para aplicar 4.0.0 a entradas nuevas, así como fijar los criterios de suficiencia en desarrollo. H4-J02 conserva su propio proceso conjunto.

**M41-03 entrega la ficha y los controles. Ninguna cohorte real queda aprobada.** El GO para inferencia y evaluación depende de una ficha real con las evidencias y autorizaciones de la etapa correspondiente. M41-04 queda pendiente de autorización.
