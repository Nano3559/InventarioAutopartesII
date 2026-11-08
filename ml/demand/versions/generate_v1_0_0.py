"""Generación local de ventas sintéticas, sin conexiones ni modelos ML."""
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ['mes_objetivo', 'productId', 'locationId', 'ventas_mes_anterior',
          'ventas_hace_2_meses', 'ventas_hace_3_meses', 'mes_sin', 'mes_cos',
          'target_ventas_mes']
MONTHS = [f'{2024 + (9+i)//12}-{(9+i)%12+1:02d}' for i in range(24)]
VERSION = '1.0.0-escenarios'


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + '\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def calendar(month):
    angle = 2 * math.pi * (int(month[5:]) - 1) / 12
    return round(math.sin(angle), 12), round(math.cos(angle), 12)


def split(month):
    return 'TRAIN' if month <= '2026-03' else ('VALIDATION' if month <= '2026-06' else 'TEST')


def validate(records, base, catalog, complete=True):
    """Valida contrato y dependencias temporales, no solo rangos de columnas."""
    products = set(catalog['included_product_ids'])
    stores = {r['id'] for r in catalog['locations'] if r['type'] == 'TIENDA'}
    history = {(r['productId'], r['locationId'], r['mes']): r['ventas_mes'] for r in base}
    if len(history) != len(base):
        raise ValueError('DUPLICATE_BASE')
    if len(base) != len(products) * len(stores) * 24:
        raise ValueError('INCOMPLETE_BASE')
    for p in products:
        for loc in stores:
            for month in MONTHS:
                value = history.get((p, loc, month))
                if type(value) is not int or value < 0:
                    raise ValueError('INVALID_BASE')
    seen = set()
    for row in records:
        if set(row) != set(FIELDS):
            raise ValueError('INVALID_COLUMNS')
        if type(row['productId']) is not int or row['productId'] not in products:
            raise ValueError('INVALID_PRODUCT')
        if type(row['locationId']) is not int or row['locationId'] not in stores:
            raise ValueError('INVALID_LOCATION')
        month = row['mes_objetivo']
        if month not in MONTHS[3:]:
            raise ValueError('INVALID_MONTH')
        key = row['productId'], row['locationId'], month
        if key in seen:
            raise ValueError('DUPLICATE_ROW')
        seen.add(key)
        for field in FIELDS[3:6] + ['target_ventas_mes']:
            if type(row[field]) is not int or row[field] < 0:
                raise ValueError('INVALID_QUANTITY')
        sin, cos = calendar(month)
        for field, expected in [('mes_sin', sin), ('mes_cos', cos)]:
            value = row[field]
            if type(value) not in (int, float) or not math.isfinite(value) or abs(value-expected) > 1e-10:
                raise ValueError('INVALID_CALENDAR')
        index = MONTHS.index(month)
        for offset, field in enumerate(FIELDS[3:6], 1):
            if row[field] != history[(key[0], key[1], MONTHS[index-offset])]:
                raise ValueError('LAG_MISMATCH')
        if row['target_ventas_mes'] != history[key]:
            raise ValueError('TARGET_MISMATCH')
    if complete and len(records) != len(products) * len(stores) * 21:
        raise ValueError('INCOMPLETE_PANEL')


def build(catalog, seed=42):
    rng = random.Random(seed)
    ids = sorted(catalog['included_product_ids'])
    stores = sorted(r['id'] for r in catalog['locations'] if r['type'] == 'TIENDA')
    shuffled = ids.copy()
    rng.shuffle(shuffled)
    rotation = {p: ['BAJA', 'MEDIA', 'ALTA'][i % 3] for i, p in enumerate(shuffled)}
    levels = {'BAJA': (0.3, 2), 'MEDIA': (4, 10), 'ALTA': (12, 22)}
    rates = {p: rng.uniform(*levels[rotation[p]]) for p in ids}
    trend = {p: rng.uniform(-0.10, 0.15) for p in ids}
    phase = {p: rng.uniform(0, 2*math.pi) for p in ids}
    amplitude = {p: rng.uniform(0.08, 0.25) for p in ids}
    effects = {loc: rng.uniform(0.8, 1.2) for loc in stores}
    pairs = [(p, loc) for p in ids for loc in stores]
    special = pairs.copy()
    rng.shuffle(special)
    zero_series, constant_series = set(special[:2]), set(special[2:4])
    base, labels, rows = [], [], []
    for product, loc in pairs:
        values = []
        for i, month in enumerate(MONTHS):
            mean = rates[product] * effects[loc] * (1+trend[product]*i/23)
            mean *= 1 + amplitude[product]*math.sin(2*math.pi*i/12+phase[product])
            value = max(0, round(rng.gauss(mean, max(0.6, math.sqrt(mean)*0.85))))
            kind, scenario = 'POSITIVO', 'OPERACION_REGULAR'
            event = rng.random()
            if event < 0.05:
                value += rng.randint(20, 40)
                kind, scenario = 'NEGATIVO', 'PEDIDO_MAYORISTA_EXTRAORDINARIO_VALIDO'
            elif event < 0.12:
                value = round(value * rng.uniform(0.15, 0.45))
                kind, scenario = 'NEGATIVO', 'CAIDA_DE_VENTAS_CONFIRMADA'
            elif event < 0.17:
                value += rng.randint(4, 12)
                kind, scenario = 'NEGATIVO', 'PICO_TEMPORAL_CONFIRMADO'
            if (product, loc) in zero_series:
                value, kind, scenario = 0, 'NEGATIVO', 'SERIE_CERO_CONFIRMADO'
            elif (product, loc) in constant_series:
                value, kind, scenario = 2, 'NEGATIVO', 'SERIE_CONSTANTE_CONFIRMADA'
            elif value == 0:
                kind, scenario = 'NEGATIVO', 'MES_CERO_CONFIRMADO'
            values.append(value)
            base.append(dict(mes=month, productId=product, locationId=loc, ventas_mes=value))
            labels.append(dict(mes=month, productId=product, locationId=loc,
                               clase_caso=kind, escenario=scenario, rotacion_simulada=rotation[product],
                               data_origin='DATOS_SINTETICOS',
                               conjunto='HISTORIA' if i < 3 else split(month)))
            if i >= 3:
                sin, cos = calendar(month)
                rows.append(dict(zip(FIELDS, [month, product, loc, values[-2], values[-3],
                                             values[-4], sin, cos, value])))
    validate(rows, base, catalog)
    return base, rows, labels


def invalid_cases(row):
    cases = []
    changes = [
        ('cantidad_negativa', 'target_ventas_mes', -1, 'INVALID_QUANTITY'),
        ('lag_negativo', 'ventas_mes_anterior', -2, 'INVALID_QUANTITY'),
        ('cantidad_fraccionaria', 'target_ventas_mes', 1.5, 'INVALID_QUANTITY'),
        ('target_desconocido', 'target_ventas_mes', None, 'INVALID_QUANTITY'),
        ('lag_desconocido', 'ventas_hace_2_meses', None, 'INVALID_QUANTITY'),
        ('texto_en_cantidad', 'target_ventas_mes', 'NaN', 'INVALID_QUANTITY'),
        ('producto_inexistente', 'productId', 999999, 'INVALID_PRODUCT'),
        ('almacen_como_tienda', 'locationId', 1, 'INVALID_LOCATION'),
        ('mes_fuera_periodo', 'mes_objetivo', '2026-10', 'INVALID_MONTH'),
        ('mes_invalido', 'mes_objetivo', '2025-13', 'INVALID_MONTH'),
        ('calendario_incorrecto', 'mes_sin', 9, 'INVALID_CALENDAR'),
        ('lag_incorrecto', 'ventas_mes_anterior', row['ventas_mes_anterior']+1, 'LAG_MISMATCH'),
        ('target_incorrecto', 'target_ventas_mes', row['target_ventas_mes']+1, 'TARGET_MISMATCH'),
        ('parametro_latente_filtrado', 'tasa_generador', 18, 'INVALID_COLUMNS')]
    for name, field, value, error in changes:
        cases.append(dict(case_id=name, clase_caso='NEGATIVO_INVALIDO',
                          expected_error=error, records=[{**row, field: value}]))
    cases.append(dict(case_id='duplicado', clase_caso='NEGATIVO_INVALIDO',
                      expected_error='DUPLICATE_ROW', records=[row.copy(), row.copy()]))
    return cases


def gray_cases(catalog):
    product, loc = catalog['included_product_ids'][0], 5
    scenarios = [
        ('SIN_STOCK', 'Cero observado no identifica demanda perdida', 'VENTAS_OBSERVADAS_NO_DEMANDA'),
        ('CAPTURA_INCOMPLETA', 'No se conoce el cierre completo del mes', 'REVISION_REQUERIDA'),
        ('PRODUCTO_SIN_HISTORIA', 'Producto sin tres meses completos', 'HISTORIAL_INSUFICIENTE'),
        ('TIENDA_SIN_HISTORIA', 'Inicio de operaciones sin historia suficiente', 'HISTORIAL_INSUFICIENTE'),
        ('DESCATALOGACION_DUDOSA', 'Ceros sin confirmación de vigencia comercial', 'REVISION_REQUERIDA'),
        ('ORIGEN_DEMO_NO_CERTIFICADO', 'La procedencia del registro no está certificada', 'REVISION_REQUERIDA'),
        ('CARGA_RETROACTIVA', 'Venta antigua conocida después del corte', 'NO_USAR_ANTES_DE_SU_REGISTRO'),
        ('DEVOLUCION_TARDIA', 'Devolución conocida meses después', 'CONSERVAR_TARGET_BRUTO'),
        ('PROMOCION_NO_DOCUMENTADA', 'Pico con causa comercial desconocida', 'REVISION_REQUERIDA'),
        ('SUSTITUCION_NO_CONFIRMADA', 'Posible equivalente sin vínculo aprobado', 'NO_TRASLADAR_HISTORIA')]
    return [dict(case_id=f'G{i:02d}', clase_caso='GRIS', escenario=name,
                 productId=product, locationId=loc, mes_objetivo='2026-07',
                 descripcion=description, respuesta_esperada=response,
                 target_demanda_real=None, data_origin='DATOS_SINTETICOS',
                 apto_entrenamiento=False)
            for i, (name, description, response) in enumerate(scenarios, 1)]


def csv_bytes(rows):
    import io
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode('utf-8')


def generate(output, catalog_path, seed=42):
    catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
    base, rows, labels = build(catalog, seed)
    invalid = invalid_cases(rows[0])
    for case in invalid:
        try:
            validate(case['records'], base, catalog, complete=False)
        except ValueError as error:
            if str(error) != case['expected_error']:
                raise
        else:
            raise ValueError('INVALID_CASE_ACCEPTED')
    artifacts = {'base_mensual.csv': csv_bytes(base),
                 'dataset_supervisado.csv': csv_bytes(rows),
                 'escenarios_metadatos.csv': csv_bytes(labels),
                 'casos_invalidos.json': canonical(invalid),
                 'casos_grises.json': canonical(gray_cases(catalog))}
    values = sorted(row['target_ventas_mes'] for row in rows)
    def describe(nums):
        ordered = sorted(nums)
        return dict(n=len(nums), minimo=min(nums), maximo=max(nums),
                    media=statistics.mean(nums), mediana=statistics.median(nums),
                    p95=ordered[math.ceil(len(ordered)*0.95)-1], ceros=nums.count(0))
    report = dict(global_target=describe(values),
                  por_tienda={str(loc): describe([r['target_ventas_mes'] for r in rows if r['locationId']==loc])
                              for loc in sorted({r['locationId'] for r in rows})},
                  por_producto={str(p): describe([r['target_ventas_mes'] for r in rows if r['productId']==p])
                                for p in catalog['included_product_ids']},
                  clases_base=dict(Counter(r['clase_caso'] for r in labels)),
                  escenarios=dict(Counter(r['escenario'] for r in labels)),
                  split=dict(Counter(split(r['mes_objetivo']) for r in rows)),
                  invalidos_rechazados=len(invalid), grises_separados=10,
                  validation='APROBADA', training_executed=False)
    artifacts['validacion.json'] = canonical(report)
    manifest = dict(data_origin='DATOS_SINTETICOS', dataset_name='DATOS_SINTETICOS_DEMANDA_H4',
                    dataset_version=VERSION, generator_version=VERSION, seed=seed,
                    fecha_generacion=datetime.now(timezone.utc).isoformat(),
                    periodo_inicio=MONTHS[0], periodo_fin=MONTHS[-1], cantidad_meses=24,
                    cantidad_meses_supervisados=21, cantidad_productos=len(catalog['included_product_ids']),
                    cantidad_tiendas=3, catalog_snapshot_hash=sha(catalog_path.read_bytes()),
                    generator_hash=sha(Path(__file__).read_bytes()), python_version=sys.version.split()[0],
                    catalog_as_of=catalog['observed_at'], catalog_is_current_read=False,
                    ventas_observadas_no_demanda_perdida=True,
                    features=FIELDS[3:8], identifiers=FIELDS[:3], target=FIELDS[-1],
                    excluded_from_features=['clase_caso', 'escenario', 'rotacion_simulada', 'conjunto'],
                    parameters=dict(rotation_levels={'BAJA':[0.3,2], 'MEDIA':[4,10], 'ALTA':[12,22]},
                                    annual_amplitude=[0.08,0.25], total_trend=[-0.10,0.15],
                                    store_factor=[0.8,1.2], exceptional_order_probability=0.05,
                                    drop_probability=0.07, temporary_peak_probability=0.05,
                                    zero_series=2, constant_series=2,
                                    policy='Supuestos de prueba, sin calibración comercial ni selección por métricas'),
                    hashes={name:sha(data) for name,data in artifacts.items()})
    output.mkdir(parents=True, exist_ok=True)
    for name, data in artifacts.items():
        path = output/name
        if path.exists() and path.read_bytes() != data:
            raise FileExistsError(f'No se sobrescribe un artefacto diferente: {name}')
    for name, data in artifacts.items():
        (output/name).write_bytes(data)
    (output/'manifest.json').write_bytes(canonical(manifest))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'data'/'escenarios_v1')
    parser.add_argument('--catalog', type=Path, default=HERE/'catalog_reference.json')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    report = generate(args.output, args.catalog, args.seed)
    print(json.dumps({k: report[k] for k in ['global_target', 'clases_base', 'split',
                                           'invalidos_rechazados', 'grises_separados',
                                           'validation', 'training_executed']},
                     ensure_ascii=False, indent=2))
