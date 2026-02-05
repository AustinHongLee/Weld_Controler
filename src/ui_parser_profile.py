from __future__ import annotations

import threading
import traceback
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk


class ParserProfileFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, on_refresh: Callable[[], None]) -> None:
        super().__init__(parent)
        self.controller = controller
        self.on_refresh = on_refresh

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="解析設定").grid(row=0, column=0, padx=10, pady=10)

        self.profile_var = ctk.StringVar(value=self._current_profile())
        self.profile_menu = ctk.CTkOptionMenu(
            self, values=list(self.controller.parser_profiles.keys()), variable=self.profile_var
        )
        self.profile_menu.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.mapping_label = ctk.CTkLabel(self, text="")
        self.mapping_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=10)

        ctk.CTkButton(self, text="重新解析全部 drawings", command=self._reparse).grid(
            row=0, column=2, padx=10, pady=10
        )

        self.profile_var.trace_add("write", self._on_profile_change)
        self._update_mapping_text()

    def _current_profile(self) -> str:
        return self.controller.project.get("meta", {}).get("parser_profile", "default")

    def _on_profile_change(self, *_args) -> None:
        profile = self.profile_var.get()
        self.controller.project.setdefault("meta", {})["parser_profile"] = profile
        self.controller.save()
        self._update_mapping_text()

    def _update_mapping_text(self) -> None:
        profile = self.controller.parser_profiles.get(self.profile_var.get(), {})
        delimiter = profile.get("delimiter", "-")
        mapping = profile.get("mapping", [])
        mapping_text = f"delimiter: {delimiter} | mapping: {', '.join(mapping)}"
        self.mapping_label.configure(text=mapping_text)

    def _reparse(self) -> None:
        def task() -> None:
            try:
                self.controller.reparse_all()
                self.on_refresh()
                self.after(0, lambda: messagebox.showinfo("完成", "已重新解析全部 DWG"))
            except Exception:  # noqa: BLE001
                summary = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror("解析失敗", summary))

        threading.Thread(target=task, daemon=True).start()
