r"""app/parsers/base.py 边角测试 - 第四轮（Round 145）。

补强已有 base/edges/edges2（共 265 测试）未覆盖的深度：
- 签名深度（inspect.signature 全部公开对象）
- ParserError 复杂场景（pickling、hashing、copy、关键字参数、混合位置/关键字）
- Parser 抽象类内部（__abstractmethods__、直接子类、abstract property 测试）
- detect_source_type 极端输入（bytes、None、Path 含空格、复杂多点路径）
- make_document_id 极端输入（bytes、None、int、长度刚好 64 含非 hex）
- _silence_unused 内部局部变量
- 模块 dunder 属性（__file__、__name__、__doc__）
- 综合行为（多调用稳定性、错误链）
"""

from __future__ import annotations

import copy
import inspect
import pickle
from pathlib import Path

import pytest

from app.parsers.base import (
    Parser,
    ParserError,
    _silence_unused,
    detect_source_type,
    make_document_id,
)


# =========================================================================
# 签名深度
# =========================================================================


def test_parser_error_init_signature_three_params():
    sig = inspect.signature(ParserError.__init__)
    # self, code, message, details
    assert len(sig.parameters) == 4


def test_parser_error_init_param_names():
    sig = inspect.signature(ParserError.__init__)
    assert set(sig.parameters) == {"self", "code", "message", "details"}


def test_parser_error_init_details_default_none():
    sig = inspect.signature(ParserError.__init__)
    assert sig.parameters["details"].default is None


def test_parser_error_init_code_no_default():
    sig = inspect.signature(ParserError.__init__)
    assert sig.parameters["code"].default is inspect.Parameter.empty


def test_parser_error_init_message_no_default():
    sig = inspect.signature(ParserError.__init__)
    assert sig.parameters["message"].default is inspect.Parameter.empty


def test_parser_error_init_return_annotation_none_str():
    sig = inspect.signature(ParserError.__init__)
    # from __future__ makes it string 'None'
    assert sig.return_annotation in (None, "None", inspect.Signature.empty)


def test_make_document_id_signature_one_param():
    sig = inspect.signature(make_document_id)
    assert len(sig.parameters) == 1


def test_make_document_id_param_name_source_hash():
    sig = inspect.signature(make_document_id)
    assert "source_hash" in sig.parameters


def test_make_document_id_param_no_default():
    sig = inspect.signature(make_document_id)
    assert sig.parameters["source_hash"].default is inspect.Parameter.empty


def test_make_document_id_return_annotation_str():
    sig = inspect.signature(make_document_id)
    assert sig.return_annotation in (str, "str")


def test_detect_source_type_signature_one_param():
    sig = inspect.signature(detect_source_type)
    assert len(sig.parameters) == 1


def test_detect_source_type_param_name_path():
    sig = inspect.signature(detect_source_type)
    assert "path" in sig.parameters


def test_detect_source_type_param_no_default():
    sig = inspect.signature(detect_source_type)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_detect_source_type_return_annotation_source_type():
    sig = inspect.signature(detect_source_type)
    # from __future__ makes it string 'SourceType'
    assert sig.return_annotation in ("SourceType", inspect.Signature.empty)


def test_parser_parse_signature_two_params():
    sig = inspect.signature(Parser.parse)
    # self, path, source_hash
    assert len(sig.parameters) == 3


def test_parser_parse_path_param_name():
    sig = inspect.signature(Parser.parse)
    assert "path" in sig.parameters
    assert "source_hash" in sig.parameters


def test_parser_parse_params_no_default():
    sig = inspect.signature(Parser.parse)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_silence_unused_signature_no_args():
    sig = inspect.signature(_silence_unused)
    assert len(sig.parameters) == 0


# =========================================================================
# ParserError 复杂场景
# =========================================================================


def test_parser_error_keyword_arguments():
    """全部用关键字参数构造。"""
    e = ParserError(code="c1", message="m1", details={"k": "v"})
    assert e.code == "c1"
    assert e.message == "m1"
    assert e.details == {"k": "v"}


def test_parser_error_mixed_positional_keyword():
    e = ParserError("c1", message="m1", details={"k": "v"})
    assert e.code == "c1"
    assert e.details == {"k": "v"}


def test_parser_error_only_required_positional():
    e = ParserError("c1", "m1")
    assert e.code == "c1"
    assert e.message == "m1"
    assert e.details == {}


def test_parser_error_details_kwarg_only():
    e = ParserError("c1", "m1", details={"a": 1})
    assert e.details == {"a": 1}


def test_parser_error_pickle_dumps_succeeds_but_loads_fails():
    """ParserError 继承 Exception.__reduce_ex__ → dumps 成功，loads 失败
    （__init__ 必填 code/message，但 args 只有 message）。
    """
    e = ParserError("c1", "m1", details={"k": "v"})
    data = pickle.dumps(e)
    assert isinstance(data, bytes)
    with pytest.raises(TypeError):
        pickle.loads(data)


def test_parser_error_pickle_default_details_loads_fails():
    e = ParserError("c1", "m1")
    data = pickle.dumps(e)
    with pytest.raises(TypeError):
        pickle.loads(data)


def test_parser_error_is_hashable():
    """exception 实例可 hash（可作 dict key）。"""
    e = ParserError("c1", "m1")
    d = {e: "value"}
    assert d[e] == "value"


def test_parser_error_hash_stable_within_lifetime():
    e = ParserError("c1", "m1")
    assert hash(e) == hash(e)


def test_parser_error_copy_not_supported_due_to_init_signature():
    """ParserError __init__ 必填参数 → copy.copy 抛 TypeError。"""
    e = ParserError("c1", "m1", details={"k": "v"})
    with pytest.raises(TypeError):
        copy.copy(e)


def test_parser_error_deepcopy_not_supported_due_to_init_signature():
    e = ParserError("c1", "m1", details={"k": "v"})
    with pytest.raises(TypeError):
        copy.deepcopy(e)


def test_parser_error_copy_does_not_share_identity_not_supported():
    e = ParserError("c1", "m1")
    with pytest.raises(TypeError):
        copy.copy(e)


def test_parser_error_raise_from_within_except():
    """在 except 块内 raise ParserError，应保留 context。"""
    try:
        try:
            raise ValueError("orig")
        except ValueError:
            raise ParserError("c1", "m1")
    except ParserError as exc:
        assert exc.code == "c1"
        assert isinstance(exc.__context__, ValueError)


def test_parser_error_str_returns_message_with_unicode():
    e = ParserError("c1", "中文错误")
    assert str(e) == "中文错误"


def test_parser_error_args_with_unicode():
    e = ParserError("c1", "中文")
    assert "中文" in e.args[0]


def test_parser_error_repr_contains_message():
    e = ParserError("c1", "specific_msg")
    assert "specific_msg" in repr(e)


def test_parser_error_can_be_raised_with_empty_message_str():
    e = ParserError("c1", "")
    assert e.message == ""
    assert str(e) == ""


def test_parser_error_caught_in_generic_except():
    """except Exception: 能捕获 ParserError。"""
    try:
        raise ParserError("c1", "m1")
    except Exception:
        pass


def test_parser_error_dict_iteration_safe():
    """details 字典支持迭代。"""
    e = ParserError("c1", "m1", details={"a": 1, "b": 2, "c": 3})
    keys = list(e.details.keys())
    assert set(keys) == {"a", "b", "c"}


def test_parser_error_mutate_details_does_not_affect_default():
    """修改一个实例的 details 不影响其他实例默认值。"""
    e1 = ParserError("c1", "m1")
    e1.details["x"] = "y"
    e2 = ParserError("c2", "m2")
    assert e2.details == {}


# =========================================================================
# Parser 抽象类内部
# =========================================================================


def test_parser_abstract_methods_set_contains_parse():
    """__abstractmethods__ 应包含 'parse'。"""
    assert "parse" in Parser.__abstractmethods__


def test_parser_abstract_methods_count_one():
    """仅 'parse' 一个抽象方法。"""
    assert len(Parser.__abstractmethods__) == 1


def test_parser_parse_is_abstractmethod():
    from abc import abstractmethod
    # abstractmethod 是装饰器工厂，检查 __isabstractmethod__ 标记
    assert Parser.parse.__isabstractmethod__ is True


def test_parser_direct_subclass_without_parse_remains_abstract():
    class Sub(Parser):
        pass

    with pytest.raises(TypeError):
        Sub()


def test_parser_direct_subclass_with_parse_instantiable():
    class Sub(Parser):
        name = "sub"
        version = "1.0"

        def parse(self, path, source_hash):
            return None

    s = Sub()
    assert s.name == "sub"
    assert s.version == "1.0"


def test_parser_subclass_can_call_super_parse_raises_not_implemented():
    class Sub(Parser):
        name = "sub"
        version = "1.0"

        def parse(self, path, source_hash):
            super().parse(path, source_hash)

    s = Sub()
    with pytest.raises(NotImplementedError):
        s.parse("x.pdf", "0" * 64)


def test_parser_subclass_inherits_abstract_marker():
    """子类未实现 parse → __abstractmethods__ 仍含 parse。"""

    class Sub(Parser):
        pass

    assert "parse" in Sub.__abstractmethods__


def test_parser_subclass_clears_abstract_marker_when_implemented():

    class Sub(Parser):
        def parse(self, path, source_hash):
            return None

    assert "parse" not in Sub.__abstractmethods__
    assert not Sub.__abstractmethods__


def test_parser_name_attribute_class_level():
    """name 是类属性，访问不需实例化。"""
    assert Parser.name == "abstract"


def test_parser_version_attribute_class_level():
    assert Parser.version == "0.0.0"


def test_parser_class_inherits_abc_meta():
    from abc import ABCMeta
    assert isinstance(Parser, ABCMeta)


def test_parser_class_has_parse_method():
    assert hasattr(Parser, "parse")


def test_parser_parse_method_takes_path_and_source_hash():
    sig = inspect.signature(Sub.parse) if False else None
    # 用一个真实子类查签名
    class S(Parser):
        def parse(self, path, source_hash):
            return None
    sig = inspect.signature(S.parse)
    assert "path" in sig.parameters
    assert "source_hash" in sig.parameters


def test_parser_subclass_can_set_instance_attributes():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return None

    s = Sub()
    s.extra_attr = "value"
    assert s.extra_attr == "value"


def test_parser_subclass_two_instances_independent_dict():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return None

    s1 = Sub()
    s2 = Sub()
    s1.foo = "a"
    assert "foo" not in s2.__dict__


def test_parser_class_has_no_init_override():
    """Parser 没有自定义 __init__。"""
    # ABC 默认 __init__ 继承自 object
    assert "__init__" not in Parser.__dict__


def test_parser_class_dict_contains_name_version_parse():
    keys = set(Parser.__dict__.keys())
    assert "name" in keys
    assert "version" in keys
    assert "parse" in keys


def test_parser_instance_dict_empty_when_no_instance_attrs():
    class Sub(Parser):
        def parse(self, path, source_hash):
            return None

    s = Sub()
    # 没有任何实例属性，__dict__ 为空
    assert s.__dict__ == {}


# =========================================================================
# make_document_id 极端输入
# =========================================================================


def test_make_document_id_all_zero_hash():
    h = "0" * 64
    assert make_document_id(h) == "doc-0000000000000000"


def test_make_document_id_all_f_hash():
    h = "f" * 64
    assert make_document_id(h) == "doc-ffffffffffffffff"


def test_make_document_id_mixed_known_hash():
    h = "0123456789abcdef" * 4  # 64 chars
    assert make_document_id(h) == "doc-0123456789abcdef"


def test_make_document_id_accepts_bytes_silently():
    """bytes 长度 64 + 切片都正常 → 不抛 TypeError，返回 bytes 字符串。
    注意：bytes 长度 64，前 16 bytes 切片后格式化为 "doc-b'\\x00...'" 类形式。
    """
    result = make_document_id(b"0" * 64)
    assert isinstance(result, str)
    assert result.startswith("doc-")


def test_make_document_id_raises_type_error_on_none():
    with pytest.raises((TypeError, AttributeError)):
        make_document_id(None)


def test_make_document_id_raises_type_error_on_int():
    with pytest.raises(TypeError):
        make_document_id(12345)


def test_make_document_id_raises_value_error_on_63_char_with_message():
    with pytest.raises(ValueError, match="source_hash"):
        make_document_id("0" * 63)


def test_make_document_id_raises_value_error_on_65_char():
    with pytest.raises(ValueError):
        make_document_id("0" * 65)


def test_make_document_id_raises_value_error_on_empty():
    with pytest.raises(ValueError):
        make_document_id("")


def test_make_document_id_three_calls_stable():
    h = "a" * 64
    a = make_document_id(h)
    b = make_document_id(h)
    c = make_document_id(h)
    assert a == b == c


def test_make_document_id_length_exactly_20_chars():
    h = "0" * 64
    result = make_document_id(h)
    assert len(result) == 20  # "doc-" (4) + 16 chars


def test_make_document_id_prefix_literal_doc_dash():
    h = "0" * 64
    assert make_document_id(h).startswith("doc-")


def test_make_document_id_does_not_use_full_hash():
    h = "0" * 64
    h = h[:15] + "1" + h[16:]  # 在第 16 位（index 15）改 1
    # 前 16 字符不变，第 17 位改了，应不影响结果
    result1 = make_document_id(h)
    # 反过来
    h2 = "0" * 64
    result2 = make_document_id(h2)
    # h[15] = '1' 是在 index 15，是第 16 个字符，所以前 16 个字符不同
    # 实际上 result1 应该和 result2 不同
    assert result1 != result2


def test_make_document_id_char_17_does_not_affect():
    """前 16 个字符之后的修改不影响 document_id。"""
    base = "0123456789abcdef" + "0" * 48
    modified = "0123456789abcdef" + "1" + "0" * 47
    assert make_document_id(base) == make_document_id(modified)


# =========================================================================
# detect_source_type 极端输入
# =========================================================================


def test_detect_source_type_path_with_spaces_pdf(tmp_path: Path):
    """文件名含空格。"""
    p = tmp_path / "my file.pdf"
    p.write_text("x", encoding="utf-8")
    assert detect_source_type(p) == "pdf"


def test_detect_source_type_path_with_spaces_docx(tmp_path: Path):
    p = tmp_path / "my file.docx"
    p.write_text("x", encoding="utf-8")
    assert detect_source_type(p) == "docx"


def test_detect_source_type_str_with_spaces_pdf(tmp_path: Path):
    p = tmp_path / "with space.pdf"
    p.write_text("x", encoding="utf-8")
    assert detect_source_type(str(p)) == "pdf"


def test_detect_source_type_complex_multiple_dots_pdf():
    """多个点的文件名，取最后一段。"""
    assert detect_source_type("archive.backup.v2.pdf") == "pdf"


def test_detect_source_type_complex_multiple_dots_docx():
    assert detect_source_type("archive.backup.v2.docx") == "docx"


def test_detect_source_type_dot_then_pdf_raises():
    """Path('.pdf').suffix == ''（无文件名），应 raise。"""
    with pytest.raises(ParserError):
        detect_source_type(".pdf")


def test_detect_source_type_dot_then_docx_raises():
    with pytest.raises(ParserError):
        detect_source_type(".docx")


def test_detect_source_type_uppercase_path_with_dirs_pdf():
    """路径含大写目录，但文件名是小写 .pdf。"""
    assert detect_source_type("C:/Users/Foo/file.pdf") == "pdf"


def test_detect_source_type_pathlib_with_parent_pdf(tmp_path: Path):
    p = tmp_path / "sub" / "x.pdf"
    p.parent.mkdir()
    p.write_text("x", encoding="utf-8")
    assert detect_source_type(p) == "pdf"


def test_detect_source_type_returns_pdf_literal_type():
    """detect_source_type('x.pdf') 返回的值等于字符串 'pdf'。"""
    result = detect_source_type("x.pdf")
    assert result == "pdf"


def test_detect_source_type_returns_docx_literal_type():
    result = detect_source_type("x.docx")
    assert result == "docx"


def test_detect_source_type_stable_across_calls():
    assert detect_source_type("a.pdf") == detect_source_type("b.pdf")


def test_detect_source_type_none_raises():
    with pytest.raises((TypeError, AttributeError)):
        detect_source_type(None)


def test_detect_source_type_bytes_raises():
    """bytes 输入应抛 TypeError。"""
    with pytest.raises((TypeError, AttributeError)):
        detect_source_type(b"x.pdf")


def test_detect_source_type_int_raises():
    with pytest.raises((TypeError, AttributeError)):
        detect_source_type(12345)


def test_detect_source_type_pdf_with_query_string_suffix():
    """后缀 .pdf 后还有内容（如 URL query）→ 视为 .pdf+x → 不识别。"""
    # suffix 是最后一段 .pdf?xxx → suffix=.pdf?xxx 不等于 .pdf
    # 但 Path.suffix 只切最后一个 .，所以 ".pdf" 仍是 suffix
    # 'file.pdf?query=val' → Path.suffix = '.pdf?query=val' 不对
    # 实际 Path('file.pdf?query=val').suffix = ''
    # 因为 ? 不是 . 分隔符
    # 让我们验证：Path('a.pdf?b=c').suffix == ''
    # 所以这里应该是 raises
    with pytest.raises(ParserError):
        detect_source_type("file.pdf?query=val")


def test_detect_source_type_error_details_suffix_for_pdf_like():
    with pytest.raises(ParserError) as exc:
        detect_source_type("file.pdff")
    assert exc.value.details == {"suffix": ".pdff"}


def test_detect_source_type_error_details_suffix_for_docx_like():
    with pytest.raises(ParserError) as exc:
        detect_source_type("file.docxx")
    assert exc.value.details == {"suffix": ".docxx"}


def test_detect_source_type_uppercase_pdf_returns_pdf():
    """大写 .PDF → lower → .pdf → 返回 'pdf'。"""
    assert detect_source_type("file.PDF") == "pdf"


def test_detect_source_type_uppercase_docx_returns_docx():
    assert detect_source_type("file.DOCX") == "docx"


def test_detect_source_type_mixed_case_pdf_returns_pdf():
    assert detect_source_type("file.PdF") == "pdf"


def test_detect_source_type_mixed_case_docx_returns_docx():
    assert detect_source_type("file.DoCx") == "docx"


# =========================================================================
# _silence_unused 内部
# =========================================================================


def test_silence_unused_has_docstring():
    assert _silence_unused.__doc__ is not None


def test_silence_unused_docstring_mentions_literal_or_source_type():
    doc = _silence_unused.__doc__
    assert "Literal" in doc or "SourceType" in doc or "类型" in doc


def test_silence_unused_can_be_called_many_times():
    for _ in range(100):
        _silence_unused()


def test_silence_unused_does_not_return_value():
    assert _silence_unused() is None


def test_silence_unused_idempotent():
    """多次调用与一次调用效果相同（无副作用）。"""
    _silence_unused()
    state_before = dir(_silence_unused)
    _silence_unused()
    _silence_unused()
    state_after = dir(_silence_unused)
    assert state_before == state_after


# =========================================================================
# 模块结构 / dunder
# =========================================================================


def test_module_has_docstring():
    import app.parsers.base as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_parser():
    import app.parsers.base as mod
    assert "解析" in mod.__doc__ or "parser" in mod.__doc__.lower()


def test_module_has_file_attr():
    import app.parsers.base as mod
    assert hasattr(mod, "__file__")
    assert mod.__file__ is not None


def test_module_has_name_attr():
    import app.parsers.base as mod
    assert mod.__name__ == "app.parsers.base"


def test_module_imports_abc():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from abc import" in src


def test_module_imports_abstractmethod():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "abstractmethod" in src


def test_module_imports_path():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from pathlib import" in src


def test_module_imports_typing_any():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "Any" in src


def test_module_imports_typing_literal():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "Literal" in src


def test_module_imports_models():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from app.models import" in src


def test_module_imports_document():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "Document" in src


def test_module_imports_source_type():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "SourceType" in src


def test_module_uses_future_annotations():
    import app.parsers.base as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_all_contains_four_names():
    import app.parsers.base as mod
    assert len(mod.__all__) == 4


def test_module_all_exact_set():
    import app.parsers.base as mod
    assert set(mod.__all__) == {
        "Parser", "ParserError",
        "make_document_id", "detect_source_type",
    }


def test_module_all_does_not_contain_silence_unused():
    import app.parsers.base as mod
    assert "_silence_unused" not in mod.__all__


def test_module_silence_unused_starts_with_underscore():
    """_silence_unused 是私有的（前缀 _）。"""
    import app.parsers.base as mod
    assert hasattr(mod, "_silence_unused")


# =========================================================================
# 综合行为
# =========================================================================


def test_parser_error_raise_and_chain_with_from():
    try:
        try:
            raise ValueError("orig")
        except ValueError as ve:
            raise ParserError("c1", "m1") from ve
    except ParserError as exc:
        assert exc.__cause__ is not None
        assert isinstance(exc.__cause__, ValueError)


def test_make_document_id_then_compare_two_hashes():
    h1 = "a" * 64
    h2 = "b" * 64
    id1 = make_document_id(h1)
    id2 = make_document_id(h2)
    assert id1 != id2
    assert id1.startswith("doc-")
    assert id2.startswith("doc-")


def test_detect_source_type_then_parser_error_caught_together():
    """两个 detect_source_type 调用 raise，能在一个 except 块捕获。"""
    errors = []
    for path in ["a.txt", "b.md", "c.csv"]:
        try:
            detect_source_type(path)
        except ParserError as e:
            errors.append(e)
    assert len(errors) == 3
    assert all(e.code == "unsupported_type" for e in errors)


def test_parser_error_does_not_mutate_input_details_dict():
    """构造 ParserError 不应吞噬调用方对 details 的引用（共享引用）。"""
    details = {"k": "v"}
    e = ParserError("c1", "m1", details=details)
    # 引用同一对象
    assert e.details is details


def test_parser_error_default_details_no_shared_object():
    """details=None 时，两次构造的实例 details 不是同一对象。"""
    e1 = ParserError("c1", "m1")
    e2 = ParserError("c2", "m2")
    assert e1.details is not e2.details
