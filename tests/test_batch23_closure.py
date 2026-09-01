"""批次 23 Phase B 收口测试：三层同源锁（audit ↔ explain ↔ 执行）。

Phase A 已锁 audit winner == discover_parser()；此处补齐 GPT 指定的
跨层证明：对同一 extension，audit-parsers / explain-parser /
discover_parser() 三者 winner 一致，覆盖 priority_competition 与真实
tie 两类场景——"全局审计只是已有 resolution 的观察层"的完整跨层证明。
"""

from __future__ import annotations

import json

import pytest

import app.parser_registry as pr
from app.cli import main as app_main
from app.parser_registry import discover_parser, register
from app.parsers.base import Parser


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


def _audit_winner_map(capfd) -> dict[str, str]:
    rc = app_main(["audit-parsers", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    return {e["extension"]: e["winner"] for e in payload["extensions"]}


def _explain_winner(capfd, fname: str) -> str:
    rc = app_main(["explain-parser", fname, "--json"])
    assert rc == 0
    return json.loads(capfd.readouterr().out)["winner"]


@pytest.mark.parametrize("fname", ["doc.md", "doc.pdf", "doc.docx"])
def test_three_layer_consistency_priority_competition(fname, capfd):
    """内置 priority 竞争扩展：三层 winner 一致。"""
    audit = _audit_winner_map(capfd)
    ext = "." + fname.rsplit(".", 1)[1]
    assert audit[ext] == _explain_winner(capfd, fname)
    assert audit[ext] == discover_parser(fname)


def test_three_layer_consistency_real_tie(fresh_registry, capfd):
    """真实平局场景：三层 winner 一致且同为先注册者。"""

    class _LayerA(Parser):
        name = "layer_tie_a"
        version = "t/1"
        supported_extensions = (".laytie",)
        priority = 7
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    class _LayerB(Parser):
        name = "layer_tie_b"
        version = "t/1"
        supported_extensions = (".laytie",)
        priority = 7
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    register(_LayerA)
    register(_LayerB)

    audit = _audit_winner_map(capfd)
    assert audit[".laytie"] == "layer_tie_a"
    assert _explain_winner(capfd, "x.laytie") == "layer_tie_a"
    # 执行通道平局仍发 UserWarning（与 audit/explain 的零告警形成
    # 三层行为差异——见 test_cli_audit_parsers / test_cli_explain_parser）
    with pytest.warns(UserWarning, match="layer_tie_a"):
        assert discover_parser("x.laytie") == "layer_tie_a"


def test_audit_extension_universe_exactly_snapshot_union(fresh_registry, capfd):
    """universe 恰为快照 extensions 并集（不增不减）。"""

    class _U(Parser):
        name = "universe_probe"
        version = "t/1"
        supported_extensions = (".uprobe",)
        priority = 11
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    register(_U)
    audit = _audit_winner_map(capfd)
    expected = sorted({
        ext
        for cap in pr._capabilities.values()
        for ext in cap.extensions
    })
    assert sorted(audit.keys()) == expected
    assert ".uprobe" in audit
