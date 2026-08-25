r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十七轮（Round 1517）。

新角度（probe 实证）Type0/CIDFont + Identity-H +
ToUnicode CMap（真实 CJK PDF 的标准结构；此前轮次全
部 Type1 单字节字体）：

- **bfchar 映射正常提取**：<00010002> → 'AB'（2 字节
  CID → Unicode）
- **CJK 映射**：<00030003>（4E2D）→ '中中'
- **未映射 CID → (cid:N) 十进制占位**：<0099> →
  '(cid:153)'（0x99=153 十进制）
- **⚠ 字面串字节按 CID 配对**：CID 字体上下文 '(mid)'
  Tj → m(0x6D)+i(0x69)=0x6D69=28009 → '(cid:28009)'，
  尾部奇数字节 'd' 丢弃 → 'A(cid:28009)B'
- **无 ToUnicode 全占位**：<00010002> → '(cid:1)
  (cid:2)'
- **bfrange 区间映射**：<0010><0011><0012> → 0061 起
  'abc'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _cmap(body):
    return (
        "/CIDInit /ProcSet findresource"
        " begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo << /Registry"
        " (Adobe) /Ordering (UCS)"
        " /Supplement 0 >> def\n"
        "/CMapName /Adobe-Identity-UCS"
        " def\n/CMapType 2 def\n"
        "1 begincodespacerange\n<0000>"
        " <FFFF>\nendcodespacerange\n"
        f"{body}endcmap\nCMapName"
        " currentdict /CMap"
        " defineresource pop\nend\nend")


def _pdf(tmp_path, name, content,
         tounicode=None):
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R]"
        " /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type0"
        " /BaseFont /Dummy"
        " /Encoding /Identity-H"
        " /DescendantFonts"
        " [<< /Type /Font /Subtype"
        " /CIDFontType0 /BaseFont"
        " /Dummy /CIDSystemInfo"
        " << /Registry (Adobe)"
        " /Ordering (Identity)"
        " /Supplement 0 >> /DW 1000"
        " >>]"
        + (f" /ToUnicode 6 0 R >>"
           if tounicode is not None
           else " >>"),
    ]
    if tounicode is not None:
        objs.append(
            f"<< /Length"
            f" {len(tounicode)} >>"
            f"\nstream\n{tounicode}"
            f"\nendstream")
    pdf = "%PDF-1.4\n" + "".join(
        f"{i + 1} 0 obj\n{o}\nendobj\n"
        for i, o in enumerate(objs))
    pdf += (f"trailer << /Root 1 0 R"
            f" /Size {len(objs) + 1} >>"
            f"\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _content(tmp_path, name, text,
             tounicode=None):
    content = ("BT /F1 12 Tf 72 700 Td"
               f" {text} Tj ET")
    p = _pdf(tmp_path, name, content,
             tounicode)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [e.content
            for e in doc.elements], \
        [w.code for w in doc.warnings]


_TU = _cmap(
    "3 beginbfchar\n<0001> <0041>\n"
    "<0002> <0042>\n<0003> <4E2D>\n"
    "endbfchar\n")


def test_bfchar_ascii(tmp_path):
    got, warns = _content(
        tmp_path, "cid1.pdf",
        "<00010002>", _TU)
    assert got == ["AB"]
    assert warns == []


def test_bfchar_cjk(tmp_path):
    got, _ = _content(
        tmp_path, "cjk.pdf",
        "<00030003>", _TU)
    assert got == ["中中"]


def test_unmapped_cid_placeholder(
        tmp_path):
    got, _ = _content(
        tmp_path, "unmap.pdf",
        "<00990001>", _TU)
    assert got == ["(cid:153)A"]


def test_literal_string_paired_cid(
        tmp_path):
    content = ("BT /F1 12 Tf 72 700 Td"
               " <0001> Tj (mid) Tj"
               " <0002> Tj ET")
    p = _pdf(tmp_path, "mixed.pdf",
             content, _TU)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "A(cid:28009)B"]


def test_no_tounicode_placeholders(
        tmp_path):
    got, _ = _content(
        tmp_path, "notu.pdf",
        "<00010002>")
    assert got == [
        "(cid:1)(cid:2)"]


def test_bfrange_mapping(tmp_path):
    tu = _cmap(
        "1 beginbfrange\n"
        "<0010> <0012> <0061>\n"
        "endbfrange\n")
    got, _ = _content(
        tmp_path, "range.pdf",
        "<001000110012>", tu)
    assert got == ["abc"]
