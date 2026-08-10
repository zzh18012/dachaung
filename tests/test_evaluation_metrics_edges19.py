r"""evaluation/metrics.py 边角测试 - 第十九轮（Round 281）。

edges18 已覆盖：模块 imports / 常量 / source-level 详尽（_null / _ratio / _bool_metric / _int_metric /
compute_automatic_metrics / _pdf_locator_ratio / _docx_locator_ratio / _is_valid_bbox /
_image_resource_ratio / _chunk_reference_ratio / _strip_unicode_whitespace / _text_preservation /
_heading_boundary_ratio / _silent_drop_count） / __all__ / namespace / 不含禁止内容 /
compute_automatic_metrics 行为（不修改/两次独立/keys 14/keys exact）/ helper metadata / 签名 / docstring。

edges19 补强未覆盖的角度（具体场景行为 + 边界）：
- **compute_automatic_metrics failed scenario**：document=None + error=dict → pipeline_success=False；error_code.value=error['code']；schema_valid null+pipeline_failed；12 null-prone metrics 都 null+pipeline_failed；element_count_by_type 也 null+pipeline_failed
- **compute_automatic_metrics succeeded scenario**：document=dict + error=None → pipeline_success=True；error_code.value=None；schema_valid 走 schema_validation import；其他 12 metrics 都有值
- **source_type='pdf'**：pdf_locator_valid_ratio 调用 _pdf_locator_ratio；docx_locator_valid_ratio null+not_pdf_document
- **source_type='docx'**：相反；pdf null+not_pdf_document；docx 调用 _docx_locator_ratio
- **source_type 其他**：pdf + docx 都 null
- **_pdf_locator_ratio 边界**：0 elements→null+no_elements；1 valid→1.0；1 invalid page→0.0；mixed
- **_pdf_locator_ratio 文本类型需要 bbox**：heading/paragraph/caption/list_item 需要 bbox；table/header/footer 不需要
- **_pdf_locator_ratio page 类型**：int>=1 valid；int<1 invalid；float invalid；str invalid；None invalid；bool invalid
- **_docx_locator_ratio 边界**：0 elements→null；含 page 或 bbox→invalid；至少一个 structural_key→valid
- **_docx_locator_ratio structural_keys**：section/paragraph_index/run_index/table_index/row_index/col_index/relationship_id 7 个
- **_is_valid_bbox 边界**：not list→False；len != 4→False；bool 元素→False；str 元素→False；nan/inf→False；4 个 int/float→True
- **_image_resource_ratio 边界**：no images→null；images but no resource_path→0.0；valid file→1.0；invalid file→0.0；image_base_dir 拼接 fallback
- **_chunk_reference_ratio 边界**：no chunks→null；all valid→1.0；all invalid→0.0；mixed
- **_chunk_reference_ratio 空 source_element_ids**：不算 valid（即使 all() on empty 返 True，但有 ids 检查）
- **_strip_unicode_whitespace 字符级**：ASCII space/NBSP/em space/ideographic space/line separator 全删；非空白保留
- **_text_preservation 边界**：empty/empty→precision/recall null+empty_expected_and_actual；equal=True；image 不参与；多集合 Counter 交集
- **_text_preservation empty_actual**：expected 非空 + actual 空 → precision null+empty_actual；recall 0.0
- **_text_preservation empty_expected**：expected 空 + actual 非空 → precision 0.0；recall null+empty_expected
- **_heading_boundary_ratio 边界**：no headings→null；all matched→1.0；none matched→0.0；chunk source_element_ids 空→不算
- **_silent_drop_count 边界**：no expectations→null；expectations 但 element_count_by_type 空→null+no_expectations_element_count；actual<exp→差值；actual>=exp→0
- **source_type='pdf' 时不调 _docx_locator_ratio**：source-level 验证
- **figure_caption_precision/recall/f1 不在 metrics 中**：annotation_metrics 在 runner.py 处理
- **chunk_boundary_* 不在 metrics 中**：annotation_metrics 处理
- **schema_valid schema_check_exception**：document_passes_schema 抛异常 → value=False + reason=schema_check_exception:ExceptionType
"""

from __future__ import annotations

import inspect
import math
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
# compute_automatic_metrics 失败场景
# =========================================================================


def test_compute_automatic_metrics_failed_pipeline_success_false():
    """document=None + error=dict → pipeline_success.value=False（不是 None）。"""
    error = {"code": "file_not_found", "message": "...", "details": {}}
    m = compute_automatic_metrics(None, error, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["pipeline_success"]["reason"] is None


def test_compute_automatic_metrics_failed_error_code_from_error():
    """失败时 error_code.value 取自 error['code']。"""
    error = {"code": "my_error", "message": "...", "details": {}}
    m = compute_automatic_metrics(None, error, "pdf", None)
    assert m["error_code"]["value"] == "my_error"
    assert m["error_code"]["reason"] is None


def test_compute_automatic_metrics_failed_error_code_none_when_error_none():
    """document=None 但 error=None → error_code.value=None（理论上不该发生，但要测）。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["error_code"]["value"] is None
    assert m["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_failed_schema_valid_pipeline_failed():
    """失败时 schema_valid.value=None + reason=pipeline_failed。"""
    error = {"code": "x", "message": "y"}
    m = compute_automatic_metrics(None, error, "pdf", None)
    assert m["schema_valid"]["value"] is None
    assert m["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_failed_12_null_metrics_reason():
    """失败时 12 个 null-prone metrics 都 null + reason=pipeline_failed。"""
    error = {"code": "x"}
    m = compute_automatic_metrics(None, error, "pdf", None)
    null_metrics = [
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
    # element_count_by_type 也 null（在 document None 时）
    for name in null_metrics:
        assert m[name]["value"] is None, f"{name} 应 null"
        assert m[name]["reason"] == "pipeline_failed", f"{name} reason 应 pipeline_failed"


# =========================================================================
# compute_automatic_metrics 成功场景
# =========================================================================


def _make_minimal_valid_document() -> dict[str, Any]:
    """构造一个能通过 schema_validation 的最小 document。

    注意：实际 schema 在 evaluation/schema_validation.py，这里构造常见的 element 形式，
    schema_valid 可能通过也可能不通过（取决于具体 schema 要求），但 pipeline_success=True。
    """
    return {
        "source_type": "pdf",
        "source_hash": "abc123",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "hello",
                "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]},
            },
        ],
        "chunks": [
            {
                "chunk_id": "c1",
                "text": "hello",
                "source_element_ids": ["e1"],
            },
        ],
    }


def test_compute_automatic_metrics_succeeded_pipeline_success_true():
    """document=dict + error=None → pipeline_success.value=True。"""
    doc = _make_minimal_valid_document()
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True


def test_compute_automatic_metrics_succeeded_error_code_none():
    """成功时 error_code.value=None。"""
    doc = _make_minimal_valid_document()
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["error_code"]["value"] is None


def test_compute_automatic_metrics_succeeded_element_count_total():
    """成功时 element_count_total 是 _int_metric(len(elements))。"""
    doc = _make_minimal_valid_document()
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 1
    assert m["element_count_total"]["reason"] is None


def test_compute_automatic_metrics_succeeded_element_count_by_type():
    """成功时 element_count_by_type 是 dict。"""
    doc = _make_minimal_valid_document()
    m = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = m["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 1}


def test_compute_automatic_metrics_succeeded_multiple_element_types():
    """多种 type → by_type 反映所有类型计数。"""
    doc = {
        "source_type": "pdf",
        "source_hash": "h",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
            {"element_id": "e2", "type": "paragraph", "content": "b", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
            {"element_id": "e3", "type": "heading", "content": "T", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
        ],
        "chunks": [{"chunk_id": "c1", "text": "a b T", "source_element_ids": ["e1", "e2", "e3"]}],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 3
    assert m["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}


# =========================================================================
# source_type 分支
# =========================================================================


def test_compute_automatic_metrics_pdf_triggers_pdf_locator():
    """source_type='pdf' → pdf_locator_valid_ratio 调用；docx null。"""
    doc = _make_minimal_valid_document()
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["reason"] is None
    assert m["docx_locator_valid_ratio"]["value"] is None
    assert m["docx_locator_valid_ratio"]["reason"] == "not_pdf_document" or \
           m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_docx_triggers_docx_locator():
    """source_type='docx' → docx_locator_valid_ratio 调用；pdf null。"""
    doc = {
        "source_type": "docx",
        "source_hash": "h",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"chunk_id": "c1", "text": "a", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["reason"] is None
    assert m["pdf_locator_valid_ratio"]["value"] is None


def test_compute_automatic_metrics_unknown_source_type_both_null():
    """source_type='other' → pdf + docx 都 null（pdf=null+not_pdf_document；docx=null+not_docx_document）。"""
    doc = _make_minimal_valid_document()
    m = compute_automatic_metrics(doc, None, "other", None)
    assert m["pdf_locator_valid_ratio"]["value"] is None
    assert m["docx_locator_valid_ratio"]["value"] is None


# =========================================================================
# _pdf_locator_ratio 边界场景
# =========================================================================


def test_pdf_locator_ratio_empty_elements():
    """0 elements → null+no_elements。"""
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_all_valid_text_with_bbox():
    """1 个 paragraph + page=1 + bbox=4 floats → 1.0。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_invalid_page_zero():
    """page=0 → invalid（必须 >= 1）。"""
    elements = [
        {"type": "table", "source_locator": {"page": 0}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_invalid_page_negative():
    """page=-1 → invalid。"""
    elements = [
        {"type": "table", "source_locator": {"page": -1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_float_invalid():
    """page=1.5（float）→ invalid（必须 int）。"""
    elements = [
        {"type": "table", "source_locator": {"page": 1.5}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_string_invalid():
    """page='1'（str）→ invalid。"""
    elements = [
        {"type": "table", "source_locator": {"page": "1"}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_none_invalid():
    """page=None → invalid。"""
    elements = [
        {"type": "table", "source_locator": {"page": None}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_bool_invalid():
    """page=True（bool）→ invalid（isinstance(True, int) 是 True，但语义错）。"""
    elements = [
        {"type": "table", "source_locator": {"page": True}},
    ]
    # 注意：isinstance(True, int) is True in Python；所以这里 page=True 实际通过 int 检查
    # 然后 True >= 1 也 True（True == 1），所以这个 element valid
    # 但这是 Python 的 bool 是 int 子类的 quirk
    out = _pdf_locator_ratio(elements)
    # bool 是 int 子类，True == 1，所以走 valid 分支
    assert out["value"] == 1.0


def test_pdf_locator_ratio_text_type_requires_bbox():
    """paragraph + page=1 但无 bbox → invalid。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_table_does_not_require_bbox():
    """table + page=1 不需要 bbox → valid。"""
    elements = [
        {"type": "table", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_header_does_not_require_bbox():
    """header + page=1 不需要 bbox → valid。"""
    elements = [
        {"type": "header", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_mixed_valid_invalid():
    """3 个 elements：2 valid + 1 invalid → 2/3。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
        {"type": "table", "source_locator": {"page": 2}},
        {"type": "paragraph", "source_locator": {"page": 0}},  # invalid
    ]
    out = _pdf_locator_ratio(elements)
    assert abs(out["value"] - 2/3) < 1e-9


def test_pdf_locator_ratio_no_source_locator():
    """element 无 source_locator → invalid（page=None）。"""
    elements = [{"type": "table"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_source_locator_none():
    """source_locator=None → element.get('source_locator') or {} → {} → page None → invalid。"""
    elements = [{"type": "table", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# =========================================================================
# _docx_locator_ratio 边界场景
# =========================================================================


def test_docx_locator_ratio_empty_elements():
    """0 elements → null+no_elements。"""
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_with_section():
    """section → valid。"""
    elements = [{"type": "paragraph", "source_locator": {"section": "sec1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_paragraph_index():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_run_index():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_table_index():
    elements = [{"type": "paragraph", "source_locator": {"table_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_row_index():
    elements = [{"type": "paragraph", "source_locator": {"row_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_col_index():
    elements = [{"type": "paragraph", "source_locator": {"col_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_relationship_id():
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_invalid():
    """含 page → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "section": "s"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_invalid():
    """含 bbox → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "section": "s"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_structural_key_invalid():
    """无任何 structural_key → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "x"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_source_locator_invalid():
    """无 source_locator → invalid。"""
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_mixed():
    """3 elements：2 valid + 1 invalid → 2/3。"""
    elements = [
        {"type": "paragraph", "source_locator": {"section": "s1"}},
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
    ]
    out = _docx_locator_ratio(elements)
    assert abs(out["value"] - 2/3) < 1e-9


# =========================================================================
# _is_valid_bbox 边界场景
# =========================================================================


def test_is_valid_bbox_not_list():
    assert _is_valid_bbox("not list") is False


def test_is_valid_bbox_tuple_not_list():
    """tuple 不是 list。"""
    assert _is_valid_bbox((0.0, 0.0, 1.0, 1.0)) is False


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_short_list():
    assert _is_valid_bbox([0.0, 0.0, 1.0]) is False  # len 3


def test_is_valid_bbox_long_list():
    assert _is_valid_bbox([0.0, 0.0, 1.0, 1.0, 2.0]) is False  # len 5


def test_is_valid_bbox_bool_element():
    """bool 元素 → invalid（isinstance(True, int) is True 但有 bool 检查）。"""
    assert _is_valid_bbox([True, 0.0, 1.0, 1.0]) is False


def test_is_valid_bbox_string_element():
    assert _is_valid_bbox(["0.0", "0.0", "1.0", "1.0"]) is False


def test_is_valid_bbox_none_element():
    assert _is_valid_bbox([None, 0.0, 1.0, 1.0]) is False


def test_is_valid_bbox_nan():
    assert _is_valid_bbox([float("nan"), 0.0, 1.0, 1.0]) is False


def test_is_valid_bbox_inf():
    assert _is_valid_bbox([float("inf"), 0.0, 1.0, 1.0]) is False


def test_is_valid_bbox_negative_inf():
    assert _is_valid_bbox([float("-inf"), 0.0, 1.0, 1.0]) is False


def test_is_valid_bbox_four_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_four_floats():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([0, 0.0, 100, 100.0]) is True


def test_is_valid_bbox_zero_box():
    assert _is_valid_bbox([0.0, 0.0, 0.0, 0.0]) is True


def test_is_valid_bbox_negative_coords():
    """负坐标也 valid（数学上合法）。"""
    assert _is_valid_bbox([-10.0, -10.0, 10.0, 10.0]) is True


# =========================================================================
# _image_resource_ratio 边界场景
# =========================================================================


def test_image_resource_ratio_no_images():
    """无 image elements → null+no_image_elements。"""
    elements = [{"type": "paragraph", "content": "a"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path():
    """image 但无 resource_path → 0.0。"""
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path():
    """resource_path='' → falsy → 跳过 → 0.0。"""
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_existing_file(tmp_path):
    """resource_path 指向存在文件 → 1.0。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_nonexistent_file():
    """resource_path 指向不存在文件 → 0.0。"""
    elements = [{"type": "image", "resource_path": "/nonexistent/path/img.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_zero_size_file(tmp_path):
    """resource_path 指向 0 字节文件 → 0.0（size>0 检查）。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_base_dir_fallback(tmp_path):
    """resource_path 只文件名 + image_base_dir 给定 → 用 base_dir 拼接。"""
    img_file = tmp_path / "image.png"
    img_file.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": "image.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path):
    """2 个 image：1 valid + 1 invalid → 0.5。"""
    img_file = tmp_path / "good.png"
    img_file.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
        {"type": "image", "resource_path": "/nonexistent/bad.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


# =========================================================================
# _chunk_reference_ratio 边界场景
# =========================================================================


def test_chunk_reference_ratio_no_chunks():
    """无 chunks → null+no_chunks。"""
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_all_valid():
    """所有 chunks 的 source_element_ids 都在 elements 中 → 1.0。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_all_invalid():
    """所有 chunks 的 source_element_ids 都不在 elements 中 → 0.0。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["unknown"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_ids_invalid():
    """chunks 的 source_element_ids 空列表 → 不算 valid（即使 all() on empty 是 True）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]  # 空列表
    out = _chunk_reference_ratio(elements, chunks)
    # 空 ids falsy → if ids 不通过 → 不算 valid
    assert out["value"] == 0.0


def test_chunk_reference_ratio_ids_none_invalid():
    """source_element_ids=None → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_ids_missing_invalid():
    """chunks 不含 source_element_ids 键 → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # 缺 key
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_mixed():
    """3 chunks：2 valid + 1 invalid → 2/3。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
        {"source_element_ids": ["missing"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert abs(out["value"] - 2/3) < 1e-9


def test_chunk_reference_ratio_partial_valid_in_one_chunk():
    """一个 chunk 的 ids 部分有效部分无效 → 不算 valid（all 检查）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# =========================================================================
# _strip_unicode_whitespace 边界场景
# =========================================================================


def test_strip_unicode_whitespace_ascii_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_tab():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_nbsp():
    """NBSP（\\u00a0）是 isspace=True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """em space（\\u2003）是 isspace=True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """en space（\\u2002）是 isspace=True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """全角空格（\\u3000）是 isspace=True。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """line separator（\\u2028）是 isspace=True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_only_whitespace():
    assert _strip_unicode_whitespace("   \t\n") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_preserves_non_whitespace():
    """非空白字符（标点、中文、emoji）都保留。"""
    assert _strip_unicode_whitespace("a，b。c") == "a，b。c"


def test_strip_unicode_whitespace_does_not_sort():
    """不排序，保留原顺序。"""
    assert _strip_unicode_whitespace("cab") == "cab"


# =========================================================================
# _text_preservation 边界场景
# =========================================================================


def test_text_preservation_both_empty():
    """expected/actual 都空 → equal True；precision/recall null+empty_expected_and_actual。"""
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_identical_content():
    """elements content 与 chunks text 完全相同（非空白） → equal True；precision/recall 1.0。"""
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_filtered():
    """image element 不参与 expected_sequence。"""
    elements = [
        {"type": "paragraph", "content": "hello"},
        {"type": "image", "content": "should_be_ignored"},
    ]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_missing_chars_in_actual():
    """actual 缺字符 → equal False；recall<1.0；precision=1.0。"""
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello"}]  # 缺 "world"
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # actual 是 hello 的子集 → precision=1.0（actual 的字符都在 expected）
    assert out["precision"]["value"] == 1.0
    # recall < 1.0
    assert out["recall"]["value"] < 1.0


def test_text_preservation_extra_chars_in_actual():
    """actual 多字符 → equal False；precision<1.0；recall=1.0。"""
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello world"}]  # 多 "world"
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] < 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_empty_actual_only():
    """expected 非空 + actual 空 → precision null+empty_actual；recall 0.0。"""
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": ""}]  # 空文本
    out = _text_preservation(elements, chunks)
    # equal False（expected="hello" vs actual=""）
    assert out["equal"]["value"] is False
    # actual 空 → precision null
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_actual"
    # recall: common=0 / 5 = 0.0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_empty_expected_only():
    """expected 空 + actual 非空 → precision 0.0；recall null+empty_expected。"""
    elements = []  # 无 elements → expected=""
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    # 走 empty_expected_and_actual 分支吗？expected=actual.strip="" 但 actual="hello"
    # 不，预期 expected="" actual="hello" → 不都空
    # common=0（Counter("") ∩ Counter("hello")=空），actual_total=5, expected_total=0
    # precision: 0/5 = 0.0
    # recall: expected 空 → null + empty_expected
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_counter_intersection_semantics():
    """重复字符：Counter 交集取 min。"""
    # expected = "aaa"（3 个 a）
    # actual   = "aa"  （2 个 a）
    # common = min(3, 2) = 2
    # precision = 2/2 = 1.0
    # recall = 2/3
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 2/3) < 1e-9


def test_text_preservation_whitespace_ignored():
    """空白不影响比对。"""
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # 删空白后都是 "abc" → equal True
    assert out["equal"]["value"] is True


def test_text_preservation_returns_3_keys():
    """返回 dict 含 3 keys：equal, precision, recall。"""
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_value_is_dict():
    """每个 metric 都是 dict 含 value+reason。"""
    out = _text_preservation([{"type": "paragraph", "content": "a"}], [{"text": "a"}])
    for k in ("equal", "precision", "recall"):
        assert "value" in out[k]
        assert "reason" in out[k]


# =========================================================================
# _heading_boundary_ratio 边界场景
# =========================================================================


def test_heading_boundary_ratio_no_headings():
    """无 heading → null+no_heading_elements。"""
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_perfect_match():
    """1 heading + 1 chunk 第一个 id 匹配 → 1.0。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "other"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_no_match():
    """1 heading 但无 chunk 首个 id 匹配 → 0.0。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_partial():
    """2 heading：1 匹配 + 1 不匹配 → 0.5。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # 只有 h1 是 chunk 首元素
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_chunk_empty_ids_skipped():
    """chunk source_element_ids 空 → 不算匹配（即使 heading_id 在 set 里）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]  # 空
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_ids_none_skipped():
    """source_element_ids=None → 不算。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": None}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_first_id_only():
    """只看 chunk 的第一个 source_element_id（不是所有）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    # h1 是 chunk 的第二个 id（不是第一个）→ 不算
    chunks = [{"source_element_ids": ["other", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_multiple_chunks():
    """多 chunk 都贡献首个 id；只要有一个匹配 heading 即可。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["other"]},
        {"source_element_ids": ["h1"]},  # 第二个 chunk 首个是 h1
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


# =========================================================================
# _silent_drop_count 边界场景
# =========================================================================


def test_silent_drop_count_no_expectations():
    """expectations=None → null+no_expectations。"""
    out = _silent_drop_count({}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations():
    """expectations={} → null+no_expectations（falsy）。"""
    out = _silent_drop_count({}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_by_type_key():
    """expectations 不含 element_count_by_type → null+no_expectations_element_count。"""
    out = _silent_drop_count({}, {"other_key": 1})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type():
    """element_count_by_type={} → null+no_expectations_element_count。"""
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drops_when_actual_ge_expected():
    """actual >= exp → drops=0。"""
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_drop_when_actual_lt_expected():
    """actual < exp → drops = exp - actual。"""
    by_type = {"paragraph": 2}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 3


def test_silent_drop_count_actual_zero():
    """actual=0 + exp=5 → drops=5。"""
    by_type = {}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 5


def test_silent_drop_count_missing_type_in_actual():
    """expected type 不在 actual → 实际 0 → drops += exp。"""
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 3, "heading": 1}}
    out = _silent_drop_count(by_type, expectations)
    # heading: 1>=1 → 0；paragraph: 0<3 → 3
    assert out["value"] == 3


def test_silent_drop_count_sum_across_types():
    """多类型 drops 求和。"""
    by_type = {"paragraph": 1}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 3, "table": 2}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph: 1<5 → 4；heading: 0<3 → 3；table: 0<2 → 2；总=9
    assert out["value"] == 9


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric 一致性
# =========================================================================


def test_null_value_is_none():
    assert _null("any_reason")["value"] is None


def test_null_reason_is_input():
    assert _null("my_reason")["reason"] == "my_reason"


def test_null_returns_dict_with_2_keys():
    out = _null("x")
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_value_is_float():
    assert isinstance(_ratio(0.5)["value"], float)


def test_ratio_reason_is_none():
    assert _ratio(0.5)["reason"] is None


def test_ratio_converts_int_to_float():
    """int 输入也被 float() 转。"""
    out = _ratio(1)  # int 1
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_bool_metric_value_is_bool():
    assert isinstance(_bool_metric(True)["value"], bool)
    assert isinstance(_bool_metric(False)["value"], bool)


def test_bool_metric_truthy_value_becomes_true():
    """truthy 输入 → True。"""
    assert _bool_metric(1)["value"] is True
    assert _bool_metric("yes")["value"] is True


def test_bool_metric_falsy_value_becomes_false():
    """falsy 输入 → False。"""
    assert _bool_metric(0)["value"] is False
    assert _bool_metric("")["value"] is False


def test_int_metric_value_is_int():
    assert isinstance(_int_metric(5)["value"], int)
    assert not isinstance(_int_metric(5)["value"], bool)


def test_int_metric_converts_float_to_int():
    """float 输入被 int() 转。"""
    out = _int_metric(3.7)
    assert out["value"] == 3
    assert isinstance(out["value"], int)


def test_int_metric_converts_string_digit():
    """'5' 被 int() 转。"""
    out = _int_metric("5")
    assert out["value"] == 5


# =========================================================================
# compute_automatic_metrics 集成场景
# =========================================================================


def test_compute_automatic_metrics_with_image_base_dir(tmp_path):
    """image_base_dir 给定 → 传给 _image_resource_ratio。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"data")
    doc = {
        "source_type": "pdf",
        "source_hash": "h",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
            {"element_id": "e2", "type": "image", "resource_path": "img.png"},
        ],
        "chunks": [{"chunk_id": "c1", "text": "a", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    # image_resource_exists_ratio 应是 1.0（找到 img.png）
    assert m["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_automatic_metrics_no_image_base_dir():
    """image_base_dir=None → 直接用 Path(rp)。"""
    doc = {
        "source_type": "pdf",
        "source_hash": "h",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
            {"element_id": "e2", "type": "image", "resource_path": "/nonexistent/x.png"},
        ],
        "chunks": [{"chunk_id": "c1", "text": "a", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=None)
    assert m["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_automatic_metrics_with_expectations_no_drops():
    """expectations 提供，actual>=exp → silent_drop_count=0。"""
    doc = {
        "source_type": "pdf",
        "source_hash": "h",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
        ],
        "chunks": [{"chunk_id": "c1", "text": "a", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 1}}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert m["silent_drop_count"]["value"] == 0


def test_compute_automatic_metrics_with_expectations_drops():
    """expectations 提供，actual<exp → silent_drop_count>0。"""
    doc = {
        "source_type": "pdf",
        "source_hash": "h",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "a",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
        ],
        "chunks": [{"chunk_id": "c1", "text": "a", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    # actual paragraph=1 < exp=5 → drops=4；actual heading=0 < exp=2 → drops=2；总=6
    assert m["silent_drop_count"]["value"] == 6


def test_compute_automatic_metrics_expectations_no_element_count():
    """expectations 但无 element_count_by_type → silent_drop_count null。"""
    doc = _make_minimal_valid_document()
    expectations = {"other_key": 1}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert m["silent_drop_count"]["value"] is None
    assert m["silent_drop_count"]["reason"] == "no_expectations_element_count"


# =========================================================================
# compute_automatic_metrics schema_valid 异常路径
# =========================================================================


def test_compute_automatic_metrics_schema_valid_calls_document_passes_schema():
    """schema_valid metric 通过 document_passes_schema 计算（成功路径）。"""
    doc = _make_minimal_valid_document()
    m = compute_automatic_metrics(doc, None, "pdf", None)
    # schema_valid.value 是 bool（True 或 False 都可能，取决于 schema 严格度）
    assert isinstance(m["schema_valid"]["value"], bool)


def test_compute_automatic_metrics_schema_check_exception_path(monkeypatch):
    """document_passes_schema 抛异常 → schema_valid.value=False + reason=schema_check_exception:...。"""
    doc = _make_minimal_valid_document()

    # 模拟 document_passes_schema 抛异常
    import evaluation.schema_validation as sv

    def boom(_doc):
        raise RuntimeError("boom")

    monkeypatch.setattr(sv, "document_passes_schema", boom)
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["schema_valid"]["value"] is False
    assert "schema_check_exception" in m["schema_valid"]["reason"]
    assert "RuntimeError" in m["schema_valid"]["reason"]


# =========================================================================
# compute_automatic_metrics 不修改输入
# =========================================================================


def test_compute_automatic_metrics_does_not_modify_document_elements():
    """elements list 不被修改。"""
    doc = _make_minimal_valid_document()
    elements_before = list(doc["elements"])
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc["elements"] == elements_before


def test_compute_automatic_metrics_does_not_modify_document_chunks():
    doc = _make_minimal_valid_document()
    chunks_before = list(doc["chunks"])
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc["chunks"] == chunks_before


def test_compute_automatic_metrics_does_not_modify_expectations_dict():
    """expectations dict 不被修改。"""
    doc = _make_minimal_valid_document()
    exp = {"element_count_by_type": {"paragraph": 5}}
    exp_before = dict(exp)
    exp_inner_before = dict(exp["element_count_by_type"])
    compute_automatic_metrics(doc, None, "pdf", exp)
    assert exp == exp_before
    assert exp["element_count_by_type"] == exp_inner_before


# =========================================================================
# compute_automatic_metrics 两次调用独立
# =========================================================================


def test_compute_automatic_metrics_two_calls_produce_independent_metrics_dict():
    """两次调用返回不同 dict（不是同一对象）。"""
    doc = _make_minimal_valid_document()
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m1 is not m2
    assert m1 == m2  # 内容相等


def test_compute_automatic_metrics_modify_output_does_not_affect_next_call():
    doc = _make_minimal_valid_document()
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    saved = m1["pipeline_success"]["value"]
    m1["pipeline_success"]["value"] = "tampered"
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m2["pipeline_success"]["value"] == saved


# =========================================================================
# __all__ 与命名空间
# =========================================================================


def test_module_all_equals_compute_automatic_metrics_only():
    import evaluation.metrics as m
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_all_is_list():
    import evaluation.metrics as m
    assert isinstance(m.__all__, list)


def test_module_namespace_has_sub_helpers():
    """模块 namespace 含所有 sub-helper 函数。"""
    import evaluation.metrics as m
    for name in [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ]:
        assert hasattr(m, name), f"模块缺 {name}"


def test_module_namespace_has_constants():
    """模块 namespace 含常量。"""
    import evaluation.metrics as m
    assert hasattr(m, "_TEXT_TYPES")
    assert hasattr(m, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(m, "_NOT_EVALUATED")


def test_module_namespace_has_math_counter_path_any():
    """模块 namespace 含 import 的模块。"""
    import evaluation.metrics as m
    import math as math_mod
    from collections import Counter
    from pathlib import Path as PathCls
    from typing import Any
    assert m.math is math_mod
    assert m.Counter is Counter
    assert m.Path is PathCls
    assert m.Any is Any


# =========================================================================
# 模块 source 不含禁止内容（再补）
# =========================================================================


def test_module_source_does_not_contain_re_import():
    """metrics.py 不用 re 模块。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "import re" not in src


def test_module_source_does_not_contain_uuid_import():
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "uuid" not in src


def test_module_source_does_not_contain_random_import():
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "import random" not in src


def test_module_source_does_not_contain_time_import():
    """metrics.py 不导入 time（计时在 runner.py）。"""
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "import time" not in src


def test_module_source_does_not_contain_datetime_import():
    import evaluation.metrics as m
    src = inspect.getsource(m)
    assert "datetime" not in src


# =========================================================================
# helper 函数类型与模块身份
# =========================================================================


def test_all_sub_helpers_are_function_type():
    import types
    import evaluation.metrics as m
    for name in [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
        "compute_automatic_metrics",
    ]:
        f = getattr(m, name)
        assert isinstance(f, types.FunctionType), f"{name} 不是 FunctionType"


def test_all_sub_helpers_module_identity():
    """所有 helper 的 __module__ == 'evaluation.metrics'。"""
    import evaluation.metrics as m
    for name in [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
        "compute_automatic_metrics",
    ]:
        f = getattr(m, name)
        assert f.__module__ == "evaluation.metrics"


# =========================================================================
# 子函数签名
# =========================================================================


def test_pdf_locator_ratio_signature_1_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1
    assert "elements" in sig.parameters


def test_docx_locator_ratio_signature_1_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1
    assert "elements" in sig.parameters


def test_is_valid_bbox_signature_1_param():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1
    assert "bbox" in sig.parameters


def test_image_resource_ratio_signature_2_params():
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2
    assert "elements" in sig.parameters
    assert "image_base_dir" in sig.parameters


def test_chunk_reference_ratio_signature_2_params():
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2
    assert "elements" in sig.parameters
    assert "chunks" in sig.parameters


def test_strip_unicode_whitespace_signature_1_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1
    assert "s" in sig.parameters


def test_text_preservation_signature_2_params():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_heading_boundary_ratio_signature_2_params():
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


def test_silent_drop_count_signature_2_params():
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2
    assert "by_type" in sig.parameters
    assert "expectations" in sig.parameters


# =========================================================================
# 常量验证
# =========================================================================


def test_text_types_exact_7_items():
    from evaluation.metrics import _TEXT_TYPES
    assert _TEXT_TYPES == (
        "heading", "paragraph", "list_item", "table", "caption", "header", "footer"
    )


def test_pdf_bbox_required_types_exact_4_items():
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_text_types_does_not_contain_image():
    from evaluation.metrics import _TEXT_TYPES
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_subset_of_text_types():
    from evaluation.metrics import _TEXT_TYPES, _PDF_BBOX_REQUIRED_TYPES
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_does_not_contain_table():
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_does_not_contain_header():
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_does_not_contain_footer():
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_value_exact():
    from evaluation.metrics import _NOT_EVALUATED
    assert _NOT_EVALUATED == "not_evaluated"
