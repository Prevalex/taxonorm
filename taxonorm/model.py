"""Canonical in-memory representation of a taxonomy."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Hashable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal

from .errors import TxValidationError

NodeId = Hashable
LeafKey = Hashable
IdPath = tuple[NodeId, ...]
Leaves = dict[LeafKey, Any]
BranchRow = list[Any]
BranchTable = list[BranchRow]
TraversalOrder = Literal["preorder", "postorder", "breadth"]
MissedLeaf = Callable[[LeafKey, IdPath], Any] | None | str


def _is_non_empty_hashable(value: object) -> bool:
    """Apply the identifier/key rules documented by taxonorm."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return False
    try:
        hash(value)
    except TypeError:
        return False
    try:
        return len(value) > 0  # type: ignore[arg-type]
    except TypeError:
        return True


def _validated_path(path: Iterable[NodeId]) -> IdPath:
    result = tuple(path)
    if not result:
        raise TxValidationError("Путь узла не может быть пустым")
    for node_id in result:
        if not _is_non_empty_hashable(node_id):
            raise TxValidationError(
                f"ID узла должен быть непустым хэшируемым объектом: {node_id!r}"
            )
    return result


def _validated_leaves(leaves: Mapping[LeafKey, Any]) -> Leaves:
    if not isinstance(leaves, Mapping):
        raise TxValidationError(
            f"Листья узла должны быть отображением, получено: {type(leaves).__name__}"
        )
    result = dict(leaves)
    for key in result:
        if not _is_non_empty_hashable(key):
            raise TxValidationError(
                f"Ключ листа должен быть непустым хэшируемым объектом: {key!r}"
            )
    return result


def _validated_missed_leaf(
    missed_leaf: MissedLeaf,
) -> Callable[[LeafKey, IdPath], Any] | None:
    if missed_leaf is None:
        return None
    if isinstance(missed_leaf, str):
        if missed_leaf != "auto":
            raise TxValidationError(
                'missed_leaf должен быть функцией, None или строкой "auto"'
            )

        def missing_leaf_value(leaf_key: LeafKey, id_path: IdPath) -> Any:
            return "<" + str(leaf_key) + ":" + ".".join(map(str, id_path)) + ">"

        return missing_leaf_value
    if callable(missed_leaf):
        return missed_leaf
    raise TxValidationError(
        'missed_leaf должен быть функцией, None или строкой "auto"'
    )


@dataclass(frozen=True, slots=True)
class TaxonomyBranch:
    """A read-only path-and-leaves view returned while traversing a taxonomy."""

    path: IdPath
    leaves: Mapping[LeafKey, Any]


@dataclass(slots=True)
class TaxonomyNode:
    """One node in the prefix tree.

    Its ID is stored once as the key of the parent ``children`` mapping (or of
    ``Taxonomy.roots``). Repeated identifiers in different branches remain
    fully supported because node identity is its complete path.
    """

    _leaves: Leaves | None = field(default=None, repr=False)
    _children: dict[NodeId, TaxonomyNode] | None = field(default=None, repr=False)

    @property
    def leaves(self) -> Mapping[LeafKey, Any]:
        """A read-only view of this node's leaves."""
        leaves = self._leaves if self._leaves is not None else {}
        return MappingProxyType(leaves)

    @property
    def children(self) -> Mapping[NodeId, TaxonomyNode]:
        """A read-only view of child nodes, in insertion order."""
        children = self._children if self._children is not None else {}
        return MappingProxyType(children)


class Taxonomy:
    """A forest-backed taxonomy whose common path prefixes are shared."""

    __slots__ = ("_roots", "_size")

    def __init__(self) -> None:
        self._roots: dict[NodeId, TaxonomyNode] = {}
        self._size = 0

    @classmethod
    def from_branches(cls, branches: Iterable[Sequence[Any]]) -> Taxonomy:
        """Build a taxonomy from ``[[id, ..., {key: value}], ...]``."""
        taxonomy = cls()
        for index, branch in enumerate(branches):
            if not isinstance(branch, Sequence) or isinstance(branch, (str, bytes)):
                raise TxValidationError(f"Ветвь #{index} не является последовательностью")
            if len(branch) < 2:
                raise TxValidationError(f"Слишком короткая ветвь #{index}: {branch!r}")
            taxonomy.add_branch(branch[:-1], branch[-1])
        return taxonomy

    @property
    def roots(self) -> Mapping[NodeId, TaxonomyNode]:
        """A read-only view of root nodes, in insertion order."""
        return MappingProxyType(self._roots)

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return bool(self._size)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Taxonomy):
            return NotImplemented
        return self.to_branches() == other.to_branches()

    def __contains__(self, path: object) -> bool:
        if isinstance(path, (str, bytes)) or not isinstance(path, Iterable):
            return False
        try:
            self.get_node(path)
        except (KeyError, TxValidationError):
            return False
        return True

    def add_branch(
        self,
        path: Iterable[NodeId],
        leaves: Mapping[LeafKey, Any],
        *,
        replace: bool = False,
    ) -> TaxonomyNode:
        """Add a branch, creating any missing ancestors.

        Exact duplicate paths are rejected unless ``replace=True``.  This also
        distinguishes an ancestor created implicitly from one supplied later
        as its own branch.
        """
        id_path = _validated_path(path)
        leaf_values = _validated_leaves(leaves)
        children = self._roots
        node: TaxonomyNode | None = None

        for index, node_id in enumerate(id_path):
            node = children.get(node_id)
            if node is None:
                node = TaxonomyNode()
                children[node_id] = node
                self._size += 1
            if index < len(id_path) - 1:
                if node._children is None:
                    node._children = {}
                children = node._children

        assert node is not None
        if node._leaves is not None and not replace:
            raise TxValidationError(f"Путь {id_path!r} дублируется")
        node._leaves = leaf_values
        return node

    def update_leaves(
        self,
        path: Iterable[NodeId],
        leaves: Mapping[LeafKey, Any],
        *,
        replace: bool = False,
    ) -> TaxonomyNode:
        """Update a node's leaves, merging by default or replacing them."""
        node = self.get_node(path)
        leaf_values = _validated_leaves(leaves)
        current_leaves = node._leaves if node._leaves is not None else {}
        node._leaves = leaf_values if replace else {**current_leaves, **leaf_values}
        return node

    def remove_branch(
        self, path: Iterable[NodeId], *, recursive: bool = False
    ) -> TaxonomyNode:
        """Remove a node, requiring ``recursive=True`` for a non-leaf node."""
        id_path = _validated_path(path)
        children = self._roots
        for node_id in id_path[:-1]:
            next_children = children[node_id]._children
            if next_children is None:
                raise KeyError(id_path)
            children = next_children
        node = children[id_path[-1]]
        if node._children and not recursive:
            raise TxValidationError(
                f"Узел {id_path!r} имеет дочерние узлы; укажите recursive=True"
            )

        subtree_size = 0
        stack = [node]
        while stack:
            current = stack.pop()
            subtree_size += 1
            if current._children is not None:
                stack.extend(current._children.values())

        del children[id_path[-1]]
        self._size -= subtree_size
        return node

    def move_subtree(
        self,
        path: Iterable[NodeId],
        new_parent: Iterable[NodeId] | None,
        *,
        new_id: NodeId | None = None,
    ) -> TaxonomyNode:
        """Move a subtree, optionally changing the moved node's ID."""
        source_path = _validated_path(path)
        destination_parent = (
            tuple() if new_parent is None else _validated_path(new_parent)
        )
        target_id = source_path[-1] if new_id is None else new_id
        if not _is_non_empty_hashable(target_id):
            raise TxValidationError(
                f"ID узла должен быть непустым хэшируемым объектом: {target_id!r}"
            )
        if destination_parent[: len(source_path)] == source_path:
            raise TxValidationError("Нельзя переместить узел внутрь его поддерева")

        source_parent_node: TaxonomyNode | None = None
        source_children = self._roots
        for node_id in source_path[:-1]:
            source_parent_node = source_children[node_id]
            if source_parent_node._children is None:
                raise KeyError(source_path)
            source_children = source_parent_node._children
        node = source_children[source_path[-1]]

        destination_parent_node: TaxonomyNode | None = None
        destination_children = self._roots
        for node_id in destination_parent:
            destination_parent_node = destination_children[node_id]
            if destination_parent_node._children is None:
                destination_children = {}
            else:
                destination_children = destination_parent_node._children

        same_parent = source_children is destination_children
        if target_id in destination_children and not (
            same_parent and target_id == source_path[-1]
        ):
            raise TxValidationError(
                f"У родителя {destination_parent!r} уже есть дочерний ID {target_id!r}"
            )
        if same_parent:
            if target_id == source_path[-1]:
                return node
            renamed = {
                (target_id if node_id == source_path[-1] else node_id): child
                for node_id, child in source_children.items()
            }
            source_children.clear()
            source_children.update(renamed)
            return node

        del source_children[source_path[-1]]
        if source_parent_node is not None and not source_children:
            source_parent_node._children = None
        if destination_parent_node is not None and destination_parent_node._children is None:
            destination_parent_node._children = destination_children
        destination_children[target_id] = node
        return node

    def rename_node(self, path: Iterable[NodeId], new_id: NodeId) -> TaxonomyNode:
        """Rename a node without changing its position or sibling order."""
        id_path = _validated_path(path)
        parent_path = id_path[:-1] or None
        return self.move_subtree(id_path, parent_path, new_id=new_id)

    def get_node(self, path: Iterable[NodeId]) -> TaxonomyNode:
        """Return the node at *path* or raise ``KeyError``."""
        id_path = _validated_path(path)
        children = self._roots
        node: TaxonomyNode | None = None
        for node_id in id_path:
            node = children[node_id]
            children = node._children if node._children is not None else {}
        assert node is not None
        return node

    def iter_branches(
        self, order: TraversalOrder = "preorder"
    ) -> Iterator[TaxonomyBranch]:
        """Yield every node using stable preorder, postorder, or breadth-first traversal."""
        if order not in {"preorder", "postorder", "breadth"}:
            raise ValueError(f"Неизвестный порядок обхода: {order!r}")

        if order == "breadth":
            queue: deque[tuple[IdPath, TaxonomyNode]] = deque(
                ((node_id,), node) for node_id, node in self._roots.items()
            )
            while queue:
                path, node = queue.popleft()
                yield TaxonomyBranch(path, MappingProxyType(dict(node._leaves or {})))
                if node._children is not None:
                    queue.extend(
                        (path + (child_id,), child)
                        for child_id, child in node._children.items()
                    )
            return

        if order == "postorder":
            post_stack: list[tuple[IdPath, TaxonomyNode, bool]] = [
                ((node_id,), node, False)
                for node_id, node in reversed(self._roots.items())
            ]
            while post_stack:
                path, node, visited = post_stack.pop()
                if visited:
                    yield TaxonomyBranch(path, MappingProxyType(dict(node._leaves or {})))
                    continue
                post_stack.append((path, node, True))
                if node._children is not None:
                    post_stack.extend(
                        (path + (child_id,), child, False)
                        for child_id, child in reversed(node._children.items())
                    )
            return

        stack: list[tuple[IdPath, TaxonomyNode]] = [
            ((node_id,), node) for node_id, node in reversed(self._roots.items())
        ]
        while stack:
            path, node = stack.pop()
            yield TaxonomyBranch(path, MappingProxyType(dict(node._leaves or {})))
            if node._children is not None:
                stack.extend(
                    (path + (child_id,), child)
                    for child_id, child in reversed(node._children.items())
                )

    def find_branches(
        self,
        predicate: Callable[[TaxonomyBranch], bool],
        *,
        order: TraversalOrder = "preorder",
    ) -> Iterator[TaxonomyBranch]:
        """Yield branches accepted by *predicate* in the requested order."""
        return (branch for branch in self.iter_branches(order) if predicate(branch))

    def to_branches(self) -> BranchTable:
        """Return a defensive list-of-branches representation."""
        return [list(branch.path) + [dict(branch.leaves)] for branch in self.iter_branches()]

    def leaf_keys(self) -> tuple[LeafKey, ...]:
        """Return leaf keys in stable first-occurrence order."""
        return tuple(dict.fromkeys(key for branch in self.iter_branches() for key in branch.leaves))

    def leaf_path(
        self,
        path: Iterable[NodeId],
        key: LeafKey,
        *,
        missed_leaf: MissedLeaf = "auto",
    ) -> tuple[Any, ...]:
        """Return leaf values for *key* from the root through *path*."""
        missing_leaf_value = _validated_missed_leaf(missed_leaf)
        id_path = _validated_path(path)
        children = self._roots
        values: list[Any] = []
        for index, node_id in enumerate(id_path):
            node = children[node_id]
            current_path = id_path[: index + 1]
            if key in node.leaves:
                values.append(node.leaves[key])
            elif missing_leaf_value is None:
                values.append(None)
            else:
                values.append(missing_leaf_value(key, current_path))
            children = node._children if node._children is not None else {}
        return tuple(values)

    def iter_leaf_paths(
        self,
        key: LeafKey,
        *,
        order: TraversalOrder = "preorder",
        missed_leaf: MissedLeaf = "auto",
    ) -> Iterator[tuple[IdPath, tuple[Any, ...]]]:
        """Yield ``(id_path, leaf_path)`` pairs for *key*."""
        if order not in {"preorder", "postorder", "breadth"}:
            raise ValueError(f"Неизвестный порядок обхода: {order!r}")
        missing_leaf_value = _validated_missed_leaf(missed_leaf)

        def leaf_value(node: TaxonomyNode, path: IdPath) -> Any:
            leaves = node._leaves or {}
            if key in leaves:
                return leaves[key]
            if missing_leaf_value is None:
                return None
            return missing_leaf_value(key, path)

        if order == "breadth":
            queue: deque[tuple[IdPath, TaxonomyNode, tuple[Any, ...]]] = deque()
            for node_id, node in self._roots.items():
                root_path: IdPath = (node_id,)
                queue.append((root_path, node, (leaf_value(node, root_path),)))
            while queue:
                path, node, values = queue.popleft()
                yield path, values
                if node._children is not None:
                    for child_id, child in node._children.items():
                        child_path = path + (child_id,)
                        queue.append(
                            (child_path, child, values + (leaf_value(child, child_path),))
                        )
            return

        if order == "postorder":
            post_stack: list[tuple[IdPath, TaxonomyNode, tuple[Any, ...], bool]] = []
            for node_id, node in reversed(self._roots.items()):
                post_root_path: IdPath = (node_id,)
                post_stack.append(
                    (post_root_path, node, (leaf_value(node, post_root_path),), False)
                )
            while post_stack:
                path, node, values, visited = post_stack.pop()
                if visited:
                    yield path, values
                    continue
                post_stack.append((path, node, values, True))
                if node._children is not None:
                    for child_id, child in reversed(node._children.items()):
                        child_path = path + (child_id,)
                        post_stack.append(
                            (child_path, child, values + (leaf_value(child, child_path),), False)
                        )
            return

        stack: list[tuple[IdPath, TaxonomyNode, tuple[Any, ...]]] = []
        for node_id, node in reversed(self._roots.items()):
            preorder_root_path: IdPath = (node_id,)
            stack.append(
                (preorder_root_path, node, (leaf_value(node, preorder_root_path),))
            )
        while stack:
            path, node, values = stack.pop()
            yield path, values
            if node._children is not None:
                for child_id, child in reversed(node._children.items()):
                    child_path = path + (child_id,)
                    stack.append(
                        (child_path, child, values + (leaf_value(child, child_path),))
                    )
