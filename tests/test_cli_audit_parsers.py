"""批次 23 Phase A 测试：audit-parsers 子命令。

裁决边界（Batch 23 Step 1 APPROVED）：
- extension universe 只来自 capability snapshot extensions 并集（无文件系统扫描）；
- 每个扩展的裁决委托 discover_parser_details()（单一决策实现）；
- status 是 CLI 派生展示字段（非 discovery 状态）；
- summary 只做数量/分类计数，无评分/排名；
- 空注册表 → 空报告不报错；不实例化 parser、不读文件、不 parse；
- audit 通道零 UserWarning；--plugin 复用批次 19 契约，错误码零新增。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

import app.parser_registry as pr
from app.cli import main as app_main
from app.parser_registry import discover_parser, register
from app.parsers.base import Parser

ROOT = Path(__file__).resolve().parent.parent

BUILTIN_EXTENSIONS = [
    ".docx", ".htm", ".html", ".ipynb", ".markdown", ".md", ".pdf",
    ".text", ".txt",
]


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


def test_human_output_extensions_and_summary(capfd):
    rc = app_main(["audit-parsers"])
    assert rc == 0
    out = capfd.readouterr().out
    for ext in BUILTIN_EXTENSIONS:
        assert ext in out
    assert "markdown_enhanced(5), markdown(20)" in out
    assert "fallback(10), kreuzberg(50)" in out
    assert "uncontested" in out and "priority_competition" in out
    assert "summary: 9 extensions" in out


def test_json_contract_shape(capfd):
    rc = app_main(["audit-parsers", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert set(payload.keys()) == {"extensions", "summary"}
    exts = payload["extensions"]
    assert [e["extension"] for e in exts] == sorted(
        e["extension"] for e in exts
    )
    assert set(payload["summary"].keys()) == {
        "extension_count", "uncontested", "priority_competition", "tie",
    }
    assert payload["summary"]["extension_count"] == len(exts)
    for e in exts:
        assert set(e.keys()) == {
            "extension", "candidates", "winner", "reason",
            "tied_names", "status",
        }
        assert e["status"] in {
            "uncontested", "priority_competition", "tie",
        }
        for c in e["candidates"]:
            assert set(c.keys()) == {
                "name", "priority", "registration_order",
            }
    total = sum(
        payload["summary"][k]
        for k in ("uncontested", "priority_competition", "tie")
    )
    assert total == payload["summary"]["extension_count"]


def test_status_derivation_three_kinds(fresh_registry, capfd):
    class _Solo(Parser):
        name = "solo_aud"
        version = "t/1"
        supported_extensions = (".solo",)
        priority = 8
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    class _TieA(Parser):
        name = "tie_a_aud"
        version = "t/1"
        supported_extensions = (".tiea",)
        priority = 7
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    class _TieB(Parser):
        name = "tie_b_aud"
        version = "t/1"
        supported_extensions = (".tiea",)
        priority = 7
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    register(_Solo)
    register(_TieA)
    register(_TieB)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rc = app_main(["audit-parsers", "--json"])
    assert rc == 0
    assert caught == [], "audit 通道不得触发 UserWarning"
    payload = json.loads(capfd.readouterr().out)
    by_ext = {e["extension"]: e for e in payload["extensions"]}
    assert by_ext[".solo"]["status"] == "uncontested"
    assert by_ext[".solo"]["winner"] == "solo_aud"
    assert by_ext[".tiea"]["status"] == "tie"
    assert by_ext[".tiea"]["winner"] == "tie_a_aud"
    assert by_ext[".tiea"]["tied_names"] == ["tie_a_aud", "tie_b_aud"]
    assert by_ext[".md"]["status"] == "priority_competition"


def test_tie_human_annotation(fresh_registry, capfd):
    class _T1(Parser):
        name = "tie_h1"
        version = "t/1"
        supported_extensions = (".tieh",)
        priority = 6
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    class _T2(Parser):
        name = "tie_h2"
        version = "t/1"
        supported_extensions = (".tieh",)
        priority = 6
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    register(_T1)
    register(_T2)
    rc = app_main(["audit-parsers"])
    assert rc == 0
    out = capfd.readouterr().out
    tie_line = next(ln for ln in out.splitlines() if ln.startswith(".tieh"))
    # D4 修正裁决：tie human 行显式含 winner name + registration_order
    # + "先注册者胜"说明（决胜依据可追溯，不需用户自行拼接）
    expected_order = list(pr._capabilities).index("tie_h1")
    assert (
        f"平局：先注册者 tie_h1 胜（registration_order={expected_order}）"
        in tie_line
    )


def test_empty_registry_empty_report(fresh_registry, capfd):
    fresh_registry.clear()
    rc = app_main(["audit-parsers", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload == {
        "extensions": [],
        "summary": {
            "extension_count": 0, "uncontested": 0,
            "priority_competition": 0, "tie": 0,
        },
    }


def test_audit_winner_matches_discover_parser(capfd):
    """同源锁：audit 的 winner 与执行通道 discover_parser() 逐扩展一致。"""
    rc = app_main(["audit-parsers", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    for e in payload["extensions"]:
        assert e["winner"] == discover_parser("x" + e["extension"])


def _run_cli(argv: list[str], env_extra: dict | None = None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *argv],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(ROOT), env=env, timeout=120,
    )


_PLUGIN = '''"""批次 23 Phase A 测试插件：.audx 参与审计。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class AudxPlug(Parser):
    name = "audx_plug"
    version = "test/1"
    supported_extensions = (".audx",)
    priority = 4
    source_types = ("audx",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''

_BAD_PLUGIN = '''"""批次 23 Phase A 测试插件：priority 非法。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class BadPlugB23(Parser):
    name = "bad_plug_b23"
    version = "test/1"
    supported_extensions = (".bad23",)
    priority = 0
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''


def test_plugin_participates_in_audit(tmp_path):
    (tmp_path / "audx_plug_b23.py").write_text(_PLUGIN, encoding="utf-8")
    r = _run_cli(
        ["audit-parsers", "--plugin", "audx_plug_b23", "--json"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    by_ext = {e["extension"]: e for e in payload["extensions"]}
    assert ".audx" in by_ext
    assert by_ext[".audx"]["winner"] == "audx_plug"
    assert by_ext[".audx"]["status"] == "uncontested"


def test_plugin_failure_before_audit(tmp_path):
    (tmp_path / "bad_plug_b23.py").write_text(_BAD_PLUGIN, encoding="utf-8")
    r = _run_cli(
        ["audit-parsers", "--plugin", "bad_plug_b23"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 1
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "plugin_register_failed"
    assert r.stdout == ""
