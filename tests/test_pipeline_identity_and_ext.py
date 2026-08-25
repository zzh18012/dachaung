r"""pipeline document_id 内容寻址 + 扩展名大小写（Round 1554）。

新角度："doc-"+sha16 前缀约定已有单测（test_pipeline_
helpers），但两个相邻不变量零覆盖：

- **document_id 内容寻址**：同字节不同文件名 → 同
  document_id（文件名不参与）；不同字节 → 不同 id
- **扩展名大小写不敏感**：`.PDF` / `.Docx` 不落入
  unsupported_type，正常解析出元素
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single
from tests._synthetic_docs import (
    build_minimal_docx, build_minimal_pdf,
)


def test_same_bytes_same_id(
        tmp_path):
    a = tmp_path / "a.pdf"
    build_minimal_pdf(a, text="(Hello)")
    b = tmp_path / "totally-different-name.pdf"
    b.write_bytes(a.read_bytes())
    da, ea = process_single(
        a, write_json=False)
    db, eb = process_single(
        b, write_json=False)
    assert ea == [] and eb == []
    assert da.document_id \
        == db.document_id


def test_different_bytes_different_id(
        tmp_path):
    a = tmp_path / "a.pdf"
    build_minimal_pdf(a, text="(Hello)")
    c = tmp_path / "c.pdf"
    build_minimal_pdf(c, text="(World)")
    da, _ = process_single(
        a, write_json=False)
    dc, _ = process_single(
        c, write_json=False)
    assert da.document_id \
        != dc.document_id


def test_uppercase_ext_pdf(
        tmp_path):
    p = tmp_path / "x.PDF"
    build_minimal_pdf(p, text="(Hello)")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert doc is not None
    assert doc.source_type == "pdf"
    assert doc.elements


def test_uppercase_ext_docx(
        tmp_path):
    p = tmp_path / "x.Docx"
    build_minimal_docx(p)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert doc is not None
    assert doc.source_type == "docx"
    assert doc.elements
