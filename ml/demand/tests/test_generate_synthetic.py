"""Pruebas del contrato temporal y separación de casos, sin bases de datos."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from generate_synthetic import HERE, MONTHS, MAX_QUANTITY, build, generate, gray_cases, invalid_cases, split, validate


class DatasetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((HERE/'catalog_reference.json').read_text(encoding='utf-8'))
        cls.base, cls.rows, cls.labels = build(cls.catalog)

    def test_full_panel_and_calendar(self):
        self.assertEqual(len(self.base), 4032)
        self.assertEqual(len(self.rows), 3528)
        self.assertEqual({r['mes'] for r in self.base}, set(MONTHS))
        self.assertEqual({r['locationId'] for r in self.rows}, {5, 6, 7})
        self.assertTrue(all(1 <= r['productId'] <= 56 for r in self.rows))
        validate(self.rows, self.base, self.catalog)

    def test_catalog_cannot_authorize_ghost_reserved_or_duplicate_ids(self):
        for change in ['ghost', 'reserved', 'duplicate', 'bool']:
            catalog = copy.deepcopy(self.catalog)
            if change == 'ghost': catalog['included_product_ids'].append(999999)
            elif change == 'reserved': catalog['included_product_ids'].append(catalog['reserved_product_ids'][0])
            elif change == 'duplicate': catalog['products'].append(catalog['products'][0])
            else: catalog['included_product_ids'][0] = True
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'INVALID_CATALOG'):
                build(catalog)

    def test_integer_overflow_is_rejected_before_conversion(self):
        row = self.rows[0].copy()
        row['target_ventas_mes'] = MAX_QUANTITY + 1
        with self.assertRaisesRegex(ValueError, '^INVALID_QUANTITY$'):
            validate([row], self.base, self.catalog, complete=False)
        base = copy.deepcopy(self.base)
        base[0]['ventas_mes'] = MAX_QUANTITY + 1
        with self.assertRaisesRegex(ValueError, '^INVALID_BASE$'):
            validate(self.rows, base, self.catalog)

    def test_ambiguous_evidence_is_not_a_known_target(self):
        cases = gray_cases(self.catalog)
        self.assertTrue(all(not c['apto_entrenamiento'] and c['requiere_revision'] for c in cases))
        self.assertTrue(all(c['target_demanda_real'] is None for c in cases))
        self.assertTrue(all(c['disponible_desde'] > c['corte_prediccion'] for c in cases))
        self.assertEqual(next(c for c in cases if c['escenario'] == 'SIN_STOCK')['ventas_observadas'], 0)

    def test_invalid_cases_rejected_for_expected_reason(self):
        for case in invalid_cases(self.rows[0]):
            with self.subTest(case=case['case_id']):
                with self.assertRaisesRegex(ValueError, '^'+case['expected_error']+'$'):
                    validate(case['records'], self.base, self.catalog, complete=False)

    def test_future_target_changes_do_not_change_past_inputs(self):
        history = copy.deepcopy(self.base)
        last = history[-1]
        target_row = next(r for r in self.rows if r['productId']==last['productId']
                          and r['locationId']==last['locationId'] and r['mes_objetivo']==last['mes'])
        row = target_row.copy()
        last['ventas_mes'] += 1
        row['target_ventas_mes'] += 1
        validate([row], history, self.catalog, complete=False)
        self.assertEqual([row[k] for k in ['ventas_mes_anterior','ventas_hace_2_meses','ventas_hace_3_meses']],
                         [target_row[k] for k in ['ventas_mes_anterior','ventas_hace_2_meses','ventas_hace_3_meses']])

    def test_missing_month_and_duplicate_base_are_not_zero_filled(self):
        with self.assertRaisesRegex(ValueError, 'INCOMPLETE_BASE'):
            validate(self.rows, self.base[:-1], self.catalog)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_BASE'):
            validate(self.rows, self.base+[self.base[0]], self.catalog)

    def test_adverse_valid_sales_remain_nonnegative(self):
        self.assertEqual({r['clase_caso'] for r in self.labels}, {'POSITIVO','NEGATIVO'})
        self.assertTrue(any('MAYORISTA' in r['escenario'] for r in self.labels))
        self.assertTrue(any(r['ventas_mes']==0 for r in self.base))
        self.assertTrue(all(type(r['ventas_mes']) is int and r['ventas_mes']>=0 for r in self.base))
        self.assertTrue(all(r['ventas_mes']<=150 for r in self.base))

    def test_complete_months_in_chronological_splits(self):
        counts={name:sum(split(r['mes_objetivo'])==name for r in self.rows)
                for name in ['TRAIN','VALIDATION','TEST']}
        self.assertEqual(counts,dict(TRAIN=2520,VALIDATION=504,TEST=504))
        self.assertEqual(split('2026-03'),'TRAIN')
        self.assertEqual(split('2026-04'),'VALIDATION')
        self.assertEqual(split('2026-07'),'TEST')

    def test_reproducibility_and_quarantine(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=Path(temp)/'a',Path(temp)/'b'
            for folder in [a,b]:
                generate(folder,HERE/'catalog_reference.json')
            for file in a.iterdir():
                if file.name!='manifest.json':
                    self.assertEqual(file.read_bytes(),(b/file.name).read_bytes())
            ma=json.loads((a/'manifest.json').read_text())
            mb=json.loads((b/'manifest.json').read_text())
            self.assertEqual(ma['hashes'],mb['hashes'])
            gray=json.loads((a/'casos_grises.json').read_text())
            self.assertEqual(len(gray),10)
            self.assertTrue(all(r['apto_entrenamiento'] is False for r in gray))
            self.assertNotIn('clase_caso',ma['features'])
            self.assertTrue(all(v in ma['hashes'] for v in ['dataset_supervisado.csv','casos_grises.json']))


if __name__=='__main__':
    unittest.main()
