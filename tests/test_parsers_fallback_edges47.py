r"""app/parsers/fallback_parser.py 边角测试 - 第四十七轮（Round 1439）。

新角度（probe 实证）表格检测几何变体（R1438 只锁了 re S 全
框格，画法变体全空白）：
- re f 纯填充（无描边）：仍产表但结构怪——空表头行 +
  'cellA\ncellB' 并入一格 '|  |\n| --- |\n| cellA\ncellB |'
- re 无任何绘制操作符（不 S 不 f）：**无表**——路径未绘制
  就不存在边缘
- 单列两格竖排：规范 1 列 2 行表 '| cellA |\n| --- |\n|
  cellB |' bbox [72.0, 62.0, 272.0, 142.0]
- m/l 显式线段拼开格网（2 竖 3 横）：同样产表 '| cellA |
  \n| --- |\n| cellB |' bbox [72.0, 72.0, 272.0, 152.0]
- 四种画法下格内文字都是独立 heading（cellA/cellB 相距
  40pt > 31 分行阈值），文本双份不变
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(content):
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


_TXT = (b"BT /F1 10 Tf 80 700 Td "
        b"(cellA) Tj ET "
        b"BT /F1 10 Tf 80 660 Td "
        b"(cellB) Tj ET")


def _pdf(tmp_path, name, drawing):
    p = tmp_path / name
    p.write_bytes(_build(drawing + _TXT))
    return p


# ---------- re f 纯填充 ----------

def test_fill_table_detected(
        tmp_path):
    p = _pdf(
        tmp_path, "fill.pdf",
        b"72 650 200 60 re f "
        b"72 710 200 60 re f ")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading",
        "table"]
    assert doc.elements[
        2].content == \
        "|  |\n| --- |\n" \
        "| cellA\ncellB |"
    assert doc.elements[
        2].source_locator["bbox"] == [
        72.0, 22.0, 272.0, 142.0]


# ---------- re 无绘制操作符 ----------

def test_nopaint_no_table(
        tmp_path):
    p = _pdf(
        tmp_path, "np.pdf",
        b"72 650 200 60 re "
        b"72 710 200 60 re ")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading"]
    assert [e.content
            for e in doc.elements] == [
        "cellA", "cellB"]


# ---------- 单列竖排 ----------

def test_vstack_table(tmp_path):
    p = _pdf(
        tmp_path, "vs.pdf",
        b"72 650 200 40 re S "
        b"72 690 200 40 re S ")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        2].type == "table"
    assert doc.elements[
        2].content == \
        "| cellA |\n| --- |\n" \
        "| cellB |"
    assert doc.elements[
        2].source_locator["bbox"] == [
        72.0, 62.0, 272.0, 142.0]


# ---------- m/l 线段 ----------

_ML = (b"72 640 m 72 720 l S "
       b"272 640 m 272 720 l S "
       b"72 720 m 272 720 l S "
       b"72 680 m 272 680 l S "
       b"72 640 m 272 640 l S ")


def test_mlines_table(tmp_path):
    p = _pdf(tmp_path, "ml.pdf",
             _ML)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        2].type == "table"
    assert doc.elements[
        2].content == \
        "| cellA |\n| --- |\n" \
        "| cellB |"
    assert doc.elements[
        2].source_locator["bbox"] == [
        72.0, 72.0, 272.0, 152.0]


# ---------- 通用 ----------

def test_fill_headings_split(
        tmp_path):
    p = _pdf(
        tmp_path, "fh.pdf",
        b"72 650 200 60 re f "
        b"72 710 200 60 re f ")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements
            if e.type == "heading"] == [
        "cellA", "cellB"]


def test_vstack_chunks(tmp_path):
    p = _pdf(
        tmp_path, "vsc.pdf",
        b"72 650 200 40 re S "
        b"72 690 200 40 re S ")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    texts = [c.text
             for c in doc.chunks]
    assert "cellA" in texts
    assert ("| cellA |\n| --- |\n"
            "| cellB |") in texts


def test_mlines_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(tmp_path, "mls.pdf",
             _ML)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_variants_no_warnings(
        tmp_path):
    for name, drawing in (
            ("w1.pdf",
             b"72 650 200 60 re f "
             b"72 710 200 60 re f "),
            ("w2.pdf", _ML),
            ("w3.pdf",
             b"72 650 200 40 re S "
             b"72 690 200 40 re S ")):
        p = _pdf(tmp_path, name,
                 drawing)
        doc = FallbackParser().parse(
            p, compute_file_hash(p))
        assert doc.warnings == []
