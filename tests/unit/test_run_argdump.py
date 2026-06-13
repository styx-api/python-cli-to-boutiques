"""Unit tests for run_argdump.py."""

import argparse
import json
import sys
import textwrap
from pathlib import Path

import pytest

import run_argdump


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_module(tmp_path, monkeypatch):
    """Write an importable module exposing parser-builder helpers.

    Yields the module name; the module is removed from ``sys.modules`` on
    teardown so each test gets a clean import.
    """
    module_name = "sample_parser_module"
    (tmp_path / f"{module_name}.py").write_text(
        textwrap.dedent(
            '''
            import argparse

            def good_parser():
                parser = argparse.ArgumentParser(prog="sample")
                parser.add_argument("foo")
                parser.add_argument("--bar", type=int, default=3)
                return parser

            def not_a_parser():
                return "definitely not a parser"

            NOT_CALLABLE = 42
            '''
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(module_name, None)
    yield module_name
    sys.modules.pop(module_name, None)


@pytest.fixture
def fake_dumps(monkeypatch):
    """Replace argdump.dumps with a recording stub.

    Lets the run_argdump tests assert on behavior without depending on
    argdump's actual serialization format. Returns the dict of recorded
    call arguments.
    """
    recorded = {}

    def _dumps(parser, indent=run_argdump.DEFAULT_INDENT):
        recorded["parser"] = parser
        recorded["indent"] = indent
        return '{"serialized": true}'

    monkeypatch.setattr(run_argdump.argdump, "dumps", _dumps)
    return recorded


# --------------------------------------------------------------------------- #
# load_parser
# --------------------------------------------------------------------------- #
def test_load_parser_returns_argument_parser(sample_module):
    parser = run_argdump.load_parser(sample_module, "good_parser")
    assert isinstance(parser, argparse.ArgumentParser)


def test_load_parser_raises_on_missing_attribute(sample_module):
    with pytest.raises(AttributeError, match="has no attribute"):
        run_argdump.load_parser(sample_module, "does_not_exist")


def test_load_parser_raises_on_wrong_return_type(sample_module):
    with pytest.raises(TypeError, match="did not return"):
        run_argdump.load_parser(sample_module, "not_a_parser")


def test_load_parser_raises_when_attribute_not_callable(sample_module):
    # getattr succeeds but calling an int raises TypeError.
    with pytest.raises(TypeError):
        run_argdump.load_parser(sample_module, "NOT_CALLABLE")


def test_load_parser_raises_on_missing_module():
    with pytest.raises(ModuleNotFoundError):
        run_argdump.load_parser("module_that_does_not_exist_xyz", "anything")


# --------------------------------------------------------------------------- #
# run_argdump
# --------------------------------------------------------------------------- #
def test_run_argdump_writes_serialized_content(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_argdump.run_argdump(f"{sample_module}:good_parser", out)
    assert out.read_text() == '{"serialized": true}\n'


def test_run_argdump_appends_trailing_newline(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_argdump.run_argdump(f"{sample_module}:good_parser", out)
    assert out.read_text().endswith("\n")


def test_run_argdump_creates_parent_directories(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "nested" / "deep" / "out.json"
    run_argdump.run_argdump(f"{sample_module}:good_parser", out)
    assert out.is_file()


def test_run_argdump_forwards_indent(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_argdump.run_argdump(f"{sample_module}:good_parser", out, indent=8)
    assert fake_dumps["indent"] == 8


def test_run_argdump_default_indent(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_argdump.run_argdump(f"{sample_module}:good_parser", out)
    assert fake_dumps["indent"] == run_argdump.DEFAULT_INDENT


def test_run_argdump_serializes_the_loaded_parser(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_argdump.run_argdump(f"{sample_module}:good_parser", out)
    assert isinstance(fake_dumps["parser"], argparse.ArgumentParser)


def test_run_argdump_location_without_colon_raises(tmp_path, sample_module, fake_dumps):
    # "no_colon".split(":") -> single element -> unpacking fails.
    with pytest.raises(ValueError):
        run_argdump.run_argdump("no_colon_here", tmp_path / "out.json")


def test_run_argdump_location_with_extra_colon_raises(tmp_path, sample_module, fake_dumps):
    with pytest.raises(ValueError):
        run_argdump.run_argdump("a:b:c", tmp_path / "out.json")


# --------------------------------------------------------------------------- #
# build_parser
# --------------------------------------------------------------------------- #
def test_build_parser_defaults():
    args = run_argdump.build_parser().parse_args(["pkg.mod:func"])
    assert args.location == "pkg.mod:func"
    assert args.output_path == Path("argdump.json")
    assert args.indent == run_argdump.DEFAULT_INDENT


def test_build_parser_custom_options():
    args = run_argdump.build_parser().parse_args(
        ["pkg.mod:func", "-o", "out.json", "--indent", "8"]
    )
    assert args.output_path == Path("out.json")
    assert args.indent == 8


def test_build_parser_output_is_path_type():
    args = run_argdump.build_parser().parse_args(["pkg.mod:func", "--output", "x.json"])
    assert isinstance(args.output_path, Path)


def test_build_parser_requires_location():
    with pytest.raises(SystemExit):
        run_argdump.build_parser().parse_args([])


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def test_main_forwards_parsed_args(monkeypatch):
    recorded = {}

    def fake_run(location, output_path, indent):
        recorded.update(location=location, output_path=output_path, indent=indent)

    monkeypatch.setattr(run_argdump, "run_argdump", fake_run)
    monkeypatch.setattr(
        sys, "argv",
        ["run_argdump.py", "pkg.mod:func", "-o", "x.json", "--indent", "3"],
    )
    run_argdump.main()
    assert recorded == {
        "location": "pkg.mod:func",
        "output_path": Path("x.json"),
        "indent": 3,
    }


# --------------------------------------------------------------------------- #
# Integration: exercise the real argdump end to end
# --------------------------------------------------------------------------- #
def test_end_to_end_produces_valid_json(tmp_path, sample_module):
    out = tmp_path / "real.json"
    run_argdump.run_argdump(f"{sample_module}:good_parser", out)
    data = json.loads(out.read_text())  # raises if not valid JSON
    assert isinstance(data, (dict, list))
