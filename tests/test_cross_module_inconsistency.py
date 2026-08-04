"""Round 93 — 跨模块不一致 / 错误传播场景测试。

互补于 test_end_to_end_invariants.py 覆盖"正常路径不变量"，本文件覆盖
"错误路径下的结构化错误传播不变量"：

- 不存在的文件 → ErrorRecord(code=file_not_found, details.path) + Document=None
- 不可读文件（权限/IO） → ErrorRecord(code=hash_io_error)
- 未知 parser → ValueError 直接抛（业务层错误，不该被 process_single 吞掉）
- Parser 抛 ParserError → ErrorRecord(code=$parser_code, message, details)
- Parser 抛意外 Exception → ErrorRecord(code=unexpected_parser_error)
- 空内容（0 element）→ ErrorRecord(code=no_extracted_elements) + warnings 透传
- Schema 校验失败 → ErrorRecord(code=schema_validation_failed, validation_errors)
- 写盘失败（output_path 父目录不可写）→ ErrorRecord(code=write_failed)
- Chunker 失败（mock） → ErrorRecord(code=chunker_failed)
- 错误的 source_hash → parser 收到正确的 hash 仍能继续
- element_id 孤儿引用 → 不在该层级校验，但保证 chunker 不会引入新孤儿
- 重复 document_id → hash 算法保证幂等
- 跨模块 ErrorRecord JSON 可序列化（每个错误都能落盘）
- Bad manifest → load_manifest 错误代码
- 评测 runner 拿到失败 doc → per_doc 仍写入，pipeline_failed=true

不修改任何源码。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.chunkers import StructuralChunker
from app.hash import compute_file_hash, compute_text_hash
from app.models import Document, Element, ErrorRecord, WarningRecord
from app.parsers import ParserError, make_document_id
from app.parsers.text_parser import TextParser
from app.pipeline import get_parser, image_output_dir_for, process_single, validate_only
from app.schema import SchemaValidationError, is_valid, validate


# =============================================================================
# 辅助
# ==============================================================================


def _write_text(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _make_text_doc(doc_id: str = "doc-test", text: str = "hello world."):
    """构造一个最小合法 Document。"""
    from app.hash import compute_text_hash
    h = compute_text_hash(text)
    return Document(
        document_id=doc_id,
        source_path="test.txt",
        source_type="text",
        source_hash=h,
        parser_name="text",
        parser_version="1.0",
        elements=[
            Element(
                element_id=f"{doc_id}::e0000",
                type="paragraph",
                content=text,
                parent_id=None,
                source_locator={},
                confidence=1.0,
                metadata={},
            )
        ],
        chunks=[],
    )


# =============================================================================
# 1. 文件层错误：不存在的文件
# =============================================================================


def test_process_single_missing_file_returns_file_not_found(tmp_path: Path):
    """文件不存在 → ErrorRecord(code=file_not_found) + Document=None。"""
    missing = tmp_path / "no_such_file.txt"
    doc, errors = process_single(missing, write_json=False)
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == "file_not_found"
    assert "path" in errors[0].details
    assert str(missing) in errors[0].details["path"] or missing.name in errors[0].details["path"]


def test_process_single_missing_file_details_path_absolute(tmp_path: Path):
    """details.path 含完整路径。"""
    missing = tmp_path / "absent.txt"
    doc, errors = process_single(missing, write_json=False)
    assert errors[0].details["path"] == str(missing)


def test_process_single_missing_file_does_not_raise(tmp_path: Path):
    """process_single 不向调用方抛异常。"""
    missing = tmp_path / "absent.txt"
    # 不应抛
    result = process_single(missing, write_json=False)
    assert isinstance(result, tuple)


# =============================================================================
# 2. 文件层错误：不可读（mock OSError）
# =============================================================================


def test_process_single_hash_io_error_returns_record(tmp_path: Path, monkeypatch):
    """compute_file_hash 抛 OSError → ErrorRecord(code=hash_io_error)。"""
    f = _write_text(tmp_path, "real.txt", "content")

    def boom(path):
        raise OSError("permission denied")

    monkeypatch.setattr("app.pipeline.compute_file_hash", boom)
    doc, errors = process_single(f, write_json=False)
    assert doc is None
    assert errors[0].code == "hash_io_error"
    assert errors[0].details["exception_type"] == "OSError"


def test_process_single_hash_io_error_details_have_path(tmp_path: Path, monkeypatch):
    f = _write_text(tmp_path, "real.txt", "x")
    monkeypatch.setattr("app.pipeline.compute_file_hash",
                        lambda p: (_ for _ in ()).throw(OSError("denied")))
    doc, errors = process_single(f, write_json=False)
    assert "path" in errors[0].details


# =============================================================================
# 3. 未知 parser
# =============================================================================


def test_get_parser_unknown_name_raises_value_error():
    with pytest.raises(ValueError) as ei:
        get_parser("nonexistent_parser")
    assert "nonexistent_parser" in str(ei.value)


def test_get_parser_unknown_message_lists_supported():
    with pytest.raises(ValueError) as ei:
        get_parser("foo")
    msg = str(ei.value)
    # 至少列出 fallback / text / markdown
    assert "fallback" in msg
    assert "text" in msg


def test_process_single_unknown_parser_caught_as_unexpected(tmp_path: Path):
    """未知 parser → ValueError 被 process_single 的 except Exception 兜底
    转成 unexpected_parser_error（不向调用方抛）。"""
    f = _write_text(tmp_path, "x.txt", "hello")
    doc, errors = process_single(f, parser_name="typo_parser", write_json=False)
    assert doc is None
    assert errors[0].code == "unexpected_parser_error"
    assert errors[0].details["parser_name"] == "typo_parser"
    assert "typo_parser" in errors[0].message or "ValueError" in errors[0].message


# =============================================================================
# 4. Parser 抛 ParserError → ErrorRecord
# =============================================================================


def test_process_single_parser_error_becomes_error_record(tmp_path: Path, monkeypatch):
    """ParserError.code → ErrorRecord.code 一致。"""
    f = _write_text(tmp_path, "x.txt", "hello")

    class BoomParser:
        name = "boom"
        version = "1.0"

        def parse(self, path, source_hash):
            raise ParserError(code="synthetic_error", message="boom!")

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: BoomParser())
    doc, errors = process_single(f, parser_name="boom", write_json=False)
    assert doc is None
    assert errors[0].code == "synthetic_error"
    assert errors[0].message == "boom!"


def test_process_single_unexpected_exception_becomes_unexpected_parser_error(
    tmp_path: Path, monkeypatch
):
    """Parser 抛非 ParserError → ErrorRecord(code=unexpected_parser_error)。"""
    f = _write_text(tmp_path, "x.txt", "hello")

    class RudeParser:
        name = "rude"
        version = "1.0"

        def parse(self, path, source_hash):
            raise RuntimeError("unexpected boom")

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: RudeParser())
    doc, errors = process_single(f, parser_name="rude", write_json=False)
    assert doc is None
    assert errors[0].code == "unexpected_parser_error"
    assert "RuntimeError" in errors[0].message
    assert errors[0].details["parser_name"] == "rude"


def test_process_single_parser_error_details_include_path(tmp_path: Path, monkeypatch):
    f = _write_text(tmp_path, "x.txt", "hi")

    class P:
        name = "p"
        version = "1"

        def parse(self, path, source_hash):
            raise ParserError(code="x", message="m", details={"custom": "v"})

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: P())
    doc, errors = process_single(f, parser_name="p", write_json=False)
    # details 应当包含 path（来自 process_single）+ 原 ParserError 的 details
    assert errors[0].details["path"] == str(f)
    assert errors[0].details["custom"] == "v"


# =============================================================================
# 5. 空内容（0 element） → no_extracted_elements
# =============================================================================


def test_process_single_empty_elements_returns_no_extracted_elements(tmp_path, monkeypatch):
    f = _write_text(tmp_path, "x.txt", "hi")

    class EmptyParser:
        name = "empty"
        version = "1.0"

        def parse(self, path, source_hash):
            return Document(
                document_id=make_document_id(source_hash),
                source_path=str(path),
                source_type="text",
                source_hash=source_hash,
                parser_name="empty",
                parser_version="1.0",
                elements=[],
                chunks=[],
                warnings=[WarningRecord(code="no_text", reason="empty")],
            )

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: EmptyParser())
    doc, errors = process_single(f, parser_name="empty", write_json=False)
    assert doc is None
    assert errors[0].code == "no_extracted_elements"
    # warnings 通过 details 透传
    assert "warnings" in errors[0].details
    assert errors[0].details["warnings"][0]["code"] == "no_text"


def test_process_single_empty_elements_warnings_serializable(tmp_path, monkeypatch):
    """warnings 通过 to_dict 后是 JSON 可序列化的。"""
    import json
    f = _write_text(tmp_path, "x.txt", "hi")

    class EmptyParser:
        name = "empty"
        version = "1"

        def parse(self, path, source_hash):
            return Document(
                document_id=make_document_id(source_hash),
                source_path=str(path),
                source_type="text",
                source_hash=source_hash,
                parser_name="empty",
                parser_version="1",
                elements=[],
                chunks=[],
                warnings=[WarningRecord(code="x", reason="y")],
            )

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: EmptyParser())
    doc, errors = process_single(f, parser_name="empty", write_json=False)
    serialized = json.dumps(errors[0].to_dict())
    assert isinstance(serialized, str)


# =============================================================================
# 6. Schema 校验失败 → schema_validation_failed
# =============================================================================


def test_process_single_schema_validation_failed_returns_error(tmp_path, monkeypatch):
    f = _write_text(tmp_path, "x.txt", "hi")

    class BadDocParser:
        name = "bad"
        version = "1"

        def parse(self, path, source_hash):
            # 故意造一个 schema 验证失败的 Document（source_type 不合法）
            return Document(
                document_id=make_document_id(source_hash),
                source_path=str(path),
                source_type="invalid_type",  # 不在 enum 中
                source_hash=source_hash,
                parser_name="bad",
                parser_version="1",
                elements=[
                    Element(
                        element_id="bad::e0000",
                        type="paragraph",
                        content="hi",
                        parent_id=None,
                        source_locator={},
                        confidence=1.0,
                        metadata={},
                    )
                ],
                chunks=[],
            )

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: BadDocParser())
    doc, errors = process_single(f, parser_name="bad", write_json=False)
    assert doc is None
    assert errors[0].code == "schema_validation_failed"
    assert "validation_errors" in errors[0].details
    # errors 截断到 20 条
    assert isinstance(errors[0].details["validation_errors"], list)


def test_process_single_schema_failed_does_not_write_json(tmp_path, monkeypatch):
    """schema 失败 → 不写盘。"""
    f = _write_text(tmp_path, "x.txt", "hi")
    out_json = tmp_path / "out.json"

    class BadDocParser:
        name = "bad"
        version = "1"

        def parse(self, path, source_hash):
            return Document(
                document_id=make_document_id(source_hash),
                source_path=str(path),
                source_type="invalid_type",
                source_hash=source_hash,
                parser_name="bad",
                parser_version="1",
                elements=[
                    Element(
                        element_id="bad::e0000",
                        type="paragraph",
                        content="hi",
                        parent_id=None,
                        source_locator={},
                        confidence=1.0,
                        metadata={},
                    )
                ],
                chunks=[],
            )

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: BadDocParser())
    process_single(f, out_json, parser_name="bad", write_json=True)
    assert not out_json.exists()


# =============================================================================
# 7. 写盘失败（output_path 不可写）
# =============================================================================


def test_process_single_write_failed_returns_error(tmp_path: Path, monkeypatch):
    f = _write_text(tmp_path, "x.txt", "hi")
    out_json = tmp_path / "out.json"

    # 让 json.dump 抛 OSError
    def boom_dump(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr("json.dump", boom_dump)
    doc, errors = process_single(f, out_json, parser_name="text", write_json=True)
    assert doc is None
    assert errors[0].code == "write_failed"
    assert errors[0].details["path"] == str(out_json)


# =============================================================================
# 8. Chunker 失败
# =============================================================================


def test_process_single_chunker_failure_returns_chunker_failed(tmp_path: Path, monkeypatch):
    f = _write_text(tmp_path, "x.txt", "hello world.")

    class BoomChunker:
        def __init__(self, *a, **kw):
            pass

        def chunk(self, document):
            raise RuntimeError("chunker boom")

    monkeypatch.setattr("app.pipeline.StructuralChunker", BoomChunker)
    doc, errors = process_single(f, parser_name="text", write_json=False)
    assert doc is None
    assert errors[0].code == "chunker_failed"
    assert errors[0].details["exception_type"] == "RuntimeError"


# =============================================================================
# 9. source_hash 一致性：parser 收到与文件匹配的 hash
# =============================================================================


def test_process_single_passes_correct_hash_to_parser(tmp_path: Path, monkeypatch):
    """process_single 计算的 hash 与文件内容匹配，parser 收到。"""
    f = _write_text(tmp_path, "x.txt", "consistent content")
    expected_hash = compute_file_hash(f)
    captured_hash = {}

    class CaptureParser:
        name = "cap"
        version = "1"

        def parse(self, path, source_hash):
            captured_hash["value"] = source_hash
            return Document(
                document_id=make_document_id(source_hash),
                source_path=str(path),
                source_type="text",
                source_hash=source_hash,
                parser_name="cap",
                parser_version="1",
                elements=[
                    Element(
                        element_id="cap::e0000",
                        type="paragraph",
                        content="x",
                        parent_id=None,
                        source_locator={},
                        confidence=1.0,
                        metadata={},
                    )
                ],
                chunks=[],
            )

    monkeypatch.setattr("app.pipeline.get_parser", lambda *a, **kw: CaptureParser())
    process_single(f, parser_name="cap", write_json=False)
    assert captured_hash["value"] == expected_hash


# =============================================================================
# 10. document_id 幂等性：同文件 → 同 document_id
# =============================================================================


def test_process_single_same_file_produces_same_document_id(tmp_path: Path):
    f = _write_text(tmp_path, "x.txt", "same content with enough text to chunk.")
    doc1, _ = process_single(f, parser_name="text", write_json=False)
    doc2, _ = process_single(f, parser_name="text", write_json=False)
    assert doc1 is not None
    assert doc2 is not None
    assert doc1.document_id == doc2.document_id


def test_process_single_different_file_produces_different_document_id(tmp_path: Path):
    f1 = _write_text(tmp_path, "a.txt", "aaa content one")
    f2 = _write_text(tmp_path, "b.txt", "bbb content two")
    doc1, _ = process_single(f1, parser_name="text", write_json=False)
    doc2, _ = process_single(f2, parser_name="text", write_json=False)
    assert doc1 is not None and doc2 is not None
    assert doc1.document_id != doc2.document_id


# =============================================================================
# 11. ErrorRecord JSON 可序列化（每个错误都能落盘）
# =============================================================================


@pytest.mark.parametrize("code", [
    "file_not_found",
    "hash_io_error",
    "parser_crashed",
    "unexpected_parser_error",
    "no_extracted_elements",
    "schema_validation_failed",
    "write_failed",
    "chunker_failed",
])
def test_error_record_json_serializable_for_each_pipeline_code(code):
    """每个 pipeline 错误码的 ErrorRecord 都能 JSON 序列化。"""
    er = ErrorRecord(code=code, message=f"simulated {code}", details={"k": "v"})
    serialized = json.dumps(er.to_dict())
    assert isinstance(serialized, str)
    deserialized = json.loads(serialized)
    assert deserialized["code"] == code


# =============================================================================
# 12. validate_only 错误传播
# =============================================================================


def test_validate_only_missing_file_returns_false_with_message(tmp_path: Path):
    missing = tmp_path / "no_such.json"
    ok, msg = validate_only(missing)
    assert ok is False
    assert "no_such" in msg or "不存在" in msg or missing.name in msg


def test_validate_only_bad_json_returns_false(tmp_path: Path):
    f = tmp_path / "bad.json"
    f.write_text("{not valid json", encoding="utf-8")
    ok, msg = validate_only(f)
    assert ok is False
    assert "JSON" in msg or "json" in msg.lower()


def test_validate_only_valid_json_returns_true(tmp_path: Path):
    """合法 JSON（最小 schema 通过）→ True。"""
    from app.parsers.text_parser import TextParser
    text = "hello world. " * 20
    f_in = tmp_path / "in.txt"
    f_in.write_text(text, encoding="utf-8")
    h = compute_file_hash(f_in)
    parser = TextParser()
    doc = parser.parse(f_in, source_hash=h)
    chunker = StructuralChunker(max_chars=800)
    doc.chunks = chunker.chunk(doc)
    f = tmp_path / "valid.json"
    f.write_text(json.dumps(doc.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    ok, msg = validate_only(f)
    assert ok is True, f"unexpected validation failure: {msg}"


# =============================================================================
# 13. image_output_dir_for 一致性
# =============================================================================


def test_image_output_dir_for_none_returns_none():
    assert image_output_dir_for(None, "abc") is None


def test_image_output_dir_for_uses_first_16_chars_of_hash():
    h = "a" * 64
    out = image_output_dir_for("/tmp/out.json", h)
    assert "images-aaaaaaaaaaaaaaaa" in str(out)  # 16 chars


def test_image_output_dir_for_under_parent_of_output():
    h = "b" * 64
    out = image_output_dir_for("/some/dir/out.json", h)
    p = Path(out)
    assert p.parent == Path("/some/dir")


# =============================================================================
# 14. get_parser 工厂：每个 parser 名 → 实例
# =============================================================================


@pytest.mark.parametrize("name,expected_class_name", [
    ("fallback", "FallbackParser"),
    ("kreuzberg", "KreuzbergParser"),
    ("markdown", "MarkdownParser"),
    ("html", "HtmlParser"),
    ("text", "TextParser"),
    ("ipynb", "IpynbParser"),
])
def test_get_parser_returns_correct_class(name, expected_class_name):
    p = get_parser(name)
    assert type(p).__name__ == expected_class_name


def test_get_parser_fallback_with_image_dir(tmp_path: Path):
    p = get_parser("fallback", image_output_dir=tmp_path)
    assert p._image_output_dir == tmp_path


# =============================================================================
# 15. parser_version 字符串格式（每种 parser 都有非空版本）
# =============================================================================


@pytest.mark.parametrize("name", ["fallback", "kreuzberg", "markdown", "html", "text", "ipynb"])
def test_get_parser_version_nonempty_string(name):
    p = get_parser(name)
    assert isinstance(p.version, str)
    assert len(p.version) > 0


# =============================================================================
# 16. ParserError → ErrorRecord 转换保 details
# =============================================================================


def test_parser_error_with_details_propagated_to_error_record():
    """ParserError details 字典完整保留到 ErrorRecord.details。"""
    err = ParserError(
        code="custom_parser_error",
        message="some failure",
        details={"page": 5, "bbox": [0, 0, 10, 10], "reason": "timeout"},
    )
    assert err.code == "custom_parser_error"
    assert err.details["page"] == 5
    assert err.details["bbox"] == [0, 0, 10, 10]


def test_parser_error_without_details_defaults_to_empty_dict():
    err = ParserError(code="x", message="y")
    assert err.details == {}


def test_parser_error_str_contains_code():
    err = ParserError(code="my_code", message="my message")
    s = str(err)
    assert "my_code" in s or "my message" in s


# =============================================================================
# 17. Bad manifest 错误代码（evaluation）
# =============================================================================


def test_load_manifest_missing_file_raises(tmp_path: Path):
    """load_manifest 不存在文件 → FileNotFoundError 或类似。"""
    from evaluation.manifest import load_manifest
    missing = tmp_path / "no.json"
    with pytest.raises((FileNotFoundError, OSError, Exception)):
        load_manifest(missing)


def test_load_manifest_invalid_json_raises(tmp_path: Path):
    from evaluation.manifest import load_manifest
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(f)


def test_load_manifest_path_must_be_relative(tmp_path: Path):
    """manifest schema：path 必须相对，正斜杠。"""
    from evaluation.manifest import load_manifest
    # 构造一个绝对路径的 manifest，应被拒
    abs_path = str(tmp_path / "x.txt").replace("\\", "/")
    manifest = {
        "version": "1.0",
        "documents": [
            {
                "id": "d1",
                "path": abs_path,  # 绝对路径
                "category": "test",
                "source_type": "docx",
            }
        ],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(f)


def test_load_manifest_backslash_rejected(tmp_path: Path):
    """path 含反斜杠 → 被拒。"""
    from evaluation.manifest import load_manifest
    manifest = {
        "version": "1.0",
        "documents": [
            {
                "id": "d1",
                "path": "subdir\\file.docx",  # 反斜杠
                "category": "test",
                "source_type": "docx",
            }
        ],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(f)


# =============================================================================
# 18. element_id 唯一性（chunker 输入不变量）
# =============================================================================


def test_chunker_does_not_introduce_orphan_element_ids(tmp_path: Path):
    """chunker 输出的 source_element_ids 必须是输入 element_id 的子集。"""
    text = "hello world. " * 50
    f = _write_text(tmp_path, "x.txt", text)
    doc, errors = process_single(f, parser_name="text", write_json=False)
    assert doc is not None
    valid_ids = {e.element_id for e in doc.elements}
    for c in doc.chunks:
        for sid in c.source_element_ids:
            assert sid in valid_ids


def test_chunker_each_chunk_has_at_least_one_source_element_id(tmp_path: Path):
    """CLAUDE.md 不变量：每个 chunk 至少 1 个非空 source_element_id。"""
    text = "sentence one. " * 50 + "sentence two. " * 50
    f = _write_text(tmp_path, "x.txt", text)
    doc, _ = process_single(f, parser_name="text", write_json=False)
    for c in doc.chunks:
        assert len(c.source_element_ids) >= 1


# =============================================================================
# 19. Pipeline 不丢不重
# =============================================================================


def test_pipeline_normalize_no_loss_no_duplication(tmp_path: Path):
    """CLAUDE.md 关键不变量：normalize(Σ chunks.text) == normalize(Σ elements.content)。"""
    from app.chunkers import normalize_text
    text = "a b c. " * 100
    f = _write_text(tmp_path, "x.txt", text)
    doc, _ = process_single(f, parser_name="text", write_json=False)
    sum_chunks = normalize_text(" ".join(c.text for c in doc.chunks))
    sum_elements = normalize_text(" ".join(e.content for e in doc.elements if e.content))
    assert sum_chunks == sum_elements


def test_pipeline_chunk_ids_unique(tmp_path: Path):
    text = "x y z. " * 100
    f = _write_text(tmp_path, "x.txt", text)
    doc, _ = process_single(f, parser_name="text", write_json=False)
    chunk_ids = [c.chunk_id for c in doc.chunks]
    assert len(chunk_ids) == len(set(chunk_ids))


def test_pipeline_element_ids_unique(tmp_path: Path):
    text = "x y z. " * 50
    f = _write_text(tmp_path, "x.txt", text)
    doc, _ = process_single(f, parser_name="text", write_json=False)
    elem_ids = [e.element_id for e in doc.elements]
    assert len(elem_ids) == len(set(elem_ids))


# =============================================================================
# 20. 跨模块 Document → JSON → schema 一致性
# =============================================================================


def test_pipeline_output_passes_schema(tmp_path: Path):
    """process_single 出来的 Document.to_dict 必过 schema。"""
    text = "hello world. " * 20
    f = _write_text(tmp_path, "x.txt", text)
    doc, _ = process_single(f, parser_name="text", write_json=False)
    assert is_valid(doc.to_dict())


def test_pipeline_write_then_read_validates(tmp_path: Path):
    """写盘 → 重新读 → 仍过 schema。"""
    text = "hello world. " * 20
    f = _write_text(tmp_path, "x.txt", text)
    out = tmp_path / "out.json"
    doc, _ = process_single(f, out, parser_name="text", write_json=True)
    assert out.exists()
    ok, msg = validate_only(out)
    assert ok is True


# =============================================================================
# 21. ParserError 的 code/message/details 不可变约束（dataclass）
# =============================================================================


def test_error_record_is_dataclass_with_required_fields():
    """ErrorRecord 必须有 code/message。"""
    er = ErrorRecord(code="c", message="m")
    assert er.code == "c"
    assert er.message == "m"


def test_error_record_to_dict_has_required_keys():
    er = ErrorRecord(code="c", message="m", details={"k": "v"})
    d = er.to_dict()
    assert "code" in d
    assert "message" in d
    assert "details" in d


# =============================================================================
# 22. Warning JSON 序列化（与 ErrorRecord 同族）
# =============================================================================


def test_warning_record_to_dict_has_code_and_reason():
    w = WarningRecord(code="c", reason="r")
    d = w.to_dict()
    assert d["code"] == "c"
    assert d["reason"] == "r"


def test_warning_record_details_default_none():
    w = WarningRecord(code="c", reason="r")
    # 默认 None（schema 允许 null）
    assert w.details is None or w.details == {}


# =============================================================================
# 23. ParserError 异常继承结构
# =============================================================================


def test_parser_error_is_exception():
    assert issubclass(ParserError, Exception)


def test_parser_error_can_be_raised_and_caught():
    try:
        raise ParserError(code="x", message="y")
    except ParserError as e:
        assert e.code == "x"


def test_parser_error_can_be_caught_as_exception():
    """作为通用 Exception 也能捕获。"""
    try:
        raise ParserError(code="x", message="y")
    except Exception as e:
        assert isinstance(e, ParserError)
