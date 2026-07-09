#!python
"""Validate a deliberately damaged row shaped like the short sample taxonomy."""

from __future__ import annotations

from taxonorm import IpStyle, validate_input

from sample_common import LEAF_KEYS


rows = [
    ["taxonorm", "0.1.0", "Sample", "variants", "en_US", "uk_UA"],
    [[], "", "", "", "Household appliances", "Побутова техніка"],
    ["", 11, "", "", "Climate technology", "Кліматична техніка"],
]

report = validate_input(
    rows,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    source="damaged-short-sample.csv",
)

print(report.format_text())
