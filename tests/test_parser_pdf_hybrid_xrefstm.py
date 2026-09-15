r"""PDF 混合引用文件（classic 表 + /XRefStm 流）单侧损伤恢复（Round 1974，a 优先级）。

PDF 1.5 hybrid 文件：老阅读器用 classic 表、新阅读器用流；
真实世界增量更新/修复工具产物。广扫 tests/ 零 XRefStm 匹
配。探针 R1974 实证 + pdfdocument.py 源码确认（read_xref_from
按 trailer /XRefStm 递归把流加入 xrefs 列表；getobj 对每个
xref 逐个尝试，KeyError 或 PSEOF/PDFSyntaxError 均 continue）：

- **H1 双表一致**（对照）→ 正常提取零告警
- **H2 classic 条目全零 + 流正确** → **全恢复**——classic
  表 pos 0 解析失败后由流条目接管（R1972 X2 同形损伤在
  纯 classic 文件是静默全丢，hybrid 提供了第二来源）
- **H3 classic 正确 + 流条目全零** → 全恢复——classic 先入
  xrefs 列表先命中，流根本不被用到
- **H4 双侧全零** → 零元素 + pdf_no_text_extracted——
  per-object 跨 xref 重试穷尽，PDFXRefFallback 不接管
  （它只在初始化期 PDFNoValidXRef 时启用）

判别式：若 getobj 改为首个 xref 即判死则 H2 翻红；若条目
级失败也触发 PDFXRefFallback 暴力扫描则 H4 恢复翻红；若
流先于 classic 消费则 H3 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(mode: str):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    body = b"BT /F1 12 Tf 100 700 Td (HYBRID) Tj ET"
    objs[4] = (b"<< /Length " + str(len(body)).encode()
               + b" >>\nstream\n" + body + b"\nendstream")

    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"

    xref_stm_off = len(out)
    offsets[6] = xref_stm_off
    entries = [bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")]
    for oid in range(1, 7):
        off = offsets[oid]
        if mode in ("stream-bad", "both-bad"):
            off = 0
        entries.append(bytes([1]) + off.to_bytes(4, "big")
                       + (0).to_bytes(2, "big"))
    sdata = b"".join(entries)
    out += (b"6 0 obj\n<< /Type /XRef /Size 7 /W [1 4 2] /Root 1 0 R"
            + b" /Length " + str(len(sdata)).encode()
            + b" >>\nstream\n" + sdata + b"\nendstream\nendobj\n")

    xref_off = len(out)
    out += b"xref\n0 7\n" + b"0000000000 65535 f \n"
    for oid in range(1, 7):
        off = offsets[oid]
        if mode in ("classic-bad", "both-bad"):
            off = 0
        out += ("%010d 00000 n \n" % off).encode()
    out += (b"trailer\n<< /Size 7 /Root 1 0 R /XRefStm "
            + str(xref_stm_off).encode()
            + b" >>\nstartxref\n" + str(xref_off).encode()
            + b"\n%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "h.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_recovered(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "HYBRID"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 145.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_agree_control():
    """H1：双表一致 → 正常提取零告警。"""
    _assert_recovered(_build("agree"))


def test_classic_zeroed_stream_recovers():
    """H2：classic 全零 + 流正确 → 流接管全恢复（纯 classic 文
    件同形损伤是静默全丢，见 R1972）。"""
    _assert_recovered(_build("classic-bad"))


def test_stream_zeroed_classic_recovers():
    """H3：classic 正确 + 流全零 → classic 先入 xrefs 列表先命
    中，全恢复。"""
    _assert_recovered(_build("stream-bad"))


def test_both_sides_zeroed_total_loss():
    """H4：双侧全零 → 零元素 + pdf_no_text_extracted——跨
    xref 重试穷尽，PDFXRefFallback 不接管。"""
    d = _build("both-bad")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]
