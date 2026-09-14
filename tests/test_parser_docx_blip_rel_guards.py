r"""DOCX a:blip 关系守卫锁定：外链图整体失败 + 非图/缺失 rid 静默跳过（Round 1899，a 优先级）。

`_extract_inline_image_rids` :428 故意收 `r:embed or r:link` 两种
blip 属性，但 `_parse_docx` :502 的 `rel.target_part` 对 External
关系未设防。探针 R1899 三路径实证：

- **r:link 外链图 → 整文档失败**：TargetMode="External" 的 image
  关系 → python-docx `target_part` 抛裸 ValueError（连 ParserError
  都不是）；pipeline 层 process_single 兜成结构化
  `unexpected_parser_error`——**一张外链图废掉整篇文档**
- **r:embed 指向非图关系（styles）→ 静默跳过**：守卫
  `"image" not in rel.reltype` 生效——无 image 元素、无告警
- **r:embed 指向缺失 rid → 静默跳过**：rels.get(rid) 为 None →
  continue——无 image 元素、无告警
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from app.pipeline import process_single


def _blip_docx(path: Path, attr: str, rid: str) -> Path:
    doc = Document()
    p = doc.add_paragraph("para with blip")
    r = p.add_run()
    drawing = OxmlElement("w:drawing")
    blip = OxmlElement("a:blip")
    blip.set(qn(attr), rid)
    drawing.append(blip)
    r._r.append(drawing)
    base = path.parent / "blip_base.docx"
    doc.save(base)
    return base


def _inject_rel(src: Path, dst: Path, rel_attrs: bytes) -> Path:
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/_rels/document.xml.rels":
                data = data.replace(
                    b"</Relationships>",
                    b'<Relationship ' + rel_attrs + b'/>'
                    + b"</Relationships>")
            zout.writestr(item, data)
    return dst


_NS_TYPE = (b'Type="http://schemas.openxmlformats.org/officeDocument'
            b'/2006/relationships/')


def test_docx_external_link_image_fails_whole_document(tmp_path):
    """r:link 外链图（TargetMode=External）：parser 层裸 ValueError；
    pipeline 层兜成 unexpected_parser_error——整文档解析失败。"""
    base = _blip_docx(tmp_path / "base.docx", "r:link", "rIdExt")
    ext = _inject_rel(
        base, tmp_path / "rlink.docx",
        _NS_TYPE + b'image" Id="rIdExt" '
        b'Target="https://example.com/x.png" TargetMode="External"')
    with pytest.raises(ValueError, match="target mode is External"):
        FallbackParser().parse(ext, compute_file_hash(ext))
    result, errors = process_single(ext, output_path=tmp_path / "out.json")
    assert result is None
    assert [e.code for e in errors] == ["unexpected_parser_error"]
    assert "target_part" in errors[0].message


def test_docx_blip_non_image_relationship_skipped(tmp_path):
    """r:embed 指向非图关系（hyperlink reltype、Target 为已存在部件，
    打开期可加载）→ 守卫生效：无 image 元素、无告警，段落照常。
    （styles reltype 不可用——python-docx 打开期要求唯一，重复即拒。）"""
    base = _blip_docx(tmp_path / "base.docx", "r:embed", "rIdHL2")
    sty = _inject_rel(
        base, tmp_path / "hlrel.docx",
        _NS_TYPE + b'hyperlink" Id="rIdHL2" Target="settings.xml"')
    parsed = FallbackParser().parse(sty, compute_file_hash(sty))
    assert [(e.type, e.content) for e in parsed.elements] == [
        ("paragraph", "para with blip")]
    assert [w.code for w in parsed.warnings] == []


def test_docx_blip_missing_rid_skipped(tmp_path):
    """r:embed 指向缺失 rid（rels 里无此关系）→ rel is None →
    continue：无 image 元素、无告警。"""
    missing = _blip_docx(tmp_path / "base.docx", "r:embed", "rId404")
    parsed = FallbackParser().parse(missing, compute_file_hash(missing))
    assert [(e.type, e.content) for e in parsed.elements] == [
        ("paragraph", "para with blip")]
    assert [w.code for w in parsed.warnings] == []
