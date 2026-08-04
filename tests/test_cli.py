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
