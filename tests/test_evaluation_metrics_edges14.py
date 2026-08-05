r"""evaluation/metrics.py 边角测试 - 第十四轮（Round 249）。

补强已有 base/edges/edges2-13（共 ~990+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含特定 token
- module metadata：__file__ 后缀 / __package__ / __name__ 精确
- 函数 metadata：__module__/__qualname__/__name__/FunctionType
- signature VAR_POSITIONAL/VAR_KEYWORD 不存在
- __future__ annotations 影响 return_annotation 为 str
- 常量精确：_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 内容+顺序+类型
- _strip_unicode_whitespace 字符级精确（NBSP/em space/零宽字符）
- _is_valid_bbox 边界（bool 拒绝/float 接受/NaN/Inf/-Inf）
- _null/_ratio/_bool_metric/_int_metric 不缓存（每次新 dict）
- _image_resource_ratio：directory 路径不算 file；size=0 算无效
- _chunk_reference_ratio：source_element_ids 含 None 跳过验证
- _silent_drop_count：actuals 多于 expected 不扣（max(0, ...)）
- _text_preservation：unicode whitespace 字符级
- module __all__ 仅 1 个元素
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
# 源码字符串断言（inspect.getsource）
# =========================================================================


def test_module_source_contains_text_types_definition():
    """源码含 '_TEXT_TYPES' 定义。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "_TEXT_TYPES" in src


def test_module_source_contains_pdf_bbox_required_types_definition():
    """源码含 '_PDF_BBOX_REQUIRED_TYPES' 定义。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_contains_not_evaluated_constant():
    """源码含 '_NOT_EVALUATED'。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "_NOT_EVALUATED" in src


def test_module_source_contains_counter_import():
    """源码含 'from collections import Counter'。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "from collections import Counter" in src


def test_module_source_contains_pathlib_path_import():
    """源码含 'from pathlib import Path'。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_contains_future_annotations():
    """源码含 'from __future__ import annotations'。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_contains_dict_subscript_syntax():
    """源码含 'dict[str,'（Python 3.9+ subscript）。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "dict[str," in src


def test_module_source_contains_schema_validation_lazy_import():
    """源码含延迟 import 'from evaluation.schema_validation import document_passes_schema'。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_module_source_contains_silent_drop_count_algorithm():
    """源码含 'max(0,' 算法（或等价的 'if actual < exp'）。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "if actual < exp" in src


def test_module_source_contains_text_preservation_v11_note():
    """源码含 'v1.1' 注释。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "v1.1" in src


def test_module_source_no_main_guard():
    """源码不含 '__main__' guard。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "__main__" not in src


def test_module_source_contains_math_isfinite():
    """源码含 'math.isfinite'。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "math.isfinite" in src


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_endswith_py():
    """模块 __file__ 以 '.py' 结尾。"""
    import evaluation.metrics as m
    assert m.__file__.endswith(".py")


def test_module_file_contains_metrics():
    """模块 __file__ 含 'metrics'。"""
    import evaluation.metrics as m
    assert "metrics" in m.__file__


def test_module_package_is_evaluation():
    """__package__ == 'evaluation'。"""
    import evaluation.metrics as m
    assert m.__package__ == "evaluation"


def test_module_name_is_evaluation_metrics():
    """__name__ == 'evaluation.metrics'。"""
    import evaluation.metrics as m
    assert m.__name__ == "evaluation.metrics"


def test_module_counter_is_collections_counter():
    """Counter is collections.Counter。"""
    import evaluation.metrics as m
    assert m.Counter is Counter


def test_module_path_is_pathlib_path():
    """Path is pathlib.Path。"""
    import evaluation.metrics as m
    from pathlib import Path as P
    assert m.Path is P


def test_module_math_is_math_module():
    """math is math。"""
    import evaluation.metrics as m
    assert m.math is math


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_only_one_element():
    """__all__ 仅 1 个元素。"""
    import evaluation.metrics as m
    assert len(m.__all__) == 1


def test_module_all_first_element_compute_automatic_metrics():
    """__all__[0] == 'compute_automatic_metrics'。"""
    import evaluation.metrics as m
    assert m.__all__[0] == "compute_automatic_metrics"


def test_module_all_does_not_contain_helpers():
    """__all__ 不含私有 helper。"""
    import evaluation.metrics as m
    assert "_null" not in m.__all__
    assert "_ratio" not in m.__all__
    assert "_is_valid_bbox" not in m.__all__


def test_module_all_is_list_not_tuple():
    """__all__ 是 list 不是 tuple。"""
    import evaluation.metrics as m
    assert isinstance(m.__all__, list)
    assert not isinstance(m.__all__, tuple)


# =========================================================================
# 常量精确（_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED）
# =========================================================================


def test_text_types_is_tuple():
    """_TEXT_TYPES 是 tuple。"""
    from evaluation.metrics import _TEXT_TYPES
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_exact_contents_in_order():
    """_TEXT_TYPES 内容精确（按定义顺序）。"""
    from evaluation.metrics import _TEXT_TYPES
    assert _TEXT_TYPES == (
        "heading",
        "paragraph",
        "list_item",
        "table",
        "caption",
        "header",
        "footer",
    )


def test_text_types_length_seven():
    """_TEXT_TYPES 7 个元素。"""
    from evaluation.metrics import _TEXT_TYPES
    assert len(_TEXT_TYPES) == 7


def test_text_types_first_heading():
    """_TEXT_TYPES[0] == 'heading'。"""
    from evaluation.metrics import _TEXT_TYPES
    assert _TEXT_TYPES[0] == "heading"


def test_text_types_last_footer():
    """_TEXT_TYPES[-1] == 'footer'。"""
    from evaluation.metrics import _TEXT_TYPES
    assert _TEXT_TYPES[-1] == "footer"


def test_text_types_no_duplicates():
    """_TEXT_TYPES 无重复。"""
    from evaluation.metrics import _TEXT_TYPES
    assert len(_TEXT_TYPES) == len(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_is_tuple():
    """_PDF_BBOX_REQUIRED_TYPES 是 tuple。"""
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_exact_contents():
    """_PDF_BBOX_REQUIRED_TYPES 内容精确。"""
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_pdf_bbox_required_types_length_four():
    """_PDF_BBOX_REQUIRED_TYPES 4 个元素。"""
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES ⊆ _TEXT_TYPES。"""
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES, _TEXT_TYPES
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_excludes_table_header_footer():
    """_PDF_BBOX_REQUIRED_TYPES 不含 table/header/footer（文本但不需要 bbox）。"""
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_value_exact():
    """_NOT_EVALUATED == 'not_evaluated'。"""
    from evaluation.metrics import _NOT_EVALUATED
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str():
    """_NOT_EVALUATED 是 str。"""
    from evaluation.metrics import _NOT_EVALUATED
    assert isinstance(_NOT_EVALUATED, str)


# =========================================================================
# 函数 metadata
# =========================================================================


def test_compute_automatic_metrics_module_attribute():
    """__module__ == 'evaluation.metrics'。"""
    assert compute_automatic_metrics.__module__ == "evaluation.metrics"


def test_compute_automatic_metrics_qualname():
    """__qualname__ == 'compute_automatic_metrics'。"""
    assert compute_automatic_metrics.__qualname__ == "compute_automatic_metrics"


def test_compute_automatic_metrics_name():
    """__name__ == 'compute_automatic_metrics'。"""
    assert compute_automatic_metrics.__name__ == "compute_automatic_metrics"


def test_compute_automatic_metrics_is_function():
    """是 Python 函数。"""
    import types
    assert isinstance(compute_automatic_metrics, types.FunctionType)


def test_compute_automatic_metrics_no_varargs():
    """无 VAR_POSITIONAL。"""
    sig = inspect.signature(compute_automatic_metrics)
    assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())


def test_compute_automatic_metrics_no_varkw():
    """无 VAR_KEYWORD。"""
    sig = inspect.signature(compute_automatic_metrics)
    assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def test_compute_automatic_metrics_return_annotation_is_str():
    """return annotation 是 str（__future__）。"""
    sig = inspect.signature(compute_automatic_metrics)
    assert isinstance(sig.return_annotation, str)


def test_all_helper_functions_no_varargs():
    """所有 helper 都无 VAR_POSITIONAL。"""
    helpers = [
        _null, _ratio, _bool_metric, _int_metric,
        _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox,
        _image_resource_ratio, _chunk_reference_ratio,
        _strip_unicode_whitespace, _text_preservation,
        _heading_boundary_ratio, _silent_drop_count,
    ]
    for fn in helpers:
        sig = inspect.signature(fn)
        assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values()), \
            f"{fn.__name__} 不应有 VAR_POSITIONAL"


def test_all_helper_functions_no_varkw():
    """所有 helper 都无 VAR_KEYWORD。"""
    helpers = [
        _null, _ratio, _bool_metric, _int_metric,
        _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox,
        _image_resource_ratio, _chunk_reference_ratio,
        _strip_unicode_whitespace, _text_preservation,
        _heading_boundary_ratio, _silent_drop_count,
    ]
    for fn in helpers:
        sig = inspect.signature(fn)
        assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()), \
            f"{fn.__name__} 不应有 VAR_KEYWORD"


def test_all_helper_functions_are_python_functions():
    """所有 helper 都是 Python 函数。"""
    import types
    helpers = [
        _null, _ratio, _bool_metric, _int_metric,
        _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox,
        _image_resource_ratio, _chunk_reference_ratio,
        _strip_unicode_whitespace, _text_preservation,
        _heading_boundary_ratio, _silent_drop_count,
    ]
    for fn in helpers:
        assert isinstance(fn, types.FunctionType), f"{fn.__name__} 应是 FunctionType"


def test_all_helper_functions_module_attribute():
    """所有 helper __module__ == 'evaluation.metrics'。"""
    helpers = [
        _null, _ratio, _bool_metric, _int_metric,
        _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox,
        _image_resource_ratio, _chunk_reference_ratio,
        _strip_unicode_whitespace, _text_preservation,
        _heading_boundary_ratio, _silent_drop_count,
    ]
    for fn in helpers:
        assert fn.__module__ == "evaluation.metrics"


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric 不缓存
# =========================================================================


def test_null_returns_new_dict_each_call():
    """_null 每次返回新 dict（不缓存）。"""
    a = _null("x")
    b = _null("x")
    assert a is not b
    assert a == b


def test_ratio_returns_new_dict_each_call():
    """_ratio 每次返回新 dict。"""
    a = _ratio(0.5)
    b = _ratio(0.5)
    assert a is not b
    assert a == b


def test_bool_metric_returns_new_dict_each_call():
    """_bool_metric 每次返回新 dict。"""
    a = _bool_metric(True)
    b = _bool_metric(True)
    assert a is not b
    assert a == b


def test_int_metric_returns_new_dict_each_call():
    """_int_metric 每次返回新 dict。"""
    a = _int_metric(5)
    b = _int_metric(5)
    assert a is not b
    assert a == b


# =========================================================================
# _is_valid_bbox 详细
# =========================================================================


def test_is_valid_bbox_float_values_accepted():
    """bbox=[1.0, 2.0, 3.0, 4.0] 接受。"""
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0]) is True


def test_is_valid_bbox_int_values_accepted():
    """bbox=[1, 2, 3, 4] 接受。"""
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_mixed_int_float_accepted():
    """bbox=[1, 2.5, 3, 4.0] 接受。"""
    assert _is_valid_bbox([1, 2.5, 3, 4.0]) is True


def test_is_valid_bbox_bool_true_rejected():
    """bbox=[True, 1, 2, 3] → bool 拒绝。"""
    assert _is_valid_bbox([True, 1, 2, 3]) is False


def test_is_valid_bbox_bool_false_rejected():
    """bbox=[1, 2, 3, False] → bool 拒绝（虽然 False 是 int 0）。"""
    assert _is_valid_bbox([1, 2, 3, False]) is False


def test_is_valid_bbox_length_three_rejected():
    """bbox=[1, 2, 3] 长度 3 拒绝。"""
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_length_five_rejected():
    """bbox=[1, 2, 3, 4, 5] 长度 5 拒绝。"""
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_empty_list_rejected():
    """bbox=[] 拒绝。"""
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_tuple_rejected():
    """bbox 是 tuple 拒绝（源码用 isinstance list）。"""
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_none_rejected():
    """bbox=None 拒绝。"""
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string_elements_rejected():
    """bbox=['1', '2', '3', '4'] 字符串元素拒绝。"""
    assert _is_valid_bbox(["1", "2", "3", "4"]) is False


def test_is_valid_bbox_inf_rejected():
    """bbox=[1, 2, 3, math.inf] Inf 拒绝。"""
    assert _is_valid_bbox([1, 2, 3, math.inf]) is False


def test_is_valid_bbox_neg_inf_rejected():
    """bbox=[1, 2, 3, -math.inf] -Inf 拒绝。"""
    assert _is_valid_bbox([1, 2, 3, -math.inf]) is False


def test_is_valid_bbox_nan_rejected():
    """bbox=[1, 2, 3, math.nan] NaN 拒绝。"""
    assert _is_valid_bbox([1, 2, 3, math.nan]) is False


def test_is_valid_bbox_negative_numbers_accepted():
    """bbox=[-1, -2, -3, -4] 负数接受（PDF 坐标可能为负）。"""
    assert _is_valid_bbox([-1, -2, -3, -4]) is True


def test_is_valid_bbox_zeros_accepted():
    """bbox=[0, 0, 0, 0] 接受。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_very_large_values_accepted():
    """bbox=[1e300, 2e300, 3e300, 4e300] 大数值接受（仍 finite）。"""
    assert _is_valid_bbox([1e300, 2e300, 3e300, 4e300]) is True


def test_is_valid_bbox_returns_bool_type():
    """返回类型是 bool（不是 int）。"""
    assert type(_is_valid_bbox([1, 2, 3, 4])) is bool
    assert type(_is_valid_bbox([1, 2, 3])) is bool


# =========================================================================
# _strip_unicode_whitespace 字符级精确
# =========================================================================


def test_strip_unicode_whitespace_nbsp():
    """NBSP (U+00A0) 是空白，被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """em space (U+2003) 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """en space (U+2002) 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """全角空格 (U+3000) 是空白。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """U+2028 LINE SEPARATOR 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029 PARAGRAPH SEPARATOR 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_zero_width_not_whitespace():
    """U+200B ZERO WIDTH SPACE 不是空白（不删除）。"""
    # 实际上 ZWSP 是否 isspace 取决于 Python 版本；CPython 3.12 中 ZWSP isspace() 是 False
    # 验证当前 Python 的行为
    expected = "" if "​".isspace() else "​"
    assert _strip_unicode_whitespace("​") == expected


def test_strip_unicode_whitespace_normal_tab():
    """普通 \t 是空白。"""
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_normal_newline():
    """普通 \n 是空白。"""
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return():
    """\r 是空白。"""
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_form_feed():
    """\f 是空白。"""
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_vertical_tab():
    """\v 是空白。"""
    assert _strip_unicode_whitespace("a\vb") == "ab"


def test_strip_unicode_whitespace_preserves_non_whitespace():
    """非空白字符全部保留（含标点、emoji、汉字）。"""
    s = "hello,世界!😀"
    assert _strip_unicode_whitespace(s) == s


def test_strip_unicode_whitespace_empty_string():
    """空字符串 → 空字符串。"""
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace():
    """全空白 → 空。"""
    assert _strip_unicode_whitespace(" \t\n\r 　") == ""


def test_strip_unicode_whitespace_bytes_raises_attribute_error():
    """bytes 输入：iterating bytes 给 int，int 无 isspace() → AttributeError。"""
    with pytest.raises(AttributeError):
        _strip_unicode_whitespace(b"abc")  # type: ignore


def test_strip_unicode_whitespace_returns_str_type():
    """返回 str。"""
    assert isinstance(_strip_unicode_whitespace("abc"), str)


def test_strip_unicode_whitespace_does_not_sort_chars():
    """不排序字符。"""
    # 'cba' → 'cba'（仅去空白，不排序）
    assert _strip_unicode_whitespace("cba") == "cba"


def test_strip_unicode_whitespace_signature_param_count():
    """signature: (s) 1 个参数。"""
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


# =========================================================================
# _image_resource_ratio 详细
# =========================================================================


def test_image_resource_ratio_directory_path_not_counted_as_valid(tmp_path: Path):
    """directory path 是 is_dir() 不是 is_file() → 无效。"""
    # 创建一个子目录当作 resource_path
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    elements = [{"type": "image", "resource_path": str(subdir)}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    # directory 不是 file → valid=0
    assert out["value"] == 0.0


def test_image_resource_ratio_size_zero_invalid(tmp_path: Path):
    """size=0 的文件 → stat().st_size > 0 失败 → 无效。"""
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(empty)}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_size_one_valid(tmp_path: Path):
    """size=1 的文件 → 有效。"""
    f = tmp_path / "tiny.png"
    f.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": str(f)}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_all_images_valid(tmp_path: Path):
    """3 个有效图片 → ratio 1.0。"""
    files = []
    for i in range(3):
        p = tmp_path / f"img{i}.png"
        p.write_bytes(b"data")
        files.append(str(p))
    elements = [{"type": "image", "resource_path": fp} for fp in files]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path: Path):
    """2 个有效 + 1 个不存在 → ratio 2/3。"""
    f1 = tmp_path / "a.png"
    f2 = tmp_path / "b.png"
    f1.write_bytes(b"a")
    f2.write_bytes(b"b")
    elements = [
        {"type": "image", "resource_path": str(f1)},
        {"type": "image", "resource_path": str(f2)},
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},
    ]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert abs(out["value"] - 2 / 3) < 1e-9


def test_image_resource_ratio_no_resource_path_key(tmp_path: Path):
    """image 元素无 resource_path key → 跳过 → valid=0。"""
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_resource_path_empty_string(tmp_path: Path):
    """resource_path='' → falsy → 跳过。"""
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_resource_path_none(tmp_path: Path):
    """resource_path=None → falsy → 跳过。"""
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_no_images_returns_no_image_elements(tmp_path: Path):
    """无 image 元素 → reason 'no_image_elements'。"""
    elements = [{"type": "paragraph", "content": "text"}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["reason"] == "no_image_elements"
    assert out["value"] is None


def test_image_resource_ratio_relative_path_with_base_dir(tmp_path: Path):
    """resource_path 是相对路径，image_base_dir 提供时也尝试拼接。"""
    f = tmp_path / "img.png"
    f.write_bytes(b"data")
    # 仅写 'img.png'（basename），与 image_base_dir 拼接
    elements = [{"type": "image", "resource_path": "img.png"}]
    # 但 Path('img.png').name == 'img.png'；image_base_dir / 'img.png' = tmp_path / 'img.png'
    # Path('img.png').is_file() 在当前工作目录可能不存在 → 走 base_dir 拼接
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    # 至少应找到 1 个（image_base_dir 拼接路径）
    assert out["value"] == 1.0


# =========================================================================
# _chunk_reference_ratio 详细
# =========================================================================


def test_chunk_reference_ratio_no_chunks_returns_null():
    """chunks=[] → 'no_chunks'。"""
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_source_element_ids_none_in_list():
    """source_element_ids=[None] → None in elem_ids 集合时视作不匹配。"""
    # elements=[{'element_id': None}] → elem_ids = {None}
    # chunk references [None] → all(None in {None}) → True
    # 但源码 ids 和 elem_ids 都可能为 None
    elements = [{"element_id": None}]
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # None in {None} is True → valid=1
    assert out["value"] == 1.0


def test_chunk_reference_ratio_chunk_source_element_ids_empty_list():
    """source_element_ids=[] → falsy → 跳过该 chunk（不计入 valid）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    # ids=[] falsy → 跳过 → valid=0, len(chunks)=1
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_source_element_ids_missing_key():
    """source_element_ids key 缺失 → .get 返回 None → or [] → falsy → 跳过。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # 无 source_element_ids key
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_partial_valid_ids():
    """chunk references [valid, invalid] → all() False → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e_missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_returns_one():
    """chunk references 全 valid → ratio 1.0。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# =========================================================================
# _silent_drop_count 详细
# =========================================================================


def test_silent_drop_count_actual_more_than_expected_no_drop():
    """actual > expected → max(0, exp-act)=0（不扣）。"""
    by_type = {"heading": 5}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_actual_equals_expected_no_drop():
    """actual == expected → 0。"""
    by_type = {"heading": 3}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_some_types_drop():
    """多类型：some drop some not。"""
    by_type = {"heading": 2, "paragraph": 5, "table": 1}
    expectations = {"element_count_by_type": {"heading": 5, "paragraph": 5, "table": 3}}
    out = _silent_drop_count(by_type, expectations)
    # heading: max(0, 5-2)=3; paragraph: 0; table: max(0, 3-1)=2; total 5
    assert out["value"] == 5


def test_silent_drop_count_expected_type_missing_in_actual():
    """expected 含 'caption':2 但 actual 无 caption → drop 2。"""
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"caption": 2}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2


def test_silent_drop_count_returns_int_metric_with_none_reason():
    """success 路径 reason 是 None。"""
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"heading": 2}}
    out = _silent_drop_count(by_type, expectations)
    assert out["reason"] is None


def test_silent_drop_count_no_expectations_returns_null():
    """expectations=None → null。"""
    out = _silent_drop_count({"heading": 1}, None)
    assert out["reason"] == "no_expectations"
    assert out["value"] is None


def test_silent_drop_count_empty_expectations_returns_null():
    """expectations={} → null。"""
    out = _silent_drop_count({"heading": 1}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expected_counts_returns_null():
    """element_count_by_type={} → 'no_expectations_element_count'。"""
    out = _silent_drop_count({"heading": 1}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expected_counts_none_returns_null():
    """element_count_by_type=None → or {} → 'no_expectations_element_count'。"""
    out = _silent_drop_count({"heading": 1}, {"element_count_by_type": None})
    assert out["reason"] == "no_expectations_element_count"


# =========================================================================
# _pdf_locator_ratio 详细
# =========================================================================


def test_pdf_locator_ratio_no_elements_returns_null():
    """空 elements → 'no_elements'。"""
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_text_type_requires_bbox():
    """paragraph 类型无 bbox → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]  # 缺 bbox
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_non_text_type_no_bbox_required():
    """table 类型不需要 bbox → 仅 page≥1 即 valid。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_header_no_bbox_required():
    """header 类型不需要 bbox。"""
    elements = [{"type": "header", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_footer_no_bbox_required():
    """footer 类型不需要 bbox。"""
    elements = [{"type": "footer", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_caption_requires_bbox():
    """caption 在 _PDF_BBOX_REQUIRED_TYPES 中 → 需要 bbox。"""
    elements = [{"type": "caption", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_list_item_requires_bbox():
    """list_item 在 _PDF_BBOX_REQUIRED_TYPES 中。"""
    elements = [{"type": "list_item", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_source_locator_none_treated_as_empty_dict():
    """source_locator=None → or {} → page=None → invalid。"""
    elements = [{"type": "table", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_source_locator_missing_key():
    """无 source_locator key → .get 返回 None → or {} → page=None → invalid。"""
    elements = [{"type": "table"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_float_rejected():
    """page=1.5 不是 int → invalid。"""
    elements = [{"type": "table", "source_locator": {"page": 1.5}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_bool_rejected():
    """page=True → isinstance(True, int) 是 True 在 Python 中，但源码不显式拒绝 bool

    Python 中 bool 是 int 子类，所以 isinstance(True, int) == True。
    page=True → page < 1 → False (因为 True == 1) → 进入 valid。
    """
    elements = [{"type": "table", "source_locator": {"page": True}}]
    out = _pdf_locator_ratio(elements)
    # True 在 Python 中相当于 1，所以 valid
    assert out["value"] == 1.0


# =========================================================================
# _docx_locator_ratio 详细
# =========================================================================


def test_docx_locator_ratio_no_elements_returns_null():
    """空 elements → 'no_elements'。"""
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_structural_keys_seven_count():
    """7 个 structural keys。"""
    # 验证：每个 key 单独都能让元素 valid
    keys = [
        "section", "paragraph_index", "run_index",
        "table_index", "row_index", "col_index", "relationship_id",
    ]
    for k in keys:
        elements = [{"type": "paragraph", "source_locator": {k: 1}}]
        out = _docx_locator_ratio(elements)
        assert out["value"] == 1.0, f"key={k} 应该 valid"


def test_docx_locator_ratio_with_page_key_invalid():
    """locator 含 page → invalid（DOCX 不应有 page）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_key_invalid():
    """locator 含 bbox → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4], "section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_only_page_and_bbox_invalid():
    """locator 仅含 page 和 bbox → invalid（无 structural key 也不行）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_source_locator_invalid():
    """无 source_locator key → .get 返回 None → or {} → no structural → invalid。"""
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_source_locator_none_invalid():
    """source_locator=None → or {} → invalid。"""
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_empty_locator_invalid():
    """source_locator={} → 无 structural key → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# =========================================================================
# _text_preservation 详细
# =========================================================================


def test_text_preservation_empty_both_returns_null_precision_recall():
    """elements=[] chunks=[] → precision/recall 'empty_expected_and_actual'。"""
    out = _text_preservation([], [])
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"
    assert out["equal"]["value"] is True  # 空字符串相等


def test_text_preservation_only_image_elements_returns_empty_expected():
    """elements 全是 image → expected_raw='' → expected='' → recall null 'empty_expected'。"""
    elements = [{"type": "image", "content": ""}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected='', actual='abc'
    # equal: '' == 'abc' → False
    assert out["equal"]["value"] is False
    # recall: c_expected empty → 'empty_expected'
    assert out["recall"]["reason"] == "empty_expected"
    # precision: c_actual non-empty → common=0 / |actual|=3 → 0.0
    assert out["precision"]["value"] == 0.0


def test_text_preservation_image_content_excluded():
    """image element 的 content 不参与 expected（即使非空）。"""
    elements = [{"type": "image", "content": "abc"}]
    chunks = []  # actual=空
    out = _text_preservation(elements, chunks)
    # expected='', actual=''
    # equal: True
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_text_none_treated_as_empty():
    """chunk text=None → or '' → actual 加空。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    # expected='abc', actual=''
    assert out["equal"]["value"] is False
    # precision: |actual|=0 → 'empty_actual'
    assert out["precision"]["reason"] == "empty_actual"
    # recall: |expected|=3, common=0 → 0/3=0.0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_element_content_none_treated_as_empty():
    """element content=None → or '' → expected 加空。"""
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected='', actual='abc'
    assert out["equal"]["value"] is False
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_returns_dict_with_three_keys():
    """返回 dict 含 3 keys：equal/precision/recall。"""
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


# =========================================================================
# _heading_boundary_ratio 详细
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    """无 heading → 'no_heading_elements'。"""
    out = _heading_boundary_ratio([{"type": "paragraph"}], [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_heading_first_id_match():
    """heading element_id == chunk[0] source_element_ids[0] → valid。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_heading_second_id_not_match():
    """heading 不是 chunk 的第一个 → 不算合规。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]  # h1 是第 2 个
    out = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids = {'other'}，h1 不在 → 0 valid
    assert out["value"] == 0.0


def test_heading_boundary_ratio_no_chunks_with_headings_returns_zero():
    """有 heading 但 chunks=[] → ratio 0.0（不算 'no_chunks'）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    # chunk_first_ids 是 set()，matched=0, len(headings)=1 → ratio 0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunks_empty_source_element_ids_skipped():
    """chunk 的 source_element_ids 空 → 跳过。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}, {"source_element_ids": None}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# =========================================================================
# compute_automatic_metrics 整体行为
# =========================================================================


def test_compute_automatic_metrics_doc_none_returns_pipeline_failed_for_late_metrics():
    """document=None → 后续 11 个 metric 全 'pipeline_failed'。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    failed_metrics = [
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
    for name in failed_metrics:
        assert out[name]["reason"] == "pipeline_failed", f"{name} 应是 pipeline_failed"


def test_compute_automatic_metrics_doc_none_pipeline_success_false():
    """document=None → pipeline_success=False。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_doc_none_error_code_none():
    """document=None error=None → error_code value=None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_automatic_metrics_doc_none_schema_valid_pipeline_failed():
    """document=None → schema_valid 'pipeline_failed'。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_total_keys_count_when_doc_none():
    """document=None → metrics 共 14 个 keys（pipeline_success + error_code + schema_valid + 11 null）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14


def test_compute_automatic_metrics_returns_dict_type():
    """返回 dict。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_automatic_metrics_does_not_mutate_input_document(tmp_path: Path):
    """不修改输入 document。"""
    import copy
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    document_before = copy.deepcopy(document)
    compute_automatic_metrics(document, None, "docx", None, image_base_dir=tmp_path)
    assert document == document_before


def test_compute_automatic_metrics_does_not_mutate_expectations():
    """不修改 expectations。"""
    import copy
    expectations = {"element_count_by_type": {"paragraph": 2}}
    expectations_before = copy.deepcopy(expectations)
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    compute_automatic_metrics(document, None, "docx", expectations)
    assert expectations == expectations_before


# =========================================================================
# module __all__ 不含 helper
# =========================================================================


def test_module_all_only_exports_compute_automatic_metrics():
    """__all__ 仅导出 compute_automatic_metrics。"""
    import evaluation.metrics as m
    assert m.__all__ == ["compute_automatic_metrics"]
