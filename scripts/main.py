#!/usr/bin/env python3
"""Dump an argparse parser to a JSON descriptor via argdump.

You tell it three things:
  - where the parser lives  (a dotted module path or a .py file)
  - the name of the thing that gives you the parser (a builder function,
    or the parser object itself)
  - where to write the resulting JSON

Examples
--------
Dotted module path (works when the package is importable / installed):

    python main.py mriqc.cli.parser _build_parser --output mriqc.json

A standalone .py file, adding its directory to the import path so its
sibling imports resolve:

    python main.py ./some/parser.py -f build_parser -o out/dump.json --sys-path ./some
"""
import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path

import argdump


def load_attr(location: str, attr_name: str):
    """Import `location` and return the attribute named `attr_name`.

    `location` may be either a dotted module path (e.g. ``mriqc.cli.parser``)
    or a path to a ``.py`` file. Dotted paths are preferred for code that
    lives inside a package, because file loading does not establish package
    context (so internal absolute/relative imports may fail).
    """
    path = Path(location)
    if path.suffix == ".py" or path.is_file():
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load a module from file: {location!r}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(location)

    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        raise AttributeError(
            f"{location!r} has no attribute {attr_name!r}"
        ) from exc


def build_parser_json(location: str, parser_name: str) -> dict:
    """Resolve the parser, run argdump, and return it as a Python dict."""
    obj = load_attr(location, parser_name)
    parser = obj() if callable(obj) else obj  # builder function or parser object

    result = argdump.dumps(parser)
    # argdump.dumps returns a JSON string; tolerate it already being a dict.
    return json.loads(result) if isinstance(result, str) else result


def main(argv=None) -> int:
    cli = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cli.add_argument(
        "location",
        help="Where the parser lives: a dotted module path "
        "(e.g. mriqc.cli.parser) or a path to a .py file.",
    )
    cli.add_argument(
        "parser",
        help="Name of the parser-builder function (called with no args) "
        "or of the parser object itself.",
    )
    cli.add_argument(
        "-o",
        "--output",
        default="argdump.json",
        help="Path to write the JSON descriptor to. Parent directories are "
        "created if needed. Default: %(default)s",
    )
    cli.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation. Use a negative value for compact output. "
        "Default: %(default)s",
    )
    cli.add_argument(
        "--sys-path",
        action="append",
        default=[],
        metavar="DIR",
        help="Directory to prepend to sys.path before importing. Repeatable. "
        "Useful when loading a standalone file that imports sibling modules.",
    )
    args = cli.parse_args(argv)

    for entry in reversed(args.sys_path):
        sys.path.insert(0, str(Path(entry).resolve()))

    try:
        data = build_parser_json(args.location, args.parser)
    except (ImportError, AttributeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out = Path(args.output)
    if out.parent != Path(""):
        out.parent.mkdir(parents=True, exist_ok=True)

    indent = args.indent if args.indent >= 0 else None
    with out.open("w") as f:
        json.dump(data, f, indent=indent)

    n = len(data) if hasattr(data, "__len__") else "?"
    print(f"Wrote {out}  ({n} top-level keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
