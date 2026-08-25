r"""CLI 图片流程端到端（Round 1561）。

新角度：CLI 测试全部用纯文本样例，**图片 PDF 经
`parse` 子命令 → images-<sha16>/ 真实创建 → `validate`
子命令通过**的子进程级流程零覆盖（pipeline 层已有
R1551/1552，本轮锁 CLI 进程边界）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent
    / ".venv" / "Scripts" / "python.exe")
PROJECT_ROOT = (Path(__file__)
                .resolve().parent.parent)
_PYTHON = (VENV_PYTHON
           if Path(VENV_PYTHON).is_file()
           else sys.executable)

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")
_IMG = bytes([0, 128, 0])


def _run_cli(args: list[str]):
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": (
            str(PROJECT_ROOT)
            + os.pathsep
            + os.environ.get(
                "PYTHONPATH", "")),
    }
    proc = subprocess.run(
        [_PYTHON, "-m", "app.cli",
         *args],
        capture_output=True,
        text=True, encoding="utf-8",
        errors="replace", env=env)
    return (proc.returncode,
            proc.stdout, proc.stderr)


def _img_pdf(tmp_path: Path) -> Path:
    c = ("q 100 0 0 100 72 692 cm"
         " /Im1 Do Q"
         " BT /F1 12 Tf 72 650 Td"
         " (BODY) Tj ET")
    im = (f"<< /Type /XObject"
          f" /Subtype /Image"
          f" /Width 1 /Height 1"
          f" /ColorSpace /DeviceRGB"
          f" /BitsPerComponent 8"
          f" /Length {len(_IMG)} >>"
          f"\nstream\n"
          ).encode() + _IMG \
        + b"\nendstream"
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >>"
            " /XObject << /Im1"
            " 7 0 R >> >>"
            " /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
        7: im,
    }
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o \
            + b"\nendobj\n"
    pdf += (b"trailer"
            b" << /Root 1 0 R"
            b" /Size 8 >>\n%%EOF")
    p = tmp_path / "img.pdf"
    p.write_bytes(pdf)
    return p


def test_parse_image_then_validate(
        tmp_path):
    p = _img_pdf(tmp_path)
    out = tmp_path / "out.json"
    rc, stdout, stderr = _run_cli(
        ["parse", str(p),
         "-o", str(out)])
    assert rc == 0, stderr
    assert out.is_file()
    data = json.loads(
        out.read_text(encoding="utf-8"))
    imgs = [el for el
            in data["elements"]
            if el["type"] == "image"]
    assert len(imgs) == 1
    assert imgs[0]["content"] is None
    assert imgs[0][
        "resource_path"]
    dirs = [x for x
            in tmp_path.iterdir()
            if x.is_dir()]
    (d,) = dirs
    assert d.name.startswith(
        "images-")
    files = list(d.iterdir())
    assert [f.name[-10:]
            for f in files] == [
        "_p1_00.png"]
    rc2, _, stderr2 = _run_cli(
        ["validate", str(out)])
    assert rc2 == 0, stderr2
