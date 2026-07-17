"""Unit tests for run_clickdump.py."""

import json
import sys
import textwrap
from pathlib import Path

import pytest

import run_clickdump


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def sample_module(tmp_path, monkeypatch):
    """Write an importable module exposing a click command."""
    module_name = "sample_click_module"
    (tmp_path / f"{module_name}.py").write_text(
        textwrap.dedent(
            """\
            import click

            @click.command()
            @click.option("-v", "--verbose", count=True)
            @click.option("--name", default="world")
            @click.argument("files", nargs=-1)
            def cli(name, verbose, files):
                pass

            @click.group()
            def parent_group():
                pass
            """
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop(module_name, None)
    yield module_name
    sys.modules.pop(module_name, None)


@pytest.fixture
def fake_dumps(monkeypatch):
    """Replace clickdump.dumps with a recording stub."""
    recorded = {}

    def _dumps(
        cmd,
        *,
        include_env=True,
        include_hidden=True,
        parent=None,
        prog=None,
        **json_kwargs,
    ):
        recorded["cmd"] = cmd
        recorded["include_env"] = include_env
        recorded["include_hidden"] = include_hidden
        recorded["parent"] = parent
        recorded["prog"] = prog
        recorded["json_kwargs"] = json_kwargs
        return '{"serialized": true}'

    monkeypatch.setattr(run_clickdump.clickdump, "dumps", _dumps)
    return recorded


# --------------------------------------------------------------------------- #
# load_command
# --------------------------------------------------------------------------- #
def test_load_command_returns_command(sample_module):
    cmd = run_clickdump.load_command(sample_module, "cli")
    assert cmd is not None


def test_load_command_raises_on_missing_attribute(sample_module):
    with pytest.raises(AttributeError, match="has no attribute"):
        run_clickdump.load_command(sample_module, "does_not_exist")


def test_load_command_raises_on_missing_module():
    with pytest.raises(ModuleNotFoundError):
        run_clickdump.load_command("module_that_does_not_exist_xyz", "anything")


# --------------------------------------------------------------------------- #
# run_clickdump
# --------------------------------------------------------------------------- #
def test_run_clickdump_writes_serialized_content(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    assert out.read_text() == '{"serialized": true}\n'


def test_run_clickdump_appends_trailing_newline(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    assert out.read_text().endswith("\n")


def test_run_clickdump_creates_parent_directories(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "nested" / "deep" / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    assert out.is_file()


def test_run_clickdump_forwards_indent(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out, indent=8)
    assert fake_dumps["json_kwargs"]["indent"] == 8


def test_run_clickdump_default_indent(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    assert fake_dumps["json_kwargs"]["indent"] == run_clickdump.DEFAULT_INDENT


def test_run_clickdump_forwards_prog(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out, prog="my-program")
    assert fake_dumps["prog"] == "my-program"


def test_run_clickdump_default_prog(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    assert fake_dumps["prog"] is None


def test_run_clickdump_forwards_parent(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(
        f"{sample_module}:cli",
        out,
        parent_location=f"{sample_module}:parent_group",
    )
    assert fake_dumps["parent"] is not None


def test_run_clickdump_default_parent(tmp_path, sample_module, fake_dumps):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    assert fake_dumps["parent"] is None


def test_run_clickdump_serializes_the_loaded_command(
    tmp_path, sample_module, fake_dumps
):
    out = tmp_path / "out.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    from click import Command

    assert isinstance(fake_dumps["cmd"], Command)


def test_run_clickdump_location_without_colon_raises(
    tmp_path, sample_module, fake_dumps
):
    with pytest.raises(ValueError):
        run_clickdump.run_clickdump("no_colon_here", tmp_path / "out.json")


def test_run_clickdump_parent_location_without_colon_raises(
    tmp_path, sample_module, fake_dumps
):
    with pytest.raises(ValueError):
        run_clickdump.run_clickdump(
            f"{sample_module}:cli",
            tmp_path / "out.json",
            parent_location="no_colon_here",
        )


# --------------------------------------------------------------------------- #
# build_parser
# --------------------------------------------------------------------------- #
def test_build_parser_defaults():
    args = run_clickdump.build_parser().parse_args(["pkg.mod:func"])
    assert args.location == "pkg.mod:func"
    assert args.output_path == Path("clickdump.json")
    assert args.indent == run_clickdump.DEFAULT_INDENT
    assert args.prog is None
    assert args.parent_location is None


def test_build_parser_custom_options():
    args = run_clickdump.build_parser().parse_args(
        [
            "pkg.mod:func",
            "-o",
            "out.json",
            "--indent",
            "8",
            "--prog",
            "my-prog",
            "--parent-location",
            "pkg.mod:parent",
        ]
    )
    assert args.output_path == Path("out.json")
    assert args.indent == 8
    assert args.prog == "my-prog"
    assert args.parent_location == "pkg.mod:parent"


def test_build_parser_output_is_path_type():
    args = run_clickdump.build_parser().parse_args(
        ["pkg.mod:func", "--output", "x.json"]
    )
    assert isinstance(args.output_path, Path)


def test_build_parser_requires_location():
    with pytest.raises(SystemExit):
        run_clickdump.build_parser().parse_args([])


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def test_main_forwards_parsed_args(monkeypatch):
    recorded = {}

    def fake_run(location, output_path, indent, prog, parent_location):
        recorded.update(
            location=location,
            output_path=output_path,
            indent=indent,
            prog=prog,
            parent_location=parent_location,
        )

    monkeypatch.setattr(run_clickdump, "run_clickdump", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_clickdump.py",
            "pkg.mod:func",
            "-o",
            "x.json",
            "--indent",
            "3",
            "--prog",
            "my-prog",
            "--parent-location",
            "pkg.mod:parent",
        ],
    )
    run_clickdump.main()
    assert recorded == {
        "location": "pkg.mod:func",
        "output_path": Path("x.json"),
        "indent": 3,
        "prog": "my-prog",
        "parent_location": "pkg.mod:parent",
    }


# --------------------------------------------------------------------------- #
# Integration: exercise the real clickdump end to end
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    not any(
        hasattr(p, "__version__") and getattr(p, "__name__", None) == "clickdump"
        for p in map(__import__, ["clickdump"])
    ),
    reason="clickdump not installed",
)
def test_end_to_end_produces_valid_json(tmp_path, sample_module):
    out = tmp_path / "real.json"
    run_clickdump.run_clickdump(f"{sample_module}:cli", out)
    data = json.loads(out.read_text())
    assert isinstance(data, (dict, list))
