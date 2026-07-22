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
BigtreeSyntheticRoot = Literal["auto"] | bool

_TAXONORM_METADATA_ATTR = "_taxonorm"
_TAXONORM_METADATA_SCHEMA = 1


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
        _taxonorm={
            "schema": _TAXONORM_METADATA_SCHEMA,
            "synthetic_root": True,
            "renumbered": renumber,
        },
        id_path=(),
        depth=0,
        leaf_values={},
        label=root_name,
        is_taxonorm_synthetic_root=True,
        renumbered=renumber,
    )
    nodes: dict[tuple[Any, ...], Any] = {(): root}
    sibling_names: dict[tuple[Any, ...], set[str]] = {(): set()}

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

        metadata = {
            "schema": _TAXONORM_METADATA_SCHEMA,
            "node_id": branch.path[-1],
            "leaves": dict(branch.leaves),
        }

        nodes[branch.path] = bigtree.Node(
            node_name,
            parent=parent,
            _taxonorm=metadata,
            node_id=branch.path[-1],
            id_path=branch.path,
            depth=len(branch.path),
            leaf_values=dict(branch.leaves),
            label=_branch_label(branch, label_key),
        )
        sibling_names.setdefault(branch.path, set())

    return bigtree.Tree(root)


def _bigtree_metadata(node: Any) -> Mapping[str, Any]:
    metadata = getattr(node, _TAXONORM_METADATA_ATTR, None)
    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise TxValidationError(
            f"bigtree node {getattr(node, 'node_name', node)!r} has invalid "
            f"{_TAXONORM_METADATA_ATTR} metadata: expected a mapping"
        )
    schema = metadata.get("schema")
    if schema is not None and schema != _TAXONORM_METADATA_SCHEMA:
        raise TxValidationError(
            f"bigtree node {getattr(node, 'node_name', node)!r} uses "
            f"unsupported taxonorm metadata schema: {schema!r}"
        )
    return metadata


def _is_synthetic_bigtree_root(node: Any) -> bool:
    metadata = _bigtree_metadata(node)
    if metadata.get("synthetic_root") is True:
        return True
    return getattr(node, "is_taxonorm_synthetic_root", False) is True


def _bigtree_node_id(
    node: Any,
    metadata: Mapping[str, Any],
    *,
    id_attr: str,
    missing_id: Literal["name", "error"],
) -> Any:
    if hasattr(node, id_attr):
        return getattr(node, id_attr)
    if "node_id" in metadata:
        return metadata["node_id"]
    if missing_id == "name":
        return node.node_name
    raise TxValidationError(
        f"bigtree node {node.node_name!r} has no {id_attr!r} ID attribute"
    )


def _bigtree_node_leaves(
    node: Any,
    metadata: Mapping[str, Any],
    *,
    leaves_attr: str,
    attribute_map: Mapping[str, LeafKey] | None,
) -> dict[LeafKey, Any]:
    if hasattr(node, leaves_attr):
        source = getattr(node, leaves_attr, {})
    else:
        source = metadata.get("leaves", {})
    if source is None:
        source = {}
    if not isinstance(source, Mapping):
        raise TxValidationError(
            f"bigtree node {node.node_name!r} has invalid leaves: "
            f"expected a mapping, got {type(source).__name__}"
        )
    leaves = dict(source)
    for attribute, leaf_key in (attribute_map or {}).items():
        if hasattr(node, attribute):
            leaves[leaf_key] = getattr(node, attribute)
    return leaves


def from_bigtree(
    tree: Any,
    *,
    synthetic_root: BigtreeSyntheticRoot = "auto",
    id_attr: str = "node_id",
    leaves_attr: str = "leaf_values",
    attribute_map: Mapping[str, LeafKey] | None = None,
    missing_id: Literal["name", "error"] = "name",
) -> Taxonomy:
    """Import a ``bigtree.Tree`` or ``bigtree.Node`` into ``Taxonomy``.

    Trees produced by :func:`to_bigtree` round-trip losslessly in memory,
    including non-string IDs, arbitrary leaf keys, forests, and empty
    taxonomies.  For native bigtree nodes without taxonorm metadata,
    ``node_name`` is used as the node ID and leaves are empty unless
    ``leaves_attr`` or ``attribute_map`` supplies values.

    The current bigtree parent/child links are authoritative.  Stored
    ``id_path`` attributes are intentionally ignored, so moving a node in
    bigtree is reflected when it is imported back.
    """
    if synthetic_root != "auto" and not isinstance(synthetic_root, bool):
        raise TxValidationError(
            'synthetic_root must be "auto", True, or False'
        )
    if missing_id not in {"name", "error"}:
        raise TxValidationError('missing_id must be "name" or "error"')
    if not isinstance(id_attr, str) or not id_attr:
        raise TxValidationError("id_attr must be a non-empty string")
    if not isinstance(leaves_attr, str) or not leaves_attr:
        raise TxValidationError("leaves_attr must be a non-empty string")
    if attribute_map is not None and not isinstance(attribute_map, Mapping):
        raise TxValidationError("attribute_map must be a mapping or None")

    bigtree = _require_optional_module("bigtree", "tree")
    if isinstance(tree, bigtree.Tree):
        root = tree.node
    elif isinstance(tree, bigtree.Node):
        root = tree
    else:
        raise TxValidationError(
            "Expected a bigtree.Tree or bigtree.Node object, got: "
            f"{type(tree).__name__}"
        )

    strip_root = (
        _is_synthetic_bigtree_root(root)
        if synthetic_root == "auto"
        else synthetic_root
    )
    starting_nodes = list(root.children) if strip_root else [root]
    branches: list[list[Any]] = []
    seen_nodes: set[int] = set()
    stack: list[tuple[Any, tuple[Any, ...]]] = [
        (node, ()) for node in reversed(starting_nodes)
    ]

    while stack:
        node, parent_path = stack.pop()
        node_marker = id(node)
        if node_marker in seen_nodes:
            raise TxValidationError(
                "bigtree input contains a repeated node or cycle"
            )
        seen_nodes.add(node_marker)

        metadata = _bigtree_metadata(node)
        node_id = _bigtree_node_id(
            node,
            metadata,
            id_attr=id_attr,
            missing_id=missing_id,
        )
        path = parent_path + (node_id,)
        leaves = _bigtree_node_leaves(
            node,
            metadata,
            leaves_attr=leaves_attr,
            attribute_map=attribute_map,
        )
        branches.append([*path, leaves])
        stack.extend(
            (child, path) for child in reversed(tuple(node.children))
        )

    return Taxonomy.from_branches(branches)
