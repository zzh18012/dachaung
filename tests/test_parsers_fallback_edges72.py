r"""app/parsers/fallback_parser.py PDF 边角测试 - 第七十二轮（Round 1495）。

新角度（probe 实证）多页 PDF + 字符串转义（edges1-71 未
碰；此前所有轮都是单页 scaffold）：

- **两页顺序保留**：page one → page two 各自成元素、
  无页码元数据（element metadata 无 page 字段）
- **⚠ 页内按 y 升序（自下而上）**：同页 bottom(y=100)
  先于 top(y=700) → ['bottom','top','top2']——R1494 的
  tr3 顺序倒置同根因，非渲染模式影响；跨页仍按页序
- **转义括号**：'a\\(b\\)c' → 'a(b)c'
- **八进制转义**：'\\053' → '+'（WinAnsi 解码）
- **转义反斜杠**：'a\\\\b' → 'a\\b'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _pdf_pages(tmp_path, name, contents):
    n = len(contents)
    kids = " ".join(
        f"{3 + 2 * i} 0 R"
        for i in range(n))
    objs = [
        "%PDF-1.4\n1 0 obj\n"
        "<< /Type /Catalog"
        " /Pages 2 0 R >>\nendobj\n",
        f"2 0 obj\n<< /Type /Pages"
        f" /Kids [{kids}]"
        f" /Count {n} >>\nendobj\n",
    ]
    font_num = 3 + 2 * n
    for i, content in enumerate(
            contents):
        page_num = 3 + 2 * i
        cont_num = 4 + 2 * i
        objs.append(
            f"{page_num} 0 obj\n"
            f"<< /Type /Page"
            f" /Parent 2 0 R"
            f" /MediaBox [0 0 612 792]"
            f" /Resources << /Font"
            f" << /F1 {font_num} 0 R"
            f" >> >>"
            f" /Contents {cont_num} 0 R"
            f" >>\nendobj\n")
        objs.append(
            f"{cont_num} 0 obj\n"
            f"<< /Length {len(content)}"
            f" >>\nstream\n{content}\n"
            f"endstream\nendobj\n")
    objs.append(
        f"{font_num} 0 obj\n"
        f"<< /Type /Font"
        f" /Subtype /Type1"
        f" /BaseFont /Helvetica"
        f" /Encoding /WinAnsiEncoding"
        f" >>\nendobj\n")
    objs.append(
        f"trailer\n<< /Root 1 0 R"
        f" /Size {font_num + 1}"
        f" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(
        "".join(objs).encode("latin-1"))
    return p


def _parse(p):
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 多页 ----------

def test_two_pages_order_preserved(
        tmp_path):
    p = _pdf_pages(
        tmp_path, "two.pdf",
        ["BT /F1 12 Tf 72 700 Td"
         " (page one) Tj ET",
         "BT /F1 12 Tf 72 700 Td"
         " (page two) Tj ET"])
    doc = _parse(p)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "page one"),
        ("heading", "page two"),
    ]
    assert all(
        "page" not in e.metadata
        for e in doc.elements)
    assert doc.warnings == []


def test_within_page_ascending_y(
        tmp_path):
    p = _pdf_pages(
        tmp_path, "yy.pdf",
        ["BT /F1 12 Tf 72 700 Td"
         " (top) Tj 72 100 Td"
         " (bottom) Tj ET",
         "BT /F1 12 Tf 72 700 Td"
         " (top2) Tj ET"])
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "bottom", "top", "top2",
    ]
    assert doc.warnings == []


# ---------- 字符串转义 ----------

def test_escaped_parens(tmp_path):
    p = _pdf(
        tmp_path, "ep.pdf",
        r"BT /F1 12 Tf 72 700 Td"
        r" (a\(b\)c) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "a(b)c",
    ]


def test_octal_escape(tmp_path):
    p = _pdf(
        tmp_path, "oc.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (a\\053b) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "a+b",
    ]


def test_escaped_backslash(tmp_path):
    p = _pdf(
        tmp_path, "eb.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (a\\\\b) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "a\\b",
    ]
