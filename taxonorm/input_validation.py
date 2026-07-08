"""User-facing validation of external taxonomy tables."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from typing import Any, Literal

from alib.validation import is_empty

from .common import IpStyle, LpStyle, tStyler
from .errors import TxInputValidationError
from .model import Taxonomy
from .validation import is_valid_keyid

Severity = Literal["error", "warning"]


def _short_repr(value: Any, limit: int = 120) -> str:
    rendered = repr(value)
    return rendered if len(rendered) <= limit else f"{rendered[: limit - 3]}..."


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One actionable problem found in external taxonomy data."""

    code: str
    message: str
    row: int | None = None
    column: int | None = None
    value: Any = None
    expected: str | None = None
    severity: Severity = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "row": self.row,
            "column": self.column,
            "value": self.value,
            "expected": self.expected,
            "severity": self.severity,
        }

    def format_text(self) -> str:
        location: list[str] = []
        if self.row is not None:
            location.append(f"строка {self.row}")
        if self.column is not None:
            location.append(f"столбец {self.column}")
        prefix = f"{', '.join(location)}: " if location else ""
        text = f"[{self.code}] {prefix}{self.message}"
        if self.value is not None:
            text += f" Получено: {_short_repr(self.value)}."
        if self.expected:
            text += f" Ожидалось: {self.expected}."
        return text


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Complete, non-throwing result of an input validation pass."""

    style: str
    source: str | None = None
    issues: tuple[ValidationIssue, ...] = ()
    checked_rows: int = 0
    truncated: bool = False

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def valid(self) -> bool:
        return not self.errors

    def __bool__(self) -> bool:
        return self.valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "style": self.style,
            "source": self.source,
            "valid": self.valid,
            "checked_rows": self.checked_rows,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "truncated": self.truncated,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def format_text(self, *, limit: int | None = None) -> str:
        errors = len(self.errors)
        warnings = len(self.warnings)
        source = f"; источник: {self.source}" if self.source else ""
        heading = (
            f"{self.style}{source}: обнаружено ошибок: {errors}; "
            f"предупреждений: {warnings}."
        )
        selected = self.issues if limit is None else self.issues[:limit]
        lines = [heading, *(issue.format_text() for issue in selected)]
        if self.truncated or len(selected) < len(self.issues):
            lines.append("Часть диагностик не показана.")
        return "\n".join(lines)

    def raise_for_errors(self) -> None:
        if not self.valid:
            raise TxInputValidationError(self)


@dataclass(slots=True)
class _Collector:
    style: str
    max_issues: int
    source: str | None = None
    issues: list[ValidationIssue] = field(default_factory=list)
    truncated: bool = False

    def add(
        self,
        code: str,
        message: str,
        *,
        row: int | None = None,
        column: int | None = None,
        value: Any = None,
        expected: str | None = None,
        severity: Severity = "error",
    ) -> None:
        if len(self.issues) >= self.max_issues:
            self.truncated = True
            return
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                row=row,
                column=column,
                value=value,
                expected=expected,
                severity=severity,
            )
        )

    def report(self, checked_rows: int) -> ValidationReport:
        return ValidationReport(
            style=self.style,
            source=self.source,
            issues=tuple(self.issues),
            checked_rows=checked_rows,
            truncated=self.truncated,
        )


def _style_name(styler: tStyler | None) -> str:
    return "UNKNOWN" if styler is None else "_".join(styler.hints)


def _trim_trailing_empty(row: Sequence[Any]) -> list[Any]:
    result = list(row)
    while result and is_empty(result[-1]):
        result.pop()
    return result


def _contains(values: Sequence[Any], target: Any) -> bool:
    return any(value == target for value in values)


def _first_key_index(row: Sequence[Any], leaf_keys: Sequence[Hashable]) -> int | None:
    for index, value in enumerate(row):
        if _contains(leaf_keys, value):
            return index
    return None


def _validated_configuration(
    styler: tStyler | None,
    leaf_keys: object,
    collector: _Collector,
) -> list[Hashable]:
    if styler is None:
        collector.add("style.missing", "Стиль таксономии не задан")
    else:
        for descriptor in fields(styler):
            value = getattr(styler, descriptor.name)
            if not isinstance(value, bool):
                collector.add(
                    "style.incomplete",
                    f"Свойство стиля {descriptor.name!r} должно быть определено",
                    value=value,
                    expected="True или False",
                )

    if not isinstance(leaf_keys, Sequence) or isinstance(leaf_keys, (str, bytes)):
        collector.add(
            "leaf_keys.type",
            "leaf_keys должен быть списком или кортежем",
            value=leaf_keys,
        )
        return []
    if not leaf_keys:
        collector.add("leaf_keys.empty", "Список ключей листьев пуст")
        return []

    result: list[Hashable] = []
    for index, key in enumerate(leaf_keys, start=1):
        if not is_valid_keyid(key):
            collector.add(
                "leaf_keys.invalid",
                "Ключ листа должен быть непустым хэшируемым объектом",
                column=index,
                value=key,
            )
            continue
        if key in result:
            collector.add(
                "leaf_keys.duplicate",
                "Ключ листа указан повторно и будет использован один раз",
                column=index,
                value=key,
                severity="warning",
            )
            continue
        result.append(key)
    return result


def _normalize_rows(
    branch_list: object, collector: _Collector
) -> list[tuple[int, list[Any]]]:
    if not isinstance(branch_list, Sequence) or isinstance(branch_list, (str, bytes)):
        collector.add(
            "table.type",
            "Таксономия должна быть последовательностью строк",
            value=branch_list,
        )
        return []
    if not branch_list:
        collector.add("table.empty", "Таблица таксономии пуста")
        return []

    rows: list[tuple[int, list[Any]]] = []
    for row_number, row in enumerate(branch_list, start=1):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            collector.add(
                "row.type",
                "Строка должна быть последовательностью ячеек",
                row=row_number,
                value=row,
            )
            continue
        converted = list(row)
        if not converted or all(is_empty(value) for value in converted):
            collector.add(
                "row.empty",
                "Пустая строка будет пропущена",
                row=row_number,
                severity="warning",
            )
        rows.append((row_number, converted))
    return rows


def _data_rows(
    rows: list[tuple[int, list[Any]]],
    header: bool,
    collector: _Collector,
) -> list[tuple[int, list[Any]]]:
    if header and not rows:
        return []
    data = rows[1:] if header else rows
    nonempty = [item for item in data if any(not is_empty(value) for value in item[1])]
    if not nonempty:
        collector.add("table.no_data", "После заголовка нет строк данных")
    return nonempty


def _validate_id_cells(
    cells: Sequence[Any], row_number: int, collector: _Collector
) -> tuple[Hashable, ...] | None:
    if not cells:
        collector.add(
            "id.missing",
            "В строке отсутствует ID-путь",
            row=row_number,
            expected="хотя бы один непустой ID",
        )
        return None
    valid: list[Hashable] = []
    invalid = False
    for column, value in enumerate(cells, start=1):
        if not is_valid_keyid(value):
            collector.add(
                "id.invalid",
                "ID должен быть непустым хэшируемым объектом",
                row=row_number,
                column=column,
                value=value,
            )
            invalid = True
        else:
            valid.append(value)
    return None if invalid else tuple(valid)


def _record_path(
    path: tuple[Hashable, ...] | None,
    row_number: int,
    seen: dict[tuple[Hashable, ...], int],
    collector: _Collector,
) -> None:
    if path is None:
        return
    previous = seen.get(path)
    if previous is not None:
        collector.add(
            "path.duplicate",
            f"ID-путь уже объявлен в строке {previous}",
            row=row_number,
            value=path,
        )
    else:
        seen[path] = row_number


def _validate_ip_header_keys(
    rows: list[tuple[int, list[Any]]],
    leaf_keys: list[Hashable],
    collector: _Collector,
) -> None:
    if not rows:
        return
    _, header = rows[0]
    first_key = _first_key_index(header, leaf_keys)
    if first_key is None:
        collector.add(
            "ip.header.keys_missing",
            "В заголовке не найден ни один переданный ключ листа",
            row=1,
            value=header,
            expected=f"один или несколько ключей из {leaf_keys!r}",
        )
        return
    for key in leaf_keys:
        positions = [index for index, value in enumerate(header) if value == key]
        if not positions:
            collector.add(
                "ip.header.key_missing",
                f"Ключ листа {key!r} отсутствует в заголовке",
                row=1,
            )
        elif len(positions) > 1:
            collector.add(
                "ip.header.key_duplicate",
                f"Ключ листа {key!r} повторяется в заголовке",
                row=1,
                column=positions[1] + 1,
            )

    seen: dict[tuple[Hashable, ...], int] = {}
    for row_number, row in _data_rows(rows, True, collector):
        raw_ids = [value for value in row[:first_key] if not is_empty(value)]
        path = _validate_id_cells(raw_ids, row_number, collector)
        _record_path(path, row_number, seen, collector)


def _validate_ip_keyed_rows(
    rows: list[tuple[int, list[Any]]],
    style: IpStyle,
    leaf_keys: list[Hashable],
    collector: _Collector,
) -> None:
    seen_paths: dict[tuple[Hashable, ...], int] = {}
    for row_number, source in _data_rows(rows, bool(style.header), collector):
        row = _trim_trailing_empty(source)
        first_key = _first_key_index(row, leaf_keys)
        if first_key is None:
            collector.add(
                "ip.row.key_missing",
                "В строке не найдено начало группы key/value",
                row=row_number,
                value=row,
                expected=f"ключ из {leaf_keys!r}",
            )
            continue

        id_source = list(row[:first_key])
        if not style.tabbed and any(is_empty(value) for value in id_source):
            collector.add(
                "ip.id.gap",
                "В нетабулированном ID-пути обнаружена пустая ячейка",
                row=row_number,
                value=id_source,
            )
        ids = [value for value in id_source if not is_empty(value)]
        path = _validate_id_cells(ids, row_number, collector)
        _record_path(path, row_number, seen_paths, collector)

        kv_cells = row[first_key:]
        seen_keys: list[Hashable] = []
        for offset in range(0, len(kv_cells), 2):
            key = kv_cells[offset]
            column = first_key + offset + 1
            if not is_valid_keyid(key):
                collector.add(
                    "ip.row.key_invalid",
                    "Ключ в группе key/value должен быть непустым и хэшируемым",
                    row=row_number,
                    column=column,
                    value=key,
                )
                continue
            if key in seen_keys:
                collector.add(
                    "ip.row.key_duplicate",
                    "Ключ листа повторяется в строке",
                    row=row_number,
                    column=column,
                    value=key,
                )
            else:
                seen_keys.append(key)
            if key not in leaf_keys:
                collector.add(
                    "ip.row.key_unknown",
                    "Ключ отсутствует в переданном leaf_keys и будет проигнорирован",
                    row=row_number,
                    column=column,
                    value=key,
                    severity="warning",
                )


def _validate_ip_without_keys(
    rows: list[tuple[int, list[Any]]],
    style: IpStyle,
    leaf_keys: list[Hashable],
    collector: _Collector,
) -> None:
    leaf_count = len(leaf_keys)
    seen_paths: dict[tuple[Hashable, ...], int] = {}
    for row_number, row in _data_rows(rows, bool(style.header), collector):
        if len(row) < leaf_count + 1:
            collector.add(
                "ip.row.too_short",
                "Недостаточно ячеек для ID и значений листьев",
                row=row_number,
                value=row,
                expected=f"не менее {leaf_count + 1} ячеек",
            )
            continue
        id_cells = list(row[:-leaf_count])
        while id_cells and is_empty(id_cells[-1]):
            id_cells.pop()
        path = _validate_id_cells(id_cells, row_number, collector)
        _record_path(path, row_number, seen_paths, collector)


def _validate_ip(
    rows: list[tuple[int, list[Any]]],
    style: IpStyle,
    leaf_keys: list[Hashable],
    collector: _Collector,
) -> None:
    if style.header and style.keys and style.tabbed:
        _validate_ip_header_keys(rows, leaf_keys, collector)
    elif style.keys:
        _validate_ip_keyed_rows(rows, style, leaf_keys, collector)
    else:
        _validate_ip_without_keys(rows, style, leaf_keys, collector)


def _find_equal(values: Sequence[Any], target: Any) -> int | None:
    for index, value in enumerate(values):
        try:
            if value == target:
                return index
        except Exception:  # equality belongs to user-provided leaf objects
            continue
    return None


def _validate_lp_ids_dense(
    rows: list[tuple[int, list[Any]]], collector: _Collector
) -> None:
    ids_seen: dict[Hashable, int] = {}
    hashable_terminals: dict[Hashable, int] = {}
    unhashable_terminals: list[Any] = []
    unhashable_rows: list[int] = []
    prepared: list[tuple[int, list[Any]]] = []

    for row_number, source in rows:
        row = _trim_trailing_empty(source)
        if len(row) < 2:
            collector.add(
                "lp.row.too_short",
                "LP-строка с ID должна содержать ID и хотя бы один лист",
                row=row_number,
                value=row,
            )
            continue
        node_id = row[0]
        if not is_valid_keyid(node_id):
            collector.add(
                "id.invalid",
                "ID должен быть непустым хэшируемым объектом",
                row=row_number,
                column=1,
                value=node_id,
            )
        elif node_id in ids_seen:
            collector.add(
                "lp.id.duplicate",
                f"ID уже объявлен в строке {ids_seen[node_id]}",
                row=row_number,
                column=1,
                value=node_id,
            )
        else:
            ids_seen[node_id] = row_number

        leaves = row[1:]
        for index, value in enumerate(leaves, start=2):
            if is_empty(value):
                collector.add(
                    "lp.leaf.gap",
                    "В плотном leaf-пути обнаружена пустая ячейка",
                    row=row_number,
                    column=index,
                    value=value,
                )
        terminal = leaves[-1]
        if isinstance(terminal, Hashable):
            previous_terminal = hashable_terminals.get(terminal)
            if previous_terminal is not None:
                collector.add(
                    "lp.leaf.duplicate",
                    f"Конечное значение листа уже объявлено в строке {previous_terminal}",
                    row=row_number,
                    column=len(row),
                    value=terminal,
                )
            else:
                hashable_terminals[terminal] = row_number
        else:
            duplicate = _find_equal(unhashable_terminals, terminal)
            if duplicate is not None:
                collector.add(
                    "lp.leaf.duplicate",
                    f"Конечное значение листа уже объявлено в строке {unhashable_rows[duplicate]}",
                    row=row_number,
                    column=len(row),
                    value=terminal,
                )
            else:
                unhashable_terminals.append(terminal)
                unhashable_rows.append(row_number)
        prepared.append((row_number, leaves))

    for row_number, leaves in prepared:
        for offset, value in enumerate(leaves, start=2):
            if is_empty(value):
                continue
            resolved = (
                value in hashable_terminals
                if isinstance(value, Hashable)
                else _find_equal(unhashable_terminals, value) is not None
            )
            if not resolved:
                collector.add(
                    "lp.leaf.unresolved",
                    "Для элемента leaf-пути не найдена строка с соответствующим конечным листом",
                    row=row_number,
                    column=offset,
                    value=value,
                )


def _validate_lp_no_ids_dense(
    rows: list[tuple[int, list[Any]]], collector: _Collector
) -> None:
    seen_paths: dict[tuple[Hashable, ...], int] = {}
    for row_number, source in rows:
        row = _trim_trailing_empty(source)
        if not row:
            collector.add(
                "lp.row.no_leaves",
                "LP-строка без ID не содержит leaf-путь",
                row=row_number,
            )
            continue
        path: list[Hashable] = []
        invalid = False
        for column, value in enumerate(row, start=1):
            if is_empty(value):
                collector.add(
                    "lp.leaf.gap",
                    "В плотном leaf-пути обнаружена пустая ячейка",
                    row=row_number,
                    column=column,
                )
                invalid = True
            elif not isinstance(value, Hashable):
                collector.add(
                    "lp.ni.leaf_unhashable",
                    "LP без ID требует хэшируемые значения leaf-пути",
                    row=row_number,
                    column=column,
                    value=value,
                )
                invalid = True
            else:
                path.append(value)
        if invalid:
            continue
        path_tuple = tuple(path)
        previous = seen_paths.get(path_tuple)
        if previous is not None:
            collector.add(
                "lp.path.duplicate",
                f"Leaf-путь уже объявлен в строке {previous}",
                row=row_number,
                value=path_tuple,
            )
        else:
            seen_paths[path_tuple] = row_number


def _expand_sparse_lp(
    rows: list[tuple[int, list[Any]]],
    *,
    ids: bool,
    collector: _Collector,
) -> list[tuple[int, list[Any]]]:
    stamp: list[Any] = [None]
    dense: list[tuple[int, list[Any]]] = []
    for row_number, row in rows:
        if ids:
            if not row:
                collector.add("lp.row.too_short", "В sparse-строке отсутствует ID", row=row_number)
                continue
            node_id = row[0]
            if not is_valid_keyid(node_id):
                collector.add(
                    "id.invalid",
                    "ID должен быть непустым хэшируемым объектом",
                    row=row_number,
                    column=1,
                    value=node_id,
                )
            carrier = list(row[1:])
        else:
            node_id = None
            carrier = list(row)

        if len(carrier) < len(stamp):
            stamp = stamp[: len(carrier)]
        elif len(carrier) > len(stamp):
            stamp.extend([None] * (len(carrier) - len(stamp)))

        changed = [index for index, value in enumerate(carrier) if not is_empty(value)]
        if not changed:
            collector.add(
                "lp.sparse.no_value",
                "Sparse-строка не содержит нового значения листа",
                row=row_number,
                value=row,
            )
            continue
        if len(changed) > 1:
            collector.add(
                "lp.sparse.multiple_values",
                "Sparse-строка должна содержать ровно одно новое значение листа",
                row=row_number,
                value=row,
                expected="одна непустая ячейка leaf-пути",
            )
        index = changed[0]
        stamp[index] = carrier[index]
        stamp = stamp[: index + 1] + [None] * len(stamp[index + 1 :])
        effective = stamp[: index + 1]
        for missing_index, value in enumerate(effective):
            if is_empty(value):
                collector.add(
                    "lp.sparse.unresolved",
                    "Значение sparse-пути невозможно восстановить из предыдущих строк",
                    row=row_number,
                    column=missing_index + (2 if ids else 1),
                )
        dense_row = ([node_id] if ids else []) + effective
        dense.append((row_number, dense_row))
    return dense


def _validate_lp(
    rows: list[tuple[int, list[Any]]],
    style: LpStyle,
    leaf_keys: list[Hashable],
    collector: _Collector,
) -> None:
    if len(leaf_keys) > 1:
        collector.add(
            "lp.leaf_keys.extra",
            "LP использует только первый ключ листа; остальные будут проигнорированы",
            value=leaf_keys[1:],
            severity="warning",
        )
    data = _data_rows(rows, bool(style.header), collector)
    if style.sparse:
        data = _expand_sparse_lp(data, ids=bool(style.ids), collector=collector)
    if style.ids:
        _validate_lp_ids_dense(data, collector)
    else:
        _validate_lp_no_ids_dense(data, collector)


def validate_input(
    branch_list: object,
    *,
    styler: tStyler | None,
    leaf_keys: object,
    max_issues: int = 100,
    source: str | None = None,
) -> ValidationReport:
    """Validate an external IP/LP table without parsing or raising."""
    if max_issues < 1:
        raise ValueError("max_issues must be positive")
    collector = _Collector(_style_name(styler), max_issues, source)
    keys = _validated_configuration(styler, leaf_keys, collector)
    rows = _normalize_rows(branch_list, collector)
    if styler is not None and keys and rows:
        if isinstance(styler, IpStyle):
            _validate_ip(rows, styler, keys, collector)
        elif isinstance(styler, LpStyle):
            _validate_lp(rows, styler, keys, collector)
        else:
            collector.add(
                "style.unsupported",
                "Тип стиля не поддерживается",
                value=styler,
            )
    return collector.report(len(rows))


def validate_taxonomy(
    taxonomy: object, *, max_issues: int = 100
) -> ValidationReport:
    """Audit an already-built Taxonomy and return a structured report."""
    collector = _Collector("Taxonomy", max_issues)
    if not isinstance(taxonomy, Taxonomy):
        collector.add(
            "taxonomy.type",
            "Ожидался объект Taxonomy",
            value=taxonomy,
        )
        return collector.report(0)
    if not taxonomy:
        collector.add(
            "taxonomy.empty",
            "Таксономия не содержит узлов",
            severity="warning",
        )
    checked = 0
    for checked, branch in enumerate(taxonomy.iter_branches(), start=1):
        for column, node_id in enumerate(branch.path, start=1):
            if not is_valid_keyid(node_id):
                collector.add(
                    "taxonomy.id.invalid",
                    "В модели обнаружен некорректный ID",
                    row=checked,
                    column=column,
                    value=node_id,
                )
        if not isinstance(branch.leaves, Mapping):
            collector.add(
                "taxonomy.leaves.type",
                "Листья узла не являются отображением",
                row=checked,
                value=branch.leaves,
            )
            continue
        for key in branch.leaves:
            if not is_valid_keyid(key):
                collector.add(
                    "taxonomy.leaf_key.invalid",
                    "В модели обнаружен некорректный ключ листа",
                    row=checked,
                    value=key,
                )
    return collector.report(checked)
