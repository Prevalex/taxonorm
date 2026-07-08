"""
domain aware helpers
"""
import re
from typing import Iterable

from alx.cons import inspect_upper_name, inspect_name
from taxonorm.common import IpStyle, LpStyle, tStyler


def get_bools_from_hints(s: str,
                         variables: Iterable[str],
                         fill_missing: bool = True) -> dict[str, bool | None]:
    """
    GPT5: Разбирает строку s и извлекает булевы значения для переменных.
    Токены: 'VAR'/'NVAR' для каждой переменной VAR (имя в верхнем регистре).
    Разделители: '_' или границы строки; справа также допускается '.'.

    # --- пример для parse_bool_hints ---
    s = "LP_K_NH_S.xlsx"
    print(parse_bool_hints(s, variables=("k", "i", "s", "h", "lp", "ip", "t")))
    # {'k': True, 'i': None, 's': True, 'h': False, 'lp': True, 'ip': None, 't': None}
    """
    # карта: верхний регистр -> оригинальное имя
    upper_to_var = {v.upper(): v for v in variables}
    # регулярка: (N?)(AB|CD|...) с учётом границ
    alternation = "|".join(map(re.escape, upper_to_var.keys()))
    pattern = re.compile(rf'(^|_)(N?)({alternation})(?=(_|$|\.))')

    out_dict: dict[str, bool | None] = {}

    if fill_missing:
        out_dict.update({v: None for v in variables})

    for m in pattern.finditer(s):
        neg, name_upper = m.group(2), m.group(3)
        var = upper_to_var[name_upper]
        value = (neg == "")  # N → False, отсутствие N → True
        out_dict[var] = value

    return out_dict


def get_style_from_hints(hint_string) -> tStyler:
    """
    Разбирает строку (например, имя файла), где мнемонически закодирован стиль таксономии
    Args:
        hint_string: строка может содержать: 'IP', 'H', 'NH', 'K', 'NK', 'T', 'NT'
                                        или: 'LP', 'H', 'NH', 'I', 'NI', 'S', 'NS'
        что кодирует IP/LP Style, Header, own_keys, own_ids, sparse, tabbed
    Returns:
        слварь с булевыми значениями мнемоник (hints).
        * LP и IP не могут быть указаны одновременно
        * Мнемоники ближе к концу строки затирают предыдущие: _H_NH ознаает {'h':False,...}
        * Если мнемоника не указана, то значение соответствующего атрибута будет None
    """

    hints = get_bools_from_hints(hint_string, ("lp", "ip", "h", "k", "i", "s", "t"))

    if isinstance(hints['lp'], bool) and isinstance(hints['ip'], bool):
        raise ValueError(f'{inspect_upper_name()}|{inspect_name()}: В строке {repr(hint_string)} одновременно указан '
                         f'стиль LP и IP. Необходимо указать только один из них.')

    if hints['lp'] is None and hints['ip'] is None:
        raise ValueError(f'{inspect_upper_name()}|{inspect_name()}: В строке {repr(hint_string)} не указан стиль '
                         f' LP или IP. Необходимо указать один из них.')

    ip_style = bool(hints['ip'])

    styler: tStyler
    if ip_style:
        styler = IpStyle(header=bool(hints['h']), keys=bool(hints['k']), tabbed=bool(hints['t']))
    else:
        styler = LpStyle(header=bool(hints['h']), ids=bool(hints['i']), sparse=bool(hints['s']))

    return styler


def branch_till_eol(branch, eol=None):
    """
    Возвращает ветку от начала и до первого появления eol. Если eol=None, то обрезание ветки не производится.
    """
    if eol is None:
        return branch
    elif eol not in branch:
        return branch
    else:
        return branch[:branch.index(eol)]
