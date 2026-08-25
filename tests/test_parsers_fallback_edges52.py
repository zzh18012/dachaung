r"""app/parsers/fallback_parser.py 边角测试 - 第五十二轮（Round 1446）。

新角度（probe 实证）增量更新 + 尾部追加（历史 PDF 全是
单代单 %%EOF，修订链从未碰过）：
- 规范增量更新（新版 obj 4 + 子段 xref + trailer 带 /Prev
  指向旧 xref）：**修订版胜出**——'Revised revision text'
  替换 'Original revision'，旧流不被读
- 增量更新**缺 /Prev**：整文档不可用 → 0 元素 +
  pdf_no_text_extracted（trailer 链断裂连 /Root 都找不到）
- %%EOF 后追加**未被引用的**孤儿对象（6 0 obj 字体）：
  完全容忍——原内容照常提取，无告警
- 前提细节：追加流必须动态 /Length（错长度 → 整流静默
  丢失，与 R1428/R1445 一致）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build_base(content4):
    objs = {
        5: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] "
            b"/Count 1 >>"),
        3: (b"<< /Type /Page /Parent "
            b"2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(content4)).encode()
            + b" >>\nstream\n" + content4
            + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n"
                .encode()
                + objs[oid]
                + b"\nendobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n" \
        b"0000000000 65535 f \n"
    for oid in range(1, 6):
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size 6 "
            b"/Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out), xref_pos


def _revise(prev=True):
    base, xref1 = _build_base(
        b"BT /F1 12 Tf 72 700 Td "
        b"(Original revision) "
        b"Tj ET")
    c4 = (b"BT /F1 12 Tf 72 700 Td "
          b"(Revised revision text)"
          b" Tj ET")
    new4 = (b"<< /Length "
            + str(len(c4)).encode()
            + b" >>\nstream\n" + c4
            + b"\nendstream")
    rev = bytearray(base)
    new4_off = len(rev)
    rev += b"4 0 obj\n" + new4 \
        + b"\nendobj\n"
    xref2 = len(rev)
    rev += (b"xref\n4 1\n"
            b"%010d 00000 n \n"
            % new4_off)
    prev_part = (b" /Prev "
                 + str(xref1).encode()
                 if prev else b"")
    rev += (b"trailer\n<< /Size 6"
            b" /Root 1 0 R"
            + prev_part
            + b" >>\nstartxref\n"
            + str(xref2).encode()
            + b"\n%%EOF")
    return bytes(rev)


# ---------- 规范增量更新 ----------

def test_incremental_prev_wins(
        tmp_path):
    p = tmp_path / "incr.pdf"
    p.write_bytes(_revise(prev=True))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Revised revision text"]
    assert doc.warnings == []


def test_incremental_prev_bbox(
        tmp_path):
    p = tmp_path / "incrb.pdf"
    p.write_bytes(_revise(prev=True))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        182.7, 94.48400000000004]


def test_incremental_prev_schema(
        tmp_path):
    from app.schema import is_valid
    p = tmp_path / "incrs.pdf"
    p.write_bytes(_revise(prev=True))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_incremental_prev_chunk(
        tmp_path):
    p = tmp_path / "incrc.pdf"
    p.write_bytes(_revise(prev=True))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == \
        "Revised revision text"


# ---------- 缺 /Prev ----------

def test_incremental_no_prev_dead(
        tmp_path):
    p = tmp_path / "np.pdf"
    p.write_bytes(_revise(prev=False))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


def test_incremental_no_prev_pipe(
        tmp_path):
    p = tmp_path / "npp.pdf"
    p.write_bytes(_revise(prev=False))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]


# ---------- 尾部孤儿对象 ----------

def _append_orphan():
    base, _ = _build_base(
        b"BT /F1 12 Tf 72 700 Td "
        b"(Keep me) Tj ET")
    rev = bytearray(base)
    rev += (b"6 0 obj\n<< /Type /Font"
            b" /Subtype /Type1"
            b" /BaseFont /Courier >>"
            b"\nendobj\n%%EOF")
    return bytes(rev)


def test_orphan_appended_ok(
        tmp_path):
    p = tmp_path / "orph.pdf"
    p.write_bytes(_append_orphan())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Keep me"]
    assert doc.warnings == []


def test_orphan_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = tmp_path / "orphs.pdf"
    p.write_bytes(_append_orphan())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_orphan_chunk(tmp_path):
    p = tmp_path / "orphc.pdf"
    p.write_bytes(_append_orphan())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "Keep me"
