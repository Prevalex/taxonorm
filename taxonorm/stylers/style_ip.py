# ip parser

from __future__ import annotations
from typing import Any

from collections.abc import Hashable

from alib.introspection import inspect_location
from alib.console import wrn
from alib.validation import is_empty, is_valid_keyid
from alib.sequences import is_empty_list

from taxonorm.validation import (validated_leaf_keys, validated_branch_list,
                                 validate_style_attribs)
from taxonorm.errors import TxParsingError


def parse_ip_xh_k_xt_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header:bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    """ GPT-4

    Функция Принимает на входе два параметра branch_list и leaf_keys

    branch_list - это список веток (подсписков)
    leaf_keys - это список ключей листьев.

    Каждая ветка имеет формат:
    --------------------------
    [id1,id2,..id3, <empty...>, Key1, Value1,..., keyN, ValueN, <empty...>],
    где <empty...> - это пустые элементы (None), которые могут быть в любом количестве или не быть вообще.

    id и key не могут быть пустыми (len(id)!=0), не могут быть None, и должны быть хэшируемыми.

    В каждой ветке должно быть один или более id. Если id не обнаружены - возникает exception ValueError)

    Ключи Key и их значения Value - всегда идут в паре. Если у последнего ключа нет пары и этот ключ - последний элемент
    списка, то у него может не быть пары и ему присваивается значение None.

    Разных ключей может быть больше, чем указано в параметре leaf_keys, но при выполнении будут выбираться только те
    ключи, которые перечислены в leaf_keys. Если включены предупреждения (ctrl.warnings), то для ключей, отсутствующих
    в leaf_keys, но найденных в branch - будут выдаваться предупреждения.

    (!) Поскольку начало группы key-value детектируется по первому обнаруженному ключу из списка leaf_keys, то группа
    key-value любой из веток должна начинаться с ключа, который есть в leaf_keys. Либо - во всех branches (именно во
    всех жо единого), группы id и key-values должны быть разделены как минимум одним пустым элементом или None. В этом
    случае программа будет ориентироваться на эту границу, а не на первый обнаруженный ключ из числа leaf_keys.

    Если ключ присутствует в leaf_keys, но не найден в ветке (branch), то ему присваивается значение None

    Функция возвращает список вида:
    ------------------------------
    id1,id2,..idN, {key1:value1,...keyN:valueN}
    Словарь всегда содержит все ключи из leaf_keys.

    Ключи в подсписке могут идти в любом порядке, не обязательно в том, что в leaf_keys
    Если какой-то из ключей не встретился в строке, то его значение в словаре будет None.

    При этом:

    Элементы считаются id если они следуют до первого появления любого из ключей из leaf_keys
    Если в подсписке нет ни одного ключа, то весь подсписок считается состоящим из id, а все ключи:None

    На выходе, словарь упорядочен в том же порядке, в котором ключи следуют в leaf_keys

    Parameters
    ----------
    branch_list - Список ветвей или обрезков (chunks). Обрезки (части веток) допустимы только если все id в таксономии
    уникальны, то есть: 1) к каждому id в таксономии ведет только один путь и 2) каждый id, соответственно, встречается
    только на одном уровне таксономии.

    leaf_keys - список ключей листьев (на выходе - это ключи словаря листьев)

    Returns
    -------

    Возвращает список ветвей, где каждая ветвь это путь по id, который заканчивается словарем листьев последнего id,
    (последнего узла) на ветке: [id1,id11,id12,{key1:value1,...keyN:valueN}]
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

        # Очистим завершающий "хвост" из None/пустых значений,
        # оставив один элемент, если он может быть последним ключом
        cleaned = list(branch)
        while cleaned and is_empty(cleaned[-1]):
            cleaned.pop()

        # Допускаем: последний элемент — допустимый ключ без значения
        if cleaned and cleaned[-1] in key_set:
            pass  # оставляем
        elif len(cleaned) % 2 == 1 and cleaned[-2] in key_set:
            pass  # последняя пара: key, value
        else:
            # если хвост после очистки остался с одиночным None — удалим
            while cleaned and is_empty(cleaned[-1]):
                cleaned.pop()
        branch = cleaned  # обновим строку

        # Найти первую позицию ключа (игнорируя пустые)
        first_key_index = None
        for i, val in enumerate(branch):
            if val in key_set:
                first_key_index = i
                break

        if first_key_index is None:
            raise TxParsingError(f"Не найдено ни одного ключа из {leaf_keys} в строке: {branch}")

        # ID блок: до первого ключа, без пустых значений
        raw_ids = [x for x in branch[:first_key_index] if not is_empty(x)]
        for i, item in enumerate(raw_ids):
            if not is_valid_keyid(item):
                raise TxParsingError(f"ID {repr(item)} не соответствует требованиям к ID. Позиция {i} в строке: {branch}")

        # Ключ-значение пары (kv pairs)
        kv_raw = branch[first_key_index:]
        kv_dict = dict((key, None) for key in leaf_keys)

        i = 0
        while i < len(kv_raw):
            leaf_key = kv_raw[i]

            if not is_valid_keyid(leaf_key):
                raise TxParsingError(f"Недопустимый ключ: {repr(leaf_key)} в ветви: {repr(branch)}")
            if leaf_key in key_set:
                value = kv_raw[i + 1] if i + 1 < len(kv_raw) else None
                kv_dict[leaf_key] = value if not is_empty(value) else None
            else:
                wrn(f"Ключ {repr(leaf_key)} не входит в список ключей {repr(leaf_keys)}. Ветвь: {repr(branch)}")
            i += 2

        result.append(raw_ids + [kv_dict])
    return result


def parse_ip_h_k_t_taxonomy(branch_list: list[list[Any]],
                            leaf_keys: list[Hashable],
                            header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    """
    Аналогична parse_ip_taxonomy_with_header с тем отличием, что теперь у нас входные данные всегда табулированы и у
    этой таблицы есть заголовок (первая строка). В этой строке заголовки id могут быть, могут не быть, но всегда есть
    заголовки столбцов, где хранятся значения ключей. А заголовок столбца значений содержит сам ключ:

    id1,    id2,    id3,    ... ,idN,   Key1,   Key2,   ... KeyN
    id11,   id12,   id13,   ... ,id1N,  Val11,  Val12,  ... Val1N
    ...     ...     ...     ...  ...    ...     ...     ... ...
    idJ1,   idJ2,   idJ3,   ... ,idJN,  ValJ1,  ValJ2,  ... ValJN

    В этом случае мы также определяем начало группы ключей по ключу в заголовке из числа полученных, но значения ключа
    выбираем из столбца с заголовком в виде данного ключа.

    Parameters
    ----------
    branch_list - список ветвей (подсписков)
    leaf_keys - список ключей листьев

    Returns
    -------
    Возвращает список ветвей, где каждая ветвь это путь по id, который заканчивается словарем листьев последнего id,
    (последнего узла) на ветке: [id1,id11,id12,{key1:value1,...keyN:valueN}]
    """

    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)

    header_row = branch_list[0]
    key_set = set(leaf_keys)

    # Найти позицию первого ключа в заголовке
    try:
        first_key_index = next(i for i, col in enumerate(header_row) if col in key_set)
    except StopIteration:
        raise TxParsingError("Ни один из ключей не найден в заголовке")

    # ID-колонки — все до первого ключа
    #id_headers = header_row[:first_key_index]  # ДА, id_headers дальше пока что не используется. Но пусть будет
    key_headers = header_row[first_key_index:]

    # Проверка, что все ключи в key_headers — валидны (опционально)
    for kh in key_headers:
        if kh not in key_set:
            wrn(f"{inspect_location()}: Ключ {repr(kh)} заголовка не найден в списке ключей {leaf_keys}")

    result = []
    for branch in branch_list[1:]:
        if is_empty_list(branch):
            wrn(f"{inspect_location()}: Пустая строка проигнорирована.")
            continue  # пропуск пустых строк

        # Считываем ID-часть
        raw_ids = branch[:first_key_index]
        ids = [x for x in raw_ids if not is_empty(x)]
        for i, item in enumerate(ids):
            if not is_valid_keyid(item):
                raise TxParsingError(f"ID {repr(item)} не соответствует требованиям к ID: Позиция {i} в строке: {branch}")

        # Построить словарь ключей и значений
        kv_values = branch[first_key_index:]
        kv_dict = dict()
        for key, val in zip(key_headers, kv_values):
            if key not in key_set:
                continue  # на случай постороннего заголовка
            kv_dict[key] = val if not is_empty(val) else None

        # Добавим недостающие ключи, если они отсутствуют
        for k in leaf_keys:
            if k not in kv_dict:
                kv_dict[k] = None

        # Сохраняем результат
        result.append(ids + [kv_dict])

    return result


def parse_ip_nk_taxonomy(branch_list: list[list[Any]],
                         leaf_keys: list[Hashable],
                         header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости

    """ GPT-4:
    Эта функция вызывается, как и предыдущие parse_ip... и возвращает тот же результат, но работает с упрощенными
    данными. Больше нет ключей в подсписках или заголовках. Просто мы теперь считаем, что в каждом подсписке, его
    последние элементы - это значения ключей, которые мы передали в функцию.

    Соответственно мы просто отсекаем последние элементы по числу ключей и назначаем эти значения ключам.
    Мы потом по прежнему проверяем, что бы строки были непустыми (то есть как минимум длиной по числу ключей + 1 и
    проверяем что бы id удовлетворяли требованиям: не были пустыми и были хэшируемыми (is_valid())

    Parameters
    ----------
    branch_list - список ветвей (подсписков)
    leaf_keys - список ключей листьев

    Returns
    -------
    Возвращает список ветвей, где каждая ветвь это путь по id, который заканчивается словарем листьев последнего id,
    (последнего узла) на ветке: [id1,id11,id12,{key1:value1,...keyN:valueN}]
    """
    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)
    validate_style_attribs(header=header)

    if header is None:
        raise TxParsingError(f"Параметр header не задан ({header=}, но требуется")
    elif header:
        header_idx = 0
    else:
        header_idx = -1

    num_keys = len(leaf_keys)
    result = []

    for idx, branch in enumerate(branch_list):

        # пропускаем заголовок и пустые строки
        if idx == header_idx or is_empty_list(branch):
            continue

        if len(branch) < num_keys + 1:
            raise TxParsingError(f"Строка слишком короткая: {branch}. Длина должна быть как минимум на 1 "
                               f"больше длины списка ключей")

        id_part = branch[:-num_keys]
        kv_part = branch[-num_keys:]

        while id_part and is_empty(id_part[-1]):
            id_part.pop()

        # Проверка ID-части
        for i, item in enumerate(id_part):
            if not is_valid_keyid(item):
                raise TxParsingError(f"Неверный ID {item} на позиции {i} в строке: {branch}")

        # Создаём словарь ключей
        kv_dict = dict()
        for key, val in zip(leaf_keys, kv_part):
            kv_dict[key] = val if not is_empty(val) else None

        result.append(id_part + [kv_dict])
    return result


def parse_ip_h_nk_xt_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = True # принудительно
    return parse_ip_nk_taxonomy(branch_list=branch_list, leaf_keys=leaf_keys, header=header)


def parse_ip_nh_nk_xt_taxonomy(branch_list: list[list[Any]],
                               leaf_keys: list[Hashable],
                               header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = False # принудительно
    return parse_ip_nk_taxonomy(branch_list=branch_list, leaf_keys=leaf_keys, header=header)
