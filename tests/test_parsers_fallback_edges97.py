r"""app/parsers_fallback PDF 边角测试 - 第九十七轮（Round 1527）。

新角度（probe 实证）Unicode/空格/emoji 文件名与深层
目录（Windows GBK 环境下的真实边角；此前轮次文件名全
ASCII 单层）：

- **中文+空格文件名正常解析**：'测试 文档 v1.pdf' →
  提取照常、source_path 原样保留（不转义）
- **深层含空格/中文目录正常**：a b/中文/x y/deep.pdf
  → 照常
- **emoji 文件名正常**：'doc 📄 name.pdf' → 照常
- **document_id 与文件名无关**：同一字节内容两个不同
  文件名 → source_hash 与 document_id 完全相同（哈希
  只看内容）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _els(tmp_path, name):
    p = _pdf(
        tmp_path, name,
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return doc


def test_chinese_space_filename(
        tmp_path):
    doc = _els(
        tmp_path, "测试 文档 v1.pdf")
    assert [e.content
            for e in doc.elements] == [
        "BODY"]
    assert "测试 文档 v1.pdf" \
        in doc.source_path
    assert doc.warnings == []


def test_deep_mixed_dirs(tmp_path):
    deep = (tmp_path / "a b" / "中文"
            / "x y")
    deep.mkdir(parents=True)
    p = deep / "deep.pdf"
    src = _pdf(
        tmp_path, "tmp.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET")
    p.write_bytes(src.read_bytes())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "BODY"]
    assert doc.warnings == []


def test_emoji_filename(tmp_path):
    doc = _els(
        tmp_path, "doc 📄 name.pdf")
    assert [e.content
            for e in doc.elements] == [
        "BODY"]
    assert doc.warnings == []


def test_document_id_name_independent(
        tmp_path):
    d1 = _els(tmp_path, "alpha.pdf")
    d2 = _els(tmp_path, "贝塔 beta.pdf")
    assert d1.source_hash \
        == d2.source_hash
    assert d1.document_id \
        == d2.document_id
    assert d1.source_path \
        != d2.source_path
