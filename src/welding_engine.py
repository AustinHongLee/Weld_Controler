"""Welding Qualification Engine — WPS / PQR / Welder management.

Inspired by ASME Section IX workflows (P-No grouping, thickness/diameter
qualification envelopes, position qualification).

DISCLAIMER:
    This is a simplified, engineering-practical model.
    It is NOT a replacement for the official ASME Section IX code.
    Verify against your company's rules and the exact code edition in use.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


# ═════════════════════════════════════════════════════════
# Position qualification mapping (seed)
# ═════════════════════════════════════════════════════════

POSITION_QUALIFICATION_MAP: Dict[str, List[str]] = {
    "1G": ["1G"],
    "2G": ["1G", "2G"],
    "5G": ["1G", "2G", "5G"],
    "6G": ["1G", "2G", "5G", "6G"],
    "6GR": ["1G", "2G", "5G", "6G", "6GR"],
}


# ═════════════════════════════════════════════════════════
# Process catalog
# ═════════════════════════════════════════════════════════

PROCESS_CATALOG: Dict[str, str] = {
    "GTAW": "Gas Tungsten Arc Welding",
    "SMAW": "Shielded Metal Arc Welding",
    "GMAW": "Gas Metal Arc Welding",
    "FCAW": "Flux Cored Arc Welding",
    "SAW": "Submerged Arc Welding",
}


# ═════════════════════════════════════════════════════════
# Qualification rules (configurable)
# ═════════════════════════════════════════════════════════

@dataclass
class ThicknessRule:
    """Simplified ASME IX thickness envelope."""
    absolute_min_mm: float = 1.5
    max_multiplier: float = 2.0

    def calc(self, test_thk_mm: float) -> Tuple[float, float]:
        if test_thk_mm <= 0:
            raise ValueError("test_thk_mm must be > 0")
        return (self.absolute_min_mm, test_thk_mm * self.max_multiplier)


@dataclass
class DiameterRule:
    """Simplified ASME IX diameter envelope."""
    large_pipe_threshold_mm: float = 73.0  # ~2.875"

    def calc(self, test_dia_mm: float) -> Tuple[float, Optional[float]]:
        if test_dia_mm <= 0:
            raise ValueError("test_dia_mm must be > 0")
        if test_dia_mm >= self.large_pipe_threshold_mm:
            return (self.large_pipe_threshold_mm, None)  # unlimited
        return (test_dia_mm, test_dia_mm * 2.0)


# ═════════════════════════════════════════════════════════
# Data models
# ═════════════════════════════════════════════════════════

@dataclass
class PQR:
    """Procedure Qualification Record."""
    pqr_no: str = ""
    revision: str = "0"
    created_date: str = ""
    company: str = ""
    project: str = ""
    prepared_by: str = ""
    approved_by: str = ""

    # Base metal
    base_metal_spec: str = ""
    p_no: str = ""
    test_thickness_mm: float = 0.0
    test_diameter_mm: float = 0.0

    # Welding processes (per pass)
    process_root: str = ""
    process_fill: str = ""
    process_cap: str = ""

    # Filler metals
    filler_root: str = ""
    filler_fill: str = ""
    filler_cap: str = ""

    # Position tested
    position_tested: str = ""

    # Test results
    vt: str = "NA"
    rt: str = "NA"
    ut: str = "NA"
    bend: str = "NA"
    tensile: str = "NA"
    impact: str = "NA"

    # Derived qualification envelope
    qualified_thickness_min_mm: float = 0.0
    qualified_thickness_max_mm: float = 0.0
    qualified_diameter_min_mm: float = 0.0
    qualified_diameter_max_mm: float = 0.0  # 0 = unlimited
    qualified_positions: List[str] = field(default_factory=list)

    remarks: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PQR:
        kw: Dict[str, Any] = {}
        for f in cls.__dataclass_fields__:
            if f in d:
                val = d[f]
                ftype = cls.__dataclass_fields__[f].type
                if ftype == "float":
                    val = float(val) if val else 0.0
                elif ftype == "List[str]":
                    val = list(val) if isinstance(val, list) else []
                else:
                    val = str(val) if val is not None else ""
                kw[f] = val
        return cls(**kw)


@dataclass
class WPS:
    """Welding Procedure Specification."""
    wps_no: str = ""
    revision: str = "0"
    created_date: str = ""
    company: str = ""
    project: str = ""
    prepared_by: str = ""
    approved_by: str = ""

    supporting_pqr_no: str = ""

    # Material scope
    p_no: str = ""
    thickness_min_mm: float = 0.0
    thickness_max_mm: float = 0.0
    diameter_min_mm: float = 0.0
    diameter_max_mm: float = 0.0  # 0 = unlimited

    # Processes
    process_root: str = ""
    process_fill: str = ""
    process_cap: str = ""

    # Positions allowed
    positions_allowed: List[str] = field(default_factory=list)

    # Treatment
    preheat_required: bool = False
    pwht_required: bool = False

    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> WPS:
        kw: Dict[str, Any] = {}
        for f in cls.__dataclass_fields__:
            if f in d:
                val = d[f]
                ftype = cls.__dataclass_fields__[f].type
                if ftype == "float":
                    val = float(val) if val else 0.0
                elif ftype == "bool":
                    val = bool(val)
                elif ftype == "List[str]":
                    val = list(val) if isinstance(val, list) else []
                else:
                    val = str(val) if val is not None else ""
                kw[f] = val
        return cls(**kw)


@dataclass
class WelderQualification:
    """Welder / Welding Operator qualification record."""
    welder_no: str = ""
    welder_name: str = ""
    company: str = ""
    id_no: str = ""  # 身份證/護照號碼

    # Qualified scope
    supporting_wps_no: str = ""
    p_no: str = ""
    processes: List[str] = field(default_factory=list)
    positions: List[str] = field(default_factory=list)

    # Thickness range
    thickness_min_mm: float = 0.0
    thickness_max_mm: float = 0.0

    # Dates
    test_date: str = ""
    expiry_date: str = ""

    status: str = "有效"  # 有效 / 過期 / 暫停

    remarks: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WelderQualification":
        kw: Dict[str, Any] = {}
        for f in cls.__dataclass_fields__:
            if f in d:
                val = d[f]
                ftype = cls.__dataclass_fields__[f].type
                if ftype == "float":
                    val = float(val) if val else 0.0
                elif ftype == "List[str]":
                    val = list(val) if isinstance(val, list) else []
                else:
                    val = str(val) if val is not None else ""
                kw[f] = val
        return cls(**kw)


# ═════════════════════════════════════════════════════════
# Engine
# ═════════════════════════════════════════════════════════

class WeldingQualificationEngine:
    """Derive PQR envelopes, validate WPS within PQR."""

    def __init__(
        self,
        p_no_map: Optional[Dict[str, str]] = None,
        position_map: Optional[Dict[str, List[str]]] = None,
        thickness_rule: Optional[ThicknessRule] = None,
        diameter_rule: Optional[DiameterRule] = None,
    ) -> None:
        self.p_no_map = p_no_map or {}
        self.position_map = position_map or POSITION_QUALIFICATION_MAP
        self.thickness_rule = thickness_rule or ThicknessRule()
        self.diameter_rule = diameter_rule or DiameterRule()

    # ── P-No lookup ──────────────────────────────────
    def infer_p_no(self, base_metal_spec: str) -> str:
        spec = base_metal_spec.strip()
        pno = self.p_no_map.get(spec, "")
        if not pno:
            # Try partial match
            for key, val in self.p_no_map.items():
                if key in spec or spec in key:
                    return val
        return pno

    # ── Position derivation ──────────────────────────
    def derive_positions(self, position_tested: str) -> List[str]:
        pos = position_tested.strip().upper()
        return list(self.position_map.get(pos, [pos]))

    # ── Derive PQR envelope ──────────────────────────
    def derive_pqr_envelope(self, pqr: PQR) -> PQR:
        # Auto-fill P-No
        if not pqr.p_no and pqr.base_metal_spec:
            pqr.p_no = self.infer_p_no(pqr.base_metal_spec)

        # Thickness envelope
        if pqr.test_thickness_mm > 0:
            tmin, tmax = self.thickness_rule.calc(pqr.test_thickness_mm)
            pqr.qualified_thickness_min_mm = tmin
            pqr.qualified_thickness_max_mm = tmax

        # Diameter envelope
        if pqr.test_diameter_mm > 0:
            dmin, dmax = self.diameter_rule.calc(pqr.test_diameter_mm)
            pqr.qualified_diameter_min_mm = dmin
            pqr.qualified_diameter_max_mm = dmax or 0.0

        # Position envelope
        if pqr.position_tested:
            pqr.qualified_positions = self.derive_positions(
                pqr.position_tested
            )

        # Default date
        if not pqr.created_date:
            pqr.created_date = date.today().isoformat()

        return pqr

    # ── Validate WPS within PQR ──────────────────────
    def validate_wps_within_pqr(
        self, wps: WPS, pqr: PQR
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        # P-No match
        if wps.p_no and pqr.p_no and wps.p_no != pqr.p_no:
            errors.append(
                f"P-No 不符: WPS={wps.p_no}, PQR={pqr.p_no}"
            )

        # Thickness
        if wps.thickness_min_mm < pqr.qualified_thickness_min_mm:
            errors.append(
                f"WPS 最小厚度 {wps.thickness_min_mm}mm "
                f"< PQR 認證下限 {pqr.qualified_thickness_min_mm}mm"
            )
        if pqr.qualified_thickness_max_mm > 0:
            if wps.thickness_max_mm > pqr.qualified_thickness_max_mm:
                errors.append(
                    f"WPS 最大厚度 {wps.thickness_max_mm}mm "
                    f"> PQR 認證上限 {pqr.qualified_thickness_max_mm}mm"
                )

        # Diameter
        if pqr.qualified_diameter_min_mm > 0:
            if (wps.diameter_min_mm > 0 and
                    wps.diameter_min_mm < pqr.qualified_diameter_min_mm):
                errors.append(
                    f"WPS 最小管徑 {wps.diameter_min_mm}mm "
                    f"< PQR 認證下限 {pqr.qualified_diameter_min_mm}mm"
                )

        # Process match
        for label, wps_p, pqr_p in [
            ("Root", wps.process_root, pqr.process_root),
            ("Fill", wps.process_fill, pqr.process_fill),
            ("Cap", wps.process_cap, pqr.process_cap),
        ]:
            w = wps_p.strip().upper()
            p = pqr_p.strip().upper()
            if w and p and w != p:
                errors.append(
                    f"{label} 焊程不符: WPS={w}, PQR={p}"
                )

        # Positions
        if wps.positions_allowed and pqr.qualified_positions:
            wps_set = {p.upper() for p in wps.positions_allowed}
            pqr_set = {p.upper() for p in pqr.qualified_positions}
            extra = wps_set - pqr_set
            if extra:
                errors.append(
                    f"WPS 位置 {sorted(extra)} "
                    f"不在 PQR 認證範圍 {sorted(pqr_set)} 內"
                )

        return (len(errors) == 0, errors)


# ═════════════════════════════════════════════════════════
# Registry (JSON persistence)
# ═════════════════════════════════════════════════════════

@dataclass
class WeldingRegistry:
    """Stores all WPS, PQR, and Welder records for a project."""
    pqrs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    wpss: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    welders: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pqrs": self.pqrs,
            "wpss": self.wpss,
            "welders": self.welders,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> WeldingRegistry:
        return cls(
            pqrs=d.get("pqrs", {}),
            wpss=d.get("wpss", {}),
            welders=d.get("welders", {}),
        )

    # ── PQR ──────────────────────────────────────────
    def add_pqr(self, pqr: PQR) -> None:
        self.pqrs[pqr.pqr_no] = pqr.to_dict()

    def get_pqr(self, pqr_no: str) -> Optional[PQR]:
        d = self.pqrs.get(pqr_no)
        return PQR.from_dict(d) if d else None

    def delete_pqr(self, pqr_no: str) -> None:
        self.pqrs.pop(pqr_no, None)

    def list_pqr_nos(self) -> List[str]:
        return sorted(self.pqrs.keys())

    # ── WPS ──────────────────────────────────────────
    def add_wps(self, wps: WPS) -> None:
        self.wpss[wps.wps_no] = wps.to_dict()

    def get_wps(self, wps_no: str) -> Optional[WPS]:
        d = self.wpss.get(wps_no)
        return WPS.from_dict(d) if d else None

    def delete_wps(self, wps_no: str) -> None:
        self.wpss.pop(wps_no, None)

    def list_wps_nos(self) -> List[str]:
        return sorted(self.wpss.keys())

    # ── Welder ───────────────────────────────────────
    def add_welder(self, w: WelderQualification) -> None:
        self.welders[w.welder_no] = w.to_dict()

    def get_welder(self, no: str) -> Optional[WelderQualification]:
        d = self.welders.get(no)
        return WelderQualification.from_dict(d) if d else None

    def delete_welder(self, no: str) -> None:
        self.welders.pop(no, None)

    def list_welder_nos(self) -> List[str]:
        return sorted(self.welders.keys())


# ═════════════════════════════════════════════════════════
# File I/O
# ═════════════════════════════════════════════════════════

def load_p_no_map(path: str) -> Dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_p_no_map(path: str, data: Dict[str, str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_welding_registry(path: str) -> WeldingRegistry:
    if not os.path.exists(path):
        return WeldingRegistry()
    with open(path, "r", encoding="utf-8") as fh:
        return WeldingRegistry.from_dict(json.load(fh))


def save_welding_registry(
    path: str, reg: WeldingRegistry
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(reg.to_dict(), fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
