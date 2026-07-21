import argparse
import json
from pathlib import Path

import pytest

from run_argdump import build_parser, load_parser, run_argdump


@pytest.fixture
def parser():
    return argparse.ArgumentParser()


class TestLoadParser:
    def test_returns_argument_parser(self, parser, _make_fake_module):
        _make_fake_module("fake_ok", "make_parser", lambda: parser)
        result = load_parser("fake_ok", "make_parser")
        assert result is parser

    def test_missing_module_raises(self):
        with pytest.raises(ModuleNotFoundError):
            load_parser("nonexistent_module_xyz", "func")

    def test_missing_attribute_raises(self, _make_fake_module):
        _make_fake_module("fake_no_attr", "other_func", lambda: None)
        with pytest.raises(AttributeError, match="has no attribute"):
            load_parser("fake_no_attr", "missing_func")

    def test_wrong_return_type_raises(self, _make_fake_module):
        _make_fake_module("fake_bad_ret", "not_a_parser", lambda: "not a parser")
        with pytest.raises(
            TypeError, match="did not return an argparse.ArgumentParser"
        ):
            load_parser("fake_bad_ret", "not_a_parser")


class TestRunArgdump:
    def test_writes_valid_json(self, parser, _make_fake_module, tmp_path):
        parser.add_argument("--foo")
        _make_fake_module("dump_mod", "make_parser", lambda: parser)
        out = tmp_path / "out.json"
        run_argdump("dump_mod:make_parser", out)
        data = json.loads(out.read_text())
        assert "actions" in data

    def test_creates_parent_directories(self, parser, _make_fake_module, tmp_path):
        _make_fake_module("dump_mod2", "make_parser", lambda: parser)
        out = tmp_path / "nested" / "deep" / "out.json"
        run_argdump("dump_mod2:make_parser", out)
        assert out.exists()

    def test_custom_indent(self, parser, _make_fake_module, tmp_path):
        _make_fake_module("dump_mod3", "make_parser", lambda: parser)
        out = tmp_path / "out.json"
        run_argdump("dump_mod3:make_parser", out, indent=4)
        text = out.read_text()
        assert "    " in text

    @pytest.mark.parametrize("prog", ["custom_name1", "custom_name2"])
    def test_with_prog_override(self, parser, _make_fake_module, tmp_path, prog):
        _make_fake_module("dump_mod4", "make_parser", lambda: parser)
        out = tmp_path / "out.json"
        run_argdump("dump_mod4:make_parser", out, prog=prog)
        data = json.loads(out.read_text())
        assert data["prog"] == prog


class TestBuildParser:
    def test_returns_argument_parser(self):
        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["mymod:myfunc"])
        assert args.output_path == Path("argdump.json")
        assert args.indent == 2
        assert args.prog is None

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
                "custom_name",
            ]
        )
        assert args.output_path == Path("custom.json")
        assert args.indent == 4
        assert args.prog == "custom_name"
