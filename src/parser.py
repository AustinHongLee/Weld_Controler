from __future__ import annotations

import json
from typing import Any, Dict, List


def load_parser_profiles(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_dwg_no(dwg_no: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    delimiter = profile.get("delimiter", "-")
    mapping: List[str] = profile.get("mapping", [])
    tokens = [token for token in dwg_no.split(delimiter) if token != ""]
    parsed: Dict[str, Any] = {"raw_tokens": tokens}
    for index, field in enumerate(mapping):
        parsed[field] = tokens[index] if index < len(tokens) else ""
    return parsed
