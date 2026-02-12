"""Export project data to Excel."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any  # noqa: F401 – kept for future use

from openpyxl import Workbook

from src.models import (
    DRAWING_HEADERS,
    DRAWING_KEYS,
    Project,
    WELD_HEADERS,
    WELD_KEYS,
)


def export_project(project: Project, output_dir: str) -> str:
    """Export two sheets: Drawing List + Weld Control."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    name = project.meta.get("project_name", "") or "project"
    filename = f"{name}_export_{ts}.xlsx"
    path = os.path.join(output_dir, filename)

    wb = Workbook()

    # ── Sheet 1: Drawing List ────────────────────────────
    ws_dwg = wb.active
    ws_dwg.title = "Drawing List"
    headers = DRAWING_HEADERS + ["最終版版次", "最終版日期"]
    ws_dwg.append(headers)
    for dw in project.drawings:
        row = [dw.get(k) for k in DRAWING_KEYS]
        row += [dw.final_rev, dw.final_rev_date]
        ws_dwg.append(row)

    # ── Sheet 2: Weld Control ────────────────────────────
    ws_weld = wb.create_sheet("Weld Control")
    weld_headers = ["流水號", "DWG NO", "SH'T NO"] + WELD_HEADERS
    ws_weld.append(weld_headers)
    for dw in project.drawings:
        for w in dw.welds:
            row = [dw.series_no, dw.dwg_no, dw.sheet_no]
            row += [getattr(w, k, "") for k in WELD_KEYS]
            ws_weld.append(row)

    wb.save(path)
    return path
