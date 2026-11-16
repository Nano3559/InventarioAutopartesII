"""Perfilado descriptivo de M5 y Favorita. Solo reportes nuevos, sin joins o modelos."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import numpy as np
import pandas as pd
from .structure import ROOT, token, inventory_digest, sha256_file, validate_contract
from .profile_sources import write_report

class Stats:
    """Conteos exactos. Cuantiles aproximados de muestra sistemática, paso 997."""
    def __init__(self):
        self.total = self.valid = self.missing = self.negative = self.zero = self.fractional = 0
        self.sum = 0.0
        self.minimum = self.maximum = None
        self.samples = []
    def add(self, values):
        a = np.asarray(values, dtype=float).ravel()
        sample = a[(-self.total) % 997::997]
        self.samples.extend(sample[np.isfinite(sample)].tolist())
        self.total += a.size
        good = np.isfinite(a)
        self.missing += int((~good).sum())
        a = a[good]
        self.valid += a.size
        if not a.size: return
        self.sum += float(a.sum())
        self.negative += int((a < 0).sum())
        self.zero += int((a == 0).sum())
        self.fractional += int((a != np.trunc(a)).sum())
        lo, hi = float(a.min()), float(a.max())
        self.minimum = lo if self.minimum is None else min(lo, self.minimum)
        self.maximum = hi if self.maximum is None else max(hi, self.maximum)
    def summary(self):
        return dict(total=self.total, valid=self.valid, missing_or_nonfinite=self.missing,
                    negative=self.negative, zero=self.zero, fractional=self.fractional,
                    minimum=self.minimum, maximum=self.maximum, mean=self.sum/self.valid if self.valid else None,
                    sum=self.sum, quantiles_approximate=dict(zip(['p50','p95','p99'],
                    np.quantile(self.samples,[.5,.95,.99]).tolist())) if self.samples else None,
                    quantile_method='Systematic positional sample every 997 values. Not an exact quantile or random sample.',
                    quantile_sample_size=len(self.samples))

def inputs(source_id, root=ROOT):
    if source_id not in ('m5_walmart','corporacion_favorita'): raise ValueError('Fuente fuera de alcance')
    manifests = list((root/'sources/manifests'/source_id).glob('*.json'))
    if len(manifests) != 1: raise ValueError('Snapshot ambiguo')
    doc = json.loads(manifests[0].read_text(encoding='utf-8'))
    validate_contract(doc,'source_manifest')
    if doc['processing_status'] != 'APPROVED_FOR_PROFILING' or doc.get('profiling_decision') != 'APPROVED_ACADEMIC_ONLY':
        raise ValueError('Fuente no habilitada')
    if doc['inventory_sha256'] != inventory_digest(doc['files']): raise ValueError('Inventario alterado')
    result = {}
    for row in doc['files']:
        path = (root/doc['raw_root']/row['relative_path']).resolve()
        if not path.is_relative_to((root/'sources/external_raw').resolve()): raise ValueError('Ruta fuera de RAW')
        if sha256_file(path) != row['sha256']: raise ValueError('RAW alterado')
        result[path.name] = path
    return result,doc

@contextmanager
def archive_stream(path):
    """tar solo escribe CSV descomprimido en un pipe. No crea archivos extraídos."""
    expected = Path(path).name.removesuffix('.7z')
    names = subprocess.run(['tar','-tf',str(path)],capture_output=True,text=True,check=True).stdout.splitlines()
    if names != [expected]: raise ValueError('Contenido inesperado del archivo comprimido')
    process = subprocess.Popen(['tar','-xOf',str(path),expected],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        yield process.stdout
        error = process.stderr.read()
        code = process.wait()
        if code: raise RuntimeError('Error de lectura 7Z: '+error.decode(errors='replace')[:200])
    finally:
        if process.poll() is None: process.terminate()
        process.stdout.close()
        process.stderr.close()
        process.wait()

def profile_m5(paths, chunk=1000):
    calendar = pd.read_csv(paths['calendar.csv'])
    dates = dict(zip(calendar['d'],calendar['date']))
    files = {}
    prefix_equal = True
    for filename in ['sales_train_validation.csv','sales_train_evaluation.csv']:
        stats=Stats();rows=0; ids=set(); pairs=set(); products=set();stores=set(); cats=set(); dup_ids=dup_pairs=0; monthly={}
        with pd.read_csv(paths[filename],chunksize=chunk) as reader:
            for frame in reader:
                days=[c for c in frame if c.startswith('d_')]
                a=frame[days].to_numpy(dtype=float); stats.add(a)
                for v in frame['id']:
                    dup_ids += v in ids; ids.add(v)
                for v in zip(frame.item_id,frame.store_id):
                    dup_pairs += v in pairs; pairs.add(v)
                products.update(frame.item_id); stores.update(frame.store_id);cats.update(frame.cat_id)
                sums=a.sum(axis=0)
                for d,v in zip(days,sums):
                    month=dates[d][:7]; monthly[month]=monthly.get(month,0)+float(v)
                rows+=len(frame)
        files[filename]=dict(series_rows=rows,unique_products=len(products),unique_stores=len(stores),categories=len(cats),
                            duplicate_ids=dup_ids,duplicate_product_store=dup_pairs,periods=len(days),
                            first_date=dates[days[0]],last_date=dates[days[-1]],units=stats.summary(),monthly_units=monthly)
        print('M5 completed '+filename,flush=True)
    with pd.read_csv(paths['sales_train_validation.csv'],chunksize=chunk) as a, pd.read_csv(paths['sales_train_evaluation.csv'],chunksize=chunk) as b:
        import itertools
        for x,y in itertools.zip_longest(a,b):
            if x is None or y is None or len(x)!=len(y): prefix_equal=False;continue
            keys=['item_id','store_id'];days=[c for c in x if c.startswith('d_')]
            prefix_equal &= x[keys].equals(y[keys]) and np.array_equal(x[days].to_numpy(),y[days].to_numpy())
    prices=pd.read_csv(paths['sell_prices.csv'],dtype={'store_id':'category','item_id':'category','wm_yr_wk':'int32'})
    st=Stats();st.add(prices.sell_price)
    price_report=dict(rows=len(prices),duplicates_product_store_week=int(prices.duplicated(['store_id','item_id','wm_yr_wk']).sum()),
                      missing_by_column={c:int(prices[c].isna().sum()) for c in prices},price=st.summary(),
                      unique_products=int(prices.item_id.nunique()),unique_stores=int(prices.store_id.nunique()),unique_weeks=int(prices.wm_yr_wk.nunique()))
    del prices
    submission_rows=sum(len(f) for f in pd.read_csv(paths['sample_submission.csv'],chunksize=10000))
    return dict(source_id='m5_walmart',sales_files=files,validation_is_exact_prefix_of_evaluation=bool(prefix_equal),
                calendar=dict(rows=len(calendar),first_date=calendar.date.min(),last_date=calendar.date.max(),duplicate_days=int(calendar.d.duplicated().sum()),
                    missing_by_column={c:int(calendar[c].isna().sum()) for c in calendar},days_with_event=int(calendar.event_name_1.notna().sum())),
                prices=price_report,submission=dict(rows=submission_rows,role='TEMPLATE_NOT_OBSERVED_SALES'),
                limitations=['Los dos históricos no son fuentes independientes. No concatenarlos.',
                    'Cero ventas no prueba cero demanda o falta de stock. No hay stock histórico certificado.',
                    'Precio semanal en USD no es costo ni cotización Bs/USD. Cambios correlacionados no demuestran causalidad.',
                    'El calendario puede llegar más lejos que las ventas etiquetadas. No inventar ventas para esos días.',
                    'Meses extremos pueden ser parciales. No equiparar 28 días a un mes calendario.',
                    'Perfil descriptivo externo sin entrenamiento ni lectura del TEST cerrado de RepuestoPro.'])

def profile_favorita(paths, chunk=250000):
    result={}; catalogs={}
    for filename in ['items.csv.7z','stores.csv.7z','oil.csv.7z','holidays_events.csv.7z','transactions.csv.7z']:
        with archive_stream(paths[filename]) as stream: frame=pd.read_csv(stream)
        entry=dict(rows=len(frame),columns=list(frame),missing_by_column={c:int(frame[c].isna().sum()) for c in frame},exact_duplicate_rows=int(frame.duplicated().sum()))
        if 'date' in frame: entry.update(first_date=str(frame.date.min()),last_date=str(frame.date.max()))
        if filename.startswith('items'):
            entry.update(unique_items=int(frame.item_nbr.nunique()),families=int(frame.family.nunique()),duplicate_item_keys=int(frame.item_nbr.duplicated().sum()));catalogs['items']=set(frame.item_nbr)
        if filename.startswith('stores'):
            entry.update(unique_stores=int(frame.store_nbr.nunique()),duplicate_store_keys=int(frame.store_nbr.duplicated().sum()));catalogs['stores']=set(frame.store_nbr)
        if filename.startswith('oil'):
            s=Stats();s.add(frame.dcoilwtico);entry['oil_reference']=s.summary()
        if filename.startswith('transactions'):
            s=Stats();s.add(frame.transactions);entry['transactions']=s.summary();entry['duplicate_date_store']=int(frame.duplicated(['date','store_nbr']).sum())
        result[filename]=entry
    for filename in ['train.csv.7z','test.csv.7z','sample_submission.csv.7z']:
        rows=missing_ids=duplicate_ids=key_dup=unknown_items=unknown_stores=0
        last_id=last_key=None; id_sorted=key_sorted=True;stats=Stats();months={};stores=set();items=set();first=last=None;promo_true=promo_false=promo_missing=0;missing={}
        with archive_stream(paths[filename]) as stream:
            with pd.read_csv(stream,chunksize=chunk) as reader:
                for frame in reader:
                    rows+=len(frame)
                    for c in frame: missing[c]=missing.get(c,0)+int(frame[c].isna().sum())
                    ids=frame.id.to_numpy();missing_ids+=int(frame.id.isna().sum());duplicate_ids+=int(frame.id.duplicated().sum())
                    if len(ids):
                        duplicate_ids+=int(last_id is not None and ids[0]==last_id)
                        id_sorted &= bool(np.all(ids[1:]>=ids[:-1])) and (last_id is None or ids[0]>=last_id);last_id=ids[-1]
                    if 'date' in frame:
                        first=min(first,str(frame.date.min())) if first else str(frame.date.min());last=max(last,str(frame.date.max())) if last else str(frame.date.max())
                        stores.update(frame.store_nbr);items.update(frame.item_nbr)
                        unknown_items+=int((~frame.item_nbr.isin(catalogs['items'])).sum());unknown_stores+=int((~frame.store_nbr.isin(catalogs['stores'])).sum())
                        if frame.item_nbr.max()>=10000000 or frame.store_nbr.max()>=1000: raise ValueError('Clave fuera de límites del control ordenado')
                        dates=frame.date.str.replace('-','',regex=False).astype('int64').to_numpy()
                        key=(dates*1000+frame.store_nbr.to_numpy())*10000000+frame.item_nbr.to_numpy()
                        key_dup+=int(frame.duplicated(['date','store_nbr','item_nbr']).sum())+int(last_key is not None and key[0]==last_key)
                        key_sorted &= bool(np.all(key[1:]>=key[:-1])) and (last_key is None or key[0]>=last_key);last_key=key[-1]
                        promo=frame.onpromotion.astype('string').str.lower();promo_true+=int(promo.eq('true').sum());promo_false+=int(promo.eq('false').sum());promo_missing+=int(promo.isna().sum())
                        by_month=frame.assign(month=frame.date.str[:7]).groupby('month',sort=False)
                        for month,group in by_month:
                            item=months.setdefault(month,dict(rows=0,net_units=0.0));item['rows']+=len(group)
                            if 'unit_sales' in group:item['net_units']+=float(group.unit_sales.sum())
                    if 'unit_sales' in frame and not filename.startswith('sample'):stats.add(frame.unit_sales)
                    if rows%5000000 < chunk:print('Favorita '+filename+' rows '+str(rows),flush=True)
        entry=dict(rows=rows,columns=list(frame),missing_by_column=missing,first_date=first,last_date=last,unique_stores=len(stores),unique_items=len(items),
                   ids_monotonic=bool(id_sorted),id_duplicates_within_chunks_and_boundary=duplicate_ids,
                   id_duplicate_check_complete=bool(id_sorted),business_keys_monotonic=bool(key_sorted),
                   business_duplicates_within_chunks_and_boundary=key_dup,business_duplicate_check_complete=bool(key_sorted) if 'date' in frame else None,
                   unknown_item_rows=unknown_items,unknown_store_rows=unknown_stores,
                   promotion=dict(true=promo_true,false=promo_false,missing=promo_missing),monthly=months)
        if filename.startswith('train'):entry['unit_sales']=stats.summary();entry['role']='OBSERVED_SALES_WITH_RETURNS'
        elif filename.startswith('test'):entry['role']='EXTERNAL_COMPETITION_FORECAST_INPUT_NO_TARGET'
        else:entry['role']='TEMPLATE_NOT_OBSERVED_SALES'
        result[filename]=entry
        print('Favorita completed '+filename+' rows '+str(rows),flush=True)
    return dict(source_id='corporacion_favorita',files=result,limitations=[
        'Los negativos no son demanda negativa. unit_sales mezcla ventas y devoluciones, sin emparejamiento transaccional certificado.',
        'Cantidades fraccionarias no equivalen a unidades enteras de repuestos.',
        'Una combinación ausente producto-tienda-fecha no se rellena automáticamente con cero.',
        'onpromotion contiene faltantes y no demuestra tamaño del descuento o efecto causal.',
        'oil es referencia de petróleo, no precio del producto, costo de compra o cotización Bs/USD.',
        'No existe precio unitario de producto en train. No derivarlo de unit_sales o de oil.',
        'Sin mezclar filas ni productos con RepuestoPro. No se exportan identificadores o filas individuales.',
        'Si claves no son monótonas, duplicados entre bloques no adyacentes quedan sin certificar. Se reporta el límite explícitamente.',
        'Los archivos test externos no son el TEST cerrado de RepuestoPro. No se utiliza ese TEST ni se entrenan modelos.'])

def run(run_id,root=ROOT):
    root=Path(root).resolve();run_id=token(run_id)
    loaded={s:inputs(s,root) for s in ['m5_walmart','corporacion_favorita']}
    out=root/'reports/v2/profiling'/run_id;out.mkdir(parents=True,exist_ok=False)
    for source,func in [('m5_walmart',profile_m5),('corporacion_favorita',profile_favorita)]:
        paths,doc=loaded[source];print('Starting '+source,flush=True)
        report=func(paths)
        for row in doc['files']:
            if sha256_file(root/doc['raw_root']/row['relative_path'])!=row['sha256']:raise ValueError('RAW cambió')
        report.update(run_id=run_id,recorded_at=datetime.now(timezone.utc).isoformat(),source_snapshot_id=doc['snapshot_id'],source_inventory_sha256=doc['inventory_sha256'],
                      purpose='DESCRIPTIVE_PROFILING_ONLY',raw_changed=False,curated_created=False,dataset_created=False,trained=False,
                      authorized_user='ROSS',private_report=True)
        write_report(out/(source+'_profile.json'),report)
    return out

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);print(run(p.parse_args().run_id))
