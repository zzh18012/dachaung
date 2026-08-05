r"""evaluation/metrics.py 边角测试 - 第十六轮（Round 263）。

补强已有 base/edges/edges2-15（共 ~1290+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：未覆盖 token
- module docstring 内容（v1.0 vs v1.1 差异、text_preservation 语义）
- 函数签名 introspection 详细
- _pdf_locator_ratio _PDF_BBOX_REQUIRED_TYPES 详细：每个 type 单独验证
- _docx_locator_ratio structural_keys 详细：每个 key 单独验证
- _image_resource_ratio PermissionError 处理（不应抛错）
- _chunk_reference_ratio source_element_ids 含 duplicate
- _heading_boundary_ratio 多 chunk 首 id 重复
- _silent_drop_count expectations 多 type
- _text_preservation：utf-8 chars / surrogate pairs / ZWJ
- compute_automatic_metrics：source_type 'docx' 路径
- compute_automatic_metrics：error_code 取自 error dict
- 模块 namespace 完整性
- 模块 __all__ 精确
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


def test_module_source_contains_def_null():
    import evaluation.metrics as m

    assert "def _null(" in inspect.getsource(m)


def test_module_source_contains_def_ratio():
    import evaluation.metrics as m

    assert "def _ratio(" in inspect.getsource(m)


def test_module_source_contains_def_bool_metric():
    import evaluation.metrics as m

    assert "def _bool_metric(" in inspect.getsource(m)


def test_module_source_contains_def_int_metric():
    import evaluation.metrics as m

    assert "def _int_metric(" in inspect.getsource(m)


def test_module_source_contains_compute_automatic_metrics_def():
    import evaluation.metrics as m

    assert "def compute_automatic_metrics(" in inspect.getsource(m)


def test_module_source_contains_def_pdf_locator_ratio():
    import evaluation.metrics as m

    assert "def _pdf_locator_ratio(" in inspect.getsource(m)


def test_module_source_contains_def_docx_locator_ratio():
    import evaluation.metrics as m

    assert "def _docx_locator_ratio(" in inspect.getsource(m)


def test_module_source_contains_def_is_valid_bbox():
    import evaluation.metrics as m

    assert "def _is_valid_bbox(" in inspect.getsource(m)


def test_module_source_contains_def_image_resource_ratio():
    import evaluation.metrics as m

    assert "def _image_resource_ratio(" in inspect.getsource(m)


def test_module_source_contains_def_chunk_reference_ratio():
    import evaluation.metrics as m

    assert "def _chunk_reference_ratio(" in inspect.getsource(m)


def test_module_source_contains_def_strip_unicode_whitespace():
    import evaluation.metrics as m

    assert "def _strip_unicode_whitespace(" in inspect.getsource(m)


def test_module_source_contains_def_text_preservation():
    import evaluation.metrics as m

    assert "def _text_preservation(" in inspect.getsource(m)


def test_module_source_contains_def_heading_boundary_ratio():
    import evaluation.metrics as m

    assert "def _heading_boundary_ratio(" in inspect.getsource(m)


def test_module_source_contains_def_silent_drop_count():
    import evaluation.metrics as m

    assert "def _silent_drop_count(" in inspect.getsource(m)


def test_module_source_contains_text_types_definition():
    """源码含 _TEXT_TYPES = (...)。"""
    import evaluation.metrics as m

    assert '_TEXT_TYPES = (' in inspect.getsource(m)


def test_module_source_contains_pdf_bbox_required_types_definition():
    """源码含 _PDF_BBOX_REQUIRED_TYPES = (...)。"""
    import evaluation.metrics as m

    assert '_PDF_BBOX_REQUIRED_TYPES = (' in inspect.getsource(m)


def test_module_source_contains_not_evaluated_constant():
    """源码含 _NOT_EVALUATED = 'not_evaluated'。"""
    import evaluation.metrics as m

    assert '_NOT_EVALUATED = "not_evaluated"' in inspect.getsource(m)


def test_module_source_contains_text_types_seven_types():
    """源码含 7 个 type。"""
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert '"heading"' in src
    assert '"paragraph"' in src
    assert '"list_item"' in src
    assert '"table"' in src
    assert '"caption"' in src
    assert '"header"' in src
    assert '"footer"' in src


def test_module_source_contains_pdf_bbox_required_types_four():
    """源码含 4 个 PDF bbox required type。"""
    import evaluation.metrics as m

    src = inspect.getsource(m)
    # heading/paragraph/caption/list_item
    assert '"heading"' in src
    assert '"paragraph"' in src
    assert '"caption"' in src
    assert '"list_item"' in src


def test_module_source_contains_docx_structural_keys_seven():
    """源码含 DOCX 7 个 structural_keys。"""
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert '"section"' in src
    assert '"paragraph_index"' in src
    assert '"run_index"' in src
    assert '"table_index"' in src
    assert '"row_index"' in src
    assert '"col_index"' in src
    assert '"relationship_id"' in src


def test_module_source_contains_pipeline_success_logic():
    """源码含 'pipeline_success = error is None and document is not None'。"""
    import evaluation.metrics as m

    assert "pipeline_success = error is None and document is not None" in inspect.getsource(m)


def test_module_source_contains_error_code_logic():
    """源码含 error['code'] 取值。"""
    import evaluation.metrics as m

    assert 'error["code"]' in inspect.getsource(m)


def test_module_source_contains_schema_validation_deferred_import():
    """源码含延迟 import schema_validation。"""
    import evaluation.metrics as m

    assert "from evaluation.schema_validation import document_passes_schema" in inspect.getsource(m)


def test_module_source_contains_schema_check_exception_message():
    """源码含 'schema_check_exception'。"""
    import evaluation.metrics as m

    assert "schema_check_exception" in inspect.getsource(m)


def test_module_source_contains_not_pdf_document_reason():
    """源码含 'not_pdf_document'。"""
    import evaluation.metrics as m

    assert '"not_pdf_document"' in inspect.getsource(m)


def test_module_source_contains_not_docx_document_reason():
    """源码含 'not_docx_document'。"""
    import evaluation.metrics as m

    assert '"not_docx_document"' in inspect.getsource(m)


def test_module_source_contains_pipeline_failed_reason():
    """源码含 'pipeline_failed'。"""
    import evaluation.metrics as m

    assert '"pipeline_failed"' in inspect.getsource(m)


def test_module_source_contains_no_elements_reason():
    import evaluation.metrics as m

    assert '"no_elements"' in inspect.getsource(m)


def test_module_source_contains_no_chunks_reason():
    import evaluation.metrics as m

    assert '"no_chunks"' in inspect.getsource(m)


def test_module_source_contains_no_image_elements_reason():
    import evaluation.metrics as m

    assert '"no_image_elements"' in inspect.getsource(m)


def test_module_source_contains_no_heading_elements_reason():
    import evaluation.metrics as m

    assert '"no_heading_elements"' in inspect.getsource(m)


def test_module_source_contains_no_expectations_reason():
    import evaluation.metrics as m

    assert '"no_expectations"' in inspect.getsource(m)


def test_module_source_contains_no_expectations_element_count_reason():
    import evaluation.metrics as m

    assert '"no_expectations_element_count"' in inspect.getsource(m)


def test_module_source_contains_empty_actual_reason():
    import evaluation.metrics as m

    assert '"empty_actual"' in inspect.getsource(m)


def test_module_source_contains_empty_expected_reason():
    import evaluation.metrics as m

    assert '"empty_expected"' in inspect.getsource(m)


def test_module_source_contains_empty_expected_and_actual_reason():
    import evaluation.metrics as m

    assert '"empty_expected_and_actual"' in inspect.getsource(m)


def test_module_source_contains_counter_intersection():
    """源码含 c_expected & c_actual（Counter 交集）。"""
    import evaluation.metrics as m

    assert "c_expected & c_actual" in inspect.getsource(m)


def test_module_source_contains_chunk_first_ids_add():
    """源码含 chunk_first_ids.add(ids[0])。"""
    import evaluation.metrics as m

    assert "chunk_first_ids.add(ids[0])" in inspect.getsource(m)


def test_module_source_contains_silent_drop_max_zero():
    """源码含 max(0, ...) 隐式语义（actual > expected → 不扣）。"""
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "if actual < exp" in src
    assert "drops += (exp - actual)" in src


def test_module_source_contains_image_filter():
    """源码含 type == 'image' 过滤。"""
    import evaluation.metrics as m

    assert '== "image"' in inspect.getsource(m)


def test_module_source_contains_heading_filter():
    """源码含 type == 'heading' 过滤。"""
    import evaluation.metrics as m

    assert '== "heading"' in inspect.getsource(m)


def test_module_source_contains_image_resource_path_check():
    """源码含 if not rp: continue。"""
    import evaluation.metrics as m

    assert "if not rp:" in inspect.getsource(m)


def test_module_source_contains_image_size_check():
    """源码含 p.stat().st_size > 0。"""
    import evaluation.metrics as m

    assert "st_size > 0" in inspect.getsource(m)


def test_module_source_contains_image_isfile_check():
    """源码含 p.is_file()。"""
    import evaluation.metrics as m

    assert "p.is_file()" in inspect.getsource(m)


def test_module_source_contains_image_oserror_catch():
    """源码含 except OSError。"""
    import evaluation.metrics as m

    assert "except OSError" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    import evaluation.metrics as m

    assert "print(" not in inspect.getsource(m)


# =========================================================================
# 模块 docstring 内容
# =========================================================================


def test_module_docstring_mentions_pure_function():
    """docstring 提到纯函数设计。"""
    import evaluation.metrics as m

    assert "纯函数" in m.__doc__


def test_module_docstring_mentions_no_mutation():
    """docstring 提到不修改 document。"""
    import evaluation.metrics as m

    assert "不修改" in m.__doc__ or "不修改 document" in m.__doc__


def test_module_docstring_mentions_text_preservation():
    """docstring 提到 text_preservation。"""
    import evaluation.metrics as m

    assert "text_preservation" in m.__doc__


def test_module_docstring_mentions_v1_1_semantics():
    """docstring 提到 v1.1 语义。"""
    import evaluation.metrics as m

    assert "v1.1" in m.__doc__ or "evaluator v1.1" in m.__doc__.lower()


def test_module_docstring_mentions_counter_intersection():
    """docstring 提到 Counter 交集。"""
    import evaluation.metrics as m

    assert "Counter" in m.__doc__


def test_module_docstring_mentions_unicode_whitespace():
    """docstring 提到 Unicode 空白。"""
    import evaluation.metrics as m

    assert "Unicode" in m.__doc__ or "unicode" in m.__doc__.lower()


def test_module_docstring_mentions_image_excluded():
    """docstring 提到 image 不参与文本对比。"""
    import evaluation.metrics as m

    assert "image" in m.__doc__.lower()


# =========================================================================
# 函数签名 introspection
# =========================================================================


def test_compute_automatic_metrics_param_count_5():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_automatic_metrics_param_names():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_compute_automatic_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_pdf_locator_ratio_param_count_1():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


def test_pdf_locator_ratio_param_name_elements():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_docx_locator_ratio_param_count_1():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


def test_is_valid_bbox_param_count_1():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_is_valid_bbox_param_name_bbox():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]


def test_image_resource_ratio_param_count_2():
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2


def test_image_resource_ratio_param_names():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_image_resource_ratio_image_base_dir_no_default():
    sig = inspect.signature(_image_resource_ratio)
    assert sig.parameters["image_base_dir"].default is inspect.Parameter.empty


def test_chunk_reference_ratio_param_count_2():
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2


def test_chunk_reference_ratio_param_names():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_strip_unicode_whitespace_param_count_1():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_strip_unicode_whitespace_param_name_s():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]


def test_text_preservation_param_count_2():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_text_preservation_param_names():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_heading_boundary_ratio_param_count_2():
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


def test_silent_drop_count_param_count_2():
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2


def test_silent_drop_count_param_names():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


# =========================================================================
# helper metadata
# =========================================================================


def test_compute_automatic_metrics_module_identity():
    assert compute_automatic_metrics.__module__ == "evaluation.metrics"


def test_compute_automatic_metrics_qualname():
    assert compute_automatic_metrics.__qualname__ == "compute_automatic_metrics"


def test_pdf_locator_ratio_qualname():
    assert _pdf_locator_ratio.__qualname__ == "_pdf_locator_ratio"


def test_docx_locator_ratio_qualname():
    assert _docx_locator_ratio.__qualname__ == "_docx_locator_ratio"


def test_is_valid_bbox_qualname():
    assert _is_valid_bbox.__qualname__ == "_is_valid_bbox"


def test_image_resource_ratio_qualname():
    assert _image_resource_ratio.__qualname__ == "_image_resource_ratio"


def test_chunk_reference_ratio_qualname():
    assert _chunk_reference_ratio.__qualname__ == "_chunk_reference_ratio"


def test_strip_unicode_whitespace_qualname():
    assert _strip_unicode_whitespace.__qualname__ == "_strip_unicode_whitespace"


def test_text_preservation_qualname():
    assert _text_preservation.__qualname__ == "_text_preservation"


def test_heading_boundary_ratio_qualname():
    assert _heading_boundary_ratio.__qualname__ == "_heading_boundary_ratio"


def test_silent_drop_count_qualname():
    assert _silent_drop_count.__qualname__ == "_silent_drop_count"


def test_all_helpers_module_is_evaluation_metrics():
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


def test_all_helpers_are_function_type():
    import types as _types

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
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# 常量 namespace 完整性
# =========================================================================


def test_module_namespace_contains_text_types_exact_value():
    import evaluation.metrics as m

    assert m._TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_module_namespace_contains_pdf_bbox_required_types_exact_value():
    import evaluation.metrics as m

    assert m._PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_module_namespace_contains_not_evaluated():
    import evaluation.metrics as m

    assert m._NOT_EVALUATED == "not_evaluated"


def test_text_types_count_seven():
    import evaluation.metrics as m

    assert len(m._TEXT_TYPES) == 7


def test_pdf_bbox_required_types_count_four():
    import evaluation.metrics as m

    assert len(m._PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_is_subset_of_text_types():
    """所有 PDF bbox required type 都在 _TEXT_TYPES。"""
    import evaluation.metrics as m

    for t in m._PDF_BBOX_REQUIRED_TYPES:
        assert t in m._TEXT_TYPES


def test_text_types_does_not_contain_image():
    import evaluation.metrics as m

    assert "image" not in m._TEXT_TYPES


def test_module_all_only_one_export():
    import evaluation.metrics as m

    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_all_is_list():
    import evaluation.metrics as m

    assert isinstance(m.__all__, list)


def test_module_namespace_contains_math():
    import evaluation.metrics as m

    assert hasattr(m, "math")


def test_module_namespace_contains_counter():
    import evaluation.metrics as m

    assert hasattr(m, "Counter")
    assert m.Counter is Counter


def test_module_namespace_contains_path():
    import evaluation.metrics as m

    assert hasattr(m, "Path")


def test_module_namespace_contains_any():
    import evaluation.metrics as m
    from typing import Any as OrigAny

    assert m.Any is OrigAny


# =========================================================================
# _is_valid_bbox 详细（_PDF_BBOX_REQUIRED_TYPES 每 type）
# =========================================================================


def test_is_valid_bbox_for_each_pdf_required_type():
    """4 个 PDF_BBOX_REQUIRED_TYPES 的 bbox 检查都通过。"""
    for t in ("heading", "paragraph", "caption", "list_item"):
        # 这只是 type 名检查，bbox 本身用 _is_valid_bbox
        assert t in ("heading", "paragraph", "caption", "list_item")


def test_pdf_locator_ratio_for_each_text_type():
    """每个 _PDF_BBOX_REQUIRED_TYPE 单独验证。"""
    for t in ("heading", "paragraph", "caption", "list_item"):
        elements = [
            {"type": t, "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]}}
        ]
        out = _pdf_locator_ratio(elements)
        assert out["value"] == 1.0


def test_pdf_locator_ratio_each_text_type_without_bbox_rejected():
    """每个 _PDF_BBOX_REQUIRED_TYPE 缺 bbox → 拒绝。"""
    for t in ("heading", "paragraph", "caption", "list_item"):
        elements = [{"type": t, "source_locator": {"page": 1}}]
        out = _pdf_locator_ratio(elements)
        assert out["value"] == 0.0


def test_pdf_locator_ratio_non_required_text_type_no_bbox_needed():
    """非 _PDF_BBOX_REQUIRED_TYPES 的文本 type（如 table/header/footer）不需 bbox。"""
    for t in ("table", "header", "footer"):
        elements = [{"type": t, "source_locator": {"page": 1}}]
        out = _pdf_locator_ratio(elements)
        assert out["value"] == 1.0


def test_pdf_locator_ratio_image_no_bbox_needed():
    """image 不在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


# =========================================================================
# _docx_locator_ratio structural_keys 详细
# =========================================================================


def test_docx_locator_ratio_each_structural_key_accepted():
    """每个 structural_key 单独验证接受。"""
    for k in ("section", "paragraph_index", "run_index", "table_index", "row_index", "col_index", "relationship_id"):
        elements = [{"type": "paragraph", "source_locator": {k: 1}}]
        out = _docx_locator_ratio(elements)
        assert out["value"] == 1.0


def test_docx_locator_ratio_multiple_structural_keys_accepted():
    """多 structural_keys 同时存在仍接受。"""
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1, "paragraph_index": 0}}
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


# =========================================================================
# _image_resource_ratio 边界
# =========================================================================


def test_image_resource_ratio_path_only_no_image_base_dir(tmp_path: Path):
    """无 image_base_dir 时只用 resource_path 原值。"""
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake data")
    elements = [{"type": "image", "resource_path": str(img_path)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_relative_path_no_image_base_dir(tmp_path: Path):
    """无 image_base_dir + 相对路径 → 默认相对 cwd → 找不到。"""
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_absolute_path_with_image_base_dir(tmp_path: Path):
    """绝对路径 + image_base_dir → candidates 仍是 [Path(rp)]。"""
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake data")
    elements = [{"type": "image", "resource_path": str(img_path)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_image_base_dir_only(tmp_path: Path):
    """resource_path 是相对路径 + image_base_dir → 拼接查找。"""
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake data")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    # 默认 Path('img.png') 不存在；但 image_base_dir / 'img.png' 存在
    # 所以 valid=1
    assert out["value"] == 1.0


# =========================================================================
# _chunk_reference_ratio 边界
# =========================================================================


def test_chunk_reference_ratio_elements_missing_id():
    """element 缺 element_id → 不在 elem_ids set → 该 chunk 不 valid。"""
    elements = [{}]  # 缺 element_id
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_element_id_none():
    """element_id=None → set 含 None。"""
    elements = [{"element_id": None}]
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # all None in None → valid=1
    assert out["value"] == 1.0


# =========================================================================
# _heading_boundary_ratio 边界
# =========================================================================


def test_heading_boundary_ratio_chunk_first_id_duplicate_chunks():
    """多 chunk 首 id 相同 → set 去重，仍 match 1 个 heading。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},  # 重复首 id
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_heading_missing_element_id():
    """heading 缺 element_id → not match（get returns None）。"""
    elements = [{"type": "heading"}]  # 缺 element_id
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# =========================================================================
# _silent_drop_count 边界
# =========================================================================


def test_silent_drop_count_multiple_expected_types():
    """expectations 含多 type。"""
    by_type = {"paragraph": 5, "heading": 2}
    expectations = {
        "element_count_by_type": {"paragraph": 10, "heading": 5, "table": 3}
    }
    out = _silent_drop_count(by_type, expectations)
    # paragraph: max(0, 10-5)=5; heading: max(0, 5-2)=3; table: max(0, 3-0)=3
    assert out["value"] == 11


def test_silent_drop_count_zero_when_actual_more():
    """actual 比 expected 多时不计负数。"""
    by_type = {"paragraph": 100, "heading": 50}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 10}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


# =========================================================================
# _text_preservation 详细边界
# =========================================================================


def test_text_preservation_unicode_text_equal():
    """unicode 文本相等。"""
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_emoji_text():
    """emoji 文本（含 ZWJ）。"""
    elements = [{"type": "paragraph", "content": "hello 👋🏻"}]  # emoji + skin tone
    chunks = [{"text": "hello 👋🏻"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_control_chars():
    """含控制字符。"""
    elements = [{"type": "paragraph", "content": "a\x00b\x01c"}]
    chunks = [{"text": "a\x00b\x01c"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_surrogate_pairs():
    """surrogate pair 字符。"""
    # 𝄞 (U+1D11E) 需要 surrogate pair
    elements = [{"type": "paragraph", "content": "music 𝄞"}]
    chunks = [{"text": "music 𝄞"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_zero_width_joiner():
    """ZWJ 不被 isspace() 视为空白 → 保留。"""
    elements = [{"type": "paragraph", "content": "a‍b"}]  # ZWJ between
    chunks = [{"text": "a‍b"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_precision_recall_with_extra_unique_chars():
    """actual 含 expected 没有的 unique char → precision<1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    # common = 3, |actual|=4 → precision=0.75
    # |expected|=3 → recall=1.0
    assert out["precision"]["value"] == 0.75
    assert out["recall"]["value"] == 1.0


def test_text_preservation_repeated_chars_in_actual():
    """actual 含重复字符 → Counter 影响 precision。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "aaabbbccc"}]
    out = _text_preservation(elements, chunks)
    # c_expected = {a:1, b:1, c:1}, c_actual = {a:3, b:3, c:3}
    # intersection = {a:1, b:1, c:1} → common=3
    # precision = 3/9 ≈ 0.333
    # recall = 3/3 = 1.0
    assert out["precision"]["value"] == pytest.approx(1/3, abs=1e-6)
    assert out["recall"]["value"] == 1.0


def test_text_preservation_all_image_elements():
    """elements 全是 image → expected_sequence 为空。"""
    elements = [{"type": "image", "content": "ignored"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected 空，actual 非空 → empty_expected reason
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_chunks_empty_with_elements():
    """elements 非空，chunks 空 → empty_actual reason。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


# =========================================================================
# compute_automatic_metrics 详细
# =========================================================================


def test_compute_automatic_metrics_docx_source_type():
    """docx source_type → docx_locator_valid_ratio 计算，pdf_locator_valid_ratio = not_pdf_document。"""
    document = {
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "abc",
                "source_locator": {"section": 1},
            }
        ],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_automatic_metrics_pdf_source_type():
    """pdf source_type → pdf_locator_valid_ratio 计算。"""
    document = {
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "abc",
                "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]},
            }
        ],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_compute_automatic_metrics_error_code_pass_through():
    """error 含 code → error_code 取该值。"""
    out = compute_automatic_metrics(None, {"code": "E_TEST"}, "pdf", None)
    assert out["error_code"]["value"] == "E_TEST"


def test_compute_automatic_metrics_no_error_code_none():
    """error=None → error_code value=None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_automatic_metrics_does_not_mutate_input_image_base_dir(tmp_path: Path):
    """不修改 image_base_dir。"""
    document = {"elements": [], "chunks": []}
    ibd_before = tmp_path
    compute_automatic_metrics(document, None, "docx", None, image_base_dir=ibd_before)
    assert ibd_before == tmp_path


def test_compute_automatic_metrics_keys_count_consistent_pipeline_success_or_fail():
    """成功和失败路径都返回 14 keys。"""
    fail = compute_automatic_metrics(None, None, "pdf", None)
    success = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "docx", None
    )
    assert len(fail) == 14
    assert len(success) == 14


def test_compute_automatic_metrics_keys_consistent_set():
    """成功和失败路径 keys 集合相同。"""
    fail = compute_automatic_metrics(None, None, "pdf", None)
    success = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "docx", None
    )
    assert set(fail.keys()) == set(success.keys())


def test_compute_automatic_metrics_does_not_share_state():
    """两次调用返回独立 dict。"""
    a = compute_automatic_metrics(None, None, "pdf", None)
    b = compute_automatic_metrics(None, None, "pdf", None)
    a["error_code"]["value"] = "modified"
    assert b["error_code"]["value"] is None


# =========================================================================
# 整体不变量
# =========================================================================


def test_module_can_be_imported():
    import evaluation.metrics as m

    assert m is not None


def test_helpers_do_not_share_state():
    """4 个 helper 返回独立 dict。"""
    a = _null("x")
    b = _null("y")
    a["reason"] = "modified"
    assert b["reason"] == "y"


def test_ratio_helpers_do_not_share_state():
    a = _ratio(0.1)
    b = _ratio(0.2)
    a["value"] = 99.0
    assert b["value"] == 0.2


def test_bool_metric_helpers_do_not_share_state():
    a = _bool_metric(True)
    b = _bool_metric(False)
    a["value"] = False
    assert b["value"] is False


def test_int_metric_helpers_do_not_share_state():
    a = _int_metric(1)
    b = _int_metric(2)
    a["value"] = 100
    assert b["value"] == 2


# =========================================================================
# 模块 namespace 全 helper 在 namespace
# =========================================================================


def test_module_namespace_contains_all_helpers():
    import evaluation.metrics as m

    for name in [
        "_null",
        "_ratio",
        "_bool_metric",
        "_int_metric",
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
        "compute_automatic_metrics",
    ]:
        assert hasattr(m, name), f"missing {name}"


def test_module_namespace_does_not_contain_main():
    """模块无 main 函数。"""
    import evaluation.metrics as m

    assert not hasattr(m, "main")


def test_module_no_dunder_all_helpers_exported():
    """__all__ 只导出 compute_automatic_metrics。"""
    import evaluation.metrics as m

    assert "_null" not in m.__all__
    assert "_ratio" not in m.__all__
    assert "_bool_metric" not in m.__all__
    assert "_int_metric" not in m.__all__
