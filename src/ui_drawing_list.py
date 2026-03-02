"""Drawing List tab — clean table + toolbar.

Import / Edit / Revision 皆以獨立對話框呈現，不佔主畫面版面。
"""
from __future__ import annotations

import traceback
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QMenu,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.controller import AppController
from src.models import DRAWING_FIELDS, REVISION_FIELDS
from src.ui_parser_settings import ParserSettingsDialog

# ─── Summary table columns ──────────────────────────────
_SUMMARY_KEYS = [
    "series_no", "dwg_no", "sheet_no",
    "final_rev", "final_rev_date",
    "dn", "system", "pipe_class",
    "material", "dwg_status", "remark",
]
_SUMMARY_HEADERS = {
    "series_no": "流水號",
    "dwg_no": "DWG NO",
    "sheet_no": "SH'T NO",
    "final_rev": "最終版版次",
    "final_rev_date": "最終版日期",
    "dn": "尺寸",
    "system": "系統",
    "pipe_class": "級數",
    "material": "管線材質",
    "dwg_status": "圖面狀態",
    "remark": "備註",
}


# ═════════════════════════════════════════════════════════
# DrawingListTab — main tab
# ═════════════════════════════════════════════════════════
class DrawingListTab(QWidget):
    def __init__(
        self,
        ctrl: AppController,
        on_open_welds: Callable[[int], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl
        self.on_open_welds = on_open_welds

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── toolbar ──────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("專案:"))
        self.project_name_edit = QLineEdit(
            self.ctrl.project.meta.get(
                "project_name", ""
            )
        )
        self.project_name_edit.setPlaceholderText("專案名稱")
        self.project_name_edit.setMinimumWidth(180)
        self.project_name_edit.editingFinished.connect(
            self._on_project_name_changed
        )
        toolbar.addWidget(self.project_name_edit)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #4e4e6e;")
        toolbar.addWidget(sep1)

        toolbar.addWidget(QLabel("解析:"))
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(
            list(self.ctrl.parser_profiles.keys())
        )
        self.profile_combo.setCurrentText(
            self.ctrl.project.meta.get(
                "parser_profile", "default"
            )
        )
        self.profile_combo.currentTextChanged.connect(
            self._on_profile_changed
        )
        toolbar.addWidget(self.profile_combo)

        settings_btn = QPushButton("⚙ 解析設定")
        settings_btn.clicked.connect(
            self._open_parser_settings
        )
        toolbar.addWidget(settings_btn)

        reparse_btn = QPushButton("🔄 重新解析")
        reparse_btn.clicked.connect(self._reparse_all)
        toolbar.addWidget(reparse_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ── action buttons ───────────────────────────────
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        import_btn = QPushButton("📥 匯入 DWG 清單")
        import_btn.clicked.connect(
            self._open_import_dialog
        )
        btn_bar.addWidget(import_btn)

        add_btn = QPushButton("➕ 新增 Drawing")
        add_btn.clicked.connect(self._add_empty_drawing)
        btn_bar.addWidget(add_btn)

        btn_bar.addStretch()

        # Status indicator
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: #9090a8; font-size: 12px;"
        )
        btn_bar.addWidget(self.status_label)

        btn_bar.addStretch()

        del_btn = QPushButton("🗑 刪除選取")
        del_btn.setStyleSheet(
            "QPushButton { background-color: #f06070; }"
            "QPushButton:hover { background-color: #ff7080; }"
        )
        del_btn.clicked.connect(self._delete_selected)
        btn_bar.addWidget(del_btn)

        layout.addLayout(btn_bar)

        # ── table ────────────────────────────────────────
        cols = len(_SUMMARY_KEYS)
        self.table = QTableWidget(0, cols)
        self.table.setHorizontalHeaderLabels(
            [_SUMMARY_HEADERS[k] for k in _SUMMARY_KEYS]
        )
        self.table.setAlternatingRowColors(True)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        hdr.setStretchLastSection(True)
        # Default column widths
        _COL_WIDTHS = {
            "series_no": 60, "dwg_no": 200,
            "sheet_no": 55, "final_rev": 70,
            "final_rev_date": 90, "dn": 50,
            "system": 60, "pipe_class": 60,
            "material": 80, "dwg_status": 70,
            "remark": 150,
        }
        for ci, key in enumerate(_SUMMARY_KEYS):
            w = _COL_WIDTHS.get(key, 80)
            self.table.setColumnWidth(ci, w)

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.table.customContextMenuRequested.connect(
            self._show_context_menu
        )
        self.table.doubleClicked.connect(
            self._on_double_click
        )
        layout.addWidget(self.table, stretch=1)

        self._refresh_table()

    # ── helpers ──────────────────────────────────────────
    def _selected_row(self) -> Optional[int]:
        sel = self.table.selectionModel().selectedRows()
        if sel:
            return sel[0].row()
        return None

    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        drawings = self.ctrl.get_drawings()
        for dw in drawings:
            row = self.table.rowCount()
            self.table.insertRow(row)
            status = dw.get("dwg_status") or ""
            for col, key in enumerate(_SUMMARY_KEYS):
                val = dw.get(key)
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                # Status badge coloring
                if key == "dwg_status":
                    if status == "關閉":
                        item.setForeground(QColor("#f06070"))
                    else:
                        item.setForeground(QColor("#43d9a0"))
                # Dim empty cells
                if not val:
                    item.setForeground(QColor("#555570"))
                    item.setText("—")
                self.table.setItem(row, col, item)
        # Update status bar
        total = len(drawings)
        active = sum(
            1 for d in drawings
            if (d.get("dwg_status") or "啟用") != "關閉"
        )
        self.status_label.setText(
            f"共 {total} 筆 Drawing  ｜  "
            f"🟢 啟用 {active}  ｜  "
            f"🔴 關閉 {total - active}"
        )

    # ── toolbar signals ──────────────────────────────────
    def _on_project_name_changed(self) -> None:
        self.ctrl.project.meta["project_name"] = (
            self.project_name_edit.text().strip()
        )
        self.ctrl.save()

    def _on_profile_changed(self, name: str) -> None:
        self.ctrl.project.meta["parser_profile"] = name
        self.ctrl.save()

    def _reparse_all(self) -> None:
        self.ctrl.reparse_all()
        self._refresh_table()
        QMessageBox.information(
            self, "完成", "已重新解析全部 DWG"
        )

    def _add_empty_drawing(self) -> None:
        """Add an empty Drawing and open the editor."""
        self.ctrl.add_empty_drawing()
        self._refresh_table()
        # Select the new row and open editor
        new_idx = len(self.ctrl.get_drawings()) - 1
        self.table.selectRow(new_idx)
        dlg = DrawingEditDialog(
            self.ctrl, new_idx, parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_table()

    def _open_parser_settings(self) -> None:
        dlg = ParserSettingsDialog(
            self.ctrl, parent=self
        )
        dlg.exec()
        # Refresh profile combo in case profiles changed
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(
            list(self.ctrl.parser_profiles.keys())
        )
        cur = self.ctrl.project.meta.get(
            "parser_profile", "default"
        )
        self.profile_combo.setCurrentText(cur)
        self.profile_combo.blockSignals(False)

    # ── open dialogs ─────────────────────────────────────
    def _open_import_dialog(self) -> None:
        dlg = ImportDialog(self.ctrl, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_table()

    def _open_edit_dialog(self) -> None:
        idx = self._selected_row()
        if idx is None:
            QMessageBox.warning(
                self, "提示", "請先選取 Drawing"
            )
            return
        dlg = DrawingEditDialog(
            self.ctrl, idx, parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_table()

    def _open_revision_dialog(self) -> None:
        idx = self._selected_row()
        if idx is None:
            QMessageBox.warning(
                self, "提示", "請先選取 Drawing"
            )
            return
        dlg = RevisionDialog(
            self.ctrl, idx, parent=self
        )
        dlg.exec()
        self._refresh_table()

    def _open_welds(self) -> None:
        idx = self._selected_row()
        if idx is None:
            QMessageBox.warning(
                self, "提示", "請先選取 Drawing"
            )
            return
        self.on_open_welds(idx)

    def _show_context_menu(self, pos) -> None:
        idx = self._selected_row()
        if idx is None:
            return
        dw = self.ctrl.get_drawing(idx)
        menu = QMenu(self)

        act_edit = QAction("✏️  編輯 Drawing", self)
        act_edit.triggered.connect(
            self._open_edit_dialog
        )
        menu.addAction(act_edit)

        act_rev = QAction("📋  版次管理", self)
        act_rev.triggered.connect(
            self._open_revision_dialog
        )
        menu.addAction(act_rev)

        menu.addSeparator()

        act_weld = QAction("⚡  開啟焊口編輯 ▶", self)
        act_weld.triggered.connect(self._open_welds)
        menu.addAction(act_weld)

        menu.addSeparator()

        # Toggle status
        if dw:
            cur_status = dw.get("dwg_status") or "啟用"
            if cur_status != "關閉":
                act_close = QAction(
                    "🔴  關閉圖面", self
                )
                act_close.triggered.connect(
                    lambda: self._toggle_status(idx, "關閉")
                )
                menu.addAction(act_close)
            else:
                act_open = QAction(
                    "🟢  啟用圖面", self
                )
                act_open.triggered.connect(
                    lambda: self._toggle_status(idx, "啟用")
                )
                menu.addAction(act_open)

        act_dup = QAction("📄  複製 Drawing", self)
        act_dup.triggered.connect(
            lambda: self._duplicate_drawing(idx)
        )
        menu.addAction(act_dup)

        menu.addSeparator()

        act_del = QAction("🗑  刪除", self)
        act_del.triggered.connect(self._delete_selected)
        menu.addAction(act_del)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _toggle_status(
        self, idx: int, status: str
    ) -> None:
        self.ctrl.update_drawing(
            idx, {"dwg_status": status}
        )
        self._refresh_table()

    def _duplicate_drawing(self, idx: int) -> None:
        dw = self.ctrl.get_drawing(idx)
        if not dw:
            return
        data = {k: dw.get(k) for k in
                [f[0] for f in DRAWING_FIELDS]}
        data["series_no"] = (
            data.get("series_no", "") + "-copy"
        )
        self.ctrl.import_drawings([data])
        self._refresh_table()

    def _on_double_click(self) -> None:
        idx = self._selected_row()
        if idx is not None:
            self._open_edit_dialog()

    def _delete_selected(self) -> None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(
                self, "提示", "請先選取 Drawing"
            )
            return
        indices = [s.row() for s in sel]
        ans = QMessageBox.question(
            self, "確認",
            f"確定刪除 {len(indices)} 筆 Drawing？",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self.ctrl.delete_drawings(indices)
        self._refresh_table()


# ═════════════════════════════════════════════════════════
# ImportDialog — 匯入 DWG 清單
# ═════════════════════════════════════════════════════════
class ImportDialog(QDialog):
    def __init__(
        self, ctrl: AppController, parent=None
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl
        self.setWindowTitle("匯入 DWG 清單")
        self.resize(560, 380)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "每行一筆，格式: "
                "流水號 <TAB/空格> DWG NO"
            )
        )

        self.text = QPlainTextEdit()
        layout.addWidget(self.text, stretch=1)

        btn_row = QHBoxLayout()
        paste_btn = QPushButton("匯入貼上內容")
        paste_btn.clicked.connect(self._import_text)
        btn_row.addWidget(paste_btn)

        file_btn = QPushButton("讀取 TXT 檔")
        file_btn.clicked.connect(self._import_file)
        btn_row.addWidget(file_btn)

        btn_row.addStretch()
        cancel_btn = QPushButton("關閉")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    # ── parsing ──────────────────────────────────────────
    @staticmethod
    def _parse_lines(
        lines: List[str],
    ) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            rows.append({
                "series_no": parts[0],
                "dwg_no": " ".join(parts[1:]),
            })
        return rows

    def _do_import(
        self, rows: List[Dict[str, str]]
    ) -> None:
        if not rows:
            QMessageBox.warning(
                self, "提示", "沒有可匯入的資料"
            )
            return
        try:
            n = self.ctrl.import_drawings(rows)
            QMessageBox.information(
                self, "完成", f"已匯入 {n} 筆 DWG"
            )
            self.accept()
        except Exception:
            QMessageBox.critical(
                self, "匯入失敗",
                traceback.format_exc(),
            )

    def _import_text(self) -> None:
        rows = self._parse_lines(
            self.text.toPlainText().splitlines()
        )
        self._do_import(rows)

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "選擇 DWG 清單 TXT", "",
            "Text Files (*.txt);;All Files (*.*)",
        )
        if not path:
            return
        try:
            with open(
                path, "r", encoding="utf-8"
            ) as fh:
                rows = self._parse_lines(fh.readlines())
            self._do_import(rows)
        except Exception:
            QMessageBox.critical(
                self, "讀取失敗",
                traceback.format_exc(),
            )


# ═════════════════════════════════════════════════════════
# DrawingEditDialog — 編輯單一 Drawing (分組現代化)
# ═════════════════════════════════════════════════════════

# Field group definitions: (group_name, [(key, header, widget_type)])
# widget_type: "line", "combo:VALS_KEY", "readonly", "combo_status"
_EDIT_GROUPS = [
    ("核心欄位", [
        ("series_no",     "流水號",       "line"),
        ("dwg_no",        "DWG NO",      "line"),
        ("sheet_no",      "SH'T NO",     "line"),
        ("line_no",       "Line_No",     "line"),
        ("area",          "區域",        "line"),
    ]),
    ("解析結果 (自動)", [
        ("dn",            "尺寸",        "readonly"),
        ("system",        "系統",        "readonly"),
        ("drawing_no",    "編號",        "readonly"),
        ("pipe_class",    "級數",        "readonly"),
        ("insulation",    "保溫",        "readonly"),
        ("sys_number",    "系統+編號",   "readonly"),
    ]),
    ("材料 / 管工", [
        ("material",      "管線材質",     "combo:default_material"),
        ("medium",        "介質",        "line"),
        ("pwht",          "退火",        "combo_yn"),
        ("design_pressure", "設計壓力Kg/cm²", "combo:design_pressure"),
        ("test_pressure", "測試壓力Kg/cm²",  "line"),
        ("test_fluid",    "試壓流體",     "line"),
    ]),
    ("NDE / 檢驗", [
        ("nde_pct",       "NDE (PT/RT)%",    "combo:nde_requirement"),
        ("test_pkg_no",   "試壓包編號",       "line"),
    ]),
    ("日程 / 其他", [
        ("delivery_date",   "運交現場日期",  "line"),
        ("install_billing", "安裝請款",     "line"),
        ("prefab_dwg",      "預製圖",       "line"),
        ("equipment_no",    "設備編號",     "line"),
        ("paint_color",     "面漆顏色",     "line"),
        ("dwg_status",      "圖面狀態",     "combo_status"),
        ("remark",          "備註",         "line"),
    ]),
]


class DrawingEditDialog(QDialog):
    def __init__(
        self,
        ctrl: AppController,
        drawing_idx: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl
        self.idx = drawing_idx
        dw = ctrl.get_drawing(drawing_idx)
        self.setWindowTitle(
            f"編輯 — {dw.series_no} {dw.dwg_no}"
            if dw else "新增 Drawing"
        )
        self.resize(820, 580)

        outer = QVBoxLayout(self)
        outer.setSpacing(8)

        # ── Header info bar ──────────────────────────────
        if dw and dw.dwg_no:
            info = QLabel(
                f"📐  {dw.series_no}   |   "
                f"{dw.dwg_no}   |   "
                f"Rev {dw.final_rev or '—'}   |   "
                f"狀態: {dw.get('dwg_status') or '啟用'}"
            )
            info.setStyleSheet(
                "font-size: 14px; font-weight: bold; "
                "padding: 6px 12px; "
                "background-color: #2a2a3c; "
                "border-radius: 6px; color: #e0e0ee;"
            )
            outer.addWidget(info)

        # ── Scrollable form area ─────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(12)

        self._widgets: Dict[str, QWidget] = {}
        common = ctrl.common_values

        for group_name, fields in _EDIT_GROUPS:
            grp = QGroupBox(group_name)
            grid = QGridLayout(grp)
            grid.setSpacing(8)
            grid.setContentsMargins(12, 16, 12, 8)

            cols_per_row = 3
            col = 0
            row_idx = 0

            for key, header, wtype in fields:
                val = dw.get(key) if dw else ""
                lbl = QLabel(header)
                lbl.setStyleSheet(
                    "font-size: 11px; color: #9090a8;"
                )
                grid.addWidget(lbl, row_idx * 2, col)

                if wtype == "readonly":
                    le = QLineEdit(val)
                    le.setReadOnly(True)
                    le.setStyleSheet(
                        "background-color: #1e1e2e; "
                        "color: #60b0f0; "
                        "border: 1px dashed #4e4e6e; "
                        "border-radius: 4px; "
                        "padding: 4px 8px;"
                    )
                    grid.addWidget(le, row_idx * 2 + 1, col)
                    self._widgets[key] = le

                elif wtype.startswith("combo:"):
                    vals_key = wtype.split(":", 1)[1]
                    cb = QComboBox()
                    cb.setEditable(True)
                    items = common.get(vals_key, [])
                    cb.addItems([""] + items)
                    cb.setCurrentText(val or "")
                    grid.addWidget(
                        cb, row_idx * 2 + 1, col
                    )
                    self._widgets[key] = cb

                elif wtype == "combo_yn":
                    cb = QComboBox()
                    cb.addItems(["", "Y", "N"])
                    cb.setCurrentText(val or "")
                    grid.addWidget(
                        cb, row_idx * 2 + 1, col
                    )
                    self._widgets[key] = cb

                elif wtype == "combo_status":
                    cb = QComboBox()
                    cb.addItems(["啟用", "關閉"])
                    cb.setCurrentText(val or "啟用")
                    grid.addWidget(
                        cb, row_idx * 2 + 1, col
                    )
                    self._widgets[key] = cb

                else:  # default "line"
                    le = QLineEdit(val)
                    grid.addWidget(
                        le, row_idx * 2 + 1, col
                    )
                    self._widgets[key] = le

                col += 1
                if col >= cols_per_row:
                    col = 0
                    row_idx += 1

            form_layout.addWidget(grp)

        form_layout.addStretch()
        scroll.setWidget(form_widget)
        outer.addWidget(scroll, stretch=1)

        # ── buttons ──────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        reparse_btn = QPushButton("🔄 重新解析")
        reparse_btn.setToolTip(
            "重新解析 DWG NO 並更新自動欄位"
        )
        reparse_btn.clicked.connect(self._reparse)
        btn_row.addWidget(reparse_btn)

        btn_row.addStretch()

        save_btn = QPushButton("💾 儲存")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #3e3e5c; }"
            "QPushButton:hover { background-color: #4e4e6e; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        outer.addLayout(btn_row)

    def _get_value(self, key: str) -> str:
        w = self._widgets.get(key)
        if w is None:
            return ""
        if isinstance(w, QComboBox):
            return w.currentText()
        if isinstance(w, QLineEdit):
            return w.text()
        return ""

    def _set_value(self, key: str, val: str) -> None:
        w = self._widgets.get(key)
        if w is None:
            return
        if isinstance(w, QComboBox):
            w.setCurrentText(val)
        elif isinstance(w, QLineEdit):
            w.setText(val)

    def _reparse(self) -> None:
        """Re-run parser on current DWG NO and update
        the readonly fields in the dialog."""
        dwg_no = self._get_value("dwg_no")
        if not dwg_no:
            return
        parsed = self.ctrl.parse_dwg(dwg_no)
        if "class" in parsed and "pipe_class" not in parsed:
            parsed["pipe_class"] = parsed.pop("class")
        if "sheet" in parsed and "sheet_no" not in parsed:
            parsed["sheet_no"] = parsed.pop("sheet")
        for key, val in parsed.items():
            if key in self._widgets:
                self._set_value(key, val)
        # Auto-compose sys_number
        sys = self._get_value("system")
        dno = self._get_value("drawing_no")
        if sys and dno:
            self._set_value("sys_number", f"{sys}-{dno}")

    def _save(self) -> None:
        data = {}
        for group_name, fields in _EDIT_GROUPS:
            for key, header, wtype in fields:
                if wtype == "readonly":
                    continue  # skip auto-parsed
                data[key] = self._get_value(key)
        self.ctrl.update_drawing(self.idx, data)
        self.accept()


# ═════════════════════════════════════════════════════════
# RevisionDialog — 版次歷程管理
# ═════════════════════════════════════════════════════════
class RevisionDialog(QDialog):
    """管理某一 Drawing 的版次歷程。"""

    def __init__(
        self,
        ctrl: AppController,
        drawing_idx: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl
        self.idx = drawing_idx
        dw = ctrl.get_drawing(drawing_idx)
        title = (
            f"版次管理 — {dw.series_no} {dw.dwg_no}"
            if dw else "版次管理"
        )
        self.setWindowTitle(title)
        self.resize(520, 380)

        layout = QVBoxLayout(self)

        # ── revision table ───────────────────────────────
        rev_headers = [f[1] for f in REVISION_FIELDS]
        self.table = QTableWidget(0, len(rev_headers))
        self.table.setHorizontalHeaderLabels(rev_headers)
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
        layout.addWidget(self.table, stretch=1)

        # ── add revision form ────────────────────────────
        add_group = QGroupBox("新增版次（進版）")
        add_lay = QHBoxLayout(add_group)

        add_lay.addWidget(QLabel("版次:"))
        self.rev_no_edit = QLineEdit()
        self.rev_no_edit.setPlaceholderText("A, B, 1…")
        add_lay.addWidget(self.rev_no_edit)

        add_lay.addWidget(QLabel("日期:"))
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("YYYY-MM-DD")
        add_lay.addWidget(self.date_edit)

        add_lay.addWidget(QLabel("備註:"))
        self.remark_edit = QLineEdit()
        add_lay.addWidget(self.remark_edit)

        add_btn = QPushButton("進版")
        add_btn.clicked.connect(self._add_revision)
        add_lay.addWidget(add_btn)

        layout.addWidget(add_group)

        # ── bottom buttons ───────────────────────────────
        btn_row = QHBoxLayout()
        del_btn = QPushButton("刪除選取版次")
        del_btn.clicked.connect(self._delete_revision)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._refresh()

    def _refresh(self) -> None:
        self.table.setRowCount(0)
        dw = self.ctrl.get_drawing(self.idx)
        if not dw:
            return
        rev_keys = [f[0] for f in REVISION_FIELDS]
        for rev in dw.revisions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(rev_keys):
                item = QTableWidgetItem(
                    getattr(rev, key, "")
                )
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                self.table.setItem(row, col, item)

    def _add_revision(self) -> None:
        rev_no = self.rev_no_edit.text().strip()
        if not rev_no:
            QMessageBox.warning(
                self, "提示", "請輸入版次"
            )
            return
        self.ctrl.add_revision(
            self.idx,
            rev_no,
            self.date_edit.text().strip(),
            self.remark_edit.text().strip(),
        )
        self.rev_no_edit.clear()
        self.date_edit.clear()
        self.remark_edit.clear()
        self._refresh()

    def _delete_revision(self) -> None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(
                self, "提示", "請先選取版次"
            )
            return
        for s in sorted(
            sel, key=lambda x: x.row(), reverse=True
        ):
            self.ctrl.delete_revision(
                self.idx, s.row()
            )
        self._refresh()
