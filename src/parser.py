"""DWG NO parser — split DWG NO into structured fields."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


def load_parser_profiles(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_parser_profiles(
    path: str, data: Dict[str, Any]
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_system_map(path: str) -> Dict[str, str]:
    """Load system-code → medium/description mapping."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_system_map(
    path: str, data: Dict[str, str]
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def parse_dwg_no(
    dwg_no: str, profile: Dict[str, Any]
) -> Dict[str, str]:
    """Split *dwg_no* by *delimiter* and map tokens.

    Returns e.g. ``{"system": "AC", "dn": "50", ...}``.
    """
    delimiter = profile.get("delimiter", "-")
    mapping: List[str] = profile.get("mapping", [])
    tokens = [t for t in dwg_no.split(delimiter) if t]
    parsed: Dict[str, str] = {}
    for idx, key in enumerate(mapping):
        parsed[key] = tokens[idx] if idx < len(tokens) else ""
    return parsed
