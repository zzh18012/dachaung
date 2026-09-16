"""PDF 内容流注释 % 与数字词法退化（Round 2026，a 优先级）。

PSBaseParser._parse_main：`%` 进 _parse_comment 吞到 EOL 且
**不产任何 token**（源码注释 "We ignore comments"）；数字仅从
-+/. 或 digit 起始。词法直测（PSStackParser）：
`--5 700` → 单个数 -5（双负号塌缩）、`1e2 1e2` → 数字 1 +
名字 e2 ×2、`+100 .5` → 100, 0.5。grep 实证注释与数字词法
形态零覆盖。探针 R2026 实证（好流基线 [100, 82.484,
134.008, 94.484]）：

- **E2 注释吞整行尾部**：`100 700 % Td (BODY) Tj ET` → Td、
  字符串、Tj、ET **全部**被注释吞掉 → 零文本 +
  pdf_no_text_extracted（静默内容丢失，无其他告警）
- E1 注释吞操作数尾部（700 在下行）→ 完整恢复基线
- E3 注释吞假字符串、真 Tj 在下行 → 基线不变
- E4 字符串内 % 是字面量 → 'BO%DY'（宽 44.676）
- **E5 科学计数**：`1e2 1e2 Td` → do_Td pop(1, /e2) →
  safe_float(名字)=0.0 **静默**（对照 R2025 do_Tf 的
  float_value→None+stderr 告警：两个算子容错策略不同）→
  'BODY' @ (1,0) → [1.0, 781.484, 35.008, 793.484]
- E6 合法变体 `+100 .5 Td` → Td(100, 0.5) → y 顶到页边
- E7 `--5 700 Td` → -5 被接受 → x=-5.0 越出 MediaBox 左缘
  照常抽取

判别式：E1/E3/E6 若偏离基线翻；E2 若非零文本+单告警翻；
E4/E5/E7 若内容或 bbox 任一变翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(content: bytes):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode()
            + b"\n%%EOF")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        p = Path(td) / "c.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_body(d, bbox):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BODY"
    assert d.elements[0].source_locator["page"] == 1
    assert d.elements[0].source_locator["bbox"] == pytest.approx(bbox, abs=0.01)
    assert d.warnings == []


BASELINE = [100.0, 82.484, 134.008, 94.484]


def test_baseline_good_stream():
    _assert_body(_parse(b"BT /F1 12 Tf 100 700 Td (BODY) Tj ET"), BASELINE)


def test_comment_mid_operands_recovers():
    """注释吞操作数行尾、700 在下一行 → Td(100,700) 完整恢复。"""
    _assert_body(_parse(b"BT /F1 12 Tf 100 % x\n 700 Td (BODY) Tj ET"),
                 BASELINE)


def test_comment_swallows_rest_of_line_loses_text():
    """`% Td (BODY) Tj ET` 整段被吞 → 零文本 + pdf_no_text_extracted。"""
    d = _parse(b"BT /F1 12 Tf 100 700 % Td (BODY) Tj ET")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_comment_swallows_decoy_string_real_next_line():
    """注释吞假字符串+假 Tj、真 Tj 在下一行 → 基线不变。"""
    _assert_body(_parse(b"BT /F1 12 Tf 100 700 Td % (BODY) Tj\n (BODY) Tj ET"),
                 BASELINE)


def test_percent_literal_inside_string():
    """字符串上下文 % 是字面量 → 'BO%DY'（宽于基线）。"""
    d = _parse(b"BT /F1 12 Tf 100 700 Td (BO%DY) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BO%DY"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 144.676, 94.484], abs=0.01)
    assert d.warnings == []


def test_scientific_notation_degrades_to_td_x1_y0():
    """`1e2 1e2 Td` → 词法切成 数字1+名字e2 ×2 → do_Td pop(1,/e2)
    → safe_float(名字)=0.0 静默 → 'BODY' @ (1,0)。"""
    _assert_body(_parse(b"BT /F1 12 Tf 1e2 1e2 Td (BODY) Tj ET"),
                 [1.0, 781.484, 35.008, 793.484])


def test_plus_and_leading_dot_number_forms():
    """`+100 .5 Td` → Td(100, 0.5) → 文本顶到页面底缘之上。"""
    _assert_body(_parse(b"BT /F1 12 Tf +100 .5 Td (BODY) Tj ET"),
                 [100.0, 781.984, 134.008, 793.984])


def test_double_minus_collapses_to_negative():
    """`--5 700 Td` → 词法塌缩为 -5 → x=-5.0 越出 MediaBox 照常抽取。"""
    _assert_body(_parse(b"BT /F1 12 Tf --5 700 Td (BODY) Tj ET"),
                 [-5.0, 82.484, 29.008, 94.484])
