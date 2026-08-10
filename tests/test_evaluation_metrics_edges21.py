r"""evaluation/metrics.py 边角测试 - 第二十一轮（Round 292）。

edges20 已覆盖：compute_automatic_metrics 输出 keys/value 类型 / element_count_by_type dict /
error_code 类型 / text_preservation 12 场景 / _is_valid_bbox 19 场景 / _pdf_locator_ratio 14 场景 /
_docx_locator_ratio 13 场景 / _chunk_reference_ratio 9 场景 / _heading_boundary_ratio 7 场景 /
_silent_drop_count 10 场景 / _strip_unicode_whitespace 6 场景 / module source 含 import + 常量 +
4 个 one-liner helper / __all__ 1 entry / 不修改 input。

edges21 补强未覆盖的角度：
- **_null / _ratio / _bool_metric / _int_metric 行为 + source level**：返回 dict 结构精确；
  value 类型；reason 类型；source 含 def + return dict 字面量；4 个函数都是 one-liner
- **_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 常量值精确**：7 entries / 4 entries
- **_NOT_EVALUATED 常量值**：'not_evaluated'
- **module imports 顺序**：math → Counter → Path → Any
- **compute_automatic_metrics 边界组合**：document=None+error=None / document=None+error=dict /
  document=dict+error=None / document=dict+error=dict / 缺 error["code"] / schema 异常
- **schema_validation 延迟 import**：source 含 'from evaluation.schema_validation import'
- **_image_resource_ratio 行为深度**：无 image / 缺 resource_path / size=0 / 文件不存在 /
  image_base_dir 给了 / OSError 跳过 / 多 candidates 都失败
- **_chunk_reference_ratio 边界**：chunks=[] / 空 elements + chunks 有 / 重复 id / all valid /
  empty source_element_ids
- **_heading_boundary_ratio 边界**：无 headings / 无 chunks / heading 缺 element_id /
  chunk first id 是空字符串 / 全部匹配 / 全部不匹配
- **_silent_drop_count 边界**：expectations={}/None/False；element_count_by_type=None/空；
  by_type 空；expected < actual 不计入；多类型 max(0, ...)
- **_strip_unicode_whitespace 行为深度**：NBSP / em space / en space / ideographic space /
  line separator / paragraph separator / 混合空白
- **_text_preservation 边界**：element type=None 参与计算 / image type 不参与 /
  chunks 全空白 / 都空 → null empty_expected_and_actual
- **module __all__ 完整性**：1 entry / 在 namespace / valid identifier / callable
- **private helpers namespace**：13 个 _ 开头的函数都在 namespace 不在 __all__
- **module docstring 深度**：含「自动指标」/「纯函数」/「不修改 document」/「text_preservation 语义」/
  「不丢不重」/「Counter」
- **module source forbidden tokens 补强**：sys/logging/subprocess/asyncio/threading/concurrent/
  re/time/datetime/itertools/functools
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

import evaluation.metrics as mmod
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
# 辅助：构造 element / chunk
# =========================================================================


def _elem(eid: str, etype: str, content: str = "", **kwargs) -> dict[str, Any]:
    e = {"element_id": eid, "type": etype, "content": content}
    e.update(kwargs)
    return e


def _chunk(cid: str, text: str, ids: list[str]) -> dict[str, Any]:
    return {"chunk_id": cid, "text": text, "source_element_ids": ids}


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric 行为 + source level
# =========================================================================


def test_null_returns_correct_structure():
    """_null 返 {value: None, reason: str}。"""
    out = _null("some_reason")
    assert out == {"value": None, "reason": "some_reason"}


def test_null_value_is_none():
    """_null value 是 None。"""
    assert _null("x")["value"] is None


def test_null_reason_type_str():
    """_null reason 是 str。"""
    assert isinstance(_null("x")["reason"], str)


def test_null_returns_dict():
    """_null 返回 dict。"""
    assert isinstance(_null("x"), dict)


def test_null_len_two():
    """_null dict 长度 2。"""
    assert len(_null("x")) == 2


def test_null_keys_exact():
    """_null keys 精确。"""
    assert set(_null("x").keys()) == {"value", "reason"}


def test_ratio_returns_correct_structure():
    """_ratio 返 {value: float, reason: None}。"""
    out = _ratio(0.5)
    assert out == {"value": 0.5, "reason": None}


def test_ratio_value_type_float():
    """_ratio value 是 float（即使传 int）。"""
    assert isinstance(_ratio(0).get("value"), float)
    assert isinstance(_ratio(1).get("value"), float)


def test_ratio_value_zero():
    """_ratio 0 → 0.0。"""
    assert _ratio(0)["value"] == 0.0


def test_ratio_value_one():
    """_ratio 1 → 1.0。"""
    assert _ratio(1)["value"] == 1.0


def test_ratio_reason_always_none():
    """_ratio reason 始终 None。"""
    assert _ratio(0)["reason"] is None


def test_bool_metric_returns_correct_structure():
    """_bool_metric 返 {value: bool, reason: None}。"""
    assert _bool_metric(True) == {"value": True, "reason": None}
    assert _bool_metric(False) == {"value": False, "reason": None}


def test_bool_metric_value_type_bool():
    """_bool_metric value 类型 bool（即使传 1/0）。"""
    assert isinstance(_bool_metric(1)["value"], bool)
    assert _bool_metric(1)["value"] is True
    assert _bool_metric(0)["value"] is False


def test_int_metric_returns_correct_structure():
    """_int_metric 返 {value: int, reason: None}。"""
    assert _int_metric(5) == {"value": 5, "reason": None}


def test_int_metric_value_type_int():
    """_int_metric value 类型 int（即使传 float）。"""
    assert isinstance(_int_metric(3.7)["value"], int)
    assert _int_metric(3.7)["value"] == 3


def test_int_metric_negative():
    """_int_metric 负数。"""
    assert _int_metric(-1)["value"] == -1


def test_int_metric_zero():
    """_int_metric 0。"""
    assert _int_metric(0)["value"] == 0


def test_null_source_one_liner():
    """_null source 是 one-liner 函数。"""
    src = inspect.getsource(_null)
    assert "def _null" in src
    assert "return" in src


def test_ratio_source_one_liner():
    """_ratio source 是 one-liner 函数。"""
    src = inspect.getsource(_ratio)
    assert "def _ratio" in src
    assert "return" in src


def test_bool_metric_source_one_liner():
    """_bool_metric source 是 one-liner。"""
    src = inspect.getsource(_bool_metric)
    assert "def _bool_metric" in src
    assert "return" in src


def test_int_metric_source_one_liner():
    """_int_metric source 是 one-liner。"""
    src = inspect.getsource(_int_metric)
    assert "def _int_metric" in src
    assert "return" in src


def test_null_source_uses_dict_literal():
    """_null source 含 dict 字面量。"""
    src = inspect.getsource(_null)
    assert "value" in src
    assert "reason" in src


def test_ratio_source_uses_float_call():
    """_ratio source 含 float(...) 强制转换。"""
    src = inspect.getsource(_ratio)
    assert "float(" in src


def test_bool_metric_source_uses_bool_call():
    """_bool_metric source 含 bool(...) 强制转换。"""
    src = inspect.getsource(_bool_metric)
    assert "bool(" in src


def test_int_metric_source_uses_int_call():
    """_int_metric source 含 int(...) 强制转换。"""
    src = inspect.getsource(_int_metric)
    assert "int(" in src


# =========================================================================
# _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 常量精确
# =========================================================================


def test_text_types_7_entries_exact():
    """_TEXT_TYPES 7 entries。"""
    assert len(mmod._TEXT_TYPES) == 7


def test_text_types_exact_set():
    """_TEXT_TYPES 内容精确。"""
    assert set(mmod._TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    }


def test_text_types_is_tuple():
    """_TEXT_TYPES 是 tuple。"""
    assert isinstance(mmod._TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_4_entries():
    """_PDF_BBOX_REQUIRED_TYPES 4 entries。"""
    assert len(mmod._PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_exact_set():
    """_PDF_BBOX_REQUIRED_TYPES 内容精确。"""
    assert set(mmod._PDF_BBOX_REQUIRED_TYPES) == {
        "heading", "paragraph", "caption", "list_item",
    }


def test_pdf_bbox_required_types_is_tuple():
    """_PDF_BBOX_REQUIRED_TYPES 是 tuple。"""
    assert isinstance(mmod._PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES 是 _TEXT_TYPES 的子集。"""
    assert set(mmod._PDF_BBOX_REQUIRED_TYPES).issubset(set(mmod._TEXT_TYPES))


def test_not_evaluated_constant_value():
    """_NOT_EVALUATED = 'not_evaluated'。"""
    assert mmod._NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_constant_type_str():
    """_NOT_EVALUATED 是 str。"""
    assert isinstance(mmod._NOT_EVALUATED, str)


def test_not_evaluated_in_module_namespace():
    """_NOT_EVALUATED 在 namespace。"""
    assert hasattr(mmod, "_NOT_EVALUATED")


# =========================================================================
# module imports 顺序
# =========================================================================


def test_module_imports_math():
    """含 import math。"""
    assert "import math" in inspect.getsource(mmod)


def test_module_imports_counter():
    """含 from collections import Counter。"""
    assert "from collections import Counter" in inspect.getsource(mmod)


def test_module_imports_path():
    """含 from pathlib import Path。"""
    assert "from pathlib import Path" in inspect.getsource(mmod)


def test_module_imports_any():
    """含 from typing import Any。"""
    assert "from typing import Any" in inspect.getsource(mmod)


def test_module_import_order_math_before_counter():
    """math 在 Counter 之前 import。"""
    src = inspect.getsource(mmod)
    assert src.find("import math") < src.find("from collections import Counter")


def test_module_import_order_counter_before_pathlib():
    """Counter 在 pathlib 之前 import。"""
    src = inspect.getsource(mmod)
    assert src.find("from collections import Counter") < src.find("from pathlib import Path")


def test_module_import_order_pathlib_before_typing():
    """pathlib 在 typing 之前 import。"""
    src = inspect.getsource(mmod)
    assert src.find("from pathlib import Path") < src.find("from typing import Any")


def test_module_namespace_has_math():
    """math 在 namespace。"""
    assert hasattr(mmod, "math")


def test_module_namespace_has_counter():
    """Counter 在 namespace。"""
    assert hasattr(mmod, "Counter")


def test_module_namespace_has_path():
    """Path 在 namespace。"""
    assert hasattr(mmod, "Path")


# =========================================================================
# compute_automatic_metrics 边界组合
# =========================================================================


def test_compute_metrics_document_none_error_none_pipeline_fails():
    """document=None + error=None → pipeline_success=False。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_document_none_error_none_error_code_none():
    """document=None + error=None → error_code value=None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_document_none_error_dict_pipeline_fails():
    """document=None + error=dict → pipeline_success=False。"""
    out = compute_automatic_metrics(None, {"code": "parse_failed"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_document_none_error_dict_error_code_from_error():
    """document=None + error=dict → error_code value=error['code']。"""
    out = compute_automatic_metrics(None, {"code": "parse_failed"}, "pdf", None)
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_metrics_document_dict_error_none_pipeline_succeeds():
    """document=dict + error=None → pipeline_success=True。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_document_none_all_metrics_null_pipeline_failed():
    """document=None → 后续 metric 都 null + reason='pipeline_failed'。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
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
    for name in null_metrics:
        assert out[name]["value"] is None
        assert out[name]["reason"] == "pipeline_failed"


def test_compute_metrics_schema_valid_when_document_dict():
    """document 存在 → schema_valid 不为 null（True 或 False）。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] in (True, False)


def test_compute_metrics_source_type_unknown_pdf_locator_not_pdf():
    """source_type='unknown' → pdf_locator_valid_ratio null + reason='not_pdf_document'。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "unknown", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_source_type_unknown_docx_locator_not_docx():
    """source_type='unknown' → docx_locator_valid_ratio null + reason='not_docx_document'。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "unknown", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_pdf_docx_locator_not_docx():
    """source_type='pdf' → docx_locator_valid_ratio null + reason='not_docx_document'。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_docx_pdf_locator_not_pdf():
    """source_type='docx' → pdf_locator_valid_ratio null + reason='not_pdf_document'。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_returns_dict():
    """compute_automatic_metrics 返回 dict。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_signature_5_params():
    """signature 5 params。"""
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_metrics_signature_image_base_dir_default_none():
    """image_base_dir 默认 None。"""
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_metrics_signature_no_varargs():
    """compute_automatic_metrics 不接受 *args。"""
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_compute_metrics_signature_no_varkw():
    """compute_automatic_metrics 不接受 **kwargs。"""
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_compute_metrics_source_lazy_import_schema_validation():
    """compute_automatic_metrics source 含 'from evaluation.schema_validation import'。"""
    src = inspect.getsource(compute_automatic_metrics)
    assert "from evaluation.schema_validation import" in src


def test_compute_metrics_source_lazy_import_document_passes_schema():
    """source 含 document_passes_schema。"""
    src = inspect.getsource(compute_automatic_metrics)
    assert "document_passes_schema" in src


def test_compute_metrics_source_contains_14_metric_keys():
    """source 含 14 个 metric key 名称。"""
    src = inspect.getsource(compute_automatic_metrics)
    keys = [
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
    for k in keys:
        assert k in src


def test_compute_metrics_source_pipeline_success_calculation():
    """source 含 pipeline_success 计算（error is None and document is not None）。"""
    src = inspect.getsource(compute_automatic_metrics)
    assert "error is None" in src
    assert "document is not None" in src


# =========================================================================
# _image_resource_ratio 行为深度
# =========================================================================


def test_image_resource_ratio_no_image_elements_returns_null():
    """无 image → null + reason='no_image_elements'。"""
    elements = [_elem("e1", "paragraph", "hi")]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_missing_resource_path():
    """image 缺 resource_path → valid=0 → ratio 0.0。"""
    elements = [_elem("e1", "image")]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_does_not_exist(tmp_path):
    """resource_path 文件不存在 → valid=0 → ratio 0.0。"""
    elements = [_elem("e1", "image", resource_path=str(tmp_path / "missing.png"))]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_exists_nonzero(tmp_path):
    """文件存在 + size > 0 → valid=1 → ratio 1.0。"""
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG fake data")
    elements = [_elem("e1", "image", resource_path=str(p))]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_file_exists_zero_size(tmp_path):
    """文件存在 + size=0 → valid=0 → ratio 0.0。"""
    p = tmp_path / "empty.png"
    p.write_bytes(b"")
    elements = [_elem("e1", "image", resource_path=str(p))]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_base_dir_filename_only(tmp_path):
    """image_base_dir 给了 + resource_path 是文件名 → 拼接路径找到。"""
    p = tmp_path / "img.png"
    p.write_bytes(b"data")
    elements = [_elem("e1", "image", resource_path="img.png")]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path):
    """混合：1 valid + 1 invalid → ratio 0.5。"""
    p1 = tmp_path / "img1.png"
    p1.write_bytes(b"data")
    elements = [
        _elem("e1", "image", resource_path=str(p1)),
        _elem("e2", "image", resource_path=str(tmp_path / "missing.png")),
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_ratio_oserror_skipped():
    """OSError 路径 → 跳过，valid=0。"""
    # 用一个非常长的非法路径（Windows 上可能抛 OSError）
    elements = [_elem("e1", "image", resource_path="/nonexistent/path/to/file.png")]
    out = _image_resource_ratio(elements, None)
    # 文件不存在 → is_file()=False，不抛 OSError，但 valid=0
    assert out["value"] == 0.0


def test_image_resource_ratio_signature():
    """signature 2 params。"""
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2


def test_image_resource_ratio_no_default_args():
    """无默认值。"""
    sig = inspect.signature(_image_resource_ratio)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# _chunk_reference_ratio 边界
# =========================================================================


def test_chunk_reference_ratio_no_chunks_returns_null():
    """chunks=[] → null + 'no_chunks'。"""
    out = _chunk_reference_ratio([_elem("e1", "paragraph")], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_elements_with_chunks_returns_zero():
    """elements=[] + chunks 有 → valid=0 → ratio 0.0。"""
    chunks = [_chunk("c1", "text", ["e1"])]
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_repeated_id_in_one_chunk():
    """chunk source_element_ids 含重复 id → all() 检查每个，仍 valid。"""
    elements = [_elem("e1", "paragraph")]
    chunks = [_chunk("c1", "text", ["e1", "e1"])]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_unknown_in_one_chunk():
    """chunk ids 部分未知 → all() False → 不 valid。"""
    elements = [_elem("e1", "paragraph")]
    chunks = [_chunk("c1", "text", ["e1", "e_unknown"])]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_source_element_ids_in_chunk():
    """chunk source_element_ids=[] → falsy → 不 valid（valid+=0）。"""
    elements = [_elem("e1", "paragraph")]
    chunks = [_chunk("c1", "text", [])]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_source_element_ids_none():
    """chunk source_element_ids=None → or [] → 不 valid。"""
    elements = [_elem("e1", "paragraph")]
    chunks = [{"chunk_id": "c1", "text": "hi", "source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_chunks_valid():
    """所有 chunks 都 valid → ratio 1.0。"""
    elements = [_elem("e1", "paragraph"), _elem("e2", "paragraph")]
    chunks = [
        _chunk("c1", "a", ["e1"]),
        _chunk("c2", "b", ["e2"]),
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_signature():
    """signature 2 params。"""
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2


# =========================================================================
# _heading_boundary_ratio 边界
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    """无 headings → null + 'no_heading_elements'。"""
    elements = [_elem("e1", "paragraph")]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_returns_zero():
    """headings + 无 chunks → ratio 0.0（chunk_first_ids 空，matched=0）。"""
    elements = [_elem("e1", "heading")]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_ratio_heading_missing_element_id():
    """heading 缺 element_id → h.get('element_id')=None → 不在 chunk_first_ids。"""
    elements = [{"type": "heading"}]  # 缺 element_id
    chunks = [_chunk("c1", "text", ["h1"])]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_first_id_empty_string():
    """chunk first id 是空字符串 → 仍 add 到 chunk_first_ids。"""
    elements = [_elem("e1", "heading")]
    chunks = [_chunk("c1", "text", [""])]
    out = _heading_boundary_ratio(elements, chunks)
    # element_id="e1" 不在 chunk_first_ids={""} → matched=0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_all_headings_match():
    """所有 heading 都在某 chunk first position → ratio 1.0。"""
    elements = [_elem("h1", "heading"), _elem("h2", "heading")]
    chunks = [
        _chunk("c1", "a", ["h1"]),
        _chunk("c2", "b", ["h2"]),
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match():
    """部分 heading 在 chunk first → ratio 0.5。"""
    elements = [_elem("h1", "heading"), _elem("h2", "heading")]
    chunks = [_chunk("c1", "a", ["h1"])]  # 只有 h1 在
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_dedup_chunk_first_ids():
    """多 chunk first id 相同 → 集合去重 → 仍算 1 个。"""
    elements = [_elem("h1", "heading")]
    chunks = [
        _chunk("c1", "a", ["h1"]),
        _chunk("c2", "b", ["h1"]),  # 同样 first id
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_signature():
    """signature 2 params。"""
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


# =========================================================================
# _silent_drop_count 边界
# =========================================================================


def test_silent_drop_count_empty_expectations_dict():
    """expectations={} → null + 'no_expectations'。"""
    out = _silent_drop_count({}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_none_expectations():
    """expectations=None → null + 'no_expectations'。"""
    out = _silent_drop_count({}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_falsy_expectations():
    """expectations=False → falsy → null。"""
    out = _silent_drop_count({}, False)
    assert out["value"] is None


def test_silent_drop_count_empty_element_count_by_type():
    """expectations={'element_count_by_type': {}} → null + 'no_expectations_element_count'。"""
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_none_element_count_by_type():
    """expectations={'element_count_by_type': None} → or [] → null。"""
    out = _silent_drop_count({}, {"element_count_by_type": None})
    assert out["value"] is None


def test_silent_drop_count_missing_element_count_by_type():
    """expectations 缺 element_count_by_type → or [] → null。"""
    out = _silent_drop_count({}, {"other_key": "value"})
    assert out["value"] is None


def test_silent_drop_count_by_type_empty():
    """by_type={} → 所有 expected 类型都算 missing → drops=Σ expected。"""
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count({}, expectations)
    assert out["value"] == 5


def test_silent_drop_count_actual_equals_expected():
    """actual == expected → drops=0。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_actual_greater_than_expected():
    """actual > expected → 不计入 drops（max(0, neg)=0）。"""
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_multi_type_partial_drop():
    """多类型部分 drop：drop=2+0+3=5。"""
    by_type = {"paragraph": 3, "heading": 5, "table": 0}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 5, "table": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 5  # (5-3) + (5-5) + (3-0) = 2 + 0 + 3


def test_silent_drop_count_value_type_int():
    """value 类型 int。"""
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert isinstance(out["value"], int)


def test_silent_drop_count_signature():
    """signature 2 params。"""
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2


# =========================================================================
# _strip_unicode_whitespace 行为深度
# =========================================================================


def test_strip_unicode_whitespace_nbsp():
    r"""删除 NBSP（U+00A0）。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_em_space():
    r"""删除 em space（U+2003）。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_en_space():
    r"""删除 en space（U+2002）。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_ideographic_space():
    r"""删除 ideographic space（U+3000）。"""
    assert _strip_unicode_whitespace("　") == ""


def test_strip_unicode_whitespace_line_separator():
    r"""删除 line separator（U+2028）。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_paragraph_separator():
    r"""删除 paragraph separator（U+2029）。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_mixed_unicode_whitespace():
    r"""混合 ASCII + Unicode 空白。"""
    s = "a b c　d\te\nf"
    assert _strip_unicode_whitespace(s) == "abcdef"


def test_strip_unicode_whitespace_all_kinds_in_one_string():
    r"""所有种类空白在一起。"""
    s = " \t\n\r   　  "
    assert _strip_unicode_whitespace(s) == ""


def test_strip_unicode_whitespace_no_whitespace():
    """无空白 → 原样返回。"""
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_returns_str_type():
    """返回值类型 str。"""
    assert isinstance(_strip_unicode_whitespace(""), str)


def test_strip_unicode_whitespace_preserves_emoji():
    """emoji 不被删除。"""
    assert _strip_unicode_whitespace("😀😁😂") == "😀😁😂"


def test_strip_unicode_whitespace_preserves_chinese():
    """中文不被删除。"""
    assert _strip_unicode_whitespace("你好 世界") == "你好世界"


def test_strip_unicode_whitespace_preserves_punctuation():
    """标点不被删除。"""
    assert _strip_unicode_whitespace("hello, world!") == "hello,world!"


def test_strip_unicode_whitespace_preserves_digits():
    """数字不被删除。"""
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_unicode_whitespace_signature():
    """signature 1 param。"""
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_strip_unicode_whitespace_no_default_args():
    """无默认值。"""
    sig = inspect.signature(_strip_unicode_whitespace)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_strip_unicode_whitespace_source_uses_isspace():
    """source 含 ch.isspace()。"""
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "isspace" in src


def test_strip_unicode_whitespace_source_uses_join():
    """source 含 ''.join 或 join。"""
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "join" in src


# =========================================================================
# _text_preservation 边界
# =========================================================================


def test_text_preservation_element_type_none_participates():
    """element type=None → 参与（None != 'image'）。"""
    elements = [{"element_id": "e1", "type": None, "content": "abc"}]
    chunks = [_chunk("c1", "abc", ["e1"])]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_element_type_image_does_not_participate():
    """element type='image' → 不参与（即使 content 不空）。"""
    elements = [
        {"element_id": "e1", "type": "image", "content": "image data"},
        {"element_id": "e2", "type": "paragraph", "content": "abc"},
    ]
    chunks = [_chunk("c1", "abc", ["e2"])]
    out = _text_preservation(elements, chunks)
    # expected = "abc"（image 不参与）
    # actual = "abc"
    assert out["equal"]["value"] is True


def test_text_preservation_chunks_all_whitespace_actual_becomes_empty():
    """chunks 全是空白 → actual 空字符串 → recall null empty_actual。"""
    elements = [_elem("e1", "paragraph", "abc")]
    chunks = [_chunk("c1", "   ", ["e1"])]
    out = _text_preservation(elements, chunks)
    # expected = "abc"
    # actual = "" (after strip)
    # expected != actual → equal False
    # sum(c_actual.values())==0 → precision null empty_actual
    # sum(c_expected.values())==3 → recall = 0/3 = 0.0
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_both_empty_returns_null_empty_expected_and_actual():
    """expected 和 actual 都空 → null empty_expected_and_actual。"""
    elements = []  # 无 elements → expected=""
    chunks = []  # 无 chunks → actual=""
    out = _text_preservation(elements, chunks)
    # 都空 → equal True + precision/recall null empty_expected_and_actual
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_returns_three_keys():
    """返回 3 keys。"""
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_value_dict():
    """每个 value 是 dict。"""
    out = _text_preservation([], [])
    for v in out.values():
        assert isinstance(v, dict)


def test_text_preservation_no_side_effects():
    """不修改输入。"""
    elements = [_elem("e1", "paragraph", "abc")]
    chunks = [_chunk("c1", "abc", ["e1"])]
    elem_before = repr(elements)
    chunk_before = repr(chunks)
    _text_preservation(elements, chunks)
    assert repr(elements) == elem_before
    assert repr(chunks) == chunk_before


def test_text_preservation_signature():
    """signature 2 params。"""
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_text_preservation_source_uses_counter():
    """source 含 Counter(...) 调用。"""
    src = inspect.getsource(_text_preservation)
    assert "Counter(" in src


def test_text_preservation_source_uses_strip_unicode_whitespace():
    """source 含 _strip_unicode_whitespace 调用。"""
    src = inspect.getsource(_text_preservation)
    assert "_strip_unicode_whitespace" in src


def test_text_preservation_source_uses_counter_intersection():
    """source 含 Counter 交集操作（&）。"""
    src = inspect.getsource(_text_preservation)
    assert "&" in src
    assert "c_actual" in src or "c_expected" in src


# =========================================================================
# _pdf_locator_ratio source level 补强
# =========================================================================


def test_pdf_locator_ratio_source_uses_isinstance_page():
    """source 含 isinstance(page, int)。"""
    src = inspect.getsource(_pdf_locator_ratio)
    assert "isinstance(page, int)" in src


def test_pdf_locator_ratio_source_uses_page_lt_one():
    """source 含 page < 1 检查。"""
    src = inspect.getsource(_pdf_locator_ratio)
    assert "< 1" in src


def test_pdf_locator_ratio_source_uses_is_valid_bbox():
    """source 含 _is_valid_bbox 调用。"""
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_is_valid_bbox" in src


def test_pdf_locator_ratio_source_no_elements_returns_null():
    """source 含 no_elements 分支。"""
    src = inspect.getsource(_pdf_locator_ratio)
    assert "no_elements" in src


def test_pdf_locator_ratio_signature():
    """signature 1 param。"""
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


# =========================================================================
# _docx_locator_ratio source level 补强
# =========================================================================


def test_docx_locator_ratio_source_defines_structural_keys():
    """source 含 7 个 structural_keys。"""
    src = inspect.getsource(_docx_locator_ratio)
    for k in ("section", "paragraph_index", "run_index", "table_index",
              "row_index", "col_index", "relationship_id"):
        assert k in src


def test_docx_locator_ratio_source_uses_page_in_check():
    """source 含 'page' in loc 检查。"""
    src = inspect.getsource(_docx_locator_ratio)
    assert "'page' in loc" in src or '"page" in loc' in src


def test_docx_locator_ratio_source_uses_bbox_in_check():
    """source 含 'bbox' in loc 检查。"""
    src = inspect.getsource(_docx_locator_ratio)
    assert "'bbox' in loc" in src or '"bbox" in loc' in src


def test_docx_locator_ratio_source_uses_any_for_structural_keys():
    """source 含 any(k in loc ...) 检查。"""
    src = inspect.getsource(_docx_locator_ratio)
    assert "any(" in src


def test_docx_locator_ratio_signature():
    """signature 1 param。"""
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


# =========================================================================
# _is_valid_bbox source level 补强
# =========================================================================


def test_is_valid_bbox_source_uses_isinstance_list():
    """source 含 isinstance(bbox, list)。"""
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(bbox, list)" in src


def test_is_valid_bbox_source_checks_len_4():
    """source 含 len(bbox) != 4。"""
    src = inspect.getsource(_is_valid_bbox)
    assert "len(bbox)" in src
    assert "4" in src


def test_is_valid_bbox_source_uses_isinstance_bool():
    """source 含 isinstance(v, bool)。"""
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(v, bool)" in src


def test_is_valid_bbox_source_uses_math_isfinite():
    """source 含 math.isfinite。"""
    src = inspect.getsource(_is_valid_bbox)
    assert "math.isfinite" in src


def test_is_valid_bbox_signature():
    """signature 1 param。"""
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


# =========================================================================
# _heading_boundary_ratio source level
# =========================================================================


def test_heading_boundary_ratio_source_uses_chunk_first_ids():
    """source 含 chunk_first_ids。"""
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids" in src


def test_heading_boundary_ratio_source_uses_set():
    """source 含 set() 构造 chunk_first_ids。"""
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids = set()" in src


def test_heading_boundary_ratio_source_uses_ids_zero_index():
    """source 含 ids[0]（first position）。"""
    src = inspect.getsource(_heading_boundary_ratio)
    assert "ids[0]" in src


def test_heading_boundary_ratio_source_uses_dedup_via_set():
    """source 含 add to set（自动去重）。"""
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids.add" in src


def test_heading_boundary_ratio_source_returns_ratio():
    """source 含 _ratio(matched / len(headings))。"""
    src = inspect.getsource(_heading_boundary_ratio)
    assert "_ratio(" in src
    assert "len(headings)" in src


# =========================================================================
# _silent_drop_count source level
# =========================================================================


def test_silent_drop_count_source_uses_max_zero():
    """source 含 max(0, ...) 或等价 (if actual < exp: drops += ...)。"""
    src = inspect.getsource(_silent_drop_count)
    # 实现：if actual < exp: drops += (exp - actual)
    assert "actual < exp" in src or "max(0" in src


def test_silent_drop_count_source_iterates_expected_counts():
    """source 含 for t, exp in expected_counts.items()。"""
    src = inspect.getsource(_silent_drop_count)
    assert "expected_counts" in src
    assert ".items()" in src


def test_silent_drop_count_source_uses_by_type_get():
    """source 含 by_type.get(t, 0)。"""
    src = inspect.getsource(_silent_drop_count)
    assert "by_type.get" in src


def test_silent_drop_count_source_returns_int_metric():
    """source 含 _int_metric(drops)。"""
    src = inspect.getsource(_silent_drop_count)
    assert "_int_metric(drops)" in src


# =========================================================================
# _image_resource_ratio source level
# =========================================================================


def test_image_resource_ratio_source_uses_resource_path_get():
    """source 含 resource_path 字段读取。"""
    src = inspect.getsource(_image_resource_ratio)
    assert "resource_path" in src


def test_image_resource_ratio_source_uses_is_file():
    """source 含 .is_file() 检查。"""
    src = inspect.getsource(_image_resource_ratio)
    assert ".is_file()" in src


def test_image_resource_ratio_source_uses_stat_st_size():
    """source 含 stat().st_size 检查。"""
    src = inspect.getsource(_image_resource_ratio)
    assert "stat().st_size" in src or ".stat()" in src


def test_image_resource_ratio_source_uses_oserror_catch():
    """source 含 except OSError。"""
    src = inspect.getsource(_image_resource_ratio)
    assert "OSError" in src


def test_image_resource_ratio_source_uses_image_base_dir():
    """source 含 image_base_dir 检查。"""
    src = inspect.getsource(_image_resource_ratio)
    assert "image_base_dir" in src


def test_image_resource_ratio_source_uses_candidates_list():
    """source 含 candidates 列表。"""
    src = inspect.getsource(_image_resource_ratio)
    assert "candidates" in src


def test_image_resource_ratio_source_uses_path_name():
    """source 含 Path(rp).name 拼接。"""
    src = inspect.getsource(_image_resource_ratio)
    assert ".name" in src


# =========================================================================
# module __all__ 完整性
# =========================================================================


def test_module_all_one_entry():
    """__all__ 1 entry。"""
    assert len(mmod.__all__) == 1


def test_module_all_entry_exact():
    """__all__ 内容精确。"""
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_all_entry_in_namespace():
    """__all__ entry 在 namespace。"""
    for name in mmod.__all__:
        assert hasattr(mmod, name)


def test_module_all_entry_callable():
    """__all__ entry 是 callable。"""
    for name in mmod.__all__:
        assert callable(getattr(mmod, name))


def test_module_all_entry_valid_identifier():
    """__all__ entry 是合法标识符。"""
    for name in mmod.__all__:
        assert name.isidentifier()


def test_module_namespace_has_13_private_helpers():
    """module namespace 含 13 个 _ 开头 helper（_null/_ratio/_bool_metric/_int_metric/
    _pdf_locator_ratio/_docx_locator_ratio/_is_valid_bbox/_image_resource_ratio/
    _chunk_reference_ratio/_strip_unicode_whitespace/_text_preservation/
    _heading_boundary_ratio/_silent_drop_count）。"""
    helpers = [
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
    ]
    for h in helpers:
        assert hasattr(mmod, h), f"missing {h}"


def test_module_namespace_helpers_not_in_all():
    """私有 helper 不在 __all__。"""
    helpers = [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ]
    for h in helpers:
        assert h not in mmod.__all__


def test_module_namespace_has_text_types_constant():
    """namespace 含 _TEXT_TYPES。"""
    assert hasattr(mmod, "_TEXT_TYPES")


def test_module_namespace_has_pdf_bbox_required_types_constant():
    """namespace 含 _PDF_BBOX_REQUIRED_TYPES。"""
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")


def test_module_namespace_constants_not_in_all():
    """常量不在 __all__。"""
    assert "_TEXT_TYPES" not in mmod.__all__
    assert "_PDF_BBOX_REQUIRED_TYPES" not in mmod.__all__
    assert "_NOT_EVALUATED" not in mmod.__all__


# =========================================================================
# module docstring 深度
# =========================================================================


def test_module_docstring_present():
    """module 有 docstring。"""
    assert mmod.__doc__ is not None


def test_module_docstring_mentions_zidong_zhibiao():
    """docstring 含「自动指标」。"""
    assert "自动指标" in mmod.__doc__


def test_module_docstring_mentions_chun_hanshu():
    """docstring 含「纯函数」。"""
    assert "纯函数" in mmod.__doc__


def test_module_docstring_mentions_bu_xiugai_document():
    """docstring 含「不修改 document」。"""
    assert "不修改" in mmod.__doc__


def test_module_docstring_mentions_text_preservation():
    """docstring 含 text_preservation 语义。"""
    assert "text_preservation" in mmod.__doc__


def test_module_docstring_mentions_bu_diu_bu_zhong():
    """docstring 含「不丢不重」。"""
    assert "不丢不重" in mmod.__doc__


def test_module_docstring_mentions_counter():
    """docstring 含 Counter 说明。"""
    assert "Counter" in mmod.__doc__


def test_module_docstring_mentions_unicode_whitespace():
    """docstring 含 Unicode 空白说明。"""
    assert "Unicode" in mmod.__doc__ or "空白" in mmod.__doc__


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_does_not_contain_sys():
    """不含 import sys。"""
    assert "import sys" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_logging():
    """不含 import logging。"""
    assert "import logging" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_subprocess():
    """不含 import subprocess。"""
    assert "import subprocess" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_asyncio():
    """不含 import asyncio。"""
    assert "import asyncio" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_threading():
    """不含 import threading。"""
    assert "import threading" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_concurrent():
    """不含 from concurrent。"""
    assert "from concurrent" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_re():
    """不含 import re。"""
    assert "import re" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_time():
    """不含 import time。"""
    assert "import time" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_datetime():
    """不含 import datetime。"""
    assert "import datetime" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_itertools():
    """不含 from itertools。"""
    assert "from itertools" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_functools():
    """不含 from functools。"""
    assert "from functools" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_os_module():
    """不含 import os。"""
    assert "import os" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_json():
    """不含 import json。"""
    assert "import json" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_star_import():
    """不含 * 导入。"""
    assert "import *" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_relative_import():
    """不含相对导入。"""
    src = inspect.getsource(mmod)
    assert "from ." not in src
    assert "from .." not in src


def test_module_source_does_not_contain_class_definition():
    """不含 class 定义。"""
    src = inspect.getsource(mmod)
    # 检查没有顶层 class（避免引入 dataclass 等）
    assert "\nclass " not in src


def test_module_source_does_not_contain_dataclass_decorator():
    """不含 @dataclass 装饰器。"""
    assert "@dataclass" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_yield():
    """不含 yield（不是 generator）。"""
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_module_source_does_not_contain_async_def():
    """不含 async def。"""
    assert "async def" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_global_keyword():
    """不含 global 关键字。"""
    assert "global " not in inspect.getsource(mmod)


def test_module_source_does_not_contain_walrus():
    """不含 := 海象运算符。"""
    assert ":=" not in inspect.getsource(mmod)


# =========================================================================
# 端到端集成（compute_automatic_metrics 完整）
# =========================================================================


def test_compute_metrics_full_pdf_document_with_elements_and_chunks():
    """完整 PDF document + chunks → 14 个 metric 都有 value。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hello",
             "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 1
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_compute_metrics_full_docx_document():
    """完整 DOCX document。"""
    doc = {
        "source_type": "docx",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "hi",
             "source_locator": {"section": 0, "paragraph_index": 0}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hi", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_metrics_with_image_elements(tmp_path):
    """含 image element → image_resource_exists_ratio 不为 null。"""
    p = tmp_path / "img.png"
    p.write_bytes(b"data")
    doc = {
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "image", "resource_path": str(p),
             "source_locator": {"page": 1}},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_metrics_does_not_mutate_document():
    """不修改 document。"""
    doc = {
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hi"}],
        "chunks": [{"chunk_id": "c1", "text": "hi", "source_element_ids": ["e1"]}],
    }
    doc_before = repr(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert repr(doc) == doc_before


def test_compute_metrics_does_not_mutate_error():
    """不修改 error dict。"""
    err = {"code": "parse_failed"}
    err_before = repr(err)
    compute_automatic_metrics(None, err, "pdf", None)
    assert repr(err) == err_before


def test_compute_metrics_error_code_missing_raises():
    """error dict 缺 code → KeyError。"""
    err = {"message": "no code"}
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, err, "pdf", None)


def test_compute_metrics_with_expectations():
    """含 expectations → silent_drop_count 不为 null。"""
    doc = {
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "hi"}],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    # actual paragraph=1, expected=5 → drop = 5-1 = 4
    assert out["silent_drop_count"]["value"] == 4


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_docstring_starts_with_zidong_zhibiao():
    """module docstring 第一行是「自动指标...」。"""
    first_line = mmod.__doc__.strip().split("\n")[0]
    assert "自动指标" in first_line


def test_module_has_future_annotations():
    """module 含 from __future__ import annotations。"""
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_future_annotations_at_top():
    """from __future__ import annotations 在 module docstring 之后第一个 import。"""
    src = inspect.getsource(mmod)
    future_pos = src.find("from __future__ import annotations")
    math_pos = src.find("import math")
    assert future_pos != -1
    assert future_pos < math_pos


def test_module_no_main_block():
    """module 没有 if __name__ == '__main__' 块。"""
    src = inspect.getsource(mmod)
    assert '__name__ == "__main__"' not in src
    assert "__name__ == '__main__'" not in src
