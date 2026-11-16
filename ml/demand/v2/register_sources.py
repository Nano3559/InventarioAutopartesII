"""Registro de archivos RAW locales. No descarga, extrae, transforma ni perfila."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import unicodedata
import re
import zipfile

from .structure import ROOT, ensure_structure, inventory_digest, sha256_file, token, validate_contract, write_new_json


def source_id(name):
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return token(value)


def local_evidence(folder):
    evidence = []
    domain = None
    coverage = None
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.name not in ("DESCRIPTION", "auto.Rd", "car_parts_dataset_with_missing_values.tsf"):
            continue
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            header = handle.read(16384)
        relative = path.relative_to(folder).as_posix()
        if path.name == "DESCRIPTION" and "Package: fable.intermittent" in header:
            domain = "INTERMITTENT_TIME_SERIES_PACKAGE"
            evidence.append(dict(path=relative, scope="PACKAGE_NOT_ALL_DATASETS",
                finding="DESCRIPTION declara fable.intermittent, License: LGPL (>= 3) y URL: https://github.com/StefanoDamato/fable.intermittent. No certifica descarga ni derechos de cada dataset."))
        if path.name == "auto.Rd" and "Automotive Spare Parts Demand Dataset" in header:
            evidence.append(dict(path=relative, scope="DOCUMENTED_SUBDATASET_NOT_DECODED",
                finding="Documenta auto: 3000 series mensuales, enero 2010 a diciembre 2011. No se leyó auto.rda ni se aplicó esta cobertura al paquete completo."))
        if path.suffix == ".tsf" and "January 1998 to March 2002" in header:
            domain = "CAR_PARTS_SALES"
            coverage = dict(start="1998-01", end="2002-03", precision="MONTH", basis="LOCAL_DOCUMENTATION")
            evidence.append(dict(path=relative, scope="HEADER_ONLY_NOT_PROFILED",
                finding="El encabezado declara 2674 series mensuales de ventas de repuestos, enero 1998 a marzo 2002, extraídas de expsmooth. Las filas y la cobertura no se verificaron."))
    return evidence, domain, coverage


def inspect_archives(folder, files):
    result = []
    for item in files:
        name = item["relative_path"]
        path = folder / name
        if path.suffix.lower() in (".zip", ".xlsx"):
            try:
                with zipfile.ZipFile(path) as archive:
                    entries = archive.namelist()
                result.append(dict(path=name, status="CENTRAL_DIRECTORY_ONLY_NO_EXTRACTION", entries=entries))
            except zipfile.BadZipFile:
                result.append(dict(path=name, status="INVALID_ZIP_CONTAINER", entries=None))
        elif path.suffix.lower() in (".7z", ".rar", ".gz", ".bz2", ".xz", ".tar"):
            result.append(dict(path=name, status="NOT_LISTED_NO_EXTRACTOR_USED", entries=None))
        elif path.suffix.lower() == ".rda":
            with path.open("rb") as handle:
                magic = handle.read(6)
            if magic == b"\xfd7zXZ\x00":
                result.append(dict(path=name, status="XZ_COMPRESSED_R_SERIALIZATION_NOT_DECODED", entries=None))
    return result


def register(run_id, root=ROOT):
    root = Path(root).resolve()
    ensure_structure(root)
    raw = root / "sources/external_raw"
    manifests = []
    used_ids = set()
    for folder in sorted(raw.iterdir()):
        if not folder.is_dir():
            raise ValueError("Archivo suelto en RAW: requiere una decisión de agrupación, no se mueve automáticamente")
        paths = sorted(p for p in folder.rglob("*") if p.is_file())
        if not paths:
            continue
        if folder.is_symlink() or any(p.is_symlink() or not p.resolve().is_relative_to(raw.resolve()) for p in paths):
            raise ValueError("No se registran enlaces RAW")
        sid = source_id(folder.name)
        if sid in used_ids:
            raise ValueError("Dos carpetas producen el mismo source_id")
        used_ids.add(sid)
        files = [dict(relative_path=p.relative_to(folder).as_posix(), original_format=p.suffix.lstrip(".").upper() or "NO_EXTENSION",
                      file_size_bytes=p.stat().st_size, sha256=sha256_file(p)) for p in paths]
        digest = inventory_digest(files)
        snapshot = "sha256-" + digest[:24]
        evidence, domain, coverage = local_evidence(folder)
        archive_info = inspect_archives(folder, files)
        value = dict(schema_version="source-manifest-1", source_id=sid, name=folder.name,
            domain=domain, source_url=None, provider=None, obtained_at=None,
            registered_at=datetime.now(timezone.utc).isoformat(), snapshot_id=snapshot,
            license=None, license_url=None, commercial_use_allowed=None,
            original_filename=files[0]["relative_path"] if len(files) == 1 else None,
            original_format=files[0]["original_format"] if len(files) == 1 else "DIRECTORY",
            sha256=files[0]["sha256"] if len(files) == 1 else digest,
            hash_scope="FILE_BYTES" if len(files) == 1 else "FILE_INVENTORY_SHA256",
            inventory_sha256=digest, file_size_bytes=sum(p["file_size_bytes"] for p in files),
            file_count=len(files), files=files, raw_root=folder.relative_to(root).as_posix(),
            temporal_coverage=coverage, geographic_scope=None, currency=None, units=None,
            description="Registro de carpeta local original. El nombre no certifica procedencia o contenido.",
            intended_use="Revisión posterior de procedencia y compatibilidad para V2. No aprobado para profiling, calibración o entrenamiento.",
            limitations=["Fecha de descarga, origen y permisos de datos no certificados.",
                         "Integridad registrada no demuestra completitud respecto al proveedor.",
                         "No se interpretaron filas, no se asociaron productos y no se verificaron unidades o moneda."],
            processing_status="PENDING_SOURCE_REVIEW", completeness="UNKNOWN",
            contains_archives=bool(archive_info), documentation_files=[p["relative_path"] for p in files if any(s in Path(p["relative_path"]).name.lower() for s in ("readme", "license", "licence", "description"))],
            evidence=evidence, visible_structure=[p.relative_to(folder).as_posix() + "/" for p in sorted(folder.rglob("*")) if p.is_dir()],
            archive_inspection=archive_info,
            notes=["null significa desconocido, no permiso denegado ni valor cero.",
                   "registered_at es el registro actual, no la fecha de adquisición.",
                   "sha256 en directorios es hash del inventario canónico. Cada files[].sha256 corresponde a bytes originales.",
                   "Las licencias de software incluidas no se atribuyen automáticamente a los datos."])
        validate_contract(value, "source_manifest")
        target = root / "sources/manifests" / sid / (snapshot + ".json")
        if target.exists():
            previous = json.loads(target.read_text(encoding="utf-8"))
            validate_contract(previous, "source_manifest")
            if previous["files"] != files or previous["raw_root"] != value["raw_root"]:
                raise ValueError("Snapshot existente incompatible")
            value = previous
        else:
            write_new_json(target, value, root=root)
        manifests.append(dict(source_id=sid, manifest=target.relative_to(root).as_posix(),
                              file_count=len(files), file_size_bytes=value["file_size_bytes"], sha256=value["sha256"],
                              hash_scope=value["hash_scope"], snapshot_id=snapshot))
    write_new_json(root / "tmp" / token(run_id) / "source_inventory.json",
                   dict(status="REGISTRATION_ONLY", sources=manifests, profiling_executed=False), root=root)
    return manifests


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(register(args.run_id), ensure_ascii=True, indent=2))
