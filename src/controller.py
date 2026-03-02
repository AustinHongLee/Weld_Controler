"""Application controller — business logic, no UI dependency."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src import parser, rules, storage, welding_engine
from src.models import (
    AUTO_PARSED_KEYS,
    Drawing,
    Project,
    Revision,
    Weld,
)


class AppController:
    """Shared controller for the whole application.

    Hierarchy: Project ➜ Drawing List ➜ Weld Control
    """

    def __init__(
        self,
        project_path: str,
        profile_path: str,
        rules_path: str,
    ) -> None:
        self.project_path = project_path
        self.profile_path = profile_path
        self.rules_path = rules_path

        # Derive system_map path from profile_path dir
        import os
        cfg_dir = os.path.dirname(profile_path)
        self.system_map_path = os.path.join(
            cfg_dir, "system_map.json"
        )
        self.common_values_path = os.path.join(
            cfg_dir, "common_values.json"
        )
        self.p_no_map_path = os.path.join(
            cfg_dir, "p_no_map.json"
        )
        self.welding_reg_path = os.path.join(
            cfg_dir, "welding_registry.json"
        )

        raw = storage.ensure_project(project_path)
        self.project = Project.from_dict(raw)
        self.parser_profiles = parser.load_parser_profiles(
            profile_path
        )
        self.spec_rules = rules.load_spec_rules(rules_path)
        self.system_map = parser.load_system_map(
            self.system_map_path
        )
        self.common_values = rules.load_common_values(
            self.common_values_path
        )

        # Welding qualification
        self.p_no_map = welding_engine.load_p_no_map(
            self.p_no_map_path
        )
        self.welding_registry = welding_engine.load_welding_registry(
            self.welding_reg_path
        )
        self.weld_engine = welding_engine.WeldingQualificationEngine(
            p_no_map=self.p_no_map,
        )

        # Currently-selected drawing index (for weld editing)
        self.current_drawing_idx: Optional[int] = None

    # ── persistence ──────────────────────────────────────
    def save(self) -> None:
        storage.save_project(
            self.project_path, self.project.to_dict()
        )

    # ── parser profile ───────────────────────────────────
    def _profile(self) -> Dict[str, Any]:
        name = self.project.meta.get("parser_profile", "default")
        return self.parser_profiles.get(
            name, self.parser_profiles.get("default", {})
        )

    def parse_dwg(self, dwg_no: str) -> Dict[str, str]:
        return parser.parse_dwg_no(dwg_no, self._profile())

    # ═════════════════════════════════════════════════════
    # Drawing List (母表)
    # ═════════════════════════════════════════════════════
    def get_drawings(self) -> List[Drawing]:
        return self.project.drawings

    def get_drawing(self, idx: int) -> Optional[Drawing]:
        if 0 <= idx < len(self.project.drawings):
            return self.project.drawings[idx]
        return None

    def import_drawings(
        self, rows: List[Dict[str, str]]
    ) -> int:
        """Import rows (series_no + dwg_no minimum).

        Auto-parses DWG NO and fills parsed fields.
        Returns number of rows imported.
        """
        count = 0
        for row in rows:
            series_no = str(row.get("series_no", "")).strip()
            dwg_no = str(row.get("dwg_no", "")).strip()
            if not dwg_no:
                continue

            # Check if drawing with same series_no exists
            existing = next(
                (d for d in self.project.drawings
                 if d.series_no == series_no),
                None,
            )
            if existing:
                existing.dwg_no = dwg_no
                self._apply_parsed(existing)
            else:
                dw = Drawing(series_no=series_no, dwg_no=dwg_no)
                self._apply_parsed(dw)
                self.project.drawings.append(dw)
            count += 1

        self.save()
        return count

    def _apply_parsed(self, dw: Drawing) -> None:
        """Run DWG NO parser and write results into the
        Drawing's auto-parsed fields.

        Also auto-fills derived fields:
        - sys_number  ← system + drawing_no
        - material    ← spec_rules[pipe_class].default_material
        - medium      ← system_map[system]
        """
        parsed = self.parse_dwg(dw.dwg_no)
        # Backwards-compat: old profiles may use "class"/"sheet"
        if "class" in parsed and "pipe_class" not in parsed:
            parsed["pipe_class"] = parsed.pop("class")
        if "sheet" in parsed and "sheet_no" not in parsed:
            parsed["sheet_no"] = parsed.pop("sheet")
        for key in AUTO_PARSED_KEYS:
            if key in parsed:
                setattr(dw, key, parsed[key])
        # Handle sheet_no that might still come separately
        if "sheet_no" in parsed and not dw.sheet_no:
            dw.sheet_no = parsed["sheet_no"]
        # Default sheet_no to "1" if still empty
        if not dw.sheet_no:
            dw.sheet_no = "1"
        # Compose sys_number automatically
        if dw.system and dw.drawing_no:
            dw.sys_number = f"{dw.system}-{dw.drawing_no}"
        # Auto-fill material from class → spec_rules
        if dw.pipe_class and not dw.material:
            mat = rules.get_default_material(
                self.spec_rules, dw.pipe_class
            )
            if mat:
                dw.material = mat
        # Auto-fill medium from system → system_map
        if dw.system and not dw.medium:
            med = self.system_map.get(
                dw.system.upper(), ""
            )
            if med:
                dw.medium = med
        # Auto-fill from spec: pwht, design_pressure, nde
        if dw.pipe_class:
            spec = rules.get_rule(
                self.spec_rules, dw.pipe_class
            )
            if spec:
                if not dw.pwht:
                    pw = spec.get("pwht_required", False)
                    dw.pwht = "Y" if pw else "N"
                if not dw.design_pressure:
                    dp = spec.get("design_pressure", "")
                    if dp:
                        dw.design_pressure = str(dp)
                if not dw.nde_pct:
                    nde = spec.get(
                        "nde_requirement", ""
                    )
                    if nde:
                        dw.nde_pct = nde

    def update_drawing(
        self, idx: int, data: Dict[str, str]
    ) -> None:
        """Update a single drawing's fields (manual edit)."""
        dw = self.get_drawing(idx)
        if not dw:
            return
        old_dwg_no = dw.dwg_no
        for key, val in data.items():
            if key != "welds" and hasattr(dw, key):
                setattr(dw, key, val)
        # Re-parse if DWG NO changed
        if dw.dwg_no != old_dwg_no:
            self._apply_parsed(dw)
        self.save()

    def add_empty_drawing(self) -> Drawing:
        """Add an empty Drawing and return it."""
        dw = Drawing()
        self.project.drawings.append(dw)
        self.save()
        return dw

    def delete_drawings(self, indices: List[int]) -> None:
        """Delete drawings at the given indices."""
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self.project.drawings):
                self.project.drawings.pop(idx)
        self.current_drawing_idx = None
        self.save()

    def reparse_all(self) -> None:
        for dw in self.project.drawings:
            self._apply_parsed(dw)
        self.save()

    # ═════════════════════════════════════════════════════
    # Revision (版次歷程)
    # ═════════════════════════════════════════════════════
    def add_revision(
        self, drawing_idx: int, rev_no: str,
        date: str = "", remark: str = "",
    ) -> None:
        dw = self.get_drawing(drawing_idx)
        if not dw:
            return
        dw.revisions.append(
            Revision(rev_no=rev_no, date=date, remark=remark)
        )
        self.save()

    def delete_revision(
        self, drawing_idx: int, rev_idx: int,
    ) -> None:
        dw = self.get_drawing(drawing_idx)
        if not dw:
            return
        if 0 <= rev_idx < len(dw.revisions):
            dw.revisions.pop(rev_idx)
            self.save()

    # ═════════════════════════════════════════════════════
    # Weld Control (子表)
    # ═════════════════════════════════════════════════════
    def set_current_drawing(self, idx: Optional[int]) -> None:
        self.current_drawing_idx = idx

    def current_drawing(self) -> Optional[Drawing]:
        if self.current_drawing_idx is None:
            return None
        return self.get_drawing(self.current_drawing_idx)

    def get_weld_defaults(self) -> Dict[str, str]:
        """Derive weld defaults from the current drawing."""
        dw = self.current_drawing()
        if not dw:
            return {}
        class_code = dw.pipe_class
        return {
            "dn": dw.dn,
            "material": dw.material,
            "thk": "",
            "weld_type": rules.get_joint_type(
                self.spec_rules, class_code, dw.dn
            ),
            "shop_field": "S",
        }

    def add_welds(self, welds: List[Dict[str, Any]]) -> None:
        dw = self.current_drawing()
        if not dw:
            return
        for w in welds:
            dw.welds.append(Weld.from_dict(w))
        self.save()

    def update_weld(
        self, weld_idx: int, data: Dict[str, str]
    ) -> None:
        dw = self.current_drawing()
        if not dw:
            return
        if 0 <= weld_idx < len(dw.welds):
            for k, v in data.items():
                if hasattr(dw.welds[weld_idx], k):
                    setattr(dw.welds[weld_idx], k, v)
            self.save()

    def delete_welds(self, indices: List[int]) -> None:
        dw = self.current_drawing()
        if not dw:
            return
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(dw.welds):
                dw.welds.pop(idx)
        self.save()

    def apply_defaults_to_all_welds(self) -> None:
        dw = self.current_drawing()
        if not dw:
            return
        defaults = self.get_weld_defaults()
        for weld in dw.welds:
            for k in ("dn", "material", "weld_type", "shop_field"):
                if defaults.get(k):
                    setattr(weld, k, defaults[k])
        self.save()

    # ═════════════════════════════════════════════════════
    # Parser Profile 管理
    # ═════════════════════════════════════════════════════
    def save_parser_profiles(
        self, data: Dict[str, Any]
    ) -> None:
        parser.save_parser_profiles(
            self.profile_path, data
        )
        self.parser_profiles = data

    def save_system_map(
        self, data: Dict[str, str]
    ) -> None:
        parser.save_system_map(
            self.system_map_path, data
        )
        self.system_map = data

    # ═════════════════════════════════════════════════════
    # Spec Rules
    # ═════════════════════════════════════════════════════
    def reload_spec_rules(self) -> None:
        self.spec_rules = rules.load_spec_rules(self.rules_path)

    def save_spec_rules(
        self, data: Dict[str, Any]
    ) -> None:
        rules.save_spec_rules(self.rules_path, data)
        self.spec_rules = data
        # Auto-merge new values into common_values
        if rules.merge_new_values(
            self.common_values, data
        ):
            rules.save_common_values(
                self.common_values_path,
                self.common_values,
            )

    # ═════════════════════════════════════════════════════
    # Export
    # ═════════════════════════════════════════════════════
    def export_project(self, output_dir: str) -> str:
        from src import export_excel
        return export_excel.export_project(
            self.project, output_dir
        )

    # ═════════════════════════════════════════════════
    # Welding Qualification (WPS / PQR / Welder)
    # ═════════════════════════════════════════════════
    def save_welding_registry(self) -> None:
        welding_engine.save_welding_registry(
            self.welding_reg_path, self.welding_registry
        )

    def save_p_no_map(self, data: Dict[str, str]) -> None:
        welding_engine.save_p_no_map(
            self.p_no_map_path, data
        )
        self.p_no_map = data
        self.weld_engine.p_no_map = data

    def get_wps_list(self) -> List[str]:
        return self.welding_registry.list_wps_nos()

    def get_welder_list(self) -> List[str]:
        return self.welding_registry.list_welder_nos()
