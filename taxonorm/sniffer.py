#!python

from typing import Any
from pathlib import Path
from collections.abc import Hashable
from collections import Counter

from alib.sequences import is_empty_list, count_non_empty, take_items_of_list_from_other_list
from alib.introspection import inspect_location
from alib.validation import is_empty
from alib.tables import read_llist_from_file, is_llist

from taxonorm.common import IpStyle, LpStyle, tStyler, SNIFFER_ACCURACY
from taxonorm.errors import TxValidationError, TxInternalError
from taxonorm.validation import validate_leaf_keys, validate_branch_list

def scan_right_tab(items: list) -> int:
    """
    Для строки вида:
     [222,223,1420,None,None,None,"Audio Accessories"]

    Возвращает индекс элемента сразу после первого участка None
    или:
        0 — если None отсутствует;
        -1 — если участок None заканчивается вместе со списком.
    """
    n = len(items)
    t = 0

    # Ищем начало первого участка None
    while t < n and not is_empty(items[t]):
        t += 1

    if t == n:
        return 0

    # Ищем конец этого участка
    while t < n and is_empty(items[t]):
        t += 1

    return -1 if t == n else t

def scan_key_occurrences(leaf_keys:list[Hashable], branch:list[Any]):
    """ Returns 1 if the keys are found in the branch, 0 otherwise."""
    return int(bool(take_items_of_list_from_other_list(leaf_keys, branch)))

def is_sparse_row(row: list[Any]) -> bool:
    """
    Определяет, соответствует ли строка (список) одному из sparse-форматов.

    Строка считается sparse, если:
     строка имеет одно непустое значение
     строка имеет два непустых значения, _и_ одно из них - первое в строке (индекс 0)
    """

    non_empty_indexes = [
        index
        for index, value in enumerate(row)
        if not is_empty(value)
    ]

    # Полностью пустая строка не считается sparse
    if not non_empty_indexes:
        return False

    # Вид 2: во всей строке только одно непустое значение
    if len(non_empty_indexes) == 1:
        return True

    # Вид 1: ровно два непустых значения,
    # первое обязательно находится в позиции 0.
    #
    # Допустимы варианты:
    # [ID, Value]
    # [ID, None, Value]
    # [ID, None, None, Value, None]
    if len(non_empty_indexes) == 2:
        first_index, _ = non_empty_indexes
        return first_index == 0

    return False


def is_t(tabs:list[int], rows:int):
    """ Is this taxonomy presented in tabular form? """
    count_tabs = Counter(tabs)
    most_tabs = count_tabs.most_common(1)
    # если индекс табуляции (первый элемент после разрыва из пустых элементов) - имеет индекс три и больше
    if most_tabs[0][0] > 2: # [id1, None, leaf1, leaf2, ..]
        # если индекс табуляции, который встречается чаще всего - встречается более чем в
        # SNIFFER_ACCURACY * rows числе строк
        if most_tabs[0][1] >= SNIFFER_ACCURACY * rows:
            return True
    return False


def is_lp_i(uniqs:list[int], rows:int):
    """ If the number of branches whose first element is not repeated at this location in other branches
        is greater than the specified quantity, then it is LP_I. Otherwise, it is IP or LP_NI """
    count_uniq = Counter(uniqs)
    if count_uniq[1] >= SNIFFER_ACCURACY * rows:
        return True
    else:
        return False


def is_lp_ni(inits:list[int], rows:int):
    """ If the taxonomy has branches with lengths of 1 and 2, it is an LP NI,
        otherwise, if there are only 2 or more, it is an IP"""
    count_init = Counter(inits)
    if count_init[1] > 0:
        if count_init[2] > 0:
            if count_init[2] >= count_init[1]:
                return True
    return False

def is_k(keys:list[int], rows:int):
    count_keys = Counter(keys)

    k_in_h = keys[0] > 0  # Are there any keys in the header?
    k_in_body = count_keys[1] >= SNIFFER_ACCURACY * rows # Are there any keys in most branches?
    return k_in_h, k_in_body


def is_h(branch_list:list[list[Any]]):

    if len(branch_list) < 1: # если нет строк
        return False

    if len(branch_list) < 2: # если всего одна строка
        return True

    if is_empty_list(branch_list[0]): # если пустая первая строка
        return True

    # Есть ли элементы первой строки, которые есть и во второй строке? (тогда и первая и вторая - ветки,
    # а не заголовок и ветка)
    have_common_elements  = scan_key_occurrences(branch_list[0], branch_list[1])   # 0 or 1

    if have_common_elements  > 0:
        return False
    else:
        return True

def is_lp_s_h(branch_list:list[list[Any]]) -> bool:
    """Correction for header detection in LP format

    Electronics,,           [0][0]
    ,Audio,,,               [1][1]

    or

    222,Electronics,,,       [0][0], [0][1]
    223,,Audio,,,            [1][0], [1][2]
    """

    if count_non_empty(branch_list[0]) == 1:
        if not is_empty(branch_list[0][0]):
            if count_non_empty(branch_list[1]) == 1:
                if not is_empty(branch_list[1][1]):
                    return False
    elif count_non_empty(branch_list[0]) == 2:
        if not is_empty(branch_list[0][0]) and not is_empty(branch_list[0][1]):
            if count_non_empty(branch_list[1]) == 2:
                if not is_empty(branch_list[1][0]) and not is_empty(branch_list[1][2]):
                    return False
    return True

def is_lp_ns_h(branch_list:list[list[Any]]) -> bool:
    """Correction for header detection in LP format

    Electronics,,           [0][0]
    Electronics,Audio,,,    [1][0], [1][1]; and [0][0] == [1][0]

    or

    222,Electronics,,,       [0][0], [0][1]
    223,Electronics,Audio,,  [1][0], [1][1], [1][2]; and  [0][1] == [1][1]
    """

    if count_non_empty(branch_list[0]) == 1:
        if not is_empty(branch_list[0][0]):
            if count_non_empty(branch_list[1]) == 2:
                if not is_empty(branch_list[1][0]) and not is_empty(branch_list[1][1]):
                    if branch_list[0][0] == branch_list[1][0]:
                        return False

    elif count_non_empty(branch_list[0]) == 2:
        if not is_empty(branch_list[0][0]) and not is_empty(branch_list[0][1]):
            if count_non_empty(branch_list[1]) == 3:
                if not is_empty(branch_list[1][0]) and not is_empty(branch_list[1][1]) and not is_empty(branch_list[1][2]):
                    if branch_list[0][1] == branch_list[1][1]:
                        return False
    return True


def is_s(sprs:list[int], rows:int):
    """ If most of the rows are sparse, we consider the taxonomy to be sparse. """
    count_sprs = Counter(sprs)
    return count_sprs[1] > SNIFFER_ACCURACY * rows


def guess_style(taxonomy: Path | str | list[list[Any]], leaf_keys:list[Hashable], cvt_dict:dict|None=None) -> tStyler:

    validate_leaf_keys(leaf_keys)

    style_dict:dict = {'ip':None, 'lp':None, 'header':None, 'keys':None, 'tabbed':None, 'ids':None,'sparse':None}

    keys = []  # numbers of keys found in each row
    tabs = []  # numbers of right tab in each row
    uniqs = []  # uniqs (1), non uniqs (0) id in this key
    inits = []  # all rows with length 1 and 2
    sprs = []   # all rows with sparse format

    idset = set()

    rows = 0

    if isinstance(taxonomy, (Path, str)):
        branch_list = read_llist_from_file(taxonomy, cvt_dict=cvt_dict)

    elif is_llist(taxonomy):
        branch_list = taxonomy
    else:
        raise TxValidationError('taxonomy is not Path, filename:str or list or lists')

    validate_branch_list(branch_list)

    for branch in branch_list:

        if len(branch) == 0:
            continue

        rows += 1

        tab = scan_right_tab(branch)

        id0 = 1 if (branch[0] not in idset) else 0
        idset.add(branch[0])

        key = scan_key_occurrences(leaf_keys, branch)

        spr = int(is_sparse_row(branch))

        # если примерно: то если единиц много больше двоек - это LP_NI
        # если точно:  двоек должно быть <= единиц)
        if len(branch) == 1:
            inits.append(1)
        # если примерно, то если двоек много больше единиц - это IP_NT / LP_I
        # (если точно - единиц вообще не должно быть)
        elif len(branch) == 2:
            inits.append(2)
        else:
            inits.append(0)

        keys.append(key)
        uniqs.append(id0)
        tabs.append(tab)
        sprs.append(spr)

    #  if the first elements of each branch are unique (in this column), then it is LP_I
    #  otherwise it is IP or LP_NI """
    if is_lp_i(uniqs, rows):

        style_dict['lp'] = True # LP
        style_dict['ids'] = True   # LP_I

    elif is_lp_ni(inits, rows):
        style_dict['lp'] = True # LP
        style_dict['ids'] = False  # LP_NI

    else: # IP
        style_dict['ip'] = True  # IP
        if is_t(tabs, rows):
            style_dict['tabbed'] = True # IP_T
        else:
            style_dict['tabbed'] = False # IP_NT

        k_h, k_b = is_k(keys, rows)

        if all((k_h, k_b)):
            style_dict['keys'] = True
            style_dict['header'] = False
        elif any((k_h, k_b)):
            style_dict['keys'] = True
            style_dict['header'] = True
        else:
            style_dict['keys'] = False

    if style_dict['header'] is None:
        style_dict['header'] = is_h(branch_list)

    if style_dict['lp']:
        if style_dict['sparse'] is None:
            if is_s(sprs, rows):
                style_dict['sparse'] = True
                style_dict['header'] = is_lp_s_h(branch_list)
            else:
                style_dict['sparse'] = False
                style_dict['header'] = is_lp_ns_h(branch_list)

        return LpStyle(header=style_dict['header'], ids=style_dict['ids'], sparse=style_dict['sparse'])

    elif style_dict['ip']:
        return IpStyle(header=style_dict['header'], keys=style_dict['keys'], tabbed=style_dict['tabbed'])

    else:
        raise TxInternalError(f'{inspect_location()} Internal error: Neither LP nor IP format selected')
