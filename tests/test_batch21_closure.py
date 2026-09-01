"""批次 21 Phase D 收口测试：跨层快照一致性 + 声明校验经插件通道。

Phase A/B/C 已分测各层；此处锁整链：
- register → 快照 → discover / details / list / declared_source_types
  在类属性漂移下的一致性（单一测试贯通四层）；
- register() 能力声明校验（priority/extensions）经批次 19 插件加载通道
  真实 CLI 呈现为 plugin_register_failed（错误体系稳定证明）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import app.parser_registry as pr
from app.parser_registry import (
    capability,
    declared_source_types,
    discover_parser,
    discover_parser_details,
    list_parsers,
    register,
)
from app.parsers.base import Parser

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


class _ClosureParser(Parser):
    name = "closure_snap"
    version = "orig/1"
    supported_extensions = (".cls",)
    priority = 6
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover - 测试桩
        raise NotImplementedError


def test_cross_layer_snapshot_consistency_under_drift(fresh_registry):
    """单一测试贯通四层：注册后改写全部能力类属性，四层读取一致。"""
    register(_ClosureParser)
    # 漂移：改写全部六项中的四项可变面（name 改写会导致重名/失联，不测）
    _ClosureParser.priority = 1
    _ClosureParser.supported_extensions = (".hack",)
    _ClosureParser.source_types = ("html",)
    _ClosureParser.version = "hacked/9"

    cap = capability("closure_snap")
    assert (cap.priority, cap.extensions, cap.source_types, cap.version) == (
        6, (".cls",), ("text",), "orig/1",
    )
    assert discover_parser("x.cls") == "closure_snap"
    with pytest.raises(ValueError, match="无已注册 parser"):
        discover_parser("x.hack")
    r = discover_parser_details("x.cls")
    assert r.winner == "closure_snap" and r.candidates[0].priority == 6
    row = next(x for x in list_parsers() if x["name"] == "closure_snap")
    assert row == {
        "name": "closure_snap",
        "priority": 6,
        "extensions": [".cls"],
        "version": "orig/1",
        "source_types": ["text"],
        "locator_family": "line_address",
    }
    assert declared_source_types(_ClosureParser) == ("text",)


_BAD_PRIORITY_PLUGIN = '''"""Phase D 收口：priority 非法（0）。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class BadPri(Parser):
    name = "bad_pri_plug"
    version = "t/1"
    supported_extensions = (".bp",)
    priority = 0
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''

_BAD_EXT_PLUGIN = '''"""Phase D 收口：扩展名非法（大写）。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class BadExt(Parser):
    name = "bad_ext_plug"
    version = "t/1"
    supported_extensions = (".BP",)
    priority = 10
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''


def _cli_with_plugin(tmp_path: Path, module_source: str, modname: str):
    (tmp_path / f"{modname}.py").write_text(module_source, encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "app.cli", "list-parsers",
         "--plugin", modname],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(ROOT), env=env, timeout=120,
    )


@pytest.mark.parametrize("source,modname", [
    (_BAD_PRIORITY_PLUGIN, "bad_pri_plug_mod"),
    (_BAD_EXT_PLUGIN, "bad_ext_plug_mod"),
])
def test_capability_validation_flows_through_plugin_channel(
    tmp_path: Path, source: str, modname: str
):
    """register() 能力校验失败 → 批次 19 既有错误码 plugin_register_failed。"""
    r = _cli_with_plugin(tmp_path, source, modname)
    assert r.returncode == 1
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "plugin_register_failed"
    assert "priority" in payload["errors"][0]["message"] or \
        "supported_extensions" in payload["errors"][0]["message"]
