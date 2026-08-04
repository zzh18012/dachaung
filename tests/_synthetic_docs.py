"""合成测试文档的统一构造函数。

把原本散落在 test_parsers.py / test_pipeline_integration.py /
test_evaluation_cli.py 里的合成 DOCX/PDF 构造逻辑收敛到这里。

设计原则：
- 所有函数接收 **显式 path**（caller 决定写到哪，通常是 `tmp_path / "synthetic.docx"`）
- 返回 Path（与旧行为一致）
- DOCX 用 stdlib zipfile 构造最小合法文件
- PDF 用手写字节流构造最小单页文件
"""

from __future__ import annotations

import zipfile
from pathlib import Path


# ---------- 共用 XML 片段 ----------

_CONTENT_TYPES_BASIC = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

_CONTENT_TYPES_WITH_STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''

_RELS_TOP = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

_RELS_DOC_WITH_STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''

_RELS_DOC_NO_STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>'''

_STYLES_HEADING1_2 = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr></w:style>
</w:styles>'''


def _wrap_doc_xml(body_inner: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + body_inner + '</w:body></w:document>'
    )


def _write_docx(
    path: Path,
    content_types: str,
    doc_rels: str,
    doc_xml: str,
    styles_xml: str | None = None,
) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", _RELS_TOP)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        if styles_xml is not None:
            z.writestr("word/styles.xml", styles_xml)
        z.writestr("word/document.xml", doc_xml)
    return path


# ---------- DOCX builders ----------

def build_minimal_docx(path: Path, with_table: bool = False) -> Path:
    """含 Heading1/Heading2 styles.xml + 1 heading + 1 paragraph + 可选 table。

    用途：fallback parser 的 heading 检测、table 检测、basic structure 测试。
    """
    body_parts = [
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter 1</w:t></w:r></w:p>',
        '<w:p><w:r><w:t>Sentence one. Sentence two.</w:t></w:r></w:p>',
    ]
    if with_table:
        body_parts.append(
            '<w:tbl>'
            '<w:tr><w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc></w:tr>'
            '<w:tr><w:tc><w:p><w:r><w:t>A2</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>B2</w:t></w:r></w:p></w:tc></w:tr>'
            '</w:tbl>'
        )
    return _write_docx(
        path,
        content_types=_CONTENT_TYPES_WITH_STYLES,
        doc_rels=_RELS_DOC_WITH_STYLES,
        doc_xml=_wrap_doc_xml("".join(body_parts)),
        styles_xml=_STYLES_HEADING1_2,
    )


def build_pipeline_docx(path: Path) -> Path:
    """无 styles.xml 但有 pStyle ref + 1 heading + 2 paragraphs。

    用途：pipeline 集成测试（不依赖 heading 检测，只验证 process_single 全程）。
    """
    body = (
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter 1</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Hello world. This is paragraph one.</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Second paragraph with more content.</w:t></w:r></w:p>'
    )
    return _write_docx(
        path,
        content_types=_CONTENT_TYPES_BASIC,
        doc_rels=_RELS_DOC_NO_STYLES,
        doc_xml=_wrap_doc_xml(body),
    )


def build_docx_with_caption(path: Path) -> Path:
    """无 styles.xml，含 2 个 caption 段落 + 1 个普通段落。

    用途：fallback parser 的 caption regex 集成测试。
    """
    body = (
        '<w:p><w:r><w:t>Figure 1. Sample architecture diagram</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Normal paragraph text here.</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>表 2 实验结果汇总</w:t></w:r></w:p>'
    )
    return _write_docx(
        path,
        content_types=_CONTENT_TYPES_BASIC,
        doc_rels=_RELS_DOC_NO_STYLES,
        doc_xml=_wrap_doc_xml(body),
    )


def build_empty_docx(path: Path) -> Path:
    """空 body 的 DOCX。

    用途：触发 docx_no_content warning。
    """
    return _write_docx(
        path,
        content_types=_CONTENT_TYPES_BASIC,
        doc_rels=_RELS_DOC_NO_STYLES,
        doc_xml=_wrap_doc_xml(""),
    )


# ---------- PDF builder ----------

def build_minimal_pdf(path: Path, text: str = "Hello World Chapter 1") -> Path:
    """构造最小单页 PDF（含一行文本）。

    文本以 PDF 字符串字面量形式嵌入（用括号包），所以传入的 text 不能包含 ( ) \。
    调用方若需要这些字符，应自行转义或避开。
    """
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    ]
    stream = b'BT /F1 24 Tf 100 700 Td (' + text.encode('latin-1') + b') Tj ET'
    objs.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

    pdf = b'%PDF-1.4\n'
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f'{i} 0 obj\n'.encode() + body + b'\nendobj\n'
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b'xref\n' + f'0 {n}\n'.encode() + b'0000000000 65535 f \n'
    for off in offsets:
        pdf += f'{off:010d} 00000 n \n'.encode()
    pdf += b'trailer\n<< /Size ' + str(n).encode() + b' /Root 1 0 R >>\nstartxref\n'
    pdf += str(xref_pos).encode() + b'\n%%EOF'

    path.write_bytes(pdf)
    return path
