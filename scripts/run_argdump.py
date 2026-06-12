#!/usr/bin/env python
"""Serialize an argparse.ArgumentParser using argdump."""

import argparse
import importlib
from pathlib import Path

import argdump

DEFAULT_INDENT = 2


def load_parser(module_path: str, parser_func_name: str) -> argparse.ArgumentParser:
    """Load a parser from a file."""
    module = importlib.import_module(module_path)

    try:
        parser = getattr(module, parser_func_name)
    except AttributeError as exception:
        raise AttributeError(
            f"{module_path!r} has no attribute {parser_func_name!r}"
        ) from exception

    return parser


def run_argdump(location: str, output_path: Path, indent=DEFAULT_INDENT):
    """Serialize an `argparse.ArgumentParser` to JSON using argdump."""
    module_path, parser_name = location.split(":")
    parser_to_serialize = load_parser(module_path, parser_name)
    serialized_parser = argdump.dumps(parser_to_serialize, indent=indent)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized_parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "location",
        help='Module path to and name of function that produces the `argparse.ArgumentParser` object. E.g., "my_package.my_module:my_func_name"',
    )
    parser.add_argument(
        "-o",
        "--output",
        "output_path",
        default="argdump.json",
        type=Path,
        help="Path to write the JSON descriptor to. Parent directories are created if needed. Default: %(default)s",
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
    run_argdump(args.location, args.output_path, indent=args.indent)


if __name__ == "__main__":
    main()
