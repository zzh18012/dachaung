r"""pipeline sequential 累积的精确 800 边界（Round 1592）。

新角度：R1570 锁 595 合并/893 开新——**计入分隔符
的精确边界**零覆盖：

- **400 + 400** → 中间 1 字分隔符使合并长 801 >
  800 → 不合并、两独立 chunk
- **399 + 400** → 合并长恰 800 → 单 chunk 覆盖
  2 元素
- **398 + 401** → 同为 800 → 合并（和恒定、与顺序
  无关）

合并条件：已累积 + 1（分隔符） + 下一元素 ≤
max_chars。
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


def _word(n: int, tag: str) -> str:
    w = tag
    while len(w) < n:
        w += "x"
    return w[:n]


def _run(tmp_path, a, b):
    parts = []
    y = 750
    for i, n in enumerate((a, b)):
        parts.append(
            f"BT /F1 10 Tf 72 {y}"
            f" Td ({_word(n, chr(97 + i))})"
            f" Tj ET")
        y -= 100
    p = _pdf(tmp_path,
             f"t{a}_{b}.pdf",
             " ".join(parts))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    return doc


def test_400_400_not_merged(tmp_path):
    doc = _run(tmp_path, 400, 400)
    got = [(len(c.text),
            len(c.source_element_ids),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [(400, 1, "sequential"),
                   (400, 1,
                    "sequential")]


def test_399_400_merged_exact(
        tmp_path):
    doc = _run(tmp_path, 399, 400)
    got = [(len(c.text),
            len(c.source_element_ids),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [(800, 2,
                    "sequential")]


def test_398_401_merged_exact(
        tmp_path):
    doc = _run(tmp_path, 398, 401)
    got = [(len(c.text),
            len(c.source_element_ids),
            c.metadata["strategy"])
           for c in doc.chunks]
    assert got == [(800, 2,
                    "sequential")]
