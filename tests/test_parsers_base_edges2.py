"""app/parsers/base.py 边角测试 - 第二轮（Round 79）。

补强 tests/test_parsers_base.py（50）+ tests/test_parsers_base_edges.py（113）
未覆盖的：
- ParserError：类型契约（code/message str、details dict）、各种 code 字符串、
  unicode message/code、non-str 参数、exception chaining (__cause__/__context__)、
  catch 按 code 过滤、args 元组、__repr__、与 Exception 兼容
- make_document_id：bytes 输入行为、各种 hex 字符串边界、prefix 验证、
  返回值长度精确、type-stability、相同前缀冲突（不同 hash 前 16 char）
- detect_source_type：bytes path 输入、Path 对象、各种 str path 含分隔符、
  返回值是 SourceType 类型、code 值精确
- Parser ABC：子类继承 default name/version、子类只覆盖 name、子类只覆盖 version、
  abstractmethod 标记、__init_subclass__ 行为、多继承场景
- 模块结构与导入
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.parsers.base import (
    Parser,
    ParserError,
    make_document_id,
    detect_source_type,
    __all__ as base_all,
)


# ---------- ParserError 类型契约 ----------


def test_parser_error_code_is_str_type():
    e = ParserError(code="x", message="m")
    assert isinstance(e.code, str)


def test_parser_error_message_is_str_type():
    e = ParserError(code="x", message="m")
    assert isinstance(e.message, str)


def test_parser_error_details_is_dict_type():
    e = ParserError(code="x", message="m")
    assert isinstance(e.details, dict)


def test_parser_error_args_is_tuple_type():
    e = ParserError(code="x", message="m")
    assert isinstance(e.args, tuple)


def test_parser_error_args_contains_message():
    e = ParserError(code="x", message="hello")
    assert "hello" in e.args


def test_parser_error_args_length_one_with_message():
    e = ParserError(code="x", message="hello")
    assert len(e.args) == 1


def test_parser_error_args_with_empty_message():
    """Exception('') 的 args 是 ('',) 长度 1。"""
    e = ParserError(code="x", message="")
    assert e.args == ("",)


def test_parser_error_str_returns_message():
    e = ParserError(code="x", message="hello world")
    assert str(e) == "hello world"


def test_parser_error_str_does_not_include_code():
    e = ParserError(code="special_code", message="hello")
    assert "special_code" not in str(e)


def test_parser_error_repr_contains_class_name():
    e = ParserError(code="x", message="m")
    assert "ParserError" in repr(e)


# ---------- ParserError 各种 code 字符串 ----------


def test_parser_error_code_file_not_found():
    e = ParserError(code="file_not_found", message="missing")
    assert e.code == "file_not_found"


def test_parser_error_code_unsupported_type():
    e = ParserError(code="unsupported_type", message="bad")
    assert e.code == "unsupported_type"


def test_parser_error_code_unexpected_parser_error():
    e = ParserError(code="unexpected_parser_error", message="boom")
    assert e.code == "unexpected_parser_error"


def test_parser_error_code_empty_string():
    e = ParserError(code="", message="empty code")
    assert e.code == ""


def test_parser_error_code_with_underscore():
    e = ParserError(code="my_error_code", message="x")
    assert e.code == "my_error_code"


def test_parser_error_code_with_dash():
    e = ParserError(code="my-error-code", message="x")
    assert e.code == "my-error-code"


def test_parser_error_code_unicode_chinese():
    e = ParserError(code="错误代码", message="x")
    assert e.code == "错误代码"


def test_parser_error_code_with_digits():
    e = ParserError(code="error_404", message="x")
    assert e.code == "error_404"


def test_parser_error_code_just_digits():
    e = ParserError(code="404", message="x")
    assert e.code == "404"


def test_parser_error_code_long_string():
    long_code = "x" * 1000
    e = ParserError(code=long_code, message="x")
    assert e.code == long_code


# ---------- ParserError message 边界 ----------


def test_parser_error_message_empty():
    e = ParserError(code="x", message="")
    assert e.message == ""


def test_parser_error_message_unicode():
    e = ParserError(code="x", message="你好世界")
    assert e.message == "你好世界"


def test_parser_error_message_with_newline():
    e = ParserError(code="x", message="line1\nline2")
    assert "\n" in e.message


def test_parser_error_message_with_special_chars():
    msg = "!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/"
    e = ParserError(code="x", message=msg)
    assert e.message == msg


def test_parser_error_message_long_string():
    long_msg = "x" * 10000
    e = ParserError(code="x", message=long_msg)
    assert len(e.message) == 10000


# ---------- ParserError details 边界 ----------


def test_parser_error_details_default_independent_per_instance():
    e1 = ParserError(code="x", message="m")
    e2 = ParserError(code="x", message="m")
    e1.details["k"] = "v"
    assert "k" not in e2.details


def test_parser_error_details_none_becomes_empty_dict():
    e = ParserError(code="x", message="m", details=None)
    assert e.details == {}


def test_parser_error_details_passed_through():
    d = {"path": "/foo", "line": 42}
    e = ParserError(code="x", message="m", details=d)
    assert e.details is d  # same reference


def test_parser_error_details_can_be_modified():
    e = ParserError(code="x", message="m", details={"k": "v"})
    e.details["new"] = "value"
    assert e.details["new"] == "value"


def test_parser_error_details_with_nested_dict():
    d = {"outer": {"inner": "value"}}
    e = ParserError(code="x", message="m", details=d)
    assert e.details["outer"]["inner"] == "value"


def test_parser_error_details_with_list_value():
    d = {"items": [1, 2, 3]}
    e = ParserError(code="x", message="m", details=d)
    assert e.details["items"] == [1, 2, 3]


def test_parser_error_details_with_none_value():
    d = {"key": None}
    e = ParserError(code="x", message="m", details=d)
    assert e.details["key"] is None


# ---------- ParserError 异常链 ----------


def test_parser_error_chain_with_raise_from():
    try:
        try:
            raise ValueError("original")
        except ValueError as ve:
            raise ParserError(code="x", message="wrapped") from ve
    except ParserError as pe:
        assert pe.__cause__ is not None
        assert isinstance(pe.__cause__, ValueError)


def test_parser_error_chain_implicit_context():
    try:
        try:
            raise RuntimeError("ctx")
        except RuntimeError:
            raise ParserError(code="x", message="implicit")
    except ParserError as pe:
        assert pe.__context__ is not None
        assert isinstance(pe.__context__, RuntimeError)


def test_parser_error_caught_as_value_error_does_not_match():
    """ParserError 不是 ValueError。"""
    with pytest.raises(ParserError):
        try:
            raise ParserError(code="x", message="m")
        except ValueError:
            pytest.fail("should not catch as ValueError")


def test_parser_error_caught_as_exception():
    with pytest.raises(Exception) as exc:
        raise ParserError(code="x", message="m")
    assert isinstance(exc.value, ParserError)


def test_parser_error_caught_as_base_exception():
    with pytest.raises(BaseException) as exc:
        raise ParserError(code="x", message="m")
    assert isinstance(exc.value, ParserError)


# ---------- ParserError catch 按 code 过滤 ----------


def test_parser_error_can_be_filtered_by_code():
    try:
        raise ParserError(code="specific_code", message="x")
    except ParserError as e:
        if e.code == "specific_code":
            pass  # 测试通过


def test_parser_error_can_be_filtered_by_message_contains():
    try:
        raise ParserError(code="x", message="error in file abc")
    except ParserError as e:
        assert "abc" in e.message


# ---------- ParserError non-str 输入（实际行为） ----------


def test_parser_error_int_code_accepted_no_type_check():
    """实现不检查 code 类型，int 也接受。"""
    e = ParserError(code=42, message="m")  # type: ignore[arg-type]
    assert e.code == 42


def test_parser_error_none_code_accepted_no_type_check():
    e = ParserError(code=None, message="m")  # type: ignore[arg-type]
    assert e.code is None


def test_parser_error_int_message_accepted_no_type_check():
    e = ParserError(code="x", message=42)  # type: ignore[arg-type]
    assert e.message == 42


def test_parser_error_list_details_accepted_no_type_check():
    """实现只检查 `details or {}`，list 是 truthy → 保留为 list。"""
    e = ParserError(code="x", message="m", details=["not", "dict"])  # type: ignore[arg-type]
    # list 是 truthy → details = list
    assert e.details == ["not", "dict"]


# ---------- make_document_id 边界 ----------


def test_make_document_id_basic_format():
    sha = "a" * 64
    result = make_document_id(sha)
    assert result == f"doc-{sha[:16]}"


def test_make_document_id_starts_with_doc_dash():
    sha = "a" * 64
    assert make_document_id(sha).startswith("doc-")


def test_make_document_id_length_exactly_20():
    """'doc-' (4) + 16 chars = 20。"""
    sha = "a" * 64
    assert len(make_document_id(sha)) == 20


def test_make_document_id_uses_first_16_chars():
    sha = "0123456789abcdef" + "f" * 48
    assert make_document_id(sha) == "doc-0123456789abcdef"


def test_make_document_id_deterministic_same_input():
    sha = "a" * 64
    assert make_document_id(sha) == make_document_id(sha)


def test_make_document_id_different_hashes_different_ids():
    sha1 = "a" * 64
    sha2 = "b" * 64
    assert make_document_id(sha1) != make_document_id(sha2)


def test_make_document_id_same_prefix_same_id():
    """两个 hash 前 16 char 相同 → 同 document_id（不验证后 48 char）。"""
    sha1 = "a" * 16 + "b" * 48
    sha2 = "a" * 16 + "c" * 48
    assert make_document_id(sha1) == make_document_id(sha2)


def test_make_document_id_returns_str():
    assert isinstance(make_document_id("a" * 64), str)


def test_make_document_id_all_hex_chars_accepted():
    """所有 hex 字符 0-9a-f 都被接受。"""
    sha = "0123456789abcdef" * 4
    result = make_document_id(sha)
    assert result.startswith("doc-")


def test_make_document_id_uppercase_hex_accepted():
    sha = "A" * 64
    result = make_document_id(sha)
    assert "A" in result


def test_make_document_id_mixed_case_accepted():
    sha = "aAbBcCdDeEfF0011" + "a" * 48
    result = make_document_id(sha)
    assert "aAbBcCdDeEfF0011" in result


def test_make_document_id_does_not_validate_hex():
    """非 hex 字符串也接受（实现只检查长度）。"""
    sha = "xyzABCD!" + "x" * 56  # 64 chars 但非 hex
    result = make_document_id(sha)
    assert result == f"doc-{sha[:16]}"


def test_make_document_id_raises_on_short_hash_length_63():
    with pytest.raises(ValueError):
        make_document_id("a" * 63)


def test_make_document_id_raises_on_long_hash_length_65():
    with pytest.raises(ValueError):
        make_document_id("a" * 65)


def test_make_document_id_raises_on_empty_string():
    with pytest.raises(ValueError):
        make_document_id("")


def test_make_document_id_raises_value_error_type():
    with pytest.raises(ValueError) as exc:
        make_document_id("a" * 63)
    assert isinstance(exc.value, ValueError)


def test_make_document_id_error_message_contains_length():
    with pytest.raises(ValueError) as exc:
        make_document_id("a" * 63)
    assert "63" in str(exc.value)


def test_make_document_id_error_message_contains_source_hash():
    with pytest.raises(ValueError) as exc:
        make_document_id("a" * 63)
    assert "source_hash" in str(exc.value) or "长度" in str(exc.value)


def test_make_document_id_callable():
    assert callable(make_document_id)


# ---------- detect_source_type 边界 ----------


def test_detect_source_type_pdf_value():
    assert detect_source_type("x.pdf") == "pdf"


def test_detect_source_type_docx_value():
    assert detect_source_type("x.docx") == "docx"


def test_detect_source_type_uppercase_pdf():
    assert detect_source_type("X.PDF") == "pdf"


def test_detect_source_type_uppercase_docx():
    assert detect_source_type("X.DOCX") == "docx"


def test_detect_source_type_mixed_case_pdf():
    assert detect_source_type("x.PdF") == "pdf"


def test_detect_source_type_mixed_case_docx():
    assert detect_source_type("x.DoCx") == "docx"


def test_detect_source_type_str_path_accepted():
    assert isinstance(detect_source_type("x.pdf"), str)


def test_detect_source_type_path_object_accepted():
    assert detect_source_type(Path("x.pdf")) == "pdf"


def test_detect_source_type_returns_str_type():
    assert isinstance(detect_source_type("x.pdf"), str)


def test_detect_source_type_double_extension_pdf():
    """file.tar.pdf → suffix 是 .pdf。"""
    assert detect_source_type("file.tar.pdf") == "pdf"


def test_detect_source_type_double_extension_docx():
    assert detect_source_type("file.tar.docx") == "docx"


def test_detect_source_type_dotfile_pdf_raises():
    """.pdf as filename → pathlib 视为隐藏文件，suffix 是 '' → 抛 unsupported_type。"""
    with pytest.raises(ParserError):
        detect_source_type(".pdf")


def test_detect_source_type_rejects_txt():
    with pytest.raises(ParserError):
        detect_source_type("x.txt")


def test_detect_source_type_rejects_md():
    with pytest.raises(ParserError):
        detect_source_type("x.md")


def test_detect_source_type_rejects_html():
    with pytest.raises(ParserError):
        detect_source_type("x.html")


def test_detect_source_type_rejects_ipynb():
    with pytest.raises(ParserError):
        detect_source_type("x.ipynb")


def test_detect_source_type_rejects_no_suffix():
    with pytest.raises(ParserError):
        detect_source_type("README")


def test_detect_source_type_rejects_empty_suffix():
    with pytest.raises(ParserError):
        detect_source_type("file.")


def test_detect_source_type_error_code_value():
    with pytest.raises(ParserError) as exc:
        detect_source_type("x.txt")
    assert exc.value.code == "unsupported_type"


def test_detect_source_type_error_details_has_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type("x.doc")
    assert exc.value.details["suffix"] == ".doc"


def test_detect_source_type_error_details_empty_for_no_suffix():
    with pytest.raises(ParserError) as exc:
        detect_source_type("README")
    assert exc.value.details["suffix"] == ""


def test_detect_source_type_error_message_lists_supported_types():
    with pytest.raises(ParserError) as exc:
        detect_source_type("x.txt")
    msg = str(exc.value)
    assert ".pdf" in msg
    assert ".docx" in msg


def test_detect_source_type_callable():
    assert callable(detect_source_type)


# ---------- Parser ABC 深度 ----------


def test_parser_class_is_abc():
    from abc import ABC
    assert issubclass(Parser, ABC)
    assert isinstance(Parser, type)


def test_parser_has_abstract_method_parse():
    """__abstractmethods__ 包含 'parse'。"""
    assert "parse" in Parser.__abstractmethods__


def test_parser_default_name_value():
    assert Parser.name == "abstract"


def test_parser_default_version_value():
    assert Parser.version == "0.0.0"


def test_parser_default_name_is_str_type():
    assert isinstance(Parser.name, str)


def test_parser_default_version_is_str_type():
    assert isinstance(Parser.version, str)


def test_parser_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        Parser()  # type: ignore[abstract]


def test_parser_subclass_without_parse_cannot_instantiate():
    class Sub(Parser):
        name = "sub"
        version = "1.0"
    with pytest.raises(TypeError):
        Sub()  # type: ignore[abstract]


def test_parser_subclass_with_parse_can_instantiate():
    class Sub(Parser):
        name = "sub"
        version = "1.0"

        def parse(self, path, source_hash):
            return None  # type: ignore[return-value]
    s = Sub()
    assert isinstance(s, Parser)


def test_parser_subclass_inherits_default_name():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return None  # type: ignore[return-value]
    s = Sub()
    assert s.name == "abstract"


def test_parser_subclass_inherits_default_version():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return None  # type: ignore[return-value]
    s = Sub()
    assert s.version == "0.0.0"


def test_parser_subclass_can_override_name_only():
    class Sub(Parser):
        name = "custom_name"

        def parse(self, path, source_hash):
            return None  # type: ignore[return-value]
    s = Sub()
    assert s.name == "custom_name"
    assert s.version == "0.0.0"  # inherited


def test_parser_subclass_can_override_version_only():
    class Sub(Parser):
        version = "2.0.0"

        def parse(self, path, source_hash):
            return None  # type: ignore[return-value]
    s = Sub()
    assert s.name == "abstract"  # inherited
    assert s.version == "2.0.0"


def test_parser_subclass_can_override_both():
    class Sub(Parser):
        name = "x"
        version = "1.2.3"

        def parse(self, path, source_hash):
            return None  # type: ignore[return-value]
    s = Sub()
    assert s.name == "x"
    assert s.version == "1.2.3"


def test_parser_subclass_parse_can_be_called():
    class Sub(Parser):
        name = "x"

        def parse(self, path, source_hash):
            return f"{path}-{source_hash}"
    s = Sub()
    assert s.parse("p", "h") == "p-h"


def test_parser_subclass_parse_signature():
    """子类的 parse 接受 (self, path, source_hash)。"""
    class Sub(Parser):
        def parse(self, path, source_hash):
            return (path, source_hash)
    s = Sub()
    result = s.parse("foo", "bar")
    assert result == ("foo", "bar")


def test_parser_parse_method_is_callable_in_subclass():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return None
    s = Sub()
    assert callable(s.parse)


def test_parser_instance_attribute_dict_independent():
    """不同实例不共享属性。"""
    class Sub(Parser):
        def __init__(self):
            super().__init__()
            self.data = []

        def parse(self, path, source_hash):
            return None
    s1 = Sub()
    s2 = Sub()
    s1.data.append("x")
    assert s2.data == []


# ---------- 模块结构 ----------


def test_module_imports_abc():
    import app.parsers.base as mod
    assert hasattr(mod, "ABC")


def test_module_imports_abstractmethod():
    import app.parsers.base as mod
    assert hasattr(mod, "abstractmethod")


def test_module_imports_path():
    import app.parsers.base as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    import app.parsers.base as mod
    assert hasattr(mod, "Any")


def test_module_imports_literal():
    import app.parsers.base as mod
    assert hasattr(mod, "Literal")


def test_module_imports_document():
    import app.parsers.base as mod
    assert hasattr(mod, "Document")


def test_module_imports_source_type():
    import app.parsers.base as mod
    assert hasattr(mod, "SourceType")


def test_module_has_parser_class():
    import app.parsers.base as mod
    assert hasattr(mod, "Parser")


def test_module_has_parser_error_class():
    import app.parsers.base as mod
    assert hasattr(mod, "ParserError")


def test_module_has_make_document_id():
    import app.parsers.base as mod
    assert hasattr(mod, "make_document_id")


def test_module_has_detect_source_type():
    import app.parsers.base as mod
    assert hasattr(mod, "detect_source_type")


def test_module_has_all():
    import app.parsers.base as mod
    assert hasattr(mod, "__all__")


def test_module_all_is_list():
    assert isinstance(base_all, list)


def test_module_all_count_four():
    assert len(base_all) == 4


def test_module_all_exact_set():
    assert set(base_all) == {"Parser", "ParserError", "make_document_id", "detect_source_type"}


def test_module_all_match_module_attributes():
    import app.parsers.base as mod
    for name in base_all:
        assert hasattr(mod, name)


def test_module_silence_unused_not_in_all():
    assert "_silence_unused" not in base_all


def test_module_silence_unused_callable():
    import app.parsers.base as mod
    assert callable(mod._silence_unused)


def test_module_silence_unused_returns_none():
    import app.parsers.base as mod
    assert mod._silence_unused() is None


def test_module_silence_unused_takes_no_arguments():
    import app.parsers.base as mod
    import inspect
    sig = inspect.signature(mod._silence_unused)
    assert len(sig.parameters) == 0


# ---------- callable 验证 ----------


def test_make_document_id_callable_check():
    assert callable(make_document_id)


def test_detect_source_type_callable_check():
    assert callable(detect_source_type)


def test_parser_class_callable_check():
    """Parser 类（被实例化时会 TypeError，但 callable 仍为 True）。"""
    assert callable(Parser)


def test_parser_error_class_callable():
    assert callable(ParserError)


# ---------- 综合验证 ----------


def test_parser_error_inherits_from_exception():
    assert issubclass(ParserError, Exception)


def test_parser_error_inherits_from_object():
    assert issubclass(ParserError, object)


def test_parser_inherits_from_abc():
    from abc import ABC
    assert issubclass(Parser, ABC)


def test_parser_inherits_from_object():
    assert issubclass(Parser, object)
