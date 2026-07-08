from __future__ import annotations

from taxonorm import IpStyle, LpStyle, Taxonomy, parse_taxonomy


def _documented_taxonomy() -> Taxonomy:
    return Taxonomy.from_branches(
        [
            ["catalog", {"name": "Каталог"}],
            ["catalog", "phones", {"name": "Телефоны"}],
            [
                "catalog",
                "phones",
                "accessories",
                {"name": "Аксессуары"},
            ],
            ["catalog", "tablets", {"name": "Планшеты"}],
            [
                "catalog",
                "tablets",
                "accessories",
                {"name": "Аксессуары"},
            ],
        ]
    )


def test_readme_low_level_parsing_example() -> None:
    rows = [
        [1, "Catalog"],
        [2, "Catalog", "Phones"],
    ]

    taxonomy = parse_taxonomy(
        rows,
        styler=LpStyle(header=False, ids=True, sparse=False),
        leaf_keys=["name"],
    )

    assert taxonomy.to_branches() == [
        [1, {"name": "Catalog"}],
        [1, 2, {"name": "Phones"}],
    ]


def test_readme_editing_workflow() -> None:
    taxonomy = _documented_taxonomy()
    taxonomy.add_branch(
        ("catalog", "wearables"), {"name": "Носимая электроника"}
    )
    taxonomy.add_branch(
        ("catalog", "wearables"), {"name": "Wearables"}, replace=True
    )
    taxonomy.update_leaves(
        ("catalog", "phones"),
        {"description": "Mobile and landline phones"},
    )
    taxonomy.rename_node(("catalog", "phones"), "telephones")
    taxonomy.move_subtree(
        ("catalog", "telephones", "accessories"),
        ("catalog", "wearables"),
        new_id="phone-accessories",
    )

    assert taxonomy.get_node(
        ("catalog", "wearables", "phone-accessories")
    ).leaves == {"name": "Аксессуары"}
    assert taxonomy.leaf_path(
        ("catalog", "wearables", "phone-accessories"), "name"
    ) == ("Каталог", "Wearables", "Аксессуары")

    taxonomy.remove_branch(("catalog", "tablets"), recursive=True)
    assert ("catalog", "tablets") not in taxonomy


def test_subtree_can_be_moved_to_roots() -> None:
    taxonomy = _documented_taxonomy()
    original_size = len(taxonomy)

    taxonomy.move_subtree(("catalog", "tablets"), None, new_id="devices")

    assert len(taxonomy) == original_size
    assert ("devices", "accessories") in taxonomy
    assert list(taxonomy.roots) == ["catalog", "devices"]


def test_style_types_are_available_from_public_package() -> None:
    assert IpStyle(header=True, keys=True, tabbed=True).hints == [
        "IP",
        "H",
        "K",
        "T",
    ]
    assert LpStyle(header=False, ids=True, sparse=False).hints == [
        "LP",
        "NH",
        "I",
        "NS",
    ]
