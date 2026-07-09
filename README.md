# taxonorm

`taxonorm` loads taxonomy tables from CSV, XLS, and XLSX files, normalizes
them into one in-memory model, and exports them back to supported taxonomy
formats. The public API accepts and returns `Taxonomy`. The branch table
representation `[id1, ..., idN, {leaf_key: value}]` is used at parser,
serializer, import, and export boundaries.

Russian documentation is preserved in [README.ru.md](README.ru.md).
Conceptual terminology and style names are introduced in [CONCEPT.md](CONCEPT.md).
Terminology for future documentation and message translation is tracked in
[docs/GLOSSARY.md](docs/GLOSSARY.md).

## Public API

### Runnable Examples

The examples below use the same small taxonomy from
`Samples/Variants/Shorts`: household appliances, electronics, and enterprise
server solutions. That directory contains the same structure saved in several
formats and styles.

Small runnable examples live in `Examples/`:

- [sample_import.py](Examples/sample_import.py) imports a CSV in
  `IpStyle(header=True, keys=True, tabbed=True)` and inspects the model;
- [sample_pandas_import.py](Examples/sample_pandas_import.py) imports an
  in-memory `pandas.DataFrame` with the same IP style;
- [sample_parse_rows.py](Examples/sample_parse_rows.py) parses rows that are
  already loaded in memory;
- [sample_api_tour.py](Examples/sample_api_tour.py) is a compact tour through
  `from_branches()`, `guess_style()`, `validate_taxonomy()`,
  `serialize_taxonomy()`, equality, ID renumbering, and exception handling;
- [sample_model_ops.py](Examples/sample_model_ops.py) demonstrates lookup,
  `leaf_path()`, leaf updates, node renaming, and subtree moves;
- [sample_iter_paths.py](Examples/sample_iter_paths.py) compares
  `iter_branches()` and `iter_paths()` for bulk path views;
- [sample_chunks.py](Examples/sample_chunks.py) restores and splits unique-ID
  IP chunks;
- [sample_adapters.py](Examples/sample_adapters.py) exports a taxonomy to
  `networkx` and `bigtree`;
- [sample_export.py](Examples/sample_export.py) exports the same taxonomy to
  another style;
- [sample_validate.py](Examples/sample_validate.py) prints a user-facing
  validation report;
- [view_taxonomy.py](Examples/view_taxonomy.py) is a tree viewer utility with
  `text`, `interactive`, and `pyvis` modes.

### Core Model

`Taxonomy` is the canonical in-memory taxonomy representation. It may contain
one root or several independent roots, so it is technically a forest. A node is
identified by its full ID path from a root; the same node ID may therefore be
used in different branches.

Create an empty mutable model with `Taxonomy()`. Use `from_branches()` when
the source branches are already in memory.

```python
from taxonorm import Taxonomy

taxonomy = Taxonomy.from_branches([
    [1, {"en_US": "Household appliances", "uk_UA": "Побутова техніка"}],
    [1, 11, {"en_US": "Climate technology", "uk_UA": "Кліматична техніка"}],
    [1, 11, 21, {"en_US": "Household fans", "uk_UA": "Вентилятори побутові"}],
    [2, {"en_US": "Electronics", "uk_UA": "Електроніка"}],
    [2, 14, {"en_US": "Audio and multimedia", "uk_UA": "Аудіо та мультимедіа"}],
])
```

The `Samples/Variants/Shorts/SHORT_2L_NU.json` variant stores the same
taxonomy with non-unique IDs. For example, ID `1` may appear under different
roots, but paths `(101, 1)` and `(102, 1)` still identify different nodes.

Core invariants:

- a node ID is any non-empty hashable object;
- a leaf key is any non-empty hashable object;
- a leaf value is any object, including `None` and unhashable objects;
- an exact ID path cannot appear twice;
- root and sibling order is stable and follows insertion order.

`None`, empty strings, whitespace-only strings, empty tuples, and other empty
containers are considered empty. Numeric `0` and `False` are valid, but keep in
mind that Python dictionaries treat `0` and `False` as equal keys.

### Creating From a Branch Table

`Taxonomy.from_branches()` accepts an iterable where each branch contains an
ID path and ends with a leaves mapping:

```python
taxonomy = Taxonomy.from_branches([
    [1, {"en_US": "Household appliances", "uk_UA": "Побутова техніка"}],
    [1, 11, {"en_US": "Climate technology", "uk_UA": "Кліматична техніка"}],
])
```

If a child branch is present but an ancestor row is missing, the model creates
the missing ancestor with empty leaves:

```python
taxonomy = Taxonomy.from_branches([
    [1, 12, 22, 31, {"en_US": "Freezers"}],
])

assert taxonomy.get_node((1,)).leaves == {}
```

`to_branches()` converts the model back to branch-table form and returns all
nodes in stable preorder:

```python
rows = taxonomy.to_branches()
# [[1, {}], [1, 12, {}], [1, 12, 22, {}], [1, 12, 22, 31, {"en_US": "Freezers"}]]
```

Lists of branches and leaves dictionaries are copied defensively. Leaf values
are copied shallowly: nested mutable objects keep their original identity.

### Reading Files

`import_taxonomy()` reads CSV, XLS, or XLSX files and always returns
`Taxonomy`:

```python
from taxonorm import IpStyle, import_taxonomy

taxonomy = import_taxonomy(
    "Samples/Variants/Shorts/U_IP_H_K_T.csv",
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=["en_US", "uk_UA"],
)
```

If `styler` is omitted, taxonorm tries to guess the style:

```python
taxonomy = import_taxonomy(
    "Samples/Variants/Shorts/U_IP_H_K_T.xlsx",
    leaf_keys=["en_US", "uk_UA"],
)
```

Style guessing is heuristic. For ambiguous or external data, prefer passing
`IpStyle` or `LpStyle` explicitly.

```python
from taxonorm import IpStyle

style = IpStyle(
    header=True,  # the first row is a header
    keys=True,    # leaf keys are present in the file
    tabbed=True,  # IDs and leaves are aligned by columns
)
```

`LpStyle` uses `header`, `ids`, and `sparse`. `IpStyle` uses `header`, `keys`,
and `tabbed`. The supported style combinations are described throughout this
document and exercised by the sample files.

Use `cvt_dict` to convert values while reading. For example, restore numeric
IDs from CSV strings:

```python
def as_int_when_possible(value):
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return value

taxonomy = import_taxonomy(
    "Samples/Variants/Shorts/U_IP_H_K_T.csv",
    leaf_keys=["en_US", "uk_UA"],
    cvt_dict={"*": as_int_when_possible},
)
```

See [Examples/sample_import.py](Examples/sample_import.py) for a full runnable
version.

`import_taxonomy()` also accepts an in-memory `pandas.DataFrame`. Pandas is an
optional dependency and is not imported by taxonorm unless you pass a DataFrame.
When `styler.header=True`, DataFrame columns are treated as the header row:

```python
import pandas as pd

from taxonorm import IpStyle, import_taxonomy

dataframe = pd.read_csv("Samples/Variants/Shorts/U_IP_H_K_T.csv", dtype=object)
taxonomy = import_taxonomy(
    dataframe,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=["en_US", "uk_UA"],
)
```

When `styler.header=False`, DataFrame columns are ignored. If `styler` is not
specified, non-default DataFrame columns are included for style guessing, while
default columns such as `0, 1, 2` are ignored. Install pandas support with:

```shell
pip install "taxonorm[pandas]"
```

See [Examples/sample_pandas_import.py](Examples/sample_pandas_import.py) for a
full runnable version.

### Low-Level Parsing and Style Guessing

If a table is already loaded by other code, `parse_taxonomy()` converts it to
`Taxonomy` without file I/O:

```python
from taxonorm import LpStyle, parse_taxonomy

rows = [
    [1, "Household appliances"],
    [11, "Household appliances", "Climate technology"],
    [21, "Household appliances", "Climate technology", "Household fans"],
]
taxonomy = parse_taxonomy(
    rows,
    styler=LpStyle(header=False, ids=True, sparse=False),
    leaf_keys=["en_US"],
)
```

See [Examples/sample_parse_rows.py](Examples/sample_parse_rows.py) for a full
runnable version.

`guess_style(rows, leaf_keys=[...])` returns a likely `IpStyle` or `LpStyle`,
but does not parse anything. Treat the result as a hint, not a proof of input
correctness. See [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### Restoring IP Chunks

Some IP tables store partial paths rather than full paths. The smallest case
is a TP-style table such as `parent_id, node_id, leaf`, but a chunk may contain
more than two IDs. These data can be restored only when each node ID has at
most one parent in the whole taxonomy:

```python
from taxonorm import IpStyle, import_taxonomy

taxonomy = import_taxonomy(
    "Samples/Variants/Chunks/mti_grp_swap.csv",
    styler=IpStyle(header=False, keys=False, tabbed=False),
    leaf_keys=["en_US"],
    restore_ip_chunks=True,
)
```

If the table is already in the exchange form `[id1, ..., idN, {key: value}]`,
use the low-level helpers:

```python
from taxonorm import restore_unique_ip_chunks, split_to_unique_ip_chunks

branches = restore_unique_ip_chunks(chunks)
chunks = split_to_unique_ip_chunks(taxonomy, max_chunk_len=2)
```

See [Examples/sample_chunks.py](Examples/sample_chunks.py).

Ambiguous parents, cycles, or conflicting leaves for the same ID raise
`TxParsingError`. `restore_ip_chunks=False` by default, so normal IP imports
are unchanged. For IP chunks without explicit keys, the last cells are matched
to `leaf_keys` using the usual `IP_NK` rule: their count must match the number
of keys. For TP rows with one leaf value, pass one key. During IP export and
serialization, pass `max_chunk_len=2` or higher to save a taxonomy with unique
IDs as bounded-length IP chunks.

### Input Validation

`validate_input()` checks an external table without parsing and never stops at
the first problem. It returns a `ValidationReport` with all discovered issues,
up to the requested limit:

```python
from taxonorm import IpStyle, validate_input

style = IpStyle(header=True, keys=True, tabbed=True)
report = validate_input(
    rows,
    styler=style,
    leaf_keys=["en_US", "uk_UA"],
)

if not report.valid:
    print(report.format_text())
```

See [Examples/sample_validate.py](Examples/sample_validate.py): it damages a
row shaped like a sample file to show the report format.

The report distinguishes errors and warnings:

```python
report.valid       # False if at least one error exists
report.errors      # tuple[ValidationIssue, ...]
report.warnings    # tuple[ValidationIssue, ...]
report.issues      # all diagnostics in discovery order
report.to_dict()   # structured data for JSON, APIs, or logs
```

Each `ValidationIssue` contains:

| Field | Meaning |
| --- | --- |
| `code` | Machine-readable code, such as `id.invalid` or `lp.sparse.unresolved` |
| `message` | Human-readable explanation |
| `row` | 1-based row number |
| `column` | 1-based column number, when applicable |
| `value` | Problematic input value |
| `expected` | Expected shape or value |
| `severity` | `"error"` or `"warning"` |

When reading a file, row numbers refer to the table after fully empty rows are
removed by the file reader. `ValidationReport.source` stores the source path,
which is useful for batch validation.

`format_text()` creates a user-facing message:

```text
IP_H_K_T; source: damaged-short-sample.csv: errors: 1; warnings: 0.
[id.missing] row 2: The row has no ID path. Expected: at least one non-empty ID.
```

Limit the number of diagnostics with `max_issues`:

```python
report = validate_input(
    rows,
    styler=style,
    leaf_keys=["en_US", "uk_UA"],
    max_issues=25,
    source="short-sample.csv",
)
```

If more issues exist, `report.truncated` is `True`.

Validators check several rule layers:

- general table shape, rows, style settings, and `leaf_keys`;
- ID presence and validity;
- key/value placement in IP;
- leaf value counts in IP without explicit keys;
- dense and sparse LP leaf paths;
- whether missing sparse path values can be restored;
- uniqueness of IDs, ID paths, and terminal LP values with own IDs;
- whether the header matches the declared keyed IP style.

A warning does not forbid parsing. For example, LP uses only the first
`leaf_keys` entry; extra keys are reported as warnings.

### Automatic Validation During Parsing

`parse_taxonomy()` and `import_taxonomy()` validate automatically. If the
report contains errors, taxonorm raises one `TxInputValidationError`:

```python
from taxonorm import TxInputValidationError, import_taxonomy

try:
    taxonomy = import_taxonomy(
        "Samples/Variants/Shorts/U_IP_H_K_T.csv",
        styler=style,
        leaf_keys=["en_US", "uk_UA"],
    )
except TxInputValidationError as error:
    print(error)                 # user-facing text
    send_to_api(error.report.to_dict())
```

The exception stores the original `ValidationReport` in `error.report`.
`context["validation"]` is also included in the standard
`TaxonormError.to_dict()` output. If the internal parser finds a rare problem
missed by pre-validation, users still receive `TxInputValidationError`, and
the original exception is preserved as `__cause__` for logs.
See [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

`max_validation_issues` limits automatic validation report size. Disabling
validation is intended only for debugging internal parsers:

```python
taxonomy = parse_taxonomy(
    rows,
    styler=style,
    leaf_keys=["en_US", "uk_UA"],
    validate=False,
)
```

With `validate=False`, low-level `TxParsingError`, `KeyError`, and other
exceptions may surface. Do not use that mode for user-supplied files.

### Validating an Existing Model

`validate_taxonomy()` audits an already-created model:

```python
from taxonorm import validate_taxonomy

report = validate_taxonomy(taxonomy)
report.raise_for_errors()
```

Normal `Taxonomy` operations already enforce model invariants, so this check
is mostly useful at integration boundaries and in diagnostic tools. Empty
taxonomies are allowed, but produce a `taxonomy.empty` warning.
See [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### Tree Traversal and Selection

`iter_branches()` returns `TaxonomyBranch` objects. Each branch contains a full
`path` and a read-only `leaves` mapping.

```python
for branch in taxonomy.iter_branches():
    print(branch.path, branch.leaves)
```

`leaf_path(path, key)` returns selected leaf values from root to node:

```python
names = taxonomy.leaf_path(
    (1, 12, 22, 31),
    "en_US",
)
# ("Household appliances", "Large household appliances", "Refrigeration equipment", "Freezers")
```

If the requested key is missing on a node, `missed_leaf` controls the value.
The default is `"auto"`:

```python
names = taxonomy.leaf_path((1, 12), "de_DE")
# ("<de_DE:1>", "<de_DE:1.12>")
```

For bulk viewing as ID-path/leaf-path pairs, use `iter_paths(key=None)`. It
yields `(id_path, leaf_path)` pairs and accumulates the leaf path during one
traversal. If no key is passed, taxonorm uses the first key from
`taxonomy.leaf_keys()`.

```python
for branch in taxonomy.iter_branches():
    id_path = branch.path
    leaf_path = taxonomy.leaf_path(branch.path, "en_US")
    print(id_path, leaf_path)

for id_path, leaf_path in taxonomy.iter_paths():
    print(id_path, leaf_path)
```

The first variant is useful when you need the whole `TaxonomyBranch`: current
node leaves, filtering by several fields, editing, or debugging the internal
model. The second variant is better for printing, exporting, and bulk path
views: the leaf path is accumulated once instead of recomputed from root for
each node.

See [Examples/sample_iter_paths.py](Examples/sample_iter_paths.py).

Three stable traversal orders are supported:

```python
taxonomy.iter_branches("preorder")   # node, then descendants; default
taxonomy.iter_branches("postorder")  # descendants, then node
taxonomy.iter_branches("breadth")    # level order from roots
taxonomy.iter_paths("en_US", order="breadth")
```

Unknown order names raise `ValueError`.

Use `find_branches()` for lazy selection:

```python
groups = taxonomy.find_branches(
    lambda branch: branch.leaves.get("en_US", "").endswith("systems"),
    order="breadth",
)

for branch in groups:
    print(branch.path)
```

The method returns a lazy iterator and does not create a separate taxonomy
copy.

### Node Lookup

```python
len(taxonomy)                         # number of nodes
(2, 14, 24, 34) in taxonomy           # full-path membership

node = taxonomy.get_node((2, 14, 24, 34))
print(node.leaves["en_US"])           # Microphones
print(node.children)
```

`get_node()` accepts a full ID path. Missing paths raise `KeyError`. Do not
pass a single scalar instead of a path: use `(1,)`, not `1`.

`leaf_keys()` returns leaf keys in first-seen order:

```python
assert taxonomy.leaf_keys() == ("en_US", "uk_UA")
```

`TaxonomyNode.leaves`, `TaxonomyNode.children`, and `Taxonomy.roots` are
read-only mappings. This prevents bypassing ID and key validation:

```python
node.leaves["en_US"] = "New name"  # TypeError
```

Change the model through `Taxonomy` methods.

`TaxonomyNode` intentionally has no separate `id` field: the ID is stored as
the incoming edge key and is not duplicated in the node. Get a node's ID and
location from `TaxonomyBranch.path` or from the path passed to `get_node()`.

### Updating Leaves

`update_leaves()` merges new leaves into existing leaves by default:

```python
taxonomy.update_leaves(
    (3, 15, 25),
    {"note": "Duplicated label, distinct path"},
)
```

Duplicate keys get new values, while other leaves remain. Use `replace=True`
to replace the whole leaves mapping:

```python
taxonomy.update_leaves(
    (3, 15, 25),
    {"en_US": "Servers", "uk_UA": "Сервери"},
    replace=True,
)
```

Missing paths raise `KeyError`. Invalid leaf keys raise `TxValidationError`,
and the model is not changed.

### Renaming IDs

`rename_node()` changes the last ID in a path while preserving the subtree and
sibling position:

```python
taxonomy.rename_node(
    (3, 15, 25, 35),
    350,
)
```

All descendant paths are updated automatically. If the same parent already has
a child with the new ID, `TxValidationError` is raised and the existing node is
not overwritten.

### ID Renumbering

`renumber_taxonomy_ids()` creates a new `Taxonomy` with the same leaves,
structure, and sibling order, but with freshly assigned numeric IDs:

```python
from taxonorm import renumber_taxonomy_ids

renumbered = renumber_taxonomy_ids(
    taxonomy,
    slack=0.10,
    round_to=10,
    start_from=1,
)
```

Use it when source IDs are absent, inconvenient, non-unique, or follow an old
scheme. New IDs are assigned by tree level using rounded ranges, as when
importing an LP taxonomy without own IDs. The original model is not modified.

Several model operations are shown in
[Examples/sample_model_ops.py](Examples/sample_model_ops.py). Renumbering is
also shown in [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### Adding Nodes

`add_branch()` creates a node and any missing ancestors:

```python
taxonomy.add_branch(
    (2, 14, 24, 39),
    {"en_US": "Studio monitors", "uk_UA": "Студійні монітори"},
)
```

An exact duplicate path raises `TxValidationError`. To fully replace the
leaves mapping of an existing node, pass `replace=True` explicitly:

```python
taxonomy.add_branch(
    (2, 14, 24, 39),
    {"en_US": "Studio monitors", "uk_UA": "Студійні монітори"},
    replace=True,
)
```

Replacing leaves does not remove child nodes.

### Removing Nodes

By default, `remove_branch()` removes only a node without descendants:

```python
taxonomy.remove_branch((2, 14, 24, 34))
```

Trying to remove a node with children raises `TxValidationError`. This protects
against accidental deletion of whole sections. To remove a full subtree,
explicitly pass `recursive=True`:

```python
taxonomy.remove_branch(
    (2, 14, 24),
    recursive=True,
)
```

The method returns the detached `TaxonomyNode`. `len(taxonomy)` decreases by
the size of the removed subtree. Removing the same path again raises
`KeyError`.

### Moving Subtrees

`move_subtree()` moves a node together with all descendants:

```python
taxonomy.move_subtree(
    (3, 15, 26, 37),
    (3, 15, 25),
)
```

You may also rename the root of the moved subtree:

```python
taxonomy.move_subtree(
    (3, 15, 26, 37),
    (3, 15, 25),
    new_id=370,
)
```

To make a node a new root, pass `new_parent=None`.

The operation checks constraints before changing the tree:

- a node cannot be moved inside its own subtree;
- the new parent must not already have a child with the target ID;
- the new parent must exist;
- the new ID must be non-empty and hashable.

The first two rule violations raise `TxValidationError`; missing source or
destination paths raise `KeyError`. If source and destination are the same,
the operation does nothing and returns the existing node.

### Tree Visualization

`taxonorm.viewer` provides three tree viewers. They work directly with
`Taxonomy`, without converting to `networkx` or another intermediate graph:

```python
from taxonorm import (
    view_live_html_tree,
    view_live_text_tree,
    view_text_tree,
)

view_text_tree(taxonomy)                   # static terminal tree
view_text_tree(taxonomy, leaf_key="en_US") # display names instead of IDs

view_live_text_tree(taxonomy, leaf_key="en_US")  # interactive TUI

html_path = view_live_html_tree(
    taxonomy,
    leaf_key="en_US",
    filename="taxonomy.html",
)
```

By default, node labels are IDs. Pass `leaf_key` to label each node with the
selected leaf value. The underlying structure remains the native `Taxonomy`
tree, so equal labels do not collapse distinct nodes.

`render_text_tree()` returns a Rich tree without printing it. `save_text_tree()`
saves a text tree to a file.

### Graph and Tree Library Adapters

`to_networkx()` and `to_bigtree()` export a taxonomy to optional third-party
libraries:

```python
from taxonorm import to_bigtree, to_networkx

graph = to_networkx(taxonomy, label_key="en_US")
tree = to_bigtree(taxonomy, label_key="en_US")
```

Install the optional dependencies when you need these adapters:

```shell
pip install "taxonorm[graph]"
pip install "taxonorm[tree]"
```

`networkx` node keys are full ID paths, for example `(1, 12, 22, 31)`.
Node attributes include `node_id`, `id_path`, `depth`, `leaves`, and `label`.
This preserves repeated local IDs without changing the taxonomy.

`bigtree` requires string node names and a single root, so `to_bigtree()` puts
the taxonomy under a synthetic root named `"Taxonomy"`. Original IDs and paths
are preserved as `node_id` and `id_path`. Leaf dictionaries are stored as
`leaf_values` because `bigtree` already uses `leaves` for its own API.

Both adapters support an explicit renumbering mode:

```python
renumbered_graph = to_networkx(taxonomy, renumber=True)
renumbered_tree = to_bigtree(taxonomy, renumber=True)
```

Renumbering is applied to a copy and does not mutate the source taxonomy. See
[Examples/sample_adapters.py](Examples/sample_adapters.py) for a runnable
example.

### Serialization and Export

`serialize_taxonomy()` converts a model to a table in a selected style without
creating a file:

```python
from taxonorm import IpStyle, serialize_taxonomy

rows = serialize_taxonomy(
    taxonomy,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    headers=["Taxonomy", "1.0"],
    key_order=["en_US", "uk_UA"],
)
```

`export_taxonomy()` serializes and writes CSV, XLS, or XLSX. The file extension
selects the file format:

```python
from taxonorm import LpStyle, export_taxonomy

export_taxonomy(
    taxonomy,
    "short-taxonomy.xlsx",
    styler=LpStyle(header=True, ids=True, sparse=False),
    leaf_key="en_US",
    headers=["id", "category"],
)
```

See [Examples/sample_export.py](Examples/sample_export.py) for an export
example that does not write into the project working directory.
`serialize_taxonomy()` without file output is shown in
[Examples/sample_api_tour.py](Examples/sample_api_tour.py).

For IP styles, `key_order` controls leaf column order. For LP styles,
`leaf_key` selects the single leaf that forms the leaf path. `missed_leaf`
controls missing leaf values: `None`, a callable, or `"auto"`.

In-memory leaf values may be any Python objects, but a concrete file format can
only store types supported by the table driver. Convert complex objects before
exporting them.

### Equality and Order

Two `Taxonomy` objects are equal when their branches, leaves, and stable
traversal order match:

```python
assert Taxonomy.from_branches(taxonomy.to_branches()) == taxonomy
```

Order is part of the observable serialization result. If input data are
semantically equal but inserted in a different order, the models may compare as
different. See [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### Exceptions

Core exceptions are defined in `taxonorm.errors`:

```python
from taxonorm.errors import (
    TaxonormError,
    TxConversionError,
    TxExportError,
    TxImportError,
    TxInputValidationError,
    TxParsingError,
    TxValidationError,
)
```

All specialized exceptions inherit from `TaxonormError` and provide a stable
`code`, a text `message`, optional `context`, and `to_dict()`. To handle all
library errors, catch `TaxonormError`. For user ID, key, and tree-operation
errors, catch `TxValidationError`. For invalid external tables, catch the more
specific `TxInputValidationError`.
See [Examples/sample_api_tour.py](Examples/sample_api_tour.py).

### `Taxonomy` Method Reference

| Method | Purpose | Main errors |
| --- | --- | --- |
| `Taxonomy()` | Create an empty model | - |
| `from_branches(rows)` | Create a model from full ID branches | `TxValidationError` |
| `to_branches()` | Return a shallow-copied branch table | - |
| `get_node(path)` | Get a node by full path | `KeyError` |
| `add_branch(path, leaves, replace=False)` | Add a node and missing ancestors | `TxValidationError` |
| `update_leaves(path, leaves, replace=False)` | Merge or replace leaves | `KeyError`, `TxValidationError` |
| `rename_node(path, new_id)` | Rename an ID while preserving the subtree | `KeyError`, `TxValidationError` |
| `move_subtree(path, new_parent, new_id=None)` | Move and optionally rename a subtree | `KeyError`, `TxValidationError` |
| `remove_branch(path, recursive=False)` | Remove a node or a subtree | `KeyError`, `TxValidationError` |
| `iter_branches(order="preorder")` | Traverse the tree in a selected order | `ValueError` |
| `find_branches(predicate, order="preorder")` | Lazily select branches | `ValueError` |
| `leaf_keys()` | Return leaf keys in first-seen order | - |
| `leaf_path(path, key, missed_leaf="auto")` | Return leaf values from root to node | `KeyError`, `TxValidationError` |
| `iter_paths(key=None, order="preorder", missed_leaf="auto")` | Traverse `(id_path, leaf_path)` pairs | `ValueError`, `TxValidationError` |
| `iter_leaf_paths(key, order="preorder", missed_leaf="auto")` | Compatibility alias for `iter_paths(key, ...)` | `ValueError`, `TxValidationError` |

Related top-level functions: `renumber_taxonomy_ids(taxonomy)` and
`restore_unique_ip_chunks(chunks)`.
