#!/usr/bin/env python
"""Update a Boutiques descriptor JSON using dot/bracket path notation."""

import argparse
import json
import re
from pathlib import Path

DEFAULT_INDENT = 2

PATH_RE = re.compile(r"([\w-]+)(?:\[(\d+)\])?")


def parse_path(path_str: str) -> list[str | int]:
    """Parse "inputs[0].name" into ["inputs", 0, "name"]."""
    parts = []
    for key, idx in PATH_RE.findall(path_str):
        parts.append(key)
        if idx:
            parts.append(int(idx))
    return parts


def set_at_path(obj: dict | list, path_parts: list[str | int], value) -> None:
    """Navigate *path_parts* through *obj* and set *value* at the leaf."""
    for part in path_parts[:-1]:
        if isinstance(part, int):
            obj = obj[part]
        else:
            if part not in obj:
                obj[part] = {}
            obj = obj[part]
    obj[path_parts[-1]] = value


def apply_updates(descriptor: dict, exclude_version: bool, updates: dict) -> dict:
    """Return *descriptor* with values from *updates* applied."""
    for path_str, value in updates.items():
        path_parts = parse_path(path_str)
        set_at_path(descriptor, path_parts, value)
    if exclude_version:
        descriptor.pop("tool-version", None)
    return descriptor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d",
        "--descriptor",
        required=True,
        type=Path,
        help="Path to the Boutiques descriptor JSON file to update",
    )
    parser.add_argument(
        "-u",
        "--updates",
        required=False,
        type=Path,
        help="Path to a JSON file mapping path expressions to their new values",
    )
    parser.add_argument(
        "--exclude-version",
        action="store_true",
        help="Exclude the tool-version field in the Boutiques descriptor even if version information is available.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to write the updated descriptor. Default: update in place",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=DEFAULT_INDENT,
        help="JSON indentation. Default: %(default)s",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    with open(args.descriptor) as f:
        descriptor = json.load(f)
    if args.updates is not None:
        with open(args.updates) as f:
            updates = json.load(f)
    else:
        updates = {}

    descriptor = apply_updates(descriptor, args.exclude_version, updates)

    output_path = args.output or args.descriptor
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{json.dumps(descriptor, indent=args.indent)}\n")


if __name__ == "__main__":
    main()
