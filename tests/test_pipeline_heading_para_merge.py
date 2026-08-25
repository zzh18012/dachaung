r"""pipeline heading 与后续段落的累积边界（Round 1595）。

新角度：R1559 锁 DOCX 标题段合并、R1592 锁段落间
累积——**heading × 超长段落**交互零覆盖：

- **heading(19) + 小段落(139)** → 合并单 chunk
  159、ids [1,2]、strategy sequential
- **heading(19) + 超长段落(899)** → 合并会超
  max_chars → heading **独立成 sequential chunk**、
  段落自行走 sentence_split [797, 101]；heading
  内容不渗入段落 chunk
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, name: str,
         c: str) -> Path:
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
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _words(n: int, tag: str) -> str:
    out = []
    total = 0
    i = 0
    while total < n:
        w = f"{tag}{i:04d}"
        out.append(w)
        total += len(w) + 1
        i += 1
    return " ".join(out)[:n]


def _run(tmp_path, para):
    c = (f"BT /F1 14 Tf 72 750"
         f" Td (Chapter One Heading)"
         f" Tj ET BT /F1 10 Tf 72"
         f" 500 Td ({para})"
         f" Tj ET")
    p = _pdf(tmp_path, "hp.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.type
            for e in doc.elements] == [
        "heading", "paragraph"]
    return doc


def test_heading_small_para_merged(
        tmp_path):
    para = " ".join(
        f"wd{i:04d}" for i in range(20))
    doc = _run(tmp_path, para)
    got = [(len(c.text),
            len(c.source_element_ids),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [(159, 2,
                    "sequential")]
    assert doc.chunks[0].text == (
        "Chapter One Heading " + para)


def test_heading_oversize_para_split(
        tmp_path):
    para = _words(900, "p")
    doc = _run(tmp_path, para)
    got = [(len(c.text),
            len(c.source_element_ids),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [
        (19, 1, "sequential"),
        (797, 1,
         "long_paragraph_sentence_split"),
        (101, 1,
         "long_paragraph_sentence_split")]
    assert doc.chunks[0].text == (
        "Chapter One Heading")
    assert not any(
        "Chapter" in c.text
        for c in doc.chunks[1:])
