r"""pipeline 长段落切分的句子边界优先（Round 1591）。

新角度：R1570 锁无标点长段落的词边界切分——
**句子边界优先与逗号对照**零覆盖：

- **'. ' 句号分隔的 959 字段落** → 切在句边界
  [767, 191]：chunk0 以 '.' 结尾、chunk1 以
  'Sentence number 008' **整句开头**
- **', ' 逗号分隔的同长段落** → 无句界可用、退回
  词边界 [797, 161]：chunk0/1 均在句中
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


def _para(punct: str) -> str:
    sents = []
    total = 0
    i = 0
    while total < 900:
        s = (f"Sentence number {i:03d} "
             + "word " * 15).rstrip() \
            + punct + " "
        sents.append(s)
        total += len(s)
        i += 1
    return "".join(sents).strip()


def _run(tmp_path, name, para):
    p = _pdf(
        tmp_path, name,
        f"BT /F1 10 Tf 72 700"
        f" Td ({para}) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == para
    return doc


def test_period_splits_on_sentence(
        tmp_path):
    doc = _run(
        tmp_path, "s.pdf", _para("."))
    got = [(len(c.text),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [
        (767,
         "long_paragraph_sentence_split"),
        (191,
         "long_paragraph_sentence_split")]
    assert doc.chunks[0].text\
        .endswith("word.")
    assert doc.chunks[1].text\
        .startswith(
            "Sentence number 008")


def test_comma_falls_to_word_boundary(
        tmp_path):
    doc = _run(
        tmp_path, "c.pdf",
        _para(","))
    got = [(len(c.text),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [
        (797,
         "long_paragraph_sentence_split"),
        (161,
         "long_paragraph_sentence_split")]
    assert doc.chunks[0].text\
        .endswith("word word")
    assert doc.chunks[1].text\
        .startswith("word")
