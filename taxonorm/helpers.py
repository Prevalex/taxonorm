"""
domain agnostic helpers
"""
import types
from typing import Any, get_origin, get_args, Union

def _as_isinstance_tuple(type_spec: Any) -> tuple[type, ...] | None:
    """Convert a type specification to an ``isinstance`` tuple.

    ``Any`` returns ``None`` to mean "accept everything".
    Parameterized generics such as ``list[int]`` are reduced to their origin.
    """
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
            f"{label} должен быть объектом класса {expected}. "
            f"Получено: {type(obj).__name__}: {obj!r}"
        )
