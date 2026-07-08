"""Helpers for rebuilding full IP paths from unique-ID path chunks."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from typing import Any

from alib.validation import is_valid_keyid

from taxonorm.errors import TxConversionError, TxParsingError
from taxonorm.model import Taxonomy


def _validate_chunk(chunk: Sequence[Any], row_index: int) -> tuple[tuple[Hashable, ...], dict[Hashable, Any]]:
    if len(chunk) < 2:
        raise TxParsingError(f"IP-обрезок #{row_index} слишком короткий: {chunk!r}")
    if not isinstance(chunk[-1], Mapping):
        raise TxParsingError(
            f"Последний элемент IP-обрезка #{row_index} должен быть словарём листьев"
        )

    ids: list[Hashable] = []
    for column, node_id in enumerate(chunk[:-1], start=1):
        if not is_valid_keyid(node_id):
            raise TxParsingError(
                f"ID {node_id!r} в IP-обрезке #{row_index}, столбец {column} "
                "не соответствует требованиям к ID"
            )
        ids.append(node_id)

    if len(ids) != len(set(ids)):
        raise TxParsingError(
            f"IP-обрезок #{row_index} содержит повторяющийся ID: {chunk!r}"
        )

    return tuple(ids), dict(chunk[-1])


def _resolve_path(
    node_id: Hashable,
    parent_by_id: Mapping[Hashable, Hashable],
) -> tuple[Hashable, ...]:
    path = [node_id]
    seen = {node_id}
    current = node_id

    while current in parent_by_id:
        parent = parent_by_id[current]
        if parent in seen:
            raise TxParsingError(
                f"В IP-обрезках обнаружен цикл: {parent!r} уже встречался в пути {path!r}"
            )
        path.append(parent)
        seen.add(parent)
        current = parent

    path.reverse()
    return tuple(path)


def restore_unique_ip_chunks(chunks: Sequence[Sequence[Any]]) -> list[list[Any]]:
    """Restore full IP branches from partial path chunks.

    Each input row must already be in the internal branch exchange form:
    ``[id1, ..., idN, {leaf_key: value}]``. The leaf dictionary belongs to
    ``idN``. Restoration is possible only when every node ID has at most one
    parent across all chunks.
    """
    parent_by_id: dict[Hashable, Hashable] = {}
    leaves_by_terminal_id: dict[Hashable, dict[Hashable, Any]] = {}
    terminal_order: list[Hashable] = []

    for row_index, chunk in enumerate(chunks, start=1):
        ids, leaves = _validate_chunk(chunk, row_index)

        for parent, child in zip(ids, ids[1:]):
            previous_parent = parent_by_id.get(child)
            if previous_parent is not None and previous_parent != parent:
                raise TxParsingError(
                    f"ID {child!r} имеет более одного родителя: "
                    f"{previous_parent!r} и {parent!r}"
                )
            parent_by_id[child] = parent

        terminal_id = ids[-1]
        if terminal_id in leaves_by_terminal_id:
            if leaves_by_terminal_id[terminal_id] != leaves:
                raise TxParsingError(
                    f"ID {terminal_id!r} описан несколькими наборами листьев"
                )
            continue

        leaves_by_terminal_id[terminal_id] = leaves
        terminal_order.append(terminal_id)

    restored: list[list[Any]] = []
    emitted_paths: set[tuple[Hashable, ...]] = set()
    for terminal_id in terminal_order:
        path = _resolve_path(terminal_id, parent_by_id)
        if path in emitted_paths:
            continue
        emitted_paths.add(path)
        restored.append(list(path) + [dict(leaves_by_terminal_id[terminal_id])])

    return restored


def _validate_max_chunk_len(max_chunk_len: int) -> int:
    if isinstance(max_chunk_len, bool) or not isinstance(max_chunk_len, int):
        raise TxConversionError(
            f"max_chunk_len должен быть целым числом не меньше 2. Получено: {max_chunk_len!r}"
        )
    if max_chunk_len < 2:
        raise TxConversionError(
            f"max_chunk_len должен быть не меньше 2. Получено: {max_chunk_len!r}"
        )
    return max_chunk_len


def _assert_unique_taxonomy_ids(taxonomy: Taxonomy) -> None:
    seen: dict[Hashable, tuple[Hashable, ...]] = {}
    for branch in taxonomy.iter_branches():
        node_id = branch.path[-1]
        previous_path = seen.get(node_id)
        if previous_path is not None:
            raise TxConversionError(
                f"ID таксономии должны быть уникальны для дробления на IP-обрезки: "
                f"{node_id!r} встречается в путях {previous_path!r} и {branch.path!r}"
            )
        seen[node_id] = branch.path


def split_to_unique_ip_chunks(
    taxonomy: Taxonomy,
    max_chunk_len: int = 2,
) -> list[list[Any]]:
    """Split a taxonomy into unique-ID IP chunks.

    The result uses the internal branch exchange form:
    ``[id1, ..., idN, {leaf_key: value}]``. Each chunk contains no more than
    ``max_chunk_len`` IDs and can be restored with ``restore_unique_ip_chunks``
    when all node IDs in the source taxonomy are unique.
    """
    if not isinstance(taxonomy, Taxonomy):
        raise TxConversionError(
            f"Ожидался объект Taxonomy, получено: {type(taxonomy).__name__}"
        )
    max_chunk_len = _validate_max_chunk_len(max_chunk_len)
    _assert_unique_taxonomy_ids(taxonomy)

    chunks: list[list[Any]] = []
    for branch in taxonomy.iter_branches():
        chunk_path = branch.path[-max_chunk_len:]
        chunks.append(list(chunk_path) + [dict(branch.leaves)])
    return chunks
