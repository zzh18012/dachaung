"""批次 21 Phase C 测试：list-parsers 能力展示（表格两列 + --json）。

裁决边界：JSON 输出必须来自 _capabilities 快照（经 list_parsers()），
不重读 Parser 类；人类表格默认输出保留（仅增列）。
"""

from __future__ import annotations

import json

import pytest

import app.parser_registry as pr
from app.cli import main as app_main
from app.parser_registry import list_parsers, register
from app.parsers.base import Parser


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


def test_table_has_capability_columns(capfd):
    rc = app_main(["list-parsers"])
    assert rc == 0
    out = capfd.readouterr().out
    for col in ("name", "priority", "extensions", "source_types",
                "locator_family", "version"):
        assert col in out, f"表头缺列 {col}"
    assert "pdf,docx" in out  # fallback 的 source_types
    assert "markdown_enhanced" in out


def test_table_locator_family_shows_dash_for_none(capfd):
    rc = app_main(["list-parsers"])
    assert rc == 0
    out = capfd.readouterr().out
    # fallback 是纯内置多类型（locator_family=None）→ 显示 -
    fallback_line = next(
        ln for ln in out.splitlines() if ln.startswith("fallback")
    )
    assert " - " in fallback_line


def test_json_output_shape_and_order(capfd):
    rc = app_main(["list-parsers", "--json"])
    assert rc == 0
    out = capfd.readouterr().out
    rows = json.loads(out)
    assert isinstance(rows, list) and rows
    names = [r["name"] for r in rows]
    assert "fallback" in names and "markdown_enhanced" in names
    # (priority, name) 稳定序
    keyed = [(r["priority"], r["name"]) for r in rows]
    assert keyed == sorted(keyed)
    for r in rows:
        assert set(r.keys()) == {
            "name", "priority", "extensions", "version",
            "source_types", "locator_family",
        }
        assert isinstance(r["extensions"], list)
        assert isinstance(r["source_types"], list)
    fb = next(r for r in rows if r["name"] == "fallback")
    assert fb["extensions"] == [".pdf", ".docx"]
    assert fb["source_types"] == ["pdf", "docx"]
    assert fb["locator_family"] is None
    md = next(r for r in rows if r["name"] == "markdown")
    assert md["source_types"] == ["markdown"]
    assert md["locator_family"] == "line_address"


def test_json_matches_list_parsers_rows(capfd):
    rc = app_main(["list-parsers", "--json"])
    assert rc == 0
    rows = json.loads(capfd.readouterr().out)
    assert rows == list_parsers(), "--json 必须与 list_parsers() 行完全一致"


def test_json_with_plugin_loaded(tmp_path, capfd):
    plugin = tmp_path / "cap_cli_plug.py"
    plugin.write_text(
        "from app.parser_registry import register\n"
        "from app.parsers.base import Parser\n"
        "\n"
        "@register\n"
        "class CapCliPlug(Parser):\n"
        "    name = 'cap_cli_plug'\n"
        "    version = 'test/1.0'\n"
        "    supported_extensions = ('.ccp',)\n"
        "    priority = 3\n"
        "    source_types = ('ccp',)\n"
        "    locator_family = 'line_address'\n"
        "\n"
        "    def parse(self, path, source_hash):  # pragma: no cover\n"
        "        raise NotImplementedError\n",
        encoding="utf-8",
    )
    import os
    import subprocess
    import sys

    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    from pathlib import Path
    root = Path(pr.__file__).resolve().parent.parent
    r = subprocess.run(
        [sys.executable, "-m", "app.cli", "list-parsers",
         "--plugin", "cap_cli_plug", "--json"],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(root), env=env,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    rows = json.loads(r.stdout)
    entry = next(x for x in rows if x["name"] == "cap_cli_plug")
    assert entry["source_types"] == ["ccp"]
    assert entry["locator_family"] == "line_address"
    assert entry["priority"] == 3
    assert entry["extensions"] == [".ccp"]


def test_json_derived_from_snapshot_not_live_attrs(fresh_registry, capfd):
    """--json 数据源是快照：注册后改类属性，CLI 输出不变。"""

    class _Drift(Parser):
        name = "cli_drift"
        version = "orig/1"
        supported_extensions = (".cld",)
        priority = 4
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    register(_Drift)
    _Drift.version = "hacked/9"
    _Drift.priority = 1
    rc = app_main(["list-parsers", "--json"])
    assert rc == 0
    rows = json.loads(capfd.readouterr().out)
    entry = next(x for x in rows if x["name"] == "cli_drift")
    assert entry["version"] == "orig/1"
    assert entry["priority"] == 4
