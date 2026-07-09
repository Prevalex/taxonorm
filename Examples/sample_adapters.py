#!python
"""Export a taxonomy to networkx and bigtree."""

from __future__ import annotations

from taxonorm import IpStyle, import_taxonomy, to_bigtree, to_networkx

from sample_common import LEAF_KEYS, SAMPLE_IP_H_K_T, as_int_when_possible


taxonomy = import_taxonomy(
    SAMPLE_IP_H_K_T,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    cvt_dict={"*": as_int_when_possible},
)

graph = to_networkx(taxonomy, label_key="en_US")
print(graph.number_of_nodes(), graph.number_of_edges())
print(graph.nodes[(1, 12, 22, 31)]["label"])

tree = to_bigtree(taxonomy, label_key="en_US")
node_by_path = {
    node.id_path: node
    for node in tree.preorder_iter()
    if not getattr(node, "is_taxonorm_synthetic_root", False)
}
print(tree.node.node_name)
print(node_by_path[(1, 12, 22, 31)].label)
