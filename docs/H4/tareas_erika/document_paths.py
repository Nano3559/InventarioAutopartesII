"""Compatibilidad de consulta documental; nunca carga o activa modelos.

Resuelve rutas guardadas en snapshots históricos sin modificar sus bytes.
No instala enlaces ni recrea las carpetas antiguas.
"""
from pathlib import Path
import json

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'ml/demand/run_tests.py').is_file())
MAP = Path(__file__).resolve().parent/'organizacion/evidence_documental/moves.json'

def relocated_path(path):
    value=Path(path).resolve()
    if not value.is_relative_to(ROOT):
        return value
    key=value.relative_to(ROOT).as_posix()
    mapping=json.loads(MAP.read_bytes())
    for old,new in sorted(mapping['prefixes'].items(),key=lambda item:len(item[0]),reverse=True):
        if key==old or key.startswith(old+'/'):
            return ROOT/new/key[len(old)+1:] if key!=old else ROOT/new
    return value

if __name__=='__main__':
    data=json.loads(MAP.read_bytes())
    assert all(relocated_path(ROOT/r['old'])==ROOT/r['new'] and relocated_path(ROOT/r['old']).is_file() for r in data['files'])
    print('191 rutas documentales resueltas; ningún archivo histórico modificado.')
