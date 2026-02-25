"""Parser Profile + System Map management dialog.

ProfileTab 使用可視化拖曳介面管理 DWG NO 解析規則。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import (
    QMimeData, QPoint, Qt, pyqtSignal,
)
from PyQt6.QtGui import (
    QDrag, QFont,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.controller import AppController

# ─── Field display names ────────────────────────────────
_FIELD_DISPLAY = {
    "system":     "系統",
    "drawing_no": "編號",
    "dn":         "尺寸",
    "pipe_class": "級數",
    "insulation": "保溫",
    "sheet_no":   "SH'T NO",
}
_ALL_FIELDS = list(_FIELD_DISPLAY.keys())


# ═════════════════════════════════════════════════════════
# DragChip — a single draggable field chip
# ═════════════════════════════════════════════════════════
class DragChip(QFrame):
    """A styled label that can be dragged to reorder."""

    CHIP_MIME = "application/x-fieldchip"

    def __init__(
        self, field_key: str, parent=None
    ) -> None:
        super().__init__(parent)
        self.field_key = field_key
        self.setFrameShape(QFrame.Shape.Box)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        self.setMinimumHeight(40)
        self.setMinimumWidth(70)
        self._update_style(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(0)

        display = _FIELD_DISPLAY.get(
            field_key, field_key
        )
        self.label = QLabel(display)
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        f = QFont()
        f.setBold(True)
        self.label.setFont(f)
        lay.addWidget(self.label)

        self.sub = QLabel(field_key)
        self.sub.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        sub_font = QFont()
        sub_font.setPointSize(8)
        self.sub.setFont(sub_font)
        self.sub.setStyleSheet("color: #9090a8;")
        lay.addWidget(self.sub)

    def _update_style(self, hover: bool) -> None:
        bg = "#3d3d5c" if hover else "#2a2a3c"
        self.setStyleSheet(
            f"DragChip {{ background: {bg}; "
            f"border: 2px solid #7c6ff7; "
            f"border-radius: 6px; color: #e0e0ee; }}"
        )

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_start = ev.pos()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev) -> None:
        if not (ev.buttons()
                & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, "_drag_start"):
            return
        dist = (ev.pos() - self._drag_start).manhattanLength()
        if dist < 10:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(
            self.CHIP_MIME,
            self.field_key.encode("utf-8"),
        )
        drag.setMimeData(mime)
        self.setCursor(
            Qt.CursorShape.ClosedHandCursor
        )
        drag.exec(Qt.DropAction.MoveAction)
        self.setCursor(
            Qt.CursorShape.OpenHandCursor
        )

    def enterEvent(self, ev) -> None:
        self._update_style(True)

    def leaveEvent(self, ev) -> None:
        self._update_style(False)


# ═════════════════════════════════════════════════════════
# ChipStrip — horizontal strip of DragChips with reorder
# ═════════════════════════════════════════════════════════
class ChipStrip(QFrame):
    """A horizontal container that accepts drag-and-drop
    reordering of DragChip items."""

    order_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(60)
        self.setStyleSheet(
            "ChipStrip { border: 2px dashed #4e4e6e; "
            "border-radius: 8px; background: #252536; }"
        )
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(6)
        self._layout.addStretch()

    # ── public API ───────────────────────────────────────
    def set_fields(self, fields: List[str]) -> None:
        self._clear()
        for f in fields:
            chip = DragChip(f, self)
            self._layout.insertWidget(
                self._layout.count() - 1, chip
            )
        self.order_changed.emit()

    def get_fields(self) -> List[str]:
        result: List[str] = []
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, DragChip):
                result.append(w.field_key)
        return result

    def add_field(self, key: str) -> None:
        chip = DragChip(key, self)
        self._layout.insertWidget(
            self._layout.count() - 1, chip
        )
        self.order_changed.emit()

    def remove_last(self) -> None:
        count = self._layout.count()
        for i in range(count - 2, -1, -1):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, DragChip):
                self._layout.removeWidget(w)
                w.deleteLater()
                break
        self.order_changed.emit()

    # ── internal ─────────────────────────────────────────
    def _clear(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _chip_index_at(self, pos: QPoint) -> int:
        """Return the index where a drop should insert."""
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, DragChip):
                mid = w.x() + w.width() // 2
                if pos.x() < mid:
                    return i
        # After all chips → before the stretch
        return max(0, self._layout.count() - 1)

    # ── drag events ──────────────────────────────────────
    def dragEnterEvent(self, ev) -> None:
        if ev.mimeData().hasFormat(DragChip.CHIP_MIME):
            ev.acceptProposedAction()

    def dragMoveEvent(self, ev) -> None:
        if ev.mimeData().hasFormat(DragChip.CHIP_MIME):
            ev.acceptProposedAction()

    def dropEvent(self, ev) -> None:
        mime = ev.mimeData()
        if not mime.hasFormat(DragChip.CHIP_MIME):
            return
        key = bytes(
            mime.data(DragChip.CHIP_MIME)
        ).decode("utf-8")

        # Find and remove the source chip
        source: Optional[DragChip] = None
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, DragChip) and w.field_key == key:
                source = w
                self._layout.removeWidget(w)
                break

        if source is None:
            # Chip from the pool (add new)
            source = DragChip(key, self)

        insert_idx = self._chip_index_at(ev.position().toPoint())
        self._layout.insertWidget(insert_idx, source)
        ev.acceptProposedAction()
        self.order_changed.emit()


# ═════════════════════════════════════════════════════════
# ParserSettingsDialog
# ═════════════════════════════════════════════════════════
class ParserSettingsDialog(QDialog):
    """管理 DWG NO 解析設定 + 系統→介質 對照表。"""

    def __init__(
        self, ctrl: AppController, parent=None
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl
        self.setWindowTitle("解析設定管理")
        self.resize(700, 520)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        self.profile_tab = ProfileTab(ctrl, self)
        tabs.addTab(
            self.profile_tab, "DWG NO 解析規則"
        )

        self.sysmap_tab = SystemMapTab(ctrl, self)
        tabs.addTab(
            self.sysmap_tab, "系統→介質 對照"
        )

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


# ═════════════════════════════════════════════════════════
# Tab 1 : ProfileTab — 可視化拖曳 mapping
# ═════════════════════════════════════════════════════════
class ProfileTab(QWidget):
    def __init__(
        self, ctrl: AppController, parent=None
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl

        layout = QVBoxLayout(self)

        # ── profile selector ─────────────────────────────
        sel = QHBoxLayout()
        sel.addWidget(QLabel("設定檔:"))
        self.combo = QComboBox()
        self.combo.addItems(
            list(self.ctrl.parser_profiles.keys())
        )
        self.combo.currentTextChanged.connect(
            self._load_profile
        )
        sel.addWidget(self.combo)

        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._add_profile)
        sel.addWidget(add_btn)
        del_btn = QPushButton("刪除")
        del_btn.clicked.connect(self._del_profile)
        sel.addWidget(del_btn)
        layout.addLayout(sel)

        # ── delimiter ────────────────────────────────────
        delim = QHBoxLayout()
        delim.addWidget(QLabel("分隔符號:"))
        self.delim_edit = QLineEdit("-")
        self.delim_edit.setMaximumWidth(50)
        self.delim_edit.textChanged.connect(
            self._update_preview
        )
        delim.addWidget(self.delim_edit)
        delim.addStretch()
        layout.addLayout(delim)

        # ── sample DWG NO ────────────────────────────────
        sample = QHBoxLayout()
        sample.addWidget(QLabel("範例 DWG NO:"))
        self.sample_edit = QLineEdit(
            "AC-1801-50-AA2B-NA-1"
        )
        self.sample_edit.textChanged.connect(
            self._update_preview
        )
        sample.addWidget(self.sample_edit)
        layout.addLayout(sample)

        # ── token preview ────────────────────────────────
        layout.addWidget(QLabel("拆解結果:"))
        self.token_label = QLabel()
        self.token_label.setStyleSheet(
            "font-size: 15px; font-family: monospace; "
            "color: #e0e0ee; padding: 4px;"
        )
        self.token_label.setWordWrap(True)
        layout.addWidget(self.token_label)

        # ── chip strip (drag-and-drop) ───────────────────
        layout.addWidget(QLabel(
            "▼ 拖曳下方欄位標籤來調整對應順序："
        ))
        self.strip = ChipStrip(self)
        self.strip.order_changed.connect(
            self._update_preview
        )
        layout.addWidget(self.strip)

        # ── chip buttons ─────────────────────────────────
        chip_btns = QHBoxLayout()
        for key, display in _FIELD_DISPLAY.items():
            btn = QPushButton(f"+ {display}")
            btn.setToolTip(key)
            btn.clicked.connect(
                lambda _=False, k=key: self.strip.add_field(k)
            )
            chip_btns.addWidget(btn)
        del_last = QPushButton("移除末尾")
        del_last.clicked.connect(self.strip.remove_last)
        chip_btns.addWidget(del_last)
        layout.addLayout(chip_btns)

        # ── mapping result preview ───────────────────────
        layout.addWidget(QLabel("對應結果預覽:"))
        self.result_label = QLabel()
        self.result_label.setStyleSheet(
            "font-size: 13px; padding: 4px; "
            "background: #2a3c2a; color: #43d9a0; border-radius: 4px;"
        )
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        # ── save ─────────────────────────────────────────
        save_row = QHBoxLayout()
        save_row.addStretch()
        save_btn = QPushButton("儲存設定檔")
        save_btn.clicked.connect(self._save)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        layout.addStretch()

        self._load_profile(self.combo.currentText())

    # ── load / save ──────────────────────────────────────
    def _load_profile(self, name: str) -> None:
        p = self.ctrl.parser_profiles.get(name, {})
        self.delim_edit.setText(
            p.get("delimiter", "-")
        )
        mapping = p.get("mapping", [])
        self.strip.set_fields(mapping)
        self._update_preview()

    def _save(self) -> None:
        name = self.combo.currentText().strip()
        if not name:
            return
        profiles = dict(self.ctrl.parser_profiles)
        profiles[name] = {
            "delimiter":
                self.delim_edit.text() or "-",
            "mapping": self.strip.get_fields(),
        }
        self.ctrl.save_parser_profiles(profiles)
        QMessageBox.information(
            self, "完成",
            f"設定檔「{name}」已儲存",
        )

    # ── preview ──────────────────────────────────────────
    def _update_preview(self) -> None:
        delim = self.delim_edit.text() or "-"
        sample = self.sample_edit.text()
        tokens = [
            t for t in sample.split(delim) if t
        ]
        fields = self.strip.get_fields()

        # Token preview
        parts = []
        for i, t in enumerate(tokens):
            parts.append(f"[{t}]")
        self.token_label.setText(
            f"  {delim}  ".join(parts)
            if parts else "(空)"
        )

        # Mapping result
        lines = []
        for i, key in enumerate(fields):
            display = _FIELD_DISPLAY.get(key, key)
            val = tokens[i] if i < len(tokens) else "—"
            lines.append(f"{display} = {val}")
        self.result_label.setText(
            "　│　".join(lines) if lines else "(無對應)"
        )

    # ── profile add / del ────────────────────────────────
    def _add_profile(self) -> None:
        name, ok = QInputDialog.getText(
            self, "新增設定檔", "名稱:"
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.ctrl.parser_profiles:
            QMessageBox.warning(
                self, "重複", "此名稱已存在"
            )
            return
        profiles = dict(self.ctrl.parser_profiles)
        profiles[name] = {
            "delimiter": "-", "mapping": [],
        }
        self.ctrl.save_parser_profiles(profiles)
        self.combo.addItem(name)
        self.combo.setCurrentText(name)

    def _del_profile(self) -> None:
        name = self.combo.currentText()
        if name == "default":
            QMessageBox.warning(
                self, "提示", "不能刪除 default"
            )
            return
        profiles = dict(self.ctrl.parser_profiles)
        profiles.pop(name, None)
        self.ctrl.save_parser_profiles(profiles)
        self.combo.removeItem(
            self.combo.findText(name)
        )


# ═════════════════════════════════════════════════════════
# Tab 2 : SystemMapTab
# ═════════════════════════════════════════════════════════
class SystemMapTab(QWidget):
    def __init__(
        self, ctrl: AppController, parent=None
    ) -> None:
        super().__init__(parent)
        self.ctrl = ctrl

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "系統代碼 → 介質 (中文說明) 對照表\n"
            "匯入 DWG 時，系統代碼會自動帶入「介質」欄位。"
        ))

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(
            ["系統代碼", "介質 / 說明"]
        )
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        hdr.setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.table, stretch=1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("新增")
        add_btn.clicked.connect(self._add_row)
        btn_row.addWidget(add_btn)

        del_btn = QPushButton("刪除選取")
        del_btn.clicked.connect(self._del_row)
        btn_row.addWidget(del_btn)

        btn_row.addStretch()

        save_btn = QPushButton("儲存")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        self._load()

    def _load(self) -> None:
        self.table.setRowCount(0)
        for code, desc in sorted(
            self.ctrl.system_map.items()
        ):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(
                row, 0, QTableWidgetItem(code)
            )
            self.table.setItem(
                row, 1, QTableWidgetItem(desc)
            )

    def _add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(
            row, 0, QTableWidgetItem("")
        )
        self.table.setItem(
            row, 1, QTableWidgetItem("")
        )

    def _del_row(self) -> None:
        sel = self.table.selectionModel().selectedRows()
        for s in sorted(
            sel, key=lambda x: x.row(), reverse=True
        ):
            self.table.removeRow(s.row())

    def _save(self) -> None:
        data: Dict[str, str] = {}
        for r in range(self.table.rowCount()):
            ci = self.table.item(r, 0)
            di = self.table.item(r, 1)
            code = (
                ci.text().strip().upper() if ci else ""
            )
            desc = di.text().strip() if di else ""
            if code:
                data[code] = desc
        self.ctrl.save_system_map(data)
        QMessageBox.information(
            self, "完成", "系統對照表已儲存"
        )
