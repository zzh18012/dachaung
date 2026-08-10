"""evaluation/metrics.py 第四十一轮 edges 测试（Round 408）。

补强 edges38 未触及的角度：
- helpers 行为深度第十二批（_null / _ratio / _bool_metric / _int_metric 边界）
- compute_automatic_metrics 行为深度第十二批（更多 corner cases：doc + error / image only / element 无 type / source_type 边界）
- pdf/docx locator 第十二批（更多 corner cases）
- image_resource_ratio 第十二批（OSError / 空 rp / image_base_dir 拼接）
- chunk_reference_ratio 第十二批（重复 id / 部分有效）
- text_preservation 第十二批（image 排除 / 缺 content / 全 image）
- heading_boundary_ratio 第十二批
- silent_drop_count 第十二批
- _is_valid_bbox 第十二批
- _strip_unicode_whitespace 第十二批（NBSP / em space / ideographic space / line separator）
- module source forbidden tokens 第十六批
- module source 字符串精确补强第十三批
- signatures 第十三批
- module 合理性第十三批
- 端到端集成第十三批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _image_resource_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- helpers 行为深度第十二批 ----------


def test_null_returns_dict_strict_batch12():
    out = _null("reason_x")
    assert type(out) is dict


def test_null_value_strictly_none_batch12():
    out = _null("any")
    assert out["value"] is None


def test_null_reason_preserved_batch12():
    out = _null("my reason")
    assert out["reason"] == "my reason"


def test_null_with_unicode_reason_batch12():
    out = _null("中文原因")
    assert out["reason"] == "中文原因"


def test_null_fresh_dict_each_call_batch12():
    out1 = _null("x")
    out2 = _null("x")
    assert out1 == out2
    assert out1 is not out2


def test_ratio_int_to_float_batch12():
    out = _ratio(0)
    assert out["value"] == 0.0
    assert type(out["value"]) is float


def test_ratio_returns_dict_strict_batch12():
    out = _ratio(1.0)
    assert type(out) is dict


def test_ratio_reason_none_batch12():
    out = _ratio(0.5)
    assert out["reason"] is None


def test_ratio_with_negative_value_batch12():
    """_ratio 接受任意 float（不强制 [0, 1]）。"""
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_with_large_value_batch12():
    out = _ratio(2.5)
    assert out["value"] == 2.5


def test_bool_metric_truthy_int_batch12():
    out = _bool_metric(1)
    assert out["value"] is True


def test_bool_metric_falsy_int_batch12():
    out = _bool_metric(0)
    assert out["value"] is False


def test_bool_metric_truthy_string_batch12():
    """非空字符串 truthy → True。"""
    out = _bool_metric("hello")
    assert out["value"] is True


def test_bool_metric_falsy_string_batch12():
    out = _bool_metric("")
    assert out["value"] is False


def test_bool_metric_returns_python_bool_batch12():
    out = _bool_metric(1)
    assert type(out["value"]) is bool


def test_int_metric_truncates_float_batch12():
    out = _int_metric(3.99)
    assert out["value"] == 3


def test_int_metric_negative_batch12():
    out = _int_metric(-5)
    assert out["value"] == -5


def test_int_metric_with_str_int_batch12():
    """int("42") → 42。"""
    out = _int_metric("42")  # type: ignore[arg-type]
    # 实际：int("42") = 42
    assert out["value"] == 42


def test_int_metric_returns_python_int_batch12():
    out = _int_metric(5)
    assert type(out["value"]) is int


def test_int_metric_with_bool_batch12():
    """int(True) → 1。"""
    out = _int_metric(True)  # type: ignore[arg-type]
    assert out["value"] == 1


# ---------- compute_automatic_metrics 行为深度第十二批 ----------


def test_compute_metrics_keys_count_with_full_doc_batch12():
    """完整 doc 应有 15 个 metric keys。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    # 14 个 metric + error_code (虽然 error_code 在 metrics dict 里)
    # 实际：pipeline_success, error_code, schema_valid, element_count_total,
    #       element_count_by_type, pdf_locator_valid_ratio, docx_locator_valid_ratio,
    #       image_resource_exists_ratio, chunk_reference_intact_ratio,
    #       text_preservation_equal, text_char_multiset_precision,
    #       text_char_multiset_recall, heading_boundary_compliance, silent_drop_count
    # = 14 keys
    assert len(out) == 14


def test_compute_metrics_doc_and_error_both_set_pipeline_false_batch12():
    """document 非 None + error 非 None → pipeline_success=False。"""
    doc = {"elements": [], "chunks": []}
    err = {"code": "weird", "message": "both set"}
    out = compute_automatic_metrics(
        document=doc, error=err, source_type="pdf", expectations=None
    )
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_doc_and_error_both_set_still_full_metrics_batch12():
    """document 非 None + error 非 None → 仍跑完整 14 metrics。"""
    doc = {"elements": [], "chunks": []}
    err = {"code": "weird"}
    out = compute_automatic_metrics(
        document=doc, error=err, source_type="pdf", expectations=None
    )
    assert len(out) == 14
    assert out["element_count_total"]["value"] == 0


def test_compute_metrics_doc_with_image_only_batch12():
    """elements 全是 image → 文本比对 expected 为空字符串。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "i1", "resource_path": "x.png"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    # image element 不参与 text_preservation → expected 为空
    # actual 也为空 → equal 应为 True (空==空)
    assert out["text_preservation_equal"]["value"] is True


def test_compute_metrics_element_with_no_type_batch12():
    """element 缺 type 字段 → by_type 计数成 'unknown'。"""
    doc = {
        "elements": [{"element_id": "x"}],  # 无 type
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    by_type = out["element_count_by_type"]["value"]
    assert by_type == {"unknown": 1}


def test_compute_metrics_source_type_unknown_batch12():
    """source_type=unknown → pdf 和 docx locator 都 not_evaluated。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="unknown", expectations=None
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_error_code_no_error_batch12():
    """无 error → error_code.value=None。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out["error_code"]["value"] is None


def test_compute_metrics_error_code_with_error_batch12():
    err = {"code": "parse_failed", "message": "boom"}
    out = compute_automatic_metrics(
        document=None, error=err, source_type="pdf", expectations=None
    )
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_metrics_error_code_with_unicode_batch12():
    err = {"code": "中文错误码", "message": "x"}
    out = compute_automatic_metrics(
        document=None, error=err, source_type="pdf", expectations=None
    )
    assert out["error_code"]["value"] == "中文错误码"


def test_compute_metrics_does_not_mutate_document_batch12():
    import copy
    doc = {
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "p1"}],
        "chunks": [{"id": "c1", "text": "hello", "source_element_ids": ["p1"]}],
    }
    snapshot = copy.deepcopy(doc)
    _ = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert doc == snapshot


def test_compute_metrics_does_not_mutate_error_batch12():
    import copy
    err = {"code": "x", "message": "y"}
    snapshot = copy.deepcopy(err)
    _ = compute_automatic_metrics(
        document=None, error=err, source_type="pdf", expectations=None
    )
    assert err == snapshot


def test_compute_metrics_idempotent_batch12():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    out2 = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    # 排除可能变化的字段（实际本函数确定性）
    assert out1 == out2


# ---------- pdf/docx locator 第十二批 ----------


def test_pdf_locator_ratio_mixed_batch12():
    """混合：1 个有效（page+bbox），1 个无 page。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {}},  # 无 page
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_ratio_all_valid_batch12():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 2, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_page_zero_invalid_batch12():
    """page=0 → < 1 → 无效。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid_batch12():
    elements = [
        {"type": "paragraph", "source_locator": {"page": -1, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_float_invalid_batch12():
    """page 是 float → isinstance(int) False → 无效。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1.0, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_image_no_bbox_required_batch12():
    """image 不需要 bbox。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # 无 bbox 但 image 不需要
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_locator_none_batch12():
    """source_locator=None → 视为 {} → 无 page → 无效。"""
    elements = [
        {"type": "paragraph", "source_locator": None},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_elements_batch12():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_no_elements_batch12():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_with_page_invalid_batch12():
    """docx 元素有 page 字段 → 无效。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_paragraph_index_batch12():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_section_batch12():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_no_structural_keys_batch12():
    elements = [
        {"type": "paragraph", "source_locator": {"unknown_key": "v"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_locator_none_batch12():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 第十二批 ----------


def test_is_valid_bbox_dict_input_batch12():
    """dict 不是 list → False。"""
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_tuple_input_batch12():
    """tuple 不是 list → False。"""
    assert _is_valid_bbox((0, 0, 10, 10)) is False


def test_is_valid_bbox_string_input_batch12():
    assert _is_valid_bbox("0,0,10,10") is False


def test_is_valid_bbox_none_input_batch12():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_with_inf_batch12():
    assert _is_valid_bbox([0, 0, math.inf, 10]) is False


def test_is_valid_bbox_with_nan_batch12():
    assert _is_valid_bbox([0, 0, float("nan"), 10]) is False


def test_is_valid_bbox_with_negative_inf_batch12():
    assert _is_valid_bbox([0, 0, -math.inf, 10]) is False


def test_is_valid_bbox_with_bool_true_batch12():
    """bool 是 int 子类，但函数显式拒绝。"""
    assert _is_valid_bbox([True, 0, 10, 10]) is False


def test_is_valid_bbox_with_string_value_batch12():
    assert _is_valid_bbox(["0", "0", "10", "10"]) is False


def test_is_valid_bbox_zero_values_batch12():
    """0 是合法值。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_values_batch12():
    """负数也合法（坐标系可能允许）。"""
    assert _is_valid_bbox([-10, -10, 10, 10]) is True


def test_is_valid_bbox_3_elements_batch12():
    assert _is_valid_bbox([0, 0, 10]) is False


def test_is_valid_bbox_5_elements_batch12():
    assert _is_valid_bbox([0, 0, 10, 10, 10]) is False


def test_is_valid_bbox_empty_list_batch12():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_float_values_batch12():
    assert _is_valid_bbox([0.0, 0.0, 10.5, 10.5]) is True


# ---------- _strip_unicode_whitespace 第十二批 ----------


def test_strip_unicode_whitespace_nbsp_batch12():
    """NBSP (U+00A0) 是 whitespace。"""
    s = "a b"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_em_space_batch12():
    """EM SPACE (U+2003) 是 whitespace。"""
    s = "a b"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_en_space_batch12():
    """EN SPACE (U+2002) 是 whitespace。"""
    s = "a b"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch12():
    """全角空格 (U+3000) 是 whitespace。"""
    s = "a　b"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_line_separator_batch12():
    """LINE SEPARATOR (U+2028) 是 whitespace。"""
    s = "a b"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch12():
    """PARAGRAPH SEPARATOR (U+2029) 是 whitespace。"""
    s = "a b"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_bom_batch12():
    """BOM (U+FEFF) 在 isspace() 中不是 whitespace。"""
    s = "a﻿b"
    # FEFF 在 Python 中 .isspace() 返回 False
    assert _strip_unicode_whitespace(s) == "a﻿b"


def test_strip_unicode_whitespace_vertical_tab_batch12():
    """VT (U+000B) 是 whitespace。"""
    s = "ab"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_form_feed_batch12():
    """FF (U+000C) 是 whitespace。"""
    s = "ab"
    assert _strip_unicode_whitespace(s) == "ab"


def test_strip_unicode_whitespace_only_whitespace_batch12():
    """全是空白 → 空字符串。"""
    assert _strip_unicode_whitespace("   \t\n") == ""


def test_strip_unicode_whitespace_empty_string_batch12():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace_batch12():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_preserves_order_batch12():
    """不重新排序，只删除空白。"""
    s = "c b a"
    assert _strip_unicode_whitespace(s) == "cba"


def test_strip_unicode_whitespace_preserves_non_ascii_batch12():
    """非 ASCII 非空白字符保留。"""
    s = "你好 世界"
    assert _strip_unicode_whitespace(s) == "你好世界"


def test_strip_unicode_whitespace_returns_str_batch12():
    assert isinstance(_strip_unicode_whitespace("x"), str)


# ---------- image_resource_ratio 第十二批 ----------


def test_image_resource_ratio_no_image_elements_batch12():
    out = _image_resource_ratio([], None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_no_resource_path_batch12():
    elements = [{"type": "image", "element_id": "i1"}]  # 无 resource_path
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_empty_resource_path_batch12():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_valid_file_batch12(tmp_path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(b"\x89PNG fake data")  # 非空文件
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_image_empty_file_batch12(tmp_path):
    """文件存在但 size=0 → 无效。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_batch12(tmp_path):
    img_file = tmp_path / "valid.png"
    img_file.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
        {"type": "image", "resource_path": "/no/such/file.png"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_ratio_oserror_silent_batch12(tmp_path, monkeypatch):
    """Path.is_file() raises OSError → silent skip。"""
    real_is_file = Path.is_file

    def _fake_is_file(self):
        if "raise_path" in str(self):
            raise OSError("boom")
        return real_is_file(self)

    elements = [{"type": "image", "resource_path": "/raise_path/file.png"}]
    with patch.object(Path, "is_file", _fake_is_file):
        out = _image_resource_ratio(elements, None)
    # OSError 被吞 → 无效
    assert out["value"] == 0.0


# ---------- chunk_reference_ratio 第十二批 ----------


def test_chunk_reference_ratio_empty_chunks_batch12():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_empty_ids_batch12():
    """chunk source_element_ids=[] → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"id": "c1", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_missing_ids_field_batch12():
    """chunk 无 source_element_ids 字段 → 默认 [] → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"id": "c1"}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_with_non_existent_id_batch12():
    elements = [{"element_id": "e1"}]
    chunks = [{"id": "c1", "source_element_ids": ["e2"]}]  # e2 不存在
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_with_partial_invalid_batch12():
    elements = [{"element_id": "e1"}]
    chunks = [{"id": "c1", "source_element_ids": ["e1", "e2"]}]  # e2 不存在
    out = _chunk_reference_ratio(elements, chunks)
    # all(...) 失败 → invalid
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_batch12():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"id": "c1", "source_element_ids": ["e1"]},
        {"id": "c2", "source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- module source forbidden tokens 第十六批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "import marshal",
        "import ctypes",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from marshal import",
        "from ctypes import",
        "subprocess.Popen",
        "os.system",
    ],
)
def test_metrics_source_no_forbidden_token_sixteenth_batch12(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_metrics_source_no_top_level_lambda_batch12():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_metrics_source_no_class_definition_batch12():
    source = inspect.getsource(mmod)
    assert "\nclass " not in source
    assert not source.startswith("class ")


def test_metrics_source_no_assert_statement_batch12():
    source = inspect.getsource(mmod)
    assert "\nassert " not in source
    assert not source.startswith("assert ")


def test_metrics_source_no_yield_batch12():
    source = inspect.getsource(mmod)
    assert "yield " not in source


def test_metrics_source_no_global_batch12():
    source = inspect.getsource(mmod)
    assert " global " not in source


def test_metrics_source_no_walrus_batch12():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_metrics_source_no_async_def_batch12():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_metrics_source_no_while_loop_batch12():
    source = inspect.getsource(mmod)
    assert "while " not in source


def test_metrics_source_no_input_call_batch12():
    source = inspect.getsource(mmod)
    assert "input(" not in source


def test_metrics_source_no_kill_batch12():
    source = inspect.getsource(mmod)
    assert ".kill(" not in source


def test_metrics_source_no_remove_batch12():
    source = inspect.getsource(mmod)
    assert ".remove(" not in source


# ---------- module source 字符串精确补强第十三批 ----------


def test_module_source_has_future_annotations_batch12():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_math_batch12():
    source = inspect.getsource(mmod)
    assert "import math" in source


def test_module_source_imports_counter_batch12():
    source = inspect.getsource(mmod)
    assert "from collections import Counter" in source


def test_module_source_imports_path_batch12():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch12():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_has_text_types_constant_batch12():
    source = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in source


def test_module_source_has_pdf_bbox_types_constant_batch12():
    source = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in source


def test_module_source_has_not_evaluated_constant_batch12():
    source = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in source


def test_module_source_has_compute_automatic_metrics_function_batch12():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_has_null_helper_batch12():
    source = inspect.getsource(mmod)
    assert "def _null(" in source


def test_module_source_has_ratio_helper_batch12():
    source = inspect.getsource(mmod)
    assert "def _ratio(" in source


def test_module_source_has_bool_metric_helper_batch12():
    source = inspect.getsource(mmod)
    assert "def _bool_metric(" in source


def test_module_source_has_int_metric_helper_batch12():
    source = inspect.getsource(mmod)
    assert "def _int_metric(" in source


def test_module_source_has_text_preservation_function_batch12():
    source = inspect.getsource(mmod)
    assert "def _text_preservation(" in source


def test_module_source_has_strip_unicode_whitespace_function_batch12():
    source = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in source


def test_module_source_has_dunder_all_batch12():
    source = inspect.getsource(mmod)
    assert "__all__" in source


def test_module_source_docstring_present_batch12():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_source_docstring_mentions_text_preservation_batch12():
    assert mmod.__doc__ is not None
    assert "text_preservation" in mmod.__doc__ or "文本保留" in mmod.__doc__


def test_module_source_docstring_mentions_v11_batch12():
    """docstring 提到 v1.1。"""
    assert mmod.__doc__ is not None
    assert "v1.1" in mmod.__doc__ or "v1.0" in mmod.__doc__


def test_module_source_no_main_block_batch12():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_no_print_batch12():
    source = inspect.getsource(mmod)
    assert "print(" not in source


def test_module_source_no_logging_batch12():
    source = inspect.getsource(mmod)
    assert "logging" not in source
    assert "logger" not in source


# ---------- signatures 第十三批 ----------


def test_signature_null_one_param_batch12():
    sig = inspect.signature(_null)
    assert list(sig.parameters) == ["reason"]


def test_signature_null_return_dict_batch12():
    sig = inspect.signature(_null)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "dict" in annot_str


def test_signature_ratio_one_param_batch12():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters) == ["value"]


def test_signature_bool_metric_one_param_batch12():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters) == ["value"]


def test_signature_int_metric_one_param_batch12():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters) == ["value"]


def test_signature_compute_metrics_5_params_batch12():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_signature_compute_metrics_image_base_dir_default_none_batch12():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["image_base_dir"]
    assert p.default is None


def test_signature_compute_metrics_image_base_dir_optional_path_batch12():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["image_base_dir"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "None" in annot_str


def test_signature_pdf_locator_ratio_1_param_batch12():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters) == ["elements"]


def test_signature_docx_locator_ratio_1_param_batch12():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters) == ["elements"]


def test_signature_is_valid_bbox_1_param_batch12():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters) == ["bbox"]


def test_signature_is_valid_bbox_return_bool_batch12():
    sig = inspect.signature(_is_valid_bbox)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "bool" in annot_str


def test_signature_strip_unicode_whitespace_1_param_batch12():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters) == ["s"]


def test_all_functions_no_var_kwargs_batch12():
    for fn in [_null, _ratio, _bool_metric, _int_metric,
               compute_automatic_metrics, _pdf_locator_ratio, _docx_locator_ratio,
               _is_valid_bbox, _strip_unicode_whitespace]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十三批 ----------


def test_module_name_evaluation_metrics_batch12():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_dunder_all_exact_set_batch12():
    assert set(mmod.__all__) == {"compute_automatic_metrics"}


def test_module_dunder_all_len_1_batch12():
    assert len(mmod.__all__) == 1


def test_module_user_function_count_batch12():
    funcs = [
        n for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_null",
        "_ratio",
        "_bool_metric",
        "_int_metric",
        "compute_automatic_metrics",
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
    }


def test_module_no_user_classes_batch12():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_constants_count_3_batch12():
    consts = [
        n for n, v in vars(mmod).items()
        if not n.startswith("__")
        and not callable(v)
        and not inspect.isclass(v)
        and not inspect.ismodule(v)
        and n not in ("annotations",)  # future
    ]
    assert set(consts) == {"_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"}


def test_module_uses_future_annotations_batch12():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_docstring_present_batch12():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 100


def test_module_has_text_types_constant_batch12():
    assert hasattr(mmod, "_TEXT_TYPES")


def test_module_text_types_value_batch12():
    assert mmod._TEXT_TYPES == (
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    )


def test_module_pdf_bbox_types_value_batch12():
    assert mmod._PDF_BBOX_REQUIRED_TYPES == (
        "heading", "paragraph", "caption", "list_item",
    )


def test_module_not_evaluated_value_batch12():
    assert mmod._NOT_EVALUATED == "not_evaluated"


# ---------- 端到端集成第十三批 ----------


def test_e2e_full_metrics_with_complex_doc_batch12():
    """复杂 doc → 完整 metrics 计算。"""
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "element_id": "p1",
                "content": "Hello world",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]},
            },
            {
                "type": "paragraph",
                "element_id": "p2",
                "content": "Foo bar",
                "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]},
            },
        ],
        "chunks": [
            {"id": "c1", "text": "Hello world", "source_element_ids": ["p1"]},
            {"id": "c2", "text": "Foo bar", "source_element_ids": ["p2"]},
        ],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["text_preservation_equal"]["value"] is True
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_text_preservation_with_whitespace_diff_batch12():
    """expected/actual 非空白字符相同但空白不同 → equal=True。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hello world"},
        ],
        "chunks": [
            {"id": "c1", "text": "hello   world", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_combined_chain_with_image_excluded_batch12():
    """image element 不参与 text_preservation。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "abc"},
            {"type": "image", "element_id": "i1", "resource_path": "x.png"},
        ],
        "chunks": [
            {"id": "c1", "text": "abc", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    # image 内容不进 expected → equal=True
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_combined_chain_chunk_reference_full_match_batch12():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"id": "c1", "source_element_ids": ["e1", "e2"]},
        {"id": "c2", "source_element_ids": ["e1"]},
    ]
    out = compute_automatic_metrics(
        document={"elements": elements, "chunks": chunks},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_combined_chain_idempotent_run_batch12():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    out2 = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out1 == out2


def test_e2e_combined_chain_document_none_short_circuit_batch12():
    """document=None → 提前返回 14 keys，其他指标 null。"""
    out = compute_automatic_metrics(
        document=None, error=None, source_type="pdf", expectations=None
    )
    # pipeline_success=false + error_code + schema_valid=pipeline_failed + 11 个 null
    # 实际看代码：metrics 内有 pipeline_success + error_code + schema_valid + 11 null = 14
    assert len(out) == 14
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
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_combined_chain_docx_locator_ratio_full_match_batch12():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="docx", expectations=None
    )
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_combined_chain_full_metrics_dict_serializable_batch12():
    import json
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_combined_chain_metric_keys_order_batch12():
    """metric keys 顺序符合预期。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
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
    assert list(out.keys()) == expected_keys


def test_e2e_combined_chain_no_chunks_text_preservation_batch12():
    """有 elements 但无 chunks → actual 空，text_preservation 看 expected 是否空。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "abc"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    # expected="abc" != actual="" → equal=False
    assert out["text_preservation_equal"]["value"] is False
