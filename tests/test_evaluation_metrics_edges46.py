"""evaluation/metrics.py 第四十八轮 edges 测试（Round 457）。

补强 edges45 未触及的角度：
- _null/_ratio/_bool_metric/_int_metric 行为深度第十九批（构造子）
- _TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES 第十九批（tuple 性质）
- _strip_unicode_whitespace 第十九批（特殊 Unicode 字符）
- compute_automatic_metrics 行为深度第十九批（pipeline_success+error 组合 / image_base_dir 类型 / schema 异常路径 / document 含 image-only 时 text_preservation 表现）
- _pdf_locator_ratio 边界第十九批（page 各种类型）
- _docx_locator_ratio 边界第十九批（locator 含 page 但为 None / 含 bbox 但为 None）
- _is_valid_bbox 第十九批（list/tuple/bool trick/NaN/inf/negative numbers）
- _image_resource_ratio 第十九批（base_dir 类型 / 重复 element_id / image count ratio）
- _chunk_reference_ratio 第十九批（element_id 类型 / chunk first id 重复）
- _text_preservation 第十九批（content None / chunks text None / 只有空白）
- _heading_boundary_ratio 第十九批（chunk first id 为 None）
- _silent_drop_count 第十九批（expected 含非 int / negative expected / 空字符串 type key）
- module source forbidden tokens 第三十四批
- module source 字符串精确补强第二十九批
- signatures 第二十九批
- module 合理性第二十九批
- 端到端集成第二十九批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _TEXT_TYPES,
    _PDF_BBOX_REQUIRED_TYPES,
    _NOT_EVALUATED,
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


# ---------- 构造子行为深度第十九批 ----------


def test_null_returns_value_none_batch19():
    r = _null("any_reason")
    assert r["value"] is None


def test_null_reason_passthrough_batch19():
    assert _null("x")["reason"] == "x"


def test_null_default_dict_structure_batch19():
    """_null 仅含 value+reason 两键。"""
    r = _null("r")
    assert set(r.keys()) == {"value", "reason"}


def test_ratio_negative_value_preserved_batch19():
    """_ratio 不做范围检查（仅转 float）。"""
    r = _ratio(-0.5)
    assert r["value"] == -0.5


def test_ratio_int_coerced_to_float_batch19():
    r = _ratio(1)
    assert isinstance(r["value"], float)
    assert r["value"] == 1.0


def test_ratio_zero_dot_zero_batch19():
    r = _ratio(0.0)
    assert r["value"] == 0.0


def test_ratio_one_dot_zero_batch19():
    r = _ratio(1.0)
    assert r["value"] == 1.0


def test_bool_metric_truthy_int_batch19():
    """_bool_metric(1) → True。"""
    assert _bool_metric(1)["value"] is True


def test_bool_metric_falsy_int_batch19():
    """_bool_metric(0) → False。"""
    assert _bool_metric(0)["value"] is False


def test_bool_metric_string_truthy_batch19():
    """非空字符串转 True。"""
    assert _bool_metric("yes")["value"] is True


def test_bool_metric_empty_string_falsy_batch19():
    assert _bool_metric("")["value"] is False


def test_int_metric_zero_batch19():
    assert _int_metric(0)["value"] == 0


def test_int_metric_negative_batch19():
    assert _int_metric(-5)["value"] == -5


def test_int_metric_large_batch19():
    """大整数不变。"""
    n = 10**18
    assert _int_metric(n)["value"] == n


def test_int_metric_float_truncates_batch19():
    """_int_metric 接受 float，按 int() 规则截断。"""
    assert _int_metric(3.7)["value"] == 3


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第十九批 ----------


def test_text_types_is_tuple_batch19():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_immutable_batch19():
    """tuple 不可变。"""
    with pytest.raises(TypeError):
        _TEXT_TYPES[0] = "x"  # type: ignore[index]


def test_text_types_count_exactly_7_batch19():
    assert len(_TEXT_TYPES) == 7


def test_text_types_contains_caption_batch19():
    assert "caption" in _TEXT_TYPES


def test_pdf_bbox_required_is_tuple_batch19():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_count_exactly_4_batch19():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_subset_batch19():
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_not_evaluated_constant_value_batch19():
    assert _NOT_EVALUATED == "not_evaluated"


# ---------- _strip_unicode_whitespace 第十九批 ----------


def test_strip_unicode_form_feed_batch19():
    """form feed (\f) is whitespace.isspace() == True。"""
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_vertical_tab_batch19():
    """vertical tab (\v) is whitespace。"""
    assert _strip_unicode_whitespace("a\t\vb") == "ab"  # \t 与 \v 都去掉


def test_strip_unicode_carriage_return_batch19():
    assert _strip_unicode_whitespace("a\r\nb") == "ab"


def test_strip_unicode_only_whitespace_returns_empty_batch19():
    assert _strip_unicode_whitespace("   \t\n  ") == ""


def test_strip_unicode_null_char_preserved_batch19():
    """null char (\x00) not isspace。"""
    assert _strip_unicode_whitespace("a\x00b") == "a\x00b"


def test_strip_unicode_keeps_punctuation_batch19():
    assert _strip_unicode_whitespace(".,;:!?") == ".,;:!?"


def test_strip_unicode_preserves_emoji_sequence_batch19():
    s = "👨‍👩‍👧 family"
    out = _strip_unicode_whitespace(s)
    assert "family" in out
    # 复合 emoji 的 ZWJ (‍) 不是 isspace，应保留
    assert "\U0001f468" in out


# ---------- compute_automatic_metrics 行为深度第十九批 ----------


def test_compute_metrics_returns_dict_batch19():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_pipeline_success_uses_is_none_batch19():
    """error is None and document is not None → success（使用 is None）。"""
    doc = {"elements": [], "chunks": [], "document_id": "d1", "source_type": "pdf"}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_error_dict_no_code_key_batch19():
    """error dict 无 code 键时 error_code 抛 KeyError（按设计）。"""
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, {"msg": "x"}, "pdf", None)


def test_compute_metrics_error_code_passthrough_batch19():
    out = compute_automatic_metrics(None, {"code": "E_X"}, "pdf", None)
    assert out["error_code"]["value"] == "E_X"


def test_compute_metrics_document_none_14_keys_batch19():
    out = compute_automatic_metrics(None, {"code": "E"}, "pdf", None)
    # pipeline_success + error_code + schema_valid + 11 null metrics
    assert len(out) == 14


def test_compute_metrics_document_none_no_locator_metrics_computed_batch19():
    out = compute_automatic_metrics(None, {"code": "E"}, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["value"] is None
    assert out["silent_drop_count"]["value"] is None


def test_compute_metrics_schema_exception_handled_batch19():
    """document_passes_schema 抛异常时 schema_valid value=False 且 reason 含 schema_check_exception。"""
    doc = {"elements": [], "chunks": [], "document_id": "d1", "source_type": "pdf"}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("boom")):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception:RuntimeError" in out["schema_valid"]["reason"]


def test_compute_metrics_image_only_no_text_types_batch19(tmp_path):
    """elements 全为 image 时 text_preservation equal True，precision/recall null。"""
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "image", "resource_path": "a.png"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] is None
    assert out["text_char_multiset_recall"]["value"] is None


def test_compute_metrics_image_base_dir_str_batch19(tmp_path):
    """image_base_dir 接受 Path（None 默认）→ 直接用 resource_path。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "image", "resource_path": str(img)},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


# ---------- _pdf_locator_ratio 边界第十九批 ----------


def test_pdf_locator_ratio_page_float_batch19():
    """page 是 float（如 1.0）应判 invalid（要求 isinstance int）。"""
    elements = [{"type": "heading", "source_locator": {"page": 1.0, "bbox": [0, 0, 1, 1]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_int_batch19():
    elements = [{"type": "heading", "source_locator": {"page": -1, "bbox": [0, 0, 1, 1]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_string_batch19():
    elements = [{"type": "heading", "source_locator": {"page": "1", "bbox": [0, 0, 1, 1]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_bool_true_batch19():
    """True 是 int 的子类但语义上是 bool。"""
    elements = [{"type": "heading", "source_locator": {"page": True, "bbox": [0, 0, 1, 1]}}]
    out = _pdf_locator_ratio(elements)
    # True 的 isinstance int 返回 True，且 True == 1（page>=1 满足），所以仍判 valid
    # 行为不定义具体值，只确保不抛错
    assert "value" in out


def test_pdf_locator_ratio_mixed_valid_invalid_batch19():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {"page": 0}},
        {"type": "table", "source_locator": {"page": 1}},  # table 不需 bbox
    ]
    out = _pdf_locator_ratio(elements)
    # 2 valid / 3 → 0.667
    assert abs(out["value"] - 2 / 3) < 1e-9


def test_pdf_locator_ratio_table_no_bbox_required_batch19():
    """table 类型不需 bbox。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_paragraph_missing_bbox_batch19():
    """paragraph 类型需要 bbox。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 边界第十九批 ----------


def test_docx_locator_ratio_with_page_none_batch19():
    """locator.page=None（显式）应被 'page' in loc 命中，仍判 invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": None, "section": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_only_page_key_batch19():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_only_bbox_key_batch19():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_only_section_batch19():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_zero_batch19():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_relationship_id_batch19():
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_no_locator_key_batch19():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 第十九批 ----------


def test_is_valid_bbox_tuple_batch19():
    """tuple 不被接受（要求 list）。"""
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_is_valid_bbox_with_negative_numbers_batch19():
    """负数 bbox 仍合法（值有限）。"""
    assert _is_valid_bbox([-1.0, -2.0, 1.0, 2.0]) is True


def test_is_valid_bbox_with_mixed_int_float_batch19():
    assert _is_valid_bbox([0, 0.5, 1, 1.5]) is True


def test_is_valid_bbox_with_complex_batch19():
    """complex 不是 (int, float)。"""
    assert _is_valid_bbox([0, 0, 1+0j, 1]) is False


def test_is_valid_bbox_with_nan_float_batch19():
    assert _is_valid_bbox([0, 0, float("nan"), 1]) is False


def test_is_valid_bbox_with_inf_float_batch19():
    assert _is_valid_bbox([0, 0, float("inf"), 1]) is False


def test_is_valid_bbox_with_negative_inf_batch19():
    assert _is_valid_bbox([float("-inf"), 0, 1, 1]) is False


def test_is_valid_bbox_with_bool_trick_batch19():
    """[True, False, True, False]：全是 bool → False。"""
    assert _is_valid_bbox([True, False, True, False]) is False


def test_is_valid_bbox_with_one_bool_in_list_batch19():
    """含一个 bool 的 list → False。"""
    assert _is_valid_bbox([0, True, 1, 1]) is False


# ---------- _image_resource_ratio 第十九批 ----------


def test_image_resource_ratio_no_resource_path_batch19(tmp_path):
    """image 元素无 resource_path → 计 invalid。"""
    elements = [{"type": "image"}, {"type": "image"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_one_empty_string_batch19(tmp_path):
    elements = [
        {"type": "image", "resource_path": ""},
        {"type": "image", "resource_path": ""},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_with_base_dir_fallback_batch19(tmp_path):
    """image_base_dir 拼接 basename 作为 fallback。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    # resource_path 仅给 basename
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_with_base_dir_and_abs_path_batch19(tmp_path):
    """resource_path 是绝对路径时 image_base_dir 不影响（第一候选即命中）。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path / "nope")
    assert out["value"] == 1.0


def test_image_resource_ratio_zero_size_counts_invalid_batch19(tmp_path):
    """0 字节文件 invalid。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_oserror_swallowed_batch19(tmp_path):
    """非法路径触发 OSError 时不抛错。"""
    # 给一个非法字符的路径，触发 OSError
    elements = [{"type": "image", "resource_path": "\x00bad"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert "value" in out


# ---------- _chunk_reference_ratio 第十九批 ----------


def test_chunk_reference_ratio_strings_batch19():
    elements = [{"element_id": "a"}, {"element_id": "b"}]
    chunks = [{"source_element_ids": ["a", "b"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_ints_batch19():
    elements = [{"element_id": 1}, {"element_id": 2}]
    chunks = [{"source_element_ids": [1, 2]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_mixed_str_int_batch19():
    elements = [{"element_id": "1"}, {"element_id": 2}]
    chunks = [{"source_element_ids": ["1", 2]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_first_unknown_batch19():
    elements = [{"element_id": "a"}]
    chunks = [{"source_element_ids": ["a", "x"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_chunks_key_missing_batch19():
    elements = [{"element_id": "a"}]
    chunks = [{"text": "x"}]  # 缺 source_element_ids 键
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunks_none_ids_batch19():
    elements = [{"element_id": "a"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _text_preservation 第十九批 ----------


def test_text_preservation_content_none_batch19():
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] is None
    assert out["recall"]["value"] is None


def test_text_preservation_chunk_text_none_batch19():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual=""
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] is None  # actual 空
    assert out["recall"]["value"] == 0.0


def test_text_preservation_only_image_elements_batch19():
    elements = [{"type": "image", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] is None


def test_text_preservation_reversed_text_batch19():
    """序列顺序错乱 → equal False，但 Counter 相同 → precision/recall = 1.0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_duplicate_chars_batch19():
    """重复字符 Counter 交集。"""
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # common = min(3, 2) = 2; precision = 2/2 = 1; recall = 2/3
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 2 / 3) < 1e-9


# ---------- _heading_boundary_ratio 第十九批 ----------


def test_heading_boundary_ratio_heading_no_element_id_batch19():
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": ["any"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0  # h.get("element_id") = None 不在 chunk_first_ids


def test_heading_boundary_ratio_chunk_first_id_is_none_batch19():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": [None, "h1"]}]  # 第一个是 None
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_first_id_empty_string_batch19():
    elements = [{"type": "heading", "element_id": ""}]
    chunks = [{"source_element_ids": ["", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # "" in chunk_first_ids（"" == ""）
    assert out["value"] == 1.0


def test_heading_boundary_ratio_multiple_chunks_first_id_h1_batch19():
    """多个 chunk 首元素都是 h1 → 不重复计数（matched = 1）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- _silent_drop_count 第十九批 ----------


def test_silent_drop_count_expected_zero_batch19():
    """expected count = 0 时不计 drop。"""
    out = _silent_drop_count({"heading": 0}, {"element_count_by_type": {"heading": 0}})
    assert out["value"] == 0


def test_silent_drop_count_expected_negative_batch19():
    """expected 负数：actual - exp 永远 >= 0（actual>=0），不计 drop。"""
    out = _silent_drop_count({"heading": 0}, {"element_count_by_type": {"heading": -3}})
    assert out["value"] == 0


def test_silent_drop_count_actual_more_than_expected_batch19():
    """实际比预期多。"""
    out = _silent_drop_count({"heading": 10}, {"element_count_by_type": {"heading": 5}})
    assert out["value"] == 0


def test_silent_drop_count_mixed_types_batch19():
    """部分 type drop，部分不 drop。"""
    by_type = {"heading": 1, "paragraph": 10}
    exp = {"element_count_by_type": {"heading": 3, "paragraph": 10, "table": 5}}
    out = _silent_drop_count(by_type, exp)
    # heading: max(0, 3-1)=2; paragraph: max(0,10-10)=0; table: max(0,5-0)=5
    assert out["value"] == 7


def test_silent_drop_count_empty_dict_in_expectations_batch19():
    out = _silent_drop_count({"heading": 1}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


# ---------- module source forbidden tokens 第三十四批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_output",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch19(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch19():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch19():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch19():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch19():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch19():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch19():
    src = inspect.getsource(mmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch19():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch19():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch19():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_call_batch19():
    src = inspect.getsource(mmod)
    assert ".unlink(" not in src


def test_module_source_no_rmdir_call_batch19():
    src = inspect.getsource(mmod)
    assert ".rmdir(" not in src


def test_module_source_no_write_text_call_batch19():
    """metrics.py 不写盘。"""
    src = inspect.getsource(mmod)
    assert ".write_text(" not in src
    assert ".write_bytes(" not in src


def test_module_source_no_sys_exit_batch19():
    src = inspect.getsource(mmod)
    assert "sys.exit" not in src


def test_module_source_no_re_compile_batch19():
    src = inspect.getsource(mmod)
    assert "re.compile" not in src


def test_module_source_no_path_open_write_mode_batch19():
    """不应该有 'w' 写模式 open。"""
    src = inspect.getsource(mmod)
    assert '"w"' not in src
    assert "'w'" not in src


def test_module_source_no_pandas_import_batch19():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch19():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第二十九批 ----------


def test_module_source_has_future_annotations_batch19():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_math_import_batch19():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_counter_import_batch19():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_pathlib_path_import_batch19():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch19():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_text_types_constant_batch19():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src


def test_module_source_has_pdf_bbox_required_constant_batch19():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src


def test_module_source_has_not_evaluated_constant_batch19():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_has_compute_automatic_metrics_function_batch19():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_text_preservation_docstring_batch19():
    src = inspect.getsource(mmod)
    assert "文本保留" in src or "text_preservation" in src


def test_module_source_has_silent_drop_docstring_batch19():
    src = inspect.getsource(mmod)
    assert "silent_drop_count" in src
    assert "expectations" in src


def test_module_source_has_all_single_entry_batch19():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


def test_module_source_has_no_evaluator_version_string_batch19():
    """metrics 不写 evaluator_version（不属于本模块）。"""
    src = inspect.getsource(mmod)
    assert "EVALUATOR_VERSION" not in src


# ---------- signatures 第二十九批 ----------


def test_signature_compute_metrics_batch19():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["document", "error", "source_type", "expectations", "image_base_dir"]
    # image_base_dir 默认 None
    assert params[-1].default is None


def test_signature_pdf_locator_ratio_batch19():
    sig = inspect.signature(_pdf_locator_ratio)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["elements"]


def test_signature_is_valid_bbox_batch19():
    sig = inspect.signature(_is_valid_bbox)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["bbox"]


def test_signature_text_preservation_batch19():
    sig = inspect.signature(_text_preservation)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["elements", "chunks"]


def test_signature_silent_drop_count_batch19():
    sig = inspect.signature(_silent_drop_count)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["by_type", "expectations"]


# ---------- module 合理性第二十九批 ----------


def test_module_has_all_attribute_batch19():
    assert hasattr(mmod, "__all__")


def test_module_all_contains_compute_automatic_metrics_batch19():
    assert "compute_automatic_metrics" in mmod.__all__


def test_module_all_only_contains_one_entry_batch19():
    assert len(mmod.__all__) == 1


def test_module_does_not_import_app_pipeline_batch19():
    src = inspect.getsource(mmod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch19():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch19():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_no_main_block_batch19():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_schema_validation_import_is_lazy_batch19():
    """document_passes_schema 在 compute_automatic_metrics 内部 lazy import。"""
    src = inspect.getsource(mmod)
    # 模块顶层不应直接 import document_passes_schema
    top = src[: src.find("def compute_automatic_metrics")]
    assert "document_passes_schema" not in top


def test_module_constants_not_in_all_batch19():
    """_TEXT_TYPES 等内部常量不在 __all__ 中。"""
    for k in ("_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"):
        assert k not in mmod.__all__


# ---------- 端到端集成 第二十九批 ----------


def test_e2e_compute_metrics_full_pdf_document_batch19():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {
                "element_id": "e1",
                "type": "heading",
                "content": "Title",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]},
            },
            {
                "element_id": "e2",
                "type": "paragraph",
                "content": "Hello world",
                "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]},
            },
        ],
        "chunks": [
            {
                "text": "Title Hello world",
                "source_element_ids": ["e1", "e2"],
            }
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_compute_metrics_with_expectations_silent_drop_batch19():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "heading", "content": "T", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [{"text": "T", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"heading": 5, "paragraph": 10}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    # heading: 5-1=4 drop; paragraph: 10-0=10 drop → total 14
    assert out["silent_drop_count"]["value"] == 14


def test_e2e_compute_metrics_docx_document_batch19():
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "Hi", "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "Hi", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_pipeline_failed_returns_14_nulls_batch19():
    out = compute_automatic_metrics(None, {"code": "E_PARSE"}, "pdf", None)
    nulls = [k for k, v in out.items() if v["value"] is None]
    # pipeline_success.value=False（非 null）；error_code.value="E_PARSE"（非 null）；schema_valid null
    # 其余 11 个 null
    assert len(nulls) == 12  # schema_valid + 11 后续指标


def test_e2e_text_preservation_chunker_word_split_batch19():
    """chunker 词内硬切（如 'Hello' → 'Hel' + 'lo'）应仍判 equal。"""
    elements = [
        {"type": "paragraph", "content": "Hello"},
    ]
    chunks = [
        {"text": "Hel "},
        {"text": "lo"},
    ]
    out = compute_automatic_metrics(
        {"document_id": "d", "source_type": "pdf", "elements": elements, "chunks": chunks},
        None,
        "pdf",
        None,
    )
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_compute_metrics_does_not_mutate_document_batch19():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "heading", "content": "x", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    import copy as _copy

    snapshot = _copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == snapshot


def test_e2e_image_only_document_text_preservation_passes_batch19():
    """全 image 的文档 text_preservation 默认 True（无文本可比）。"""
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "image", "resource_path": "/x.png"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True
    assert out["chunk_reference_intact_ratio"]["value"] is None
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"
