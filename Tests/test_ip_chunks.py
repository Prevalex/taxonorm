from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from taxonorm import (
    IpStyle,
    Taxonomy,
    TxInputValidationError,
    import_taxonomy,
    parse_taxonomy,
    restore_unique_ip_chunks,
    serialize_taxonomy,
    split_to_unique_ip_chunks,
)
from taxonorm.errors import TxConversionError, TxParsingError

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

    with pytest.raises(TxParsingError):
        restore_unique_ip_chunks(chunks)


def test_restore_unique_ip_chunks_rejects_cycles() -> None:
    chunks = [
        [1, 2, {"name": "Two"}],
        [2, 1, {"name": "One"}],
    ]

    with pytest.raises(TxParsingError):
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


def test_split_to_unique_ip_chunks_is_restore_inverse() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            [0, {"name": "Root"}],
            [0, 1, {"name": "Notebooks"}],
            [0, 1, 101, {"name": "Notebook parts"}],
            [0, 1, 101, 777, {"name": "Notebook cables"}],
            [0, 2, {"name": "Computers"}],
            [0, 2, 201, 202, {"name": "Deep chunk"}],
        ]
    )

    chunks = split_to_unique_ip_chunks(taxonomy, max_chunk_len=2)

    assert chunks == [
        [0, {"name": "Root"}],
        [0, 1, {"name": "Notebooks"}],
        [1, 101, {"name": "Notebook parts"}],
        [101, 777, {"name": "Notebook cables"}],
        [0, 2, {"name": "Computers"}],
        [2, 201, {}],
        [201, 202, {"name": "Deep chunk"}],
    ]
    assert restore_unique_ip_chunks(chunks) == taxonomy.to_branches()


def test_split_to_unique_ip_chunks_rejects_duplicate_ids() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["catalog", "audio", {"name": "Audio"}],
            ["sale", "audio", {"name": "Sale audio"}],
        ]
    )

    with pytest.raises(TxConversionError):
        split_to_unique_ip_chunks(taxonomy)


@pytest.mark.parametrize("max_chunk_len", [None, 1, True, "2"])
def test_split_to_unique_ip_chunks_rejects_invalid_max_chunk_len(max_chunk_len: Any) -> None:
    taxonomy = Taxonomy.from_branches([[0, {"name": "Root"}]])

    with pytest.raises(TxConversionError, match="max_chunk_len"):
        split_to_unique_ip_chunks(taxonomy, max_chunk_len=max_chunk_len)


def test_serialize_taxonomy_can_emit_restorable_ip_chunks() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            [0, {"name": "Root"}],
            [0, 1, {"name": "Notebooks"}],
            [0, 1, 101, {"name": "Notebook parts"}],
            [0, 1, 101, 777, {"name": "Notebook cables"}],
        ]
    )
    style = IpStyle(header=False, keys=False, tabbed=False)

    rows = serialize_taxonomy(
        taxonomy,
        styler=style,
        key_order=["name"],
        max_chunk_len=2,
    )

    assert rows == [
        [0, "Root"],
        [0, 1, "Notebooks"],
        [1, 101, "Notebook parts"],
        [101, 777, "Notebook cables"],
    ]
    restored = parse_taxonomy(
        rows,
        styler=style,
        leaf_keys=["name"],
        restore_ip_chunks=True,
    )
    assert restored == taxonomy


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
