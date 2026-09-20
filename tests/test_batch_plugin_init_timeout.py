"""Stage 10 批次 7 测试：plugin_init_report_timeout 路径补齐（r60 授权，C5）。

裁决边界（Stage-10-Batch-7 AUTHORIZED / ADOPTION §145）：
- 纯测试债务批：不改默认 timeout 值/公开 API/插件发现加载语义/retry
  策略/错误分类契约——默认值 120.0 由守护测试钉死；
- 确定性机制：monkeypatch 模块常量 PLUGIN_INIT_REPORT_TIMEOUT（父进程
  运行时读全局，生产默认零变化；子进程不用该值）+ sentinel 门控的
  worker 侧导入挂起（真实跨进程 spawn，父进程小超时确定性先到，观察
  等待仅为补丁值，worker 的 sleep 随池 terminate 被杀，无真实长等待）；
- 两面覆盖（r60）：正常插件不受影响（默认超时并行全量成功、零超时
  事件）+ 超时路径按既有契约（queue.Empty → 受控
  plugin_init_report_timeout，文件任务零派发、无 summary、结构化 JSON
  无 traceback、JSONL 带 expected/received worker 数）；
- 既有真实 parser 插件的并行成功路径另见
  tests/test_plugin_loader.py::test_batch_parallel_with_plugins_jsonl。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import app.batch as batch_mod
from app.cli import main as app_main
from app.plugin_loader import load_plugins

_PLUGIN_NOOP = "X = 1\n"

# sentinel 门控挂起：父进程先于 sentinel 落盘导入（快速成功、CLI 预载
# 走 sys.modules 缓存）；worker 侧（spawn 全新 sys.modules）重放导入时
# sentinel 已在 → time.sleep 挂起 → 永不回报 → 父进程补丁超时先到。
_PLUGIN_HANGING = r'''
import os
import time

_SENTINEL = os.path.join(os.path.dirname(__file__), "hang_on.txt")
if os.path.exists(_SENTINEL):
    time.sleep(30)

from app.parser_registry import register
from app.parsers.base import Parser


@register
class HangingParser(Parser):
    name = "hanging_plugin"
    version = "test/1.0"
    supported_extensions = (".hng",)
    priority = 1
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):
        raise NotImplementedError
'''


def _write_plugin(directory: Path, mod_name: str, source: str) -> str:
    (directory / f"{mod_name}.py").write_text(source, encoding="utf-8")
    return mod_name


def _write_docs(directory: Path, n: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (directory / f"doc{i}.md").write_text(f"# 文档{i}\n\n正文{i}\n", encoding="utf-8")
    return directory


@pytest.fixture
def plugin_env(tmp_path: Path, monkeypatch):
    """sys.path 注入 + 注册表/能力快照副本隔离 + 首载备忘重置 +
    模块 sys.modules 清理（沿 test_plugin_loader.py 批次 5 修正版）。"""
    monkeypatch.syspath_prepend(str(tmp_path))
    import app.parser_registry as pr
    from app import plugin_loader as pl

    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    monkeypatch.setattr(pl, "_FIRST_LOAD", {})
    yield tmp_path
    for key, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and str(tmp_path) in str(f):
            del sys.modules[key]


def _read_events(log: Path) -> list[dict]:
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


# ---------- 契约守护：默认值钉死（r60：不改变默认 timeout 值） ----------

def test_default_timeout_constant_frozen():
    assert batch_mod.PLUGIN_INIT_REPORT_TIMEOUT == 120.0


# ---------- 面 1：正常插件不受影响（默认超时，真实并行池） ----------

def test_normal_plugin_parallel_default_timeout_unaffected(plugin_env: Path):
    _write_plugin(plugin_env, "noop_mod", _PLUGIN_NOOP)
    docs = _write_docs(plugin_env / "docs", 3)
    out = plugin_env / "out"
    log = plugin_env / "batch.jsonl"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--plugin", "noop_mod",
         "--workers", "2", "--log-file", str(log)]
    )
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 3 and summary["failed"] == 0
    events = _read_events(log)
    kinds = {e["event"] for e in events}
    assert "plugin_loaded" in kinds
    assert "plugin_load_failed" not in kinds  # 默认 120s 下回报通道零超时
    assert sum(1 for e in events if e["event"] == "file_complete") == 3


# ---------- 面 2：超时路径按既有契约（补丁超时 + worker 导入挂起） ----------

def test_worker_init_report_timeout_controlled(plugin_env: Path, capfd, monkeypatch):
    """真实跨进程：父进程预载成功（无 sentinel），worker 重放导入挂起
    （sentinel 已落盘）→ 父进程补丁超时（1.0s）确定性先到 →
    queue.Empty 受控上抛，池回收，零文件派发。"""
    _write_plugin(plugin_env, "hang_mod", _PLUGIN_HANGING)
    load_plugins(["hang_mod"])  # 父进程侧快速导入成功（sentinel 未落盘）
    (plugin_env / "hang_on.txt").write_text("on", encoding="utf-8")
    monkeypatch.setattr(batch_mod, "PLUGIN_INIT_REPORT_TIMEOUT", 1.0)

    docs = _write_docs(plugin_env / "docs2", 3)
    out = plugin_env / "out2"
    log = plugin_env / "timeout.jsonl"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out),
         "--plugin", "hang_mod", "--workers", "2", "--log-file", str(log)]
    )
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    e0 = err["errors"][0]
    assert e0["code"] == "plugin_init_report_timeout"
    assert e0["plugin"] == "hang_mod"
    assert e0["error_type"] == "Empty"  # queue.Empty 的受控类型名
    assert "固定上限 1.0s" in e0["message"]  # 补丁常量流入消息（运行时读全局）
    assert "traceback" not in json.dumps(err)

    assert not (out / "summary.json").exists()  # 受控终止，无 summary

    events = _read_events(log)
    kinds = {ev["event"] for ev in events}
    failed = [ev for ev in events if ev["event"] == "plugin_load_failed"]
    assert len(failed) == 1
    f0 = failed[0]
    assert f0["error_code"] == "plugin_init_report_timeout"
    assert f0["plugin"] == "hang_mod"
    assert f0["expected_workers"] == 2
    assert f0["received_reports"] == 0
    # 文件任务零派发（批次 19 契约：回报收取先于派发）
    assert "file_complete" not in kinds
    assert "file_error" not in kinds
    assert "batch_complete" not in kinds
    assert "batch_start" in kinds
