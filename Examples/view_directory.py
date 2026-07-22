#!python
"""Display a directory as a Taxonomy rendered with Rich.

This follows the idea of Rich's ``examples/tree.py``, but deliberately builds
the filesystem hierarchy as a normal taxonorm model before rendering it.
Directory entry names are node IDs; filesystem facts are stored as leaves.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from rich import print
from rich.filesize import decimal
from rich.markup import escape

from taxonorm import Taxonomy, TaxonomyNode, to_rich_tree


def directory_to_taxonomy(
    directory: str | Path,
    *,
    include_hidden: bool = False,
    max_depth: int | None = None,
) -> Taxonomy:
    """Build a taxonomy whose ID paths mirror relative filesystem paths."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    if max_depth is not None and max_depth < 0:
        raise ValueError("max_depth must be zero or greater")

    root_id = root.name or root.anchor or str(root)
    taxonomy = Taxonomy.from_branches(
        [[root_id, {"kind": "directory", "path": root}]]
    )
    pending: list[tuple[Path, tuple[str, ...], int]] = [
        (root, (root_id,), 0)
    ]

    while pending:
        parent, parent_ids, depth = pending.pop()
        if max_depth is not None and depth >= max_depth:
            continue
        try:
            entries = sorted(
                parent.iterdir(),
                key=lambda path: (not path.is_dir(), path.name.casefold()),
            )
        except OSError as exc:
            taxonomy.update_leaves(
                parent_ids,
                {"scan_error": f"{type(exc).__name__}: {exc}"},
            )
            continue

        child_directories: list[tuple[Path, tuple[str, ...], int]] = []
        for entry in entries:
            if not include_hidden and entry.name.startswith("."):
                continue
            child_ids = parent_ids + (entry.name,)
            leaves: dict[str, Any] = {"path": entry}
            try:
                if entry.is_symlink():
                    leaves.update(kind="symlink", target=os.readlink(entry))
                elif entry.is_dir():
                    leaves["kind"] = "directory"
                    child_directories.append((entry, child_ids, depth + 1))
                else:
                    leaves.update(
                        kind="file",
                        size=entry.stat().st_size,
                        suffix=entry.suffix,
                    )
            except OSError as exc:
                leaves.update(
                    kind="unavailable",
                    scan_error=f"{type(exc).__name__}: {exc}",
                )
            taxonomy.add_branch(child_ids, leaves)

        pending.extend(reversed(child_directories))

    return taxonomy


def rich_filesystem_label(
    path: tuple[Any, ...], node: TaxonomyNode, label: str
) -> str:
    """Format one filesystem taxonomy node as opt-in Rich markup."""
    entry = node.leaves.get("path")
    uri = entry.as_uri() if isinstance(entry, Path) else ""
    link_open = f"[link={uri}]" if uri else ""
    link_close = "[/link]" if uri else ""
    name = escape(label)
    kind = node.leaves.get("kind")

    if kind == "directory":
        dim = " dim" if str(path[-1]).startswith("__") else ""
        return (
            f"[bold magenta{dim}]:open_file_folder: "
            f"{link_open}{name}{link_close}[/bold magenta{dim}]"
        )
    if kind == "file":
        suffix = str(node.leaves.get("suffix", ""))
        stem = name[: -len(suffix)] if suffix else name
        styled_name = f"[green]{stem}[/green][bold red]{escape(suffix)}[/bold red]"
        size = decimal(int(node.leaves.get("size", 0)))
        return (
            f":page_facing_up: {link_open}{styled_name}{link_close} "
            f"[blue]({size})[/blue]"
        )
    if kind == "symlink":
        target = escape(str(node.leaves.get("target", "?")))
        return f"[cyan]:link: {link_open}{name}{link_close} -> {target}[/cyan]"
    return f"[red]:warning: {name}[/red]"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display a directory through taxonorm and rich.tree.Tree."
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "--hidden", action="store_true", help="Include dot-prefixed entries."
    )
    parser.add_argument(
        "--max-depth", type=int, default=None, help="Limit scanned depth."
    )
    args = parser.parse_args()

    taxonomy = directory_to_taxonomy(
        args.directory,
        include_hidden=args.hidden,
        max_depth=args.max_depth,
    )
    tree = to_rich_tree(
        taxonomy,
        formatter=rich_filesystem_label,
        markup=True,
    )
    tree.hide_root = True
    print(tree)


if __name__ == "__main__":
    main()
