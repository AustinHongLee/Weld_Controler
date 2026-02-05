from __future__ import annotations

import threading
import traceback
from tkinter import messagebox

import customtkinter as ctk


class ExportFrame(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(anchor="w", padx=10, pady=(10, 4))

        ctk.CTkButton(self, text="匯出 Excel", command=self._export).pack(
            padx=10, pady=10, anchor="w"
        )

    def _export(self) -> None:
        def task() -> None:
            try:
                path = self.controller.export_project("output")
                self.after(0, lambda: self.status_label.configure(text=f"已輸出: {path}"))
                self.after(0, lambda: messagebox.showinfo("完成", f"匯出完成: {path}"))
            except Exception:  # noqa: BLE001
                summary = traceback.format_exc()
                self.after(0, lambda: messagebox.showerror("匯出失敗", summary))

        threading.Thread(target=task, daemon=True).start()
