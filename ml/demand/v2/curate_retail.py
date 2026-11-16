"""Transformación privada de referencias M5/Favorita, sin calibración o ML."""
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from .structure import ROOT, token, sha256_file, validate_contract
from .profile_retail import inputs, archive_stream
from .profile_sources import write_report

RULES='v2/contracts/retail_transformations.v2.json'
RUN_ID='curate-retail-20261115-01'

class Sink:
    def __init__(self,path,schema):
        self.path=Path(path);self.writer=pq.ParquetWriter(self.path,schema,compression='zstd');self.schema=schema;self.rows=0
    def add(self,frame):
        if len(frame):
            self.writer.write_table(pa.Table.from_pandas(frame,schema=self.schema,preserve_index=False,safe=True));self.rows+=len(frame)
    def close(self):self.writer.close()

def fail_if(condition,message):
    if condition:raise ValueError(message)

def normalize_promotion(values):
    text=values.astype('string').str.lower()
    fail_if(bool((text.notna() & ~text.isin(['true','false'])).any()),'Promoción no reconocida: detener para cuarentena')
    return text.map({'true':'TRUE','false':'FALSE'}).fillna('UNKNOWN')

def periods(values,config):
    return np.where(values.between(config['reference_estimation_window']['start'],config['reference_estimation_window']['end']),'REFERENCE',
                    np.where(values.between(config['descriptive_comparison_window']['start'],config['descriptive_comparison_window']['end']),'DESCRIPTIVE_COMPARISON','OUTSIDE'))

def check_sorted_keys(frame,last_key=None):
    dates=pd.to_datetime(frame.date,format='%Y-%m-%d',errors='raise')
    fail_if(bool(frame[['id','store_nbr','item_nbr']].isna().any().any()),'Clave incompleta')
    fail_if(bool((frame.item_nbr>=10000000).any() or (frame.store_nbr>=1000).any()),'Clave fuera del rango auditado')
    key=(dates.dt.strftime('%Y%m%d').astype('int64').to_numpy()*1000+frame.store_nbr.to_numpy())*10000000+frame.item_nbr.to_numpy()
    fail_if(bool(np.any(key[1:]<=key[:-1])) or (last_key is not None and key[0]<=last_key),'Clave repetida o fuera de orden: detener para cuarentena, sin publicar')
    return key[-1],dates

def m5(paths,out,config):
    cal=pd.read_csv(paths['calendar.csv'])
    fail_if(cal.d.duplicated().any(),'calendar.d duplicado')
    dt=pd.to_datetime(cal.date,format='%Y-%m-%d',errors='raise')
    fail_if(dt.duplicated().any(),'Fecha calendario duplicada')
    cal['date']=dt.dt.strftime('%Y-%m-%d');cal.to_parquet(out/'calendar.parquet',index=False,compression='zstd')
    mapping=dict(zip(cal.d,cal.date));count=0;source_units=output_units=0.;seen=set();series=0
    schema=pa.schema([('item_id',pa.string()),('store_id',pa.string()),('cat_id',pa.string()),('source_series_row',pa.int64()),('month',pa.string()),('units_observed',pa.float64()),('zero_days',pa.int64()),('days_observed',pa.int64()),('days_expected',pa.int64()),('complete_month',pa.bool_()),('window',pa.string()),('first_source_day',pa.string()),('last_source_day',pa.string())])
    sink=Sink(out/'sales_monthly_observed.parquet',schema)
    try:
        for frame in pd.read_csv(paths[config['selected_sales_file']],chunksize=1000):
            keys=list(zip(frame.item_id,frame.store_id))
            fail_if(len(set(keys))!=len(keys) or any(k in seen for k in keys),'M5 clave repetida: detener para cuarentena')
            seen.update(keys)
            days=[c for c in frame if c.startswith('d_')];fail_if(any(c not in mapping for c in days),'Día M5 sin calendario')
            a=frame[days].to_numpy(dtype=float)
            fail_if(not np.isfinite(a).all() or bool((a<0).any()) or bool((a!=np.trunc(a)).any()),'Cantidad M5 inválida: detener para cuarentena')
            source_units+=float(a.sum());count+=a.size
            dates=pd.DatetimeIndex([mapping[c] for c in days]);months=dates.strftime('%Y-%m')
            for month in sorted(set(months)):
                ix=np.flatnonzero(months==month);v=a[:,ix];days_expected=pd.Period(month).days_in_month
                f=pd.DataFrame({'item_id':frame.item_id.to_numpy(),'store_id':frame.store_id.to_numpy(),'cat_id':frame.cat_id.to_numpy(),'source_series_row':np.arange(series+1,series+len(frame)+1),
                     'month':month,'units_observed':v.sum(axis=1),'zero_days':(v==0).sum(axis=1),'days_observed':len(ix),'days_expected':days_expected,
                     'complete_month':len(ix)==days_expected,'first_source_day':days[ix[0]],'last_source_day':days[ix[-1]]})
                f['window']=periods(f.month,config);output_units+=float(f.units_observed.sum());sink.add(f)
            series+=len(frame)
    finally:sink.close()
    prices=pd.read_csv(paths['sell_prices.csv'],dtype={'item_id':'category','store_id':'category'})
    fail_if(prices.duplicated(['item_id','store_id','wm_yr_wk']).any(),'Clave de precio repetida')
    fail_if(prices.isna().any().any() or not np.isfinite(prices.sell_price).all() or (prices.sell_price<=0).any(),'Precio inválido: detener para cuarentena')
    prices['source_row']=np.arange(1,len(prices)+1)
    weeks=cal.groupby('wm_yr_wk').date.agg(['min','max','count']);weekstart=pd.to_datetime(weeks['min']);weekend=pd.to_datetime(weeks['max'])
    weeks['closed']=((weekend-weekstart).dt.days==6) & weeks['count'].eq(7)
    prices['week_start']=prices.wm_yr_wk.map(weeks['min']);prices['week_end']=prices.wm_yr_wk.map(weeks['max']);prices['calendar_week_complete']=prices.wm_yr_wk.map(weeks['closed'])
    fail_if(prices[['week_start','week_end','calendar_week_complete']].isna().any().any(),'Semana sin calendario')
    prices=prices.sort_values(['item_id','store_id','week_start']).reset_index(drop=True)
    same=prices.item_id.eq(prices.item_id.shift()) & prices.store_id.eq(prices.store_id.shift())
    adjacent=pd.to_datetime(prices.week_start).diff().dt.days.eq(7)
    eligible=same & adjacent & prices.calendar_week_complete & prices.calendar_week_complete.shift(fill_value=False)
    prices['adjacent_change_eligible']=eligible;prices['relative_change']=prices.sell_price.div(prices.sell_price.shift()).sub(1).where(eligible)
    prices['previous_observation_gap']=same & ~adjacent
    prices['available_at_assumed_date']=(pd.to_datetime(prices.week_end)+pd.Timedelta(days=1)).dt.strftime('%Y-%m-%d').where(prices.calendar_week_complete)
    prices['availability_basis']='ASSUMED_SIMULATION_AVAILABILITY';prices['price_unit']='USD/source_unit';prices['window']=periods(prices.week_start.str[:7],config)
    prices.to_parquet(out/'prices_weekly.parquet',index=False,compression='zstd')
    fail_if(source_units!=output_units,'M5 sumas no reconciliadas')
    return dict(series_rows=series,source_daily_observations=count,source_units=source_units,monthly_units=output_units,monthly_rows=sink.rows,prices_rows=len(prices),price_change_eligible=int(eligible.sum()),price_gap_pairs=int(prices.previous_observation_gap.sum()),quarantined_rows=0,duplicates_removed=0,partial_months_preserved_not_eligible=True)

FAV_SCHEMA=pa.schema([('source_row',pa.int64()),('id',pa.int64()),('date',pa.string()),('store_nbr',pa.int64()),('item_nbr',pa.int64()),('unit_sales',pa.float64()),('onpromotion',pa.string()),('window',pa.string()),('fractional_quantity',pa.bool_())])
MONTH_SCHEMA=pa.schema([('month',pa.string()),('store_nbr',pa.int64()),('item_nbr',pa.int64()),('rows_observed',pa.int64()),('positive_units',pa.float64()),('negative_units',pa.float64()),('positive_rows',pa.int64()),('negative_rows',pa.int64()),('zero_rows',pa.int64()),('fractional_rows',pa.int64()),('promotion_true',pa.int64()),('promotion_false',pa.int64()),('promotion_unknown',pa.int64()),('days_observed',pa.int64()),('calendar_days_expected',pa.int64()),('calendar_month_complete',pa.bool_()),('product_store_panel_complete_certified',pa.bool_()),('window',pa.string())])

def favorita(paths,out,config):
    catalogs={}
    for name in ['items','stores','holidays_events','transactions']:
        with archive_stream(paths[name+'.csv.7z']) as stream:f=pd.read_csv(stream)
        if name in ['items','stores']:
            key='item_nbr' if name=='items' else 'store_nbr'
            fail_if(f[key].isna().any() or f[key].duplicated().any(),'Catálogo ambiguo')
            catalogs[name]=set(f[key])
        if name=='transactions':fail_if(f.duplicated(['date','store_nbr']).any(),'Transacción tienda-fecha repetida')
        f.to_parquet(out/(name+'.parquet'),index=False,compression='zstd')
    sinks={name:Sink(out/(name+'.parquet'),FAV_SCHEMA) for name in ['positive_observations','negative_adjustments','zero_observations']}
    monthly=Sink(out/'monthly_recorded_summary.parquet',MONTH_SCHEMA)
    count=0;last_key=last_id=None;net=positive=negative=0.;fractional=unknown=0;cohorts={};month_parts=[];current_month=None
    def flush():
        if not month_parts:return
        f=pd.concat(month_parts,ignore_index=True).groupby(['store_nbr','item_nbr'],sort=True).sum().reset_index()
        f['month']=current_month;f['days_observed']=f.rows_observed;f['calendar_days_expected']=pd.Period(current_month).days_in_month
        f['calendar_month_complete']=config['complete_calendar_months']['start']<=current_month<=config['complete_calendar_months']['end']
        f['product_store_panel_complete_certified']=False;f['window']=periods(f.month,config);monthly.add(f);month_parts.clear()
    try:
        with archive_stream(paths[config['selected_sales_file']]) as stream:
            for frame in pd.read_csv(stream,chunksize=250000,dtype={'onpromotion':'string'}):
                last_key,dates=check_sorted_keys(frame,last_key)
                ids=frame.id.to_numpy();fail_if(bool(np.any(ids[1:]<=ids[:-1])) or (last_id is not None and ids[0]<=last_id),'ID repetido o fuera de orden')
                last_id=ids[-1]
                fail_if((~frame.item_nbr.isin(catalogs['items'])).any() or (~frame.store_nbr.isin(catalogs['stores'])).any(),'Referencia inexistente: detener para cuarentena')
                qty=frame.unit_sales.to_numpy(dtype=float);fail_if(not np.isfinite(qty).all(),'Cantidad inválida: detener para cuarentena')
                frame['source_row']=np.arange(count+1,count+len(frame)+1);frame['unit_sales']=qty;frame['onpromotion']=normalize_promotion(frame.onpromotion)
                month=frame.date.str[:7];frame['window']=periods(month,config);frame['fractional_quantity']=qty!=np.trunc(qty)
                for name,mask in [('positive_observations',qty>0),('negative_adjustments',qty<0),('zero_observations',qty==0)]:sinks[name].add(frame.loc[mask])
                ref=frame[frame.window.eq('REFERENCE')]
                c=ref.assign(has_fraction=ref.fractional_quantity,has_positive=ref.unit_sales.gt(0)).groupby('item_nbr')[['has_fraction','has_positive']].max()
                for item,row in c.iterrows():
                    old=cohorts.setdefault(int(item),[False,False]);old[0]|=bool(row.has_fraction);old[1]|=bool(row.has_positive)
                net+=float(qty.sum());positive+=float(qty[qty>0].sum());negative+=float(qty[qty<0].sum());fractional+=int(frame.fractional_quantity.sum());unknown+=int(frame.onpromotion.eq('UNKNOWN').sum())
                frame['month']=month
                for name,g in frame.groupby('month',sort=False):
                    if current_month is not None and current_month!=name:flush()
                    current_month=name
                    a=pd.DataFrame({'store_nbr':g.store_nbr,'item_nbr':g.item_nbr,'rows_observed':1,'positive_units':g.unit_sales.where(g.unit_sales>0,0),'negative_units':g.unit_sales.where(g.unit_sales<0,0),
                        'positive_rows':g.unit_sales.gt(0).astype('int64'),'negative_rows':g.unit_sales.lt(0).astype('int64'),'zero_rows':g.unit_sales.eq(0).astype('int64'),
                        'fractional_rows':g.fractional_quantity.astype('int64'),'promotion_true':g.onpromotion.eq('TRUE').astype('int64'),'promotion_false':g.onpromotion.eq('FALSE').astype('int64'),'promotion_unknown':g.onpromotion.eq('UNKNOWN').astype('int64')})
                    month_parts.append(a.groupby(['store_nbr','item_nbr'],sort=False).sum().reset_index())
                count+=len(frame)
                if count%5000000<250000:print('Curated Favorita rows '+str(count),flush=True)
        flush()
    finally:
        for s in sinks.values():s.close()
        monthly.close()
    cohort_rows=[]
    for item in sorted(catalogs['items']):
        fraction,pos=cohorts.get(item,[False,False]);label='OBSERVED_FRACTIONAL' if fraction else 'OBSERVED_INTEGER' if pos else 'UNKNOWN'
        cohort_rows.append(dict(item_nbr=item,unit_cohort=label,reference_only=True))
    pd.DataFrame(cohort_rows).to_parquet(out/'unit_cohorts.parquet',index=False,compression='zstd')
    fail_if(sum(s.rows for s in sinks.values())!=count,'Filas Favorita no reconciliadas')
    fail_if(not np.isclose(net,positive+negative,rtol=1e-12,atol=.01),'Sumas Favorita no reconciliadas')
    return dict(input_rows=count,positive_rows=sinks['positive_observations'].rows,negative_rows=sinks['negative_adjustments'].rows,zero_rows=sinks['zero_observations'].rows,monthly_rows=monthly.rows,
        net_units=net,positive_units=positive,negative_units=negative,fractional_rows=fractional,promotion_unknown=unknown,quarantined_rows=0,duplicates_removed=0,
        excluded_files=['test.csv.7z','sample_submission.csv.7z','oil.csv.7z'],month_panels_not_certified=True,quantities_rounded=False)

def run(run_id,root=ROOT):
    root=Path(root).resolve();run_id=token(run_id);policy=json.loads((root/RULES).read_text(encoding='utf-8'))
    selected={s:inputs(s,root) for s in ['m5_walmart','corporacion_favorita']}
    report_dir=root/'reports/v2/curation'/run_id;report_dir.mkdir(parents=True,exist_ok=False)
    outputs={}
    for source,(paths,doc) in selected.items():
        pinned=policy['source_identity'][source]
        fail_if(pinned['inventory_sha256']!=doc['inventory_sha256'] or pinned['snapshot_id']!=doc['snapshot_id'],'Snapshot distinto al contrato')
        out=root/'sources/external_curated'/source/doc['snapshot_id']/('processing-1-'+run_id)
        fail_if(not out.resolve().is_relative_to((root/'sources/external_curated').resolve()),'Destino inseguro')
        out.mkdir(parents=True,exist_ok=False)
        try:
            print('Starting curated '+source,flush=True)
            audit=(m5 if source=='m5_walmart' else favorita)(paths,out,policy['sources'][source])
            inputs(source,root)
            write_report(out/'audit.json',dict(status='WRITTEN_PENDING_INDEPENDENT_VALIDATION',source_id=source,**audit))
            files=[]
            for p in sorted(out.iterdir()):
                files.append(dict(relative_path=p.name,original_format=p.suffix.lstrip('.').upper(),file_size_bytes=p.stat().st_size,sha256=sha256_file(p)))
            manifest=dict(schema_version='curated-manifest-1',source_id=source,snapshot_id=doc['snapshot_id'],original_inventory_sha256=doc['inventory_sha256'],original_files=doc['files'],processing_version='processing-1-'+run_id,
                 script='v2/curate_retail.py',script_sha256=sha256_file(Path(__file__)),parameters=dict(run_id=run_id,rules_contract_path=RULES,rules_contract_sha256=sha256_file(root/RULES),
                 private_use_scope='ROSS_ACADEMIC_NON_COMMERCIAL_NO_REDISTRIBUTION',profile_run='profile-retail-20261115-01',reference_windows=policy['sources'][source]['reference_estimation_window'],
                 comparison_windows=policy['sources'][source]['descriptive_comparison_window'],chunk_rows=1000 if source=='m5_walmart' else 250000,calibrated=False,final_dataset_created=False,trained=False,
                 unexpected_anomaly_policy='STOP_WITH_FAILED_MARKER_NO_PUBLICATION. Any malformed/conflicting row blocks acceptance until a separate quarantined processing version is authorized.',
                 source_line_number_base=1,availability='Assumed week-close date, no real published_at',dependency_hashes={n:sha256_file(root/n) for n in ['v2/profile_retail.py','v2/profile_sources.py','v2/structure.py']}),
                 executed_at=datetime.now(timezone.utc).isoformat(),outputs=files,source_manifest_path=str(next((root/'sources/manifests'/source).glob('*.json')).relative_to(root)).replace('\\','/'))
            validate_contract(manifest,'curated_manifest');write_report(out/'manifest.json',manifest);outputs[source]=out.relative_to(root).as_posix()
            print('Written '+source,flush=True)
        except Exception as e:
            write_report(out/'FAILED.json',{'status':'FAILED_NOT_ACCEPTED','reason':str(e),'no_calibration':True});raise
    write_report(report_dir/'execution.json',dict(run_id=run_id,status='WRITTEN_PENDING_INDEPENDENT_VALIDATION',sources=outputs,calibrated=False,dataset_created=False,trained=False))
    return report_dir

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);print(run(p.parse_args().run_id))
