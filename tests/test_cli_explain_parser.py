"""批次 22 Phase A 测试：explain-parser 子命令。

裁决边界（Batch 22 Step 1 APPROVED）：
- 只取 path.suffix，不读文件内容、不实例化 parser、不 parse（文件不存在可解释）；
- 解释报告（stdout）含 extension/candidates/winner/reason/平局信息；
- 不重放 discover_parser() 的 UserWarning（执行路径与解释语义不同）；
- --json 显式构造字段（不用 asdict，防未来内部字段泄漏）；
- 无候选 → unsupported_type；插件加载失败 → plugin_*（错误码零新增）。
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

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


def test_human_output_basic(capfd):
    rc = app_main(["explain-parser", "doc.md"])
    assert rc == 0
    out = capfd.readouterr().out
    assert "extension: .md" in out
    assert "winner: markdown_enhanced" in out  # 5 < 20
    assert "candidates" in out
    assert "markdown_enhanced" in out  # .md 有两个候选
    assert "<-- winner" in out
    assert "reason:" in out
    # 裁决要求的免责说明
    assert "file content was not read" in out


def test_file_not_exist_still_explains(capfd, tmp_path):
    """解释对象是扩展名，不是文件内容——不存在也能解释。"""
    rc = app_main(["explain-parser", str(tmp_path / "no_such_file.pdf")])
    assert rc == 0
    out = capfd.readouterr().out
    assert "extension: .pdf" in out
    assert "winner: fallback" in out


def test_json_output_shape_md(capfd):
    rc = app_main(["explain-parser", "doc.md", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    # D4 裁决：显式字段集，恰好五键
    assert set(payload.keys()) == {
        "extension", "candidates", "winner", "reason", "tied_names",
    }
    assert payload["extension"] == ".md"
    assert payload["winner"] == "markdown_enhanced"  # 5 < 20
    assert payload["tied_names"] == []  # 5 < 20 非平局
    for c in payload["candidates"]:
        assert set(c.keys()) == {"name", "priority", "registration_order"}
    assert [c["name"] for c in payload["candidates"]] == [
        "markdown_enhanced", "markdown",
    ]
    prios = [(c["priority"], c["registration_order"]) for c in payload["candidates"]]
    assert prios == sorted(prios)


def test_json_output_shape_pdf_single_candidate(capfd):
    rc = app_main(["explain-parser", "doc.pdf", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload["winner"] == "fallback"
    cand_names = [c["name"] for c in payload["candidates"]]
    assert cand_names == ["fallback", "kreuzberg"]  # 10 < 50
    assert payload["reason"].startswith("扩展名 .pdf 共 2 个候选")


def test_no_candidates_unsupported_type(capfd, tmp_path):
    rc = app_main(["explain-parser", str(tmp_path / "x.zzz")])
    assert rc == 1
    captured = capfd.readouterr()
    payload = json.loads(captured.err)
    assert payload["errors"][0]["code"] == "unsupported_type"
    assert ".zzz" in payload["errors"][0]["message"]
    assert captured.out == ""


def test_tie_shown_without_warning(fresh_registry, capfd):
    """平局信息入报告；explain 通道不重放 discover_parser 的 UserWarning。"""
    from app.parsers.base import Parser

    class _TieA(Parser):
        name = "tie_a"
        version = "t/1"
        supported_extensions = (".tie",)
        priority = 7
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    class _TieB(Parser):
        name = "tie_b"
        version = "t/1"
        supported_extensions = (".tie",)
        priority = 7
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    pr.register(_TieA)
    pr.register(_TieB)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rc = app_main(["explain-parser", "x.tie", "--json"])
    assert rc == 0
    assert caught == [], "explain-parser 不得触发 UserWarning"
    payload = json.loads(capfd.readouterr().out)
    assert payload["winner"] == "tie_a"
    assert payload["tied_names"] == ["tie_a", "tie_b"]
    assert "平局" in payload["reason"]
    assert "先注册者" in payload["reason"]


def _run_cli(argv: list[str], env_extra: dict | None = None, cwd: Path = ROOT):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *argv],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd), env=env, timeout=120,
    )


_PLUGIN = '''"""批次 22 Phase A 测试插件：.exx 解释参与。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class ExxPlug(Parser):
    name = "exx_plug"
    version = "test/1"
    supported_extensions = (".exx",)
    priority = 3
    source_types = ("exx",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''

_BAD_PLUGIN = '''"""批次 22 Phase A 测试插件：priority 非法。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class BadPlug(Parser):
    name = "bad_plug_b22"
    version = "test/1"
    supported_extensions = (".bad",)
    priority = 0
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''


def test_plugin_participates_in_explanation(tmp_path):
    (tmp_path / "exx_plug_b22.py").write_text(_PLUGIN, encoding="utf-8")
    r = _run_cli(
        ["explain-parser", "doc.exx", "--plugin", "exx_plug_b22", "--json"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["winner"] == "exx_plug"
    assert [c["name"] for c in payload["candidates"]] == ["exx_plug"]


def test_plugin_load_failure_before_explanation(tmp_path):
    (tmp_path / "bad_plug_b22.py").write_text(_BAD_PLUGIN, encoding="utf-8")
    r = _run_cli(
        ["explain-parser", "doc.md", "--plugin", "bad_plug_b22"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 1
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "plugin_register_failed"
    assert r.stdout == ""  # 未进入解释输出


def test_builtin_behavior_unchanged_reported_via_explain(capfd):
    """内置语义经 explain 可见：.docx 也由 fallback 胜出（10 < 50）。"""
    rc = app_main(["explain-parser", "doc.docx", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload["extension"] == ".docx"
    assert payload["winner"] == "fallback"
