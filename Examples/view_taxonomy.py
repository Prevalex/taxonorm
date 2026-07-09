#!python
"""Small CLI utility for viewing keyed tabbed IP taxonomies."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from taxonorm import (  # noqa: E402
    IpStyle,
    import_taxonomy,
    view_live_html_tree,
    view_live_text_tree,
    view_text_tree,
)

DEFAULT_LEAF_KEY = "en_US"
COMMON_LEAF_KEYS = ("en_US", "uk_UA", "ru_RU")
STYLE = IpStyle(header=True, keys=True, tabbed=True)


def _convert_cell(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def _csv_header_keys(source: Path) -> list[str]:
    if source.suffix.lower() != ".csv":
        return []
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        try:
            header = next(csv.reader(stream))
        except StopIteration:
            return []
    return [key for key in COMMON_LEAF_KEYS if key in header]


def _leaf_keys(source: Path, selected_key: str, configured_keys: str | None) -> list[str]:
    if configured_keys is None:
        keys = _csv_header_keys(source) or [selected_key]
    else:
        keys = [key.strip() for key in configured_keys.split(",") if key.strip()]

    if selected_key and selected_key not in keys:
        keys.append(selected_key)
    return keys


def _default_html_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}.viewer.html")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "View a taxonomy file in IP_H_K_T style "
            "(IpStyle(header=True, keys=True, tabbed=True))."
        )
    )
    parser.add_argument("source", type=Path, help="Path to CSV/XLS/XLSX taxonomy file.")
    parser.add_argument(
        "viewer",
        choices=("text", "interactive", "pyvis"),
        help="Viewer type: static Rich text, Textual TUI, or pyvis HTML.",
    )
    parser.add_argument(
        "leaf_key",
        nargs="?",
        default=DEFAULT_LEAF_KEY,
        help=f"Leaf key to display. Default: {DEFAULT_LEAF_KEY}.",
    )
    parser.add_argument(
        "--ids",
        action="store_true",
        help="Display node IDs instead of leaf values.",
    )
    parser.add_argument(
        "--leaf-keys",
        help=(
            "Comma-separated keys to parse from keyed IP rows. "
            "Default for CSV: known locale keys found in the header; "
            "otherwise the selected leaf key only."
        ),
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="Output HTML path for the pyvis viewer.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Write pyvis HTML without opening the browser.",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Sort siblings by ID label instead of preserving source order.",
    )
    parser.add_argument(
        "--unicode-icons",
        action="store_true",
        help='Use Textual default Unicode expand icons: "▶ " and "▼ ".',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"File not found: {source}")

    display_leaf_key = None if args.ids else args.leaf_key
    taxonomy = import_taxonomy(
        source,
        styler=STYLE,
        leaf_keys=_leaf_keys(source, args.leaf_key, args.leaf_keys),
        cvt_dict={"*": _convert_cell},
    )

    if args.viewer == "text":
        view_text_tree(taxonomy, leaf_key=display_leaf_key, sort=args.sort)
        return 0

    if args.viewer == "interactive":
        icon_kwargs = (
            {"icon_node": "▶ ", "icon_node_expanded": "▼ "}
            if args.unicode_icons
            else {}
        )
        view_live_text_tree(
            taxonomy,
            leaf_key=display_leaf_key,
            sort=args.sort,
            **icon_kwargs,
        )
        return 0

    html_path = args.html or _default_html_path(source)
    output = view_live_html_tree(
        taxonomy,
        leaf_key=display_leaf_key,
        filename=html_path,
        open_browser=not args.no_browser,
        sort=args.sort,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
