# H4-J02B · Continuación del ensayo de aceptación

**Estado de H4-J02: PENDIENTE DE ACEPTACIÓN.** El Plan V2 define H4-J02 como el recorrido real y ensayo conjunto. Los identificadores J02-06 a J02-12 corresponden al registro de la primera ejecución. Los sufijos de este informe identifican subcasos de continuación.

## Referencias y entorno

- Alcance y criterios: [Plan V2, línea 1829](PLAN_DE_TRABAJO_V2.md#L1829) y [guía H4 vigente](H4_IMPLEMENTACION_MODELO_PREDICTIVO.md). Contrato: [demand-scenarios-1.0.0](../../ml/demand/v2/contracts/scenarios.v1.json), en especial SC01, SC02, SC04, SC10, SC11 y SC18.
- Equivalencia comercial y diagnóstico de advertencias en [M41-06](H4_M41_06_CORRECCIONES_RUNTIME.md). Cabeceras, exportación y recuperación histórica en [M41-08](H4_M41_08_TRAZABILIDAD_RESPUESTAS.md).
- Ejecución: 17 de noviembre de 2026, zona America/La_Paz. Responsable técnico de cada fila: Codex QA. Aceptación humana: Erika y Ross. Chrome headless con perfil temporal, Vite, Express, PostgreSQL 18 local en modo de solo lectura y runtime Python congelado 4.0.0. El arranque prescindió del planificador de reposición comercial.
- Se recuperaron los cinco archivos temporales de J02 y se preservaron sus originales en [evidencia J02](evidencia/H4-J02B/J02-original/). Los casos ya aprobados de cálculo nuevo, repetición idempotente, conflicto y exportación con revisión conocida mantienen su evidencia en el [registro principal](evidencia/H4-J02B/J02-original/resultado.json), [suplemento](evidencia/H4-J02B/J02-original/suplemento.json) y [descarga original](evidencia/H4-J02B/J02-original/escenario-scenario-d1ac7925101434e7920fb652.json).

## Matriz técnica

Los cuerpos exactos, incluidas fechas y políticas, están en [resultado.json](evidencia/H4-J02B/J02B/resultado.json) bajo `checks.additional.scenarios`. Para cada escenario se guardaron predicción, reposición, advertencias e impactos cuando la API los publicó.

| ID | Subcaso e entrada | Esperado | Observado | Estado y evidencia |
| --- | --- | --- | --- | --- |
| J02-11a · SC04 | Costo 999 Bs con `SET_LANDED_COST_BS`, vigencia 1 de noviembre, precios BASE | Rechazo económico de costo superior al precio mayorista | HTTP 400 `INCOHERENT_PRICES` | PASS · `cost` |
| J02-11b | Estrés por compromiso de 100.000 unidades mayoristas, 10 de noviembre | Abstención ante compromiso fuera del dominio | HTTP 200 `OUTSIDE_TRAINING_RANGE`, pronóstico nulo y reposición `INCOMPLETE` | PASS · `spike`. El compromiso se declara como hipótesis al corte. Su resultado no mide la capacidad de anticipar un evento futuro sin señal. |
| J02-11c · SC02 | Primera observación histórica con una unidad sin modalidad, stock 3 | Abstención sin advertencia de pronóstico superior al suministro | HTTP 200 `UNKNOWN_CHANNEL_MIX`, unidades nulas, reposición `INCOMPLETE` y sin advertencia numérica residual | PASS · `unknownChannel` |
| J02-11d | Bytes incompatibles en la ruta del artefacto de un entorno aislado | HTTP 503 `INCOMPATIBLE_ARTIFACT` antes de deserializar | Código y sobre contractual correctos. Se usó el router real y una copia intacta del código Python con el archivo de prueba incompatible. | PASS · [historial y artefacto](evidencia/H4-J02B/J02B/historial-y-artefacto.json) |
| J02-10a · SC01 | Producto 999999, sin producto ni snapshot equivalente en las capacidades | Rechazo de referencia sin predicción ni historia fabricada | HTTP 409 `SNAPSHOT_MISMATCH`; el panel ofrece productos publicados | PASS · `newProduct` para no disponibilidad. Un caso de producto registrado sin historial queda BLOCKED por falta de un snapshot autorizado de ese tipo. |
| J02-10b · SC01 | Diciembre de 2026 con el snapshot publicado de noviembre | Solo se ofrece noviembre; la API rechaza la combinación | Chrome mostró solo `2026-11`; HTTP 409 `SNAPSHOT_MISMATCH` | PASS · `month`, [transiciones](evidencia/H4-J02B/J02B/transiciones-y-demora.json) |
| J02-10c | Cambiar producto 53 → 13 y tienda 6 → 5 | Cargar la referencia del par seleccionado | La API sirvió snapshots de los nuevos pares y los selectores conservaron 13/5 | PASS · [transiciones](evidencia/H4-J02B/J02B/transiciones-y-demora.json) |
| J02-11e | Retener un POST 200 de 53/6 en Chrome y cambiar a producto 13 | Mantener selección nueva y omitir el resultado viejo | Chrome canceló la solicitud al cambiar el producto. El resultado retenido no apareció en pantalla. | PASS · [transiciones](evidencia/H4-J02B/J02B/transiciones-y-demora.json), `late` |
| J02-11f · SC18 | Cuentas locales vigentes y petición sin sesión | ADMIN 200, sin sesión 401, rol no permitido 403 | ADMIN 200, anónimo 401; TIENDA e INVENTARIO iniciaron sesión con 200 y recibieron 403 al consultar capacidades | PASS · `checks.additional.roles` |
| J02-08a · SC18 | Eliminar las dos cabeceras en la entrega de un 200 real mediante DevTools | Etiquetas desconocidas y resultado, fecha y huella conservados | El panel mostró «Procedencia desconocida» y «Revisión desconocida». Conservó 87.17 en BASE e hipótesis. El JSON guardó `delivery: unknown`, `runtimeRevision: null` y los valores originales de fecha y huella. | PASS · [captura](evidencia/H4-J02B/J02B/cabeceras-ausentes.png) y [exportación](evidencia/H4-J02B/J02B/escenario-scenario-4f581dc82eff5e852764c105.json) |
| J02-08b · SC18 | Repetición de un registro de prueba en formato antiguo sin revisión | `replayed` y `unknown` con cuerpo original íntegro | Chrome leyó ambas cabeceras. Se verificó igualdad del cuerpo y de los bytes guardados en la caché aislada. | PASS · [historial y artefacto](evidencia/H4-J02B/J02B/historial-y-artefacto.json) |
| J02-12 | Aceptación personal | Erika y Ross realizan el recorrido y registran su conformidad | Pendiente de ambos integrantes | BLOCKED |

### J02-06 · Logística individual

Todos los casos partieron del snapshot sintético 53/6 de noviembre, stock 90, 50 unidades previstas y seguridad 5. Las cantidades siguientes son simuladas. Se verificó que la posición fuese stock menos reservas posteriores más entradas elegibles, que las requeridas respetasen el máximo entre pronóstico y compromiso y que la sugerencia coincidiera con la necesidad aplicando mínimo cero y múltiplo uno. Todos los casos obtuvieron HTTP 200 y `OK_MONTH_END_ESTIMATE`.

| ID | Entrada y efecto esperado | Pronóstico | Posición | Requeridas | Sugeridas | Resultado y evidencia |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| J02-06a | Reducir el primer envío a 25; 25 elegibles | 87.885 | 115 | 93 | 0 | PASS · `partial`, un impacto y aviso de recepción prevista |
| J02-06b | Postergar primer envío al 10 de diciembre; cero elegibles | 86.57 | 90 | 92 | 2 | PASS · `postponed`, un impacto de fecha |
| J02-06c | Pedido mayorista conocido de 20 el 10 de noviembre; compromiso 20 | 87.17 | 140 | 93 | 0 | PASS · `known`, cinco impactos y aviso de solapamiento |
| J02-06d | Reservar 4 del pedido de noviembre; conservar posición sin doble descuento | 87.17 | 140 | 93 | 0 | PASS · `reserveWithin`, cinco impactos y cuatro reservas dentro |
| J02-06e | Pedido mayorista de 20 el 10 de diciembre; compromiso del mes cero | 87.17 | 140 | 93 | 0 | PASS · `lateOrder`, cinco impactos |
| J02-06f | Reservar 4 del pedido de diciembre; posición 136 | 87.17 | 136 | 93 | 0 | PASS · `reserveAfter`, cinco impactos y cuatro reservas posteriores |
| J02-06g | Recepción de 25 y reservas posteriores de 4; posición 111 | 87.885 | 111 | 93 | 0 | PASS · `combined`, seis impactos y aviso de recepción prevista |

Los siete casos conservaron la advertencia de reposición mensual sin garantía diaria. El snapshot consultado antes y después coincidió. Los resultados son de la API real llamada desde Chrome. Queda para la aceptación humana comprobar en pantalla cada edición de logística y su explicación.

## Incidencias e integridad

- Incidencias del arnés corregidas: la primera pausa de red capturó el preflight `OPTIONS` en vez del `POST`; otro intento usó un selector CSS inválido tras comprobar la cancelación; el primer entorno de artefacto incompatible carecía del esquema de solicitud y por ello devolvió `MODEL_UNAVAILABLE`. La repetición añadió una copia intacta del esquema y obtuvo `INCOMPATIBLE_ARTIFACT`. Estas incidencias no se contaron como fallos del producto.
- No se identificaron fallos de producto en los subcasos ejecutados. El producto registrado sin historia requiere un caso de entrada adicional autorizado si se desea demostrar ese flujo más allá del rechazo de una referencia desconocida.
- La comprobación binaria antes y después encontró los mismos 554 archivos protegidos. SHA256 agregado `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`. SHA256 del modelo `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e`.
- Se escribieron documentos, evidencias y nuevas entradas técnicas de simulación. Las entradas históricas no se reescribieron. No se modificaron frontend, backend ni archivos protegidos. No se ejecutaron migraciones, escrituras comerciales, entrenamiento o nueva evaluación TEST. No hubo conexión a Neon.

**Dictamen técnico:** GO para los casos verificados del release 4.0.0. H4-J02 permanece pendiente de aceptación.

## Checklist de aceptación humana

- [ ] Erika verifica el SHA256 del release y contrasta los resultados y rechazos de la API local con SC01–SC21 y los registros de esta continuación.
- [ ] Ross recorre la selección de producto y tienda, comprueba el mes que ofrece 4.0.0 y vuelve a comparar tras cancelar una solicitud en curso. Verifica que el panel muestre datos de la selección vigente.
- [ ] Ambos contrastan por separado recepción parcial y postergada, reservas y pedidos. Revisan posición, requeridas, sugeridas e impactos en el panel frente a la API.
- [ ] Ambos comprueban ADMIN y al menos una cuenta no ADMIN autorizada, además del caso sin sesión.
- [ ] Ross verifica las etiquetas nueva, recuperada y desconocida y revisa el JSON descargado. Erika contrasta la fecha original, la huella de entrada y la revisión guardada.
- [ ] Ambos revisan las incidencias y los límites de alcance de esta entrega. Registran fecha, entorno, resultado y conformidad de cada integrante.
