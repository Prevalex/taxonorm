from __future__ import annotations

import pytest

from taxonorm.benchmark_model import (
    compare_memory,
    make_balanced_branches,
    make_deep_branches,
    make_wide_branches,
)


@pytest.mark.parametrize(
    ("branches", "expected_nodes", "maximum_ratio"),
    [
        (make_deep_branches(200), 200, 0.70),
        (make_wide_branches(5000), 5001, 1.10),
        (make_balanced_branches(4, 6), 5461, 1.05),
    ],
    ids=["deep", "wide", "balanced"],
)
def test_taxonomy_memory_by_shape(
    branches: list[list[object]], expected_nodes: int, maximum_ratio: float
) -> None:
    result = compare_memory(branches)

    assert result["nodes"] == expected_nodes
    assert result["memory_ratio"] < maximum_ratio


@pytest.mark.parametrize(
    ("factory", "arguments"),
    [
        (make_deep_branches, (0,)),
        (make_wide_branches, (0,)),
        (make_balanced_branches, (0, 1)),
        (make_balanced_branches, (2, -1)),
    ],
)
def test_synthetic_shape_dimensions_must_be_valid(factory: object, arguments: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        factory(*arguments)  # type: ignore[operator]
