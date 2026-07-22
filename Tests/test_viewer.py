from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from taxonorm import (
    Taxonomy,
    render_text_tree,
    save_text_tree,
    to_rich_tree,
    view_live_html_tree,
    view_text_tree,
)
from taxonorm.errors import TxValidationError


def _taxonomy() -> Taxonomy:
    return Taxonomy.from_branches(
        [
            ["catalog", {"name": "Каталог"}],
            ["catalog", "phones", {"name": "Телефоны"}],
            ["catalog", "phones", "accessories", {"name": "Аксессуары"}],
            ["catalog", "tablets", {"name": "Планшеты"}],
            ["catalog", "tablets", "accessories", {"name": "Аксессуары"}],
        ]
    )


def _render_to_text(tree: object) -> str:
    console = Console(record=True, width=100)
    console.print(tree)
    return console.export_text()


def test_render_text_tree_uses_ids_by_default() -> None:
    text = _render_to_text(render_text_tree(_taxonomy(), label="Categories"))

    assert "Categories" in text
    assert "catalog" in text
    assert "phones" in text
    assert "Телефоны" not in text


def test_render_text_tree_can_use_leaf_labels_without_collapsing_nodes() -> None:
    text = _render_to_text(render_text_tree(_taxonomy(), leaf_key="name"))

    assert "Каталог" in text
    assert "Телефоны" in text
    assert text.count("Аксессуары") == 2


def test_to_rich_tree_treats_string_labels_as_literal_text() -> None:
    taxonomy = Taxonomy.from_branches(
        [["[literal]", {"name": "[red]Danger[/red]"}]]
    )

    text = _render_to_text(
        to_rich_tree(taxonomy, label="[root]", leaf_key="name")
    )

    assert "[root]" in text
    assert "[red]Danger[/red]" in text


def test_to_rich_tree_can_opt_in_to_markup() -> None:
    taxonomy = Taxonomy.from_branches([["root", {"name": "Name"}]])

    text = _render_to_text(
        to_rich_tree(
            taxonomy,
            leaf_key="name",
            formatter=lambda path, node, label: f"[red]{label}[/red]",
            markup=True,
        )
    )

    assert "Name" in text
    assert "[red]" not in text


def test_to_rich_tree_handles_deep_taxonomy_without_recursion() -> None:
    path = tuple(range(1_200))
    taxonomy = Taxonomy.from_branches([[*path, {}]])

    branch = to_rich_tree(taxonomy)

    depth = 0
    while branch.children:
        branch = branch.children[0]
        depth += 1
    assert depth == len(path)


def test_view_text_tree_prints_and_returns_tree(capsys: pytest.CaptureFixture[str]) -> None:
    tree = view_text_tree(_taxonomy(), leaf_key="name")

    assert tree is not None
    assert "Каталог" in capsys.readouterr().out


def test_save_text_tree_writes_file(tmp_path: Path) -> None:
    output = save_text_tree(_taxonomy(), tmp_path / "tree.txt", leaf_key="name")

    assert output == tmp_path / "tree.txt"
    assert "Каталог" in output.read_text(encoding="utf-8")


def test_view_live_html_tree_writes_pyvis_html(tmp_path: Path) -> None:
    output = view_live_html_tree(
        _taxonomy(),
        leaf_key="name",
        filename=tmp_path / "tree",
        open_browser=False,
    )

    assert output == tmp_path / "tree.html"
    html = output.read_text(encoding="utf-8")
    assert r"\u041a\u0430\u0442\u0430\u043b\u043e\u0433" in html
    assert "catalog / phones" in html


def test_viewers_reject_non_taxonomy_input() -> None:
    with pytest.raises(TxValidationError, match="Taxonomy"):
        render_text_tree([["root", {"name": "Root"}]])  # type: ignore[arg-type]
