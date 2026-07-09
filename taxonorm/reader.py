#! This module of the taxonorm package is designed to read taxonomy data from files of supported formats
#  (csv, xls, xlsx, json, xml)

from typing import Any, Callable
from pathlib import Path

from taxonorm._tables import read_llist_from_file, is_llist, is_completed_llist
from taxonorm._introspection import inspect_location
from taxonorm._console import wrn

from taxonorm.common import tStyler, R_CODEPAGE, DEFAULT_LEAF_KEY
from taxonorm.errors import TxImportError, TxInputValidationError, TxValidationError
from taxonorm.input_validation import ValidationIssue, ValidationReport
from taxonorm.model import Taxonomy
from taxonorm.parser import parse_taxonomy, trim_string_cells, trim_string_leaf_keys
from taxonorm.sniffer import guess_style
from taxonorm.validation import validated_leaf_keys

def import_taxonomy(source: str | Path | list[list[Any]], *,
                    leaf_keys: list | tuple | None = None,
                    styler: tStyler | None = None,
                    sheet: Any = None,
                    cvt_dict: dict | None = None,
                    sort_cvt: Callable | str | None = 'auto',
                    none: bool = True,
                    codepage=R_CODEPAGE,
                    eol: Any = None,
                    restore_ip_chunks: bool = False,
                    validate: bool = True,
                    max_validation_issues: int = 100) -> Taxonomy:

    if leaf_keys is None:
        leaf_keys = [DEFAULT_LEAF_KEY]

    if styler is None:
        _header_ = None
    else:
        _header_ = styler.header

    try:
        leaf_keys = validated_leaf_keys(leaf_keys)
    except TxValidationError as error:
        style_name = "UNKNOWN" if styler is None else "_".join(styler.hints)
        report = ValidationReport(
            style=style_name,
            source=str(source) if isinstance(source, (str, Path)) else None,
            issues=(
                ValidationIssue(
                    code="leaf_keys.invalid",
                    message=str(error),
                    value=leaf_keys,
                    expected="a non-empty list of non-empty hashable keys",
                ),
            ),
        )
        raise TxInputValidationError(report) from error
    leaf_keys = trim_string_leaf_keys(leaf_keys)

    if isinstance(source, (str, Path)):
        taxonomy_data = read_llist_from_file(source, sheet=sheet, cvt_dict=cvt_dict,
                                             header=_header_,
                                             none=none,
                                             codepage=codepage,
                                             skip_empty=True,
                                             eol=eol)
    elif is_llist(source):
        taxonomy_data = source

    else:
        raise TxImportError(
            "Imported taxonomy must be a file path or a list of rows. "
            f"The row list must not contain empty branch rows. {type(source)=}"
        )

    if is_completed_llist(taxonomy_data):
        taxonomy_data = trim_string_cells(taxonomy_data)
        if styler is None:
            styler = guess_style(taxonomy_data, leaf_keys=leaf_keys)
            wrn(
                f"{inspect_location()}: taxonomy style is not specified "
                f"(styler=None). Guessed style {styler} will be used."
            )

        parsed_taxonomy = parse_taxonomy(taxonomy_data, leaf_keys=leaf_keys,
                                         styler=styler,
                                         sort_cvt=sort_cvt,
                                         restore_ip_chunks=restore_ip_chunks,
                                         validate=validate,
                                         max_validation_issues=max_validation_issues,
                                         validation_source=str(source) if isinstance(source, (str, Path)) else None)
        return parsed_taxonomy
    else:
        raise TxImportError("Read data does not contain a taxonomy.")
