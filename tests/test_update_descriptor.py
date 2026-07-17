import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "update_descriptor.py"
)

_spec = importlib.util.spec_from_file_location("update_descriptor", _SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules["update_descriptor"] = _module
_spec.loader.exec_module(_module)

parse_path = _module.parse_path
set_at_path = _module.set_at_path
apply_updates = _module.apply_updates


class TestParsePath:
    def test_simple_key(self):
        assert parse_path("name") == ["name"]

    def test_dotted_keys(self):
        assert parse_path("key1.key2.key3") == ["key1", "key2", "key3"]

    def test_bracket_index(self):
        assert parse_path("inputs[0]") == ["inputs", 0]

    def test_bracket_index_dotted(self):
        assert parse_path("inputs[0].name") == ["inputs", 0, "name"]

    def test_multiple_indices(self):
        assert parse_path("groups[0].members[1]") == ["groups", 0, "members", 1]

    def test_two_digit_index(self):
        assert parse_path("inputs[42]") == ["inputs", 42]


class TestSetAtPath:
    def test_set_existing_dict_key(self):
        obj = {"name": "old"}
        set_at_path(obj, ["name"], "new")
        assert obj == {"name": "new"}

    def test_set_existing_nested_dict_key(self):
        obj = {"outer": {"inner": "old"}}
        set_at_path(obj, ["outer", "inner"], "new")
        assert obj == {"outer": {"inner": "new"}}

    def test_set_new_nested_dict_key_creates_parents(self):
        obj = {}
        set_at_path(obj, ["new-key", "nested"], "value")
        assert obj == {"new-key": {"nested": "value"}}

    def test_set_deeply_nested_creates_all_parents(self):
        obj = {}
        set_at_path(obj, ["a", "b", "c"], "deep")
        assert obj == {"a": {"b": {"c": "deep"}}}

    def test_set_via_index(self):
        obj = {"inputs": [{"name": "old"}]}
        set_at_path(obj, ["inputs", 0, "name"], "new")
        assert obj == {"inputs": [{"name": "new"}]}

    def test_set_mixed_existing_and_new(self):
        obj = {"existing": {"x": 1}}
        set_at_path(obj, ["existing", "new-key"], 2)
        assert obj == {"existing": {"x": 1, "new-key": 2}}


class TestApplyUpdates:
    def test_apply_single_update(self):
        descriptor = {"name": "old"}
        result = apply_updates(descriptor, {"name": "new"})
        assert result == {"name": "new"}

    def test_apply_multiple_updates(self):
        descriptor = {"name": "tool", "version": "1.0"}
        result = apply_updates(descriptor, {"name": "updated", "version": "2.0"})
        assert result == {"name": "updated", "version": "2.0"}

    def test_apply_nested_update(self):
        descriptor = {"custom": {"field": 1}}
        result = apply_updates(descriptor, {"custom.field": 2})
        assert result == {"custom": {"field": 2}}

    def test_apply_creates_missing_parents(self):
        descriptor = {}
        result = apply_updates(descriptor, {"a.b.c": 3})
        assert result == {"a": {"b": {"c": 3}}}

    def test_apply_mixed_paths(self):
        descriptor = {"inputs": [{"id": "in1"}]}
        result = apply_updates(
            descriptor, {"inputs[0].id": "updated", "custom.flag": True}
        )
        assert result == {"inputs": [{"id": "updated"}], "custom": {"flag": True}}
