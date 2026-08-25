r"""pipeline/parse 确定性与幂等性测试（Round 1550）。

新角度：此前 100+ 轮全部验证**单次**行为——输出对同
一输入是否**可复现**（document_id、元素序、chunk_id、
写盘 JSON 字节级）零覆盖：

- **parse 两次全同**：document_id / element_id 序列 /
  content / bbox 逐一相等
- **pipeline 写盘字节级幂等**：两次 process_single 输出
  JSON 字节完全一致（无时间戳等噪声源）
- **多元素（文本+表格混合页）次序确定**：含表格页两
  次解析元素序列相同、chunk_id 序列相同
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
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
        " /Kids [3 0 R]"
        " /Count 1 >>",
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


def _sig(doc):
    return [
        (e.element_id, e.type, e.content,
         e.source_locator.get("bbox"))
        for e in doc.elements]


def test_parse_deterministic(tmp_path):
    p = _pdf(tmp_path, "doc.pdf",
             "BT /F1 12 Tf 72 700 Td"
             " (BODY text here) Tj ET")
    h = compute_file_hash(p)
    d1 = FallbackParser().parse(p, h)
    d2 = FallbackParser().parse(p, h)
    assert d1.document_id \
        == d2.document_id
    assert _sig(d1) == _sig(d2)


def test_pipeline_byte_identical(
        tmp_path):
    p = _pdf(tmp_path, "doc.pdf",
             "BT /F1 12 Tf 72 700 Td"
             " (BODY text here) Tj ET")
    o1 = tmp_path / "a.json"
    o2 = tmp_path / "b.json"
    _, e1 = process_single(
        p, o1, write_json=True)
    _, e2 = process_single(
        p, o2, write_json=True)
    assert e1 == [] and e2 == []
    assert o1.read_bytes() \
        == o2.read_bytes()


def test_mixed_page_order_deterministic(
        tmp_path):
    grid = " ".join(
        f"{x} {y} 100 30 re S"
        for x in (72, 172)
        for y in (650, 610))
    content = (grid
               + " BT /F1 10 Tf 80 655"
               " Td (a1) Tj ET"
               " BT /F1 10 Tf 80 615"
               " Td (a2) Tj ET")
    p = _pdf(tmp_path, "tab.pdf", content)
    h = compute_file_hash(p)
    d1 = FallbackParser().parse(p, h)
    d2 = FallbackParser().parse(p, h)
    assert _sig(d1) == _sig(d2)
    doc1, e1 = process_single(
        p, write_json=False)
    doc2, e2 = process_single(
        p, write_json=False)
    assert e1 == [] and e2 == []
    assert [c.chunk_id
            for c in doc1.chunks] == [
        c.chunk_id
        for c in doc2.chunks]
    assert [c.text
            for c in doc1.chunks] == [
        c.text for c in doc2.chunks]
