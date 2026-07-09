# taxonorm Glossary

This glossary fixes the English terminology used in public documentation,
examples, docstrings, and future user-facing messages.

| Russian | English | Notes |
| --- | --- | --- |
| таксономия | taxonomy | The whole tree or forest represented by `Taxonomy`. |
| модель | model | The in-memory object model. |
| узел | node | One item in the taxonomy prefix tree. |
| корень | root | A top-level node. A taxonomy may have several roots. |
| лес | forest | A taxonomy with one or more independent roots. |
| ветвь | branch | A node view represented as `TaxonomyBranch(path, leaves)`, or an exchange row `[id1, ..., idN, leaves]`. |
| путь ID | ID path | Tuple of node IDs from root to a node, e.g. `(1, 12, 22)`. |
| полный путь ID | full ID path | Same as ID path; emphasize that the complete path identifies the node. |
| путь листьев | leaf path | Tuple of leaf values from root to a node for one leaf key. |
| лист | leaf | A named value stored on a node, not necessarily a terminal node. |
| листья | leaves | Mapping of leaf keys to leaf values. |
| ключ листа | leaf key | A key in the `leaves` mapping, e.g. `"en_US"`. |
| значение листа | leaf value | A value in the `leaves` mapping. |
| дочерний узел | child node | A node under another node. |
| родитель | parent | The node immediately above a child node. |
| поддерево | subtree | A node and all of its descendants. |
| обход | traversal | Iterating over nodes in a defined order. |
| выборка | selection | Filtering branches, usually with `find_branches()`. |
| порядок обхода | traversal order | `preorder`, `postorder`, or `breadth`. |
| табличное представление ветвей | branch table | List of exchange rows `[id1, ..., idN, leaves]`. |
| обменный вид | exchange form | Internal boundary representation used by parsers, serializers, and chunks helpers. |
| IP-обрезки | IP chunks | Partial unique-ID paths that can be restored to full ID paths. |
| восстановление IP-обрезков | restoring IP chunks | Rebuilding full ID paths with `restore_unique_ip_chunks()`. |
| дробление IP-обрезков | splitting into IP chunks | Converting full ID paths into bounded-length chunks with `split_to_unique_ip_chunks()`. |
| перенумерация ID | ID renumbering | Reassigning node IDs while preserving taxonomy structure and leaves. |
| стиль | style | Input/output shape described by `IpStyle` or `LpStyle`. |
| определение стиля | style guessing | Heuristic detection via `guess_style()`. |
| заголовок | header | A first table row with metadata and/or leaf keys. |
| собственные ID | own IDs | IDs provided by the source table. |
| собственные ключи | own keys | Leaf keys provided by the source table. |
| sparse | sparse | Keep as English in all languages; means sparse leaf paths. |
| dense | dense | Keep as English in all languages; means fully populated leaf paths. |
| keyed | keyed | Keep as English when describing IP styles with explicit key/value pairs. |
| tabbed | tabbed | Keep as English when describing aligned ID and leaf columns. |
| валидация | validation | User-facing structural checks before or after parsing. |
| отчёт валидации | validation report | `ValidationReport`. |
| диагностика | diagnostic / issue | Prefer `validation issue` when referring to `ValidationIssue`. |
| ошибка | error | A blocking validation issue or exception. |
| предупреждение | warning | A non-blocking validation issue. |
| исключение | exception | Python exception. |
| пользовательское сообщение | user-facing message | Text intended for users, not just developers. |
| совместимый алиас | compatibility alias | API kept to avoid breaking existing users. |

## Naming Preferences

- Use `ID`, not `id`, in prose when speaking about identifiers.
- Use `id_path` in code only where it is an existing variable or API field.
- Use `leaf path` for accumulated values and `ID path` for accumulated node IDs.
- Use `branch` for `TaxonomyBranch` and branch-table rows; use `node` for `TaxonomyNode`.
- Keep style hints such as `IP_H_K_T`, `LP_NH_I_S`, `sparse`, `keyed`, and `tabbed` unchanged.
- Prefer `read/import` for file-to-model operations and `serialize/export` for model-to-table/file operations.
