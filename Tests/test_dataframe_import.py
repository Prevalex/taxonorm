from __future__ import annotations

import sys

import pytest

from taxonorm import IpStyle, LpStyle, import_taxonomy
from taxonorm._tables import dataframe_to_llist, is_dataframe
from taxonorm.sniffer import guess_style


def test_dataframe_to_llist_uses_columns_when_header_is_true() -> None:
    pd = pytest.importorskip("pandas")
    dataframe = pd.DataFrame(
        [
            [1, None, "Root"],
            [1, 11, "Child"],
        ],
        columns=["id1", "id2", "en_US"],
    )

    assert is_dataframe(dataframe)
    assert dataframe_to_llist(dataframe, header=True) == [
        ["id1", "id2", "en_US"],
        [1, None, "Root"],
        [1, 11, "Child"],
    ]


def test_import_taxonomy_accepts_ip_dataframe_with_columns_as_header() -> None:
    pd = pytest.importorskip("pandas")
    dataframe = pd.DataFrame(
        [
            [1, None, "Root", "Корінь"],
            [1, 11, "Child", "Дитина"],
        ],
        columns=["id1", "id2", "en_US", "uk_UA"],
    )

    taxonomy = import_taxonomy(
        dataframe,
        styler=IpStyle(header=True, keys=True, tabbed=True),
        leaf_keys=["en_US", "uk_UA"],
    )

    assert taxonomy.to_branches() == [
        [1, {"en_US": "Root", "uk_UA": "Корінь"}],
        [1, 11, {"en_US": "Child", "uk_UA": "Дитина"}],
    ]


def test_import_taxonomy_accepts_lp_dataframe_with_columns_as_header() -> None:
    pd = pytest.importorskip("pandas")
    dataframe = pd.DataFrame(
        [
            [1, "Root", None],
            [11, "Root", "Child"],
        ],
        columns=["id", "level1", "level2"],
    )

    taxonomy = import_taxonomy(
        dataframe,
        styler=LpStyle(header=True, ids=True, sparse=False),
        leaf_keys=["en_US"],
    )

    assert taxonomy.to_branches() == [
        [1, {"en_US": "Root"}],
        [1, 11, {"en_US": "Child"}],
    ]


def test_import_taxonomy_accepts_dataframe_without_header_columns() -> None:
    pd = pytest.importorskip("pandas")
    dataframe = pd.DataFrame(
        [
            [1, "Root"],
            [11, "Root", "Child"],
        ]
    )

    taxonomy = import_taxonomy(
        dataframe,
        styler=LpStyle(header=False, ids=True, sparse=False),
        leaf_keys=["en_US"],
    )

    assert taxonomy.to_branches() == [
        [1, {"en_US": "Root"}],
        [1, 11, {"en_US": "Child"}],
    ]


def test_guess_style_accepts_dataframe() -> None:
    pd = pytest.importorskip("pandas")
    dataframe = pd.DataFrame(
        [
            [1, None, "Root"],
            [1, 11, "Child"],
        ],
        columns=["id1", "id2", "en_US"],
    )

    rows = dataframe_to_llist(dataframe, header=None)

    assert guess_style(dataframe, leaf_keys=["en_US"]) == guess_style(
        rows,
        leaf_keys=["en_US"],
    )


def test_pandas_is_not_imported_for_plain_list_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "pandas", None)

    taxonomy = import_taxonomy(
        [[1, "Root"], [11, "Root", "Child"]],
        styler=LpStyle(header=False, ids=True, sparse=False),
        leaf_keys=["en_US"],
    )

    assert taxonomy.to_branches() == [
        [1, {"en_US": "Root"}],
        [1, 11, {"en_US": "Child"}],
    ]
