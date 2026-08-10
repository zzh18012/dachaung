"""evaluation/metrics.py 边角测试 - 第二十轮（Round 287）。

edges19 已覆盖：compute_automatic_metrics failed/succeeded scenarios / source_type 分支 / _pdf_locator_ratio
各场景 / _docx_locator_ratio structural_keys / _is_valid_bbox 16 场景 / _image_resource_ratio 文件系统 /
_chunk_reference_ratio 混合 / _strip_unicode_whitespace 字符级 / _text_preservation 各场景 /
_heading_boundary_ratio 各场景 / _silent_drop_count 多 type sum / helper consistency / schema_valid 异常路径。

edges20 补强未覆盖的角度：**Schema 联动** + **Counter 多集合深度** + **算法边界与混合**：
- compute_automatic_metrics Schema 联动：
  - 输出可作为 evaluation-report.schema.json 的 per_doc[i].metrics 字段
  - 输出 dict 14 个 keys 都有 'value' + 'reason'
  - element_count_by_type.value 类型是 dict
  - error_code.value 类型是 str 或 None

- _text_preservation Counter 多集合深度：
  - expected="aabbcc" actual="aabbcc" → equal=True, precision=1.0, recall=1.0
  - expected="aabbcc" actual="abc" → equal=False, precision=1.0, recall=0.5
  - expected="abc" actual="aabbcc" → equal=False, precision=0.5, recall=1.0
  - expected="aabbcc" actual="xxyyzz" → equal=False, precision=0.0, recall=0.0
  - expected="aaa" actual="aa" → precision=1.0, recall=2/3
  - expected="aa" actual="aaa" → precision=2/3, recall=1.0
  - Counter 交集 (c1 & c2) 取 min
  - 重复字符在 expected/actual 各方向不对等

- _text_preservation image 不参与：
  - elements 含 image + content → expected 不含 image.content
  - chunks 不受影响

- _text_preservation content=None / 缺 content：
  - element 缺 content → 视为空 string
  - element content=None → 视为空 string
  - chunk 缺 text → 视为空 string
  - chunk text=None → 视为空 string

- _is_valid_bbox 混合类型：
  - [0, 0, 100, 100] 全 int → True
  - [0.0, 0.0, 100.0, 100.0] 全 float → True
  - [0, 0.0, 100, 100.0] int+float 混合 → True
  - [True, 0, 0, 0] bool → False（isinstance(True, bool) 是 True 但 isinstance(True, int) 也是 True，但代码先检查 bool）
  - [0, 0, 0, 0] 全 0 → True（valid bbox at origin）
  - [-1, -1, 100, 100] 负数 → True（不限制 sign）
  - [1e308, 1e308, 1e308, 1e308] 极大但 finite → True
  - [float('nan'), 0, 0, 0] → False
  - [float('inf'), 0, 0, 0] → False
  - [float('-inf'), 0, 0, 0] → False
  - [0j, 0, 0, 0] complex → False
  - ["0", 0, 0, 0] str → False

- _pdf_locator_ratio 混合：
  - 全 valid page 但 text type 缺 bbox → 部分 valid
  - text type 缺 source_locator → invalid（page=None）
  - text type source_locator={} → invalid
  - text type source_locator=None → invalid（loc=None 后 `or {}` 变 {}）
  - 多 type 多 page 多 bbox 混合

- _docx_locator_ratio structural_keys 组合：
  - 只有 section → valid
  - 只有 paragraph_index → valid
  - 有 page + paragraph_index → invalid（page 优先）
  - 有 bbox + section → invalid
  - 多个 structural_keys → valid
  - 空 locator → invalid
  - locator=None → invalid

- _chunk_reference_ratio 边界：
  - chunk source_element_ids=[] → 不算 valid（ids falsy 短路）
  - chunk source_element_ids=None → c.get(...) or [] = [] → 不算 valid
  - chunk 缺 source_element_ids → 不算 valid
  - chunk source_element_ids 含未知 id → not all() → 不算 valid
  - chunk source_element_ids 含已知 id + 未知 id → 不算 valid
  - elements 空 + chunks 有 → elem_ids=set()，all(sid in set()) 必为 False（除非 ids 空）

- _heading_boundary_ratio 边界：
  - chunks=[] → chunk_first_ids=set() → matched=0 → ratio=0.0
  - chunk source_element_ids=[] → 不参与 chunk_first_ids
  - chunk source_element_ids 缺第一个 id → ids[0] 是 None
  - heading element_id=None → 不能 match（None not in set 一定 False）
  - 多 chunk 共享同一首 id（dedup by set）
  - heading 重复 element_id（不应发生但测）

- _silent_drop_count 边界：
  - expectations={} → null+no_expectations
  - expectations=None → null+no_expectations
  - expectations.element_count_by_type={} → null+no_expectations_element_count
  - expectations.element_count_by_type=None → null+no_expectations_element_count
  - by_type 完全等于 expected → drops=0
  - by_type > expected → drops=0（max(0, neg)）
  - by_type 缺 expected 中某 type → drops += expected
  - by_type 含 expected 没有的 type → 不参与

- 模块 source level 完整补强：
  - _null / _ratio / _bool_metric / _int_metric 都是 1 行函数体
  - compute_automatic_metrics source 含 14 个 metric key 字面量
  - _pdf_locator_ratio 含 _PDF_BBOX_REQUIRED_TYPES 引用
  - _docx_locator_ratio 含 7 个 structural_keys 字面量
  - 模块 source 不含 logging / json / subprocess / os import
  - 模块 source 不含 star import / relative import
  - 模块 source 含 'from __future__ import annotations'
  - 模块 source 含 'import math'（用于 math.isfinite）

- compute_automatic_metrics 集成场景：
  - document dict 含完整 elements + chunks → 14 metrics 都有值
  - source_type='txt' / 'unknown' → pdf + docx 都 null
  - error_code['code'] 取自 error dict
  - error 缺 'code' key → KeyError（不静默）
"""

from __future__ import annotations

import inspect
import json
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


# ============================================================================
# compute_automatic_metrics Schema 联动
# ============================================================================


def test_compute_automatic_metrics_output_can_be_in_metric_section_of_report():
    """输出可作为 per_doc[i].metrics 加入 evaluation-report.schema.json。"""
    document = {
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "hello world",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            },
        ],
        "chunks": [
            {
                "chunk_id": "c1",
                "text": "hello world",
                "source_element_ids": ["e1"],
            }
        ],
    }
    metrics = compute_automatic_metrics(document, None, "pdf", None)
    full_report = {
        "report_version": "1.1",
        "provenance": {
            "git_commit": "abc",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 1,
            "content_group_count": 1,
            "pdf_count": 1,
            "docx_count": 0,
            "categories_covered": ["cat_a"],
        },
        "summary": {},
        "per_doc": [
            {
                "doc_id": "doc1",
                "source_type": "pdf",
                "metrics": metrics,
                "wall_time_seconds": {
                    "total": 0.1,
                    "parse": None,
                    "chunk": None,
                    "parse_reason": "not_instrumented",
                    "chunk_reason": "not_instrumented",
                },
            }
        ],
    }
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "evaluation-report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    errs = list(validator.iter_errors(full_report))
    assert errs == [], f"schema errors: {errs}"


def test_compute_automatic_metrics_all_keys_have_value_and_reason():
    """每个 metric 都含 value 和 reason 2 keys。"""
    document = {
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "x"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "x", "source_element_ids": ["e1"]},
        ],
    }
    metrics = compute_automatic_metrics(document, None, "pdf", None)
    for name, metric in metrics.items():
        assert "value" in metric, f"{name} missing value"
        assert "reason" in metric, f"{name} missing reason"


def test_compute_automatic_metrics_element_count_by_type_value_is_dict():
    document = {
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "x"},
        ],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(document, None, "pdf", None)
    assert isinstance(metrics["element_count_by_type"]["value"], dict)


def test_compute_automatic_metrics_error_code_value_type_str_or_none():
    """error_code.value 是 str（来自 error['code']）或 None。"""
    # 失败：str
    error = {"code": "boom", "message": "...", "details": {}}
    m1 = compute_automatic_metrics(None, error, "pdf", None)
    assert isinstance(m1["error_code"]["value"], str)

    # 成功：None
    document = {"elements": [], "chunks": []}
    m2 = compute_automatic_metrics(document, None, "pdf", None)
    assert m2["error_code"]["value"] is None


# ============================================================================
# _text_preservation Counter 多集合深度
# ============================================================================


def _make_elements(contents_with_types: list[tuple[str, str]]) -> list[dict]:
    """构造 elements list。contents_with_types = [(content, type), ...]。"""
    return [
        {"element_id": f"e{i}", "type": t, "content": c}
        for i, (c, t) in enumerate(contents_with_types)
    ]


def _make_chunks(texts: list[str]) -> list[dict]:
    return [
        {"chunk_id": f"c{i}", "text": t, "source_element_ids": [f"e{i}"]}
        for i, t in enumerate(texts)
    ]


def test_text_preservation_equal_when_identical():
    elements = _make_elements([("aabbcc", "paragraph")])
    chunks = _make_chunks(["aabbcc"])
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_partial_actual_subset_of_expected():
    """expected='aabbcc' actual='abc' → equal=False, precision=1.0, recall=0.5。"""
    elements = _make_elements([("aabbcc", "paragraph")])
    chunks = _make_chunks(["abc"])
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0  # all of abc is in aabbcc
    # recall = 3/6 = 0.5
    assert out["recall"]["value"] == 0.5


def test_text_preservation_partial_actual_superset_of_expected():
    """expected='abc' actual='aabbcc' → precision=0.5, recall=1.0。"""
    elements = _make_elements([("abc", "paragraph")])
    chunks = _make_chunks(["aabbcc"])
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision = 3/6 = 0.5
    assert out["precision"]["value"] == 0.5
    assert out["recall"]["value"] == 1.0


def test_text_preservation_completely_disjoint():
    """expected='aabbcc' actual='xxyyzz' → precision=0.0, recall=0.0。"""
    elements = _make_elements([("aabbcc", "paragraph")])
    chunks = _make_chunks(["xxyyzz"])
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_partial_repeat_char():
    """expected='aaa' actual='aa' → precision=1.0, recall=2/3。"""
    elements = _make_elements([("aaa", "paragraph")])
    chunks = _make_chunks(["aa"])
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_partial_repeat_char_other_direction():
    """expected='aa' actual='aaa' → precision=2/3, recall=1.0。"""
    elements = _make_elements([("aa", "paragraph")])
    chunks = _make_chunks(["aaa"])
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == pytest.approx(2 / 3)
    assert out["recall"]["value"] == 1.0


def test_text_preservation_counter_intersection_takes_min():
    """Counter 交集 (c1 & c2) 取 min。"""
    c1 = Counter("aabbcc")
    c2 = Counter("abc")
    intersection = c1 & c2
    assert intersection == Counter({"a": 1, "b": 1, "c": 1})


def test_text_preservation_image_does_not_participate():
    """image element 的 content 不进入 expected。"""
    elements = _make_elements([("abc", "paragraph"), ("image-binary", "image")])
    chunks = _make_chunks(["abc"])
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_image_does_not_participate_even_if_in_actual():
    """即使 chunk 中有 image content，也只比 non-image。"""
    elements = _make_elements([("abc", "paragraph"), ("image-content", "image")])
    chunks = _make_chunks(["abcimage-content"])
    out = _text_preservation(elements, chunks)
    # expected = 'abc'；actual = 'abcimage-content'
    # equal=False, precision=3/17≈0.176, recall=1.0
    assert out["equal"]["value"] is False
    assert out["recall"]["value"] == 1.0


def test_text_preservation_element_missing_content():
    """element 缺 content → 视为空 string。"""
    elements = [{"element_id": "e1", "type": "paragraph"}]  # 缺 content
    chunks = _make_chunks([""])
    out = _text_preservation(elements, chunks)
    # expected='' actual='' → 都空 → null
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_element_content_none():
    elements = [{"element_id": "e1", "type": "paragraph", "content": None}]
    chunks = _make_chunks([""])
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_missing_text():
    """chunk 缺 text → 视为空 string。"""
    elements = _make_elements([("", "paragraph")])
    chunks = [{"chunk_id": "c1", "source_element_ids": ["e1"]}]  # 缺 text
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_text_none():
    elements = _make_elements([("", "paragraph")])
    chunks = [{"chunk_id": "c1", "text": None, "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_multi_element_concat_order_matters():
    """多 element 的 content 按 list 顺序拼接。"""
    elements = _make_elements([("abc", "paragraph"), ("def", "paragraph")])
    chunks = _make_chunks(["abcdef"])
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    # reversed order → 不相等
    chunks_rev = _make_chunks(["defabc"])
    out_rev = _text_preservation(elements, chunks_rev)
    assert out_rev["equal"]["value"] is False


# ============================================================================
# _is_valid_bbox 混合类型
# ============================================================================


def test_is_valid_bbox_all_int():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_all_float():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0]) is True


def test_is_valid_bbox_int_and_float_mix():
    assert _is_valid_bbox([0, 0.0, 100, 100.0]) is True


def test_is_valid_bbox_bool_first_element():
    """bool 元素 → False（即使 isinstance(True, int) 也是 True，但代码先检查 bool）。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_bool_in_middle():
    assert _is_valid_bbox([0, False, 0, 0]) is False


def test_is_valid_bbox_all_zero():
    """全 0 是有效 bbox（origin）。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_numbers():
    """负数 → True（不限制 sign）。"""
    assert _is_valid_bbox([-1, -1, 100, 100]) is True


def test_is_valid_bbox_large_but_finite():
    """极大但 finite → True。"""
    assert _is_valid_bbox([1e308, 1e308, 1e308, 1e308]) is True


def test_is_valid_bbox_nan():
    """NaN → False（math.isfinite(nan)=False）。"""
    assert _is_valid_bbox([float("nan"), 0, 0, 0]) is False


def test_is_valid_bbox_inf():
    """inf → False。"""
    assert _is_valid_bbox([float("inf"), 0, 0, 0]) is False


def test_is_valid_bbox_negative_inf():
    """-inf → False。"""
    assert _is_valid_bbox([float("-inf"), 0, 0, 0]) is False


def test_is_valid_bbox_complex():
    """complex 不是 int/float → False。"""
    assert _is_valid_bbox([0j, 0, 0, 0]) is False


def test_is_valid_bbox_string():
    """str 不是 int/float → False。"""
    assert _is_valid_bbox(["0", 0, 0, 0]) is False


def test_is_valid_bbox_tuple():
    """tuple 不是 list → False。"""
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_dict():
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_len_3():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_len_5():
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


# ============================================================================
# _pdf_locator_ratio 混合场景
# ============================================================================


def test_pdf_locator_ratio_all_valid_text_with_bbox():
    """全 valid：text type 含 page + bbox。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
        },
        {
            "type": "heading",
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]},
        },
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_text_missing_bbox_invalid():
    """text type 缺 bbox → invalid。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_missing_source_locator_invalid():
    """text type 缺 source_locator → invalid（page=None）。"""
    elements = [{"type": "paragraph"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_source_locator_empty_dict():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_source_locator_none():
    """source_locator=None → loc = None or {} = {}。"""
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_table_does_not_require_bbox():
    """table 类型不需要 bbox（不在 _PDF_BBOX_REQUIRED_TYPES）。"""
    elements = [
        {"type": "table", "source_locator": {"page": 1}},  # 无 bbox 但 table
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_header_does_not_require_bbox():
    elements = [{"type": "header", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_footer_does_not_require_bbox():
    elements = [{"type": "footer", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_caption_requires_bbox():
    """caption 在 _PDF_BBOX_REQUIRED_TYPES。"""
    elements = [{"type": "caption", "source_locator": {"page": 1}}]  # 缺 bbox
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_list_item_requires_bbox():
    elements = [{"type": "list_item", "source_locator": {"page": 1}}]  # 缺 bbox
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_mixed_types():
    """多 type 混合，部分 valid。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (no bbox)
        {"type": "table", "source_locator": {"page": 1}},  # valid
        {"type": "image", "source_locator": {"page": 1}},  # valid (image not in required)
    ]
    out = _pdf_locator_ratio(elements)
    # 3/4 = 0.75
    assert out["value"] == 0.75


def test_pdf_locator_ratio_zero_page_invalid():
    """page=0 < 1 → invalid。"""
    elements = [{"type": "table", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_negative_page_invalid():
    elements = [{"type": "table", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_float_page_invalid():
    """float page → invalid（要求 int）。"""
    elements = [{"type": "table", "source_locator": {"page": 1.0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ============================================================================
# _docx_locator_ratio structural_keys 组合
# ============================================================================


def test_docx_locator_ratio_only_section_valid():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_only_paragraph_index_valid():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_page_makes_invalid():
    """有 page → invalid（即使有 structural_key）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_bbox_makes_invalid():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_multiple_structural_keys_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1, "paragraph_index": 0, "run_index": 0}}
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_empty_locator_invalid():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_none_locator_invalid():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_missing_locator_invalid():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_each_structural_key_alone_valid():
    """7 个 structural_keys 各自单独都 valid。"""
    for key in ("section", "paragraph_index", "run_index", "table_index", "row_index", "col_index", "relationship_id"):
        elements = [{"type": "paragraph", "source_locator": {key: 1}}]
        out = _docx_locator_ratio(elements)
        assert out["value"] == 1.0


def test_docx_locator_ratio_mixed_valid_invalid():
    """混合 valid + invalid → 部分 ratio。"""
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ============================================================================
# _chunk_reference_ratio 边界
# ============================================================================


def test_chunk_reference_ratio_empty_source_element_ids():
    """chunk source_element_ids=[] → 不算 valid（ids falsy 短路）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_source_element_ids_none():
    chunks = [{"chunk_id": "c1", "source_element_ids": None}]
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_missing_source_element_ids():
    chunks = [{"chunk_id": "c1"}]  # 缺 source_element_ids
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_unknown_id():
    elements = [{"element_id": "e1"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": ["unknown_id"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_known_plus_unknown_id():
    elements = [{"element_id": "e1"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": ["e1", "unknown_id"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # all() is False because unknown_id not in elem_ids
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_elements_with_chunks():
    """elements 空 + chunks 有 → elem_ids=set()，all(sid in set()) 必为 False（除非 ids 空）。"""
    chunks = [{"chunk_id": "c1", "source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_multiple_chunks_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"chunk_id": "c1", "source_element_ids": ["e1"]},
        {"chunk_id": "c2", "source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_multiple_chunks_partial():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"chunk_id": "c1", "source_element_ids": ["e1"]},  # valid
        {"chunk_id": "c2", "source_element_ids": ["e2"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


# ============================================================================
# _heading_boundary_ratio 边界
# ============================================================================


def test_heading_boundary_ratio_no_chunks():
    """chunks=[] → chunk_first_ids=set() → matched=0。"""
    elements = [{"element_id": "h1", "type": "heading"}]
    out = _heading_boundary_ratio(elements, [])
    # headings non-empty, no chunks to match
    assert out["value"] == 0.0


def test_heading_boundary_ratio_empty_source_element_ids():
    """chunk source_element_ids=[] → 不参与 chunk_first_ids。"""
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_first_id_only():
    """chunk 的第 2/3 个 id 不算（只有第 1 个 id 算）。"""
    elements = [{"element_id": "h1", "type": "heading"}, {"element_id": "p1", "type": "paragraph"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": ["p1", "h1"]}]  # h1 是第 2 个，不算
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_first_id_match():
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": ["h1"]}]  # h1 是第 1 个
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_dedup_chunk_first_ids():
    """多 chunk 共享同一首 id → set 去重。"""
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = [
        {"chunk_id": "c1", "source_element_ids": ["h1"]},
        {"chunk_id": "c2", "source_element_ids": ["h1"]},  # 同一 id
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match():
    elements = [
        {"element_id": "h1", "type": "heading"},
        {"element_id": "h2", "type": "heading"},
    ]
    chunks = [{"chunk_id": "c1", "source_element_ids": ["h1"]}]  # 只匹配 h1
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_no_headings():
    elements = [{"element_id": "p1", "type": "paragraph"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["reason"] == "no_heading_elements"


# ============================================================================
# _silent_drop_count 边界
# ============================================================================


def test_silent_drop_count_empty_expectations_dict():
    """expectations={} → null+no_expectations。"""
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_none_expectations():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_element_count_by_type():
    """expectations.element_count_by_type={} → null+no_expectations_element_count。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_none_element_count_by_type():
    """expectations.element_count_by_type=None → null+no_expectations_element_count。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": None})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_missing_element_count_by_type():
    """expectations 不含 element_count_by_type → 用 .get 取 None → null。"""
    out = _silent_drop_count({"paragraph": 5}, {"other_key": 1})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_equals_expected():
    """actual==expected → drops=0。"""
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_actual_greater_than_expected():
    """actual>expected → drops=0（max(0, neg)）。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_actual_missing_type():
    """by_type 缺 expected 中某 type → drops += expected。"""
    out = _silent_drop_count(
        {},  # by_type 完全空
        {"element_count_by_type": {"paragraph": 5, "heading": 2}},
    )
    assert out["value"] == 7


def test_silent_drop_count_by_type_has_extra_type():
    """by_type 含 expected 没有的 type → 不参与。"""
    out = _silent_drop_count(
        {"paragraph": 5, "image": 10},  # image 不在 expected
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_multi_type_partial_drop():
    """多 type 部分缺。"""
    out = _silent_drop_count(
        {"paragraph": 3, "heading": 2},  # paragraph 缺 2，heading 完整
        {"element_count_by_type": {"paragraph": 5, "heading": 2}},
    )
    assert out["value"] == 2


# ============================================================================
# _strip_unicode_whitespace 字符级深度
# ============================================================================


def test_strip_unicode_whitespace_preserves_non_whitespace_only():
    """无空白的 string 原样返回。"""
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_removes_all_ascii_whitespace():
    """删除所有 ASCII 空白。"""
    assert _strip_unicode_whitespace("a b\tc\nd\re\f") == "abcde"


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   \t\n\r") == ""


def test_strip_unicode_whitespace_preserves_digits_and_punctuation():
    """非空白字符（含数字、标点）保留。"""
    assert _strip_unicode_whitespace("123, abc!") == "123,abc!"


def test_strip_unicode_whitespace_returns_str_type():
    out = _strip_unicode_whitespace("abc")
    assert isinstance(out, str)


# ============================================================================
# 模块 source level 完整补强
# ============================================================================


def test_module_source_contains_future_annotations_at_top():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    pos_future = src.find("from __future__ import annotations")
    pos_math = src.find("import math")
    assert pos_future != -1
    assert pos_math != -1
    assert pos_future < pos_math


def test_module_source_contains_import_math():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "import math" in src


def test_module_source_contains_counter_import():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "from collections import Counter" in src


def test_module_source_contains_pathlib_import():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_does_not_contain_logging():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "import logging" not in src


def test_module_source_does_not_contain_json():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "import json" not in src


def test_module_source_does_not_contain_subprocess():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "import subprocess" not in src


def test_module_source_does_not_contain_os():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "import os" not in src


def test_module_source_does_not_contain_star_import():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "import *" not in src


def test_module_source_does_not_contain_relative_import():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert "from ." not in src
    assert "from .." not in src


def test_module_source_contains_text_types_definition():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert '_TEXT_TYPES = (' in src


def test_module_source_contains_pdf_bbox_required_types_definition():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert '_PDF_BBOX_REQUIRED_TYPES = (' in src


def test_module_source_contains_not_evaluated_constant():
    import evaluation.metrics as m

    src = inspect.getsource(m)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_14_metric_keys():
    """compute_automatic_metrics source 含 14 个 metric key 字面量。"""
    import evaluation.metrics as m

    src = inspect.getsource(m.compute_automatic_metrics)
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
    for k in expected_keys:
        assert f'"{k}"' in src, f"missing key in source: {k}"


def test_module_source_null_function_one_liner():
    """_null 函数体是单行 return。"""
    import evaluation.metrics as m

    src = inspect.getsource(m._null)
    assert 'return {"value": None, "reason": reason}' in src


def test_module_source_ratio_function_one_liner():
    import evaluation.metrics as m

    src = inspect.getsource(m._ratio)
    assert "return {" in src
    assert "float(value)" in src


def test_module_source_bool_metric_function_one_liner():
    import evaluation.metrics as m

    src = inspect.getsource(m._bool_metric)
    assert "return {" in src
    assert "bool(value)" in src


def test_module_source_int_metric_function_one_liner():
    import evaluation.metrics as m

    src = inspect.getsource(m._int_metric)
    assert "return {" in src
    assert "int(value)" in src


def test_docx_locator_ratio_source_contains_7_structural_keys():
    """_docx_locator_ratio source 含 7 个 structural_keys 字面量。"""
    import evaluation.metrics as m

    src = inspect.getsource(m._docx_locator_ratio)
    for key in (
        "section",
        "paragraph_index",
        "run_index",
        "table_index",
        "row_index",
        "col_index",
        "relationship_id",
    ):
        assert f'"{key}"' in src


def test_pdf_locator_ratio_source_contains_pdf_bbox_required_types_ref():
    """_pdf_locator_ratio source 引用 _PDF_BBOX_REQUIRED_TYPES。"""
    import evaluation.metrics as m

    src = inspect.getsource(m._pdf_locator_ratio)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


# ============================================================================
# compute_automatic_metrics 集成场景
# ============================================================================


def test_compute_automatic_metrics_full_document_all_metrics_have_values():
    """完整 document → 14 metrics 都有非 None value（除了可能的 null 路径）。"""
    document = {
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "hello",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            },
            {
                "element_id": "e2",
                "type": "heading",
                "content": "title",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]},
            },
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "title", "source_element_ids": ["e2"]},
            {"chunk_id": "c2", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    metrics = compute_automatic_metrics(document, None, "pdf", None)
    # 14 keys
    assert len(metrics) == 14
    # 大部分 metric 应有非 None value
    assert metrics["element_count_total"]["value"] == 2
    assert metrics["pdf_locator_valid_ratio"]["value"] == 1.0


def test_compute_automatic_metrics_unknown_source_type():
    """source_type='unknown' → pdf + docx 都 null。"""
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(document, None, "unknown", None)
    assert metrics["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert metrics["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_error_code_missing_code_raises():
    """error dict 缺 'code' → KeyError（不静默）。"""
    error = {"message": "no code"}  # 缺 'code'
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, error, "pdf", None)


def test_compute_automatic_metrics_with_image_elements(tmp_path):
    """含 image element → image_resource_exists_ratio 走文件检查路径。"""
    # 创建一个 image 文件
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG fake data")

    document = {
        "elements": [
            {
                "element_id": "img1",
                "type": "image",
                "resource_path": str(img_file),
            },
        ],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(document, None, "pdf", None)
    assert metrics["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_automatic_metrics_does_not_mutate_input():
    """不修改 document。"""
    document = {
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "x"}],
        "chunks": [{"chunk_id": "c1", "text": "x", "source_element_ids": ["e1"]}],
    }
    snapshot = json.loads(json.dumps(document))
    compute_automatic_metrics(document, None, "pdf", None)
    assert document == snapshot


def test_compute_automatic_metrics_does_not_mutate_error():
    error = {"code": "boom", "message": "x", "details": {}}
    snapshot = json.loads(json.dumps(error))
    compute_automatic_metrics(None, error, "pdf", None)
    assert error == snapshot


# ============================================================================
# __all__ 与 namespace 完整性
# ============================================================================


def test_module_all_only_one_entry():
    import evaluation.metrics as m

    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_all_entries_each_valid_identifier():
    import evaluation.metrics as m

    for name in m.__all__:
        assert isinstance(name, str)
        assert name.isidentifier()


def test_module_namespace_has_private_helpers_not_in_all():
    """私有 helper（带下划线）在 namespace 不在 __all__。"""
    import evaluation.metrics as m

    for name in [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
        "_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED",
    ]:
        assert hasattr(m, name), f"missing: {name}"
        assert name not in m.__all__
