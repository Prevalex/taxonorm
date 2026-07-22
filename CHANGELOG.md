# Changelog

## 0.1.0 - 2026-07-22

Initial public-package preparation snapshot.

- Added the canonical `Taxonomy` prefix-forest model.
- Added import, parsing, validation, serialization, and export for supported
  IP and LP taxonomy table styles.
- Added IP chunk restore/split helpers.
- Added text, interactive text, and HTML tree viewers.
- Added optional `to_networkx()` export and bidirectional `to_bigtree()` /
  `from_bigtree()` adapters, including lossless in-memory round trips for
  forests, mixed hashable IDs, and arbitrary leaf mappings.
- Added `to_rich_tree()` with literal-safe labels and kept
  `render_text_tree()` as a compatibility name.
- Added a filesystem-to-`Taxonomy` Rich tree example inspired by Rich's own
  directory tree demonstration.
- Added optional `pandas.DataFrame` inputs.
- Removed private `alib`/`alx` runtime dependencies from package code.
- Switched public documentation, docstrings, comments, and user-facing default
  messages to English.
- Declared the project under the MIT License.
