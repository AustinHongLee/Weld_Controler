from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Dict, List

import customtkinter as ctk


class SpecRulesFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, on_saved: Callable[[], None]) -> None:
        super().__init__(parent)
        self.controller = controller
        self.on_saved = on_saved

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.class_list = tk.Listbox(self, width=24)
        self.class_list.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=10, pady=10)
        self.class_list.bind("<<ListboxSelect>>", self._on_select_class)

        right = ctk.CTkFrame(self)
        right.grid(row=0, column=1, rowspan=4, sticky="nsew", padx=(0, 10), pady=10)
        right.grid_columnconfigure(1, weight=1)
        right.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(right, text="Class Code").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.class_entry = ctk.CTkEntry(right)
        self.class_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=(8, 2))

        ctk.CTkLabel(right, text="Material Candidates (逗號分隔)").grid(
            row=1, column=0, sticky="w", padx=8, pady=2
        )
        self.material_entry = ctk.CTkEntry(right)
        self.material_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=2)

        ctk.CTkLabel(right, text="Default Weld Type").grid(row=2, column=0, sticky="w", padx=8, pady=2)
        self.weld_type_entry = ctk.CTkEntry(right)
        self.weld_type_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=2)

        ctk.CTkLabel(right, text="thk_candidates_by_dn").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )

        table_wrap = ctk.CTkFrame(right)
        table_wrap.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        self.thk_tree = ttk.Treeview(table_wrap, columns=("dn", "thk_list"), show="headings", height=8)
        self.thk_tree.heading("dn", text="DN")
        self.thk_tree.heading("thk_list", text="THK Candidates (逗號分隔)")
        self.thk_tree.column("dn", width=90, anchor="center")
        self.thk_tree.column("thk_list", width=260, anchor="w")
        self.thk_tree.grid(row=0, column=0, sticky="nsew")

        thk_editor = ctk.CTkFrame(right)
        thk_editor.grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        thk_editor.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(thk_editor, text="DN").grid(row=0, column=0, padx=4, pady=4)
        self.dn_entry = ctk.CTkEntry(thk_editor, width=80)
        self.dn_entry.grid(row=0, column=1, padx=4, pady=4, sticky="w")

        ctk.CTkLabel(thk_editor, text="THK 列表").grid(row=0, column=2, padx=4, pady=4)
        self.thk_entry = ctk.CTkEntry(thk_editor)
        self.thk_entry.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        ctk.CTkButton(thk_editor, text="新增/更新DN規則", command=self._upsert_dn_rule).grid(
            row=0, column=4, padx=4, pady=4
        )
        ctk.CTkButton(thk_editor, text="刪除選取DN", command=self._delete_dn_rule).grid(
            row=0, column=5, padx=4, pady=4
        )

        btn_row = ctk.CTkFrame(self)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="新增 Class", command=self._new_class).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="刪除 Class", command=self._delete_class).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="儲存到 spec_rules.json", command=self._save).pack(
            side="right", padx=4
        )

        self._working_rules: Dict[str, Dict] = {}
        self.refresh_from_file()

    def refresh_from_file(self) -> None:
        self.controller.reload_spec_rules()
        self._working_rules = {k: dict(v) for k, v in self.controller.spec_rules.items()}
        self._refresh_class_list()
        self._clear_form()

    def _refresh_class_list(self) -> None:
        self.class_list.delete(0, tk.END)
        for class_code in sorted(self._working_rules.keys()):
            self.class_list.insert(tk.END, class_code)

    def _clear_form(self) -> None:
        self.class_entry.delete(0, tk.END)
        self.material_entry.delete(0, tk.END)
        self.weld_type_entry.delete(0, tk.END)
        self.dn_entry.delete(0, tk.END)
        self.thk_entry.delete(0, tk.END)
        for item in self.thk_tree.get_children():
            self.thk_tree.delete(item)

    def _current_selected_key(self) -> str:
        sel = self.class_list.curselection()
        if not sel:
            return ""
        return self.class_list.get(sel[0])

    def _on_select_class(self, _event: tk.Event) -> None:
        class_code = self._current_selected_key()
        if not class_code:
            return
        self._load_class_to_form(class_code)

    def _load_class_to_form(self, class_code: str) -> None:
        rule = self._working_rules.get(class_code, {})

        self.class_entry.delete(0, tk.END)
        self.class_entry.insert(0, class_code)

        materials = rule.get("material_candidates", [])
        self.material_entry.delete(0, tk.END)
        self.material_entry.insert(0, ", ".join(materials))

        self.weld_type_entry.delete(0, tk.END)
        self.weld_type_entry.insert(0, rule.get("default_weld_type", ""))

        for item in self.thk_tree.get_children():
            self.thk_tree.delete(item)
        for dn, thk_list in sorted(rule.get("thk_candidates_by_dn", {}).items(), key=lambda x: x[0]):
            self.thk_tree.insert("", "end", values=(dn, ", ".join(thk_list)))

    def _upsert_dn_rule(self) -> None:
        class_code = self.class_entry.get().strip().upper()
        if not class_code:
            messagebox.showwarning("提示", "請先指定 Class Code")
            return
        dn = self.dn_entry.get().strip()
        thk_raw = self.thk_entry.get().strip()
        if not dn.isdigit():
            messagebox.showerror("格式錯誤", "DN 必須為數字")
            return
        thk_list = [item.strip() for item in thk_raw.split(",") if item.strip()]
        if not thk_list:
            messagebox.showerror("格式錯誤", "THK 候選不可為空")
            return

        rule = self._working_rules.setdefault(
            class_code,
            {"material_candidates": [], "thk_candidates_by_dn": {}, "default_weld_type": ""},
        )
        by_dn = rule.setdefault("thk_candidates_by_dn", {})
        by_dn[dn] = thk_list
        self._load_class_to_form(class_code)

    def _delete_dn_rule(self) -> None:
        class_code = self.class_entry.get().strip().upper()
        if not class_code or class_code not in self._working_rules:
            return
        sel = self.thk_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "請先選取要刪除的 DN")
            return
        dn = self.thk_tree.item(sel[0], "values")[0]
        self._working_rules[class_code].setdefault("thk_candidates_by_dn", {}).pop(dn, None)
        self._load_class_to_form(class_code)

    def _new_class(self) -> None:
        self.class_list.selection_clear(0, tk.END)
        self._clear_form()

    def _delete_class(self) -> None:
        key = self._current_selected_key()
        if not key:
            messagebox.showwarning("提示", "請先選取 Class")
            return
        if not messagebox.askyesno("確認", f"確定要刪除 {key} ?"):
            return
        self._working_rules.pop(key, None)
        self._refresh_class_list()
        self._clear_form()

    def _validate_and_collect(self) -> Dict[str, Dict]:
        result: Dict[str, Dict] = {}
        for class_code, rule in self._working_rules.items():
            normalized_class = class_code.strip().upper()
            if not normalized_class:
                raise ValueError("存在空白 class code")

            mats = [str(m).strip() for m in rule.get("material_candidates", []) if str(m).strip()]
            # 去重且保序
            dedup_mats: List[str] = []
            seen = set()
            for material in mats:
                if material not in seen:
                    seen.add(material)
                    dedup_mats.append(material)

            by_dn_raw = rule.get("thk_candidates_by_dn", {})
            by_dn: Dict[str, List[str]] = {}
            if not isinstance(by_dn_raw, dict):
                raise ValueError(f"{normalized_class} 的 thk_candidates_by_dn 必須是物件")
            for dn, values in by_dn_raw.items():
                dn_key = str(dn).strip()
                if not dn_key.isdigit():
                    raise ValueError(f"{normalized_class} 的 DN '{dn_key}' 不是數字")
                if not isinstance(values, list):
                    raise ValueError(f"{normalized_class} 的 DN {dn_key} 候選必須是陣列")
                thk_values = [str(v).strip() for v in values if str(v).strip()]
                if not thk_values:
                    raise ValueError(f"{normalized_class} 的 DN {dn_key} 沒有有效厚度候選")
                by_dn[dn_key] = thk_values

            result[normalized_class] = {
                "material_candidates": dedup_mats,
                "thk_candidates_by_dn": by_dn,
                "default_weld_type": str(rule.get("default_weld_type", "")).strip(),
            }
        return result

    def _save(self) -> None:
        class_code = self.class_entry.get().strip().upper()
        if class_code:
            materials = [item.strip() for item in self.material_entry.get().split(",") if item.strip()]
            self._working_rules[class_code] = {
                "material_candidates": materials,
                "thk_candidates_by_dn": self._working_rules.get(class_code, {}).get(
                    "thk_candidates_by_dn", {}
                ),
                "default_weld_type": self.weld_type_entry.get().strip(),
            }

        try:
            checked = self._validate_and_collect()
            self.controller.save_spec_rules(checked)
            self._working_rules = {k: dict(v) for k, v in checked.items()}
            self._refresh_class_list()
            self._clear_form()
            self.on_saved()
            messagebox.showinfo("完成", "spec_rules.json 已更新")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("儲存失敗", str(exc))
