r"""PDF 线框表跨列/跨行——不均匀行（Round 1997，a 优先级）。

既有 PDF 表格夹具行宽全均匀（2×2/3×3 网格，col_count 测试
3 处）；跨列（中间竖线只画上半）与跨行（横线只画左列）的
**不均匀行**零覆盖——_rows_to_markdown 尾部补空
（fallback_parser.py:66）从未被 PDF 端真实几何触发。探针
R1997 实证：

- **T1 跨列**：竖线只画顶行 → 顶行 [A][B]、底行单宽格
  [SPAN] → '| SPAN |  |'（尾补空）、col_count=2
- **T2 跨行**：横线只画左列 → 行结构 [C1, D]/[C2]——高格
  D **按上边缘归入第一行**，第二行 [C2] 尾补空
- **T3 表头窄于正文**：竖线只画底行 → 表头 [H] 单格 →
  '| H |  |'（**表头行**补空），分隔行按最大宽两列 '---'

判别式：若 pdfplumber 按最大网格补 None 占位 → 空串 vs
None 的取值差异实证锁定；若宽格被漏检 → 行丢失/表不成立
翻红；若分隔行宽度跟表头走（1 列）则 T3 翻红（实际按最
大宽 2 列）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(content: bytes):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode()
            + b"\n%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _txt(x: float, y: float, s: str) -> bytes:
    return f"BT /F1 10 Tf {x} {y} Td ({s}) Tj ET\n".encode()


_RECT = b"100 600 m 400 600 l 400 700 l 100 700 l h S\n"


def _table_of(d):
    tbls = [e for e in d.elements if e.type == "table"]
    assert len(tbls) == 1
    return tbls[0]


def test_colspan_row_padded_tail():
    """T1：跨列宽格 → 底行 '| SPAN |  |' 尾补空。"""
    d = _parse(_RECT
               + b"100 650 m 400 650 l S\n"
               + b"250 650 m 250 700 l S\n"
               + _txt(120, 660, "A") + _txt(270, 660, "B")
               + _txt(200, 615, "SPAN"))
    tbl = _table_of(d)
    assert tbl.content == "| A | B |\n| --- | --- |\n| SPAN |  |"
    assert tbl.metadata["row_count"] == 2
    assert tbl.metadata["col_count"] == 2
    assert d.warnings == []


def test_rowspan_tall_cell_in_first_row():
    """T2：跨行高格按上边缘归第一行 → [C1, D]/[C2]。"""
    d = _parse(_RECT
               + b"250 600 m 250 700 l S\n"
               + b"100 650 m 250 650 l S\n"
               + _txt(120, 660, "C1") + _txt(120, 612, "C2")
               + _txt(280, 640, "D"))
    tbl = _table_of(d)
    assert tbl.content == "| C1 | D |\n| --- | --- |\n| C2 |  |"
    assert tbl.metadata["row_count"] == 2
    assert tbl.metadata["col_count"] == 2
    assert d.warnings == []


def test_narrow_header_padded_to_max_width():
    """T3：表头窄于正文 → 表头行补空，分隔行按最大宽。"""
    d = _parse(_RECT
               + b"100 650 m 400 650 l S\n"
               + b"250 600 m 250 650 l S\n"
               + _txt(210, 660, "H") + _txt(120, 612, "X")
               + _txt(280, 612, "Y"))
    tbl = _table_of(d)
    assert tbl.content == "| H |  |\n| --- | --- |\n| X | Y |"
    assert tbl.metadata["row_count"] == 2
    assert tbl.metadata["col_count"] == 2
    assert d.warnings == []
