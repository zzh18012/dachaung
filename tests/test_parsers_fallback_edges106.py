r"""app/parsers_fallback PDF 边角测试 - 第一百零六轮（Round 1536）。

新角度（probe 实证）词法容忍度家族（真实 PDF 生成器
差异：无空格 token、CR 老式行尾、非规范数字——此前
轮次内容流全为规范空格 + \\n 行尾 + 规范数字）：

- **无空格 token**（BT/F1、Td(BODY)Tj）→ 照常提取
- **全 CR 行尾**（对象间 + 流内 \\r）→ 照常、bbox 同基线
- **CRLF 行尾** → 照常
- **负字号 Tf -12 → 水平镜像**：'NEG' → 'GEN'、x 左移
  起点变 46（文本向左推进）、行高不变
- **Tz 0 → 零宽 bbox**：'ZERO' 仍完整提取但 bbox
  x1==x2==72（水平缩放 0，字符全部叠在同一点）
- **巨大坐标**（1e6/7e5）→ 原样保留：bbox x=1000000、
  y 翻转后深负（-699217.5）——不裁剪、不拒绝
- **前导零/加号数字**（+012、072）→ 照常解析
- **无整数部分小数**（.5 .5 Td）→ 照常解析（bbox
  [0.5, 782, 25.8, 794]）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path: Path, name: str,
         content: str,
         eol: str = "\n") -> Path:
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"{eol}stream{eol}{content}"
        f"{eol}endstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
    ]
    pdf = "%PDF-1.4" + eol
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj{eol}"
                f"{o}{eol}endobj{eol}")
    pdf += (f"trailer << /Root 1 0 R"
            f" /Size 6 >>{eol}%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _els(tmp_path, name, content,
         eol="\n"):
    p = _pdf(tmp_path, name, content, eol)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []
    return [(e.content,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_no_space_tokens(tmp_path):
    assert _els(
        tmp_path, "nospace.pdf",
        "BT/F1 12 Tf 72 700 Td"
        "(BODY)Tj ET") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_cr_only_line_endings(
        tmp_path):
    assert _els(
        tmp_path, "cronly.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET",
        eol="\r") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_crlf_line_endings(
        tmp_path):
    assert _els(
        tmp_path, "crlf.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET",
        eol="\r\n") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_negative_font_size(
        tmp_path):
    assert _els(
        tmp_path, "negsize.pdf",
        "BT /F1 -12 Tf 72 700 Td"
        " (NEG) Tj ET") == [
        ("GEN", [46.0, 89.5, 72.0,
                 101.5])]


def test_zero_horizontal_scale(
        tmp_path):
    assert _els(
        tmp_path, "zerotz.pdf",
        "BT /F1 12 Tf 0 Tz 72 700 Td"
        " (ZERO) Tj ET") == [
        ("ZERO", [72.0, 82.5, 72.0,
                  94.5])]


def test_huge_coordinates(
        tmp_path):
    assert _els(
        tmp_path, "huge.pdf",
        "BT /F1 12 Tf 1000000 700000"
        " Td (HUGE) Tj ET") == [
        ("HUGE", [1000000.0,
                  -699217.5,
                  1000034.7,
                  -699205.5])]


def test_leading_zeros_plus(
        tmp_path):
    assert _els(
        tmp_path, "zeros.pdf",
        "BT /F1 +012 Tf 072 0700 Td"
        " (ZEROS) Tj ET") == [
        ("ZEROS", [72.0, 82.5, 113.3,
                   94.5])]


def test_dot_decimal(tmp_path):
    assert _els(
        tmp_path, "dot5.pdf",
        "BT /F1 12 Tf .5 .5 Td"
        " (DOT) Tj ET") == [
        ("DOT", [0.5, 782.0, 25.8,
                 794.0])]
