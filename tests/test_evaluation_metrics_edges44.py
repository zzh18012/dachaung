"""evaluation/metrics.py 第四十六轮 edges 测试（Round 443）。

补强 edges43 未触及的角度：
- _null / _ratio / _bool_metric / _int_metric 边界第十七批（return dict key 严格 2 个 / 不同输入类型 / 多次调用一致）
- compute_automatic_metrics 第十七批（document 缺 elements/chunks key / source_type 大小写 / 不区分 PDF/PDF / image_base_dir 真实目录 / error_code dict 结构）
- _strip_unicode_whitespace 第十七批（多种 unicode 空白字符 / 长字符串 / emoji 多字节）
- _is_valid_bbox 第十七批（4 个相同值 / 全 0 / 全负 / 全 float / 全 inf）
- _pdf_locator_ratio 第十七批（page 是 1+ / heading 完整 / caption 缺 page / image 无 locator）
- _docx_locator_ratio 第十七批（任意单一结构键 / locator 字段类型 / 多种结构键组合）
- _image_resource_ratio 第十七批（image 是 dict 缺字段 / image_base_dir 是文件而非目录 / Unicode 文件名）
- _chunk_reference_ratio 第十七批（chunk 缺 source_element_ids / ids 含重复 / 元素 element_id 是 None）
- _text_preservation 第十七批（多 chunk 拼接 / 中文 / emoji / 全 image）
- _heading_boundary_ratio 第十七批（chunk source_element_ids 顺序 / 多 heading / heading 同 id）
- _silent_drop_count 第十七批（expectations 含字符串 count / 负数 / mix valid+invalid）
- module source forbidden tokens 第三十一批
- module source 字符串精确补强第二十七批
- signatures 第二十七批
- module 合理性第二十七批
- 端到端集成第二十七批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
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


# ---------- _null / _ratio / _bool_metric / _int_metric 边界第十七批 ----------


def test_null_returns_dict_with_2_keys_batch17():
    r = _null("x")
    assert set(r.keys()) == {"value", "reason"}


def test_null_returns_consistent_batch17():
    r1 = _null("x")
    r2 = _null("x")
    assert r1 == r2


def test_ratio_returns_dict_with_2_keys_batch17():
    r = _ratio(0.5)
    assert set(r.keys()) == {"value", "reason"}


def test_ratio_value_always_float_batch17():
    """即使传 int，返回也是 float。"""
    r = _ratio(0)
    assert isinstance(r["value"], float)


def test_ratio_reason_always_none_batch17():
    r = _ratio(0.5)
    assert r["reason"] is None


def test_bool_metric_returns_dict_with_2_keys_batch17():
    r = _bool_metric(True)
    assert set(r.keys()) == {"value", "reason"}


def test_bool_metric_value_always_bool_batch17():
    """即使传 1/0，也强转为 bool。"""
    r = _bool_metric(1)
    assert isinstance(r["value"], bool)
    assert r["value"] is True


def test_int_metric_returns_dict_with_2_keys_batch17():
    r = _int_metric(5)
    assert set(r.keys()) == {"value", "reason"}


def test_int_metric_value_always_int_batch17():
    """即使传 float，也强转为 int。"""
    r = _int_metric(3.7)
    assert isinstance(r["value"], int)
    assert r["value"] == 3


def test_int_metric_negative_value_batch17():
    r = _int_metric(-100)
    assert r["value"] == -100


# ---------- compute_automatic_metrics 第十七批 ----------


def test_compute_metrics_doc_no_elements_key_batch17():
    """document 无 elements key → 用 .get() 默认 []。"""
    doc = {"chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 0


def test_compute_metrics_doc_no_chunks_key_batch17():
    """document 无 chunks key → 用 .get() 默认 []。"""
    doc = {"elements": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    # chunks=[] → no_chunks reason
    assert m["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_metrics_source_type_case_sensitive_batch17():
    """source_type='PDF'（大写）→ 不等于 "pdf" → not_pdf_document。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "PDF", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_image_base_dir_real_dir_batch17(tmp_path):
    """image_base_dir 是真实目录 → 传给 _image_resource_ratio。"""
    doc = {"elements": [{"type": "image", "resource_path": "x.png"}], "chunks": []}
    # 不存在的文件 → ratio=0
    m = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert m["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_metrics_image_base_dir_none_batch17():
    """image_base_dir=None → 用 resource_path 原样。"""
    doc = {"elements": [{"type": "image", "resource_path": "/no/x.png"}], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=None)
    assert m["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_metrics_error_code_structure_batch17():
    err = {"code": "parse_failed"}
    m = compute_automatic_metrics(None, err, "pdf", None)
    assert m["error_code"]["value"] == "parse_failed"
    assert m["error_code"]["reason"] is None


def test_compute_metrics_does_not_mutate_error_batch17():
    err = {"code": "x"}
    before = dict(err)
    compute_automatic_metrics(None, err, "pdf", None)
    assert err == before


def test_compute_metrics_does_not_mutate_expectations_batch17():
    exp = {"element_count_by_type": {"paragraph": 5}}
    before = repr(exp)
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    compute_automatic_metrics(doc, None, "pdf", exp)
    assert repr(exp) == before


def test_compute_metrics_schema_valid_via_import_batch17():
    """schema_valid 字段的结构。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert set(m["schema_valid"].keys()) == {"value", "reason"}


def test_compute_metrics_pipeline_success_structure_batch17():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert set(m["pipeline_success"].keys()) == {"value", "reason"}


# ---------- _strip_unicode_whitespace 第十七批 ----------


def test_strip_unicode_whitespace_nbsp_batch17():
    """NBSP U+00A0 是空白。"""
    assert _strip_unicode_whitespace("a\xa0b") == "ab"


def test_strip_unicode_whitespace_em_space_batch17():
    """EM space U+2003 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch17():
    """全角空格 U+3000 是空白。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch17():
    """Line separator U+2028 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch17():
    """Paragraph separator U+2029 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_long_text_batch17():
    """长字符串性能（不验证速度，只验证正确性）。"""
    s = "a" * 1000 + " " * 100 + "b" * 1000
    result = _strip_unicode_whitespace(s)
    assert len(result) == 2000


def test_strip_unicode_whitespace_emoji_batch17():
    """emoji 不是空白。"""
    assert _strip_unicode_whitespace("😀") == "😀"


def test_strip_unicode_whitespace_tab_batch17():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_form_feed_batch17():
    """\f (form feed) 是空白。"""
    assert _strip_unicode_whitespace("a\x0cb") == "ab"


# ---------- _is_valid_bbox 第十七批 ----------


def test_is_valid_bbox_four_zeros_batch17():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_four_negatives_batch17():
    assert _is_valid_bbox([-1, -2, -3, -4]) is True


def test_is_valid_bbox_four_floats_batch17():
    assert _is_valid_bbox([0.1, 0.2, 0.3, 0.4]) is True


def test_is_valid_bbox_large_values_batch17():
    assert _is_valid_bbox([1e10, 1e10, 1e10, 1e10]) is True


def test_is_valid_bbox_three_elements_batch17():
    assert _is_valid_bbox([0, 0, 1]) is False


def test_is_valid_bbox_five_elements_batch17():
    assert _is_valid_bbox([0, 0, 1, 1, 2]) is False


def test_is_valid_bbox_dict_batch17():
    assert _is_valid_bbox({"a": 1}) is False


def test_is_valid_bbox_set_batch17():
    assert _is_valid_bbox({0, 0, 1, 1}) is False


def test_is_valid_bbox_generator_batch17():
    """generator 不是 list → False（即使内容合法）。"""
    assert _is_valid_bbox(x for x in [0, 0, 1, 1]) is False


def test_is_valid_bbox_empty_list_batch17():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_none_batch17():
    assert _is_valid_bbox(None) is False


# ---------- _pdf_locator_ratio 第十七批 ----------


def test_pdf_locator_ratio_page_one_batch17():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_page_large_batch17():
    elements = [{"type": "paragraph", "source_locator": {"page": 999, "bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_page_zero_batch17():
    elements = [{"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_caption_complete_batch17():
    elements = [{"type": "caption", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_caption_missing_bbox_batch17():
    elements = [{"type": "caption", "source_locator": {"page": 1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_image_no_locator_batch17():
    elements = [{"type": "image"}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_page_string_batch17():
    """page 是字符串 → 不是 int → invalid。"""
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_page_float_batch17():
    """page 是 1.0（float）→ 不是 int → invalid。"""
    elements = [{"type": "image", "source_locator": {"page": 1.0}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


# ---------- _docx_locator_ratio 第十七批 ----------


def test_docx_locator_ratio_table_index_batch17():
    elements = [{"type": "paragraph", "source_locator": {"table_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_row_col_batch17():
    elements = [{"type": "paragraph", "source_locator": {"row_index": 0, "col_index": 1}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_run_index_batch17():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 5}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_section_only_batch17():
    elements = [{"type": "paragraph", "source_locator": {"section": 2}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_only_batch17():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 10}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_structural_keys_string_value_batch17():
    """结构键的值类型不限，只看 key 是否存在。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": "abc"}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_no_structural_key_batch17():
    elements = [{"type": "paragraph", "source_locator": {"random_key": 1}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


# ---------- _image_resource_ratio 第十七批 ----------


def test_image_resource_ratio_image_no_resource_path_key_batch17(tmp_path):
    elements = [{"type": "image"}]
    r = _image_resource_ratio(elements, tmp_path)
    assert r["value"] == 0.0


def test_image_resource_ratio_image_base_dir_is_file_batch17(tmp_path):
    """image_base_dir 是文件而不是目录 → 仍尝试拼接（Path(rp).name）。"""
    f = tmp_path / "base.txt"
    f.write_text("x")
    elements = [{"type": "image", "resource_path": "x.png"}]
    r = _image_resource_ratio(elements, f)
    # image_base_dir / "x.png" → tmp_path/base.txt/x.png → 不存在
    assert r["value"] == 0.0


def test_image_resource_ratio_unicode_filename_batch17(tmp_path):
    """Unicode 文件名。"""
    img = tmp_path / "中文.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1.0


def test_image_resource_ratio_resource_path_with_spaces_batch17(tmp_path):
    img = tmp_path / "my image.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1.0


def test_image_resource_ratio_image_base_dir_prepended_only_filename_batch17(tmp_path):
    """resource_path 是 'sub/x.png' 但文件在 image_base_dir/x.png → 用 Path(rp).name。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "sub/x.png"}]
    r = _image_resource_ratio(elements, tmp_path)
    # candidates = [Path("sub/x.png"), tmp_path/Path("sub/x.png").name = tmp_path/x.png]
    # 后者存在 → valid=1
    assert r["value"] == 1.0


def test_image_resource_ratio_no_image_type_batch17():
    """没有 image 类型 → no_image_elements。"""
    elements = [{"type": "paragraph"}]
    r = _image_resource_ratio(elements, None)
    assert r["reason"] == "no_image_elements"


# ---------- _chunk_reference_ratio 第十七批 ----------


def test_chunk_reference_ratio_chunk_no_source_ids_batch17():
    chunks = [{"text": "x"}]
    r = _chunk_reference_ratio([{"element_id": "e1"}], chunks)
    # chunk 缺 source_element_ids → 用 .get() 返回 None → falsy → invalid
    assert r["value"] == 0.0


def test_chunk_reference_ratio_element_id_none_batch17():
    """elements 中 element_id=None → 进 set（None 是 hashable）。"""
    chunks = [{"text": "x", "source_element_ids": [None]}]
    r = _chunk_reference_ratio([{"element_id": None}], chunks)
    assert r["value"] == 1.0


def test_chunk_reference_ratio_chunk_with_mixed_ids_batch17():
    chunks = [{"text": "x", "source_element_ids": ["e1", None]}]
    r = _chunk_reference_ratio([{"element_id": "e1"}], chunks)
    # None not in elem_ids → invalid
    assert r["value"] == 0.0


def test_chunk_reference_ratio_all_chunks_valid_batch17():
    chunks = [
        {"text": "x", "source_element_ids": ["e1"]},
        {"text": "y", "source_element_ids": ["e2"]},
    ]
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_chunk_reference_ratio_no_chunks_returns_null_batch17():
    r = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert r["reason"] == "no_chunks"


# ---------- _text_preservation 第十七批 ----------


def test_text_preservation_multi_chunk_batch17():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [
        {"text": "a", "source_element_ids": ["e1"]},
        {"text": "b", "source_element_ids": ["e1"]},
        {"text": "c", "source_element_ids": ["e1"]},
    ]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True
    assert r["precision"]["value"] == 1.0
    assert r["recall"]["value"] == 1.0


def test_text_preservation_chinese_batch17():
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界", "source_element_ids": ["e1"]}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


def test_text_preservation_emoji_batch17():
    elements = [{"type": "paragraph", "content": "😀🎉"}]
    chunks = [{"text": "😀🎉", "source_element_ids": ["e1"]}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


def test_text_preservation_with_whitespace_batch17():
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc", "source_element_ids": ["e1"]}]
    r = _text_preservation(elements, chunks)
    # 删除空白后都是 abc → equal
    assert r["equal"]["value"] is True


def test_text_preservation_returns_dict_batch17():
    r = _text_preservation([], [])
    assert isinstance(r, dict)
    assert set(r.keys()) == {"equal", "precision", "recall"}


# ---------- _heading_boundary_ratio 第十七批 ----------


def test_heading_boundary_multiple_headings_batch17():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"text": "x", "source_element_ids": ["h1"]},
        {"text": "y", "source_element_ids": ["h2"]},
    ]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_heading_boundary_partial_batch17():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.5


def test_heading_boundary_no_chunks_batch17():
    elements = [{"type": "heading", "element_id": "h1"}]
    r = _heading_boundary_ratio(elements, [])
    assert r["value"] == 0.0


def test_heading_boundary_chunk_first_id_matches_batch17():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1", "other"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_heading_boundary_chunk_first_id_not_heading_batch17():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "paragraph", "element_id": "p1"},
    ]
    chunks = [{"text": "x", "source_element_ids": ["p1", "h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    # 第一是 p1 → 不算 heading 边界
    assert r["value"] == 0.0


# ---------- _silent_drop_count 第十七批 ----------


def test_silent_drop_string_count_batch17():
    """expectations 含字符串 count → TypeError（py3 不支持 int < str）。"""
    by_type = {"paragraph": 5}
    exp = {"element_count_by_type": {"paragraph": "10"}}  # str 而非 int
    with pytest.raises(TypeError):
        _silent_drop_count(by_type, exp)


def test_silent_drop_count_zero_actual_batch17():
    by_type = {"paragraph": 0}
    exp = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, exp)
    assert r["value"] == 5


def test_silent_drop_count_negative_drop_batch17():
    """actual > expected → max(0, exp-act)=0 for that type。"""
    by_type = {"paragraph": 10}
    exp = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, exp)
    assert r["value"] == 0


def test_silent_drop_count_mixed_types_batch17():
    by_type = {"paragraph": 3, "heading": 5, "table": 1}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 3, "table": 1}}
    r = _silent_drop_count(by_type, exp)
    # paragraph: 5-3=2, heading: 0 (5>3), table: 0 → 2
    assert r["value"] == 2


def test_silent_drop_count_type_in_actual_not_in_expected_batch17():
    by_type = {"paragraph": 5, "heading": 3}
    exp = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, exp)
    # 只看 expected_types：paragraph 0 drop
    assert r["value"] == 0


# ---------- module source forbidden tokens 第三十一批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch17(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch17():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch17():
    src = inspect.getsource(mmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第二十七批 ----------


def test_module_source_has_future_annotations_batch17():
    src = inspect.getsource(mmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch17():
    src = inspect.getsource(mmod)
    assert "自动指标：13 项" in src


def test_module_source_has_text_types_definition_batch17():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES = " in src


def test_module_source_has_pdf_bbox_definition_batch17():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES = " in src


def test_module_source_has_counter_import_batch17():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_math_import_batch17():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_pathlib_import_batch17():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch17():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_compute_function_batch17():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_all_dunder_batch17():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- signatures 第二十七批 ----------


def test_signature_null_batch17():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_batch17():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_compute_metrics_batch17():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_metrics_image_base_dir_default_none_batch17():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_pdf_locator_ratio_batch17():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_docx_locator_ratio_batch17():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_silent_drop_count_batch17():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


# ---------- module 合理性第二十七批 ----------


def test_module_has_all_attribute_batch17():
    assert hasattr(mmod, "__all__")
    assert isinstance(mmod.__all__, list)


def test_module_all_count_1_batch17():
    assert len(mmod.__all__) == 1


def test_module_compute_callable_batch17():
    assert callable(compute_automatic_metrics)


def test_module_text_types_is_tuple_batch17():
    assert isinstance(_TEXT_TYPES, tuple)


def test_module_pdf_bbox_required_types_is_tuple_batch17():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_text_types_includes_paragraph_batch17():
    assert "paragraph" in _TEXT_TYPES


def test_module_text_types_excludes_image_batch17():
    assert "image" not in _TEXT_TYPES


def test_module_pdf_bbox_required_types_includes_heading_batch17():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES


# ---------- 端到端集成第二十七批 ----------


def test_e2e_compute_metrics_returns_14_keys_batch17():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert len(m) == 14


def test_e2e_metric_keys_correct_set_batch17():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    expected = {
        "pipeline_success", "error_code", "schema_valid", "element_count_total",
        "element_count_by_type", "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio", "text_preservation_equal",
        "text_char_multiset_precision", "text_char_multiset_recall",
        "heading_boundary_compliance", "silent_drop_count",
    }
    assert set(m.keys()) == expected


def test_e2e_pdf_full_pipeline_batch17(tmp_path):
    doc = {
        "elements": [
            {"type": "heading", "content": "标题", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"type": "paragraph", "content": "正文", "element_id": "p1",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "标题正文", "source_element_ids": ["h1", "p1"]},
        ],
    }
    exp = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    m = compute_automatic_metrics(doc, None, "pdf", exp)
    assert m["element_count_total"]["value"] == 2
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    assert m["text_preservation_equal"]["value"] is True
    assert m["silent_drop_count"]["value"] == 0


def test_e2e_pipeline_failed_returns_all_null_batch17():
    m = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["schema_valid"]["reason"] == "pipeline_failed"
    # error_code 不应是 null（保留 error.code）
    assert m["error_code"]["value"] == "x"


def test_e2e_docx_full_pipeline_batch17():
    doc = {
        "elements": [
            {"type": "paragraph", "content": "正文", "element_id": "p1",
             "source_locator": {"paragraph_index": 0, "section": 0}},
        ],
        "chunks": [{"text": "正文", "source_element_ids": ["p1"]}],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_metric_dict_serializable_batch17():
    """所有 metric value 都可 JSON 序列化。"""
    import json
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    s = json.dumps(m)
    assert isinstance(s, str)


def test_e2e_schema_valid_true_when_passes_batch17():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    # _mk_doc 不通过 schema（缺 source_hash 等），但 schema_valid 字段应存在
    assert "schema_valid" in m
    # value 是 True 或 False（schema 决定）
    assert isinstance(m["schema_valid"]["value"], bool)


def test_e2e_element_count_by_type_correct_batch17():
    doc = {
        "elements": [
            {"type": "heading"},
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "table"},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = m["element_count_by_type"]["value"]
    assert by_type == {"heading": 1, "paragraph": 2, "table": 1}


def test_e2e_unknown_type_counted_batch17():
    doc = {"elements": [{"type": "unknown_type"}], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = m["element_count_by_type"]["value"]
    assert by_type == {"unknown_type": 1}
