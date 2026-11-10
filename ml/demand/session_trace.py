"""Revisiones de datos de simulación; nunca autorizan operaciones de modelos."""
from copy import deepcopy
from datetime import datetime, timezone
import uuid


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def append_revision(log, kind, pair, month, **details):
    log.append(dict(id="REV-" + uuid.uuid4().hex, sequence=len(log) + 1,
                    timestamp=utc_now(), type=kind, product_id=pair[0] if pair else None,
                    location_id=pair[1] if pair else None, month=month, **deepcopy(details)))
