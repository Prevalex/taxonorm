#!python
"""Export the short sample taxonomy to another style in a temporary folder."""

from __future__ import annotations

import tempfile
from pathlib import Path

from taxonorm import IpStyle, LpStyle, export_taxonomy, import_taxonomy

from sample_common import LEAF_KEYS, SAMPLE_IP_H_K_T, as_int_when_possible


taxonomy = import_taxonomy(
    SAMPLE_IP_H_K_T,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    cvt_dict={"*": as_int_when_possible},
)

output = Path(tempfile.gettempdir()) / "taxonorm_short_lp.csv"
export_taxonomy(
    taxonomy,
    output,
    styler=LpStyle(header=True, ids=True, sparse=False),
    leaf_key="en_US",
    headers=["id", "category"],
)

print(output)
