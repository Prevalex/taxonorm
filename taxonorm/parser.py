#! This taxonorm package module is designed to parse taxonomies of different styles and bring them to a unified style.

"""
Модуль parser преобразует табличные ветви поддерживаемых стилей в единое
внутреннее представление :class:`Taxonomy` (см. README.md).
"""
import warnings

from collections.abc import Hashable, Callable, Iterable
from dataclasses import asdict
from typing import Any

from alib.validation import is_empty
from alib.tables import trim_llist_sublists, deduplicated_llist, sorted_llist 
from alib.sequences import is_empty_list

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


# ТО есть, если 98% строк удовлетворяют особенностям формата, а два процента - не удовлетворяют, то мы считаем эти
# два процента ошибкой формата и разберемся с этими ошибками позже.


def is_lp_without_id(llist: Iterable[Iterable[Any]], header: bool) -> bool:
    """
    Старается Определить, является яли формат таксономии форматом LP no ID. Это вариант LP который очень похож на IP.
    А эта функция предназначена для проверки уже распознанного IP формата и пытается определить - не является ли формат,
    распознанный как IP на самом деле - форматом LP без ID

    Отличия между lp и ip в этом случае только в том, что в lp без id, цепочки будут начинаться, как правило, с одного
    элемента:

    'one' < всего один элемент
    'one', 'two'
    'one', 'two', 'three'

    А в lp с id или в ip - как правило, будет два элемента в начальном подсписке ветки
    IP:
    ---
    'id1', 'leaf1' < два элемента
    'id1', 'id2', 'leaf2'
    ..
    LP ID:
    -----
    'id1', 'leaf1'  < два элемента
    'id2', 'leaf1', 'leaf2'

    Поэтому вот что мы сделаем. Мы соберем два множества:
    Первое - start_with_single - множество из первых элементов тех цепочек, где всего один элемент
    Второе - start_with_pair - множество из первых элементов тех цепочек, где два элемента
    Затем мы вычтем из второго множества первое. И тогда во втором множестве останутся только те цепочки, которые
    начинались с пары значений. Если после этого - len(start_with_single) > len(start_with_pair), то будем считать
    что у нас lp таксономия без id.
    * Помним, что листья могут быть нехэшируемыми и мы не можем применять множества и поэтому будем работать со
      списками. Соответствующую функцию _extract_lists любезно предоставил ChatGPT5
    """
    start_with_singles: list = []
    start_with_pair: list = []

    if header:
        header_idx = 0
    else:
        header_idx = -1

    for idx, row in enumerate(llist):
        row = list(row)

        # Пропускаем заголовок и пустые ветки
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

    # diff_list = элементы start_with_pair, которых нет в start_with_singles
    diff_list = [x for x in start_with_pair if x not in start_with_singles]

    # dbg(f'{start_with_singles=}; {start_with_pair=}; {diff_list=}')

    return len(start_with_singles) > len(diff_list)


def is_sparse(branch_list: list[list[Any]]) -> bool:
    """
    Используется для проверки подтипа sparse.
    В sparse каждая строка (ветка) содержит ровно два непустых значения ID и значение
    листа (категории). Функция вычисляет процент строк, которые не удовлетворяют этому правилу, в общем числе
    строк (веток) и если он меньше допустимой ошибки - то считает что формат sparse. Для большей уверенности, он
    проверяет, что бы какой - то процент строк (меньший допустимой ошибки) был таким, что между id и значением листа
    были бы пустые значения (на то он и sparse). И тогда - это точно sparse.

    Parameters
    ----------
    branch_list

    Returns
    -------
    True/False: Sparse/No Sparse
    """

    # Найдем число строк, где кроме первого id есть еще всего одно непустое значение, то есть ищем соответствие
    # формату sparse. При этом - пропустим первую строку, така как она может быть заголовком и при малом числе строк
    # исказит результат теста
    single_leaf_branch_count = sum(
        1 for branch in branch_list[1:] if sum(1 for leaf_value in branch[1:] if not is_empty(leaf_value)) == 1)

    # первый фактор = True - если процент строк, которые нарушают формат меньше или равен допустимой ошибке
    factor_one = ((1 - single_leaf_branch_count / (len(branch_list) - 1)) <= STYLE_ACCURACY)

    # найдем число строк, где между id и значением листа есть хоть одно пустое значение
    # * эту строку придумал GPT 5, я оставил как есть
    sparse_branch_count = sum(
        1 for branch in branch_list[1:]
        if any(is_empty(leaf_value) for leaf_value in branch[:next((i for i, y in enumerate(branch)
                                                                    if not is_empty(y)), len(branch))])
    )

    # второй фактор = True - если процент характерных строк с пустыми промежутками _не_меньше_ чем допустимая ошибка
    factor_two = ((1 - sparse_branch_count / len(branch_list)) > STYLE_ACCURACY)

    # dbg(f'{single_leaf_branch_count=} of {len(branch_list)-1}: {factor_one=} and {factor_two=}')
    return factor_one and factor_two


def guess_taxonomy_style(branch_list: list[list[Any]],
                leaf_keys: list[Hashable] | None = None) -> tStyler:
    warnings.warn(
        "guess_taxonomy_style() is deprecated; use sniffer.guess_style()",
        DeprecationWarning,
        stacklevel=2,
    )
    """
    Пытается угадать стиль таксономии, наличие заголовка в ней и для lp таксономии пытается распознать sparse формат.

    Затем пытается найти own_keys
    own_keys = True   если таксономия содержит ключи из списка leaf_keys
    own_keys = False  если таксономия не содержит ключей из списка leaf_keys

    Затем пытается найти заголовок
    Если own_keys = True,  то определяется наличие заголовка (header= True/False) по наличию ключей в заголовке и
                отсутствии их под заголовком
    Если own_keys = False, то определить наличие заголовка невозможно и возвращается header = None.

    Если ip_style = True, то это, скорее всего,  IP таксономия (IdPath with Leaves)
    Если ip_style = False, то это, скорее всего, LP таксономия (LeafPath with IDs)

    Parameters
    ----------
    branch_list
    leaf_keys

    Returns
    -------
    (own_keys, header, ip_style)

    """

    if leaf_keys is None:
        leaf_keys = [DEFAULT_LEAF_KEY]

    ip_style = own_keys = own_ids = header = sparse = tabbed = False

    validate_branch_list(branch_list)
    validate_leaf_keys(leaf_keys)
    key_list = list(leaf_keys)

    # Проверим стиль - ip или lp. У lp формата c ID первый столбец - идентификаторы. И они уникальны, то есть не повторяются
    # в разных строках.
    start_list = []
    for branch in branch_list:
        if is_empty_list(branch):
            continue
        else:
            start_list.append(branch[0])

    lp_guess_error = 1 - len(set(start_list)) / len(start_list)
    ip_style = lp_guess_error > STYLE_ACCURACY

    ## Мы проверили - повторяются ли вниз по списку первые элементы каждой строки, или они уникальны для каждой строки.
    ## Если уникальны (с допустимой ошибкой), значит это LP_I. Если нет - то это IP, или LP NI.
    ## ! Пока что считаем, что это IP

    if ip_style:
        first_row = branch_list[0]
        rest = branch_list[1:]

        # Есть ли ключи в заголовке (начиная с позиции 1 — допускаем, что ID может быть первым)?
        keys_in_header = any(h in key_list for h in first_row[1:])

        # Есть ли ключи в других строках (начиная с позиции 1)?
        keys_in_body = any(
            any(cell in key_list for cell in row[1:])
            for row in rest if row
        )

        if keys_in_header or keys_in_body:  # Это точно ip_style таксономия с ключами
            own_keys = True
            if keys_in_header and not keys_in_body:  # ip keyed w/header
                # ip, keyed, w/header
                header = True
            else:  # ip, keyed, wo/header
                header = False
        else:
            own_keys = False
            # Значит это ip без ключей, но мы не знаем - с заголовком или без.
            # Будем считать, что если первый элемент первой строки не повторяется ниже ни водной строке на том же месте,
            # то первая [0] строка - это заголовок
            if branch_list[0][0] in start_list[1:]:
                header = False
            else:
                header = True

    else:  # Это lp.

        # Теперь нужно проверить его на sparse формат. В sparse формате есть только по два непустых значения в
        # каждой строке. И между ними часто бывают пустые значения

        if is_sparse(branch_list):
            sparse = True
        else:
            sparse = False

        # Наконец, проверяем наличие заголовка. Считаем, что если первый элемент нулевой строки больше не повторяется
        # нигде в ниже в этом столбце - то нулевая строка - это заголовок. Мы не проверяем нулевой как было в ip,
        # потому что в нулевом столбце содержатся id, а они по определению не повторяются, потому что уникальны.

        header = False
        if branch_list:
            if branch_list[0]:
                # В sparse формате число непустых элементов в строке = 2. В dense такого строгого правила нет, но мы
                # будем считать что в заголовке должно быть более двух элементов
                if sum(1 for leaf_value in branch_list[0] if not is_empty(leaf_value)) > 2:
                    column_header_n2 = branch_list[0][1]  # берем заголовок второго столбца (индекс==1)
                    if all(branch[1] != column_header_n2 for branch in branch_list[1:] if len(branch) > 1):
                        # раз элемент первой позиции нулевой строки нигде дальше не повторяется - то считаем его заголовком
                        header = True

        #  Ок. Теперь проверим еще и на own_id
        if is_lp_without_id(branch_list, header):
            own_ids = False
        else:
            own_ids = True

    # здесь уточним параметры на основании приоритетных. А приоритет у  ip_style.
    # если ip_style = True,  то sparse Всегда False
    # если ip_style = False, то own_keys всегда False
    # if ip_style:
    #    sparse = False
    # else:
    #    own_keys = False

    ## Ну вот, допустим мы определились. Но есть вариант LP который очень похож на IP. Это - LP без ID. И если это так,
    ## То тогда код выше, определили этот LP без ID Как IP без Own_Keys. Поэтому, если это именно этот случай - то
    # посмотрим внимательнее.

    # отличия между lp и ip в этом случае только в том, что в lp без id, цепочки будут начинаться, как правило, с одного
    # элемента:

    # 'one' < всего один элемент
    # 'one', 'two'
    # 'one', 'two', 'three'

    # А в lp с id или в ip - как правило, будет два элемента в начальном подсписке ветки
    # IP:
    # ---
    # 'id1', 'leaf1' < два элемента
    # 'id1', 'id2', 'leaf2'
    # ...
    # LP ID:
    # -----
    # 'id1', 'leaf1'  < два элемента
    # 'id2', 'leaf1', 'leaf2'

    # Поэтому вот что мы сделаем. Мы соберем два множества:
    # Первое - start_with_single - множество из первых элементов тех цепочек, где всего один элемент
    # Второе - start_with_pair - множество из первых элементов тех цепочек, где два элемента
    # Затем мы вычтем из второго множества первое. И когда во втором множестве останутся только те цепочки, которые
    # начинались с пары значений. Если после этого - len(start_with_single) > len(start_with_pair), то будем считать
    # что у нас lp таксономия без id.
    # * Помним, что листья могут быть нехэшируемыми и мы не можем применять множества и поэтому будем работать со
    #   списками. Соответствующую функцию _extract_lists любезно предоставил ChatGPT5

    # if False and ip_style and not own_keys:
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
    """
    Выбирает функцию-парсер в зависимости от заданного стиля.

    Args:
        styler: объект класса tStyle, который хранит атрибуты стиля.
    Returns:
        Возвращает функцию-парсер. Все функции-парсеры предназначенные для назначения - имеют одинаковую сигнатуру:
        parser_function(branch_list, leaf_keys)
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
            raise TxParsingError(f"Стиль {styler} - не предусмотрен.")


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
                raise TxParsingError("Восстановление IP-обрезков доступно только для IP-стилей")
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
                    expected="данные, соответствующие заявленному стилю",
                ),
            ),
        )
        raise TxInputValidationError(report) from error
