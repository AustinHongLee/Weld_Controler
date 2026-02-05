from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from openpyxl import Workbook


HEADERS = [
    "流水號",
    "DWG NO",
    "銲口編號",
    "尺寸",
    "厚度",
    "材質",
    "銲接型式",
    "預製S/現場F",
    "備註",
]


def export_welds(project: Dict[str, Any], output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"焊口編號明細_{timestamp}.xlsx"
    path = os.path.join(output_dir, filename)

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)

    for drawing in project.get("drawings", []):
        serial = drawing.get("serial", "")
        dwg_no = drawing.get("dwg_no", "")
        for weld in drawing.get("welds", []):
            sheet.append(
                [
                    serial,
                    dwg_no,
                    weld.get("weld_no", ""),
                    weld.get("dn", ""),
                    weld.get("thk", ""),
                    weld.get("material", ""),
                    weld.get("weld_type", ""),
                    weld.get("shop_field", ""),
                    weld.get("remark", ""),
                ]
            )

    workbook.save(path)
    return path
