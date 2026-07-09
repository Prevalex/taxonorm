#!python
"""Parse a few rows from the same short taxonomy without reading a file."""

from __future__ import annotations

from taxonorm import LpStyle, parse_taxonomy


rows = [
    [1, "Household appliances"],
    [11, "Household appliances", "Climate technology"],
    [21, "Household appliances", "Climate technology", "Household fans"],
    [12, "Household appliances", "Large household appliances"],
    [
        22,
        "Household appliances",
        "Large household appliances",
        "Refrigeration equipment",
    ],
]

taxonomy = parse_taxonomy(
    rows,
    styler=LpStyle(header=False, ids=True, sparse=False),
    leaf_keys=["en_US"],
)

for branch in taxonomy.iter_branches():
    print(branch.path, branch.leaves["en_US"])
