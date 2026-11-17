"""Conformity: real 4.0.0 capabilities output against scenario_capabilities.schema.json.

No training, no Neon, no frozen-contract edits. Executes admin_scenarios.py exactly
as the backend scenarioQuery bridge does (python -B, JSON on stdin) and validates the
response bytes with Draft 2020-12.
"""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


class ScenarioCapabilitiesSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (ROOT / 'v2' / 'contracts' / 'scenario_capabilities.schema.json').read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator.check_schema(cls.schema)
        cls.validator = jsonschema.Draft202012Validator(cls.schema)
        cls.response = cls._real_capabilities()

    @classmethod
    def _real_capabilities(cls):
        process = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'admin_scenarios.py')],
            input=json.dumps({'action': 'capabilities'}),
            capture_output=True, text=True, encoding='utf-8',
            cwd=str(ROOT), timeout=60)
        if process.returncode != 0:
            raise AssertionError(f'admin_scenarios.py failed: {process.stderr[-500:]}')
        return json.loads(process.stdout)

    def errors(self, value):
        return list(self.validator.iter_errors(value))

    def test_real_capabilities_response_satisfies_the_full_schema(self):
        self.assertEqual(self.errors(self.response), [])
        self.assertEqual(self.response['datasetVersion'], '4.0.0')
        self.assertEqual(self.response['status'], 'AVAILABLE')

    def test_real_response_includes_every_property_required_by_the_aligned_schema(self):
        for key in ('historyEnd', 'forecastMonth', 'stockTrainingMax'):
            self.assertIn(key, self.response)
        self.assertGreater(len(self.response['snapshots']), 0)
        for snapshot in self.response['snapshots']:
            for key in ('previousMonthUnits', 'historyMonthly'):
                self.assertIn(key, snapshot)
            self.assertEqual(len(snapshot['historyMonthly']), 10)

    def test_schema_rejects_additional_properties_at_every_level(self):
        mutations = (
            lambda d: d.update({'inventedField': True}),
            lambda d: d['snapshots'][0].update({'inventedField': True}),
            lambda d: d['snapshots'][0]['historyMonthly'][0].update({'inventedField': True}),
        )
        for mutate in mutations:
            tampered = copy.deepcopy(self.response)
            mutate(tampered)
            self.assertTrue(self.errors(tampered))

    def test_schema_rejects_missing_new_required_properties(self):
        for key in ('historyEnd', 'forecastMonth', 'stockTrainingMax'):
            tampered = copy.deepcopy(self.response)
            del tampered[key]
            self.assertTrue(self.errors(tampered), key)
        for key in ('previousMonthUnits', 'historyMonthly'):
            tampered = copy.deepcopy(self.response)
            del tampered['snapshots'][0][key]
            self.assertTrue(self.errors(tampered), key)

    def test_new_properties_reject_wrong_types_bounds_and_lengths(self):
        cases = (
            ('forecastMonth bad month', lambda d: d.update({'forecastMonth': '2026-13'})),
            ('forecastMonth not string', lambda d: d.update({'forecastMonth': 202611})),
            ('historyEnd bad month', lambda d: d.update({'historyEnd': 'november'})),
            ('stockTrainingMax negative', lambda d: d.update({'stockTrainingMax': -1})),
            ('stockTrainingMax string', lambda d: d.update({'stockTrainingMax': '150'})),
            ('previousMonthUnits negative',
             lambda d: d['snapshots'][0].update({'previousMonthUnits': -1})),
            ('previousMonthUnits fractional',
             lambda d: d['snapshots'][0].update({'previousMonthUnits': 1.5})),
            ('historyMonthly too short',
             lambda d: d['snapshots'][0].update({'historyMonthly': d['snapshots'][0]['historyMonthly'][:-1]})),
            ('historyMonthly entry fractional units',
             lambda d: d['snapshots'][0]['historyMonthly'][0].update({'units': 0.5})),
            ('historyMonthly entry negative retail',
             lambda d: d['snapshots'][0]['historyMonthly'][0].update({'retailUnits': -1})),
            ('historyMonthly entry bad month',
             lambda d: d['snapshots'][0]['historyMonthly'][0].update({'month': '2026-13'})),
        )
        for name, mutate in cases:
            tampered = copy.deepcopy(self.response)
            mutate(tampered)
            self.assertTrue(self.errors(tampered), name)


if __name__ == '__main__':
    unittest.main()
