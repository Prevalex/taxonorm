"""Minimal call-site helpers used for diagnostics."""

from __future__ import annotations

from typing import Any, get_args, get_origin, Union
import inspect
import types


def inspect_location(*levels: int, joiner: str = "|") -> str:
    if not levels:
        levels = (0,)

    names: list[str] = []
    frame = inspect.currentframe()
    for level in levels:
        if not isinstance(level, int):
            raise TypeError(f"level must be int. Got: {level!r}")
        if level > 0:
            raise ValueError(f"level must be <= 0. Got: {level!r}")

        current = frame
        for _ in range(abs(level) + 1):
            current = current.f_back if current is not None else None
        names.append(current.f_code.co_name if current is not None else "<unknown>")
    return joiner.join(names)


def inspect_name() -> str:
    return inspect_location(0)


def inspect_upper_name() -> str:
    return inspect_location(-1)


def repr_type(value: Any) -> str:
    return f"{value!r}:{value.__class__.__name__}"


def _as_isinstance_tuple(type_spec: Any) -> tuple[type, ...] | None:
    if type_spec is Any:
        return None

    origin = get_origin(type_spec)
    if origin is Union or isinstance(type_spec, types.UnionType):
        collected: list[type] = []
        for arg in get_args(type_spec):
            converted = _as_isinstance_tuple(arg)
            if converted is None:
                return None
            collected.extend(converted)
        return tuple(collected)

    if origin is not None and isinstance(origin, type):
        return (origin,)
    if isinstance(type_spec, tuple) and all(isinstance(item, type) for item in type_spec):
        return type_spec
    if isinstance(type_spec, type):
        return (type_spec,)
    return (type(type_spec),)


def validate_type(obj: Any, label: str, typer: Any) -> None:
    acceptable = _as_isinstance_tuple(typer)
    if acceptable is None:
        return
    if not isinstance(obj, acceptable):
        expected = " | ".join(item.__name__ for item in acceptable)
        raise TypeError(
            f"{label} must be an instance of {expected}. "
            f"Got: {type(obj).__name__}: {obj!r}"
        )
