#! This module of the taxonorm package is intended to define structures and data types common to the entire package.
from dataclasses import dataclass, fields
from typing import TypeAlias

WARNINGS = True
DEBUG = True

W_CODEPAGE = 'utf-8'
R_CODEPAGE = 'utf-8-sig'
UTF8_BOM = 'utf-8-sig'
DEFAULT_LEAF_KEY = '@'
STYLE_ACCURACY = 0.05  # процент ошибки, который мы считаем допустимым при угадывании стиля таксономии.
SNIFFER_ACCURACY = 2/3

@dataclass
class tMapper:
    """
    idmap - {...
                (id1,...idN):[Key1Value,...,keyJValue],
             ...
                }

    keymap: индексы ключей листьев { key1: index1, key2: index2, ...} где индекс - это индекс ключа в списке ключей
    min_width - минимальная длина пути id
    max_width - максимальная длина пути id
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
    # описывает свойства IP Стиля, предназначен для сокращения числа ключевых параметров, передаваемых функциям и
    # для более строгого контроля перечня и значений таких параметров
    header: bool | None  # Наличие (Да/Нет) заголовка
    keys: bool | None  # Ключи хранятся (Да/Нет)  в таксономии
    tabbed: bool | None  # Табулированный (Да/Нет)

    @property
    def hints(self):
        # получаем ЗНАЧЕНИЕ свойства базового класса и добавляем префикс
        base = super(IpStyle, self).hints
        return ['IP', *base]


@dataclass(frozen=True, slots=True)
class LpStyle(tStyle):
    # описывает свойства LP Стиля, предназначен для сокращения числа ключевых параметров, передаваемых функциям и
    # для более строгого контроля перечня и значений таких параметров
    header: bool | None  # Наличие (Да/Нет) заголовка
    ids: bool | None  # Идентификаторы ветвей хранятся (Да/Нет) в таксономии
    sparse: bool | None  # Разреженная (Да/Нет) таксономия

    @property
    def hints(self):
        # получаем ЗНАЧЕНИЕ свойства базового класса и добавляем префикс
        base = super(LpStyle, self).hints
        return ['LP', *base]  # или ['IP', *base]

tStyler: TypeAlias = IpStyle | LpStyle


