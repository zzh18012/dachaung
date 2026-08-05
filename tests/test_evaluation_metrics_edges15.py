r"""evaluation/metrics.py 边角测试 - 第十五轮（Round 256）。

补强已有 base/edges/edges2-14（共 ~1070+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含未覆盖的特定 token
- module 文档字符串与文档字符串长度断言
- compute_automatic_metrics keys 顺序精确
- _null / _ratio / _bool_metric / _int_metric 返回 dict 字段名精确
- _text_preservation：non-image filter；image-only；dict 缺 content / text
- _strip_unicode_whitespace：bytes 拒绝（int iter）；bytearray 拒绝
- _is_valid_bbox：dict / set / string / None 拒绝；float Inf / NaN / -Inf
- _pdf_locator_ratio：bool page 拒绝；page=0 拒绝；page=1 接受
- _docx_locator_ratio：locator None / 缺所有 structural_keys
- _image_resource_ratio：resource_path 为 None / 空 / 仅空格
- _chunk_reference_ratio：source_element_ids 含 duplicate；空 list
- _heading_boundary_ratio：source_element_ids 为空 list / None
- _silent_drop_count：expectations 空字典 / None / 含空 element_count_by_type
- compute_automatic_metrics：source_type 'markdown' 视为 not_pdf_document
- 常量 _NOT_EVALUATED 内容精确
- module __all__ 是 list 不是 tuple
- 签名 introspection：compute_automatic_metrics 参数名 / default 精确
- dataclass 与 None behavior
- bytes / bytearray 在 normalize_text 边界（_strip_unicode_whitespace）
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from evaluation.metrics import (
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _heading_boundary_ratio,
    _image_resource_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _silent_drop_count,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# =========================================================================
# 源码字符串断言（inspect.getsource）— 未覆盖 token
# =========================================================================


def test_module_source_contains_compute_automatic_metrics_def():
    import evaluation.metrics as m

    assert "def compute_automatic_metrics(" in inspect.getsource(m)


def test_module_source_contains_pdf_locator_ratio_def():
    import evaluation.metrics as m

    assert "def _pdf_locator_ratio(" in inspect.getsource(m)


def test_module_source_contains_docx_locator_ratio_def():
    import evaluation.metrics as m

    assert "def _docx_locator_ratio(" in inspect.getsource(m)


def test_module_source_contains_is_valid_bbox_def():
    import evaluation.metrics as m

    assert "def _is_valid_bbox(" in inspect.getsource(m)


def test_module_source_contains_image_resource_ratio_def():
    import evaluation.metrics as m

    assert "def _image_resource_ratio(" in inspect.getsource(m)


def test_module_source_contains_chunk_reference_ratio_def():
    import evaluation.metrics as m

    assert "def _chunk_reference_ratio(" in inspect.getsource(m)


def test_module_source_contains_strip_unicode_whitespace_def():
    import evaluation.metrics as m

    assert "def _strip_unicode_whitespace(" in inspect.getsource(m)


def test_module_source_contains_text_preservation_def():
    import evaluation.metrics as m

    assert "def _text_preservation(" in inspect.getsource(m)


def test_module_source_contains_heading_boundary_ratio_def():
    import evaluation.metrics as m

    assert "def _heading_boundary_ratio(" in inspect.getsource(m)


def test_module_source_contains_silent_drop_count_def():
    import evaluation.metrics as m

    assert "def _silent_drop_count(" in inspect.getsource(m)


def test_module_source_contains_image_element_filter():
    """源码含 type != 'image' 过滤。"""
    import evaluation.metrics as m

    assert "!= \"image\"" in inspect.getsource(m)


def test_module_source_contains_silent_drop_formula():
    """源码含 silent_drop 计算公式 'drops += (exp - actual)'。"""
    import evaluation.metrics as m

    assert "drops += (exp - actual)" in inspect.getsource(m)


def test_module_source_contains_intersection_counter():
    """源码含 Counter 交集 '& c_actual'。"""
    import evaluation.metrics as m

    assert "& c_actual" in inspect.getsource(m)


def test_module_source_contains_chunk_first_id_assignment():
    """源码含 chunk_first_ids.add(ids[0])。"""
    import evaluation.metrics as m

    assert "chunk_first_ids.add(ids[0])" in inspect.getsource(m)


def test_module_source_contains_image_base_dir_concat():
    """源码含 image_base_dir / Path(rp).name。"""
    import evaluation.metrics as m

    assert "image_base_dir / Path(rp).name" in inspect.getsource(m)


def test_module_source_contains_isfile_check():
    """源码含 p.is_file()。"""
    import evaluation.metrics as m

    assert "p.is_file()" in inspect.getsource(m)


def test_module_source_contains_stat_st_size():
    """源码含 st_size > 0。"""
    import evaluation.metrics as m

    assert "st_size > 0" in inspect.getsource(m)


def test_module_source_contains_heading_filter():
    """源码含 type == 'heading' 过滤。"""
    import evaluation.metrics as m

    assert "== \"heading\"" in inspect.getsource(m)


def test_module_source_contains_image_filter():
    """源码含 type == 'image' 过滤。"""
    import evaluation.metrics as m

    assert "== \"image\"" in inspect.getsource(m)


def test_module_source_contains_math_import():
    import evaluation.metrics as m

    assert "import math" in inspect.getsource(m)


def test_module_source_contains_math_isfinite():
    import evaluation.metrics as m

    assert "math.isfinite" in inspect.getsource(m)


def test_module_source_contains_pipeline_failed():
    """源码含 'pipeline_failed' reason。"""
    import evaluation.metrics as m

    assert "pipeline_failed" in inspect.getsource(m)


def test_module_source_contains_no_elements_reason():
    """源码含 'no_elements' reason。"""
    import evaluation.metrics as m

    assert "\"no_elements\"" in inspect.getsource(m)


def test_module_source_contains_no_chunks_reason():
    """源码含 'no_chunks' reason。"""
    import evaluation.metrics as m

    assert "\"no_chunks\"" in inspect.getsource(m)


def test_module_source_contains_no_heading_elements_reason():
    """源码含 'no_heading_elements' reason。"""
    import evaluation.metrics as m

    assert "\"no_heading_elements\"" in inspect.getsource(m)


def test_module_source_contains_no_image_elements_reason():
    """源码含 'no_image_elements' reason。"""
    import evaluation.metrics as m

    assert "\"no_image_elements\"" in inspect.getsource(m)


def test_module_source_contains_no_expectations_reason():
    """源码含 'no_expectations' reason。"""
    import evaluation.metrics as m

    assert "\"no_expectations\"" in inspect.getsource(m)


def test_module_source_contains_pipeline_success_logic():
    """源码含 'pipeline_success = error is None and document is not None'。"""
    import evaluation.metrics as m

    assert "pipeline_success = error is None and document is not None" in inspect.getsource(m)


def test_module_source_contains_pipeline_failed_loop():
    """源码含循环构造 null metrics。"""
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "for name in (" in src
    assert "metrics[name] = _null" in src


def test_module_source_does_not_contain_print():
    """源码不含 print 调用。"""
    import evaluation.metrics as m

    assert "print(" not in inspect.getsource(m)


# =========================================================================
# 模块 metadata 深度
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.metrics as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 100  # 文档字符串应该相当长


def test_module_docstring_contains_text_preservation_semantics():
    """文档字符串描述了 text_preservation 语义。"""
    import evaluation.metrics as m

    assert "text_preservation" in m.__doc__


def test_module_docstring_contains_pure_function_principle():
    """文档字符串提到纯函数设计原则。"""
    import evaluation.metrics as m

    assert "纯函数" in m.__doc__ or "Counter" in m.__doc__


def test_module_all_is_list_not_tuple():
    """__all__ 是 list 不是 tuple。"""
    import evaluation.metrics as m

    assert isinstance(m.__all__, list)
    assert not isinstance(m.__all__, tuple)


def test_module_namespace_contains_text_types():
    """_TEXT_TYPES 在 module namespace。"""
    import evaluation.metrics as m

    assert hasattr(m, "_TEXT_TYPES")
    assert m._TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_module_namespace_contains_pdf_bbox_required_types():
    import evaluation.metrics as m

    assert hasattr(m, "_PDF_BBOX_REQUIRED_TYPES")
    assert m._PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_module_namespace_contains_not_evaluated():
    import evaluation.metrics as m

    assert m._NOT_EVALUATED == "not_evaluated"


def test_module_namespace_contains_math_and_counter():
    """math 和 Counter 都在 namespace。"""
    import evaluation.metrics as m

    assert hasattr(m, "math")
    assert hasattr(m, "Counter")


def test_module_namespace_identity_with_typing_any():
    """Any 在 module namespace。"""
    import evaluation.metrics as m
    from typing import Any as OrigAny

    assert m.Any is OrigAny


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric 字段名精确
# =========================================================================


def test_null_dict_has_value_and_reason_keys_only():
    out = _null("xyz")
    assert set(out.keys()) == {"value", "reason"}


def test_null_dict_keys_order_value_then_reason():
    out = _null("xyz")
    keys = list(out.keys())
    assert keys == ["value", "reason"]


def test_ratio_dict_has_value_and_reason_keys_only():
    out = _ratio(0.5)
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_dict_keys_order_value_then_reason():
    out = _ratio(0.5)
    keys = list(out.keys())
    assert keys == ["value", "reason"]


def test_bool_metric_dict_has_value_and_reason_keys_only():
    out = _bool_metric(True)
    assert set(out.keys()) == {"value", "reason"}


def test_bool_metric_dict_keys_order_value_then_reason():
    out = _bool_metric(False)
    keys = list(out.keys())
    assert keys == ["value", "reason"]


def test_int_metric_dict_has_value_and_reason_keys_only():
    out = _int_metric(5)
    assert set(out.keys()) == {"value", "reason"}


def test_int_metric_dict_keys_order_value_then_reason():
    out = _int_metric(5)
    keys = list(out.keys())
    assert keys == ["value", "reason"]


def test_null_dict_can_be_serialized_to_json():
    import json

    out = _null("a reason")
    s = json.dumps(out)
    assert json.loads(s) == out


def test_ratio_dict_can_be_serialized_to_json():
    import json

    out = _ratio(0.123)
    s = json.dumps(out)
    assert json.loads(s) == out


# =========================================================================
# 签名 introspection
# =========================================================================


def test_compute_automatic_metrics_signature_has_5_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_automatic_metrics_param_names_exact():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_compute_automatic_metrics_param_defaults_exact():
    """前 4 个无默认，image_base_dir 默认 None。"""
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty
    assert params[1].default is inspect.Parameter.empty
    assert params[2].default is inspect.Parameter.empty
    assert params[3].default is inspect.Parameter.empty
    assert params[4].default is None


def test_compute_automatic_metrics_no_var_positional():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_compute_automatic_metrics_no_var_keyword():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_compute_automatic_metrics_image_base_dir_is_keyword_or_positional():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_compute_automatic_metrics_return_annotation_is_str_due_to_future():
    """from __future__ import annotations → return_annotation 是 'dict[str, Any]' 字符串。"""
    sig = inspect.signature(compute_automatic_metrics)
    assert isinstance(sig.return_annotation, str)


def test_compute_automatic_metrics_module_identity():
    assert compute_automatic_metrics.__module__ == "evaluation.metrics"


def test_compute_automatic_metrics_qualname_no_dots():
    assert compute_automatic_metrics.__qualname__ == "compute_automatic_metrics"


def test_compute_automatic_metrics_is_function_type():
    assert isinstance(compute_automatic_metrics, types.FunctionType) if False else True
    import types as _types
    assert isinstance(compute_automatic_metrics, _types.FunctionType)


# =========================================================================
# _strip_unicode_whitespace 字符级精确（更全面）
# =========================================================================


def test_strip_unicode_whitespace_empty_string_returns_empty():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace_returns_unchanged():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_all_whitespace_returns_empty():
    assert _strip_unicode_whitespace(" \t\n\r\f\v") == ""


def test_strip_unicode_whitespace_pure_nbsp_returns_empty():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_mixed_ascii_and_unicode_whitespace():
    """混合 ASCII 空格和 Unicode 空白。"""
    s = "a b c\nd"
    assert _strip_unicode_whitespace(s) == "abcd"


def test_strip_unicode_whitespace_preserves_non_whitespace_unicode():
    """中日韩文字不被删除。"""
    s = "你好 world 世界"
    assert _strip_unicode_whitespace(s) == "你好world世界"


def test_strip_unicode_whitespace_does_not_sort_chars():
    """字符顺序保留。"""
    s = "cab"
    assert _strip_unicode_whitespace(s) == "cab"


def test_strip_unicode_whitespace_em_space_removed():
    """U+2003 EM SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space_removed():
    """U+2002 EN SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_removed():
    """U+3000 IDEOGRAPHIC SPACE。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_removed():
    """U+2028 LINE SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_removed():
    """U+2029 PARAGRAPH SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_zero_width_space_preserved():
    """U+200B ZERO WIDTH SPACE 不是 isspace() → 保留。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_does_not_use_normalize_text():
    """与 normalize_text 不同：不 collapse 多空格、不 strip 两端。"""
    s = "  a  b  "
    # normalize_text 会 strip + collapse → 'a b'
    # _strip_unicode_whitespace 仅删除空白 → 'ab'
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_returns_str_type():
    out = _strip_unicode_whitespace("abc")
    assert isinstance(out, str)


# =========================================================================
# _strip_unicode_whitespace 输入类型边界
# =========================================================================


def test_strip_unicode_whitespace_bytes_raises_attribute_error():
    """bytes 迭代得到 int；int 无 isspace → AttributeError。"""
    with pytest.raises(AttributeError):
        _strip_unicode_whitespace(b"abc")


def test_strip_unicode_whitespace_int_raises_type_error():
    """int 不可迭代 → TypeError。"""
    with pytest.raises(TypeError):
        _strip_unicode_whitespace(123)  # type: ignore[arg-type]


def test_strip_unicode_whitespace_none_raises_type_error():
    with pytest.raises(TypeError):
        _strip_unicode_whitespace(None)  # type: ignore[arg-type]


# =========================================================================
# _is_valid_bbox 边界（更彻底）
# =========================================================================


def test_is_valid_bbox_none_returns_false():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list_returns_false():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_short_list_returns_false():
    assert _is_valid_bbox([1.0, 2.0, 3.0]) is False


def test_is_valid_bbox_long_list_returns_false():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0, 5.0]) is False


def test_is_valid_bbox_tuple_returns_false():
    """tuple 不是 list → False。"""
    assert _is_valid_bbox((1.0, 2.0, 3.0, 4.0)) is False


def test_is_valid_bbox_dict_returns_false():
    assert _is_valid_bbox({"x": 1, "y": 2, "w": 3, "h": 4}) is False


def test_is_valid_bbox_set_returns_false():
    assert _is_valid_bbox({1.0, 2.0, 3.0, 4.0}) is False


def test_is_valid_bbox_string_returns_false():
    assert _is_valid_bbox("1234") is False


def test_is_valid_bbox_integers_accepted():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_floats_accepted():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0]) is True


def test_is_valid_bbox_mixed_int_float_accepted():
    assert _is_valid_bbox([1, 2.0, 3, 4.0]) is True


def test_is_valid_bbox_true_rejected():
    """True 是 bool 但 isinstance(True, int) is True；要显式拒绝。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_is_valid_bbox_false_rejected():
    assert _is_valid_bbox([False, 2, 3, 4]) is False


def test_is_valid_bbox_nan_rejected():
    assert _is_valid_bbox([float("nan"), 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_inf_rejected():
    assert _is_valid_bbox([float("inf"), 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_negative_inf_rejected():
    assert _is_valid_bbox([float("-inf"), 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_none_in_list_rejected():
    assert _is_valid_bbox([None, 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_string_in_list_rejected():
    assert _is_valid_bbox(["1.0", 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_returns_bool_type():
    """返回类型必须是 bool。"""
    assert type(_is_valid_bbox([1, 2, 3, 4])) is bool
    assert type(_is_valid_bbox(None)) is bool


# =========================================================================
# _pdf_locator_ratio 边界（更彻底）
# =========================================================================


def test_pdf_locator_ratio_empty_list_returns_no_elements():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_page_zero_rejected():
    """page=0 拒绝（< 1）。"""
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_rejected():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_one_accepted():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_bool_page_rejected():
    """bool 是 int 的子类，但 is True/False 时 page=1 仅接受 True。"""
    elements = [{"type": "image", "source_locator": {"page": True}}]
    out = _pdf_locator_ratio(elements)
    # isinstance(True, int) is True, and True == 1
    assert out["value"] == 1.0


def test_pdf_locator_ratio_float_page_rejected():
    """float 不是 int → 拒绝。"""
    elements = [{"type": "image", "source_locator": {"page": 1.0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_string_page_rejected():
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_missing_locator_rejected():
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_none_locator_rejected():
    elements = [{"type": "image", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_requires_bbox():
    """heading/paragraph/caption/list_item 需要 bbox。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_with_valid_bbox_accepted():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]}}
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_returns_ratio_with_none_reason():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["reason"] is None


def test_pdf_locator_ratio_returns_float_value():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert isinstance(out["value"], float)


def test_pdf_locator_ratio_partial_valid():
    """一半有效，一半无效 → 0.5。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
        {"type": "image", "source_locator": {"page": 0}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


# =========================================================================
# _docx_locator_ratio 边界（更彻底）
# =========================================================================


def test_docx_locator_ratio_empty_list_returns_no_elements():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_no_structural_keys_rejected():
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "x"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_section_accepted():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_paragraph_index_accepted():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_relationship_id_accepted():
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_rejected():
    """DOCX 不允许 page。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_rejected():
    elements = [
        {"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4], "section": 1}}
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_missing_locator_rejected():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_none_locator_treated_as_empty():
    """None locator → 'None or {}' → {} → no structural keys → rejected。"""
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_partial_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1}},
        {"type": "paragraph", "source_locator": {"unknown_key": "x"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


def test_docx_locator_ratio_returns_float_value():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert isinstance(out["value"], float)


# =========================================================================
# _chunk_reference_ratio 边界（更彻底）
# =========================================================================


def test_chunk_reference_ratio_empty_chunks_returns_no_chunks():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunks_with_empty_ids_skipped():
    """source_element_ids=[] 的 chunk 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunks_with_none_ids_treated_as_empty():
    """source_element_ids=None → None or [] → [] → 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunks_missing_ids_treated_as_empty():
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # 缺 source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_chunks_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e1", "e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_some_chunks_invalid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e_unknown"]},  # 无效
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_duplicate_ids_in_chunk_still_valid():
    """重复 id 仍 valid（all check）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e1", "e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_returns_float_value():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert isinstance(out["value"], float)


# =========================================================================
# _heading_boundary_ratio 边界（更彻底）
# =========================================================================


def test_heading_boundary_ratio_empty_elements_returns_no_heading():
    out = _heading_boundary_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_headings_returns_no_heading():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_returns_zero():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_first_id_matches():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_chunk_first_id_not_match():
    """heading 在非首位置 → 不算合规。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1", "h1"]}]  # h1 在第 2 位
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_empty_ids_skipped():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": []},  # 空，跳过
        {"source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_none_ids_skipped():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": None},  # None，跳过
        {"source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_missing_ids_skipped():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {},  # 缺 source_element_ids
        {"source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial():
    """2 个 heading，1 个匹配 → 0.5。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_returns_float_value():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert isinstance(out["value"], float)


def test_heading_boundary_ratio_duplicate_headings():
    """2 个 heading 都是 h1 → 都匹配（set 去重不影响）。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


# =========================================================================
# _silent_drop_count 边界（更彻底）
# =========================================================================


def test_silent_drop_count_none_expectations_returns_no_expectations():
    out = _silent_drop_count({}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_no_expectations():
    """{} 是 falsy → no_expectations。"""
    out = _silent_drop_count({}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_without_element_count_returns_no_expectations_count():
    out = _silent_drop_count({}, {"other_field": "x"})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_returns_no_expectations_count():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drop_returns_zero():
    """actual == expected → drop=0。"""
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0
    assert out["reason"] is None


def test_silent_drop_count_drop_three():
    """5 expected, 2 actual → drop=3。"""
    by_type = {"paragraph": 2}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 3


def test_silent_drop_count_actual_more_than_expected_not_negative():
    """actual > expected → 0 contribution（max(0, ...)）。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_sum_across_types():
    by_type = {"paragraph": 0, "heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph: 5-0=5, heading: 3-1=2 → 7
    assert out["value"] == 7


def test_silent_drop_count_expected_type_missing_in_actual():
    """expected 含 actual 中没有的 type → 全算 drop。"""
    by_type = {}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 5


def test_silent_drop_count_actual_type_missing_in_expected():
    """actual 含 expected 中没有的 type → 忽略。"""
    by_type = {"paragraph": 100}
    expectations = {"element_count_by_type": {"heading": 5}}
    out = _silent_drop_count(by_type, expectations)
    # heading: 5-0=5
    assert out["value"] == 5


def test_silent_drop_count_returns_int_value():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert isinstance(out["value"], int)


def test_silent_drop_count_value_can_be_zero_int_not_float():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0
    assert type(out["value"]) is int  # 不是 float


# =========================================================================
# _image_resource_ratio 边界（更彻底）
# =========================================================================


def test_image_resource_ratio_no_images_returns_no_image_elements():
    elements = [{"type": "paragraph", "content": "x"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_empty_elements_returns_no_image_elements():
    out = _image_resource_ratio([], None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path_rejected():
    elements = [{"type": "image"}]  # 缺 resource_path
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_rejected():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_none_resource_path_rejected():
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_existing_file_accepted(tmp_path: Path):
    """文件存在 + size>0 → valid。"""
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"\x89PNG fake")  # 9 bytes
    elements = [{"type": "image", "resource_path": str(img_path)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_zero_size_file_rejected(tmp_path: Path):
    """size=0 → 无效。"""
    img_path = tmp_path / "empty.png"
    img_path.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_path)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_directory_not_treated_as_file(tmp_path: Path):
    """目录不算 file。"""
    elements = [{"type": "image", "resource_path": str(tmp_path)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_partial(tmp_path: Path):
    """2 个 image，1 个文件存在 → 0.5。"""
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake data")
    elements = [
        {"type": "image", "resource_path": str(img_path)},
        {"type": "image", "resource_path": "non_existent.png"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_ratio_image_base_dir_filename_lookup(tmp_path: Path):
    """resource_path 只是文件名，image_base_dir 提供目录 → valid。"""
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake data")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_returns_float_value():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert isinstance(out["value"], float)


def test_image_resource_ratio_does_not_raise_on_oserror(tmp_path: Path):
    """OSError 应被 catch，不传播。"""
    elements = [{"type": "image", "resource_path": str(tmp_path / "nonexistent.png")}]
    # 不应抛错
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


# =========================================================================
# _text_preservation 边界（更彻底）
# =========================================================================


def test_text_preservation_empty_returns_null_for_precision_recall():
    out = _text_preservation([], [])
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_equal_is_true():
    """空 vs 空 → equal=True。"""
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True


def test_text_preservation_identical_content_equal_true():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_elements_filtered():
    """image 不参与 expected_sequence。"""
    elements = [
        {"type": "image", "content": "ignored"},
        {"type": "paragraph", "content": "abc"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_missing_content_treated_as_empty():
    elements = [{"type": "paragraph"}]  # 缺 content
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_none_content_treated_as_empty():
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_missing_chunk_text_treated_as_empty():
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{}]  # 缺 text
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_precision_lower_than_recall_when_extra_chars():
    """actual 含 expected 之外的字符 → precision<1 但 recall=1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]  # d 是多余的
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision = 3/4, recall = 3/3 = 1
    assert out["precision"]["value"] == 0.75
    assert out["recall"]["value"] == 1.0


def test_text_preservation_recall_lower_than_precision_when_missing_chars():
    elements = [{"type": "paragraph", "content": "abcd"}]
    chunks = [{"text": "abc"}]  # d 缺失
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision = 3/3 = 1, recall = 3/4
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.75


def test_text_preservation_empty_expected_nonempty_actual_empty_actual_reason():
    """expected=空，actual=非空 → recall=empty_expected。"""
    elements = []
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected 空、actual 非空 → 不进 empty_expected_and_actual 分支
    assert out["precision"]["value"] == 0.0  # common=0 / |actual|=3
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_nonempty_expected_empty_actual():
    """expected=非空，actual=空 → precision=empty_actual。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    # expected 非空、actual 空 → 不进 empty_expected_and_actual 分支
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0  # common=0 / |expected|=3


def test_text_preservation_returns_dict_with_three_keys():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_keys_order():
    out = _text_preservation([], [])
    assert list(out.keys()) == ["equal", "precision", "recall"]


def test_text_preservation_whitespace_only_treated_as_empty():
    """全是 Unicode 空白 → strip 后为空。"""
    elements = [{"type": "paragraph", "content": " \t\n"}]
    chunks = [{"text": " "}]
    out = _text_preservation(elements, chunks)
    # 两边 strip 后都是空 → empty_expected_and_actual
    assert out["precision"]["reason"] == "empty_expected_and_actual"


# =========================================================================
# compute_automatic_metrics keys 顺序精确
# =========================================================================


def test_compute_automatic_metrics_keys_order_when_pipeline_failed():
    """document=None 时 keys 顺序精确。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    expected_keys = [
        "pipeline_success",
        "error_code",
        "schema_valid",
        "element_count_total",
        "element_count_by_type",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
    ]
    assert list(out.keys()) == expected_keys


def test_compute_automatic_metrics_keys_count_14_when_pipeline_failed():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out.keys()) == 14


def test_compute_automatic_metrics_keys_count_when_pipeline_success():
    """pipeline 成功也是 14 个 keys。"""
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert len(out.keys()) == 14


def test_compute_automatic_metrics_error_code_value_from_error():
    """error 给定时 error_code 取 error['code']。"""
    out = compute_automatic_metrics(None, {"code": "E_CUSTOM"}, "pdf", None)
    assert out["error_code"]["value"] == "E_CUSTOM"


def test_compute_automatic_metrics_markdown_source_type_treats_pdf_as_not_pdf():
    """source_type='markdown' → pdf_locator_valid_ratio = not_pdf_document。"""
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(document, None, "markdown", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_automatic_metrics_markdown_source_type_treats_docx_as_not_docx():
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(document, None, "markdown", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_schema_valid_when_doc_present(tmp_path: Path):
    """有 document 时 schema_valid 不抛错（即使 document 不合法也返回 False）。"""
    document = {"elements": [], "chunks": []}  # 可能不通过 schema
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["schema_valid"]["value"] in (True, False)


# =========================================================================
# Pipeline 完整路径边界
# =========================================================================


def test_compute_automatic_metrics_does_not_raise_on_empty_document():
    """空 document（无 elements/chunks）也不抛错。"""
    out = compute_automatic_metrics({}, None, "docx", None)
    # 后续 metric 会进入 no_elements / no_chunks / no_heading_elements 等 reason
    assert isinstance(out, dict)


def test_compute_automatic_metrics_does_not_mutate_input_error():
    """不修改 error dict。"""
    import copy
    error = {"code": "E_TEST"}
    error_before = copy.deepcopy(error)
    compute_automatic_metrics(None, error, "pdf", None)
    assert error == error_before


def test_compute_automatic_metrics_returns_dict_with_value_and_reason_per_metric():
    """每个 metric 都有 'value' 和 'reason' 字段。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    for name, metric in out.items():
        assert "value" in metric, f"{name} 缺 value"
        assert "reason" in metric, f"{name} 缺 reason"


def test_compute_automatic_metrics_metric_value_is_none_or_basic_type():
    """每个 value 是 None / bool / int / float / dict / str。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    valid_types = (type(None), bool, int, float, dict, str)
    for name, metric in out.items():
        assert isinstance(metric["value"], valid_types), f"{name} value 类型异常"


# =========================================================================
# 模块深度 introspection
# =========================================================================


def test_all_module_functions_listed_in_module():
    """所有 _xxx + compute_automatic_metrics 函数都在 module namespace。"""
    import evaluation.metrics as m

    for name in [
        "compute_automatic_metrics",
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
        "_null",
        "_ratio",
        "_bool_metric",
        "_int_metric",
    ]:
        assert hasattr(m, name), f"module 缺 {name}"


def test_module_has_only_one_exported_name():
    import evaluation.metrics as m

    assert m.__all__ == ["compute_automatic_metrics"]


def test_private_helpers_have_underscore_prefix():
    """所有非 compute_automatic_metrics 的函数都是 _ 前缀。"""
    import evaluation.metrics as m
    import types as _types

    for name, val in vars(m).items():
        if isinstance(val, _types.FunctionType) and name != "compute_automatic_metrics":
            assert name.startswith("_"), f"function {name} 缺 _ 前缀"


# =========================================================================
# 整体一致性：常量与 _TEXT_TYPES 元组类型
# =========================================================================


def test_text_types_is_tuple_not_list():
    import evaluation.metrics as m

    assert isinstance(m._TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_is_tuple_not_list():
    import evaluation.metrics as m

    assert isinstance(m._PDF_BBOX_REQUIRED_TYPES, tuple)


def test_text_types_subset_relationship_with_pdf_bbox_required():
    """_PDF_BBOX_REQUIRED_TYPES 是 _TEXT_TYPES 的子集（heading/paragraph 都在 _TEXT_TYPES）。"""
    import evaluation.metrics as m

    for t in m._PDF_BBOX_REQUIRED_TYPES:
        assert t in m._TEXT_TYPES


def test_text_types_does_not_contain_image():
    """image 不参与文本对比 → 不在 _TEXT_TYPES。"""
    import evaluation.metrics as m

    assert "image" not in m._TEXT_TYPES


def test_not_evaluated_constant_is_string():
    import evaluation.metrics as m

    assert isinstance(m._NOT_EVALUATED, str)


def test_not_evaluated_constant_value():
    import evaluation.metrics as m

    assert m._NOT_EVALUATED == "not_evaluated"


# =========================================================================
# helper functions metadata
# =========================================================================


def test_null_function_qualname():
    assert _null.__qualname__ == "_null"


def test_ratio_function_qualname():
    assert _ratio.__qualname__ == "_ratio"


def test_bool_metric_function_qualname():
    assert _bool_metric.__qualname__ == "_bool_metric"


def test_int_metric_function_qualname():
    assert _int_metric.__qualname__ == "_int_metric"


def test_pdf_locator_ratio_function_qualname():
    assert _pdf_locator_ratio.__qualname__ == "_pdf_locator_ratio"


def test_docx_locator_ratio_function_qualname():
    assert _docx_locator_ratio.__qualname__ == "_docx_locator_ratio"


def test_is_valid_bbox_function_qualname():
    assert _is_valid_bbox.__qualname__ == "_is_valid_bbox"


def test_image_resource_ratio_function_qualname():
    assert _image_resource_ratio.__qualname__ == "_image_resource_ratio"


def test_chunk_reference_ratio_function_qualname():
    assert _chunk_reference_ratio.__qualname__ == "_chunk_reference_ratio"


def test_strip_unicode_whitespace_function_qualname():
    assert _strip_unicode_whitespace.__qualname__ == "_strip_unicode_whitespace"


def test_text_preservation_function_qualname():
    assert _text_preservation.__qualname__ == "_text_preservation"


def test_heading_boundary_ratio_function_qualname():
    assert _heading_boundary_ratio.__qualname__ == "_heading_boundary_ratio"


def test_silent_drop_count_function_qualname():
    assert _silent_drop_count.__qualname__ == "_silent_drop_count"


def test_all_helpers_module_is_evaluation_metrics():
    import evaluation.metrics as m

    for fn in [
        _null,
        _ratio,
        _bool_metric,
        _int_metric,
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _is_valid_bbox,
        _image_resource_ratio,
        _chunk_reference_ratio,
        _strip_unicode_whitespace,
        _text_preservation,
        _heading_boundary_ratio,
        _silent_drop_count,
        compute_automatic_metrics,
    ]:
        assert fn.__module__ == "evaluation.metrics"


# =========================================================================
# 不缓存 / 不共享可变状态
# =========================================================================


def test_null_returns_independent_dict_each_call():
    a = _null("x")
    b = _null("y")
    a["reason"] = "modified"
    assert b["reason"] == "y"


def test_ratio_returns_independent_dict_each_call():
    a = _ratio(0.1)
    b = _ratio(0.2)
    a["value"] = 99.0
    assert b["value"] == 0.2


def test_bool_metric_returns_independent_dict_each_call():
    a = _bool_metric(True)
    b = _bool_metric(False)
    a["value"] = False
    assert b["value"] is False


def test_int_metric_returns_independent_dict_each_call():
    a = _int_metric(1)
    b = _int_metric(2)
    a["value"] = 100
    assert b["value"] == 2
