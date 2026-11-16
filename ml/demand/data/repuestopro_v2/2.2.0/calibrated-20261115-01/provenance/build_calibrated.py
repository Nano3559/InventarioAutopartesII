"""Publicador local privado 2.2.0. Solo después de validación, sin entrenamiento."""
import copy
import csv
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
from .structure import ROOT,sha256_file,token
from .generate_calibrated_v1_1 import inputs,simulate,VERSION
from .generate_expanded import FILES as BASE_FILES
from .generate import write_csv
from .validate_build import canonical_hash,strict_json,split_issues
from .validate_calibrated import validate_tables

DATASET_VERSION='2.2.0'
FILES={**BASE_FILES,'calibration_audit':'calibration_audit.csv','price_events':'price_events.csv','pricing_audit':'pricing_audit.csv'}


def save_json(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def make_split(rows):
    result=dict(origin='SYNTHETIC',root_seed=42,new_v2_streams=True,random_split=False,training_authorized=False,
                test_access_status='GENERATED_AND_INTEGRITY_CHECKED_NOT_USED_FOR_SELECTION',sets={})
    for name,start,end in [('TRAIN','2025-01','2026-03'),('VALIDATION','2026-04','2026-06'),('TEST','2026-07','2026-09')]:
        selected=[r for r in rows if start<=r['mes_objetivo']<=end]
        result['sets'][name]=dict(start=start,end=end,rows=len(selected),row_content_sha256=canonical_hash(selected))
    return result


def inspect_files(path,expected_schema=None):
    """Relee JSON tipado y cada CSV sin usar el generador."""
    path=Path(path);bundle=strict_json((path/'tables.json').read_text(encoding='utf-8'))
    schema=strict_json((path/'schema.json').read_text(encoding='utf-8'))
    if expected_schema is not None and schema!=expected_schema:raise ValueError('Esquema escrito distinto')
    for table,filename in FILES.items():
        rows=bundle[table]
        if not rows:raise ValueError('Tabla vacía requiere contrato explícito: '+table)
        columns=([c['name'] for c in schema['columns']] if table=='supervised' else
                 [c['name'] for c in schema['design']['supporting_tables'][filename]['columns']] if table in ['base','audit'] else list(rows[0]))
        with (path/filename).open(encoding='utf-8',newline='') as f:
            reader=csv.DictReader(f)
            if reader.fieldnames!=columns:raise ValueError('Cabecera incorrecta: '+filename)
            count=0
            for count,row in enumerate(reader,1):
                if count>len(rows) or None in row:raise ValueError('Filas o columnas sobrantes: '+filename)
                expected={c:'' if rows[count-1][c] is None else str(rows[count-1][c]) for c in columns}
                if row!=expected:raise ValueError('CSV difiere de tabla tipada: '+filename)
            if count!=len(rows):raise ValueError('Fila ausente: '+filename)
    return bundle,schema


def verify_checksums(path):
    path=Path(path);lines=(path/'checksums.sha256').read_text(encoding='utf-8').splitlines();seen=set()
    for line in lines:
        digest,name=line.split('  ',1);target=(path/name).resolve()
        if not target.is_relative_to(path.resolve()) or name in seen or sha256_file(target)!=digest:raise ValueError('Checksum inválido: '+name)
        seen.add(name)
    actual={p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file() and p.name!='checksums.sha256'}
    if seen!=actual:raise ValueError('Inventario de archivos incompleto')
    return len(seen)


def build(build_id,root=ROOT):
    root=Path(root).resolve();build_id=token(build_id)
    target=root/'data/repuestopro_v2'/DATASET_VERSION/build_id
    staging=root/'tmp'/('publish-2.2.0-'+build_id)
    if not target.resolve().is_relative_to((root/'data/repuestopro_v2').resolve()) or not staging.resolve().is_relative_to((root/'tmp').resolve()):raise ValueError('Ruta insegura')
    if target.exists():raise FileExistsError('Build existente, no sobrescribir')
    staging.mkdir(parents=True,exist_ok=False)
    args=inputs(root);config,legacy,old_schema,catalog,prep,calibration,recipe=args
    if recipe['dataset_version']!=DATASET_VERSION or not recipe['publication_authorized'] or recipe['training_authorized']:raise ValueError('Build no autorizado')
    try:
        bundle=simulate(*args)
        first_hash=canonical_hash(bundle)
        second=simulate(*args)
        if canonical_hash(second)!=first_hash:raise ValueError('Generador no reproducible')
        del second
        schema=copy.deepcopy(old_schema);schema['design'].update(dataset_version=DATASET_VERSION,dataset_name='DATOS_SINTETICOS_DEMANDA_H4_V2_2',definition_status='GENERATED_VALIDATED_PRIVATE_ACADEMIC_BUILD',dictionary_revision='calibrated-2.2-1')
        schema['design']['publication']['build_created']=True
        schema['design']['reference_use'].update(m5_walmart='Referencia de cambios relativos y rangos de escenarios, no historia propia.',corporacion_favorita='Referencia de cola positiva y cobertura, sin mapear IDs.')
        schema['design']['future_work']=['Entrenamiento solo con autorización posterior','Mantener TEST separado de selección','No sustituir automáticamente el artefacto 2.1.0 de la API']
        split=make_split(bundle['supervised']);schema['design']['split_design']['test_status']=split['test_access_status'];schema['design']['split_design']['test_hash']=split['sets']['TEST']['row_content_sha256']
        report=validate_tables(bundle,schema,catalog,config,legacy,recipe,calibration,prep['scenario_design']['scenarios'])
        report['failures']=sorted(set(report['failures']+split_issues(bundle['supervised'],split)))
        if report['failures']:raise ValueError('Validación previa falló: '+str(report['failures']))
        for table,filename in FILES.items():
            rows=bundle[table]
            columns=([c['name'] for c in schema['columns']] if table=='supervised' else [c['name'] for c in schema['design']['supporting_tables'][filename]['columns']] if table in ['base','audit'] else list(rows[0]))
            write_csv(staging/filename,rows,columns)
        for name,value in [('tables.json',bundle),('schema.json',schema),('split_manifest.json',split),('catalog_reference.json',catalog),('generator_config.json',recipe),('calibration.json',calibration)]:save_json(staging/name,value)
        parsed,parsed_schema=inspect_files(staging,schema)
        reread=validate_tables(parsed,parsed_schema,catalog,config,legacy,recipe,calibration,prep['scenario_design']['scenarios'])
        if reread['failures'] or split_issues(parsed['supervised'],split):raise ValueError('Validación independiente de archivos falló')
        report.update(serialized_files_revalidated=True,reproducibility_sha256=first_hash,reproducible=True,local_private_publication_only=True,
                      economic_review_is_explicit_academic_assumption=True,training_authorized=False)
        save_json(staging/'validation.json',report)
        provenance=staging/'provenance';provenance.mkdir()
        source_paths=['v2/generate_calibrated_v1_1.py','v2/retail_mechanisms.py','v2/validate_calibrated.py','v2/build_calibrated.py','v2/contracts/generator.retail_extension.v1_1.json','v2/contracts/retail_transformations.v2.json','v2/contracts/calibration.v2.json','v2/contracts/expanded.v2_1.json']
        for relative in source_paths:shutil.copyfile(root/relative,provenance/Path(relative).name)
        sources={}
        for sid in ['monash_car_parts','uci_online_retail_ii','m5_walmart','corporacion_favorita']:
            manifest=next((root/'sources/manifests'/sid).glob('*.json'));doc=strict_json(manifest.read_text(encoding='utf-8'))
            sources[sid]=dict(snapshot_id=doc['snapshot_id'],raw_sha256=doc['sha256'],license=doc['license'],manifest_sha256=sha256_file(manifest))
        manifest=dict(dataset_version=DATASET_VERSION,build_id=build_id,origin='SYNTHETIC',root_seed=42,generator_version=VERSION,generator_sha256=sha256_file(root/'v2/generate_calibrated_v1_1.py'),
          config_id='generator.retail_extension.v1_1',config_sha256=sha256_file(root/'v2/contracts/generator.retail_extension.v1_1.json'),catalog_reference_sha256=sha256_file(root/'catalog_reference.json'),
          catalog_observed_at=catalog.get('observed_at',catalog.get('recorded_at')),selected_product_ids=catalog['included_product_ids'],selected_store_ids=sorted(s['id'] for s in catalog['locations'] if s['type']=='TIENDA'),
          reference_source_ids=list(sources),reference_snapshot_ids={k:v['snapshot_id'] for k,v in sources.items()},reference_raw_sha256={k:v['raw_sha256'] for k,v in sources.items()},
          compatibility_report_sha256=sha256_file(root/'reports/v2/compatibility/profile-retail-20261115-01/source_compatibility_matrix.json'),processing_versions_if_any={k:v['processing_version'] for k,v in calibration['trace']['sources'].items()},
          assumptions=recipe['assumed_mechanisms'],economic_review=recipe['economic_review'],created_at=datetime.now(timezone.utc).isoformat(),feature_sets=schema['design']['feature_sets'],split_design=split,test_access_status=split['test_access_status'],environment_versions={'python':__import__('platform').python_version()},
          training_authorized=False,automotive_status='BLOCKED_LICENSE_EXCLUDED',model_2_2_exists=False,existing_api_artifact_changed=False,source_conditions=sources,publication_scope='LOCAL_PRIVATE_ACADEMIC_NOT_PUBLIC_REDISTRIBUTION',generation_report=report['status'],counts=report['counts'])
        save_json(staging/'manifest.json',manifest)
        with (staging/'checksums.sha256').open('x',encoding='utf-8') as f:
            for p in sorted(staging.rglob('*')):
                if p.is_file() and p.name!='checksums.sha256':f.write(sha256_file(p)+'  '+p.relative_to(staging).as_posix()+'\n')
        verify_checksums(staging)
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():raise FileExistsError('Colisión de publicación')
        # Ambos destinos absolutos fueron comprobados dentro de tmp y data del módulo.
        os.rename(staging,target)
        verify_checksums(target)
        return target,report
    except Exception as exc:
        if staging.exists() and not (staging/'FAILED.json').exists():save_json(staging/'FAILED.json',{'status':'FAILED_NOT_PUBLISHED','error':str(exc)})
        raise

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-id',required=True);a=p.parse_args();path,report=build(a.build_id)
    print(json.dumps({'path':str(path),'status':report['status'],'counts':report['counts']},ensure_ascii=True))
