"""Spec Rules editor — Piping Material Classification.

Left: class list.  Right: tabbed detail (基本定義 / 連接 / 檢驗 / 管材&壁厚).
"""
from __future__ import annotations

from typing import Any, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
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
        self._common = dict(self.ctrl.common_values)

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
        self.default_mat_edit = QComboBox()
        self.default_mat_edit.setEditable(True)
        dm_vals = self._common.get(
            "default_material", []
        )
        self.default_mat_edit.addItems(dm_vals)
        self.default_mat_edit.setCurrentText("")
        mg.addWidget(self.default_mat_edit, 0, 1)
        mg.addWidget(
            QLabel("材質候選 (逗號分隔):"), 1, 0
        )
        self.mat_edit = QLineEdit()
        mg.addWidget(self.mat_edit, 1, 1)
        t4.addWidget(mat_group)

        # ── DN × Schedule checkbox matrix ────────
        thk_group = QGroupBox(
            "壁厚候選 — DN × Schedule 矩陣"
        )
        tg = QVBoxLayout(thk_group)

        # quick-fill toolbar
        qf = QHBoxLayout()
        qf.addWidget(QLabel("快填:"))

        btn_small_80 = QPushButton(
            "小口徑(≤40) S-80"
        )
        btn_small_80.clicked.connect(
            lambda: self._quick_fill(
                max_dn=40, schedules=["S-80"]
            )
        )
        qf.addWidget(btn_small_80)

        btn_large_40 = QPushButton(
            "大口徑(≥50) S-40"
        )
        btn_large_40.clicked.connect(
            lambda: self._quick_fill(
                min_dn=50, schedules=["S-40"]
            )
        )
        qf.addWidget(btn_large_40)

        btn_all_10s = QPushButton("全部 S-10S")
        btn_all_10s.clicked.connect(
            lambda: self._quick_fill(
                schedules=["S-10S"]
            )
        )
        qf.addWidget(btn_all_10s)

        btn_clear = QPushButton("清除全部")
        btn_clear.clicked.connect(self._clear_matrix)
        qf.addWidget(btn_clear)

        qf.addStretch()
        tg.addLayout(qf)

        # scrollable matrix
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        matrix_widget = QWidget()
        self._matrix_grid = QGridLayout(matrix_widget)
        self._matrix_grid.setSpacing(2)

        self._dn_list: List[str] = self._common.get(
            "standard_dn", []
        )
        self._sch_list: List[str] = self._common.get(
            "standard_schedule", []
        )
        # {(dn, sch): QCheckBox}
        self._matrix_cbs: Dict[
            tuple, QCheckBox
        ] = {}

        # header row — schedule labels
        for ci, sch in enumerate(self._sch_list):
            lbl = QLabel(sch)
            lbl.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
            lbl.setStyleSheet(
                "font-size: 11px; font-weight: bold;"
            )
            self._matrix_grid.addWidget(
                lbl, 0, ci + 1
            )

        # rows — DN + checkboxes
        for ri, dn in enumerate(self._dn_list):
            dn_lbl = QLabel(f"DN {dn}")
            dn_lbl.setStyleSheet(
                "font-weight: bold; min-width: 50px;"
            )
            self._matrix_grid.addWidget(
                dn_lbl, ri + 1, 0
            )
            for ci, sch in enumerate(self._sch_list):
                cb = QCheckBox()
                self._matrix_cbs[(dn, sch)] = cb
                self._matrix_grid.addWidget(
                    cb, ri + 1, ci + 1,
                    Qt.AlignmentFlag.AlignCenter,
                )

        scroll.setWidget(matrix_widget)
        tg.addWidget(scroll, stretch=1)
        t4.addWidget(thk_group, stretch=1)

        self.tabs.addTab(tab4, "管材 & 壁厚")

        # ── Tab 5: 支管表 (Branch Table) ─────────
        tab5 = QWidget()
        t5 = QVBoxLayout(tab5)

        # quick-fill toolbar
        bf = QHBoxLayout()
        bf.addWidget(QLabel("快填:"))

        btn_auto_br = QPushButton("自動填充 (依DN門檻)")
        btn_auto_br.setToolTip(
            "對角線→等徑三通, 小口徑→SOC/ETE/RTE, "
            "大口徑→RWE/TER/TEE/RPA"
        )
        btn_auto_br.clicked.connect(self._branch_auto_fill)
        bf.addWidget(btn_auto_br)

        btn_clear_br = QPushButton("清除全部")
        btn_clear_br.clicked.connect(self._branch_clear)
        bf.addWidget(btn_clear_br)

        bf.addStretch()
        t5.addLayout(bf)

        # scrollable DN × DN matrix (QComboBox cells)
        br_scroll = QScrollArea()
        br_scroll.setWidgetResizable(True)
        br_matrix_w = QWidget()
        self._br_grid = QGridLayout(br_matrix_w)
        self._br_grid.setSpacing(1)

        self._br_fitting_types: List[str] = (
            [""] + self._common.get(
                "branch_fitting_types",
                ["SOC", "ETE", "RTE", "RWE",
                 "TER", "TEE", "RPA"],
            )
        )
        # {(header_dn, branch_dn): QComboBox}
        self._br_cbs: Dict[tuple, QComboBox] = {}

        # corner label
        corner = QLabel("H \\ B")
        corner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner.setStyleSheet(
            "font-size: 10px; font-weight: bold;"
        )
        self._br_grid.addWidget(corner, 0, 0)

        # header row — branch DN labels
        for ci, bdn in enumerate(self._dn_list):
            lbl = QLabel(bdn)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "font-size: 10px; font-weight: bold;"
            )
            lbl.setFixedWidth(48)
            self._br_grid.addWidget(lbl, 0, ci + 1)

        # rows — header DN + combo cells
        for ri, hdn in enumerate(self._dn_list):
            h_lbl = QLabel(hdn)
            h_lbl.setStyleSheet(
                "font-weight: bold; min-width: 36px;"
            )
            self._br_grid.addWidget(h_lbl, ri + 1, 0)
            hdn_int = int(hdn)
            for ci, bdn in enumerate(self._dn_list):
                bdn_int = int(bdn)
                if bdn_int > hdn_int:
                    # branch > header → invalid cell
                    continue
                cb = QComboBox()
                cb.setFixedWidth(48)
                cb.addItems(self._br_fitting_types)
                cb.setStyleSheet("font-size: 10px;")
                self._br_cbs[(hdn, bdn)] = cb
                self._br_grid.addWidget(
                    cb, ri + 1, ci + 1
                )

        br_scroll.setWidget(br_matrix_w)
        t5.addWidget(br_scroll, stretch=1)

        self.tabs.addTab(tab5, "支管表")

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
                w: QWidget = QCheckBox()
                grid.addWidget(w, r, c * cols + 1)
            elif key in self._common:
                w = QComboBox()
                w.setEditable(True)
                w.addItems(self._common[key])
                w.setCurrentText("")
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
            elif isinstance(w, QComboBox):
                w.setCurrentText(
                    str(val) if val else ""
                )
            else:
                w.setText(str(val) if val else "")

        # material tab
        self.default_mat_edit.setCurrentText(
            str(rule.get("default_material", ""))
        )
        mats = rule.get("material_candidates", [])
        self.mat_edit.setText(", ".join(mats))

        # thk — checkbox matrix
        self._load_matrix(
            rule.get("thk_candidates_by_dn", {})
        )

        # branch table
        self._load_branch_table(
            rule.get("branch_table", {})
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
            elif isinstance(w, QComboBox):
                spec[key] = w.currentText().strip()
            else:
                spec[key] = w.text().strip()

        # material
        spec["default_material"] = (
            self.default_mat_edit.currentText().strip()
        )
        spec["material_candidates"] = [
            m.strip()
            for m in self.mat_edit.text().split(",")
            if m.strip()
        ]

        # thk by dn — from checkbox matrix
        spec["thk_candidates_by_dn"] = (
            self._read_matrix()
        )

        # preserve thk_rules if they existed
        old = self._rules.get(self._current_class, {})
        spec["thk_rules"] = old.get("thk_rules", [])

        # branch table — from combo matrix
        spec["branch_table"] = self._read_branch_table()

        return spec

    # ── matrix helpers ───────────────────────────
    def _load_matrix(
        self, by_dn: Dict[str, List[str]]
    ) -> None:
        """Set checkbox states from thk_candidates_by_dn."""
        # clear all
        for cb in self._matrix_cbs.values():
            cb.setChecked(False)
        # check matching
        for dn, schs in by_dn.items():
            for sch in schs:
                key = (dn, sch)
                if key in self._matrix_cbs:
                    self._matrix_cbs[key].setChecked(True)

    def _read_matrix(self) -> Dict[str, List[str]]:
        """Read checkbox states → thk_candidates_by_dn."""
        by_dn: Dict[str, List[str]] = {}
        for dn in self._dn_list:
            checked = [
                sch for sch in self._sch_list
                if self._matrix_cbs.get(
                    (dn, sch), None
                ) and self._matrix_cbs[
                    (dn, sch)
                ].isChecked()
            ]
            if checked:
                by_dn[dn] = checked
        return by_dn

    def _quick_fill(
        self,
        schedules: List[str],
        min_dn: int = 0,
        max_dn: int = 9999,
    ) -> None:
        """Check specified schedules for DN in range."""
        for dn in self._dn_list:
            try:
                dn_int = int(dn)
            except ValueError:
                continue
            if min_dn <= dn_int <= max_dn:
                for sch in schedules:
                    key = (dn, sch)
                    if key in self._matrix_cbs:
                        self._matrix_cbs[
                            key
                        ].setChecked(True)

    def _clear_matrix(self) -> None:
        for cb in self._matrix_cbs.values():
            cb.setChecked(False)

    # ── branch table helpers ─────────────────────
    def _load_branch_table(
        self, bt: Dict[str, Dict[str, str]]
    ) -> None:
        """Set combo values from branch_table dict."""
        for cb in self._br_cbs.values():
            cb.setCurrentIndex(0)  # empty
        for hdn, cols in bt.items():
            for bdn, ft in cols.items():
                key = (hdn, bdn)
                if key in self._br_cbs:
                    idx = self._br_cbs[key].findText(
                        ft.upper()
                    )
                    if idx >= 0:
                        self._br_cbs[key].setCurrentIndex(idx)

    def _read_branch_table(
        self,
    ) -> Dict[str, Dict[str, str]]:
        """Read combo states → branch_table dict."""
        bt: Dict[str, Dict[str, str]] = {}
        for (hdn, bdn), cb in self._br_cbs.items():
            ft = cb.currentText().strip()
            if ft:
                bt.setdefault(hdn, {})[bdn] = ft
        return bt

    def _branch_auto_fill(self) -> None:
        """Auto-fill branch table using standard logic.

        - diagonal (H==B) → equal tee (ETE if ≤40, TEE if >40)
        - small bore off-diagonal (H≤40, B<H) → SOC
        - large bore off-diagonal: use TER/RWE/RPA heuristics
        """
        # read dn_threshold_bw from current class
        thr = 50  # default
        if self._current_class:
            rule = self._rules.get(
                self._current_class, {}
            )
            try:
                thr = int(
                    str(
                        rule.get("dn_threshold_bw", "50")
                    ).strip()
                )
            except ValueError:
                pass

        for (hdn, bdn), cb in self._br_cbs.items():
            h = int(hdn)
            b = int(bdn)
            if b > h:
                continue

            if h == b:
                # diagonal → equal tee
                ft = "ETE" if h < thr else "TEE"
            elif h < thr:
                # small bore → sockolet
                ft = "SOC"
            else:
                # large bore off-diagonal
                if b < thr:
                    # branch is small bore
                    ft = "SOC"
                elif h == b:
                    ft = "TEE"
                elif b >= h * 0.5:
                    ft = "TER"
                else:
                    ft = "RWE"
            idx = cb.findText(ft)
            if idx >= 0:
                cb.setCurrentIndex(idx)

    def _branch_clear(self) -> None:
        for cb in self._br_cbs.values():
            cb.setCurrentIndex(0)

    # ════════════════════════════════════════════════════
    # Combo refresh (after new values merged)
    # ════════════════════════════════════════════════════
    def _refresh_combos(self) -> None:
        """Update all editable combos with latest common
        values, keeping current text intact."""
        for key, w in self._scalar_widgets.items():
            if isinstance(w, QComboBox):
                cur = w.currentText()
                w.clear()
                w.addItems(
                    self._common.get(key, [])
                )
                w.setCurrentText(cur)
        # default_material combo
        cur = self.default_mat_edit.currentText()
        self.default_mat_edit.clear()
        self.default_mat_edit.addItems(
            self._common.get("default_material", [])
        )
        self.default_mat_edit.setCurrentText(cur)

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
            # Refresh common values (may have new entries)
            self._common = dict(
                self.ctrl.common_values
            )
            self._refresh_combos()
            QMessageBox.information(
                self, "完成", "規則已儲存"
            )
            if self.on_saved:
                self.on_saved()
        except Exception as exc:
            QMessageBox.critical(
                self, "錯誤", str(exc)
            )
