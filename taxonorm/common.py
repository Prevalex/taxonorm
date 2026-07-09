#! This module of the taxonorm package is intended to define structures and data types common to the entire package.
from dataclasses import dataclass, fields
from typing import TypeAlias

WARNINGS = True
DEBUG = True

W_CODEPAGE = 'utf-8'
R_CODEPAGE = 'utf-8-sig'
UTF8_BOM = 'utf-8-sig'
DEFAULT_LEAF_KEY = '@'
STYLE_ACCURACY = 0.05  # Allowed error rate when guessing a taxonomy style.
SNIFFER_ACCURACY = 2/3

@dataclass
class tMapper:
    """
    idmap - {...
                (id1,...idN):[Key1Value,...,keyJValue],
             ...
                }

    keymap: leaf key indexes {key1: index1, key2: index2, ...}, where
        each index points into the leaf key list
    min_width - minimum ID path length
    max_width - maximum ID path length
    """
    idmap: dict
    keymap: dict
    min_width: int
    max_width: int


@dataclass(frozen=True, slots=True)
class tStyle:
    # def __post_init__(self):
    #    validate_dataclass_types(self)

    @property
    def hints(self):
        return [('' if getattr(self, f.name) else 'N') + f.name[0].upper() for f in fields(self)]


@dataclass(frozen=True, slots=True)
class IpStyle(tStyle):
    # IP style flags used to keep parser/serializer signatures compact.
    header: bool | None  # Whether the table has a header.
    keys: bool | None  # Whether leaf keys are stored in the table.
    tabbed: bool | None  # Whether the ID path is tab-indented.

    @property
    def hints(self):
        base = super(IpStyle, self).hints
        return ['IP', *base]


@dataclass(frozen=True, slots=True)
class LpStyle(tStyle):
    # LP style flags used to keep parser/serializer signatures compact.
    header: bool | None  # Whether the table has a header.
    ids: bool | None  # Whether branch IDs are stored in the table.
    sparse: bool | None  # Whether the table uses sparse leaf paths.

    @property
    def hints(self):
        base = super(LpStyle, self).hints
        return ['LP', *base]

tStyler: TypeAlias = IpStyle | LpStyle


