r"""evaluation/schema_validation.py 边角测试 - 第二轮（Round 135）。

补强已有 edges（51 测试）未覆盖的深度路径：
- document_passes_schema 异常透传
- 延迟 import 验证
- bool() 转换语义
- 模块结构与签名深度
- 边界类型（非 dict、嵌套结构）
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from evaluation.schema_validation import (
    __all__ as schema_validation_all,
    document_passes_schema,
)


# =========================================================================
# document_passes_schema 异常透传
# =========================================================================


def test_document_passes_schema_propagates_is_valid_exception(monkeypatch):
    """如果 app.schema.is_valid 抛异常，document_passes_schema 不吞掉。"""
    import app.schema

    def _boom(_doc):
        raise ValueError("boom")

    monkeypatch.setattr(app.schema, "is_valid", _boom)
    with pytest.raises(ValueError, match="boom"):
        document_passes_schema({"any": "thing"})


def test_document_passes_schema_propagates_type_error(monkeypatch):
    import app.schema

    def _te(_doc):
        raise TypeError("type")

    monkeypatch.setattr(app.schema, "is_valid", _te)
    with pytest.raises(TypeError):
        document_passes_schema({})


def test_document_passes_schema_propagates_import_error(monkeypatch):
    """模拟 is_valid 不存在 → 抛 ImportError（不是 AttributeError）。"""
    import app.schema

    monkeypatch.delattr(app.schema, "is_valid")
    with pytest.raises(ImportError):
        document_passes_schema({})


# =========================================================================
# bool() 转换语义
# =========================================================================


def test_document_passes_schema_converts_truthy_int_to_true(monkeypatch):
    """is_valid 返回 1（truthy）→ document_passes_schema 返回 True。"""
    import app.schema

    monkeypatch.setattr(app.schema, "is_valid", lambda d: 1)
    assert document_passes_schema({}) is True


def test_document_passes_schema_converts_zero_int_to_false(monkeypatch):
    """is_valid 返回 0 → document_passes_schema 返回 False。"""
    import app.schema

    monkeypatch.setattr(app.schema, "is_valid", lambda d: 0)
    assert document_passes_schema({}) is False


def test_document_passes_schema_converts_empty_list_to_false(monkeypatch):
    """is_valid 返回 []（falsy）→ False。"""
    import app.schema

    monkeypatch.setattr(app.schema, "is_valid", lambda d: [])
    assert document_passes_schema({}) is False


def test_document_passes_schema_converts_non_empty_list_to_true(monkeypatch):
    """is_valid 返回 ['x']（truthy）→ True。"""
    import app.schema

    monkeypatch.setattr(app.schema, "is_valid", lambda d: ["x"])
    assert document_passes_schema({}) is True


def test_document_passes_schema_converts_none_to_false(monkeypatch):
    """is_valid 返回 None → False。"""
    import app.schema

    monkeypatch.setattr(app.schema, "is_valid", lambda d: None)
    assert document_passes_schema({}) is False


def test_document_passes_schema_returns_python_bool_not_int(monkeypatch):
    """返回值必须是 bool 类型，不是 int（即使 is_valid 返回 int）。"""
    import app.schema

    monkeypatch.setattr(app.schema, "is_valid", lambda d: 1)
    result = document_passes_schema({})
    assert type(result) is bool  # noqa: E721


# =========================================================================
# 延迟 import 验证
# =========================================================================


def test_document_passes_schema_lazy_imports_is_valid():
    """函数体内才 import is_valid，不在模块顶层。"""
    src = inspect.getsource(document_passes_schema)
    assert "from app.schema import is_valid" in src


def test_schema_validation_module_does_not_import_app_schema_at_top():
    """模块顶层不 import app.schema（避免循环依赖）。"""
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    # 顶层 import 区域：在函数 def 之前
    func_start = src.index("def document_passes_schema")
    top_section = src[:func_start]
    assert "import app.schema" not in top_section
    assert "from app.schema" not in top_section


def test_schema_validation_module_imports_typing_any():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_schema_validation_module_uses_future_annotations():
    import evaluation.schema_validation as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


# =========================================================================
# __all__ 深度
# =========================================================================


def test_all_is_list():
    assert isinstance(schema_validation_all, list)


def test_all_count_one():
    assert len(schema_validation_all) == 1


def test_all_exact():
    assert schema_validation_all == ["document_passes_schema"]


def test_all_items_are_str():
    for name in schema_validation_all:
        assert isinstance(name, str)


# =========================================================================
# 签名深度
# =========================================================================


def test_document_passes_schema_one_param():
    sig = inspect.signature(document_passes_schema)
    assert len(sig.parameters) == 1


def test_document_passes_schema_param_name_document():
    sig = inspect.signature(document_passes_schema)
    assert "document" in sig.parameters


def test_document_passes_schema_no_default():
    sig = inspect.signature(document_passes_schema)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_document_passes_schema_param_kind_positional_or_keyword():
    sig = inspect.signature(document_passes_schema)
    p = sig.parameters["document"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_document_passes_schema_return_annotation_bool():
    """返回注解是 bool（from __future__ 使之为字符串 'bool'）。"""
    sig = inspect.signature(document_passes_schema)
    assert sig.return_annotation in (bool, "bool")


def test_document_passes_schema_param_annotation_dict():
    sig = inspect.signature(document_passes_schema)
    p = sig.parameters["document"]
    # 由于 from __future__ import annotations，注解是字符串
    assert p.annotation is not inspect.Parameter.empty


# =========================================================================
# docstring 深度
# =========================================================================


def test_document_passes_schema_has_docstring():
    assert document_passes_schema.__doc__ is not None


def test_document_passes_schema_docstring_mentions_is_valid():
    assert "is_valid" in document_passes_schema.__doc__


def test_module_has_docstring():
    import evaluation.schema_validation as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_circular():
    """模块 docstring 应提及避免循环依赖的设计意图。"""
    import evaluation.schema_validation as mod
    assert "循环" in mod.__doc__ or "circular" in mod.__doc__.lower()


# =========================================================================
# 综合：document 类型边界
# =========================================================================


def test_document_passes_schema_with_extra_keys_still_works():
    """document 含额外键，仍能调用（schema 决定是否通过）。"""
    doc = {"extra_top_level": "value"}
    # 不该崩溃；is_valid 决定 True/False
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_document_passes_schema_idempotent():
    """对同一 document 多次调用结果一致。"""
    doc = {}
    r1 = document_passes_schema(doc)
    r2 = document_passes_schema(doc)
    assert r1 == r2


def test_document_passes_schema_does_not_mutate_input():
    """调用前后 document 不变。"""
    doc = {"a": 1}
    doc_before = {"a": 1}
    document_passes_schema(doc)
    assert doc == doc_before
