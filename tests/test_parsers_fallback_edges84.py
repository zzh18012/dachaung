r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十四轮（Round 1514）。

新角度（probe 实证）多内容流 /Contents 数组与
FlateDecode 压缩流（真实 PDF 生成器的常见结构；此前
80+ 轮全部单流明文）：

- **⚠ 多流页字符 bbox 零宽**：/Contents [4 0 R 6 0 R]
  两流 → 内容/y 正常提取且顺序保持，但每字符宽度信
  息丢失 → bbox x0==x1（[72,80,72,92]），stderr 伴随
  "Could not get FontBBox" 告警（pdfminer 对流数组的
  字体度量解析缺陷）
- **三流中间 FlateDecode 正常解码**：明文+压缩+明文混
  排 → FIRST/SECOND/THIRD 顺序无恙
- **全压缩流**：全部 FlateDecode → 照常提取
- **单流压缩对照**：单 FlateDecode 流 bbox 完全正常
  （[72,82.5,106.7,94.5]）——零宽是多流特有
- **流边界隐式结束文本对象**：第一流缺 'ET'、第二流
  另起 BT → 两流文本均照常提取
"""

from __future__ import annotations

import zlib
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf_streams(tmp_path, name,
                 contents_spec):
    n = len(contents_spec)
    refs = " ".join(f"{4 + i} 0 R"
                    for i in range(n))
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R] /Count 1 >>",
        3: "<< /Type /Page"
           " /Parent 2 0 R"
           " /MediaBox [0 0 612 792]"
           " /Resources << /Font"
           " << /F1 5 0 R >> >>"
           f" /Contents [{refs}] >>",
        5: "<< /Type /Font"
           " /Subtype /Type1"
           " /BaseFont /Helvetica"
           " /Encoding"
           " /WinAnsiEncoding >>",
    }
    for i, (data, flate) in enumerate(
            contents_spec):
        if flate:
            body = zlib.compress(data)
            objs[4 + i] = (
                f"<< /Filter"
                f" /FlateDecode /Length"
                f" {len(body)} >>"
                f"\nstream\n"
                .encode("latin-1")
                + body + b"\nendstream")
        else:
            objs[4 + i] = (
                f"<< /Length"
                f" {len(data)} >>"
                f"\nstream\n"
                .encode("latin-1")
                + data + b"\nendstream")
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                .encode("latin-1")
                + o + b"\nendobj\n")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size "
            + str(max(objs) + 1)
            .encode() + b" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _els(tmp_path, name,
         contents_spec):
    p = _pdf_streams(
        tmp_path, name, contents_spec)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [(e.content,
             [round(v, 1)
              for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


_T1 = (b"BT /F1 12 Tf 72 700 Td"
       b" (FIRST) Tj ET")
_T2 = (b"BT /F1 12 Tf 72 650 Td"
       b" (SECOND) Tj ET")
_T3 = (b"BT /F1 12 Tf 72 600 Td"
       b" (THIRD) Tj ET")


def test_two_streams_zero_width(
        tmp_path):
    got = _els(
        tmp_path, "arr2.pdf",
        [(_T1, False), (_T2, False)])
    assert got == [
        ("FIRST",
         [72.0, 80.0, 72.0, 92.0]),
        ("SECOND",
         [72.0, 130.0, 72.0, 142.0]),
    ]


def test_three_streams_middle_flate(
        tmp_path):
    got = _els(
        tmp_path, "arr3f.pdf",
        [(_T1, False), (_T2, True),
         (_T3, False)])
    assert [c for c, _ in got] == [
        "FIRST", "SECOND", "THIRD"]


def test_all_flate_streams(
        tmp_path):
    got = _els(
        tmp_path, "allf.pdf",
        [(_T1, True), (_T2, True)])
    assert [c for c, _ in got] == [
        "FIRST", "SECOND"]


def test_single_flate_normal_bbox(
        tmp_path):
    got = _els(
        tmp_path, "sf.pdf",
        [(_T1, True)])
    assert got == [
        ("FIRST",
         [72.0, 82.5, 106.7, 94.5])]


def test_missing_et_across_streams(
        tmp_path):
    got = _els(
        tmp_path, "noet.pdf",
        [(b"BT /F1 12 Tf 72 700 Td"
          b" (FIRST) Tj", False),
         (_T2, False)])
    assert [c for c, _ in got] == [
        "FIRST", "SECOND"]
