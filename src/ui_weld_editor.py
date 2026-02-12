"""Weld Control tab — child-table editor for a selected Drawing."""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.controller import AppController
from src.models import WELD_FIELDS, WELD_KEYS


class WeldControlTab(QWidget):
    """Weld editor bound to a single Drawing selected in the controller."""

    def __init__(
        self, ctrl: AppController, parent=None
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl
        self._sel_row: Optional[int] = None

        layout = QVBoxLayout(self)

        # ── header ───────────────────────────────────────
        self.header_label = QLabel("尚未選擇 Drawing")
        self.header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )
        layout.addWidget(self.header_label)

        # ── batch generate ───────────────────────────────
        gen_group = QGroupBox("批次產生焊口")
        gen_layout = QHBoxLayout(gen_group)

        gen_layout.addWidget(QLabel("焊口數量:"))
        self.gen_count = QSpinBox()
        self.gen_count.setRange(1, 500)
        self.gen_count.setValue(5)
        gen_layout.addWidget(self.gen_count)

        gen_layout.addWidget(QLabel("編號前綴:"))
        self.gen_prefix = QLineEdit("W")
        self.gen_prefix.setMaximumWidth(80)
        gen_layout.addWidget(self.gen_prefix)

        gen_btn = QPushButton("產生")
        gen_btn.clicked.connect(self._batch_generate)
        gen_layout.addWidget(gen_btn)

        default_btn = QPushButton("套用母表預設值到所有焊口")
        default_btn.clicked.connect(self._apply_defaults)
        gen_layout.addWidget(default_btn)

        gen_layout.addStretch()
        layout.addWidget(gen_group)

        # ── weld table ───────────────────────────────────
        self.table = QTableWidget(0, len(WELD_KEYS))
        self.table.setHorizontalHeaderLabels(
            [f[1] for f in WELD_FIELDS]
        )
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.currentCellChanged.connect(
            self._on_select
        )
        layout.addWidget(self.table, stretch=1)

        # ── single-weld editor ───────────────────────────
        edit_group = QGroupBox("編輯焊口")
        edit_grid = QGridLayout(edit_group)
        self.weld_fields: Dict[str, QLineEdit] = {}

        for col, (key, header) in enumerate(WELD_FIELDS):
            edit_grid.addWidget(QLabel(header), 0, col)
            if key == "shop_field":
                combo = QComboBox()
                combo.addItems(["S", "F"])
                edit_grid.addWidget(combo, 1, col)
                self._shop_combo = combo
            else:
                le = QLineEdit()
                edit_grid.addWidget(le, 1, col)
                self.weld_fields[key] = le

        btn_row = QHBoxLayout()
        save_btn = QPushButton("儲存焊口修改")
        save_btn.clicked.connect(self._save_weld)
        btn_row.addWidget(save_btn)

        del_btn = QPushButton("刪除選取焊口")
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()

        edit_grid.addLayout(
            btn_row, 2, 0, 1, len(WELD_FIELDS)
        )
        layout.addWidget(edit_group)

    # ══════════════════════════════════════════════════════
    # Public
    # ══════════════════════════════════════════════════════
    def refresh(self) -> None:
        """Reload table from current drawing."""
        dw = self.ctrl.current_drawing()
        if dw is None:
            self.header_label.setText("尚未選擇 Drawing")
            self.table.setRowCount(0)
            return
        self.header_label.setText(
            f"Drawing: {dw.series_no}  —  {dw.dwg_no}"
        )
        self.table.setRowCount(0)
        for w in dw.welds:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(WELD_KEYS):
                val = getattr(w, key, "")
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                self.table.setItem(row, col, item)
        self._sel_row = None

    # ══════════════════════════════════════════════════════
    # Internal
    # ══════════════════════════════════════════════════════
    def _on_select(
        self, row: int, _c: int, _pr: int, _pc: int
    ) -> None:
        if row < 0:
            self._sel_row = None
            return
        self._sel_row = row
        dw = self.ctrl.current_drawing()
        if not dw or row >= len(dw.welds):
            return
        w = dw.welds[row]
        for key, le in self.weld_fields.items():
            le.setText(getattr(w, key, ""))
        self._shop_combo.setCurrentText(w.shop_field or "S")

    # ── batch generate ───────────────────────────────────
    def _batch_generate(self) -> None:
        dw = self.ctrl.current_drawing()
        if not dw:
            QMessageBox.warning(
                self, "提示", "請先從 Drawing List 選取 Drawing"
            )
            return
        count = self.gen_count.value()
        prefix = self.gen_prefix.text().strip() or "W"
        start = len(dw.welds) + 1
        defaults = self.ctrl.get_weld_defaults()
        new_welds: List[Dict[str, str]] = []
        for i in range(count):
            w = dict(defaults)
            w["weld_no"] = f"{prefix}{start + i}"
            new_welds.append(w)
        self.ctrl.add_welds(new_welds)
        self.refresh()

    def _apply_defaults(self) -> None:
        self.ctrl.apply_defaults_to_all_welds()
        self.refresh()
        QMessageBox.information(
            self, "完成", "已套用母表預設值"
        )

    # ── save / delete ────────────────────────────────────
    def _save_weld(self) -> None:
        if self._sel_row is None:
            QMessageBox.warning(
                self, "提示", "請先選取焊口"
            )
            return
        data = {k: le.text() for k, le in self.weld_fields.items()}
        data["shop_field"] = self._shop_combo.currentText()
        self.ctrl.update_weld(self._sel_row, data)
        self.refresh()

    def _delete_selected(self) -> None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(self, "提示", "請先選取焊口")
            return
        indices = [s.row() for s in sel]
        ans = QMessageBox.question(
            self, "確認",
            f"確定刪除 {len(indices)} 個焊口？",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.ctrl.delete_welds(indices)
        self._sel_row = None
        self.refresh()
