r"""pipeline 输出路径与 CJK 文件名/内容（Round 1555）。

新角度：三个相邻集成不变量零覆盖：

- **输出目录不存在** → process_single 自动创建嵌套父目录
  后写盘成功（此前测试全部预 mkdir，行为未锁）
- **中文文件名** → 正常解析且 document_id 仍为
  doc-<sha256[:16]>（文件名不参与）
- **CJK 内容按字符数分块** → 280 字中文段落
  max_chars=200 切成 [200, 80]（字符计数而非 UTF-8
  字节计数）
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.hash import compute_file_hash
from app.pipeline import process_single
from tests._synthetic_docs import (
    build_minimal_pdf,
)

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


def _cjk_docx(tmp_path: Path) -> Path:
    para = "这是一段很长的中文测试文本。" * 20
    doc_xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w='
        '"http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>'
        f'{para}</w:t></w:r></w:p>'
        '</w:body></w:document>')
    p = tmp_path / "cjk.docx"
    with zipfile.ZipFile(
            p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/document.xml",
                   doc_xml)
    return p


def test_missing_parent_dirs_created(
        tmp_path):
    p = tmp_path / "a.pdf"
    build_minimal_pdf(p, text="(Hello)")
    out = (tmp_path / "nodir" / "sub"
           / "o.json")
    doc, errors = process_single(
        p, out, write_json=True)
    assert errors == []
    assert out.is_file()


def test_cjk_filename(tmp_path):
    p = tmp_path / "中文报告.pdf"
    build_minimal_pdf(p, text="(Hello)")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert doc.document_id == (
        "doc-"
        + compute_file_hash(p)[:16])
    assert doc.elements


def test_cjk_content_char_split(
        tmp_path):
    p = _cjk_docx(tmp_path)
    doc, errors = process_single(
        p, write_json=False,
        max_chars=200)
    assert errors == []
    (el,) = doc.elements
    assert len(el.content) == 280
    assert [len(c.text)
            for c in doc.chunks] == [
        200, 80]
    assert all(
        c.source_element_ids
        for c in doc.chunks)
