"""Bounded stdin/stdout API bridge. No operational database or TEST reads."""
import json
import sys
from v2.scenario_runtime import capabilities, snapshot_view, preview, ScenarioError
from v2 import calendar2026_runtime


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ScenarioError('INVALID_INPUT')
        result[key] = value
    return result


def reject_constant(_):
    raise ScenarioError('INVALID_INPUT')


if __name__ == '__main__':
    try:
        text = sys.stdin.read(100001)
        if len(text) > 100000: raise ScenarioError('INVALID_INPUT')
        p = json.loads(text, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
        if not isinstance(p, dict): raise ScenarioError('INVALID_INPUT')
        action = p.pop('action', None)
        current = str(p.get('baseSnapshotId', '')).startswith('calendar-2026-')
        if action == 'capabilities' and not p: result = calendar2026_runtime.capabilities()
        elif action == 'snapshot' and set(p) == {'baseSnapshotId'}: result = (calendar2026_runtime.snapshot_view if current else snapshot_view)(p['baseSnapshotId'])
        elif action == 'preview': result = (calendar2026_runtime.preview if current else preview)(p)
        else: raise ScenarioError('INVALID_INPUT')
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    except Exception as error:
        print(json.dumps({'error': {'code': error.code if isinstance(error, ScenarioError) else 'MODEL_UNAVAILABLE'}}))
        sys.exit(1)
