"""Export tab — Excel / future format export."""
from __future__ import annotations

import traceback

from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.controller import AppController


class ExportWidget(QWidget):
    """Simple panel to trigger project export to Excel."""

    def __init__(
        self, controller: AppController, parent=None
    ) -> None:
        super().__init__(parent)
        self.ctrl = controller

        layout = QVBoxLayout(self)

        group = QGroupBox("匯出 Excel")
        g_layout = QVBoxLayout(group)

        g_layout.addWidget(
            QLabel(
                "匯出兩張工作表：\n"
                "  Sheet 1 — Drawing List (母表)\n"
                "  Sheet 2 — Weld Control (子表)"
            )
        )

        export_btn = QPushButton("選擇目錄並匯出")
        export_btn.clicked.connect(self._export)
        g_layout.addWidget(export_btn)

        self.result_label = QLabel("")
        g_layout.addWidget(self.result_label)

        layout.addWidget(group)
        layout.addStretch()

    def _export(self) -> None:
        out_dir = QFileDialog.getExistingDirectory(
            self, "選擇匯出目錄"
        )
        if not out_dir:
            return
        try:
            path = self.ctrl.export_project(out_dir)
            self.result_label.setText(f"已匯出: {path}")
            QMessageBox.information(
                self, "完成", f"檔案已匯出至:\n{path}"
            )
        except Exception:
            QMessageBox.critical(
                self, "匯出失敗", traceback.format_exc()
            )
