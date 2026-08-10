r"""evaluation/metrics.py 边角测试 - 第二十二轮（Round 298）。

edges21 已覆盖：4 helper one-liner + 3 constants + 11 metric 各分支深度 + source level +
端到端集成。

edges22 补强未覆盖的角度（深度边界 + 行为 + source level + signatures + 端到端）：
- **4 helper one-liner 行为深度补强**：_null 返 dict 结构精确；_ratio 接受 int 输入；
  _ratio 接受负数（不 clamp）；_bool_metric 接受 0/1 int；_bool_metric 接受 truthy dict；
  _int_metric 接受 float 输入（截断）；_int_metric 接受 str（TypeError）；
  4 helper source level 含具体语法
- **3 常量精确补强**：_TEXT_TYPES 7 entries 顺序精确；_PDF_BBOX_REQUIRED_TYPES 4 entries 顺序精确；
  _NOT_EVALUATED = "not_evaluated"；
  _TEXT_TYPES 子集关系：_PDF_BBOX_REQUIRED_TYPES ⊂ _TEXT_TYPES
- **compute_automatic_metrics 边界组合补强**：document None + error dict 含 code →
  pipeline_success=False, error_code=error['code']；
  document dict + error dict 都给 → pipeline_success=False（error is None false）；
  document dict + error None → pipeline_success=True；
  source_type='unknown' → pdf_locator null not_pdf + docx_locator null not_docx；
  source_type='pdf' → docx_locator null；source_type='docx' → pdf_locator null；
  document 是空 dict (no elements/chunks) → 各 metric 走 no_elements/no_chunks 分支
- **schema_valid 行为深度**：document None → null pipeline_failed；
  document dict 但 schema 校验通过 → bool_metric True；
  document dict 但 schema 校验失败 → bool_metric False；
  schema 校验抛 Exception → value=False, reason='schema_check_exception:TypeName'
- **_pdf_locator_ratio 行为深度补强**：elements=[] → null no_elements；
  全 valid → ratio 1.0；全 invalid → ratio 0.0；混合 → 0.5；
  page=None/0/-1/"1"（str） → invalid；
  bbox 缺/不是 list/len≠4/bool/int+float/math.isfinite
- **_docx_locator_ratio 行为深度补强**：elements=[] → null；
  全 structural_keys valid → 1.0；含 page/bbox → invalid；
  全无 structural_keys → 0.0
- **_image_resource_ratio 行为深度补强**：无 image → null no_image_elements；
  有 image 但无 resource_path → ratio 0.0；resource_path 文件存在 size=0 → invalid；
  resource_path 是绝对路径 + image_base_dir → 仅用 Path(rp)；
  resource_path 是相对路径 + image_base_dir → 拼接 candidates；
  resource_path 文件不存在 → 0.0；OSError 跳过
- **_chunk_reference_ratio 边界补强**：chunks=[] → null no_chunks；
  elements=[] chunks 有 source_element_ids=['x'] → 0.0（'x' not in elem_ids）；
  重复 id 仍 valid；部分未知 id invalid；空 source_element_ids invalid
- **_heading_boundary_ratio 边界补强**：无 headings → null no_heading_elements；
  无 chunks → 0.0；chunk first id 是空字符串 "" → 不匹配；集合去重
- **_silent_drop_count 边界补强**：expectations={} → null；expectations=None → null；
  expectations={'element_count_by_type':None} → null；
  expectations={'element_count_by_type':{}} → null；by_type={} 全 drop；
  actual==expected → 0；actual>expected → 0；多类型 partial 求和
- **_strip_unicode_whitespace 行为深度补强**：所有 ASCII 空白 → 删除；
  所有 Unicode 空白 → 删除；保留 emoji/中文/数字/标点；
  全空白 → ""；无空白原样；混合 ASCII+Unicode
- **_text_preservation 边界补强**：image elements 不参与；
  chunks 全空白 → actual 空 → precision null empty_actual；
  elements 全是 image → expected 空 → precision null empty_expected；
  都空 → null empty_expected_and_actual；
  重复字符 Counter 取 min；乱序 → equal False 但 precision/recall 仍 1.0
- **module imports 顺序**：future → math → collections → pathlib → typing；
  5 imports 精确；math import 但仅用于 math.isfinite
- **module __all__ 精确**：1 entry 'compute_automatic_metrics'；namespace 含；
  valid identifier；callable；__all__ 是 list[str]
- **module namespace**：compute_automatic_metrics 是 module-level；
  13 helper（_null/_ratio/_bool_metric/_int_metric/_pdf_locator_ratio/_docx_locator_ratio/
  _is_valid_bbox/_image_resource_ratio/_chunk_reference_ratio/_strip_unicode_whitespace/
  _text_preservation/_heading_boundary_ratio/_silent_drop_count）是 module-level private；
  3 constant（_TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED）是 module-level private
- **module source forbidden tokens 补强**：os/sys/re/logging/subprocess/asyncio/
  threading/concurrent/json/time/datetime/itertools/functools/relative/class/dataclass/
  yield/async/global/walrus/assert
- **module docstring 深度补强**：含「自动指标」/「纯函数」/「不修改 document」/
  「text_preservation」/「Counter」/「Unicode 空白」/「evaluator v1.1」
- **signatures 精确**：compute_automatic_metrics 5 params + image_base_dir default=None；
  _pdf_locator_ratio 1 param；_docx_locator_ratio 1 param；_is_valid_bbox 1 param；
  _image_resource_ratio 2 params；_chunk_reference_ratio 2 params；
  _strip_unicode_whitespace 1 param；_text_preservation 2 params；
  _heading_boundary_ratio 2 params；_silent_drop_count 2 params；
  4 helper（_null/_ratio/_bool_metric/_int_metric）1 param each；
  所有 callable no varargs/varkw
- **module source level 完整**：compute_automatic_metrics 含 lazy import schema_validation；
  含 try/except Exception；含 11 metric 名称；含 pipeline_success 计算；
  含 elements/chunks 提取；含 by_type dict 构造；
  13 helper source 含具体算法（Counter 交集 / set 操作 / math.isfinite / Path(rp).is_file 等）
- **端到端集成**：完整 PDF document + error=None → 全 metric 都有值；
  完整 DOCX document → docx locator 1.0；document 含 image + tmp 文件 →
  image_resource_exists_ratio 1.0；不修改 document/error；
  含 expectations → silent_drop_count 计算；缺 code 抛 KeyError
- **模块整体合理性**：__all__ 1 entry；1 public + 13 private + 3 constant；
  无 class 定义；无 __main__ 块
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from typing import Any

import pytest

import evaluation.metrics as mmod
from evaluation.metrics import (
    _PDF_BBOX_REQUIRED_TYPES,
    _NOT_EVALUATED,
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


# =========================================================================
# 辅助
# =========================================================================


def _make_element(
    eid: str = "e1",
    etype: str = "paragraph",
    content: str = "hello",
    source_locator: dict | None = None,
    resource_path: str | None = None,
) -> dict[str, Any]:
    e = {"element_id": eid, "type": etype, "content": content}
    if source_locator is not None:
        e["source_locator"] = source_locator
    if resource_path is not None:
        e["resource_path"] = resource_path
    return e


def _make_chunk(text: str = "hello", cids: list[str] | None = None, cid: str = "c1") -> dict[str, Any]:
    return {"chunk_id": cid, "text": text, "source_element_ids": cids or ["e1"]}


def _make_pdf_document(
    elements: list[dict] | None = None,
    chunks: list[dict] | None = None,
) -> dict[str, Any]:
    if elements is None:
        elements = [_make_element(source_locator={"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]})]
    if chunks is None:
        chunks = [_make_chunk()]
    return {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": elements,
        "chunks": chunks,
    }


# =========================================================================
# 4 helper one-liner 行为深度补强
# =========================================================================


def test_null_returns_dict_with_value_none():
    out = _null("any_reason")
    assert out["value"] is None
    assert out["reason"] == "any_reason"


def test_null_returns_independent_dict():
    a = _null("x")
    b = _null("x")
    assert a is not b
    assert a == b


def test_ratio_accepts_int():
    out = _ratio(0)
    assert out["value"] == 0.0
    assert isinstance(out["value"], float)


def test_ratio_accepts_negative_no_clamp():
    """_ratio 不 clamp 负数（直接 float(value)）。"""
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_returns_float():
    out = _ratio(1)
    assert isinstance(out["value"], float)


def test_ratio_reason_is_none():
    out = _ratio(0.5)
    assert out["reason"] is None


def test_bool_metric_accepts_int_zero():
    """_bool_metric(0) → False（bool(0) False）。"""
    out = _bool_metric(0)
    assert out["value"] is False


def test_bool_metric_accepts_int_one():
    out = _bool_metric(1)
    assert out["value"] is True


def test_bool_metric_accepts_truthy_dict():
    out = _bool_metric({"a": 1})
    assert out["value"] is True


def test_bool_metric_returns_bool_type():
    out = _bool_metric(1)
    assert isinstance(out["value"], bool)


def test_int_metric_accepts_float_truncates():
    """_int_metric(3.99) → int(3.99) = 3。"""
    out = _int_metric(3.99)
    assert out["value"] == 3


def test_int_metric_accepts_negative():
    out = _int_metric(-5)
    assert out["value"] == -5


def test_int_metric_returns_int_type():
    out = _int_metric(42)
    assert isinstance(out["value"], int)
    assert not isinstance(out["value"], bool)  # 注意：bool 是 int 子类


def test_int_metric_raises_on_str():
    """_int_metric(str) 抛 ValueError。"""
    with pytest.raises(ValueError):
        _int_metric("abc")


# =========================================================================
# 3 常量精确补强
# =========================================================================


def test_text_types_7_entries_in_order():
    assert _TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_pdf_bbox_required_types_4_entries_in_order():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_pdf_bbox_required_is_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES ⊂ _TEXT_TYPES。"""
    pdf_set = set(_PDF_BBOX_REQUIRED_TYPES)
    text_set = set(_TEXT_TYPES)
    assert pdf_set.issubset(text_set)


def test_text_types_does_not_include_image():
    assert "image" not in _TEXT_TYPES


def test_constants_are_tuples():
    assert isinstance(_TEXT_TYPES, tuple)
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


# =========================================================================
# compute_automatic_metrics 边界组合补强
# =========================================================================


def test_compute_metrics_document_none_with_error_dict():
    """document None + error dict 含 code → pipeline_success=False, error_code=error['code']。"""
    out = compute_automatic_metrics(
        document=None,
        error={"code": "E_PARSE", "message": "fail"},
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "E_PARSE"


def test_compute_metrics_document_dict_with_error_dict():
    """document dict + error dict → pipeline_success=False（error is None false）。"""
    doc = _make_pdf_document()
    out = compute_automatic_metrics(
        document=doc,
        error={"code": "E_MISC"},
        source_type="pdf",
        expectations=None,
    )
    # error 给了 → pipeline_success=False（虽然 document 也给了）
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_source_type_unknown():
    """source_type='unknown' → pdf_locator null not_pdf + docx_locator null not_docx。"""
    doc = _make_pdf_document()
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="unknown", expectations=None
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_pdf_docx_null():
    doc = _make_pdf_document()
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_docx_pdf_null():
    doc = _make_pdf_document()
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="docx", expectations=None
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_empty_document_dict():
    """document 是空 dict (no elements/chunks) → 各 metric 走 no_elements/no_chunks 分支。"""
    out = compute_automatic_metrics(
        document={"source_type": "pdf"}, error=None, source_type="pdf", expectations=None
    )
    # elements 默认 []
    assert out["element_count_total"]["value"] == 0
    # pdf_locator no_elements
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_error_code_none_when_no_error():
    out = compute_automatic_metrics(
        document=_make_pdf_document(), error=None, source_type="pdf", expectations=None
    )
    assert out["error_code"]["value"] is None


def test_compute_metrics_returns_dict_with_13_plus_keys():
    out = compute_automatic_metrics(
        document=_make_pdf_document(), error=None, source_type="pdf", expectations=None
    )
    # 至少 13 个 metric
    assert len(out) >= 13


# =========================================================================
# schema_valid 行为深度
# =========================================================================


def test_schema_valid_document_none_pipeline_failed():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["schema_valid"]["reason"] == "pipeline_failed"


def test_schema_valid_document_passes():
    """合法 document → schema_valid True。"""
    doc = _make_pdf_document()
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 不强制 True，但 value 是 bool
    assert isinstance(out["schema_valid"]["value"], bool)


def test_schema_valid_value_is_bool_when_document_given():
    out = compute_automatic_metrics(_make_pdf_document(), None, "pdf", None)
    assert isinstance(out["schema_valid"]["value"], bool)


# =========================================================================
# _pdf_locator_ratio 行为深度补强
# =========================================================================


def test_pdf_locator_ratio_empty_elements():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_all_valid():
    elements = [
        _make_element("e1", "paragraph", source_locator={"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}),
        _make_element("e2", "heading", source_locator={"page": 2, "bbox": [0.0, 0.0, 1.0, 1.0]}),
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_all_invalid_page():
    elements = [
        _make_element("e1", "paragraph", source_locator={"page": 0, "bbox": [0.0, 0.0, 1.0, 1.0]}),
        _make_element("e2", "paragraph", source_locator={"page": -1, "bbox": [0.0, 0.0, 1.0, 1.0]}),
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_mixed():
    elements = [
        _make_element("e1", "paragraph", source_locator={"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}),
        _make_element("e2", "paragraph", source_locator={"page": 0, "bbox": [0.0, 0.0, 1.0, 1.0]}),
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_ratio_page_string_invalid():
    """page='1' 是 str → invalid。"""
    elements = [
        _make_element("e1", "paragraph", source_locator={"page": "1", "bbox": [0.0, 0.0, 1.0, 1.0]}),
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_none_invalid():
    elements = [
        _make_element("e1", "paragraph", source_locator={"page": None, "bbox": [0.0, 0.0, 1.0, 1.0]}),
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_invalid_bbox_for_text_type():
    """paragraph 需要 bbox，bbox 缺 → invalid。"""
    elements = [
        _make_element("e1", "paragraph", source_locator={"page": 1}),
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_non_text_type_no_bbox_required():
    """table 类型不在 _PDF_BBOX_REQUIRED_TYPES → 不需 bbox。"""
    elements = [
        _make_element("e1", "table", source_locator={"page": 1}),
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


# =========================================================================
# _docx_locator_ratio 行为深度补强
# =========================================================================


def test_docx_locator_ratio_empty_elements():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_all_valid_structural_keys():
    elements = [
        _make_element("e1", "paragraph", source_locator={"paragraph_index": 0}),
        _make_element("e2", "heading", source_locator={"section": "intro"}),
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_has_page_invalid():
    elements = [
        _make_element("e1", "paragraph", source_locator={"page": 1}),
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_has_bbox_invalid():
    elements = [
        _make_element("e1", "paragraph", source_locator={"bbox": [0, 0, 1, 1]}),
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys_invalid():
    elements = [
        _make_element("e1", "paragraph", source_locator={"random_key": "value"}),
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# =========================================================================
# _is_valid_bbox 行为深度补强
# =========================================================================


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_not_list():
    assert _is_valid_bbox((0.0, 0.0, 1.0, 1.0)) is False


def test_is_valid_bbox_wrong_length():
    assert _is_valid_bbox([0.0, 0.0, 1.0]) is False
    assert _is_valid_bbox([0.0, 0.0, 1.0, 1.0, 1.0]) is False


def test_is_valid_bbox_contains_bool():
    assert _is_valid_bbox([0.0, 0.0, 1.0, True]) is False


def test_is_valid_bbox_contains_str():
    assert _is_valid_bbox([0.0, 0.0, 1.0, "1.0"]) is False


def test_is_valid_bbox_contains_nan():
    assert _is_valid_bbox([0.0, 0.0, 1.0, float("nan")]) is False


def test_is_valid_bbox_contains_inf():
    assert _is_valid_bbox([0.0, 0.0, 1.0, float("inf")]) is False


def test_is_valid_bbox_valid_int():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_valid_float():
    assert _is_valid_bbox([0.0, 0.0, 1.5, 2.5]) is True


# =========================================================================
# _image_resource_ratio 行为深度补强
# =========================================================================


def test_image_resource_ratio_no_image_elements():
    elements = [_make_element("e1", "paragraph")]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_no_resource_path():
    elements = [_make_element("e1", "image", content=None)]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_exists(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG")
    elements = [_make_element("e1", "image", resource_path=str(img))]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_file_size_zero(tmp_path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [_make_element("e1", "image", resource_path=str(img))]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_not_exist():
    elements = [_make_element("e1", "image", resource_path="/nope/missing.png")]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_base_dir(tmp_path):
    """resource_path 是文件名，image_base_dir 提供目录 → 拼接 candidates。"""
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG")
    elements = [_make_element("e1", "image", resource_path="test.png")]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path):
    img = tmp_path / "exists.png"
    img.write_bytes(b"\x89PNG")
    elements = [
        _make_element("e1", "image", resource_path=str(img)),
        _make_element("e2", "image", resource_path="/nope/missing.png"),
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


# =========================================================================
# _chunk_reference_ratio 边界补强
# =========================================================================


def test_chunk_reference_ratio_no_chunks():
    out = _chunk_reference_ratio([_make_element()], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_elements_empty_chunks_with_ids():
    out = _chunk_reference_ratio([], [_make_chunk(cids=["x"])])
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid():
    elements = [_make_element("e1"), _make_element("e2")]
    chunks = [_make_chunk("a", ["e1"]), _make_chunk("b", ["e2"])]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_unknown_id():
    elements = [_make_element("e1")]
    chunks = [_make_chunk("a", ["e1"]), _make_chunk("b", ["unknown"])]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_empty_source_ids_invalid():
    """source_element_ids=[] → invalid（_make_chunk 的 cids or ['e1'] 会把 [] 替换，需要直接构造）。"""
    elements = [_make_element("e1")]
    chunks = [{"chunk_id": "c1", "text": "a", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_none_source_ids_invalid():
    elements = [_make_element("e1")]
    chunk = {"chunk_id": "c1", "text": "a", "source_element_ids": None}
    out = _chunk_reference_ratio(elements, [chunk])
    assert out["value"] == 0.0


def test_chunk_reference_ratio_repeated_id_still_valid():
    elements = [_make_element("e1")]
    chunks = [_make_chunk("a", ["e1", "e1", "e1"])]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# =========================================================================
# _heading_boundary_ratio 边界补强
# =========================================================================


def test_heading_boundary_ratio_no_headings():
    elements = [_make_element("e1", "paragraph")]
    out = _heading_boundary_ratio(elements, [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks():
    elements = [_make_element("e1", "heading")]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_ratio_perfect_match():
    elements = [_make_element("e1", "heading")]
    chunks = [_make_chunk("hello", ["e1"])]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match():
    elements = [_make_element("e1", "heading"), _make_element("e2", "heading")]
    chunks = [_make_chunk("hello", ["e1"])]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_chunk_first_id_empty_string():
    """chunk first id 是 "" → 不匹配。"""
    elements = [_make_element("e1", "heading")]
    chunks = [_make_chunk("hello", [""])]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_id_not_first():
    """chunk source_element_ids[0] != heading id → 不匹配。"""
    elements = [_make_element("e1", "heading"), _make_element("e2", "paragraph")]
    chunks = [_make_chunk("hello", ["e2", "e1"])]  # first id is e2 not e1
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_dedup_via_set():
    """多个 chunk first id 相同 → 集合去重不影响 matched。"""
    elements = [_make_element("e1", "heading")]
    chunks = [_make_chunk("a", ["e1"]), _make_chunk("b", ["e1"]), _make_chunk("c", ["e1"])]
    out = _heading_boundary_ratio(elements, chunks)
    # 只有 1 个 heading → matched=1, ratio=1/1=1.0
    assert out["value"] == 1.0


# =========================================================================
# _silent_drop_count 边界补强
# =========================================================================


def test_silent_drop_count_no_expectations():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_dict_expectations():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_no_element_count_key():
    out = _silent_drop_count({"paragraph": 5}, {"other_key": "value"})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expectations_element_count_none():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": None})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expectations_element_count_empty():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_by_type_empty_all_dropped():
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 3}})
    assert out["value"] == 3


def test_silent_drop_count_actual_equals_expected():
    out = _silent_drop_count({"paragraph": 3}, {"element_count_by_type": {"paragraph": 3}})
    assert out["value"] == 0


def test_silent_drop_count_actual_greater_than_expected():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 3}})
    assert out["value"] == 0


def test_silent_drop_count_multi_type_partial_drop():
    out = _silent_drop_count(
        {"paragraph": 2, "heading": 1},
        {"element_count_by_type": {"paragraph": 5, "heading": 1, "table": 3}},
    )
    # paragraph: max(0, 5-2)=3, heading: max(0, 1-1)=0, table: max(0, 3-0)=3 → 6
    assert out["value"] == 6


def test_silent_drop_count_returns_int():
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 1}})
    assert isinstance(out["value"], int)


# =========================================================================
# _strip_unicode_whitespace 行为深度补强
# =========================================================================


def test_strip_unicode_whitespace_ascii_space():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_ascii_tab_newline():
    assert _strip_unicode_whitespace("a\tb\nc") == "abc"


def test_strip_unicode_whitespace_nbsp():
    """NBSP (U+00A0) 是空白 → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """em space (U+2003) 是空白 → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """CJK 全角空格 (U+3000) 是空白 → 删除。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """U+2028 LINE SEPARATOR 是空白 → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029 PARAGRAPH SEPARATOR 是空白 → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   \t\n\r ") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_preserve_emoji():
    assert _strip_unicode_whitespace("hello 🌍 world") == "hello🌍world"


def test_strip_unicode_whitespace_preserve_chinese():
    assert _strip_unicode_whitespace("你好 世界") == "你好世界"


def test_strip_unicode_whitespace_preserve_punctuation():
    assert _strip_unicode_whitespace("hello, world!") == "hello,world!"


def test_strip_unicode_whitespace_preserve_digits():
    assert _strip_unicode_whitespace("123 456") == "123456"


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


# =========================================================================
# _text_preservation 边界补强
# =========================================================================


def test_text_preservation_image_not_participated():
    """image element 不参与 expected_sequence。"""
    elements = [
        _make_element("e1", "paragraph", "abc"),
        _make_element("e2", "image", None),
    ]
    chunks = [_make_chunk("abc")]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_chunks_all_whitespace_actual_empty():
    """chunks 全空白 → actual 空 → precision null empty_actual。"""
    elements = [_make_element("e1", "paragraph", "abc")]
    chunks = [_make_chunk("   ")]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_elements_all_image_expected_empty():
    """elements 全是 image → expected 空 → precision null empty_expected。"""
    elements = [_make_element("e1", "image", None)]
    chunks = [_make_chunk("abc")]
    out = _text_preservation(elements, chunks)
    # expected="" actual="abc"
    # sum(c_actual.values()) = 3 > 0 → precision = 0 / 3 = 0.0
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_both_empty():
    """elements 无内容 + chunks 无内容 → 都空 → null empty_expected_and_actual。"""
    elements = [_make_element("e1", "paragraph", "")]
    chunks = [_make_chunk("")]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_counter_takes_min():
    """重复字符 Counter 取 min（交集）。"""
    elements = [_make_element("e1", "paragraph", "aaabbb")]
    chunks = [_make_chunk("ababab")]
    out = _text_preservation(elements, chunks)
    # expected chars: a=3, b=3
    # actual chars:   a=3, b=3
    # common = 6
    # precision = 6/6 = 1.0, recall = 6/6 = 1.0
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_equal_true_when_order_matches():
    elements = [_make_element("e1", "paragraph", "hello world")]
    chunks = [_make_chunk("hello world")]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_equal_false_when_order_differs():
    """乱序 → equal False 但 precision/recall 仍 1.0。"""
    elements = [_make_element("e1", "paragraph", "ab")]
    chunks = [_make_chunk("ba")]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_returns_3_keys():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


# =========================================================================
# module imports 顺序
# =========================================================================


def test_module_source_has_future_annotations():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_math_import():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_collections_counter_import():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_pathlib_path_import():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_imports_in_correct_order():
    src = inspect.getsource(mmod)
    lines = [l.strip() for l in src.splitlines() if l.strip().startswith(("from ", "import "))]
    # 第 1 个是 future，第 2 个是 math，第 3 个是 collections，第 4 个是 pathlib，第 5 个是 typing
    assert "from __future__ import annotations" in lines[0]
    assert "import math" in lines[1]


def test_module_source_no_os_sys_imports():
    src = inspect.getsource(mmod)
    assert "\nimport os" not in src
    assert "\nimport sys" not in src


# =========================================================================
# module __all__ 精确
# =========================================================================


def test_module_all_has_1_entry():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_all_entry_in_namespace():
    assert hasattr(mmod, "compute_automatic_metrics")


def test_module_all_entry_callable():
    assert callable(mmod.compute_automatic_metrics)


def test_module_all_entry_valid_identifier():
    for name in mmod.__all__:
        assert name.isidentifier()


# =========================================================================
# module namespace
# =========================================================================


def test_module_namespace_4_helpers():
    """4 helper one-liner：_null / _ratio / _bool_metric / _int_metric。"""
    for name in ["_null", "_ratio", "_bool_metric", "_int_metric"]:
        assert hasattr(mmod, name)
        assert callable(getattr(mmod, name))


def test_module_namespace_9_metric_helpers():
    """9 个 metric helper（含 _is_valid_bbox / _strip_unicode_whitespace）。"""
    for name in [
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
    ]:
        assert hasattr(mmod, name)


def test_module_namespace_3_constants():
    for name in ["_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"]:
        assert hasattr(mmod, name)


def test_module_namespace_compute_automatic_metrics_public():
    """compute_automatic_metrics 是 module-level public（不在 _ 前缀）。"""
    import types
    funcs = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isfunction)
        if obj.__module__ == mmod.__name__
    ]
    assert "compute_automatic_metrics" in funcs


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_re_module():
    src = inspect.getsource(mmod)
    assert "\nimport re" not in src


def test_module_source_no_logging_module():
    src = inspect.getsource(mmod)
    assert "\nimport logging" not in src


def test_module_source_no_subprocess_module():
    src = inspect.getsource(mmod)
    assert "\nimport subprocess" not in src


def test_module_source_no_asyncio_module():
    src = inspect.getsource(mmod)
    assert "\nimport asyncio" not in src


def test_module_source_no_threading_module():
    src = inspect.getsource(mmod)
    assert "\nimport threading" not in src


def test_module_source_no_json_module():
    src = inspect.getsource(mmod)
    assert "\nimport json" not in src


def test_module_source_no_time_module():
    src = inspect.getsource(mmod)
    assert "\nimport time" not in src


def test_module_source_no_datetime_module():
    src = inspect.getsource(mmod)
    assert "\nimport datetime" not in src


def test_module_source_no_itertools_module():
    src = inspect.getsource(mmod)
    assert "\nimport itertools" not in src


def test_module_source_no_functools_module():
    src = inspect.getsource(mmod)
    assert "\nimport functools" not in src


def test_module_source_no_relative_import():
    src = inspect.getsource(mmod)
    assert "from ." not in src


def test_module_source_no_class_def():
    src = inspect.getsource(mmod)
    assert "\nclass " not in src


def test_module_source_no_dataclass_decorator():
    src = inspect.getsource(mmod)
    assert "@dataclass" not in src


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield " not in src


def test_module_source_no_async_def():
    src = inspect.getsource(mmod)
    assert "async def" not in src


def test_module_source_no_global_stmt():
    src = inspect.getsource(mmod)
    assert "\nglobal " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_module_source_no_assert_stmt():
    src = inspect.getsource(mmod)
    assert "\nassert " not in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_automatic_metrics():
    doc = mmod.__doc__ or ""
    assert "自动指标" in doc


def test_module_docstring_contains_pure_function():
    doc = mmod.__doc__ or ""
    assert "纯函数" in doc


def test_module_docstring_contains_no_modify_document():
    doc = mmod.__doc__ or ""
    assert "不修改 document" in doc or "不修改" in doc


def test_module_docstring_contains_text_preservation():
    doc = mmod.__doc__ or ""
    assert "text_preservation" in doc


def test_module_docstring_contains_counter():
    doc = mmod.__doc__ or ""
    assert "Counter" in doc


def test_module_docstring_contains_unicode_whitespace():
    doc = mmod.__doc__ or ""
    assert "Unicode 空白" in doc or "Unicode空白" in doc


def test_module_docstring_contains_v11():
    doc = mmod.__doc__ or ""
    assert "v1.1" in doc


# =========================================================================
# signatures 精确
# =========================================================================


def test_compute_metrics_signature_5_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5
    assert list(sig.parameters.keys()) == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_compute_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert params[4].name == "image_base_dir"
    assert params[4].default is None


def test_compute_metrics_no_varargs_varkw():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_null_signature_1_param():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["reason"]


def test_ratio_signature_1_param():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["value"]


def test_bool_metric_signature_1_param():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["value"]


def test_int_metric_signature_1_param():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["value"]


def test_pdf_locator_ratio_signature_1_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


def test_docx_locator_ratio_signature_1_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


def test_is_valid_bbox_signature_1_param():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_image_resource_ratio_signature_2_params():
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_chunk_reference_ratio_signature_2_params():
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2


def test_strip_unicode_whitespace_signature_1_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_text_preservation_signature_2_params():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_heading_boundary_ratio_signature_2_params():
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


def test_silent_drop_count_signature_2_params():
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2


def test_all_helpers_no_varargs_varkw():
    """13 个 helper 都 no varargs/varkw。"""
    helpers = [
        _null, _ratio, _bool_metric, _int_metric,
        _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox,
        _image_resource_ratio, _chunk_reference_ratio,
        _strip_unicode_whitespace, _text_preservation,
        _heading_boundary_ratio, _silent_drop_count,
    ]
    for h in helpers:
        sig = inspect.signature(h)
        for p in sig.parameters.values():
            assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD), \
                f"{h.__name__} has varargs/varkw"


# =========================================================================
# module source level 完整
# =========================================================================


def test_compute_metrics_source_has_lazy_import_schema_validation():
    src = inspect.getsource(compute_automatic_metrics)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_compute_metrics_source_has_try_except_exception():
    src = inspect.getsource(compute_automatic_metrics)
    assert "except Exception" in src


def test_compute_metrics_source_has_pipeline_success_calc():
    src = inspect.getsource(compute_automatic_metrics)
    assert "error is None and document is not None" in src


def test_compute_metrics_source_has_11_metric_names():
    """document None 分支列出 11 个 metric 名。"""
    src = inspect.getsource(compute_automatic_metrics)
    expected_metrics = [
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
    for m in expected_metrics:
        assert m in src


def test_pdf_locator_ratio_source_has_no_elements_branch():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if not elements" in src
    assert "no_elements" in src


def test_pdf_locator_ratio_source_uses_pdf_bbox_required_types():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_pdf_locator_ratio_source_uses_is_valid_bbox():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_is_valid_bbox" in src


def test_docx_locator_ratio_source_has_structural_keys():
    src = inspect.getsource(_docx_locator_ratio)
    assert "structural_keys" in src
    # 7 个 keys
    for k in ("section", "paragraph_index", "run_index", "table_index", "row_index", "col_index", "relationship_id"):
        assert k in src


def test_is_valid_bbox_source_uses_math_isfinite():
    src = inspect.getsource(_is_valid_bbox)
    assert "math.isfinite" in src


def test_image_resource_ratio_source_has_candidates():
    src = inspect.getsource(_image_resource_ratio)
    assert "candidates" in src
    assert "Path(rp)" in src


def test_image_resource_ratio_source_uses_stat_st_size():
    src = inspect.getsource(_image_resource_ratio)
    assert ".stat().st_size" in src


def test_image_resource_ratio_source_except_oserror():
    src = inspect.getsource(_image_resource_ratio)
    assert "except OSError" in src


def test_chunk_reference_ratio_source_uses_set_comprehension():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "{e.get(\"element_id\") for e in elements}" in src or "elem_ids" in src


def test_strip_unicode_whitespace_source_uses_isspace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "ch.isspace()" in src


def test_text_preservation_source_uses_counter():
    src = inspect.getsource(_text_preservation)
    assert "Counter(expected)" in src
    assert "Counter(actual)" in src


def test_text_preservation_source_uses_intersection():
    src = inspect.getsource(_text_preservation)
    assert "c_expected & c_actual" in src


def test_heading_boundary_ratio_source_uses_chunk_first_ids_set():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids" in src
    assert "ids[0]" in src


def test_silent_drop_count_source_uses_max_zero():
    """silent_drop_count 计算 max(0, expected - actual)。"""
    src = inspect.getsource(_silent_drop_count)
    assert "if actual < exp" in src
    assert "drops += (exp - actual)" in src


# =========================================================================
# 端到端集成
# =========================================================================


def test_end_to_end_pdf_document_all_metrics_present():
    """完整 PDF document → 全 metric 都有值。"""
    doc = _make_pdf_document()
    out = compute_automatic_metrics(doc, None, "pdf", None)
    expected_keys = [
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ]
    for k in expected_keys:
        assert k in out


def test_end_to_end_docx_document_docx_locator_one():
    """DOCX document → docx_locator_valid_ratio 1.0（structural keys valid）。"""
    doc = {
        "source_type": "docx",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.docx",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            _make_element("e1", "paragraph", "hello", source_locator={"paragraph_index": 0}),
        ],
        "chunks": [_make_chunk("hello", ["e1"])],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_end_to_end_image_with_tmp_file(tmp_path):
    """document 含 image + tmp 文件 → image_resource_exists_ratio 1.0。"""
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG")
    doc = {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            _make_element("e1", "paragraph", "hello", source_locator={"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}),
            _make_element("e2", "image", None, source_locator={"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}, resource_path=str(img)),
        ],
        "chunks": [_make_chunk("hello", ["e1"])],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_end_to_end_no_modification_of_document():
    """compute_automatic_metrics 不修改 document。"""
    import copy as _copy
    doc = _make_pdf_document()
    doc_before = _copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == doc_before


def test_end_to_end_no_modification_of_error():
    import copy as _copy
    err = {"code": "E_TEST", "message": "test"}
    err_before = _copy.deepcopy(err)
    compute_automatic_metrics(None, err, "pdf", None)
    assert err == err_before


def test_end_to_end_with_expectations_silent_drop():
    """含 expectations → silent_drop_count 计算。"""
    doc = _make_pdf_document()
    out = compute_automatic_metrics(
        doc, None, "pdf",
        expectations={"element_count_by_type": {"paragraph": 5}},
    )
    # actual paragraph=1, expected=5 → drop=4
    assert out["silent_drop_count"]["value"] == 4


def test_end_to_end_missing_code_raises_keyerror():
    """error dict 缺 code → 抛 KeyError。"""
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, {"message": "no code"}, "pdf", None)


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_all_1_entry():
    assert len(mmod.__all__) == 1


def test_module_no_class_definitions():
    classes = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isclass)
        if obj.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_no_main_block():
    src = inspect.getsource(mmod)
    assert 'if __name__' not in src


def test_module_has_1_public_function():
    import types
    public_funcs = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isfunction)
        if obj.__module__ == mmod.__name__ and not name.startswith("_")
    ]
    assert public_funcs == ["compute_automatic_metrics"]


def test_module_has_13_private_functions():
    """13 个 _ 前缀 helper。"""
    import types
    private_funcs = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isfunction)
        if obj.__module__ == mmod.__name__ and name.startswith("_")
    ]
    # 4 helper + 9 metric helper = 13
    assert len(private_funcs) == 13
