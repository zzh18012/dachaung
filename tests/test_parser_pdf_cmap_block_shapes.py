r"""PDF ToUnicode CMap 源块形态变体（Round 1995，a 优先级）。

edges87 只锁 bfrange 连续 dst 起点（<0010><0012><0061>）；
R1994 锁 bfchar dst 形态。CMap **源块**侧形态零覆盖。探针
R1995 实证（cmapdb.py ENDBFRANGE/ENDCIDRANGE 源码对照）：

- **T1 bfrange 数组 dst**（规范第三形态）：<0010><0011>
  [<0041><0042>] → 'AB'——每码点显式列出（zip 配对，非连
  续 dst 起点重复）
- **T2 数组 dst 变长条目**：[<00410042> <D83DDE00>] →
  'AB\U0001F600'——数组路径同样走 UTF-16BE 变长解码
  （cmapdb.py:190 decode("UTF-16BE", "ignore")）
- **T3 多 bfchar 块合并**：两个独立 beginbfchar/endbfchar
  块（真实 PDF >100 条目分块写法）→ 全部条目生效 'XY'
- **T4 cidrange 块混入 ToUnicode**：begincidrange（CID
  CMap 专用块）**不被忽略**——ENDCIDRANGE 同样调
  add_cid2unichr，把范围基址 CID 映到**码点字节按 UTF-16BE
  解**：<0030><0031> 49 → CID49→b'\\x00\\x30'→'0'、
  CID50→'1'；文本 <00300031>（CID 48/49）→ '(cid:48)0'
  （48 未映射占位 + 49 意外命中）

判别式：数组 dst 若按连续 dst 解析 T1 得 'AA'；变长若定长
切 T2 拆代理；多块若只留末块 T3 首条目翻 (cid:N)；cidrange
若被忽略 T4 得 '(cid:48)(cid:49)'。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(hex_text: str, blocks: str):
    tu = (f"/CIDInit /ProcSet findresource begin\n12 dict begin\n"
          "begincmap\n/CIDSystemInfo << /Registry (Adobe)"
          " /Ordering (UCS) /Supplement 0 >> def\n"
          "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n"
          "1 begincodespacerange\n<0000> <ffff>\n"
          "endcodespacerange\n"
          f"{blocks}"
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
            b" /Encoding /Identity-H /DescendantFonts [ << /Type /Font"
            b" /Subtype /CIDFontType2 /BaseFont /Test /DW 1000"
            b" /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity)"
            b" /Supplement 0 >> /CIDToGIDMap /Identity >> ]"
            b" /ToUnicode 7 0 R >>"),
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
        p = Path(td) / "c.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_bfrange_array_dst():
    """T1：bfrange 数组 dst 显式逐码点配对 → 'AB'。"""
    d = _build("00100011", "1 beginbfrange\n<0010> <0011> "
              "[<0041> <0042>]\nendbfrange\n")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_bfrange_array_dst_varlen_entries():
    """T2：数组 dst 变长条目走 UTF-16BE → 'AB\\U0001F600'。"""
    d = _build("00100011", "1 beginbfrange\n<0010> <0011> "
              "[<00410042> <D83DDE00>]\nendbfrange\n")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AB\U0001F600"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_two_bfchar_blocks_merge():
    """T3：两个独立 bfchar 块全部生效 → 'XY'。"""
    d = _build("00200021",
               "1 beginbfchar\n<0020> <0058>\nendbfchar\n"
               "1 beginbfchar\n<0021> <0059>\nendbfchar\n")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "XY"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_cidrange_block_maps_cid_to_code_bytes():
    """T4：cidrange 不被忽略——CID 映到码点字节 UTF-16BE 解。"""
    d = _build("00300031",
               "1 begincidrange\n<0030> <0031> 49\nendcidrange\n")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "(cid:48)0"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 124.0, 92.0], abs=0.01)
    assert d.warnings == []
