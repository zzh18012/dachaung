r"""app/parsers/base.py 边角测试 - 第四轮（Round 165）。

补强已有 base/edges/edges2/edges3（共 383 测试）未覆盖的深度：
- ParserError 深度（attributes、equality、init signature、details 默认值）
- make_document_id 不变量（长度校验、prefix、稳定性）
- detect_source_type 各分支（.pdf/.docx/unsupported/无扩展名/大小写）
- Parser 抽象类（无法实例化、子类必须实现 parse）
- 模块结构与签名
- _silence_unused 存在
- 综合行为
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, SourceType
from app.parsers.base import (
    Parser,
    ParserError,
    detect_source_type,
    make_document_id,
)


# =========================================================================
# ParserError 深度
# =========================================================================


def test_parser_error_init_three_params():
    sig = inspect.signature(ParserError.__init__)
    assert set(sig.parameters) == {"self", "code", "message", "details"}


def test_parser_error_details_default_none_init():
    sig = inspect.signature(ParserError.__init__)
    assert sig.parameters["details"].default is None


def test_parser_error_explicit_details_dict():
    e = ParserError(code="x", message="y", details={"k": "v"})
    assert e.details == {"k": "v"}


def test_parser_error_no_details_defaults_to_empty_dict():
    e = ParserError(code="x", message="y")
    assert e.details == {}


def test_parser_error_explicit_none_details_defaults_to_empty_dict():
    e = ParserError(code="x", message="y", details=None)
    assert e.details == {}


def test_parser_error_attributes():
    e = ParserError(code="my_code", message="my message", details={"a": 1})
    assert e.code == "my_code"
    assert e.message == "my message"
    assert e.details == {"a": 1}


def test_parser_error_str_returns_message():
    e = ParserError(code="x", message="my error message")
    assert str(e) == "my error message"


def test_parser_error_repr_has_class_name():
    e = ParserError(code="x", message="y")
    assert "ParserError" in repr(e)


def test_parser_error_args_has_message_only():
    """super().__init__(message) → args = (message,)。"""
    e = ParserError(code="x", message="y")
    assert e.args == ("y",)


def test_parser_error_inherits_exception():
    assert issubclass(ParserError, Exception)


def test_parser_error_not_valueerror():
    assert not issubclass(ParserError, ValueError)


def test_parser_error_can_be_raised_and_caught_as_exception():
    try:
        raise ParserError(code="x", message="y")
    except Exception:
        pass


def test_parser_error_caught_specifically():
    with pytest.raises(ParserError):
        raise ParserError(code="x", message="y")


def test_parser_error_message_with_special_chars():
    msg = "error with 中文 \n\t whitespace and quotes \""
    e = ParserError(code="x", message=msg)
    assert e.message == msg
    assert str(e) == msg


def test_parser_error_code_can_be_empty_string():
    e = ParserError(code="", message="m")
    assert e.code == ""


def test_parser_error_message_can_be_empty_string():
    e = ParserError(code="c", message="")
    assert e.message == ""
    assert str(e) == ""


def test_parser_error_details_with_nested_dict():
    e = ParserError(code="x", message="y", details={"outer": {"inner": [1, 2, 3]}})
    assert e.details == {"outer": {"inner": [1, 2, 3]}}


def test_parser_error_details_with_list_value():
    e = ParserError(code="x", message="y", details={"items": ["a", "b"]})
    assert e.details["items"] == ["a", "b"]


def test_parser_error_details_not_shared_when_default():
    """不传 details 时，每个实例应有独立的空 dict。"""
    a = ParserError(code="x", message="y")
    b = ParserError(code="x", message="y")
    a.details["k"] = "v"
    assert "k" not in b.details


def test_parser_error_equality_not_identity():
    """Exception 默认按 identity 比较。"""
    a = ParserError(code="x", message="y")
    b = ParserError(code="x", message="y")
    assert a is not b


# =========================================================================
# make_document_id 不变量
# =========================================================================


def test_make_document_id_returns_doc_prefix():
    h = "a" * 64
    assert make_document_id(h).startswith("doc-")


def test_make_document_id_takes_first_16_chars():
    h = "0123456789abcdef" + "X" * 48
    assert make_document_id(h) == "doc-0123456789abcdef"


def test_make_document_id_stable_same_input():
    h = "a" * 64
    assert make_document_id(h) == make_document_id(h)


def test_make_document_id_different_input_different_output():
    h1 = "a" * 64
    h2 = "b" * 64
    assert make_document_id(h1) != make_document_id(h2)


def test_make_document_id_short_raises():
    with pytest.raises(ValueError) as exc:
        make_document_id("short")
    assert "长度异常" in str(exc.value) or "length" in str(exc.value).lower()
    assert "5" in str(exc.value)


def test_make_document_id_long_raises():
    h = "a" * 65
    with pytest.raises(ValueError):
        make_document_id(h)


def test_make_document_id_empty_raises():
    with pytest.raises(ValueError):
        make_document_id("")


def test_make_document_id_no_chars_raises():
    with pytest.raises(ValueError):
        make_document_id("")


def test_make_document_id_exactly_64_ok():
    h = "a" * 64
    result = make_document_id(h)
    assert result == "doc-" + "a" * 16


def test_make_document_id_returns_str():
    h = "a" * 64
    assert isinstance(make_document_id(h), str)


def test_make_document_id_length_4_chars_plus_dash():
    """返回 doc-XXXX... 共 4+16=20 字符。"""
    h = "a" * 64
    result = make_document_id(h)
    assert len(result) == 4 + 16  # "doc-" + 16 chars


def test_make_document_id_hex_inputs():
    """典型的 SHA-256 hex 输入。"""
    h = "e3b0c44298fc1c149afbf4c8996fb924" + "27ae41e4649b934ca495991b7852b855"
    assert len(h) == 64
    result = make_document_id(h)
    assert result == "doc-" + h[:16]


# =========================================================================
# detect_source_type 各分支
# =========================================================================


def test_detect_source_type_pdf():
    assert detect_source_type("foo.pdf") == "pdf"


def test_detect_source_type_docx():
    assert detect_source_type("foo.docx") == "docx"


def test_detect_source_type_uppercase_pdf():
    assert detect_source_type("FOO.PDF") == "pdf"


def test_detect_source_type_uppercase_docx():
    assert detect_source_type("FOO.DOCX") == "docx"


def test_detect_source_type_mixed_case_pdf():
    assert detect_source_type("Foo.PdF") == "pdf"


def test_detect_source_type_unsupported_txt():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo.txt")
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_unsupported_md():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo.md")
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_unsupported_html():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo.html")
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_unsupported_ipynb():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo.ipynb")
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_no_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo")
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_no_suffix_details_empty():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo")
    assert exc.value.details == {"suffix": ""}


def test_detect_source_type_txt_details_has_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo.txt")
    assert exc.value.details == {"suffix": ".txt"}


def test_detect_source_type_message_mentions_pdf_docx():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo.txt")
    msg = exc.value.message
    assert ".pdf" in msg
    assert ".docx" in msg


def test_detect_source_type_message_mentions_actual_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type("foo.json")
    assert ".json" in exc.value.message


def test_detect_source_type_accepts_path_object():
    """支持 pathlib.Path 输入。"""
    assert detect_source_type(Path("foo.pdf")) == "pdf"


def test_detect_source_type_accepts_path_with_dir():
    assert detect_source_type(Path("/tmp/foo.pdf")) == "pdf"


def test_detect_source_type_accepts_relative_path():
    assert detect_source_type("./foo.docx") == "docx"


def test_detect_source_type_double_extension():
    """tar.pdf 这种 — 取最后一段 .pdf。"""
    assert detect_source_type("archive.tar.pdf") == "pdf"


def test_detect_source_type_returns_source_type_type():
    """返回值是 SourceType（即 'pdf'/'docx' 字面量）。"""
    result = detect_source_type("foo.pdf")
    assert result in ("pdf", "docx")


# =========================================================================
# Parser 抽象类
# =========================================================================


def test_parser_is_abstract_class():
    from abc import ABC
    assert issubclass(Parser, ABC)
    assert inspect.isabstract(Parser)


def test_parser_cannot_be_instantiated():
    with pytest.raises(TypeError):
        Parser()  # type: ignore[abstract]


def test_parser_has_abstract_parse():
    assert "__abstractmethods__" in Parser.__dict__
    assert "parse" in Parser.__abstractmethods__


def test_parser_default_name_abstract():
    assert Parser.name == "abstract"


def test_parser_default_version_zero():
    assert Parser.version == "0.0.0"


def test_parser_concrete_subclass_with_parse():
    class MyParser(Parser):
        name = "my"
        version = "1.0.0"

        def parse(self, path, source_hash):
            return None  # type: ignore

    p = MyParser()
    assert p.name == "my"
    assert p.version == "1.0.0"


def test_parser_concrete_subclass_without_parse_raises():
    class IncompleteParser(Parser):
        name = "incomplete"

    with pytest.raises(TypeError):
        IncompleteParser()  # type: ignore[abstract]


def test_parser_subclass_inherits_name_if_not_overridden():
    class P(Parser):
        def parse(self, path, source_hash):
            return None  # type: ignore

    p = P()
    # 未覆盖 name → 继承父类
    assert p.name == "abstract"


def test_parser_parse_signature_abstract():
    sig = inspect.signature(Parser.parse)
    assert set(sig.parameters) == {"self", "path", "source_hash"}


def test_parser_parse_params_no_defaults():
    sig = inspect.signature(Parser.parse)
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        assert p.default is inspect.Parameter.empty


def test_parser_parse_return_annotation_document():
    sig = inspect.signature(Parser.parse)
    assert "Document" in str(sig.return_annotation)


def test_parser_parse_is_abstract_method():
    assert getattr(Parser.parse, "__isabstractmethod__", False) is True


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.parsers.base as mod
    assert mod.__all__ == ["Parser", "ParserError", "make_document_id", "detect_source_type"]


def test_module_all_is_list():
    import app.parsers.base as mod
    assert isinstance(mod.__all__, list)


def test_module_all_no_duplicates():
    import app.parsers.base as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_abc():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from abc import ABC, abstractmethod" in src


def test_module_imports_path():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_literal():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "Literal" in src


def test_module_imports_document_sourcetype():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from app.models import" in src
    assert "Document" in src
    assert "SourceType" in src


def test_module_uses_future_annotations():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.parsers.base as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_business_code_isolation():
    """docstring 提及"业务代码不直接依赖 kreuzberg"等。"""
    import app.parsers.base as mod
    doc = mod.__doc__
    assert "业务代码" in doc or "pipeline" in doc.lower()
    assert "kreuzberg" in doc or "pdfplumber" in doc


def test_module_has_silence_unused():
    """_silence_unused 函数存在（保留 Literal/SourceType 引用）。"""
    import app.parsers.base as mod
    assert hasattr(mod, "_silence_unused")
    assert callable(mod._silence_unused)


def test_module_silence_unused_no_op():
    """_silence_unused 调用应不抛异常。"""
    import app.parsers.base as mod
    mod._silence_unused()


def test_module_silence_unused_returns_none():
    import app.parsers.base as mod
    assert mod._silence_unused() is None


def test_parser_error_class_in_module():
    import app.parsers.base as mod
    assert mod.ParserError is ParserError


def test_parser_class_in_module():
    import app.parsers.base as mod
    assert mod.Parser is Parser


def test_make_document_id_in_module():
    import app.parsers.base as mod
    assert mod.make_document_id is make_document_id


def test_detect_source_type_in_module():
    import app.parsers.base as mod
    assert mod.detect_source_type is detect_source_type


# =========================================================================
# 签名深度
# =========================================================================


def test_make_document_id_signature():
    sig = inspect.signature(make_document_id)
    assert set(sig.parameters) == {"source_hash"}


def test_make_document_id_param_no_default():
    sig = inspect.signature(make_document_id)
    assert sig.parameters["source_hash"].default is inspect.Parameter.empty


def test_make_document_id_return_annotation_str():
    sig = inspect.signature(make_document_id)
    assert "str" in str(sig.return_annotation)


def test_detect_source_type_signature():
    sig = inspect.signature(detect_source_type)
    assert set(sig.parameters) == {"path"}


def test_detect_source_type_param_annotation():
    sig = inspect.signature(detect_source_type)
    annot = str(sig.parameters["path"].annotation)
    assert "str" in annot or "Path" in annot


def test_detect_source_type_return_annotation_sourcetype():
    sig = inspect.signature(detect_source_type)
    assert "SourceType" in str(sig.return_annotation)


# =========================================================================
# 综合行为
# =========================================================================


def test_parser_error_caught_in_caller_uses_code():
    try:
        raise ParserError(code="my_code", message="m", details={"k": "v"})
    except ParserError as e:
        assert e.code == "my_code"
        assert e.details == {"k": "v"}


def test_make_document_id_consistent_with_hash():
    """对真实 SHA-256 hash 的稳定性。"""
    import hashlib
    content = b"hello world"
    h = hashlib.sha256(content).hexdigest()
    assert len(h) == 64
    doc_id = make_document_id(h)
    assert doc_id == f"doc-{h[:16]}"


def test_detect_source_type_idempotent():
    assert detect_source_type("foo.pdf") == detect_source_type("foo.pdf")


def test_parser_error_attributes_immutable_after_raise():
    """raise 后再 catch，属性仍可读。"""
    e = ParserError(code="c", message="m", details={"k": "v"})
    try:
        raise e
    except ParserError as caught:
        assert caught.code == "c"
        assert caught.message == "m"
        assert caught.details == {"k": "v"}
        assert caught is e
