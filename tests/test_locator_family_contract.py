"""source_locator family 契约测试（Stage 6 批次 3）。

契约：docs/locator-kvfs-contract.md。逐条映射：
- §2 四族 family 正确性（按 parser 实际产出验证）
- §5 既有键不变（Determinism：去掉 family 后与 legacy 形状相等）
- §4 版本分支（0.3.0 必填 family + 每族 const；0.2.0/0.1.0 拒 family；
  无 family 的旧输出仍可校验）
- §5 resolver 可执行断言（line_address 行命中、container_line cell 命中）
- §1 不变量 2 豁免：kreuzberg 占位 locator 的标记键保留
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models import SCHEMA_VERSION_LOCATOR
from app.parsers.html_parser import HtmlParser
from app.parsers.ipynb_parser import IpynbParser
from app.parsers.kreuzberg_parser import _make_locator as _krb_locator
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.text_parser import TextParser
from app.schema import validate as validate_udm

ROOT = Path(__file__).resolve().parent.parent


def _strip_family(loc: dict) -> dict:
    return {k: v for k, v in loc.items() if k != "family"}


# ---------- §2 family 正确性：line_address ----------

def test_text_family_line_address(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("one\n\ntwo\n", encoding="utf-8")
    doc = TextParser().parse(p, source_hash="a" * 64)
    assert [e.source_locator["family"] for e in doc.elements] == [
        "line_address", "line_address"]
    # 既有键不变（Determinism）
    assert [_strip_family(e.source_locator) for e in doc.elements] == [
        {"line": 1}, {"line": 3}]


def test_markdown_family_line_address(tmp_path: Path):
    p = tmp_path / "a.md"
    p.write_text("# Title\n\nbody\n", encoding="utf-8")
    doc = MarkdownParser().parse(p, source_hash="a" * 64)
    assert all(e.source_locator["family"] == "line_address"
               for e in doc.elements)
    heading = doc.elements[0]
    assert _strip_family(heading.source_locator) == {
        "line": 1, "section_path": "Title"}


def test_html_family_line_address(tmp_path: Path):
    p = tmp_path / "a.html"
    p.write_text("<p>Alpha.</p>\n\n<p>Beta.</p>\n", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert [e.source_locator["family"] for e in doc.elements] == [
        "line_address", "line_address"]
    assert [_strip_family(e.source_locator) for e in doc.elements] == [
        {"line": 1}, {"line": 3}]


# ---------- §2 family 正确性：container_line ----------

def _nb(path: Path, cells: list[dict]) -> Path:
    doc = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {}, "cells": cells,
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_ipynb_family_container_line(tmp_path: Path):
    p = _nb(tmp_path / "a.ipynb", [
        {"cell_type": "markdown", "source": ["md cell"]},
        {"cell_type": "code", "source": ["print(1)"]},
    ])
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    fams = [e.source_locator["family"] for e in doc.elements]
    assert fams == ["container_line", "container_line"]
    # 既有键不变：md cell 元素与 code cell 元素的 legacy 形状
    md_loc = _strip_family(doc.elements[0].source_locator)
    code_loc = _strip_family(doc.elements[1].source_locator)
    assert md_loc == {"cell_index": 0, "cell_type": "markdown", "line": 1}
    assert code_loc == {"cell_index": 1, "cell_type": "code", "line": 1}


# ---------- §2 family 正确性：kreuzberg 占位（含不变量 2 豁免） ----------

def test_kreuzberg_placeholder_locator_family_and_marker_keys():
    pdf_loc = _krb_locator("pdf", 0)
    assert pdf_loc["family"] == "page_geometry"
    assert pdf_loc["_kreuzberg_placeholder"] is True  # 豁免标记保留
    assert _strip_family(pdf_loc) == {"page": 1, "_kreuzberg_placeholder": True}

    docx_loc = _krb_locator("docx", 3)
    assert docx_loc["family"] == "structural_index"
    assert docx_loc["_kreuzberg_heuristic"] is True
    assert _strip_family(docx_loc) == {
        "paragraph_index": 3, "_kreuzberg_heuristic": True}


# ---------- §2 family 正确性：fallback pdf/docx（devset 真实样本） ----------

def _devset_entry(source_type: str):
    devset = ROOT / "samples/private/devset/manifest.json"
    if not devset.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    from evaluation.manifest import load_manifest
    m = load_manifest(devset, project_root=ROOT)
    return next((d for d in m.documents if d.source_type == source_type), None)


def test_fallback_pdf_family_page_geometry():
    entry = _devset_entry("pdf")
    if entry is None:
        pytest.skip("devset 无 pdf 样本")
    from app.parsers.fallback_parser import FallbackParser
    doc = FallbackParser().parse(entry.resolved_path, source_hash="a" * 64)
    assert doc.elements
    for e in doc.elements:
        assert e.source_locator["family"] == "page_geometry"
        legacy = _strip_family(e.source_locator)
        assert "page" in legacy and legacy["page"] >= 1


def test_fallback_docx_family_structural_index():
    entry = _devset_entry("docx")
    if entry is None:
        pytest.skip("devset 无 docx 样本")
    from app.parsers.fallback_parser import FallbackParser
    doc = FallbackParser().parse(entry.resolved_path, source_hash="a" * 64)
    assert doc.elements
    for e in doc.elements:
        assert e.source_locator["family"] == "structural_index"
        legacy = _strip_family(e.source_locator)
        assert "paragraph_index" in legacy or "table_index" in legacy


# ---------- §4 版本分支 ----------

def _udm(source_type: str, version: str, locator: dict) -> dict:
    return {
        "schema_version": version,
        "document_id": "doc1",
        "source_path": "samples/x",
        "source_type": source_type,
        "source_hash": "a" * 64,
        "parser_name": "p",
        "parser_version": "1",
        "elements": [{
            "element_id": "e1", "type": "paragraph", "parent_id": None,
            "source_locator": locator, "content": "x", "resource_path": None,
            "confidence": 1.0, "metadata": {},
        }],
        "chunks": [], "relations": [], "warnings": [], "errors": [],
        "metadata": {},
    }


_FAMILY_CASES = [
    ("pdf", {"family": "page_geometry", "page": 1}),
    ("docx", {"family": "structural_index", "paragraph_index": 0}),
    ("markdown", {"family": "line_address", "line": 1}),
    ("html", {"family": "line_address", "line": 1}),
    ("text", {"family": "line_address", "line": 1}),
    ("ipynb", {"family": "container_line", "cell_index": 0,
               "cell_type": "code"}),
]


@pytest.mark.parametrize("source_type,locator", _FAMILY_CASES)
def test_030_requires_family_and_accepts_correct_const(source_type, locator):
    assert SCHEMA_VERSION_LOCATOR == "0.3.0"
    validate_udm(_udm(source_type, "0.3.0", locator))


@pytest.mark.parametrize("source_type,locator", _FAMILY_CASES)
def test_030_rejects_missing_family(source_type, locator):
    with pytest.raises(Exception):
        validate_udm(_udm(source_type, "0.3.0", _strip_family(locator)))


@pytest.mark.parametrize("source_type,locator", [
    ("pdf", {"family": "structural_index", "page": 1}),
    ("docx", {"family": "page_geometry", "paragraph_index": 0}),
    ("markdown", {"family": "container_line", "line": 1}),
    ("html", {"family": "page_geometry", "line": 1}),
    ("text", {"family": "structural_index", "line": 1}),
    ("ipynb", {"family": "line_address", "cell_index": 0,
               "cell_type": "code"}),
])
def test_030_rejects_wrong_family_const(source_type, locator):
    with pytest.raises(Exception):
        validate_udm(_udm(source_type, "0.3.0", locator))


@pytest.mark.parametrize("source_type,locator", _FAMILY_CASES)
def test_020_rejects_family(source_type, locator):
    with pytest.raises(Exception):
        validate_udm(_udm(source_type, "0.2.0", locator))


def test_010_rejects_family():
    with pytest.raises(Exception):
        validate_udm(_udm("pdf", "0.1.0",
                          {"family": "page_geometry", "page": 1}))


@pytest.mark.parametrize("source_type,locator", _FAMILY_CASES)
def test_old_output_without_family_still_validates(source_type, locator):
    """读兼容：无 family 的 0.2.0 旧产物继续可校验。"""
    legacy = _strip_family(locator)
    validate_udm(_udm(source_type, "0.2.0", legacy))
    if source_type in ("pdf", "docx"):
        validate_udm(_udm(source_type, "0.1.0", legacy))


# ---------- §5 resolver 可执行断言 ----------

def test_resolver_line_address_hits_physical_lines(tmp_path: Path):
    """line_address resolver：UTF-8 decode → 物理行（空行计入）→ 首行命中。"""
    raw = "alpha para.\n\nbeta para.\n"
    p = tmp_path / "r.txt"
    p.write_text(raw, encoding="utf-8")
    doc = TextParser().parse(p, source_hash="a" * 64)
    lines = raw.split("\n")
    for e in doc.elements:
        loc = e.source_locator
        assert loc["family"] == "line_address"
        first_line = lines[loc["line"] - 1]
        assert first_line  # 指向非空物理行
        assert e.content.startswith(first_line.strip()[:4])


def test_resolver_container_line_hits_cell(tmp_path: Path):
    """container_line resolver：JSON cells[cell_index] 命中容器。"""
    p = _nb(tmp_path / "r.ipynb", [
        {"cell_type": "markdown", "source": ["# head", "body"]},
        {"cell_type": "code", "source": ["print(1)"]},
    ])
    raw = json.loads(p.read_text(encoding="utf-8"))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    for e in doc.elements:
        loc = e.source_locator
        cell = raw["cells"][loc["cell_index"]]
        assert cell["cell_type"] == loc["cell_type"]
        if loc["cell_type"] == "markdown":
            src_lines = "".join(cell["source"]).split("\n")
            assert src_lines[loc["line"] - 1]
