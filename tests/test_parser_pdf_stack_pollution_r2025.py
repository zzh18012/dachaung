"""PDF 内容流操作数栈污染 + BX/EX 未实现（Round 2025，a 优先级）。

pdfinterp.py:1417-1447：未知算子在非 STRICT 下静默跳过且
**不清栈**；已知算子 pop(nargs) 只取栈顶 nargs，多余操作数
永久残留；整个内容流共享一个操作数栈。更关键的是
pdfinterp.py:1015-1031 的 do_BT/do_ET/do_BX/do_EX **方法体
全为空**（docstring 声称 BT 重置矩阵，实现是 no-op）——
位置跨 ET/BT 泄漏、BX/EX 不抑制任何内容。探针 R2025 实证
（好流 '(BODY)' 基线 [100, 82.484, 134.008, 94.484]）：

- E1 Td 多余前置操作数 `300 100 700 Td` → pop2 取栈顶
  （100,700），300 残留但本轮 Tj 不受影响 → 基线不变
- **E2 跨 ET 栈泄漏**：块1 残留 300；块2 `/F1 Tf` 只压
  1 操作数 → do_Tf pop2 取 (300, /F1)：300 作 fontid
  int 键查表静默失败、/F1 作字号 float_value(PSLiteral)
  → None → stderr "invalid float value" + 字体未设 +
  do_BT no-op 位置沿用块1 Td → 'TAIL' 零宽盒
  [100, 80, 100, 92]、零告警（stderr 不进 warnings）
- E3 BX 块：BX/EX 自身当未知算子忽略、内部内容照常
  解释 → 基线不变（兼容性段不降级）
- E4 未知算子 /Foo 夹在操作数与 Tj 之间 → 忽略、Tj 照常
- E5 Tf 多余前置操作数 `300 /F1 12 Tf` → pop2 取
  (/F1,12)、300 残留 → 基线不变

判别式：E1/E3/E4/E5 若偏离基线翻；E2 若非 TAIL@零宽盒
或出现告警翻。
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
        p = Path(td) / "s.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_body(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BODY"
    assert d.elements[0].source_locator["page"] == 1
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 134.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_baseline_good_stream():
    _assert_body(_parse(b"BT /F1 12 Tf 100 700 Td (BODY) Tj ET"))


def test_extra_td_operand_absorbed():
    """`300 100 700 Td` → pop2 取栈顶 (100,700)，300 残留不影响本轮。"""
    _assert_body(_parse(b"BT /F1 12 Tf 300 100 700 Td (BODY) Tj ET"))


def test_leak_across_et_swaps_tf_operands():
    """块1 残留 300 被块2 `/F1 Tf` pop2 吞作 fontid → 字体失效 +
    do_BT no-op 位置沿用 → 'TAIL' 零宽盒、零告警。"""
    d = _parse(b"BT /F1 12 Tf 300 100 700 Td ET"
               b"BT /F1 Tf (TAIL) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "TAIL"
    assert d.elements[0].source_locator["page"] == 1
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 80.0, 100.0, 92.0], abs=0.01)
    assert d.warnings == []


def test_bx_ex_block_content_interpreted():
    """BX/EX 空实现（no-op）→ 内部内容照常解释 → 基线不变。"""
    _assert_body(_parse(b"BT /F1 12 Tf BX 100 700 Td (BODY) Tj EX ET"))


def test_unknown_op_between_operands_ignored():
    """`/Foo` 夹在操作数与 Tj 之间 → 非 STRICT 静默忽略不清栈。"""
    _assert_body(_parse(b"BT /F1 12 Tf 100 700 Td /Foo (BODY) Tj ET"))


def test_extra_tf_operand_absorbed():
    """`300 /F1 12 Tf` → pop2 取 (/F1,12)，300 残留不影响本轮。"""
    _assert_body(_parse(b"BT 300 /F1 12 Tf 100 700 Td (BODY) Tj ET"))
