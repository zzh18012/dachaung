"""app.cli 端到端测试：聚焦 inspect 子命令（解析+校验子命令由 pipeline 集成测试覆盖）。

子进程跑真实 CLI 入口，验证退出码、stdout、stderr 的契约。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 在 pytest 内运行时（无 .venv）回退到当前 Python
_PYTHON = VENV_PYTHON if Path(VENV_PYTHON).is_file() else sys.executable


def _run_cli(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [_PYTHON, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd) if cwd else None,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _synthetic_document() -> dict:
    """最小合法文档 JSON（结构对齐 Document.to_dict，但不跑 schema 校验）。"""
    return {
        "schema_version": "0.1.0",
        "document_id": "d-test0000000001",
        "source_path": "/tmp/sample.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "test",
        "parser_version": "0",
        "elements": [
            {
                "element_id": "d-test0000000001::e0000",
                "type": "heading",
                "source_locator": {"paragraph_index": 0},
                "content": "Chapter One",
            },
            {
                "element_id": "d-test0000000001::e0001",
                "type": "paragraph",
                "source_locator": {"paragraph_index": 1},
                "content": "Hello world. This is the first paragraph.",
            },
            {
                "element_id": "d-test0000000001::e0002",
                "type": "paragraph",
                "source_locator": {"paragraph_index": 2},
                "content": "Second paragraph with more text.",
            },
        ],
        "chunks": [
            {
                "chunk_id": "d-test0000000001::c0000",
                "text": "Chapter One Hello world. This is the first paragraph.",
                "source_element_ids": [
                    "d-test0000000001::e0000",
                    "d-test0000000001::e0001",
                ],
                "metadata": {"char_count": 52, "strategy": "default"},
            },
            {
                "chunk_id": "d-test0000000001::c0001",
                "text": "Second paragraph with more text.",
                "source_element_ids": ["d-test0000000001::e0002"],
                "metadata": {"char_count": 33, "strategy": "default"},
            },
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


@pytest.fixture
def doc_json(tmp_path: Path) -> Path:
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_synthetic_document(), ensure_ascii=False), encoding="utf-8")
    return p


# ---- inspect: 摘要模式 ----


def test_inspect_summary_mode(doc_json: Path):
    rc, out, err = _run_cli(["inspect", str(doc_json)])
    assert rc == 0, f"stderr={err}"
    # 摘要关键字段都在
    assert "file:" in out
    assert "schema:" in out
    assert "document_id:" in out
    assert "source:" in out
    assert "parser:" in out
    assert "counts:" in out
    assert "elements by type:" in out
    # 计数正确
    assert "elements=3" in out
    assert "chunks=2" in out
    # element 类型计数
    assert "heading=1" in out
    assert "paragraph=2" in out
    # chunk 字符数统计
    assert "chunk text:" in out
    assert "chunk refs:" in out


def test_inspect_summary_shows_hash_truncation(doc_json: Path):
    rc, out, _ = _run_cli(["inspect", str(doc_json)])
    assert rc == 0
    # source_hash 截断为 16 字符 + 省略号
    assert "hash=" + "a" * 16 + "…" in out


# ---- inspect: --elements ----


def test_inspect_elements_flag(doc_json: Path):
    rc, out, err = _run_cli(["inspect", str(doc_json), "--elements"])
    assert rc == 0, f"stderr={err}"
    assert "elements (3):" in out
    # 每个 element 一行
    assert "heading" in out
    assert "paragraph" in out
    assert "::e0000" in out
    assert "::e0001" in out
    assert "::e0002" in out
    # 内容预览
    assert "Chapter One" in out
    assert "Hello world." in out


def test_inspect_elements_with_limit(doc_json: Path):
    rc, out, err = _run_cli(["inspect", str(doc_json), "--elements", "--limit", "2"])
    assert rc == 0, f"stderr={err}"
    # 限制 2 个 + more 提示（CLI 用 "+N more" 不带空格）
    assert "+1 more" in out
    assert "use --limit 0 to see all" in out


def test_inspect_elements_limit_zero_shows_all(doc_json: Path):
    rc, out, err = _run_cli(["inspect", str(doc_json), "--elements", "--limit", "0"])
    assert rc == 0, f"stderr={err}"
    # 全列，没有 more 提示
    assert "+1 more" not in out
    assert "::e0002" in out


# ---- inspect: --chunks ----


def test_inspect_chunks_flag(doc_json: Path):
    rc, out, err = _run_cli(["inspect", str(doc_json), "--chunks"])
    assert rc == 0, f"stderr={err}"
    assert "chunks (2):" in out
    assert "::c0000" in out
    assert "::c0001" in out
    # 字符数 / refs 数 / 预览
    assert "chars=" in out
    assert "refs=" in out


def test_inspect_chunks_with_limit(doc_json: Path):
    rc, out, err = _run_cli(["inspect", str(doc_json), "--chunks", "--limit", "1"])
    assert rc == 0, f"stderr={err}"
    assert "+1 more" in out


def test_inspect_chunks_spans_flag_without_spans_data(doc_json: Path):
    """合成 doc_json 不带 source_spans → --spans 显示 (none)。"""
    rc, out, err = _run_cli(["inspect", str(doc_json), "--chunks", "--spans"])
    assert rc == 0, f"stderr={err}"
    assert "span:" not in out  # 没有具体 span 行
    assert "spans: (none)" in out  # 每个 chunk 都标 (none)


def test_inspect_chunks_spans_flag_with_real_pipeline(tmp_path: Path):
    """跑真实 pipeline（带 source_spans）→ --spans 显示具体 span 行。"""
    src = tmp_path / "doc.md"
    src.write_text("# Title\n\nHello world paragraph.\n", encoding="utf-8")
    out_json = tmp_path / "out.json"
    rc, _, err = _run_cli(["parse", str(src), "-o", str(out_json)])
    assert rc == 0, f"stderr={err}"

    rc, out, err = _run_cli(["inspect", str(out_json), "--chunks", "--spans"])
    assert rc == 0, f"stderr={err}"
    # 至少有一个具体 span 行
    assert "span:" in out
    # span 行格式：span: <element_id>[<start>:<end>]
    assert "[0:" in out
    # 不应出现 (none)（pipeline 产出必带 spans）
    assert "spans: (none)" not in out


# ---- inspect: 组合 ----


def test_inspect_elements_and_chunks_combined(doc_json: Path):
    rc, out, err = _run_cli(
        ["inspect", str(doc_json), "--elements", "--chunks"]
    )
    assert rc == 0, f"stderr={err}"
    assert "elements (3):" in out
    assert "chunks (2):" in out


def test_inspect_limit_applies_to_both(doc_json: Path):
    rc, out, err = _run_cli(
        ["inspect", str(doc_json), "--elements", "--chunks", "--limit", "1"]
    )
    assert rc == 0, f"stderr={err}"
    # elements 截断（3 → 1，提示 +2 more）
    assert "+2 more" in out
    # chunks 截断（2 → 1，提示 +1 more）
    assert "+1 more" in out


# ---- inspect: 错误路径 ----


def test_inspect_missing_file(tmp_path: Path):
    missing = tmp_path / "nope.json"
    rc, out, err = _run_cli(["inspect", str(missing)])
    assert rc == 2
    assert "[ERROR] 文件不存在" in err
    assert str(missing) in err


def test_inspect_bad_json(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    rc, out, err = _run_cli(["inspect", str(bad)])
    assert rc == 1
    assert "[ERROR] JSON 解析失败" in err


def test_inspect_top_level_not_object(tmp_path: Path):
    # JSON 合法但顶层不是对象（例如数组）
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    rc, out, err = _run_cli(["inspect", str(arr)])
    assert rc == 1
    assert "JSON 顶层不是对象" in err


# ---- inspect: 边界 ----


def test_inspect_empty_document(tmp_path: Path):
    """空文档（无 elements/chunks）也能 inspect，不出错。"""
    empty = {
        "schema_version": "0.1.0",
        "document_id": "d-empty",
        "source_path": "/tmp/empty.docx",
        "source_type": "docx",
        "source_hash": "b" * 64,
        "parser_name": "test",
        "parser_version": "0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "empty.json"
    p.write_text(json.dumps(empty), encoding="utf-8")
    rc, out, err = _run_cli(["inspect", str(p), "--elements", "--chunks"])
    assert rc == 0, f"stderr={err}"
    assert "elements=0" in out
    assert "chunks=0" in out
    assert "elements (0):" in out
    assert "chunks (0):" in out


def test_inspect_preview_collapses_whitespace(tmp_path: Path):
    """_preview 把换行/多空格压成单空格，并在超长时加省略号。"""
    long_text = "word " * 30  # 150 字符，含尾空格
    doc = _synthetic_document()
    doc["elements"][0]["content"] = long_text
    p = tmp_path / "long.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    rc, out, err = _run_cli(["inspect", str(p), "--elements", "--limit", "1"])
    assert rc == 0, f"stderr={err}"
    # 预览末尾有省略号
    assert "…" in out


# ---- parse 子命令：parser 自动推断 ----


def test_infer_parser_by_extension():
    """_infer_parser_name 按扩展名映射正确。"""
    from app.cli import _infer_parser_name
    cases = {
        "doc.pdf": "fallback",
        "doc.docx": "fallback",
        "doc.md": "markdown",
        "doc.markdown": "markdown",
        "doc.html": "html",
        "doc.htm": "html",
        "doc.txt": "text",
        "doc.text": "text",
        "doc.ipynb": "ipynb",
        # 未知扩展名回退
        "doc.unknown": "fallback",
        "noext": "fallback",
    }
    for name, expected in cases.items():
        assert _infer_parser_name(Path(name)) == expected, f"{name} → {expected}"


def test_parse_auto_infers_markdown(tmp_path: Path):
    """不带 --parser 时，.md 文件自动用 markdown parser。"""
    src = tmp_path / "doc.md"
    src.write_text("# Title\n\nHello.\n", encoding="utf-8")
    out = tmp_path / "out.json"
    rc, stdout, stderr = _run_cli(["parse", str(src), "-o", str(out)])
    assert rc == 0, f"stderr={stderr}"
    # stderr 应有 INFO 行说明自动推断
    assert "自动选择" in stderr
    assert "markdown" in stderr
    # 输出确实是 markdown 解析结果
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "markdown"
    assert data["parser_name"] == "markdown"


def test_parse_auto_infers_html(tmp_path: Path):
    src = tmp_path / "doc.html"
    src.write_text("<html><body><h1>Hi</h1></body></html>", encoding="utf-8")
    out = tmp_path / "out.json"
    rc, _, stderr = _run_cli(["parse", str(src), "-o", str(out)])
    assert rc == 0, f"stderr={stderr}"
    assert "html" in stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["parser_name"] == "html"


def test_parse_auto_infers_text(tmp_path: Path):
    src = tmp_path / "doc.txt"
    src.write_text("Hello text.\n\nSecond para.\n", encoding="utf-8")
    out = tmp_path / "out.json"
    rc, _, stderr = _run_cli(["parse", str(src), "-o", str(out)])
    assert rc == 0, f"stderr={stderr}"
    assert "text" in stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["parser_name"] == "text"


def test_parse_auto_infers_ipynb(tmp_path: Path):
    nb = {
        "cells": [{"cell_type": "markdown", "source": "# T"}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    src = tmp_path / "doc.ipynb"
    src.write_text(json.dumps(nb), encoding="utf-8")
    out = tmp_path / "out.json"
    rc, _, stderr = _run_cli(["parse", str(src), "-o", str(out)])
    assert rc == 0, f"stderr={stderr}"
    assert "ipynb" in stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["parser_name"] == "ipynb"


def test_parse_explicit_parser_overrides_inference(tmp_path: Path):
    """显式 --parser 时，不打印 INFO 行，直接用指定 parser。"""
    src = tmp_path / "doc.md"
    src.write_text("# Hi\n", encoding="utf-8")
    out = tmp_path / "out.json"
    rc, _, stderr = _run_cli(["parse", str(src), "-o", str(out), "--parser", "markdown"])
    assert rc == 0, f"stderr={stderr}"
    # 显式指定时不应有 INFO 行
    assert "自动选择" not in stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["parser_name"] == "markdown"


# ---- parse-dir 子命令 ----


def test_parse_dir_processes_multiple_files(tmp_path: Path):
    """目录批处理：3 种扩展名 → 3 个 JSON + 1 个 summary。"""
    in_dir = tmp_path / "input"
    in_dir.mkdir()
    (in_dir / "a.md").write_text("# A\n\nBody A.\n", encoding="utf-8")
    (in_dir / "b.html").write_text("<h1>B</h1><p>Body B.</p>", encoding="utf-8")
    (in_dir / "c.txt").write_text("Body C paragraph.\n", encoding="utf-8")
    # 未知扩展名应被忽略
    (in_dir / "skip.xyz").write_text("ignored", encoding="utf-8")

    out_dir = tmp_path / "out"
    rc, stdout, stderr = _run_cli(["parse-dir", str(in_dir), "-o", str(out_dir)])
    assert rc == 0, f"stderr={stderr}"
    # 3 个 JSON 输出（每个含原扩展名以避免冲突）
    assert (out_dir / "a.md.json").is_file()
    assert (out_dir / "b.html.json").is_file()
    assert (out_dir / "c.txt.json").is_file()
    # summary
    summary_path = out_dir / "_summary.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total"] == 3
    assert summary["success"] == 3
    assert summary["failure"] == 0
    # 顶层 stdout 有 SUMMARY 行
    assert "[SUMMARY] 3/3 ok" in stdout


def test_parse_dir_recursive(tmp_path: Path):
    """--recursive 走子目录。"""
    in_dir = tmp_path / "input"
    sub = in_dir / "sub"
    sub.mkdir(parents=True)
    (in_dir / "top.md").write_text("# Top\n", encoding="utf-8")
    (sub / "nested.md").write_text("# Nested\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    # 不带 --recursive：只处理顶层
    rc, stdout, _ = _run_cli(["parse-dir", str(in_dir), "-o", str(out_dir)])
    assert rc == 0
    assert (out_dir / "top.md.json").is_file()
    assert not (out_dir / "sub" / "nested.md.json").is_file()

    # 带 --recursive：处理子目录
    out_dir2 = tmp_path / "out2"
    rc, stdout, _ = _run_cli(["parse-dir", str(in_dir), "-o", str(out_dir2), "--recursive"])
    assert rc == 0
    assert (out_dir2 / "top.md.json").is_file()
    assert (out_dir2 / "sub" / "nested.md.json").is_file()


def test_parse_dir_records_failures_in_summary(tmp_path: Path):
    """失败文件计入 summary.failure 但不阻塞其他文件。"""
    in_dir = tmp_path / "input"
    in_dir.mkdir()
    (in_dir / "ok.md").write_text("# OK\n", encoding="utf-8")
    # 构造一个会失败的 markdown（虽然 markdown parser 很难失败；改用伪造的 .pdf）
    (in_dir / "bad.pdf").write_bytes(b"%PDF-1.4\nthis is not valid\n%%EOF")

    out_dir = tmp_path / "out"
    rc, stdout, stderr = _run_cli(["parse-dir", str(in_dir), "-o", str(out_dir)])
    # 因有 1 个失败 → rc != 0
    assert rc != 0
    # OK 文件仍写出
    assert (out_dir / "ok.md.json").is_file()
    # summary 记录
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["failure"] == 1
    # failure 条目有 errors
    fail_entries = [e for e in summary["files"] if e["status"] == "fail"]
    assert len(fail_entries) == 1
    assert fail_entries[0]["errors"][0]["code"]  # 错误码非空
    # bad.pdf 不应留半成品
    assert not (out_dir / "bad.pdf.json").is_file()


def test_parse_dir_explicit_parser_recorded_in_summary(tmp_path: Path):
    """--parser markdown 时，summary.parser_override 与 per-file parser 都记录为 markdown。

    注：parser 内部仍按自身扩展名白名单校验，所以不能用 .txt 强制 markdown（会失败）；
    这里用 .md + markdown 验证显式覆盖被记录。
    """
    in_dir = tmp_path / "input"
    in_dir.mkdir()
    (in_dir / "doc.md").write_text("# Title\n\nBody.\n", encoding="utf-8")

    out_dir = tmp_path / "out"
    rc, _, stderr = _run_cli([
        "parse-dir", str(in_dir), "-o", str(out_dir), "--parser", "markdown",
    ])
    assert rc == 0, f"stderr={stderr}"
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["parser_override"] == "markdown"
    assert all(f["parser"] == "markdown" for f in summary["files"])
    # 输出 JSON 确实是 markdown parser 产出
    data = json.loads((out_dir / "doc.md.json").read_text(encoding="utf-8"))
    assert data["parser_name"] == "markdown"


def test_parse_dir_missing_dir_returns_2(tmp_path: Path):
    rc, _, _ = _run_cli(["parse-dir", str(tmp_path / "nope"), "-o", str(tmp_path / "out")])
    assert rc == 2


def test_parse_dir_empty_dir_warns_but_succeeds(tmp_path: Path):
    """空目录（无支持文件）：warning，rc=0，summary.total=0。"""
    in_dir = tmp_path / "empty"
    in_dir.mkdir()
    out_dir = tmp_path / "out"
    rc, _, stderr = _run_cli(["parse-dir", str(in_dir), "-o", str(out_dir)])
    assert rc == 0
    assert "未发现支持类型的文件" in stderr
    summary = json.loads((out_dir / "_summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 0
    assert summary["success"] == 0
    assert summary["failure"] == 0


# ---------- 边角与缺漏补强（Round 33） ----------


# argparse 入口校验


def test_no_command_returns_2():
    """argparse required=True 时缺子命令 → rc=2 + stderr。"""
    rc, out, err = _run_cli([])
    assert rc != 0
    assert "command" in err.lower() or "required" in err.lower()


def test_unknown_command_returns_2():
    """未知子命令 → argparse rc=2。"""
    rc, out, err = _run_cli(["bogus"])
    assert rc != 0


def test_parse_missing_output_returns_2(tmp_path: Path):
    """parse 缺 -o 必填项 → argparse rc=2。"""
    src = tmp_path / "doc.md"
    src.write_text("# T\n", encoding="utf-8")
    rc, out, err = _run_cli(["parse", str(src)])
    assert rc != 0
    assert "--output" in err or "-o" in err


def test_parse_invalid_parser_choice_returns_2(tmp_path: Path):
    """--parser 不在 choices 内 → argparse rc=2。"""
    src = tmp_path / "doc.md"
    src.write_text("# T\n", encoding="utf-8")
    rc, out, err = _run_cli([
        "parse", str(src), "-o", str(tmp_path / "out.json"),
        "--parser", "bogus_parser",
    ])
    assert rc != 0
    assert "invalid choice" in err


def test_parse_nonexistent_input_returns_1(tmp_path: Path):
    """输入文件不存在 → rc=1 + 结构化 error JSON。"""
    missing = tmp_path / "nope.md"
    out = tmp_path / "out.json"
    rc, stdout, stderr = _run_cli(["parse", str(missing), "-o", str(out)])
    assert rc == 1
    # 结构化 error 写到 stderr
    err_data = json.loads(stderr)
    assert err_data["errors"][0]["code"] == "file_not_found"
    assert str(missing) in err_data["input"]


def test_validate_nonexistent_returns_2(tmp_path: Path):
    """validate 缺输入文件 → rc=2（与 parse 的 rc=1 不同，注意区分）。"""
    rc, out, err = _run_cli(["validate", str(tmp_path / "nope.json")])
    assert rc == 2
    assert "[ERROR] 文件不存在" in err


def test_validate_bad_json_returns_1(tmp_path: Path):
    """validate 拿到非合法 JSON → rc=1。"""
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    rc, out, err = _run_cli(["validate", str(bad)])
    assert rc == 1
    assert "[FAIL]" in err


def test_validate_invalid_content_returns_1(tmp_path: Path):
    """validate 拿到合法 JSON 但 schema 不合规 → rc=1。"""
    bad = tmp_path / "wrong_shape.json"
    bad.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    rc, out, err = _run_cli(["validate", str(bad)])
    assert rc == 1
    assert "[FAIL]" in err


def test_validate_valid_file_returns_0(tmp_path: Path):
    """validate 通过 schema 校验 → rc=0 + [OK]。"""
    src = tmp_path / "doc.md"
    src.write_text("# Title\n\nbody.\n", encoding="utf-8")
    out = tmp_path / "out.json"
    rc, _, _ = _run_cli(["parse", str(src), "-o", str(out)])
    assert rc == 0
    rc, stdout, stderr = _run_cli(["validate", str(out)])
    assert rc == 0
    assert "[OK]" in stdout


# _iter_supported_files / _relative_output_path / _preview / _load_document_json / _format_* 直接单测


def test_iter_supported_files_filters_by_extension(tmp_path: Path):
    from app.cli import _iter_supported_files
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "b.docx").write_bytes(b"x")
    (tmp_path / "c.unknown").write_text("x", encoding="utf-8")
    (tmp_path / "d.txt").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = sorted(p.name for p in result)
    assert names == ["a.md", "b.docx", "d.txt"]


def test_iter_supported_files_sorted_by_name(tmp_path: Path):
    from app.cli import _iter_supported_files
    # 倒序写入
    for n in ["z.md", "a.md", "m.md"]:
        (tmp_path / n).write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert names == ["a.md", "m.md", "z.md"]


def test_iter_supported_files_recursive_walks_subdir(tmp_path: Path):
    from app.cli import _iter_supported_files
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.md").write_text("x", encoding="utf-8")
    (sub / "nested.md").write_text("y", encoding="utf-8")
    flat = _iter_supported_files(tmp_path, recursive=False)
    deep = _iter_supported_files(tmp_path, recursive=True)
    assert len(flat) == 1
    assert len(deep) == 2


def test_iter_supported_files_skips_directories(tmp_path: Path):
    """目录（即便叫 x.md）应被 is_file 过滤。"""
    from app.cli import _iter_supported_files
    (tmp_path / "weird.md").mkdir()  # 同名目录
    (tmp_path / "real.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert "weird.md" not in names
    assert "real.md" in names


def test_iter_supported_files_extension_case_insensitive(tmp_path: Path):
    """大写扩展名也应识别（_EXTENSION_TO_PARSER 用 lower()）。"""
    from app.cli import _iter_supported_files
    (tmp_path / "A.MD").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    assert len(result) == 1


def test_relative_output_path_basic(tmp_path: Path):
    from app.cli import _relative_output_path
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    f = in_dir / "doc.md"
    result = _relative_output_path(in_dir, f, out_dir)
    assert result == out_dir / "doc.md.json"


def test_relative_output_path_nested(tmp_path: Path):
    from app.cli import _relative_output_path
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    f = in_dir / "sub" / "doc.md"
    result = _relative_output_path(in_dir, f, out_dir)
    # 嵌套路径保留 + 加 .json 后缀
    assert "sub" in result.parts
    assert result.name == "doc.md.json"


def test_relative_output_path_with_multiple_dots():
    """a.b.md 类文件名 → a.b.md.json。"""
    from app.cli import _relative_output_path
    from pathlib import Path
    result = _relative_output_path(
        Path("in"), Path("in") / "weird.name.md", Path("out")
    )
    assert result.name == "weird.name.md.json"


def test_preview_none_returns_empty_string():
    from app.cli import _preview
    assert _preview(None) == ""


def test_preview_empty_string_returns_empty():
    from app.cli import _preview
    assert _preview("") == ""


def test_preview_short_text_returned_as_is():
    from app.cli import _preview
    assert _preview("hello world") == "hello world"


def test_preview_collapses_whitespace():
    from app.cli import _preview
    assert _preview("hello\n\nworld  foo") == "hello world foo"


def test_preview_truncates_when_over_width():
    from app.cli import _preview
    text = "word " * 30  # 150 字符
    result = _preview(text, width=20)
    assert result.endswith("…")
    assert len(result) == 20  # width-1 字符 + 省略号


def test_preview_at_exact_width_no_truncation():
    from app.cli import _preview
    assert _preview("abc", width=3) == "abc"


def test_preview_custom_width():
    from app.cli import _preview
    assert _preview("hello world foo", width=5) == "hell…"


def test_load_document_json_valid(tmp_path: Path):
    from app.cli import _load_document_json
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    data, err = _load_document_json(p)
    assert data == {"a": 1}
    assert err == ""


def test_load_document_json_missing(tmp_path: Path):
    from app.cli import _load_document_json
    data, err = _load_document_json(tmp_path / "nope.json")
    assert data is None
    assert "文件不存在" in err


def test_load_document_json_invalid_json(tmp_path: Path):
    from app.cli import _load_document_json
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    data, err = _load_document_json(p)
    assert data is None
    assert "JSON 解析失败" in err


def test_format_summary_with_full_doc():
    from app.cli import _format_summary
    doc = _synthetic_document()
    result = _format_summary(doc, Path("/tmp/x.json"))
    assert "file:" in result
    assert "schema:      0.1.0" in result
    assert "elements=3" in result
    assert "chunks=2" in result
    assert "heading=1" in result
    assert "paragraph=2" in result
    assert "chunk text:" in result
    assert "chunk refs:" in result


def test_format_summary_with_warnings_and_errors():
    from app.cli import _format_summary
    doc = _synthetic_document()
    doc["warnings"] = [
        {"code": "low_conf", "reason": "ocr fallback"},
        {"code": "low_conf", "reason": "ocr fallback 2"},
    ]
    doc["errors"] = [
        {"code": "parse_err", "message": "broken"},
    ]
    result = _format_summary(doc, Path("/tmp/x.json"))
    assert "warnings (2)" in result
    assert "[low_conf] ocr fallback" in result
    assert "errors (1)" in result
    assert "[parse_err] broken" in result


def test_format_summary_truncates_warning_list_to_5():
    from app.cli import _format_summary
    doc = _synthetic_document()
    doc["warnings"] = [
        {"code": f"w{i}", "reason": f"r{i}"} for i in range(8)
    ]
    result = _format_summary(doc, Path("/tmp/x.json"))
    assert "+3 more" in result


def test_format_summary_with_empty_doc():
    from app.cli import _format_summary
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d",
        "source_path": "x",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "test",
        "parser_version": "0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    result = _format_summary(doc, Path("x.json"))
    assert "elements=0" in result
    assert "chunks=0" in result
    # 无 element 时不打印 element text 行
    assert "element text:" not in result
    # 无 chunk 时不打印 chunk text 行
    assert "chunk text:" not in result


def test_format_elements_list_empty():
    from app.cli import _format_elements_list
    result = _format_elements_list([], limit=10)
    assert "elements (0):" in result


def test_format_elements_list_with_parent_id():
    from app.cli import _format_elements_list
    elements = [
        {
            "element_id": "e1", "type": "paragraph",
            "content": "x", "parent_id": "e0",
        }
    ]
    result = _format_elements_list(elements, limit=10)
    assert "parent=e0" in result


def test_format_elements_list_no_parent_id():
    from app.cli import _format_elements_list
    elements = [
        {"element_id": "e1", "type": "paragraph", "content": "x"}
    ]
    result = _format_elements_list(elements, limit=10)
    assert "parent=" not in result


def test_format_elements_list_content_none():
    from app.cli import _format_elements_list
    elements = [
        {"element_id": "e1", "type": "image", "content": None,
         "resource_path": "x.png"}
    ]
    result = _format_elements_list(elements, limit=10)
    # content None 不应崩
    assert "image" in result
    assert "e1" in result


def test_format_elements_list_limit_zero_lists_all():
    from app.cli import _format_elements_list
    elements = [
        {"element_id": f"e{i}", "type": "paragraph", "content": str(i)}
        for i in range(20)
    ]
    result = _format_elements_list(elements, limit=0)
    assert "e0" in result
    assert "e19" in result
    assert "+N more" not in result
    assert "use --limit 0 to see all" not in result


def test_format_chunks_list_with_spans():
    from app.cli import _format_chunks_list
    chunks = [
        {
            "chunk_id": "c1", "text": "hello",
            "source_element_ids": ["e1"],
            "source_spans": [
                {"element_id": "e1", "start": 0, "end": 5},
                {"element_id": "e2", "start": 10, "end": 15},
            ],
        }
    ]
    result = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "e1[0:5]" in result
    assert "e2[10:15]" in result


def test_format_chunks_list_without_spans_data():
    from app.cli import _format_chunks_list
    chunks = [
        {"chunk_id": "c1", "text": "hi", "source_element_ids": ["e1"]},
    ]
    result = _format_chunks_list(chunks, limit=10, show_spans=True)
    assert "spans: (none)" in result


def test_format_chunks_list_show_spans_false_omits_span_lines():
    from app.cli import _format_chunks_list
    chunks = [
        {
            "chunk_id": "c1", "text": "hi",
            "source_element_ids": ["e1"],
            "source_spans": [{"element_id": "e1", "start": 0, "end": 2}],
        }
    ]
    result = _format_chunks_list(chunks, limit=10, show_spans=False)
    assert "spans:" not in result
    assert "span:" not in result


def test_format_chunks_list_text_none():
    from app.cli import _format_chunks_list
    chunks = [
        {"chunk_id": "c1", "text": None, "source_element_ids": ["e1"]},
    ]
    result = _format_chunks_list(chunks, limit=10)
    # text None 不应崩，chars=0
    assert "chars=0" in result


def test_emit_structured_error_writes_to_stderr(capsys, tmp_path: Path):
    from app.cli import _emit_structured_error
    _emit_structured_error(tmp_path / "x.pdf", "code1", "msg1", extra_key="v1")
    captured = capsys.readouterr()
    assert captured.out == ""  # nothing on stdout
    data = json.loads(captured.err)
    assert data["schema_version"] == "0.1.0"
    assert data["input"] == str(tmp_path / "x.pdf")
    assert data["errors"][0]["code"] == "code1"
    assert data["errors"][0]["message"] == "msg1"
    assert data["errors"][0]["extra_key"] == "v1"


def test_emit_structured_error_no_extra(capsys, tmp_path: Path):
    from app.cli import _emit_structured_error
    _emit_structured_error(tmp_path / "x.pdf", "code1", "msg1")
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["errors"][0] == {"code": "code1", "message": "msg1"}


# main() 函数级别测试


def test_main_returns_2_for_unknown_command():
    """main(['bogus']) → argparse rc=2 (SystemExit)。"""
    from app.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["bogus"])
    assert exc.value.code != 0


def test_main_validate_returns_0_for_valid_file(tmp_path: Path):
    """main(['validate', valid]) → 0。"""
    from app.cli import main
    src = tmp_path / "doc.md"
    src.write_text("# T\n\nbody.\n", encoding="utf-8")
    out = tmp_path / "out.json"
    main(["parse", str(src), "-o", str(out)])
    assert main(["validate", str(out)]) == 0


def test_main_inspect_returns_0_for_summary(tmp_path: Path):
    from app.cli import main
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_synthetic_document()), encoding="utf-8")
    assert main(["inspect", str(p)]) == 0


def test_main_inspect_returns_1_for_top_level_array(tmp_path: Path):
    """inspect 顶层是数组 → main 返回 1。"""
    from app.cli import main
    p = tmp_path / "arr.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    assert main(["inspect", str(p)]) == 1


def test_main_inspect_returns_2_for_missing_file(tmp_path: Path):
    from app.cli import main
    assert main(["inspect", str(tmp_path / "nope.json")]) == 2


def test_main_validate_returns_2_for_missing_file(tmp_path: Path):
    from app.cli import main
    assert main(["validate", str(tmp_path / "nope.json")]) == 2


def test_main_validate_returns_1_for_invalid_content(tmp_path: Path):
    from app.cli import main
    p = tmp_path / "wrong.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    assert main(["validate", str(p)]) == 1


