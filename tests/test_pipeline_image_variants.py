r"""pipeline 图片路径策略变体（Round 1552）。

新角度：R1551 锁定了标准路径（output_path + write_json）
下的图片落盘；本轮锁 **output_path 缺失 / write_json=False**
与**多图片序号 / 重复运行**策略——零覆盖：

- **output_path=None** → resource_path 为哨兵
  `'(unrendered)'`、extracted_to_disk=False、不写任何目录
- **output_path 给定但 write_json=False** → 图片**仍**落盘
  到输出旁的 images-<sha16>/，但 JSON 不写
- **同页两图** → `_p1_00.png` / `_p1_01.png` 顺序编号
- **同输出重复运行** → 目录内容不增长（幂等）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, n_imgs: int = 1,
         name: str = "img.pdf") -> Path:
    parts = []
    for i in range(n_imgs):
        parts.append(
            f"q 100 0 0 100 72"
            f" {692 - i * 120} cm"
            f" /Im{i + 1} Do Q")
    parts.append("BT /F1 12 Tf 72 100"
                 " Td (BODY) Tj ET")
    c = " ".join(parts)
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R] /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >>"
            " /XObject << "
            + " ".join(
                f"/Im{i + 1} {7 + i} 0 R"
                for i in range(n_imgs))
            + " >> >> /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
    }
    for i in range(n_imgs):
        px = bytes(
            [255, i * 60 % 256, 0])
        objs[7 + i] = (
            f"<< /Type /XObject"
            f" /Subtype /Image"
            f" /Width 1 /Height 1"
            f" /ColorSpace /DeviceRGB"
            f" /BitsPerComponent 8"
            f" /Length {len(px)} >>"
            f"\nstream\n"
            ).encode() + px \
            + b"\nendstream"
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o + b"\nendobj\n"
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size "
            + str(len(objs) + 1).encode()
            + b" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _imgs(doc):
    return [e for e in doc.elements
            if e.type == "image"]


def test_no_output_path_unrendered(
        tmp_path):
    p = _pdf(tmp_path)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (img,) = _imgs(doc)
    assert img.resource_path \
        == "(unrendered)"
    assert img.metadata[
        "extracted_to_disk"] is False
    assert img.content is None
    assert [x.name
            for x in tmp_path.
            iterdir()] == ["img.pdf"]


def test_images_written_without_json(
        tmp_path):
    p = _pdf(tmp_path)
    out = tmp_path / "sub" / "o.json"
    out.parent.mkdir()
    doc, errors = process_single(
        p, out, write_json=False)
    assert errors == []
    sha = compute_file_hash(p)[:16]
    (img,) = _imgs(doc)
    assert img.metadata[
        "extracted_to_disk"] is True
    d = out.parent / f"images-{sha}"
    assert d.is_dir()
    assert (d / f"image_{sha}"
            f"_p1_00.png").is_file()
    assert not out.exists()


def test_two_images_sequential(
        tmp_path):
    p = _pdf(tmp_path, n_imgs=2)
    out = tmp_path / "o.json"
    doc, errors = process_single(
        p, out, write_json=True)
    assert errors == []
    sha = compute_file_hash(p)[:16]
    imgs = _imgs(doc)
    assert len(imgs) == 2
    for i, e in enumerate(imgs):
        assert e.resource_path\
            .endswith(
                f"\\image_{sha}"
                f"_p1_{i:02d}.png")
    d = tmp_path / f"images-{sha}"
    assert sorted(
        f.name for f in d.iterdir()
    ) == [f"image_{sha}_p1_00.png",
          f"image_{sha}_p1_01.png"]
    assert [c.text
            for c in doc.chunks] == [
        "BODY"]


def test_rerun_dir_idempotent(
        tmp_path):
    p = _pdf(tmp_path, n_imgs=2)
    out = tmp_path / "o.json"
    for _ in range(2):
        _, errors = process_single(
            p, out, write_json=True)
        assert errors == []
    sha = compute_file_hash(p)[:16]
    d = tmp_path / f"images-{sha}"
    assert sorted(
        f.name for f in d.iterdir()
    ) == [f"image_{sha}_p1_00.png",
          f"image_{sha}_p1_01.png"]
