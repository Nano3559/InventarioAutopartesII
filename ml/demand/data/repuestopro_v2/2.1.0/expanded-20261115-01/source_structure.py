"""Rutas aisladas, hashes de bytes y escrituras nuevas, sin dependencias V1."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    "sources", "sources/external_raw", "sources/external_curated",
    "sources/manifests", "data/repuestopro_v2", "reports/v2", "models/v2",
    "v2", "tmp",
)
STATES = ("RAW_REGISTERED", "PENDING_SOURCE_REVIEW", "APPROVED_FOR_PROFILING", "CURATED", "REJECTED")


def sha256_file(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def inventory_digest(files):
    """Hash del inventario, distinto del hash de bytes de cada archivo."""
    rows = [{key: item[key] for key in ("relative_path", "sha256", "file_size_bytes")}
            for item in sorted(files, key=lambda row: row["relative_path"])]
    return hashlib.sha256(json.dumps(rows, ensure_ascii=True, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", value) or value in (".", ".."):
        raise ValueError("Identificador de ruta inválido")
    return value


def new_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]


def ensure_structure(root=ROOT):
    root = Path(root).resolve()
    created = []
    for name in DIRECTORIES:
        path = root / name
        if not path.resolve().is_relative_to(root):
            raise ValueError("La ruta sale del módulo")
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(name)
        elif not path.is_dir():
            raise ValueError("Se esperaba una carpeta")
    return created


def new_build_directory(dataset_version, build_id, root=ROOT):
    """Reserva explícita futura. No crea CSV ni publica un dataset."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", dataset_version):
        raise ValueError("Versión inválida")
    base = Path(root).resolve() / "data/repuestopro_v2"
    if base.resolve() != base:
        raise ValueError("No se admiten enlaces en el destino del build")
    target = base / dataset_version / token(build_id)
    if not target.resolve().is_relative_to(base.resolve()):
        raise ValueError("Ruta inválida")
    target.mkdir(parents=True, exist_ok=False)
    return target


def write_new_json(path, value, *, root=ROOT):
    """Únicamente manifests V2 o temporales. Nunca RAW, reportes/modelos V1."""
    root = Path(root).resolve()
    path = Path(path).resolve()
    allowed = [root / "sources/manifests", root / "tmp"]
    if not any(path.is_relative_to(base) for base in allowed):
        raise ValueError("Destino no autorizado para registro")
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)


def strict_format_checker():
    """Date-time local sin depender de extras opcionales de jsonschema."""
    from jsonschema import FormatChecker
    checker = FormatChecker()

    @checker.checks("date-time")
    def date_time(value):
        if not isinstance(value, str):
            return True
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value):
            return False
        try:
            parsed = datetime.fromisoformat(value.upper().replace("Z", "+00:00"))
            return parsed.utcoffset() is not None
        except ValueError:
            return False

    return checker


def validate_contract(value, contract_name):
    """Valida contratos locales. No resuelve referencias por Internet."""
    from jsonschema import Draft202012Validator
    if contract_name not in ("source_manifest", "dataset_schema", "curated_manifest"):
        raise ValueError("Contrato desconocido")
    schema = json.loads((Path(__file__).parent / "contracts" / (contract_name + ".schema.json")).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=strict_format_checker()).validate(value)
    if contract_name == "source_manifest":
        raw_root = value["raw_root"]
        if ".." in raw_root.split("/") or "\\" in raw_root or ":" in raw_root:
            raise ValueError("Ubicación RAW inválida")
        files = value["files"]
        if len({row["relative_path"] for row in files}) != len(files):
            raise ValueError("Archivo duplicado en inventario")
        for row in files:
            path = row["relative_path"]
            if path.startswith(("/", "\\")) or "\\" in path or ":" in path or ".." in path.split("/"):
                raise ValueError("Ruta RAW no relativa")
        if value["file_count"] != len(files) or value["file_size_bytes"] != sum(row["file_size_bytes"] for row in files):
            raise ValueError("Totales incorrectos")
        if value["inventory_sha256"] != inventory_digest(files):
            raise ValueError("Inventario alterado")
        if len(files) == 1:
            if value["hash_scope"] != "FILE_BYTES" or value["sha256"] != files[0]["sha256"] or value["original_filename"] != files[0]["relative_path"]:
                raise ValueError("Identidad de archivo incorrecta")
        elif value["hash_scope"] != "FILE_INVENTORY_SHA256" or value["sha256"] != value["inventory_sha256"] or value["original_filename"] is not None:
            raise ValueError("Identidad de paquete incorrecta")
        if value["processing_status"] == "APPROVED_FOR_PROFILING":
            if (value.get("license_status") != "VERIFIED"
                    or value.get("academic_use_status") != "VERIFIED"
                    or value.get("profiling_decision") != "APPROVED_ACADEMIC_ONLY"
                    or not value.get("evidence_urls") or not value.get("verified_at")):
                raise ValueError("Aprobación sin revisión suficiente de procedencia y uso académico")
        elif value["processing_status"] not in ("RAW_REGISTERED", "PENDING_SOURCE_REVIEW", "REJECTED"):
            raise ValueError("Esta fase no admite declarar fuentes procesadas")
    elif contract_name == "dataset_schema":
        names = [item["name"] for item in value["columns"]]
        if len(names) != len(set(names)):
            raise ValueError("Columna duplicada")
        if "design" in value:
            design = value["design"]
            columns = {item["name"]: item for item in value["columns"]}
            expected_key = ["productId", "locationId", "mes_objetivo"]
            if design["primary_key"] != expected_key or any(columns.get(n, {}).get("role") != "IDENTIFIER" for n in expected_key):
                raise ValueError("Clave de producto, tienda y mes inválida")
            targets = [c for c in columns.values() if c["role"] == "TARGET"]
            if len(targets) != 1 or targets[0]["name"] != design["target"] or design["target"] != "target_ventas_mes":
                raise ValueError("Target V2 inválido")
            if targets[0].get("availability_class") != "POST_TARGET_CLOSE":
                raise ValueError("El target solo está disponible después del mes objetivo")
            features = {c["name"] for c in columns.values() if c["role"] == "FEATURE"}
            if set(design["feature_sets"].get("v2_full", [])) != features:
                raise ValueError("Feature set completo no coincide con el diccionario")
            forbidden = {"productId", "locationId", "mes_objetivo", "target_ventas_mes", "feature_cutoff_at", "history_snapshot_id", "quality_status", "scenario_id", "scenario_instance_id", "event_at", "available_at", "parameters_json", "latent_demand_units", "split", "seed"}
            if features & forbidden:
                raise ValueError("Identificadores, auditoría o target usados como features")
            for members in design["feature_sets"].values():
                if not set(members).issubset(features):
                    raise ValueError("Feature set con columnas desconocidas o no predictivas")
            for c in columns.values():
                if not c.get("missing_policy") or not c.get("source_kind"):
                    raise ValueError("Columna V2 sin origen o tratamiento de faltantes")
                if c["role"] == "FEATURE" and c.get("availability_class") != "PRE_CUTOFF":
                    raise ValueError("Feature con disponibilidad posterior al corte")
                if c["role"] == "FEATURE" and c["source_kind"] not in ("SIMULATED", "CALENDAR", "FROZEN_REFERENCE_IN_SYNTHETIC_WORLD"):
                    raise ValueError("El diseño inicial no admite filas externas como features propias")
                if c["role"] == "FEATURE" and c["name"].startswith("precio_") and c["unit"] != "Bs/unidad":
                    raise ValueError("El precio del diseño V2 debe expresarse en Bs por unidad")
                if c["name"] == "tipo_cambio_bs_usd_conocido" and c["unit"] != "Bs/USD":
                    raise ValueError("La cotización V2 debe expresarse en Bs/USD")
            if "categoryId" in columns and columns["categoryId"].get("encoding") != "CATEGORICAL":
                raise ValueError("categoryId debe codificarse como categoría")
            if design["reference_use"].get("external_row_mapping_allowed") is not False:
                raise ValueError("No se permite trasladar IDs o ventas externas a RepuestoPro")
            if design["row_policy"].get("missing_month_is_zero") is not False or design["row_policy"].get("review_and_invalid_rows_in_training") is not False:
                raise ValueError("Política de filas desconocidas o inválidas insegura")
            if design["split_design"].get("random_row_split_allowed") is not False or design["split_design"].get("unit") != "COMPLETE_MONTH_BLOCKS":
                raise ValueError("La división debe respetar meses completos")
            for table in design["supporting_tables"].values():
                table_names = [c["name"] for c in table["columns"]]
                if len(table_names) != len(set(table_names)):
                    raise ValueError("Columnas duplicadas en tabla auxiliar")
