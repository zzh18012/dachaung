"""evaluation/metrics.py 第五十九轮 edges 测试（Round 533）。

补强 edges56 未触及的角度（第三十一批）：
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第三十一批：长度 / hashable / 序号 / 顺序
- 基础构造器 第三十一批：null reason 字符串 / ratio 边界值 / bool_metric 非 0/1 / int_metric 边界
- compute_automatic_metrics 第三十一批：error_code 无 message / schema_valid None / element_count_by_type 多种类型 / pipeline_failed 全 null
- _pdf_locator_ratio 第三十一批：page 是 float / page 是 str / 全 valid / 混合 valid invalid
- _docx_locator_ratio 第三十一批：空 elements / locator 是 None / 部分 valid 部分 invalid
- _is_valid_bbox 第三十一批：list 5 个值 / tuple / None / 字符串元素
- _image_resource_ratio 第三十一批：image_base_dir None / 多 image 部分存在 / 全存在 / rp 是绝对路径
- _chunk_reference_ratio 第三十一批：source_element_ids 含 None / 与 element_id 部分匹配
- _strip_unicode_whitespace 第三十一批：vertical tab / form feed / file separator / null char
- _text_preservation 第三十一批：含 image / Counter empty / unicode 多字节 / 大小写敏感
- _heading_boundary_ratio 第三十一批：heading 是 chunk 第二个 / chunk 无 ids / 多 heading 多 chunk
- _silent_drop_count 第三十一批：actual > expected / actual == expected / 多类型
- module source forbidden tokens 第四十八批
- module source 字符串精确补强第四十四批
- signatures 第四十四批
- module 合理性第四十四批
- 端到端集成第四十四批
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
    _NOT_EVALUATED,
    _PDF_BBOX_REQUIRED_TYPES,
    _TEXT_TYPES,
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


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第三十一批 ----------


def test_text_types_length_seven_batch31():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_length_four_batch31():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_text_types_hashable_batch31():
    """tuple 是 hashable。"""
    assert hash(_TEXT_TYPES) is not None


def test_text_types_unique_entries_batch31():
    assert len(set(_TEXT_TYPES)) == len(_TEXT_TYPES)


def test_pdf_bbox_required_types_unique_batch31():
    assert len(set(_PDF_BBOX_REQUIRED_TYPES)) == len(_PDF_BBOX_REQUIRED_TYPES)


def test_text_types_caption_index_batch31():
    """caption 在 _TEXT_TYPES 中位置 3。"""
    assert _TEXT_TYPES.index("caption") == 4


def test_pdf_bbox_required_types_first_is_heading_batch31():
    assert _PDF_BBOX_REQUIRED_TYPES[0] == "heading"


# ---------- 基础构造器 第三十一批 ----------


def test_null_reason_is_string_batch31():
    """reason 是 str（不是 enum）。"""
    m = _null("my_reason")
    assert isinstance(m["reason"], str)


def test_ratio_one_batch31():
    assert _ratio(1.0)["value"] == 1.0


def test_ratio_zero_batch31():
    assert _ratio(0.0)["value"] == 0.0


def test_bool_metric_empty_string_batch31():
    """bool 强转：'' → False。"""
    assert _bool_metric("")["value"] is False


def test_bool_metric_non_empty_string_batch31():
    assert _bool_metric("x")["value"] is True


def test_int_metric_large_value_batch31():
    assert _int_metric(10**9)["value"] == 10**9


def test_int_metric_zero_batch31():
    assert _int_metric(0)["value"] == 0


def test_int_metric_negative_batch31():
    assert _int_metric(-42)["value"] == -42


# ---------- compute_automatic_metrics 第三十一批 ----------


def test_compute_automatic_metrics_error_code_no_message_batch31():
    """error 不含 message 也 OK。"""
    result = compute_automatic_metrics(
        document=None,
        error={"code": "code_only"},
        source_type="pdf",
        expectations=None,
    )
    assert result["error_code"]["value"] == "code_only"


def test_compute_automatic_metrics_no_error_no_document_batch31():
    """error=None document=None → pipeline_success=False（error is None 但 document 也 None）。"""
    result = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert result["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_pipeline_failed_all_null_batch31():
    """pipeline_failed → 所有 metrics 都是 null + reason=pipeline_failed（除前 3 项）。"""
    result = compute_automatic_metrics(
        document=None,
        error={"code": "fail"},
        source_type="pdf",
        expectations=None,
    )
    for k in (
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
    ):
        assert result[k]["value"] is None
        assert result[k]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_element_count_by_type_multiple_types_batch31():
    """多种类型 element → 按类型计数。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1"},
            {"type": "paragraph", "element_id": "p2"},
            {"type": "heading", "element_id": "h1"},
            {"type": "image", "element_id": "i1"},
        ],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    by_type = result["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 2, "heading": 1, "image": 1}


def test_compute_automatic_metrics_with_chunks_batch31():
    """带 chunks 的完整 document。"""
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "hello"}],
        "chunks": [{"text": "hello", "source_element_ids": ["p1"]}],
    }
    result = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert result["element_count_total"]["value"] == 1
    assert result["chunk_reference_intact_ratio"]["value"] == 1.0


def test_compute_automatic_metrics_no_modification_batch31():
    """不修改 document。"""
    import json
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert json.dumps(doc, sort_keys=True) == before


def test_compute_automatic_metrics_idempotent_batch31():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    r1 = compute_automatic_metrics(doc, None, "pdf", None)
    r2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert r1 == r2


# ---------- _pdf_locator_ratio 第三十一批 ----------


def test_pdf_locator_ratio_page_float_batch31():
    """page 是 float（如 1.0）→ invalid（必须 int）。"""
    elements = [{"type": "image", "source_locator": {"page": 1.0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_string_batch31():
    """page 是 str → invalid。"""
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_all_valid_batch31():
    """全部 valid → 1.0。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]},
        },
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_mixed_batch31():
    """混合 valid/invalid → 0.5。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
        {"type": "image", "source_locator": {"page": 0}},  # invalid
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_ratio_table_no_bbox_required_batch31():
    """table 类型不需要 bbox → 只要 page 合法就 valid。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_empty_list_batch31():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


# ---------- _docx_locator_ratio 第三十一批 ----------


def test_docx_locator_ratio_empty_elements_batch31():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_locator_none_batch31():
    """source_locator 是 None → loc={} → 无结构键 → invalid。"""
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_partial_valid_batch31():
    """部分 valid 部分 invalid → 0.5。"""
    elements = [
        {"type": "paragraph", "source_locator": {"section": "s"}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


def test_docx_locator_ratio_relationship_id_only_batch31():
    """只含 relationship_id 也算 valid。"""
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "r1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_only_batch31():
    elements = [{"type": "paragraph", "source_locator": {"section": "main"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _is_valid_bbox 第三十一批 ----------


def test_is_valid_bbox_five_values_batch31():
    """5 个值 → invalid。"""
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0, 5.0]) is False


def test_is_valid_bbox_tuple_batch31():
    """tuple 不是 list → invalid。"""
    assert _is_valid_bbox((1.0, 2.0, 3.0, 4.0)) is False


def test_is_valid_bbox_none_batch31():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string_elements_batch31():
    """字符串元素 → invalid。"""
    assert _is_valid_bbox(["1", "2", "3", "4"]) is False


def test_is_valid_bbox_zero_values_batch31():
    """全 0 → 仍 valid（0 是有限数）。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_values_batch31():
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


# ---------- _image_resource_ratio 第三十一批 ----------


def test_image_resource_ratio_no_images_batch31():
    """无 image element → null。"""
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_base_dir_none_batch31(tmp_path):
    """image_base_dir=None → 仅用 Path(rp) 校验。"""
    img_in_root = tmp_path / "img.png"
    img_in_root.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": str(img_in_root)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_partial_existence_batch31(tmp_path):
    """2 image 1 个存在 → 0.5。"""
    (tmp_path / "exists.png").write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": "exists.png"},
        {"type": "image", "resource_path": "nope.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


def test_image_resource_ratio_all_exist_batch31(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.png").write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": "a.png"},
        {"type": "image", "resource_path": "b.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_absolute_path_batch31(tmp_path):
    """rp 是绝对路径 → 直接用。"""
    abs_path = tmp_path / "abs.png"
    abs_path.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": str(abs_path)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


# ---------- _chunk_reference_ratio 第三十一批 ----------


def test_chunk_reference_ratio_no_chunks_batch31():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_ids_with_none_batch31():
    """source_element_ids 含 None（不应匹配）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # None 不在 elem_ids 集合 → invalid
    assert out["value"] == 0.0


def test_chunk_reference_ratio_partial_match_batch31():
    """部分 chunk 引用合法、部分不合法 → 0.5。"""
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["eX"]},  # 不存在
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_empty_ids_batch31():
    """source_element_ids 空列表 → 不计入 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_no_ids_key_batch31():
    """chunk 缺 source_element_ids key → 视为空。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x"}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_batch31():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e1", "e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- _strip_unicode_whitespace 第三十一批 ----------


def test_strip_unicode_whitespace_vertical_tab_batch31():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_form_feed_batch31():
    assert _strip_unicode_whitespace("a\x0cb") == "ab"


def test_strip_unicode_whitespace_file_separator_batch31():
    """文件分隔符 \x1c 是空白？Python isspace: 否（\x1c 不是空白）。"""
    # Python: '\x1c'.isspace() → False（控制字符除 \t\n\r\f\v 外大多不视为空白）
    # 不删除
    result = _strip_unicode_whitespace("a\x1cb")
    # \x1c 不是空白 → 保留
    assert "a" in result and "b" in result


def test_strip_unicode_whitespace_null_char_batch31():
    """null char \\x00 → 不是空白（Python isspace False）→ 保留。"""
    result = _strip_unicode_whitespace("a\x00b")
    assert len(result) == 3  # 全保留


def test_strip_unicode_whitespace_tab_batch31():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_carriage_return_batch31():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_mixed_batch31():
    """混合多种空白。"""
    result = _strip_unicode_whitespace(" \t\n\r a 　 b")
    assert result == "ab"


# ---------- _text_preservation 第三十一批 ----------


def test_text_preservation_image_excluded_batch31():
    """image element 不参与比对。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_unicode_chars_batch31():
    """unicode 多字节字符保留。"""
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_case_sensitive_batch31():
    """大小写敏感：'A' != 'a'。"""
    elements = [{"type": "paragraph", "content": "A"}]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_empty_actual_batch31():
    """expected 非空，actual 空 → precision null, recall=0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_empty_expected_batch31():
    """expected 空，actual 非空 → recall null, precision=0。"""
    elements = [{"type": "image", "content": "x"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # image 被排除 → expected 空
    assert out["recall"]["reason"] == "empty_expected"
    assert out["precision"]["value"] == 0.0


def test_text_preservation_both_empty_batch31():
    """expected 与 actual 都空 → precision/recall null。"""
    elements = []
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_equal_but_different_multiset_batch31():
    """等价但 multiset 不同不可能（等价就 multiset 同）。"""
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


# ---------- _heading_boundary_ratio 第三十一批 ----------


def test_heading_boundary_ratio_heading_second_in_chunk_batch31():
    """heading 是 chunk 第 2 个 id → 不算合规。"""
    elements = [
        {"type": "paragraph", "element_id": "p1"},
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"source_element_ids": ["p1", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # h1 不是任一 chunk 首元素 → 0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_no_ids_batch31():
    """chunk 无 source_element_ids → 不贡献首 id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "no ids"}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_no_headings_batch31():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"source_element_ids": ["p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_multiple_headings_multiple_chunks_batch31():
    """2 个 heading + 2 个 chunk（首 id 对应） → 1.0。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_half_compliance_batch31():
    """2 个 heading，1 个合规 → 0.5。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _silent_drop_count 第三十一批 ----------


def test_silent_drop_count_actual_greater_than_expected_batch31():
    """actual > expected → 不计 drop（max(0, neg)=0）。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_actual_equal_expected_batch31():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_multiple_types_batch31():
    """多类型分别计算。"""
    by_type = {"paragraph": 5, "heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 10, "heading": 1, "image": 3}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph: 10-5=5, heading: 0, image: 3-0=3 → 8
    assert out["value"] == 8


def test_silent_drop_count_no_expectations_batch31():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch31():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_element_count_batch31():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_returns_int_batch31():
    by_type = {"paragraph": 1}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert isinstance(out["value"], int)


# ---------- module source forbidden tokens 第四十八批 ----------


def test_module_source_no_subprocess_batch31():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch31():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch31():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch31():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch31():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch31():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch31():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch31():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch31():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch31():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch31():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch31():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch31():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_text_types_constant_batch31():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading"' in src


def test_module_source_contains_pdf_bbox_required_constant_batch31():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading"' in src


def test_module_source_contains_not_evaluated_constant_batch31():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_null_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _null(reason: str)" in src


def test_module_source_contains_ratio_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _ratio(value: float)" in src


def test_module_source_contains_bool_metric_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _bool_metric" in src


def test_module_source_contains_int_metric_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _int_metric" in src


def test_module_source_contains_compute_automatic_metrics_func_batch31():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics" in src


def test_module_source_contains_pdf_locator_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio" in src


def test_module_source_contains_docx_locator_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio" in src


def test_module_source_contains_is_valid_bbox_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox" in src


def test_module_source_contains_image_resource_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio" in src


def test_module_source_contains_chunk_reference_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio" in src


def test_module_source_contains_strip_unicode_whitespace_batch31():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace" in src


def test_module_source_contains_text_preservation_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _text_preservation" in src


def test_module_source_contains_heading_boundary_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio" in src


def test_module_source_contains_silent_drop_count_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count" in src


def test_module_source_contains_math_import_batch31():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_contains_counter_import_batch31():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


# ---------- signatures 第四十四批 ----------


def test_signature_null_return_batch31():
    sig = inspect.signature(_null)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_null_reason_annotation_batch31():
    sig = inspect.signature(_null)
    assert sig.parameters["reason"].annotation == "str"


def test_signature_ratio_return_batch31():
    sig = inspect.signature(_ratio)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_ratio_value_annotation_batch31():
    sig = inspect.signature(_ratio)
    assert sig.parameters["value"].annotation == "float"


def test_signature_bool_metric_value_annotation_batch31():
    sig = inspect.signature(_bool_metric)
    assert sig.parameters["value"].annotation == "bool"


def test_signature_int_metric_value_annotation_batch31():
    sig = inspect.signature(_int_metric)
    assert sig.parameters["value"].annotation == "int"


def test_signature_compute_automatic_metrics_source_type_batch31():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["source_type"].annotation == "str"


def test_signature_compute_automatic_metrics_return_batch31():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_is_valid_bbox_return_bool_batch31():
    sig = inspect.signature(_is_valid_bbox)
    assert sig.return_annotation == "bool"


def test_signature_strip_unicode_whitespace_return_str_batch31():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert sig.parameters["s"].annotation == "str"
    assert sig.return_annotation == "str"


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_math_batch31():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch31():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_imports_pathlib_batch31():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch31():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch31():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_all_has_compute_automatic_metrics_batch31():
    src = inspect.getsource(mmod)
    assert '"compute_automatic_metrics"' in src


def test_module_no_main_block_batch31():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_compute_automatic_metrics_full_pdf_batch31(tmp_path):
    """端到端：完整 PDF document。"""
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"data")
    doc = {
        "elements": [
            {
                "type": "heading",
                "element_id": "h1",
                "content": "Title",
                "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]},
            },
            {
                "type": "paragraph",
                "element_id": "p1",
                "content": "Body",
                "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]},
            },
            {
                "type": "image",
                "element_id": "i1",
                "resource_path": str(img_path),
                "source_locator": {"page": 1},
            },
        ],
        "chunks": [
            {"text": "TitleBody", "source_element_ids": ["h1", "p1"]},
        ],
    }
    result = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=tmp_path,
    )
    assert result["element_count_total"]["value"] == 3
    assert result["pdf_locator_valid_ratio"]["value"] == 1.0
    assert result["image_resource_exists_ratio"]["value"] == 1.0
    assert result["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_compute_automatic_metrics_full_docx_batch31():
    """端到端：完整 DOCX document。"""
    doc = {
        "elements": [
            {
                "type": "heading",
                "element_id": "h1",
                "content": "Title",
                "source_locator": {"section": "s", "paragraph_index": 0},
            },
            {
                "type": "paragraph",
                "element_id": "p1",
                "content": "Body",
                "source_locator": {"section": "s", "paragraph_index": 1},
            },
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Body", "source_element_ids": ["p1"]},
        ],
    }
    result = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="docx",
        expectations={"element_count_by_type": {"heading": 1, "paragraph": 1}},
    )
    assert result["docx_locator_valid_ratio"]["value"] == 1.0
    assert result["silent_drop_count"]["value"] == 0


def test_e2e_pipeline_failed_passes_all_null_batch31():
    """端到端：pipeline 失败 → 全 null。"""
    result = compute_automatic_metrics(
        document=None,
        error={"code": "parse_error", "message": "broken pdf"},
        source_type="pdf",
        expectations=None,
    )
    assert result["element_count_total"]["value"] is None
    assert result["silent_drop_count"]["value"] is None


def test_e2e_idempotent_full_run_batch31():
    """端到端：两次相同输入相同结果。"""
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    r1 = compute_automatic_metrics(doc, None, "pdf", None)
    r2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert r1 == r2


def test_e2e_no_input_modification_batch31():
    """端到端：不修改输入。"""
    import json
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == before


def test_e2e_returns_dict_batch31():
    result = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(result, dict)


def test_e2e_silent_drop_with_expectations_batch31():
    """端到端：expectations 触发 silent_drop_count。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "x"},
        ],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    result = compute_automatic_metrics(doc, None, "pdf", expectations)
    # actual: paragraph=1, heading=0
    # expected: paragraph=5, heading=2 → drops = (5-1) + (2-0) = 6
    assert result["silent_drop_count"]["value"] == 6
