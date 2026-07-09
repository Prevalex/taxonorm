from typing import Any, TypeGuard
from collections.abc import Hashable

from ._introspection import repr_type
from ._tables import is_empty_llist
from ._validation import is_empty

from .errors import TxValidationError

def validate_leaf_keys(leaf_keys):
    """Validate leaf keys and raise ``TxValidationError`` on failure."""
    if isinstance(leaf_keys, (list, tuple)):
        if leaf_keys:
            for key in leaf_keys:
                if is_valid_keyid(key):
                    continue
                else:
                    raise TxValidationError(
                        f"Leaf key {key!r} does not satisfy key requirements: "
                        "hashable; not empty; not None"
                    )
            else:
                return
        else:
            raise TxValidationError("Leaf key list is empty.")
    else:
        raise TxValidationError(
            "leaf_keys must be a list or tuple. "
            f"Got {type(leaf_keys)}:{leaf_keys!r}"
        )


def validated_leaf_keys(leaf_keys) -> list[Hashable]:
    """Validate leaf keys and return a de-duplicated list preserving order."""
    validate_leaf_keys(leaf_keys)
    return list(dict.fromkeys(leaf_keys))


def validate_branch_list(branch_list):
    if is_empty_llist(branch_list):
        raise TxValidationError("branch_list is empty or contains empty objects.")


def validated_branch_list(branch_list):
    validate_branch_list(branch_list)  # returns True or ValueError Exception
    return [list(branch) for branch in branch_list]


def validate_style_attribs(**attribs):
    for _name, _value in attribs.items():
        if isinstance(_value, (bool, type(None))):
            continue
        else:
            raise TxValidationError(
                f"Style flag {_name} must be bool or None. Got: {_name}={_value!r}"
            )

def validated_list_like(list_like: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    """
        list_like: list or tuple
        returns it converted (type cast) to list
    """
    if list_like is None:
        return []

    if isinstance(list_like, (list, tuple)):
        if isinstance(list_like, tuple):
            return list(list_like)
        else:
            return list_like
    else:
        raise TxValidationError(f'An object of type list or tuple was expected. Received: {repr_type(list_like)}')

def is_valid_keyid(id_key: object, allow_empty: bool = False) -> TypeGuard[Hashable]:
    if isinstance(id_key, Hashable):
        return True if allow_empty else not is_empty(id_key)
    return False

def validated_header_titles(
    titles: list[Hashable] | tuple[Hashable, ...] | None,
) -> list[Hashable]:
    titles = validated_list_like(titles)  # (tuple -> list, None -> [], Any other -> exception )
    for title in titles:
        if not is_valid_keyid(title, allow_empty=True):
            raise TxValidationError(
                f'The headers contain an unhashable title: {repr(title)}')
    return titles
