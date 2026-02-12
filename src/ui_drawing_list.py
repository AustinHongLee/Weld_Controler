"""Drawing List tab — clean table + toolbar.

Import / Edit / Revision 皆以獨立對話框呈現，不佔主畫面版面。
"""
from __future__ import annotations

import traceback
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
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

        # ── toolbar ──────────────────────────────────────
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("專案:"))
        self.project_name_edit = QLineEdit(
            self.ctrl.project.meta.get(
                "project_name", ""
            )
        )
        self.project_name_edit.setPlaceholderText("專案名稱")
        self.project_name_edit.editingFinished.connect(
            self._on_project_name_changed
        )
        toolbar.addWidget(self.project_name_edit)

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

        settings_btn = QPushButton("解析設定…")
        settings_btn.clicked.connect(
            self._open_parser_settings
        )
        toolbar.addWidget(settings_btn)

        reparse_btn = QPushButton("重新解析全部")
        reparse_btn.clicked.connect(self._reparse_all)
        toolbar.addWidget(reparse_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ── action buttons ───────────────────────────────
        btn_bar = QHBoxLayout()

        import_btn = QPushButton("匯入 DWG 清單…")
        import_btn.clicked.connect(
            self._open_import_dialog
        )
        btn_bar.addWidget(import_btn)

        btn_bar.addStretch()

        del_btn = QPushButton("刪除選取")
        del_btn.clicked.connect(self._delete_selected)
        btn_bar.addWidget(del_btn)

        layout.addLayout(btn_bar)

        # ── table ────────────────────────────────────────
        cols = len(_SUMMARY_KEYS)
        self.table = QTableWidget(0, cols)
        self.table.setHorizontalHeaderLabels(
            [_SUMMARY_HEADERS[k] for k in _SUMMARY_KEYS]
        )
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        hdr.setStretchLastSection(True)
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
        for dw in self.ctrl.get_drawings():
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(_SUMMARY_KEYS):
                val = dw.get(key)
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                self.table.setItem(row, col, item)

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
        menu = QMenu(self)
        act_edit = QAction("編輯 Drawing…", self)
        act_edit.triggered.connect(
            self._open_edit_dialog
        )
        menu.addAction(act_edit)

        act_rev = QAction("版次管理…", self)
        act_rev.triggered.connect(
            self._open_revision_dialog
        )
        menu.addAction(act_rev)

        menu.addSeparator()

        act_weld = QAction("開啟焊口編輯 ▶", self)
        act_weld.triggered.connect(self._open_welds)
        menu.addAction(act_weld)

        menu.exec(self.table.viewport().mapToGlobal(pos))

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
# DrawingEditDialog — 編輯單一 Drawing
# ═════════════════════════════════════════════════════════
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
            if dw else "編輯 Drawing"
        )
        self.resize(720, 480)

        outer = QVBoxLayout(self)

        # scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_widget = QWidget()
        grid = QGridLayout(form_widget)

        self.fields: Dict[str, QLineEdit] = {}
        self.combos: Dict[str, QComboBox] = {}
        cols_per_row = 4
        col = 0
        row_idx = 0
        for key, header, _ in DRAWING_FIELDS:
            r = row_idx * 2
            c = col
            grid.addWidget(QLabel(header), r, c)
            if key == "dwg_status":
                cb = QComboBox()
                cb.addItems(["啟用", "關閉"])
                if dw:
                    cb.setCurrentText(
                        dw.get(key) or "啟用"
                    )
                grid.addWidget(cb, r + 1, c)
                self.combos[key] = cb
            else:
                le = QLineEdit()
                if dw:
                    le.setText(dw.get(key))
                grid.addWidget(le, r + 1, c)
                self.fields[key] = le
            col += 1
            if col >= cols_per_row:
                col = 0
                row_idx += 1

        scroll.setWidget(form_widget)
        outer.addWidget(scroll, stretch=1)

        # buttons
        btn_row = QHBoxLayout()
        save_btn = QPushButton("儲存")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()

        outer.addLayout(btn_row)

    def _save(self) -> None:
        data = {
            k: le.text()
            for k, le in self.fields.items()
        }
        for k, cb in self.combos.items():
            data[k] = cb.currentText()
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
