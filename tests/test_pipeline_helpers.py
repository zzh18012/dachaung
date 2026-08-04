"""app.pipeline 公共 helper 的单元测试。

process_single 的端到端测试见 tests/test_pipeline_integration.py；
这里聚焦 image_output_dir_for 命名约定（单一事实源）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline import image_output_dir_for


def test_image_output_dir_basic_naming():
    """约定：output_path.parent / images-<sha16>。"""
    out = image_output_dir_for(Path("reports") / "doc.json", "a" * 64)
    assert out == Path("reports") / "images-aaaaaaaaaaaaaaaa"


def test_image_output_dir_accepts_str_path():
    """str 路径也能用。"""
    out = image_output_dir_for("reports/doc.json", "b" * 64)
    assert out == Path("reports") / "images-bbbbbbbbbbbbbbbb"


def test_image_output_dir_none_output_path():
    """output_path=None（不写盘场景）→ helper 返回 None。"""
    assert image_output_dir_for(None, "c" * 64) is None


def test_image_output_dir_short_hash():
    """source_hash 短于 16 字符时取全部，不报错（pipeline 内部约束 sha256 不会短，但 helper 不强制）。"""
    out = image_output_dir_for(Path("out") / "d.json", "abc")
    assert out == Path("out") / "images-abc"


def test_image_output_dir_consistent_with_process_single(tmp_path: Path):
    """helper 推导的结果必须与 process_single 实际使用的 image_output_dir 一致。

    回归：早期 evaluation/runner.py 用 document_id 反推 sha16，依赖两个
    硬编码约定（"doc-" 前缀 + "images-<sha16>" 命名）。本测试用 process_single
    实跑一遍，验证 helper 给出同样答案。
    """
    import zipfile

    from app.pipeline import process_single

    # 合成最小 DOCX（无图，但 process_single 仍会推导 image_output_dir）
    docx = tmp_path / "synthetic.docx"
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hello world.</w:t></w:r></w:p>
  </w:body>
</w:document>'''
    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)

    out_path = tmp_path / "out" / "doc.json"
    out_path.parent.mkdir(parents=True)

    document, errors = process_single(
        docx, out_path, parser_name="fallback", write_json=False,
    )
    assert errors == []
    assert document is not None

    expected_dir = image_output_dir_for(out_path, document.source_hash)
    # image_output_dir_for 给出的路径应当存在（process_single 内部已经创建过）
    # 因为该 DOCX 无图，目录可能未被实际创建；但路径推导必须对齐
    assert expected_dir is not None
    assert expected_dir.name.startswith("images-")
    assert expected_dir.parent == out_path.parent
    # 关键：sha16 部分与 source_hash 前 16 字符一致
    sha16 = expected_dir.name.replace("images-", "")
    assert sha16 == document.source_hash[:16]
    # 也与 document_id 后半部分一致（document_id = "doc-" + sha16）
    assert document.document_id == f"doc-{sha16}"
