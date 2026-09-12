"""Stage 10 批次 5 测试：--plugin .py 文件路径加载（r43 授权）。

覆盖裁决要求：成功路径（绝对/相对/cwd 裸文件名）/ 缺失文件 /
导入失败沿用既有错误码 / 注册冲突沿用既有错误码 / 命名冲突
（同 stem 不同文件 + stdlib shadow）/ sys.path 状态恢复（成功与
失败）/ dotted 行为不变边界 / provenance 冻结原始路径拼写 /
CLI 端到端（parse/list-parsers/inspect-parser）/ 批量父进程
fail-fast 与并行 worker 路径重放。全部合成夹具，零真实语料。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import app.parser_registry as pr
from app.cli import main as app_main
from app.parser_registry import capability, discover_parser
from app.plugin_loader import PluginLoadError, load_plugins

# 与批次 19 的 myx_test 插件同构，但 parser 名独立（避免跨测试串扰）
_PLUGIN_PATH_MYX = r'''
from pathlib import Path

from app.models import Document, Element, WarningRecord
from app.parser_registry import register
from app.parsers.base import Parser, make_document_id


@register
class MyxPathParser(Parser):
    name = "myx_path"
    version = "test/1.0"
    supported_extensions = (".myx",)
    priority = 1
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        document_id = make_document_id(source_hash)
        elements = [
            Element(
                element_id=f"{document_id}::e{i:04d}",
                type="paragraph",
                content=seg.strip(),
                parent_id=None,
                source_locator={"family": "line_address", "line": 1},
                confidence=0.95,
                metadata={},
            )
            for i, seg in enumerate(s for s in text.split("\n\n") if s.strip())
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
            warnings=[],
            errors=[],
            metadata={"myx_path": True},
        )
'''

_PLUGIN_PATH_CLASH = r'''
from app.parser_registry import register
from app.parsers.base import Parser


@register
class ClashPathParser(Parser):
    name = "fallback"
    version = "test/1.0"
    supported_extensions = (".clash",)
    priority = 1

    def parse(self, path, source_hash):
        raise NotImplementedError
'''


@pytest.fixture
def path_env(tmp_path: Path, monkeypatch):
    """注册表副本隔离 + 首载备忘重置 + 模块 sys.modules 清理。

    刻意**不**把 tmp_path 注入 sys.path：路径加载不依赖 PYTHONPATH，
    夹具的独立性本身即断言（dotted 加载才需要 sys.path）。
    """
    from app import plugin_loader as pl

    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    # 序免疫：能力快照只保留 builtin 基线——其他套件若泄漏插件快照
    #（如 myx_test 的 .myx 同优先级条目），不得到达本文件的平局判定
    monkeypatch.setattr(
        pr,
        "_capabilities",
        {n: c for n, c in pr._capabilities.items() if c.loaded_via == "builtin"},
    )
    monkeypatch.setattr(pl, "_FIRST_LOAD", {})
    yield tmp_path
    for key, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and str(tmp_path) in str(f):
            del sys.modules[key]


def _write(directory: Path, name: str, source: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(source, encoding="utf-8")
    return p


# ---------- 解析与成功路径 ----------

def test_path_spec_absolute_success(path_env: Path):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    out = load_plugins([str(f)])
    assert out == [{"plugin": str(f), "parsers_added": ["myx_path"]}]
    assert discover_parser("x.myx") == "myx_path"


def test_path_spec_relative_from_cwd(path_env: Path, monkeypatch):
    _write(path_env / "plugins", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    monkeypatch.chdir(path_env)
    out = load_plugins(["plugins/myx_path_mod.py"])
    assert out[0]["plugin"] == "plugins/myx_path_mod.py"
    assert out[0]["parsers_added"] == ["myx_path"]


def test_bare_py_filename_is_path_spec(path_env: Path, monkeypatch):
    """裸 "foo.py"（无分隔符）按路径处理：历史上是非法模块名必失败，
    现在解析为 cwd 下文件——错误码从 plugin_import_failed 迁移的边界件。"""
    _write(path_env, "myx_path_mod.py", _PLUGIN_PATH_MYX)
    monkeypatch.chdir(path_env)
    out = load_plugins(["myx_path_mod.py"])
    assert out[0]["parsers_added"] == ["myx_path"]


def test_windows_separator_path_spec(path_env: Path, monkeypatch):
    _write(path_env / "plugins", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    monkeypatch.chdir(path_env)
    out = load_plugins(["plugins\\myx_path_mod.py"])
    assert out[0]["parsers_added"] == ["myx_path"]


# ---------- 路径错误码 ----------

def test_missing_file_not_found(path_env: Path):
    spec = str(path_env / "no_such" / "plugin.py")
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([spec])
    e = ei.value
    assert e.code == "plugin_path_not_found"
    assert e.plugin == spec
    assert e.error_type == "PluginPathNotFound"
    d = e.to_dict()
    assert d["code"] == "plugin_path_not_found"
    assert "traceback" not in d


def test_not_py_suffix_invalid(path_env: Path):
    f = _write(path_env, "plugin.txt", "X = 1\n")
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(f)])
    assert ei.value.code == "plugin_path_invalid"
    assert ei.value.error_type == "PluginPathInvalid"


def test_directory_with_py_name_invalid(path_env: Path):
    d = path_env / "weird.py"
    d.mkdir()
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(d)])
    assert ei.value.code == "plugin_path_invalid"


def test_stem_not_identifier_invalid(path_env: Path):
    f = _write(path_env, "my-plugin.py", "X = 1\n")
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(f)])
    assert ei.value.code == "plugin_path_invalid"
    assert "stem" in ei.value.error_message


def test_syntax_error_maps_to_import_failed(path_env: Path):
    f = _write(path_env / "plug", "bad_syntax.py", "def broken(:\n")
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(f)])
    assert ei.value.code == "plugin_import_failed"
    assert ei.value.error_type == "SyntaxError"
    assert ei.value.plugin == str(f)


def test_register_conflict_maps_to_register_failed(path_env: Path):
    f = _write(path_env / "plug", "clash_mod.py", _PLUGIN_PATH_CLASH)
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(f)])
    assert ei.value.code == "plugin_register_failed"
    assert ei.value.error_type == "ParserRegistrationError"


# ---------- 命名冲突与幂等 ----------

def test_same_stem_different_file_conflict(path_env: Path):
    a = _write(path_env / "dirA", "same_stem.py", _PLUGIN_PATH_MYX)
    b = _write(path_env / "dirB", "same_stem.py", _PLUGIN_PATH_MYX)
    load_plugins([str(a)])
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(b)])
    e = ei.value
    assert e.code == "plugin_path_conflict"
    assert e.error_type == "PluginPathConflict"
    assert "same_stem" in e.error_message
    assert e.plugin == str(b)


def test_stdlib_name_shadow_conflict(path_env: Path):
    """json.py：模块名被标准库占用（__file__ 不同）→ 保守拒绝；
    同时证明注入策略不会 shadow 标准库。"""
    f = _write(path_env, "json.py", "X = 1\n")
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(f)])
    assert ei.value.code == "plugin_path_conflict"
    import json as real_json

    assert real_json.__file__ is not None


def test_same_file_two_spellings_idempotent(path_env: Path, monkeypatch):
    """不同拼写指向同一文件：第二次走 sys.modules 同文件命中，不重复
    执行注册（parsers_added 为空）；registry 计数不变。"""
    _write(path_env / "plugins", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    monkeypatch.chdir(path_env)
    first = load_plugins(["plugins/myx_path_mod.py"])
    assert first[0]["parsers_added"] == ["myx_path"]
    n_reg = len(pr._registry)
    second = load_plugins([str((path_env / "plugins" / "myx_path_mod.py").resolve())])
    assert second[0]["parsers_added"] == []
    assert second[0]["plugin"] == str((path_env / "plugins" / "myx_path_mod.py").resolve())
    assert len(pr._registry) == n_reg


def test_repeated_same_path_spec_returns_first_increment(path_env: Path):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    first = load_plugins([str(f)])
    n_reg = len(pr._registry)
    second = load_plugins([str(f)])
    assert first == second
    assert len(pr._registry) == n_reg


# ---------- sys.path 状态恢复 ----------

def test_sys_path_restored_success_and_failure(path_env: Path):
    ok = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    bad = _write(path_env / "plug", "bad_syntax.py", "def broken(:\n")
    missing = str(path_env / "nope.py")

    snapshot = list(sys.path)
    load_plugins([str(ok)])
    assert sys.path == snapshot
    with pytest.raises(PluginLoadError):
        load_plugins([str(bad)])
    assert sys.path == snapshot
    with pytest.raises(PluginLoadError):
        load_plugins([missing])
    assert sys.path == snapshot
    conflict_b = _write(path_env / "dirB", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    with pytest.raises(PluginLoadError):
        load_plugins([str(conflict_b)])  # 与 ok 同 stem 不同文件
    assert sys.path == snapshot


# ---------- dotted 行为不变边界 ----------

def test_dotted_without_separator_still_module_channel(path_env: Path):
    """无分隔符且不以 .py 结尾的 spec 仍走 dotted 通道：缺失模块报
    ModuleNotFoundError（而非 plugin_path_not_found）——判定边界锁定。"""
    with pytest.raises(PluginLoadError) as ei:
        load_plugins(["definitely_missing_module_zzz9"])
    assert ei.value.code == "plugin_import_failed"
    assert ei.value.error_type == "ModuleNotFoundError"


# ---------- provenance（批次 24 契约在路径形态上的延续） ----------

def test_provenance_freezes_original_path_spelling(path_env: Path, monkeypatch):
    _write(path_env / "plugins", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    monkeypatch.chdir(path_env)
    load_plugins(["plugins/myx_path_mod.py"])
    cap = capability("myx_path")
    assert cap.loaded_via == "plugin"
    assert cap.plugin_spec == "plugins/myx_path_mod.py"  # 原始拼写，非 resolved


# ---------- CLI 端到端 ----------

def test_cli_parse_with_plugin_path(path_env: Path):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    doc = _write(path_env, "a.myx", "第一段\n\n第二段 MARK25\n")
    out = path_env / "a.json"
    rc = app_main(
        ["parse", str(doc), "-o", str(out), "--plugin", str(f), "--parser", "myx_path"]
    )
    assert rc == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["parser_name"] == "myx_path"
    assert d["metadata"]["myx_path"] is True
    assert any("MARK25" in e["content"] for e in d["elements"])


def test_cli_parse_auto_routes_path_plugin(path_env: Path):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    doc = _write(path_env, "b.myx", "auto 路径插件\n")
    out = path_env / "b.json"
    rc = app_main(
        ["parse", str(doc), "-o", str(out), "--plugin", str(f), "--parser", "auto"]
    )
    assert rc == 0
    assert json.loads(out.read_text(encoding="utf-8"))["parser_name"] == "myx_path"


def test_cli_missing_path_structured(path_env: Path, capfd):
    doc = _write(path_env, "c.md", "x\n")
    spec = str(path_env / "no" / "such.py")
    rc = app_main(
        ["parse", str(doc), "-o", str(path_env / "c.json"), "--plugin", spec]
    )
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "plugin_path_not_found"
    assert err["errors"][0]["plugin"] == spec
    assert "traceback" not in err["errors"][0]
    assert not (path_env / "c.json").exists()


def test_cli_list_parsers_with_plugin_path(path_env: Path, capfd):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    rc = app_main(["list-parsers", "--plugin", str(f)])
    assert rc == 0
    out = capfd.readouterr().out
    assert "myx_path" in out and ".myx" in out


def test_cli_inspect_parser_shows_path_spec(path_env: Path, capfd):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    rc = app_main(["inspect-parser", "myx_path", "--plugin", str(f), "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload["loaded_via"] == "plugin"
    assert payload["plugin_spec"] == str(f)
    assert payload["name"] == "myx_path"


def test_cli_explain_parser_with_plugin_path(path_env: Path, capfd):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    rc = app_main(["explain-parser", "doc.myx", "--plugin", str(f), "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert payload["winner"] == "myx_path"
    assert payload["extension"] == ".myx"


# ---------- 批量：父进程 fail-fast 与并行 worker 重放 ----------

def _write_md_docs(directory: Path, n: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (directory / f"doc{i}.md").write_text(f"# 文档{i}\n\n正文{i}\n", encoding="utf-8")
    return directory


def test_batch_parent_path_failure_no_pool(path_env: Path, capfd):
    docs = _write_md_docs(path_env / "docs", 3)
    spec = str(path_env / "no" / "such.py")
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(path_env / "out"),
         "--plugin", spec, "--workers", "2"]
    )
    assert rc == 1
    err = json.loads(capfd.readouterr().err)
    assert err["errors"][0]["code"] == "plugin_path_not_found"
    assert not (path_env / "out" / "summary.json").exists()


def test_batch_sequential_with_path_plugin(path_env: Path):
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    docs = _write_md_docs(path_env / "docs", 1)
    out = path_env / "out"
    rc = app_main(["batch-parse", str(docs), "-o", str(out), "--plugin", str(f)])
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 1 and summary["failed"] == 0


def test_batch_parallel_path_plugin_jsonl(path_env: Path):
    """spawn worker 内真实路径重放：worker sys.modules 全新，必须凭
    spec 重新 resolve + import；事件通道 plugin_loaded.plugin = 路径 spec。"""
    f = _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    docs = _write_md_docs(path_env / "docs", 3)
    out = path_env / "out"
    log = path_env / "batch.jsonl"
    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--plugin", str(f),
         "--workers", "2", "--log-file", str(log)]
    )
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 3 and summary["failed"] == 0
    events = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    by_event: dict[str, list[dict]] = {}
    for ev in events:
        by_event.setdefault(ev["event"], []).append(ev)
    loaded = by_event["plugin_loaded"]
    assert len(loaded) == 1
    assert loaded[0]["plugin"] == str(f)
    assert loaded[0]["parsers_added"] == ["myx_path"]
    assert by_event["batch_start"][0]["plugins"] == [str(f)]
    assert len(by_event["file_complete"]) == 3


def test_mixed_specs_fail_fast(path_env: Path):
    """dotted 与路径混合列表：首个失败中止，后续不加载（fail-fast 不变）。"""
    _write(path_env / "plug", "myx_path_mod.py", _PLUGIN_PATH_MYX)
    with pytest.raises(PluginLoadError) as ei:
        load_plugins([str(path_env / "nope.py"), "myx_path_mod"])
    assert ei.value.code == "plugin_path_not_found"
    assert "myx_path" not in pr._registry
