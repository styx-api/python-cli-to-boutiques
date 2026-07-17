import argparse
import json
from pathlib import Path

import pytest

from update_descriptor import apply_updates, build_parser, parse_path, set_at_path


class TestParsePath:
    @pytest.mark.parametrize(
        "path_str, expected",
        [
            ("name", ["name"]),
            ("inputs.name", ["inputs", "name"]),
            ("inputs[0]", ["inputs", 0]),
            ("inputs[0].name", ["inputs", 0, "name"]),
            ("my-key", ["my-key"]),
            ("inputs[0].name[1]", ["inputs", 0, "name", 1]),
            ("a.b[0].c[1].d", ["a", "b", 0, "c", 1, "d"]),
        ],
    )
    def test_parse_path(self, path_str, expected):
        assert parse_path(path_str) == expected

    def test_empty_string(self):
        assert parse_path("") == []


class TestSetAtPath:
    @pytest.mark.parametrize(
        "path_parts, value, expected",
        [
            (["name"], "hello", {"name": "hello"}),
            (["a", "b"], 42, {"a": {"b": 42}}),
        ],
    )
    def test_set_at_path(self, path_parts, value, expected):
        obj = {}
        set_at_path(obj, path_parts, value)
        assert obj == expected

    def test_creates_missing_intermediate_dict(self):
        obj = {"a": {}}
        set_at_path(obj, ["a", "b", "c"], "deep")
        assert obj == {"a": {"b": {"c": "deep"}}}

    def test_int_index_on_list(self):
        obj = {"a": [1, 2, 3]}
        set_at_path(obj, ["a", 1], "x")
        assert obj == {"a": [1, "x", 3]}

    def test_int_index_on_dict_raises(self):
        obj = {"a": {}}
        with pytest.raises(TypeError, match="Expected list"):
            set_at_path(obj, ["a", 0], "x")

    def test_int_index_on_root_dict_raises(self):
        with pytest.raises(TypeError, match="Expected list"):
            set_at_path({}, [0], "x")

    def test_overwrites_existing_value(self):
        obj = {"a": {"b": 1}}
        set_at_path(obj, ["a", "b"], 2)
        assert obj == {"a": {"b": 2}}


class TestApplyUpdates:
    def test_single_update(self):
        desc = {"name": "old"}
        result = apply_updates(desc, {"name": "new"}, remove_version=False)
        assert result["name"] == "new"

    def test_multiple_updates(self):
        desc = {"a": 1, "b": 2}
        result = apply_updates(desc, {"a": 10, "b": 20}, remove_version=False)
        assert result == {"a": 10, "b": 20}

    def test_nested_update(self):
        desc = {"inputs": [{"name": "old"}]}
        result = apply_updates(desc, {"inputs[0].name": "new"}, remove_version=False)
        assert result["inputs"][0]["name"] == "new"

    def test_remove_version_true(self):
        desc = {"name": "tool", "tool-version": "1.0"}
        result = apply_updates(desc, {}, remove_version=True)
        assert "tool-version" not in result

    def test_remove_version_false(self):
        desc = {"name": "tool", "tool-version": "1.0"}
        result = apply_updates(desc, {}, remove_version=False)
        assert result["tool-version"] == "1.0"

    def test_remove_version_missing_key(self):
        desc = {"name": "tool"}
        result = apply_updates(desc, {}, remove_version=True)
        assert result == {"name": "tool"}


class TestBuildParser:
    def test_returns_argument_parser(self):
        assert isinstance(build_parser(), argparse.ArgumentParser)

    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["-d", "desc.json"])
        assert args.output is None
        assert args.indent == 2
        assert args.remove_version is False
        assert args.updates_str is None
        assert args.updates_file is None

    def test_missing_required_descriptor(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args([])

    def test_custom_args(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "-d",
                "desc.json",
                "-o",
                "out.json",
                "--indent",
                "4",
                "--remove-version",
                "--updates-str",
                '{"name": "new"}',
            ]
        )
        assert args.descriptor == Path("desc.json")
        assert args.output == Path("out.json")
        assert args.indent == 4
        assert args.remove_version is True
        assert args.updates_str == '{"name": "new"}'

    def test_updates_file_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "-d",
                "desc.json",
                "--updates-file",
                "updates.json",
            ]
        )
        assert args.updates_file == Path("updates.json")
