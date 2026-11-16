"""Verificación independiente de Parquet y perfiles congelados. No entrena."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from .structure import ROOT, sha256_file, validate_contract, token
from .profile_retail import inputs
from .profile_sources import write_report

def require(condition,message):
    if not condition:raise ValueError(message)

def tables(path):
    for b in pq.ParquetFile(path).iter_batches(batch_size=200000):yield b.to_pandas()

def check_manifest(out,source,root=ROOT):
    require(not (out/'FAILED.json').exists(),'Ejecución fallida')
    m=json.loads((out/'manifest.json').read_text(encoding='utf-8'));validate_contract(m,'curated_manifest')
    require(m['source_id']==source,'Fuente inesperada');_,original=inputs(source,root)
    require(m['original_inventory_sha256']==original['inventory_sha256'],'RAW distinto')
    require(m['original_files']==original['files'],'Inventario original alterado')
    require(sha256_file(root/m['script'])==m['script_sha256'],'Script cambió')
    require(sha256_file(root/m['parameters']['rules_contract_path'])==m['parameters']['rules_contract_sha256'],'Reglas cambiaron')
    for n,h in m['parameters']['dependency_hashes'].items():require(sha256_file(root/n)==h,'Dependencia cambió')
    require({p.name for p in out.iterdir()}=={'manifest.json'}|{v['relative_path'] for v in m['outputs']},'Archivos extra o faltantes')
    for f in m['outputs']:
        p=out/f['relative_path'];require(p.resolve().is_relative_to(out.resolve()),'Ruta fuera de curated')
        require(p.stat().st_size==f['file_size_bytes'] and sha256_file(p)==f['sha256'],'Salida alterada')
    return m

def validate_m5(out,profile):
    total=rows=days=zeros=complete=0;seen=set();last_row=None
    for f in tables(out/'sales_monthly_observed.parquet'):
        require(not f.isna().any().any(),'M5 mensual con null')
        require((f.units_observed>=0).all() and np.isfinite(f.units_observed).all(),'Unidades M5 inválidas')
        expected=f.month.map(lambda v:pd.Period(v).days_in_month)
        require(f.days_expected.eq(expected).all(),'Días esperados inválidos')
        require(f.complete_month.eq(f.days_observed.eq(expected)).all(),'Mes completo falso')
        require((f.zero_days<=f.days_observed).all(),'Ceros imposibles')
        # Orden de emisión por bloque de series y mes: verificar clave de unicidad con hash independiente.
        keys=pd.util.hash_pandas_object(f[['item_id','store_id','month']],index=False).to_numpy()
        require(len(np.unique(keys))==len(keys),'Clave mensual repetida')
        require(not any(int(k) in seen for k in keys),'Clave mensual repetida entre bloques')
        seen.update(map(int,keys))
        total+=float(f.units_observed.sum());rows+=len(f);days+=int(f.days_observed.sum());zeros+=int(f.zero_days.sum());complete+=int(f.complete_month.sum())
    expected=profile['sales_files']['sales_train_evaluation.csv']
    require(total==expected['units']['sum'],'Suma M5 distinta al perfil original')
    require(days==expected['units']['total'] and zeros==expected['units']['zero'],'Observaciones M5 no reconciliadas')
    price=pd.read_parquet(out/'prices_weekly.parquet')
    require(len(price)==profile['prices']['rows'],'Filas de precio faltantes')
    require(np.isfinite(price.sell_price).all() and price.sell_price.gt(0).all(),'Precio inválido')
    require(np.isclose(price.sell_price.sum(),profile['prices'].get('price',{}).get('sum',price.sell_price.sum()),rtol=1e-12,atol=.01),'Suma de precios alterada')
    require(not price.duplicated(['item_id','store_id','wm_yr_wk']).any(),'Precios duplicados')
    calendar=pd.read_parquet(out/'calendar.parquet')
    require(not calendar.d.duplicated().any() and not calendar.date.duplicated().any(),'Calendario ambiguo')
    if 'calendar' in profile:require(len(calendar)==profile['calendar']['rows'],'Filas calendario alteradas')
    weeks=calendar.groupby('wm_yr_wk').date.agg(['min','max','count'])
    require(price.week_start.eq(price.wm_yr_wk.map(weeks['min'])).all() and price.week_end.eq(price.wm_yr_wk.map(weeks['max'])).all(),'Relación de semanas inválida')
    closed=(pd.to_datetime(weeks['max'])-pd.to_datetime(weeks['min'])).dt.days.eq(6) & weeks['count'].eq(7)
    require(price.calendar_week_complete.eq(price.wm_yr_wk.map(closed)).all(),'Semana parcial declarada completa')
    same=price.item_id.eq(price.item_id.shift()) & price.store_id.eq(price.store_id.shift())
    gap=pd.to_datetime(price.week_start).diff().dt.days
    eligible=same & gap.eq(7) & price.calendar_week_complete & price.calendar_week_complete.shift(fill_value=False)
    require(price.adjacent_change_eligible.eq(eligible).all(),'Cambios sin semana adyacente')
    require(price.relative_change.isna().eq(~eligible).all(),'Cambio calculado sobre hueco')
    actual=price.sell_price.div(price.sell_price.shift()).sub(1)
    require(np.allclose(price.loc[eligible,'relative_change'],actual[eligible],rtol=1e-12,atol=1e-12),'Cambio incorrecto')
    avail=(pd.to_datetime(price.week_end)+pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d')
    require(price.loc[price.calendar_week_complete,'available_at_assumed_date'].eq(avail[price.calendar_week_complete]).all(),'Fecha supuesta incorrecta')
    require(price.loc[~price.calendar_week_complete,'available_at_assumed_date'].isna().all(),'Disponibilidad inventada en semana parcial')
    return dict(monthly_rows=rows,complete_month_rows=complete,partial_month_rows=rows-complete,units=total,observed_days=days,zero_days=zeros,prices=len(price),price_changes_eligible=int(eligible.sum()),
                monthly_key_check='64-bit hash duplicate check, conservatively rejects any collision',source_totals_match=True)

def validate_favorita(out,profile,config):
    expected=profile['files']['train.csv.7z'];n=expected['rows'];seen=np.zeros(n,dtype=bool)
    total=rows=positive_rows=negative_rows=zero_rows=fracs=unknown=0;positive=negative=0.;ref_positive=set();ref_fraction=set();last={};sums={};promos={'TRUE':0,'FALSE':0,'UNKNOWN':0}
    items=set(pd.read_parquet(out/'items.parquet').item_nbr);stores=set(pd.read_parquet(out/'stores.parquet').store_nbr)
    for name in ['items','stores','holidays_events','transactions']:
        auxiliary=pd.read_parquet(out/(name+'.parquet'))
        source_profile=profile['files'].get(name+'.csv.7z')
        if source_profile:require(len(auxiliary)==source_profile['rows'],'Filas auxiliares alteradas')
        if name in ['items','stores']:
            key='item_nbr' if name=='items' else 'store_nbr'
            require(not auxiliary[key].duplicated().any(),'Catálogo duplicado')
        if name=='transactions':
            require(not auxiliary.duplicated(['date','store_nbr']).any(),'Transacciones duplicadas')
            if source_profile:require(auxiliary.transactions.sum()==source_profile['transactions']['sum'],'Transacciones alteradas')
    for name,sign in [('positive_observations',1),('negative_adjustments',-1),('zero_observations',0)]:
        last_source=0;last_key=None
        for f in tables(out/(name+'.parquet')):
            require(not f.isna().any().any(),'Null no clasificado')
            q=f.unit_sales.to_numpy();require(np.isfinite(q).all(),'Cantidad no finita')
            require(((q>0) if sign==1 else (q<0) if sign==-1 else (q==0)).all(),'Partición de signo incorrecta')
            ix=f.source_row.to_numpy(dtype='int64')-1
            require(((ix>=0)&(ix<n)).all() and len(np.unique(ix))==len(ix),'Fila de procedencia inválida')
            require(not seen[ix].any(),'Fila original contada dos veces');seen[ix]=True
            require(f.source_row.is_monotonic_increasing and int(f.source_row.iloc[0])>last_source,'Orden de procedencia alterado');last_source=int(f.source_row.iloc[-1])
            date=pd.to_datetime(f.date,format='%Y-%m-%d',errors='raise');key=(date.dt.strftime('%Y%m%d').astype('int64').to_numpy()*1000+f.store_nbr.to_numpy())*10000000+f.item_nbr.to_numpy()
            require((key[1:]>key[:-1]).all() and (last_key is None or key[0]>last_key),'Clave externa repetida o desordenada');last_key=key[-1]
            require(f.item_nbr.isin(items).all() and f.store_nbr.isin(stores).all(),'Referencia inexistente')
            require(f.fractional_quantity.eq(q!=np.trunc(q)).all(),'Fracciones alteradas')
            require(f.onpromotion.isin(promos).all(),'Promoción inválida')
            for p in promos:promos[p]+=int(f.onpromotion.eq(p).sum())
            month=f.date.str[:7];ref=month.between(config['reference_estimation_window']['start'],config['reference_estimation_window']['end'])
            cmp=month.between(config['descriptive_comparison_window']['start'],config['descriptive_comparison_window']['end'])
            require(f.window.eq(np.where(ref,'REFERENCE',np.where(cmp,'DESCRIPTIVE_COMPARISON','OUTSIDE'))).all(),'Ventana incorrecta')
            ref_positive.update(f.loc[ref & f.unit_sales.gt(0),'item_nbr']);ref_fraction.update(f.loc[ref & f.fractional_quantity,'item_nbr'])
            rows+=len(f);total+=float(q.sum());fracs+=int(f.fractional_quantity.sum());unknown+=int(f.onpromotion.eq('UNKNOWN').sum())
            if rows % 5000000 < 200000:print('Validated Favorita observation rows '+str(rows),flush=True)
            if sign==1:positive+=float(q.sum());positive_rows+=len(f)
            elif sign==-1:negative+=float(q.sum());negative_rows+=len(f)
            else:zero_rows+=len(f)
    require(seen.all() and rows==n,'Faltan filas originales');del seen
    require(np.isclose(total,expected['unit_sales']['sum'],rtol=1e-12,atol=.01),'Suma distinta al RAW perfilado')
    require(negative_rows==expected['unit_sales']['negative'] and zero_rows==expected['unit_sales']['zero'],'Conteos de signo alterados')
    require(fracs==expected['unit_sales']['fractional'] and unknown==expected['promotion']['missing'],'Fracciones o promociones alteradas')
    require(promos['TRUE']==expected['promotion']['true'] and promos['FALSE']==expected['promotion']['false'],'Promociones no reconciliadas')
    cohorts=pd.read_parquet(out/'unit_cohorts.parquet');require(not cohorts.item_nbr.duplicated().any() and set(cohorts.item_nbr)==items,'Cohorte incompleta')
    labels=cohorts.item_nbr.map(lambda x:'OBSERVED_FRACTIONAL' if x in ref_fraction else 'OBSERVED_INTEGER' if x in ref_positive else 'UNKNOWN')
    require(cohorts.unit_cohort.eq(labels).all(),'Cohortes usan comparación o unidad incorrecta')
    monthly_rows=monthly_source_rows=monthly_fracs=monthly_unknown=0;monthly_pos=monthly_neg=0.;last=None;monthly_positive=monthly_negative=monthly_zero=monthly_true=monthly_false=0
    for f in tables(out/'monthly_recorded_summary.parquet'):
        require(not f.product_store_panel_complete_certified.any(),'Panel ausente declarado completo')
        require(f.days_observed.eq(f.rows_observed).all() and (f.days_observed<=f.calendar_days_expected).all(),'Días observados inconsistentes')
        require(f.calendar_month_complete.eq(f.month.between(config['complete_calendar_months']['start'],config['complete_calendar_months']['end'])).all(),'Mes parcial no señalado')
        require(f.rows_observed.eq(f.positive_rows+f.negative_rows+f.zero_rows).all(),'Filas mensuales no reconciliadas')
        require(f.rows_observed.eq(f.promotion_true+f.promotion_false+f.promotion_unknown).all(),'Cobertura mensual inventada')
        key=(f.month.str.replace('-','',regex=False).astype('int64').to_numpy()*1000+f.store_nbr.to_numpy())*10000000+f.item_nbr.to_numpy()
        require((key[1:]>key[:-1]).all() and (last is None or key[0]>last),'Resumen mensual duplicado');last=key[-1]
        monthly_rows+=len(f);monthly_source_rows+=int(f.rows_observed.sum());monthly_pos+=float(f.positive_units.sum());monthly_neg+=float(f.negative_units.sum());monthly_fracs+=int(f.fractional_rows.sum());monthly_unknown+=int(f.promotion_unknown.sum())
        monthly_positive+=int(f.positive_rows.sum());monthly_negative+=int(f.negative_rows.sum());monthly_zero+=int(f.zero_rows.sum());monthly_true+=int(f.promotion_true.sum());monthly_false+=int(f.promotion_false.sum())
    require(monthly_source_rows==n and monthly_fracs==fracs and monthly_unknown==unknown,'Resumen mensual perdió filas')
    require((monthly_positive,monthly_negative,monthly_zero,monthly_true,monthly_false)==(positive_rows,negative_rows,zero_rows,promos['TRUE'],promos['FALSE']),'Particiones mensuales inconsistentes')
    require(np.isclose(monthly_pos,positive,rtol=1e-12,atol=.01) and np.isclose(monthly_neg,negative,rtol=1e-12,atol=.01),'Suma mensual alterada')
    return dict(rows=rows,positive_rows=positive_rows,negative_rows=negative_rows,zero_rows=zero_rows,fractional_rows=fracs,promotion_unknown=unknown,net_units=total,monthly_rows=monthly_rows,
                source_row_coverage='Exact bitset, each original row appears once across sign partitions',source_totals_match=True,cohort_counts={str(k):int(v) for k,v in cohorts.unit_cohort.value_counts().items()})

def run(run_id,root=ROOT):
    root=Path(root).resolve();run_id=token(run_id);report_dir=root/'reports/v2/curation'/run_id
    execution=json.loads((report_dir/'execution.json').read_text(encoding='utf-8'));policy=json.loads((root/'v2/contracts/retail_transformations.v2.json').read_text(encoding='utf-8'));results={}
    for source,path in execution['sources'].items():
        require(source in ['m5_walmart','corporacion_favorita'],'Automotive no autorizado');out=(root/path).resolve()
        require(out.is_relative_to((root/'sources/external_curated').resolve()),'Ruta de validación insegura');check_manifest(out,source,root)
        profile=json.loads((root/'reports/v2/profiling/profile-retail-20261115-01'/(source+'_profile.json')).read_text(encoding='utf-8'))
        print('Independent validation '+source,flush=True)
        results[source]=validate_m5(out,profile) if source=='m5_walmart' else validate_favorita(out,profile,policy['sources'][source])
    write_report(report_dir/'validation.json',dict(status='VALIDATED_PRIVATE_REFERENCES_ONLY',sources=results,calibrated=False,dataset_created=False,trained=False,raw_changed=False,validation_script_sha256=sha256_file(Path(__file__))))
    print('Validated both curated sources',flush=True);return results

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
