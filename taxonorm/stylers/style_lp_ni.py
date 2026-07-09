#lp ni parser

from __future__ import annotations

from typing import Any
from collections.abc import Hashable
from collections import defaultdict, deque

import math
import re

from taxonorm._sequences import is_empty_list
from taxonorm.errors import TxParsingError, TxValidationError
from taxonorm.model import Taxonomy
from taxonorm.stylers.refiller import lp_sparse_to_dense

def _normalize_leaf_value(leaf_value: Any) -> Any:
    """Normalize a string leaf value by trimming and collapsing whitespace."""
    if isinstance(leaf_value, str):
        leaf_value = leaf_value.strip()
        leaf_value = re.sub(r"\s+", " ", leaf_value)
    return leaf_value

def _build_tree(branch_list: list[list[str]]) -> dict[tuple[Any, ...], list[Any]]:
    """Build a child map from leaf-name paths."""

    children: defaultdict[tuple[Any, ...], set[Any]] = defaultdict(set)
    for branch in branch_list:
        branch = [_normalize_leaf_value(leaf) for leaf in branch if leaf and _normalize_leaf_value(leaf)]
        for i in range(len(branch)):
            parent = tuple(branch[:i])
            children[parent].add(branch[i])
    
    return {k: sorted(v, key=lambda x: str(x).lower()) for k, v in children.items()}

def _count_per_depth(children: dict[tuple[Any, ...], list[Any]]):
    """Count nodes at each tree depth."""
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
            depth = len(child)
            depth_count[depth] += 1
            q.append((child, depth))
    max_depth = max(depth_count.keys()) if depth_count else 0
    return depth_count, max_depth

def _round_up_nice(n: int, round_to: int = 10):
    """Round upward to the next configured bucket size."""
    if n <= 0:
        return round_to
    return int(math.ceil(n / round_to) * round_to)

def _plan_level_ranges(depth_count: dict[int, int], slack: float = 0.10, round_to: int = 10, start_from: int = 1):
    """Plan inclusive numeric ID ranges for each depth."""
    ranges = {}
    next_start = start_from
    for depth in sorted(depth_count.keys()):
        need = depth_count[depth]
        cap = _round_up_nice(int(math.ceil(need * (1.0 + slack))), round_to=round_to)
        start = next_start
        end = start + cap - 1
        ranges[depth] = (start, end)
        next_start = end + 1
    return ranges

def _assign_ids_dfs(children, ranges):
    """Assign an integer ID to each name path using depth-specific ranges."""
    id_map = {}
    counters = {d: ranges[d][0] for d in ranges}

    def _dfs(node_tuple: tuple[str, ...]):
        for name in children.get(node_tuple, []):
            child = node_tuple + (name,)
            depth = len(child)
            cur = counters[depth]
            start, end = ranges[depth]
            if cur > end:
                raise RuntimeError(f"Level {depth} range overflowed: [{start}, {end}]")
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
    """Parse LP-without-ID paths and assign numeric IDs.

    IDs are allocated in depth-specific contiguous ranges. Each range is sized
    from the number of nodes at that depth, expanded by ``slack`` and rounded
    up by ``round_to``. Nodes are then assigned IDs by DFS order, so siblings
    tend to receive nearby IDs. Moving a node to a different depth will change
    its generated ID.
    """

    leaf_key=leaf_keys[0]

    children = _build_tree(branch_list)
    depth_count, _ = _count_per_depth(children)
    if not depth_count:
        return[]

    ranges = _plan_level_ranges(depth_count, slack=slack, round_to=round_to, start_from=1)
    id_map = _assign_ids_dfs(children, ranges)

    taxonomy = []
    emitted = set()

    if header is None:
        raise TxParsingError(f"header parameter is not set ({header=}) but is required")
    elif header:
        header_idx = 0
    else:
        header_idx = -1

    for idx, branch in enumerate(branch_list):

        if idx == header_idx or is_empty_list(branch):
            continue

        branch = [_normalize_leaf_value(_leaf) for _leaf in branch if _leaf and _normalize_leaf_value(_leaf)]
        for i in range(1, len(branch)+1):
            chain = [id_map[tuple(branch[:k])] for k in range(1, i+1)]
            key = tuple(chain)
            if key in emitted:
                continue
            emitted.add(key)
            taxonomy.append(chain + [{leaf_key: branch[i-1]}])

    taxonomy.sort(key=lambda br: (len(br)-1, tuple(br[:-1])))
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
            f"Expected a Taxonomy object, got: {type(taxonomy).__name__}"
        )
    if slack < 0:
        raise TxValidationError("slack cannot be negative")
    if round_to <= 0:
        raise TxValidationError("round_to must be positive")

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
                f"Level {depth} range overflowed: [{start}, {end}]"
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
                             header: bool|None=None) -> list[list[Any]]:
    header = True
    taxonomy = parse_lp_ni_taxonomy(branch_list, leaf_keys, header=header)
    return taxonomy


def parse_lp_nh_ni_ns_taxonomy(branch_list: list[list[Any]],
                               leaf_keys: list[Hashable],
                               header: bool|None=None) -> list[list[Any]]:
    header = False
    taxonomy = parse_lp_ni_taxonomy(branch_list, leaf_keys, header=header)
    return taxonomy


def parse_lp_xh_ni_s_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]:

    dense_table = lp_sparse_to_dense(branch_list=branch_list,
                                     header=header,
                                     ids=False)

    taxonomy = parse_lp_ni_taxonomy(dense_table, leaf_keys, header=False)
    return taxonomy


def parse_lp_nh_ni_s_taxonomy(branch_list: list[list[Any]],
                              leaf_keys: list[Hashable],
                              header: bool|None=None) -> list[list[Any]]:
    raise NotImplementedError('Parser LpStyle(ids=False, sparse=True) is not yet implemented')
