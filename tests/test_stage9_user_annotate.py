# -*- coding: utf-8 -*-
"""Stage 9 批次 26：第二标注人 dump/assemble 工具回归测试。

R4'（2026-09-10 十二轮裁决 P3'）：G⑤ 换真人任务包重制时发现
load_registry 把 page.width 当绝对 x1 用——MediaBox 整体平移的
页面（tech-08 实测 x0=-0.2875）右半栏 crop 越界直接 ValueError。
修复：裁剪一律取 page.bbox 实际坐标。本测试用平移 MediaBox 的
合成 PDF 锁死该行为。
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage9_user_annotate.py"


def _load_module(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "stage9_user_annotate_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.FILES = tmp_path
    return mod


def _build_shifted_pdf(path: Path) -> None:
    """合成单页 PDF：MediaBox [-1 0 611 792]（整体左移 1pt），两行
    文字分居中线（x0=305）两侧——修复前右半栏 crop (305,0,612,792)
    越出页面 bbox 右缘 611，直接 ValueError。"""
    left = b"BT /F1 12 Tf 100 700 Td (Left column line.) Tj ET"
    right = b"BT /F1 12 Tf 350 700 Td (Right column line.) Tj ET"
    stream = left + b"\n" + right
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [-1 0 611 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += ("%d 0 obj\n" % i).encode() + body + b"\nendobj\n"
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b"xref\n" + ("0 %d\n" % n).encode() + b"0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += b"trailer\n<< /Size " + str(n).encode() + b" /Root 1 0 R >>" \
        b"\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    path.write_bytes(pdf)


def test_load_registry_shifted_mediabox(tmp_path):
    mod = _load_module(tmp_path)
    _build_shifted_pdf(tmp_path / "shift.pdf")
    reg, reg_meta, fingerprint, pages_meta, _matched = mod.load_registry(
        "shift")
    texts = sorted(reg[(1, col, 0)] for col in ("L", "R")
                   if (1, col, 0) in reg)
    assert texts == ["Left column line.", "Right column line."], texts
    assert pages_meta[1]["L"] == 1 and pages_meta[1]["R"] == 1
    assert len(fingerprint) == 64


def test_dump_cli_shifted_mediabox(tmp_path, capsys):
    mod = _load_module(tmp_path)
    _build_shifted_pdf(tmp_path / "shift.pdf")
    rc = mod.main(["dump", "--doc", "shift", "--stdout"])
    assert rc in (0, None)
    out = capsys.readouterr().out
    assert "p001" in out and "Left column line." in out
    assert "Right column line." in out
