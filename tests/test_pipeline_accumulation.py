r"""pipeline 行距驱动的段落合并与累积分块（Round 1570）。

新角度：单段落 800 边界已锁（R1569）；**多段落**的
两条路径零覆盖：

- **近距行（20pt）** → pdfplumber 合并为**单元素**
 （3×297 → 893 字），再走长段落切分 [797, 95]
- **远距行（100pt）** → 3 个独立段落元素，chunker
  **顺序累积**：a+b=595 ≤800 合一 chunk，+c 超限
  开新 chunk → [595, 297]、strategy='sequential'、
  ids 计数 [2, 1]
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _para(n: int, tag: str) -> str:
    words, used = [], 0
    i = 0
    while True:
        w = f"{tag}{i}"
        need = (len(w) if used == 0
                else 1 + len(w))
        if used + need > n - 2:
            break
        words.append(w)
        used += need
        i += 1
    return " ".join(words)


def _pdf(tmp_path: Path, paras,
         gap: int) -> Path:
    parts = []
    y = 750
    for p in paras:
        parts.append(
            f"BT /F1 10 Tf 72 {y}"
            f" Td ({p}) Tj ET")
        y -= gap
    c = " ".join(parts)
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
    }
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o \
            + b"\nendobj\n"
    pdf += (b"trailer"
            b" << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / "m.pdf"
    p.write_bytes(pdf)
    return p


def test_close_lines_merge_single_element(
        tmp_path):
    paras = [_para(300, t)
             for t in "abc"]
    p = _pdf(tmp_path, paras, gap=20)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert len(el.content) == 893
    lengths = [len(c.text)
               for c in doc.chunks]
    assert lengths == [797, 95]
    assert all(
        c.metadata["strategy"]
        == "long_paragraph_"
           "sentence_split"
        for c in doc.chunks)


def test_far_lines_accumulate(
        tmp_path):
    paras = [_para(300, t)
             for t in "abc"]
    p = _pdf(tmp_path, paras, gap=100)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [len(e.content)
            for e in doc.elements] == [
        297, 297, 297]
    chunks = doc.chunks
    assert [len(c.text)
            for c in chunks] == [
        595, 297]
    assert [len(c.source_element_ids)
            for c in chunks] == [2, 1]
    assert chunks[0].text.\
        startswith("a0 ")
    assert chunks[0].text.\
        endswith(" b74 b75 b76")
    assert chunks[1].text.\
        startswith("c0 ")
    assert all(
        c.metadata["strategy"]
        == "sequential"
        for c in chunks)
