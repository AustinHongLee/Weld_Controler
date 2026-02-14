"""Spec Rules editor — Piping Material Classification.

Left: class list.  Right: tabbed detail (基本定義 / 連接 / 檢驗 / 管材&壁厚).
"""
from __future__ import annotations

from typing import Any, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.controller import AppController
from src.rules import SPEC_FIELDS, _empty_spec, normalize_rules


class SpecRulesWidget(QWidget):
    """Full-featured Piping Material Classification editor."""

    def __init__(
        self,
        controller: AppController,
        on_saved=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ctrl = controller
        self.on_saved = on_saved
        # work on a deep copy
        self._rules: Dict[str, Any] = {
            k: dict(v) for k, v in self.ctrl.spec_rules.items()
        }
        self._current_class: str = ""

        outer = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ════════════════════════════════════════════
        # LEFT — class list
        # ════════════════════════════════════════════
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)

        left_lay.addWidget(QLabel("管線級數 (Class)"))
        self.class_list = QListWidget()
        self.class_list.currentTextChanged.connect(
            self._on_class_selected
        )
        left_lay.addWidget(self.class_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._add_class)
        btn_row.addWidget(add_btn)
        dup_btn = QPushButton("複製")
        dup_btn.clicked.connect(self._dup_class)
        btn_row.addWidget(dup_btn)
        del_btn = QPushButton("刪除")
        del_btn.clicked.connect(self._del_class)
        btn_row.addWidget(del_btn)
        left_lay.addLayout(btn_row)

        splitter.addWidget(left)

        # ════════════════════════════════════════════
        # RIGHT — tabbed detail
        # ════════════════════════════════════════════
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)

        self.class_label = QLabel("（請選擇級數）")
        self.class_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )
        right_lay.addWidget(self.class_label)

        self.tabs = QTabWidget()

        # ── Tab 1: 基本定義 ──────────────────────
        tab1 = QWidget()
        t1 = QGridLayout(tab1)
        self._scalar_widgets: Dict[str, QWidget] = {}

        _BASIC_KEYS = [
            "description", "rating", "base_material",
            "pipe_spec", "design_temp_min",
            "design_temp_max", "design_pressure",
            "corrosion_allowance",
        ]
        self._build_scalar_grid(t1, _BASIC_KEYS)
        t1.setRowStretch(t1.rowCount(), 1)
        self.tabs.addTab(tab1, "基本定義")

        # ── Tab 2: 連接方式 ──────────────────────
        tab2 = QWidget()
        t2 = QGridLayout(tab2)
        _CONN_KEYS = [
            "default_weld_type", "joint_type",
            "dn_threshold_bw", "flange_face",
            "gasket_type", "bolt_material",
        ]
        self._build_scalar_grid(t2, _CONN_KEYS)
        t2.setRowStretch(t2.rowCount(), 1)
        self.tabs.addTab(tab2, "連接方式")

        # ── Tab 3: 檢驗/處理 ─────────────────────
        tab3 = QWidget()
        t3 = QGridLayout(tab3)
        _INSP_KEYS = [
            "pwht_required", "nde_requirement",
        ]
        self._build_scalar_grid(t3, _INSP_KEYS)
        t3.setRowStretch(t3.rowCount(), 1)
        self.tabs.addTab(tab3, "檢驗 / 處理")

        # ── Tab 4: 管材 & 壁厚 ───────────────────
        tab4 = QWidget()
        t4 = QVBoxLayout(tab4)

        # default material + candidates
        mat_group = QGroupBox("管材")
        mg = QGridLayout(mat_group)
        mg.addWidget(QLabel("預設管材:"), 0, 0)
        self.default_mat_edit = QLineEdit()
        mg.addWidget(self.default_mat_edit, 0, 1)
        mg.addWidget(
            QLabel("材質候選 (逗號分隔):"), 1, 0
        )
        self.mat_edit = QLineEdit()
        mg.addWidget(self.mat_edit, 1, 1)
        t4.addWidget(mat_group)

        # thk by dn table
        thk_group = QGroupBox("壁厚候選 by DN")
        tg = QVBoxLayout(thk_group)
        self.thk_table = QTableWidget(0, 2)
        self.thk_table.setHorizontalHeaderLabels(
            ["DN", "壁厚候選 (逗號分隔)"]
        )
        hdr = self.thk_table.horizontalHeader()
        hdr.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        tg.addWidget(self.thk_table)

        thk_btns = QHBoxLayout()
        add_dn = QPushButton("新增 DN 行")
        add_dn.clicked.connect(self._add_dn_row)
        thk_btns.addWidget(add_dn)
        del_dn = QPushButton("刪除 DN 行")
        del_dn.clicked.connect(self._del_dn_row)
        thk_btns.addWidget(del_dn)
        tg.addLayout(thk_btns)
        t4.addWidget(thk_group)

        self.tabs.addTab(tab4, "管材 & 壁厚")

        right_lay.addWidget(self.tabs, stretch=1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        outer.addWidget(splitter, stretch=1)

        # ── save button ──────────────────────────
        save_btn = QPushButton("儲存規則")
        save_btn.setMinimumHeight(36)
        save_btn.clicked.connect(self._save)
        outer.addWidget(save_btn)

        # populate
        self._load_classes()

    # ════════════════════════════════════════════════════
    # Build helpers
    # ════════════════════════════════════════════════════
    def _build_scalar_grid(
        self, grid: QGridLayout, keys: List[str]
    ) -> None:
        _lookup = {f[0]: f for f in SPEC_FIELDS}
        cols = 2  # label + widget per column pair
        col_pairs = 2  # two pairs side by side
        r, c = 0, 0
        for key in keys:
            meta = _lookup.get(key)
            if not meta:
                continue
            _, header, input_type = meta

            label = QLabel(f"{header}:")
            grid.addWidget(label, r, c * cols)

            if input_type == "bool":
                w = QCheckBox()
                grid.addWidget(w, r, c * cols + 1)
            else:
                w = QLineEdit()
                grid.addWidget(w, r, c * cols + 1)

            self._scalar_widgets[key] = w
            c += 1
            if c >= col_pairs:
                c = 0
                r += 1
        # final row if odd
        if c != 0:
            r += 1

    # ════════════════════════════════════════════════════
    # Class list
    # ════════════════════════════════════════════════════
    def _load_classes(self) -> None:
        self.class_list.clear()
        for k in sorted(self._rules.keys()):
            self.class_list.addItem(k)
        if self.class_list.count():
            self.class_list.setCurrentRow(0)

    def _add_class(self) -> None:
        name, ok = QInputDialog.getText(
            self, "新增級數", "Class 代碼:"
        )
        name = name.strip().upper()
        if not ok or not name:
            return
        if name in self._rules:
            QMessageBox.warning(
                self, "重複", f"{name} 已存在"
            )
            return
        self._rules[name] = _empty_spec()
        self._load_classes()
        items = self.class_list.findItems(
            name, Qt.MatchFlag.MatchExactly
        )
        if items:
            self.class_list.setCurrentItem(items[0])

    def _dup_class(self) -> None:
        cur = self.class_list.currentItem()
        if not cur:
            return
        src_key = cur.text()
        name, ok = QInputDialog.getText(
            self, "複製級數",
            f"將 {src_key} 複製為:",
        )
        name = name.strip().upper()
        if not ok or not name:
            return
        if name in self._rules:
            QMessageBox.warning(
                self, "重複", f"{name} 已存在"
            )
            return
        import copy
        self._commit_current()
        self._rules[name] = copy.deepcopy(
            self._rules[src_key]
        )
        self._load_classes()
        items = self.class_list.findItems(
            name, Qt.MatchFlag.MatchExactly
        )
        if items:
            self.class_list.setCurrentItem(items[0])

    def _del_class(self) -> None:
        cur = self.class_list.currentItem()
        if not cur:
            return
        key = cur.text()
        ans = QMessageBox.question(
            self, "確認", f"確定刪除 {key}？",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._rules.pop(key, None)
        self._current_class = ""
        self._load_classes()

    # ════════════════════════════════════════════════════
    # Detail population / commit
    # ════════════════════════════════════════════════════
    def _on_class_selected(self, class_code: str) -> None:
        if not class_code:
            return
        # commit previous class
        self._commit_current()
        self._current_class = class_code
        rule = self._rules.get(class_code, {})

        self.class_label.setText(
            f"{class_code}  —  "
            f"{rule.get('description', '')}"
        )

        # scalar fields
        for key, w in self._scalar_widgets.items():
            val = rule.get(key, "")
            if isinstance(w, QCheckBox):
                w.setChecked(bool(val))
            else:
                w.setText(str(val) if val else "")

        # material tab
        self.default_mat_edit.setText(
            str(rule.get("default_material", ""))
        )
        mats = rule.get("material_candidates", [])
        self.mat_edit.setText(", ".join(mats))

        # thk table
        self.thk_table.setRowCount(0)
        by_dn = rule.get("thk_candidates_by_dn", {})
        for dk in sorted(
            by_dn.keys(),
            key=lambda x: int(x) if x.isdigit() else 0,
        ):
            row = self.thk_table.rowCount()
            self.thk_table.insertRow(row)
            self.thk_table.setItem(
                row, 0, QTableWidgetItem(dk)
            )
            self.thk_table.setItem(
                row, 1,
                QTableWidgetItem(", ".join(by_dn[dk])),
            )

    def _commit_current(self) -> None:
        key = self._current_class
        if not key or key not in self._rules:
            return
        self._rules[key] = self._build_from_ui()

    def _build_from_ui(self) -> Dict[str, Any]:
        spec = _empty_spec()

        # scalar fields
        for key, w in self._scalar_widgets.items():
            if isinstance(w, QCheckBox):
                spec[key] = w.isChecked()
            else:
                spec[key] = w.text().strip()

        # material
        spec["default_material"] = (
            self.default_mat_edit.text().strip()
        )
        spec["material_candidates"] = [
            m.strip()
            for m in self.mat_edit.text().split(",")
            if m.strip()
        ]

        # thk by dn
        by_dn: Dict[str, List[str]] = {}
        for r in range(self.thk_table.rowCount()):
            dn_item = self.thk_table.item(r, 0)
            thk_item = self.thk_table.item(r, 1)
            if not dn_item:
                continue
            dk = dn_item.text().strip()
            thks = (
                [
                    t.strip()
                    for t in thk_item.text().split(",")
                    if t.strip()
                ]
                if thk_item else []
            )
            if dk:
                by_dn[dk] = thks
        spec["thk_candidates_by_dn"] = by_dn

        # preserve thk_rules if they existed
        old = self._rules.get(self._current_class, {})
        spec["thk_rules"] = old.get("thk_rules", [])

        return spec

    # ── thk table helpers ────────────────────────
    def _add_dn_row(self) -> None:
        row = self.thk_table.rowCount()
        self.thk_table.insertRow(row)
        self.thk_table.setItem(
            row, 0, QTableWidgetItem("")
        )
        self.thk_table.setItem(
            row, 1, QTableWidgetItem("")
        )

    def _del_dn_row(self) -> None:
        row = self.thk_table.currentRow()
        if row >= 0:
            self.thk_table.removeRow(row)

    # ════════════════════════════════════════════════════
    # Save
    # ════════════════════════════════════════════════════
    def _save(self) -> None:
        self._commit_current()
        try:
            cleaned = normalize_rules(self._rules)
            self.ctrl.save_spec_rules(cleaned)
            self._rules = {
                k: dict(v)
                for k, v in cleaned.items()
            }
            QMessageBox.information(
                self, "完成", "規則已儲存"
            )
            if self.on_saved:
                self.on_saved()
        except Exception as exc:
            QMessageBox.critical(
                self, "錯誤", str(exc)
            )
