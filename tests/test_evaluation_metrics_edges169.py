r"""evaluation/metrics.py 边角第一百六十九轮（Round 1426）。

新角度（probe 实证）退化几何穿 metrics 层（R1420/R1419/
R1422/R1425 锁的四种退化 bbox 首次上 metrics）：
- 零宽 bbox（未注册字体 /F9）pdfloc 仍 1.0——locator 有
  效性是**结构性**判定（page + 4 数字），不做几何合理性
- /Rotate 180 倒序文本：字符多重集精度/召回仍 1.0（多重
  集与顺序无关）、tpe True
- /Rotate 90 竖条 bbox、单 BT 双 Td 负 top bbox：pdfloc
  全 1.0
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.pipeline import process_single
from evaluation.metrics import \
    compute_automatic_metrics


def _build(content, page_extra=b""):
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
            + page_extra
            + b"/Resources << /Font "
            b"<< /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n" + content
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
    return bytes(out)


def _metrics(tmp_path, name, content,
             page_extra=b""):
    p = tmp_path / name
    p.write_bytes(_build(content,
                         page_extra))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    return compute_automatic_metrics(
        doc.to_dict(), None, "pdf",
        None)


# ---------- 零宽 bbox ----------

def test_zerowidth_pdfloc_one(
        tmp_path):
    m = _metrics(
        tmp_path, "uf.pdf",
        b"BT /F9 12 Tf 72 700 Td "
        b"(Unknown font text) "
        b"Tj ET")
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0,
        "reason": None}


def test_zerowidth_other_green(
        tmp_path):
    m = _metrics(
        tmp_path, "uf.pdf",
        b"BT /F9 12 Tf 72 700 Td "
        b"(Unknown font text) "
        b"Tj ET")
    assert m[
        "schema_valid"] == {
        "value": True, "reason": None}
    assert m[
        "chunk_reference_intact_"
        "ratio"] == {
        "value": 1.0,
        "reason": None}


# ---------- /Rotate 180 倒序 ----------

def test_rot180_multiset_one(
        tmp_path):
    m = _metrics(
        tmp_path, "rot.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Rotated page text) "
        b"Tj ET",
        b"/Rotate 180 ")
    assert m[
        "text_char_multiset_"
        "precision"] == {
        "value": 1.0,
        "reason": None}
    assert m[
        "text_char_multiset_"
        "recall"] == {
        "value": 1.0,
        "reason": None}


def test_rot180_tpe_true(
        tmp_path):
    m = _metrics(
        tmp_path, "rot.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Rotated page text) "
        b"Tj ET",
        b"/Rotate 180 ")
    assert m[
        "text_preservation_equal"] == {
        "value": True,
        "reason": None}


def test_rot180_pdfloc_one(
        tmp_path):
    m = _metrics(
        tmp_path, "rot.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Rotated page text) "
        b"Tj ET",
        b"/Rotate 180 ")
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0,
        "reason": None}


# ---------- /Rotate 90 竖条 ----------

def test_rot90_pdfloc_one(
        tmp_path):
    m = _metrics(
        tmp_path, "rot90.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Rotated page text) "
        b"Tj ET",
        b"/Rotate 90 ")
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0,
        "reason": None}


def test_rot90_hbc_one(
        tmp_path):
    m = _metrics(
        tmp_path, "rot90.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Rotated page text) "
        b"Tj ET",
        b"/Rotate 90 ")
    assert m[
        "heading_boundary_"
        "compliance"] == {
        "value": 1.0,
        "reason": None}


# ---------- 负 top bbox ----------

def test_negative_bbox_pdfloc_one(
        tmp_path):
    m = _metrics(
        tmp_path, "td.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(First Td line) Tj "
        b"72 640 Td "
        b"(Second Td line) Tj ET")
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0,
        "reason": None}


def test_negative_bbox_tpe(
        tmp_path):
    m = _metrics(
        tmp_path, "td.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(First Td line) Tj "
        b"72 640 Td "
        b"(Second Td line) Tj ET")
    assert m[
        "text_preservation_equal"] == {
        "value": True,
        "reason": None}
    assert m[
        "element_count_total"] == {
        "value": 2, "reason": None}
