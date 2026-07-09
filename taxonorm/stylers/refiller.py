from __future__ import annotations
from typing import Any

from taxonorm._sequences import is_empty_list
from taxonorm.validation import validated_branch_list, validate_style_attribs


def _resize_stamp(stamp_: list, carrier_: list) -> list:
    len_c = len(carrier_)
    len_s = len(stamp_)
    if len_c == len_s:
        return stamp_[:]  # [:] to make a copy, same as list(stamp_)
    elif len_c < len_s:
        return stamp_[:len_c]
    else:
        return stamp_[:] + [None] * (len_c - len_s)

def lp_sparse_to_dense(branch_list: list[list[Any]],
                       header: bool | None = None,
                       ids: bool | None = None
                       ) -> list[list[Any]]:

    branch_list = validated_branch_list(branch_list)
    validate_style_attribs(header=header, ids=ids)

    if header:
        header_idx = 0
    else:
        header_idx = -1

    stamp = [None]
    dense_table = list()

    for idx, branch in enumerate(branch_list):
        if idx == header_idx or is_empty_list(branch):
            continue

        if ids:
            _id_ = branch[0]
            carrier = branch[1:]
        else:
            carrier = branch[:]

        stamp = _resize_stamp(stamp, carrier)

        for index, leaf_value in enumerate(carrier):
            if leaf_value is None:
                pass
            else:
                stamp[index] = leaf_value
                stamp = stamp[:index + 1] + [None] * len(stamp[index + 1:])
                break

        if ids:
            dense_table.append([_id_] + stamp)
        else:
            dense_table.append(stamp)

    return dense_table
