from __future__ import annotations

import copy
import re
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from src import rules

DN_RANGE_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


class SpecRulesFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, on_saved: Callable[[], None]) -> None:
        super().__init__(parent)
        self.controller = controller
        self.on_saved = on_saved
        self._filtered_class_keys: List[str] = []
        self._active_class: str = ""

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=10, pady=10)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="搜尋 Class").grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        self.class_search_entry = ctk.CTkEntry(left)
        self.class_search_entry.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        self.class_search_entry.bind("<KeyRelease>", self._on_search_class)

        self.class_list = tk.Listbox(left, width=24)
        self.class_list.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
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

        ctk.CTkLabel(right, text="thk candidates (DN / 區段)").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )

        table_wrap = ctk.CTkFrame(right)
        table_wrap.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        self.thk_tree = ttk.Treeview(table_wrap, columns=("dn", "thk_list"), show="headings", height=8)
        self.thk_tree.heading("dn", text="DN / Range")
        self.thk_tree.heading("thk_list", text="THK Candidates (逗號分隔)")
        self.thk_tree.column("dn", width=120, anchor="center")
        self.thk_tree.column("thk_list", width=260, anchor="w")
        self.thk_tree.grid(row=0, column=0, sticky="nsew")
        self.thk_tree.bind("<Double-1>", self._on_tree_double_click)

        thk_editor = ctk.CTkFrame(right)
        thk_editor.grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        thk_editor.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(thk_editor, text="DN/Range").grid(row=0, column=0, padx=4, pady=4)
        self.dn_entry = ctk.CTkEntry(thk_editor, width=120)
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
        ctk.CTkButton(thk_editor, text="套用到全部 DN", command=self._apply_to_all_dn).grid(
            row=1, column=4, padx=4, pady=4
        )
        ctk.CTkButton(thk_editor, text="複製上一筆", command=self._copy_selected_rule).grid(
            row=1, column=5, padx=4, pady=4
        )
        ctk.CTkButton(thk_editor, text="快速建立區段", command=self._quick_add_ranges).grid(
            row=1, column=6, padx=4, pady=4
        )

        btn_row = ctk.CTkFrame(self)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        ctk.CTkButton(btn_row, text="新增 Class", command=self._new_class).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="刪除 Class", command=self._delete_class).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="複製 Class...", command=self._copy_class).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="儲存到 spec_rules.json", command=self._save).pack(side="right", padx=4)

        self._working_rules: Dict[str, Dict] = {}
        self.refresh_from_file()

    def refresh_from_file(self) -> None:
        self.controller.reload_spec_rules()
        self._working_rules = rules.normalize_rules(self.controller.spec_rules)
        self._refresh_class_list()
        self._clear_form()

    def _refresh_class_list(self, keep_selected: str = "") -> None:
        selected = keep_selected or self._active_class
        keyword = self.class_search_entry.get().strip().upper() if hasattr(self, "class_search_entry") else ""
        all_keys = sorted(self._working_rules.keys())
        self._filtered_class_keys = [key for key in all_keys if keyword in key]
        self.class_list.delete(0, tk.END)
        selected_idx = -1
        for idx, class_code in enumerate(self._filtered_class_keys):
            self.class_list.insert(tk.END, class_code)
            if class_code == selected:
                selected_idx = idx
        if selected_idx >= 0:
            self.class_list.selection_set(selected_idx)
            self.class_list.activate(selected_idx)

    def _clear_form(self) -> None:
        self._active_class = ""
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
        idx = sel[0]
        if idx >= len(self._filtered_class_keys):
            return ""
        return self._filtered_class_keys[idx]

    def _on_search_class(self, _event: tk.Event) -> None:
        self._refresh_class_list()

    def _on_select_class(self, _event: tk.Event) -> None:
        class_code = self._current_selected_key()
        if not class_code:
            return
        if self._active_class and class_code != self._active_class and not self._confirm_switch_class(class_code):
            self._refresh_class_list(keep_selected=self._active_class)
            return
        self._load_class_to_form(class_code)

    def _confirm_switch_class(self, target_class: str) -> bool:
        if not self._is_form_dirty():
            return True
        answer = messagebox.askyesnocancel("未儲存變更", "目前 Class 有未儲存變更，是否先套用到暫存規則？")
        if answer is None:
            return False
        if answer:
            if not self._persist_form_to_working():
                return False
            self._refresh_class_list(keep_selected=target_class)
        return True

    def _load_class_to_form(self, class_code: str) -> None:
        rule = self._working_rules.get(class_code, {})
        self._active_class = class_code

        self.class_entry.delete(0, tk.END)
        self.class_entry.insert(0, class_code)

        materials = rule.get("material_candidates", [])
        self.material_entry.delete(0, tk.END)
        self.material_entry.insert(0, ", ".join(materials))

        self.weld_type_entry.delete(0, tk.END)
        self.weld_type_entry.insert(0, rule.get("default_weld_type", ""))

        self._reload_thk_tree(class_code)

    def _reload_thk_tree(self, class_code: str) -> None:
        rule = self._working_rules.get(class_code, {})
        for item in self.thk_tree.get_children():
            self.thk_tree.delete(item)

        by_dn = rule.get("thk_candidates_by_dn", {})
        for dn, thk_list in sorted(by_dn.items(), key=lambda x: int(x[0])):
            self.thk_tree.insert("", "end", iid=f"dn::{dn}", values=(dn, ", ".join(thk_list)))

        for idx, range_item in enumerate(sorted(rule.get("thk_rules", []), key=lambda x: (x["dn_min"], x["dn_max"]))):
            label = f"{range_item['dn_min']}-{range_item['dn_max']}"
            self.thk_tree.insert("", "end", iid=f"range::{idx}", values=(label, ", ".join(range_item.get("thk", []))))

    def _upsert_dn_rule(self) -> None:
        class_code = self.class_entry.get().strip().upper()
        if not class_code:
            messagebox.showwarning("提示", "請先指定 Class Code")
            return

        dn_text = self.dn_entry.get().strip()
        thk_list = self._parse_thk_list()
        if not thk_list:
            messagebox.showerror("格式錯誤", "THK 候選不可為空")
            return

        rule = self._working_rules.setdefault(
            class_code,
            {"material_candidates": [], "thk_candidates_by_dn": {}, "thk_rules": [], "default_weld_type": ""},
        )
        by_dn = rule.setdefault("thk_candidates_by_dn", {})
        ranges = rule.setdefault("thk_rules", [])

        if dn_text.isdigit():
            by_dn[dn_text] = thk_list
        else:
            matched = DN_RANGE_RE.match(dn_text)
            if not matched:
                messagebox.showerror("格式錯誤", "DN 必須是數字或區段，例如 15-40")
                return
            dn_min, dn_max = int(matched.group(1)), int(matched.group(2))
            if dn_min > dn_max:
                dn_min, dn_max = dn_max, dn_min
            self._upsert_range_rule(ranges, dn_min, dn_max, thk_list)

        self._active_class = class_code
        self._refresh_class_list(keep_selected=class_code)
        self._load_class_to_form(class_code)

    def _upsert_range_rule(self, ranges: List[Dict], dn_min: int, dn_max: int, thk_list: List[str]) -> None:
        for item in ranges:
            if int(item.get("dn_min", -1)) == dn_min and int(item.get("dn_max", -1)) == dn_max:
                item["thk"] = thk_list
                return
        ranges.append({"dn_min": dn_min, "dn_max": dn_max, "thk": thk_list})

    def _delete_dn_rule(self) -> None:
        class_code = self.class_entry.get().strip().upper()
        if not class_code or class_code not in self._working_rules:
            return
        sel = self.thk_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "請先選取要刪除的 DN")
            return

        item_id = sel[0]
        rule = self._working_rules[class_code]
        if item_id.startswith("dn::"):
            dn = item_id.split("::", 1)[1]
            rule.setdefault("thk_candidates_by_dn", {}).pop(dn, None)
        elif item_id.startswith("range::"):
            dn_text = self.thk_tree.item(item_id, "values")[0]
            matched = DN_RANGE_RE.match(dn_text)
            if matched:
                dn_min, dn_max = int(matched.group(1)), int(matched.group(2))
                rule["thk_rules"] = [
                    item
                    for item in rule.setdefault("thk_rules", [])
                    if int(item.get("dn_min", -1)) != dn_min or int(item.get("dn_max", -1)) != dn_max
                ]
        self._load_class_to_form(class_code)

    def _copy_selected_rule(self) -> None:
        sel = self.thk_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "請先選取一筆規則")
            return
        dn_text, thk_text = self.thk_tree.item(sel[0], "values")
        self.dn_entry.delete(0, tk.END)
        self.dn_entry.insert(0, dn_text)
        self.thk_entry.delete(0, tk.END)
        self.thk_entry.insert(0, thk_text)

    def _on_tree_double_click(self, _event: tk.Event) -> None:
        self._copy_selected_rule()

    def _apply_to_all_dn(self) -> None:
        class_code = self.class_entry.get().strip().upper()
        if not class_code or class_code not in self._working_rules:
            messagebox.showwarning("提示", "請先選擇有效的 Class")
            return
        thk_list = self._parse_thk_list()
        if not thk_list:
            messagebox.showerror("格式錯誤", "THK 候選不可為空")
            return
        rule = self._working_rules[class_code]
        for dn in list(rule.get("thk_candidates_by_dn", {}).keys()):
            rule["thk_candidates_by_dn"][dn] = thk_list
        for item in rule.get("thk_rules", []):
            item["thk"] = thk_list
        self._load_class_to_form(class_code)

    def _quick_add_ranges(self) -> None:
        class_code = self.class_entry.get().strip().upper()
        if not class_code:
            messagebox.showwarning("提示", "請先指定 Class Code")
            return
        thk_list = self._parse_thk_list()
        if not thk_list:
            messagebox.showerror("格式錯誤", "請先輸入 THK 列表後再快速建立區段")
            return

        preset = [(15, 40), (50, 125), (150, 600)]
        rule = self._working_rules.setdefault(
            class_code,
            {"material_candidates": [], "thk_candidates_by_dn": {}, "thk_rules": [], "default_weld_type": ""},
        )
        ranges = rule.setdefault("thk_rules", [])
        for dn_min, dn_max in preset:
            self._upsert_range_rule(ranges, dn_min, dn_max, thk_list)

        self._active_class = class_code
        self._refresh_class_list(keep_selected=class_code)
        self._load_class_to_form(class_code)

    def _new_class(self) -> None:
        if self._active_class and self._is_form_dirty() and not self._confirm_switch_class(""):
            return
        self.class_list.selection_clear(0, tk.END)
        self._clear_form()

    def _copy_class(self) -> None:
        source = self._current_selected_key() or self._active_class
        if not source or source not in self._working_rules:
            messagebox.showwarning("提示", "請先選取要複製的來源 Class")
            return
        target = simpledialog.askstring("複製 Class", "請輸入新的 Class Code")
        if target is None:
            return
        new_code = target.strip().upper()
        if not new_code:
            messagebox.showerror("錯誤", "Class Code 不可為空")
            return
        if new_code in self._working_rules:
            messagebox.showerror("錯誤", f"{new_code} 已存在")
            return

        self._working_rules[new_code] = copy.deepcopy(self._working_rules[source])
        self._refresh_class_list(keep_selected=new_code)
        self._load_class_to_form(new_code)

    def _delete_class(self) -> None:
        key = self._current_selected_key() or self._active_class
        if not key:
            messagebox.showwarning("提示", "請先選取 Class")
            return
        if not messagebox.askyesno("確認", f"確定要刪除 {key} ?"):
            return
        self._working_rules.pop(key, None)
        self._refresh_class_list()
        self._clear_form()

    def _parse_thk_list(self) -> List[str]:
        return [item.strip() for item in self.thk_entry.get().split(",") if item.strip()]

    def _material_list(self) -> List[str]:
        return [item.strip() for item in self.material_entry.get().split(",") if item.strip()]

    def _persist_form_to_working(self) -> Optional[str]:
        class_code = self.class_entry.get().strip().upper()
        if not class_code:
            return None

        base_rule = self._working_rules.get(self._active_class or class_code, {})
        next_rule = {
            "material_candidates": self._material_list(),
            "thk_candidates_by_dn": copy.deepcopy(base_rule.get("thk_candidates_by_dn", {})),
            "thk_rules": copy.deepcopy(base_rule.get("thk_rules", [])),
            "default_weld_type": self.weld_type_entry.get().strip(),
        }

        if self._active_class and self._active_class != class_code:
            self._working_rules.pop(self._active_class, None)
        self._working_rules[class_code] = next_rule
        self._active_class = class_code
        return class_code

    def _is_form_dirty(self) -> bool:
        class_code = self.class_entry.get().strip().upper()
        if not class_code:
            return any(
                [
                    self.material_entry.get().strip(),
                    self.weld_type_entry.get().strip(),
                    self.dn_entry.get().strip(),
                    self.thk_entry.get().strip(),
                ]
            )

        base_rule = self._working_rules.get(self._active_class or class_code, {})
        current_rule = {
            "material_candidates": self._material_list(),
            "thk_candidates_by_dn": base_rule.get("thk_candidates_by_dn", {}),
            "thk_rules": base_rule.get("thk_rules", []),
            "default_weld_type": self.weld_type_entry.get().strip(),
        }
        existing_rule = self._working_rules.get(class_code)
        if existing_rule is None:
            return True
        return rules.normalize_rules({"_": current_rule})["_"] != rules.normalize_rules({"_": existing_rule})["_"]

    def _validate_and_collect(self) -> Dict[str, Dict]:
        return rules.normalize_rules(self._working_rules)

    def _save(self) -> None:
        class_code = self._persist_form_to_working()

        try:
            checked = self._validate_and_collect()
            self.controller.save_spec_rules(checked)
            self._working_rules = copy.deepcopy(checked)
            keep_key = class_code or self._active_class
            self._refresh_class_list(keep_selected=keep_key)
            if keep_key and keep_key in self._working_rules:
                self._load_class_to_form(keep_key)
            else:
                self._clear_form()
            self.on_saved()
            messagebox.showinfo("完成", "spec_rules.json 已更新")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("儲存失敗", str(exc))
