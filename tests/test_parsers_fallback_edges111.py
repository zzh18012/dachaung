r"""app/parsers_fallback PDF 边角测试 - 第一百一十一轮（Round 1541）。

新角度（probe 实证）页树结构家族（此前轮次页树全为扁
平单层 Kids；真实 PDF 常见多层中间 /Pages 节点与属性
继承——零覆盖）：

- **多层嵌套中间 /Pages 节点**：Catalog→Pages→[中间
  Pages[叶,叶], 叶] → 三页按深度优先序提取（N1/N2/N3
  对应 page 1/2/3）
- **MediaBox/Resources 从父 /Pages 继承**：叶子页省略
  两属性 → 照常解析（I1/I2 双页）
- **/Count 5 实际 1 页** → 只按 /Kids 提取 1 页（Kids
  权威、Count 忽略）
- **同一页对象重复引用两次** → 只提取一次（单页）
- **空 Kids + Count 0** → 零页文档容忍：elements=[] +
  仅 pdf_no_text_extracted 警告（不崩溃）
- **缺失 /Count** → 照常提取
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _stream(txt: str) -> str:
    return (f"<< /Length {len(txt)} >>"
            f"\nstream\n{txt}\n"
            f"endstream")


def _parse(tmp_path, name, objs,
           size):
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                .encode("latin-1")
                + o + b"\nendobj\n")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size " + str(size).encode()
            + b" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return FallbackParser().parse(
        p, compute_file_hash(p))


def _leaf(parent: int,
          contents: int) -> str:
    return (f"<< /Type /Page"
            f" /Parent {parent} 0 R"
            f" /MediaBox [0 0 612 792]"
            f" /Resources << /Font"
            f" << /F1 5 0 R >> >>"
            f" /Contents {contents}"
            f" 0 R >>")


def test_nested_intermediate_nodes(
        tmp_path):
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [10 0 R 3 0 R]"
           " /Count 3 >>",
        10: "<< /Type /Pages"
            " /Parent 2 0 R"
            " /Kids [11 0 R 12 0 R]"
            " /Count 2 >>",
        11: _leaf(10, 21),
        12: _leaf(10, 22),
        3: _leaf(2, 23),
        21: _stream("BT /F1 12 Tf 72 700"
                    " Td (N1) Tj ET"),
        22: _stream("BT /F1 12 Tf 72 700"
                    " Td (N2) Tj ET"),
        23: _stream("BT /F1 12 Tf 72 700"
                    " Td (N3) Tj ET"),
        5: _FONT,
    }
    doc = _parse(tmp_path, "nested.pdf",
                 objs, 24)
    assert [(e.content,
             e.source_locator["page"])
            for e in doc.elements] == [
        ("N1", 1), ("N2", 2), ("N3", 3)]
    assert doc.warnings == []


def test_inherited_attributes(
        tmp_path):
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: ("<< /Type /Pages"
            " /Kids [3 0 R 4 0 R]"
            " /Count 2"
            " /MediaBox [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >> >>"),
        3: "<< /Type /Page"
           " /Parent 2 0 R"
           " /Contents 6 0 R >>",
        4: "<< /Type /Page"
           " /Parent 2 0 R"
           " /Contents 7 0 R >>",
        6: _stream("BT /F1 12 Tf 72 700"
                   " Td (I1) Tj ET"),
        7: _stream("BT /F1 12 Tf 72 700"
                   " Td (I2) Tj ET"),
        5: _FONT,
    }
    doc = _parse(tmp_path, "inherit.pdf",
                 objs, 8)
    assert [(e.content,
             e.source_locator["page"])
            for e in doc.elements] == [
        ("I1", 1), ("I2", 2)]
    assert doc.warnings == []


def test_count_mismatch(tmp_path):
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R] /Count 5 >>",
        3: _leaf(2, 4),
        4: _stream("BT /F1 12 Tf 72 700"
                   " Td (C5) Tj ET"),
        5: _FONT,
    }
    doc = _parse(tmp_path, "count5.pdf",
                 objs, 6)
    assert [(e.content,
             e.source_locator["page"])
            for e in doc.elements] == [
        ("C5", 1)]
    assert doc.warnings == []


def test_duplicate_page_ref(
        tmp_path):
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: ("<< /Type /Pages"
            " /Kids [3 0 R 3 0 R]"
            " /Count 2 >>"),
        3: _leaf(2, 4),
        4: _stream("BT /F1 12 Tf 72 700"
                   " Td (DUP) Tj ET"),
        5: _FONT,
    }
    doc = _parse(tmp_path, "dupref.pdf",
                 objs, 6)
    assert [(e.content,
             e.source_locator["page"])
            for e in doc.elements] == [
        ("DUP", 1)]
    assert doc.warnings == []


def test_empty_kids(tmp_path):
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [] /Count 0 >>",
    }
    doc = _parse(tmp_path, "nopages.pdf",
                 objs, 3)
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == [
        "pdf_no_text_extracted"]


def test_missing_count(tmp_path):
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R] >>",
        3: _leaf(2, 4),
        4: _stream("BT /F1 12 Tf 72 700"
                   " Td (NC) Tj ET"),
        5: _FONT,
    }
    doc = _parse(tmp_path, "nocount.pdf",
                 objs, 6)
    assert [(e.content,
             e.source_locator["page"])
            for e in doc.elements] == [
        ("NC", 1)]
    assert doc.warnings == []
