"""Mecanismos sintéticos versionados, sin E/S, datasets o modelos."""
from datetime import datetime,timedelta
from decimal import Decimal,ROUND_HALF_UP
import math
import random
from .generate import month_start
from .validate_build import canonical_hash,instant

VERSION='retail-reference-generator-1.0.0'


def number(value,name,lower=None,upper=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Número inválido: '+name)
    if lower is not None and value<lower or upper is not None and value>upper:raise ValueError('Fuera de rango: '+name)
    return value


def money(value):
    number(value,'importe',lower=0)
    return float(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def validate_prices(retail,wholesale,cost):
    for name,value in [('retail',retail),('wholesale',wholesale),('cost',cost)]:number(value,name,lower=0)
    if not 0<cost<=wholesale<=retail:raise ValueError('PRICE_RULE: costo <= POR MAYOR <= POR MENOR. No corregir silenciosamente.')
    return retail,wholesale,cost


class Mechanisms:
    def __init__(self,calibration,recipe,stores):
        if recipe['generator_version']!=VERSION or recipe['seed']!=42:raise ValueError('Versión o seed no admitida')
        if not stores or len(set(stores))!=len(stores):raise ValueError('Tiendas inválidas')
        self.recipe=recipe;self.seed=42;self.calibration=calibration
        p=calibration['parameters']
        self.probability=number(p['weekly_price_change_probability']['value'],'probabilidad',0,1)
        self.magnitude=number(p['conditional_absolute_price_change']['value'],'magnitud',0)
        if not 0<self.magnitude<1:raise ValueError('Magnitud bidireccional debe estar entre cero y uno')
        self.up_share=number(p['conditional_up_share']['value'],'dirección',0,1)
        if p['price_elasticity']['value'] is not None or p['promotion_daily_probability']['value'] is not None:raise ValueError('No activar parámetros no identificados')
        if p['bolivian_exchange_rate_stock_modalities_cost_lead_time']['value'] is not None:raise ValueError('Fuente externa no respalda esos datos')
        self.bursts={'NONE':1.0,'P95':number(p['positive_burst_p95_over_median']['reference_quantiles']['p50'],'p95',1),'P99':number(p['positive_burst_p99_over_median']['reference_quantiles']['p50'],'p99',1)}
        if self.bursts['P99']<self.bursts['P95']:raise ValueError('Colas desordenadas')
        if not recipe['burst_cycle'] or any(x not in self.bursts for x in recipe['burst_cycle']):raise ValueError('Ciclo de cobertura inválido')
        levels=recipe['store_levels']
        if not levels:raise ValueError('Sin niveles de tienda')
        values=[number(p['store_volume_factor']['reference_quantiles'][levels[i%len(levels)]],'factor de tienda',0) for i,_ in enumerate(sorted(stores))]
        if any(v<=0 for v in values):raise ValueError('Factor cero requiere escenario inactivo, no una tienda activa')
        mean=sum(values)/len(values)
        self.store_factors={sid:v/mean for sid,v in zip(sorted(stores),values)}
        amplitude=number(p['calendar_amplitude']['reference_quantiles'][recipe['calendar_level']],'amplitud',0)
        self.beta=math.log1p(amplitude)
        self.phase=number(recipe['calendar_phase_month'],'fase',0,11)
        if not isinstance(self.phase,int):raise ValueError('Fase mensual entera requerida')
        self.calendar_mean=sum(math.exp(self.beta*math.sin(2*math.pi*(m-self.phase)/12)) for m in range(1,13))/12
        self.first_week=month_start(0)+timedelta(days=(-month_start(0).weekday())%7)
    def rng(self,stream,*keys):
        return random.Random(int(canonical_hash([VERSION,self.seed,stream,*keys]),16))
    def seasonal_factor(self,month):
        if not isinstance(month,int) or isinstance(month,bool) or not 1<=month<=12:raise ValueError('Mes inválido')
        value=math.exp(self.beta*math.sin(2*math.pi*(month-self.phase)/12))/self.calendar_mean
        return number(value,'factor positivo',0)
    def volume_factor(self,store,month):return self.store_factors[store]*self.seasonal_factor(month)
    def weekly_event(self,product,store,start):
        if start.tzinfo is None or start.utcoffset()!=month_start(0).utcoffset() or start.weekday()!=0 or (start.hour,start.minute,start.second,start.microsecond)!=(0,0,0,0):raise ValueError('Semana debe iniciar lunes local a medianoche')
        r=self.rng('weekly-price',product,store,start.isoformat())
        if r.random()>=self.probability:return None
        change=self.magnitude if r.random()<self.up_share else -self.magnitude
        return dict(productId=product,locationId=store,week_start=start.isoformat(),available_at=(start+timedelta(days=7)).isoformat(),
                    relative_change=change,availability_basis='ASSUMED_SIMULATION_WEEK_CLOSE',source='M5_RELATIVE_REFERENCE_NOT_REAL_LOCAL_PRICE')
    def price_state(self,product,store,cutoff):
        cutoff=instant(cutoff) if isinstance(cutoff,str) else cutoff
        if cutoff.tzinfo is None:raise ValueError('Corte sin zona horaria')
        if not month_start(0)<=cutoff<=month_start(24):raise ValueError('Corte fuera del horizonte académico')
        week=self.first_week;factor=1.;events=[]
        while week+timedelta(days=7)<=cutoff:
            event=self.weekly_event(product,store,week)
            if event is not None:
                factor*=1+event['relative_change'];events.append(event)
            week+=timedelta(days=7)
        return number(factor,'factor de precio',0),events
    def retail_quantity(self,quantity,product,store,month_index):
        if not isinstance(quantity,int) or isinstance(quantity,bool) or quantity<0:raise ValueError('Conteo sintético entero requerido')
        if not isinstance(month_index,int) or not 0<=month_index<24:raise ValueError('Índice temporal inválido')
        cycle=self.recipe['burst_cycle'];offset=self.rng('burst-offset',product,store).randrange(len(cycle));case=cycle[(offset+month_index)%len(cycle)]
        # Redondeo de un conteo sintético propio, nunca de una cantidad extranjera.
        result=math.ceil(quantity*self.bursts[case])
        return result,dict(case=case,multiplier=self.bursts[case],coverage_basis='FORCED_ACADEMIC_COVERAGE_NOT_EMPIRICAL_FREQUENCY',mode='POR_MENOR')
