r"""app/parsers_fallback PDF 边角测试 - 第一百零五轮（Round 1535）。

新角度（probe 实证）BX/EX 兼容性块家族（PDF 规范：BX
...EX 内未知算子应被阅读器忽略；此前未知算子轮均在块
外——块内屏蔽语义、块平衡性零覆盖）：

- **BX 内未知算子 → 忽略，文本照常提取**（'INBOX'、零
  警告）
- **块外未知算子行为完全相同**（无 BX/EX 差异——pdfminer
  对未知算子一律静默跳过，不做块内屏蔽）
- **未定义字体 /F9 → 文本仍提取、零警告**（BADOUT/GOOD
  双出——字体缺失静默回退，此前记录的 word_extract 失败
  仅在更深层结构缺陷时出现）
- **BX 无 EX → 容忍**（'NOEX' 照常）
- **嵌套 BX/BX/EX/EX 与孤儿 EX → 容忍**
- **文本操作跨越 BX 边界**（BT → BX → Tj → EX → ET）→
  照常提取
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path: Path, name: str,
         content: str) -> Path:
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
        f"\nstream\n{content}\n"
        f"endstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _els(tmp_path, name, content):
    p = _pdf(tmp_path, name, content)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []
    return [e.content for e in
            doc.elements]


def test_unknown_op_inside_bx(
        tmp_path):
    assert _els(
        tmp_path, "inbox.pdf",
        "BX /FooMode setfoo"
        " BT /F1 12 Tf 72 700 Td"
        " (INBOX) Tj ET EX"
    ) == ["INBOX"]


def test_unknown_op_outside(
        tmp_path):
    assert _els(
        tmp_path, "nobox.pdf",
        "/FooMode setfoo"
        " BT /F1 12 Tf 72 700 Td"
        " (NOBOX) Tj ET"
    ) == ["NOBOX"]


def test_undefined_font_fallback(
        tmp_path):
    assert _els(
        tmp_path, "badout.pdf",
        "BT /F9 12 Tf 72 700 Td"
        " (BADOUT) Tj ET"
        " BT /F1 12 Tf 72 650 Td"
        " (GOOD) Tj ET"
    ) == ["BADOUT", "GOOD"]


def test_bx_without_ex(tmp_path):
    assert _els(
        tmp_path, "noex.pdf",
        "BX BT /F1 12 Tf 72 700 Td"
        " (NOEX) Tj ET"
    ) == ["NOEX"]


def test_nested_and_orphan_ex(
        tmp_path):
    assert _els(
        tmp_path, "nest.pdf",
        "BX BX BT /F1 12 Tf 72 700"
        " Td (NEST) Tj ET EX EX"
    ) == ["NEST"]
    assert _els(
        tmp_path, "nobx.pdf",
        "EX BT /F1 12 Tf 72 700 Td"
        " (NOBX) Tj ET EX"
    ) == ["NOBX"]


def test_text_spanning_boundary(
        tmp_path):
    assert _els(
        tmp_path, "span.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " BX (SPAN) Tj EX ET"
    ) == ["SPAN"]
