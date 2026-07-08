from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from taxonorm import (
    IpStyle,
    TxInputValidationError,
    import_taxonomy,
    parse_taxonomy,
    restore_unique_ip_chunks,
)
from taxonorm.errors import TxParsingError

ROOT = Path(__file__).resolve().parents[1]


def _as_int_when_possible(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return str(value)


def test_restore_unique_ip_chunks_expands_partial_paths() -> None:
    chunks = [
        [0, 1, {"name": "Notebooks"}],
        [1, 101, {"name": "Notebook parts"}],
        [101, 777, {"name": "Notebook cables"}],
        [0, 2, {"name": "Computers"}],
        [2, 201, 202, {"name": "Deep chunk"}],
    ]

    assert restore_unique_ip_chunks(chunks) == [
        [0, 1, {"name": "Notebooks"}],
        [0, 1, 101, {"name": "Notebook parts"}],
        [0, 1, 101, 777, {"name": "Notebook cables"}],
        [0, 2, {"name": "Computers"}],
        [0, 2, 201, 202, {"name": "Deep chunk"}],
    ]


def test_restore_unique_ip_chunks_rejects_ambiguous_parent() -> None:
    chunks = [
        [0, 1, {"name": "One"}],
        [2, 1, {"name": "Same node under another parent"}],
    ]

    with pytest.raises(TxParsingError, match="более одного родителя"):
        restore_unique_ip_chunks(chunks)


def test_restore_unique_ip_chunks_rejects_cycles() -> None:
    chunks = [
        [1, 2, {"name": "Two"}],
        [2, 1, {"name": "One"}],
    ]

    with pytest.raises(TxParsingError, match="цикл"):
        restore_unique_ip_chunks(chunks)


def test_parse_taxonomy_can_restore_ip_chunks() -> None:
    rows = [
        [0, 1, "Notebooks"],
        [1, 101, "Notebook parts"],
        [101, 777, "Notebook cables"],
    ]

    taxonomy = parse_taxonomy(
        rows,
        styler=IpStyle(header=False, keys=False, tabbed=False),
        leaf_keys=["name"],
        restore_ip_chunks=True,
    )

    assert taxonomy.get_node((0, 1, 101, 777)).leaves == {
        "name": "Notebook cables"
    }
    assert (1, 101) not in taxonomy


def test_ip_chunks_without_keys_reject_too_many_leaf_keys() -> None:
    rows = [
        [0, 1, "Ноутбуки"],
        [1, 101, "Ноутбуки"],
    ]

    with pytest.raises(TxInputValidationError) as caught:
        parse_taxonomy(
            rows,
            styler=IpStyle(header=False, keys=False, tabbed=False),
            leaf_keys=["en_US", "uk_UA", "ru_RU"],
            restore_ip_chunks=True,
        )

    assert caught.value.report.errors[0].code == "ip.row.too_short"


def test_real_mti_tp_file_imports_as_restored_ip_taxonomy() -> None:
    taxonomy = import_taxonomy(
        ROOT / "zArc" / "Experiments" / "mti" / "mti_grp_swap.csv",
        styler=IpStyle(header=False, keys=False, tabbed=False),
        leaf_keys=["name"],
        cvt_dict={"*": _as_int_when_possible},
        restore_ip_chunks=True,
    )

    assert taxonomy.get_node((0, 963, 966, 138)).leaves == {
        "name": "Витратні матеріали для друкувальних пристроїв"
    }
    assert taxonomy.get_node((0, 99005)).leaves == {"name": "ЦОД інфраструктура"}
    assert (963, 966) not in taxonomy
