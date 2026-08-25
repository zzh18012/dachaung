r"""pipeline 错误优先级（Round 1557）。

新角度：各错误码单独出现时都有覆盖，但**多个失败
条件叠加时谁先胜出**零覆盖（probe 实证顺序：
扩展名检查 > 打开/解析 > chunker > 空元素检查）：

- **坏 PDF + 非法 max_chars** → 仅 pdfplumber_open_
  failed（解析先于 chunker）
- **⚠ 空元素 DOCX + 非法 max_chars** → 仅
  chunker_failed（chunker 先于 no_extracted_elements
  检查——空元素判定发生在分块之后）
- **未知扩展名 + 非法 max_chars** → 仅 unsupported_type
- 对照：空元素 DOCX + 合法 max_chars →
  no_extracted_elements
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.pipeline import process_single

_CT = ('<?xml version="1.0"?>'
       '<Types xmlns="http://schemas.'
       'openxmlformats.org/package/'
       '2006/content-types">'
       '<Default Extension="rels"'
       ' ContentType="application/'
       'vnd.openxmlformats-package.'
       'relationships+xml"/>'
       '<Default Extension="xml"'
       ' ContentType="application/xml"/>'
       '<Override PartName='
       '"/word/document.xml"'
       ' ContentType="application/vnd.'
       'openxmlformats-officedocument.'
       'wordprocessingml.document.main+xml"'
       '/></Types>')
_RELS = ('<?xml version="1.0"?>'
         '<Relationships xmlns='
         '"http://schemas.openxmlformats.'
         'org/package/2006/relationships">'
         '<Relationship Id="rId1"'
         ' Type="http://schemas.'
         'openxmlformats.org/officeDocument/'
         '2006/relationships/officeDocument"'
         ' Target="word/document.xml"/>'
         '</Relationships>')


def _empty_docx(tmp_path: Path) -> Path:
    p = tmp_path / "empty.docx"
    with zipfile.ZipFile(
            p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr(
            "word/document.xml",
            '<?xml version="1.0"?>'
            '<w:document xmlns:w='
            '"http://schemas.openxmlformats.'
            'org/wordprocessingml/2006/main">'
            '<w:body></w:body>'
            '</w:document>')
    return p


def test_broken_pdf_beats_bad_max_chars(
        tmp_path):
    p = tmp_path / "g.pdf"
    p.write_bytes(b"garbage bytes")
    doc, errors = process_single(
        p, write_json=False, max_chars=5)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "pdfplumber_open_failed"]


def test_chunker_beats_empty_elements(
        tmp_path):
    p = _empty_docx(tmp_path)
    doc, errors = process_single(
        p, write_json=False, max_chars=5)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "chunker_failed"]


def test_unsupported_ext_beats_all(
        tmp_path):
    p = tmp_path / "x.xyz"
    p.write_text("data")
    doc, errors = process_single(
        p, write_json=False, max_chars=5)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "unsupported_type"]


def test_empty_docx_valid_max_chars(
        tmp_path):
    p = _empty_docx(tmp_path)
    doc, errors = process_single(
        p, write_json=False)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]
