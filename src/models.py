from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Weld:
    weld_no: str
    dn: str = ""
    thk: str = ""
    material: str = ""
    weld_type: str = ""
    shop_field: str = "S"
    remark: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Weld":
        return cls(
            weld_no=str(data.get("weld_no", "")),
            dn=str(data.get("dn", "")),
            thk=str(data.get("thk", "")),
            material=str(data.get("material", "")),
            weld_type=str(data.get("weld_type", "")),
            shop_field=str(data.get("shop_field", "S")),
            remark=str(data.get("remark", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weld_no": self.weld_no,
            "dn": self.dn,
            "thk": self.thk,
            "material": self.material,
            "weld_type": self.weld_type,
            "shop_field": self.shop_field,
            "remark": self.remark,
        }


@dataclass
class Drawing:
    serial: int
    dwg_no: str
    parsed: Dict[str, Any] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)
    welds: List[Weld] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Drawing":
        return cls(
            serial=int(data.get("serial", 0)),
            dwg_no=str(data.get("dwg_no", "")),
            parsed=dict(data.get("parsed", {})),
            defaults=dict(data.get("defaults", {})),
            welds=[Weld.from_dict(item) for item in data.get("welds", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "serial": self.serial,
            "dwg_no": self.dwg_no,
            "parsed": self.parsed,
            "defaults": self.defaults,
            "welds": [weld.to_dict() for weld in self.welds],
        }


@dataclass
class Project:
    meta: Dict[str, Any]
    drawings: List[Drawing] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        return cls(
            meta=dict(data.get("meta", {})),
            drawings=[Drawing.from_dict(item) for item in data.get("drawings", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meta": self.meta,
            "drawings": [drawing.to_dict() for drawing in self.drawings],
        }
