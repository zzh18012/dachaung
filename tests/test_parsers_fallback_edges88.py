r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十八轮（Round 1518）。

新角度（probe 实证）标记内容与注释家族（tagged PDF
结构；此前轮次未碰 BDC/BMC/ActualText/Annots）：

- **⚠ /ActualText 替换被忽略**：/Span <</ActualText
  (replaced)>> BDC (xyz) Tj EMC → 提取 'xyz'（不是
  'replaced'——pdfplumber 不读 ActualText，tagged PDF
  的替换文本丢失）
- **BDC 带属性字典无副作用**：/P <</Tag /P>> BDC →
  'real' 正常
- **⚠ /Artifact 标记文本照常提取**：BMC (hidden?) Tj
  EMC → 'hidden?'（页眉页脚等分页装饰标记不剔除）
- **FreeText 注释不提取**：/Annots FreeText /Contents
  (ANNOT TEXT) → 只提取正文 BODY
- **便签注释不提取**：/Subtype /Text /Contents → 同上
- **悬空 /Annots 引用容忍**：指向不存在对象 → 无警告
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _doc(tmp_path, name, content,
         extra_page="", extra_obj=""):
    p = _pdf(tmp_path, name, content)
    raw = p.read_bytes().decode("latin-1")
    if extra_page:
        raw = raw.replace(
            "<< /Type /Page /Parent 2 0 R",
            f"<< /Type /Page {extra_page}"
            " /Parent 2 0 R")
    if extra_obj:
        raw = raw.replace(
            "trailer", f"{extra_obj}\ntrailer")
    p.write_bytes(raw.encode("latin-1"))
    return FallbackParser().parse(
        p, compute_file_hash(p))


def test_actualtext_ignored(tmp_path):
    doc = _doc(
        tmp_path, "at.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " /Span << /ActualText"
        " (replaced) >> BDC"
        " (xyz) Tj EMC ET")
    assert [e.content
            for e in doc.elements] == [
        "xyz"]


def test_bdc_dict_no_effect(tmp_path):
    doc = _doc(
        tmp_path, "bdc.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " /P << /Tag /P >> BDC"
        " (real) Tj EMC ET")
    assert [e.content
            for e in doc.elements] == [
        "real"]


def test_artifact_bmc_still_extracted(
        tmp_path):
    doc = _doc(
        tmp_path, "bmc.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " /Artifact BMC"
        " (hidden?) Tj EMC ET")
    assert [(e.content, e.type)
            for e in doc.elements] == [
        ("hidden?", "paragraph")]


def test_freetext_annotation_skipped(
        tmp_path):
    doc = _doc(
        tmp_path, "ft.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET",
        extra_page="/Annots [7 0 R]",
        extra_obj=(
            "7 0 obj << /Type /Annot"
            " /Subtype /FreeText"
            " /Rect [100 600 300 630]"
            " /Contents (ANNOT TEXT)"
            " /DA (/F1 12 Tf 0 g) >>"
            " endobj"))
    assert [e.content
            for e in doc.elements] == [
        "BODY"]
    assert doc.warnings == []


def test_sticky_note_skipped(tmp_path):
    doc = _doc(
        tmp_path, "note.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET",
        extra_page="/Annots [7 0 R]",
        extra_obj=(
            "7 0 obj << /Type /Annot"
            " /Subtype /Text"
            " /Rect [100 600 120 620]"
            " /Contents (sticky note"
            " body) /T (author) >>"
            " endobj"))
    assert [e.content
            for e in doc.elements] == [
        "BODY"]


def test_dangling_annot_ref_tolerated(
        tmp_path):
    doc = _doc(
        tmp_path, "dang.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET",
        extra_page="/Annots [9 0 R]")
    assert [e.content
            for e in doc.elements] == [
        "BODY"]
    assert doc.warnings == []
