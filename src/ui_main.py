"""Main window — Drawing List 母表為核心 UI."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.controller import AppController
from src.ui_drawing_list import DrawingListTab
from src.ui_weld_editor import WeldControlTab
from src.ui_spec_rules import SpecRulesWidget
from src.ui_welding_qual import WeldingQualWidget
from src.ui_export import ExportWidget


class MainWindow(QMainWindow):
    def __init__(self, ctrl: AppController) -> None:
        super().__init__()
        self.ctrl = ctrl
        self.setWindowTitle(
            f"管線工程管控系統 — {ctrl.project.meta.get('project_name', '')}"
        )
        self.resize(1400, 780)
        self.setMinimumSize(1100, 640)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # ── Tab 1: Drawing List (母表) ───────────────────
        self.drawing_tab = DrawingListTab(
            ctrl=self.ctrl,
            on_open_welds=self._open_weld_tab,
        )
        self.tabs.addTab(self.drawing_tab, "Drawing List")

        # ── Tab 2: Weld Control (子表) ───────────────────
        self.weld_tab = WeldControlTab(ctrl=self.ctrl)
        self.tabs.addTab(self.weld_tab, "Weld Control")

        # ── Tab 3: Spec Rules ────────────────────────────
        self.spec_tab = SpecRulesWidget(
            controller=self.ctrl,
            on_saved=self.weld_tab.refresh,
        )
        self.tabs.addTab(self.spec_tab, "Spec Rules 管理")

        # ── Tab 4: WPS/PQR/Welder ─────────────────────
        self.welding_tab = WeldingQualWidget(
            controller=self.ctrl
        )
        self.tabs.addTab(self.welding_tab, "WPS/PQR 管理")

        # ── Tab 5: Export ────────────────────────────────
        self.export_tab = ExportWidget(controller=self.ctrl)
        self.tabs.addTab(self.export_tab, "匯出 Excel")

    def _open_weld_tab(self, drawing_idx: int) -> None:
        """Called when user double-clicks a drawing to edit welds."""
        self.ctrl.set_current_drawing(drawing_idx)
        self.weld_tab.refresh()
        self.tabs.setCurrentWidget(self.weld_tab)


def launch_app(
    project_path: str,
    profile_path: str,
    rules_path: str,
) -> None:
    app = QApplication(sys.argv)
    ctrl = AppController(project_path, profile_path, rules_path)
    win = MainWindow(ctrl)
    win.show()
    sys.exit(app.exec())
