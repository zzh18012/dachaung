r"""app/parsers/fallback_parser.py 边角测试 - 第三十七轮（Round 1428）。

新角度（probe 实证）/Length 与流实际长度不符（历史流长度
全声明正确）：
- 声明偏短（20 < 实际）：pdfminer 无法恢复 → 0 元素 +
  pdf_no_text_extracted 告警（可抽取文本整体静默丢失）
- 声明偏长（+50）：同样 0 元素 + 告警（尾部字节被误判成
  内联图像噪声）
- /Length 0 空流：同样走 no elements 路径
- 三者 parse 层 schema 均绿；管线层 no_extracted_elements
  结构化错误
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(content,
           length_override=None):
    L = (length_override
         if length_override is not None
         else len(content))
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
            + str(L).encode()
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


_CONTENT = (b"BT /F1 12 Tf 72 700 Td "
            b"(Length mismatch text) "
            b"Tj ET")


def _pdf(tmp_path, name, L):
    p = tmp_path / name
    p.write_bytes(_build(_CONTENT,
                         length_override=L))
    return p


# ---------- 声明偏短 ----------

def test_short_zero_elements(
        tmp_path):
    p = _pdf(tmp_path,
             "short.pdf", 20)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []


def test_short_warning(tmp_path):
    p = _pdf(tmp_path,
             "short.pdf", 20)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [(w.code, w.reason)
            for w in doc.warnings] == [
        ("pdf_no_text_extracted",
         "pdfplumber 未提取到任何文本"
         "/表格/图片（可能为扫描件，"
         "本阶段不支持 OCR）")]


# ---------- 声明偏长 ----------

def test_long_zero_elements(
        tmp_path):
    p = _pdf(
        tmp_path, "long.pdf",
        len(_CONTENT) + 50)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []


def test_long_warning(tmp_path):
    p = _pdf(
        tmp_path, "long.pdf",
        len(_CONTENT) + 50)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


# ---------- 空流 /Length 0 ----------

def test_zero_length_empty(
        tmp_path):
    p = tmp_path / "z.pdf"
    p.write_bytes(_build(b"",
                         0))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


# ---------- schema 与管线 ----------

def test_mismatch_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(tmp_path,
             "short.pdf", 20)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_short_pipeline_error(
        tmp_path):
    p = _pdf(tmp_path,
             "short.pdf", 20)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]


def test_long_pipeline_error(
        tmp_path):
    p = _pdf(
        tmp_path, "long.pdf",
        len(_CONTENT) + 50)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]


def test_correct_length_still_works(
        tmp_path):
    """对照：声明正确时同字节照常
    抽取（隔离 /Length 单一变量）。"""
    p = tmp_path / "ok.pdf"
    p.write_bytes(_build(_CONTENT))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Length mismatch text"]
    assert doc.warnings == []
