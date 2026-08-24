r"""Round 1367 — 跨模块结构不变量测试。

与 test_cross_module_conformance.py（常量对齐）互补，本文件锁
"全管线产物在模块之间满足的结构不变量"：

- id 无孤儿：每个 chunk.source_element_ids ⊆ elements 的 id 集合
- id 不重：同一 element id 最多出现在一个 chunk（跨 chunk 不重复）
- 顺序保持：各 chunk 的 source_element_ids 展平后 == 元素文档序
  （过滤未分块元素后）
- image 是唯一不进 chunk 的元素类型（table 进 isolated_table）
- 每个 chunk 文本非空、source_element_ids 非空（CLAUDE.md 不变量）
- document.source_hash == compute_file_hash(源文件)；
  document_id == make_document_id(source_hash)
- compute_file_hash 确定性；内容相同路径不同 → 同 hash；
  内容不同 → 异 hash；64 位小写 hex
- chunk metadata 键集合恰为 {strategy, char_count, max_chars}
- element_id / chunk_id 在文档内唯一

不修改任何源码。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.base import make_document_id
from app.pipeline import process_single

MD = ("# H\n\npara one two three\n\n- a\n- b\n\n"
      "| x | y |\n| --- | --- |\n| 1 | 2 |\n\n"
      "## Sub\n\ntail text here\n")

HTML = ("<html><body><h1>H</h1><p>para text</p>"
        "<table><tr><th>x</th><th>y</th></tr>"
        "<tr><td>1</td><td>2</td></tr></table>"
        "<img src='p.png' alt='x'><p>after</p>"
        "</body></html>")

NB = {
    "cells": [
        {"cell_type": "markdown",
         "source": ["# H\n", "para one\n"]},
        {"cell_type": "code",
         "source": "print(1)\nprint(2)"},
        {"cell_type": "markdown",
         "source": "## Sub\n\ntail"}],
    "metadata": {}, "nbformat": 4,
}


def _board(tmp_path):
    (tmp_path / "d.md").write_text(MD, encoding="utf-8")
    (tmp_path / "d.html").write_text(HTML, encoding="utf-8")
    (tmp_path / "n.ipynb").write_text(
        json.dumps(NB, ensure_ascii=False), encoding="utf-8")
    return (
        ("markdown", tmp_path / "d.md"),
        ("html", tmp_path / "d.html"),
        ("ipynb", tmp_path / "n.ipynb"),
    )


def _all_docs(tmp_path):
    out = []
    for name, path in _board(tmp_path):
        doc, errors = process_single(
            path, None, parser_name=name, max_chars=200)
        assert errors == [], (name, errors)
        out.append((name, doc))
    return out


# ---------- id 无孤儿 / 不重 / 顺序 ----------

def test_no_orphan_source_ids(tmp_path):
    for name, doc in _all_docs(tmp_path):
        eids = {e.element_id for e in doc.elements}
        for ch in doc.chunks:
            for sid in ch.source_element_ids:
                assert sid in eids, (name, sid)


def test_no_element_id_in_two_chunks(tmp_path):
    for name, doc in _all_docs(tmp_path):
        seen = set()
        for ch in doc.chunks:
            for sid in ch.source_element_ids:
                assert sid not in seen, (name, sid)
                seen.add(sid)


def test_source_ids_flatten_preserves_order(tmp_path):
    for name, doc in _all_docs(tmp_path):
        eids = [e.element_id for e in doc.elements]
        flat = [s for ch in doc.chunks
                for s in ch.source_element_ids]
        assert flat == [i for i in eids if i in set(flat)], \
            name


def test_image_is_only_unchunked_type(tmp_path):
    for name, doc in _all_docs(tmp_path):
        seen = {s for ch in doc.chunks
                for s in ch.source_element_ids}
        missing = [e for e in doc.elements
                   if e.element_id not in seen]
        types = {e.type for e in missing}
        if name == "html":
            assert types == {"image"}, name
        else:
            assert types == set(), name


# ---------- chunk 基本不变量 ----------

def test_chunk_text_nonempty(tmp_path):
    for name, doc in _all_docs(tmp_path):
        assert all(ch.text for ch in doc.chunks), name


def test_chunk_sources_nonempty(tmp_path):
    for name, doc in _all_docs(tmp_path):
        assert all(ch.source_element_ids
                   for ch in doc.chunks), name


def test_chunk_meta_keys_exact(tmp_path):
    for name, doc in _all_docs(tmp_path):
        for ch in doc.chunks:
            assert set(ch.metadata) == {
                "strategy", "char_count", "max_chars"}, \
                (name, sorted(ch.metadata))


def test_chunk_char_count_matches_len(tmp_path):
    for name, doc in _all_docs(tmp_path):
        for ch in doc.chunks:
            assert ch.metadata["char_count"] == \
                len(ch.text), name


def test_chunk_max_chars_echo(tmp_path):
    for name, doc in _all_docs(tmp_path):
        for ch in doc.chunks:
            assert ch.metadata["max_chars"] == 200, name


def test_element_ids_unique_per_doc(tmp_path):
    for name, doc in _all_docs(tmp_path):
        ids = [e.element_id for e in doc.elements]
        assert len(set(ids)) == len(ids), name


def test_chunk_ids_unique_per_doc(tmp_path):
    for name, doc in _all_docs(tmp_path):
        ids = [c.chunk_id for c in doc.chunks]
        assert len(set(ids)) == len(ids), name


# ---------- hash ↔ pipeline 关联 ----------

def test_source_hash_matches_file(tmp_path):
    for name, path in _board(tmp_path):
        doc, errors = process_single(
            path, None, parser_name=name, max_chars=200)
        assert errors == []
        assert doc.source_hash == \
            compute_file_hash(path), name


def test_document_id_from_source_hash(tmp_path):
    for name, path in _board(tmp_path):
        doc, _ = process_single(
            path, None, parser_name=name, max_chars=200)
        assert doc.document_id == \
            make_document_id(doc.source_hash), name


def test_document_id_prefix_consistent(tmp_path):
    for name, path in _board(tmp_path):
        doc, _ = process_single(
            path, None, parser_name=name, max_chars=200)
        assert doc.document_id.startswith("doc-")
        assert len(doc.document_id) == 20, name


# ---------- compute_file_hash 性质 ----------

def test_hash_deterministic(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello\n", encoding="utf-8")
    assert compute_file_hash(f) == compute_file_hash(f)


def test_hash_content_addressed(tmp_path):
    (tmp_path / "a.txt").write_text(
        "same body\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text(
        "same body\n", encoding="utf-8")
    assert compute_file_hash(
        tmp_path / "a.txt") == compute_file_hash(
        tmp_path / "b.txt")


def test_hash_sensitive_to_content(tmp_path):
    (tmp_path / "a.txt").write_text(
        "same body\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text(
        "same bodyX\n", encoding="utf-8")
    assert compute_file_hash(
        tmp_path / "a.txt") != compute_file_hash(
        tmp_path / "b.txt")


def test_hash_is_64_lowercase_hex(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x\n", encoding="utf-8")
    h = compute_file_hash(f)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ---------- image / heading 元素性质 ----------

def test_image_content_null_resource_set(tmp_path):
    (tmp_path / "d.html").write_text(HTML, encoding="utf-8")
    doc, _ = process_single(
        tmp_path / "d.html", None,
        parser_name="html", max_chars=200)
    img = [e for e in doc.elements
           if e.type == "image"][0]
    assert img.content is None
    assert img.resource_path == "p.png"


def test_heading_level_in_metadata(tmp_path):
    for name, doc in _all_docs(tmp_path):
        for e in doc.elements:
            if e.type == "heading":
                assert isinstance(
                    e.metadata.get("level"), int), name


def test_html_h1_level_one(tmp_path):
    (tmp_path / "d.html").write_text(HTML, encoding="utf-8")
    doc, _ = process_single(
        tmp_path / "d.html", None,
        parser_name="html", max_chars=200)
    h = [e for e in doc.elements
         if e.type == "heading"][0]
    assert h.metadata["level"] == 1


def test_md_sub_level_two(tmp_path):
    (tmp_path / "d.md").write_text(MD, encoding="utf-8")
    doc, _ = process_single(
        tmp_path / "d.md", None,
        parser_name="markdown", max_chars=200)
    hs = [e for e in doc.elements
          if e.type == "heading"]
    assert [h.metadata["level"] for h in hs] == [1, 2]


# ---------- evaluation 版本核 ----------

def test_evaluator_version_value():
    from evaluation import EVALUATOR_VERSION
    assert EVALUATOR_VERSION == "1.1"


def test_report_version_value():
    from evaluation import REPORT_VERSION
    assert REPORT_VERSION == "1.1"


def test_evaluator_version_no_schema_const():
    rs = json.loads(Path(
        "schemas/evaluation-report.schema.json"
    ).read_text(encoding="utf-8"))
    ev = rs["$defs"]["provenance"]["properties"][
        "evaluator_version"]
    assert "const" not in ev


def test_report_version_schema_const():
    from evaluation import REPORT_VERSION
    rs = json.loads(Path(
        "schemas/evaluation-report.schema.json"
    ).read_text(encoding="utf-8"))
    assert rs["properties"]["report_version"][
        "const"] == REPORT_VERSION == "1.1"
