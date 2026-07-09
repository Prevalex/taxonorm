# ip parser

from __future__ import annotations
from typing import Any

from collections.abc import Hashable

from taxonorm._introspection import inspect_location
from taxonorm._console import wrn
from taxonorm._validation import is_empty, is_valid_keyid
from taxonorm._sequences import is_empty_list

from taxonorm.validation import (validated_leaf_keys, validated_branch_list,
                                 validate_style_attribs)
from taxonorm.errors import TxParsingError


def parse_ip_xh_k_xt_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header:bool|None=None) -> list[list[Any]]:
    """Parse an IP table where keys are present in each row.

    Rows are shaped as ``id..., key1, value1, ...`` with optional empty cells.
    The output is the internal branch form ``id..., {leaf_key: value}``; the
    leaves dictionary always contains all requested ``leaf_keys``.
    """

    if header:
        header_idx = 0
    else:
        header_idx = -1

    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)

    key_set = list(leaf_keys)
    result = []

    for idx, branch in enumerate(branch_list):

        if idx == header_idx:
            continue

        if is_empty_list(branch):
            continue

        # Trim trailing empty cells, while preserving a final key without value.
        cleaned = list(branch)
        while cleaned and is_empty(cleaned[-1]):
            cleaned.pop()

        if cleaned and cleaned[-1] in key_set:
            pass
        elif len(cleaned) % 2 == 1 and cleaned[-2] in key_set:
            pass
        else:
            while cleaned and is_empty(cleaned[-1]):
                cleaned.pop()
        branch = cleaned

        first_key_index = None
        for i, val in enumerate(branch):
            if val in key_set:
                first_key_index = i
                break

        if first_key_index is None:
            raise TxParsingError(f"None of the keys {leaf_keys} were found in row: {branch}")

        raw_ids = [x for x in branch[:first_key_index] if not is_empty(x)]
        for i, item in enumerate(raw_ids):
            if not is_valid_keyid(item):
                raise TxParsingError(
                    f"ID {item!r} does not satisfy ID requirements. "
                    f"Position {i} in row: {branch}"
                )

        kv_raw = branch[first_key_index:]
        kv_dict = dict((key, None) for key in leaf_keys)

        i = 0
        while i < len(kv_raw):
            leaf_key = kv_raw[i]

            if not is_valid_keyid(leaf_key):
                raise TxParsingError(f"Invalid key {leaf_key!r} in branch: {branch!r}")
            if leaf_key in key_set:
                value = kv_raw[i + 1] if i + 1 < len(kv_raw) else None
                kv_dict[leaf_key] = value if not is_empty(value) else None
            else:
                wrn(
                    f"Key {leaf_key!r} is not present in leaf_keys {leaf_keys!r}. "
                    f"Branch: {branch!r}"
                )
            i += 2

        result.append(raw_ids + [kv_dict])
    return result


def parse_ip_h_k_t_taxonomy(branch_list: list[list[Any]],
                            leaf_keys: list[Hashable],
                            header: bool|None=None) -> list[list[Any]]:
    """Parse tabbed IP data with a header row containing leaf keys.

    id1,    id2,    id3,    ... ,idN,   Key1,   Key2,   ... KeyN
    id11,   id12,   id13,   ... ,id1N,  Val11,  Val12,  ... Val1N
    ...     ...     ...     ...  ...    ...     ...     ... ...
    idJ1,   idJ2,   idJ3,   ... ,idJN,  ValJ1,  ValJ2,  ... ValJN
    """

    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)

    header_row = branch_list[0]
    key_set = set(leaf_keys)

    try:
        first_key_index = next(i for i, col in enumerate(header_row) if col in key_set)
    except StopIteration:
        raise TxParsingError("None of the keys were found in the header")

    key_headers = header_row[first_key_index:]

    for kh in key_headers:
        if kh not in key_set:
            wrn(
                f"{inspect_location()}: header key {kh!r} is not present "
                f"in leaf_keys {leaf_keys}"
            )

    result = []
    for branch in branch_list[1:]:
        if is_empty_list(branch):
            wrn(f"{inspect_location()}: empty row ignored.")
            continue

        raw_ids = branch[:first_key_index]
        ids = [x for x in raw_ids if not is_empty(x)]
        for i, item in enumerate(ids):
            if not is_valid_keyid(item):
                raise TxParsingError(
                    f"ID {item!r} does not satisfy ID requirements. "
                    f"Position {i} in row: {branch}"
                )

        kv_values = branch[first_key_index:]
        kv_dict = dict()
        for key, val in zip(key_headers, kv_values):
            if key not in key_set:
                continue
            kv_dict[key] = val if not is_empty(val) else None

        for k in leaf_keys:
            if k not in kv_dict:
                kv_dict[k] = None

        result.append(ids + [kv_dict])

    return result


def parse_ip_nk_taxonomy(branch_list: list[list[Any]],
                         leaf_keys: list[Hashable],
                         header: bool|None=None) -> list[list[Any]]:

    """Parse IP data where rows store leaf values without explicit keys."""
    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)
    validate_style_attribs(header=header)

    if header is None:
        raise TxParsingError(f"header parameter is not set ({header=}) but is required")
    elif header:
        header_idx = 0
    else:
        header_idx = -1

    num_keys = len(leaf_keys)
    result = []

    for idx, branch in enumerate(branch_list):

        if idx == header_idx or is_empty_list(branch):
            continue

        if len(branch) < num_keys + 1:
            raise TxParsingError(
                f"Row is too short: {branch}. Length must be at least 1 "
                "greater than the key list length"
            )

        id_part = branch[:-num_keys]
        kv_part = branch[-num_keys:]

        while id_part and is_empty(id_part[-1]):
            id_part.pop()

        for i, item in enumerate(id_part):
            if not is_valid_keyid(item):
                raise TxParsingError(f"Invalid ID {item} at position {i} in row: {branch}")

        kv_dict = dict()
        for key, val in zip(leaf_keys, kv_part):
            kv_dict[key] = val if not is_empty(val) else None

        result.append(id_part + [kv_dict])
    return result


def parse_ip_h_nk_xt_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]:
    header = True
    return parse_ip_nk_taxonomy(branch_list=branch_list, leaf_keys=leaf_keys, header=header)


def parse_ip_nh_nk_xt_taxonomy(branch_list: list[list[Any]],
                               leaf_keys: list[Hashable],
                               header: bool|None=None) -> list[list[Any]]:
    header = False
    return parse_ip_nk_taxonomy(branch_list=branch_list, leaf_keys=leaf_keys, header=header)
