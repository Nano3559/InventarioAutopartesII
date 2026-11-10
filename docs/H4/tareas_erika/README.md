# H4 — Tareas y evidencias de Erika

Este índice organiza documentos existentes; no cambia estados de cumplimiento, métricas ni decisiones. La guía oficial, informe final, matriz final, checklist de Ross y contratos compartidos permanecen en `docs/H4/`. `historico/` permanece intacto.

| Tarea | Informe / matriz | Evidencias |
|---|---|---|
| 10 | [Runtime](tarea_10/H4_TAREA_10_INFORME.md) | [evidence](tarea_10/evidence/) |
| 11 | [Activación V1](tarea_11/H4_TAREA_11_ACTIVACION_V1.md) | [evidence](tarea_11/evidence/) |
| 12 | [Reentrenamiento](tarea_12/H4_TAREA_12_REENTRENAMIENTO.md) | [evidence](tarea_12/evidence/) |
| 13 | [Comparación y decisión](tarea_13/H4_TAREA_13_COMPARACION_DECISION.md) | [evidence](tarea_13/evidence/) |
| 14 | [Matriz original](tarea_14/H4_MATRIZ_CUMPLIMIENTO.md); el informe final compartido sigue en raíz | [evidence](tarea_14/evidence/) |
| 15 | [Correcciones](tarea_15/H4_TAREA_15_CORRECCIONES_FUNCIONALES.md), matriz T15 | [evidence](tarea_15/evidence/) |
| 17 | [Contextos por par](tarea_17/H4_TAREA_17_CONTEXTOS_POR_PAR.md), matriz T17 | [evidence](tarea_17/evidence/) |
| 18 | [Registro de decisiones](tarea_18/H4_TAREA_18_REGISTRO_VERSIONES_DECISIONES.md), matriz T18 | [evidence](tarea_18/evidence/) |
| 19 | [Exportación](tarea_19/H4_TAREA_19_EXPORTACION_TRAZABILIDAD.md), matriz T19 | [evidence](tarea_19/evidence/) |
| 20 | No existía informe T20 en el inventario; no se fabrica | [evidence](tarea_20/evidence/) |
| 21 | [Auditoría final](tarea_21/H4_TAREA_21_AUDITORIA_FINAL.md) | [evidence](tarea_21/evidence/) |
| Organización previa | Conserva inventario, pruebas y respaldo de 442 eventos | [evidence](organizacion/evidence/) |
| Reorganización documental | [Informe de traslado](organizacion/REORGANIZACION_DOCUMENTAL.md) | [evidence_documental](organizacion/evidence_documental/) |

No se creó `tarea_16/`: no había archivos de esa tarea. Los nombres y resultados históricos se conservan; esta estructura no certifica que falten o estén realizadas tareas no documentadas.

## Referencias históricas

El [mapa de traslados](organizacion/evidence_documental/moves.json) conserva las 191 rutas anteriores, destinos y SHA256 originales. Los JSON, CSV de matrices intermedias, logs, eventos, modelos de ejemplo y ZIP no se reescriben para actualizar rutas internas. Las rutas absolutas que contienen son procedencia histórica, no autorización de carga ni de activación. `document_paths.relocated_path()` permite consultar desde scripts documentales los archivos trasladados sin duplicarlos, crear enlaces ni alterar los originales.

Las rutas en Markdown activo y en la matriz final se actualizaron; los estados de la matriz final no cambiaron. Las matrices históricas CSV siguen siendo snapshots de su fecha. Para contrastar una ruta antigua consultar el mapa, no regenerar las evidencias.

## Verificación segura desde PowerShell

Desde la raíz del repositorio y con el entorno existente:

```powershell
& .\ml\demand\.venv\Scripts\python.exe -B docs/H4/tareas_erika/document_paths.py
& .\ml\demand\.venv\Scripts\python.exe -B docs/H4/tareas_erika/tarea_21/evidence/build_closure.py --check-paths
& .\ml\demand\.venv\Scripts\python.exe -B docs/H4/tareas_erika/organizacion/evidence_documental/verify.py
& .\ml\demand\.venv\Scripts\python.exe -B ml/demand/run_tests.py
```

El ensayo T21 puede repetirse **solo en un destino nuevo**:

```powershell
$h4AuditOutput = Join-Path $env:TEMP ("h4-audit-" + [guid]::NewGuid().ToString("N"))
& .\ml\demand\.venv\Scripts\python.exe -B docs/H4/tareas_erika/tarea_21/evidence/validate_flows.py --output-dir $h4AuditOutput
```

`build_closure.py --output-dir DESTINO_NUEVO` permite reconstrucción documental aislada usando evidencias existentes; no reemplaza ni actualiza el cierre oficial. Los scripts de T14/T15 son históricos: sus conteos 375/394 y diagnósticos corresponden a esas fechas. No se ejecutaron para sobrescribir snapshots con los resultados actuales. Su resolución de raíz/rutas fue actualizada, pero no se promete que una validación histórica de conteo coincida con la suite actual de 464. Tampoco se ejecutó `fixture_example.py`, que genera eventos nuevos; se conserva como código de reproducción, sin reconstruir eventos pasados.

## Conservación y Git

Se conservan códigos de auditoría, manifiestos, huellas, ejemplos, decisiones, resultados históricos, logs e intentos interrumpidos. Los logs `.txt` de esta entrega aportan evidencia fechada y no se excluyen por ser regenerables. No se añadió ninguna regla de exclusión; el comentario del respaldo en `.gitignore` solo apunta a su nueva ubicación. El respaldo ZIP y las carpetas de evidencia deben incorporarse selectivamente a Git por Ross junto con la documentación. No se realizaron staging, commits ni push.
