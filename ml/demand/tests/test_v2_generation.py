"""Build V2 con fixtures y publicaciones en tmp, sin entrenar o tocar RAW."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from v2.generate import ROOT, build, digest, load_inputs, rng, simulate, validate_generated


class GenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=load_inputs()
        cls.tables=simulate(*cls.inputs)

    def test_reference_grid_and_counts(self):
        result=validate_generated(self.tables,self.inputs[2])
        self.assertEqual(result["rows_base"],56*3*24)
        self.assertEqual(result["rows_supervised"],56*3*21)
        self.assertFalse(result["training_authorized"])

    def test_same_inputs_reproduce_all_tables_without_mutation(self):
        before=digest(self.inputs)
        self.assertEqual(digest(simulate(*self.inputs)),digest(self.tables))
        self.assertEqual(digest(self.inputs),before)

    def test_streams_are_separate_by_mechanism_and_partition(self):
        self.assertEqual(rng(42,"counts",1,"TRAIN").random(),rng(42,"counts",1,"TRAIN").random())
        self.assertNotEqual(rng(42,"counts",1,"TEST").random(),rng(42,"counts",1,"TRAIN").random())
        self.assertNotEqual(rng(42,"stock",1,"TEST").random(),rng(42,"counts",1,"TEST").random())

    def test_no_reserved_products_or_warehouse_and_exact_contract(self):
        catalog=self.inputs[3]
        base,rows,audit,ledger=self.tables
        self.assertFalse({x["productId"] for x in base}&set(catalog["reserved_product_ids"]))
        self.assertEqual({x["locationId"] for x in base},{5,6,7})
        self.assertEqual(set(rows[0]),{x["name"] for x in self.inputs[2]["columns"]})
        self.assertNotIn("latent_demand_units",rows[0])

    def test_common_fx_is_identical_for_each_cutoff(self):
        grouped={}
        for row in self.tables[1]:
            grouped.setdefault(row["mes_objetivo"],set()).add(row["tipo_cambio_bs_usd_conocido"])
        self.assertTrue(all(len(v)==1 for v in grouped.values()))

    def test_optional_nulls_are_not_replaced_with_zero(self):
        rows=self.tables[1]
        self.assertTrue(any(x["dias_sin_stock_mes_anterior"] is None for x in rows))
        for row in rows:
            if not row["ventas_mes_anterior"]:
                self.assertIsNone(row["proporcion_por_mayor_mes_anterior"])
                self.assertIsNone(row["cobertura_modalidad_mes_anterior"])
        self.assertTrue(any(x["variacion_precio_menor_conocida"] is None for x in rows))

    def test_stock_in_transit_is_not_immediately_sellable(self):
        ledger=self.tables[3]
        delayed=[x for x in ledger if x["opening_stock"]==0 and x["received_units"]==0 and x["sent_units"]>0]
        self.assertTrue(delayed)
        self.assertTrue(all(x["sold_units"]==0 for x in delayed))
        self.assertTrue(any(x["latent_units"]>x["sold_units"] for x in ledger))

    def test_duplicate_and_missing_month_block_publication(self):
        for kind in ["duplicate","missing"]:
            tables=copy.deepcopy(self.tables)
            if kind=="duplicate":tables[0].append(copy.deepcopy(tables[0][0]))
            else:tables[0].pop(0)
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                validate_generated(tables,self.inputs[2])

    def test_corrupted_lag_or_target_blocks_publication(self):
        for name in ["ventas_hace_3_meses","target_ventas_mes"]:
            tables=copy.deepcopy(self.tables);tables[1][0][name]+=1
            with self.subTest(name=name),self.assertRaises(ValueError):
                validate_generated(tables,self.inputs[2])

    def test_invalid_price_and_broken_stock_block_publication(self):
        for index,name in [(0,"precio_mayor_cierre_bs"),(3,"closing_stock")]:
            tables=copy.deepcopy(self.tables);tables[index][0][name]=-1
            with self.subTest(name=name),self.assertRaises(ValueError):
                validate_generated(tables,self.inputs[2])

    def test_future_history_and_future_price_plan_block_publication(self):
        for name in ["ventas_disponibles_at","plan_precios_disponible_at"]:
            tables=copy.deepcopy(self.tables)
            # Diciembre es la historia inmediata de la primera fila de enero.
            row=next(x for x in tables[0] if x["mes"]=="2024-12" and x["productId"]==1 and x["locationId"]==5)
            row[name]="2030-01-01T00:00:00-04:00"
            with self.subTest(name=name),self.assertRaises(ValueError):
                validate_generated(tables,self.inputs[2])

    def test_empty_build_is_not_valid(self):
        with self.assertRaises(ValueError):
            validate_generated(([],[],[],[]),self.inputs[2])

    def test_publish_new_builds_and_refuse_overwrite(self):
        import shutil
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="generation-test-") as directory:
            root=Path(directory)
            # Solo copiar contratos y perfiles, nunca RAW ni datos V1.
            paths=["catalog_reference.json","v2/calibration.py","v2/contracts/calibration.v2.json",
                   "v2/contracts/preparation.v2.json","v2/contracts/dataset_columns.v2.json",
                   "reports/v2/compatibility/compatibility-20261114-01/source_compatibility_matrix.json"]
            paths += [str(Path(e["profile_path"]).relative_to("ml/demand")) for e in self.inputs[0]["input_evidence"]]
            for name in paths:
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
            first,_,manifest=build("first",root=root)
            second,_,_=build("second",root=root)
            self.assertFalse(manifest["training_authorized"])
            self.assertFalse(manifest["scenario_coverage"]["all_57_scenarios_validated"])
            for name in ["base_mensual.csv","dataset_supervisado.csv","escenarios_metadatos.csv","simulation_ledger.csv"]:
                self.assertEqual((first/name).read_bytes(),(second/name).read_bytes())
            before=(first/"checksums.sha256").read_bytes()
            with self.assertRaises(FileExistsError):build("first",root=root)
            self.assertEqual((first/"checksums.sha256").read_bytes(),before)
            for line in before.decode().splitlines():
                from v2.structure import sha256_file
                sha,name=line.split("  ",1);self.assertEqual(sha256_file(first/name),sha)
            with (first/"dataset_supervisado.csv").open(encoding="utf-8",newline="") as f:
                self.assertEqual(len(list(csv.DictReader(f))),3528)
            self.assertEqual(manifest["split_design"]["sets"]["TEST"]["rows"],504)

    def test_path_injection_is_rejected(self):
        for name in ["../outside","bad/name",".",""]:
            with self.subTest(name=name),self.assertRaises(ValueError):build(name)

    def test_schema_accepts_pending_build_without_claiming_training_readiness(self):
        from v2.structure import validate_contract
        document=copy.deepcopy(self.inputs[2])
        document["design"]["definition_status"]="BUILD_GENERATED_PENDING_EXHAUSTIVE_V2_07"
        validate_contract(document,"dataset_schema")
        document["design"]["definition_status"]="TRAINED"
        with self.assertRaises(Exception):validate_contract(document,"dataset_schema")


if __name__ == "__main__":
    unittest.main()
