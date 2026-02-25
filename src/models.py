"""Data models — Project ➜ Drawing ➜ Weld hierarchy."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# ─── Drawing field definitions ───────────────────────────
# Each tuple: (internal_key, display_header, auto_parsed?)
# NOTE: rev1-rev5 / final_rev 已改為 Revision 歷程清單，
#       不再是固定欄位。
DRAWING_FIELDS: List[tuple] = [
    ("series_no",       "流水號",          False),
    ("dwg_no",          "DWG NO",         False),
    ("sheet_no",        "SH'T NO",        False),
    ("line_no",         "Line_No",        False),
    ("area",            "區域",           False),
    ("delivery_date",   "運交現場日期",    False),
    ("install_billing", "安裝請款",        False),
    # --- auto-parsed from DWG NO ---
    ("dn",              "尺寸",           True),
    ("system",          "系統",           True),
    ("drawing_no",      "編號",           True),
    ("pipe_class",      "級數",           True),
    ("insulation",      "保溫",           True),
    # --- continued manual fields ---
    ("material",        "管線材質",        False),
    ("remark",          "備註",           False),
    ("sys_number",      "系統+編號",      False),
    ("pwht",            "退火",           False),
    ("design_pressure", "設計壓力Kg/cm²", False),
    ("test_pressure",   "測試壓力Kg/cm²", False),
    ("test_fluid",      "試壓流體",        False),
    ("test_pkg_no",     "試壓包編號",      False),
    ("medium",          "介質",           False),
    ("nde_pct",         "NDE (PT/RT)%",   False),
    ("prefab_dwg",      "預製圖",         False),
    ("equipment_no",    "設備編號",        False),
    ("paint_color",     "面漆顏色",        False),
    ("dwg_status",      "圖面狀態",        False),
]

DRAWING_KEYS = [f[0] for f in DRAWING_FIELDS]
DRAWING_HEADERS = [f[1] for f in DRAWING_FIELDS]
AUTO_PARSED_KEYS = [f[0] for f in DRAWING_FIELDS if f[2]]


# ─── Revision (版次歷程) ─────────────────────────────────
REVISION_FIELDS: List[tuple] = [
    ("rev_no",  "版次"),
    ("date",    "日期"),
    ("remark",  "備註"),
]
REVISION_KEYS = [f[0] for f in REVISION_FIELDS]


@dataclass
class Revision:
    rev_no: str = ""
    date: str = ""
    remark: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Revision:
        return cls(**{
            k: str(d.get(k, "")) for k in REVISION_KEYS
        })

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in REVISION_KEYS}


# ─── Weld ────────────────────────────────────────────────
WELD_FIELDS: List[tuple] = [
    ("weld_no",    "焊口編號"),
    ("dn",         "尺寸"),
    ("thk",        "厚度"),
    ("material",   "材質"),
    ("weld_type",  "焊接型式"),
    ("wps_no",     "WPS 編號"),
    ("welder_no",  "焊工編號"),
    ("shop_field", "預製S/現場F"),
    ("remark",     "備註"),
]

WELD_KEYS = [f[0] for f in WELD_FIELDS]
WELD_HEADERS = [f[1] for f in WELD_FIELDS]


@dataclass
class Weld:
    weld_no: str = ""
    dn: str = ""
    thk: str = ""
    material: str = ""
    weld_type: str = ""
    wps_no: str = ""
    welder_no: str = ""
    shop_field: str = "S"
    remark: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Weld:
        return cls(**{
            k: str(d.get(k, "")) for k in WELD_KEYS
        })

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in WELD_KEYS}


@dataclass
class Drawing:
    """One row in the Drawing List; owns Revisions + Welds."""
    # --- identity ---
    series_no: str = ""
    dwg_no: str = ""
    sheet_no: str = "1"
    line_no: str = ""
    # --- management ---
    area: str = ""
    delivery_date: str = ""
    install_billing: str = ""
    # --- auto-parsed ---
    dn: str = ""
    system: str = ""
    drawing_no: str = ""
    pipe_class: str = ""
    insulation: str = ""
    # --- engineering ---
    material: str = ""
    remark: str = ""
    sys_number: str = ""
    pwht: str = ""
    design_pressure: str = ""
    test_pressure: str = ""
    test_fluid: str = ""
    test_pkg_no: str = ""
    medium: str = ""
    nde_pct: str = ""
    prefab_dwg: str = ""
    equipment_no: str = ""
    paint_color: str = ""
    dwg_status: str = "啟用"
    # --- child data ---
    revisions: List[Revision] = field(default_factory=list)
    welds: List[Weld] = field(default_factory=list)

    # ── computed revision fields ─────────────────────────
    @property
    def final_rev(self) -> str:
        """最終版版次 — 取版次歷程最後一筆。"""
        if self.revisions:
            return self.revisions[-1].rev_no
        return ""

    @property
    def final_rev_date(self) -> str:
        """最終版日期 — 取版次歷程最後一筆。"""
        if self.revisions:
            return self.revisions[-1].date
        return ""

    @property
    def rev_count(self) -> int:
        return len(self.revisions)

    # ── serialization ────────────────────────────────────
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Drawing:
        kwargs = {k: str(d.get(k, "")) for k in DRAWING_KEYS}
        kwargs["revisions"] = [
            Revision.from_dict(r)
            for r in d.get("revisions", [])
        ]
        kwargs["welds"] = [
            Weld.from_dict(w)
            for w in d.get("welds", [])
        ]
        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        data = {k: getattr(self, k) for k in DRAWING_KEYS}
        data["revisions"] = [
            r.to_dict() for r in self.revisions
        ]
        data["welds"] = [w.to_dict() for w in self.welds]
        return data

    def get(self, key: str, default: str = "") -> str:
        """支援 computed fields (final_rev, etc.)."""
        if key == "final_rev":
            return self.final_rev
        if key == "final_rev_date":
            return self.final_rev_date
        return getattr(self, key, default)


@dataclass
class Project:
    meta: Dict[str, Any] = field(default_factory=dict)
    drawings: List[Drawing] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Project:
        return cls(
            meta=dict(d.get("meta", {})),
            drawings=[
                Drawing.from_dict(item)
                for item in d.get("drawings", [])
            ],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta,
            "drawings": [
                dw.to_dict() for dw in self.drawings
            ],
        }
