"""Small conversion-map helpers for list-of-lists tables."""

from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import Any, Literal
import warnings

OnMissing = Literal["ignore", "warn", "raise"]
Converter = Callable[[Any], Any] | None
_MISSING_TITLE = object()


class MappingError(ValueError):
    """Raised when a conversion map cannot be applied."""


def _validate_conversion_args(
    cvt_dict: object,
    default_key: Any,
    on_missing: str,
) -> None:
    if not isinstance(cvt_dict, dict):
        raise MappingError("cvt_dict must be dict")
    if not all(callable(converter) or converter is None for converter in cvt_dict.values()):
        raise MappingError("all cvt_dict values must be callable or None")
    try:
        hash(default_key)
    except TypeError as err:
        raise MappingError("default_key must be hashable") from err
    if on_missing not in {"ignore", "warn", "raise"}:
        raise MappingError(f"on_missing must be 'ignore', 'warn', or 'raise'. Got: {on_missing!r}")


def _validate_list_converter_keys(cvt_dict: dict[Any, Converter], default_key: Any) -> None:
    invalid = [
        key
        for key in cvt_dict
        if key != default_key and (not isinstance(key, int) or isinstance(key, bool) or key < 0)
    ]
    if invalid:
        raise MappingError(f"list converter keys must be non-negative integer indexes. Got: {invalid!r}")


def apply_cvt_dict_to_llist(
    rows: list[list[Any]],
    cvt_dict: dict[Any, Converter],
    *,
    header: bool = True,
    default_key: Any = "*",
    on_missing: OnMissing = "ignore",
) -> None:
    if not isinstance(rows, list):
        raise MappingError("table must be list")
    if not rows:
        raise MappingError("table must be a non-empty list")
    if not all(isinstance(row, list) for row in rows):
        raise MappingError("table rows must be lists")
    _validate_conversion_args(cvt_dict, default_key, on_missing)

    start_row = 1 if header else 0
    normalized_titles: list[Any] = []

    if header:
        title_indexes: dict[Hashable, list[int]] = {}
        for index, title in enumerate(rows[0]):
            normalized = title.strip() if isinstance(title, str) else title
            if normalized is None or normalized == "":
                normalized_titles.append(_MISSING_TITLE)
                continue
            if normalized == default_key:
                raise MappingError(
                    f"column {index} title {normalized!r} conflicts with default_key {default_key!r}"
                )
            if not isinstance(normalized, Hashable):
                warnings.warn(f"title of column {index} is unhashable and will be ignored", stacklevel=2)
                normalized_titles.append(_MISSING_TITLE)
                continue
            normalized_titles.append(normalized)
            title_indexes.setdefault(normalized, []).append(index)

        for title, indexes in title_indexes.items():
            if len(indexes) < 2:
                continue
            warnings.warn(
                f"column title {title!r} is duplicated at indexes {indexes}; "
                "the ambiguous title will be ignored",
                stacklevel=2,
            )
            for index in indexes:
                normalized_titles[index] = _MISSING_TITLE
    else:
        _validate_list_converter_keys(cvt_dict, default_key)

    column_count = max(len(row) for row in rows)
    has_default = default_key in cvt_dict
    converters_by_index: dict[int, Converter] = {}

    for index in range(column_count):
        title_key = normalized_titles[index] if header and index < len(normalized_titles) else _MISSING_TITLE
        has_usable_title = header and title_key is not _MISSING_TITLE
        if has_usable_title and title_key in cvt_dict:
            converters_by_index[index] = cvt_dict[title_key]
        elif index in cvt_dict:
            converters_by_index[index] = cvt_dict[index]
        elif has_default:
            converters_by_index[index] = cvt_dict[default_key]
        else:
            identifier = f"header {title_key!r}" if has_usable_title else f"index {index}"
            if on_missing == "warn":
                warnings.warn(f"Conversion for {identifier} is not defined.", stacklevel=2)
            elif on_missing == "raise":
                raise MappingError(f"Conversion for {identifier} is not defined.")

    for row in rows[start_row:]:
        for index, value in enumerate(row):
            converter = converters_by_index.get(index)
            if converter is not None:
                row[index] = converter(value)
