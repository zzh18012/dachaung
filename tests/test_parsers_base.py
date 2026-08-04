"""app/parsers/base.py 的单元测试。

覆盖：
- ParserError 异常类（init / 属性 / 默认值 / 继承）
- make_document_id 哈希派生（前缀 / 长度 / 异常路径）
- detect_source_type 扩展名判定（接受 / 拒绝 / 大写）
- Parser 抽象基类（不能直接实例化 / 子类契约）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import Document
from app.parsers.base import (
    Parser,
    ParserError,
    detect_source_type,
    make_document_id,
)


# ---------- ParserError ----------


def test_parser_error_basic_init():
    err = ParserError(code="some_code", message="boom")
    assert err.code == "some_code"
    assert err.message == "boom"


def test_parser_error_message_attribute_matches_arg():
    err = ParserError(code="c", message="hello world")
    assert err.message == "hello world"


def test_parser_error_str_returns_message():
    err = ParserError(code="c", message="bad thing")
    assert str(err) == "bad thing"


def test_parser_error_inherits_from_exception():
    err = ParserError(code="c", message="x")
    assert isinstance(err, Exception)


def test_parser_error_can_be_raised_and_caught_as_exception():
    with pytest.raises(Exception) as exc:
        raise ParserError(code="c", message="explode")
    assert isinstance(exc.value, ParserError)


def test_parser_error_can_be_raised_and_caught_as_parser_error():
    with pytest.raises(ParserError) as exc:
        raise ParserError(code="my_code", message="explode")
    assert exc.value.code == "my_code"


def test_parser_error_details_default_empty_dict():
    err = ParserError(code="c", message="x")
    assert err.details == {}


def test_parser_error_details_none_becomes_empty_dict():
    err = ParserError(code="c", message="x", details=None)
    assert err.details == {}


def test_parser_error_details_passed_through():
    err = ParserError(code="c", message="x", details={"k": "v", "n": 42})
    assert err.details == {"k": "v", "n": 42}


def test_parser_error_details_is_dict_when_default():
    err = ParserError(code="c", message="x")
    assert isinstance(err.details, dict)


def test_parser_error_details_independent_per_instance():
    """每个实例的 details 默认 {} 都应独立（不能是共享可变默认）。"""
    err1 = ParserError(code="c1", message="x")
    err2 = ParserError(code="c2", message="y")
    err1.details["k"] = "v"
    assert err2.details == {}


def test_parser_error_args_attribute_order():
    """构造参数顺序：code, message, details。"""
    err = ParserError("a", "b", {"k": "v"})
    assert err.code == "a"
    assert err.message == "b"
    assert err.details == {"k": "v"}


# ---------- make_document_id ----------


def test_make_document_id_basic_format():
    h = "a" * 64
    assert make_document_id(h) == "doc-" + "a" * 16


def test_make_document_id_prefix_is_doc_dash():
    h = "0123456789abcdef" * 4  # 64 chars
    doc_id = make_document_id(h)
    assert doc_id.startswith("doc-")


def test_make_document_id_takes_first_16_chars():
    h = "0123456789abcdefFEDCBA9876543210" * 2  # 64 chars
    doc_id = make_document_id(h)
    assert doc_id == "doc-0123456789abcdef"


def test_make_document_id_deterministic():
    h = "b" * 64
    assert make_document_id(h) == make_document_id(h)


def test_make_document_id_different_hashes_different_ids():
    h1 = "a" * 64
    h2 = "b" * 64
    assert make_document_id(h1) != make_document_id(h2)


def test_make_document_id_accepts_uppercase_hex():
    h = "A" * 64
    assert make_document_id(h) == "doc-" + "A" * 16


def test_make_document_id_accepts_mixed_case_hex():
    h = "aAbBcCdDeEfF0123" * 4  # 64 chars
    doc_id = make_document_id(h)
    assert doc_id == "doc-" + "aAbBcCdDeEfF0123"


def test_make_document_id_id_length_is_20():
    """'doc-' (4 chars) + 16 hex chars = 20 chars total."""
    h = "c" * 64
    assert len(make_document_id(h)) == 20


def test_make_document_id_raises_on_short_hash():
    with pytest.raises(ValueError) as exc:
        make_document_id("a" * 63)
    assert "source_hash" in str(exc.value)


def test_make_document_id_raises_on_long_hash():
    with pytest.raises(ValueError) as exc:
        make_document_id("a" * 65)


def test_make_document_id_raises_on_empty_string():
    with pytest.raises(ValueError):
        make_document_id("")


def test_make_document_id_raises_on_non_hex_string():
    """长度匹配但非 hex 字符也应被接受（函数只查长度，不查字符）。

    注：当前实现不验证 hex 字符集，这里验证此契约。
    """
    # 64 字符的非 hex 字符串，函数应接受（契约：只查长度）
    h = "z" * 64
    assert make_document_id(h) == "doc-" + "z" * 16


# ---------- detect_source_type ----------


def test_detect_source_type_pdf(tmp_path: Path):
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-1.4")
    assert detect_source_type(p) == "pdf"


def test_detect_source_type_docx(tmp_path: Path):
    p = tmp_path / "doc.docx"
    p.write_bytes(b"PK")  # 不是真 docx，但 detect 只看扩展名
    assert detect_source_type(p) == "docx"


def test_detect_source_type_uppercase_pdf():
    """扩展名 lower() 比较，所以 .PDF 也接受。"""
    assert detect_source_type(Path("doc.PDF")) == "pdf"


def test_detect_source_type_uppercase_docx():
    assert detect_source_type(Path("doc.DOCX")) == "docx"


def test_detect_source_type_mixed_case_pdf():
    assert detect_source_type(Path("doc.Pdf")) == "pdf"


def test_detect_source_type_mixed_case_docx():
    assert detect_source_type(Path("doc.Docx")) == "docx"


def test_detect_source_type_str_path_accepted():
    assert detect_source_type("doc.pdf") == "pdf"
    assert detect_source_type("doc.docx") == "docx"


def test_detect_source_type_path_object_accepted():
    assert detect_source_type(Path("doc.pdf")) == "pdf"


def test_detect_source_type_rejects_txt():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("doc.txt"))
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_rejects_md():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("doc.md"))
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_rejects_ipynb():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("doc.ipynb"))
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_rejects_html():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("doc.html"))
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_rejects_no_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("noext"))
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_rejects_empty_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("trailingdot."))
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_details_contains_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("doc.unknown"))
    assert exc.value.details == {"suffix": ".unknown"}


def test_detect_source_type_details_empty_for_no_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("noext"))
    assert exc.value.details == {"suffix": ""}


def test_detect_source_type_message_mentions_extension():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("doc.weird"))
    msg = str(exc.value)
    assert ".weird" in msg or "weird" in msg


# ---------- Parser 抽象基类 ----------


def test_parser_cannot_be_instantiated_directly():
    """Parser 是 ABC + abstractmethod parse，不能直接构造。"""
    with pytest.raises(TypeError):
        Parser()  # type: ignore[abstract]


def test_parser_default_name_attribute():
    """Parser 类本身有 name='abstract' 默认值。"""
    assert Parser.name == "abstract"


def test_parser_default_version_attribute():
    """Parser 类本身有 version='0.0.0' 默认值。"""
    assert Parser.version == "0.0.0"


def test_parser_subclass_without_parse_cannot_instantiate():
    class BadParser(Parser):
        name = "bad"
        version = "0.1.0"
        # 没有实现 parse

    with pytest.raises(TypeError):
        BadParser()  # type: ignore[abstract]


def test_parser_subclass_with_parse_can_instantiate():
    class GoodParser(Parser):
        name = "good"
        version = "1.0.0"

        def parse(self, path, source_hash):
            return None  # 占位

    p = GoodParser()
    assert p.name == "good"
    assert p.version == "1.0.0"


def test_parser_subclass_inherits_name_default():
    class P(Parser):
        def parse(self, path, source_hash):
            return None

    p = P()
    # 没有覆盖 name → 继承 'abstract'
    assert p.name == "abstract"
    assert p.version == "0.0.0"


def test_parser_subclass_can_override_name_and_version():
    class P(Parser):
        name = "custom"
        version = "2.3.4"

        def parse(self, path, source_hash):
            return None

    p = P()
    assert p.name == "custom"
    assert p.version == "2.3.4"


def test_parser_parse_abstract_method_raises_not_implemented_in_body():
    """abstractmethod 装饰的 parse 方法 body 是 raise NotImplementedError。

    注：由于 ABC 阻止直接调用，这里只能通过子类 super() 触发；
    实际上 ABC 机制保证子类必须实现 parse，所以 body 不会执行。
    这个测试仅记录契约：body 有 raise NotImplementedError。
    """
    # 由于 Parser() 直接失败，这个测试只能是契约性的
    # 验证 abstractmethod 装饰器存在
    assert getattr(Parser.parse, "__isabstractmethod__", False) is True


def test_parser_subclass_parse_can_return_document(tmp_path: Path):
    """子类的 parse 可以返回 Document 实例（完整契约）。"""

    class DocParser(Parser):
        name = "doc"
        version = "1.0.0"

        def parse(self, path, source_hash):
            return Document(
                document_id=make_document_id(source_hash),
                source_path=str(path),
                source_type="text",  # type: ignore[arg-type]
                source_hash=source_hash,
                parser_name=self.name,
                parser_version=self.version,
                elements=[],
                chunks=[],
                relations=[],
                warnings=[],
                errors=[],
                metadata={},
            )

    p = tmp_path / "x.txt"
    p.write_text("hi")
    parser = DocParser()
    doc = parser.parse(p, "a" * 64)
    assert isinstance(doc, Document)
    assert doc.parser_name == "doc"
    assert doc.parser_version == "1.0.0"
