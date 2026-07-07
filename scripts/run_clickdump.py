#!/usr/bin/env python
"""Serialize a click.Command or click.Group using clickdump."""

import argparse
import importlib
from pathlib import Path
from typing import Optional

import clickdump

DEFAULT_INDENT = 2


def load_command(module_path: str, attr_name: str):
    """Load a click command from a module."""
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr_name)
    except AttributeError as exception:
        raise AttributeError(
            f"{module_path!r} has no attribute {attr_name!r}"
        ) from exception


def run_clickdump(
    location: str,
    output_path: Path,
    indent: int = DEFAULT_INDENT,
    prog: Optional[str] = None,
    parent_location: Optional[str] = None,
    include_hidden: bool = False,
):
    """Serialize a click.Command/Group to JSON using clickdump."""
    module_path, command_name = location.split(":")
    command = load_command(module_path, command_name)

    parent = None
    if parent_location:
        parent_module_path, parent_name = parent_location.split(":")
        parent = load_command(parent_module_path, parent_name)

    serialized = clickdump.dumps(
        command, parent=parent, prog=prog, indent=indent, include_hidden=include_hidden
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{serialized}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "location",
        help='Module path to and name of the click command. E.g., "my_package.my_module:cli"',
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        default="clickdump.json",
        type=Path,
        help="Path to write the JSON descriptor to. Default: %(default)s",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=DEFAULT_INDENT,
        help="JSON indentation. Default: %(default)s",
    )
    parser.add_argument(
        "--prog",
        default=None,
        help="Override the root program name in the computed program path.",
    )
    parser.add_argument(
        "--parent",
        default=None,
        help='Module path and attribute of the parent click.Group. E.g., "my_package.my_module:parent_group"',
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden options in the dumped descriptor.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    run_clickdump(
        args.location,
        args.output_path,
        indent=args.indent,
        prog=args.prog,
        parent_location=args.parent,
        include_hidden=args.include_hidden,
    )


if __name__ == "__main__":
    main()
