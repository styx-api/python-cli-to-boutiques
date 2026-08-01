import argparse
import json
from pathlib import Path

import click
import pytest
from run_clickdump import build_parser, load_command, run_clickdump


@pytest.fixture
def click_command():
    @click.command()
    @click.option("--name", help="Your name")
    def hello(name):
        """A simple hello command."""

    return hello


@pytest.fixture
def click_group(click_command):
    @click.group()
    def cli():
        """A parent group."""

    cli.add_command(click_command)
    return cli


class TestLoadCommand:
    def test_returns_command(self, click_command, _make_fake_module):
        _make_fake_module("fake_cmd_mod", "hello", click_command)
        result = load_command("fake_cmd_mod", "hello")
        assert result is click_command

    def test_missing_module_raises(self):
        with pytest.raises(ModuleNotFoundError):
            load_command("nonexistent_module_xyz", "func")

    def test_missing_attribute_raises(self, _make_fake_module):
        _make_fake_module("fake_cmd_no_attr", "other_func", lambda: None)
        with pytest.raises(AttributeError, match="has no attribute"):
            load_command("fake_cmd_no_attr", "missing_func")


class TestRunClickdump:
    def test_writes_valid_json(self, click_command, _make_fake_module, tmp_path):
        _make_fake_module("dump_cmd_mod", "hello", click_command)
        out = tmp_path / "out.json"
        run_clickdump("dump_cmd_mod:hello", out)
        data = json.loads(out.read_text())
        assert "actions" in data

    def test_creates_parent_directories(
        self, click_command, _make_fake_module, tmp_path
    ):
        _make_fake_module("dump_cmd_mod2", "hello", click_command)
        out = tmp_path / "nested" / "deep" / "out.json"
        run_clickdump("dump_cmd_mod2:hello", out)
        assert out.exists()

    def test_custom_indent(self, click_command, _make_fake_module, tmp_path):
        _make_fake_module("dump_cmd_mod3", "hello", click_command)
        out = tmp_path / "out.json"
        run_clickdump("dump_cmd_mod3:hello", out, indent=4)
        text = out.read_text()
        assert "    " in text

    def test_with_parent_location(
        self, click_command, click_group, _make_fake_module, tmp_path
    ):
        mod = _make_fake_module("dump_cmd_parent_mod", "hello", click_command)
        mod.cli = click_group
        out = tmp_path / "out.json"
        run_clickdump(
            "dump_cmd_parent_mod:hello",
            out,
            parent_location="dump_cmd_parent_mod:cli",
        )
        data = json.loads(out.read_text())
        assert data["prog"] == "cli hello"

    def test_with_prog_override(self, click_command, _make_fake_module, tmp_path):
        _make_fake_module("dump_cmd_prog_mod", "hello", click_command)
        out = tmp_path / "out.json"
        run_clickdump("dump_cmd_prog_mod:hello", out, prog="custom_name")
        data = json.loads(out.read_text())
        assert data["prog"] == "custom_name"

    def test_include_hidden(self, _make_fake_module, tmp_path):
        @click.command()
        @click.option("--name", help="Your name")
        @click.option("--hidden-opt", help="Hidden option", hidden=True)
        def cmd_with_hidden(name, hidden_opt):
            """A command with hidden option."""

        _make_fake_module("dump_cmd_hidden_mod", "cmd", cmd_with_hidden)

        out_hidden = tmp_path / "with_hidden.json"
        run_clickdump("dump_cmd_hidden_mod:cmd", out_hidden, include_hidden=True)
        data_hidden = json.loads(out_hidden.read_text())
        dests_hidden = [a["dest"] for a in data_hidden["actions"]]
        assert "hidden_opt" in dests_hidden

        out_no_hidden = tmp_path / "without_hidden.json"
        run_clickdump("dump_cmd_hidden_mod:cmd", out_no_hidden, include_hidden=False)
        data_no_hidden = json.loads(out_no_hidden.read_text())
        dests_no_hidden = [a["dest"] for a in data_no_hidden["actions"]]
        assert "hidden_opt" not in dests_no_hidden


class TestBuildParser:
    def test_returns_argument_parser(self):
        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["mymod:myfunc"])
        assert args.output_path == Path("clickdump.json")
        assert args.indent == 2
        assert args.prog is None
        assert args.parent is None
        assert args.include_hidden is False

    def test_custom_args(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "mymod:myfunc",
                "-o",
                "custom.json",
                "--indent",
                "4",
                "--prog",
                "myprog",
                "--parent",
                "mymod:parent",
                "--include-hidden",
            ]
        )
        assert args.output_path == Path("custom.json")
        assert args.indent == 4
        assert args.prog == "myprog"
        assert args.parent == "mymod:parent"
        assert args.include_hidden is True
