# taxonorm Concepts

This document introduces the conceptual model and terminology used by
`taxonorm`.  It is meant to be read before the README when the style names
(`IP`, `LP`, `sparse`, `tabbed`, `chunks`) are still unfamiliar.

The original Russian version is kept as [CONCEPT.ru.md](CONCEPT.ru.md).

## Taxonomy

In `taxonorm`, a taxonomy is a hierarchical structure: a tree, or more
precisely a forest, of nodes.  Each node has an ID and may store any number of
named values.  Those named values are called leaves.

A node may have:

- child nodes;
- leaves;
- both child nodes and leaves;
- neither child nodes nor leaves.

A taxonomy may have one root or several independent roots.  Because several
roots are allowed, the internal model is a prefix forest rather than a single
rooted tree.

## Nodes, IDs, and ID Paths

A node ID is the identifier written on one edge of the hierarchy.  A node is
identified in the model by its full ID path, not necessarily by the last ID
alone.

```python
("catalog", "phones", "accessories")
```

This means the same node ID may appear in different parts of the taxonomy as
long as the full path is different:

```python
("catalog", "phones", "accessories")
("catalog", "tablets", "accessories")
```

The repeated ID `"accessories"` is valid here because the full ID paths are
different.  A full ID path, however, may not be declared twice unless the API
explicitly allows replacement.

Node IDs may be any non-empty hashable Python object.  Strings, integers, and
tuples are valid when they are non-empty and hashable.  `None`, empty strings,
strings containing only whitespace, empty tuples, empty containers, and
unhashable objects are not valid node IDs.

## Leaves and Leaf Keys

Leaves are values attached to a node.  They are stored as a mapping:

```python
leaves = {
    "en_US": "Household fans",
    "uk_UA": "Вентилятори побутові",
}
```

The mapping key is called a leaf key.  The mapping value is called a leaf
value.

Leaf keys follow the same requirements as node IDs: a leaf key must be a
non-empty hashable object.  Leaf values are deliberately unrestricted: a leaf
value may be any Python object, including `None`.

Common leaf keys are locale names such as `"en_US"` or `"uk_UA"`, but this is a
convention, not a requirement.

## Internal Model

The canonical in-memory representation is `Taxonomy`.  A `Taxonomy` contains
`TaxonomyNode` objects arranged as a prefix forest.

`TaxonomyNode` stores:

- the node's leaves;
- the node's children.

The node ID itself is not duplicated inside `TaxonomyNode`.  It is stored as
the key by which the node is reached from `Taxonomy.roots` or from its
parent's `children` mapping.  This mirrors the prefix-tree structure and avoids
duplicating IDs.

## Branch Exchange Form

Parsers and serializers use a flat exchange form made of branches.  A branch is
an ID path followed by the leaves of the last node:

```python
branches = [
    [1, {"en_US": "Household appliances"}],
    [1, 11, {"en_US": "Climate technology"}],
    [1, 11, 21, {"en_US": "Household fans"}],
]
```

This is not the internal data structure.  It is a boundary representation used
between table parsers, serializers, IP chunk helpers, and `Taxonomy`.

`Taxonomy.from_branches()` builds the prefix forest from this exchange form.
`Taxonomy.to_branches()` returns the exchange form in stable preorder.

If a table declares a child branch but does not declare an ancestor branch, the
model creates the missing ancestor with empty leaves.

## Style vs File Format

`taxonorm` distinguishes style from file format.

A style describes how taxonomy data is encoded inside a table.  Examples:
`IP_H_K_T`, `LP_NH_I_S`.

A file format describes the container used to store that table.  Examples:
CSV, XLS, XLSX, JSON.

The same taxonomy style can be stored in different file formats:

```text
IP_H_K_T.csv
IP_H_K_T.xlsx
LP_NH_I_NS.csv
```

The word style is preferred for taxonomy layout so it is not confused with the
physical file format.

## IP and LP

`taxonorm` currently has two main table-style families:

| Family | Meaning | Path is written as | Leaf values are written as |
| --- | --- | --- | --- |
| `IP` | ID Path | node IDs from root to node | values at the end of the row |
| `LP` | Leaf Path | leaf values from root to node | usually one selected leaf key |

### IP: ID Path

In an IP table, each row starts with the ID path to a node:

```csv
1,Household appliances
1,11,Climate technology
1,11,21,Household fans
```

The internal branch form is the same idea, but the row ends with a leaves
mapping:

```python
[1, 11, 21, {"en_US": "Household fans"}]
```

IP is the natural style when:

- node IDs are the primary way to address nodes;
- one node may have several leaf values;
- leaf keys are stored in the table or supplied by the caller.

### LP: Leaf Path

In an LP table, each row describes the path by leaf values.  When IDs are
present, the first cell is the ID of the final node:

```csv
1,Household appliances
11,Household appliances,Climate technology
21,Household appliances,Climate technology,Household fans
```

This is common in taxonomies such as Google Product Categories, where every
row gives the human-readable category path.

LP is convenient when:

- one leaf key is enough to describe the path;
- the table is mainly edited by humans;
- the source already stores full category names along every row.

Because LP stores a path through leaf values, it normally uses one selected
leaf key.  If a taxonomy must carry several leaf keys in one file, IP is the
more general representation.

## Style Flags

The style dataclasses are `IpStyle` and `LpStyle`.  File names and examples use
compact mnemonic flags.

| Flag | Meaning | Applies to |
| --- | --- | --- |
| `H` / `NH` | header / no header | IP, LP |
| `K` / `NK` | leaf keys are stored / not stored | IP |
| `I` / `NI` | node IDs are stored / generated from leaf paths | LP |
| `T` / `NT` | tabbed / not tabbed | IP |
| `S` / `NS` | sparse / dense | LP |

Examples:

| Style | Meaning |
| --- | --- |
| `IP_H_K_T` | IP table with a header, leaf keys in the header, tabbed ID columns |
| `IP_NH_K_NT` | IP table without header, key/value pairs in each row, not tabbed |
| `IP_NH_NK_NT` | IP table without header or stored keys; leaf key order is supplied by the caller |
| `LP_H_I_NS` | LP table with header, own IDs, dense leaf paths |
| `LP_NH_NI_S` | LP table without header or own IDs, sparse leaf paths |

## Header

A header is a first table row that is not a taxonomy branch.

In most styles, `header=True` simply means "skip the first row when parsing."

There is one important IP exception: in `IP_H_K_T`, leaf keys are stored in the
header.  The parser uses the first header cell matching one of the supplied
leaf keys to find where the leaf-value columns begin.

```csv
,,,,en_US,uk_UA
101,,,,HOUSE APPLIANCES AND GOODS,ПОБУТОВА ТЕХНІКА ТА ТОВАРИ
101,1,,,Air conditioning equipment,Кліматична техніка
```

## Leaf Keys in IP Tables

IP tables can store or omit leaf keys.

### Keyed IP Rows

When `keys=True` and the keys are not stored in the header, every row contains
key/value pairs after the ID path:

```csv
101,en_US,HOUSE APPLIANCES AND GOODS,uk_UA,ПОБУТОВА ТЕХНІКА ТА ТОВАРИ
101,1,en_US,Air conditioning equipment,uk_UA,Кліматична техніка
```

The caller still passes the expected leaf keys to the parser.  This lets the
parser distinguish leaf keys from ordinary leaf values.

### IP Rows Without Stored Keys

When `keys=False`, the last N cells are interpreted as leaf values, where N is
the number of leaf keys supplied by the caller:

```csv
101,HOUSE APPLIANCES AND GOODS,ПОБУТОВА ТЕХНІКА ТА ТОВАРИ
101,1,Air conditioning equipment,Кліматична техніка
```

Here the caller might pass:

```python
leaf_keys = ["en_US", "uk_UA"]
```

The order of `leaf_keys` is significant.

## Tabbed IP

A tabbed IP table aligns ID columns and leaf-value columns for spreadsheet
editing.  Empty cells are used only as alignment placeholders:

```csv
101,,,,HOUSE APPLIANCES AND GOODS,ПОБУТОВА ТЕХНІКА ТА ТОВАРИ
101,1,,,Air conditioning equipment,Кліматична техніка
101,1,1,,Household fans,Вентилятори побутові
101,1,1,1,Exhaust fans,Вентилятори витяжні
```

The empty cells do not mean missing node IDs.  They are part of the tabular
layout.

In tabbed IP tables, any number of empty columns may appear between the ID path
area and the leaf-value area.

## Sparse and Dense LP

LP leaf paths often repeat the same prefix in many adjacent rows:

```csv
1,Household appliances
11,Household appliances,Climate technology
21,Household appliances,Climate technology,Household fans
```

A sparse LP table stores repeated prefix values only once and leaves the later
cells empty:

```csv
1,Household appliances
11,,Climate technology
21,,,Household fans
```

The dense form can be reconstructed only when rows are in an order that makes
the inherited values unambiguous.  Therefore sparse LP tables are intended to
be sorted.

Non-sparse LP tables may also be called dense tables.

Sparse currently applies to LP styles.  IP sparse notation is not a separate
style in the current public API.

## Unique and Reused IDs

Some taxonomies use globally unique node IDs.  If an ID is globally unique,
the ID alone is enough to know which node is meant.

Other taxonomies reuse local IDs in different parts of the tree:

```csv
101,HOUSE APPLIANCES AND GOODS
101,1,Air conditioning equipment
101,1,1,Household fans
101,1,1,1,Exhaust fans
101,1,1,2,Floor fans
```

This is valid in `taxonorm` because the full ID path identifies the node:

```python
(101, 1, 1, 1)
(101, 1, 1, 2)
```

Many file-system-like structures behave this way: the same local name may
appear in different directories.

## IP Chunks

Earlier design notes treated triples such as `node_id, parent_id, leaf_value`
as a separate TP style.  In the current API, this idea is handled as IP chunks,
not as a separate style family.

An IP chunk is a partial ID path.  For example, instead of storing every full
path:

```python
[0, 1, 101, 777, {"en_US": "Notebook cables"}]
```

a source may store smaller pieces:

```python
[0, 1, {"en_US": "Notebooks"}]
[1, 101, {"en_US": "Notebook parts"}]
[101, 777, {"en_US": "Notebook cables"}]
```

These chunks can be restored to full IP paths only when node IDs are unique
enough to make every parent relationship unambiguous.  Restoration is invalid
when:

- one ID has more than one parent;
- chunks form a cycle;
- the same terminal ID is described with conflicting leaves.

The relevant helpers are:

```python
restore_unique_ip_chunks(chunks)
split_to_unique_ip_chunks(taxonomy, max_chunk_len=2)
```

`parse_taxonomy(..., restore_ip_chunks=True)` can restore chunks during IP
parsing.

## Model Invariants

The public model follows these rules:

- a node is identified by its full ID path;
- a full ID path is unique inside one `Taxonomy`;
- a node ID may be reused under different parents;
- a node ID must be non-empty and hashable;
- a leaf key must be non-empty and hashable;
- a leaf value may be any object, including `None`;
- roots and siblings preserve insertion order;
- traversal order is explicit (`preorder`, `postorder`, or `breadth`);
- IDs do not need to be mutually comparable or sortable.

Python dictionary equality means some values are considered the same key even
if their types differ.  For example, `0` and `False` compare equal as dictionary
keys.  This is normal Python behavior and applies to node IDs and leaf keys.

## Import, Parse, Serialize, Export

`taxonorm` separates model operations from table and file operations:

| Operation | Direction | Result |
| --- | --- | --- |
| parse | branch table -> `Taxonomy` | in-memory model |
| import | file -> `Taxonomy` | in-memory model |
| serialize | `Taxonomy` -> branch table | table data |
| export | `Taxonomy` -> file | written file |

The README contains practical API examples for these operations.  This
document explains the terms used by those examples.
