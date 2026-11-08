"""Contrato de entrada de la interfaz H4. Sin motor, modelos ni escrituras."""
import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
# Los widgets numéricos pasan por JavaScript. Se exige un entero exacto.
MAX_UI_QUANTITY = 2**53 - 1
FEATURE_NAMES = (
    "ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses",
    "mes_sin", "mes_cos",
)
SCENARIOS = (
    "NORMAL", "CRECIMIENTO", "CAÍDA", "PICO MAYORISTA", "STOCKOUT",
    "PRODUCTO NUEVO", "CAMBIO PERSISTENTE", "RECUPERACIÓN",
)


class InputError(ValueError):
    """Error de referencia o edición que puede mostrarse sin datos sensibles."""


def parse_month(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        raise InputError("MES INVÁLIDO: utiliza YYYY-MM.")
    year, month = map(int, value.split("-"))
    if not 1 <= year <= 9999 or not 1 <= month <= 12:
        raise InputError("MES INVÁLIDO: comprueba año y mes.")
    return year, month


def offset_month(value, offset):
    year, month = parse_month(value)
    index = (year - 1) * 12 + month - 1 + offset
    if not 0 <= index < 9999 * 12:
        raise InputError("MES FUERA DEL RANGO TÉCNICO del calendario.")
    year, month = divmod(index, 12)
    return f"{year + 1:04d}-{month + 1:02d}"


def month_label(value):
    year, month = parse_month(value)
    names = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
    return f"{names[month - 1]} {year}"


def validate_quantity(value):
    if type(value) is not int or not 0 <= value <= MAX_UI_QUANTITY:
        raise InputError(
            "CANTIDAD INVÁLIDA: usa unidades enteras entre 0 y "
            f"{MAX_UI_QUANTITY}. El máximo es técnico, no comercial."
        )
    return value


@dataclass(frozen=True)
class Reference:
    products: dict
    stores: dict
    history: dict
    months: tuple

    def recent(self, product_id, location_id, month):
        self.check_ids(product_id, location_id)
        return tuple(
            (offset_month(month, -lag), self.history.get(
                (product_id, location_id, offset_month(month, -lag))
            ))
            for lag in (3, 2, 1)
        )

    def check_ids(self, product_id, location_id):
        if type(product_id) is not int or product_id not in self.products:
            raise InputError("PRODUCTO INVÁLIDO o reservado en el catálogo de referencia.")
        if type(location_id) is not int or location_id not in self.stores:
            raise InputError("TIENDA INVÁLIDA en el catálogo de referencia.")


def load_reference(folder=HERE):
    """Lee únicamente la referencia y el panel 1.1 con sus huellas verificadas."""
    data = folder / "data" / "escenarios_v1_1"
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    catalog_bytes = (folder / "catalog_reference.json").read_bytes()
    base_bytes = (data / "base_mensual.csv").read_bytes()
    if (hashlib.sha256(catalog_bytes).hexdigest() != manifest["catalog_snapshot_hash"]
            or hashlib.sha256(base_bytes).hexdigest()
            != manifest["hashes"]["base_mensual.csv"]):
        raise InputError("REFERENCIA NO VÁLIDA: las huellas del catálogo o del panel no coinciden.")
    catalog = json.loads(catalog_bytes)
    included = set(catalog["included_product_ids"])
    products = {r["id"]: r for r in catalog["products"] if r["id"] in included}
    stores = {r["id"]: r for r in catalog["locations"] if r["type"] == "TIENDA"}
    if not products or not stores or included != set(products):
        raise InputError("REFERENCIA NO VÁLIDA: catálogo incompleto.")
    history = {}
    for row in csv.DictReader(base_bytes.decode("utf-8").splitlines()):
        month = row["mes"]
        parse_month(month)
        key = (int(row["productId"]), int(row["locationId"]), month)
        if key in history or key[0] not in products or key[1] not in stores:
            raise InputError("REFERENCIA NO VÁLIDA: clave duplicada o fuera del catálogo.")
        history[key] = validate_quantity(int(row["ventas_mes"]))
    return Reference(products, stores, history, tuple(sorted({k[2] for k in history})))


def build_inputs(reference, product_id, location_id, month, chronological_values,
                 complete=True, scenario="NORMAL"):
    """Los valores llegan en orden lag3, lag2, lag1. El target no es un argumento."""
    reference.check_ids(product_id, location_id)
    _, month_number = parse_month(month)
    # También comprueba los tres meses anteriores en el calendario soportado.
    recent = reference.recent(product_id, location_id, month)
    if scenario not in SCENARIOS:
        raise InputError("ESCENARIO INVÁLIDO.")
    if scenario == "PRODUCTO NUEVO":
        raise InputError("HISTORIAL INSUFICIENTE: el caso de producto nuevo no admite pronóstico.")
    if complete is not True:
        raise InputError("DATOS INCOMPLETOS: confirma el cierre de los tres meses anteriores.")
    if len(chronological_values) != 3 or any(v is None for v in chronological_values):
        raise InputError("HISTORIAL INSUFICIENTE: se necesitan tres meses consecutivos completos.")
    if any(value is None for _, value in recent):
        raise InputError("HISTORIAL INSUFICIENTE: no existe referencia para esos tres meses.")
    lag3, lag2, lag1 = map(validate_quantity, chronological_values)
    angle = 2 * math.pi * (month_number - 1) / 12
    return dict(zip(FEATURE_NAMES, (
        lag1, lag2, lag3, round(math.sin(angle), 12), round(math.cos(angle), 12),
    )))
