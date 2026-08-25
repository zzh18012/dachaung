r"""app/parsers_fallback PDF 边角测试 - 第一百一十四轮（Round 1544）。

新角度（probe 实证）图形状态算子中性 + 深度堆栈（
gs/rg/g/k/cs/w/d 等算子对**提取**的影响——零覆盖）：

- **gs 有效 ExtGState（含 /LW /Font）** → 中性（bbox 同
  基线）
- **gs 悬空引用 /GS9** → 中性容忍
- **全套颜色算子**（rg/RGB/g/k/cs/scn）→ 中性
- **全套描边算子**（w/d/J/j/M/ri/i）→ 中性
- **100 层 q/Q 嵌套** → 照常、bbox 不变
- **q + cm 100× 缩放 + 文本 + Q** → 文本被放大：bbox x
  达 7200..10600.8（cm 在 BT 外合法作用——q/Q 正确平衡
  不撤销对文本的影响）
- **嵌套 BT/BT** → 容忍照常（'NEST'）
- **3 个未恢复 q** → 照常
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_BASE = ("BT /F1 12 Tf 72 700 Td"
         " (BODY) Tj ET")


def _els(tmp_path, name, content):
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >>"
        " /ExtGState"
        " << /GS1 7 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\n"
        f"endstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
        "<< /Type /ExtGState"
        " /LW 2 /Font 0 >>",
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 8 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []
    return [(e.content,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_gs_valid(tmp_path):
    assert _els(
        tmp_path, "gsok.pdf",
        "/GS1 gs " + _BASE) == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_gs_missing_ref(tmp_path):
    assert _els(
        tmp_path, "gsmiss.pdf",
        "/GS9 gs " + _BASE) == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_color_operators(tmp_path):
    assert _els(
        tmp_path, "colors.pdf",
        "1 0 0 rg 0 0 1 RG 0.5 g"
        " 1 k /DeviceRGB cs"
        " 0 0 0 scn " + _BASE) == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_stroke_operators(tmp_path):
    assert _els(
        tmp_path, "stroke.pdf",
        "5 w [2 2] 0 d 1 J 1 j 5 M"
        " /RelativeColorimetric ri"
        " 3 i " + _BASE) == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_deep_q_stack(tmp_path):
    assert _els(
        tmp_path, "deepq.pdf",
        "q " * 100 + _BASE
        + " Q " * 100) == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_cm_scale_extreme(tmp_path):
    assert _els(
        tmp_path, "qafter.pdf",
        "q 100 0 0 1 0 0 cm "
        + _BASE + " Q") == [
        ("BODY", [7200.0, 82.5,
                  10600.8, 94.5])]


def test_nested_bt(tmp_path):
    assert _els(
        tmp_path, "nestbt.pdf",
        "BT /F1 12 Tf BT 72 700 Td"
        " (NEST) Tj ET ET") == [
        ("NEST", [72.0, 82.5, 104.0,
                  94.5])]


def test_unmatched_q(tmp_path):
    assert _els(
        tmp_path, "manyq.pdf",
        "q q q " + _BASE) == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]
