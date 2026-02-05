from __future__ import annotations

import tkinter as tk
from typing import Any, Dict, List, Optional

import customtkinter as ctk

from src import export_excel, parser, rules, storage
from src.ui_dwg_import import DwgImportFrame
from src.ui_export import ExportFrame
from src.ui_parser_profile import ParserProfileFrame
from src.ui_weld_editor import WeldEditorFrame
from src.ui_spec_rules import SpecRulesFrame


class AppController:
    def __init__(self, project_path: str, profile_path: str, rules_path: str) -> None:
        self.project_path = project_path
        self.profile_path = profile_path
        self.rules_path = rules_path
        self.project = storage.ensure_project(project_path)
        self.parser_profiles = parser.load_parser_profiles(profile_path)
        self.spec_rules = rules.load_spec_rules(rules_path)
        self.current_index: Optional[int] = None

    def save(self) -> None:
        storage.save_project(self.project_path, self.project)

    def get_drawings(self) -> List[Dict[str, Any]]:
        return list(self.project.get("drawings", []))

    def get_current_drawing(self) -> Optional[Dict[str, Any]]:
        if self.current_index is None:
            return None
        drawings = self.project.get("drawings", [])
        if 0 <= self.current_index < len(drawings):
            return drawings[self.current_index]
        return None

    def set_current_index(self, index: Optional[int]) -> None:
        self.current_index = index

    def _profile(self) -> Dict[str, Any]:
        profile_name = self.project.get("meta", {}).get("parser_profile", "default")
        return self.parser_profiles.get(profile_name, self.parser_profiles.get("default", {}))

    def parse_dwg(self, dwg_no: str) -> Dict[str, Any]:
        return parser.parse_dwg_no(dwg_no, self._profile())

    def import_drawings(self, rows: List[Dict[str, Any]]) -> None:
        drawings = self.project.setdefault("drawings", [])
        for row in rows:
            serial = int(row["serial"])
            dwg_no = str(row["dwg_no"])
            existing = next((d for d in drawings if int(d.get("serial", 0)) == serial), None)
            if existing:
                existing["dwg_no"] = dwg_no
            else:
                existing = {
                    "serial": serial,
                    "dwg_no": dwg_no,
                    "parsed": {},
                    "defaults": {
                        "dn": "",
                        "class": "",
                        "material": "",
                        "thk": "",
                        "weld_type": "",
                        "shop_field": "S",
                    },
                    "welds": [],
                }
                drawings.append(existing)
            parsed = self.parse_dwg(dwg_no)
            existing["parsed"] = parsed
            existing.setdefault("defaults", {})
            existing["defaults"]["dn"] = parsed.get("dn", "")
            existing["defaults"]["class"] = parsed.get("class", "")
        self.save()

    def reparse_all(self) -> None:
        drawings = self.project.get("drawings", [])
        for drawing in drawings:
            parsed = self.parse_dwg(drawing.get("dwg_no", ""))
            drawing["parsed"] = parsed
            drawing.setdefault("defaults", {})
            drawing["defaults"]["dn"] = parsed.get("dn", "")
            drawing["defaults"]["class"] = parsed.get("class", "")
        self.save()

    def update_defaults(self, defaults: Dict[str, Any]) -> None:
        drawing = self.get_current_drawing()
        if not drawing:
            return
        drawing["defaults"].update(defaults)
        self.save()

    def add_welds(self, welds: List[Dict[str, Any]]) -> None:
        drawing = self.get_current_drawing()
        if not drawing:
            return
        drawing.setdefault("welds", []).extend(welds)
        self.save()

    def update_weld(self, index: int, weld: Dict[str, Any]) -> None:
        drawing = self.get_current_drawing()
        if not drawing:
            return
        welds = drawing.setdefault("welds", [])
        if 0 <= index < len(welds):
            welds[index] = weld
            self.save()

    def apply_defaults_to_all(self) -> None:
        drawing = self.get_current_drawing()
        if not drawing:
            return
        defaults = drawing.get("defaults", {})
        for weld in drawing.get("welds", []):
            for key in ["dn", "thk", "material", "weld_type", "shop_field"]:
                weld[key] = defaults.get(key, "")
        self.save()

    def export_project(self, output_dir: str) -> str:
        return export_excel.export_welds(self.project, output_dir)

    def reload_spec_rules(self) -> None:
        self.spec_rules = rules.load_spec_rules(self.rules_path)

    def save_spec_rules(self, spec_rules_data: Dict[str, Any]) -> None:
        rules.save_spec_rules(self.rules_path, spec_rules_data)
        self.spec_rules = spec_rules_data


class MainApp(ctk.CTk):
    def __init__(self, controller: AppController) -> None:
        super().__init__()
        self.controller = controller
        self.title("焊口主控表建檔工具")
        self.geometry("1200x720")
        self.minsize(1000, 640)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.left_frame, text="DWG 清單").grid(row=0, column=0, pady=(10, 4))

        self.listbox = tk.Listbox(self.left_frame, width=30, height=30)
        self.listbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.path_label = ctk.CTkLabel(
            self.right_frame, text=f"Project: {self.controller.project_path}"
        )
        self.path_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        self.tabview = ctk.CTkTabview(self.right_frame)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        tab_import = self.tabview.add("匯入/管理 DWG")
        tab_welds = self.tabview.add("焊口建立/編輯")
        tab_spec_rules = self.tabview.add("Spec Rules 管理")
        tab_export = self.tabview.add("匯出 Excel")

        self.dwg_import_frame = DwgImportFrame(
            tab_import,
            controller=self.controller,
            on_refresh=self.refresh_drawings,
        )
        self.dwg_import_frame.pack(fill="both", expand=True)

        self.parser_profile_frame = ParserProfileFrame(
            tab_import,
            controller=self.controller,
            on_refresh=self.refresh_drawings,
        )
        self.parser_profile_frame.pack(fill="x", expand=False, pady=(10, 0))

        self.weld_editor_frame = WeldEditorFrame(
            tab_welds,
            controller=self.controller,
            on_update=self.refresh_drawings,
        )
        self.weld_editor_frame.pack(fill="both", expand=True)

        self.spec_rules_frame = SpecRulesFrame(
            tab_spec_rules, controller=self.controller, on_saved=self.weld_editor_frame.refresh
        )
        self.spec_rules_frame.pack(fill="both", expand=True)

        self.export_frame = ExportFrame(tab_export, controller=self.controller)
        self.export_frame.pack(fill="both", expand=True)

        self.refresh_drawings()

    def refresh_drawings(self) -> None:
        self.listbox.delete(0, tk.END)
        for drawing in self.controller.get_drawings():
            serial = drawing.get("serial", "")
            dwg_no = drawing.get("dwg_no", "")
            self.listbox.insert(tk.END, f"{serial}  {dwg_no}")
        self.weld_editor_frame.refresh()

    def _on_select(self, _event: tk.Event) -> None:
        selection = self.listbox.curselection()
        if not selection:
            self.controller.set_current_index(None)
        else:
            self.controller.set_current_index(selection[0])
        self.weld_editor_frame.refresh()


def launch_app(project_path: str, profile_path: str, rules_path: str) -> None:
    controller = AppController(project_path, profile_path, rules_path)
    app = MainApp(controller)
    app.mainloop()
