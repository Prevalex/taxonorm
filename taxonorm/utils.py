"""
domain aware helpers
"""
import re
from typing import Iterable

from taxonorm._introspection import inspect_upper_name, inspect_name
from taxonorm.common import IpStyle, LpStyle, tStyler


def get_bools_from_hints(s: str,
                         variables: Iterable[str],
                         fill_missing: bool = True) -> dict[str, bool | None]:
    """Parse boolean style hints from *s*.

    Tokens use ``VAR``/``NVAR`` for each upper-cased variable name. Tokens are
    separated by underscores or string boundaries; a dot is also accepted on
    the right side.

    s = "LP_K_NH_S.xlsx"
    print(parse_bool_hints(s, variables=("k", "i", "s", "h", "lp", "ip", "t")))
    # {'k': True, 'i': None, 's': True, 'h': False, 'lp': True, 'ip': None, 't': None}
    """
    upper_to_var = {v.upper(): v for v in variables}
    alternation = "|".join(map(re.escape, upper_to_var.keys()))
    pattern = re.compile(rf'(^|_)(N?)({alternation})(?=(_|$|\.))')

    out_dict: dict[str, bool | None] = {}

    if fill_missing:
        out_dict.update({v: None for v in variables})

    for m in pattern.finditer(s):
        neg, name_upper = m.group(2), m.group(3)
        var = upper_to_var[name_upper]
        value = neg == ""
        out_dict[var] = value

    return out_dict


def get_style_from_hints(hint_string) -> tStyler:
    """Parse a mnemonic taxonomy style from a string, usually a file name.

    Args:
        hint_string: may contain ``IP``, ``H``, ``NH``, ``K``, ``NK``, ``T``,
            ``NT`` or ``LP``, ``H``, ``NH``, ``I``, ``NI``, ``S``, ``NS``.

    Returns:
        An ``IpStyle`` or ``LpStyle`` decoded from the hints. Later hints
        override earlier ones, so ``_H_NH`` means ``header=False``.
    """

    hints = get_bools_from_hints(hint_string, ("lp", "ip", "h", "k", "i", "s", "t"))

    if isinstance(hints['lp'], bool) and isinstance(hints['ip'], bool):
        raise ValueError(
            f"{inspect_upper_name()}|{inspect_name()}: {hint_string!r} "
            "contains both LP and IP style hints. Specify only one style."
        )

    if hints['lp'] is None and hints['ip'] is None:
        raise ValueError(
            f"{inspect_upper_name()}|{inspect_name()}: {hint_string!r} "
            "does not contain an LP or IP style hint. Specify one style."
        )

    ip_style = bool(hints['ip'])

    styler: tStyler
    if ip_style:
        styler = IpStyle(header=bool(hints['h']), keys=bool(hints['k']), tabbed=bool(hints['t']))
    else:
        styler = LpStyle(header=bool(hints['h']), ids=bool(hints['i']), sparse=bool(hints['s']))

    return styler


def branch_till_eol(branch, eol=None):
    """Return the branch prefix up to the first *eol* marker."""
    if eol is None:
        return branch
    elif eol not in branch:
        return branch
    else:
        return branch[:branch.index(eol)]
