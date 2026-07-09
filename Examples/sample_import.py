#!python
"""Import the short sample taxonomy from a keyed, tabbed IP CSV file."""

from __future__ import annotations

from taxonorm import IpStyle, import_taxonomy

from sample_common import LEAF_KEYS, SAMPLE_IP_H_K_T, as_int_when_possible


taxonomy = import_taxonomy(
    SAMPLE_IP_H_K_T,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    cvt_dict={"*": as_int_when_possible},
)

print(f"nodes: {len(taxonomy)}")
print(f"leaf keys: {taxonomy.leaf_keys()}")
print(taxonomy.get_node((2, 14, 24, 34)).leaves["en_US"])
print(taxonomy.leaf_path((1, 12, 22, 31), "en_US"))
