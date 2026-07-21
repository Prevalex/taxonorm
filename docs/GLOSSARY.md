# taxonorm Glossary

This glossary fixes the English terminology used in public documentation,
examples, docstrings, and future user-facing messages.

| Term | Meaning |
| --- | --- |
| taxonomy | The whole tree or forest represented by `Taxonomy`. |
| model | The in-memory object model. |
| node | One item in the taxonomy prefix tree. |
| root | A top-level node. A taxonomy may have several roots. |
| forest | A taxonomy with one or more independent roots. |
| branch | A node view represented as `TaxonomyBranch(path, leaves)`, or an exchange row `[id1, ..., idN, leaves]`. |
| ID path | Tuple of node IDs from root to a node, e.g. `(1, 12, 22)`. |
| full ID path | Same as ID path; emphasize that the complete path identifies the node. |
| leaf path | Tuple of leaf values from root to a node for one leaf key. |
| leaf | A named value stored on a node, not necessarily a terminal node. |
| leaves | Mapping of leaf keys to leaf values. |
| leaf key | A key in the `leaves` mapping, e.g. `"en_US"`. |
| leaf value | A value in the `leaves` mapping. |
| child node | A node under another node. |
| parent | The node immediately above a child node. |
| subtree | A node and all of its descendants. |
| traversal | Iterating over nodes in a defined order. |
| selection | Filtering branches, usually with `find_branches()`. |
| traversal order | `preorder`, `postorder`, or `breadth`. |
| branch table | List of exchange rows `[id1, ..., idN, leaves]`. |
| exchange form | Internal boundary representation used by parsers, serializers, and chunks helpers. |
| IP chunks | Partial unique-ID paths that can be restored to full ID paths. |
| restoring IP chunks | Rebuilding full ID paths with `restore_unique_ip_chunks()`. |
| splitting into IP chunks | Converting full ID paths into bounded-length chunks with `split_to_unique_ip_chunks()`. |
| ID renumbering | Reassigning node IDs while preserving taxonomy structure and leaves. |
| style | Input/output shape described by `IpStyle` or `LpStyle`. |
| style guessing | Heuristic detection via `guess_style()`. |
| header | A first table row with metadata and/or leaf keys. |
| own IDs | IDs provided by the source table. |
| own keys | Leaf keys provided by the source table. |
| sparse | Keep as English in all languages; means sparse leaf paths. |
| dense | Keep as English in all languages; means fully populated leaf paths. |
| keyed | Keep as English when describing IP styles with explicit key/value pairs. |
| tabbed | Keep as English when describing aligned ID and leaf columns. |
| validation | User-facing structural checks before or after parsing. |
| validation report | `ValidationReport`. |
| diagnostic / issue | Prefer `validation issue` when referring to `ValidationIssue`. |
| error | A blocking validation issue or exception. |
| warning | A non-blocking validation issue. |
| exception | Python exception. |
| user-facing message | Text intended for users, not just developers. |
| compatibility alias | API kept to avoid breaking existing users. |

## Naming Preferences

- Use `ID`, not `id`, in prose when speaking about identifiers.
- Use `id_path` in code only where it is an existing variable or API field.
- Use `leaf path` for accumulated values and `ID path` for accumulated node IDs.
- Use `branch` for `TaxonomyBranch` and branch-table rows; use `node` for `TaxonomyNode`.
- Keep style hints such as `IP_H_K_T`, `LP_NH_I_S`, `sparse`, `keyed`, and `tabbed` unchanged.
- Prefer `read/import` for file-to-model operations and `serialize/export` for model-to-table/file operations.
