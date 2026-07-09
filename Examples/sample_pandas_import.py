#!python
"""Import an in-memory pandas DataFrame as a taxonomy table."""

from __future__ import annotations

import pandas as pd

from taxonorm import IpStyle, import_taxonomy

from sample_common import LEAF_KEYS, SAMPLE_IP_H_K_T, as_int_when_possible


dataframe = pd.read_csv(SAMPLE_IP_H_K_T, dtype=object)

taxonomy = import_taxonomy(
    dataframe,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    cvt_dict={"*": as_int_when_possible},
)

print(f"nodes: {len(taxonomy)}")
print(taxonomy.leaf_path((1, 12, 22, 31), "en_US"))
