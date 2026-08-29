from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from taxonorm import LpStyle, Taxonomy, export_taxonomy


@pytest.mark.parametrize("suffix", [".xlsx", ".xls"])
def test_excel_export_formats_strings_as_text(
    tmp_path: Path,
    suffix: str,
) -> None:
    destination = tmp_path / f"taxonomy{suffix}"
    taxonomy = Taxonomy.from_branches(
        [
            ["001", {"name": "Root"}],
            ["001", "=002", {"name": "Child"}],
            [3, {"name": "Numeric ID"}],
        ]
    )

    export_taxonomy(
        taxonomy,
        destination,
        styler=LpStyle(header=True, ids=True, sparse=False),
        leaf_key="name",
        headers=["id", "category"],
    )

    if suffix == ".xlsx":
        openpyxl = pytest.importorskip("openpyxl")
        worksheet = openpyxl.load_workbook(destination).active

        assert worksheet["A2"].value == "001"
        assert worksheet["A2"].data_type == "s"
        assert worksheet["A2"].number_format == "@"
        assert worksheet["A3"].value == "=002"
        assert worksheet["A3"].data_type == "s"
        assert worksheet["A4"].value == 3
        assert worksheet["A4"].number_format == "General"
        return

    xlrd = pytest.importorskip("xlrd")
    workbook = xlrd.open_workbook(destination, formatting_info=True)
    worksheet = workbook.sheet_by_index(0)
    text_cell = worksheet.cell(1, 0)
    number_cell = worksheet.cell(3, 0)

    assert text_cell.value == "001"
    assert text_cell.ctype == xlrd.XL_CELL_TEXT
    assert _xls_number_format(workbook, text_cell) == "@"
    assert _xls_number_format(workbook, number_cell) == "General"


def _xls_number_format(workbook: Any, cell: Any) -> str:
    xf = workbook.xf_list[cell.xf_index]
    return workbook.format_map[xf.format_key].format_str
