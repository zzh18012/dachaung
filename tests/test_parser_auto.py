"""--parser auto 混合 manifest 调度验收测试（evaluator v1.7 / report 1.3）。

ChatGPT 5.6 Sol 2026-08-27 指示：auto 只依据 manifest 的 source_type 确定
parser，不按扩展名猜测；显式 --parser 旧行为不变；报告 per_doc 记录
parser_used。ipynb 注册（v1.7）后覆盖：
1. 映射表与解析函数：pdf/docx→fallback、markdown→markdown、html→html、
   text→text、ipynb→ipynb；未注册类型 → None（文档级合成失败）；显式名原样透传
2. 混合 manifest（markdown+html+text+ipynb）单次 auto 运行：逐文档
   parser_used 正确、四类全部成功、报告通过 schema 校验、
   provenance.parser_name=="auto" 且 parser_version 为 null
   （多 parser 并存时单值会误导）
3. 显式 --parser markdown 行为不变：parser_used 全为 markdown，
   非 md 文档按既有语义 unsupported_type
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.manifest import load_manifest
from evaluation.runner import (
    AUTO_PARSER_BY_SOURCE_TYPE,
    _resolve_parser_name,
    run_evaluation,
)
from evaluation.schema import validate_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------- 映射与解析函数 ----------

def test_auto_mapping_table_registered_types_only():
    assert AUTO_PARSER_BY_SOURCE_TYPE == {
        "pdf": "fallback",
        "docx": "fallback",
        "markdown": "markdown",
        "html": "html",
        "text": "text",
        "ipynb": "ipynb",
    }


@pytest.mark.parametrize(
    "source_type,expected",
    [
        ("pdf", "fallback"),
        ("docx", "fallback"),
        ("markdown", "markdown"),
        ("html", "html"),
        ("text", "text"),
        ("ipynb", "ipynb"),  # v1.7 注册
        (None, "fallback"),  # ef 旧条目无 source_type → 沿用 fallback
    ],
)
def test_auto_resolves_by_source_type(source_type, expected):
    assert _resolve_parser_name("auto", source_type) == expected


def test_explicit_parser_passthrough():
    assert _resolve_parser_name("markdown", "html") == "markdown"
    assert _resolve_parser_name("fallback", "pdf") == "fallback"
    assert _resolve_parser_name("html", "markdown") == "html"


# ---------- 混合 manifest 单次运行 ----------

def _write(tmp_path: Path, rel: str, text: str) -> str:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return rel


def _mixed_manifest(tmp_path: Path) -> Path:
    md = _write(tmp_path, "docs/a.md", "# 标题\n\n正文 AUTO_MD 标记\n")
    html = _write(tmp_path, "docs/b.html", "<h1>标题</h1><p>AUTO_HTML 标记</p>")
    text = _write(tmp_path, "docs/c.txt", "plain text AUTO_TXT 标记\n")
    # v1.7：ipynb 已注册，混合 manifest 用真实 nbformat 4 notebook
    nb = {
        "cells": [
            {"cell_type": "markdown",
             "source": "# NB 标题\n\n正文 AUTO_NB 标记"},
            {"cell_type": "code", "source": "print('hi')"},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    ipynb = _write(tmp_path, "docs/d.ipynb", json.dumps(nb, ensure_ascii=False))
    data = {
        "manifest_version": "1.1",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "AUTO-MD", "path": md, "source_type": "markdown"},
            {"doc_id": "AUTO-HTML", "path": html, "source_type": "html"},
            {"doc_id": "AUTO-TEXT", "path": text, "source_type": "text"},
            {"doc_id": "AUTO-IPYNB", "path": ipynb, "source_type": "ipynb"},
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='test'\n", encoding="utf-8"
    )
    return tmp_path


def test_auto_mixed_manifest_single_run(tmp_project: Path):
    manifest = load_manifest(_mixed_manifest(tmp_project), project_root=tmp_project)
    out = tmp_project / "outputs" / "report.json"
    report = run_evaluation(manifest, out, parser_name="auto")

    # 报告通过 schema 校验（1.3 要求 per_doc.parser_used）
    validate_file(out, "evaluation-report.schema.json")
    assert report["report_version"] == "1.3"
    assert report["provenance"]["parser_name"] == "auto"
    # auto 模式多 parser 并存 → parser_version 为 null
    assert report["provenance"]["parser_version"] is None
    assert report["provenance"]["evaluator_version"] == "1.7"

    by_id = {d["doc_id"]: d for d in report["per_doc"]}
    assert by_id["AUTO-MD"]["parser_used"] == "markdown"
    assert by_id["AUTO-MD"]["metrics"]["pipeline_success"]["value"] is True
    assert by_id["AUTO-HTML"]["parser_used"] == "html"
    assert by_id["AUTO-HTML"]["metrics"]["pipeline_success"]["value"] is True

    # text 已注册（v1.6）：正常解析成功
    t = by_id["AUTO-TEXT"]
    assert t["parser_used"] == "text"
    assert t["metrics"]["pipeline_success"]["value"] is True

    # ipynb 已注册（v1.7）：正常解析成功
    nb = by_id["AUTO-IPYNB"]
    assert nb["parser_used"] == "ipynb"
    assert nb["metrics"]["pipeline_success"]["value"] is True


def test_explicit_markdown_behavior_unchanged(tmp_project: Path):
    manifest = load_manifest(_mixed_manifest(tmp_project), project_root=tmp_project)
    out = tmp_project / "outputs" / "report.json"
    report = run_evaluation(manifest, out, parser_name="markdown")

    assert report["provenance"]["parser_name"] == "markdown"
    # 显式模式：parser_used 全等于显式名（含失败文档）
    for d in report["per_doc"]:
        assert d["parser_used"] == "markdown"

    by_id = {d["doc_id"]: d for d in report["per_doc"]}
    assert by_id["AUTO-MD"]["metrics"]["pipeline_success"]["value"] is True
    # html/txt 过 markdown parser 按既有扩展名门控失败
    assert by_id["AUTO-HTML"]["metrics"]["error_code"]["value"] == "unsupported_type"
    assert by_id["AUTO-TEXT"]["metrics"]["error_code"]["value"] == "unsupported_type"


def test_auto_expected_failure_without_source_type(tmp_project: Path):
    """ef 旧条目无 source_type：auto 沿用 fallback（旧行为）。"""
    bad = tmp_project / "docs" / "bad.pdf"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"%PDF-1.4\nthis is not valid\n%%EOF")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ERR-1",
                "path": "docs/bad.pdf",
                "expected_error_code": "pdfplumber_open_failed",
            }
        ],
    }
    p = tmp_project / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_project)
    out = tmp_project / "outputs" / "report.json"
    report = run_evaluation(manifest, out, parser_name="auto")
    ef = report["expected_failures"][0]
    assert ef["actual_error_code"] == "pdfplumber_open_failed"
    assert ef["matches"] is True
