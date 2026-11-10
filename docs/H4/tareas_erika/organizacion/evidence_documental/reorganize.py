"""Traslados documentales verificables; no modifica modelos ni lógica productiva.

Ejecutado una vez para esta reorganización. verify.py comprueba el resultado.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'ml/demand/run_tests.py').is_file())
D = ROOT/'docs/H4'
OUT = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def dump(name,data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

assert not (OUT/'before.json').exists(), 'No sobrescribir la auditoría inicial'
initial={rel(p):sha(p) for p in D.rglob('*') if p.is_file() and OUT not in p.parents}
python_before={rel(p):sha(p) for p in (ROOT/'ml/demand').rglob('*.py') if '.venv' not in p.parts}
protected=json.loads((D/'task21_evidence/integrity_before.json').read_bytes())
assert all(sha(ROOT/p)==h for p,h in protected.items())
dump('before.json',{'docs':initial,'python':python_before,'protected':protected,'gitignore_sha256':sha(ROOT/'.gitignore')})
(OUT/'git_status_before.txt').write_bytes(subprocess.check_output(['git','status','--short','--untracked-files=all'],cwd=ROOT))

moves={}
for p in D.iterdir():
    m=re.match(r'H4_TAREA_(\d+)_',p.name) or re.match(r'H4_MATRIZ_CUMPLIMIENTO_T(\d+)\.',p.name)
    if m: moves[p]=D/'tareas_erika'/f'tarea_{m[1]}'/p.name
    elif p.name in ['H4_MATRIZ_CUMPLIMIENTO.md','H4_MATRIZ_CUMPLIMIENTO.csv']:
        moves[p]=D/'tareas_erika/tarea_14'/p.name
    elif p.is_dir() and (m:=re.fullmatch(r'task(\d+)_evidence',p.name)):
        moves[p]=D/'tareas_erika'/f'tarea_{m[1]}'/'evidence'
    elif p.name=='organizacion_evidence': moves[p]=D/'tareas_erika/organizacion/evidence'
filemoves={p:(dest/p.relative_to(src) if src.is_dir() else dest)
           for src,dest in moves.items() for p in (src.rglob('*') if src.is_dir() else [src]) if p.is_file()}
assert len(filemoves)==191
assert len(set(filemoves.values()))==191
assert all(not q.exists() and q.resolve().is_relative_to(D.resolve()) for q in filemoves.values())
plan={'prefixes':{rel(p):rel(q) for p,q in moves.items()},
      'files':[{'old':rel(p),'new':rel(q),'sha256':initial[rel(p)]} for p,q in filemoves.items()]}
dump('moves.json',plan)

# rename conserva bytes y realiza el traslado completo de cada carpeta, sin borrar archivos.
for src,dest in moves.items():
    dest.parent.mkdir(parents=True,exist_ok=True)
    assert src.resolve().is_relative_to(D.resolve()) and dest.resolve().is_relative_to(D.resolve())
    src.rename(dest)
assert all(sha(ROOT/r['new'])==r['sha256'] and not (ROOT/r['old']).exists() for r in plan['files'])
dump('moves_verified.json',{'files_moved':191,'all_sha256_equal_immediately_after_move':True,'overwritten_files':0})

prefixes=sorted(plan['prefixes'].items(),key=lambda x:len(x[0]),reverse=True)
mapping={r['old']:r['new'] for r in plan['files']}
inverse={v:k for k,v in mapping.items()}
def translate(text):
    # Sustituciones simultáneas: no se vuelve a procesar una ruta ya traducida.
    for a,b in prefixes:
        text=text.replace(a,b).replace(a.replace('/','\\'),b.replace('/','\\'))
    return text
def move_path(path):
    return ROOT/mapping.get(rel(path),rel(path))
modified=[]
def save(p,text):
    old=p.read_bytes(); new=text.encode('utf-8')
    if old.startswith(b'\xef\xbb\xbf') and not new.startswith(b'\xef\xbb\xbf'): new=b'\xef\xbb\xbf'+new
    if old!=new:
        p.write_bytes(new)
        modified.append({'path':rel(p),'sha256_before_edit':hashlib.sha256(old).hexdigest(),'sha256_after':sha(p)})

# Markdown fuera de historico/: solo rutas; no se modifican valores, estados o métricas.
md=list(D.rglob('*.md'))+[ROOT/'ml/demand/README.md']
for p in md:
    if D/'historico' in p.parents or OUT in p.parents: continue
    oldp=ROOT/inverse.get(rel(p),rel(p))
    text=p.read_bytes().decode('utf-8-sig')
    def link(m):
        target=m[1]
        if target.startswith(('http:','https:','mailto:','#','codex:')): return m[0]
        part,sep,anchor=target.partition('#')
        if not part: return m[0]
        resolved=(oldp.parent/part.replace('\\','/')).resolve()
        if not resolved.is_relative_to(ROOT): return m[0]
        if resolved.is_file() or rel(resolved) in mapping or resolved.is_dir():
            dest=move_path(resolved)
            for a,b in prefixes:
                if rel(resolved)==a: dest=ROOT/b;break
            return ']('+Path(os.path.relpath(dest,p.parent)).as_posix()+(sep+anchor if sep else '')+')'
        return m[0]
    text=re.sub(r'\]\(([^)]+)\)',link,text)
    text=translate(text)
    # Referencias textuales relativas a la raíz H4 en informes, tablas y comandos.
    def bare(m):
        token=m[0]
        if token.startswith('task'):
            n=re.search(r'\d+',token)[0]
            dest=D/'tareas_erika'/f'tarea_{n}'/'evidence'
        else: dest=D/'tareas_erika/organizacion/evidence'
        return Path(os.path.relpath(dest,p.parent)).as_posix()
    text=re.sub(r'(?<![\w/\\])(?:task\d+_evidence|organizacion_evidence)(?![\w])',bare,text)
    save(p,text)

# CSV final activo: referencias actuales; snapshots CSV/JSON de tareas permanecen intactos.
p=D/'H4_MATRIZ_CUMPLIMIENTO_FINAL.csv'
save(p,translate(p.read_bytes().decode('utf-8')))

# Solo scripts de auditoría y pruebas: rutas. No se toca el motor, runtime ni interfaz.
external=[ROOT/'ml/demand'/p for p in ['validate_v1_activation.py','validate_h4_integral.py','validate_candidate_comparison.py',
    'tests/test_h4_functional_fixes.py','tests/test_model_comparison.py','tests/test_reference_runtime.py','tests/test_retraining.py']]
for p in list(D.rglob('*.py'))+external:
    if OUT in p.parents: continue
    text=translate(p.read_bytes().decode('utf-8-sig'))
    text=text.replace('ROOT = Path(__file__).resolve().parents[3]',
        'ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())')
    if D in p.parents:
        # Rutas construidas mediante DOC + sufijo en generadores históricos.
        text=re.sub(r'(["\'])task(\d+)_evidence/',lambda m:m[1]+'tareas_erika/tarea_'+m[2]+'/evidence/',text)
        text=text.replace("E = D / 'task21_evidence'","E = Path(__file__).resolve().parent")
        text=text.replace("D/'organizacion_evidence/","D/'tareas_erika/organizacion/evidence/")
        text=text.replace("D/'H4_MATRIZ_CUMPLIMIENTO_T19.csv'","D/'tareas_erika/tarea_19/H4_MATRIZ_CUMPLIMIENTO_T19.csv'")
        # Ejecución de pruebas desde rutas históricas, ahora bajo el paquete tests.
        text=text.replace('discover(str(ROOT / "ml/demand"), pattern="test_*.py")',
            'discover(str(ROOT / "ml/demand/tests"), pattern="test_*.py", top_level_dir=str(ROOT / "ml/demand"))')
        text=text.replace('from test_h4_functional_fixes import','from tests.test_h4_functional_fixes import')
        # Las rutas en snapshots congelados se consultan mediante el mapa, sin reescribir el JSON.
        if p.name=='verify_evidence.py':
            text=text.replace('assert (ROOT/path).exists()', 'assert relocated_path(ROOT/path).exists()')
            text=text.replace('ROOT/"docs/H4"/name','relocated_path(ROOT/"docs/H4"/name)')
            text=text.replace('from simulator_inputs import HERE, content_sha256',
                'from simulator_inputs import HERE, content_sha256\n'+
                'sys.path.insert(0, str(ROOT / "docs/H4/tareas_erika"))\nfrom document_paths import relocated_path')
    save(p,text)

# Solo comentario; las reglas de exclusión conservan su comportamiento.
p=ROOT/'.gitignore'
save(p,translate(p.read_bytes().decode('utf-8')))
dump('reference_edits.json',modified)
print(json.dumps({'moved':191,'reference_files_edited':len(modified)},ensure_ascii=False))
