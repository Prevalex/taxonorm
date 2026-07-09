#! This taxonorm package module is designed to parse taxonomies of different styles and bring them to a unified style.

"""Parse supported tabular taxonomy styles into the unified ``Taxonomy`` model."""
import warnings

from collections.abc import Hashable, Callable, Iterable
from dataclasses import asdict
from typing import Any

from taxonorm._validation import is_empty
from taxonorm._tables import trim_llist_sublists, deduplicated_llist, sorted_llist
from taxonorm._sequences import is_empty_list

from taxonorm.common import IpStyle, LpStyle, DEFAULT_LEAF_KEY, tStyler, STYLE_ACCURACY
from taxonorm.chunks import restore_unique_ip_chunks
from taxonorm.serializer import complete_taxonomy
from taxonorm.stylers.style_lp_i import parse_lp_h_i_ns_taxonomy, parse_lp_nh_i_ns_taxonomy, parse_lp_h_i_s_taxonomy, \
    parse_lp_nh_i_s_taxonomy
from taxonorm.stylers.style_lp_ni import parse_lp_h_ni_ns_taxonomy, parse_lp_nh_ni_ns_taxonomy, \
    parse_lp_xh_ni_s_taxonomy

from taxonorm.validation import (validate_leaf_keys, validate_branch_list, validate_style_attribs)
from taxonorm.errors import TxInputValidationError, TxParsingError, TxValidationError
from taxonorm.input_validation import ValidationIssue, ValidationReport, validate_input
from taxonorm.model import Taxonomy


# When almost all rows match a style signature, the remaining rows are treated
# as input errors and handled by validation/parser diagnostics later.


def is_lp_without_id(llist: Iterable[Iterable[Any]], header: bool) -> bool:
    """Heuristically detect LP-without-ID data that can look like IP data.

    LP without IDs usually has chains that start with one non-empty item:

    'one'
    'one', 'two'
    'one', 'two', 'three'

    IP and LP-with-ID rows usually start with two non-empty items:

    'id1', 'leaf1'
    'id1', 'id2', 'leaf2'
    'id2', 'leaf1', 'leaf2'

    Values can be unhashable, so this function uses lists instead of sets.
    """
    start_with_singles: list = []
    start_with_pair: list = []

    if header:
        header_idx = 0
    else:
        header_idx = -1

    for idx, row in enumerate(llist):
        row = list(row)

        if idx == header_idx or is_empty_list(row):
            continue

        first = row[0]
        non_empty_count = sum(1 for x in row if not is_empty(x))

        if non_empty_count == 1 and not is_empty(first):
            # print(f'{idx}: {row}')
            # print('non_empty_count == 1')
            if first not in start_with_singles:
                start_with_singles.append(first)
        elif non_empty_count == 2 and not is_empty(first):
            # print(f'{idx}: {row}')
            # print('non_empty_count == 2')
            if first not in start_with_pair:
                start_with_pair.append(first)

    diff_list = [x for x in start_with_pair if x not in start_with_singles]

    # dbg(f'{start_with_singles=}; {start_with_pair=}; {diff_list=}')

    return len(start_with_singles) > len(diff_list)


def is_sparse(branch_list: list[list[Any]]) -> bool:
    """Return whether rows look like sparse LP data.

    Sparse LP rows usually contain an ID and exactly one non-empty leaf value,
    often with empty cells between them.
    """

    # Skip the first row because it may be a header and can distort small
    # samples.
    single_leaf_branch_count = sum(
        1 for branch in branch_list[1:] if sum(1 for leaf_value in branch[1:] if not is_empty(leaf_value)) == 1)

    factor_one = ((1 - single_leaf_branch_count / (len(branch_list) - 1)) <= STYLE_ACCURACY)

    # Count rows with at least one empty cell between the ID and the leaf value.
    sparse_branch_count = sum(
        1 for branch in branch_list[1:]
        if any(is_empty(leaf_value) for leaf_value in branch[:next((i for i, y in enumerate(branch)
                                                                    if not is_empty(y)), len(branch))])
    )

    factor_two = ((1 - sparse_branch_count / len(branch_list)) > STYLE_ACCURACY)

    # dbg(f'{single_leaf_branch_count=} of {len(branch_list)-1}: {factor_one=} and {factor_two=}')
    return factor_one and factor_two


def guess_taxonomy_style(branch_list: list[list[Any]],
                leaf_keys: list[Hashable] | None = None) -> tStyler:
    """Guess a taxonomy style from table shape and optional leaf keys."""
    warnings.warn(
        "guess_taxonomy_style() is deprecated; use sniffer.guess_style()",
        DeprecationWarning,
        stacklevel=2,
    )

    if leaf_keys is None:
        leaf_keys = [DEFAULT_LEAF_KEY]

    ip_style = own_keys = own_ids = header = sparse = tabbed = False

    validate_branch_list(branch_list)
    validate_leaf_keys(leaf_keys)
    key_list = list(leaf_keys)

    # LP-with-ID rows usually have unique first-column IDs. Repeated
    # first-column values make IP more likely.
    start_list = []
    for branch in branch_list:
        if is_empty_list(branch):
            continue
        else:
            start_list.append(branch[0])

    lp_guess_error = 1 - len(set(start_list)) / len(start_list)
    ip_style = lp_guess_error > STYLE_ACCURACY

    if ip_style:
        first_row = branch_list[0]
        rest = branch_list[1:]

        # Look for leaf keys after the first column; the first column may be an ID.
        keys_in_header = any(h in key_list for h in first_row[1:])

        keys_in_body = any(
            any(cell in key_list for cell in row[1:])
            for row in rest if row
        )

        if keys_in_header or keys_in_body:
            own_keys = True
            if keys_in_header and not keys_in_body:  # ip keyed w/header
                header = True
            else:  # ip, keyed, wo/header
                header = False
        else:
            own_keys = False
            # For IP without keys, treat the first row as a header when its
            # first cell does not repeat below in the same position.
            if branch_list[0][0] in start_list[1:]:
                header = False
            else:
                header = True

    else:
        if is_sparse(branch_list):
            sparse = True
        else:
            sparse = False

        # In LP-with-ID, column 0 contains unique IDs, so header detection uses
        # the second column instead.
        header = False
        if branch_list:
            if branch_list[0]:
                if sum(1 for leaf_value in branch_list[0] if not is_empty(leaf_value)) > 2:
                    column_header_n2 = branch_list[0][1]
                    if all(branch[1] != column_header_n2 for branch in branch_list[1:] if len(branch) > 1):
                        header = True

        if is_lp_without_id(branch_list, header):
            own_ids = False
        else:
            own_ids = True

    # LP without IDs can be misdetected as IP without own keys, so refine that
    # specific case with a second heuristic.
    if ip_style and not own_keys:
        if is_lp_without_id(branch_list, header):
            ip_style = False
            sparse = False
            own_ids = False

    styler: tStyler
    if ip_style:
        styler = IpStyle(header=header, keys=own_keys, tabbed=tabbed)
    else:
        styler = LpStyle(header=header, ids=own_ids, sparse=sparse)
    return styler

def select_parser(styler: tStyler) -> Callable:
    """Select a parser function for the declared style.

    Args:
        styler: style descriptor with parser flags.

    Returns:
        A parser function with the standard ``parser(branch_list, leaf_keys)``
        signature.
    """

    match styler:

        # --- IP ---

        # IP_H_K_T
        case IpStyle(header=True, keys=True, tabbed=True):
            from taxonorm.stylers.style_ip import parse_ip_h_k_t_taxonomy
            return parse_ip_h_k_t_taxonomy

        # IP_H_K_NT
        case IpStyle(header=True, keys=True, tabbed=False):
            from taxonorm.stylers.style_ip import parse_ip_xh_k_xt_taxonomy
            return parse_ip_xh_k_xt_taxonomy

        # IP_NH_K
        case IpStyle(header=False, keys=True, tabbed=_):
            from taxonorm.stylers.style_ip import parse_ip_xh_k_xt_taxonomy
            return parse_ip_xh_k_xt_taxonomy

        # IP_H_NK
        case IpStyle(header=True, keys=False, tabbed=_):
            from taxonorm.stylers.style_ip import parse_ip_h_nk_xt_taxonomy
            return parse_ip_h_nk_xt_taxonomy

        # IP_NH_NK
        case IpStyle(header=False, keys=False, tabbed=_):
            from taxonorm.stylers.style_ip import parse_ip_nh_nk_xt_taxonomy
            return parse_ip_nh_nk_xt_taxonomy

        # --- LP ---

        # LP_H_I_S
        case LpStyle(header=True, ids=True, sparse=True):
            return parse_lp_h_i_s_taxonomy

        # LP_H_I_NS
        case LpStyle(header=True, ids=True, sparse=False):
            return parse_lp_h_i_ns_taxonomy

        # LP_H_NI_S
        case LpStyle(header=True, ids=False, sparse=True):
            return parse_lp_xh_ni_s_taxonomy

        # LP_H_NI_NS
        case LpStyle(header=True, ids=False, sparse=False):
            return parse_lp_h_ni_ns_taxonomy

        # LP_NH_I_S
        case LpStyle(header=False, ids=True, sparse=True):
            return parse_lp_nh_i_s_taxonomy

        # LP_NH_I_NS
        case LpStyle(header=False, ids=True, sparse=False):
            return parse_lp_nh_i_ns_taxonomy

        # LP_NH_NI_S
        case LpStyle(header=False, ids=False, sparse=True):
            return parse_lp_xh_ni_s_taxonomy

        # LP_NH_NI_NS
        case LpStyle(header=False, ids=False, sparse=False):
            return parse_lp_nh_ni_ns_taxonomy

        case _:
            raise TxParsingError(f"Style {styler} is not supported.")


def trim_string_cells(branch_list: list[list[Any]]) -> list[list[Any]]:
    return [
        [cell.strip() if isinstance(cell, str) else cell for cell in branch]
        for branch in branch_list
    ]


def trim_string_leaf_keys(leaf_keys: list[Hashable]) -> list[Hashable]:
    return [
        leaf_key.strip() if isinstance(leaf_key, str) else leaf_key
        for leaf_key in leaf_keys
    ]


def parse_taxonomy(branch_list: list[list[Any]], *,
                   styler: tStyler,
                   leaf_keys: list[Hashable],
                   sort_cvt: Callable | str | None = 'auto',
                   eol: Any = None,
                   restore_ip_chunks: bool = False,
                   validate: bool = True,
                   max_validation_issues: int = 100,
                   validation_source: str | None = None) -> Taxonomy:

    if eol is not None:
        trim_llist_sublists(branch_list, eol=eol, remove_empty=True)

    branch_list = trim_string_cells(branch_list)
    leaf_keys = trim_string_leaf_keys(leaf_keys)

    if validate:
        validate_input(
            branch_list,
            styler=styler,
            leaf_keys=leaf_keys,
            max_issues=max_validation_issues,
            source=validation_source,
        ).raise_for_errors()
    else:
        validate_style_attribs(**asdict(styler))

    branch_list = deduplicated_llist(branch_list)
    parser = select_parser(styler)

    try:
        taxonomy = parser(branch_list=branch_list, leaf_keys=leaf_keys, header=styler.header)
        if restore_ip_chunks:
            if not isinstance(styler, IpStyle):
                raise TxParsingError("IP chunk restoration is available only for IP styles")
            taxonomy = restore_unique_ip_chunks(taxonomy)
        taxonomy = complete_taxonomy(taxonomy)
        taxonomy = sorted_llist(taxonomy, stop=-1, sort_cvt=sort_cvt, headtail=1 if styler.header else 0)  # ??? head_tail ???
        return Taxonomy.from_branches(taxonomy)
    except (TxParsingError, TxValidationError) as error:
        if not validate:
            raise
        report = ValidationReport(
            style="_".join(styler.hints),
            source=validation_source,
            checked_rows=len(branch_list),
            issues=(
                ValidationIssue(
                    code="parser.rejected_input",
                    message=str(error),
                    expected="data matching the declared style",
                ),
            ),
        )
        raise TxInputValidationError(report) from error
