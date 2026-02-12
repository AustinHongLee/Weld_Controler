"""Spec Rules editor — pipe class → material / thk / weld_type."""
from __future__ import annotations

from typing import Any, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.controller import AppController


class SpecRulesWidget(QWidget):
    """Editor for spec_rules.json (pipe class → material, thk, weld_type)."""

    def __init__(
        self,
        controller: AppController,
        on_saved=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ctrl = controller
        self.on_saved = on_saved
        self._rules: Dict[str, Any] = dict(self.ctrl.spec_rules)

        outer = QVBoxLayout(self)

        # ── class list ───────────────────────────────────
        top = QHBoxLayout()

        left_box = QGroupBox("管線級數 (Class)")
        left_layout = QVBoxLayout(left_box)
        self.class_list = QListWidget()
        self.class_list.currentTextChanged.connect(
            self._on_class_selected
        )
        left_layout.addWidget(self.class_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._add_class)
        btn_row.addWidget(add_btn)
        del_btn = QPushButton("刪除")
        del_btn.clicked.connect(self._del_class)
        btn_row.addWidget(del_btn)
        left_layout.addLayout(btn_row)

        top.addWidget(left_box, stretch=1)

        # ── detail panel ─────────────────────────────────
        right_box = QGroupBox("規則明細")
        right_layout = QVBoxLayout(right_box)

        # materials
        right_layout.addWidget(QLabel("材質候選 (逗號分隔):"))
        self.mat_edit = QLineEdit()
        right_layout.addWidget(self.mat_edit)

        # default weld type
        right_layout.addWidget(QLabel("預設焊接型式:"))
        self.weld_type_edit = QLineEdit()
        right_layout.addWidget(self.weld_type_edit)

        # thk by dn table
        right_layout.addWidget(
            QLabel("厚度候選 by DN (DN | thk候選逗號分隔):")
        )
        self.thk_table = QTableWidget(0, 2)
        self.thk_table.setHorizontalHeaderLabels(
            ["DN", "厚度候選"]
        )
        self.thk_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        right_layout.addWidget(self.thk_table, stretch=1)

        thk_btns = QHBoxLayout()
        add_dn_btn = QPushButton("新增 DN 行")
        add_dn_btn.clicked.connect(self._add_dn_row)
        thk_btns.addWidget(add_dn_btn)
        del_dn_btn = QPushButton("刪除 DN 行")
        del_dn_btn.clicked.connect(self._del_dn_row)
        thk_btns.addWidget(del_dn_btn)
        right_layout.addLayout(thk_btns)

        top.addWidget(right_box, stretch=3)
        outer.addLayout(top)

        # ── save ─────────────────────────────────────────
        save_btn = QPushButton("儲存規則")
        save_btn.clicked.connect(self._save)
        outer.addWidget(save_btn)

        # initial load
        self._load_classes()

    # ═════════════════════════════════════════════════════
    # Class list management
    # ═════════════════════════════════════════════════════
    def _load_classes(self) -> None:
        self.class_list.clear()
        for key in sorted(self._rules.keys()):
            self.class_list.addItem(key)
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
        self._rules[name] = {
            "material_candidates": [],
            "thk_candidates_by_dn": {},
            "default_weld_type": "",
        }
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
        self._load_classes()

    # ═════════════════════════════════════════════════════
    # Detail panel
    # ═════════════════════════════════════════════════════
    def _on_class_selected(self, class_code: str) -> None:
        if not class_code or class_code not in self._rules:
            return
        self._commit_current()
        rule = self._rules[class_code]

        # material candidates
        mats = rule.get("material_candidates", [])
        self.mat_edit.setText(", ".join(mats))

        # weld type
        self.weld_type_edit.setText(
            str(rule.get("default_weld_type", ""))
        )

        # thk by dn
        by_dn = rule.get("thk_candidates_by_dn", {})
        self.thk_table.setRowCount(0)
        for dn_key in sorted(
            by_dn.keys(),
            key=lambda x: int(x) if x.isdigit() else 0,
        ):
            row = self.thk_table.rowCount()
            self.thk_table.insertRow(row)
            self.thk_table.setItem(
                row, 0, QTableWidgetItem(dn_key)
            )
            self.thk_table.setItem(
                row, 1,
                QTableWidgetItem(", ".join(by_dn[dn_key])),
            )

    def _commit_current(self) -> None:
        """Save current detail edits back into self._rules."""
        prev = None
        for i in range(self.class_list.count()):
            item = self.class_list.item(i)
            if item and item.isSelected():
                prev = item.text()
                break
        if not prev or prev not in self._rules:
            return
        self._rules[prev] = self._build_rule_from_ui()

    def _build_rule_from_ui(self) -> Dict[str, Any]:
        mats = [
            m.strip()
            for m in self.mat_edit.text().split(",")
            if m.strip()
        ]
        by_dn: Dict[str, List[str]] = {}
        for r in range(self.thk_table.rowCount()):
            dn_item = self.thk_table.item(r, 0)
            thk_item = self.thk_table.item(r, 1)
            if not dn_item:
                continue
            dn_key = dn_item.text().strip()
            thks = (
                [t.strip() for t in thk_item.text().split(",") if t.strip()]
                if thk_item
                else []
            )
            if dn_key:
                by_dn[dn_key] = thks
        return {
            "material_candidates": mats,
            "thk_candidates_by_dn": by_dn,
            "default_weld_type": self.weld_type_edit.text().strip(),
        }

    def _add_dn_row(self) -> None:
        row = self.thk_table.rowCount()
        self.thk_table.insertRow(row)
        self.thk_table.setItem(row, 0, QTableWidgetItem(""))
        self.thk_table.setItem(row, 1, QTableWidgetItem(""))

    def _del_dn_row(self) -> None:
        row = self.thk_table.currentRow()
        if row >= 0:
            self.thk_table.removeRow(row)

    # ═════════════════════════════════════════════════════
    # Save
    # ═════════════════════════════════════════════════════
    def _save(self) -> None:
        self._commit_current()
        try:
            from src.rules import normalize_rules
            cleaned = normalize_rules(self._rules)
            self.ctrl.save_spec_rules(cleaned)
            self._rules = dict(cleaned)
            QMessageBox.information(
                self, "完成", "規則已儲存"
            )
            if self.on_saved:
                self.on_saved()
        except Exception as exc:
            QMessageBox.critical(
                self, "錯誤", str(exc)
            )
