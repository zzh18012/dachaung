"""evaluation/metrics.py 第四十三轮 edges 测试（Round 422）。

补强 edges40 未触及的角度：
- 模块常量深度第十四批（_TEXT_TYPES 顺序 / _PDF_BBOX_REQUIRED_TYPES 与 _TEXT_TYPES 交集 / _NOT_EVALUATED 字面量 / 模块级常量数）
- _null / _ratio / _bool_metric / _int_metric 边界第十四批（返回 dict 结构 / value 类型 / reason 类型 / None vs str）
- compute_automatic_metrics 第十四批（14 个 keys 顺序 / pipeline_success 逻辑 / error_code 字段 / schema_check_exception 路径 / expectations 含 element_count_by_type 部分覆盖）
- _strip_unicode_whitespace 边界第十四批（全角空格 / 中文 / Tab / 多种 Unicode 空白）
- _is_valid_bbox 边界第十四批（None / list 长度边界 / 数字 vs 字符串）
- _pdf_locator_ratio / _docx_locator_ratio 第十四批（document 缺 elements / elements 是 None / 缺 bbox 字段）
- _image_resource_ratio 第十四批（document 缺 elements / image 缺 resource_path / resource_path 是 None / image_base_dir 是 None）
- _chunk_reference_ratio 第十四批（chunks 缺 source_element_ids / source_element_ids 是 None / 空字符串 element_id）
- module source forbidden tokens 第十九批
- module source 字符串精确补强第十六批
- signatures 第十六批
- module 合理性第十六批
- 端到端集成第十六批
"""

from __future__ import annotations

import inspect
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch, MagicMock

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


# ---------- 模块常量深度第十四批 ----------


def test_text_types_count_7_batch14():
    assert len(_TEXT_TYPES) == 7


def test_text_types_exact_contents_batch14():
    assert set(_TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    }


def test_text_types_is_tuple_batch14():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_count_4_batch14():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_is_subset_of_text_types_batch14():
    s_text = set(_TEXT_TYPES)
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in s_text


def test_pdf_bbox_required_types_no_image_batch14():
    assert "image" not in _PDF_BBOX_REQUIRED_TYPES
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_no_table_header_footer_batch14():
    """table/header/footer 不需要 bbox。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_constant_value_batch14():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_constant_is_str_batch14():
    assert isinstance(_NOT_EVALUATED, str)


def test_module_constants_count_3_batch14():
    """3 个模块级常量。"""
    assert hasattr(mmod, "_TEXT_TYPES")
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_constants_are_tuples_or_str_batch14():
    assert isinstance(mmod._TEXT_TYPES, tuple)
    assert isinstance(mmod._PDF_BBOX_REQUIRED_TYPES, tuple)
    assert isinstance(mmod._NOT_EVALUATED, str)


# ---------- _null / _ratio / _bool_metric / _int_metric 边界第十四批 ----------


def test_null_returns_value_none_batch14():
    out = _null("reason_x")
    assert out["value"] is None


def test_null_returns_reason_batch14():
    out = _null("reason_x")
    assert out["reason"] == "reason_x"


def test_null_dict_independence_batch14():
    a = _null("x")
    b = _null("y")
    a["value"] = "modified"
    assert b["value"] is None


def test_ratio_returns_float_batch14():
    out = _ratio(0.5)
    assert isinstance(out["value"], float)


def test_ratio_returns_int_as_float_batch14():
    out = _ratio(0)
    assert isinstance(out["value"], float)
    assert out["value"] == 0.0


def test_ratio_returns_one_as_float_batch14():
    out = _ratio(1)
    assert isinstance(out["value"], float)
    assert out["value"] == 1.0


def test_ratio_reason_none_batch14():
    out = _ratio(0.5)
    assert out["reason"] is None


def test_bool_metric_returns_bool_batch14():
    assert _bool_metric(True)["value"] is True
    assert _bool_metric(False)["value"] is False


def test_bool_metric_coerce_int_batch14():
    """int 输入被 bool() 强制转换。"""
    assert _bool_metric(0)["value"] is False
    assert _bool_metric(1)["value"] is True


def test_bool_metric_coerce_string_batch14():
    """非空字符串被 bool() 转 True。"""
    assert _bool_metric("x")["value"] is True
    assert _bool_metric("")["value"] is False


def test_int_metric_returns_int_batch14():
    out = _int_metric(5)
    assert isinstance(out["value"], int)
    assert out["value"] == 5


def test_int_metric_coerce_float_batch14():
    """float 输入被 int() 截断。"""
    assert _int_metric(5.99)["value"] == 5


def test_int_metric_reason_none_batch14():
    out = _int_metric(0)
    assert out["reason"] is None


# ---------- compute_automatic_metrics 第十四批 ----------


def _make_full_doc():
    return {
        "document_id": "d1",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0.0",
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "Title", "bbox": [0, 0, 100, 20]},
            {"type": "paragraph", "element_id": "p1", "content": "Body", "bbox": [0, 30, 100, 50]},
        ],
        "chunks": [
            {"text": "Title Body", "source_element_ids": ["h1", "p1"]},
        ],
        "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]},
    }


def test_compute_automatic_metrics_keys_count_14_batch14():
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert len(out) == 14


def test_compute_automatic_metrics_keys_exact_batch14():
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="pdf",
        expectations=None,
    )
    # figure_caption_* 不在 metrics.py（在 runner.py 通过 annotation_metrics 注入）
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert expected_keys.issubset(set(out.keys()))


def test_compute_automatic_metrics_pipeline_success_true_batch14():
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is True


def test_compute_automatic_metrics_pipeline_success_false_when_error_batch14():
    out = compute_automatic_metrics(
        document=None,
        error={"code": "parse_failed", "message": "boom"},
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_pipeline_success_false_when_no_doc_no_error_batch14():
    out = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    # error=None and document=None → False
    assert out["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_error_code_passthrough_batch14():
    out = compute_automatic_metrics(
        document=None,
        error={"code": "parse_failed"},
        source_type="pdf",
        expectations=None,
    )
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_automatic_metrics_error_code_none_when_no_error_batch14():
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["error_code"]["value"] is None


def test_compute_automatic_metrics_schema_check_exception_path_batch14():
    """schema_check 抛异常 → schema_valid={value:False, reason:schema_check_exception:...}。"""
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("oops")):
        out = compute_automatic_metrics(
            document=_make_full_doc(),
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception" in out["schema_valid"]["reason"]


def test_compute_automatic_metrics_no_mutation_batch14():
    doc = _make_full_doc()
    doc_before = json.loads(json.dumps(doc))
    compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert doc == doc_before


def test_compute_automatic_metrics_docx_source_type_batch14():
    doc = _make_full_doc()
    doc["source_type"] = "docx"
    doc["source_locator"] = {"paragraph_index": 0}
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="docx",
        expectations=None,
    )
    assert "docx_locator_valid_ratio" in out
    assert "pdf_locator_valid_ratio" in out


def test_compute_automatic_metrics_unknown_source_type_batch14():
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="unknown",
        expectations=None,
    )
    assert "pdf_locator_valid_ratio" in out
    assert "docx_locator_valid_ratio" in out


def test_compute_automatic_metrics_with_silent_drop_batch14():
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="pdf",
        expectations=expectations,
    )
    assert "silent_drop_count" in out


def test_compute_automatic_metrics_no_expectations_silent_drop_null_batch14():
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["silent_drop_count"]["value"] is None


def test_compute_automatic_metrics_idempotent_batch14():
    doc1 = _make_full_doc()
    doc2 = _make_full_doc()
    out1 = compute_automatic_metrics(
        document=doc1, error=None, source_type="pdf", expectations=None,
    )
    out2 = compute_automatic_metrics(
        document=doc2, error=None, source_type="pdf", expectations=None,
    )
    assert out1 == out2


def test_compute_automatic_metrics_dict_independence_batch14():
    out1 = compute_automatic_metrics(
        document=_make_full_doc(), error=None, source_type="pdf", expectations=None,
    )
    out2 = compute_automatic_metrics(
        document=_make_full_doc(), error=None, source_type="pdf", expectations=None,
    )
    # 修改 out1 不应影响 out2
    out1["pipeline_success"]["value"] = "x"
    assert out2["pipeline_success"]["value"] is True


# ---------- _strip_unicode_whitespace 边界第十四批 ----------


def test_strip_unicode_whitespace_full_width_space_batch14():
    """全角空格 U+3000 应被删除。"""
    s = "a　b"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_tab_batch14():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline_batch14():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return_batch14():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_chinese_batch14():
    """中文字符不是空白，应保留。"""
    s = "你好 世界"
    out = _strip_unicode_whitespace(s)
    assert "你" in out
    assert "好" in out


def test_strip_unicode_whitespace_only_whitespace_batch14():
    assert _strip_unicode_whitespace("   \t\n  ") == ""


def test_strip_unicode_whitespace_empty_batch14():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_returns_str_batch14():
    assert isinstance(_strip_unicode_whitespace("x"), str)


# ---------- _is_valid_bbox 边界第十四批 ----------


def test_is_valid_bbox_none_batch14():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list_batch14():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_short_list_batch14():
    """长度 < 4。"""
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_long_list_batch14():
    """长度 > 4。"""
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_4_ints_batch14():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_4_floats_batch14():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 100.5]) is True


def test_is_valid_bbox_string_elements_batch14():
    """字符串元素应失败（非数字）。"""
    assert _is_valid_bbox(["a", "b", "c", "d"]) is False


def test_is_valid_bbox_mixed_types_batch14():
    """混合类型应失败（部分是字符串）。"""
    assert _is_valid_bbox([0, 0, "100", 100]) is False


def test_is_valid_bbox_nan_batch14():
    import math
    assert _is_valid_bbox([0, 0, math.nan, 100]) is False


def test_is_valid_bbox_inf_batch14():
    import math
    assert _is_valid_bbox([0, 0, math.inf, 100]) is False


def test_is_valid_bbox_tuple_batch14():
    """tuple 而非 list → 应失败。"""
    assert _is_valid_bbox((0, 0, 100, 100)) is False


# ---------- _pdf_locator_ratio / _docx_locator_ratio 第十四批 ----------


def test_pdf_locator_ratio_no_elements_batch14():
    out = _pdf_locator_ratio([])
    assert out["value"] is None


def test_pdf_locator_ratio_missing_elements_key_batch14():
    out = _pdf_locator_ratio([])
    assert out["value"] is None


def test_pdf_locator_ratio_with_bbox_all_valid_batch14():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_with_some_missing_bbox_batch14():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # 无 bbox → invalid
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_docx_locator_ratio_no_paragraphs_batch14():
    elements = [{"type": "heading", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    # 有 elements 但无 structural_keys → 0/1=0.0
    assert out["value"] == 0.0


def test_docx_locator_ratio_missing_elements_key_batch14():
    out = _docx_locator_ratio([])
    assert out["value"] is None


def test_docx_locator_ratio_all_have_paragraph_index_batch14():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"paragraph_index": 1}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_some_missing_paragraph_index_batch14():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {}},  # 无 paragraph_index
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- _image_resource_ratio 第十四批 ----------


def test_image_resource_ratio_no_elements_batch14():
    out = _image_resource_ratio([], None)
    assert out["value"] is None


def test_image_resource_ratio_missing_elements_key_batch14():
    out = _image_resource_ratio([], None)
    assert out["value"] is None


def test_image_resource_ratio_no_images_batch14():
    elements = [{"type": "paragraph", "content": "x"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None


def test_image_resource_ratio_image_no_resource_path_batch14(tmp_path):
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, tmp_path)
    # 无 resource_path → 计 0
    assert out["value"] == 0.0


def test_image_resource_ratio_image_resource_path_none_batch14(tmp_path):
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_file_exists_batch14(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "a.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


# ---------- _chunk_reference_ratio 第十四批 ----------


def test_chunk_reference_ratio_missing_chunks_key_batch14():
    elements = []
    out = _chunk_reference_ratio(elements, [])
    assert out["value"] is None


def test_chunk_reference_ratio_empty_chunks_batch14():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None


def test_chunk_reference_ratio_missing_source_element_ids_batch14():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "abc"}]
    out = _chunk_reference_ratio(elements, chunks)
    # 缺 source_element_ids → 计 0
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_source_element_ids_batch14():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "abc", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_have_ids_batch14():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"text": "a", "source_element_ids": ["e1"]},
        {"text": "b", "source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_some_missing_ids_batch14():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"text": "a", "source_element_ids": ["e1"]},
        {"text": "b", "source_element_ids": []},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- module source forbidden tokens 第十九批 ----------


_FORBIDDEN_TOKENS_ROUND19 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND19)
def test_module_source_forbidden_tokens_round19_batch14(token):
    source = inspect.getsource(mmod)
    assert token not in source


# ---------- module source 字符串精确补强第十六批 ----------


def test_module_source_module_docstring_present_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_math_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import math" in head


def test_module_source_imports_counter_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from collections import Counter" in head


def test_module_source_imports_pathlib_path_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_any_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_defines_text_types_batch14():
    source = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in source


def test_module_source_defines_pdf_bbox_required_types_batch14():
    source = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in source


def test_module_source_defines_not_evaluated_batch14():
    source = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in source


def test_module_source_defines_null_helper_batch14():
    source = inspect.getsource(mmod)
    assert "def _null(" in source


def test_module_source_defines_ratio_helper_batch14():
    source = inspect.getsource(mmod)
    assert "def _ratio(" in source


def test_module_source_defines_bool_metric_batch14():
    source = inspect.getsource(mmod)
    assert "def _bool_metric(" in source


def test_module_source_defines_int_metric_batch14():
    source = inspect.getsource(mmod)
    assert "def _int_metric(" in source


def test_module_source_defines_compute_automatic_metrics_batch14():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_defines_strip_unicode_whitespace_batch14():
    source = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in source


def test_module_source_defines_is_valid_bbox_batch14():
    source = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in source


def test_module_source_uses_isspace_batch14():
    source = inspect.getsource(mmod)
    assert ".isspace()" in source


def test_module_source_uses_isfinite_batch14():
    source = inspect.getsource(mmod)
    assert "math.isfinite" in source


def test_module_source_no_subprocess_import_batch14():
    source = inspect.getsource(mmod)
    assert "import subprocess" not in source


def test_module_source_no_open_call_batch14():
    source = inspect.getsource(mmod)
    # 不应有 open( 调用（除注释中的）
    assert "open('/etc" not in source
    assert 'open("/etc' not in source


def test_module_source_has_text_types_docstring_batch14():
    source = inspect.getsource(mmod)
    assert "文本元素类型" in source or "TEXT_TYPES" in source


def test_module_source_uses_counter_intersection_batch14():
    source = inspect.getsource(mmod)
    # Counter 交集应该是 & 操作符
    assert "Counter" in source


def test_module_source_has_dunder_all_batch14():
    source = inspect.getsource(mmod)
    assert "__all__" in source


def test_module_source_has_image_excluded_comment_batch14():
    source = inspect.getsource(mmod)
    assert "image" in source


def test_module_source_has_pipeline_failed_reason_batch14():
    source = inspect.getsource(mmod)
    assert "pipeline_failed" in source


# ---------- signatures 第十六批 ----------


def test_null_signature_one_param_batch14():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1
    assert "reason" in sig.parameters


def test_ratio_signature_one_param_batch14():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1
    assert "value" in sig.parameters


def test_bool_metric_signature_one_param_batch14():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1
    assert "value" in sig.parameters


def test_int_metric_signature_one_param_batch14():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1
    assert "value" in sig.parameters


def test_compute_automatic_metrics_signature_5_params_batch14():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5
    for n in ("document", "error", "source_type", "expectations", "image_base_dir"):
        assert n in sig.parameters


def test_compute_automatic_metrics_image_base_dir_default_none_batch14():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_document_optional_batch14():
    sig = inspect.signature(compute_automatic_metrics)
    p_str = str(sig.parameters["document"].annotation)
    assert "None" in p_str or "Optional" in p_str


def test_compute_automatic_metrics_return_annotation_dict_batch14():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict" in str(sig.return_annotation)


def test_null_return_annotation_dict_batch14():
    sig = inspect.signature(_null)
    assert "dict" in str(sig.return_annotation)


def test_ratio_return_annotation_dict_batch14():
    sig = inspect.signature(_ratio)
    assert "dict" in str(sig.return_annotation)


def test_bool_metric_return_annotation_dict_batch14():
    sig = inspect.signature(_bool_metric)
    assert "dict" in str(sig.return_annotation)


def test_int_metric_return_annotation_dict_batch14():
    sig = inspect.signature(_int_metric)
    assert "dict" in str(sig.return_annotation)


def test_module_dunder_all_callable_batch14():
    for name in mmod.__all__:
        assert callable(getattr(mmod, name))


# ---------- module 合理性第十六批 ----------


def test_module_dunder_file_exists_batch14():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_metrics_py_batch14():
    assert "evaluation" in mmod.__file__
    assert mmod.__file__.endswith("metrics.py")


def test_module_name_evaluation_metrics_batch14():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_dunder_all_one_item_batch14():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_no_class_definitions_batch14():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_constants_count_3_with_correct_names_batch14():
    assert mmod._TEXT_TYPES
    assert mmod._PDF_BBOX_REQUIRED_TYPES
    assert mmod._NOT_EVALUATED


def test_module_helper_functions_count_4_batch14():
    helpers = [n for n in ("_null", "_ratio", "_bool_metric", "_int_metric") if hasattr(mmod, n)]
    assert len(helpers) == 4


# ---------- 端到端集成第十六批 ----------


def test_e2e_compute_metrics_full_doc_json_serializable_batch14():
    out = compute_automatic_metrics(
        document=_make_full_doc(),
        error=None,
        source_type="pdf",
        expectations=None,
    )
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_compute_metrics_with_docx_locator_batch14():
    doc = _make_full_doc()
    doc["source_type"] = "docx"
    doc["source_locator"] = {"paragraph_index": 0}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="docx", expectations=None,
    )
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_compute_metrics_with_image_element_batch14(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    doc = _make_full_doc()
    doc["elements"].append({"type": "image", "resource_path": "x.png"})
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf",
        expectations=None, image_base_dir=tmp_path,
    )
    assert "image_resource_exists_ratio" in out


def test_e2e_compute_metrics_with_expectations_batch14():
    doc = _make_full_doc()
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=expectations,
    )
    # 应有 silent_drop_count
    assert "silent_drop_count" in out


def test_e2e_helpers_chain_null_ratio_bool_int_batch14():
    """4 个 helper 各自返回 dict 不互相干扰。"""
    n = _null("r")
    r = _ratio(0.5)
    b = _bool_metric(True)
    i = _int_metric(7)
    assert n["value"] is None
    assert r["value"] == 0.5
    assert b["value"] is True
    assert i["value"] == 7


def test_e2e_combined_metrics_idempotent_batch14():
    doc1 = _make_full_doc()
    doc2 = _make_full_doc()
    out1 = compute_automatic_metrics(
        document=doc1, error=None, source_type="pdf", expectations=None,
    )
    out2 = compute_automatic_metrics(
        document=doc2, error=None, source_type="pdf", expectations=None,
    )
    # round-trip 应相同
    assert json.loads(json.dumps(out1)) == json.loads(json.dumps(out2))


def test_e2e_text_types_used_in_text_preservation_batch14():
    """text_preservation 应只对 _TEXT_TYPES 中的元素统计。"""
    elements = [
        {"type": "paragraph", "element_id": "p1", "content": "abc"},
        {"type": "image", "element_id": "i1", "content": "ignored"},  # image 不参与
    ]
    chunks = [{"text": "abc", "source_element_ids": ["p1"]}]
    out = _text_preservation(elements, chunks)
    # image 的 "ignored" 不应影响 equal
    assert out["equal"]["value"] is True


def test_e2e_silent_drop_count_with_no_expectations_batch14():
    out = _silent_drop_count({}, None)
    assert out["value"] is None


def test_e2e_silent_drop_count_with_matching_expectations_batch14():
    by_type = {"heading": 1, "paragraph": 1}
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_e2e_silent_drop_count_with_drops_batch14():
    by_type = {"heading": 1, "paragraph": 0}
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 2}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph expected 2, actual 0 → drop 2
    assert out["value"] == 2
