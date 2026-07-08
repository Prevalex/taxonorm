#! This module of the taxonorm package is designed to write taxonomy data to files of supported formats
#  (csv, xls, xlsx, json, xml)

from pathlib import Path
from typing import Hashable, Callable

from alib.tables import save_llist_to_file
from alib.files import is_opened

from taxonorm.common import tStyler, UTF8_BOM
from taxonorm.model import Taxonomy
from taxonorm.serializer import serialize_taxonomy
from taxonorm.errors import TxExportError


def export_taxonomy(taxonomy: Taxonomy, filename: str | Path, *,
                    styler: tStyler,
                    leaf_key: Hashable | None = None,
                    headers: list | None = None,
                    key_order: list[Hashable] | None = None,
                    sort_cvt: Callable | str | None = 'auto',
                    missed_leaf: Callable | None | str = 'auto',
                    sheet: str | None = None,
                    codepage=UTF8_BOM):
    _ok, _msg = True, ''

    if is_opened(filename):
        raise TxExportError(f'Файл {filename} открыт в другом приложении')

    serial = serialize_taxonomy(
        taxonomy,
        styler=styler,
        leaf_key=leaf_key,
        headers=headers,
        key_order=key_order,
        sort_cvt=sort_cvt,
        missed_leaf=missed_leaf,
    )
    save_llist_to_file(serial, filename, codepage=codepage, sheet=sheet)
    return
