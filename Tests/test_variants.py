from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from alib.tables import read_llist_from_file

from taxonorm import Taxonomy, export_taxonomy, import_taxonomy, serialize_taxonomy
from taxonorm.common import IpStyle, LpStyle
from taxonorm.sniffer import guess_style
from taxonorm.utils import get_style_from_hints
from taxonorm import writer

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "Samples" / "Variants" / "Briefs"
PATTERNS = ROOT / "Samples" / "Patterns"
LEAF_KEYS = ["en_US", "uk_UA", "ru_RU"]


def _as_int_when_possible(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return str(value)


def _as_numeric_string(value: Any) -> Any:
    return str(int(value)) if isinstance(value, (int, float)) else value


def _load_pattern(name: str) -> Taxonomy:
    with (PATTERNS / name).open(encoding="utf-8") as stream:
        return Taxonomy.from_branches(json.load(stream))


IP_PATTERN = _load_pattern("BRIEF_3L.json")
LP_PATTERN = _load_pattern("BRIEF_EN.json")
CSV_VARIANTS = sorted(VARIANTS.glob("*.csv"))
ALL_VARIANTS = sorted(
    path
    for path in VARIANTS.iterdir()
    if path.is_file() and path.suffix.lower() in {".csv", ".xls", ".xlsx"}
)
ROUND_TRIP_CASES = [
    (get_style_from_hints(source.stem), suffix)
    for source in CSV_VARIANTS
    for suffix in (".csv", ".xls", ".xlsx")
]
ROUND_TRIP_IDS = [
    f"{'_'.join(style.hints)}-{suffix.removeprefix('.')}"
    for style, suffix in ROUND_TRIP_CASES
]


def _leaf_paths(taxonomy: Taxonomy, key: str) -> list[tuple[Any, ...]]:
    return sorted(
        (taxonomy.leaf_path(branch.path, key) for branch in taxonomy.iter_branches()),
        key=repr,
    )


def _without_trailing_empty_cells(rows: list[list[Any]]) -> list[list[Any]]:
    result: list[list[Any]] = []
    for source in rows:
        row = list(source)
        while row and row[-1] is None:
            row.pop()
        result.append(row)
    return result


@pytest.mark.parametrize("source", CSV_VARIANTS, ids=lambda path: path.stem)
def test_csv_variant_parses_like_its_pattern(source: Path) -> None:
    style = get_style_from_hints(source.stem)
    actual = import_taxonomy(
        source,
        leaf_keys=LEAF_KEYS,
        styler=style,
        cvt_dict={"*": _as_int_when_possible},
        eol="#",
    )
    expected = IP_PATTERN if isinstance(style, IpStyle) else LP_PATTERN

    if isinstance(style, LpStyle) and not style.ids:
        assert _leaf_paths(actual, "en_US") == _leaf_paths(expected, "en_US")
    else:
        assert actual == expected


@pytest.mark.parametrize(
    "source", ALL_VARIANTS, ids=lambda path: f"{path.stem}{path.suffix}"
)
def test_variant_style_is_guessed_from_contents(source: Path) -> None:
    rows = read_llist_from_file(
        source,
        cvt_dict={"*": _as_numeric_string},
        eol="#",
        skip_empty=True,
    )

    assert guess_style(rows, leaf_keys=["en_US", "uk_UA"]) == get_style_from_hints(
        source.stem
    )


@pytest.mark.parametrize("expected_file", CSV_VARIANTS, ids=lambda path: path.stem)
def test_variant_serialization_matches_sample(expected_file: Path) -> None:
    style = get_style_from_hints(expected_file.stem)
    actual = serialize_taxonomy(
        IP_PATTERN,
        styler=style,
        leaf_key="en_US",
        headers=["taxonorm", "0.1.0", "Sample", "variants"],
        key_order=LEAF_KEYS,
    )
    expected = read_llist_from_file(
        expected_file,
        cvt_dict={"*": _as_int_when_possible},
        eol="#",
        skip_empty=True,
    )

    assert _without_trailing_empty_cells(actual) == expected


def test_writer_serializes_taxonomy_before_saving(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: dict[str, Any] = {}

    def capture(rows: list[list[Any]], filename: Path, **options: Any) -> None:
        saved["rows"] = rows
        saved["filename"] = filename
        saved["options"] = options

    monkeypatch.setattr(writer, "is_opened", lambda filename: False)
    monkeypatch.setattr(writer, "save_llist_to_file", capture)
    style = IpStyle(header=False, keys=False, tabbed=False)
    destination = Path("taxonomy.csv")

    writer.export_taxonomy(
        IP_PATTERN,
        destination,
        styler=style,
        key_order=LEAF_KEYS,
        max_chunk_len=2,
    )

    assert saved["filename"] == destination
    assert saved["rows"] == serialize_taxonomy(
        IP_PATTERN,
        styler=style,
        key_order=LEAF_KEYS,
        max_chunk_len=2,
    )


@pytest.mark.parametrize(
    ("style", "suffix"), ROUND_TRIP_CASES, ids=ROUND_TRIP_IDS
)
def test_variant_round_trip_through_real_file(
    tmp_path: Path, style: IpStyle | LpStyle, suffix: str
) -> None:
    destination = tmp_path / f"taxonomy{suffix}"

    export_taxonomy(
        IP_PATTERN,
        destination,
        styler=style,
        leaf_key="en_US",
        headers=["taxonorm", "0.1.0", "Sample", "variants"],
        key_order=LEAF_KEYS,
    )

    assert destination.is_file()
    assert destination.stat().st_size > 0

    actual = import_taxonomy(
        destination,
        leaf_keys=LEAF_KEYS,
        styler=style,
        cvt_dict={"*": _as_int_when_possible},
        eol="#",
    )
    expected = IP_PATTERN if isinstance(style, IpStyle) else LP_PATTERN

    if isinstance(style, LpStyle) and not style.ids:
        assert _leaf_paths(actual, "en_US") == _leaf_paths(expected, "en_US")
    else:
        assert actual == expected
