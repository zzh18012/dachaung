r"""pipeline 生成式坏 DOCX 错误路径（Round 1553）。

新角度：`docx_open_failed` 此前只在 **parser 层**
（pytest.raises ParserError）断言过；pipeline 层坏 DOCX
零覆盖（R1548 已做坏 PDF 镜像，本轮补 DOCX 侧）：

- **纯垃圾字节 / 空文件** → docx_open_failed +
  exception_type=PackageNotFoundError（消息含输入路径）
- **合法 zip 但非 DOCX**（无 [Content_Types].xml）→
  docx_open_failed + KeyError
- **有 [Content_Types].xml 但缺 document.xml** →
  docx_open_failed + AttributeError（lxml 容器缺失）
- **失败时不写输出**：write_json=True 且失败 →
  输出文件不出现、目录零残留
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from app.pipeline import process_single


def _run(p: Path):
    return process_single(p, write_json=False)


def test_garbage_bytes(tmp_path):
    p = tmp_path / "g.docx"
    p.write_bytes(b"not a zip " * 8)
    doc, errors = _run(p)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "docx_open_failed"
    assert e.details[
        "exception_type"] == \
        "PackageNotFoundError"
    assert str(p) in e.message


def test_empty_file(tmp_path):
    p = tmp_path / "e.docx"
    p.write_bytes(b"")
    doc, errors = _run(p)
    assert doc is None
    (e,) = errors
    assert e.code == "docx_open_failed"
    assert e.details[
        "exception_type"] == \
        "PackageNotFoundError"


def test_zip_without_content_types(
        tmp_path):
    p = tmp_path / "z.docx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("hello.txt", "hi")
    doc, errors = _run(p)
    assert doc is None
    (e,) = errors
    assert e.code == "docx_open_failed"
    assert e.details[
        "exception_type"] == "KeyError"


def test_zip_without_document_xml(
        tmp_path):
    p = tmp_path / "z.docx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("[Content_Types].xml",
                   "<Types/>")
    doc, errors = _run(p)
    assert doc is None
    (e,) = errors
    assert e.code == "docx_open_failed"
    assert e.details[
        "exception_type"] == \
        "AttributeError"


def test_failure_writes_nothing(
        tmp_path):
    p = tmp_path / "g.docx"
    p.write_bytes(b"not a zip " * 8)
    out = tmp_path / "o.json"
    doc, errors = process_single(
        p, out, write_json=True)
    assert doc is None and errors
    assert not out.exists()
    assert [x.name
            for x in tmp_path.iterdir()
            ] == ["g.docx"]
