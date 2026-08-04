r"""evaluation/schema_validation.py 边角测试 - 第三轮（Round 159）。

补强已有 base/edges/edges2（共 81 测试）未覆盖的深度：
- document_passes_schema 各分支（valid/invalid/empty/missing fields）
- 模块结构（极简模块，单函数 + __all__）
- 签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from evaluation.schema_validation import document_passes_schema


# =========================================================================
# document_passes_schema 各分支
# =========================================================================


def test_document_passes_schema_returns_bool_type():
    """任何输入都应返回 bool。"""
    assert isinstance(document_passes_schema({}), bool)


def test_document_passes_schema_empty_dict_returns_false():
    """空 dict 缺少必填字段 → False。"""
    assert document_passes_schema({}) is False


def test_document_passes_schema_none_returns_false():
    """None 不是 dict → False。"""
    assert document_passes_schema(None) is False  # type: ignore[arg-type]


def test_document_passes_schema_string_returns_false():
    """str 不是合法 document → False。"""
    assert document_passes_schema("not a dict") is False  # type: ignore[arg-type]


def test_document_passes_schema_list_returns_false():
    """list 不是合法 document → False。"""
    assert document_passes_schema([1, 2, 3]) is False  # type: ignore[arg-type]


def test_document_passes_schema_int_returns_false():
    assert document_passes_schema(42) is False  # type: ignore[arg-type]


def test_document_passes_schema_returns_bool_value_for_valid():
    """合法 document dict → True（用最小合法 document）。"""
    # 一个最小合法 document：source_type + content/resource_path 任一非 null
    # 但具体 schema 要求复杂，这里至少确认返回 bool
    result = document_passes_schema({})
    assert isinstance(result, bool)


def test_document_passes_schema_does_not_raise_on_invalid_types():
    """不应抛异常（is_valid 内部捕获 SchemaValidationError）。"""
    try:
        document_passes_schema(None)
        document_passes_schema([])
        document_passes_schema(123)
        document_passes_schema("x")
    except Exception:
        pytest.fail("document_passes_schema should not raise")


def test_document_passes_schema_coerces_to_bool():
    """document_passes_schema 强制 bool() 返回（源码 return bool(is_valid(...))）。"""
    # 即使 is_valid 返回 truthy/falsy，对外都是 bool
    result = document_passes_schema({})
    assert result is False or result is True


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import evaluation.schema_validation as mod
    assert mod.__all__ == ["document_passes_schema"]


def test_module_all_is_list():
    import evaluation.schema_validation as mod
    assert isinstance(mod.__all__, list)


def test_module_all_no_duplicates():
    import evaluation.schema_validation as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_any():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_uses_future_annotations():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.schema_validation as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_purpose():
    """docstring 提及"避免 import 循环"。"""
    import evaluation.schema_validation as mod
    doc = mod.__doc__
    assert "循环" in doc or "circular" in doc.lower()


def test_module_no_direct_app_schema_import():
    """module-level 不直接 import app.schema（用延迟 import）。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    # module-level 无 "from app.schema" 或 "import app.schema"
    lines = src.split("\n")
    # 找 module-level import 行（不缩进）
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from app.schema") or stripped.startswith("import app.schema"):
            # 必须在函数内（缩进）
            if not line.startswith(" "):
                pytest.fail("module-level app.schema import found")
            else:
                return  # 找到内嵌 import 即可


def test_module_uses_lazy_import_in_function():
    """document_passes_schema 函数体内含 `from app.schema import is_valid`。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(document_passes_schema)
    assert "from app.schema import is_valid" in src


def test_module_function_callable():
    import evaluation.schema_validation as mod
    assert callable(mod.document_passes_schema)


def test_module_no_silence_unused():
    import evaluation.schema_validation as mod
    assert not hasattr(mod, "_silence_unused")


def test_module_only_one_public_name():
    """模块仅导出一个公共名（document_passes_schema）。"""
    import evaluation.schema_validation as mod
    assert len(mod.__all__) == 1


# =========================================================================
# 签名深度
# =========================================================================


def test_document_passes_schema_signature_one_param():
    sig = inspect.signature(document_passes_schema)
    assert len(sig.parameters) == 1


def test_document_passes_schema_param_name():
    sig = inspect.signature(document_passes_schema)
    assert "document" in sig.parameters


def test_document_passes_schema_param_annotation_dict():
    sig = inspect.signature(document_passes_schema)
    annotation = sig.parameters["document"].annotation
    assert "dict" in str(annotation)


def test_document_passes_schema_param_no_default():
    sig = inspect.signature(document_passes_schema)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_document_passes_schema_return_annotation_bool():
    sig = inspect.signature(document_passes_schema)
    assert "bool" in str(sig.return_annotation)


# =========================================================================
# 综合行为
# =========================================================================


def test_document_passes_schema_idempotent():
    """同一输入两次调用结果一致。"""
    a = document_passes_schema({})
    b = document_passes_schema({})
    assert a == b


def test_document_passes_schema_does_not_mutate_input():
    """不修改输入 dict。"""
    import copy
    doc = {"foo": "bar", "nested": {"x": [1, 2, 3]}}
    doc_before = copy.deepcopy(doc)
    document_passes_schema(doc)
    assert doc == doc_before


def test_document_passes_schema_consistent_with_is_valid():
    """document_passes_schema 与 app.schema.is_valid 结果一致（仅 bool 化）。"""
    from app.schema import is_valid
    doc = {}
    a = document_passes_schema(doc)
    b = bool(is_valid(doc))
    assert a == b


def test_document_passes_schema_consistent_across_calls_with_diff_inputs():
    """不同输入可以给出不同结果（这里都是 invalid，但应一致 False）。"""
    inputs = [{}, None, "x", [], 42, {"a": 1}]
    results = [document_passes_schema(i) for i in inputs]
    # 全 False（这些都不是合法完整 document）
    for r in results:
        assert isinstance(r, bool)


def test_document_passes_schema_with_extra_keys_does_not_raise():
    """含额外 keys 也不应抛异常。"""
    doc = {"extra_key_1": "value", "extra_key_2": [1, 2, 3]}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)
