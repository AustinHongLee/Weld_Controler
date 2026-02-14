"""Piping Material Classification (Spec Rules) engine.

Each *class_code* (e.g. AA2B) maps to a full piping spec:

    ┌─ 基本定義 ───────────────────────────────────┐
    │ description         級數說明                  │
    │ rating              壓力等級 (150#, 300# …)    │
    │ base_material       基本管材 (C.S, SS304 …)   │
    │ pipe_spec           管材規範 (ASTM A106 Gr.B) │
    │ design_temp_min/max 設計溫度範圍              │
    │ design_pressure     設計壓力                  │
    │ corrosion_allowance 腐蝕裕度 (mm)             │
    ├─ 連接方式 ───────────────────────────────────┤
    │ default_weld_type   預設焊接型式 (SMAW/GTAW)  │
    │ joint_type          連接型式 (BW/SW/THD)      │
    │ dn_threshold_bw     BW/SW 分界DN (≥此值用BW)  │
    │ flange_face         法蘭面型式 (RF/RTJ/FF)    │
    │ gasket_type         墊片型式                  │
    │ bolt_material       螺栓材質                  │
    ├─ 檢驗/處理 ──────────────────────────────────┤
    │ pwht_required       是否需退火                │
    │ nde_requirement     NDE 要求 (RT10%, PT100%)  │
    ├─ 管材候選 (沿用) ────────────────────────────┤
    │ material_candidates 可選管材清單              │
    │ default_material    預設管材                  │
    │ thk_candidates_by_dn  DN→壁厚對照           │
    │ thk_rules            DN範圍→壁厚規則         │
    └──────────────────────────────────────────────┘
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


# ─── Spec field metadata ─────────────────────────────────
# (key, display_header, input_type)
#   input_type: "text" | "combo" | "bool"
SPEC_FIELDS: List[tuple] = [
    # 基本定義
    ("description",         "級數說明",         "text"),
    ("rating",              "壓力等級",         "text"),
    ("base_material",       "基本管材",         "text"),
    ("pipe_spec",           "管材規範",         "text"),
    ("design_temp_min",     "最低設計溫度 °C",  "text"),
    ("design_temp_max",     "最高設計溫度 °C",  "text"),
    ("design_pressure",     "設計壓力 Kg/cm²",  "text"),
    ("corrosion_allowance", "腐蝕裕度 mm",      "text"),
    # 連接方式
    ("default_weld_type",   "預設焊接型式",     "text"),
    ("joint_type",          "連接型式",         "text"),
    ("dn_threshold_bw",     "BW/SW 分界 DN",   "text"),
    ("flange_face",         "法蘭面型式",       "text"),
    ("gasket_type",         "墊片型式",         "text"),
    ("bolt_material",       "螺栓材質",         "text"),
    # 檢驗/處理
    ("pwht_required",       "是否需退火",       "bool"),
    ("nde_requirement",     "NDE 要求",         "text"),
    # 材質候選
    ("default_material",    "預設管材",         "text"),
]

SPEC_KEYS = [f[0] for f in SPEC_FIELDS]


# ─── Persistence ─────────────────────────────────────────

def load_spec_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_spec_rules(
    path: str, data: Dict[str, Any]
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ─── Common values (下拉常用值) ──────────────────────────
# Keys in common_values.json map to SPEC_FIELDS keys.

def load_common_values(path: str) -> Dict[str, List[str]]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_common_values(
    path: str, data: Dict[str, List[str]]
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def merge_new_values(
    common: Dict[str, List[str]],
    spec_rules: Dict[str, Any],
) -> bool:
    """Scan all specs for values not yet in *common*.

    Returns True if new values were added.
    """
    changed = False
    for _code, rule in spec_rules.items():
        if not isinstance(rule, dict):
            continue
        for key in common:
            val = rule.get(key, "")
            if isinstance(val, bool):
                continue
            val = str(val).strip()
            if val and val not in common[key]:
                common[key].append(val)
                changed = True
    return changed


# ─── Query helpers ───────────────────────────────────────

def get_rule(
    rules: Dict[str, Any], class_code: str
) -> Dict[str, Any]:
    """Return the spec dict for *class_code*, or {}."""
    return rules.get(class_code, {})


def get_default_material(
    rules: Dict[str, Any], class_code: str
) -> str:
    rule = get_rule(rules, class_code)
    dm = rule.get("default_material", "")
    if dm:
        return str(dm)
    cands = rule.get("material_candidates", [])
    return str(cands[0]) if cands else ""


def get_material_candidates(
    rules: Dict[str, Any], class_code: str
) -> List[str]:
    return list(
        get_rule(rules, class_code)
        .get("material_candidates", [])
    )


def get_default_weld_type(
    rules: Dict[str, Any], class_code: str
) -> str:
    return str(
        get_rule(rules, class_code)
        .get("default_weld_type", "")
    )


def get_joint_type(
    rules: Dict[str, Any], class_code: str,
    dn: str = "",
) -> str:
    """Return joint type, auto-switch BW/SW by DN if
    *dn_threshold_bw* is set.
    """
    rule = get_rule(rules, class_code)
    jt = str(rule.get("joint_type", ""))
    threshold = rule.get("dn_threshold_bw", "")
    if not threshold or not dn:
        return jt
    try:
        dn_int = int(str(dn).strip())
        thr_int = int(str(threshold).strip())
    except ValueError:
        return jt
    return "BW" if dn_int >= thr_int else "SW"


def get_thk_candidates(
    rules: Dict[str, Any], class_code: str, dn: str
) -> List[str]:
    try:
        dn_int = int(str(dn).strip())
    except ValueError:
        return []
    return _thk_for_dn(
        get_rule(rules, class_code), dn_int
    )


def get_thk_candidates_for_dn(
    rules: Dict[str, Any], class_code: str,
    dn_int: int,
) -> List[str]:
    return _thk_for_dn(
        get_rule(rules, class_code), dn_int
    )


def _thk_for_dn(
    rule: Dict[str, Any], dn_int: int
) -> List[str]:
    by_dn = rule.get("thk_candidates_by_dn", {})
    direct = by_dn.get(str(dn_int), [])
    if direct:
        return list(direct)
    for item in rule.get("thk_rules", []):
        if not isinstance(item, dict):
            continue
        try:
            lo = int(item["dn_min"])
            hi = int(item["dn_max"])
        except (KeyError, TypeError, ValueError):
            continue
        if lo <= dn_int <= hi:
            return [
                str(v).strip()
                for v in item.get("thk", [])
                if str(v).strip()
            ]
    return []


# ─── Normalize / migrate ────────────────────────────────

def _empty_spec() -> Dict[str, Any]:
    """Return a blank spec dict with all keys present."""
    return {
        "description": "",
        "rating": "",
        "base_material": "",
        "pipe_spec": "",
        "design_temp_min": "",
        "design_temp_max": "",
        "design_pressure": "",
        "corrosion_allowance": "",
        "default_weld_type": "",
        "joint_type": "",
        "dn_threshold_bw": "",
        "flange_face": "",
        "gasket_type": "",
        "bolt_material": "",
        "pwht_required": False,
        "nde_requirement": "",
        "default_material": "",
        "material_candidates": [],
        "thk_candidates_by_dn": {},
        "thk_rules": [],
        "branch_table": {},
    }


def normalize_rules(
    rules: Dict[str, Any]
) -> Dict[str, Any]:
    """Clean & migrate spec data, ensuring all keys exist."""
    normalized: Dict[str, Any] = {}
    for class_code, rule in rules.items():
        key = str(class_code).strip().upper()
        if not key or not isinstance(rule, dict):
            continue

        spec = _empty_spec()

        # scalar text fields
        for fk in (
            "description", "rating", "base_material",
            "pipe_spec", "design_temp_min",
            "design_temp_max", "design_pressure",
            "corrosion_allowance", "default_weld_type",
            "joint_type", "dn_threshold_bw",
            "flange_face", "gasket_type",
            "bolt_material", "nde_requirement",
            "default_material",
        ):
            val = rule.get(fk, "")
            spec[fk] = str(val).strip() if val else ""

        # bool
        spec["pwht_required"] = bool(
            rule.get("pwht_required", False)
        )

        # material candidates
        spec["material_candidates"] = _dedup_clean(
            rule.get("material_candidates", [])
        )

        # thk by dn — direct mapping
        by_dn_raw = rule.get(
            "thk_candidates_by_dn", {}
        )
        by_dn: Dict[str, List[str]] = {}
        if isinstance(by_dn_raw, dict):
            for dk, tv in by_dn_raw.items():
                d = str(dk).strip()
                if not d.isdigit():
                    continue
                if not isinstance(tv, list):
                    continue
                cleaned = _dedup_clean(tv)
                if cleaned:
                    by_dn[d] = cleaned
        spec["thk_candidates_by_dn"] = by_dn

        # thk rules — range-based
        rules_raw = rule.get("thk_rules", [])
        thk_rules: List[Dict[str, Any]] = []
        if isinstance(rules_raw, list):
            for item in rules_raw:
                if not isinstance(item, dict):
                    continue
                try:
                    lo = int(item["dn_min"])
                    hi = int(item["dn_max"])
                except (KeyError, TypeError, ValueError):
                    continue
                if lo > hi:
                    lo, hi = hi, lo
                thk_rules.append({
                    "dn_min": lo,
                    "dn_max": hi,
                    "thk": _dedup_clean(
                        item.get("thk", [])
                    ),
                })
        thk_rules.sort(
            key=lambda r: (r["dn_min"], r["dn_max"])
        )
        spec["thk_rules"] = thk_rules

        # branch table — {header_dn: {branch_dn: fitting_type}}
        bt_raw = rule.get("branch_table", {})
        bt: Dict[str, Dict[str, str]] = {}
        if isinstance(bt_raw, dict):
            for hdr, cols in bt_raw.items():
                h = str(hdr).strip()
                if not h.isdigit() or not isinstance(cols, dict):
                    continue
                row: Dict[str, str] = {}
                for br, ft in cols.items():
                    b = str(br).strip()
                    ft_s = str(ft).strip().upper()
                    if b.isdigit() and ft_s:
                        row[b] = ft_s
                if row:
                    bt[h] = row
        spec["branch_table"] = bt

        normalized[key] = spec
    return normalized


def _dedup_clean(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    seen: set = set()
    result: List[str] = []
    for v in values:
        t = str(v).strip()
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result
