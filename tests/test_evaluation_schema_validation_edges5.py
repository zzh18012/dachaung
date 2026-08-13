"""evaluation/schema_validation.py 第五轮 edges 测试（Round 591）。

补强 edges4 未触及的角度（第五批）。
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import patch

import pytest

from evaluation.schema_validation import document_passes_schema
import evaluation.schema_validation as smod


# ---------- document_passes_schema 输入类型 第五批


def test_document_passes_schema_memoryview_returns_false_batch5():
    """memoryview 不是 dict → False。"""
    mv = memoryview(b"abc")
    assert document_passes_schema(mv) is False  # type: ignore[arg-type]


def test_document_passes_schema_range_returns_false_batch5():
    assert document_passes_schema(range(3)) is False  # type: ignore[arg-type]


def test_document_passes_schema_bytearray_returns_false_batch5():
    assert document_passes_schema(bytearray(b"x")) is False  # type: ignore[arg-type]


def test_document_passes_schema_complex_returns_false_batch5():
    assert document_passes_schema(complex(1, 2)) is False  # type: ignore[arg-type]


def test_document_passes_schema_iterator_returns_false_batch5():
    """iter 对象不是 dict → False。"""
    assert document_passes_schema(iter([1, 2])) is False  # type: ignore[arg-type]


def test_document_passes_schema_generator_returns_false_batch5():
    def gen():
        yield 1
    assert document_passes_schema(gen()) is False  # type: ignore[arg-type]


def test_document_passes_schema_class_instance_returns_false_batch5():
    class Foo:
        pass
    assert document_passes_schema(Foo()) is False  # type: ignore[arg-type]


def test_document_passes_schema_function_object_returns_false_batch5():
    def f():
        pass
    assert document_passes_schema(f) is False  # type: ignore[arg-type]


def test_document_passes_schema_module_returns_false_batch5():
    """模块对象不是 dict。"""
    import sys
    assert document_passes_schema(sys) is False  # type: ignore[arg-type]


def test_document_passes_schema_type_returns_false_batch5():
    """type 对象不是 dict。"""
    assert document_passes_schema(int) is False  # type: ignore[arg-type]


# ---------- document_passes_schema dict 内容 第五批


def test_document_passes_schema_dict_with_tuple_keys_batch5():
    """tuple 不可作 JSON key。"""
    doc = {(1, 2): "value"}  # type: ignore[dict-item]
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_frozenset_value_batch5():
    doc = {"x": frozenset([1, 2])}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_set_value_batch5():
    """set 不可 JSON 序列化。"""
    doc = {"x": {1, 2}}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_callable_value_batch5():
    doc = {"x": callable}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_inf_value_batch5():
    """inf 不可 JSON 序列化但 jsonschema 可能接受。"""
    doc = {"x": float("inf")}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_nan_value_batch5():
    doc = {"x": float("nan")}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_self_referential_batch5():
    """自引用 dict。"""
    doc: dict[str, Any] = {}
    doc["self"] = doc
    try:
        result = document_passes_schema(doc)
        assert isinstance(result, bool)
    except (ValueError, TypeError, RecursionError):
        pass


def test_document_passes_schema_dict_with_long_key_batch5():
    doc = {"x" * 1000: "value"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_long_value_batch5():
    doc = {"key": [1] * 1000}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


# ---------- document_passes_schema 行为 第五批


def test_document_passes_schema_returns_python_bool_not_numpy_batch5():
    """返回的是 Python 内置 bool（不是 numpy 等）。"""
    result = document_passes_schema({})
    assert type(result) is bool


def test_document_passes_schema_with_100_dicts_no_raise_batch5():
    """连续 100 次调用不抛异常。"""
    for i in range(100):
        result = document_passes_schema({"i": i})
        assert isinstance(result, bool)


def test_document_passes_schema_consistent_with_is_valid_batch5():
    """document_passes_schema 与底层 is_valid 一致（仅多包一层 bool()）。"""
    from app.schema import is_valid
    for doc in [{}, {"x": 1}, {"a": "b"}, None, "x"]:
        a = document_passes_schema(doc)  # type: ignore[arg-type]
        b = bool(is_valid(doc))  # type: ignore[arg-type]
        assert a == b


def test_document_passes_schema_accepts_keyword_document_batch5():
    """document 是 POSITIONAL_OR_KEYWORD，可按关键字传。"""
    result = document_passes_schema(document={})
    assert isinstance(result, bool)


def test_document_passes_schema_no_unexpected_kwargs_batch5():
    """未知关键字参数 → TypeError。"""
    with pytest.raises(TypeError):
        document_passes_schema(unknown={})  # type: ignore[call-arg]


def test_document_passes_schema_no_extra_positional_args_batch5():
    """不接受多于 1 个位置参数。"""
    with pytest.raises(TypeError):
        document_passes_schema({}, {})  # type: ignore[call-arg]


def test_document_passes_schema_returns_consistent_false_for_invalid_batch5():
    """无效输入始终 False。"""
    invalid_inputs = [None, [], 0, 0.0, "", b"", (), frozenset(), object()]
    for inp in invalid_inputs:
        assert document_passes_schema(inp) is False  # type: ignore[arg-type]


# ---------- 模块结构 第五批


def test_module_lines_count_under_30_batch5():
    src = inspect.getsource(smod)
    assert len(src.split("\n")) < 30


def test_module_has_all_attribute_batch5():
    assert hasattr(smod, "__all__")


def test_module_all_is_list_batch5():
    assert isinstance(smod.__all__, list)


def test_module_all_exact_one_element_batch5():
    assert smod.__all__ == ["document_passes_schema"]


def test_module_all_len_one_batch5():
    assert len(smod.__all__) == 1


def test_module_docstring_present_batch5():
    assert smod.__doc__ is not None


def test_module_docstring_mentions_schema_batch5():
    doc = smod.__doc__
    assert "schema" in doc.lower()


def test_module_docstring_mentions_avoid_batch5():
    """docstring 提到"避免"或类似关键词。"""
    doc = smod.__doc__
    assert "避免" in doc or "import" in doc.lower()


def test_module_no_class_definition_batch5():
    src = inspect.getsource(smod)
    assert "\nclass " not in src


def test_module_no_loops_batch5():
    src = inspect.getsource(smod)
    assert "\n    for " not in src
    assert "\n    while " not in src


def test_module_no_try_except_batch5():
    src = inspect.getsource(smod)
    assert "try:" not in src
    assert "except" not in src


def test_module_no_conditional_batch5():
    src = inspect.getsource(smod)
    assert "\nif " not in src
    assert "\n    if " not in src


def test_module_only_one_function_batch5():
    """模块只有 document_passes_schema 一个 user-defined function。"""
    functions = [
        name for name, obj in vars(smod).items()
        if inspect.isfunction(obj) and not name.startswith("__")
    ]
    assert functions == ["document_passes_schema"]


def test_module_has_future_annotations_batch5():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_has_typing_any_import_batch5():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_has_lazy_import_inside_function_batch5():
    """app.schema 在函数内 import，不在模块顶部。"""
    src_lines = inspect.getsource(smod).split("\n")
    # 顶部（无缩进）不应有 app.schema import
    for line in src_lines:
        stripped = line.strip()
        if (stripped.startswith("from app.schema") or
                stripped.startswith("import app.schema")):
            # 必须在函数内（缩进 > 0）
            assert line.startswith(" "), f"unexpected top-level import: {line}"


def test_module_function_uses_bool_cast_batch5():
    """函数体用 bool() 包裹 is_valid 返回。"""
    src = inspect.getsource(document_passes_schema)
    assert "bool(" in src
    assert "is_valid" in src


def test_module_function_has_return_statement_batch5():
    src = inspect.getsource(document_passes_schema)
    assert "return" in src


def test_module_function_no_input_validation_batch5():
    """函数体内无 type check（is_valid 自己处理）。"""
    src = inspect.getsource(document_passes_schema)
    assert "isinstance" not in src
    assert "type(" not in src


def test_module_does_not_have_module_level_app_schema_batch5():
    """模块顶部不 import app.schema（用延迟 import）。"""
    src_lines = inspect.getsource(smod).split("\n")
    for line in src_lines:
        if (line.startswith("from app.") or line.startswith("import app.")):
            pytest.fail(f"unexpected module-level app import: {line}")


# ---------- 签名深度 第五批


def test_signature_one_param_batch5():
    sig = inspect.signature(document_passes_schema)
    assert len(sig.parameters) == 1


def test_signature_param_name_document_batch5():
    sig = inspect.signature(document_passes_schema)
    assert list(sig.parameters.keys()) == ["document"]


def test_signature_param_kind_positional_or_keyword_batch5():
    sig = inspect.signature(document_passes_schema)
    p = sig.parameters["document"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_param_no_default_batch5():
    sig = inspect.signature(document_passes_schema)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_signature_param_annotation_dict_str_any_batch5():
    """document 参数注解是 dict[str, Any]。"""
    sig = inspect.signature(document_passes_schema)
    ann = str(sig.parameters["document"].annotation)
    assert "dict" in ann


def test_signature_return_annotation_bool_batch5():
    sig = inspect.signature(document_passes_schema)
    assert "bool" in str(sig.return_annotation)


def test_signature_no_var_positional_batch5():
    sig = inspect.signature(document_passes_schema)
    has_var_pos = any(
        p.kind == inspect.Parameter.VAR_POSITIONAL
        for p in sig.parameters.values()
    )
    assert not has_var_pos


def test_signature_no_var_keyword_batch5():
    sig = inspect.signature(document_passes_schema)
    has_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    )
    assert not has_var_kw


# ---------- 综合行为 第五批


def test_e2e_does_not_raise_on_huge_dict_batch5():
    """超大 dict 也不抛异常。"""
    huge = {f"k{i}": i for i in range(2000)}
    result = document_passes_schema(huge)
    assert isinstance(result, bool)


def test_e2e_does_not_raise_on_unicode_content_batch5():
    doc = {"content": "中文测试日本語한국어"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_does_not_raise_on_special_chars_batch5():
    doc = {"content": "a\x00b\x01c"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_does_not_raise_on_emoji_batch5():
    doc = {"content": "😀🎉"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_does_not_mutate_input_batch5():
    import copy
    doc = {"foo": [1, 2, 3], "bar": {"x": "y"}}
    doc_before = copy.deepcopy(doc)
    document_passes_schema(doc)
    assert doc == doc_before


def test_e2e_returns_same_result_across_many_calls_batch5():
    """100 次相同调用结果一致。"""
    results = [document_passes_schema({}) for _ in range(100)]
    assert all(r == results[0] for r in results)


def test_e2e_with_dict_subclass_batch5():
    """dict 子类（如 defaultdict）也合法。"""
    class MyDict(dict):
        pass
    d = MyDict()
    d["x"] = 1
    result = document_passes_schema(d)
    assert isinstance(result, bool)


def test_e2e_pure_function_no_side_effects_batch5():
    """两次调用之间不应有副作用。"""
    doc1 = {"a": 1}
    doc2 = {"b": 2}
    r1 = document_passes_schema(doc1)
    r2 = document_passes_schema(doc2)
    assert isinstance(r1, bool)
    assert isinstance(r2, bool)


def test_e2e_callable_multiple_times_batch5():
    for _ in range(50):
        assert callable(document_passes_schema)


# ---------- module source forbidden tokens 第五批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch5(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- 端到端集成 第五批


def test_e2e_call_with_patch_is_valid_batch5():
    """patch app.schema.is_valid 验证 document_passes_schema 委托调用。"""
    with patch("app.schema.is_valid", return_value=True):
        assert document_passes_schema({}) is True
    with patch("app.schema.is_valid", return_value=False):
        assert document_passes_schema({}) is False


def test_e2e_call_with_is_valid_truthy_int_batch5():
    """is_valid 返回 truthy int → document_passes_schema 返回 True。"""
    with patch("app.schema.is_valid", return_value=1):
        assert document_passes_schema({}) is True


def test_e2e_call_with_is_valid_falsy_int_batch5():
    """is_valid 返回 0 → document_passes_schema 返回 False。"""
    with patch("app.schema.is_valid", return_value=0):
        assert document_passes_schema({}) is False


def test_e2e_call_with_is_valid_none_batch5():
    """is_valid 返回 None → document_passes_schema 返回 False。"""
    with patch("app.schema.is_valid", return_value=None):
        assert document_passes_schema({}) is False


def test_e2e_is_valid_called_with_input_doc_batch5():
    """document_passes_schema 把 doc 传给 is_valid。"""
    captured = {}
    def fake_is_valid(doc):
        captured["doc"] = doc
        return True
    with patch("app.schema.is_valid", side_effect=fake_is_valid):
        document_passes_schema({"sentinel": "x"})
    assert captured["doc"] == {"sentinel": "x"}
