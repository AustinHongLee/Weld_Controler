"""WPS / PQR / Welder qualification management UI."""
from __future__ import annotations

from typing import Any, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
from src.welding_engine import (
    PQR,
    WPS,
    WelderQualification,
    PROCESS_CATALOG,
)


# ═════════════════════════════════════════════════════════
# Field definitions for form builders
# ═════════════════════════════════════════════════════════

PQR_FIELDS = [
    ("pqr_no",          "PQR 編號",      "text"),
    ("revision",        "版次",          "text"),
    ("created_date",    "建立日期",      "text"),
    ("company",         "公司",          "text"),
    ("project",         "專案",          "text"),
    ("prepared_by",     "編製",          "text"),
    ("approved_by",     "核准",          "text"),
    ("base_metal_spec", "母材規範",      "text"),
    ("p_no",            "P-No",          "text"),
    ("test_thickness_mm", "試件厚度 mm", "float"),
    ("test_diameter_mm",  "試件管徑 mm", "float"),
    ("process_root",    "Root 焊程",     "process"),
    ("process_fill",    "Fill 焊程",     "process"),
    ("process_cap",     "Cap 焊程",      "process"),
    ("filler_root",     "Root 焊材",     "text"),
    ("filler_fill",     "Fill 焊材",     "text"),
    ("filler_cap",      "Cap 焊材",      "text"),
    ("position_tested", "試驗姿勢",      "position"),
    ("vt",  "VT",      "result"),
    ("rt",  "RT",      "result"),
    ("ut",  "UT",      "result"),
    ("bend", "Bend",   "result"),
    ("tensile", "Tensile", "result"),
    ("impact",  "Impact",  "result"),
    ("remarks", "備註",    "text"),
]

WPS_FIELDS = [
    ("wps_no",            "WPS 編號",      "text"),
    ("revision",          "版次",          "text"),
    ("created_date",      "建立日期",      "text"),
    ("company",           "公司",          "text"),
    ("project",           "專案",          "text"),
    ("prepared_by",       "編製",          "text"),
    ("approved_by",       "核准",          "text"),
    ("supporting_pqr_no", "支持 PQR",      "pqr_list"),
    ("p_no",              "P-No",          "text"),
    ("thickness_min_mm",  "厚度下限 mm",   "float"),
    ("thickness_max_mm",  "厚度上限 mm",   "float"),
    ("diameter_min_mm",   "管徑下限 mm",   "float"),
    ("diameter_max_mm",   "管徑上限 mm (0=無限)", "float"),
    ("process_root",      "Root 焊程",     "process"),
    ("process_fill",      "Fill 焊程",     "process"),
    ("process_cap",       "Cap 焊程",      "process"),
    ("preheat_required",  "需預熱",        "bool"),
    ("pwht_required",     "需退火",        "bool"),
    ("notes",             "備註",          "text"),
]

WELDER_FIELDS = [
    ("welder_no",         "焊工編號",      "text"),
    ("welder_name",       "焊工姓名",      "text"),
    ("company",           "公司",          "text"),
    ("id_no",             "身份證/護照",    "text"),
    ("supporting_wps_no", "支持 WPS",      "wps_list"),
    ("p_no",              "P-No",          "text"),
    ("thickness_min_mm",  "厚度下限 mm",   "float"),
    ("thickness_max_mm",  "厚度上限 mm",   "float"),
    ("test_date",         "考試日期",      "text"),
    ("expiry_date",       "到期日期",      "text"),
    ("status",            "狀態",          "status"),
    ("remarks",           "備註",          "text"),
]

# Summary columns for list tables
PQR_SUMMARY = ["pqr_no", "p_no", "base_metal_spec",
               "process_root", "position_tested"]
WPS_SUMMARY = ["wps_no", "p_no", "supporting_pqr_no",
               "process_root", "thickness_min_mm", "thickness_max_mm"]
WELDER_SUMMARY = ["welder_no", "welder_name", "p_no",
                  "status", "expiry_date"]


# ═════════════════════════════════════════════════════════
# Main Widget
# ═════════════════════════════════════════════════════════

class WeldingQualWidget(QWidget):
    """Tabbed manager for PQR / WPS / Welder qualifications."""

    def __init__(
        self, controller: AppController, parent=None
    ) -> None:
        super().__init__(parent)
        self.ctrl = controller
        self.reg = controller.welding_registry

        outer = QVBoxLayout(self)

        self.tabs = QTabWidget()

        # ── Sub-tab 1: PQR ───────────────────────────
        self.pqr_panel = _RecordPanel(
            ctrl=self.ctrl,
            title="PQR",
            fields=PQR_FIELDS,
            summary_keys=PQR_SUMMARY,
            get_list=lambda: self.reg.list_pqr_nos(),
            get_record=lambda k: (self.reg.get_pqr(k).to_dict()
                                  if self.reg.get_pqr(k) else {}),
            save_record=self._save_pqr,
            delete_record=self._delete_pqr,
        )
        self.tabs.addTab(self.pqr_panel, "PQR")

        # ── Sub-tab 2: WPS ───────────────────────────
        self.wps_panel = _RecordPanel(
            ctrl=self.ctrl,
            title="WPS",
            fields=WPS_FIELDS,
            summary_keys=WPS_SUMMARY,
            get_list=lambda: self.reg.list_wps_nos(),
            get_record=lambda k: (self.reg.get_wps(k).to_dict()
                                  if self.reg.get_wps(k) else {}),
            save_record=self._save_wps,
            delete_record=self._delete_wps,
        )
        self.tabs.addTab(self.wps_panel, "WPS")

        # ── Sub-tab 3: Welder ────────────────────────
        self.welder_panel = _RecordPanel(
            ctrl=self.ctrl,
            title="焊工資格",
            fields=WELDER_FIELDS,
            summary_keys=WELDER_SUMMARY,
            get_list=lambda: self.reg.list_welder_nos(),
            get_record=lambda k: (self.reg.get_welder(k).to_dict()
                                  if self.reg.get_welder(k) else {}),
            save_record=self._save_welder,
            delete_record=self._delete_welder,
        )
        self.tabs.addTab(self.welder_panel, "焊工資格")

        # ── Sub-tab 4: Validation ────────────────────
        val_tab = QWidget()
        vl = QVBoxLayout(val_tab)
        vl.addWidget(QLabel(
            "選擇 WPS 和 PQR 驗證 WPS 是否在 PQR 認證範圍內"
        ))
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("WPS:"))
        self.val_wps_combo = QComboBox()
        sel_row.addWidget(self.val_wps_combo)
        sel_row.addWidget(QLabel("PQR:"))
        self.val_pqr_combo = QComboBox()
        sel_row.addWidget(self.val_pqr_combo)
        val_btn = QPushButton("驗證")
        val_btn.clicked.connect(self._run_validation)
        sel_row.addWidget(val_btn)
        sel_row.addStretch()
        vl.addLayout(sel_row)

        self.val_result = QLabel("")
        self.val_result.setWordWrap(True)
        self.val_result.setStyleSheet("font-size: 13px;")
        vl.addWidget(self.val_result, stretch=1)
        self.tabs.addTab(val_tab, "驗證")

        outer.addWidget(self.tabs)

        # Listen for tab changes to refresh combos
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # ── Save callbacks ───────────────────────────────
    def _save_pqr(self, data: Dict[str, Any]) -> str:
        pqr_no = str(data.get("pqr_no", "")).strip()
        if not pqr_no:
            return "PQR 編號不可為空"
        pqr = PQR.from_dict(data)
        # Auto-derive envelope
        self.ctrl.weld_engine.derive_pqr_envelope(pqr)
        self.reg.add_pqr(pqr)
        self.ctrl.save_welding_registry()
        return ""

    def _delete_pqr(self, key: str) -> None:
        self.reg.delete_pqr(key)
        self.ctrl.save_welding_registry()

    def _save_wps(self, data: Dict[str, Any]) -> str:
        wps_no = str(data.get("wps_no", "")).strip()
        if not wps_no:
            return "WPS 編號不可為空"
        wps = WPS.from_dict(data)
        self.reg.add_wps(wps)
        self.ctrl.save_welding_registry()
        return ""

    def _delete_wps(self, key: str) -> None:
        self.reg.delete_wps(key)
        self.ctrl.save_welding_registry()

    def _save_welder(self, data: Dict[str, Any]) -> str:
        no = str(data.get("welder_no", "")).strip()
        if not no:
            return "焊工編號不可為空"
        w = WelderQualification.from_dict(data)
        self.reg.add_welder(w)
        self.ctrl.save_welding_registry()
        return ""

    def _delete_welder(self, key: str) -> None:
        self.reg.delete_welder(key)
        self.ctrl.save_welding_registry()

    # ── Validation ───────────────────────────────────
    def _on_tab_changed(self, idx: int) -> None:
        if idx == 3:  # validation tab
            self.val_wps_combo.clear()
            self.val_wps_combo.addItems(self.reg.list_wps_nos())
            self.val_pqr_combo.clear()
            self.val_pqr_combo.addItems(self.reg.list_pqr_nos())

    def _run_validation(self) -> None:
        wps_no = self.val_wps_combo.currentText()
        pqr_no = self.val_pqr_combo.currentText()
        if not wps_no or not pqr_no:
            self.val_result.setText("請選擇 WPS 和 PQR")
            return
        wps = self.reg.get_wps(wps_no)
        pqr = self.reg.get_pqr(pqr_no)
        if not wps or not pqr:
            self.val_result.setText("找不到記錄")
            return
        ok, errors = self.ctrl.weld_engine.validate_wps_within_pqr(
            wps, pqr
        )
        if ok:
            self.val_result.setStyleSheet(
                "font-size: 13px; color: green;"
            )
            self.val_result.setText(
                f"✓ WPS {wps_no} 在 PQR {pqr_no} 認證範圍內\n\n"
                f"PQR 認證厚度: {pqr.qualified_thickness_min_mm} ~ "
                f"{pqr.qualified_thickness_max_mm} mm\n"
                f"PQR 認證姿勢: {', '.join(pqr.qualified_positions)}"
            )
        else:
            self.val_result.setStyleSheet(
                "font-size: 13px; color: red;"
            )
            self.val_result.setText(
                "✗ 驗證失敗:\n\n" + "\n".join(
                    f"  • {e}" for e in errors
                )
            )


# ═════════════════════════════════════════════════════════
# Generic Record Panel (reused for PQR / WPS / Welder)
# ═════════════════════════════════════════════════════════

class _RecordPanel(QWidget):
    """Left list + right form for any record type."""

    def __init__(
        self,
        ctrl: AppController,
        title: str,
        fields: List[tuple],
        summary_keys: List[str],
        get_list,
        get_record,
        save_record,
        delete_record,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl
        self.title = title
        self.fields = fields
        self.summary_keys = summary_keys
        self._get_list = get_list
        self._get_record = get_record
        self._save_record = save_record
        self._delete_record = delete_record
        self._current_key: str = ""

        outer = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── LEFT: summary table ──────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        ll.addWidget(QLabel(f"{title} 列表"))

        # Summary headers from fields
        self._sum_headers = []
        for sk in summary_keys:
            for fkey, fhdr, _ in fields:
                if fkey == sk:
                    self._sum_headers.append(fhdr)
                    break
            else:
                self._sum_headers.append(sk)

        self.list_table = QTableWidget(0, len(summary_keys))
        self.list_table.setHorizontalHeaderLabels(self._sum_headers)
        hdr = self.list_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.list_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.list_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.list_table.currentCellChanged.connect(
            self._on_list_select
        )
        ll.addWidget(self.list_table)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("新增")
        new_btn.clicked.connect(self._new_record)
        btn_row.addWidget(new_btn)
        del_btn = QPushButton("刪除")
        del_btn.clicked.connect(self._del_record)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        ll.addLayout(btn_row)

        splitter.addWidget(left)

        # ── RIGHT: detail form ───────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)

        self.detail_label = QLabel(f"（請選擇 {title}）")
        self.detail_label.setStyleSheet(
            "font-size: 14px; font-weight: bold;"
        )
        rl.addWidget(self.detail_label)

        form_grid = QGridLayout()
        self._form_widgets: Dict[str, QWidget] = {}

        row = 0
        col_pair = 0
        for fkey, fhdr, ftype in fields:
            # 2 columns of label+widget pairs
            form_grid.addWidget(
                QLabel(f"{fhdr}:"), row, col_pair * 2
            )
            w = self._make_widget(fkey, ftype)
            form_grid.addWidget(w, row, col_pair * 2 + 1)
            self._form_widgets[fkey] = w
            col_pair += 1
            if col_pair >= 2:
                col_pair = 0
                row += 1
        if col_pair != 0:
            row += 1

        rl.addLayout(form_grid)

        # Envelope display (for PQR)
        self.envelope_label = QLabel("")
        self.envelope_label.setWordWrap(True)
        self.envelope_label.setStyleSheet(
            "color: #555; font-size: 12px; margin-top: 8px;"
        )
        rl.addWidget(self.envelope_label)

        save_btn = QPushButton(f"儲存 {title}")
        save_btn.setMinimumHeight(36)
        save_btn.clicked.connect(self._save)
        rl.addWidget(save_btn)

        rl.addStretch()
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        outer.addWidget(splitter)
        self._refresh_list()

    def _make_widget(self, key: str, ftype: str) -> QWidget:
        if ftype == "bool":
            return QCheckBox()
        elif ftype == "process":
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems([""] + list(PROCESS_CATALOG.keys()))
            return cb
        elif ftype == "position":
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(["", "1G", "2G", "5G", "6G", "6GR"])
            return cb
        elif ftype == "result":
            cb = QComboBox()
            cb.addItems(["NA", "PASS", "FAIL"])
            return cb
        elif ftype == "status":
            cb = QComboBox()
            cb.addItems(["有效", "過期", "暫停"])
            return cb
        elif ftype == "pqr_list":
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(
                [""] + self.ctrl.welding_registry.list_pqr_nos()
            )
            return cb
        elif ftype == "wps_list":
            cb = QComboBox()
            cb.setEditable(True)
            cb.addItems(
                [""] + self.ctrl.welding_registry.list_wps_nos()
            )
            return cb
        else:
            return QLineEdit()

    def _refresh_list(self) -> None:
        keys = self._get_list()
        self.list_table.setRowCount(0)
        for k in keys:
            rec = self._get_record(k)
            row = self.list_table.rowCount()
            self.list_table.insertRow(row)
            for ci, sk in enumerate(self.summary_keys):
                val = str(rec.get(sk, ""))
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                self.list_table.setItem(row, ci, item)

    def _on_list_select(
        self, row: int, _c: int, _pr: int, _pc: int
    ) -> None:
        if row < 0:
            self._current_key = ""
            return
        keys = self._get_list()
        if row >= len(keys):
            return
        key = keys[row]
        self._current_key = key
        rec = self._get_record(key)
        self.detail_label.setText(f"{self.title}: {key}")
        self._populate_form(rec)

    def _populate_form(self, rec: Dict[str, Any]) -> None:
        for fkey, _, ftype in self.fields:
            w = self._form_widgets.get(fkey)
            if not w:
                continue
            val = rec.get(fkey, "")
            if isinstance(w, QCheckBox):
                w.setChecked(bool(val))
            elif isinstance(w, QComboBox):
                w.setCurrentText(str(val) if val else "")
            elif isinstance(w, QLineEdit):
                w.setText(str(val) if val else "")

        # Show envelope info for PQR
        env_parts = []
        for ek, elbl in [
            ("qualified_thickness_min_mm", "認證厚度下限"),
            ("qualified_thickness_max_mm", "認證厚度上限"),
            ("qualified_diameter_min_mm", "認證管徑下限"),
            ("qualified_diameter_max_mm", "認證管徑上限"),
        ]:
            v = rec.get(ek)
            if v:
                env_parts.append(f"{elbl}: {v} mm")
        qp = rec.get("qualified_positions", [])
        if qp:
            env_parts.append(f"認證姿勢: {', '.join(qp)}")
        self.envelope_label.setText(
            "  |  ".join(env_parts) if env_parts else ""
        )

    def _read_form(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for fkey, _, ftype in self.fields:
            w = self._form_widgets.get(fkey)
            if not w:
                continue
            if isinstance(w, QCheckBox):
                data[fkey] = w.isChecked()
            elif isinstance(w, QComboBox):
                data[fkey] = w.currentText().strip()
            elif isinstance(w, QLineEdit):
                data[fkey] = w.text().strip()
        return data

    def _new_record(self) -> None:
        # Clear form
        for fkey, _, ftype in self.fields:
            w = self._form_widgets.get(fkey)
            if isinstance(w, QCheckBox):
                w.setChecked(False)
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
            elif isinstance(w, QLineEdit):
                w.clear()
        self._current_key = ""
        self.detail_label.setText(f"新增 {self.title}")
        self.envelope_label.setText("")
        # Refresh PQR/WPS combo lists
        for fkey, _, ftype in self.fields:
            if ftype in ("pqr_list", "wps_list"):
                w = self._form_widgets[fkey]
                if isinstance(w, QComboBox):
                    cur = w.currentText()
                    w.clear()
                    if ftype == "pqr_list":
                        w.addItems(
                            [""] + self.ctrl.welding_registry.list_pqr_nos()
                        )
                    else:
                        w.addItems(
                            [""] + self.ctrl.welding_registry.list_wps_nos()
                        )
                    w.setCurrentText(cur)

    def _save(self) -> None:
        data = self._read_form()
        err = self._save_record(data)
        if err:
            QMessageBox.warning(self, "錯誤", err)
            return
        self._refresh_list()
        QMessageBox.information(self, "完成", f"{self.title} 已儲存")

    def _del_record(self) -> None:
        if not self._current_key:
            QMessageBox.warning(self, "提示", f"請先選擇 {self.title}")
            return
        ans = QMessageBox.question(
            self, "確認",
            f"確定刪除 {self._current_key}？",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._delete_record(self._current_key)
        self._current_key = ""
        self._refresh_list()
