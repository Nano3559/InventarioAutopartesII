"""Pruebas de perfilado con fixtures temporales. Sin datasets finales o modelos."""
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from v2.profile_sources import Numbers, TransactionProfile, approved_source, month_at, profile_monash, profile_uci, write_report
from v2.structure import ROOT, sha256_file


class ProfilingTests(unittest.TestCase):
    def fixture(self):
        parent = ROOT / "tmp/profile-20261114-01"
        parent.mkdir(parents=True, exist_ok=True)
        directory = tempfile.TemporaryDirectory(dir=parent, prefix="test-")
        self.addCleanup(directory.cleanup)
        return Path(directory.name)

    def test_quantities_distinguish_missing_zero_negative_and_invalid(self):
        values = Numbers()
        for value in [None, "", 0, 1, 2, -1, .5, True, float("inf"), "wrong"]:
            values.add(value)
        result = values.summary()
        self.assertEqual(result["valid"], 5)
        self.assertEqual(result["missing"], 2)
        self.assertEqual(result["invalid"], 3)
        self.assertEqual(result["zero"], 1)
        self.assertEqual(result["negative"], 1)
        self.assertEqual(result["fractional"], 1)

    def test_empty_statistics_do_not_invent_zero_mean(self):
        self.assertIsNone(Numbers().summary()["mean"])

    def test_month_order_includes_year_change(self):
        self.assertEqual(month_at(datetime(1998, 12, 1), 1), "1999-01")

    def test_tsf_missing_is_not_zero_and_raw_is_unchanged(self):
        path = self.fixture() / "reference.tsf"
        path.write_text("@frequency monthly\n@missing true\n@data\nA:1998-01-01 00-00-00:0,?,2\nB:1998-01-01 00-00-00:0,0,0\nC:1998-01-01 00-00-00:0,0,0\n", encoding="utf-8")
        before = sha256_file(path)
        result = profile_monash(path)
        self.assertEqual(result["series_count"], 3)
        self.assertEqual(result["observed_values"]["missing"], 1)
        self.assertEqual(result["observed_values"]["zero"], 7)
        self.assertEqual(result["complete_series"], 2)
        self.assertEqual(result["complete_all_zero_series"], 2)
        self.assertEqual(result["duplicate_trajectories_after_first"], 1)
        self.assertEqual(result["monthly_coverage"]["1998-02"]["missing"], 1)
        self.assertEqual(sha256_file(path), before)

    def test_trailing_missing_differs_from_internal_missing(self):
        path = self.fixture() / "reference.tsf"
        path.write_text("@data\nA:1998-01-01 00-00-00:0,1,?\nB:1998-01-01 00-00-00:0,?,1\n", encoding="utf-8")
        result = profile_monash(path)
        self.assertEqual(result["series_with_missing"], 2)
        self.assertEqual(result["series_with_trailing_missing"], 1)

    def test_uci_cancellation_flags_do_not_replace_quantity(self):
        profile = TransactionProfile()
        profile.add(["C1", "A", "X", -2, datetime(2010,1,1), 5, None, "UK"], "first")
        profile.add(["2", "A", "X", -1, datetime(2010,1,2), 5, 1, "UK"], "first")
        profile.add(["C3", "A", "X", 1, datetime(2010,1,3), 0, 1, "UK"], "first")
        result = profile.summary()
        self.assertEqual(result["quantity"]["negative"], 2)
        self.assertEqual(result["flags"]["c_prefix_rows"], 2)
        self.assertEqual(result["flags"]["negative_quantity_without_c_prefix"], 1)
        self.assertEqual(result["flags"]["c_prefix_with_positive_quantity"], 1)
        self.assertEqual(result["missing_by_column"]["customer_id"], 1)

    def test_duplicate_lines_across_sheets_are_reported_not_removed(self):
        profile = TransactionProfile()
        row = [1, "A", "X", 2, datetime(2010,1,1), 5, 1, "UK"]
        profile.add(row, "first")
        profile.add(row, "second")
        profile.add([1, "A", "X", 3, datetime(2010,1,1), 5, 1, "UK"], "second")
        result = profile.summary()
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["exact_duplicate_rows_after_first"], 1)
        self.assertEqual(result["cross_sheet_duplicate_occurrences"], 1)
        self.assertEqual(result["repeated_invoice_product_groups"], 1)

    def test_xlsx_is_read_only_closed_and_reports_overlap(self):
        header = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
        row = [1, "A", "X", 2, datetime(2010,1,1), 5, 1, "UK"]
        sheets = [SimpleNamespace(title=name,iter_rows=lambda **kwargs:iter([header,row])) for name in ("first","second")]
        closed = []
        book = SimpleNamespace(worksheets=sheets,close=lambda:closed.append(True))
        calls = []
        def load(*args, **kwargs):
            calls.append(kwargs)
            return book
        with patch.dict(sys.modules,{"openpyxl":SimpleNamespace(load_workbook=load)}):
            result = profile_uci("fixture.xlsx")
        self.assertTrue(calls[0]["read_only"])
        self.assertFalse(calls[0]["data_only"])
        self.assertTrue(closed)
        self.assertIsNotNone(result["sheet_date_overlap"])
        self.assertEqual(result["combined"]["rows"], 2)

    def test_report_writer_never_overwrites_existing_results(self):
        path = self.fixture() / "report.json"
        write_report(path, {"rows":1})
        with self.assertRaises(FileExistsError):
            write_report(path, {"rows":2})
        self.assertEqual(json.loads(path.read_text())["rows"], 1)

    def test_other_sources_cannot_be_profiled_by_this_entrypoint(self):
        for source in ("m5_walmart", "corporacion_favorita", "automotive_spare_parts_demand"):
            with self.assertRaises(ValueError):
                approved_source(source, ROOT)
