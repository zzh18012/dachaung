"""runner.py 的单元测试：聚焦 _process_one 的返回值契约。

端到端的 CLI 测试见 tests/test_evaluation_cli.py；这里覆盖
错误路径下 image_dir 的返回值（必须为 None，不能是 Path()）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


from evaluation.runner import _process_one


@dataclass
class _FakeDocEntry:
    """模拟 manifest.DocumentEntry 的最小结构。"""
    doc_id: str
    resolved_path: Path


def test_process_one_returns_none_image_dir_on_failure(tmp_path: Path):
    """当 process_single 失败时，_process_one 第 5 个返回值必须为 None。

    回归：早期版本返回 `image_dir or Path()`，当 image_dir 为 None 时
    退化成 `Path()`（= 当前工作目录）。下游 `image_dir.is_dir()` 会把
    cwd 当作 image_base_dir，虽然失败文档无图片所以无害，但语义错误。
    """
    missing = tmp_path / "does_not_exist.docx"
    doc = _FakeDocEntry(doc_id="missing-1", resolved_path=missing)

    document, error, elapsed, parser_version, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800,
    )
    assert document is None
    assert error is not None
    assert error["code"] == "file_not_found"
    assert elapsed >= 0
    assert parser_version is None
    # 关键不变量：image_dir 必须是 None，不能是 Path()
    assert image_dir is None, (
        f"image_dir 应为 None（失败文档无图片），实际为 {image_dir!r}"
    )


def test_process_one_returns_path_image_dir_on_success(tmp_path: Path):
    """成功路径下，image_dir 应是 Path 对象（指向 _per_doc/images-<sha16>）。"""
    # 构造最小 DOCX
    import zipfile

    docx_path = tmp_path / "input" / "sample.docx"
    docx_path.parent.mkdir(parents=True)
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
    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)

    doc = _FakeDocEntry(doc_id="ok-1", resolved_path=docx_path)
    document, error, elapsed, parser_version, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800,
    )
    assert document is not None
    assert error is None
    assert parser_version is not None
    # image_dir 应是 Path 对象，且不等于当前工作目录
    assert image_dir is not None
    assert isinstance(image_dir, Path)
    # 名字应为 images-<sha16>
    assert image_dir.name.startswith("images-")
    assert image_dir.parent.name == "_per_doc"
