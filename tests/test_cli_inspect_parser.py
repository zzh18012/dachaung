"""批次 24 Phase A 测试：inspect-parser 子命令（D3/D4/D5）。

裁决边界（Batch 24 Step 1 APPROVED AFTER D1 REVISION）：
- 新增 `inspect-parser <name> [--plugin MODULE ...] [--json]`，只做
  identity/provenance，不解释选择/竞争/能力全量；
- --json 显式构造六键 {name, version, module, qualname, loaded_via,
  plugin_spec}（禁 asdict）；builtin 时 plugin_spec 为 null 不省略；
- 禁 __file__/绝对路径/cwd/临时目录/环境变量/import search path 泄漏；
  human 模式信息集合不超六项；
- --plugin 加载先于名字查询：初始未知、加载后出现 → 可查询；插件失败
  → plugin_import_failed/plugin_register_failed（不得落成 unknown_parser）；
  插件成功但名字不存在 → unknown_parser rc 1；
- 既有三个 JSON（list/explain/audit）键集零变化（键集锁回归）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import app.parser_registry as pr
from app.cli import main as app_main
from app.parser_registry import register
from app.parsers.base import Parser

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


def _make_cls(name: str, ext: str, version: str = "test/1"):
    return type(
        f"Cli_{name}",
        (Parser,),
        {
            "name": name,
            "version": version,
            "supported_extensions": (ext,),
            "priority": 80,
            "source_types": ("text",),
            "locator_family": "line_address",
            "parse": lambda self, path, source_hash: None,  # pragma: no cover
        },
    )


def _run_cli(argv: list[str], env_extra: dict | None = None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *argv],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(ROOT), env=env, timeout=120,
    )


# ---------- D4：JSON 六键契约 ----------

def test_json_builtin_exact_six_keys_plugin_spec_null(capfd):
    rc = app_main(["inspect-parser", "fallback", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert set(payload.keys()) == {
        "name", "version", "module", "qualname", "loaded_via", "plugin_spec",
    }
    assert payload["name"] == "fallback"
    assert payload["module"] == "app.parsers.fallback_parser"
    assert payload["qualname"] == "FallbackParser"
    assert payload["loaded_via"] == "builtin"
    assert payload["plugin_spec"] is None  # null 不省略
    assert payload["version"] == pr.capability("fallback").version  # 注册表冻结值


def test_json_no_path_leak(capfd):
    """D4 负面约束：module/qualname/plugin_spec 是 dotted 名，不含路径
    分隔符/绝对路径/__file__（version 由 parser 作者自定，不作路径判定；
    plugin_spec 拒路径在 registry 层测试覆盖）。"""
    rc = app_main(["inspect-parser", "markdown_enhanced", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    for key in ("module", "qualname"):
        assert "/" not in payload[key]
        assert "\\" not in payload[key]
    assert payload["plugin_spec"] is None


# ---------- D3：human 输出 ----------

def test_human_output_exactly_six_items(capfd):
    rc = app_main(["inspect-parser", "kreuzberg"])
    assert rc == 0
    lines = [ln for ln in capfd.readouterr().out.splitlines() if ln.strip()]
    assert len(lines) == 6  # 信息集合不超六项
    keys = [ln.split(":", 1)[0] for ln in lines]
    assert keys == [
        "name", "version", "module", "qualname", "loaded_via", "plugin_spec",
    ]
    assert "loaded_via: builtin" in lines
    assert "plugin_spec: -" in lines  # None 显示 "-"，与 list-parsers 同规


def test_human_and_json_same_information_set(capfd):
    """human 与 --json 信息集合一致（六项，无额外/缺失）。"""
    app_main(["inspect-parser", "html"])
    human = capfd.readouterr().out
    app_main(["inspect-parser", "html", "--json"])
    payload = json.loads(capfd.readouterr().out)
    for key in payload:
        assert f"{key}:" in human
    assert human.count("\n") == 6  # 恰六行（末行换行）


# ---------- D5：unknown / 插件序 ----------

def test_unknown_name_structured_error(capfd):
    rc = app_main(["inspect-parser", "no_such_parser"])
    assert rc == 1
    captured = capfd.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["errors"][0]["code"] == "unknown_parser"
    assert "no_such_parser" in payload["errors"][0]["message"]


def test_plugin_registered_then_inspectable(tmp_path):
    """初始未知 → unknown_parser；--plugin 加载后出现 → 可查询且
    provenance 归该 spec。"""
    plugin = '''"""批次 24 CLI 测试插件。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class InspPlug(Parser):
    name = "insp_plug"
    version = "test/1"
    supported_extensions = (".insp",)
    priority = 3
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''
    (tmp_path / "insp_plug_b24.py").write_text(plugin, encoding="utf-8")
    r0 = _run_cli(
        ["inspect-parser", "insp_plug", "--json"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r0.returncode == 1
    assert json.loads(r0.stderr)["errors"][0]["code"] == "unknown_parser"

    r1 = _run_cli(
        ["inspect-parser", "insp_plug", "--plugin", "insp_plug_b24", "--json"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r1.returncode == 0, r1.stderr
    payload = json.loads(r1.stdout)
    assert payload["loaded_via"] == "plugin"
    assert payload["plugin_spec"] == "insp_plug_b24"
    assert payload["module"] == "insp_plug_b24"


def test_plugin_failure_not_unknown_parser(tmp_path):
    """插件失败 → plugin_register_failed（rc 1），不落成 unknown_parser。"""
    bad = '''"""批次 24 CLI 测试插件：priority 非法。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class BadPlugB24(Parser):
    name = "bad_plug_b24"
    version = "test/1"
    supported_extensions = (".bad24",)
    priority = 0
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''
    (tmp_path / "bad_plug_b24.py").write_text(bad, encoding="utf-8")
    r = _run_cli(
        ["inspect-parser", "bad_plug_b24", "--plugin", "bad_plug_b24"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 1
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "plugin_register_failed"
    assert r.stdout == ""


def test_plugin_ok_but_other_name_unknown(tmp_path):
    """插件成功但查询的是别的名字 → unknown_parser rc 1。"""
    plugin = '''from app.parser_registry import register
from app.parsers.base import Parser


@register
class OkPlugB24(Parser):
    name = "ok_plug_b24"
    version = "test/1"
    supported_extensions = (".ok24",)
    priority = 4
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''
    (tmp_path / "ok_plug_b24.py").write_text(plugin, encoding="utf-8")
    r = _run_cli(
        ["inspect-parser", "someone_else", "--plugin", "ok_plug_b24"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 1
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "unknown_parser"


# ---------- D2/D4：inspect 只读快照，注册后漂移不生效 ----------

def test_inspect_reads_snapshot_not_live_class(fresh_registry, capfd):
    cls = _make_cls("cli_drift", ".clidrift", version="orig/24")
    orig_module, orig_qualname = cls.__module__, cls.__qualname__
    register(cls)  # 无上下文 → builtin
    cls.__module__ = "fake.module"
    cls.__qualname__ = "FakeQual"
    cls.version = "hacked/1"
    with pr._plugin_registration_context("plug.late"):
        rc = app_main(["inspect-parser", "cli_drift", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload["module"] == orig_module
    assert payload["qualname"] == orig_qualname
    assert payload["version"] == "orig/24"
    assert payload["loaded_via"] == "builtin"
    assert payload["plugin_spec"] is None


# ---------- 键集锁回归：三个既有 JSON 不泄漏新字段 ----------

def test_existing_json_keysets_locked_with_plugin_provenance(fresh_registry, capfd):
    """快照携带 provenance 四字段后，list/explain/audit 的 JSON 键集
    仍与批次 21/22/23 契约完全一致（显式构造不泄漏新字段）。"""
    with pr._plugin_registration_context("plug.lock"):
        register(_make_cls("keyset_plug", ".keyset24"))
    rc = app_main(["list-parsers", "--json"])
    assert rc == 0
    rows = json.loads(capfd.readouterr().out)
    for row in rows:
        assert set(row.keys()) == {
            "name", "priority", "extensions", "version",
            "source_types", "locator_family",
        }

    rc = app_main(["explain-parser", "doc.keyset24", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert set(payload.keys()) == {
        "extension", "candidates", "winner", "reason", "tied_names",
    }
    for c in payload["candidates"]:
        assert set(c.keys()) == {"name", "priority", "registration_order"}
    assert payload["winner"] == "keyset_plug"

    rc = app_main(["audit-parsers", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert set(payload.keys()) == {"extensions", "summary"}
    assert set(payload["summary"].keys()) == {
        "extension_count", "uncontested", "priority_competition", "tie",
    }
    for e in payload["extensions"]:
        assert set(e.keys()) == {
            "extension", "candidates", "winner", "reason",
            "tied_names", "status",
        }
