from __future__ import annotations

import pytest

from taxonorm import Taxonomy, from_bigtree, to_bigtree, to_networkx
from taxonorm.errors import TxValidationError


def _taxonomy_with_repeated_ids() -> Taxonomy:
    return Taxonomy.from_branches(
        [
            ["root", {"name": "Root"}],
            ["root", "left", {"name": "Left"}],
            ["root", "left", "item", {"name": "Left item"}],
            ["root", "right", {"name": "Right"}],
            ["root", "right", "item", {"name": "Right item"}],
        ]
    )


def test_to_networkx_uses_full_id_paths_as_node_keys() -> None:
    pytest.importorskip("networkx")
    taxonomy = _taxonomy_with_repeated_ids()

    graph = to_networkx(taxonomy, label_key="name")

    assert set(graph.nodes) == {
        ("root",),
        ("root", "left"),
        ("root", "left", "item"),
        ("root", "right"),
        ("root", "right", "item"),
    }
    assert graph.nodes[("root", "left", "item")]["node_id"] == "item"
    assert graph.nodes[("root", "left", "item")]["label"] == "Left item"
    assert graph.nodes[("root", "left", "item")]["leaves"] == {
        "name": "Left item"
    }
    assert graph.has_edge(("root", "left"), ("root", "left", "item"))
    assert graph.has_edge(("root", "right"), ("root", "right", "item"))
    assert graph.graph["taxonorm_node_key"] == "id_path"


def test_to_networkx_renumber_returns_unique_ids_without_mutating_source() -> None:
    pytest.importorskip("networkx")
    taxonomy = _taxonomy_with_repeated_ids()

    graph = to_networkx(
        taxonomy,
        renumber=True,
        renumber_options={"slack": 0, "round_to": 1, "start_from": 100},
    )

    assert taxonomy.to_branches()[0][0] == "root"
    assert graph.graph["renumbered"] is True
    node_ids = [data["node_id"] for _, data in graph.nodes(data=True)]
    assert len(set(node_ids)) == len(node_ids)
    assert (100, 101, 103) in graph


def test_to_bigtree_exports_forest_under_synthetic_root() -> None:
    pytest.importorskip("bigtree")
    taxonomy = Taxonomy.from_branches(
        [
            [1, {"name": "One"}],
            [1, 11, {"name": "Child"}],
            [2, {"name": "Two"}],
        ]
    )

    tree = to_bigtree(taxonomy, label_key="name")
    root = tree.node
    exported = {
        node.id_path: node
        for node in tree.preorder_iter()
        if not getattr(node, "is_taxonorm_synthetic_root", False)
    }

    assert root.node_name == "Taxonomy"
    assert root.is_taxonorm_synthetic_root is True
    assert set(exported) == {(1,), (1, 11), (2,)}
    assert exported[(1, 11)].node_id == 11
    assert exported[(1, 11)].label == "Child"
    assert exported[(1, 11)].leaf_values == {"name": "Child"}


def test_to_bigtree_id_strategy_rejects_string_name_collisions() -> None:
    pytest.importorskip("bigtree")
    taxonomy = Taxonomy.from_branches(
        [
            [1, {"name": "Numeric"}],
            ["1", {"name": "String"}],
        ]
    )

    with pytest.raises(TxValidationError, match="collision"):
        to_bigtree(taxonomy, name_strategy="id")


def test_bigtree_round_trip_preserves_forest_mixed_ids_and_leaves() -> None:
    pytest.importorskip("bigtree")
    mutable_leaf = ["kept", "by", "reference"]
    taxonomy = Taxonomy.from_branches(
        [
            [False, {("locale", 1): mutable_leaf}],
            [False, ("tuple", 2), {1: None}],
            [1, {"name": "Numeric"}],
            ["1", {"name": "String"}],
        ]
    )

    restored = from_bigtree(to_bigtree(taxonomy))

    assert restored == taxonomy
    assert restored.get_node((False,)).leaves[("locale", 1)] is mutable_leaf


def test_empty_taxonomy_round_trips_through_synthetic_root() -> None:
    pytest.importorskip("bigtree")

    restored = from_bigtree(to_bigtree(Taxonomy()))

    assert restored == Taxonomy()


def test_from_bigtree_uses_current_structure_not_stored_id_path() -> None:
    pytest.importorskip("bigtree")
    taxonomy = Taxonomy.from_branches(
        [
            ["root", {"name": "Root"}],
            ["root", "left", {"name": "Left"}],
            ["root", "left", "item", {"name": "Item"}],
            ["root", "right", {"name": "Right"}],
        ]
    )
    tree = to_bigtree(taxonomy)
    nodes = {
        node.node_id: node
        for node in tree.preorder_iter()
        if hasattr(node, "node_id")
    }
    nodes["item"].parent = nodes["right"]

    restored = from_bigtree(tree)

    assert ("root", "left", "item") not in restored
    assert restored.get_node(("root", "right", "item")).leaves == {
        "name": "Item"
    }


def test_from_bigtree_imports_edits_to_exchange_attributes() -> None:
    pytest.importorskip("bigtree")
    tree = to_bigtree(
        Taxonomy.from_branches(
            [["root", {}], ["root", "child", {"name": "Before"}]]
        )
    )
    child = next(
        node
        for node in tree.preorder_iter()
        if hasattr(node, "node_id") and node.node_id == "child"
    )
    child.node_id = "renamed"
    child.leaf_values = {"name": "After"}

    restored = from_bigtree(tree)

    assert ("root", "child") not in restored
    assert restored.get_node(("root", "renamed")).leaves == {"name": "After"}


def test_from_native_bigtree_uses_names_and_selected_attributes() -> None:
    bigtree = pytest.importorskip("bigtree")
    root = bigtree.Node("root", description="Root node")
    bigtree.Node("child", parent=root, description="Child node")

    taxonomy = from_bigtree(
        root,
        attribute_map={"description": "description"},
    )

    assert taxonomy.to_branches() == [
        ["root", {"description": "Root node"}],
        ["root", "child", {"description": "Child node"}],
    ]


def test_from_bigtree_can_require_explicit_id_metadata() -> None:
    bigtree = pytest.importorskip("bigtree")

    with pytest.raises(TxValidationError, match="has no 'node_id'"):
        from_bigtree(bigtree.Node("root"), missing_id="error")


def test_bigtree_top_level_id_may_equal_synthetic_root_name() -> None:
    pytest.importorskip("bigtree")
    taxonomy = Taxonomy.from_branches([["Taxonomy", {}]])

    restored = from_bigtree(to_bigtree(taxonomy, name_strategy="id"))

    assert restored == taxonomy


def test_adapters_reject_non_taxonomy_input() -> None:
    with pytest.raises(TxValidationError, match="Taxonomy"):
        to_networkx([["root", {"name": "Root"}]])  # type: ignore[arg-type]

    with pytest.raises(TxValidationError, match="Taxonomy"):
        to_bigtree([["root", {"name": "Root"}]])  # type: ignore[arg-type]

    with pytest.raises(TxValidationError, match="bigtree"):
        from_bigtree([["root", {"name": "Root"}]])
