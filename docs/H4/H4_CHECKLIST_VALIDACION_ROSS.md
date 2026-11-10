# H4 — Checklist de aceptación manual de Ross

Estado: **pendiente; ninguna casilla acredita trabajo ya realizado**. Complementa la auditoría T21; AppTest no sustituye esta revisión. Registrar fecha/hora, commit o snapshot, versión de Python/Streamlit, ruta/entorno, viewport y persona que valida. Adjuntar capturas reales sin secretos. No activar desde JSON, entrenar V1 ni reevaluar TEST oficial.

## Preparación y portabilidad

- [ ] Revisar entrega selectiva de código, datos, dependencias, modelos, reportes y evidencia según informe T21; no asumir que untracked ya está publicado.
- [ ] Documentar o resolver en tarea aprobada la ruta absoluta del candidato archivado; conservar manifiesto original y sus hashes. No cambiar el hash para permitir una ruta.
- [ ] Preparar entorno desde README y lock; ejecutar `python -B ml/demand/run_tests.py` desde raíz. Guardar resultado, versiones y directorio real. No prometer clon limpio hasta probarlo.

Desde la raíz en PowerShell con entorno preparado:

```powershell
& .\ml\demand\.venv\Scripts\python.exe -B ml/demand/run_tests.py
& .\ml\demand\.venv\Scripts\python.exe -m streamlit run ml/demand/streamlit_app.py
```

La URL debe ser la que muestre el proceso local. El runner no requiere entrenar modelos oficiales. Para reinstalación consultar `ml/demand/README.md` y `H4_GUIA_EJECUCION_WINDOWS.md`; registrar cualquier diferencia de entorno.

## Selectores, entradas y meses — R11/R12/R34/R53/R56/R57

- [ ] En escritorio seleccionar 1/5, revisar mes inicial octubre 2026, unidades y etiquetas; editar/confirmar lags, revisar validación y mensajes de inputs inválidos.
- [ ] Comprobar que cambiar un input invalida solo una emisión pendiente según reglas; revelar/cerrar bloquea cambios retrospectivos.
- [ ] Activar V1 explícitamente con motivo; mostrar nombre/versión y alcance local por par. RF debe aparecer solo cuando está ACTIVE.
- [ ] PREDECIR → GENERAR OBSERVADO → CERRAR/AVANZAR durante seis meses: revisar reloj, lags y gráficos contra la tabla; reintentos no duplican cierres ni alteran históricos.
- [ ] Cierre manual incompleto rechazado sin avance; observación completa permite cerrar; cero conocido válido. No completar ausencias con ventas inventadas.
- [ ] Repetir NORMAL, CRECIMIENTO, CAÍDA, PICO MAYORISTA, STOCKOUT, PRODUCTO NUEVO, CAMBIO PERSISTENTE y RECUPERACIÓN. Revisar política persistente del escenario; PRODUCTO NUEVO conserva abstención mientras está seleccionado.
- [ ] STOCKOUT: observado no supera disponibilidad; no etiquetar latente como venta ni usarlo como observado exportado.
- [ ] Revisar legibilidad de ejes, unidades, leyendas, tablas, botones, mensajes de error y estados vacíos.
- [ ] Repetir con viewport estrecho y registrar dimensiones/capturas: sin controles inaccesibles, tablas ilegibles ni estados ocultos. No inferirlo de AppTest.

## Referencias — R23/R30

**Falta integración en aplicación normal:** existe el adaptador `ui_panels.compare_reference_models`, pero no una llamada en `streamlit_app.py`. Cualquier cambio de conexión debe realizarse en una tarea autorizada y conservar contratos; este checklist no implementa la conexión.

- [ ] Conectar una acción/presentación explícita para el mismo par/mes y las mismas cinco features, usando contrato T20 y adaptador existente.
- [ ] Mostrar baseline lag1 sin depender de ACTIVE; identificar LinearRegression como REFERENCE no promovible; RF V1 únicamente si está ACTIVE en ese par.
- [ ] Mostrar valor o abstención/motivo por modelo. No convertir un error o resultado negativo en una predicción inventada; respetar política del adaptador.
- [ ] Comprobar historial insuficiente, PRODUCTO NUEVO, inputs inválidos, observado ya conocido y periodo no permitido. No usar TEST inicial para la demostración.
- [ ] Guardar captura real de las tres salidas, features y modelo/versión; confirmar que no cambia ACTIVE/CANDIDATE ni emisiones previas.

## Contextos y ciclo de modelos — R21/R45/R48/R49/R50

- [ ] Con 1/5 ACTIVE, cambiar a 2/5: SIN ACTIVE y sin candidato heredado. Volver y recuperar referencia original; rollback en un par no afecta otro.
- [ ] Otra sesión debe iniciar SIN ACTIVE, sin heredar RNG mutable ni candidatos. Mismo seed puede reproducir los mismos observados; eso no implica estado compartido.
- [ ] ENSAYAR REENTRENAMIENTO insuficiente debe abstenerse. Si se demuestra con fixture, usar solo nuevos cierres 3 + 6 + 3, carpeta temporal y etiquetar la demo. No reentrenar ni sobrescribir V1.
- [ ] COMPARAR CANDIDATE muestra identidad, hashes, periodo, n, métricas y motivo. Para candidato archivado: 6 entrenadas/3 reservadas, INSUFFICIENT_EVIDENCE, sin proclamar superioridad estadística.
- [ ] RECHAZAR conserva ACTIVE y resultado original; promoción real permanece bloqueada sin ruta alternativa desde UI/JSON. No habilitar política de fixtures en aplicación normal.
- [ ] ROLLBACK muestra referencia recuperada y no modifica cierres ni emisiones antiguas.
- [ ] RESET restaura seed/reloj/escenario y deja V1 disponible SIN ACTIVE. Evidencia previa debe seguir exportable; no reactivar automáticamente.
- [ ] Comprobar registro visible/local con fecha, sesión, par, estado anterior/posterior y hashes; reruns no duplican eventos. No editar registros para corregir una inconsistencia.

## Exportación — R52

- [ ] Descargar archivo real desde interfaz, tanto con cierres como después de reset; guardar evidencia de descarga y versión de esquema.
- [ ] Confirmar compatibilidad `h4-session-1` + extensión `h4-traceability-1`. No cambiar nombres/tipos legacy. Valores desconocidos deben seguir desconocidos.
- [ ] Contrastar seed real y estado RNG por par, mes/calendario/contexto, observados cerrados con procedencia manual/generada, revisiones y predicciones emitidas contra tabla/journal.
- [ ] Confirmar modelos/versión/hashes, referencias anteriores, eventos/decisiones y snapshot previo al reset. No mezclar predicción/hipótesis/latente con observado real.
- [ ] Verificar huellas con el validador y documentar errores sin editar el archivo original. Un hash de JSON recalculado no autoriza activación ni carga de joblib.
- [ ] Ross confirma por escrito consumo de campos públicos e internos y acepta presentación/descarga. Solo entonces revisar estado global de R52.

## Cierre conjunto

- [ ] R73: implementar en tarea autorizada y verificar desglose por escenario con n/cobertura; cuatro agrupaciones actuales no lo sustituyen.
- [ ] Recuperar prompts originales disponibles y marcar ausencias, sin inventar fechas/textos.
- [ ] Revisar matriz final juntos, resolver o aceptar explícitamente pendientes sin marcar casillas retroactivas. Mantener promoción bloqueada hasta protocolo previamente aprobado.
- [ ] Ensayar demo y defensa con Erika y Ross; guardar evidencia real de participación y aceptación.
- [ ] No describir cobertura de salidas como exactitud o confianza del 95 %. No existe intervalo calibrado al 95 % en V1.

Registro de aceptación pendiente: fecha ___; entorno/viewport ___; evidencia/capturas ___; incidencias ___; Erika ___; Ross ___. La firma de este documento no autoriza por sí sola promoción real ni cambios de artefactos congelados.
