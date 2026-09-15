r"""PDF Type0 竖排 Identity-V 与 W2/DW2（Round 2000，a 优先级）。

Identity-V（WMode=1，cmapdb.py:292）与竖排分支
（pdffont.py:1163-1173 widths2/get_widths2、DW2 默认
[880,-1000]、default_disp=(None,vy)）零覆盖。探针 R2000
（含逐字符盒诊断）实证：

- **T1 竖排默认 DW2**：无 W2 → w=-1000 → 每字 12pt 盒
  向下堆叠（A 90.56..102.56、B 102.56..114.56 恰相接）
  → 'A B'（不重叠=两"行"以空格连接）、bbox
  [94, 90.56, 106, 114.56]（vx=None → 半宽 6 → x0=94）
- **T2 /DW2 [900 -600]**：w=-600 → 7.2pt 盒（90.8..98
  ..105.2）→ 'A B'、高 14.4
- **T3 /W2 数组态截断**：[1 [500 300 700 300]] →
  choplist(3,) **丢不完整尾**（尾 300 消失）→ 仅 CID1
  得 (w=500,disp(300,700))；adv=+6 **正号上移原点**；
  CID2 回退 (None,880)+w-1000；两字 y 重叠 → 合并单词
  **'BA'**（x 排序 B 94 < A 96.4）、bbox
  [94, 82.4, 108.4, 96.56]
- **T4 /W2 五元组范围态**：[1 2 500 300 700] → 两 CID
  同 (500,(300,700)) → B 叠 A 正上方（B bottom 82.4 ==
  A top）→ 'B A'、bbox [96.4, 76.4, 108.4, 88.4]
- **T5 横排对照**：同字体 Identity-H → 'AB' 水平
  [100, 80, 124, 92]（R1999 基线）

判别式：竖排走横排位移则 T5 翻；DW2 不参与则 T2 与 T1
同值翻；数组态不丢尾则 T3 的 B 变 3.6pt 盒翻；正 adv 若
按绝对值下移则 T3/T4 的 B 在 A 下方翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(encoding: bytes, extra: bytes, hex_text: str):
    tu = (f"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
          "begincmap\n/CIDSystemInfo << /Registry (Adobe)"
          " /Ordering (UCS) /Supplement 0 >> def\n"
          "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
          "1 begincodespacerange\n<0000> <ffff>\n"
          "endcodespacerange\n"
          "2 beginbfchar\n<0001> <0041>\n<0002> <0042>\n"
          "endbfchar\n"
          "endcmap\nCMapName currentdict /CMap defineresource"
          " pop\nend\nend").encode()
    content = f"BT /F1 12 Tf 100 700 Td <{hex_text}> Tj ET".encode()
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Type /Font /Subtype /Type0 /BaseFont /Test"
            b" /Encoding " + encoding
            + b" /DescendantFonts [ << /Type /Font"
            b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
            b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
            b" /Supplement 0 >> /CIDToGIDMap /Identity" + extra
            + b" >> ] /ToUnicode 7 0 R >>"),
        7: (b"<< /Length " + str(len(tu)).encode()
            + b" >>\nstream\n" + tu + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.5\n")
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
        p = Path(td) / "v.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


_V = b"/Identity-V"
_H = b"/Identity-H"


def _heading(d):
    assert [e.type for e in d.elements] == ["heading"]
    return d.elements[0]


def test_vertical_default_dw2_stacks_down():
    """T1：无 W2 → 每字 12pt 向下堆叠 → 'A B' [94, 90.56, 106, 114.56]。"""
    d = _build(_V, b"", "00010002")
    e = _heading(d)
    assert e.content == "A B"
    assert e.source_locator["bbox"] == pytest.approx(
        [94.0, 90.56, 106.0, 114.56], abs=0.01)
    assert d.warnings == []


def test_vertical_dw2_custom_spacing():
    """T2：/DW2 [900 -600] → 7.2pt 盒 → 'A B' 高 14.4。"""
    d = _build(_V, b" /DW2 [900 -600]", "00010002")
    e = _heading(d)
    assert e.content == "A B"
    assert e.source_locator["bbox"] == pytest.approx(
        [94.0, 90.8, 106.0, 105.2], abs=0.01)
    assert d.warnings == []


def test_vertical_w2_array_truncates_tail():
    """T3：数组态丢不完整尾 → 仅 CID1 映射；正 adv 上移 → 'BA' 合并单词。"""
    d = _build(_V, b" /W2 [1 [500 300 700 300]]", "00010002")
    e = _heading(d)
    assert e.content == "BA"
    assert e.source_locator["bbox"] == pytest.approx(
        [94.0, 82.4, 108.4, 96.56], abs=0.01)
    assert d.warnings == []


def test_vertical_w2_range_both_cids():
    """T4：五元组范围态两 CID 同参数 → B 叠 A 上 → 'B A'。"""
    d = _build(_V, b" /W2 [1 2 500 300 700]", "00010002")
    e = _heading(d)
    assert e.content == "B A"
    assert e.source_locator["bbox"] == pytest.approx(
        [96.4, 76.4, 108.4, 88.4], abs=0.01)
    assert d.warnings == []


def test_horizontal_contrast():
    """T5：同字体 Identity-H 对照 → 'AB' 水平 [100, 80, 124, 92]。"""
    d = _build(_H, b"", "00010002")
    e = _heading(d)
    assert e.content == "AB"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []
