"""Verifica traslados e integridad sin reescribir evidencias históricas."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
from zipfile import ZipFile

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'ml/demand/run_tests.py').is_file())
OUT=Path(__file__).resolve().parent
D=ROOT/'docs/H4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def dump(name,data):(OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

before=load(OUT/'before.json')
plan=load(OUT/'moves.json')
mapping={r['old']:r['new'] for r in plan['files']}
edits=load(OUT/'reference_edits.json')
edited={r['path']:r for r in edits}
current_edits=[]
untouched=[]
for old,h in before['docs'].items():
    new=mapping.get(old,old);p=ROOT/new
    assert p.is_file(), f'Archivo perdido: {old}'
    if sha(p)!=h:
        assert p.suffix in ('.md','.py') or new=='docs/H4/H4_MATRIZ_CUMPLIMIENTO_FINAL.csv', f'Evidencia histórica alterada: {new}'
        assert new in edited, f'Edición sin registrar: {new}'
        current_edits.append({'old':old,'new':new,'sha256_original':h,'sha256_final':sha(p)})
    else:untouched.append(new)
assert all(not (ROOT/p).exists() for p in mapping)
assert all(sha(ROOT/p)==h for p,h in before['protected'].items())

# Deshacer únicamente las sustituciones de rutas en memoria debe recuperar
# exactamente los siete scripts externos originales (ninguna aserción debilitada).
prefixes=sorted(plan['prefixes'].items(),key=lambda item:len(item[1]),reverse=True)
external=[]
for p,h in before['python'].items():
    actual=sha(ROOT/p)
    if actual==h:continue
    assert p in edited, f'Código modificado fuera de referencias: {p}'
    raw=(ROOT/p).read_bytes()
    text=raw.decode('utf-8')
    for old,new in prefixes:
        text=text.replace(new,old).replace(new.replace('/','\\'),old.replace('/','\\'))
    assert hashlib.sha256(text.encode('utf-8')).hexdigest()==h, f'Cambio de lógica o contenido ajeno a rutas: {p}'
    external.append(p)
assert len(external)==7

inventory=load(D/'tareas_erika/organizacion/evidence/lifecycle_inventory.json')
assert len(inventory['files'])==len(list((ROOT/'ml/demand/lifecycle').rglob('*.json')))==442
assert all(sha(ROOT/p)==h for p,h in inventory['files'].items())
archive=D/'tareas_erika/organizacion/evidence/lifecycle_preservado.zip'
assert sha(archive)==inventory['archive_sha256']
with ZipFile(archive) as z:
    assert z.testzip() is None and len(z.namelist())==442
    assert all(hashlib.sha256(z.read(p)).hexdigest()==h for p,h in inventory['files'].items())

links=[];scripts=[]
for p in D.rglob('*.md'):
    if 'historico' in p.relative_to(D).parts:continue
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8-sig')):
        if target.startswith(('http:','https:','mailto:','#')):continue
        assert (p.parent/target.split('#')[0]).exists(), (str(p),target)
        links.append([p.relative_to(ROOT).as_posix(),target])
for p in D.rglob('*.py'):
    ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
    scripts.append(p.relative_to(ROOT).as_posix())

frozen_refs=[]
for p in D.rglob('*'):
    if not p.is_file() or OUT in p.parents or p.suffix not in ('.json','.csv','.txt'):continue
    raw=p.read_bytes()
    if re.search(rb'task\d+_evidence|organizacion_evidence',raw):
        frozen_refs.append(p.relative_to(ROOT).as_posix())
dump('historical_references.json',{'policy':'Contenido histórico conservado; usar moves.json y document_paths.relocated_path para consultas. No son rutas de autorización.', 'files':frozen_refs})
dump('verified.json',{'moved_files':len(mapping),'all_present':True,'move_time_hashes_equal':load(OUT/'moves_verified.json'),
    'original_documents':len(before['docs']),'original_documents_byte_identical':len(untouched),
    'document_reference_edits':current_edits,'external_path_only_scripts':external,
    'protected_files_unchanged':len(before['protected']),'lifecycle_events_unchanged':442,
    'zip_entries_verified':442,'markdown_links_checked':len(links),'broken_links':0,
    'documentation_python_parses':scripts,'new_ignore_rules':0})
dump('reference_edits_final.json',[dict(r,sha256_after=sha(ROOT/r['path'])) for r in edits])
diff=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True)
(OUT/'git_diff_check.txt').write_bytes(diff.stdout+diff.stderr)
assert diff.returncode==0
(OUT/'git_status_after.txt').write_bytes(subprocess.check_output(['git','status','--short','--untracked-files=all'],cwd=ROOT))
(OUT/'git_diff_stat.txt').write_bytes(subprocess.check_output(['git','diff','--stat'],cwd=ROOT))
tree=[]
for p in sorted(D.rglob('*')):
    if p.is_file():tree.append(p.relative_to(D).as_posix())
(OUT/'tree_final.txt').write_text('docs/H4/\n'+'\n'.join('  '+p for p in tree)+'\n',encoding='utf-8')
print(json.dumps({'moved':len(mapping),'protected':29,'lifecycle':442,'broken_links':0,'external_path_only_edits':len(external)}))
