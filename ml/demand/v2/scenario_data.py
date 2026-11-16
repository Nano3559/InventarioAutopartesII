"""Read-only adapter for the published scenario dataset. No database access."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'data/repuestopro_v2/3.0.0/scenarios-20261115-02'
TARGET = 'target_ventas_mes'
# Only variables supported by the documented synthetic sales mechanism.
# FX/cost/lead time remain validation or replenishment inputs, not causal drivers.
NUMERIC = [
    'ventas_mes_anterior', 'ventas_hace_2_meses', 'ventas_hace_3_meses',
    'mes_sin', 'mes_cos', 'proporcion_por_mayor_mes_anterior',
    'precio_menor_base_corte_bs', 'precio_mayor_base_corte_bs',
    'variacion_precio_menor_plan_ponderada', 'variacion_precio_mayor_plan_ponderada',
    'dias_vigencia_nuevo_precio_plan', 'dias_sin_stock_mes_anterior',
    'stock_vendible_al_corte_unidades', 'reservas_posteriores_unidades',
    'compromisos_por_menor_horizonte_unidades', 'compromisos_por_mayor_horizonte_unidades',
    'entradas_plan_horizonte_unidades', 'dias_hasta_primera_entrada_plan',
]
FEATURES = NUMERIC + ['categoryId']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def verify_build():
    for line in (BUILD / 'checksums.sha256').read_text().splitlines():
        digest, name = line.split(None, 1)
        if sha(BUILD / name.strip()) != digest:
            raise ValueError('DATASET_INTEGRITY')


def rows(partition):
    if partition not in ('TRAIN', 'VALIDATION'):
        raise PermissionError('TEST_IS_SEALED')
    bounds = json.loads((BUILD / 'split_manifest.json').read_text())['splits'][partition]
    with (BUILD / 'dataset_supervisado.csv').open(encoding='utf8', newline='') as stream:
        for row in csv.DictReader(stream):
            # Never access target/feature values of another partition.
            if bounds[0] <= row['mes_objetivo'] <= bounds[1] and row['realization_id'] == partition:
                yield row


def frame(records):
    import pandas as pd
    return pd.DataFrame([{k: (str(r[k]) if k == 'categoryId' else float(r[k]) if r[k] != '' else float('nan'))
                          for k in FEATURES} for r in records], columns=FEATURES)


def build_snapshots():
    """Publish only input-side BASE snapshots from VALIDATION, never targets."""
    selected = {r['scenario_id']: r for r in rows('VALIDATION') if r['scenario_id'].endswith('-BASE')}
    snapshots = {}
    catalog = json.loads((BUILD / 'catalog_reference.json').read_text(encoding='utf8'))
    products = {p['id']: p for p in catalog['products']}
    locations = {p['id']: p for p in catalog['locations']}
    for sid, r in selected.items():
        pid, lid = int(r['productId']), int(r['locationId'])
        snapshots[r['history_snapshot_id']] = {
            'baseSnapshotId': r['history_snapshot_id'], 'productId': pid, 'locationId': lid,
            'productName': products[pid]['name'], 'locationName': locations[lid]['name'],
            'targetMonth': r['mes_objetivo'], 'features': {k: r[k] for k in FEATURES},
            'history': [], 'prices': [], 'orders': [], 'shipments': [],
        }
    mappings = {
        'closed_history_monthly': 'history', 'price_plan_events': 'prices',
        'exchange_quote_events': 'quote', 'cost_plan_events': 'cost',
        'opening_stock_snapshot': 'stock', 'open_order_plan': 'orders',
        'pending_shipment_plan': 'shipments', 'logistics_policy': 'logistics',
    }
    for table, key in mappings.items():
        with (BUILD / (table + '.csv')).open(encoding='utf8', newline='') as stream:
            for r in csv.DictReader(stream):
                if r['scenario_id'] not in selected:
                    continue
                snapshot = snapshots[selected[r['scenario_id']]['history_snapshot_id']]
                if key in ('history', 'prices', 'orders', 'shipments'):
                    snapshot[key].append(r)
                else:
                    snapshot[key] = r
    return snapshots
