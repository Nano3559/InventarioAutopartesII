"""Prepara experimentos sin entrenar, muestrear ventas ni cambiar builds."""
import copy
import inspect
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from v2.structure import ROOT, sha256_file
from v2.experiment_preparation import (preflight, preparation_examples, quote_asof,
    receive_and_fulfil, supply_plan, training_feature_profile)

AT="2026-02-01T00:00:00-04:00"


def event(**changes):
    row=dict(value=10,unit="Bs/USD",source_id="SYNTHETIC_REFERENCE",rate_kind="SIMULATED_MARKET_REFERENCE",
             observed_at="2026-01-30T00:00:00-04:00",available_at="2026-01-31T00:00:00-04:00")
    row.update(changes);return row


def order(units=40,**changes):
    row=dict(id="O1",units=units,known_at="2026-01-31T00:00:00-04:00",due_at="2026-02-15T00:00:00-04:00")
    row.update(changes);return row


class ExperimentPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/"v2/contracts/experiments.v2.json").read_text(encoding="utf-8"))

    def plan(self,**changes):
        values=dict(at=AT,sellable=5,reserved=0,history_units=[1,2,3],firm_orders=[order()],incoming=[])
        values.update(changes);return supply_plan(**values)

    def test_named_variants_remove_only_constant_age(self):
        schema=json.loads((ROOT/"v2/contracts/dataset_columns.v2.json").read_text(encoding="utf-8"))
        self.assertEqual(len(schema["design"]["feature_sets"]["v2_full"]),17)
        self.assertEqual([len(g["columns"]) for g in self.contract["feature_sets"]],[5,7,11,13,15,16])
        for g in self.contract["feature_sets"]:
            original=schema["design"]["feature_sets"][g["source_feature_set"]]
            self.assertEqual(g["columns"],[c for c in original if c!="antiguedad_tipo_cambio_dias"])

    def test_feature_profile_ignores_all_labels_and_nontrain_feature_values(self):
        schema={"columns":[{"name":"age","type":"integer","role":"FEATURE"}]}
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="feature-profile-") as tmp:
            p=Path(tmp)/"fixture.csv"
            p.write_text("mes_objetivo,age,target_ventas_mes\n2025-01,2,NOT_A_LABEL\n2025-02,2,NA\n2026-04,NaN,BAD\n2026-07,NaN,SECRET_TEST\n",encoding="utf-8")
            result=training_feature_profile(p,schema,"2025-01","2026-03")
            self.assertEqual(result["rows"],2)
            self.assertEqual(result["columns"]["age"]["constant_value"],2)
            self.assertFalse(result["labels_processed"])

    def test_quote_ages_come_from_dates_not_jitter(self):
        result=preparation_examples()
        self.assertEqual([c["selected"]["age_days"] for c in result["quote_ages"]],[0,2,7,30])
        self.assertTrue(all(c["selected"]["value"]==10 for c in result["quote_ages"]))
        self.assertFalse(result["sampled_sales_dataset_created"])

    def test_future_quotes_and_other_rate_types_cannot_change_asof_value(self):
        known=event()
        future=event(value=float("nan"),observed_at="2026-02-03T00:00:00-04:00",available_at="2026-02-03T00:00:00-04:00")
        purchase=event(value=99,rate_kind="SUPPLIER_PURCHASE")
        self.assertEqual(quote_asof([known],AT),quote_asof([purchase,future,known],AT))
        self.assertEqual(quote_asof([future],AT)["status"],"UNKNOWN")

    def test_same_stream_gives_common_quote_for_all_product_store_queries(self):
        values=[quote_asof([event()],AT) for _ in [(1,5),(2,6),(56,7)]]
        self.assertEqual(values,[values[0]]*3)
        self.assertNotIn("productId",inspect.signature(quote_asof).parameters)

    def test_invalid_quote_and_conflicting_revision_are_rejected(self):
        for bad in [0,-1,float("nan"),float("inf")]:
            with self.assertRaises(ValueError):quote_asof([event(value=bad)],AT)
        with self.assertRaises(ValueError):quote_asof([event(unit="USD/Bs")],AT)
        with self.assertRaises(ValueError):quote_asof([event(),event(value=11)],AT)

    def test_known_wholesale_can_be_fulfilled_without_stock_created_from_target(self):
        for units in [20,40,80]:
            plan=self.plan(firm_orders=[order(units)])
            state=receive_and_fulfil(sellable=5,pending=plan["order_units"],received=plan["order_units"],requested=units)
            self.assertEqual(state["sold"],units)
            self.assertGreaterEqual(state["closing_stock"],5)
            self.assertEqual(plan["order_units"]%6,0)
        self.assertNotIn("target_units",inspect.signature(supply_plan).parameters)
        self.assertNotIn("requested",inspect.signature(supply_plan).parameters)

    def test_unknown_future_order_does_not_create_pre_cutoff_stock(self):
        late=order(40,known_at="2026-02-10T00:00:00-04:00")
        plan=self.plan(firm_orders=[late])
        self.assertEqual(plan["known_commitments"],0)
        self.assertEqual(plan["order_units"],6)
        fulfilled=receive_and_fulfil(sellable=5,pending=6,received=6,requested=40)
        self.assertEqual(fulfilled["sold"],11)
        self.assertEqual(fulfilled["unmet_simulated_units"],29)

    def test_recurrent_history_and_known_order_are_not_added_twice(self):
        plan=self.plan(sellable=0,history_units=[40,40,40])
        self.assertEqual(plan["required_units"],45)
        self.assertEqual(plan["order_units"],48)

    def test_identified_reservations_are_not_purchased_twice(self):
        plan=self.plan(sellable=50,reserved=40,history_units=[40,40,40],firm_orders=[order(reserved_units=40)])
        self.assertEqual(plan["known_unreserved_commitments"],0)
        self.assertEqual(plan["order_units"],0)
        with self.assertRaises(ValueError):self.plan(reserved=4,firm_orders=[order()])

    def test_late_incoming_cannot_fulfil_an_earlier_order(self):
        incoming=dict(id="I1",pending_units=40,status="IN_TRANSIT",known_at="2026-01-31T00:00:00-04:00",expected_at="2026-02-20T00:00:00-04:00")
        plan=self.plan(incoming=[incoming])
        self.assertEqual(plan["incoming_firm_pending"],0)
        incoming["expected_at"]="2026-02-10T00:00:00-04:00"
        self.assertEqual(self.plan(incoming=[incoming])["order_units"],0)

    def test_partial_or_missing_receipts_preserve_unmet_units_and_transit(self):
        state=receive_and_fulfil(sellable=5,pending=42,received=21,requested=40)
        self.assertEqual(state,{"sold":26,"closing_stock":0,"remaining_transit":21,"unmet_simulated_units":14})
        self.assertEqual(receive_and_fulfil(sellable=5,pending=42,received=0,requested=40)["sold"],5)
        with self.assertRaises(ValueError):receive_and_fulfil(sellable=0,pending=2,received=3,requested=3)

    def test_calendar_window_excludes_next_month_and_handles_leap_year(self):
        at="2024-02-01T00:00:00-04:00"
        next_month=order(80,known_at=at,due_at="2024-03-01T00:00:00-04:00")
        p=self.plan(at=at,firm_orders=[next_month])
        self.assertEqual(p["known_commitments"],0)
        self.assertEqual(p["required_by"],"2024-03-01T00:00:00-04:00")

    def test_invalid_or_duplicate_supply_facts_are_rejected(self):
        with self.assertRaises(ValueError):self.plan(firm_orders=[order(),order()])
        with self.assertRaises(ValueError):self.plan(history_units=[0,1])
        with self.assertRaises(ValueError):self.plan(lot_size=0)
        with self.assertRaises(ValueError):self.plan(sellable=-1)

    def test_expanding_folds_and_fit_budget_are_explicit_and_unexecuted(self):
        c=self.contract
        self.assertFalse(c["training_authorized"])
        self.assertEqual(c["execution_budget"]["actual_fits"],0)
        self.assertEqual(c["execution_budget"]["maximum_planned_fits"],6*3*(4+1)+12)
        for fold in c["temporal_validation"]["folds"]:
            self.assertLess(fold["train"][1],fold["validation"][0])
            self.assertLessEqual(fold["validation"][1],"2026-03")

    def test_grid_is_supported_by_installed_classes_without_fitting(self):
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        rf=self.contract["models"]["random_forest"]
        self.assertTrue(set(rf["fixed"])|set(rf["grid"])<=set(inspect.signature(RandomForestRegressor).parameters))
        self.assertTrue(set(self.contract["models"]["linear_regression"]["parameters"])<=set(inspect.signature(LinearRegression).parameters))

    def test_preflight_publishes_only_preparation_and_refuses_overwrite(self):
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="experiment-plan-") as tmp:
            root=Path(tmp);prep=json.loads((ROOT/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
            relative=self.contract["input_build"]["relative_path"]
            shutil.copytree(ROOT/relative,root/relative)
            paths=["v2/contracts/preparation.v2.json","v2/contracts/experiments.v2.json",str(Path(prep["dataset_validation"]["report"]).relative_to("ml/demand"))]
            for name in paths:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
            before={p.name:sha256_file(p) for p in (root/relative).iterdir()}
            with patch.object(RandomForestRegressor,"fit",side_effect=AssertionError("training forbidden")),patch.object(LinearRegression,"fit",side_effect=AssertionError("training forbidden")):
                path,result=preflight("first",root=root)
            self.assertEqual(result["actual_fit_count"],0)
            self.assertEqual([v["train_rows"] for v in result["folds"]],[1008,1512,2016])
            self.assertEqual([v["validation_rows"] for v in result["folds"]],[504,504,504])
            self.assertEqual(before,{p.name:sha256_file(p) for p in (root/relative).iterdir()})
            self.assertFalse(list(root.rglob("*.joblib")))
            self.assertFalse(list(root.rglob("experiments.csv")))
            with self.assertRaises(FileExistsError):preflight("first",root=root)


if __name__=="__main__":unittest.main()
