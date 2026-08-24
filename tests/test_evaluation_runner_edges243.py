r"""evaluation/runner.py 边角测试 - 第二百四十三轮（Round 1396）。

新角度（probe 实证）：评测 run 后的磁盘图片布局（真 PDF
Image XObject + pypdfium2 渲染落盘，历史 runner 图片测试
只验 image_dir 命名，从未真跑渲染核对文件本体）：
- `<out>/_per_doc/` 存在且无 JSON 残留（stub 已 unlink）
- `<out>/_per_doc/images-<sha16>/image_<sha16>_p1_00.png`
  ——目录名与文件名的 sha16 一致（= document_id 前缀）
- 落盘文件是真 PNG（\x89PNG 签名，pypdfium2 渲染 447 字节）
- 同一 run 的 irer 1.0
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
from pathlib import Path

from evaluation.cli import main


def _build_pdf_with_image():
    def text(x, y, t):
        return (f"BT /F1 12 Tf {x} {y} "
                f"Td ({t}) Tj ET")

    c1 = "\n".join([
        text(72, 700,
             "Disk Layout Heading"),
        text(72, 640,
             "Body paragraph to give "
             "the document some real "
             "text content for the "
             "chunker."),
        "q 80 0 0 80 450 600 cm "
        "/Im1 Do Q"]).encode()
    img_data = b"\x00\x00\xff"
    objs = {
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] /Count 1 >>"),
        3: (b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 "
            b"6 0 R >> /XObject << /Im1 "
            b"5 0 R >> >> /Contents "
            b"4 0 R >>"),
        5: (b"<< /Type /XObject /Subtype "
            b"/Image /Width 1 /Height 1 "
            b"/ColorSpace /DeviceRGB "
            b"/BitsPerComponent 8 "
            b"/Length 3 >>\nstream\n"
            + img_data + b"\nendstream"),
        6: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        4: (b"<< /Length "
            + str(len(c1)).encode()
            + b" >>\nstream\n" + c1
            + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n".encode()
                + objs[oid] + b"\nendobj\n")
    xref_pos = len(out)
    out += (b"xref\n0 7\n"
            b"0000000000 65535 f \n")
    for oid in range(1, 7):
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size 7 "
            b"/Root 1 0 R >>\nstartxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


def _run(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples"
     / "d.pdf").write_bytes(
        _build_pdf_with_image())
    outdir = tmp_path / "out"
    outdir.mkdir()
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "dd",
             "path": "samples/d.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    rep = outdir / "r.json"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["run", "--manifest",
                   str(mf),
                   "--output", str(rep),
                   "--parser", "fallback",
                   "--max-chars", "800"])
    data = json.loads(
        rep.read_text(encoding="utf-8"))
    return rc, outdir, data


# ---------- _per_doc 布局 ----------

def test_per_doc_dir_exists(tmp_path):
    _, outdir, _ = _run(tmp_path)
    assert (outdir / "_per_doc").is_dir()


def test_per_doc_no_json_stubs(tmp_path):
    _, outdir, _ = _run(tmp_path)
    stubs = list(
        (outdir / "_per_doc")
        .glob("*.json"))
    assert stubs == []


def test_images_dir_naming(tmp_path):
    _, outdir, _ = _run(tmp_path)
    dirs = [d for d in
            (outdir / "_per_doc")
            .iterdir() if d.is_dir()]
    assert len(dirs) == 1
    assert re.fullmatch(
        r"images-[0-9a-f]{16}",
        dirs[0].name)


# ---------- 渲染文件本体 ----------

def test_rendered_png_present(tmp_path):
    _, outdir, _ = _run(tmp_path)
    pngs = list(
        outdir.rglob("*.png"))
    assert len(pngs) == 1
    assert pngs[0].name == \
        re.sub(
            r"^images-",
            "image_",
            pngs[0].parent.name
        ) + "_p1_00.png"


def test_rendered_png_signature(tmp_path):
    _, outdir, _ = _run(tmp_path)
    png = list(
        outdir.rglob("*.png"))[0]
    assert png.read_bytes()[:8] == \
        b"\x89PNG\r\n\x1a\n"


def test_rendered_png_nonempty(tmp_path):
    _, outdir, _ = _run(tmp_path)
    png = list(
        outdir.rglob("*.png"))[0]
    assert png.stat().st_size == 447


def test_sha_consistent_dir_and_file(
        tmp_path):
    _, outdir, _ = _run(tmp_path)
    png = list(
        outdir.rglob("*.png"))[0]
    sha = png.parent.name[
        len("images-"):]
    assert png.name == (
        f"image_{sha}_p1_00.png")


# ---------- 报告对齐 ----------

def test_run_rc0(tmp_path):
    rc, _, _ = _run(tmp_path)
    assert rc == 0


def test_irer_one(tmp_path):
    _, _, data = _run(tmp_path)
    assert data["per_doc"][0][
        "metrics"][
        "image_resource_exists_ratio"] \
        == {"value": 1.0,
            "reason": None}


def test_report_next_to_per_doc(
        tmp_path):
    _, outdir, _ = _run(tmp_path)
    assert (outdir
            / "r.json").is_file()
