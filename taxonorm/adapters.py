"""Optional adapters for third-party tree and graph libraries."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from typing import Any, Literal
from urllib.parse import quote

from .errors import TxValidationError
from .model import LeafKey, Taxonomy, TaxonomyBranch
from .stylers.style_lp_ni import renumber_taxonomy_ids

BigtreeNameStrategy = Literal["index", "id", "path"]


def _require_taxonomy(taxonomy: Taxonomy) -> None:
    if not isinstance(taxonomy, Taxonomy):
        raise TxValidationError(
            f"Expected a Taxonomy object, got: {type(taxonomy).__name__}"
        )


def _require_optional_module(module_name: str, extra_name: str) -> Any:
    try:
        return import_module(module_name)
    except ImportError as exc:
        raise TxValidationError(
            f"{module_name} is not installed; install taxonorm[{extra_name}]"
        ) from exc


def _prepared_taxonomy(
    taxonomy: Taxonomy,
    *,
    renumber: bool,
    renumber_options: Mapping[str, Any] | None,
) -> Taxonomy:
    _require_taxonomy(taxonomy)
    if not renumber:
        return taxonomy
    options = dict(renumber_options or {})
    return renumber_taxonomy_ids(taxonomy, **options)


def _branch_label(branch: TaxonomyBranch, label_key: LeafKey | None) -> Any:
    if label_key is not None and label_key in branch.leaves:
        return branch.leaves[label_key]
    return branch.path[-1]


def to_networkx(
    taxonomy: Taxonomy,
    *,
    label_key: LeafKey | None = None,
    renumber: bool = False,
    renumber_options: Mapping[str, Any] | None = None,
) -> Any:
    """Export *taxonomy* to a ``networkx.DiGraph``.

    Node keys are full ID paths, so repeated local node IDs are preserved
    without renumbering.  Each node receives ``node_id``, ``id_path``,
    ``depth``, ``leaves``, and ``label`` attributes.
    """
    source = _prepared_taxonomy(
        taxonomy,
        renumber=renumber,
        renumber_options=renumber_options,
    )
    nx = _require_optional_module("networkx", "graph")
    graph = nx.DiGraph()
    graph.graph.update(
        taxonorm_node_key="id_path",
        taxonomy_roots=tuple((root_id,) for root_id in source.roots),
        renumbered=renumber,
    )

    for branch in source.iter_branches():
        graph.add_node(
            branch.path,
            node_id=branch.path[-1],
            id_path=branch.path,
            depth=len(branch.path),
            leaves=dict(branch.leaves),
            label=_branch_label(branch, label_key),
        )
        if len(branch.path) > 1:
            graph.add_edge(branch.path[:-1], branch.path)

    return graph


def _safe_bigtree_name(value: object) -> str:
    return quote(str(value), safe="")


def _bigtree_node_name(
    branch: TaxonomyBranch,
    *,
    index: int,
    name_strategy: BigtreeNameStrategy,
) -> str:
    if name_strategy == "index":
        return f"n{index:06d}"
    if name_strategy == "id":
        return _safe_bigtree_name(branch.path[-1])
    if name_strategy == "path":
        return _safe_bigtree_name(repr(branch.path))
    raise TxValidationError(
        'name_strategy must be one of "index", "id", or "path"'
    )


def to_bigtree(
    taxonomy: Taxonomy,
    *,
    root_name: str = "Taxonomy",
    label_key: LeafKey | None = None,
    name_strategy: BigtreeNameStrategy = "index",
    renumber: bool = False,
    renumber_options: Mapping[str, Any] | None = None,
) -> Any:
    """Export *taxonomy* to a ``bigtree.Tree``.

    ``bigtree`` requires a single root and string node names, so taxonorm
    forests are exported under a synthetic root.  Original node IDs and full
    ID paths are preserved as ``node_id`` and ``id_path`` attributes.  Leaves
    are stored as ``leaf_values`` because ``bigtree`` already uses ``leaves``
    for its own API.
    """
    source = _prepared_taxonomy(
        taxonomy,
        renumber=renumber,
        renumber_options=renumber_options,
    )
    bigtree = _require_optional_module("bigtree", "tree")

    root = bigtree.Node(
        root_name,
        id_path=(),
        depth=0,
        leaf_values={},
        label=root_name,
        is_taxonorm_synthetic_root=True,
        renumbered=renumber,
    )
    nodes: dict[tuple[Any, ...], Any] = {(): root}
    sibling_names: dict[tuple[Any, ...], set[str]] = {(): {root_name}}

    for index, branch in enumerate(source.iter_branches(), start=1):
        parent_path = branch.path[:-1]
        parent = nodes[parent_path]
        node_name = _bigtree_node_name(
            branch,
            index=index,
            name_strategy=name_strategy,
        )
        used_names = sibling_names.setdefault(parent_path, set())
        if node_name in used_names:
            raise TxValidationError(
                f"bigtree node name collision under {parent_path!r}: {node_name!r}"
            )
        used_names.add(node_name)

        nodes[branch.path] = bigtree.Node(
            node_name,
            parent=parent,
            node_id=branch.path[-1],
            id_path=branch.path,
            depth=len(branch.path),
            leaf_values=dict(branch.leaves),
            label=_branch_label(branch, label_key),
        )
        sibling_names.setdefault(branch.path, set())

    return bigtree.Tree(root)
