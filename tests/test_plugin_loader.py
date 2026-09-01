"""批次 19 测试：显式外部插件加载。

覆盖裁决要求：可重复 --plugin / dotted 模块语义与幂等 / 导入与注册失败
错误契约（plugin_import_failed vs plugin_register_failed）/ 插件加载先于
parser 名称校验 / 动态校验 unknown_parser rc1 / list-parsers --plugin /
批量父进程 fail-fast 不启动池 / 并行 worker 受控初始化回报通道 /
parse_one_file 防御背板 / JSONL 事件 / validate 不变。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import app.batch as batch_mod
from app.cli import main as app_main
from app.parser_registry import discover_parser
from app.plugin_loader import PluginLoadError, load_plugins

_PLUGIN_MYX = r'''
from pathlib import Path

from app.models import Document, Element, WarningRecord
from app.parser_registry import register
from app.parsers.base import Parser, make_document_id


@register
class MyxParser(Parser):
    name = "myx_test"
    version = "test/1.0"
    supported_extensions = (".myx",)
    priority = 1
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        document_id = make_document_id(source_hash)
        elements = []
        for i, seg in enumerate(s for s in text.split("\n\n") if s.strip()):
            elements.append(
                Element(
                    element_id=f"{document_id}::e{i:04d}",
                    type="paragraph",
                    content=seg.strip(),
                    parent_id=None,
                    source_locator={"family": "line_address", "line": 1},
                    confidence=0.95,
                    metadata={},
                )
            )
        warnings = [] if elements else [
            WarningRecord(code="myx_no_content", reason="空文档")
        ]
        return Document(
            document_id=document_id,
            source_path=str(p),
            source_type="text",
            source_hash=source_hash,
            parser_name=self.name,
            parser_version=self.version,
            elements=elements,
            chunks=[],
            relations=[],
            warnings=warnings,
            errors=[],
            metadata={"myx": True},
        )
'''

_PLUGIN_CLASH = r'''
from app.parser_registry import register
from app.parsers.base import Parser


@register
class ClashParser(Parser):
    name = "fallback"
    version = "test/1.0"
    supported_extensions = (".clash",)
    priority = 1

    def parse(self, path, source_hash):
        raise NotImplementedError
'''

_PLUGIN_SYNTAX_ERROR = "def broken(:\n"

_PLUGIN_TOPLEVEL_VALUEERROR = "raise ValueError('top-level plugin ValueError')\n"

_PLUGIN_SENTINEL = r'''
import os

_SENTINEL = os.path.join(os.path.dirname(__file__), "sentinel_on.txt")
if os.path.exists(_SENTINEL):
    raise RuntimeError("worker-only plugin failure")

from app.parser_registry import register
from app.parsers.base import Parser


@register
class SentinelParser(Parser):
    name = "sentinel_plugin"
    version = "test/1.0"
    supported_extensions = (".snt",)
    priority = 1
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):
        raise NotImplementedError
'''


def _tie_plugin(var: str) -> str:
    return (
        "from app.parser_registry import register\n"
        "from app.parsers.base import Parser\n"
        "\n"
        "\n"
        "@register\n"
        f"class {var.upper()}Parser(Parser):\n"
        f'    name = "{var}"\n'
        '    version = "test/1.0"\n'
        '    supported_extensions = (".tie",)\n'
        "    priority = 7\n"
        '    source_types = ("text",)\n'
        '    locator_family = "line_address"\n'
        "\n"
        "    def parse(self, path, source_hash):\n"
        "        raise NotImplementedError\n"
    )


def _write_plugin(directory: Path, mod_name: str, source: str) -> str:
    (directory / f"{mod_name}.py").write_text(source, encoding="utf-8")
    return mod_name


@pytest.fixture
def plugin_env(tmp_path: Path, monkeypatch):
    """sys.path 注入 + 注册表副本隔离 + 首载备忘重置 + 模块 sys.modules 清理。"""
    monkeypatch.syspath_prepend(str(tmp_path))
    import app.parser_registry as pr
    from app import plugin_loader as pl

    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pl, "_FIRST_LOAD", {})
    yield tmp_path
    for key, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and str(tmp_path) in str(f):
            del sys.modules[key]


# ---------- load_plugins 基础 ----------

def test_load_plugins_returns_parsers_added(plugin_env: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    out = load_plugins(["myx_mod"])
    assert out == [{"plugin": "myx_mod", "parsers_added": ["myx_test"]}]


def test_load_plugins_repeat_module_returns_first_increment(plugin_env: Path):
    """封口修正：重复加载返回首次真实增量（事件不得恒为空），且不重复注册。"""
    import app.parser_registry as pr

    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    first = load_plugins(["myx_mod"])
    n_after_first = len(pr._registry)
    second = load_plugins(["myx_mod"])
    assert first == second == [
        {"plugin": "myx_mod", "parsers_added": ["myx_test"]}
    ]
    assert len(pr._registry) == n_after_first  # 幂等：无二次注册


def test_load_plugins_missing_module(plugin_env: Path):
    with pytest.raises(PluginLoadError) as ei:
        load_plugins(["definitely_missing_module_zzz9"])
    e = ei.value
    assert e.code == "plugin_import_failed"
    assert e.plugin == "definitely_missing_module_zzz9"
    assert e.error_type == "ModuleNotFoundError"
    d = e.to_dict()
    assert d["code"] == "plugin_import_failed" and "message" in d
    assert "traceback" not in d  # 标准 JSON 不含 traceback（裁决 D4）
    assert "traceback" in e.to_dict(include_traceback=True)


def test_load_plugins_name_conflict_register_failed(plugin_env: Path):
    _write_plugin(plugin_env, "clash_mod", _PLUGIN_CLASH)
    with pytest.raises(PluginLoadError) as ei:
        load_plugins(["clash_mod"])
    assert ei.value.code == "plugin_register_failed"
    assert ei.value.plugin == "clash_mod"
    assert ei.value.error_type == "ParserRegistrationError"
    assert "重名注册" in ei.value.error_message


def test_load_plugins_syntax_error_import_failed(plugin_env: Path):
    _write_plugin(plugin_env, "syntax_mod", _PLUGIN_SYNTAX_ERROR)
    with pytest.raises(PluginLoadError) as ei:
        load_plugins(["syntax_mod"])
    assert ei.value.code == "plugin_import_failed"
    assert ei.value.error_type == "SyntaxError"


def test_load_plugins_toplevel_valueerror_import_failed(plugin_env: Path):
    """裁决补充项：顶层普通 ValueError 归 plugin_import_failed 而非注册冲突。"""
    _write_plugin(plugin_env, "ve_mod", _PLUGIN_TOPLEVEL_VALUEERROR)
    with pytest.raises(PluginLoadError) as ei:
        load_plugins(["ve_mod"])
    assert ei.value.code == "plugin_import_failed"
    assert ei.value.error_type == "ValueError"


def test_load_plugins_order_defines_first_registered(plugin_env: Path):
    _write_plugin(plugin_env, "tie_a_mod", _tie_plugin("tie_a"))
    _write_plugin(plugin_env, "tie_b_mod", _tie_plugin("tie_b"))
    load_plugins(["tie_a_mod", "tie_b_mod"])
    with pytest.warns(UserWarning, match="同优先级"):
        assert discover_parser("x.tie") == "tie_a"


def test_load_plugins_fail_fast_stops_at_first_failure(plugin_env: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    with pytest.raises(PluginLoadError):
        load_plugins(["definitely_missing_module_zzz9", "myx_mod"])
    import app.parser_registry as pr

    assert "myx_test" not in pr._registry  # 后续模块未加载


# ---------- CLI parse ----------

def test_cli_parse_explicit_external_plugin(plugin_env: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    f = plugin_env / "a.myx"
    f.write_text("第一段\n\n第二段 MARK19\n", encoding="utf-8")
    out = plugin_env / "a.json"
    rc = app_main(
        ["parse", str(f), "-o", str(out), "--plugin", "myx_mod", "--parser", "myx_test"]
    )
    assert rc == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["parser_name"] == "myx_test"
    assert d["metadata"]["myx"] is True
    assert any("MARK19" in e["content"] for e in d["elements"])


def test_cli_parse_auto_routes_to_external_plugin(plugin_env: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    f = plugin_env / "b.myx"
    f.write_text("auto 路由\n", encoding="utf-8")
    out = plugin_env / "b.json"
    rc = app_main(
        ["parse", str(f), "-o", str(out), "--plugin", "myx_mod", "--parser", "auto"]
    )
    assert rc == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["parser_name"] == "myx_test"


def test_cli_plugin_load_failure_structured(plugin_env: Path, capfd):
    f = plugin_env / "c.myx"
    f.write_text("x", encoding="utf-8")
    rc = app_main(
        ["parse", str(f), "-o", str(plugin_env / "c.json"),
         "--plugin", "definitely_missing_module_zzz9", "--parser", "myx_test"]
    )
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "plugin_import_failed"
    assert err["errors"][0]["plugin"] == "definitely_missing_module_zzz9"
    assert "traceback" not in err["errors"][0]
    assert not (plugin_env / "c.json").exists()


def test_cli_plugin_conflict_structured(plugin_env: Path, capfd):
    _write_plugin(plugin_env, "clash_mod", _PLUGIN_CLASH)
    f = plugin_env / "d.myx"
    f.write_text("x", encoding="utf-8")
    rc = app_main(
        ["parse", str(f), "-o", str(plugin_env / "d.json"), "--plugin", "clash_mod"]
    )
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "plugin_register_failed"
    assert err["errors"][0]["plugin"] == "clash_mod"


# ---------- 动态校验（裁决 D6） ----------

def test_cli_unknown_parser_structured_rc1(plugin_env: Path, capfd):
    f = plugin_env / "e.md"
    f.write_text("# T\n\n正文\n", encoding="utf-8")
    rc = app_main(["parse", str(f), "-o", str(plugin_env / "e.json"), "--parser", "nope"])
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "unknown_parser"


def test_cli_external_parser_name_requires_plugin(plugin_env: Path, capfd):
    """插件名在未加载插件时同样是 unknown_parser（加载后才可校验通过）。"""
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    f = plugin_env / "f.myx"
    f.write_text("x", encoding="utf-8")
    rc = app_main(["parse", str(f), "-o", str(plugin_env / "f.json"), "--parser", "myx_test"])
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "unknown_parser"


def test_cli_plugin_load_precedes_parser_validation(plugin_env: Path, capfd):
    """--plugin 失败优先于 unknown_parser（插件加载先于名称校验）。"""
    f = plugin_env / "g.md"
    f.write_text("x", encoding="utf-8")
    rc = app_main(
        ["parse", str(f), "-o", str(plugin_env / "g.json"),
         "--parser", "nope", "--plugin", "definitely_missing_module_zzz9"]
    )
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "plugin_import_failed"


def test_cli_parse_auto_without_plugin_unchanged(plugin_env: Path):
    f = plugin_env / "h.md"
    f.write_text("# 标题\n\n正文\n", encoding="utf-8")
    out = plugin_env / "h.json"
    assert app_main(["parse", str(f), "-o", str(out), "--parser", "auto"]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["parser_name"] == "markdown_enhanced"


# ---------- list-parsers ----------

def test_cli_list_parsers_with_plugin(plugin_env: Path, capfd):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    rc = app_main(["list-parsers", "--plugin", "myx_mod"])
    assert rc == 0
    out = capfd.readouterr().out
    assert "myx_test" in out and ".myx" in out


def test_cli_list_parsers_plugin_failure(plugin_env: Path, capfd):
    rc = app_main(["list-parsers", "--plugin", "definitely_missing_module_zzz9"])
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "plugin_import_failed"


# ---------- batch：父进程 fail-fast 与两条路径 ----------

def _write_docs(directory: Path, n: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (directory / f"doc{i}.md").write_text(f"# 文档{i}\n\n正文{i}\n", encoding="utf-8")
    return directory


def test_batch_parent_load_failure_no_pool(plugin_env: Path, capfd):
    docs = _write_docs(plugin_env / "docs", 3)
    out = plugin_env / "out"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out),
         "--plugin", "definitely_missing_module_zzz9", "--workers", "2"]
    )
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "plugin_import_failed"
    assert not (out / "summary.json").exists()  # 未启动批处理，无 summary


def test_batch_sequential_with_plugins(plugin_env: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    docs = _write_docs(plugin_env / "docs", 1)
    out = plugin_env / "out"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--plugin", "myx_mod"]
    )
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 1 and summary["failed"] == 0


def test_batch_parallel_with_plugins_jsonl(plugin_env: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    docs = _write_docs(plugin_env / "docs", 3)
    out = plugin_env / "out"
    log = plugin_env / "batch.jsonl"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--plugin", "myx_mod",
         "--workers", "2", "--log-file", str(log)]
    )
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 3 and summary["failed"] == 0

    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    by_event: dict[str, list[dict]] = {}
    for ev in events:
        by_event.setdefault(ev["event"], []).append(ev)
    plugin_events = by_event["plugin_loaded"]
    # 封口修正断言（裁决要求）：CLI 流程下事件含首次加载的真实 parser 名单；
    # batch_start.plugins 保留输入模块列表
    assert len(plugin_events) == 1
    assert plugin_events[0]["plugin"] == "myx_mod"
    assert plugin_events[0]["parsers_added"] == ["myx_test"]
    assert by_event["batch_start"][0]["plugins"] == ["myx_mod"]
    assert len(by_event["file_complete"]) == 3
    assert by_event["batch_complete"][0]["success"] == 3


def test_batch_duplicate_plugin_spec_single_event(plugin_env: Path):
    """重复 --plugin 同一模块：只发一次命令级 plugin_loaded 事件。"""
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    docs = _write_docs(plugin_env / "docs", 1)
    out = plugin_env / "out"
    log = plugin_env / "dup.jsonl"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out),
         "--plugin", "myx_mod", "--plugin", "myx_mod", "--log-file", str(log)]
    )
    assert rc == 0
    events = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    loaded = [e for e in events if e["event"] == "plugin_loaded"]
    assert len(loaded) == 1
    assert loaded[0]["plugin"] == "myx_mod"
    start = next(e for e in events if e["event"] == "batch_start")
    assert start["plugins"] == ["myx_mod", "myx_mod"]  # 保留原始输入列表


_PLUGIN_NO_REGISTER = "X = 1\n"


def test_batch_plugin_registering_nothing_empty_added(plugin_env: Path):
    """真实幂等为空：模块本身不注册任何 parser 时 parsers_added 为空表。"""
    _write_plugin(plugin_env, "noop_mod", _PLUGIN_NO_REGISTER)
    docs = _write_docs(plugin_env / "docs", 1)
    out = plugin_env / "out"
    log = plugin_env / "noop.jsonl"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--plugin", "noop_mod",
         "--log-file", str(log)]
    )
    assert rc == 0
    events = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    loaded = [e for e in events if e["event"] == "plugin_loaded"]
    assert len(loaded) == 1
    assert loaded[0]["plugin"] == "noop_mod"
    assert loaded[0]["parsers_added"] == []


def test_batch_parallel_worker_init_failure_controlled(plugin_env: Path, capfd):
    """真实跨进程：父进程加载成功（缓存命中），worker 侧导入失败 →
    受控通道结构化返回，池被回收，无 summary、无原始 traceback 上抛。"""
    _write_plugin(plugin_env, "sentinel_mod", _PLUGIN_SENTINEL)
    load_plugins(["sentinel_mod"])  # 父进程先加载成功（模块体缓存）
    (plugin_env / "sentinel_on.txt").write_text("on", encoding="utf-8")

    docs = _write_docs(plugin_env / "docs2", 3)
    out = plugin_env / "out2"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out),
         "--plugin", "sentinel_mod", "--workers", "2"]
    )
    assert rc == 1
    err_text = capfd.readouterr().err
    assert '"code": "plugin_import_failed"' in err_text
    assert '"plugin": "sentinel_mod"' in err_text
    assert "worker-only plugin failure" in err_text
    assert not (out / "summary.json").exists()
    # 原始 traceback 不进结构化 JSON（worker 内部细节已封装为错误字段）
    assert '"traceback"' not in err_text


# ---------- worker 函数单元（受控通道与背板） ----------

class _FakeQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def test_worker_init_plugins_catches_and_reports(monkeypatch):
    monkeypatch.setattr(batch_mod, "_WORKER_PLUGIN_ERROR", None)

    def _boom(modules):
        raise PluginLoadError(
            "plugin_register_failed", "m", "ParserRegistrationError", "重名"
        )

    monkeypatch.setattr(batch_mod, "load_plugins", _boom)
    q = _FakeQueue()
    batch_mod._worker_init_plugins(("m",), q)
    assert batch_mod._WORKER_PLUGIN_ERROR is not None
    assert batch_mod._WORKER_PLUGIN_ERROR["code"] == "plugin_register_failed"
    assert q.items and q.items[0]["ok"] is False
    assert q.items[0]["plugin"] == "m"


def test_worker_init_plugins_success_reports_ok(monkeypatch):
    monkeypatch.setattr(batch_mod, "_WORKER_PLUGIN_ERROR", None)
    monkeypatch.setattr(batch_mod, "load_plugins", lambda modules: [])
    q = _FakeQueue()
    batch_mod._worker_init_plugins(("m",), q)
    assert batch_mod._WORKER_PLUGIN_ERROR is None
    assert q.items == [{"ok": True}]


def test_parse_one_file_backstop(plugin_env: Path, monkeypatch):
    monkeypatch.setattr(
        batch_mod,
        "_WORKER_PLUGIN_ERROR",
        {"code": "plugin_import_failed", "message": "worker 侧插件失败"},
    )
    r = batch_mod.parse_one_file(("whatever.md", str(plugin_env), "markdown", 800))
    assert r["success"] is False
    assert r["error_code"] == "plugin_import_failed"
    assert r["traceback"] is None


# ---------- validate 不变 ----------

def test_validate_has_no_plugin_flag(plugin_env: Path):
    f = plugin_env / "v.json"
    f.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        app_main(["validate", str(f), "--plugin", "some_mod"])
    assert ei.value.code == 2  # argparse：无此选项（validate 不参与插件机制）
