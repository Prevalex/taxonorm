"""Measure Taxonomy against the former full-path branch table."""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter
from typing import Any

from taxonorm import Taxonomy, import_taxonomy
from taxonorm.common import LpStyle
from taxonorm.model import BranchTable
from taxonorm.pathfinder import samples_dir


DEFAULT_SOURCE = (
    samples_dir
    / "Google"
    / "Original"
    / "en-US"
    / "taxonomy-with-ids.en-US.csv"
)


def _as_int_when_possible(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return str(value)


def deep_size(value: object, seen: set[int] | None = None) -> int:
    """Approximate retained Python memory while counting shared objects once."""
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        return 0
    seen.add(identity)

    size = sys.getsizeof(value)
    if isinstance(value, Mapping):
        return size + sum(
            deep_size(key, seen) + deep_size(item, seen)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return size + sum(deep_size(item, seen) for item in value)

    slots = getattr(type(value), "__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    for slot in slots:
        if hasattr(value, slot):
            size += deep_size(getattr(value, slot), seen)
    return size


def mib(size: int) -> float:
    return size / (1024 * 1024)


def make_deep_branches(depth: int = 200) -> BranchTable:
    """Create one chain containing *depth* nodes."""
    if depth < 1:
        raise ValueError("depth must be positive")
    branches: BranchTable = []
    path: list[int] = []
    for node_id in range(depth):
        path.append(node_id)
        branches.append([*path, {"name": f"node-{node_id}"}])
    return branches


def make_wide_branches(width: int = 5000) -> BranchTable:
    """Create a root with *width* direct children."""
    if width < 1:
        raise ValueError("width must be positive")
    return [[0, {"name": "root"}]] + [
        [0, node_id, {"name": f"node-{node_id}"}]
        for node_id in range(1, width + 1)
    ]


def make_balanced_branches(branching: int = 4, depth: int = 6) -> BranchTable:
    """Create a balanced tree with local child IDs from zero to branching-1."""
    if branching < 1 or depth < 0:
        raise ValueError("branching must be positive and depth must be non-negative")
    branches: BranchTable = []
    level: list[tuple[int, ...]] = [(0,)]
    for current_depth in range(depth + 1):
        next_level: list[tuple[int, ...]] = []
        for path in level:
            branches.append([*path, {"name": ".".join(map(str, path))}])
            if current_depth < depth:
                next_level.extend(path + (child_id,) for child_id in range(branching))
        level = next_level
    return branches


def compare_memory(branches: BranchTable) -> dict[str, float | int]:
    """Compare retained sizes of a branch table and the equivalent Taxonomy."""
    taxonomy = Taxonomy.from_branches(branches)
    model_bytes = deep_size(taxonomy)
    branches_bytes = deep_size(branches)
    return {
        "nodes": len(taxonomy),
        "model_bytes": model_bytes,
        "branches_bytes": branches_bytes,
        "memory_ratio": model_bytes / branches_bytes,
    }


def benchmark_synthetic() -> dict[str, dict[str, float | int]]:
    """Measure representative deep, wide, and balanced shapes."""
    return {
        "deep-200": compare_memory(make_deep_branches()),
        "wide-5000": compare_memory(make_wide_branches()),
        "balanced-4x6": compare_memory(make_balanced_branches()),
    }


def benchmark(source: Path = DEFAULT_SOURCE) -> dict[str, float | int]:
    started = perf_counter()
    taxonomy = import_taxonomy(
        source,
        leaf_keys=["en_US"],
        styler=LpStyle(header=False, ids=True, sparse=False),
        cvt_dict={"*": _as_int_when_possible},
    )
    import_seconds = perf_counter() - started

    started = perf_counter()
    branches = taxonomy.to_branches()
    to_branches_seconds = perf_counter() - started

    started = perf_counter()
    rebuilt = Taxonomy.from_branches(branches)
    from_branches_seconds = perf_counter() - started
    assert rebuilt == taxonomy

    started = perf_counter()
    for branch in taxonomy.iter_branches():
        taxonomy.get_node(branch.path)
    lookup_seconds = perf_counter() - started

    model_bytes = deep_size(taxonomy)
    branches_bytes = deep_size(branches)
    return {
        "nodes": len(taxonomy),
        "import_seconds": import_seconds,
        "to_branches_seconds": to_branches_seconds,
        "from_branches_seconds": from_branches_seconds,
        "lookup_seconds": lookup_seconds,
        "model_bytes": model_bytes,
        "branches_bytes": branches_bytes,
        "memory_ratio": model_bytes / branches_bytes,
    }


def main() -> None:
    result = benchmark()
    print(f"Source: {DEFAULT_SOURCE}")
    print(f"Nodes: {result['nodes']}")
    print(f"Import CSV -> Taxonomy: {result['import_seconds']:.4f} s")
    print(f"Taxonomy -> branch table: {result['to_branches_seconds']:.4f} s")
    print(f"Branch table -> Taxonomy: {result['from_branches_seconds']:.4f} s")
    print(f"Lookup every node by path: {result['lookup_seconds']:.4f} s")
    print(f"Taxonomy retained size: {mib(int(result['model_bytes'])):.3f} MiB")
    print(f"Branch table retained size: {mib(int(result['branches_bytes'])):.3f} MiB")
    print(f"Taxonomy / branch table memory: {result['memory_ratio']:.1%}")
    print("\nSynthetic shapes:")
    for name, synthetic in benchmark_synthetic().items():
        print(
            f"  {name}: {synthetic['nodes']} nodes; "
            f"Taxonomy={mib(int(synthetic['model_bytes'])):.3f} MiB; "
            f"branches={mib(int(synthetic['branches_bytes'])):.3f} MiB; "
            f"ratio={synthetic['memory_ratio']:.1%}"
        )


if __name__ == "__main__":
    main()
