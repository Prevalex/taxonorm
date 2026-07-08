# lp style

from __future__ import annotations
from typing import Any

from collections.abc import Hashable

from alib.sequences import is_empty_list
from alib.introspection import inspect_location
from alib.validation import is_empty, is_valid_keyid

from taxonorm.common import DEFAULT_LEAF_KEY
from taxonorm.validation import (validated_leaf_keys, validated_branch_list,
                                 validate_style_attribs)

from taxonorm.stylers.refiller import lp_sparse_to_dense

from taxonorm.errors import TxParsingError


def parse_lp_i_taxonomy(branch_list: list[list[Any]],
                        leaf_keys: list[Hashable],
                        header: bool|None = None) -> list[list[Any]]:
    """
    Выполнит разор LP (id_LeafPath) таксономии (например, структуры товарных категорий) и преобразует ее в вид:
    [id1, ..., idN, {leaf_key1:value_key1_idN}]

    Входной формат выглядит таким образом. Это список списков, полученный импортом из excel или csv и имеющий
    следующий формат:
    [
        [id1, Name1],
        [id2, Name1, Name2],
        [id3, Name1, Name2, Name3],
        [id4, Name4],
        ...
    ]

    * Первый элемент в каждом подсписке - это идентификатор категории.
    * Последнее непустое имя в подсписке - это имя категории, чей идентификатор - первый элемент списка.
    * Идентификаторы и их имена - уникальны. Это значит, что,
    1) идентификаторы не повторяются,
    2) каждый идентификатор имеет имя, которое также не повторяется. То есть, например, id3 имеет имя Name3
       и никакой другой идентификатор не имеет такого имени.

    Примером такой таксономии может служить Google Product Categories. Вот отрывок из csv файла, содержащего список
    Google Product Categories
    ```
    222,Electronics,,,,,,
    278,Electronics,Computers,,,,,
    5254,Electronics,Computers,Barebone Computers,,,,
    331,Electronics,Computers,Computer Servers,,,,
    325,Electronics,Computers,Desktop Computers,,,,
    ````
    1) Последние элементы списка подряд могут быть пустыми. Это артефакты, возникающие при импорте из Excel или
    сохранении Csv из excel. Эти пустые элементы ('', None) отбрасываются при парсинге
    2) Внутри списка имен категорий пустые элементы не допускаются. Если они встречаются - возникает exception.
    Таким образом, Пустые элементы могут в любом количестве присутствовать только в конце подсписка и не могут
    чередоваться с непустыми. Они отбрасываются при парсинге.
    3) Все id - могут быть объектами любого типа, кроме None, но они должны быть хэшируемыми, и не должны быть
    пустыми значениями ('' или с len()==0). Это проверяется и вызывается exception, если что-то не так.

    Что делает функция.
    -------------------
    Поскольку каждому идентификатору соответствует уникальное имя в конце подсписка, мне необходимо произвести замену и заменить путь категории, составленный по именам на путь категории составленный по идентификаторам. В конце этого нового подсписка должен нажодится словарь, в котором по ключу key, переданному в функцию находится значение - имя категории по последнему идентификатору в строке.
    Например, для категории выше - это будет вот такой выход функции после вызова:
    taxonomy = parse_lp_taxonomy(google_cats, key='@')
    результат:
    taxonome = [
        ["222", 		{"@": "Electronics"}]
        ["222", "278", 		{"@": "Computers"}]
        ["222", "278", "5254", 	{"@": "Barebone Computers"}]
        ["222", "278", "331", 	{"@": "Computer Servers"}]
        ["222", "278", "325", 	{"@": "Desktop Computers"}]
    ]

    Parameters
    ----------
    branch_list - список категорий в формате для каждой категории [idX, leaf1, ..., leafX]
    key - ключ, который будет использован в словаре листьев выходного формата

    Returns
    -------
    таксономия в формате <id_path>,<leaves_dict>
    """
    branch_list = validated_branch_list(branch_list)
    leaf_keys = validated_leaf_keys(leaf_keys)
    validate_style_attribs(header=header)

    key = leaf_keys[0]

    if key is None:
        key = DEFAULT_LEAF_KEY

    # Строим map (словарь) категории: имя -> идентификатор
    value_to_id_map: dict[Hashable, Any] = {}  # будет хранить пары {leaf value: leaf id}
    id_to_value_map: dict[Hashable, Any] = {}  # будет хранить пары {leaf id: leaf value}

    leaf_ids_lst: list[Any] = []  # если leaf value не хэшируется, то его id помещается сюда
    leaf_values_lst: list[Any] = []  # если leaf value не хэшируется, то он помещается сюда с тем же смещением, что и leaf id в
    # leaves_ids

    if header:
        header_idx = 0
    else:
        header_idx = -1

    # Проходим по всем элементам, собираем map и проверяем корректность данных
    for idx, branch in enumerate(branch_list):

        # Пропускаем заголовок и пустые ветки
        if idx == header_idx or is_empty_list(branch):
            continue

        _id = branch[0]

        # Проверяем, что ID корректный
        if not is_valid_keyid(_id):
            raise TxParsingError(f"ID {repr(_id)} не соответствует требованиям к ID. "
                             f"Ветвь: {branch}")

        # Убираем пустые элементы в конце
        while branch and is_empty(branch[-1]):
            branch.pop()

        leaf_path = branch[1:]
        leaf_value = branch[
            -1]  # значение последнего листа в пути - это имя ветки, соответствующее id (потому что unique)

        # Проверяем наличие листьев
        if not leaf_path:
            f"{inspect_location()}: Пустая ветвь #{idx}: {repr(branch)}"

        # Проверка на пустые листья
        if any(is_empty(itm) for itm in leaf_path):
            raise TxParsingError(f"Пустое значение листа на ветви # {idx}: {repr(branch)}")

        # Добавляем имя категории в map с его ID
        if _id in id_to_value_map:
            raise TxParsingError(f"ID {repr(_id)} дублируется в таксономии с листьями "
                             f"{repr(id_to_value_map[_id])} и {repr(leaf_value)}")  # repr(branch[-1]) = Имя категории -
            # это последний элемент в пути.
        if isinstance(leaf_value, Hashable):
            if leaf_value in value_to_id_map:
                raise TxParsingError(f"Значение листа (категории) {repr(leaf_value)} дублируется в "
                                 f"таксономии: ID {repr(_id)} и ID {repr(value_to_id_map[leaf_value])}\n"
                                 f"Проверьте формат таксономии для стиля: ip_style=False, sparse=False")
            else:
                value_to_id_map[leaf_value] = _id
                id_to_value_map[_id] = leaf_value
        else:
            if leaf_value in leaf_values_lst:
                raise TxParsingError(f"Лист {repr(leaf_value)} дублируется в таксономии с ID "
                                 f"{repr(_id)} и ID {repr(leaf_ids_lst[leaf_values_lst.index(leaf_value)])}")
            else:
                leaf_ids_lst.append(_id)
                leaf_values_lst.append(leaf_value)
                id_to_value_map[_id] = leaf_value

    # Строим результат, заменяя имена на ID
    result = []
    for idx, branch in enumerate(branch_list):
        if idx == header_idx or is_empty_list(branch):
            continue
        # Все элементы, кроме последнего - это путь
        leaf_path = branch[1:]
        leaf_value = branch[-1]

        # Создаем новый путь, заменяя имена на ID
        _id_path = []

        for _leaf_val in leaf_path:
            try:
                _leaf_id = value_to_id_map[_leaf_val]
            except (KeyError, TypeError):
                try:
                    _leaf_id = leaf_ids_lst[leaf_values_lst.index(_leaf_val)]
                except ValueError:
                    raise TxParsingError(f"В таксономии отсутствует id для листа {repr(_leaf_val)}")

            _id_path.append(_leaf_id)

        # Добавляем словарь с ключом key и значением имени категории
        _new_item = _id_path + [{key: leaf_value}]
        result.append(_new_item)

    return result


def parse_lp_h_i_ns_taxonomy(branch_list: list[list[Any]],
                             leaf_keys: list[Hashable],
                             header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = True # принудительно
    return parse_lp_i_taxonomy(branch_list, leaf_keys, header=header)


def parse_lp_nh_i_ns_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = False  # принудительно
    return parse_lp_i_taxonomy(branch_list, leaf_keys, header=header)


def parse_lp_i_s_taxonomy(branch_list: list[list[Any]], leaf_keys: list[Hashable], header: bool | None = None
                          ) -> list[list[Any]]:

    dense_table = lp_sparse_to_dense(branch_list=branch_list,
                                     header=header,
                                     ids=True)

    # мы восстановили обычный lp формат и у нас уже есть функция конвертации ее в таксономию
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

    dense_table = []  # в dense_table восстанавливаем lp таксономию из lp sparse таксономии
    stamp = [None]

    for idx, carrier in enumerate(branch_list):

        # Пропускаем заголовок и пустые ветки
        if idx == header_idx or is_empty_list(carrier):
            continue

        _id_ = carrier[0]  # id просто переносим
        carrier = carrier[1:]
        stamp = resize_stamp(stamp, carrier)

        for index, leaf_value in enumerate(carrier):
            if leaf_value is None:
                pass
            else:
                stamp[index] = leaf_value  # переносим категорию
                stamp = stamp[:index + 1] + [None] * len(stamp[index + 1:])  # и проставляем None в ячейки справа от нее
                break

        dense_table.append([_id_] + stamp)

    # мы восстановили обычный lp формат и у нас уже есть функция конвертации ее в таксономию
    return parse_lp_i_taxonomy(dense_table, leaf_keys, header=False)


def parse_lp_h_i_s_taxonomy(branch_list: list[list[Any]],
                            leaf_keys: list[Hashable],
                            header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = True # прнудительно
    return parse_lp_i_s_taxonomy(branch_list, leaf_keys, header=header)


def parse_lp_nh_i_s_taxonomy(branch_list: list[list[Any]],
                             leaf_keys: list[Hashable],
                             header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = False # прнудительно
    return parse_lp_i_s_taxonomy(branch_list, leaf_keys, header=header)
