r"""app/parsers/fallback_parser.py DOCX 边角测试 - 第七十七轮（Round 1506）。

新角度（**警告码覆盖审计**发现的全库唯一零覆盖码）：

- 警告码审计：grep app/ 全部 warning code → 逐码 grep
  tests/，`docx_image_save_failed` 是唯一 0 文件命中的
  码（其余 38 码均有覆盖）；成功写盘路径已由 edges14
  锁（文件名 pattern / bytes / extracted_to_disk=True），
  **失败分支零覆盖**
- 触发方式：image_output_dir 指向一个**普通文件**（mkdir
  parents 到文件内 → OSError/WinError 183）
- probe 实证：**docx_image_save_failed** 告警 + details
  {rid, paragraph_index}；图片回退 resource_path=
  '(unsaved)'、extracted_to_disk=False；段落不受影响
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges65 \
    import _build_docx

_PX = (
    "<w:p><w:r><w:t>pic: </w:t></w:r>"
    "<w:r><w:drawing><wp:inline>"
    '<wp:extent cx="9525" cy="9525"/>'
    "<a:graphic><a:graphicData "
    'uri="http://schemas.'
    'openxmlformats.org/drawingml/'
    '2006/picture">'
    "<pic:pic><pic:nvPicPr>"
    '<pic:cNvPr id="0" name="p.png"/>'
    "<pic:cNvPicPr/></pic:nvPicPr>"
    '<pic:blipFill><a:blip '
    'r:embed="rId20"/></pic:blipFill>'
    "<pic:spPr><a:xfrm>"
    '<a:off x="0" y="0"/>'
    '<a:ext cx="9525" cy="9525"/>'
    "</a:xfrm><a:prstGeom "
    'prst="rect"><a:avLst/>'
    "</a:prstGeom></pic:spPr>"
    "</pic:pic></a:graphicData>"
    "</a:graphic></wp:inline>"
    "</w:drawing></w:r></w:p>")


def _parse_with_blocked_dir(
        tmp_path):
    p = tmp_path / "pic.docx"
    p.write_bytes(
        _build_docx(_PX, image=True))
    blocker = tmp_path / "blocker.txt"
    blocker.write_text(
        "x", encoding="utf-8")
    return FallbackParser(
        image_output_dir=blocker
    ).parse(p, compute_file_hash(p))


def test_image_save_failed_warning(
        tmp_path):
    doc = _parse_with_blocked_dir(
        tmp_path)
    assert len(doc.warnings) == 1
    w = doc.warnings[0]
    assert w.code == \
        "docx_image_save_failed"
    assert w.reason.startswith(
        "图片保存失败 rId=rId20:")
    assert w.details == {
        "rid": "rId20",
        "paragraph_index": 0,
    }


def test_image_falls_back_unsaved(
        tmp_path):
    doc = _parse_with_blocked_dir(
        tmp_path)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "pic:"),
        ("image", None),
    ]
    img = doc.elements[1]
    assert img.resource_path == \
        "(unsaved)"
    assert img.metadata == {
        "byte_size": 69,
        "ext": "png",
        "extracted_to_disk": False,
    }
