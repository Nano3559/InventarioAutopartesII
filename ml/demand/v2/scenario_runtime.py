"""Trusted synthetic snapshots, strict semantics and read-only scenario inference.

No generator, training, TEST partition, network or database is used here.
"""
import copy
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
import hashlib
import json
import math
import re
import joblib
import numpy as np
from jsonschema import Draft202012Validator, FormatChecker
from .scenario_data import ROOT, FEATURES, NUMERIC, canonical, frame

CONTRACT = 'demand-scenarios-1.0.0'
RELEASE_PATH = ROOT / 'reports/v2/3.0.0/scenarios-model-20261115-01/release.json'
EXPECTED_RELEASE_SHA256 = '803cfefe8feabf23383f801235b0c0f63ef7178858ff78f566014839929a1b07'
FINAL_METRICS_SHA256 = '5030d06587d29f0022f094462d123ca24156583d184894addb985f0c8a65db99'
CHANGES = ['history', 'prices', 'quote', 'cost', 'stock', 'orders', 'logistics']


class ScenarioError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def check(condition, code):
    if not condition:
        raise ScenarioError(code)


def _read_verified_json(path, expected_sha256):
    data = path.read_bytes()
    check(hashlib.sha256(data).hexdigest() == expected_sha256, 'INCOMPATIBLE_ARTIFACT')
    return json.loads(data.decode('utf8'))


def instant(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        check(result.tzinfo is not None, 'INVALID_INPUT')
        return result
    except (ValueError, TypeError, AttributeError):
        raise ScenarioError('INVALID_INPUT')


def end_month(month):
    y, m = map(int, month.split('-'))
    return datetime.fromisoformat(f'{y + (m == 12):04d}-{m % 12 + 1:02d}-01T00:00:00-04:00')


@lru_cache(maxsize=1)
def release():
    r = _read_verified_json(RELEASE_PATH, EXPECTED_RELEASE_SHA256)
    check(r['features'] == FEATURES and r['datasetVersion'] == '3.0.0', 'INCOMPATIBLE_ARTIFACT')
    snapshots = _read_verified_json(ROOT / r['snapshots'], r['snapshotsSha256'])
    # Only deserialize the exact, code-pinned artifact bytes.
    import io
    data = (ROOT / r['artifact']).read_bytes()
    check(hashlib.sha256(data).hexdigest() == r['artifactSha256'], 'INCOMPATIBLE_ARTIFACT')
    return r, snapshots, joblib.load(io.BytesIO(data))


def identity(r):
    return {k: r[k] for k in ('artifactSha256', 'datasetVersion', 'modelVersion', 'policyVersion')}


def capabilities():
    r, snapshots, _ = release()
    # First example uses nonzero preceding history, never the unknown target.
    ordered = sorted(snapshots.values(), key=lambda s: (-float(s['features']['ventas_mes_anterior']), s['baseSnapshotId']))
    return {'contractVersion': CONTRACT, 'status': 'AVAILABLE', 'supportedChanges': CHANGES,
            'snapshots': [{**{k: s[k] for k in ('baseSnapshotId', 'productId', 'locationId', 'targetMonth', 'productName', 'locationName')},
                           'previousMonthUnits': sum(int(h[k]) for k in ('unidades_por_menor', 'unidades_por_mayor', 'unidades_modalidad_desconocida'))}
                          for s in ordered for h in [max(s['history'], key=lambda row: row['mes'])]], **identity(r)}


def get_snapshot(sid):
    _, snapshots, _ = release()
    check(sid in snapshots, 'SNAPSHOT_MISMATCH')
    s = copy.deepcopy(snapshots[sid])
    return s


def state(s):
    t0 = instant(s['targetMonth'] + '-01T00:00:00-04:00')
    price = s['prices'][0]
    return {'features': dict(s['features']), 'history': sorted(s['history'], key=lambda h: h['mes']),
            'retail': Decimal(price['precio_menor_bs']), 'wholesale': Decimal(price['precio_mayor_bs']),
            'priceAt': t0, 'quote': Decimal(s['quote']['bs_per_usd']), 'quoteAt': instant(s['quote']['observed_at']),
            'cost': Decimal(s['cost']['unit_cost_landed_bs']), 'costAt': t0,
            'stock': int(s['stock']['sellable_physical_units']),
            'orders': [{'orderId': o['order_id'], 'mode': o['sale_mode'], 'outstandingUnits': int(o['outstanding_units_at_cutoff']), 'reservedUnits': int(o['reserved_units_at_cutoff']), 'dueAt': o['due_at']} for o in s['orders']],
            'shipments': [{'shipmentId': o['shipment_id'], 'pendingUnits': int(o['pending_units_at_cutoff']), 'reservedAfterHorizonUnits': int(o['reserved_after_horizon_units']), 'expectedArrivalAt': o['expected_arrival_at']} for o in s['shipments']],
            'supplierDays': int(s['logistics']['supplier_lead_time_days']), 'internalDays': int(s['logistics']['internal_restock_days']), 'orderAt': instant(s['logistics']['planned_order_at'])}


def snapshot_view(sid):
    s = get_snapshot(sid); base = state(s)
    return {k: s[k] for k in ('baseSnapshotId', 'productId', 'locationId', 'targetMonth', 'productName', 'locationName')} | {
        'origin': 'SYNTHETIC_SCENARIO_NOT_REAL_SALES', 'retail': str(base['retail']), 'wholesale': str(base['wholesale']),
        'costBs': str(base['cost']), 'quote': str(base['quote']), 'quoteAt': base['quoteAt'].isoformat(),
        'stock': base['stock'], 'supplierDays': base['supplierDays'], 'internalDays': base['internalDays'],
        'orderAt': base['orderAt'].isoformat(), 'orders': base['orders'], 'shipments': base['shipments'],
        'history': [{'month': h['mes'], 'retailUnits': int(h['unidades_por_menor']), 'wholesaleUnits': int(h['unidades_por_mayor']), 'unknownModeUnits': int(h['unidades_modalidad_desconocida'])} for h in base['history']]}


def validate_request(p):
    schema = json.loads((ROOT / 'v2/contracts/scenarios.v1.json').read_text(encoding='utf8'))['request_schema']
    check(not list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(p)), 'INVALID_INPUT')


def prepare(p, s):
    validate_request(p)
    for k in ('productId', 'locationId', 'targetMonth', 'baseSnapshotId'):
        check(p[k] == s[k], 'SNAPSHOT_MISMATCH')
    base = state(s); out = copy.deepcopy(base); edits = p['changes']; impacts = []; warnings = []
    t0, end = instant(s['targetMonth'] + '-01T00:00:00-04:00'), end_month(s['targetMonth'])
    def impact(field, before, after, unit, role, explanation, effect='USED'):
        if before == after:
            return
        if isinstance(before, Decimal): before = str(before)
        if isinstance(after, Decimal): after = str(after)
        impacts.append({'field': field, 'before': before, 'after': after, 'unit': unit, 'role': role,
                        'effectStatus': effect, 'explanation': explanation, 'baseSourceKind': 'FROZEN_SYNTHETIC_BASE',
                        'scenarioSourceKind': 'HYPOTHETICAL_ASSUMPTION'})
    def in_month(v):
        d = instant(v); check(t0 <= d < end, 'INVALID_INPUT'); return d
    history = edits['history']
    if history['mode'] != 'KEEP':
        check([h['month'] for h in history['months']] == [h['mes'] for h in base['history']], 'INVALID_HISTORY_WINDOW')
        for i, h in enumerate(history['months']):
            total = sum(h[k] for k in ('retailUnits', 'wholesaleUnits', 'unknownModeUnits'))
            check(total <= 10**9, 'INVALID_QUANTITY')
            for k, physical in [('retailUnits', 'unidades_por_menor'), ('wholesaleUnits', 'unidades_por_mayor'), ('unknownModeUnits', 'unidades_modalidad_desconocida')]:
                impact(f'history.{i}.{k}', int(base['history'][i][physical]), h[k], 'unidades', 'DERIVED_MODEL_FEATURE', 'Historia hipotética, no modifica ventas registradas.')
            out['features'][['ventas_hace_3_meses', 'ventas_hace_2_meses', 'ventas_mes_anterior'][i]] = total
        last = history['months'][-1]; total = sum(last[k] for k in ('retailUnits', 'wholesaleUnits', 'unknownModeUnits'))
        out['features']['proporcion_por_mayor_mes_anterior'] = last['wholesaleUnits'] / total if total and not last['unknownModeUnits'] else ''
        if last['unknownModeUnits']: warnings.append('UNKNOWN_CHANNEL_MIX')
    prices = edits['prices']
    if prices['mode'] != 'KEEP':
        retail = Decimal(prices['retailPriceBs'])
        wholesale = Decimal(prices['wholesalePriceBs'])
        price_at = in_month(prices['effectiveAt'])
        if (retail, wholesale) != (base['retail'], base['wholesale']):
            out['retail'], out['wholesale'], out['priceAt'] = retail, wholesale, price_at
            remaining_seconds = (end - price_at).total_seconds()
            weight = Decimal(str(remaining_seconds)) / Decimal(str((end - t0).total_seconds()))
            for key, feature, field in [('retail', 'variacion_precio_menor_plan_ponderada', 'retailPriceBs'), ('wholesale', 'variacion_precio_mayor_plan_ponderada', 'wholesalePriceBs')]:
                out['features'][feature] = float((out[key] / base[key] - 1) * weight)
                impact('prices.' + field, base[key], out[key], 'Bs/unidad', 'DERIVED_MODEL_FEATURE', 'Cambio ponderado por tiempo de vigencia conocido. Sensibilidad sintética, no causalidad comercial.')
            out['features']['dias_vigencia_nuevo_precio_plan'] = remaining_seconds / 86400
            impact('prices.effectiveAt', t0.isoformat(), price_at.isoformat(), 'America/La_Paz', 'DERIVED_MODEL_FEATURE', 'Antes de la fecha se conserva el precio base.')
    quote = edits['quote']
    if quote['mode'] != 'KEEP':
        out['quote'], out['quoteAt'] = Decimal(quote['bsPerUsd']), instant(quote['observedAt'])
        check(out['quoteAt'] <= t0, 'INVALID_QUOTE_TIME')
        impact('quote.bsPerUsd', base['quote'], out['quote'], 'Bs/USD', 'VALIDATION_ONLY', 'Se usa para una compra USD hipotética. No cambia precios o compras históricos.', 'NOT_USED_BY_SELECTED_MODEL')
        impact('quote.observedAt', base['quoteAt'].isoformat(), out['quoteAt'].isoformat(), 'America/La_Paz', 'VALIDATION_ONLY', 'Antigüedad al corte, no una cotización de mercado certificada.', 'NOT_USED_BY_SELECTED_MODEL')
    age = (t0 - out['quoteAt']).total_seconds() / 86400
    if age > 30: warnings.append('QUOTE_OLDER_THAN_30_DAYS_ASSUMPTION')
    cost = edits['cost']
    if cost['mode'] != 'KEEP':
        out['costAt'] = in_month(cost['effectiveAt'])
        out['cost'] = Decimal(cost['unitCostBs']) if cost['mode'] == 'SET_LANDED_COST_BS' else Decimal(cost['unitCostUsd']) * out['quote'] + Decimal(cost['freightPerUnitBs']) + Decimal(cost['otherPerUnitBs'])
        impact('cost.unitCostBs', base['cost'], out['cost'], 'Bs/unidad', 'VALIDATION_ONLY', 'Costo USD × Bs/USD + flete + otros. Comprueba margen, no impone demanda.', 'NOT_USED_BY_SELECTED_MODEL')
        for key in ('unitCostUsd', 'freightPerUnitBs', 'otherPerUnitBs'):
            if key in cost: impact('cost.' + key, None, cost[key], 'USD/unidad' if key == 'unitCostUsd' else 'Bs/unidad', 'VALIDATION_ONLY', 'Componente explícito de la compra hipotética.', 'NOT_USED_BY_SELECTED_MODEL')
        impact('cost.effectiveAt', t0.isoformat(), out['costAt'].isoformat(), 'America/La_Paz', 'VALIDATION_ONLY', 'El costo no se aplica antes de su fecha.', 'NOT_USED_BY_SELECTED_MODEL')
    # Check each segment, not just the last or weighted prices.
    for d in sorted({t0, out['costAt'], out['priceAt']}):
        c = out['cost'] if d >= out['costAt'] else base['cost']
        a, b = (out['retail'], out['wholesale']) if d >= out['priceAt'] else (base['retail'], base['wholesale'])
        check(c <= b <= a, 'INCOHERENT_PRICES')
    if edits['stock']['mode'] != 'KEEP':
        out['stock'] = edits['stock']['sellablePhysicalUnits']
        impact('stock.sellablePhysicalUnits', base['stock'], out['stock'], 'unidades', 'DIRECT_MODEL_FEATURE', 'Solo stock vendible, excluye tránsito y cuarentena.')
    if edits['orders']['mode'] != 'KEEP': out['orders'] = copy.deepcopy(edits['orders']['orders'])
    if edits['logistics']['mode'] != 'KEEP':
        logistics = edits['logistics']; out['shipments'] = copy.deepcopy(logistics['pendingShipments'])
        out['supplierDays'], out['internalDays'], out['orderAt'] = logistics['supplierLeadTimeDays'], logistics['internalRestockDays'], instant(logistics['plannedOrderAt'])
        check(out['orderAt'] >= t0, 'INVALID_SHIPMENT_PLAN')
        for field in ('supplierDays', 'internalDays', 'orderAt'):
            a, b = base[field], out[field]
            if a != b:
                impact('logistics.' + field, a.isoformat() if isinstance(a, datetime) else a, b.isoformat() if isinstance(b, datetime) else b, 'fecha' if field == 'orderAt' else 'dias', 'REPLENISHMENT_ONLY', 'Determina llegada y viabilidad de la reposición, no incrementa ventas.', 'NOT_USED_BY_SELECTED_MODEL')
    for collection, id_key, error in [('orders', 'orderId', 'INVALID_ORDER_PLAN'), ('shipments', 'shipmentId', 'INVALID_SHIPMENT_PLAN')]:
        entries = out[collection]; check(len({o[id_key] for o in entries}) == len(entries), error)
        for o in entries:
            check(o.get('reservedUnits', o.get('reservedAfterHorizonUnits', 0)) <= o.get('outstandingUnits', o.get('pendingUnits', 0)), error)
            if collection == 'shipments': check(instant(o['expectedArrivalAt']) >= t0, error)
    check(sum(o['reservedUnits'] for o in out['orders']) <= out['stock'], 'INVALID_RESERVATION')
    out['committed'] = sum(o['outstandingUnits'] for o in out['orders'] if instant(o['dueAt']) < end)
    out['reservedWithin'] = sum(o['reservedUnits'] for o in out['orders'] if instant(o['dueAt']) < end)
    out['reservedAfter'] = sum(o['reservedUnits'] for o in out['orders'] if instant(o['dueAt']) >= end)
    eligible = [o for o in out['shipments'] if instant(o['expectedArrivalAt']) < end]
    out['incoming'] = sum(o['pendingUnits'] - o['reservedAfterHorizonUnits'] for o in eligible)
    check(all(n <= 10**9 for n in (out['committed'], out['reservedAfter'], out['incoming'], out['stock'] + out['incoming'])), 'INVALID_QUANTITY')
    f = out['features']; f['stock_vendible_al_corte_unidades'] = out['stock']; f['reservas_posteriores_unidades'] = out['reservedAfter']
    for mode, key in [('POR_MENOR', 'compromisos_por_menor_horizonte_unidades'), ('POR_MAYOR', 'compromisos_por_mayor_horizonte_unidades')]:
        f[key] = sum(o['outstandingUnits'] for o in out['orders'] if o['mode'] == mode and instant(o['dueAt']) < end)
    f['entradas_plan_horizonte_unidades'] = out['incoming']
    f['dias_hasta_primera_entrada_plan'] = min((instant(o['expectedArrivalAt']) - t0).total_seconds() / 86400 for o in eligible if o['pendingUnits'] > o['reservedAfterHorizonUnits']) if any(o['pendingUnits'] > o['reservedAfterHorizonUnits'] for o in eligible) else ''
    # Trace the union of stable identities, including rows absent from the new plan.
    # Indices label this sorted union, not positions in either submitted list.
    minor, major = 'compromisos_por_menor_horizonte_unidades', 'compromisos_por_mayor_horizonte_unidades'
    reserved = 'reservas_posteriores_unidades'
    incoming, first = 'entradas_plan_horizonte_unidades', 'dias_hasta_primera_entrada_plan'
    base_values = {name: float(base['features'][name]) if base['features'][name] != '' else '' for name in NUMERIC}
    def contributions(collection, row):
        if not row: return {}
        if collection == 'orders':
            within = instant(row['dueAt']) < end
            return {minor: row['outstandingUnits'] if within and row['mode'] == 'POR_MENOR' else 0,
                    major: row['outstandingUnits'] if within and row['mode'] == 'POR_MAYOR' else 0,
                    reserved: row['reservedUnits'] if not within else 0,
                    'reservedWithin': row['reservedUnits'] if within else 0}
        arrival = instant(row['expectedArrivalAt'])
        net = row['pendingUnits'] - row['reservedAfterHorizonUnits'] if arrival < end else 0
        return {incoming: net, first: (arrival - t0).total_seconds() / 86400 if net else ''}
    for collection, id_key, keys, dependencies in [
        ('orders', 'orderId', ('orderId', 'mode', 'outstandingUnits', 'reservedUnits', 'dueAt'),
         {'mode': (minor, major), 'outstandingUnits': (minor, major),
          'reservedUnits': (reserved,), 'dueAt': (minor, major, reserved)}),
        ('shipments', 'shipmentId', ('shipmentId', 'pendingUnits', 'reservedAfterHorizonUnits', 'expectedArrivalAt'),
         {k: (incoming, first) for k in ('pendingUnits', 'reservedAfterHorizonUnits', 'expectedArrivalAt')}),
    ]:
        if edits['orders' if collection == 'orders' else 'logistics']['mode'] == 'KEEP': continue
        old_rows = {row[id_key]: row for row in base[collection]}
        new_rows = {row[id_key]: row for row in out[collection]}
        for i, identity in enumerate(sorted(old_rows.keys() | new_rows.keys())):
            old, new = old_rows.get(identity, {}), new_rows.get(identity, {})
            before, after = contributions(collection, old), contributions(collection, new)
            action = 'agregado' if not old else 'eliminado' if not new else 'modificado'
            for key in keys:
                a, b = old.get(key), new.get(key)
                if a == b: continue
                affected = [name for name in dependencies.get(key, ())
                            if before.get(name, '' if name == first else 0) != after.get(name, '' if name == first else 0)
                            and base_values[name] != (float(f[name]) if f[name] != '' else '')]
                role = 'DERIVED_MODEL_FEATURE' if affected else 'VALIDATION_ONLY'
                detail = 'Sin variación de entradas del modelo; validación del plan.'
                if affected:
                    detail = 'Afecta entradas derivadas: ' + ', '.join(affected) + '. No garantiza un cambio en la predicción.'
                elif collection == 'orders' and key in ('reservedUnits', 'dueAt') and before.get('reservedWithin', 0) != after.get('reservedWithin', 0):
                    role = 'REPLENISHMENT_ONLY'
                    detail = 'Reservas dentro del horizonte: contexto de reposición, no se descuentan dos veces.'
                impact(f'{collection}.{i}.{key}', a, b,
                       'fecha' if key.endswith('At') else 'unidades' if key.endswith('Units') else 'identificador',
                       role, f'Plan hipotético {action} ({identity}). ' + detail,
                       'USED' if affected else 'NOT_USED_BY_SELECTED_MODEL')
    if out['committed']: warnings.append('COMMITMENT_OVERLAP_UNCERTAIN')
    if eligible: warnings.append('EXPECTED_RECEIPTS_NOT_CONFIRMED_STOCK')
    return out, impacts, warnings


def estimate(features):
    r, _, model = release()
    # Numeric extrapolation is explicit. Never treat novel values as verified.
    outside = [k for k in NUMERIC if features[k] != '' and not r['bounds'][k][0] <= float(features[k]) <= r['bounds'][k][1]]
    if outside:
        return {'status': 'OUT_OF_DOMAIN', 'salesUnits': None, 'reason': 'OUTSIDE_TRAINING_RANGE'}, outside
    value = float(model.predict(frame([features]))[0])
    check(math.isfinite(value), 'MODEL_UNAVAILABLE')
    return {'status': 'OK', 'salesUnits': max(0, value), 'reason': None}, []


def replenishment(p, out, forecast, month):
    policy = p['replenishment']; end = end_month(month)
    r = {'status': 'NOT_REQUESTED', 'policy': 'MONTH_END_COMMITMENT_FLOOR_V1',
         'temporalFeasibility': 'MONTH_END_ONLY_NO_DAILY_STOCKOUT_GUARANTEE', 'warnings': []}
    names = ['suggestedUnits', 'requiredUnits', 'availablePositionUnits', 'committedUnitsWithinHorizon', 'reservedUnitsWithinHorizon', 'reservedUnitsAfterHorizon', 'eligibleIncomingUnits', 'expectedNewOrderArrivalAt', 'rawNeedUnits', 'minimumOrderUnits', 'orderMultipleUnits', 'protectionEndAt']
    r.update(dict.fromkeys(names))
    if not policy['requested']: return r
    if forecast['salesUnits'] is None:
        r['status'] = 'INCOMPLETE'; r['warnings'] = ['FORECAST_UNAVAILABLE']; return r
    arrival = out['orderAt'] + timedelta(days=out['supplierDays'] + out['internalDays'])
    protection = arrival + timedelta(days=policy['reviewPeriodDays'])
    required = math.ceil(max(forecast['salesUnits'], out['committed'])) + policy['safetyStockUnits']
    position = out['stock'] - out['reservedAfter'] + out['incoming']
    need = max(0, required - position)
    # Common quantities must be valid even when no in-horizon order is suggested.
    check(max(required, position, need) <= 10**9, 'INVALID_QUANTITY')
    r.update(requiredUnits=required, availablePositionUnits=position, committedUnitsWithinHorizon=out['committed'], reservedUnitsWithinHorizon=out['reservedWithin'], reservedUnitsAfterHorizon=out['reservedAfter'], eligibleIncomingUnits=out['incoming'], expectedNewOrderArrivalAt=arrival.isoformat(), rawNeedUnits=need, minimumOrderUnits=policy['minimumOrderUnits'], orderMultipleUnits=policy['orderMultipleUnits'], protectionEndAt=protection.isoformat())
    r['warnings'] = ['NO_DAILY_STOCKOUT_GUARANTEE']
    if arrival >= end or protection >= end:
        r['status'] = 'OUTSIDE_FORECAST_HORIZON'; return r
    suggested = 0 if need == 0 else math.ceil(max(need, policy['minimumOrderUnits']) / policy['orderMultipleUnits']) * policy['orderMultipleUnits']
    check(max(required, position, suggested) <= 10**9, 'INVALID_QUANTITY')
    r.update(status='OK_MONTH_END_ESTIMATE', suggestedUnits=suggested)
    return r


def preview(p):
    validate_request(p)
    r, _, _ = release(); s = get_snapshot(p['baseSnapshotId'])
    out, impacts, warnings = prepare(p, s)
    base, _ = estimate(s['features']); scenario, outside = estimate(out['features'])
    if outside: warnings.append('OUTSIDE_TRAINING_RANGE')
    if p['changes']['history']['mode'] != 'KEEP' and any(h['unknownModeUnits'] for h in p['changes']['history']['months']):
        scenario = {'status': 'ABSTAINED', 'salesUnits': None, 'reason': 'UNKNOWN_CHANNEL_MIX'}
    if scenario['salesUnits'] is not None and scenario['salesUnits'] > out['stock'] - out['reservedAfter'] + out['incoming']:
        warnings.append('FORECAST_EXCEEDS_PLANNED_SUPPLY')
    delta = scenario['salesUnits'] - base['salesUnits'] if base['salesUnits'] is not None and scenario['salesUnits'] is not None else None
    repos = replenishment(p, out, scenario, s['targetMonth'])
    digest = hashlib.sha256(canonical(p)).hexdigest()
    final_path = RELEASE_PATH.parent / 'test-evaluation.json'
    final = _read_verified_json(final_path, FINAL_METRICS_SHA256)
    check(final['artifactSha256'] == r['artifactSha256'], 'INCOMPATIBLE_ARTIFACT')
    saved_metrics = {'partition': 'FINAL_TEST_SAVED', 'origin': 'SYNTHETIC', **final['model']}
    response = {'contractVersion': CONTRACT, 'mode': 'HYPOTHETICAL_SCENARIO', 'origin': 'SYNTHETIC_SCENARIO_NOT_REAL_SALES',
        'status': 'OK' if scenario['status'] == base['status'] == 'OK' and repos['status'] in ('NOT_REQUESTED', 'OK_MONTH_END_ESTIMATE') else 'PARTIAL',
        'scenarioId': 'scenario-' + digest[:24], **{k:s[k] for k in ('productId','locationId','targetMonth','baseSnapshotId')},
        'horizonMonths': 1, 'timeZone': 'America/La_Paz', 'featureCutoffAt': s['targetMonth'] + '-01T00:00:00-04:00',
        'assumedAsOf': s['targetMonth'] + '-01T00:00:00-04:00', 'recordedAt': datetime.now().astimezone().isoformat(timespec='seconds'),
        'scenarioInputSha256': digest, **identity(r), 'baseline': base, 'scenario': scenario, 'deltaSalesUnits': delta,
        'impacts': impacts, 'replenishment': repos, 'metrics': saved_metrics,
        'assumptions': ['Ventas, sensibilidad al precio y planes sintéticos. No es historia comercial certificada.', 'La cotización y el costo no son variables causales de ventas en este modelo. Pueden validar una compra hipotética.', 'Ventas observadas no equivalen a demanda total. No se crean compras ni se modifica inventario.', 'TEST se evaluó una sola vez: 1008 filas. La política de rangos se abstuvo en 6, sin ajustar el modelo después. Las métricas mostradas describen el modelo sobre las 1008 filas.'],
        'warnings': warnings}
    schema = json.loads((ROOT / 'v2/contracts/scenarios.v1.json').read_text(encoding='utf8'))['response_schema']
    # Runtime extension: detailed traces for up to 100 orders and 100 shipments.
    # Keep the original design contract bytes immutable for dataset provenance.
    schema['$defs']['response']['properties']['impacts']['maxItems'] = 2000
    check(not list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(response)), 'INCOHERENT_RESPONSE')
    return response
