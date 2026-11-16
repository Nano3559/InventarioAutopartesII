"""V2-04C: descripción de dos fuentes aprobadas, sin limpieza o entrenamiento.

XLSX se abre read_only, sin guardar. Los reportes no contienen IDs de clientes.
"""
from array import array
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

from .structure import ROOT, sha256_file, token, inventory_digest


class Numbers:
    def __init__(self):
        self.values = array("d")
        self.missing = self.invalid = 0

    def add(self, value):
        if value is None or value == "":
            self.missing += 1
            return None
        if isinstance(value, bool):
            self.invalid += 1
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            self.invalid += 1
            return None
        if not math.isfinite(number):
            self.invalid += 1
            return None
        self.values.append(number)
        return number

    def summary(self):
        import numpy as np
        values = np.frombuffer(self.values, dtype="float64")
        result = dict(valid=len(values), missing=self.missing, invalid=self.invalid)
        if not len(values):
            return dict(result, minimum=None, maximum=None, mean=None, median=None, p95=None, p99=None, zero=0, negative=0, fractional=0)
        return dict(result, minimum=float(values.min()), maximum=float(values.max()), mean=float(values.mean()),
            median=float(np.median(values)), p95=float(np.quantile(values, .95)), p99=float(np.quantile(values, .99)),
            zero=int((values == 0).sum()), negative=int((values < 0).sum()), fractional=int((values != np.trunc(values)).sum()))


def write_report(path, report):
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)


def month_at(start, offset):
    index = start.year * 12 + start.month - 1 + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def profile_monash(path):
    stats = Numbers()
    names = set()
    duplicate_names = 0
    lengths = Counter()
    trajectories = Counter()
    monthly = {}
    summaries = []
    declared = {}
    data = False
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("@"):
                if line.lower() == "@data":
                    data = True
                else:
                    key, _, value = line.partition(" ")
                    if key.lower() != "@attribute":
                        declared[key.lstrip("@")] = value
                continue
            if not data:
                raise ValueError(f"TSF sin @data antes de línea {line_number}")
            name, timestamp, observations = line.split(":", 2)
            start = datetime.strptime(timestamp, "%Y-%m-%d %H-%M-%S")
            if name in names:
                duplicate_names += 1
            names.add(name)
            values = []
            missing = zeros = positive = negative = invalid = longest_zero_run = current_zero_run = 0
            for offset, raw in enumerate(observations.split(",")):
                month = month_at(start, offset)
                bucket = monthly.setdefault(month, dict(slots=0, observed=0, missing=0, invalid=0, zeros=0, positive=0))
                bucket["slots"] += 1
                number = stats.add(None if raw == "?" else raw)
                values.append(number)
                if raw == "?":
                    missing += 1
                    bucket["missing"] += 1
                elif number is None:
                    invalid += 1
                    bucket["invalid"] += 1
                else:
                    bucket["observed"] += 1
                    zeros += number == 0
                    positive += number > 0
                    negative += number < 0
                    bucket["zeros"] += number == 0
                    bucket["positive"] += number > 0
                current_zero_run = current_zero_run + 1 if number == 0 else 0
                longest_zero_run = max(longest_zero_run, current_zero_run)
            trailing_missing = 0
            for v in reversed(values):
                if v is not None:
                    break
                trailing_missing += 1
            lengths[len(values)] += 1
            digest = hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()
            trajectories[digest] += 1
            summaries.append(dict(source_series_id=name, periods=len(values), observed=len(values)-missing-invalid,
                missing=missing, invalid=invalid, zeros=zeros, positive=positive, negative=negative,
                start=month_at(start, 0), end=month_at(start, len(values)-1), trailing_missing=trailing_missing,
                longest_zero_run=longest_zero_run, latest_three_observed=len(values)>=3 and all(v is not None for v in values[-3:])))
    summary = stats.summary()
    return dict(source_id="monash_car_parts", declared_metadata=declared, series_count=len(summaries), unique_series_ids=len(names),
        duplicate_series_ids=duplicate_names, periods_distribution=dict(lengths), observed_values=summary,
        zero_fraction_of_observed=summary["zero"]/summary["valid"] if summary["valid"] else None,
        complete_series=sum(s["missing"] == 0 and s["invalid"] == 0 for s in summaries),
        series_with_missing=sum(s["missing"] > 0 for s in summaries),
        series_with_trailing_missing=sum(s["trailing_missing"] > 0 for s in summaries),
        complete_all_zero_series=sum(s["observed"] == s["periods"] and s["zeros"] == s["periods"] for s in summaries),
        all_observed_zero_series=sum(s["observed"] > 0 and s["zeros"] == s["observed"] for s in summaries),
        series_with_last_three_observed=sum(s["latest_three_observed"] for s in summaries),
        duplicate_trajectory_groups=sum(n > 1 for n in trajectories.values()), duplicate_trajectories_after_first=sum(n-1 for n in trajectories.values()),
        temporal_start=min((s["start"] for s in summaries), default=None), temporal_end=max((s["end"] for s in summaries), default=None),
        monthly_coverage=dict(sorted(monthly.items())), per_series=summaries,
        limitations=["Los signos ? se conservan como faltantes, nunca como cero.",
            "Trayectorias iguales no demuestran productos duplicados. No se eliminó ninguna serie.",
            "No contiene precio, tienda, cotización Bs/USD ni plazo de proveedor. No se construyeron lags o parámetros de simulación."])


def digest_values(values):
    normalized = []
    for v in values:
        if isinstance(v, datetime):
            normalized.append(["date", v.isoformat()])
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            normalized.append(["number", float(v)])
        else:
            normalized.append([type(v).__name__, v])
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=True, separators=(",", ":"), default=str).encode()).digest()


class TransactionProfile:
    def __init__(self):
        self.rows = 0
        self.quantity = Numbers()
        self.price = Numbers()
        self.positive_quantity = Numbers()
        self.positive_price = Numbers()
        self.missing = Counter()
        self.flags = Counter()
        self.monthly = {}
        self.invoices, self.products, self.customers, self.countries = set(), set(), set(), set()
        self.exact = Counter()
        self.first_sheet = {}
        self.cross_sheet_duplicates = 0
        self.pairs = Counter()
        self.start = self.end = None
        self.sheet_names = set()

    def add(self, values, sheet):
        if len(values) != 8:
            raise ValueError("Se esperaban ocho columnas UCI")
        if all(v is None for v in values):
            self.flags["blank_rows"] += 1
            return
        self.rows += 1
        self.sheet_names.add(sheet)
        invoice, product, description, quantity, date, price, customer, country = values
        for label, value in zip(("invoice", "stock_code", "description", "quantity", "invoice_date", "unit_price", "customer_id", "country"), values):
            if value is None or value == "":
                self.missing[label] += 1
        q, p = self.quantity.add(quantity), self.price.add(price)
        if q is not None and q > 0:
            self.positive_quantity.add(q)
        if p is not None and p > 0:
            self.positive_price.add(p)
        cancel = invoice is not None and str(invoice).upper().startswith("C")
        self.flags["c_prefix_rows"] += cancel
        self.flags["negative_quantity_without_c_prefix"] += q is not None and q < 0 and not cancel
        self.flags["c_prefix_with_positive_quantity"] += cancel and q is not None and q > 0
        self.flags["zero_price_with_positive_quantity"] += p == 0 and q is not None and q > 0
        self.flags["negative_price_with_positive_quantity"] += p is not None and p < 0 and q is not None and q > 0
        if isinstance(date, datetime):
            self.start = min(self.start, date) if self.start else date
            self.end = max(self.end, date) if self.end else date
            month = date.strftime("%Y-%m")
            b = self.monthly.setdefault(month, dict(rows=0, c_prefix_rows=0, negative_quantity_rows=0, zero_price_rows=0))
            b["rows"] += 1
            b["c_prefix_rows"] += cancel
            b["negative_quantity_rows"] += q is not None and q < 0
            b["zero_price_rows"] += p == 0
        else:
            self.flags["invalid_or_missing_dates"] += 1
        for value, destination in [(invoice,self.invoices),(product,self.products),(customer,self.customers),(country,self.countries)]:
            if value is not None and value != "":
                destination.add(str(value))
        h = digest_values(values)
        if h in self.first_sheet and self.first_sheet[h] != sheet:
            self.cross_sheet_duplicates += 1
        self.first_sheet.setdefault(h, sheet)
        self.exact[h] += 1
        if invoice is not None and product is not None:
            self.pairs[digest_values([invoice, product])] += 1

    def summary(self):
        return dict(rows=self.rows, quantity=self.quantity.summary(), unit_price=self.price.summary(),
            positive_quantity=self.positive_quantity.summary(), positive_unit_price=self.positive_price.summary(),
            missing_by_column=dict(self.missing), flags=dict(self.flags),
            unique_invoice_identifiers=len(self.invoices), unique_stock_codes=len(self.products),
            unique_nonmissing_customer_ids=len(self.customers), country_count=len(self.countries),
            exact_duplicate_rows_after_first=sum(n-1 for n in self.exact.values()), exact_duplicate_groups=sum(n>1 for n in self.exact.values()),
            repeated_invoice_product_groups=sum(n>1 for n in self.pairs.values()),
            cross_sheet_duplicate_occurrences=self.cross_sheet_duplicates,
            earliest_date=self.start.isoformat() if self.start else None, latest_date=self.end.isoformat() if self.end else None,
            monthly_distribution=dict(sorted(self.monthly.items())))


def profile_uci(path):
    from openpyxl import load_workbook
    workbook = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    combined = TransactionProfile()
    sheets = []
    try:
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            headers = list(next(rows))
            expected = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
            if headers != expected:
                raise ValueError("Cabecera UCI distinta del contrato inspeccionado")
            current = TransactionProfile()
            for values in rows:
                current.add(values, sheet.title)
                combined.add(values, sheet.title)
            sheets.append(dict(sheet=sheet.title, original_headers=headers, **current.summary()))
    finally:
        workbook.close()
    overlap = None
    if len(sheets) == 2:
        a,b = sheets
        start=max(a["earliest_date"],b["earliest_date"])
        end=min(a["latest_date"],b["latest_date"])
        if start<=end:
            overlap=dict(start=start,end=end)
    return dict(source_id="uci_online_retail_ii", sheets=sheets, combined=combined.summary(), sheet_date_overlap=overlap,
        limitations=["Las filas son líneas, no facturas únicas. Se informa por hoja y combinado, sin crear una tabla combinada persistente.",
            "Se detectan repeticiones de valores decodificados de las ocho celdas. No se elimina ninguna fila ni se decide automáticamente que sea una operación duplicada.",
            "Prefijo C se informa por separado de quantity negativa. Cancelación no equivale automáticamente a devolución operativa de RepuestoPro.",
            "Los precios GBP no son costos, elasticidad causal o tipo de cambio Bs/USD.",
            "No se exportan identificadores de clientes, facturas o productos. Solo conteos y estadísticas.",
            "Las fechas se interpretan como aparecen en Excel, sin inventar zona horaria."])


def approved_source(source_id, root):
    if source_id not in ("monash_car_parts", "uci_online_retail_ii"):
        raise ValueError("Fuente fuera del alcance aprobado")
    manifests = list((root / "sources/manifests" / source_id).glob("*.json"))
    if len(manifests) != 1:
        raise ValueError("Snapshot ambiguo")
    doc = json.loads(manifests[0].read_text(encoding="utf-8"))
    if (doc["processing_status"] != "APPROVED_FOR_PROFILING" or doc.get("profiling_decision") != "APPROVED_ACADEMIC_ONLY"
            or doc.get("license_status") != "VERIFIED" or doc.get("academic_use_status") != "VERIFIED"):
        raise ValueError("Fuente no aprobada")
    if inventory_digest(doc["files"]) != doc["inventory_sha256"] or len(doc["files"]) != 1:
        raise ValueError("Inventario incompatible")
    path = (root / doc["raw_root"] / doc["files"][0]["relative_path"]).resolve()
    if not path.is_relative_to((root / "sources/external_raw").resolve()):
        raise ValueError("RAW fuera de alcance")
    if sha256_file(path) != doc["files"][0]["sha256"]:
        raise ValueError("RAW no coincide con manifest")
    return path, doc


def run(run_id, root=ROOT):
    root = Path(root).resolve()
    inputs = {sid:approved_source(sid, root) for sid in ("monash_car_parts", "uci_online_retail_ii")}
    out = root / "reports/v2/profiling" / token(run_id)
    if not out.resolve().is_relative_to((root / "reports/v2").resolve()):
        raise ValueError("Destino de reporte inválido")
    out.mkdir(parents=True, exist_ok=False)
    for sid, function in [("monash_car_parts",profile_monash),("uci_online_retail_ii",profile_uci)]:
        path, manifest = inputs[sid]
        print("Profiling " + sid, flush=True)
        report = function(path)
        if sha256_file(path) != manifest["files"][0]["sha256"]:
            raise ValueError("RAW cambió durante la lectura")
        report.update(run_id=run_id, recorded_at=datetime.now(timezone.utc).isoformat(),
            source_sha256=manifest["sha256"], snapshot_id=manifest["snapshot_id"],
            purpose="DESCRIPTIVE_PROFILING_ONLY", transformed=False, trained=False, final_dataset_created=False)
        write_report(out / (sid + "_profile.json"), report)
        print("Completed " + sid, flush=True)
    return out


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(run(args.run_id))
