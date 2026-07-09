# lp style

from __future__ import annotations
from typing import Any

from collections.abc import Hashable

from taxonorm._sequences import is_empty_list
from taxonorm._introspection import inspect_location
from taxonorm._validation import is_empty, is_valid_keyid

from taxonorm.common import DEFAULT_LEAF_KEY
from taxonorm.validation import (validated_leaf_keys, validated_branch_list,
                                 validate_style_attribs)

from taxonorm.stylers.refiller import lp_sparse_to_dense

from taxonorm.errors import TxParsingError


def parse_lp_i_taxonomy(branch_list: list[list[Any]],
                        leaf_keys: list[Hashable],
                        header: bool|None = None) -> list[list[Any]]:
    """Parse LP-with-ID rows into internal branch form.

    Input rows are usually imported from CSV/Excel and look like:

    [
        [id1, Name1],
        [id2, Name1, Name2],
        [id3, Name1, Name2, Name3],
        [id4, Name4],
        ...
    ]

    The first item is the category ID. The last non-empty name is the leaf
    value for that ID. IDs and terminal names must be unique. Trailing empty
    cells are ignored; empty cells inside the leaf path are invalid.
    """
    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)
    validate_style_attribs(header=header)

    key = leaf_keys[0]

    if key is None:
        key = DEFAULT_LEAF_KEY

    value_to_id_map: dict[Hashable, Any] = {}
    id_to_value_map: dict[Hashable, Any] = {}

    leaf_ids_lst: list[Any] = []
    leaf_values_lst: list[Any] = []

    if header:
        header_idx = 0
    else:
        header_idx = -1

    for idx, branch in enumerate(branch_list):

        if idx == header_idx or is_empty_list(branch):
            continue

        _id = branch[0]

        if not is_valid_keyid(_id):
            raise TxParsingError(
                f"ID {_id!r} does not satisfy ID requirements. Branch: {branch}"
            )

        while branch and is_empty(branch[-1]):
            branch.pop()

        leaf_path = branch[1:]
        leaf_value = branch[-1]

        if not leaf_path:
            f"{inspect_location()}: Empty branch #{idx}: {branch!r}"

        if any(is_empty(itm) for itm in leaf_path):
            raise TxParsingError(f"Empty leaf value in branch #{idx}: {branch!r}")

        if _id in id_to_value_map:
            raise TxParsingError(
                f"ID {_id!r} is duplicated in the taxonomy with leaves "
                f"{id_to_value_map[_id]!r} and {leaf_value!r}"
            )
        if isinstance(leaf_value, Hashable):
            if leaf_value in value_to_id_map:
                raise TxParsingError(
                    f"Leaf value (category) {leaf_value!r} is duplicated in the taxonomy: "
                    f"ID {_id!r} and ID {value_to_id_map[leaf_value]!r}\n"
                    "Check the taxonomy format for style: ip_style=False, sparse=False"
                )
            else:
                value_to_id_map[leaf_value] = _id
                id_to_value_map[_id] = leaf_value
        else:
            if leaf_value in leaf_values_lst:
                raise TxParsingError(
                    f"Leaf {leaf_value!r} is duplicated in the taxonomy with ID "
                    f"{_id!r} and ID {leaf_ids_lst[leaf_values_lst.index(leaf_value)]!r}"
                )
            else:
                leaf_ids_lst.append(_id)
                leaf_values_lst.append(leaf_value)
                id_to_value_map[_id] = leaf_value

    result = []
    for idx, branch in enumerate(branch_list):
        if idx == header_idx or is_empty_list(branch):
            continue
        leaf_path = branch[1:]
        leaf_value = branch[-1]

        _id_path = []

        for _leaf_val in leaf_path:
            try:
                _leaf_id = value_to_id_map[_leaf_val]
            except (KeyError, TypeError):
                try:
                    _leaf_id = leaf_ids_lst[leaf_values_lst.index(_leaf_val)]
                except ValueError:
                    raise TxParsingError(f"Taxonomy has no ID for leaf {_leaf_val!r}")

            _id_path.append(_leaf_id)

        _new_item = _id_path + [{key: leaf_value}]
        result.append(_new_item)

    return result


def parse_lp_h_i_ns_taxonomy(branch_list: list[list[Any]],
                             leaf_keys: list[Hashable],
                             header: bool|None=None) -> list[list[Any]]:
    header = True
    return parse_lp_i_taxonomy(branch_list, leaf_keys, header=header)


def parse_lp_nh_i_ns_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]:
    header = False
    return parse_lp_i_taxonomy(branch_list, leaf_keys, header=header)


def parse_lp_i_s_taxonomy(branch_list: list[list[Any]], leaf_keys: list[Hashable], header: bool | None = None
                          ) -> list[list[Any]]:

    dense_table = lp_sparse_to_dense(branch_list=branch_list,
                                     header=header,
                                     ids=True)

    return parse_lp_i_taxonomy(dense_table, leaf_keys, header=False)


def _parse_lp_i_s_taxonomy(branch_list: list[list[Any]], leaf_keys: list[Hashable], header: bool | None = None
                          ) -> list[list[Any]]:
    def resize_stamp(stamp_: list, carrier_: list) -> list:
        len_c = len(carrier_)
        len_s = len(stamp_)

        if len_c == len_s:
            return stamp_
        elif len_c < len_s:
            return stamp_[:len_c]
        else:
            return stamp_ + [None] * (len_c - len_s)

    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)

    validate_style_attribs(header=header)

    if header:
        header_idx = 0
    else:
        header_idx = -1

    dense_table = []
    stamp = [None]

    for idx, carrier in enumerate(branch_list):

        if idx == header_idx or is_empty_list(carrier):
            continue

        _id_ = carrier[0]
        carrier = carrier[1:]
        stamp = resize_stamp(stamp, carrier)

        for index, leaf_value in enumerate(carrier):
            if leaf_value is None:
                pass
            else:
                stamp[index] = leaf_value
                stamp = stamp[:index + 1] + [None] * len(stamp[index + 1:])
                break

        dense_table.append([_id_] + stamp)

    return parse_lp_i_taxonomy(dense_table, leaf_keys, header=False)


def parse_lp_h_i_s_taxonomy(branch_list: list[list[Any]],
                            leaf_keys: list[Hashable],
                            header: bool|None=None) -> list[list[Any]]:
    header = True
    return parse_lp_i_s_taxonomy(branch_list, leaf_keys, header=header)


def parse_lp_nh_i_s_taxonomy(branch_list: list[list[Any]],
                             leaf_keys: list[Hashable],
                             header: bool|None=None) -> list[list[Any]]:
    header = False
    return parse_lp_i_s_taxonomy(branch_list, leaf_keys, header=header)
