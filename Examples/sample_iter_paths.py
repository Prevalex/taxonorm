#!python
"""Compare iter_branches()+leaf_path() with iter_paths()."""

from __future__ import annotations

from taxonorm import IpStyle, import_taxonomy

from sample_common import LEAF_KEYS, SAMPLE_IP_H_K_T, as_int_when_possible


taxonomy = import_taxonomy(
    SAMPLE_IP_H_K_T,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    cvt_dict={"*": as_int_when_possible},
)

print("Via iter_branches() + leaf_path():")
for branch in taxonomy.iter_branches():
    id_path = branch.path
    leaf_path = taxonomy.leaf_path(branch.path, "en_US")
    print(id_path, leaf_path)

print("\nVia iter_paths():")
for id_path, leaf_path in taxonomy.iter_paths():
    print(id_path, leaf_path)
