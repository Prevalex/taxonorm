"""Small sequence helpers used internally by taxonorm."""

from __future__ import annotations

from collections.abc import Hashable
from typing import Any, TypeVar, cast

from ._validation import is_empty

T = TypeVar("T")


def is_empty_list(row: list[Any]) -> bool:
    return all(is_empty(item) for item in row)


def count_non_empty(row: list[Any]) -> int:
    return sum(not is_empty(value) for value in row)


def take_items_of_list_from_other_list(
    hashable_items: list[Hashable],
    any_items: list[Any],
) -> tuple[Hashable, ...]:
    keys = set(hashable_items)
    found: set[Hashable] = set()
    for item in any_items:
        try:
            if item in keys:
                found.add(item)
        except TypeError:
            continue
    return tuple(key for key in hashable_items if key in found)


def resized_list(
    values: list[T],
    length: int,
    default: T | None = None,
) -> list[T | None]:
    if not isinstance(length, int) or isinstance(length, bool):
        raise TypeError(f"length must be int. Got: {type(length).__name__}={length!r}")
    if length < 0:
        raise ValueError(f"length must be >= 0. Got: {length}")
    if len(values) >= length:
        return cast(list[T | None], values[:length])
    return values + [default] * (length - len(values))
