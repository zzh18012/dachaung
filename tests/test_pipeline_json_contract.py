r"""pipeline 写盘 JSON 契约（Round 1558）。

新角度：schema 校验保证字段**存在**，但写盘产物的
**顶层键集、source_path 形态、metadata 内容、表格→
markdown chunk 原文**未在 pipeline 层锁定：

- **source_path** == str(输入绝对路径)
- **顶层键集**恰为 13 键（无多余键漂移）
- **metadata**：fallback=True、image_output_dir 以
  images-<sha16> 结尾；parser_version 含库版本号
- **表格元素 → 原样 markdown chunk**：`| a1 |  |`
  + `| --- | --- |` 分隔行，单一 source_element_ids
"""

from __future__ import annotations

import json
from pathlib import Path

from app.hash import compute_file_hash
from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, name: str,
         content: str) -> Path:
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\n"
        f"endstream",
        _FONT,
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_source_path_absolute(
        tmp_path):
    p = _pdf(tmp_path, "doc.pdf",
             "BT /F1 12 Tf 72 700 Td"
             " (BODY) Tj ET")
    out = tmp_path / "o.json"
    process_single(p, out, write_json=True)
    data = json.loads(
        out.read_text(encoding="utf-8"))
    assert data["source_path"] \
        == str(p)


def test_top_level_key_set(
        tmp_path):
    p = _pdf(tmp_path, "doc.pdf",
             "BT /F1 12 Tf 72 700 Td"
             " (BODY) Tj ET")
    out = tmp_path / "o.json"
    process_single(p, out, write_json=True)
    data = json.loads(
        out.read_text(encoding="utf-8"))
    assert set(data) == {
        "document_id", "source_type",
        "source_path", "source_hash",
        "parser_name", "parser_version",
        "schema_version", "elements",
        "chunks", "relations", "errors",
        "warnings", "metadata"}
    assert data["errors"] == []
    assert data["warnings"] == []
    assert data["relations"] == []


def test_metadata_fields(tmp_path):
    p = _pdf(tmp_path, "doc.pdf",
             "BT /F1 12 Tf 72 700 Td"
             " (BODY) Tj ET")
    out = tmp_path / "o.json"
    process_single(p, out, write_json=True)
    data = json.loads(
        out.read_text(encoding="utf-8"))
    assert data["parser_name"] \
        == "fallback"
    assert "pdfplumber=" \
        in data["parser_version"]
    assert data["metadata"][
        "fallback"] is True
    sha = compute_file_hash(p)[:16]
    assert data["metadata"][
        "image_output_dir"]\
        .endswith(f"images-{sha}")


def test_table_markdown_chunk(
        tmp_path):
    grid = " ".join(
        f"{x} {y} 100 30 re S"
        for x in (72, 172)
        for y in (650, 610))
    content = (grid
               + " BT /F1 10 Tf 80 655"
               " Td (a1) Tj ET"
               + " BT /F1 10 Tf 80 615"
               " Td (a2) Tj ET")
    p = _pdf(tmp_path, "tab.pdf",
             content)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    tabs = [c for c in doc.chunks
            if c.text.startswith("|")]
    assert [c.text for c in tabs] == [
        "| a1 |  |\n| --- | --- |",
        "| a2 |  |\n| --- | --- |"]
    for c in tabs:
        assert len(
            c.source_element_ids) == 1
