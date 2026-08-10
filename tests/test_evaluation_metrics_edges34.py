"""evaluation/metrics.py 第三十五轮 edges 测试（Round 373）。

补强 edges33 未触及的角度：
- compute_automatic_metrics 行为深度第七批（image_base_dir、schema_valid exception、document None + error None、各 metric shape 完整）
- _pdf_locator_ratio 行为深度第七批（element without locator、page=0、page 负、bbox as tuple/string/None 元素）
- _docx_locator_ratio 行为深度第七批（empty locator、only page、all structural keys、locator None）
- _image_resource_ratio 行为深度第七批（image_base_dir 拼接、绝对路径、空 resource_path、不存在的文件）
- _chunk_reference_ratio 行为深度第七批（empty ids、non-existent ids、全部 valid）
- _text_preservation 行为深度第七批（empty exp + actual、whitespace only、nbps 内部空白）
- _heading_boundary_ratio 行为深度第七批（multiple headings 部分 match、heading without element_id）
- _silent_drop_count 行为深度第七批（actual 多于 expected → 0、额外 type、全部 drops）
- _is_valid_bbox 行为深度第七批（negative 数值、mixed int/float、tuple/string/None 元素）
- _strip_unicode_whitespace 行为深度第七批（empty、所有空白字符组合、内部空白）
- module source forbidden tokens 第十批
- module 合理性第七批（_TEXT_TYPES tuple 顺序、_PDF_BBOX_REQUIRED_TYPES 顺序、_NOT_EVALUATED 值）
- 端到端集成第七批（compute 完整 pipeline 各种边界）
"""

from __future__ import annotations

import inspect
import math
import types
from pathlib import Path

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


# ---------- compute_automatic_metrics 行为深度第七批 ----------


def _full_doc(**overrides):
    base = {
        "elements": [
            {"type": "heading", "content": "Title", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 20.0]}},
            {"type": "paragraph", "content": "Body", "element_id": "e2",
             "source_locator": {"page": 1, "bbox": [0.0, 25.0, 100.0, 50.0]}},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["e1"]},
            {"text": "Body", "source_element_ids": ["e2"]},
        ],
    }
    base.update(overrides)
    return base


def test_compute_document_none_and_error_none_pipeline_success_false():
    """document=None + error=None → pipeline_success=False（document None 即失败）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_with_image_base_dir_none():
    """image_base_dir=None 时 image_resource_ratio 走默认路径。"""
    doc = _full_doc()
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=None)
    assert "image_resource_exists_ratio" in out
    # 没有 image element → null
    assert out["image_resource_exists_ratio"]["value"] is None


def test_compute_with_image_base_dir_provided(tmp_path):
    """image_base_dir 给定时 image_resource_ratio 使用拼接路径。"""
    # 创建一个 image 文件
    img = tmp_path / "img.png"
    img.write_text("fake image data")
    doc = {
        "elements": [
            {"type": "image", "resource_path": "img.png", "element_id": "i1"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_with_image_absolute_path(tmp_path):
    """resource_path 是绝对路径，无需 image_base_dir。"""
    img = tmp_path / "img.png"
    img.write_text("fake")
    doc = {
        "elements": [
            {"type": "image", "resource_path": str(img), "element_id": "i1"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=None)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_returns_14_metrics_keys():
    """document 非空时应返回 14 个 metric。"""
    doc = _full_doc()
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 13 metric + error_code
    expected = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert expected.issubset(set(out.keys()))


def test_compute_returns_14_metrics_when_document_none():
    """document=None 时也应返回 14 个 metric（全部 null/False）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    expected = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert expected == set(out.keys())


def test_compute_with_docx_source_type():
    """source_type=docx 时走 docx_locator 分支。"""
    doc = {
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    # docx_locator 应是 ratio 而非 null
    assert out["docx_locator_valid_ratio"]["value"] is not None
    # pdf_locator 应是 null
    assert out["pdf_locator_valid_ratio"]["value"] is None


def test_compute_with_unknown_source_type():
    """未知 source_type → 两个 locator 都是 null。"""
    doc = _full_doc()
    out = compute_automatic_metrics(doc, None, "unknown", None)
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["value"] is None


def test_compute_does_not_mutate_document():
    doc = _full_doc()
    doc_before = dict(doc)
    doc_before["elements"] = [dict(e) for e in doc["elements"]]
    doc_before["chunks"] = [dict(c) for c in doc["chunks"]]
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc["elements"] == doc_before["elements"]
    assert doc["chunks"] == doc_before["chunks"]


def test_compute_does_not_mutate_error():
    err = {"code": "E1", "message": "boom"}
    err_before = dict(err)
    compute_automatic_metrics(None, err, "pdf", None)
    assert err == err_before


def test_compute_idempotent():
    doc = _full_doc()
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


# ---------- _pdf_locator_ratio 行为深度第七批 ----------


def test_pdf_locator_element_without_source_locator():
    """element 无 source_locator → loc={} → page None → 不算 valid。"""
    elements = [{"type": "paragraph", "content": "x"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_zero_invalid():
    """page=0 invalid（要求 page >= 1）。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_negative_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": -1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bbox_as_tuple_rejected():
    """bbox 是 tuple 而非 list → isinstance False → 不 valid。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": (0.0, 0.0, 1.0, 1.0)}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_non_text_type_skips_bbox_check():
    """非文本类型（如 image）不需要 bbox，只要 page valid。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # image 不需 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_partial_valid():
    """部分 valid：1/2 valid → 0.5。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
        {"type": "paragraph", "source_locator": {"page": 0}},  # invalid page
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_source_locator_none():
    """source_locator=None → or {} → 空 dict → page None → invalid。"""
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_as_string_invalid():
    """page 是字符串而非 int → invalid。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": "1", "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 行为深度第七批 ----------


def test_docx_locator_empty_locator_dict():
    """locator 空 dict → 无任何 structural key → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_only_page_rejected():
    """DOCX locator 不允许 page。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_all_structural_keys():
    """所有 structural key 都设 → valid。"""
    elements = [
        {"type": "paragraph", "source_locator": {
            "section": 1, "paragraph_index": 0, "run_index": 0,
            "table_index": 0, "row_index": 0, "col_index": 0,
            "relationship_id": "r1",
        }},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_one_structural_key():
    """只要一个 structural key 即可。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_bbox_rejected():
    """DOCX locator 不允许 bbox。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_partial_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # valid
        {"type": "paragraph", "source_locator": {}},  # invalid
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- _image_resource_ratio 行为深度第七批 ----------


def test_image_resource_no_image_elements():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_empty_resource_path():
    """image element 但 resource_path 缺失 → invalid。"""
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_nonexistent_file():
    elements = [{"type": "image", "resource_path": "nonexistent.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_existing_file(tmp_path):
    img = tmp_path / "img.png"
    img.write_text("fake")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_with_image_base_dir(tmp_path):
    """resource_path 是相对文件名，image_base_dir 提供路径。"""
    img = tmp_path / "img.png"
    img.write_text("fake")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_partial(tmp_path):
    """部分 image 文件存在。"""
    img = tmp_path / "exists.png"
    img.write_text("fake")
    elements = [
        {"type": "image", "resource_path": str(img)},  # exists
        {"type": "image", "resource_path": "nonexistent.png"},  # doesn't exist
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_zero_byte_file(tmp_path):
    """0 字节文件 → 不算存在。"""
    img = tmp_path / "empty.png"
    img.write_text("")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


# ---------- _chunk_reference_ratio 行为深度第七批 ----------


def test_chunk_reference_empty_chunks():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_empty_source_element_ids():
    """chunk 的 source_element_ids 是空 → 不 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_missing_source_element_ids_key():
    """chunk 无 source_element_ids key → 视作空 → 不 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_non_existent_ids():
    """chunk 引用不存在的 element_id → 不 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["non_existent"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_partial_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["non_existent"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_multiple_ids_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}, {"element_id": "e3"}]
    chunks = [{"source_element_ids": ["e1", "e2", "e3"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- _text_preservation 行为深度第七批 ----------


def test_text_preservation_empty_elements_and_chunks():
    """两者都空 → null + empty_expected_and_actual。"""
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_actual_with_non_empty_expected():
    out = _text_preservation([{"type": "paragraph", "content": "abc"}], [])
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_empty_expected_with_non_empty_actual():
    out = _text_preservation([], [{"text": "abc"}])
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_whitespace_only_both():
    """两边都只有空白 → strip 后都空 → empty_expected_and_actual。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "   "}],
        [{"text": "  "}],
    )
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_match():
    out = _text_preservation(
        [{"type": "paragraph", "content": "hello"}],
        [{"text": "hello"}],
    )
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_partial_overlap():
    """部分字符重叠。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "abcde"}],
        [{"text": "abxyz"}],
    )
    # 共享：'a' 'b' = 2 个
    # precision = 2/5, recall = 2/5
    assert out["precision"]["value"] == pytest.approx(2/5)
    assert out["recall"]["value"] == pytest.approx(2/5)


def test_text_preservation_with_image_skipped():
    """image element 的 content 不参与比对。"""
    out = _text_preservation(
        [
            {"type": "paragraph", "content": "abc"},
            {"type": "image", "content": "should_be_ignored"},
        ],
        [{"text": "abc"}],
    )
    assert out["equal"]["value"] is True


def test_text_preservation_returns_three_keys():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


# ---------- _heading_boundary_ratio 行为深度第七批 ----------


def test_heading_boundary_no_headings():
    out = _heading_boundary_ratio(
        [{"type": "paragraph", "element_id": "p1"}],
        [{"source_element_ids": ["p1"]}],
    )
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_partial_match():
    """2 个 heading，1 个 match → 0.5。"""
    out = _heading_boundary_ratio(
        [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
        ],
        [{"source_element_ids": ["h1"]}],
    )
    assert out["value"] == 0.5


def test_heading_boundary_no_chunks_with_first_id():
    """所有 chunk 都没 source_element_ids → chunk_first_ids 空 → 0 match。"""
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": []}],
    )
    assert out["value"] == 0.0


def test_heading_boundary_full_match():
    out = _heading_boundary_ratio(
        [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
        ],
        [
            {"source_element_ids": ["h1"]},
            {"source_element_ids": ["h2"]},
        ],
    )
    assert out["value"] == 1.0


def test_heading_boundary_heading_without_element_id():
    """heading 无 element_id → get 返回 None → 不在 chunk_first_ids 中。"""
    out = _heading_boundary_ratio(
        [{"type": "heading"}],  # no element_id
        [{"source_element_ids": ["h1"]}],
    )
    assert out["value"] == 0.0


def test_heading_boundary_multiple_chunks_same_first_id():
    """两个 chunk 首元素都是 h1 → set 去重，h1 仍只算 1 个 match。"""
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [
            {"source_element_ids": ["h1", "p1"]},
            {"source_element_ids": ["h1", "p2"]},
        ],
    )
    assert out["value"] == 1.0


# ---------- _silent_drop_count 行为深度第七批 ----------


def test_silent_drop_no_expectations():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_expectations():
    """expectations={} 视为 None。"""
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None


def test_silent_drop_expectations_without_element_count():
    """expectations 不含 element_count_by_type。"""
    out = _silent_drop_count({"paragraph": 5}, {"other_key": "value"})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_actual_more_than_expected():
    """actual 多于 expected → drop = 0（max(0, neg)）。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_extra_type_in_expectations():
    """expected 含 actual 没有的 type → 那个 type 全部 drop。"""
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5, "heading": 3}},
    )
    # heading 全部 drop = 3
    assert out["value"] == 3


def test_silent_drop_mixed():
    """混合：一些 drop，一些 exceed。"""
    out = _silent_drop_count(
        {"paragraph": 5, "heading": 3},
        {"element_count_by_type": {"paragraph": 3, "heading": 5, "image": 2}},
    )
    # paragraph: max(0, 3-5) = 0
    # heading: max(0, 5-3) = 2
    # image: max(0, 2-0) = 2
    assert out["value"] == 4


def test_silent_drop_returns_int():
    out = _silent_drop_count(
        {"paragraph": 3},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert isinstance(out["value"], int)


# ---------- _is_valid_bbox 行为深度第七批 ----------


def test_is_valid_bbox_negative_numbers():
    """负数 bbox 仍 valid。"""
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([1, 2.5, 3, 4.0]) is True


def test_is_valid_bbox_tuple_rejected():
    assert _is_valid_bbox((1.0, 2.0, 3.0, 4.0)) is False


def test_is_valid_bbox_string_rejected():
    assert _is_valid_bbox("1234") is False


def test_is_valid_bbox_with_none_element():
    assert _is_valid_bbox([1.0, None, 3.0, 4.0]) is False


def test_is_valid_bbox_with_string_element():
    assert _is_valid_bbox(["1.0", 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_too_short():
    assert _is_valid_bbox([1.0, 2.0, 3.0]) is False


def test_is_valid_bbox_too_long():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0, 5.0]) is False


def test_is_valid_bbox_with_nan():
    assert _is_valid_bbox([1.0, float("nan"), 3.0, 4.0]) is False


def test_is_valid_bbox_with_inf():
    assert _is_valid_bbox([1.0, float("inf"), 3.0, 4.0]) is False


def test_is_valid_bbox_with_negative_inf():
    assert _is_valid_bbox([1.0, float("-inf"), 3.0, 4.0]) is False


def test_is_valid_bbox_all_zeros():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_dict_rejected():
    assert _is_valid_bbox({"x": 1, "y": 2}) is False


# ---------- _strip_unicode_whitespace 行为深度第七批 ----------


def test_strip_unicode_whitespace_empty():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   \t\n\r") == ""


def test_strip_unicode_whitespace_internal_whitespace():
    """内部空白被删除（与 str.strip 不同）。"""
    assert _strip_unicode_whitespace("a\tb c") == "abc"


def test_strip_unicode_whitespace_nbsp():
    """NBSP 是 isspace True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """em space (U+2003) 是 isspace True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """全角空格 (U+3000) 是 isspace True。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """U+2028 (line separator) 是 isspace True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029 (paragraph separator) 是 isspace True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_non_whitespace():
    """不应删除任何非空白字符（标点、emoji 等）。"""
    assert _strip_unicode_whitespace("a!@#$%^&*()b") == "a!@#$%^&*()b"


def test_strip_unicode_whitespace_returns_str():
    assert isinstance(_strip_unicode_whitespace("hello"), str)


def test_strip_unicode_whitespace_idempotent():
    """调用两次结果相同。"""
    s = "hello world"
    once = _strip_unicode_whitespace(s)
    twice = _strip_unicode_whitespace(once)
    assert once == twice


# ---------- module source forbidden tokens 第十批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.chmod", "os.chown",
        "os.execv", "os.fork",
        "os.kill", "os.mkdir",
        "os.makedirs", "os.remove",
        "os.rename", "os.rmdir",
        "os.unlink",
        "pathlib.Path.rmdir",
        "pathlib.Path.unlink",
        "eval(", "exec(",
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "memoryview",
        "bytearray(",
        "errno",
        "signal.signal",
        "fcntl",
        "termios",
        "tty",
        "winreg",
        "msvcrt",
        "_winapi",
        "re.match",
        "re.sub",
        "shutil.rmtree",
        "tempfile.mkdtemp",
    ],
)
def test_metrics_source_no_forbidden_token_v3(token):
    src = inspect.getsource(mmod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module 合理性第七批 ----------


def test_module_text_types_exact_entries():
    """_TEXT_TYPES 顺序与定义一致。"""
    expected = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")
    assert _TEXT_TYPES == expected


def test_module_pdf_bbox_required_types_exact_entries():
    expected = ("heading", "paragraph", "caption", "list_item")
    assert _PDF_BBOX_REQUIRED_TYPES == expected


def test_module_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_module_not_evaluated_type():
    assert isinstance(_NOT_EVALUATED, str)


def test_module_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_module_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_text_types_length_7():
    assert len(_TEXT_TYPES) == 7


def test_module_pdf_bbox_required_types_length_4():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_module_all_length_1():
    assert len(mmod.__all__) == 1


def test_module_all_only_compute_automatic_metrics():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_namespace_callable_count_14():
    """14 callable：1 公开 + 13 私有 helper（_null/_ratio/_bool_metric/_int_metric
    + compute_automatic_metrics + 7 helper + _strip_unicode_whitespace + _is_valid_bbox
    + _text_preservation + _silent_drop_count）。
    """
    funcs = [
        name for name, val in vars(mmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == mmod.__name__
    ]
    assert len(funcs) == 14


def test_module_no_user_classes():
    classes = [
        name for name, val in vars(mmod).items()
        if isinstance(val, type) and val.__module__ == mmod.__name__
    ]
    assert len(classes) == 0


def test_module_function_module_eq_mmod():
    assert compute_automatic_metrics.__module__ == "evaluation.metrics"


def test_module_docstring_present():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


def test_module_docstring_mentions_text_preservation():
    assert "text_preservation" in mmod.__doc__


def test_module_docstring_mentions_pure_function():
    assert "纯函数" in mmod.__doc__ or "纯" in mmod.__doc__


# ---------- 端到端集成第七批 ----------


def test_e2e_compute_metrics_with_full_pdf_doc():
    doc = {
        "elements": [
            {"type": "heading", "content": "Title", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 20.0]}},
            {"type": "paragraph", "content": "Body", "element_id": "p1",
             "source_locator": {"page": 1, "bbox": [0.0, 25.0, 100.0, 50.0]}},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Body", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_compute_metrics_with_error_dict():
    err = {"code": "PARSE_ERROR", "message": "failed"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "PARSE_ERROR"


def test_e2e_compute_metrics_document_none_returns_14_null_metrics():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14
    # pipeline_success 是 False（bool metric），其他都是 null
    assert out["pipeline_success"]["value"] is False
    # error_code 是 None
    assert out["error_code"]["value"] is None
    # 其他 null
    assert out["schema_valid"]["value"] is None


def test_e2e_compute_metrics_with_positional_args():
    doc = _full_doc()
    out = compute_automatic_metrics(doc, None, "pdf", None, None)
    assert out["pipeline_success"]["value"] is True


def test_e2e_compute_metrics_with_kwargs():
    doc = _full_doc()
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert out["pipeline_success"]["value"] is True


def test_e2e_pdf_locator_with_image_no_bbox():
    """image 不需要 bbox（非文本类型）。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_e2e_docx_locator_with_relationship_id():
    elements = [
        {"type": "paragraph", "source_locator": {"relationship_id": "rId1"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_e2e_chunk_reference_with_none_elements_list():
    """elements=[] 但有 chunks → 0 valid。"""
    out = _chunk_reference_ratio([], [{"source_element_ids": ["x"]}])
    assert out["value"] == 0.0


def test_e2e_text_preservation_with_dup_chars_in_actual():
    """actual 有重复字符 → counter 交集取 min。"""
    out = _text_preservation(
        [{"type": "paragraph", "content": "abc"}],
        [{"text": "aabbcc"}],
    )
    # expected = abc → c_expected = {a:1, b:1, c:1}
    # actual = aabbcc → c_actual = {a:2, b:2, c:2}
    # common = {a:1, b:1, c:1} = 3
    # precision = 3/6 = 0.5
    # recall = 3/3 = 1.0
    assert out["precision"]["value"] == pytest.approx(0.5)
    assert out["recall"]["value"] == 1.0


def test_e2e_heading_boundary_with_three_headings_partial():
    out = _heading_boundary_ratio(
        [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
            {"type": "heading", "element_id": "h3"},
        ],
        [
            {"source_element_ids": ["h1"]},
            {"source_element_ids": ["h2"]},
        ],
    )
    # 2/3 = 0.667
    assert out["value"] == pytest.approx(2/3)
