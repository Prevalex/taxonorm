from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from taxonorm._tables import read_llist_from_file

from taxonorm import (
    IpStyle,
    LpStyle,
    Taxonomy,
    TxInputValidationError,
    import_taxonomy,
    parse_taxonomy,
    validate_input,
    validate_taxonomy,
)
from taxonorm.errors import TxParsingError
from taxonorm.utils import get_style_from_hints

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "Samples" / "Variants" / "Briefs"
CSV_VARIANTS = sorted(VARIANTS.glob("*.csv"))
LEAF_KEYS = ["en_US", "uk_UA", "ru_RU"]


def _as_int_when_possible(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return str(value)


def _read(source: Path) -> list[list[Any]]:
    return read_llist_from_file(
        source,
        cvt_dict={"*": _as_int_when_possible},
        eol="#",
        skip_empty=True,
    )


@pytest.mark.parametrize("source", CSV_VARIANTS, ids=lambda path: path.stem)
def test_every_supported_variant_has_valid_input_report(source: Path) -> None:
    style = get_style_from_hints(source.stem)

    report = validate_input(_read(source), styler=style, leaf_keys=LEAF_KEYS)

    assert report.valid, report.format_text()
    assert report.checked_rows > 0


@pytest.mark.parametrize("source", CSV_VARIANTS, ids=lambda path: path.stem)
def test_every_style_reports_a_corrupted_data_row(source: Path) -> None:
    style = get_style_from_hints(source.stem)
    rows = _read(source)
    first_data = 1 if style.header else 0

    if isinstance(style, IpStyle) or style.ids:
        rows[first_data][0] = []
    elif style.sparse:
        target = next(
            row for row in rows[first_data:] if len(row) > 1 and any(value is not None for value in row)
        )
        occupied = next(index for index, value in enumerate(target) if value is not None)
        extra = 1 if occupied == 0 else 0
        target[extra] = "unexpected second value"
    else:
        target = next(row for row in rows[first_data:] if len(row) > 1)
        target[0] = None

    report = validate_input(rows, styler=style, leaf_keys=LEAF_KEYS)

    assert not report.valid
    assert report.errors


def test_report_collects_multiple_actionable_errors() -> None:
    rows = [
        [None, "One"],
        [[], "Two"],
        [1, "Three"],
        [1, "Duplicate path"],
    ]

    report = validate_input(
        rows,
        styler=IpStyle(header=False, keys=False, tabbed=False),
        leaf_keys=["name"],
    )

    assert not report.valid
    assert len(report.errors) == 3
    assert {issue.code for issue in report.errors} == {
        "id.missing",
        "path.duplicate",
    }
    assert report.errors[0].row == 1
    assert report.errors[0].code == "id.missing"
    assert report.to_dict()["error_count"] == 3


def test_parse_raises_one_user_facing_exception_with_report() -> None:
    rows = [[None, "Leaf"]]

    with pytest.raises(TxInputValidationError) as caught:
        parse_taxonomy(
            rows,
            styler=IpStyle(header=False, keys=False, tabbed=False),
            leaf_keys=["name"],
        )

    error = caught.value
    assert error.report.errors[0].code == "id.missing"
    assert error.report.errors[0].row == 1
    assert error.to_dict()["context"]["validation"]["valid"] is False


def test_parse_trims_string_ids_leaf_keys_and_leaf_values() -> None:
    rows = [
        [" root ", " name ", " Root "],
        [" root ", " child ", " name ", " Child "],
    ]

    taxonomy = parse_taxonomy(
        rows,
        styler=IpStyle(header=False, keys=True, tabbed=False),
        leaf_keys=[" name "],
    )

    assert taxonomy.get_node(("root",)).leaves == {"name": "Root"}
    assert taxonomy.get_node(("root", "child")).leaves == {"name": "Child"}
    assert (" root ",) not in taxonomy


def test_import_error_names_the_source_file(tmp_path: Path) -> None:
    source = tmp_path / "broken.csv"
    source.write_text("1,not-a-key,value\n", encoding="utf-8-sig")

    with pytest.raises(TxInputValidationError) as caught:
        import_taxonomy(
            source,
            styler=IpStyle(header=False, keys=True, tabbed=False),
            leaf_keys=["name"],
        )

    assert caught.value.report.source == str(source)
    assert str(source) in str(caught.value)
    assert caught.value.report.errors[0].row == 1


def test_import_configuration_error_uses_validation_report(tmp_path: Path) -> None:
    source = tmp_path / "taxonomy.csv"
    source.write_text("1,Catalog\n", encoding="utf-8-sig")

    with pytest.raises(TxInputValidationError) as caught:
        import_taxonomy(
            source,
            styler=LpStyle(header=False, ids=True, sparse=False),
            leaf_keys=[],
        )

    assert caught.value.report.source == str(source)
    assert caught.value.report.errors[0].code == "leaf_keys.invalid"


def test_validation_can_be_disabled_for_internal_parser_debugging() -> None:
    rows = [[1, "not-a-key", "value"]]
    style = IpStyle(header=False, keys=True, tabbed=False)

    with pytest.raises(TxInputValidationError):
        parse_taxonomy(rows, styler=style, leaf_keys=["name"])
    with pytest.raises(TxParsingError):
        parse_taxonomy(rows, styler=style, leaf_keys=["name"], validate=False)


def test_warnings_do_not_block_parsing() -> None:
    rows = [[1, "Catalog"], [2, "Catalog", "Phones"]]
    style = LpStyle(header=False, ids=True, sparse=False)

    report = validate_input(rows, styler=style, leaf_keys=["name", "ignored"])
    taxonomy = parse_taxonomy(rows, styler=style, leaf_keys=["name", "ignored"])

    assert report.valid
    assert report.warnings[0].code == "lp.leaf_keys.extra"
    assert len(taxonomy) == 2


def test_header_key_error_points_to_header() -> None:
    rows = [
        ["id", None, "en_US"],
        [1, None, "Catalog"],
    ]

    report = validate_input(
        rows,
        styler=IpStyle(header=True, keys=True, tabbed=True),
        leaf_keys=["en_US", "uk_UA"],
    )

    issue = next(issue for issue in report.errors if issue.code == "ip.header.key_missing")
    assert issue.row == 1
    assert issue.value == "uk_UA"


def test_sparse_error_explains_ambiguous_row() -> None:
    rows = [
        [1, "Root", None],
        [2, "Second root", "Child"],
    ]

    report = validate_input(
        rows,
        styler=LpStyle(header=False, ids=True, sparse=True),
        leaf_keys=["name"],
    )

    issue = next(
        issue for issue in report.errors if issue.code == "lp.sparse.multiple_values"
    )
    assert issue.row == 2
    assert issue.expected == "one non-empty leaf path cell"


def test_report_honours_maximum_issue_count() -> None:
    rows = [[None, f"leaf-{index}"] for index in range(10)]

    report = validate_input(
        rows,
        styler=IpStyle(header=False, keys=False, tabbed=False),
        leaf_keys=["name"],
        max_issues=2,
    )

    assert len(report.issues) == 2
    assert report.truncated


def test_built_taxonomy_can_be_audited() -> None:
    taxonomy = Taxonomy.from_branches([["root", {"name": None}]])

    assert validate_taxonomy(taxonomy).valid

    empty_report = validate_taxonomy(Taxonomy())
    assert empty_report.valid
    assert empty_report.warnings[0].code == "taxonomy.empty"

    wrong_type = validate_taxonomy([["root", {"name": "Root"}]])
    assert not wrong_type.valid
    assert wrong_type.errors[0].code == "taxonomy.type"
