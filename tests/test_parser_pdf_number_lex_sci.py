"""PDF 内容流数字词法退化：科学计数/nan/inf/-.5（Round 2017，a 优先级）。

pdfminer PS 词法数字正则**不含指数部分**：`1e2` 截成数字 1 +
未知裸关键字 `e2`——PDFContentParser.do_keyword 对未知关键字
**静默丢弃**（不上栈）。裸词 `nan`/`inf` 整词变关键字被丢 →
Td 弹栈不足 → 操作符整体跳过 → 文本矩阵保持单位阵 → 文本落
**原点 (0,0)**（bbox 冲出 Letter 页顶）。edges106（R1536）已
锁前导零/+012/072/.5；科学计数/裸 nan/inf/-.5 grep 实证零
覆盖。探针 R2017 实证（文本 '(NUM)' 12pt Helvetica，基线
'100 700 Td' → bbox [100, 82.484, 127.324, 94.484]）：

- **T1 科学计数截尾**：`1e2 700 Td` → 1e2 取**尾数前缀** 1.0
  （e2 关键字被丢）→ bbox [1.0, 82.484, 28.324, 94.484]
  （不是 100 也不是异常）
- **T2 nan**：`nan 700 Td` → 关键字被丢、Td 弹栈不足被跳过 →
  文本在原点 → bbox [0.0, 782.484, 27.324, 794.484]（top
  超页顶 792）
- **T3 inf**：与 T2 同机制同 bbox
- **T4 负号小数**：`-.5 700 Td` → 正常 -0.5 → bbox [-0.5,
  82.484, 26.824, 94.484]
- **T5 双操作数科学计数**：`1.5e1 7e2 Td` → (1.5, 7) → bbox
  [1.5, 775.484, 28.824, 787.484]（7e2 取 7，非 700）

判别式：T1/T5 若当 100/700 或异常翻；T2/T3 若 y=700 正常
落字翻；T4 若异常翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(td_op: bytes):
    content = b"BT /F1 12 Tf " + td_op + b" Td (NUM) Tj ET"
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
        p = Path(td) / "n.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _one(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NUM"
    assert d.warnings == []
    return d.elements[0].source_locator["bbox"]


def test_scientific_truncates_to_mantissa():
    """T1：1e2 → 尾数前缀 1.0，e2 关键字静默丢弃。"""
    assert _one(_parse(b"1e2 700")) == pytest.approx(
        [1.0, 82.484, 28.324, 94.484], abs=0.01)


def test_nan_keyword_td_skipped_origin():
    """T2：nan 关键字被丢 → Td 跳过 → 文本落原点。"""
    assert _one(_parse(b"nan 700")) == pytest.approx(
        [0.0, 782.484, 27.324, 794.484], abs=0.01)


def test_inf_keyword_td_skipped_origin():
    """T3：inf 与 nan 同机制同原点 bbox。"""
    assert _one(_parse(b"inf 700")) == pytest.approx(
        [0.0, 782.484, 27.324, 794.484], abs=0.01)


def test_negative_dot_number():
    """T4：-.5 正常解析为 -0.5。"""
    assert _one(_parse(b"-.5 700")) == pytest.approx(
        [-0.5, 82.484, 26.824, 94.484], abs=0.01)


def test_both_operands_scientific():
    """T5：1.5e1 7e2 → (1.5, 7) 双双截尾。"""
    assert _one(_parse(b"1.5e1 7e2")) == pytest.approx(
        [1.5, 775.484, 28.824, 787.484], abs=0.01)
