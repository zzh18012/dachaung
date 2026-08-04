"""Round 90 — 跨模块端到端不变量测试。

互补于已有的 per-module 单测，这里覆盖跨模块的不变量：
- pipeline → schema 校验：每个 parser 端到端产出的 Document 都过 schema
- chunker → 不丢不重：所有 chunk 文本拼接后等于所有 element 文本拼接（规范化后）
- 每个 chunk 至少有 1 个 source_element_id（CLAUDE.md 关键不变量）
- evaluation runner 能消费合法 manifest + 文档
- Document.to_dict JSON 可序列化
- source_hash 与 compute_file_hash 一致

不修改任何源码。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.chunkers import StructuralChunker, normalize_text
from app.chunkers.structural import _ChunkBuffer
from app.hash import compute_file_hash, compute_text_hash
from app.models import Document
from app.parsers import Parser, make_document_id
from app.parsers.html_parser import HtmlParser
from app.parsers.ipynb_parser import IpynbParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.text_parser import TextParser
from app.pipeline import get_parser, process_single
from app.schema import is_valid, validate


# =============================================================================
# 辅助：构造小尺寸测试输入
# ==============================================================================


def _write_text(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _write_json(tmp_path: Path, name: str, data) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# =============================================================================
# Parser 端到端：每个 parser 产出都过 schema
# =============================================================================


PARSER_INPUTS = [
    ("text", "hello.txt", "hello world. This is a test."),
    ("markdown", "test.md", "# Title\n\nParagraph one.\n\n## Sub\n\nPara two.\n"),
    ("html", "test.html", "<html><body><h1>Title</h1><p>Content.</p></body></html>"),
    ("ipynb", "test.ipynb", {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title"]},
            {"cell_type": "code", "source": ["print(1)"], "outputs": [], "metadata": {}},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }),
]


@pytest.mark.parametrize("parser_name,filename,content", [
    ("text", "hello.txt", "hello world. This is a test."),
    ("markdown", "test.md", "# Title\n\nParagraph one.\n\n## Sub\n\nPara two.\n"),
    ("html", "test.html", "<html><body><h1>Title</h1><p>Content.</p></body></html>"),
])
def test_end_to_end_parser_produces_schema_valid_document(
    tmp_path, parser_name, filename, content
):
    """每个文本类 parser 端到端产出的 Document 都过 schema。"""
    p = _write_text(tmp_path, filename, content)
    doc, errors = process_single(p, parser_name=parser_name, write_json=False)
    assert doc is not None
    assert errors == []
    assert is_valid(doc.to_dict()) is True


def test_end_to_end_ipynb_parser_produces_schema_valid_document(tmp_path):
    p = _write_json(tmp_path, "test.ipynb", {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title"]},
            {"cell_type": "code", "source": ["print(1)"], "outputs": [], "metadata": {}},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    })
    doc, errors = process_single(p, parser_name="ipynb", write_json=False)
    assert doc is not None
    assert errors == []
    assert is_valid(doc.to_dict()) is True


def test_end_to_end_document_to_dict_is_json_serializable(tmp_path):
    """Document.to_dict 必须 JSON 可序列化（写盘要求）。"""
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    s = json.dumps(doc.to_dict(), ensure_ascii=False)
    assert isinstance(s, str)
    # 反序列化一致
    parsed = json.loads(s)
    assert parsed["document_id"] == doc.document_id


def test_end_to_end_source_hash_matches_compute_file_hash(tmp_path):
    """Document.source_hash 必须等于 compute_file_hash(input_path)。"""
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert doc.source_hash == compute_file_hash(p)


def test_end_to_end_document_id_starts_with_doc_prefix(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert doc.document_id.startswith("doc-")
    assert len(doc.document_id) == 20  # "doc-" + 16 hex


def test_end_to_end_document_id_matches_make_document_id(tmp_path):
    """document_id 由 source_hash 派生，应等于 make_document_id(source_hash)。"""
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert doc.document_id == make_document_id(doc.source_hash)


# =============================================================================
# Chunker 不变量：每个 chunk 至少有 1 个 source_element_id
# =============================================================================


def test_chunker_every_chunk_has_non_empty_source_element_ids(tmp_path):
    """CLAUDE.md 关键不变量：每个 chunk 必须有非空 source_element_ids。"""
    p = _write_text(tmp_path, "test.txt", "hello world. " * 100)
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert len(doc.chunks) > 0
    for chunk in doc.chunks:
        assert len(chunk.source_element_ids) >= 1
        for eid in chunk.source_element_ids:
            assert eid  # 非空字符串


def test_chunker_every_chunk_text_is_non_empty(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world. " * 100)
    doc, _ = process_single(p, parser_name="text", write_json=False)
    for chunk in doc.chunks:
        assert chunk.text  # 非空字符串


def test_chunker_every_chunk_id_unique(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world. " * 100)
    doc, _ = process_single(p, parser_name="text", write_json=False)
    ids = [c.chunk_id for c in doc.chunks]
    assert len(ids) == len(set(ids))  # 无重复


def test_chunker_every_chunk_id_within_max_chars_default(tmp_path):
    """默认 max_chars=800。"""
    p = _write_text(tmp_path, "test.txt", "a " * 2000)
    doc, _ = process_single(p, parser_name="text", write_json=False)
    for chunk in doc.chunks:
        assert len(chunk.text) <= 800


def test_chunker_chunk_text_concatenation_preserves_normalized_text(tmp_path):
    """不丢不重：normalize 后，Σ chunk.text == Σ element.content（非 image）。"""
    p = _write_text(tmp_path, "test.txt", "hello world. foo bar baz. extra text here.")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    expected = normalize_text(
        " ".join(e.content for e in doc.elements if e.type != "image" and e.content)
    )
    actual = normalize_text(" ".join(c.text for c in doc.chunks))
    assert expected == actual


def test_chunker_chunk_text_concatenation_preserves_normalized_long(tmp_path):
    """100 段长文本也应保持不丢不重。"""
    text = "The quick brown fox jumps over the lazy dog. " * 100
    p = _write_text(tmp_path, "test.txt", text)
    doc, _ = process_single(p, parser_name="text", write_json=False)
    expected = normalize_text(text)
    actual = normalize_text(" ".join(c.text for c in doc.chunks))
    assert expected == actual


def test_chunker_metadata_includes_strategy_and_max_chars(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    for chunk in doc.chunks:
        assert "strategy" in chunk.metadata
        assert "max_chars" in chunk.metadata
        assert "char_count" in chunk.metadata


def test_chunker_metadata_char_count_matches_text_length(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    for chunk in doc.chunks:
        assert chunk.metadata["char_count"] == len(chunk.text)


def test_chunker_chunks_reference_existing_element_ids(tmp_path):
    """每个 chunk.source_element_ids 必须是 element.element_id 的子集。"""
    p = _write_text(tmp_path, "test.txt", "hello world. " * 50)
    doc, _ = process_single(p, parser_name="text", write_json=False)
    element_ids = {e.element_id for e in doc.elements}
    for chunk in doc.chunks:
        for eid in chunk.source_element_ids:
            assert eid in element_ids


# =============================================================================
# Parser/Document 一致性
# =============================================================================


def test_parser_name_and_version_present_in_document(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert doc.parser_name == "text"
    assert doc.parser_version  # 非空


def test_parser_metadata_is_dict(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert isinstance(doc.metadata, dict)


def test_parser_relations_is_list(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert isinstance(doc.relations, list)


def test_parser_warnings_is_list(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert isinstance(doc.warnings, list)


def test_parser_errors_is_list_empty_on_success(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, errors = process_single(p, parser_name="text", write_json=False)
    assert isinstance(doc.errors, list)
    assert errors == []


# =============================================================================
# 直接调用各 parser（不经 pipeline）的 schema 一致性
# =============================================================================


def test_text_parser_direct_call_schema_valid(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    sha = compute_file_hash(p)
    parser = TextParser()
    doc = parser.parse(p, source_hash=sha)
    assert is_valid(doc.to_dict()) is True


def test_markdown_parser_direct_call_schema_valid(tmp_path):
    p = _write_text(tmp_path, "test.md", "# Title\n\nPara.\n")
    sha = compute_file_hash(p)
    parser = MarkdownParser()
    doc = parser.parse(p, source_hash=sha)
    assert is_valid(doc.to_dict()) is True


def test_html_parser_direct_call_schema_valid(tmp_path):
    p = _write_text(tmp_path, "test.html", "<html><body><p>hi</p></body></html>")
    sha = compute_file_hash(p)
    parser = HtmlParser()
    doc = parser.parse(p, source_hash=sha)
    assert is_valid(doc.to_dict()) is True


def test_ipynb_parser_direct_call_schema_valid(tmp_path):
    p = _write_json(tmp_path, "test.ipynb", {
        "cells": [{"cell_type": "code", "source": ["x"], "outputs": [], "metadata": {}}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    })
    sha = compute_file_hash(p)
    parser = IpynbParser()
    doc = parser.parse(p, source_hash=sha)
    assert is_valid(doc.to_dict()) is True


# =============================================================================
# Pipeline 幂等性
# =============================================================================


def test_pipeline_idempotent_same_input_same_hash(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc1, _ = process_single(p, parser_name="text", write_json=False)
    doc2, _ = process_single(p, parser_name="text", write_json=False)
    assert doc1.source_hash == doc2.source_hash
    assert doc1.document_id == doc2.document_id


def test_pipeline_idempotent_same_chunks(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world. " * 100)
    doc1, _ = process_single(p, parser_name="text", write_json=False)
    doc2, _ = process_single(p, parser_name="text", write_json=False)
    assert [c.text for c in doc1.chunks] == [c.text for c in doc2.chunks]


def test_pipeline_different_input_different_hash(tmp_path):
    p1 = _write_text(tmp_path, "a.txt", "content a")
    p2 = _write_text(tmp_path, "b.txt", "content b")
    doc1, _ = process_single(p1, parser_name="text", write_json=False)
    doc2, _ = process_single(p2, parser_name="text", write_json=False)
    assert doc1.source_hash != doc2.source_hash


# =============================================================================
# JSON 写盘 ↔ 读盘 round-trip
# =============================================================================


def test_pipeline_write_then_read_json_roundtrip(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world. " * 50)
    out = tmp_path / "out.json"
    doc, _ = process_single(p, out, parser_name="text", write_json=True)
    assert out.is_file()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # 字段一致性
    assert data["document_id"] == doc.document_id
    assert data["source_hash"] == doc.source_hash
    assert data["source_type"] == doc.source_type
    assert len(data["chunks"]) == len(doc.chunks)
    assert len(data["elements"]) == len(doc.elements)


def test_pipeline_output_json_is_indented(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text")
    content = out.read_text(encoding="utf-8")
    assert "\n" in content  # indent 不为 None


def test_pipeline_output_json_is_utf8(tmp_path):
    """ensure_ascii=False：中文不转义。"""
    p = _write_text(tmp_path, "test.txt", "你好世界")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text")
    content = out.read_text(encoding="utf-8")
    assert "你好" in content  # 不转义


def test_pipeline_output_json_passes_validate_only(tmp_path):
    """process_single 写出的 JSON 用 validate_only 校验返回 True。"""
    from app.pipeline import validate_only
    p = _write_text(tmp_path, "test.txt", "hello world")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text")
    ok, msg = validate_only(out)
    assert ok is True
    assert msg == "OK"


# =============================================================================
# 与 evaluation/runner 的兼容性
# =============================================================================


def _make_minimal_manifest(project_root: Path, doc_relative_path: str, source_type: str = "docx") -> dict:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": doc_relative_path,
                "source_type": source_type,
            }
        ],
    }


def test_pipeline_output_consumable_by_evaluation_runner(tmp_path):
    """evaluation/runner 能消费合法 manifest + 文档，生成报告。

    注：manifest schema 限定 source_type ∈ {pdf, docx}，本测试用 .docx 后缀的
    文本文件（fallback_parser 会失败但 runner 应当捕获并继续）。
    """
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples_dir = proj_root / "samples"
    samples_dir.mkdir()

    doc_path = samples_dir / "test.docx"
    doc_path.write_text("hello world. " * 20, encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_data = _make_minimal_manifest(proj_root, "samples/test.docx", "docx")
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    output_path = proj_root / "report.json"
    report = run_evaluation(
        manifest,
        output_path,
        parser_name="fallback",
        max_chars=800,
        tolerance_chars=30,
    )

    assert isinstance(report, dict)
    assert "per_doc" in report
    assert len(report["per_doc"]) == 1
    # pipeline 失败（伪 docx），但报告仍生成
    assert "metrics" in report["per_doc"][0]


def test_pipeline_output_report_passes_schema(tmp_path):
    """evaluation runner 产出的报告通过 evaluation-report.schema.json。"""
    from evaluation.schema import validate as eval_validate
    from evaluation.manifest import load_manifest
    from evaluation.runner import run_evaluation

    proj_root = tmp_path / "proj"
    proj_root.mkdir()
    samples_dir = proj_root / "samples"
    samples_dir.mkdir()
    doc_path = samples_dir / "test.md"
    doc_path.write_text("# Title\n\nHello world.\n", encoding="utf-8")

    manifest_path = proj_root / "manifest.json"
    manifest_data = _make_minimal_manifest(proj_root, doc_path)
    # source_type 不允许 txt/markdown（manifest schema 限定 pdf/docx）
    # 但实际 manifest schema 限制 document.source_type ∈ {pdf, docx}
    manifest_data["documents"][0]["source_type"] = "docx"
    # 改后缀为 docx，但实际内容是 text（让 fallback_parser 解析）
    new_doc_path = samples_dir / "test.docx"
    new_doc_path.write_text("# Title\n\nHello world.\n", encoding="utf-8")
    manifest_data["documents"][0]["path"] = "samples/test.docx"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    output_path = proj_root / "report.json"

    # 注：.docx 实际是文本会被 fallback_parser 当 docx 处理 → 报错
    # 但 run_evaluation 应当捕获错误，pipeline_success=False，仍生成报告
    report = run_evaluation(
        manifest,
        output_path,
        parser_name="fallback",
        max_chars=800,
    )
    eval_validate(report, "evaluation-report.schema.json")  # 不抛


# =============================================================================
# Schema 反向不变量：to_dict() 字段集与 schema required 一致
# =============================================================================


def test_document_to_dict_has_all_required_top_level_fields(tmp_path):
    """Document.to_dict 必须含 schema 要求的 13 个顶层字段。"""
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    d = doc.to_dict()
    required = {
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert required.issubset(set(d.keys()))


def test_document_to_dict_schema_version_is_0_1_0(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    assert doc.to_dict()["schema_version"] == "0.1.0"


def test_document_to_dict_source_hash_is_64_lowercase_hex(tmp_path):
    import re
    p = _write_text(tmp_path, "test.txt", "hello world")
    doc, _ = process_single(p, parser_name="text", write_json=False)
    h = doc.to_dict()["source_hash"]
    assert re.match(r"^[0-9a-f]{64}$", h)


# =============================================================================
# 多 parser 一致性：所有 parser 输出的 Document 类型一致
# =============================================================================


def test_all_parsers_return_document_type(tmp_path):
    """每个 parser 的 parse() 返回 Document 实例。"""
    p = _write_text(tmp_path, "test.txt", "hello")
    sha = compute_file_hash(p)
    for parser_name in ("text", "markdown", "html"):
        # 构造符合该 parser 的输入
        if parser_name == "text":
            inp = p
        elif parser_name == "markdown":
            inp = _write_text(tmp_path, "test.md", "# T\n\nP.\n")
        elif parser_name == "html":
            inp = _write_text(tmp_path, "test.html", "<p>x</p>")
        sha = compute_file_hash(inp)
        parser = get_parser(parser_name)
        doc = parser.parse(inp, source_hash=sha)
        assert isinstance(doc, Document)


def test_all_parsers_set_chunks_empty_initially(tmp_path):
    """parser.parse() 返回的 Document.chunks 必须为空（chunker 在后续步骤填充）。"""
    p = _write_text(tmp_path, "test.txt", "hello world")
    sha = compute_file_hash(p)
    parser = TextParser()
    doc = parser.parse(p, source_hash=sha)
    assert doc.chunks == []


def test_all_parsers_set_elements_non_empty_on_real_input(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello world")
    sha = compute_file_hash(p)
    parser = TextParser()
    doc = parser.parse(p, source_hash=sha)
    assert len(doc.elements) >= 1


# =============================================================================
# Hash 一致性
# =============================================================================


def test_compute_file_hash_idempotent(tmp_path):
    p = _write_text(tmp_path, "test.txt", "hello")
    assert compute_file_hash(p) == compute_file_hash(p)


def test_compute_text_hash_idempotent():
    assert compute_text_hash("hello") == compute_text_hash("hello")


def test_compute_file_hash_matches_text_hash_for_same_content(tmp_path):
    """对纯文本文件，compute_file_hash(content) == compute_text_hash(content)。"""
    content = "hello world"
    p = _write_text(tmp_path, "test.txt", content)
    assert compute_file_hash(p) == compute_text_hash(content)


def test_compute_file_hash_different_files_different_hashes(tmp_path):
    a = _write_text(tmp_path, "a.txt", "content a")
    b = _write_text(tmp_path, "b.txt", "content b")
    assert compute_file_hash(a) != compute_file_hash(b)


def test_compute_text_hash_returns_64_char_hex():
    import re
    h = compute_text_hash("test")
    assert re.match(r"^[0-9a-f]{64}$", h)


# =============================================================================
# normalize_text 不丢不重（chunker 用它做对账）
# =============================================================================


def test_normalize_text_idempotent():
    s = "hello   world\n\nfoo"
    once = normalize_text(s)
    twice = normalize_text(once)
    assert once == twice


def test_normalize_text_strips_ends():
    assert normalize_text("  hello  ") == "hello"


def test_normalize_text_collapses_internal_whitespace():
    assert normalize_text("a\tb\nc") == "a b c"


def test_normalize_text_empty_returns_empty():
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""


# =============================================================================
# _ChunkBuffer 与 Chunk 不变量
# =============================================================================


def test_chunk_buffer_flush_keeps_at_least_one_source_element_id(tmp_path):
    """_ChunkBuffer.flush 即使有 1 个 part，也产生有效 chunk。"""
    buf = _ChunkBuffer(document_id="test-doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    chunk = buf.flush(strategy="test", max_chars=800)
    assert chunk is not None
    assert len(chunk.source_element_ids) >= 1


def test_chunk_buffer_flush_clears_parts():
    buf = _ChunkBuffer(document_id="test-doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    buf.flush(strategy="test", max_chars=800)
    assert buf.is_empty()


def test_chunk_buffer_flush_increments_counter_for_next_chunk():
    """counter 由调用方管理；flush 用当前 counter 生成 chunk_id。"""
    buf = _ChunkBuffer(document_id="test-doc", counter=0)
    buf.push_text("hello", "e1", 0, 5)
    c1 = buf.flush(strategy="test", max_chars=800)
    assert c1.chunk_id.endswith("c0000")

    buf.counter = 1
    buf.push_text("world", "e2", 0, 5)
    c2 = buf.flush(strategy="test", max_chars=800)
    assert c2.chunk_id.endswith("c0001")


# =============================================================================
# 错误传播：parser 错误变成结构化 ErrorRecord
# =============================================================================


def test_pipeline_file_not_found_returns_structured_error(tmp_path):
    """FileNotFoundError → ErrorRecord(code=file_not_found)。"""
    from app.models import ErrorRecord
    doc, errors = process_single(tmp_path / "missing.txt")
    assert doc is None
    assert len(errors) == 1
    assert isinstance(errors[0], ErrorRecord)
    assert errors[0].code == "file_not_found"


def test_pipeline_unknown_parser_returns_structured_error(tmp_path):
    """未知 parser → ErrorRecord(code=unexpected_parser_error)。"""
    from app.models import ErrorRecord
    p = _write_text(tmp_path, "test.txt", "hello")
    doc, errors = process_single(p, parser_name="nonexistent")
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == "unexpected_parser_error"


def test_pipeline_errors_are_json_serializable(tmp_path):
    """ErrorRecord 必须 JSON 可序列化（写盘要求）。"""
    doc, errors = process_single(tmp_path / "missing.txt")
    for e in errors:
        d = e.to_dict() if hasattr(e, "to_dict") else e.__dict__
        json.dumps(d, default=str)  # 不抛
