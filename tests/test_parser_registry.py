"""批次 18 测试：Parser 插件化与扩展接口（Option B 裁决）。

覆盖裁决要求的 7 类：自动发现 / 优先级平局 / 重名注册失败 /
--parser auto / 默认 fallback 不变 / frontmatter 降级 warning /
外部显式注册；另含注册表基础与 CLI list-parsers。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.parser_registry as pr
from app.batch import effective_parser_for
from app.cli import main as app_main
from app.parser_registry import (
    discover_parser,
    get_parser,
    list_parsers,
    register,
)
from app.parsers.base import Parser
from app.parsers.fallback_parser import FallbackParser
from app.parsers.markdown_parser import MarkdownParser
from app.pipeline import get_parser as pipeline_get_parser


def _write_md(directory: Path, name: str, text: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def fresh_registry(monkeypatch):
    """隔离的全局注册表副本：测试内注册不污染其他测试。"""
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    return pr._registry


# ---------- 注册表基础 ----------

def test_builtin_parsers_registered_with_metadata():
    rows = {r["name"]: r for r in list_parsers()}
    assert set(rows) >= {
        "fallback",
        "kreuzberg",
        "markdown",
        "html",
        "text",
        "ipynb",
        "markdown_enhanced",
    }
    assert rows["fallback"]["extensions"] == [".pdf", ".docx"]
    assert rows["markdown"]["priority"] == 20
    assert rows["markdown_enhanced"]["priority"] == 5


def test_get_parser_unknown_name_value_error():
    with pytest.raises(ValueError, match="未知 parser"):
        get_parser("no_such_parser")


def test_get_parser_fallback_image_output_dir(tmp_path: Path):
    p = get_parser("fallback", image_output_dir=tmp_path)
    assert isinstance(p, FallbackParser)
    assert isinstance(get_parser("markdown"), MarkdownParser)


def test_pipeline_get_parser_delegates_to_registry():
    assert isinstance(pipeline_get_parser("markdown"), MarkdownParser)
    with pytest.raises(ValueError, match="未知 parser"):
        pipeline_get_parser("nope")


# ---------- 裁决 1：自动发现（扩展名 + priority 最小者） ----------

def test_discover_by_extension_priority():
    assert discover_parser("x.md") == "markdown_enhanced"  # 5 < 20
    assert discover_parser("x.markdown") == "markdown_enhanced"
    assert discover_parser("x.pdf") == "fallback"  # 10 < 50
    assert discover_parser("x.docx") == "fallback"
    assert discover_parser("x.html") == "html"
    assert discover_parser("x.txt") == "text"


def test_discover_no_candidate_value_error():
    with pytest.raises(ValueError, match="无已注册 parser"):
        discover_parser("x.zzz9")


# ---------- 裁决 2：优先级平局 → 先注册者胜 + warning ----------

def _make_parser_cls(name: str, exts: tuple, priority: int) -> type[Parser]:
    class _P(Parser):
        def parse(self, path, source_hash):  # pragma: no cover - 测试桩
            raise NotImplementedError

    _P.name = name
    _P.supported_extensions = exts
    _P.priority = priority
    # 批次 20：契约声明强制——测试桩统一声明 text/line_address
    _P.source_types = ("text",)
    _P.locator_family = "line_address"
    return _P


def test_priority_tie_first_registered_wins_with_warning(fresh_registry):
    first = _make_parser_cls("tie_first", (".tie",), 7)
    second = _make_parser_cls("tie_second", (".tie",), 7)
    register(first)
    register(second)
    with pytest.warns(UserWarning, match="同优先级"):
        assert discover_parser("a.tie") == "tie_first"


# ---------- 裁决 3：重名注册失败 ----------

def test_duplicate_registration_raises(fresh_registry):
    register(_make_parser_cls("dup_me", (".dup",), 30))
    with pytest.raises(ValueError, match="重名注册: dup_me"):
        register(_make_parser_cls("dup_me", (".dup2",), 31))


def test_register_requires_real_name(fresh_registry):
    with pytest.raises(ValueError, match="name"):
        register(_make_parser_cls("abstract", (), 100))


# ---------- 裁决 7 + 外部注册：外部显式注册（import + @register 同款） ----------

def test_external_explicit_registration_visible_everywhere(fresh_registry):
    @register
    class _External(_make_parser_cls("external_test", (".ext9",), 1)):
        pass

    assert discover_parser("anything.ext9") == "external_test"
    assert isinstance(get_parser("external_test"), _External)
    assert "external_test" in {r["name"] for r in list_parsers()}


# ---------- 裁决 4：--parser auto（CLI 单文件 + batch 路由） ----------

def test_cli_parse_auto_resolves_md_to_enhanced(tmp_path: Path):
    f = _write_md(
        tmp_path, "a.md", "---\ntitle: T\n---\n\n# H1\n\n正文 MARKAUTO\n"
    )
    out = tmp_path / "a.json"
    rc = app_main(["parse", str(f), "-o", str(out), "--parser", "auto"])
    assert rc == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["parser_name"] == "markdown_enhanced"
    assert d["metadata"]["title"] == "T"
    assert "MARKAUTO" in json.dumps(d, ensure_ascii=False)


def test_cli_parse_auto_unsupported_extension_rc1(tmp_path: Path):
    f = tmp_path / "b.zzz9"
    f.write_text("x", encoding="utf-8")
    rc = app_main(["parse", str(f), "-o", str(tmp_path / "b.json"), "--parser", "auto"])
    assert rc == 1


def test_cli_default_parser_unchanged_md_fails_as_before(tmp_path: Path):
    """裁决 6(a)：默认 fallback 零变化——.md 不带 --parser 仍报 unsupported_type。"""
    f = _write_md(tmp_path, "c.md", "# 标题\n\n正文\n")
    rc = app_main(["parse", str(f), "-o", str(tmp_path / "c.json")])
    assert rc == 1
    assert not (tmp_path / "c.json").exists()


def test_batch_effective_parser_auto_routing():
    assert effective_parser_for("auto", "x.md") == "markdown_enhanced"
    assert effective_parser_for("auto", Path("x.pdf")) == "fallback"
    assert effective_parser_for("auto", "x.docx") == "fallback"
    # 无候选 → 回落 fallback，由 worker 产出结构化 unsupported_type，不炸批
    assert effective_parser_for("auto", "x.zzz9") == "fallback"
    # 既有行为不变
    assert effective_parser_for("fallback", "x.md") == "markdown"
    assert effective_parser_for("markdown", "x.md") == "markdown"


def test_cli_batch_parse_auto(tmp_path: Path):
    _write_md(tmp_path / "docs", "d.md", "# 标题\n\n- [x] 完成\n")
    rc = app_main(
        [
            "batch-parse", str(tmp_path / "docs"), "-o", str(tmp_path / "out"),
            "--parser", "auto",
        ]
    )
    assert rc == 0
    d = json.loads(
        (tmp_path / "out" / "d.json").read_text(encoding="utf-8")
    )
    assert d["parser_name"] == "markdown_enhanced"


# ---------- 裁决 5：frontmatter 受限解析与降级 warning ----------

def test_frontmatter_flat_scalars_kept(tmp_path: Path):
    f = _write_md(
        tmp_path, "fm.md", '---\ntitle: 标题A\nauthor: "作者B"\nn: 42\n---\n\n# H\n\n正文。\n'
    )
    doc = get_parser("markdown_enhanced").parse(f, "a" * 64)
    assert doc.metadata["title"] == "标题A"
    assert doc.metadata["author"] == "作者B"  # 一层引号剥除
    assert doc.metadata["n"] == "42"  # 标量保持字符串（受限解析不猜类型）
    assert doc.metadata["markdown"] is True


def test_frontmatter_nested_and_list_skipped_with_warning(tmp_path: Path):
    f = _write_md(
        tmp_path,
        "fmbad.md",
        "---\ntitle: 好\ntags:\n  - a\n  - b\ninline: [1, 2]\nmap: {x: 1}\n---\n\n正文保留\n",
    )
    doc = get_parser("markdown_enhanced").parse(f, "b" * 64)
    assert doc.metadata["title"] == "好"
    assert "tags" not in doc.metadata and "inline" not in doc.metadata
    assert "map" not in doc.metadata
    codes = {w.code for w in doc.warnings}
    assert "frontmatter_value_skipped" in codes
    assert "frontmatter_line_skipped" in codes
    assert any("正文保留" == e.content for e in doc.elements)


def test_unclosed_frontmatter_not_treated_as_frontmatter(tmp_path: Path):
    f = _write_md(tmp_path, "unclosed.md", "---\ntitle: X\n\n# 不是 frontmatter\n")
    doc = get_parser("markdown_enhanced").parse(f, "c" * 64)
    assert "title" not in doc.metadata


# ---------- GFM 任务列表增强 ----------

def test_task_list_items_metadata(tmp_path: Path):
    f = _write_md(tmp_path, "task.md", "# T\n\n- [x] 完成\n- [ ] 待办\n- 普通项\n")
    doc = get_parser("markdown_enhanced").parse(f, "d" * 64)
    tasks = [e for e in doc.elements if e.metadata.get("task_item")]
    assert len(tasks) == 2
    assert tasks[0].content == "完成" and tasks[0].metadata["checked"] is True
    assert tasks[1].content == "待办" and tasks[1].metadata["checked"] is False
    plain = [e for e in doc.elements if e.type == "list_item" and not e.metadata.get("task_item")]
    assert [e.content for e in plain] == ["普通项"]


# ---------- CLI list-parsers ----------

def test_cli_list_parsers(tmp_path: Path, capfd):
    rc = app_main(["list-parsers"])
    assert rc == 0
    out = capfd.readouterr().out
    for name in ("fallback", "markdown", "markdown_enhanced", "priority"):
        assert name in out
