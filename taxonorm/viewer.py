"""Human-facing viewers for :class:`taxonorm.model.Taxonomy` trees."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Mapping
from html import escape
from pathlib import Path
from typing import Any

from .errors import TxValidationError
from .model import IdPath, LeafKey, MissedLeaf, NodeId, Taxonomy, TaxonomyNode

LabelFormatter = Callable[[IdPath, TaxonomyNode, str], str]


def _ensure_taxonomy(taxonomy: Taxonomy) -> None:
    if not isinstance(taxonomy, Taxonomy):
        raise TxValidationError(
            f"Expected a Taxonomy object, got: {type(taxonomy).__name__}"
        )


def _format_value(value: Any) -> str:
    return str(value)


def _display_label(
    taxonomy: Taxonomy,
    path: IdPath,
    node: TaxonomyNode,
    *,
    leaf_key: LeafKey | None,
    missed_leaf: MissedLeaf,
    formatter: LabelFormatter | None,
) -> str:
    if leaf_key is None:
        value = path[-1]
    else:
        value = taxonomy.leaf_path(path, leaf_key, missed_leaf=missed_leaf)[-1]
    label = _format_value(value)
    if formatter is not None:
        label = formatter(path, node, label)
    return label


def _iter_children(
    children: Mapping[NodeId, TaxonomyNode], *, sort: bool
) -> list[tuple[NodeId, TaxonomyNode]]:
    items = list(children.items())
    if sort:
        items.sort(key=lambda item: str(item[0]).casefold())
    return items


def to_rich_tree(
    taxonomy: Taxonomy,
    *,
    label: Any = "Taxonomy",
    leaf_key: LeafKey | None = None,
    missed_leaf: MissedLeaf = "auto",
    sort: bool = False,
    formatter: LabelFormatter | None = None,
    markup: bool = False,
) -> Any:
    """Export *taxonomy* as a :class:`rich.tree.Tree` renderable.

    By default node labels are node IDs.  Pass ``leaf_key`` to display the
    selected leaf value at each node instead, for example ``leaf_key="name"``.
    The underlying structure still follows the native ``Taxonomy`` tree, so
    sibling nodes with equal display labels remain distinct.  String labels
    are treated as literal text by default; pass ``markup=True`` to interpret
    Rich console markup returned by ``formatter`` or supplied as ``label``.
    """
    _ensure_taxonomy(taxonomy)
    try:
        from rich.text import Text as RichText
        from rich.tree import Tree as RichTree
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            'Install the "rich" dependency to use to_rich_tree().'
        ) from exc

    def rich_label(value: Any) -> Any:
        if isinstance(value, str) and not markup:
            return RichText(value)
        return value

    tree = RichTree(rich_label(label))

    pending: list[
        tuple[Any, Mapping[NodeId, TaxonomyNode], IdPath]
    ] = [(tree, taxonomy.roots, ())]
    while pending:
        branch, children, parent_path = pending.pop()
        added: list[tuple[Any, TaxonomyNode, IdPath]] = []
        for node_id, node in _iter_children(children, sort=sort):
            path = parent_path + (node_id,)
            child = branch.add(
                rich_label(
                    _display_label(
                        taxonomy,
                        path,
                        node,
                        leaf_key=leaf_key,
                        missed_leaf=missed_leaf,
                        formatter=formatter,
                    )
                )
            )
            added.append((child, node, path))
        pending.extend(
            (child, node.children, path)
            for child, node, path in reversed(added)
        )

    return tree


def render_text_tree(
    taxonomy: Taxonomy,
    *,
    label: Any = "Taxonomy",
    leaf_key: LeafKey | None = None,
    missed_leaf: MissedLeaf = "auto",
    sort: bool = False,
    formatter: LabelFormatter | None = None,
    markup: bool = False,
) -> Any:
    """Compatibility name for :func:`to_rich_tree`."""
    return to_rich_tree(
        taxonomy,
        label=label,
        leaf_key=leaf_key,
        missed_leaf=missed_leaf,
        sort=sort,
        formatter=formatter,
        markup=markup,
    )


def view_text_tree(
    taxonomy: Taxonomy,
    *,
    label: Any = "Taxonomy",
    leaf_key: LeafKey | None = None,
    missed_leaf: MissedLeaf = "auto",
    sort: bool = False,
    formatter: LabelFormatter | None = None,
    markup: bool = False,
) -> Any:
    """Print *taxonomy* as a static Rich text tree and return the Rich tree."""
    try:
        from rich.console import Console as RichConsole
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            'Install the "rich" dependency to use view_text_tree().'
        ) from exc

    tree = render_text_tree(
        taxonomy,
        label=label,
        leaf_key=leaf_key,
        missed_leaf=missed_leaf,
        sort=sort,
        formatter=formatter,
        markup=markup,
    )
    RichConsole().print(tree)
    return tree


def save_text_tree(
    taxonomy: Taxonomy,
    filename: str | Path = "$taxonomy$.txt",
    *,
    label: Any = "Taxonomy",
    leaf_key: LeafKey | None = None,
    missed_leaf: MissedLeaf = "auto",
    sort: bool = False,
    formatter: LabelFormatter | None = None,
    markup: bool = False,
    width: int = 120,
) -> Path:
    """Save a static Rich text tree to *filename* and return the path."""
    try:
        from rich.console import Console as RichConsole
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            'Install the "rich" dependency to use save_text_tree().'
        ) from exc

    path = Path(filename)
    tree = render_text_tree(
        taxonomy,
        label=label,
        leaf_key=leaf_key,
        missed_leaf=missed_leaf,
        sort=sort,
        formatter=formatter,
        markup=markup,
    )
    with path.open("w", encoding="utf-8") as stream:
        RichConsole(file=stream, force_terminal=True, width=width).print(tree)
    return path


def view_live_text_tree(
    taxonomy: Taxonomy,
    *,
    label: str = "Taxonomy",
    leaf_key: LeafKey | None = None,
    missed_leaf: MissedLeaf = "auto",
    sort: bool = False,
    formatter: LabelFormatter | None = None,
    icon_node: str = "> ",
    icon_node_expanded: str = "v ",
) -> None:
    """Open an interactive Textual tree viewer for *taxonomy*."""
    _ensure_taxonomy(taxonomy)
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Footer, Tree
        from textual.widgets.tree import TreeNode
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            'Install the "textual" dependency to use view_live_text_tree().'
        ) from exc

    class TaxonomyTree(Tree[Any]):
        ICON_NODE = icon_node
        ICON_NODE_EXPANDED = icon_node_expanded

    class TaxonomyTreeApp(App[None]):
        BINDINGS = [("q", "quit", "Quit")]
        CSS_PATH = None

        def compose(self) -> ComposeResult:
            yield TaxonomyTree(label, id="taxonomy_tree")
            yield Footer()

        def on_mount(self) -> None:
            tree_widget = self.query_one("#taxonomy_tree", TaxonomyTree)
            populate(tree_widget.root, taxonomy.roots, ())
            tree_widget.show_root = True
            tree_widget.root.expand()

    def populate(
        branch: TreeNode[Any],
        children: Mapping[NodeId, TaxonomyNode],
        parent_path: IdPath,
    ) -> None:
        for node_id, node in _iter_children(children, sort=sort):
            path = parent_path + (node_id,)
            child = branch.add(
                _display_label(
                    taxonomy,
                    path,
                    node,
                    leaf_key=leaf_key,
                    missed_leaf=missed_leaf,
                    formatter=formatter,
                )
            )
            populate(child, node.children, path)

    TaxonomyTreeApp().run()


def _default_html_name(taxonomy: Taxonomy, leaf_key: LeafKey | None) -> str:
    by = "ids" if leaf_key is None else "leaves"
    return f"taxonomy_{len(taxonomy)}_nodes_by_{by}.html"


def _html_title(path: IdPath, node: TaxonomyNode) -> str:
    parts = [f"<b>Path</b>: {escape(' / '.join(map(str, path)))}"]
    if node.leaves:
        parts.append("<b>Leaves</b>:")
        parts.extend(
            f"{escape(str(key))}: {escape(str(value))}"
            for key, value in node.leaves.items()
        )
    return "<br>".join(parts)


def view_live_html_tree(
    taxonomy: Taxonomy,
    *,
    leaf_key: LeafKey | None = None,
    missed_leaf: MissedLeaf = "auto",
    filename: str | Path | None = None,
    tempfolder: str | Path | None = None,
    notebook: bool = False,
    open_browser: bool | None = None,
    sort: bool = False,
    formatter: LabelFormatter | None = None,
    directed: bool = True,
    hierarchical: bool = True,
    cdn_resources: str = "in_line",
) -> Any:
    """Render *taxonomy* to an interactive pyvis HTML file.

    Returns the generated :class:`pathlib.Path`.  When ``notebook=True`` pyvis
    returns an iframe object instead, matching its native notebook behaviour.
    """
    _ensure_taxonomy(taxonomy)
    try:
        from pyvis.network import Network
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            'Install the "pyvis" dependency to use view_live_html_tree().'
        ) from exc

    if filename is None:
        folder = (
            Path(tempfolder) if tempfolder is not None else Path(tempfile.gettempdir())
        )
        output = folder / _default_html_name(taxonomy, leaf_key)
    else:
        output = Path(filename)
        if output.suffix.lower() != ".html":
            output = output.with_suffix(".html")
    output.parent.mkdir(parents=True, exist_ok=True)

    net = Network(directed=directed, notebook=notebook, cdn_resources=cdn_resources)
    if hierarchical:
        net.set_options(
            """
            var options = {
              "layout": {
                "hierarchical": {
                  "enabled": true,
                  "direction": "UD",
                  "sortMethod": "directed"
                }
              },
              "physics": {
                "enabled": true,
                "solver": "hierarchicalRepulsion",
                "hierarchicalRepulsion": {
                  "nodeDistance": 130,
                  "springLength": 160
                }
              },
              "interaction": {
                "hover": true,
                "keyboard": true,
                "navigationButtons": true
              }
            }
            """
        )

    def add_nodes(
        children: Mapping[NodeId, TaxonomyNode],
        parent_path: IdPath,
        parent_id: str | None,
    ) -> None:
        for node_id, node in _iter_children(children, sort=sort):
            path = parent_path + (node_id,)
            graph_id = repr(path)
            net.add_node(
                graph_id,
                label=_display_label(
                    taxonomy,
                    path,
                    node,
                    leaf_key=leaf_key,
                    missed_leaf=missed_leaf,
                    formatter=formatter,
                ),
                title=_html_title(path, node),
                level=len(path) - 1,
            )
            if parent_id is not None:
                net.add_edge(parent_id, graph_id)
            add_nodes(node.children, path, graph_id)

    add_nodes(taxonomy.roots, (), None)

    if open_browser is None:
        open_browser = not notebook
    if notebook:
        return net.show(str(output), notebook=True)
    net.write_html(str(output), notebook=False, open_browser=open_browser)
    return output
