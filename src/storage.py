from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_empty_project() -> Dict[str, Any]:
    now = _now_iso()
    return {
        "meta": {
            "project_name": "",
            "created_at": now,
            "updated_at": now,
            "parser_profile": "default",
        },
        "drawings": [],
    }


def ensure_project(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = make_empty_project()
        save_project(path, data)
        return data
    return load_project(path)


def load_project(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return ensure_project(path)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_project(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data.setdefault("meta", {})
    data["meta"]["updated_at"] = _now_iso()
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
