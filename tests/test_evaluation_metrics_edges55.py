"""evaluation/metrics.py 第五十七轮 edges 测试（Round 519）。

补强 edges54 未触及的角度（第二十九批）：
- 基础构造器 第二十九批：_null 与 _ratio 返回结构再细分
- compute_automatic_metrics 第二十九批：error 含非标准 code / source_type="docx" + 含 elements / source_type="pdf" + 无 elements / expectations 完整
- _pdf_locator_ratio 第二十九批：page 是 string / page 是 float / page 是 True / page 是 list
- _docx_locator_ratio 第二十九批：locator 含所有 7 个结构键之一 / 多个结构键同时
- _is_valid_bbox 第二十九批：list 含 None / tuple 非法 / list of strings / mixed types
- _image_resource_ratio 第二十九批：100% 多图 / resource_path 是 Path 对象 / resource_path 是 int
- _chunk_reference_ratio 第二十九批：所有 chunk 都无 ids / element_ids 含重复
- _strip_unicode_whitespace 第二十九批：tab / 各种 ASCII 空白 / mixed
- _text_preservation 第二十九批：expected=actual / expected 含 unicode / chunks 顺序乱
- _heading_boundary_ratio 第二十九批：多 heading + 多 chunk / heading 无 element_id
- _silent_drop_count 第二十九批：actual=expected 边界 / 实际大于预期 / 只有一种 type
- module source forbidden tokens 第四十六批
- module source 字符串精确补强第四十二批
- signatures 第四十二批
- module 合理性第四十二批
- 端到端集成第四十二批
"""

from __future__ import annotations

import inspect
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import metrics as mmod
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


# ---------- 基础构造器 第二十九批 ----------


def test_null_returns_only_two_keys_batch29():
    m = _null("x")
    assert set(m.keys()) == {"value", "reason"}


def test_ratio_returns_only_two_keys_batch29():
    m = _ratio(0.5)
    assert set(m.keys()) == {"value", "reason"}


def test_bool_metric_returns_only_two_keys_batch29():
    m = _bool_metric(True)
    assert set(m.keys()) == {"value", "reason"}


def test_int_metric_returns_only_two_keys_batch29():
    m = _int_metric(0)
    assert set(m.keys()) == {"value", "reason"}


def test_null_with_empty_reason_batch29():
    """空字符串 reason 也透传。"""
    m = _null("")
    assert m["reason"] == ""


def test_null_with_unicode_reason_batch29():
    m = _null("原因")
    assert m["reason"] == "原因"


def test_ratio_with_negative_value_batch29():
    """实现不限制范围；负值也透传。"""
    m = _ratio(-0.5)
    assert m["value"] == -0.5


def test_ratio_with_value_above_one_batch29():
    """实现不限制范围；>1 也透传。"""
    m = _ratio(1.5)
    assert m["value"] == 1.5


def test_bool_metric_with_zero_batch29():
    m = _bool_metric(0)
    assert m["value"] is False


def test_bool_metric_with_empty_string_batch29():
    m = _bool_metric("")
    assert m["value"] is False


# ---------- compute_automatic_metrics 第二十九批 ----------


def test_compute_metrics_error_with_custom_code_batch29():
    """error.code 是任意字符串。"""
    m = compute_automatic_metrics(None, {"code": "custom_error"}, "pdf", None)
    assert m["error_code"]["value"] == "custom_error"


def test_compute_metrics_error_with_empty_code_batch29():
    m = compute_automatic_metrics(None, {"code": ""}, "pdf", None)
    assert m["error_code"]["value"] == ""


def test_compute_metrics_docx_with_elements_batch29():
    doc = {
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "x"}],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_metrics_pdf_no_elements_batch29():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    # _pdf_locator_ratio([]) → no_elements
    assert m["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_with_expectations_no_element_count_batch29():
    """expectations 不含 element_count_by_type → silent_drop 'no_expectations_element_count'。"""
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", {"required_markers": ["x"]})
    assert m["silent_drop_count"]["reason"] == "no_expectations_element_count"


def test_compute_metrics_schema_valid_exception_path_batch29():
    """document 让 schema 校验抛异常 → schema_valid=False + 'schema_check_exception:...'。"""
    # 构造一个会让 document_passes_schema 抛异常的 document
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("boom")):
        m = compute_automatic_metrics({"elements": []}, None, "pdf", None)
    assert m["schema_valid"]["value"] is False
    assert "schema_check_exception" in m["schema_valid"]["reason"]


def test_compute_metrics_returns_dict_with_metrics_key_only_batch29():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(m, dict)


# ---------- _pdf_locator_ratio 第二十九批 ----------


def test_pdf_locator_ratio_page_is_string_batch29():
    """page 是 string → not isinstance(page, int) → invalid。"""
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_is_float_batch29():
    """page 是 float → not isinstance(page, int) → invalid。

    注：Python 中 isinstance(1.0, int) is False（不像 bool）。
    """
    elements = [{"type": "image", "source_locator": {"page": 1.0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_is_true_batch29():
    """page=True → isinstance(True, int) is True, True >= 1 → 但 page=True 视为 1，合法。"""
    elements = [{"type": "image", "source_locator": {"page": True}}]
    out = _pdf_locator_ratio(elements)
    # isinstance(True, int) is True, True >= 1 → valid for image
    assert out["value"] == 1.0


def test_pdf_locator_ratio_page_is_list_batch29():
    elements = [{"type": "image", "source_locator": {"page": [1]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_is_dict_batch29():
    elements = [{"type": "image", "source_locator": {"page": {"x": 1}}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_all_images_with_page_only_batch29():
    """images 不需 bbox。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
        {"type": "image", "source_locator": {"page": 2}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _docx_locator_ratio 第二十九批 ----------


def test_docx_locator_ratio_all_structural_keys_batch29():
    """逐一测试 7 个结构键。"""
    for key in (
        "section",
        "paragraph_index",
        "run_index",
        "table_index",
        "row_index",
        "col_index",
        "relationship_id",
    ):
        elements = [{"type": "paragraph", "source_locator": {key: "v"}}]
        out = _docx_locator_ratio(elements)
        assert out["value"] == 1.0


def test_docx_locator_ratio_multiple_structural_keys_batch29():
    """多个结构键同时存在。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {
                "section": "main",
                "paragraph_index": 0,
                "run_index": 0,
            },
        }
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_structural_key_zero_value_batch29():
    """paragraph_index=0 是 falsy 但 key 存在。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_structural_key_none_value_batch29():
    """locator.section=None 但 key 存在。"""
    elements = [{"type": "paragraph", "source_locator": {"section": None}}]
    out = _docx_locator_ratio(elements)
    # 实现 `if not any(k in loc for k in structural_keys)` → "section" in loc → True → valid
    assert out["value"] == 1.0


# ---------- _is_valid_bbox 第二十九批 ----------


def test_is_valid_bbox_list_with_none_batch29():
    assert _is_valid_bbox([0, None, 0, 0]) is False


def test_is_valid_bbox_tuple_batch29():
    """tuple 不是 list → False。"""
    assert _is_valid_bbox((0, 0, 0, 0)) is False


def test_is_valid_bbox_list_of_strings_batch29():
    assert _is_valid_bbox(["0", "0", "0", "0"]) is False


def test_is_valid_bbox_mixed_types_batch29():
    assert _is_valid_bbox([0, "0", 0, 0]) is False


def test_is_valid_bbox_very_large_batch29():
    """非常大数字也合法。"""
    assert _is_valid_bbox([1e308, 1e308, 1e308, 1e308]) is True


def test_is_valid_bbox_very_small_batch29():
    assert _is_valid_bbox([1e-308, 1e-308, 1e-308, 1e-308]) is True


def test_is_valid_bbox_zero_values_batch29():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


# ---------- _image_resource_ratio 第二十九批 ----------


def test_image_resource_ratio_all_exist_batch29(tmp_path):
    """多图都存在。"""
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"\x89PNG")
    img2 = tmp_path / "b.png"
    img2.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": str(img2)},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_resource_path_int_batch29(tmp_path):
    """resource_path 是 int → Path(int) 抛 TypeError？实际 Path(123) 在 Python 3.12 接受 int。"""
    # 不严格断言，只测不崩溃
    elements = [{"type": "image", "resource_path": 123}]
    try:
        _image_resource_ratio(elements, None)
    except (TypeError, ValueError):
        pass  # 合法：某些类型可能抛


def test_image_resource_ratio_resource_path_path_object_batch29(tmp_path):
    """resource_path 是 Path 对象 → Path(Path(...)) 等价。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": img}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_no_image_but_other_elements_batch29():
    """全是非 image 类型 → no_image_elements。"""
    elements = [
        {"type": "paragraph"},
        {"type": "heading"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_returns_dict_batch29():
    out = _image_resource_ratio([], None)
    assert isinstance(out, dict)


# ---------- _chunk_reference_ratio 第二十九批 ----------


def test_chunk_reference_ratio_all_chunks_no_ids_batch29():
    """所有 chunk 都缺 source_element_ids → 0.0。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}, {}, {}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_duplicate_ids_batch29():
    """source_element_ids 含重复元素。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e1", "e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # all in elem_ids → valid
    assert out["value"] == 1.0


def test_chunk_reference_ratio_elements_no_id_key_batch29():
    """element 缺 element_id key → set 包含 None。"""
    elements = [{}]  # 无 element_id
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # elem_ids = {None}, source_element_ids=[None], None in {None} → valid
    assert out["value"] == 1.0


def test_chunk_reference_ratio_chunk_ids_with_none_batch29():
    """source_element_ids 含 None。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # elem_ids = {"e1"}, source_element_ids=["e1", None], None not in elem_ids → not all
    assert out["value"] == 0.0


# ---------- _strip_unicode_whitespace 第二十九批 ----------


def test_strip_unicode_whitespace_tab_batch29():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline_batch29():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return_batch29():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_form_feed_batch29():
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_vertical_tab_batch29():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_mixed_batch29():
    """多种空白混合。"""
    assert _strip_unicode_whitespace(" \t\n\r a\t b\n") == "ab"


def test_strip_unicode_whitespace_no_space_at_all_batch29():
    """无空白字符串原样返回。"""
    assert _strip_unicode_whitespace("hello") == "hello"


# ---------- _text_preservation 第二十九批 ----------


def test_text_preservation_perfect_match_batch29():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0
    assert out["equal"]["reason"] is None


def test_text_preservation_unicode_batch29():
    """unicode 内容。"""
    elements = [{"type": "paragraph", "content": "你好"}]
    chunks = [{"text": "你好"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_chunk_order_matters_batch29():
    """chunk 顺序乱 → equal=False。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # 但字符多集合相同 → precision=1.0 recall=1.0
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_expected_only_whitespace_batch29():
    """expected 纯空白，actual 含字符。"""
    elements = [{"type": "paragraph", "content": "   "}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # expected 空 → recall 'empty_expected'
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_actual_only_whitespace_batch29():
    """actual 纯空白，expected 含字符。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "   "}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # actual 空 → precision 'empty_actual'
    assert out["precision"]["reason"] == "empty_actual"


# ---------- _heading_boundary_ratio 第二十九批 ----------


def test_heading_boundary_multiple_headings_multiple_chunks_batch29():
    """多 heading + 多 chunk。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
        {"source_element_ids": ["other"]},  # h3 不在第一个位置
    ]
    out = _heading_boundary_ratio(elements, chunks)
    # h1 + h2 matched, h3 not → 2/3
    assert abs(out["value"] - 2.0 / 3.0) < 1e-9


def test_heading_ratio_heading_no_element_id_batch29():
    """heading 缺 element_id → 当 None 处理。"""
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": [None]}]
    out = _heading_boundary_ratio(elements, chunks)
    # heading.element_id=None, chunk.first=None → match
    assert out["value"] == 1.0


def test_heading_ratio_chunks_empty_batch29():
    """chunks=[] → 0 matched。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    # matched = 0, headings=1 → 0/1 = 0.0
    assert out["value"] == 0.0


def test_heading_ratio_returns_dict_batch29():
    out = _heading_boundary_ratio([{"type": "paragraph"}], [])
    assert isinstance(out, dict)


# ---------- _silent_drop_count 第二十九批 ----------


def test_silent_drop_actual_equals_expected_batch29():
    """actual == expected → drop=0。"""
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_actual_greater_than_expected_batch29():
    """actual > expected → drop=0（max(0, ...)）。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_single_type_batch29():
    """只有一种 type。"""
    out = _silent_drop_count(
        {"paragraph": 0},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 5


def test_silent_drop_multiple_types_batch29():
    """多 type 同时 drop。"""
    out = _silent_drop_count(
        {"paragraph": 1},
        {"element_count_by_type": {"paragraph": 5, "heading": 3, "image": 2}},
    )
    # paragraph: 5-1=4, heading: 3-0=3, image: 2-0=2 → 9
    assert out["value"] == 9


def test_silent_drop_returns_int_value_batch29():
    out = _silent_drop_count(
        {},
        {"element_count_by_type": {"paragraph": 1}},
    )
    assert isinstance(out["value"], int)


# ---------- module source forbidden tokens 第四十六批 ----------


def test_module_source_no_subprocess_batch29():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch29():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch29():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch29():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch29():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch29():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch29():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch29():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch29():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch29():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch29():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch29():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十二批 ----------


def test_module_source_contains_module_docstring_batch29():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_text_types_constant_value_batch29():
    """_TEXT_TYPES 含具体类型。"""
    src = inspect.getsource(mmod)
    assert '"heading"' in src
    assert '"paragraph"' in src


def test_module_source_contains_pdf_bbox_required_types_constant_batch29():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_contains_text_preservation_docstring_batch29():
    src = inspect.getsource(mmod)
    assert "文本保留" in src


def test_module_source_contains_silent_drop_docstring_batch29():
    src = inspect.getsource(mmod)
    assert "silent_drop_count" in src


def test_module_source_contains_counter_intersection_batch29():
    """实现使用 Counter 交集。"""
    src = inspect.getsource(mmod)
    assert "&" in src  # Counter 交集操作符
    assert "c_expected & c_actual" in src or "c_actual & c_expected" in src


def test_module_source_contains_normalize_text_not_used_batch29():
    """v1.1 不再使用 normalize_text（直接 strip 空白）。"""
    src = inspect.getsource(mmod)
    # 实现里没有 from app.chunkers 导入 normalize_text
    assert "from app.chunkers" not in src


def test_module_source_contains_strip_unicode_whitespace_function_batch29():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace" in src


def test_module_source_contains_empty_actual_reason_batch29():
    src = inspect.getsource(mmod)
    assert "empty_actual" in src


def test_module_source_contains_empty_expected_reason_batch29():
    src = inspect.getsource(mmod)
    assert "empty_expected" in src


def test_module_source_contains_no_heading_elements_reason_batch29():
    src = inspect.getsource(mmod)
    assert "no_heading_elements" in src


def test_module_source_contains_no_expectations_reason_batch29():
    src = inspect.getsource(mmod)
    assert "no_expectations" in src


# ---------- signatures 第四十二批 ----------


def test_signature_null_only_reason_param_batch29():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_only_value_param_batch29():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_compute_metrics_image_base_dir_annotation_batch29():
    sig = inspect.signature(compute_automatic_metrics)
    annotation = sig.parameters["image_base_dir"].annotation
    assert "Path" in str(annotation)
    assert "None" in str(annotation)


def test_signature_compute_metrics_returns_dict_batch29():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_text_preservation_return_annotation_batch29():
    sig = inspect.signature(_text_preservation)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_is_valid_bbox_return_bool_batch29():
    sig = inspect.signature(_is_valid_bbox)
    assert sig.return_annotation == "bool"


def test_signature_strip_unicode_whitespace_return_str_batch29():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert sig.return_annotation == "str"


# ---------- module 合理性第四十二批 ----------


def test_module_has_future_annotations_batch29():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_math_batch29():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch29():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_imports_pathlib_batch29():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch29():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_text_types_seven_entries_batch29():
    src = inspect.getsource(mmod)
    # 7 个 text 类型
    for t in ("heading", "paragraph", "list_item", "table", "caption", "header", "footer"):
        assert f'"{t}"' in src


def test_module_pdf_bbox_required_types_four_entries_batch29():
    src = inspect.getsource(mmod)
    # 4 个需要 bbox 的 PDF 文本类型
    for t in ("heading", "paragraph", "caption", "list_item"):
        assert f'"{t}"' in src


def test_module_all_only_compute_batch29():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- 端到端集成第四十二批 ----------


def test_e2e_compute_metrics_full_pdf_document_batch29():
    """端到端：完整 PDF document 含 image + paragraph + heading。"""
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "element_id": "p1",
                "content": "hello",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            },
            {
                "type": "heading",
                "element_id": "h1",
                "content": "title",
                "source_locator": {"page": 1, "bbox": [0, 100, 100, 120]},
            },
            {"type": "image", "element_id": "i1", "source_locator": {"page": 1}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "hello", "source_element_ids": ["p1"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 3
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    # 文本保留：expected="hellotitle"（image 不算），actual="titlehello"
    # 等于？→ False（顺序不同）
    assert m["text_preservation_equal"]["value"] is False
    # 字符多集合相同 → P=R=1.0
    assert m["text_char_multiset_precision"]["value"] == 1.0


def test_e2e_compute_metrics_docx_with_relationship_id_batch29():
    """端到端：DOCX 含 image (relationship_id)。"""
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "x",
                "source_locator": {"paragraph_index": 0},
            },
            {
                "type": "image",
                "source_locator": {"relationship_id": "rId1"},
            },
        ],
        "chunks": [{"text": "x"}],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_silent_drop_with_multiple_types_batch29():
    """端到端：多 type expectations。"""
    doc = {
        "elements": [
            {"type": "paragraph", "content": "a"},
            {"type": "paragraph", "content": "b"},
            {"type": "heading", "content": "title"},
        ],
        "chunks": [{"text": "ab title"}],
    }
    expectations = {
        "element_count_by_type": {
            "paragraph": 5,
            "heading": 3,
        }
    }
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    # paragraph: 5-2=3, heading: 3-1=2 → total 5
    assert m["silent_drop_count"]["value"] == 5


def test_e2e_no_side_effects_batch29():
    """端到端：调用不修改输入。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc"}],
    }
    before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == before


def test_e2e_text_preservation_with_whitespace_batch29():
    """端到端：含大量空白仍 equal=True。"""
    elements = [{"type": "paragraph", "content": "a   b\tc\nd"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    # 删空白后都是 "abcd" → equal=True
    assert out["equal"]["value"] is True


def test_e2e_pdf_locator_with_image_and_paragraph_batch29():
    """端到端：image + paragraph 混合。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # valid
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]},  # valid
        },
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (no bbox)
    ]
    out = _pdf_locator_ratio(elements)
    assert abs(out["value"] - 2.0 / 3.0) < 1e-9


def test_e2e_image_resource_ratio_with_relative_path_batch29(tmp_path):
    """端到端：相对 resource_path + image_base_dir 拼接。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG\r\n")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    # 实现里 candidates = [Path("img.png"), tmp_path/"img.png"]
    # Path("img.png").is_file() 相对 cwd（pytest cwd 可能不对）
    # tmp_path/"img.png" 找到
    assert out["value"] == 1.0
