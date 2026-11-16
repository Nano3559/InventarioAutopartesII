"""Calibración descriptiva ampliada desde curated validado. No genera datos ni ajusta modelos."""
from datetime import datetime,timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from .structure import ROOT,sha256_file,validate_contract,token
from .profile_sources import write_report


def distribution(values):
    a=np.asarray(values,dtype=float);a=a[np.isfinite(a)]
    if not a.size:return dict(n=0,mean=None,p10=None,p50=None,p90=None,p95=None,p99=None,minimum=None,maximum=None)
    q=np.quantile(a,[.1,.5,.9,.95,.99],method='linear')
    return dict(n=int(a.size),mean=float(a.mean()),minimum=float(a.min()),maximum=float(a.max()),**dict(zip(['p10','p50','p90','p95','p99'],q.tolist())))


def series_metrics(values):
    """Una serie completa, sin rellenar ausencias. CV poblacional y cambios adyacentes."""
    a=np.asarray(values,dtype=float)
    if not a.size or not np.isfinite(a).all() or (a<0).any():raise ValueError('Serie inválida')
    mean=float(a.mean());current=longest=0
    for v in a:
        current=current+1 if v==0 else 0;longest=max(longest,current)
    return dict(zero_probability=float((a==0).mean()),cv=float(a.std(ddof=0)/mean) if mean>0 else None,
                longest_zero_run=longest,normalized_absolute_change_p95=float(np.quantile(np.abs(np.diff(a))/mean,.95)) if len(a)>1 and mean>0 else None)


def seasonal_amplitude(values,months):
    a=np.asarray(values,dtype=float);dates=pd.to_datetime(pd.Series(months).astype(str)+'-01')
    counts=dates.groupby(dates.dt.month).apply(lambda x:x.dt.year.nunique())
    if len(counts)!=12 or counts.min()<2 or not np.isfinite(a).all() or a.mean()<=0:return None
    f=pd.DataFrame({'m':dates.dt.month,'v':a}).groupby('m').v.mean()/a.mean()
    return float((f.max()-f.min())/2)


def m5_reference(base):
    sales=pd.read_parquet(base/'sales_monthly_observed.parquet')
    prices=pd.read_parquet(base/'prices_weekly.parquet')
    result={}
    for window in ['REFERENCE','COMPARISON']:
        source_window='REFERENCE' if window=='REFERENCE' else 'DESCRIPTIVE_COMPARISON'
        f=sales.loc[(sales.window==source_window)&sales.complete_month].copy()
        if f.empty:raise ValueError('Ventana sin observaciones elegibles: '+source_window)
        if not f.days_observed.eq(f.days_expected).all():raise ValueError('Mes incompleto')
        wide=f.pivot(index=['item_id','store_id'],columns='month',values='units_observed').sort_index(axis=1)
        if wide.isna().any().any():raise ValueError('Serie con mes ausente, no imputar')
        a=wide.to_numpy(dtype=float);means=a.mean(axis=1);positive=means>0
        zero=(a==0).mean(axis=1);cv=np.full(len(a),np.nan);cv[positive]=a[positive].std(axis=1,ddof=0)/means[positive]
        growth=np.quantile(np.abs(np.diff(a[positive],axis=1))/means[positive,None],.95,axis=1)
        current=np.zeros(len(a),dtype=int);longest=current.copy()
        for col in a.T:current=np.where(col==0,current+1,0);longest=np.maximum(longest,current)
        daily=f.groupby(['item_id','store_id'],observed=True)[['zero_days','days_observed']].sum()
        product_mean=pd.Series(means,index=wide.index).groupby(level=0).transform('mean').to_numpy()
        eligible=product_mean>0;store_factors=means[eligible]/product_mean[eligible]
        dates=pd.to_datetime(wide.columns+'-01')
        eligible_calendar=all(len(set(dates.year[dates.month==month]))>=2 for month in range(1,13))
        if eligible_calendar:
            normalized=np.stack([a[:,dates.month==month].mean(axis=1) for month in range(1,13)],axis=1)
            amplitudes=((normalized[positive].max(axis=1)-normalized[positive].min(axis=1))/(2*means[positive])).tolist()
            insufficient=int((~positive).sum())
        else:
            amplitudes=[];insufficient=len(a)
        pr=prices.loc[(prices.window==source_window)&prices.adjacent_change_eligible].copy()
        if (pr.previous_observation_gap.any() or pr.relative_change.isna().any()):raise ValueError('Cambio no elegible')
        pr['event']=pr.relative_change.ne(0);pr['up']=pr.relative_change.gt(0);pr['down']=pr.relative_change.lt(0)
        groups=pr.groupby(['item_id','store_id'],observed=True)
        freq=groups[['event','up','down']].mean()
        changes=pr.loc[pr.event].copy();changes['magnitude']=changes.relative_change.abs()
        mags=changes.groupby(['item_id','store_id'],observed=True).magnitude.median()
        up=changes.groupby(['item_id','store_id'],observed=True).up.mean()
        magnitude_quantiles=changes.groupby(['item_id','store_id'],observed=True).magnitude.quantile([.1,.5,.9]).unstack()
        result[window]=dict(series=len(wide),months=len(wide.columns),first_month=str(wide.columns[0]),last_month=str(wide.columns[-1]),
            weighting='One value per product-store series, equal weight. No row-weighted mixing.',
            monthly_zero_probability=distribution(zero),daily_zero_probability=distribution(daily.zero_days/daily.days_observed),
            monthly_cv=distribution(cv),all_zero_series=int((~positive).sum()),monthly_longest_zero_run=distribution(longest),
            normalized_monthly_change_p95=distribution(growth),store_relative_volume_factor=distribution(store_factors),
            seasonal_amplitude=distribution([v for v in amplitudes if v is not None]),seasonal_insufficient_series=insufficient,
            prices=dict(eligible_pairs=len(pr),series_with_eligible_pairs=len(freq),series_with_changes=len(mags),
                weekly_change_probability=distribution(freq.event),weekly_up_probability=distribution(freq.up),weekly_down_probability=distribution(freq.down),
                conditional_up_share_per_changing_series=distribution(up),conditional_median_absolute_relative_change=distribution(mags),
                conditional_size_quantiles={str(q):distribution(magnitude_quantiles[q]) for q in [.1,.5,.9]} if len(changes) else {},
                limitations='Week-close availability is assumed. Eligible current week determines window; a prior adjacent week may be boundary context. Changes are not causal price effects.'))
        print('M5 reference complete '+window,flush=True)
    return result


DTYPE=np.dtype([('key','<i8'),('window','u1'),('cohort','u1'),('value','<f8')])


def exact_positive_metrics(values):
    a=np.asarray(values,dtype=float)
    if not a.size or not np.isfinite(a).all() or (a<=0).any():raise ValueError('Positivos inválidos')
    median,p95,p99=np.quantile(a,[.5,.95,.99],method='linear')
    return dict(n=len(a),p50=float(median),p95_over_p50=float(p95/median),p99_over_p50=float(p99/median),cv=float(a.std(ddof=0)/a.mean()) if len(a)>=2 else None)


def favorita_reference(base,tmp):
    cohorts=pd.read_parquet(base/'unit_cohorts.parquet').set_index('item_nbr').unit_cohort
    mapping=cohorts.map({'OBSERVED_INTEGER':1,'OBSERVED_FRACTIONAL':2,'UNKNOWN':0}).to_dict()
    bins=tmp/'positive_bins';bins.mkdir(exist_ok=False)
    files=[(bins/f'{i:02d}.bin').open('xb') for i in range(32)]
    counts=dict(reference=0,comparison=0,outside=0,unknown_cohort=0,comparison_fractional_in_integer_cohort=0)
    seen=0
    try:
        for batch in pq.ParquetFile(base/'positive_observations.parquet').iter_batches(batch_size=500000,columns=['store_nbr','item_nbr','unit_sales','window','fractional_quantity']):
            f=batch.to_pandas();seen+=len(f)
            codes=f.item_nbr.map(mapping)
            if codes.isna().any():raise ValueError('Item sin cohorte')
            phase=f.window.map({'REFERENCE':1,'DESCRIPTIVE_COMPARISON':2}).fillna(0).to_numpy(dtype='uint8')
            cohort=codes.to_numpy(dtype='uint8');frac=f.fractional_quantity.to_numpy(dtype=bool)
            if ((phase==1)&(cohort==1)&frac).any():raise ValueError('Cohorte entera contradice su referencia')
            exclude=(phase==2)&(cohort==1)&frac
            counts['comparison_fractional_in_integer_cohort']+=int(exclude.sum())
            counts['outside']+=int((phase==0).sum());counts['unknown_cohort']+=int(((phase!=0)&(cohort==0)).sum())
            keep=(phase>0)&(cohort>0)&(~exclude)
            counts['reference']+=int(((phase==1)&keep).sum());counts['comparison']+=int(((phase==2)&keep).sum())
            if not (f.item_nbr.between(1,9999999).all() and f.store_nbr.between(1,999).all()):raise ValueError('Clave fuera de límites')
            a=np.empty(int(keep.sum()),dtype=DTYPE)
            a['key']=(f.store_nbr.to_numpy(dtype='int64')*10000000+f.item_nbr.to_numpy(dtype='int64'))[keep]
            a['window']=phase[keep];a['cohort']=cohort[keep];a['value']=f.unit_sales.to_numpy(dtype=float)[keep]
            bucket=a['key']%32
            for i,handle in enumerate(files):a[bucket==i].tofile(handle)
            if seen%10000000<500000:print('Favorita positives inspected '+str(seen),flush=True)
    finally:
        for handle in files:handle.close()
    return summarize_positive_bins(base,bins,counts,seen)


def summarize_positive_bins(base,bins,counts,seen):
    cohorts=pd.read_parquet(base/'unit_cohorts.parquet').set_index('item_nbr').unit_cohort
    mapping=cohorts.map({'OBSERVED_INTEGER':1,'OBSERVED_FRACTIONAL':2,'UNKNOWN':0}).to_dict()
    metrics={}
    for p in bins.glob('*.bin'):
        a=np.fromfile(p,dtype=DTYPE)
        if not len(a):continue
        a=a[np.lexsort((a['key'],a['cohort'],a['window']))]
        edges=np.r_[0,np.flatnonzero((a['key'][1:]!=a['key'][:-1])|(a['window'][1:]!=a['window'][:-1])|(a['cohort'][1:]!=a['cohort'][:-1]))+1,len(a)]
        for start,end in zip(edges[:-1],edges[1:]):
            group=a[start:end];key=(int(group['window'][0]),int(group['cohort'][0]));m=exact_positive_metrics(group['value'])
            bucket=metrics.setdefault(key,{k:[] for k in m})
            for k,v in m.items():bucket[k].append(v)
        print('Favorita exact quantiles bucket '+p.stem,flush=True)
    result={'positive_rows_inspected':seen,'partition_counts':counts,'exact_quantile_method':'All eligible positive values sorted within each source product-store series and window. numpy linear quantile. Temporary binary partitions under tmp only. No approximation.', 'groups':{}}
    monthly=pd.read_parquet(base/'monthly_recorded_summary.parquet')
    monthly['cohort']=monthly.item_nbr.map(mapping)
    for phase,win in [(1,'REFERENCE'),(2,'COMPARISON')]:
        result['groups'][win]={}
        for code,label in [(1,'OBSERVED_INTEGER'),(2,'OBSERVED_FRACTIONAL')]:
            raw=metrics.get((phase,code),{})
            f=monthly.loc[(monthly.window==('REFERENCE' if win=='REFERENCE' else 'DESCRIPTIVE_COMPARISON'))&(monthly.cohort==code)]
            grouped=f.groupby(['store_nbr','item_nbr'],observed=True)[['rows_observed','promotion_true','promotion_false','promotion_unknown']].sum()
            known=grouped.promotion_true+grouped.promotion_false
            freq=grouped.promotion_true/known.replace(0,np.nan)
            coverage=known/grouped.rows_observed
            result['groups'][win][label]=dict(series_with_positive_reference=len(raw.get('n',[])),series_with_single_positive=sum(n<2 for n in raw.get('n',[])),positive_metrics={k:distribution(v) for k,v in raw.items()},
                promotion=dict(series_observed=len(grouped),series_without_known_promotion=int((known==0).sum()),
                  true_frequency_given_known_observed_rows=distribution(freq),known_coverage_in_observed_rows=distribution(coverage)),
                weighting='Equal series within frozen item-unit cohort. No row-weighted mixing between sources or units.',
                limitation='Conditional on recorded positive observations, not a complete daily process. Integer cohort is observed unit evidence, not proof of real spare parts. No wholesale or causal promotion label.')
    return result


def verify_inputs(root):
    validation_path=root/'reports/v2/curation/curate-retail-20261115-01/validation.json'
    validation=json.loads(validation_path.read_text(encoding='utf-8'))
    if validation['status']!='VALIDATED_PRIVATE_REFERENCES_ONLY':raise ValueError('Curated no validado')
    rules=root/'v2/contracts/retail_transformations.v2.json';rules_hash=sha256_file(rules)
    bases={};trace={}
    for source in ['m5_walmart','corporacion_favorita']:
        paths=list((root/'sources/external_curated'/source).glob('*/*/manifest.json'))
        if len(paths)!=1:raise ValueError('Curated ambiguo')
        p=paths[0];doc=json.loads(p.read_text(encoding='utf-8'));validate_contract(doc,'curated_manifest')
        if doc['parameters']['rules_contract_sha256']!=rules_hash:raise ValueError('Reglas cambiaron')
        source_doc=json.loads((root/doc['source_manifest_path']).read_text(encoding='utf-8'))
        if doc['source_id']!=source or doc['snapshot_id']!=source_doc['snapshot_id'] or doc['original_inventory_sha256']!=source_doc['inventory_sha256']:raise ValueError('Procedencia curated inconsistente')
        if not validation['sources'].get(source,{}).get('source_totals_match'):raise ValueError('Totales no reconciliados')
        if source_doc['academic_use_status']!='VERIFIED' or source_doc['profiling_decision']!='APPROVED_ACADEMIC_ONLY':raise ValueError('Permiso insuficiente')
        for row in doc['outputs']:
            path=(p.parent/row['relative_path']).resolve()
            if not path.is_relative_to(p.parent.resolve()) or sha256_file(path)!=row['sha256']:raise ValueError('Curated alterado')
        bases[source]=p.parent
        trace[source]=dict(curated_manifest=str(p.relative_to(root)),curated_manifest_sha256=sha256_file(p),snapshot_id=doc['snapshot_id'],processing_version=doc['processing_version'])
    return bases,dict(sources=trace,rules_sha256=rules_hash,curation_validation_sha256=sha256_file(validation_path))


def build_policy(m5,fav):
    ref=m5['REFERENCE'];prices=ref['prices'];integer=fav['groups']['REFERENCE']['OBSERVED_INTEGER']
    return dict(status='CALIBRATED_REFERENCE_CONFIGURATION_NOT_APPLIED_TO_GENERATOR',seed_for_future_simulation=42,
      parameters={
       'weekly_price_change_probability':dict(value=prices['weekly_change_probability']['mean'],unit='probability_per_eligible_week',basis='M5_EQUAL_SERIES_REFERENCE',application='Representative scenario only. A fixed Bernoulli mechanism is an academic assumption, not measured independence.'),
       'conditional_absolute_price_change':dict(value=prices['conditional_median_absolute_relative_change']['p50'],unit='relative_change',basis='M5_MEDIAN_OF_CHANGING_SERIES_MEDIANS',application='Typical nonzero-change size. Sign is separate, an assumed mechanism rather than an estimated joint law. Stress levels use reference quantiles, without extrapolating causal sales response. A downward magnitude must remain strictly below one. Do not mirror extreme upward changes as negative prices or clip them silently.'),
       'conditional_up_share':dict(value=prices['conditional_up_share_per_changing_series']['mean'],unit='probability_given_price_change',basis='M5_EQUAL_CHANGING_SERIES_REFERENCE',application='Representative direction mix, not weighted by frequency or a fitted joint distribution.'),
       'store_volume_factor':dict(reference_quantiles=ref['store_relative_volume_factor'],basis='M5_WITHIN_PRODUCT_RELATIVE_VOLUME',application='Sensitivity scenarios. No mapping of foreign stores to own stores and no claim of local factors.'),
       'retail_monthly_zero_probability':dict(reference_quantiles=ref['monthly_zero_probability'],basis='M5_OBSERVED_SALES_REFERENCE',application='External contrast and stress only. Preserve Monash automotive baseline. Not stockout probability.'),
       'monthly_variability':dict(reference_quantiles=ref['monthly_cv'],basis='M5_CV_EQUAL_SERIES',application='Sensitivity range, not a new noise distribution or replacement of existing academic assumptions.'),
       'calendar_amplitude':dict(reference_quantiles=ref['seasonal_amplitude'],basis='M5_WITHIN_SERIES_MONTH_OF_YEAR',application='External sensitivity reference. Bolivian peak months, phase and event effects remain assumptions, not copied from M5. This peak-to-trough statistic is not a sinusoidal coefficient and can exceed one. A future positive-valued seasonal mechanism must be justified separately.'),
       'positive_burst_p95_over_median':dict(reference_quantiles=integer['positive_metrics'].get('p95_over_p50'),basis='FAVORITA_OBSERVED_INTEGER_COHORT_EQUAL_SERIES',application='Conditional tail stress reference. Not wholesale probability, order size or local base demand.'),
       'positive_burst_p99_over_median':dict(reference_quantiles=integer['positive_metrics'].get('p99_over_p50'),basis='FAVORITA_OBSERVED_INTEGER_COHORT_EQUAL_SERIES',application='Extreme observed-tail sensitivity only. Fractional and unknown cohorts cannot set integer units.'),
       'promotion_daily_probability':dict(value=None,status='NOT_IDENTIFIABLE_FROM_RECORDED_ROWS',application='Favorita conditional frequency and coverage are diagnostics. A simulated promotion schedule requires an explicit independent academic assumption before feature cutoff.'),
       'price_elasticity':dict(value=None,status='NOT_CAUSALLY_IDENTIFIED'),
       'bolivian_exchange_rate_stock_modalities_cost_lead_time':dict(value=None,status='NOT_SUPPORTED_BY_M5_OR_FAVORITA',application='Retain versioned academic assumptions or obtain authorized own evidence. Lead times remain separate replenishment scope.')},
      integration='No generator or frozen contract changed. A future version must explicitly consume this configuration before creating any new build. Monthly CV and burst statistics remain reference ranges, not a fitted joint probability law. Store factor zero is not suitable for an active-store default without an explicit scenario.',
      unsupported=['Automotive pending license','Local commercial accuracy','Lost demand','Commercial use or redistribution automatically authorized'],
      causal_effects_estimated=False,uncertainty='Empirical quantile ranges describe series heterogeneity, not confidence intervals or guaranteed local bounds.',commercial_validation=False)


def run(run_id,root=ROOT,reuse_partitions_from=None):
    root=Path(root).resolve();run_id=token(run_id);tmp=root/'tmp'/run_id/'statistics';tmp.mkdir(parents=True,exist_ok=False)
    out=root/'reports/v2/calibration'/run_id;out.mkdir(parents=True,exist_ok=False)
    bases,trace=verify_inputs(root)
    m5=m5_reference(bases['m5_walmart']);write_report(out/'m5_reference_statistics.json',m5)
    if reuse_partitions_from is None:
        fav=favorita_reference(bases['corporacion_favorita'],tmp)
        reuse_trace=None
    else:
        previous=token(reuse_partitions_from)
        prior=root/'reports/v2/calibration'/previous
        prior_policy=json.loads((prior/'calibration.json').read_text(encoding='utf-8'))
        if prior_policy['trace']!=trace:raise ValueError('No reutilizar particiones de otras fuentes')
        old=json.loads((prior/'favorita_reference_statistics.json').read_text(encoding='utf-8'))
        bins=root/'tmp'/previous/'statistics/positive_bins'
        parts=sorted(bins.glob('*.bin'))
        if len(parts)!=32:raise ValueError('Particiones temporales incompletas')
        before={p.name:sha256_file(p) for p in parts}
        if sum(p.stat().st_size for p in parts)!=DTYPE.itemsize*(old['partition_counts']['reference']+old['partition_counts']['comparison']):raise ValueError('Particiones truncadas')
        fav=summarize_positive_bins(bases['corporacion_favorita'],bins,old['partition_counts'],old['positive_rows_inspected'])
        if before!={p.name:sha256_file(p) for p in parts}:raise ValueError('Particiones cambiaron')
        reuse_trace=dict(previous_run=previous,partition_byte_hashes=before,reason='Recompute summaries with single-observation CV excluded. Same observations, cohorts and windows, no dataset generation.')
    write_report(out/'favorita_reference_statistics.json',fav)
    policy=build_policy(m5,fav)
    policy.update(run_id=run_id,recorded_at=datetime.now(timezone.utc).isoformat(),trace=trace,
                  calibration_script_sha256=sha256_file(Path(__file__)),base_calibration_path='v2/contracts/calibration.v2.json',base_calibration_sha256=sha256_file(root/'v2/contracts/calibration.v2.json'),quantiles='Exact per series, then exact equal-series summaries. No systematic sample.',
                  windows='REFERENCE sets policy. COMPARISON descriptive only, previously observed globally. Not untouched TEST.',
                  partition_reuse=reuse_trace,raw_read_for_statistics=False,curated_modified=False,dataset_created=False,trained=False,test_evaluated=False,neon_used=False)
    verify_inputs(root)
    write_report(out/'calibration.json',policy)
    print('Calibration complete, no generator invoked: '+str(out),flush=True)
    return out

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);p.add_argument('--reuse-partitions-from');args=p.parse_args();print(run(args.run_id,reuse_partitions_from=args.reuse_partitions_from))
