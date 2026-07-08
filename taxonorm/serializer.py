#! This module of the taxonorm package is intended to perform operations with taxonomy
from typing import Any
from collections.abc import Hashable, Callable

from alib.console import wrn
from alib.introspection import inspect_location, validate_type, repr_type
from alib.sequences import resized_list
from alib.tables import sorted_llist

from taxonorm.common import tMapper, tStyler, DEFAULT_LEAF_KEY, IpStyle, LpStyle
from taxonorm.chunks import split_to_unique_ip_chunks
from taxonorm.validation import validated_leaf_keys, validated_list_like, validated_header_titles
from taxonorm.errors import TxConversionError
from taxonorm.model import Taxonomy
from taxonorm.validation import is_valid_keyid

def complete_taxonomy(taxonomy):
    """
    Дополняет таксономию цепочками, которые явно в ней не указаны.
    Например, в таксономии могут быть вот такие цепочки:
    [
     [0,1,2,   {'@':'Leaf2'}],
     [0,1,2,3, {'@':'Leaf3'}],
     ]
    А цепочки для 0 и 1 - отсутствуют, потому что для них нет листьев.

    В таком случае данная функция вернет:
    [
     [0,1,2,   {'@':'Leaf2'}],
     [0,1,2,3, {'@':'Leaf3'}],
     [0, {}],
     [0, 1, {}],
     ]

    """
    # сначала сделаем перепись тех узлов, которые явно указаны в таксономии
    seen = set()
    for branch in taxonomy:
        body = list(branch[:-1])
        seen.add(tuple(body))

    # Теперь поищем узлы, которые не описаны явно в таксономии.  То есть те, которые присутствуют в путях, но для
    # которых нет их строк (цепочек) с путем.
    missed = list()
    for branch in taxonomy:
        body = list(branch[:-1])
        while len(body) > 0:
            if tuple(body) not in seen:
                missed.append(body + [dict()])
                seen.add(tuple(body))
            body.pop()

    # И явно добавим пропущенные цепочки (строки) узлов в таксономию. Не сортируем - это потом.
    return taxonomy + missed


def create_mapper(taxonomy: Taxonomy,
                  key_order: list[Hashable] | None = None,
                  sort_cvt: Callable | str | None = 'auto',
                  missed_leaf: Callable | None | str = 'auto') -> tMapper:
    """
    Возвращает объект класса Mapper: Mapper(idmap, keymap, min_width, max_width).
    Mapper устанавливает соответствие между id-путем к узлу и списком листьев этого узла. Mapper также устанавливает
    порядок следования листьев, задавая порядок следования ключей листьев - одинаковый для всех узлов.


    idmap: dict - словарь, где ключи - это пути по id, а значение - это список значений листьев этого пути.
            Пример: idmap = {...
                        (0,1,3,4):['Zero', 'One', 'Two', 'Three']
                        ...}
            А ключи листьев хранятся в словаре keymap. Также, словарь keymap задает порядок следования листьев, потому
            что он хранит индекс (порядковый номер) каждого ключа

    keymap: dict - словарь, где ключи - это ключи листьев, а значения - индекс этих листьев в списке idmap
            Пример: keymap = {'@':0, '#':1, '&':2, '$':3}
            Таким образом, в списке ['Zero', 'One', 'Two', 'Three'] - лист 'Zero' стоит на нулевой позиции, значит
            ключ имеет индекс 0, то есть это ключ '@'.

    min_width: int - минимальная длина путей в idmap
    max_width: int - максимальная длина путей в idmap
    ---
    Например, таксономия включала ветку: [0,1,2,3, {'@':'Zero', '#':'One', '&':'Two', '$':'Three'}]
    Тогда:

    idmap = {...
            (0,1,3,4):[Zero, One, Two, Three]
            ...}

    keymap = {'@':0, '#':1, '&':2, '$':3}

    Parameters
    ----------
    taxonomy - список таксономии
    key_order - предпочтительный порядок следования ключей
    sort_cvt - параметр, применяемый в sorted_llist(). Таксономия сортируется по последовательности ID узлов
    mising_leaf - указывает, что будет подставлено вместо значения листа узла, если листа с таким ключом нет в
                  этом узле.
                  Это может быть функция, которая принимает два аргумента: <ключ листа>, <путь id к данному узлу>
                  Это может быть None - тогда будет подставлен None
                  Это может быть "auto". Тогда будет подставлена строка "<id.path:leaf_key>", где id.path - это id путь
                  к узлу: '.'.join(list(map(str,id_path))

    Returns
    -------
    Mapper object
    """

    if not isinstance(taxonomy, Taxonomy):
        raise TxConversionError(
            f"Ожидался объект Taxonomy, получено: {type(taxonomy).__name__}"
        )
    if not taxonomy:
        raise TxConversionError("Таксономия пуста")

    return _create_mapper_from_branches(
        taxonomy.to_branches(),
        key_order=key_order,
        sort_cvt=sort_cvt,
        missed_leaf=missed_leaf,
    )


def _create_mapper_from_branches(branches: list[list[Any]],
                                 key_order: list[Hashable] | None = None,
                                 sort_cvt: Callable | str | None = 'auto',
                                 missed_leaf: Callable | None | str = 'auto') -> tMapper:
    def _missing_leaf_fun(leaf_key, id_path):
        return '<' + str(leaf_key) + ':' + '.'.join(list(map(str, id_path))) + '>'

    # Проверим корректность missing_leaf, установим auto, если указано
    if missed_leaf is None:
        pass
    elif isinstance(missed_leaf, str):
        if missed_leaf == 'auto':
            missed_leaf = _missing_leaf_fun
        else:
            raise TxConversionError(f": Аргумент missing_leaf должен быть функцией, None или"
                             f'строкой "auto". Получено missing_leaf={repr(missed_leaf)}')
    elif not callable(missed_leaf):
        raise TxConversionError(f'Аргумент missing_leaf должен быть функцией, строкой "auto" или None. '
                        f'Получено {type(missed_leaf)}={missed_leaf}')

    # Теперь проверим корректность keys_order
    if key_order is None:
        key_order = []
    else:
        try:
            key_order = validated_leaf_keys(key_order)
        except ValueError as err:
            raise TxConversionError(f"{str(err)}") from err

    if not branches:
        raise TxConversionError("Таксономия пуста")

    # Теперь отсортируем таксономию и дополним ее узлами, которые явно не указаны, но присутствуют в путях.
    # Сортировка может ускорить дальнейшую обработку и улучшить читаемость таксономии на выходе, но критически
    # необходима только для создания lp sparse форматов.
    branches = sorted_llist(
        branches, stop=-1, sort_cvt=sort_cvt, headtail=0
    )

    # Теперь создадим список ключей, которые присутствуют в таксономии. Те из них, что перечислены в keys_order -
    # будут идти в порядке, установленном в keys_order
    taxonomy_keys = []

    # Соберем все ключи по словарям листьев. Быстрее было использовать set.update, но мы постараемся сохранить тот
    # порядок в каком мы встретили ключи в таксономии. Заодно - найдем ширину таксономии (длину самой длинной ветки)
    max_width = 0
    for branch in branches:
        max_width = max(max_width, len(branch))
        for _key in branch[-1]:
            if _key not in taxonomy_keys:
                taxonomy_keys.append(_key)

    tx_keys_in_key_order = [_key for _key in key_order if _key in taxonomy_keys]
    rest_of_tx_keys = [_key for _key in taxonomy_keys if _key not in key_order]

    leaf_keys = tx_keys_in_key_order + rest_of_tx_keys

    # Теперь строим карту таксономии и ключей к ней.
    # Мы будем использовать кортежи путей id Как ключи. Мы можем это спокойно делать,
    # потому что все id прошли проверку при добавлении в Taxonomy.

    id_to_leaves_dict = dict()
    min_width = max_width

    for branch in branches:
        min_width = min(min_width, len(branch))
        branch_id_path = tuple(branch[:-1])

        branch_leaves = branch[-1]
        branch_leaf_list = []

        # создаем список значений листьев, заменяя отсутствующие значения в соответствии
        # с заданным параметром missed_leaf
        for _key in leaf_keys:
            if _key in branch_leaves:
                branch_leaf_list.append(branch_leaves[_key])
            elif missed_leaf is None:
                branch_leaf_list.append(None)
            else:
                branch_leaf_list.append(missed_leaf(_key, branch_id_path))

        ### branch_leaf_list = [branch[-1].get(_key, None) for _key in leaf_keys]
        id_to_leaves_dict[branch_id_path] = branch_leaf_list

    key_to_leaf_index_dict = dict([(_key, _idx) for _idx, _key in enumerate(leaf_keys)])

    min_width -= 1
    max_width -= 1

    return tMapper(idmap=id_to_leaves_dict, keymap=key_to_leaf_index_dict, min_width=min_width, max_width=max_width)


def serialize_ip_h_k_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width) + leaf_keys
    table = [titles]
    for ids, leaves in mapper.idmap.items():  # ids - это кортеж. Но resized_list превратит его в список
        row = resized_list(list(ids), mapper.max_width) + leaves
        table.append(row)
    return table


def serialize_ip_h_k_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width + len(leaf_keys) * 2) # ключ + лист на каждій ключ
    table = [titles] + serialize_ip_nh_k_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)
    return table


def serialize_ip_h_nk_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width + len(leaf_keys))  # лист на каждій ключ
    table = [titles] + serialize_ip_nh_nk_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)
    return table


def serialize_ip_h_nk_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width + len(leaf_keys))  # лист на каждій ключ
    table = [titles] + serialize_ip_nh_nk_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)
    return table


def serialize_ip_nh_k_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():  # ids - это кортеж. Но resized_list превратит его в список
        row = resized_list(list(ids), mapper.max_width) + [x for pair in zip(leaf_keys, leaves) for x in pair]
        table.append(row)
    return table


def serialize_ip_nh_k_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():  # ids - это кортеж. Мы должны будем превратить его в список
        row = list(ids) + [x for pair in zip(leaf_keys, leaves) for x in pair]
        table.append(row)
    return table


def serialize_ip_nh_nk_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():  # ids - это кортеж. Но resized_list превратит его в список
        row = resized_list(list(ids), mapper.max_width) + leaves
        table.append(row)
    return table


def serialize_ip_nh_nk_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():  # ids - это кортеж. Мы должны будем превратить его в список
        row = list(ids) + leaves
        table.append(row)
    return table

def serialize_ip_taxonomy(mapper: tMapper, styler: IpStyle, *, titles: tuple | list | None = None) -> list[list[Any]]:
    """
    Сериализует таксономию в ip формате.
    Parameters
    ----------
    mapper:Mapper - объект отображения таксономии
    styler: стиль формата таксономии - объект класса Styler
    titles:list|None - содержимое заголовка

    Returns
    -------
    возвращает таблицу-сериализацию в заданном формате
    """

    # проверяем mapper
    validate_type(mapper, 'mapper', tMapper)
    validate_type(styler, 'styler', IpStyle)

    # восстанавливаем leaf_keys (не проверяем, проверки сделаны в create_mapper())
    leaf_keys = validated_leaf_keys(list(mapper.keymap))

    # Проверяем titles и приводим к list. А именно: tuple преобразуем в list, None преобразуем в пустой список.
    titles = validated_header_titles(titles)

    match styler:

        case IpStyle(header=True, keys=True, tabbed=True):
            return serialize_ip_h_k_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=True, keys=True, tabbed=False):
            return serialize_ip_h_k_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=True, keys=False, tabbed=True):
            return serialize_ip_h_nk_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=True, keys=False, tabbed=False):
            return serialize_ip_h_nk_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=True, tabbed=True):
            return serialize_ip_nh_k_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=True, tabbed=False):
            return serialize_ip_nh_k_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=False, tabbed=True):
            return serialize_ip_nh_nk_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=False, tabbed=False):
            return serialize_ip_nh_nk_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

    raise TxConversionError(f"Неполностью определён IP-стиль: {styler!r}")


def serialize_lp_taxonomy(mapper: tMapper, styler: LpStyle, titles: tuple | list | None = None,
                          leaf_key: Hashable | None = None) -> list[list[Any]]:
    """
    Сериализует таксономию в lp формате.
    id, leaf path
    Parameters
    ----------
    mapper:Mapper - объект отображения таксономии
    styler: стиль формата таксономии - объект класса tStyle или None
    leaf_key: ключ, по которому выбираются значения листа для каждого узла
    titles:bool|list - включать ли заголовок. Может быть задан списком элементов заголовка

    Returns
    -------
    возвращает таблицу-сериализацию в заданном формате
    """

    # проверяем mapper
    validate_type(mapper, 'mapper', tMapper)
    validate_type(styler, 'styler', LpStyle)

    # ВОССТАНОВИМ СПИСОК  leaf_keys из mapper
    # восстанавливаем leaf_keys (не проверяем, проверки сделаны в crate_mapper())
    leaf_keys = list(mapper.keymap)

    # Проверяем titles и приводим к list. А именно: tuple преобразуем в list, None преобразуем в пустой список.
    titles = validated_list_like(titles)   # (tuple -> list, None -> [], Any other -> exception )
    # Если заголовок задан списком - проверяем элементы списка на хэшируемость, разрешаем пустые
    if styler.header:
        for title in titles:
            if not is_valid_keyid(title, allow_empty=True):
                raise TxConversionError(
                    f'Заголовок содержит нехэшируемый объект: {repr(title)}')

    # ПРОВЕРИМ КЛЮЧ, ПО КОТОРОМУ СОЗДАЕТСЯ LP ФОРМАТ
    # Проверим правильность ключа и подставим значение по умолчанию, если ключ явно не указан, а ключ по умолчанию
    # есть в таксономии и может быть использован
    if leaf_key not in leaf_keys:
        if leaf_key is not None:
            raise TxConversionError(f'Ключ {repr(leaf_key)} отсутствует в таксономии')
        else:  # leaf_key is None
            if DEFAULT_LEAF_KEY in mapper.keymap:
                wrn(f'{inspect_location()}: Ключ листа не задан (=None). Принимаем значение по '
                    f'умолчанию: {repr(DEFAULT_LEAF_KEY)=}')
                leaf_key = DEFAULT_LEAF_KEY
            else:
                raise TxConversionError(f'Ключ листа не задан (=None). Значение ключа по умолчанию '
                                 f'{repr(DEFAULT_LEAF_KEY)=} отсутствует в таксономии и не может быть использовано. '
                                 f'Укажите ключ явно.')
    # Создаем выходную таблицу
    table: list[list[Any]] = []
    if styler.header:
        titles = list(resized_list(titles, mapper.max_width + 1))
        # Включаем заголовок в таблицу
        table.append(titles)

    # Если требовался заголовок - он создан. Теперь генерируем строчка за строчкой
    leaf_index = mapper.keymap[leaf_key]  # сначала получим индекс листа в списке листьев
    for ids, leaves in mapper.idmap.items():
        _ids = list(ids)  # помним, что ids - это кортеж, но нам нужен список.
        if styler.ids:
            _row = [_ids[-1]]  # выбираем крайний справа идентификатор в пути идентификаторов - это идентификатор ветки
            _ins = 1 # если есть id, то листья на ветке идут с индекса 1, т.е. после id (индекс 0)
        else:
            # Если own_ids == False, то не включаем id в таксономию. Тогда они должны будут назначены при парсинге
            _row = []
            _ins = 0 # если нет id, то листья на ветке идут с индекса 0


        while _ids: # пока список не опустеет

            _ids_tuple = tuple(_ids)  # назад в кортеж, по которому будем искать лисит в словаре idmap маппера.

            if styler.sparse and _ids_tuple != ids:  # для sparse, оставляем None всем листьям, кроме последнего для
                # данного пути
                _leaf = None
            else:
                _leaf_list = mapper.idmap[_ids_tuple]
                _leaf = _leaf_list[leaf_index]

            _row.insert(_ins, _leaf)

            _ids.pop()

        table.append(_row)

    #print('\nserial:')
    #pp(table, width=180)
    return table


def serialize_taxonomy(taxonomy: Taxonomy, *, styler: tStyler,
                       leaf_key: Hashable | None = None,
                       headers: list | None = None,
                       key_order: list[Hashable] | None = None,
                       sort_cvt: Callable | str | None = 'auto',
                       missed_leaf: Callable | None | str = 'auto',
                       max_chunk_len: int | None = None) -> list[list[Any]]:
    if isinstance(styler, IpStyle):
        if max_chunk_len is None:
            mapper = create_mapper(
                taxonomy,
                key_order=key_order,
                sort_cvt=sort_cvt,
                missed_leaf=missed_leaf,
            )
        else:
            mapper = _create_mapper_from_branches(
                split_to_unique_ip_chunks(taxonomy, max_chunk_len=max_chunk_len),
                key_order=key_order,
                sort_cvt=sort_cvt,
                missed_leaf=missed_leaf,
            )
        return serialize_ip_taxonomy(mapper=mapper, styler=styler, titles=headers)
    elif isinstance(styler, LpStyle):
        if max_chunk_len is not None:
            raise TxConversionError("max_chunk_len поддерживается только для IP-стилей")
        mapper = create_mapper(
            taxonomy,
            key_order=key_order,
            sort_cvt=sort_cvt,
            missed_leaf=missed_leaf,
        )
        return serialize_lp_taxonomy(mapper=mapper, styler=styler, leaf_key=leaf_key, titles=headers)
    else:
        raise TxConversionError(f'Ожидался объект класса {IpStyle.__name__} '
                                f'или {LpStyle.__name__}. Получено: {repr_type(styler)}')
