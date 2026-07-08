from typing import Any, TypeGuard
from collections.abc import Hashable

from alib.introspection import repr_type
from alib.tables import is_empty_llist
from alib.validation import is_empty

from .errors import TxValidationError

def validate_leaf_keys(leaf_keys):
    """
    Проверяет корректность ключей листьев. Если обнаружено нарушение, то генерирует исключение.
    Для удобства отладки - в сообщении исключения фигурирует имя функции, вызвавшей данную
    проверочную функцию.
    Parameters
    ----------
    leaf_keys

    Returns
    -------
    None
    """
    if isinstance(leaf_keys, (list, tuple)):
        if leaf_keys:
            for key in leaf_keys:
                if is_valid_keyid(key):
                    continue
                else:
                    raise TxValidationError(f'Ключ листа {repr(key)} не соответствует требованиям к '
                                          f'ключам: hashable; not empty; not None')
            else:
                return
        else:
            raise TxValidationError('Список ключей листьев - пуст.')
    else:
        raise TxValidationError(f'Параметр leaf_keys должен быть списком или кортежем. '
                              f'Получено {type(leaf_keys)}:{repr(leaf_keys)}')


def validated_leaf_keys(leaf_keys) -> list[Hashable]:
    """
    Проверяет корректность ключей листьев. Если обнаружено нарушение, то генерирует исключение.
    Для удобства отладки - в сообщении исключения фигурирует имя функции, вызвавшей данную
    проверочную функцию.
    Если все Ок - возвращает копию списка или кортежа листьев, полученного на входе
    Parameters
    ----------
    leaf_keys

    Returns
    -------
    list of leaf_keys
    """
    validate_leaf_keys(leaf_keys)
    return list(dict.fromkeys(leaf_keys))  # (GPT4)- c дедупликацией ключей и сохранением порядка (python > 3.7)


def validate_branch_list(branch_list):
    if is_empty_llist(branch_list):
        raise TxValidationError('Список веток (branch_list) содержит пустые объекты или пуст.')


def validated_branch_list(branch_list):
    validate_branch_list(branch_list)  # returns True or ValueError Exception
    return [list(branch) for branch in branch_list]


def validate_style_attribs(**attribs):
    for _name, _value in attribs.items():
        if isinstance(_value, (bool, type(None))):
            continue
        else:
            raise TxValidationError(f'Триггер {_name} может иметь тип bool или быть None. '
                                  f'Получено: {_name}={repr(_value)}')

def validated_list_like(list_like: list[Any] | tuple[Any, ...] | None) -> list[Any]:
    """
        list_like: list or tuple
        returns it converted (type cast) to list
    """
    if list_like is None:
        return []

    if isinstance(list_like, (list, tuple)):
        if isinstance(list_like, tuple):
            return list(list_like)
        else:
            return list_like
    else:
        raise TxValidationError(f'An object of type list or tuple was expected. Received: {repr_type(list_like)}')

def is_valid_keyid(id_key: object, allow_empty: bool = False) -> TypeGuard[Hashable]:
    if isinstance(id_key, Hashable):
        return True if allow_empty else not is_empty(id_key)
    return False

def validated_header_titles(
    titles: list[Hashable] | tuple[Hashable, ...] | None,
) -> list[Hashable]:
    # Проверяем titles и приводим к list. А именно: tuple преобразуем в list, None преобразуем в пустой список.
    titles = validated_list_like(titles)  # (tuple -> list, None -> [], Any other -> exception )
    # Если заголовок задан списком - проверяем элементы списка на хэшируемость, разрешаем пустые
    for title in titles:
        if not is_valid_keyid(title, allow_empty=True):
            raise TxValidationError(
                f'The headers contain an unhashable title: {repr(title)}')
    return titles
