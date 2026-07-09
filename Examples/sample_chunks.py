#!python
"""Restore and split unique-ID IP chunks."""

from __future__ import annotations

from taxonorm import (
    IpStyle,
    Taxonomy,
    import_taxonomy,
    restore_unique_ip_chunks,
    split_to_unique_ip_chunks,
)

from sample_common import SAMPLE_IP_CHUNKS, as_int_when_possible


chunks = [
    [0, 1, {"en_US": "Laptops"}],
    [1, 101, {"en_US": "Laptops"}],
    [1, 1686, {"en_US": "Laptop parts and options"}],
    [0, 2, {"en_US": "Computers"}],
    [2, 110, {"en_US": "All-in-one PCs"}],
]

restored = restore_unique_ip_chunks(chunks)
taxonomy = Taxonomy.from_branches(restored)
print(restored)
print(split_to_unique_ip_chunks(taxonomy, max_chunk_len=2))

from_file = import_taxonomy(
    SAMPLE_IP_CHUNKS,
    styler=IpStyle(header=False, keys=False, tabbed=False),
    leaf_keys=["en_US"],
    cvt_dict={"*": as_int_when_possible},
    restore_ip_chunks=True,
)
print(len(from_file))
print(from_file.leaf_path((0, 1, 101), "en_US"))
