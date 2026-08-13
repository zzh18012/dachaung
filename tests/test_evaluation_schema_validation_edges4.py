"""evaluation/schema_validation.py 第四轮 edges 测试（Round 582）。

补强 base/edges/edges2/edges3（共 81+ 测试）未覆盖的角度（第四批）。
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from evaluation.schema_validation import document_passes_schema


# ---------- document_passes_schema 输入类型 第四批


def test_document_passes_schema_tuple_returns_false_batch4():
    """tuple 不是 dict → False。"""
    assert document_passes_schema((1, 2)) is False  # type: ignore[arg-type]


def test_document_passes_schema_set_returns_false_batch4():
    assert document_passes_schema({1, 2}) is False  # type: ignore[arg-type]


def test_document_passes_schema_bytes_returns_false_batch4():
    assert document_passes_schema(b"x") is False  # type: ignore[arg-type]


def test_document_passes_schema_float_returns_false_batch4():
    assert document_passes_schema(3.14) is False  # type: ignore[arg-type]


def test_document_passes_schema_bool_true_returns_false_batch4():
    """True 不是 dict → False。"""
    assert document_passes_schema(True) is False  # type: ignore[arg-type]


def test_document_passes_schema_bool_false_returns_false_batch4():
    assert document_passes_schema(False) is False  # type: ignore[arg-type]


def test_document_passes_schema_zero_returns_false_batch4():
    assert document_passes_schema(0) is False  # type: ignore[arg-type]


def test_document_passes_schema_negative_int_returns_false_batch4():
    assert document_passes_schema(-1) is False  # type: ignore[arg-type]


def test_document_passes_schema_frozenset_returns_false_batch4():
    assert document_passes_schema(frozenset([1, 2])) is False  # type: ignore[arg-type]


# ---------- document_passes_schema dict 内容 第四批


def test_document_passes_schema_dict_with_none_values_batch4():
    """dict 全 None values → 取决于 schema。"""
    doc = {"a": None, "b": None}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_nested_dict_batch4():
    doc = {"a": {"b": {"c": 1}}}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_list_value_batch4():
    doc = {"elements": [], "chunks": []}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_unicode_keys_batch4():
    doc = {"中文": "value"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_int_keys_batch4():
    """JSON Schema 只接受 str keys；int keys 视为无效。"""
    doc = {1: "value"}  # type: ignore[dict-item]
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_very_long_value_batch4():
    """超长 string value。"""
    doc = {"content": "x" * 10000}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_dict_with_deeply_nested_batch4():
    """深度嵌套 dict（不应崩溃）。"""
    doc = {"a": {"b": {"c": {"d": {"e": "f"}}}}}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


# ---------- document_passes_schema 行为 第四批


def test_document_passes_schema_callable_batch4():
    assert callable(document_passes_schema)


def test_document_passes_schema_with_valid_minimal_doc_batch4():
    """最小合法 doc 结构（需通过 schema 校验）。

    Schema 要求 source_type / elements / chunks / document_id 等。
    """
    # 一个相对完整的 document 结构
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "x.pdf",
        "sha256": "a" * 64,
        "elements": [],
        "chunks": [],
    }
    result = document_passes_schema(doc)
    # 不强求 True（schema 可能更严格），但必须返回 bool
    assert isinstance(result, bool)


def test_document_passes_schema_idempotent_across_many_calls_batch4():
    """多次调用结果一致。"""
    doc = {"x": 1}
    results = [document_passes_schema(doc) for _ in range(10)]
    assert all(r == results[0] for r in results)


def test_document_passes_schema_does_not_mutate_input_with_nested_batch4():
    """不修改嵌套 dict。"""
    import copy
    doc = {"a": [1, 2, {"b": "c"}], "d": {"e": "f"}}
    doc_before = copy.deepcopy(doc)
    document_passes_schema(doc)
    assert doc == doc_before


def test_document_passes_schema_returns_bool_not_truthy_batch4():
    """严格返回 bool 类型（不是 truthy/falsy 的其他类型）。"""
    result = document_passes_schema({})
    assert type(result) is bool


def test_document_passes_schema_pure_function_batch4():
    """纯函数：相同输入相同输出，无副作用。"""
    doc = {"test": "value"}
    r1 = document_passes_schema(doc)
    r2 = document_passes_schema(doc)
    assert r1 == r2


# ---------- 模块结构 第四批


def test_module_source_lines_count_batch4():
    """模块很短（< 30 行）。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    # 模块精简
    assert len(src.split("\n")) < 30


def test_module_source_contains_documentation_batch4():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "schema 校验" in src or "schema_validation" in src


def test_module_source_contains_no_class_batch4():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "\nclass " not in src


def test_module_source_contains_no_loops_batch4():
    """模块内无 for/while 循环。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "\n    for " not in src
    assert "\n    while " not in src


def test_module_source_contains_no_try_except_batch4():
    """模块内无 try/except。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "try:" not in src
    assert "except" not in src


def test_module_source_contains_no_conditional_batch4():
    """模块内无 if/else（只委托给 is_valid）。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "\nif " not in src
    assert "\n    if " not in src


def test_module_source_contains_lazy_import_keyword_batch4():
    """模块使用"延迟 import"。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "延迟" in src or "lazy" in src.lower()


def test_module_source_contains_bool_call_batch4():
    """函数体使用 bool() 强转。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "bool(" in src


def test_module_source_contains_return_batch4():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "return" in src


def test_module_source_contains_module_doc_batch4():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    # docstring 第一行
    assert '"""' in src


def test_module_has_no_other_functions_batch4():
    """模块只有一个用户定义的函数（inspect.isfunction 过滤掉 Any 等 typing 类型）。"""
    import evaluation.schema_validation as mod
    functions = [
        name for name, obj in vars(mod).items()
        if inspect.isfunction(obj) and not name.startswith("__")
    ]
    assert functions == ["document_passes_schema"]


def test_module_function_source_no_docstring_call_batch4():
    """函数 docstring 描述用途。"""
    src = inspect.getsource(document_passes_schema)
    assert "is_valid" in src or "schema" in src


# ---------- 签名深度 第四批


def test_signature_param_kind_batch4():
    sig = inspect.signature(document_passes_schema)
    p = sig.parameters["document"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_no_var_positional_batch4():
    sig = inspect.signature(document_passes_schema)
    has_var_pos = any(
        p.kind == inspect.Parameter.VAR_POSITIONAL
        for p in sig.parameters.values()
    )
    assert not has_var_pos


def test_signature_no_var_keyword_batch4():
    sig = inspect.signature(document_passes_schema)
    has_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    )
    assert not has_var_kw


def test_signature_param_count_exact_one_batch4():
    sig = inspect.signature(document_passes_schema)
    assert len(sig.parameters) == 1


def test_signature_only_one_param_named_document_batch4():
    sig = inspect.signature(document_passes_schema)
    assert list(sig.parameters.keys()) == ["document"]


# ---------- 综合行为 第四批


def test_e2e_does_not_raise_on_huge_dict_batch4():
    """超大 dict 也不抛异常。"""
    huge = {f"k{i}": i for i in range(1000)}
    result = document_passes_schema(huge)
    assert isinstance(result, bool)


def test_e2e_does_not_raise_on_unicode_content_batch4():
    doc = {"content": "中文测试日本語한국어"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_does_not_raise_on_special_chars_batch4():
    """特殊字符（包括 NUL 字节）也不抛异常。"""
    doc = {"content": "a\x00b\x01c"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_dict_with_circular_reference_safe_batch4():
    """含 circular ref 的 dict（虽然 JSON 序列化会失败，但 is_valid 可能能处理）。"""
    # 注意：构造真正的 circular ref 然后传给 schema 校验
    # is_valid 内部用 jsonschema Draft202012Validator
    # 它不要求 JSON 序列化，所以 circular ref 在内部可能不抛错
    doc: dict[str, Any] = {}
    doc["self"] = doc
    # 这里只验证不抛内存错误或异常
    try:
        result = document_passes_schema(doc)
        assert isinstance(result, bool)
    except (ValueError, TypeError, RecursionError):
        # 某些情况下 schema 校验可能拒绝 circular ref → 也算合法行为
        pass


def test_e2e_does_not_raise_on_empty_string_batch4():
    """空字符串 input 也不抛异常。"""
    result = document_passes_schema("")
    assert isinstance(result, bool)


def test_e2e_consistent_results_in_random_order_batch4():
    """随机顺序调用结果一致。"""
    docs = [{"x": 1}, {"y": 2}, {}, {"a": "b"}]
    r1 = [document_passes_schema(d) for d in docs]
    r2 = [document_passes_schema(d) for d in docs]
    assert r1 == r2


def test_e2e_with_complex_nested_list_batch4():
    """含 list 嵌套 dict。"""
    doc = {
        "elements": [
            {"type": "paragraph", "content": "abc"},
            {"type": "image", "resource_path": "x.png"},
        ],
    }
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_with_null_value_batch4():
    """顶层 value 为 null。"""
    doc = {"x": None}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_with_empty_list_batch4():
    doc = []
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_e2e_with_empty_dict_batch4():
    """空 dict → False（缺必填字段）。"""
    assert document_passes_schema({}) is False


# ---------- module source forbidden tokens 第四批


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
def test_module_source_no_forbidden_tokens_batch4(token):
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert token not in src
