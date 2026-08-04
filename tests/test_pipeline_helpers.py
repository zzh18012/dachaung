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


# ---------- 边角与缺漏补强（Round 29） ----------


def test_image_output_dir_different_hashes_produce_different_dirs():
    """不同 source_hash → 不同 image 目录。"""
    out_a = image_output_dir_for(Path("out") / "a.json", "a" * 64)
    out_b = image_output_dir_for(Path("out") / "a.json", "b" * 64)
    assert out_a != out_b
    assert out_a.name == "images-aaaaaaaaaaaaaaaa"
    assert out_b.name == "images-bbbbbbbbbbbbbbbb"


def test_image_output_dir_different_output_paths_produce_different_parents():
    """相同 hash + 不同 output_path → 不同 parent。"""
    out_a = image_output_dir_for(Path("a") / "doc.json", "x" * 64)
    out_b = image_output_dir_for(Path("b") / "doc.json", "x" * 64)
    assert out_a.parent != out_b.parent
    # 但 name 相同（hash 一样）
    assert out_a.name == out_b.name


def test_image_output_dir_hash_truncated_to_16_chars():
    """source_hash 长度 ≥ 16 时，name 用前 16 字符。"""
    # 17 字符 hash → 截到 16
    out = image_output_dir_for(Path("o") / "d.json", "abcdefghijklmnopq")
    assert out.name == "images-abcdefghijklmnop"
    # 第 17 个字符 'q' 被丢


def test_image_output_dir_hash_exactly_16_chars():
    """恰好 16 字符 hash 边界。"""
    out = image_output_dir_for(Path("o") / "d.json", "0123456789abcdef")
    assert out.name == "images-0123456789abcdef"


def test_image_output_dir_nested_output_path():
    """嵌套 output_path 的 parent 链保留。"""
    out = image_output_dir_for(Path("a") / "b" / "c" / "d.json", "z" * 64)
    assert out == Path("a") / "b" / "c" / "images-zzzzzzzzzzzzzzzz"


def test_image_output_dir_filename_only_no_parent():
    """output_path 只有文件名（无父目录）→ parent = Path('.')。"""
    out = image_output_dir_for("doc.json", "x" * 64)
    assert out == Path("doc.json").parent / "images-xxxxxxxxxxxxxxxx"
    # Path("doc.json").parent 在 POSIX 是 "."
    assert out.parent == Path(".")


def test_image_output_dir_returns_path_object_when_output_given():
    """output_path 给定时返回值必须是 Path 对象（不是 str）。"""
    out = image_output_dir_for("doc.json", "x" * 64)
    assert isinstance(out, Path)


def test_image_output_dir_empty_string_hash():
    """空 hash → 'images-' 前缀加空串（约定一致，helper 不强制非空）。"""
    out = image_output_dir_for(Path("o") / "d.json", "")
    assert out is not None
    assert out.name == "images-"


# ---------- validate_only ----------


def test_validate_only_returns_true_for_valid_json(tmp_path: Path):
    """合法 document JSON → (True, "OK")。"""
    import json
    from app.pipeline import validate_only

    valid_doc = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "hi",
                "parent_id": None,
                "source_locator": {"paragraph_index": 0},
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hi", "source_element_ids": ["e1"], "metadata": {}}
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is True
    assert msg == "OK"


def test_validate_only_accepts_str_path(tmp_path: Path):
    """str 路径也能用。"""
    import json
    from app.pipeline import validate_only

    valid_doc = {
        "schema_version": "0.1.0",
        "document_id": "d2",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "b" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    # 注意：空 elements 触发 schema 校验通过但 process_single 会拒绝；
    # validate_only 只关心 schema 通过与否
    p = tmp_path / "valid2.json"
    p.write_text(json.dumps(valid_doc), encoding="utf-8")
    ok, msg = validate_only(str(p))
    assert ok is True


# ---------- get_parser additional ----------


def test_get_parser_returns_distinct_instances_per_call():
    """每次调用 get_parser 都应返回新实例（不缓存）。"""
    from app.pipeline import get_parser
    p1 = get_parser("fallback")
    p2 = get_parser("fallback")
    assert p1 is not p2


def test_get_parser_text_parser_no_image_output_dir_kwarg():
    """text parser 不需要 image_output_dir，调用应正常。"""
    from app.pipeline import get_parser
    from app.parsers.text_parser import TextParser
    p = get_parser("text")
    assert isinstance(p, TextParser)


def test_get_parser_markdown_parser_no_image_output_dir_kwarg():
    from app.pipeline import get_parser
    from app.parsers.markdown_parser import MarkdownParser
    p = get_parser("markdown")
    assert isinstance(p, MarkdownParser)


def test_get_parser_ipynb_parser_no_image_output_dir_kwarg():
    from app.pipeline import get_parser
    from app.parsers.ipynb_parser import IpynbParser
    p = get_parser("ipynb")
    assert isinstance(p, IpynbParser)


def test_get_parser_html_parser_no_image_output_dir_kwarg():
    from app.pipeline import get_parser
    from app.parsers.html_parser import HtmlParser
    p = get_parser("html")
    assert isinstance(p, HtmlParser)


def test_get_parser_kreuzberg_parser_no_image_output_dir_kwarg():
    """kreuzberg 不接 image_output_dir（保留给未来扩展）。"""
    from app.pipeline import get_parser
    from app.parsers.kreuzberg_parser import KreuzbergParser
    p = get_parser("kreuzberg")
    assert isinstance(p, KreuzbergParser)
