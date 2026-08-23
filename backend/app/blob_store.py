from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.config import get_settings


def blob_path(job_id: UUID) -> Path:
    root = get_settings().resolved_blob_root
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{job_id}.json"


def write_blob(job_id: UUID, payload: dict[str, Any]) -> str:
    path = blob_path(job_id)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def read_blob(job_id: UUID) -> dict[str, Any] | None:
    path = blob_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def blob_exists(job_id: UUID) -> bool:
    return blob_path(job_id).exists()
