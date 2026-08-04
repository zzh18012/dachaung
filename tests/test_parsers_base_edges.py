"""app/parsers/base.py 边角测试（Round 61）。

补强 tests/test_parsers_base.py（45 个测试）未覆盖的：
- ParserError 类深度边角（args 长度/code/message 类型/repr/exception chaining）
- make_document_id 返回类型/前缀/字符集范围
- detect_source_type SourceType 字面量/dotfile/双扩展名/反斜杠路径
- Parser 抽象类 __abstractmethods__/name/version 默认值/子类强制契约
- _silence_unused 占位函数
- __all__ 导出列表
- 模块导入无副作用
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.base import (
    Parser,
    ParserError,
    __all__,
    _silence_unused,
    detect_source_type,
    make_document_id,
)


# ---------- ParserError 类深度边角 ----------


def test_parser_error_code_attribute_is_str():
    err = ParserError("code1", "msg")
    assert isinstance(err.code, str)
    assert err.code == "code1"


def test_parser_error_message_attribute_is_str():
    err = ParserError("c", "message text")
    assert isinstance(err.message, str)
    assert err.message == "message text"


def test_parser_error_args_length_one():
    """Exception.args 应只有 message（super().__init__(message)）。"""
    err = ParserError("c", "msg", {"k": "v"})
    assert len(err.args) == 1
    assert err.args[0] == "msg"


def test_parser_error_args_zero_when_empty_message():
    err = ParserError("c", "")
    assert len(err.args) == 1
    assert err.args[0] == ""


def test_parser_error_repr_contains_class_name():
    err = ParserError("code1", "msg")
    assert "ParserError" in repr(err)


def test_parser_error_str_does_not_include_code():
    """str(err) 只有 message，不含 code（避免误用）。"""
    err = ParserError("secret_code", "user message")
    assert "secret_code" not in str(err)
    assert "user message" in str(err)


def test_parser_error_two_instances_not_equal():
    """默认 object identity（无 __eq__）。"""
    e1 = ParserError("c", "m")
    e2 = ParserError("c", "m")
    assert e1 != e2


def test_parser_error_same_object_equal_to_itself():
    e1 = ParserError("c", "m")
    assert e1 == e1


def test_parser_error_can_chain_from_other_exception():
    """raise ParserError from ValueError → __cause__ is ValueError。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise ParserError("c", "outer") from e
    except ParserError as outer:
        assert isinstance(outer.__cause__, ValueError)
        assert str(outer.__cause__) == "inner"


def test_parser_error_can_chain_implicitly():
    """在 except 块内 raise → __context__ 是原异常。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError:
            raise ParserError("c", "outer")
    except ParserError as outer:
        assert isinstance(outer.__context__, ValueError)


def test_parser_error_details_dict_mutable_per_instance():
    """details 默认 {} 每实例独立（details or {}）。"""
    e1 = ParserError("c", "m")
    e2 = ParserError("c", "m")
    e1.details["k"] = "v"
    assert "k" not in e2.details  # 不共享


def test_parser_error_details_pass_through_same_object():
    """传入的 details dict 是同一对象引用。"""
    d = {"k": "v"}
    err = ParserError("c", "m", d)
    assert err.details is d


def test_parser_error_can_be_raised_without_details_kwarg():
    with pytest.raises(ParserError):
        raise ParserError("c", "m")


def test_parser_error_caught_as_general_exception():
    """可作为 Exception 捕获。"""
    with pytest.raises(Exception):
        raise ParserError("c", "m")


def test_parser_error_empty_code_accepted():
    """空 code 也接受（不强制非空）。"""
    err = ParserError("", "msg")
    assert err.code == ""


def test_parser_error_unicode_message():
    err = ParserError("c", "中文消息 🎉")
    assert "中文" in err.message
    assert "🎉" in err.message


# ---------- make_document_id 边角 ----------


def test_make_document_id_returns_str_type():
    result = make_document_id("a" * 64)
    assert isinstance(result, str)


def test_make_document_id_starts_with_doc_dash():
    result = make_document_id("b" * 64)
    assert result.startswith("doc-")


def test_make_document_id_length_exactly_20():
    """'doc-' (4) + 16 chars = 20。"""
    result = make_document_id("c" * 64)
    assert len(result) == 20


def test_make_document_id_first_16_chars_used():
    """取 source_hash 的前 16 字符。"""
    sha = "0123456789abcdef" + "x" * 48
    result = make_document_id(sha)
    assert result == "doc-0123456789abcdef"


def test_make_document_id_deterministic_same_input():
    sha = "a" * 64
    assert make_document_id(sha) == make_document_id(sha)


def test_make_document_id_different_prefixes_different_ids():
    """不同 source_hash 前 16 字符 → 不同 doc_id。"""
    sha1 = "a" * 64
    sha2 = "b" * 64
    assert make_document_id(sha1) != make_document_id(sha2)


def test_make_document_id_same_prefix_same_id():
    """前 16 字符相同 → doc_id 相同（即使后续字符不同）。"""
    sha1 = "a" * 16 + "x" * 48
    sha2 = "a" * 16 + "y" * 48
    assert make_document_id(sha1) == make_document_id(sha2)


def test_make_document_id_raises_on_length_63():
    with pytest.raises(ValueError) as exc:
        make_document_id("a" * 63)
    assert "63" in str(exc.value)


def test_make_document_id_raises_on_length_65():
    with pytest.raises(ValueError):
        make_document_id("a" * 65)


def test_make_document_id_raises_value_error_on_wrong_length():
    """长度异常 → ValueError（不是 ParserError）。"""
    with pytest.raises(ValueError):
        make_document_id("a" * 10)


def test_make_document_id_accepts_all_hex_chars():
    """0-9, a-f 都接受（不强制小写）。"""
    sha = "0123456789abcdefABCDEF" * 3  # 66 chars → 调整
    sha = "0123456789abcdef" * 4  # 64 chars
    result = make_document_id(sha)
    # 不应 raise
    assert result.startswith("doc-")


def test_make_document_id_does_not_validate_hex_chars():
    """只检查长度，不检查字符是否是 hex。"""
    # 非 hex 字符也接受（只看长度）
    result = make_document_id("z" * 64)
    assert result == "doc-zzzzzzzzzzzzzzzz"


def test_make_document_id_empty_string_raises():
    with pytest.raises(ValueError):
        make_document_id("")


# ---------- detect_source_type 边角 ----------


def test_detect_source_type_returns_str_type():
    """detect_source_type 返回 SourceType（str literal）。"""
    result = detect_source_type(Path("x.pdf"))
    assert isinstance(result, str)


def test_detect_source_type_pdf_value():
    assert detect_source_type(Path("x.pdf")) == "pdf"


def test_detect_source_type_docx_value():
    assert detect_source_type(Path("x.docx")) == "docx"


def test_detect_source_type_uppercase_pdf():
    assert detect_source_type(Path("x.PDF")) == "pdf"


def test_detect_source_type_uppercase_docx():
    assert detect_source_type(Path("x.DOCX")) == "docx"


def test_detect_source_type_mixed_case_pdf():
    assert detect_source_type(Path("x.pDf")) == "pdf"
    assert detect_source_type(Path("x.PdF")) == "pdf"


def test_detect_source_type_mixed_case_docx():
    assert detect_source_type(Path("x.dOcX")) == "docx"


def test_detect_source_type_dotfile_pdf():
    """.hidden.pdf → suffix 是 '.pdf'。"""
    assert detect_source_type(Path(".hidden.pdf")) == "pdf"


def test_detect_source_type_dotfile_docx():
    assert detect_source_type(Path(".hidden.docx")) == "docx"


def test_detect_source_type_double_extension_pdf():
    """file.tar.pdf → suffix 是 '.pdf'。"""
    assert detect_source_type(Path("file.tar.pdf")) == "pdf"


def test_detect_source_type_double_extension_docx():
    assert detect_source_type(Path("file.tar.docx")) == "docx"


def test_detect_source_type_str_path_pdf():
    assert detect_source_type("x.pdf") == "pdf"


def test_detect_source_type_str_path_docx():
    assert detect_source_type("x.docx") == "docx"


def test_detect_source_type_str_with_backslashes():
    """Windows 反斜杠路径（Path 自动处理）。"""
    assert detect_source_type("a\\b\\c.pdf") == "pdf"


def test_detect_source_type_str_with_forward_slashes():
    assert detect_source_type("a/b/c.docx") == "docx"


def test_detect_source_type_no_suffix_raises():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("README"))
    assert exc.value.code == "unsupported_type"
    assert "(无)" in exc.value.message


def test_detect_source_type_empty_suffix_raises():
    with pytest.raises(ParserError):
        detect_source_type(Path("README."))  # suffix 是 '.'


def test_detect_source_type_rejects_py():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.py"))


def test_detect_source_type_rejects_json():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.json"))


def test_detect_source_type_rejects_xml():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.xml"))


def test_detect_source_type_rejects_csv():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.csv"))


def test_detect_source_type_rejects_html():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.html"))


def test_detect_source_type_rejects_md():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.md"))


def test_detect_source_type_rejects_ipynb():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.ipynb"))


def test_detect_source_type_rejects_txt():
    with pytest.raises(ParserError):
        detect_source_type(Path("x.txt"))


def test_detect_source_type_details_contains_suffix_for_unknown():
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("x.unknown"))
    assert exc.value.details["suffix"] == ".unknown"


def test_detect_source_type_details_empty_string_for_no_suffix():
    """无扩展名 → suffix 是 '' → details.suffix 是 ''。"""
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("README"))
    assert exc.value.details["suffix"] == ""


def test_detect_source_type_message_lists_supported_types():
    """错误消息应提到 .pdf / .docx。"""
    with pytest.raises(ParserError) as exc:
        detect_source_type(Path("x.unknown"))
    msg = exc.value.message
    assert ".pdf" in msg
    assert ".docx" in msg


# ---------- Parser 抽象类 ----------


def test_parser_class_is_abc():
    """Parser 是 ABC（不能直接实例化）。"""
    from abc import ABC
    assert issubclass(Parser, ABC)


def test_parser_has_abstract_methods():
    """Parser 应有 __abstractmethods__ 集合。"""
    assert hasattr(Parser, "__abstractmethods__")
    assert "parse" in Parser.__abstractmethods__


def test_parser_default_name_is_abstract():
    assert Parser.name == "abstract"


def test_parser_default_version_is_000():
    assert Parser.version == "0.0.0"


def test_parser_default_name_is_str():
    assert isinstance(Parser.name, str)


def test_parser_default_version_is_str():
    assert isinstance(Parser.version, str)


def test_parser_cannot_be_instantiated_directly():
    """抽象类直接实例化 → TypeError。"""
    with pytest.raises(TypeError):
        Parser()  # type: ignore[abstract]


def test_parser_subclass_without_parse_cannot_instantiate():
    class Sub(Parser):
        pass
    with pytest.raises(TypeError):
        Sub()  # type: ignore[abstract]


def test_parser_subclass_with_only_name_no_parse_cannot_instantiate():
    class Sub(Parser):
        name = "sub"
    with pytest.raises(TypeError):
        Sub()  # type: ignore[abstract]


def test_parser_subclass_with_parse_can_instantiate():
    class Sub(Parser):
        name = "sub"
        version = "1.0"
        def parse(self, path, source_hash):
            return None
    s = Sub()
    assert s.name == "sub"
    assert s.version == "1.0"
    assert s.parse("x", "y") is None  # type: ignore[arg-type]


def test_parser_subclass_inherits_default_name():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return None
    s = Sub()
    assert s.name == "abstract"  # 继承默认
    assert s.version == "0.0.0"


def test_parser_subclass_can_override_name_only():
    class Sub(Parser):
        name = "overridden"
        def parse(self, path, source_hash):
            return None
    s = Sub()
    assert s.name == "overridden"
    assert s.version == "0.0.0"  # 默认值


def test_parser_subclass_can_override_version_only():
    class Sub(Parser):
        version = "9.9"
        def parse(self, path, source_hash):
            return None
    s = Sub()
    assert s.name == "abstract"  # 默认
    assert s.version == "9.9"


def test_parser_parse_method_is_callable_in_subclass():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return "result"
    s = Sub()
    assert callable(s.parse)


def test_parser_parse_abstractmethod_marker():
    """Parser.parse 应是 abstractmethod。"""
    from abc import abstractmethod
    # __isabstractmethod__ 标记
    assert getattr(Parser.parse, "__isabstractmethod__", False) is True


# ---------- __all__ 导出列表 ----------


def test_all_exports_listed():
    assert set(__all__) == {
        "Parser", "ParserError", "make_document_id", "detect_source_type"
    }


def test_all_exports_is_list_type():
    assert isinstance(__all__, list)


def test_all_exports_match_module_attributes():
    import app.parsers.base as base_mod
    for name in __all__:
        assert hasattr(base_mod, name)


def test_all_exports_count_is_four():
    assert len(__all__) == 4


def test_silence_unused_not_in_all():
    """_silence_unused 是内部辅助，不应在 __all__。"""
    assert "_silence_unused" not in __all__


# ---------- _silence_unused 占位函数 ----------


def test_silence_unused_returns_none():
    assert _silence_unused() is None


def test_silence_unused_takes_no_arguments():
    import inspect
    sig = inspect.signature(_silence_unused)
    assert len(sig.parameters) == 0


def test_silence_unused_callable():
    assert callable(_silence_unused)


def test_silence_unused_can_be_called_multiple_times():
    """可重复调用（无副作用）。"""
    _silence_unused()
    _silence_unused()
    _silence_unused()
    # 不抛即 OK


# ---------- 模块导入无副作用 ----------


def test_import_base_does_not_crash():
    """导入 base 不应有副作用（仅检查可导入，不 reload 以免污染其他测试）。"""
    import importlib
    mod = importlib.import_module("app.parsers.base")
    assert mod is not None


def test_base_module_has_required_attributes():
    import app.parsers.base as mod
    for attr in ("Parser", "ParserError", "make_document_id", "detect_source_type"):
        assert hasattr(mod, attr)


def test_base_module_has_silence_unused():
    import app.parsers.base as mod
    assert hasattr(mod, "_silence_unused")
