"""Theme engine — load config/theme.json and generate QSS stylesheet.

Provides a modern, rounded UI with high-contrast color coding per tab.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_theme(config_dir: str) -> Dict[str, Any]:
    """Load the active theme from config/theme.json."""
    path = os.path.join(config_dir, "theme.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    active = data.get("active_theme", "dark_modern")
    themes = data.get("themes", {})
    theme = themes.get(active, {})
    theme["_name"] = active
    theme["_tab_colors"] = theme.get("tabs", {})
    return theme


def generate_qss(theme: Dict[str, Any]) -> str:
    """Generate a complete QSS stylesheet from a theme dict."""
    if not theme:
        return ""

    b = theme.get("base", {})
    a = theme.get("accent", {})

    bg          = b.get("bg",           "#1e1e2e")
    bg_s        = b.get("bg_surface",   "#252536")
    bg_c        = b.get("bg_card",      "#2a2a3c")
    bg_h        = b.get("bg_hover",     "#33334a")
    bg_sel      = b.get("bg_selected",  "#3d3d5c")
    border      = b.get("border",       "#3e3e5c")
    border_l    = b.get("border_light", "#4e4e6e")
    text        = b.get("text",         "#e0e0ee")
    text_dim    = b.get("text_dim",     "#9090a8")
    text_head   = b.get("text_heading", "#ffffff")

    primary     = a.get("primary",       "#7c6ff7")
    primary_h   = a.get("primary_hover", "#9589ff")
    success     = a.get("success",       "#43d9a0")
    warning     = a.get("warning",       "#f0c040")
    danger      = a.get("danger",        "#f06070")
    info        = a.get("info",          "#60b0f0")

    return f"""
/* ═══════════ Global ═══════════ */
* {{
    font-family: "Segoe UI", "Microsoft JhengHei", "Noto Sans TC", sans-serif;
    font-size: 13px;
}}

QWidget {{
    background-color: {bg};
    color: {text};
}}

/* ═══════════ Main Window ═══════════ */
QMainWindow {{
    background-color: {bg};
}}

/* ═══════════ Labels ═══════════ */
QLabel {{
    color: {text};
    background: transparent;
    padding: 1px;
}}

/* ═══════════ Tab Widget ═══════════ */
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: 8px;
    background-color: {bg_s};
    margin-top: -1px;
}}

QTabBar {{
    background: transparent;
}}

QTabBar::tab {{
    background-color: {bg_c};
    color: {text_dim};
    border: 1px solid {border};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 18px;
    margin-right: 3px;
    min-width: 90px;
    font-weight: 500;
}}

QTabBar::tab:hover {{
    background-color: {bg_h};
    color: {text};
}}

QTabBar::tab:selected {{
    background-color: {bg_s};
    color: {text_head};
    font-weight: bold;
    border-bottom: 3px solid {primary};
}}

/* ═══════════ Buttons ═══════════ */
QPushButton {{
    background-color: {primary};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    min-height: 28px;
}}

QPushButton:hover {{
    background-color: {primary_h};
}}

QPushButton:pressed {{
    background-color: {_darken(primary, 0.15)};
}}

QPushButton:disabled {{
    background-color: {border};
    color: {text_dim};
}}

/* Danger button (delete) — by object name */
QPushButton[danger="true"] {{
    background-color: {danger};
}}
QPushButton[danger="true"]:hover {{
    background-color: {_lighten(danger, 0.12)};
}}

/* ═══════════ Input fields ═══════════ */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {bg_c};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 10px;
    selection-background-color: {primary};
    selection-color: #ffffff;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1.5px solid {primary};
}}

/* ═══════════ ComboBox ═══════════ */
QComboBox {{
    background-color: {bg_c};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 5px 10px;
    min-height: 22px;
}}

QComboBox:hover {{
    border-color: {primary};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 24px;
    border-left: 1px solid {border};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background: transparent;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {text_dim};
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {bg_c};
    color: {text};
    border: 1px solid {border_l};
    border-radius: 6px;
    selection-background-color: {primary};
    selection-color: #ffffff;
    outline: none;
}}

/* ═══════════ Tables ═══════════ */
QTableWidget, QTableView {{
    background-color: {bg_s};
    alternate-background-color: {bg_c};
    color: {text};
    gridline-color: {border};
    border: 1px solid {border};
    border-radius: 8px;
    selection-background-color: {bg_sel};
    selection-color: {text_head};
    outline: none;
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

QTableWidget::item:selected {{
    background-color: {bg_sel};
    color: {text_head};
}}

QHeaderView::section {{
    background-color: {bg_c};
    color: {text_head};
    border: none;
    border-bottom: 2px solid {primary};
    border-right: 1px solid {border};
    padding: 6px 8px;
    font-weight: 600;
    font-size: 12px;
}}

QHeaderView::section:hover {{
    background-color: {bg_h};
}}

/* ═══════════ List Widget ═══════════ */
QListWidget {{
    background-color: {bg_s};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    outline: none;
}}

QListWidget::item {{
    padding: 6px 12px;
    border-radius: 4px;
    margin: 1px 2px;
}}

QListWidget::item:hover {{
    background-color: {bg_h};
}}

QListWidget::item:selected {{
    background-color: {primary};
    color: #ffffff;
}}

/* ═══════════ GroupBox ═══════════ */
QGroupBox {{
    background-color: {bg_c};
    border: 1px solid {border};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 600;
    color: {text_head};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    background-color: {primary};
    color: #ffffff;
    border-radius: 4px;
    left: 12px;
}}

/* ═══════════ CheckBox ═══════════ */
QCheckBox {{
    spacing: 6px;
    color: {text};
    background: transparent;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {border_l};
    border-radius: 4px;
    background-color: {bg_c};
}}

QCheckBox::indicator:hover {{
    border-color: {primary};
}}

QCheckBox::indicator:checked {{
    background-color: {primary};
    border-color: {primary};
    image: none;
}}

/* Checkmark via border trick */
QCheckBox::indicator:checked {{
    background-color: {primary};
    border-color: {primary};
}}

/* ═══════════ ScrollArea ═══════════ */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ═══════════ Scrollbar ═══════════ */
QScrollBar:vertical {{
    background-color: {bg_s};
    width: 10px;
    border: none;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {border_l};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {primary};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {bg_s};
    height: 10px;
    border: none;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {border_l};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {primary};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ═══════════ Splitter ═══════════ */
QSplitter::handle {{
    background-color: {border};
    border-radius: 2px;
}}

QSplitter::handle:horizontal {{
    width: 3px;
}}

QSplitter::handle:vertical {{
    height: 3px;
}}

/* ═══════════ ToolTip ═══════════ */
QToolTip {{
    background-color: {bg_c};
    color: {text};
    border: 1px solid {primary};
    border-radius: 6px;
    padding: 6px 10px;
}}

/* ═══════════ Menu ═══════════ */
QMenu {{
    background-color: {bg_c};
    color: {text};
    border: 1px solid {border_l};
    border-radius: 8px;
    padding: 4px 0;
}}

QMenu::item {{
    padding: 6px 28px;
    border-radius: 4px;
    margin: 2px 4px;
}}

QMenu::item:selected {{
    background-color: {primary};
    color: #ffffff;
}}

/* ═══════════ Message Box ═══════════ */
QMessageBox {{
    background-color: {bg_s};
}}

QMessageBox QLabel {{
    color: {text};
}}

/* ═══════════ Input Dialog ═══════════ */
QInputDialog {{
    background-color: {bg_s};
}}

/* ═══════════ Status colors (via property) ═══════════ */
QLabel[status="success"] {{
    color: {success};
}}

QLabel[status="warning"] {{
    color: {warning};
}}

QLabel[status="danger"] {{
    color: {danger};
}}

QLabel[status="info"] {{
    color: {info};
}}
"""


def get_tab_indicator_qss(
    theme: Dict[str, Any], tab_names: list[str]
) -> str:
    """Generate per-tab bottom-border color for the tab bar."""
    tab_colors = theme.get("_tab_colors", {})
    if not tab_colors:
        return ""

    parts: list[str] = []
    for i, name in enumerate(tab_names):
        color = tab_colors.get(name, "")
        if color:
            parts.append(
                f"QTabBar::tab:nth({i}) {{ "
                f"border-bottom-color: {color}; }}"
            )
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════
# Color utility helpers
# ═══════════════════════════════════════════════════════════

def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _darken(hex_color: str, amount: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    factor = 1.0 - amount
    return _rgb_to_hex(
        int(r * factor), int(g * factor), int(b * factor)
    )


def _lighten(hex_color: str, amount: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(
        min(255, int(r + (255 - r) * amount)),
        min(255, int(g + (255 - g) * amount)),
        min(255, int(b + (255 - b) * amount)),
    )


def contrast_text(bg_hex: str) -> str:
    """Return white or dark text based on background luminance."""
    return "#ffffff" if _luminance(bg_hex) < 0.5 else "#1a1a2e"
