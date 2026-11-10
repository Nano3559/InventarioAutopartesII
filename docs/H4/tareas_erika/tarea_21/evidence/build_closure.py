"""Construye exclusivamente documentación y evidencia de auditoría T21."""
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
D = ROOT / 'docs/H4'
E = Path(__file__).resolve().parent
if '--check-paths' in sys.argv:
    for name in ('integrity_before.json', 'source_before.json', 'discovered_tests.txt', 'full_tests.txt', 'flows.json'):
        assert (E/name).is_file(), name
    for path in ('tareas_erika/organizacion/evidence/lifecycle_inventory.json',
                 'tareas_erika/organizacion/evidence/lifecycle_preservado.zip',
                 'tareas_erika/tarea_19/H4_MATRIZ_CUMPLIMIENTO_T19.csv'):
        assert (D/path).is_file(), path
    print('Entradas T21 resueltas; no se regeneró ni modificó evidencia histórica.')
    raise SystemExit(0)
if '--output-dir' not in sys.argv:
    raise SystemExit('Use --check-paths para verificar entradas o --output-dir con un destino nuevo; no sobrescribir el cierre histórico.')
DEST = Path(sys.argv[sys.argv.index('--output-dir')+1]).resolve()
if DEST.exists():
    raise SystemExit('El destino de regeneración debe ser nuevo.')
DEST.mkdir(parents=True)
def dump(path, value):
    (DEST/path.name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
before = json.loads((E/'integrity_before.json').read_bytes())
after = {p:sha(ROOT/p) for p in before}
assert before == after, 'Integridad protegida alterada'
dump(E/'integrity_after.json', after)
sources = json.loads((E/'source_before.json').read_bytes())
approved_root = D/'tareas_erika/organizacion/evidence_documental'
approved_before = json.loads((approved_root/'before.json').read_bytes())['python']
approved_edits = {r['path']:r['sha256_after'] for r in json.loads((approved_root/'reference_edits.json').read_bytes())}
assert all(sha(ROOT/p)==h or (approved_before.get(p)==h and approved_edits.get(p)==sha(ROOT/p))
           for p,h in sources.items()), 'Código Python alterado fuera de los ajustes documentales registrados'
inventory = json.loads((D/'tareas_erika/organizacion/evidence/lifecycle_inventory.json').read_bytes())
assert all(sha(ROOT/p)==h for p,h in inventory['files'].items())
assert len(list((ROOT/'ml/demand/lifecycle').rglob('*.json')))==442
archive = D/'tareas_erika/organizacion/evidence/lifecycle_preservado.zip'
assert sha(archive)==inventory['archive_sha256']
with ZipFile(archive) as z:
    assert z.testzip() is None and len(z.namelist())==442
    assert all(hashlib.sha256(z.read(p)).hexdigest()==h for p,h in inventory['files'].items())
def read_log(path):
    raw=path.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig', errors='replace')
ids = read_log(E/'discovered_tests.txt').splitlines()
ids = [s for s in ids if s.startswith('tests.')]
assert len(ids)==len(set(ids))==464
log=read_log(E/'full_tests.txt')
assert 'Ran 464 tests' in log and log.rstrip().endswith('OK')
flows=json.loads((E/'flows.json').read_bytes())
assert flows['status']=='PASSED' and len(flows['scenarios'])==8
dump(E/'final_checks.json', {'protected_files':len(after),'protected_unchanged':True,
    'python_source_files_unchanged':sum(sha(ROOT/p)==h for p,h in sources.items()),
    'documented_reference_only_changes':[p for p,h in sources.items() if sha(ROOT/p)!=h],'test_modules':21,
    'discovered_unique_tests':len(ids),'passed':464,'failed':0,'errors':0,'skipped':0,
    'lifecycle_files_unchanged':442,'zip_entries_verified':442,'zip_sha256':sha(archive),
    'flows_status':flows['status'],'closed_scenario_months':48,
    'additional_manual_closed_months':1,'inference_fit_calls':0,
    'visual_review':'NOT_PERFORMED','official_test_reevaluated':False})

rows=list(csv.DictReader((D/'tareas_erika/tarea_19/H4_MATRIZ_CUMPLIMIENTO_T19.csv').open(encoding='utf-8-sig')))
pending={
 'R11':'Ross: revisión interactiva y capturas de selectores en escritorio y pantalla estrecha.',
 'R12':'Ross: verificar edición, confirmación, invalidación y mensajes visuales.',
 'R23':'Ross: conectar baseline independiente de ACTIVE mediante el adaptador de referencias y etiquetarlo.',
 'R30':'Ross: conectar compare_reference_models a la aplicación normal, mostrar las tres salidas/abstenciones y aprobar visualmente.',
 'R34':'Ross: validar legibilidad, ejes, tablas, comparaciones, estados vacíos y errores.',
 'R45':'Aprobar previamente un protocolo real de elegibilidad con datos suficientes; mantener bloqueo mientras no exista.',
 'R52':'Ross: aceptar consumo de h4-session-1 + h4-traceability-1 y verificar descarga y visualización reales.',
 'R56':'Ross: ejecutar revisión real en escritorio y guardar capturas fechadas con versión y viewport.',
 'R57':'Ross: repetir revisión real en pantalla estrecha y documentar desbordamientos/legibilidad.',
 'R58':'Recuperar únicamente prompts originales disponibles; declarar ausencias sin reconstruir citas ni fechas.',
 'R61':'Erika y Ross: revisar conjuntamente checklist/tracking y registrar aceptación efectiva.',
 'R62':'Aportar evidencia real de ensayo/participación de ambos en exposición o defensa.',
 'R63':'Erika y Ross: validar juntos guion y demo con evidencias visuales.',
 'R73':'Implementar y verificar desglose por Escenario con n/cobertura; pendiente de tarea autorizada.'}
testgroups={
 'test_generate_synthetic.py':['R02','R03','R04','R06','R07','R09'],
 'test_ml_pipeline.py':['R08','R10','R22','R26','R35','R68'],
 'test_demand_engine.py':['R05','R13','R14','R15','R16','R17','R18','R19','R20','R38','R50','R53'],
 'test_h4_functional_fixes.py':['R17','R20','R48','R50','R69'],
 'test_pair_contexts.py':['R21','R48','R50'],
 'test_linear_regression.py':['R24'],
 'test_random_forest.py':['R25','R29'],
 'test_select_v1.py':['R27','R31'],
 'test_evaluate_v1.py':['R28'],
 'test_demand_runtime.py':['R32','R33','R46','R48','R51'],
 'test_reference_runtime.py':['R23','R30'],
 'test_ross_ui.py':['R11','R12','R34','R35','R36','R37','R54','R73'],
 'test_retraining.py':['R38','R39','R40','R41'],
 'test_model_comparison.py':['R42','R43','R44','R45','R46','R47','R48'],
 'test_lifecycle_registry.py':['R49'],
 'test_session_export.py':['R52'],
 'test_integrity.py':['R03','R55','R70'],
 'test_runtime_integration.py':['R32','R33','R54','R69','R71']}
for r in rows:
    rid=r['id']
    for k in ['archivos','evidencia']:
        r[k]=re.sub(r'ml/demand/(test_[\w]+\.py)',r'ml/demand/tests/\1',r[k])
    if r['estado']=='PENDIENTE': r['estado']='NO VERIFICADO'
    if rid in ['R50','R53']:
        r['estado']=r['cumplimiento_tecnico']='CUMPLIDO'
        r['demostracion_visual']='PENDIENTE (se evalúa en R56/R57)'
        r['evidencia']='docs/H4/tareas_erika/tarea_21/evidence/flows.json; docs/H4/tareas_erika/tarea_21/evidence/validate_flows.py'
    if rid=='R50':
        r['observaciones']='Criterio explícitamente aprobado en T17: reset deja V1 DISPONIBLE y SIN ACTIVE. T21 verifica nuevo contexto, seed 42, reloj 2026-10, escenario NORMAL, RNG reproducible y archivo de evidencia previo. No se interpreta reset como activación automática.'
    if rid=='R53':
        r['observaciones']='T21 repite seis meses por cada uno de ocho escenarios (48 cierres), más cierre manual incompleto rechazado sin mutación y completo permitido. PRODUCTO NUEVO mantiene abstención por política del escenario. No equivale a aceptación visual.'
    if rid=='R30':
        r['archivos']='ml/demand/reference_runtime.py; ml/demand/ui_panels.py; ml/demand/tests/test_reference_runtime.py'
        r['cumplimiento_tecnico']='CUMPLIDO (adaptador); PARCIAL (conexión UI normal)'
        r['observaciones']='LinearRegression real verificado y adaptador de tres referencias disponible. AppTest del adaptador pasa; streamlit_app.py no invoca compare_reference_models. Falta conexión y aceptación visual; no sustituye ACTIVE/CANDIDATE.'
    if rid=='R23': r['observaciones']='Baseline independiente de ACTIVE ya existe en reference_runtime; falta su ruta visible en la aplicación normal.'
    if rid in ['R56','R57','R62']: r['observaciones']='No hay evidencia suficiente de aceptación/participación real. AppTest no la sustituye.'
    if rid=='R58': r['archivos']='docs/H4/PROMPTS_MODELO_PREDICTIVO_H4.md; informes T10–T21'
    if rid in ['R61','R63']: r['archivos']='docs/H4/H4_CHECKLIST_VALIDACION_ROSS.md; docs/H4/H4_GUIA_EJECUCION_WINDOWS.md'
    tests=[f'ml/demand/tests/{t}' for t,reqs in testgroups.items() if rid in reqs]
    if tests: r['evidencia']='; '.join(tests+['docs/H4/tareas_erika/tarea_21/evidence/full_tests.txt']) + ('; docs/H4/tareas_erika/tarea_21/evidence/flows.json' if rid in ['R13','R14','R16','R17','R18','R21','R33','R48','R49','R50','R53','R69','R71'] else '')
    if rid in ['R03','R55','R70']: r['evidencia']+='; docs/H4/tareas_erika/tarea_21/evidence/final_checks.json'
    r['accion_pendiente']=pending.get(rid, 'Ninguna para el alcance técnico verificado.' if r['estado']=='CUMPLIDO' else 'Fuera del alcance obligatorio actual; conservar justificación de NO APLICA.')
counts=Counter(r['estado'] for r in rows)
assert counts=={'CUMPLIDO':54,'PARCIAL':11,'NO VERIFICADO':3,'NO APLICA':5}, counts
with (DEST/'H4_MATRIZ_CUMPLIMIENTO_FINAL.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
dump(E/'matrix_summary.json', {'total':73,'applicable':68,'states':dict(counts),'strict_percent':54/68*100,'method':'CUMPLIDO / aplicables; PARCIAL no suma fracciones; NO APLICA excluido'})
def cell(s): return str(s).replace('|','/').replace('\n',' ')
head='''# H4 — Matriz final auditada T21

Fecha: 2026-11-09. Fuente normativa leída: `H4_IMPLEMENTACION_MODELO_PREDICTIVO.md`; identificadores y correspondencia con las tres semanas conservados de la matriz original T14 y su mapeo de cláusulas, contrastados con T19 y código/pruebas actuales. Los IDs son de la matriz local, no numeración inventada de la guía.

73 requisitos: **54 CUMPLIDOS, 11 PARCIALES, 3 NO VERIFICADOS, 0 NO CUMPLIDOS, 5 NO APLICA**. Aplicables: 68. Cumplimiento estricto: **54/68 = 79,41 %**; parciales y no verificados no suman puntos. No es porcentaje de exactitud del modelo ni aceptación visual. Las limitaciones funcionales incompletas se clasifican PARCIAL y no se ocultan en NO APLICA.

R50 pasa a CUMPLIDO por evidencia nueva y por la política de reset aprobada explícitamente en T17: V1 disponible, SIN ACTIVE. R53 pasa a CUMPLIDO por repetición integral nueva posterior a la corrección del cierre incompleto. R30/R52 permanecen PARCIALES. La aceptación visual se controla aparte en R56/R57; no se infiere de AppTest. PENDIENTE histórico se normaliza a NO VERIFICADO cuando falta evidencia real (R56/R57/R62).

Los cinco NO APLICA conservan justificación individual: MLP opcional, baseline estacional opcional, integración productiva H5 fuera de alcance, intervalos calibrados futuros no existentes y TimeSeriesSplit adicional no autorizado como obligación. R67 no significa que exista confianza del 95 %.

El CSV compañero conserva responsable, semana, evidencia y cláusulas originales completas. Las matrices históricas no se modifican. Las pruebas `test_evaluate_v1` ejercitan fixtures temporales; no son nueva evaluación oficial TEST. Logs: `tareas_erika/tarea_21/evidence/full_tests.txt`, comprobaciones finales `tareas_erika/tarea_21/evidence/final_checks.json`, flujos `tareas_erika/tarea_21/evidence/flows.json`.

| ID | Semana / responsable | Requisito | Estado | Técnico / visual | Implementación | Prueba o evidencia | Observación | Acción pendiente |
|---|---|---|---|---|---|---|---|---|
'''
for r in rows:
    head+='| '+' | '.join(cell(s) for s in [r['id'],r['semana']+' / '+r['responsable'],r['requisito_original'],r['estado'],r['cumplimiento_tecnico']+' / '+r['demostracion_visual'],r['archivos'],r['evidencia'],r['observaciones'],r['accion_pendiente']])+' |\n'
(DEST/'H4_MATRIZ_CUMPLIMIENTO_FINAL.md').write_text(head,encoding='utf-8')
print(json.dumps({'matrix':dict(counts),'protected':len(after),'source_unchanged':sum(sha(ROOT/p)==h for p,h in sources.items()),'tests':len(ids)},ensure_ascii=True))
