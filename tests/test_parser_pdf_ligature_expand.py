"""PDF pdfplumber 连字展开 expand_ligatures（Round 2013，a 优先级）。

pdfplumber/utils/text.py:34 LIGATURES 七映射（ﬀ→ff ﬃ→ffi
ﬄ→ffl ﬁ→fi ﬂ→fl ﬆ→st ﬅ→st），:476 默认展开进 word 文本。
连字字符需 /Encoding /Differences 字形名重映射进 PDF
（edges85 锁过 /Beta /euro 一般重映射，连字字形名 parser 侧
零覆盖——grep 实证 ligature 命中全在 evaluation gold 对照）。
探针 R2013 实证：

- **T1 fi/fl**：`[97 /fi /fl]` + `(ab)` → 字符 ﬁﬂ → 词文本
  **'fifl'**（展开拼接），宽度按字形名查表 500/1000 →
  bbox [100,82.484,112.0,94.484]
- **T2 ff/ffi/ffl 零宽陷阱**：字形在 Helvetica AFM 无宽度
  条目 → 宽度 0 → 三字符全部停在 x=100 → 词文本照常展开
  'ffffiffl' 但 **bbox 退化 x0==x1==100**、零告警
- **T3 'st' 非 AGL 名**：`[102 /st]` + `(f)` → Differences
  条目被静默丢弃、码位 102 走基础编码 'f'（宽 3.336），
  无 (cid:) 占位、零告警

判别式：T1 若 'ﬁﬂ' 未展开翻；T2 若 bbox 非零宽或文本缺段
翻；T3 若 'st' 生效或出 (cid:102) 翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(differences: bytes, text: bytes):
    content = b"BT /F1 12 Tf 100 700 Td (" + text + b") Tj ET"
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica"
            b" /Encoding << /Differences [" + differences + b"] >> >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
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
        p = Path(td) / "l.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_fi_fl_expanded():
    """T1：ﬁﬂ → 'fifl'，宽度按字形名 500/1000 查表。"""
    d = _parse(b"97 /fi /fl", b"ab")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "fifl"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 112.0, 94.484], abs=0.01)
    assert d.warnings == []


def test_ff_family_zero_width_degenerate_bbox():
    """T2：ff/ffi/ffl 无 AFM 宽度 → 文本照常展开但 bbox 退化 x0==x1。"""
    d = _parse(b"99 /ff /ffi /ffl", b"cde")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ffffiffl"
    bbox = d.elements[0].source_locator["bbox"]
    assert bbox == pytest.approx([100.0, 82.484, 100.0, 94.484], abs=0.01)
    assert d.warnings == []


def test_st_not_in_agl_dropped():
    """T3：'st' 非 AGL 名 → Differences 条目丢弃、码位走基础编码 'f'。"""
    d = _parse(b"102 /st", b"f")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "f"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 103.336, 94.484], abs=0.01)
    assert d.warnings == []
