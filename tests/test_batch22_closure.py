"""批次 22 Phase B 收口测试：解释通道与执行通道同源 + D4 JSON 契约锁。

Phase A 已分测 explain-parser 行为；此处锁整链不变量：
- explain 的 winner 与执行路径 discover_parser() 对同一扩展名永远一致
  （解释是观察窗口，不是第二套决策）；
- --json 恰好五键、candidates 恰好三键——显式构造契约（裁决 D4），
  DiscoveryResult 未来新增内部字段不得泄漏进 CLI JSON。
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


@pytest.mark.parametrize("fname", ["doc.md", "doc.pdf", "doc.docx", "a/b/x.md"])
def test_explain_winner_matches_execution_path(fname, capfd):
    """解释通道的 winner == 执行通道 discover_parser() 的选择（同源锁）。"""
    rc = app_main(["explain-parser", fname, "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload["winner"] == discover_parser(fname)


def test_explain_winner_matches_execution_with_plugin(fresh_registry, capfd):
    """插件注册后两通道仍一致（解释覆盖插件场景）。"""

    class _Plug(Parser):
        name = "closure_b22_plug"
        version = "t/1"
        supported_extensions = (".c22",)
        priority = 2
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    register(_Plug)
    rc = app_main(["explain-parser", "x.c22", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload["winner"] == "closure_b22_plug"
    assert payload["winner"] == discover_parser("x.c22")


def test_json_contract_exact_keys(fresh_registry, capfd):
    """D4 契约锁：--json 恰好五键、candidates 元素恰好三键。"""

    class _Extra(Parser):
        name = "extra_field_probe"
        version = "t/1"
        supported_extensions = (".efp",)
        priority = 4
        source_types = ("text",)
        locator_family = "line_address"

        def parse(self, path, source_hash):  # pragma: no cover
            raise NotImplementedError

    register(_Extra)
    # 模拟未来 DiscoveryResult 漂移：给实例塞额外属性也不得改变 CLI JSON
    rc = app_main(["explain-parser", "x.efp", "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert set(payload.keys()) == {
        "extension", "candidates", "winner", "reason", "tied_names",
    }
    for c in payload["candidates"]:
        assert set(c.keys()) == {"name", "priority", "registration_order"}
