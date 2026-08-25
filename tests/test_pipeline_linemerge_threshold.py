r"""pipeline 行合并间距阈值 = 2.5×字号（Round 1589）。

新角度：R1570 锁 20pt 合并/100pt 分离两端——
**阈值精确边界与字号缩放**零覆盖：

- **fs10**：间距 25 → 合并单元素、26 → 3 元素
- **fs20**：50 → 合并、51 → 分离（阈值随字号线性）
- **fs5**：12 → 合并、13 → 分离
- 统一规律：合并 ⟺ 间距 ≤ 2.5 × font_size
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


def _three_lines(gap: int, fs: int):
    parts = []
    y = 750
    for i in range(3):
        parts.append(
            f"BT /F1 {fs} Tf 72 {y}"
            f" Td (L{i}) Tj ET")
        y -= gap
    return " ".join(parts)


def _run(tmp_path, gap, fs):
    p = _pdf(
        tmp_path, f"g{gap}f{fs}.pdf",
        _three_lines(gap, fs))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    return doc


def test_fs10_boundary(tmp_path):
    d25 = _run(tmp_path, 25, 10)
    assert len(d25.elements) == 1
    assert d25.elements[0].content \
        == "L0 L1 L2"
    d26 = _run(tmp_path, 26, 10)
    assert [e.content
            for e in d26.elements] == [
        "L0", "L1", "L2"]


def test_fs20_scales(tmp_path):
    d50 = _run(tmp_path, 50, 20)
    assert len(d50.elements) == 1
    assert d50.elements[0].content \
        == "L0 L1 L2"
    d51 = _run(tmp_path, 51, 20)
    assert [e.content
            for e in d51.elements] == [
        "L0", "L1", "L2"]


def test_fs5_boundary(tmp_path):
    d12 = _run(tmp_path, 12, 5)
    assert len(d12.elements) == 1
    d13 = _run(tmp_path, 13, 5)
    assert [e.content
            for e in d13.elements] == [
        "L0", "L1", "L2"]
