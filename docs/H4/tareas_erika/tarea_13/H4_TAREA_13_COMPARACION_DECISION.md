# H4 — Tarea 13: comparación, rechazo, promoción de fixtures y rollback

Fecha: 9 de noviembre de 2026. Rama: erika.

## Resultado formal del candidato real

Candidato: **CAND-f3690f19436644959f2218cdc079110c**.
Entrenamiento: seis filas nuevas de una serie (producto 1, tienda 5),
enero–junio de 2027. Comparación: tres observaciones reservadas de
julio–septiembre de 2027, posteriores a ambos entrenamientos.

**Elegibilidad: INSUFFICIENT_EVIDENCE. Decisión explícita:
REJECTED_FOR_PROMOTION. El candidato real no fue promovido.**
V1 conserva su selección, artefacto congelado y evaluación TEST original.
Tres observaciones no acreditan superioridad estadística y el candidato además
tiene mayores errores descriptivos en esta reserva. No se inventaron umbrales
después de observar los resultados.

## Comparación reproducible

| Modelo | N observados | N con predicción | Cobertura | MAE | RMSE |
|---|---:|---:|---:|---:|---:|
| RandomForest V1 | 3 | 3 | 100 % | 0.9279069888581345 | 1.1202195739427763 |
| Candidato incremental | 3 | 3 | 100 % | 4.454166666666662 | 4.528384630429605 |

| Mes simulado | Observado | V1 | Candidato |
|---|---:|---:|---:|
| 2027-07 | 19 | 17.296876688478108 | 15.545833333333338 |
| 2027-08 | 20 | 19.085401144934462 | 15.545833333333338 |
| 2027-09 | 21 | 20.834001200013027 | 15.545833333333338 |

Los valores son observaciones simuladas, no ventas reales. Ambos modelos
recibieron exactamente las mismas cinco features, reconstruidas desde los
observados anteriores y en el orden oficial. No se ajustaron transformaciones
ni hiperparámetros. Se comprobaron ausencia de solape temporal y coincidencia
entre CSV y snapshot. No se consultó el TEST oficial inicial para evaluar.

R² inferencial se deja **no disponible**. Se conserva exclusivamente como
descriptivo aritmético: V1 −0.8823378407668028 y candidato −29.759401041666607.
No se interpreta como porcentaje de precisión ni como evidencia estadística.
La cobertura usa las tres solicitudes como denominador; las métricas comunes
se calculan solo donde ambos predicen. Aquí las tres filas son comunes.

Comando explícito de reproducción (crea decisiones nuevas, no reentrena):

```powershell
.\ml\demand\.venv\Scripts\python.exe -B ml/demand/validate_candidate_comparison.py
```

El comando activa V1 solo temporalmente para comparar y ejecuta rollback al
finalizar. Está separado del arranque de Streamlit y de unittest discovery.
El candidato mantiene su rol interno CANDIDATE; su rechazo se registra aparte,
sin modificar el paquete o los resultados originales de Tarea 12.

## Identidad, confianza y trazabilidad

Las nuevas ejecuciones solo se comparan si RetrainingSession las encuentra en
su registro propio de confianza. Un run_id de JSON importado no registra un
modelo. Para el candidato archivado se fijó independientemente en código la
huella binaria de su manifiesto auditado:
556bd266c53bda5aee932ec3a359a53a43a6e1c8a690e564f2c9e8d991360b0f.

Todas las huellas de datos y artefacto se verifican antes de joblib.load; se
deserializan los mismos bytes contrastados. Los CSV se cotejan con el snapshot,
se reconstruyen lags y calendario, y se comprueban versión de sklearn, esquema,
tipo de estimador, parámetros, columnas, corte y procedencia.

| Identidad | SHA256 binario |
|---|---|
| V1 | fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e |
| CANDIDATE | 481b9195d8696afae729547b7f89f82c67693cade4c09bcc00ac683821484712 |

El límite de confianza sigue siendo el código local auditado y los registros
de entrenamiento en memoria; no se afirma disponer de firmas externas.

ComparisonSession escribe registros nuevos exclusivos en decisions/<sesión>/.
Conservan identidad de ambos modelos, huellas, datos, periodo, features por fila,
predicciones, métricas, fecha, sesión y motivo. El rechazo es un segundo archivo;
no sobrescribe el registro original de comparación. Una repetición idéntica en
la misma instancia devuelve una copia del resultado registrado. Los resultados
expuestos son copias para impedir su modificación desde la interfaz.

Comparación formal: CMP-3b6df70a763c4626b439598112d66b0e.
Rechazo: DEC-bc1a594e0e06418181d2b44e64b22e3c.
Sesión: 60a54a1435134d62b247c71b8369d50c.
Los timestamps UTC exactos se conservan en la evidencia; la sesión terminó
sin ACTIVE. No existe cambio global persistido de versión activa.

## Política real bloqueada

DemandRuntime.promote_candidate() deniega incondicionalmente cualquier
solicitud y registra PROMOTION_BLOCKED. No hay flags de configuración, variables
de entorno ni parámetros de create_runtime() para cambiar esta política.
No existe una autoridad de elegibilidad real aprobada y no se introduce una
regla numérica de superioridad.

APROBADO, PROMOVER o cualquier otro campo de un JSON no autoriza nada. El
contrato h4-comparison-1 de Ross se mantiene: su decision=RECHAZADO representa
la visualización del bloqueo, y la decisión detallada INSUFFICIENT_EVIDENCE
queda en el registro separado. Un reporte importado puede mostrar APROBADO
según el contrato anterior, pero sigue siendo solo lectura, sin efecto en
ACTIVE. Esta separación fue probada.

## Demostración positiva exclusivamente con fixtures

La subclase FixturePromotionRuntime y la política positiva solo existen en
test_model_comparison.py. La app no las importa ni ofrece un selector de
políticas. El runtime productivo nunca delega su decisión a esa subclase.

La revisión del fixture exige identidad de ACTIVE y candidato, huella de datos,
revisión de cobertura, errores por grupos, reproducibilidad y un responsable
de prueba. Es un doble de revisión predefinido para probar la transición; no es
una certificación estadística ni un protocolo aplicable al candidato real.
Solo admite artefactos pequeños generados dentro de la raíz temporal del
fixture y del esquema de prueba. Se comprobó el rechazo del candidato real.

Las pruebas demostraron dos promociones aisladas, preservación de la referencia
anterior, rechazo de un fixture no elegible, rollback a la identidad anterior
y conservación de emisiones cerradas. La evidencia adicional registra esos
eventos y el retorno final a SIN ACTIVE. No se entrenó durante el rollback.

## Rollback

El runtime conserva referencias completas anteriores y ahora contrasta antes
de restaurarlas los metadatos originales, la huella del archivo y el contrato
de columnas. Si cambia el artefacto anterior se bloquea la restauración sin
reemplazar ACTIVE. No se recarga ni mezcla un scaler de otro modelo.

ObservationJournal no se modifica desde comparación, rechazo, bloqueo o
rollback. Las predicciones y meses cerrados conservan sus versiones originales.
La comparación real interceptó RandomForestRegressor.fit para fallar si se
llamaba: **cero llamadas**. Su V1 temporal fue revertida a SIN ACTIVE.

## Streamlit

Se añadieron acciones separadas COMPARAR CANDIDATE y RECHAZAR CANDIDATE,
motivo explícito y ROLLBACK LOCAL. PROMOVER CANDIDATE permanece siempre
deshabilitado y muestra la causa del bloqueo. El método del runtime también
deniega, aunque se intente saltar el control visual.

La comparación utiliza el candidato de la sesión o, si no existe, el archivado
auditado indicado claramente. Requiere un ACTIVE ya establecido explícitamente
en esa sesión; no activa V1 por pulsar COMPARAR. Conserva el comportamiento de
inicio SIN ACTIVE. La validación real usa la activación temporal autorizada
del ejecutable anterior; no deja un navegador humano con un modelo activo.

Los resultados alimentan la vista existente de Ross por parse_comparison(),
sin cambiar create_runtime(), get_active_model(), predict(features),
ObservationJournal ni el esquema público de comparación. Reset descarta el
estado de comparación/decisión local; no elimina registros guardados. Los ocho
escenarios y las acciones de predicción, generación, cierre, avance y ensayo
de reentrenamiento continúan cubiertos por la suite anterior.

## Pruebas e integridad

**375 pruebas aprobadas en 50.370 segundos: 360 anteriores y 15 nuevas.**

```powershell
.\ml\demand\.venv\Scripts\python.exe -B -m unittest discover -s ml/demand -p 'test_*.py' -q
```

Las nuevas pruebas cubren igualdad de entradas, métricas y cobertura con
abstenciones, reserva sin solape, evidencia insuficiente, archivos corruptos
rechazados antes de deserializar, registros de otra sesión, cambio de ACTIVE,
decisiones separadas, JSON sin autoridad, promoción/rechazo de fixtures,
rollback e integración AppTest con bloqueo real y reset.

Los primeros ensayos detectaron dos errores de implementación: orden alfabético
del JSON canónico frente al orden del CSV y captura mutable de la huella en el
verificador del fixture. Se corrigieron y la suite final pasó completa. No se
modificó ni debilitó ninguna prueba anterior.

AppTest se ejecutó fuera del sandbox por sus sockets locales internos. Los
entrenamientos de pruebas existentes fueron temporales y aislados. No se
reentrenó V1 ni se ejecutó la evaluación oficial TEST.

Se verificaron los 12 archivos protegidos oficiales y los 5 archivos originales
del candidato archivado antes/después: **17 archivos intactos**. También se
comprobaron dataset, catálogo y generador contra el manifiesto. No se alteraron
experiments.csv, artefactos congelados ni resultados previos. git diff --check
pasó. No hubo commits, push, acceso Neon o cambios productivos.

## Inventario y evidencia

Nuevos: model_comparison.py, test_model_comparison.py,
validate_candidate_comparison.py, decisiones nuevas bajo ml/demand/decisions/,
este informe y evidence/.

Modificados en esta tarea: demand_runtime.py (bloqueo y rollback verificado),
retraining.py (consulta de ejecuciones propias), ui_panels.py (acciones locales)
y streamlit_app.py (presentación y limpieza del estado).
Los cambios anteriores del repositorio se conservaron.

- [Validación real completa](evidence/validation-60a54a1435134d62b247c71b8369d50c.json)
- [Eventos de fixtures](evidence/fixture_validation.json)
- [Suite completa](evidence/full_tests.txt)
- [Pruebas nuevas con nombres](evidence/new_tests.txt)
- [Integridad final](evidence/integrity.json)
- [Git status acumulado](evidence/git_status.txt)
- [Git diff stat acumulado](evidence/git_diff_stat.txt)

El diff stat versionado acumulado es 4 archivos, 317 inserciones y 36
eliminaciones; no incluye los archivos sin seguimiento, incluidos los módulos
de las tareas anteriores editados aquí.

## Pendientes exactos para el cierre integral de H4

1. Autorizar y ejecutar una validación integral final de la versión completa:
   flujos mensuales prolongados, escenarios, edición/manual, abstenciones,
   errores, aislamiento, reset, comparación, rechazo y rollback.
2. Revisar visualmente la interfaz real en escritorio y pantalla estrecha:
   gráficos, estados, motivos y separación de observados/predicciones. AppTest
   no sustituye esta revisión visual ni una sesión interactiva humana.
3. Revisar conjuntamente guía oficial, checklist, tracking y log de prompts
   contra la evidencia actual; conservar las secciones históricas fechadas y
   preparar el recorrido reproducible de demo/defensa con participación del equipo.
4. Aceptar formalmente la limitación del candidato de seis filas. La ruta
   positiva está demostrada solo con fixtures; el protocolo real de elegibilidad
   sigue pendiente de aprobación previa y no es un requisito que se deba eludir
   para presentar la demo. Una eventual promoción real exige otra autorización
   y evidencia nueva suficiente; este informe no la concede.

No se inició la validación integral final ni una nueva fase de entrenamiento.
