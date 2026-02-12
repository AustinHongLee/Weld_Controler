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
    try:
        dn_int = int(str(dn).strip())
    except ValueError:
        return []
    return get_thk_candidates_for_dn(rules, class_code, dn_int)


def get_default_weld_type(rules: Dict[str, Any], class_code: str) -> str:
    rule = rules.get(class_code, {})
    return str(rule.get("default_weld_type", ""))


def get_thk_candidates_for_dn(rules: Dict[str, Any], class_code: str, dn_int: int) -> List[str]:
    rule = rules.get(class_code, {})
    by_dn = rule.get("thk_candidates_by_dn", {})
    direct = by_dn.get(str(dn_int), [])
    if direct:
        return list(direct)

    for item in rule.get("thk_rules", []):
        if not isinstance(item, dict):
            continue
        try:
            dn_min = int(item.get("dn_min"))
            dn_max = int(item.get("dn_max"))
        except (TypeError, ValueError):
            continue
        if dn_min <= dn_int <= dn_max:
            return [str(v).strip() for v in item.get("thk", []) if str(v).strip()]
    return []


def normalize_rules(rules: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for class_code, rule in rules.items():
        key = str(class_code).strip().upper()
        if not key:
            continue

        mats_raw = rule.get("material_candidates", []) if isinstance(rule, dict) else []
        mats = _dedup_clean_list(mats_raw)

        by_dn_raw = rule.get("thk_candidates_by_dn", {}) if isinstance(rule, dict) else {}
        by_dn: Dict[str, List[str]] = {}
        if isinstance(by_dn_raw, dict):
            for dn_key, thk_values in by_dn_raw.items():
                dn = str(dn_key).strip()
                if not dn.isdigit() or not isinstance(thk_values, list):
                    continue
                cleaned = _dedup_clean_list(thk_values)
                if cleaned:
                    by_dn[dn] = cleaned

        rules_raw = rule.get("thk_rules", []) if isinstance(rule, dict) else []
        thk_rules: List[Dict[str, Any]] = []
        if isinstance(rules_raw, list):
            for item in rules_raw:
                if not isinstance(item, dict):
                    continue
                try:
                    dn_min = int(item.get("dn_min"))
                    dn_max = int(item.get("dn_max"))
                except (TypeError, ValueError):
                    continue
                if dn_min > dn_max:
                    dn_min, dn_max = dn_max, dn_min
                thk_values = _dedup_clean_list(item.get("thk", []))
                thk_rules.append({"dn_min": dn_min, "dn_max": dn_max, "thk": thk_values})
        thk_rules.sort(key=lambda row: (row["dn_min"], row["dn_max"]))

        normalized[key] = {
            "material_candidates": mats,
            "thk_candidates_by_dn": by_dn,
            "thk_rules": thk_rules,
            "default_weld_type": str(rule.get("default_weld_type", "")).strip()
            if isinstance(rule, dict)
            else "",
        }
    return normalized


def _dedup_clean_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    result: List[str] = []
    seen = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result
