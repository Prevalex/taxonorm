from __future__ import annotations

import pytest

from taxonorm import Taxonomy, renumber_taxonomy_ids
from taxonorm.errors import TxValidationError


def test_branch_round_trip_builds_missing_ancestors() -> None:
    source = [
        ["root", "child", {"name": "Child"}],
        ["root", {"name": "Root"}],
    ]

    taxonomy = Taxonomy.from_branches(source)

    assert taxonomy.to_branches() == [
        ["root", {"name": "Root"}],
        ["root", "child", {"name": "Child"}],
    ]
    assert len(taxonomy) == 2


def test_common_prefixes_are_shared_and_repeated_ids_are_supported() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["root", "left", "item", {"name": "One"}],
            ["root", "right", "item", {"name": "Two"}],
        ]
    )

    root = taxonomy.get_node(("root",))
    assert len(taxonomy) == 5
    assert root.children["left"].children["item"].leaves == {"name": "One"}
    assert root.children["right"].children["item"].leaves == {"name": "Two"}


def test_hashable_ids_and_keys_and_arbitrary_leaf_values_are_supported() -> None:
    taxonomy = Taxonomy()
    taxonomy.add_branch((0, ("section", 1)), {("locale", "uk"): None, 7: [1, 2]})

    assert taxonomy.get_node((0, ("section", 1))).leaves == {
        ("locale", "uk"): None,
        7: [1, 2],
    }
    assert taxonomy.leaf_keys() == (("locale", "uk"), 7)


@pytest.mark.parametrize("bad_id", [None, "", "   ", (), [], {}])
def test_empty_or_unhashable_ids_are_rejected(bad_id: object) -> None:
    taxonomy = Taxonomy()

    with pytest.raises(TxValidationError):
        taxonomy.add_branch((bad_id,), {"name": "value"})


@pytest.mark.parametrize("bad_key", [None, "", "   ", ()])
def test_empty_leaf_keys_are_rejected(bad_key: object) -> None:
    taxonomy = Taxonomy()

    with pytest.raises(TxValidationError):
        taxonomy.add_branch(("root",), {bad_key: "value"})  # type: ignore[dict-item]


def test_duplicate_paths_require_explicit_replacement() -> None:
    taxonomy = Taxonomy.from_branches([["root", {"name": "old"}]])

    with pytest.raises(TxValidationError, match="дублируется"):
        taxonomy.add_branch(("root",), {"name": "new"})

    taxonomy.add_branch(("root",), {"name": "new"}, replace=True)
    assert taxonomy.get_node(("root",)).leaves == {"name": "new"}


def test_adapters_do_not_share_leaf_dictionaries_with_callers() -> None:
    leaves = {"name": "original"}
    taxonomy = Taxonomy.from_branches([["root", leaves]])
    leaves["name"] = "changed outside"

    exported = taxonomy.to_branches()
    exported[0][-1]["name"] = "changed export"

    assert taxonomy.get_node(("root",)).leaves == {"name": "original"}


def test_leaf_path_follows_the_requested_id_path() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["root", {"name": "Root"}],
            ["root", "child", {"name": "Child"}],
        ]
    )

    assert taxonomy.leaf_path(("root", "child"), "name") == ("Root", "Child")


def test_leaves_are_updated_only_through_validated_taxonomy_api() -> None:
    taxonomy = Taxonomy.from_branches([["root", {"name": "Root"}]])

    taxonomy.update_leaves(("root",), {"description": None})
    assert taxonomy.get_node(("root",)).leaves == {
        "name": "Root",
        "description": None,
    }

    with pytest.raises(TypeError):
        taxonomy.get_node(("root",)).leaves["name"] = "unsafe"  # type: ignore[index]


def test_removing_non_leaf_node_requires_explicit_recursive_flag() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["root", {"name": "Root"}],
            ["root", "child", {"name": "Child"}],
        ]
    )

    with pytest.raises(TxValidationError, match="recursive=True"):
        taxonomy.remove_branch(("root",))

    taxonomy.remove_branch(("root",), recursive=True)
    assert not taxonomy
    assert ("root",) not in taxonomy


def test_rename_preserves_subtree_and_sibling_order() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["root", {"name": "Root"}],
            ["root", "left", {"name": "Left"}],
            ["root", "left", "item", {"name": "Item"}],
            ["root", "right", {"name": "Right"}],
        ]
    )

    taxonomy.rename_node(("root", "left"), "primary")

    assert list(taxonomy.get_node(("root",)).children) == ["primary", "right"]
    assert ("root", "left") not in taxonomy
    assert taxonomy.get_node(("root", "primary", "item")).leaves == {
        "name": "Item"
    }


def test_move_subtree_rejects_cycles_and_collisions() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["root", {"name": "Root"}],
            ["root", "left", {"name": "Left"}],
            ["root", "left", "item", {"name": "Item"}],
            ["root", "right", {"name": "Right"}],
            ["root", "right", "item", {"name": "Existing"}],
        ]
    )

    with pytest.raises(TxValidationError, match="поддерева"):
        taxonomy.move_subtree(("root", "left"), ("root", "left", "item"))
    with pytest.raises(TxValidationError, match="уже есть"):
        taxonomy.move_subtree(("root", "left", "item"), ("root", "right"))

    taxonomy.move_subtree(
        ("root", "left", "item"), ("root", "right"), new_id="moved"
    )
    assert ("root", "left", "item") not in taxonomy
    assert taxonomy.get_node(("root", "right", "moved")).leaves == {
        "name": "Item"
    }


def test_traversal_orders_and_selection_are_stable() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["root", {"kind": "root"}],
            ["root", "a", {"kind": "group"}],
            ["root", "a", "one", {"kind": "item"}],
            ["root", "b", {"kind": "group"}],
        ]
    )

    assert [branch.path for branch in taxonomy.iter_branches()] == [
        ("root",),
        ("root", "a"),
        ("root", "a", "one"),
        ("root", "b"),
    ]
    assert [branch.path for branch in taxonomy.iter_branches("breadth")] == [
        ("root",),
        ("root", "a"),
        ("root", "b"),
        ("root", "a", "one"),
    ]
    assert [branch.path for branch in taxonomy.iter_branches("postorder")] == [
        ("root", "a", "one"),
        ("root", "a"),
        ("root", "b"),
        ("root",),
    ]
    assert [
        branch.path
        for branch in taxonomy.find_branches(
            lambda branch: branch.leaves.get("kind") == "group"
        )
    ] == [("root", "a"), ("root", "b")]


def test_renumber_taxonomy_ids_returns_copy_with_unique_numeric_paths() -> None:
    taxonomy = Taxonomy.from_branches(
        [
            ["catalog", {"name": "Catalog"}],
            ["catalog", "phones", {"name": "Phones"}],
            ["catalog", "phones", "accessories", {"name": "Phone accessories"}],
            ["catalog", "tablets", {"name": "Tablets"}],
            ["catalog", "tablets", "accessories", {"name": "Tablet accessories"}],
        ]
    )

    renumbered = renumber_taxonomy_ids(
        taxonomy,
        slack=0,
        round_to=1,
        start_from=100,
    )

    assert taxonomy.to_branches()[0][0] == "catalog"
    assert renumbered.to_branches() == [
        [100, {"name": "Catalog"}],
        [100, 101, {"name": "Phones"}],
        [100, 101, 103, {"name": "Phone accessories"}],
        [100, 102, {"name": "Tablets"}],
        [100, 102, 104, {"name": "Tablet accessories"}],
    ]
    assert len({branch.path[-1] for branch in renumbered.iter_branches()}) == len(
        renumbered
    )


def test_renumber_taxonomy_ids_rejects_non_taxonomy_input() -> None:
    with pytest.raises(TxValidationError, match="Taxonomy"):
        renumber_taxonomy_ids([["root", {"name": "Root"}]])  # type: ignore[arg-type]
