#lp ni parser

from __future__ import annotations

from typing import Any
from collections.abc import Hashable
from collections import defaultdict, deque

import math
import re

from alib.sequences import is_empty_list
from taxonorm.errors import TxParsingError, TxValidationError
from taxonorm.model import Taxonomy
from taxonorm.stylers.refiller import lp_sparse_to_dense

def _normalize_leaf_value(leaf_value: Any) -> Any:
    """ GPT-5:
    Нормализует значения листа, если это строка: выполняет strip(), а внутри все white spaces меняет на пробел.  
    # используется в  _build_tree > parse_lp_ni_taxonomy -> parse_lp_ni_taxonomy
    """
    if isinstance(leaf_value, str):
        leaf_value = leaf_value.strip()
        leaf_value = re.sub(r"\s+", " ", leaf_value)
    return leaf_value

def _build_tree(branch_list: list[list[str]]) -> dict[tuple[Any, ...], list[Any]]:
    """ GPT-5:
    Строим дерево из путей имен. Возвращает children: {tuple(names): [child_name,...]}
    Используется в: parse_lp_ni_taxonomy
    """

    children: defaultdict[tuple[Any, ...], set[Any]] = defaultdict(set)
    for branch in branch_list:
        branch = [_normalize_leaf_value(leaf) for leaf in branch if leaf and _normalize_leaf_value(leaf)]
        for i in range(len(branch)):
            parent = tuple(branch[:i])
            children[parent].add(branch[i])
    
    # сортируем детей лексикографически (можно заменить на свой порядок)
    return {k: sorted(v, key=lambda x: str(x).lower()) for k, v in children.items()}

def _count_per_depth(children: dict[tuple[Any, ...], list[Any]]):
    """ GPT-5:
    Считает число узлов на каждом уровне глубины.
    Используется в: parse_lp_ni_taxonomy
    """
    depth_count: defaultdict[int, int] = defaultdict(int)
    q: deque[tuple[tuple[Any, ...], int]] = deque([(tuple(), 0)])
    seen: set[tuple[Any, ...]] = {tuple()}
    while q:
        node, d = q.popleft()
        for ch in children.get(node, []):
            child = node + (ch,)
            if child in seen:
                continue
            seen.add(child)
            depth = len(child)  # корень на глубине 1
            depth_count[depth] += 1
            q.append((child, depth))
    max_depth = max(depth_count.keys()) if depth_count else 0
    return depth_count, max_depth

def _round_up_nice(n: int, round_to: int = 10):
    """ GPT-5:
    Округление вверх до ближайшего 'круглого' числа (10, 50, 100 ...).
    Используется в: _plan_level_ranges > parse_lp_ni_taxonomy
    """
    if n <= 0:
        return round_to
    return int(math.ceil(n / round_to) * round_to)

def _plan_level_ranges(depth_count: dict[int, int], slack: float = 0.10, round_to: int = 10, start_from: int = 1):
    """ GPT-5:
    Для каждого уровня (1..D) планирует [start, end] включительно.
    Возвращает dict: depth -> (start, end), также dict depth->next_id (счётчик).
    Используется в: parse_lp_ni_taxonomy
    """
    ranges = {}
    next_start = start_from
    for depth in sorted(depth_count.keys()):
        need = depth_count[depth]
        cap = _round_up_nice(int(math.ceil(need * (1.0 + slack))), round_to=round_to)
        start = next_start
        end = start + cap - 1
        ranges[depth] = (start, end)
        next_start = end + 1  # следующий блок начинается сразу после текущего
    return ranges

def _assign_ids_dfs(children, ranges):
    """ GPT-5:
    Назначает ID каждому узлу (tuple(names)) по DFS, используя блок текущей глубины. 
              https://en.wikipedia.org/wiki/Depth-first_search
    Возвращает id_map: {tuple(names): int_id}
    Используется в: parse_lp_ni_taxonomy
    """
    id_map = {}
    counters = {d: ranges[d][0] for d in ranges}  # следующий свободный ID для глубины d

    def _dfs(node_tuple: tuple[str, ...]):
        # назначить ID всем детям node_tuple
        for name in children.get(node_tuple, []):
            child = node_tuple + (name,)
            depth = len(child)  # глубина узла
            # выдаём следующий ID в блоке соответствующего depth
            cur = counters[depth]
            start, end = ranges[depth]
            if cur > end:
                raise RuntimeError(f"Переполнен диапазон уровня {depth}: [{start}, {end}]")
            id_map[child] = cur
            counters[depth] = cur + 1
            _dfs(child)

    _dfs(tuple())
    return id_map

def parse_lp_ni_taxonomy(branch_list: list[list[Any]],
                         leaf_keys: list[Hashable],
                         header: bool|None = None,
                         slack: float=0.10,
                         round_to: int=10) -> list[list[Any]]:
    """ GPT-5:
    Главная функция: пути по именам -> внутреннее представление с интервалами по уровням.
    Возвращает:
      internal: список веток вида [id1, id2, ..., {'@': last_name}]
      meta: {
         'ranges': {depth: (start, end)},
         'depth_count': {depth: count}
      }
    Args:
        branch_list: список подсписков, где подсписки - это, например, списки (под) категорий:
                paths=[
                    ['Electronics'],
                    ['Electronics', 'Arcade Equipment'],
                    ['Electronics', 'Arcade Equipment', 'Basketball Arcade Games'],
                    ['Electronics', 'Arcade Equipment', 'Pinball Machine Accessories'],
                    ...
                    ]
        leaf_keys: ключи листьев. Исползуется только leaf_keys[0]

        header: наличие заголовка True/False
        slack: запас в процентах (0.1==10%) который должен быть предусмотрен в каждом диапазоне уровня относительно
               текущего числа категорий на данном уровне. Это делается для создания запаса для добавления новых
               подкатегорий данного уровня, что бы не возникало необходимости переназначения идентификаторов или
               добавления в данный уровень идентификаторов из других (верхних, резервных диапазонов), если число
               вышло за пределы диапазона.В примере выше уровень 0 - это 'Electronics' (одна категория),
               а уровень 2 - это 'Basketball Arcade Games' и 'Pinball Machine Accessories' - 2 категории.

        round_to: До какой границы округлять каждый диапазон. Если до 10ти, то значит для категорий уровня, например, 0
                  будет выделен диапазон от 1 - до 10, а для второго уровня, например, от 11 - до 40

    Returns:
        internal: список веток вида [id1, id2, ..., {'@': last_name}]
        meta: {
         'ranges': {depth: (start, end)},
         'depth_count': {depth: count}
      }

    """
    """
Коротко:
--------
Считаем, сколько узлов на каждом уровне глубины.
Для уровня d выделяем непрерывный блок чисел такой ёмкости, чтобы было ceil(count[d] * (1 + запас)), округлив «вверх» 
до круглого числа. Обходим дерево DFS (или в нужном вам порядке) и выдаём ID из соответствующего блока текущего уровня 
по мере встречи узлов. Так дети одного родителя получают соседние ID (хорошо для локальности). Внутренние пути строим 
как цепочки выданных ID.

Плюсы:
------
Из ID сразу видна глубина (по интервалу).
Дети одного родителя идут компактными диапазонами (благодаря DFS-обходу: DFS = Depth-First Search:
https://en.wikipedia.org/wiki/Depth-first_search).
Хорошо сортируется (по глубине → по обходу).

Минусы/нюансы:
-------------
Если структура сильно вырастет на каком-то уровне и «запас» закончится, придётся:
a) расширять диапазон уровня (ломает «красоту» круглых интервалов), или
b) начать «доп. блоки» для уровня (например, добавлять второй диапазон), или
c) один раз «перенумеровать» этот уровень.

Перемещение узла по глубине → смена ID (как и в любой схеме, где ID кодирует глубину).
Если нужен глобально стабильный ID, можно хранить двойку: id (стабильный хэш пути) + code (ваши интервальные ID).

Рабочий код (Python)
--------------------
Ниже — «готовый» конструктор: берёт пути по именам, выделяет интервалы с запасом и строит внутренние ветки.
Порядок назначения внутри уровня — DFS по дереву (дети лексикографически), но можно легко поменять.

Запас (slack)  и «круглость» (round_to) настраиваются.
"""

    leaf_key=leaf_keys[0]

    children = _build_tree(branch_list)
    depth_count, _ = _count_per_depth(children)
    if not depth_count:
        #return [], {'ranges': {}, 'depth_count': {}}
        return[]

    ranges = _plan_level_ranges(depth_count, slack=slack, round_to=round_to, start_from=1)
    id_map = _assign_ids_dfs(children, ranges)

    # строим ветки
    taxonomy = []
    emitted = set()

    if header is None:
        raise TxParsingError(f"Параметр header не задан ({header=}, но требуется")
    elif header:
        header_idx = 0
    else:
        header_idx = -1

    for idx, branch in enumerate(branch_list):

        # пропускаем заголовок и пустые строки
        if idx == header_idx or is_empty_list(branch):
            continue

        branch = [_normalize_leaf_value(_leaf) for _leaf in branch if _leaf and _normalize_leaf_value(_leaf)]
        for i in range(1, len(branch)+1):
            #t = tuple(branch[:i])
            chain = [id_map[tuple(branch[:k])] for k in range(1, i+1)]
            key = tuple(chain)
            if key in emitted:
                continue
            emitted.add(key)
            taxonomy.append(chain + [{leaf_key: branch[i-1]}])

    taxonomy.sort(key=lambda br: (len(br)-1, tuple(br[:-1])))
    #meta = {'ranges': ranges, 'depth_count': dict(depth_count)}
    #return taxonomy, meta
    return taxonomy


def _count_taxonomy_per_depth(taxonomy: Taxonomy) -> dict[int, int]:
    depth_count: defaultdict[int, int] = defaultdict(int)
    for branch in taxonomy.iter_branches():
        depth_count[len(branch.path)] += 1
    return dict(depth_count)


def renumber_taxonomy_ids(
    taxonomy: Taxonomy,
    *,
    slack: float = 0.10,
    round_to: int = 10,
    start_from: int = 1,
) -> Taxonomy:
    """Return a copy of *taxonomy* with freshly assigned numeric node IDs.

    The tree shape, leaves, root order and sibling order are preserved. New IDs
    are unique across the whole taxonomy and are allocated by depth using the
    same rounded range planning as LP taxonomies without own IDs.
    """
    if not isinstance(taxonomy, Taxonomy):
        raise TxValidationError(
            f"Ожидался объект Taxonomy, получено: {type(taxonomy).__name__}"
        )
    if slack < 0:
        raise TxValidationError("Параметр slack не может быть отрицательным")
    if round_to <= 0:
        raise TxValidationError("Параметр round_to должен быть положительным")

    depth_count = _count_taxonomy_per_depth(taxonomy)
    if not depth_count:
        return Taxonomy()

    ranges = _plan_level_ranges(
        depth_count,
        slack=slack,
        round_to=round_to,
        start_from=start_from,
    )
    counters = {depth: start for depth, (start, _) in ranges.items()}
    id_map: dict[tuple[Hashable, ...], int] = {}
    renumbered = Taxonomy()

    for branch in taxonomy.iter_branches():
        depth = len(branch.path)
        current_id = counters[depth]
        start, end = ranges[depth]
        if current_id > end:
            raise TxValidationError(
                f"Переполнен диапазон уровня {depth}: [{start}, {end}]"
            )
        counters[depth] = current_id + 1
        id_map[branch.path] = current_id

        new_path = tuple(
            id_map[branch.path[:path_depth]]
            for path_depth in range(1, depth + 1)
        )
        renumbered.add_branch(new_path, branch.leaves)

    return renumbered


def parse_lp_h_ni_ns_taxonomy(branch_list: list[list[Any]],
                             leaf_keys: list[Hashable],
                             header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = True # принудительно
    taxonomy = parse_lp_ni_taxonomy(branch_list, leaf_keys, header=header)
    return taxonomy


def parse_lp_nh_ni_ns_taxonomy(branch_list: list[list[Any]],
                               leaf_keys: list[Hashable],
                               header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    header = False # принудительно
    taxonomy = parse_lp_ni_taxonomy(branch_list, leaf_keys, header=header)
    return taxonomy


def parse_lp_xh_ni_s_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости

    dense_table = lp_sparse_to_dense(branch_list=branch_list,
                                     header=header,
                                     ids=False)

    # теперь ставим header = False потому что lp_sparse_to_dense уже удалил заголовок
    taxonomy = parse_lp_ni_taxonomy(dense_table, leaf_keys, header=False)  # lp_sparse_to_dense уже удалил заголовок
    return taxonomy


def parse_lp_nh_ni_s_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]: # header - справочный параметр совместимости
    raise NotImplementedError('Parser LpStyle(ids=False, sparse=True) is not yet implemented')
