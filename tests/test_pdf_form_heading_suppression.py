"""Stage 10 批次 6 测试：PDF 表单域标签 heading 负向语义信号（r59 授权）。

裁决边界（登记行 Stage-10-Batch-6 AUTHORIZED / ADOPTION §144）：
- C2 范围 = PDF short_line heading 启发式中的"表单域/表单标签类假阳性"，
  仅局部负向语义信号，不重写通用 heading 评分框架；
- 合成夹具两组必须同时成立：表单标签不得判 heading + 正常 heading
  不受影响；
- 页面家具类（页码/封面日期/宣传语）不得被表单标签规则顺带压掉
  （r59 ③），本文件 Group C 为其回归守护；
- 不硬编码 real-02 真实样本内容，夹具字符串全部为等义合成行。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.parsers.fallback_parser import (
    FallbackParser,
    _classify_pdf_paragraph,
    _form_label_signal,
)
from app.pipeline import process_single


# ---------- Group A：表单标签不得判 heading（单元级） ----------

FORM_LABEL_CASES = [
    # (文本, 期望信号)
    ("Contact address:", "form_label_short_colon"),
    ("Date of birth:", "form_label_short_colon"),
    ("Advisor name:", "form_label_short_colon"),
    ("Contact phone number:", "form_label_short_colon"),
    ("Further Notes/Observations and/or Actions:", "form_label_short_colon"),
    ("Reference code: Expiry date:", "form_label_multi_colon"),
    ("Company name: Contact person (secretary):", "form_label_multi_colon"),
    ("Type of transport: (please indicate) Road Rail Sea", "form_label_instruction"),
    ("Mode of operation: (Tick one) Manual Automatic", "form_label_instruction"),
    ("Is a safety plan attached? Yes No N/A", "form_label_option_suffix"),
    ("联系地址：", "form_label_short_colon"),
    ("注册编号： 有效期至：", "form_label_multi_colon"),
]


@pytest.mark.parametrize("text,signal", FORM_LABEL_CASES)
def test_form_label_lines_are_not_headings(text: str, signal: str):
    etype, meta = _classify_pdf_paragraph(text)
    assert etype == "paragraph"
    assert meta.get("heading_suppressed") == signal


@pytest.mark.parametrize(
    "text,signal",
    [
        ("Contact address:", "form_label_short_colon"),
        ("Reference code: Expiry date:", "form_label_multi_colon"),
        ("Type of transport: (please indicate) Road Rail Sea", "form_label_instruction"),
        ("Is a safety plan attached? Yes No N/A", "form_label_option_suffix"),
    ],
)
def test_form_label_signal_helper_direct(text: str, signal: str):
    assert _form_label_signal(text) == signal


def test_short_colon_token_boundary_at_four():
    """恰 4 token 的冒号结尾行 = 标签（抑制）；5 token 句式冒号结尾行
    （"This report was prepared by:" 一类）= heading（Group B 边界）。"""
    assert _form_label_signal("Further Notes/Observations and/or Actions:") == (
        "form_label_short_colon"
    )
    assert _form_label_signal("This document was reviewed by:") is None


# ---------- Group B：正常 heading 不受影响（单元级） ----------

NORMAL_HEADING_CASES = [
    "Introduction",
    "Executive summary",
    "High consequence dangerous goods",
    "Practices & procedures",
    "This document was reviewed by:",
    "Annual Safety Report for the Transport of Hazardous Materials",
    "Guidance notes (see appendix) here",
]


@pytest.mark.parametrize("text", NORMAL_HEADING_CASES)
def test_normal_headings_unaffected(text: str):
    etype, meta = _classify_pdf_paragraph(text)
    assert etype == "heading"
    assert meta == {"level": 0, "heuristic": "short_line"}


# ---------- Group C：页面家具不得被顺带压掉（r59 ③ 守护） ----------

PAGE_FURNITURE_CASES = [
    "Page 21",
    "January 2031",
    "Moving forward together, safely",
]


@pytest.mark.parametrize("text", PAGE_FURNITURE_CASES)
def test_page_furniture_not_suppressed_by_form_rules(text: str):
    etype, meta = _classify_pdf_paragraph(text)
    assert etype == "heading"
    assert meta == {"level": 0, "heuristic": "short_line"}


# ---------- Group D：既有行为不变（caption 优先/句末/超长/空行） ----------

def test_existing_classification_behavior_unchanged():
    assert _classify_pdf_paragraph("Figure 3. Form layout example") == (
        "caption",
        {"heuristic": "caption_regex"},
    )
    assert _classify_pdf_paragraph("This is a normal sentence.") == ("paragraph", {})
    assert _classify_pdf_paragraph("x" * 81 + " address:") == ("paragraph", {})
    assert _classify_pdf_paragraph("") == ("paragraph", {})
    assert _classify_pdf_paragraph("Contact address:") != ("paragraph", {})


# ---------- 端到端：手写最小 PDF（合成夹具，零真实语料） ----------

def _escape_pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text_stream(lines: list[str]) -> str:
    """单页多行文本，行距 60pt（> 1.5×中位字高），每行独立成段。"""
    ops = []
    y = 720
    for line in lines:
        ops.append(f"BT /F1 10 Tf 72 {y} Td ({_escape_pdf_literal(line)}) Tj ET")
        y -= 60
    return "\n".join(ops) + "\n"


def _make_pdf(path: Path, page_streams: list[str]) -> Path:
    n = len(page_streams)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for stream in page_streams:
        content = stream.encode("latin-1")
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Contents " + str(len(objs) + 2).encode() + b" 0 R"
            b" /Resources << /Font << /F1 3 0 R >> >> >>"
        )
        objs.append(
            b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"
        )
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(pdf)
    total = len(objs) + 1
    pdf += b"xref\n" + f"0 {total}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += (
        b"trailer\n<< /Size " + str(total).encode() + b" /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    )
    path.write_bytes(pdf)
    return path


E2E_LINES = [
    "Section Overview",
    "Contact address:",
    "Reference code: Expiry date:",
    "Mode of operation: (please indicate) Road Rail Sea",
    "Is a safety plan attached? Yes No N/A",
    "This document was reviewed by:",
    "Page 21",
    "Normal body sentence about the quarterly audit findings.",
]


def _parse_elements(pdf_path: Path):
    h = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    doc = FallbackParser().parse(pdf_path, source_hash=h)
    return {e.content: e for e in doc.elements}


def test_pdf_form_headings_suppressed_end_to_end(tmp_path: Path):
    pdf = _make_pdf(tmp_path / "form.pdf", [_text_stream(E2E_LINES)])
    by_content = _parse_elements(pdf)

    headings = [c for c, e in by_content.items() if e.type == "heading"]
    assert sorted(headings) == [
        "Page 21",
        "Section Overview",
        "This document was reviewed by:",
    ]
    for c in ("Contact address:", "Reference code: Expiry date:",
              "Mode of operation: (please indicate) Road Rail Sea",
              "Is a safety plan attached? Yes No N/A",
              "Normal body sentence about the quarterly audit findings."):
        assert by_content[c].type == "paragraph"
    assert by_content["Contact address:"].metadata["heading_suppressed"] == (
        "form_label_short_colon"
    )
    assert by_content["Reference code: Expiry date:"].metadata["heading_suppressed"] == (
        "form_label_multi_colon"
    )
    assert by_content[
        "Mode of operation: (please indicate) Road Rail Sea"
    ].metadata["heading_suppressed"] == "form_label_instruction"
    assert by_content[
        "Is a safety plan attached? Yes No N/A"
    ].metadata["heading_suppressed"] == "form_label_option_suffix"
    # 家具类（Page 21）与 5-token 冒号结尾句式 heading 保持 short_line
    assert by_content["Page 21"].metadata == {"level": 0, "heuristic": "short_line"}
    assert by_content["This document was reviewed by:"].metadata == {
        "level": 0,
        "heuristic": "short_line",
    }


def test_suppressed_document_passes_pipeline_schema(tmp_path: Path):
    pdf = _make_pdf(tmp_path / "pipe.pdf", [_text_stream(E2E_LINES)])
    out = tmp_path / "pipe.json"
    doc, errs = process_single(pdf, out)
    assert errs == []
    assert out.exists()
    assert doc is not None
