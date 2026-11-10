# H4 — Tarea 15: correcciones funcionales D01, D02 y D03

Fecha: 9 de noviembre de 2026. Rama: erika. Alcance autorizado: tres defectos;
no se inició una corrección masiva del resto de H4.

## Resultado

- D01: generación independiente y reproducible por par producto/tienda/sesión.
- D02: cierres manuales incompletos bloqueados, sin avanzar ni escribir historia.
- D03: activación explícita de la V1 congelada desde la interfaz normal,
  con identidad verificada, registro local y rollback.
- **394 pruebas aprobadas en 54.742 segundos: 375 anteriores + 19 nuevas.**
- **29 archivos protegidos idénticos**. No se reentrenó V1 ni se reevaluó TEST.

## 1. Requisitos y documentación revisados

Se leyó la guía oficial, informe final T14, matriz y guía Windows. Los textos
que fundamentan estas correcciones están en §13:

- «La historia, borrador de entradas, reloj, generador aleatorio, predicciones,
  candidato y referencia ACTIVE serán independientes por sesión y por par
  producto-tienda».
- «Una misma secuencia de acciones y ediciones deberá reproducir los mismos
  resultados».
- «Sin resultado o con mes incompleto no se cierra».
- PREDECIR debe resolver una referencia ACTIVE compatible, sin aprender ni
  ejecutar fit; cada emisión conserva modelo y versión.

La autorización T15 concreta una acción normal para activar la V1 ya elegida,
manteniendo separada y bloqueada la promoción de nuevos candidatos reales.
No cambia los contratos de Ross create_runtime(), get_active_model() y
predict(features), ni el alcance local por sesión.

## 2. D01 — causa y solución del azar compartido

Antes, DemandSession tenía un único self._rng usado por todos los pares.
Generar en una tienda/producto consumía la secuencia del siguiente par,
aunque sus historiales estuvieran en diccionarios separados.

Ahora cada PairState posee su propia instancia random.Random. Su semilla
derivada es el entero SHA256 de la cadena UTF-8:

```text
H4_PAIR_RNG_V1|<seed de sesión>|<product_id>|<location_id>
```

No se utiliza hash() de Python, dependiente del proceso, ni el UUID aleatorio
de sesión, que impediría reproducir acciones con la misma seed. Las instancias
son independientes por sesión; sesiones distintas con igual seed, IDs y acciones
reproducen los mismos valores. Otra seed o par produce un flujo distinto.
Reset elimina los estados por par y recrea sus flujos deterministas.

La distribución, fórmulas y límites de los ocho escenarios se conservaron;
solo cambió la separación de secuencias. Los resultados nuevos pueden diferir
de los de T14. No se recalculó ni sobrescribió ninguna historia guardada,
dataset 1.1 o etiqueta usada por los artefactos congelados.

Evidencia sobre la serie 1/5 durante seis meses, con historia inicial normal:

| Ejecución | Observados simulados |
|---|---|
| Serie sola | 23, 24, 25, 26, 27, 26 |
| Intercalando generación de 2/5 | 23, 24, 25, 26, 27, 26 |

Además, las regresiones verifican doce meses para cada uno de los ocho
escenarios, cambio de orden de selección, seeds, reset y estado RNG del otro par.

## 3. D02 — causa y solución del cierre incompleto

La ruta REGISTRAR OBSERVADO exigía confirmar mes completo, pero AVANZAR MES
solo comprobaba si había un observado pendiente. El motor no recibía la
confirmación; esa segunda ruta podía cerrar un registro manual no confirmado.

Se añadió validate_close_month(complete=...) como preflight sin escrituras y
close_month lo ejecuta antes de cambiar estado. Comprueba resultado presente,
cantidad válida, procedencia y confirmación booleana estricta. Un cierre fallido
conserva observado pendiente, historia, reloj, fuentes y estado aleatorio.
advance_month continúa rechazando meses que no hayan sido cerrados.

Streamlit distingue:

- **MANUAL:** ambas rutas exigen la casilla de mes completo. Sin ella, cerrar
  y avanzar están deshabilitados y se muestra MES INCOMPLETO con la acción
  requerida. No se completa una venta faltante con cero ni con la predicción.
- **GENERATED:** el generador representa el resultado completo de un mes
  simulado; puede avanzar directamente, como exigían los flujos anteriores.

La cobertura mínima de cierre es un observado mensual válido del par/mes,
no disponer de predicción ML o tres lags. Se permite cerrar una abstención
de PRODUCTO NUEVO con un observado completo para acumular historia; exigir
una predicción sería incompatible con ese escenario. Cero conocido es válido.

close_current_month verifica asimismo la emisión pendiente, par, mes, valor
revelado y referencia de rotación antes de escribir en motor y diario. Una
contradicción o falta de emisión no deja el motor cerrado parcialmente.

Compatibilidad de la API local: una llamada programática explícita a
close_month() sigue declarando por defecto que su total mensual está completo,
como los fixtures/consumidores existentes. complete=False/None/1/"true" se
rechazan. Las dos rutas de Streamlit pasan siempre la condición explícita;
no utilizan ese valor por defecto para autorizar un cierre manual.
El simulador no puede certificar hechos comerciales externos a una declaración
manual del usuario; no se introduce una falsa garantía de procedencia real.

Evidencia: observado manual 10, casilla false, ambos botones deshabilitados,
cero cierres y estado intacto ante el rechazo del motor. Después de confirmar,
se cerró el mismo 10 y se avanzó a noviembre, sin inventar valores.

### Compatibilidad de presentación del cierre

La primera ejecución de las 375 pruebas encontró un fallo adicional expuesto
por la nueva secuencia: la vista cerrada ocultaba el campo de observado y dejaba
como último número un lag 22; antes coincidía casualmente con el observado.
Con el nuevo RNG el observado era 23 y la prueba existente lo detectó.

Se restauró la presentación del observado cerrado en un control deshabilitado,
tomado del registro inmutable del diario. No se cambió su valor, ni el RNG para
forzar coincidencias, ni la prueba anterior. Es una corrección acotada de la
presentación del cierre necesaria para conservar el contrato existente.

## 4. D03 — activación normal de la referencia V1

Antes, create_runtime y reconectar devolvían una instancia vacía y no había
acción normal que seleccionara V1. Los arneses anteriores inyectaban un runtime
o lo activaban desde Python, sin establecerlo en la sesión humana del navegador.

Ahora la vista de predicción contiene:

1. Motivo de activación de V1, inicialmente vacío.
2. Botón ACTIVAR V1 CONGELADA, habilitado solo con motivo y proveedor compatible.
3. La acción llama activate_v1(reason) sobre h4_runtime de esa sesión.

activate_v1 reutiliza el cargador completo y la misma ruta fija de V1: comprueba
manifiesto, SHA256 binario independiente fijado en código, huella normalizada,
esquema, contrato, estimador, parámetros y corte. No acepta rutas ni modelos
desde el formulario. Si falla, conserva la referencia anterior.

El evento nuevo es **ACTIVATE_V1**, con motivo, fecha, versión y huella completa.
Se distingue de promote_candidate(), que continúa bloqueado incondicionalmente.
El alias histórico promote_v1() se conserva para los consumidores anteriores
con su evento PROMOTE; ambos caminos verifican la misma V1 congelada.

La activación vive únicamente en la instancia de sesión. Mientras V1 está
activa su botón queda deshabilitado. ROLLBACK LOCAL requiere motivo, verifica
la referencia anterior y refresca la pantalla para evitar mostrar ACTIVE o
PREDECIR obsoletos. Reset/reconectar dejan SIN ACTIVE y requieren nueva acción.
Los eventos viven en runtime.events; no se declara registro global persistente.

### Evidencia por la ruta normal

AppTest abrió streamlit_app.py sin inyectar un proveedor activo. Escribió un
motivo y pulsó ACTIVAR V1 CONGELADA. V1 devolvió la identidad:

```text
RandomForestRegressor / V1 / corte 2026-03 / origen SIMULACION
SHA256 binario: fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e
```

Con producto 1, tienda 5 y mes simulado 2026-10, las features
[22,18,26,−1,−0] produjeron **21.773409189130824 unidades** del RandomForest
real. Son una predicción simulada, no una venta comercial. Con fit interceptado
para fallar, hubo cero llamadas. Se generó/cerró/avanzó un mes y se ejecutó
rollback: SIN ACTIVE, con el cierre previo idéntico. Otra sesión no recibió
la activación. JSON con APROBADO/PROMOVER no cambió la política de candidatos.

## 5. Pruebas y verificaciones

**19 pruebas nuevas** en test_h4_functional_fixes.py:

- Cinco de independencia RNG: ocho escenarios, intercalado, orden, seed,
  reset y estado del otro par.
- Seis del cierre: incompleto sin mutación, falta de resultado, cero válido,
  abstención con observado, contradicción del diario y falta de emisión.
- Ocho de Streamlit: dos rutas de cierre, resultado generado completo,
  activación real normal, rollback, sesiones/reset, verificación fallida y
  bloqueo de promoción desde JSON.

Suite completa final: **394 pruebas, OK, 54.742 segundos**. Incluye las
375 anteriores, sin editar ni debilitar ninguna de ellas. Los entrenamientos
existentes de tests permanecieron aislados; no entrenaron la V1 oficial ni
añadieron experimentos oficiales. AppTest se ejecutó fuera del sandbox para
permitir sus sockets internos. No se repitió la evaluación TEST oficial.

La revisión visual de navegador sigue pendiente; esta etapa aporta evidencia
funcional automatizada, sin capturas inventadas ni afirmación de revisión visual.

## 6. Matriz: cambios acotados y cálculo transparente

La [matriz T15](H4_MATRIZ_CUMPLIMIENTO_T15.md) deriva de la fotografía T14,
con los mismos 73 IDs, 125 referencias y 68 requisitos aplicables. Solo cambian:

| ID | Relación | Antes | Después | Evidencia |
|---|---|---|---|---|
| R17 | Cierre incompleto | PARCIAL | CUMPLIDO | Preflight del motor y ambos botones; confirmación posterior |
| R20 | Azar independiente por par | PARCIAL | CUMPLIDO | Igualdad sola/intercalada, ocho escenarios y reset |
| R69 | Disponer de ACTIVE en la interfaz normal | PARCIAL | CUMPLIDO | Motivo y botón real, inferencia y rollback sin inyección |

Resultado: **50 cumplidos, 15 parciales, 3 pendientes y 5 no aplicables**.
Porcentaje estricto: 50/68 = **73.53 %**, frente a 47/68 = 69.12 % en T14.
La diferencia corresponde exactamente a tres requisitos; no se alteraron
denominador, pesos o estados no cubiertos. El cálculo alternativo de medio punto
por parcial sería 84.56 %; no equivale a aceptación o nota académica.

R53 se conserva parcial hasta una nueva revisión integral de su alcance,
aunque D02 ya esté corregido. R56/R57 visuales siguen pendientes. No se otorga
crédito por una demo humana, defensa o registro completo no verificados.
La matriz original y los resultados T14 se preservan con enlaces a esta revisión.

## 7. Archivos de esta etapa

Modificados de implementación:

- ml/demand/demand_engine.py: RNG por par y validación previa de cierre.
- ml/demand/demand_runtime.py: activate_v1 y ruta común de verificación.
- ml/demand/ui_panels.py: botón/motivo V1, cierre validado y presentación congelada.
- ml/demand/streamlit_app.py: limpieza de las claves nuevas en reset.

Modificados documentales: H4_GUIA_EJECUCION_WINDOWS.md (procedimiento actual),
H4_INFORME_FINAL.md y H4_MATRIZ_CUMPLIMIENTO.md (solo notas de revisión histórica).

Nuevos: test_h4_functional_fixes.py, este informe,
H4_MATRIZ_CUMPLIMIENTO_T15.md/.csv y evidence/ con registros y herramientas
de verificación. No se modificaron backend/frontend productivo, mobile o Prisma.

## 8. Integridad y evidencia

Los 29 archivos protegidos se contrastaron antes/después contra T14: dataset
1.1 y versión previa, catálogo, generadores, modelos LR/V1, manifiestos,
reporte TEST, experiments.csv, candidato archivado y sus decisiones. Se
conservaron además las referencias independientes de identidad V1 y candidato.
No se sobrescribió un artefacto ni se promovió el candidato real.

- [Evidencia funcional normal](evidence/functional_validation.json)
- [Suite completa final](evidence/full_tests.txt)
- [19 regresiones detalladas](evidence/new_tests.txt)
- [Integridad final](evidence/integrity_after.json)
- [Comparación de matriz](evidence/matrix.json)
- [Git status acumulado](evidence/git_status.txt)
- [Git diff stat acumulado](evidence/git_diff_stat.txt)
- [Guía Windows actualizada](../../H4_GUIA_EJECUCION_WINDOWS.md)

git diff --check pasó. No hubo commits, push, cambios de datos históricos,
reentrenamiento V1 ni evaluación TEST oficial. El diff stat acumulado incluye
cambios de tareas anteriores y excluye archivos sin seguimiento; el inventario
anterior identifica lo propio de T15.
Resultado acumulado de git diff --stat: cuatro archivos versionados,
360 inserciones y 38 eliminaciones. Los módulos aún sin seguimiento y la
documentación nueva/modificada sin seguimiento se detallan en git status.

## 9. Pendientes fuera de esta etapa

Revisión visual escritorio/pantalla estrecha; revisión integral posterior;
referencias ACTIVE/candidato por par; registro/exportación completos; desgloses
por escenario; integración LR/baseline restante; reconciliación de guía,
tracking/prompts y ensayo/defensa conjunta. Los intervalos 95 % siguen como
mejora futura sin calibración independiente. La promoción real de candidatos
sigue bloqueada hasta aprobación previa de su protocolo y evidencia suficiente.

Para aplicar esta versión a un servidor/sesión ya abiertos, reiniciar el
servidor y comenzar una sesión nueva o restablecerla expresamente. No se migran
ni reescriben cierres anteriores para que coincidan con el RNG nuevo.

Se detiene el trabajo al completar las tres correcciones autorizadas. No se
inicia la corrección masiva de los demás requisitos ni una promoción real.
