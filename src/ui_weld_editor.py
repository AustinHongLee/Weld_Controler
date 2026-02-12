from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from src import rules


class WeldEditorFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, on_update: Callable[[], None]) -> None:
        super().__init__(parent)
        self.controller = controller
        self.on_update = on_update
        self._suppress_trace = False
        self._selected_index: Optional[int] = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.parsed_label = ctk.CTkLabel(self, text="請選擇 DWG")
        self.parsed_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        self.defaults_frame = ctk.CTkFrame(self)
        self.defaults_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        for index in range(6):
            self.defaults_frame.grid_columnconfigure(index, weight=1)

        self.dn_var = ctk.StringVar()
        self.class_var = ctk.StringVar()
        self.material_var = ctk.StringVar()
        self.thk_var = ctk.StringVar()
        self.weld_type_var = ctk.StringVar()
        self.shop_field_var = ctk.StringVar()

        self._add_defaults_field("DN", self.dn_var, 0)
        self._add_defaults_field("Class", self.class_var, 1)
        self.material_combo = self._add_defaults_combo("Material", self.material_var, 2)
        self.thk_combo = self._add_defaults_combo("Thk", self.thk_var, 3)
        self.weld_type_combo = self._add_defaults_combo("Weld Type", self.weld_type_var, 4)
        self.shop_field_combo = self._add_defaults_combo(
            "Shop/Field", self.shop_field_var, 5, values=["S", "F"]
        )

        self.dn_var.trace_add("write", self._on_defaults_change)
        self.class_var.trace_add("write", self._on_defaults_change)
        self.material_var.trace_add("write", self._on_defaults_change)
        self.thk_var.trace_add("write", self._on_defaults_change)
        self.weld_type_var.trace_add("write", self._on_defaults_change)
        self.shop_field_var.trace_add("write", self._on_defaults_change)

        tools_frame = ctk.CTkFrame(self)
        tools_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=6)
        tools_frame.grid_columnconfigure((1, 4), weight=1)

        ctk.CTkLabel(tools_frame, text="批量生成 N").grid(row=0, column=0, padx=5)
        self.batch_entry = ctk.CTkEntry(tools_frame, width=80)
        self.batch_entry.grid(row=0, column=1, padx=5)
        ctk.CTkButton(tools_frame, text="生成", command=self._batch_generate).grid(
            row=0, column=2, padx=5
        )

        ctk.CTkLabel(tools_frame, text="貼上焊口編號列表").grid(row=0, column=3, padx=5)
        self.paste_entry = ctk.CTkTextbox(tools_frame, height=50)
        self.paste_entry.grid(row=0, column=4, padx=5, sticky="ew")
        ctk.CTkButton(tools_frame, text="貼上建立", command=self._paste_generate).grid(
            row=0, column=5, padx=5
        )

        ctk.CTkButton(
            tools_frame,
            text="一鍵套用 defaults 到全部",
            command=self._apply_defaults,
        ).grid(row=0, column=6, padx=10)

        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=4)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = (
            "weld_no",
            "dn",
            "thk",
            "material",
            "weld_type",
            "shop_field",
            "remark",
        )
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        editor_frame = ctk.CTkFrame(self)
        editor_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=6)
        for index in range(7):
            editor_frame.grid_columnconfigure(index, weight=1)

        self.edit_vars = {
            "weld_no": ctk.StringVar(),
            "dn": ctk.StringVar(),
            "thk": ctk.StringVar(),
            "material": ctk.StringVar(),
            "weld_type": ctk.StringVar(),
            "shop_field": ctk.StringVar(),
            "remark": ctk.StringVar(),
        }

        self._add_editor_field(editor_frame, "焊口", "weld_no", 0)
        self._add_editor_field(editor_frame, "DN", "dn", 1)
        self._add_editor_field(editor_frame, "Thk", "thk", 2)
        self._add_editor_field(editor_frame, "Material", "material", 3)
        self._add_editor_field(editor_frame, "Weld", "weld_type", 4)
        self._add_editor_field(editor_frame, "S/F", "shop_field", 5)
        self._add_editor_field(editor_frame, "備註", "remark", 6)

        ctk.CTkButton(editor_frame, text="更新選取焊口", command=self._update_selected).grid(
            row=2, column=0, columnspan=7, pady=6
        )

    def _add_defaults_field(self, label: str, var: ctk.StringVar, column: int) -> None:
        ctk.CTkLabel(self.defaults_frame, text=label).grid(row=0, column=column, padx=4)
        entry = ctk.CTkEntry(self.defaults_frame, textvariable=var)
        entry.grid(row=1, column=column, padx=4, pady=(0, 6), sticky="ew")

    def _add_defaults_combo(
        self, label: str, var: ctk.StringVar, column: int, values: Optional[List[str]] = None
    ) -> ctk.CTkComboBox:
        ctk.CTkLabel(self.defaults_frame, text=label).grid(row=0, column=column, padx=4)
        combo = ctk.CTkComboBox(self.defaults_frame, values=values or [], variable=var)
        combo.configure(state="normal")
        combo.grid(row=1, column=column, padx=4, pady=(0, 6), sticky="ew")
        return combo

    def _add_editor_field(self, parent, label: str, key: str, column: int) -> None:
        ctk.CTkLabel(parent, text=label).grid(row=0, column=column, padx=4)
        entry = ctk.CTkEntry(parent, textvariable=self.edit_vars[key])
        entry.grid(row=1, column=column, padx=4, pady=(0, 6), sticky="ew")

    def refresh(self) -> None:
        drawing = self.controller.get_current_drawing()
        if not drawing:
            self.parsed_label.configure(text="請選擇 DWG")
            self._set_defaults({})
            self._populate_tree([])
            return

        parsed = drawing.get("parsed", {})
        parsed_text = (
            f"system: {parsed.get('system', '')} | "
            f"dn: {parsed.get('dn', '')} | class: {parsed.get('class', '')} | "
            f"insulation: {parsed.get('insulation', '')} | sheet: {parsed.get('sheet', '')}"
        )
        self.parsed_label.configure(text=parsed_text)
        self._set_defaults(drawing.get("defaults", {}))
        self._populate_tree(drawing.get("welds", []))

    def _set_defaults(self, defaults: Dict[str, str]) -> None:
        self._suppress_trace = True
        self.dn_var.set(defaults.get("dn", ""))
        self.class_var.set(defaults.get("class", ""))
        self.material_var.set(defaults.get("material", ""))
        self.thk_var.set(defaults.get("thk", ""))
        self.weld_type_var.set(defaults.get("weld_type", ""))
        self.shop_field_var.set(defaults.get("shop_field", "S"))
        self._update_candidates()
        self._suppress_trace = False

    def _update_candidates(self) -> None:
        class_code = self.class_var.get()
        dn = self.dn_var.get()
        materials = rules.get_material_candidates(self.controller.spec_rules, class_code)
        thk_candidates = rules.get_thk_candidates(self.controller.spec_rules, class_code, dn)
        default_weld_type = rules.get_default_weld_type(self.controller.spec_rules, class_code)
        self.material_combo.configure(values=materials)
        self.thk_combo.configure(values=thk_candidates)
        self.weld_type_combo.configure(values=[default_weld_type] if default_weld_type else [])
        if default_weld_type and not self.weld_type_var.get():
            self.weld_type_var.set(default_weld_type)

    def _on_defaults_change(self, *_args) -> None:
        if self._suppress_trace:
            return
        self._update_candidates()
        defaults = {
            "dn": self.dn_var.get(),
            "class": self.class_var.get(),
            "material": self.material_var.get(),
            "thk": self.thk_var.get(),
            "weld_type": self.weld_type_var.get(),
            "shop_field": self.shop_field_var.get(),
        }
        self.controller.update_defaults(defaults)

    def _populate_tree(self, welds: List[Dict[str, str]]) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, weld in enumerate(welds):
            values = (
                weld.get("weld_no", ""),
                weld.get("dn", ""),
                weld.get("thk", ""),
                weld.get("material", ""),
                weld.get("weld_type", ""),
                weld.get("shop_field", ""),
                weld.get("remark", ""),
            )
            self.tree.insert("", "end", iid=str(index), values=values)

    def _batch_generate(self) -> None:
        drawing = self.controller.get_current_drawing()
        if not drawing:
            messagebox.showwarning("提示", "請先選擇 DWG")
            return
        try:
            count = int(self.batch_entry.get().strip())
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效的數字")
            return
        if count <= 0:
            messagebox.showerror("錯誤", "數量需大於 0")
            return
        existing_numbers = [
            int(weld.get("weld_no", 0))
            for weld in drawing.get("welds", [])
            if str(weld.get("weld_no", "")).isdigit()
        ]
        start = max(existing_numbers, default=0) + 1
        defaults = drawing.get("defaults", {})
        welds = []
        for offset in range(count):
            welds.append(
                {
                    "weld_no": str(start + offset),
                    "dn": defaults.get("dn", ""),
                    "thk": defaults.get("thk", ""),
                    "material": defaults.get("material", ""),
                    "weld_type": defaults.get("weld_type", ""),
                    "shop_field": defaults.get("shop_field", "S"),
                    "remark": "",
                }
            )
        self.controller.add_welds(welds)
        self.refresh()
        self.on_update()

    def _paste_generate(self) -> None:
        drawing = self.controller.get_current_drawing()
        if not drawing:
            messagebox.showwarning("提示", "請先選擇 DWG")
            return
        content = self.paste_entry.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "請貼上焊口編號")
            return
        weld_numbers = [line.strip() for line in content.splitlines() if line.strip()]
        if not weld_numbers:
            messagebox.showwarning("提示", "沒有有效的焊口編號")
            return
        defaults = drawing.get("defaults", {})
        welds = []
        for weld_no in weld_numbers:
            welds.append(
                {
                    "weld_no": weld_no,
                    "dn": defaults.get("dn", ""),
                    "thk": defaults.get("thk", ""),
                    "material": defaults.get("material", ""),
                    "weld_type": defaults.get("weld_type", ""),
                    "shop_field": defaults.get("shop_field", "S"),
                    "remark": "",
                }
            )
        self.controller.add_welds(welds)
        self.refresh()
        self.on_update()

    def _apply_defaults(self) -> None:
        self.controller.apply_defaults_to_all()
        self.refresh()

    def _on_tree_select(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            self._selected_index = None
            return
        self._selected_index = int(selection[0])
        drawing = self.controller.get_current_drawing()
        if not drawing:
            return
        weld = drawing.get("welds", [])[self._selected_index]
        for key, var in self.edit_vars.items():
            var.set(weld.get(key, ""))

    def _update_selected(self) -> None:
        if self._selected_index is None:
            messagebox.showwarning("提示", "請選擇焊口")
            return
        weld = {key: var.get() for key, var in self.edit_vars.items()}
        self.controller.update_weld(self._selected_index, weld)
        self.refresh()
        self.on_update()
