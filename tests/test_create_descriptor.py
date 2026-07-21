from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "create_descriptor.sh"


def _base_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "tests")
    env["PARSER_TYPE"] = "argparse"
    env["PARSER_LOCATION"] = "conftest:make_parser"
    env["DUMP_FILE"] = "dump.json"
    env["OUTPUT_PATH"] = str(tmp_path / "desc.json")
    env["CLICK_PROG_NAME"] = ""
    env["CLICK_PARENT_LOCATION"] = ""
    env["EXCLUDE_VERSION"] = "false"
    env["UPDATES_FILE"] = ""
    env["UPDATES_STR"] = ""
    return env


def _run(
    tmp_path: Path, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    (tmp_path / "scripts").symlink_to(REPO_ROOT / "scripts")
    env = _base_env(tmp_path)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )


class TestArgparseFlow:
    def test_creates_output_file(self, tmp_path):
        result = _run(tmp_path)
        assert result.returncode == 0
        assert (tmp_path / "desc.json").exists()

    def test_output_is_valid_json(self, tmp_path):
        _run(tmp_path)
        data = json.loads((tmp_path / "desc.json").read_text())
        assert "name" in data

    def test_does_not_use_clickdump(self, tmp_path):
        result = _run(tmp_path)
        assert "run_clickdump" not in result.stderr

    def test_custom_args(self, tmp_path):
        result = _run(
            tmp_path,
            {
                "PROG_NAME": "custom_name",
            },
        )
        assert result.returncode == 0
        out_file = tmp_path / "desc.json"
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert data["name"] == "custom_name"


class TestClickFlow:
    def test_creates_output_file(self, tmp_path):
        result = _run(
            tmp_path,
            {"PARSER_TYPE": "click", "PARSER_LOCATION": "conftest:test_cli"},
        )
        assert result.returncode == 0
        assert (tmp_path / "desc.json").exists()

    def test_output_is_valid_json(self, tmp_path):
        _run(tmp_path, {"PARSER_TYPE": "click", "PARSER_LOCATION": "conftest:test_cli"})
        data = json.loads((tmp_path / "desc.json").read_text())
        assert "name" in data

    def test_with_prog(self, tmp_path):
        result = _run(
            tmp_path,
            {
                "PARSER_TYPE": "click",
                "PARSER_LOCATION": "conftest:test_cli",
                "CLICK_PROG_NAME": "myprog",
            },
        )
        assert result.returncode == 0
        data = json.loads((tmp_path / "desc.json").read_text())
        assert data.get("name") == "myprog"

    def test_with_parent(self, tmp_path):
        result = _run(
            tmp_path,
            {
                "PARSER_TYPE": "click",
                "PARSER_LOCATION": "conftest:test_cli",
                "CLICK_PARENT_LOCATION": "conftest:test_cli",
            },
        )
        assert result.returncode == 0
        assert (tmp_path / "desc.json").exists()


class TestUpdateDescriptor:
    def test_exclude_version_true(self, tmp_path):
        result = _run(tmp_path, {"EXCLUDE_VERSION": "true"})
        assert result.returncode == 0

    def test_with_updates_file(self, tmp_path):
        updates_file = tmp_path / "updates.json"
        updates_file.write_text(json.dumps({"description": "updated via file"}))
        _run(tmp_path, {"UPDATES_FILE": str(updates_file)})
        data = json.loads((tmp_path / "desc.json").read_text())
        assert data["description"] == "updated via file"

    def test_with_updates_str(self, tmp_path):
        _run(tmp_path, {"UPDATES_STR": json.dumps({"description": "updated via str"})})
        data = json.loads((tmp_path / "desc.json").read_text())
        assert data["description"] == "updated via str"


class TestErrorCases:
    def test_unknown_parser_type_exits(self, tmp_path):
        result = _run(tmp_path, {"PARSER_TYPE": "invalid"})
        assert result.returncode != 0


class TestOutputParentDirs:
    def test_creates_nested_output_dirs(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "desc.json"
        result = _run(tmp_path, {"OUTPUT_PATH": str(nested)})
        assert result.returncode == 0
        assert nested.exists()
