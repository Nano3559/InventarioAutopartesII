"""V2-07: revisión independiente, política por hechos y pruebas de corrupción."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from v2.structure import ROOT
from v2.validate_build import (canonical_hash, check_rows, cutoff, inspect_build,
    instant, month_offset, read_table, split_issues, strict_json, training_statistics)
from v2.scenario_checks import assess, apply_scenario, base_facts, scenario_suite, set_target

BUILD=ROOT/"data/repuestopro_v2/2.0.0/academic-20261114-03"


class ScenarioPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design=json.loads((ROOT/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))["scenario_design"]

    def test_all_57_scenarios_and_eight_combinations_have_concrete_fixtures(self):
        records=scenario_suite(self.design)
        self.assertEqual(len(records),65)
        self.assertEqual({r["id"] for r in records},{c["scenario_id"] for c in self.design["scenarios"]}|{c["id"] for c in self.design["mandatory_combinations"]})
        for r in records:
            with self.subTest(case=r["id"]):
                self.assertTrue(r["passed"],r["actual"])
                self.assertNotIn("scenario_id",r["facts"])
                self.assertNotIn("expected_action",r["facts"])

    def test_price_increase_does_not_require_sales_decrease(self):
        for target in [0,3,8,25]:
            f=apply_scenario(base_facts(),"N09");set_target(f,target)
            r=assess(f)
            self.assertEqual(r["action"],"KEEP")
            self.assertEqual(r["features"]["variacion_precio_menor_conocida"],.25)
            self.assertEqual(r["target_units"],target)

    def test_future_price_event_cannot_change_inputs(self):
        f=apply_scenario(base_facts(),"A01");r=assess(f)
        f["unannounced_price_event"]["retail"]=999
        self.assertEqual(assess(f)["features"],r["features"])
        f=apply_scenario(base_facts(),"G09")
        self.assertIsNone(assess(f)["features"]["variacion_precio_menor_conocida"])

    def test_feature_leakage_is_rejected_even_under_an_approved_name(self):
        f=base_facts();f["feature_inputs"]={"ventas_mes_anterior":999}
        self.assertEqual(assess(f)["action"],"REJECT")
        f=base_facts();f["feature_available_at"]={"ventas_mes_anterior":"2026-02-02T00:00:00-04:00"}
        self.assertEqual(assess(f)["action"],"REJECT")

    def test_returns_reduce_debt_first_and_wait_for_inspection(self):
        f=apply_scenario(base_facts(),"A21");r=assess(f)
        self.assertEqual(r["refund"],{"debt_reduction":70,"cash_refund":30,"sellable_return_units":0})
        self.assertEqual(r["target_units"],8)
        f["refund"]["inspected"]=True
        self.assertEqual(assess(f)["refund"]["sellable_return_units"],2)

    def test_early_and_late_voids_have_different_frozen_label_treatment(self):
        self.assertEqual(assess(apply_scenario(base_facts(),"A24"))["action"],"KEEP")
        late=assess(apply_scenario(base_facts(),"A22"))
        self.assertEqual(late["action"],"REVIEW")
        self.assertEqual(late["target_units"],8)

    def test_zero_unknown_stock_and_unknown_mode_remain_distinct(self):
        r=assess(apply_scenario(base_facts(),"G06"))
        self.assertEqual(r["target_units"],0)
        self.assertIsNone(r["features"]["dias_sin_stock_mes_anterior"])
        self.assertEqual(r["features"]["cobertura_stock_mes_anterior"],0)
        self.assertIsNone(r["features"]["proporcion_por_mayor_mes_anterior"])
        r=assess(apply_scenario(base_facts(),"G05"))
        self.assertEqual(r["features"]["proporcion_por_mayor_mes_anterior"],.25)
        self.assertEqual(r["features"]["cobertura_modalidad_mes_anterior"],.5)

    def test_old_fx_is_preserved_and_unknown_fx_is_not_filled(self):
        old=assess(apply_scenario(base_facts(),"G07"))
        self.assertEqual(old["features"]["tipo_cambio_bs_usd_conocido"],10)
        self.assertEqual(old["features"]["antiguedad_tipo_cambio_dias"],31)
        unknown=assess(apply_scenario(base_facts(),"G08"))
        self.assertIsNone(unknown["features"]["tipo_cambio_bs_usd_conocido"])
        self.assertIsNone(unknown["features"]["variacion_tipo_cambio_ultimo_mes"])

    def test_current_price_and_equal_price_do_not_reconstruct_history_or_mode(self):
        current=assess(apply_scenario(base_facts(),"G10"))
        self.assertIsNone(current["features"]["precio_menor_cierre_anterior_bs"])
        equal=assess(apply_scenario(base_facts(),"G14"))
        self.assertEqual(equal["features"]["cobertura_modalidad_mes_anterior"],0)

    def test_new_category_routes_to_unknown_without_inference_or_encoding_fit(self):
        for cat in [None,999]:
            f=base_facts();f["categoryId"]=cat
            r=assess(f);self.assertEqual(r["category_route"],"UNKNOWN")
            self.assertEqual(r["features"]["categoryId"],cat)

    def test_open_target_blocks_training_but_not_inference(self):
        f=apply_scenario(base_facts(),"G04")
        self.assertEqual(assess(f)["action"],"REVIEW")
        f.update(purpose="INFERENCE",target_units=None)
        self.assertEqual(assess(f)["action"],"KEEP")

    def test_context_review_does_not_exclude_valid_sales(self):
        r=assess(apply_scenario(base_facts(),"G17"))
        self.assertEqual(r["action"],"REVIEW")
        self.assertEqual(r["core_row_action"],"KEEP")

    def test_invalid_prices_units_and_outputs_are_rejected(self):
        for bad in [0,-1,float("nan"),float("inf")]:
            f=base_facts();f["prices"]["retail"]=bad
            self.assertEqual(assess(f)["action"],"REJECT")
            f=base_facts();f["plan"]["retail"]=bad
            self.assertEqual(assess(f)["action"],"REJECT")
        f=base_facts();f["fx"]["unit"]="USD/Bs"
        self.assertEqual(assess(f)["action"],"REJECT")
        for bad in [-1,float("nan"),float("inf")]:
            f=base_facts();f["prediction"]=bad
            self.assertEqual(assess(f)["action"],"REJECT")

    def test_partition_contamination_is_rejected(self):
        for field,value in [("transform_fit_partitions",["TRAIN","VALIDATION"]),
                            ("model_selection_partitions",["TEST"]),
                            ("test_origin","V1_ALREADY_OBSERVED"),
                            ("split_month_assignments",{"2026-01":["TRAIN","TEST"]})]:
            f=base_facts();f[field]=value
            self.assertEqual(assess(f)["action"],"REJECT")

    def test_timezone_boundaries_leap_day_and_year_change(self):
        for timestamp,month in [("2026-03-01T03:59:59+00:00","2026-02"),
                                ("2026-03-01T04:00:00+00:00","2026-03"),
                                ("2024-03-01T03:59:59+00:00","2024-02"),
                                ("2026-01-01T03:59:59+00:00","2025-12")]:
            self.assertEqual(instant(timestamp).astimezone(cutoff(month).tzinfo).strftime("%Y-%m"),month)
        self.assertEqual((cutoff("2024-03")-cutoff("2024-02")).days,29)
        with self.assertRaises(ValueError):instant("2026-02-30T00:00:00-04:00")
        with self.assertRaises(ValueError):instant("2026-02-01T00:00:00")


class IndependentBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema=json.loads((BUILD/"schema.json").read_text(encoding="utf-8"))
        cls.catalog=json.loads((BUILD/"catalog_reference.json").read_text(encoding="utf-8"))
        cls.base=read_table(BUILD/"base_mensual.csv",cls.schema["design"]["supporting_tables"]["base_mensual.csv"]["columns"])
        cls.rows=read_table(BUILD/"dataset_supervisado.csv",cls.schema["columns"])
        import csv
        with (BUILD/"simulation_ledger.csv").open(encoding="utf-8",newline="") as f:
            cls.ledger=[{k:(v if k=="mes" else int(v)) for k,v in r.items()} for r in csv.DictReader(f)]

    def test_published_build_passes_independent_validator(self):
        report=inspect_build(BUILD)
        self.assertEqual(report["status"],"PASSED",report["failures"])
        self.assertFalse(report["test_target_statistics_computed"])
        self.assertNotIn("TEST",report["statistics"])
        self.assertEqual(report["counts"]["supervised"],3528)

    def test_optional_feature_corruption_is_detected(self):
        for name in ["proporcion_por_mayor_mes_anterior","cobertura_modalidad_mes_anterior",
            "precio_menor_cierre_anterior_bs","variacion_precio_menor_conocida","tipo_cambio_bs_usd_conocido",
            "variacion_tipo_cambio_ultimo_mes","antiguedad_tipo_cambio_dias","cobertura_stock_mes_anterior","categoryId","mes_sin"]:
            rows=copy.deepcopy(self.rows);r=next(x for x in rows if x[name] is not None);r[name]+=1
            with self.subTest(feature=name):self.assertTrue(check_rows(self.base,rows,self.ledger,self.catalog))

    def test_stock_ledger_and_snapshot_corruption_are_detected(self):
        for field in ["received_units","transit_closing","latent_units"]:
            ledger=copy.deepcopy(self.ledger)
            ledger[0][field]=-1
            self.assertTrue(check_rows(self.base,self.rows,ledger,self.catalog))
        base=copy.deepcopy(self.base);base[0]["history_snapshot_id"]="different"
        self.assertIn("BASE_SNAPSHOT_HASH",check_rows(base,self.rows,self.ledger,self.catalog))

    def test_split_tampering_and_duplicate_rows_are_detected(self):
        split=json.loads((BUILD/"split_manifest.json").read_text(encoding="utf-8"))
        split["sets"]["TRAIN"]["end"]="2026-04"
        self.assertTrue(split_issues(self.rows,split))
        rows=self.rows+[self.rows[0]]
        self.assertIn("DUPLICATE_SUPERVISED",check_rows(self.base,rows,self.ledger,self.catalog))

    def test_statistics_cannot_depend_on_test_targets(self):
        before=training_statistics(self.rows,self.schema)
        rows=copy.deepcopy(self.rows)
        for r in rows:
            if r["mes_objetivo"]>="2026-07":r["target_ventas_mes"]=999999
        self.assertEqual(training_statistics(rows,self.schema),before)

    def test_nonfinite_json_and_csv_values_are_rejected(self):
        with self.assertRaises(ValueError):strict_json('{"value":NaN}')
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="validator-") as tmp:
            p=Path(tmp)/"fixture.csv";p.write_text("value\nNaN\n",encoding="utf-8")
            with self.assertRaises(ValueError):read_table(p,[{"name":"value","type":"number","nullable":False}])

    def test_rewritten_manifest_and_checksums_do_not_replace_registered_identity(self):
        import shutil
        from v2.structure import sha256_file
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="manifest-attack-") as tmp:
            root=Path(tmp);dest=root/"data/repuestopro_v2/fixture"
            shutil.copytree(BUILD,dest)
            for name in ["catalog_reference.json","v2/generate.py","v2/contracts/preparation.v2.json","v2/contracts/calibration.v2.json"]:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            manifest=json.loads((dest/"manifest.json").read_text(encoding="utf-8"))
            manifest["assumptions"].append("Unauthorized metadata replacement")
            (dest/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
            lines=[]
            for line in (dest/"checksums.sha256").read_text(encoding="utf-8").splitlines():
                _,name=line.split("  ",1);lines.append(sha256_file(dest/name)+"  "+name)
            (dest/"checksums.sha256").write_text("\n".join(lines)+"\n",encoding="utf-8")
            report=inspect_build(dest,root=root)
            self.assertIn("UNREGISTERED_OR_CHANGED_MANIFEST",report["failures"])

    def test_report_publication_is_read_only_for_build_and_refuses_overwrite(self):
        import shutil
        from v2.validate import validate
        from v2.structure import sha256_file
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="validation-report-") as tmp:
            root=Path(tmp);dest=root/"data/repuestopro_v2/2.0.0/academic-20261114-03"
            shutil.copytree(BUILD,dest)
            for name in ["catalog_reference.json","v2/generate.py","v2/validate.py","v2/validate_build.py","v2/scenario_checks.py","v2/contracts/preparation.v2.json","v2/contracts/calibration.v2.json"]:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            before={p.name:sha256_file(p) for p in dest.iterdir()}
            output,report=validate("academic-20261114-03","first",root=root)
            self.assertEqual(report["policy_cases_passed"],65)
            self.assertFalse(report["training_authorized"])
            self.assertEqual(before,{p.name:sha256_file(p) for p in dest.iterdir()})
            self.assertNotIn("TEST",(output/"distribuciones.csv").read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):validate("academic-20261114-03","first",root=root)


if __name__=="__main__":unittest.main()
