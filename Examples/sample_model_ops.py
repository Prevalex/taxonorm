#!python
"""Explore and edit the short sample taxonomy in memory."""

from __future__ import annotations

from taxonorm import IpStyle, import_taxonomy

from sample_common import LEAF_KEYS, SAMPLE_IP_H_K_T, as_int_when_possible


taxonomy = import_taxonomy(
    SAMPLE_IP_H_K_T,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    cvt_dict={"*": as_int_when_possible},
)

servers_path = (3, 15, 25)
print(taxonomy.leaf_path(servers_path, "en_US"))

taxonomy.update_leaves(servers_path, {"note": "Duplicated label, distinct path"})
taxonomy.rename_node((3, 15, 25, 35), 350)
taxonomy.move_subtree((3, 15, 26, 37), (3, 15, 25), new_id=370)

print(taxonomy.get_node((3, 15, 25)).leaves)
print(taxonomy.leaf_path((3, 15, 25, 370), "en_US"))
print((3, 15, 26, 37) in taxonomy)
