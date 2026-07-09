"""Small validation primitives used internally by taxonorm."""

from __future__ import annotations

from collections.abc import Hashable, Sized
from numbers import Number
from typing import Any


def is_empty(value: Any) -> bool:
    """Return whether *value* is empty in tabular-data terms."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, bool):
        return False
    if isinstance(value, Number):
        return False
    if isinstance(value, Sized):
        return len(value) == 0
    return False


def is_valid_keyid(value: object, allow_empty: bool = False) -> bool:
    return isinstance(value, Hashable) and (allow_empty or not is_empty(value))
