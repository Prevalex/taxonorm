#! This module of the taxonorm package is intended to perform operations with taxonomy
from typing import Any
from collections.abc import Hashable, Callable

from taxonorm._console import wrn
from taxonorm._introspection import inspect_location, validate_type, repr_type
from taxonorm._sequences import resized_list
from taxonorm._tables import sorted_llist

from taxonorm.common import tMapper, tStyler, DEFAULT_LEAF_KEY, IpStyle, LpStyle
from taxonorm.chunks import split_to_unique_ip_chunks
from taxonorm.validation import validated_leaf_keys, validated_list_like, validated_header_titles
from taxonorm.errors import TxConversionError
from taxonorm.model import Taxonomy
from taxonorm.validation import is_valid_keyid

def complete_taxonomy(taxonomy):
    """Add implicit ancestor branches that are missing from a branch table.

    Example input:

    [
     [0,1,2,   {'@':'Leaf2'}],
     [0,1,2,3, {'@':'Leaf3'}],
     ]

    Result:

    [
     [0,1,2,   {'@':'Leaf2'}],
     [0,1,2,3, {'@':'Leaf3'}],
     [0, {}],
     [0, 1, {}],
     ]

    """
    seen = set()
    for branch in taxonomy:
        body = list(branch[:-1])
        seen.add(tuple(body))

    missed = list()
    for branch in taxonomy:
        body = list(branch[:-1])
        while len(body) > 0:
            if tuple(body) not in seen:
                missed.append(body + [dict()])
                seen.add(tuple(body))
            body.pop()

    return taxonomy + missed


def create_mapper(taxonomy: Taxonomy,
                  key_order: list[Hashable] | None = None,
                  sort_cvt: Callable | str | None = 'auto',
                  missed_leaf: Callable | None | str = 'auto') -> tMapper:
    """Create a mapper used by serializers.

    ``idmap`` maps an ID path to the ordered leaf values for that node.
    ``keymap`` maps leaf keys to indexes in each value list and defines the
    shared leaf order for all rows.
    """

    if not isinstance(taxonomy, Taxonomy):
        raise TxConversionError(
            f"Expected a Taxonomy object, got: {type(taxonomy).__name__}"
        )
    if not taxonomy:
        raise TxConversionError("Taxonomy is empty")

    return _create_mapper_from_branches(
        taxonomy.to_branches(),
        key_order=key_order,
        sort_cvt=sort_cvt,
        missed_leaf=missed_leaf,
    )


def _create_mapper_from_branches(branches: list[list[Any]],
                                 key_order: list[Hashable] | None = None,
                                 sort_cvt: Callable | str | None = 'auto',
                                 missed_leaf: Callable | None | str = 'auto') -> tMapper:
    def _missing_leaf_fun(leaf_key, id_path):
        return '<' + str(leaf_key) + ':' + '.'.join(list(map(str, id_path))) + '>'

    if missed_leaf is None:
        pass
    elif isinstance(missed_leaf, str):
        if missed_leaf == 'auto':
            missed_leaf = _missing_leaf_fun
        else:
            raise TxConversionError(
                'missed_leaf must be a callable, None, or the string "auto". '
                f"Got missing_leaf={missed_leaf!r}"
            )
    elif not callable(missed_leaf):
        raise TxConversionError(
            'missed_leaf must be a callable, the string "auto", or None. '
            f"Got {type(missed_leaf)}={missed_leaf}"
        )

    if key_order is None:
        key_order = []
    else:
        try:
            key_order = validated_leaf_keys(key_order)
        except ValueError as err:
            raise TxConversionError(f"{str(err)}") from err

    if not branches:
        raise TxConversionError("Taxonomy is empty")

    # Sorting improves readability and is required for LP sparse output.
    branches = sorted_llist(
        branches, stop=-1, sort_cvt=sort_cvt, headtail=0
    )

    taxonomy_keys = []

    # Preserve first-seen key order while also measuring the maximum path width.
    max_width = 0
    for branch in branches:
        max_width = max(max_width, len(branch))
        for _key in branch[-1]:
            if _key not in taxonomy_keys:
                taxonomy_keys.append(_key)

    tx_keys_in_key_order = [_key for _key in key_order if _key in taxonomy_keys]
    rest_of_tx_keys = [_key for _key in taxonomy_keys if _key not in key_order]

    leaf_keys = tx_keys_in_key_order + rest_of_tx_keys

    id_to_leaves_dict = dict()
    min_width = max_width

    for branch in branches:
        min_width = min(min_width, len(branch))
        branch_id_path = tuple(branch[:-1])

        branch_leaves = branch[-1]
        branch_leaf_list = []

        for _key in leaf_keys:
            if _key in branch_leaves:
                branch_leaf_list.append(branch_leaves[_key])
            elif missed_leaf is None:
                branch_leaf_list.append(None)
            else:
                branch_leaf_list.append(missed_leaf(_key, branch_id_path))

        ### branch_leaf_list = [branch[-1].get(_key, None) for _key in leaf_keys]
        id_to_leaves_dict[branch_id_path] = branch_leaf_list

    key_to_leaf_index_dict = dict([(_key, _idx) for _idx, _key in enumerate(leaf_keys)])

    min_width -= 1
    max_width -= 1

    return tMapper(idmap=id_to_leaves_dict, keymap=key_to_leaf_index_dict, min_width=min_width, max_width=max_width)


def serialize_ip_h_k_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width) + leaf_keys
    table = [titles]
    for ids, leaves in mapper.idmap.items():
        row = resized_list(list(ids), mapper.max_width) + leaves
        table.append(row)
    return table


def serialize_ip_h_k_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width + len(leaf_keys) * 2)
    table = [titles] + serialize_ip_nh_k_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)
    return table


def serialize_ip_h_nk_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width + len(leaf_keys))
    table = [titles] + serialize_ip_nh_nk_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)
    return table


def serialize_ip_h_nk_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    titles = resized_list(titles, mapper.max_width + len(leaf_keys))
    table = [titles] + serialize_ip_nh_nk_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)
    return table


def serialize_ip_nh_k_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():
        row = resized_list(list(ids), mapper.max_width) + [x for pair in zip(leaf_keys, leaves) for x in pair]
        table.append(row)
    return table


def serialize_ip_nh_k_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():
        row = list(ids) + [x for pair in zip(leaf_keys, leaves) for x in pair]
        table.append(row)
    return table


def serialize_ip_nh_nk_t(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():
        row = resized_list(list(ids), mapper.max_width) + leaves
        table.append(row)
    return table


def serialize_ip_nh_nk_nt(mapper: tMapper, *, leaf_keys:list[Hashable], titles: list[Hashable]) -> list[list[Any]]:
    table=[]
    for ids, leaves in mapper.idmap.items():
        row = list(ids) + leaves
        table.append(row)
    return table

def serialize_ip_taxonomy(mapper: tMapper, styler: IpStyle, *, titles: tuple | list | None = None) -> list[list[Any]]:
    """Serialize a taxonomy mapper to an IP-style table."""

    validate_type(mapper, 'mapper', tMapper)
    validate_type(styler, 'styler', IpStyle)

    leaf_keys = validated_leaf_keys(list(mapper.keymap))

    titles = validated_header_titles(titles)

    match styler:

        case IpStyle(header=True, keys=True, tabbed=True):
            return serialize_ip_h_k_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=True, keys=True, tabbed=False):
            return serialize_ip_h_k_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=True, keys=False, tabbed=True):
            return serialize_ip_h_nk_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=True, keys=False, tabbed=False):
            return serialize_ip_h_nk_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=True, tabbed=True):
            return serialize_ip_nh_k_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=True, tabbed=False):
            return serialize_ip_nh_k_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=False, tabbed=True):
            return serialize_ip_nh_nk_t(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

        case IpStyle(header=False, keys=False, tabbed=False):
            return serialize_ip_nh_nk_nt(mapper=mapper, leaf_keys=leaf_keys, titles=titles)

    raise TxConversionError(f"Incomplete IP style: {styler!r}")


def serialize_lp_taxonomy(mapper: tMapper, styler: LpStyle, titles: tuple | list | None = None,
                          leaf_key: Hashable | None = None) -> list[list[Any]]:
    """Serialize a taxonomy mapper to an LP-style table."""

    validate_type(mapper, 'mapper', tMapper)
    validate_type(styler, 'styler', LpStyle)

    leaf_keys = list(mapper.keymap)

    titles = validated_list_like(titles)   # (tuple -> list, None -> [], Any other -> exception )
    if styler.header:
        for title in titles:
            if not is_valid_keyid(title, allow_empty=True):
                raise TxConversionError(
                    f"Header contains an unhashable object: {title!r}")

    if leaf_key not in leaf_keys:
        if leaf_key is not None:
            raise TxConversionError(f"Key {leaf_key!r} is absent from the taxonomy")
        else:  # leaf_key is None
            if DEFAULT_LEAF_KEY in mapper.keymap:
                wrn(
                    f"{inspect_location()}: leaf_key is not specified (=None). "
                    f"Using default: {DEFAULT_LEAF_KEY!r}"
                )
                leaf_key = DEFAULT_LEAF_KEY
            else:
                raise TxConversionError(
                    "leaf_key is not specified (=None). The default key "
                    f"{DEFAULT_LEAF_KEY!r} is absent from the taxonomy and cannot be used. "
                    "Pass leaf_key explicitly."
                )
    table: list[list[Any]] = []
    if styler.header:
        titles = list(resized_list(titles, mapper.max_width + 1))
        table.append(titles)

    leaf_index = mapper.keymap[leaf_key]
    for ids, leaves in mapper.idmap.items():
        _ids = list(ids)
        if styler.ids:
            _row = [_ids[-1]]
            _ins = 1
        else:
            _row = []
            _ins = 0


        while _ids:

            _ids_tuple = tuple(_ids)

            if styler.sparse and _ids_tuple != ids:
                _leaf = None
            else:
                _leaf_list = mapper.idmap[_ids_tuple]
                _leaf = _leaf_list[leaf_index]

            _row.insert(_ins, _leaf)

            _ids.pop()

        table.append(_row)

    #print('\nserial:')
    #pp(table, width=180)
    return table


def serialize_taxonomy(taxonomy: Taxonomy, *, styler: tStyler,
                       leaf_key: Hashable | None = None,
                       headers: list | None = None,
                       key_order: list[Hashable] | None = None,
                       sort_cvt: Callable | str | None = 'auto',
                       missed_leaf: Callable | None | str = 'auto',
                       max_chunk_len: int | None = None) -> list[list[Any]]:
    if isinstance(styler, IpStyle):
        if max_chunk_len is None:
            mapper = create_mapper(
                taxonomy,
                key_order=key_order,
                sort_cvt=sort_cvt,
                missed_leaf=missed_leaf,
            )
        else:
            mapper = _create_mapper_from_branches(
                split_to_unique_ip_chunks(taxonomy, max_chunk_len=max_chunk_len),
                key_order=key_order,
                sort_cvt=sort_cvt,
                missed_leaf=missed_leaf,
            )
        return serialize_ip_taxonomy(mapper=mapper, styler=styler, titles=headers)
    elif isinstance(styler, LpStyle):
        if max_chunk_len is not None:
            raise TxConversionError("max_chunk_len is supported only for IP styles")
        mapper = create_mapper(
            taxonomy,
            key_order=key_order,
            sort_cvt=sort_cvt,
            missed_leaf=missed_leaf,
        )
        return serialize_lp_taxonomy(mapper=mapper, styler=styler, leaf_key=leaf_key, titles=headers)
    else:
        raise TxConversionError(
            f"Expected an instance of {IpStyle.__name__} or {LpStyle.__name__}. "
            f"Got: {repr_type(styler)}"
        )
