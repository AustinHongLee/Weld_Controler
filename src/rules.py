from __future__ import annotations

import json
import os
from typing import Any, Dict, List


def load_spec_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_spec_rules(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def get_material_candidates(rules: Dict[str, Any], class_code: str) -> List[str]:
    rule = rules.get(class_code, {})
    return list(rule.get("material_candidates", []))


def get_thk_candidates(rules: Dict[str, Any], class_code: str, dn: str) -> List[str]:
    rule = rules.get(class_code, {})
    by_dn = rule.get("thk_candidates_by_dn", {})
    return list(by_dn.get(dn, []))


def get_default_weld_type(rules: Dict[str, Any], class_code: str) -> str:
    rule = rules.get(class_code, {})
    return str(rule.get("default_weld_type", ""))
