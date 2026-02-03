from __future__ import annotations

import tkinter as tk
import traceback
from tkinter import filedialog, messagebox
from typing import Callable, Dict, List

import customtkinter as ctk


class DwgImportFrame(ctk.CTkFrame):
    def __init__(self, parent, controller, on_refresh: Callable[[], None]) -> None:
        super().__init__(parent)
        self.controller = controller
        self.on_refresh = on_refresh

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text="貼上 DWG 清單 (每行: 流水號<tab/空白>DWG NO)").grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4)
        )

        self.textbox = ctk.CTkTextbox(self, height=160)
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10)

        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(button_frame, text="匯入貼上內容", command=self._import_from_text).grid(
            row=0, column=0, padx=5
        )
        ctk.CTkButton(button_frame, text="讀取 TXT 檔", command=self._import_from_file).grid(
            row=0, column=1, padx=5
        )

    def _parse_lines(self, lines: List[str]) -> List[Dict[str, str]]:
        rows = []
        for line in lines:
            cleaned = line.strip()
            if not cleaned:
                continue
            parts = cleaned.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            dwg_no = " ".join(parts[1:]).strip()
            if not dwg_no:
                continue
            rows.append({"serial": serial, "dwg_no": dwg_no})
        return rows

    def _import_from_text(self) -> None:
        try:
            content = self.textbox.get("1.0", tk.END)
            rows = self._parse_lines(content.splitlines())
            if not rows:
                messagebox.showwarning("提示", "沒有可匯入的資料")
                return
            self.controller.import_drawings(rows)
            self.on_refresh()
            messagebox.showinfo("完成", f"已匯入 {len(rows)} 筆 DWG")
        except Exception:  # noqa: BLE001
            summary = traceback.format_exc()
            messagebox.showerror("匯入失敗", summary)

    def _import_from_file(self) -> None:
        path = filedialog.askopenfilename(
            title="選擇 DWG 清單 TXT",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                rows = self._parse_lines(handle.readlines())
            if not rows:
                messagebox.showwarning("提示", "沒有可匯入的資料")
                return
            self.controller.import_drawings(rows)
            self.on_refresh()
            messagebox.showinfo("完成", f"已匯入 {len(rows)} 筆 DWG")
        except Exception:  # noqa: BLE001
            summary = traceback.format_exc()
            messagebox.showerror("匯入失敗", summary)
