"""evaluation/metrics.py 第四十九轮 edges 测试（Round 463）。

补强 edges46 未触及的角度。
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


# ---------- _null 深度第二十批 ----------


def test_null_value_type_is_none_object_batch20():
    """_null 的 value 永远是 None（NoneType）。"""
    assert _null("x")["value"] is None
    assert type(_null("x")["value"]) is type(None)


def test_null_reason_type_is_str_batch20():
    assert isinstance(_null("x")["reason"], str)


def test_null_does_not_accept_extra_args_batch20():
    """_null 仅接 1 个参数。"""
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert len(params) == 1


# ---------- _ratio 深度第二十批 ----------


def test_ratio_with_huge_value_batch20():
    """_ratio 不限制上界。"""
    r = _ratio(1000.0)
    assert r["value"] == 1000.0


def test_ratio_with_nan_batch20():
    """NaN 也被接受（float 强转）。"""
    r = _ratio(float("nan"))
    assert math.isnan(r["value"])


def test_ratio_with_inf_batch20():
    r = _ratio(float("inf"))
    assert r["value"] == float("inf")


# ---------- _bool_metric 深度第二十批 ----------


def test_bool_metric_none_value_batch20():
    """_bool_metric(None) → False。"""
    assert _bool_metric(None)["value"] is False


def test_bool_metric_dict_value_batch20():
    """_bool_metric({}) → False（空 dict 是 falsy）。"""
    assert _bool_metric({})["value"] is False


def test_bool_metric_non_empty_dict_value_batch20():
    assert _bool_metric({"x": 1})["value"] is True


def test_bool_metric_list_value_batch20():
    assert _bool_metric([0])["value"] is True  # 非空 list


# ---------- _int_metric 深度第二十批 ----------


def test_int_metric_with_float_negative_batch20():
    assert _int_metric(-3.7)["value"] == -3  # int(-3.7) = -3


def test_int_metric_with_string_int_batch20():
    """_int_metric 接受数字 str 时 int() 成功（Python 行为）。"""
    # int("5") == 5
    assert _int_metric("5")["value"] == 5


def test_int_metric_with_invalid_string_batch20():
    """非数字 str 抛 ValueError。"""
    with pytest.raises(ValueError):
        _int_metric("hello")


def test_int_metric_with_none_batch20():
    with pytest.raises(TypeError):
        _int_metric(None)


# ---------- _TEXT_TYPES 第二批 ----------


def test_text_types_unique_values_batch20():
    """无重复。"""
    assert len(set(_TEXT_TYPES)) == len(_TEXT_TYPES)


def test_text_types_specific_values_batch20():
    assert _TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_pdf_bbox_required_specific_values_batch20():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


# ---------- _strip_unicode_whitespace 第二批 ----------


def test_strip_unicode_with_only_one_char_batch20():
    assert _strip_unicode_whitespace("a") == "a"


def test_strip_unicode_preserves_digits_batch20():
    assert _strip_unicode_whitespace("123") == "123"


def test_strip_unicode_preserves_letters_batch20():
    assert _strip_unicode_whitespace("abcXYZ") == "abcXYZ"


def test_strip_unicode_with_tab_batch20():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_with_newline_batch20():
    assert _strip_unicode_whitespace("a\nb") == "ab"


# ---------- compute_automatic_metrics 深度第二十批 ----------


def test_compute_metrics_source_type_docx_no_pdf_locator_batch20():
    """source_type=docx 时 pdf_locator_valid_ratio reason='not_pdf_document'。"""
    doc = {
        "document_id": "d",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_source_type_pdf_no_docx_locator_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_no_chunks_chunk_ref_null_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "x"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_metrics_no_heading_no_boundary_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "x"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["reason"] == "no_heading_elements"


def test_compute_metrics_no_elements_image_ratio_null_batch20():
    """无 elements → image_resource_exists_ratio reason='no_image_elements'。"""
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_metrics_pdf_locator_all_invalid_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "source_locator": {"page": 0}},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_compute_metrics_element_count_by_type_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "heading"},
            {"element_id": "e2", "type": "heading"},
            {"element_id": "e3", "type": "paragraph"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"heading": 2, "paragraph": 1}


def test_compute_metrics_element_count_by_type_with_unknown_type_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1"},  # 缺 type 字段
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1}


def test_compute_metrics_silent_drop_with_expectations_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "heading", "content": "x"}],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"heading": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 4


# ---------- _pdf_locator_ratio 第二批 ----------


def test_pdf_locator_ratio_no_locator_key_batch20():
    elements = [{"type": "heading"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_empty_dict_locator_batch20():
    elements = [{"type": "heading", "source_locator": {}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_no_bbox_batch20():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 第二批 ----------


def test_docx_locator_ratio_empty_batch20():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_no_text_elements_batch20():
    elements = [{"type": "image", "source_locator": {"section": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0  # image 也算


def test_docx_locator_ratio_mixed_batch20():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 0}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
        {"type": "paragraph", "source_locator": {}},  # invalid
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1 / 3


# ---------- _is_valid_bbox 第二批 ----------


def test_is_valid_bbox_with_decimal_string_batch20():
    assert _is_valid_bbox(["0.5", "1.0", "1.5", "2.0"]) is False


def test_is_valid_bbox_with_more_than_4_items_batch20():
    assert _is_valid_bbox([0, 0, 1, 1, 1]) is False


def test_is_valid_bbox_with_dict_batch20():
    assert _is_valid_bbox({"a": 1}) is False


def test_is_valid_bbox_with_set_batch20():
    assert _is_valid_bbox({0, 0, 1, 1}) is False


# ---------- _image_resource_ratio 第二批 ----------


def test_image_resource_ratio_with_path_object_batch20(tmp_path):
    """resource_path 是 Path（不是 str）应能被 Path(rp) 接受。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": img}]  # Path object
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_with_no_image_type_batch20(tmp_path):
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_count_in_denominator_batch20(tmp_path):
    """分母是 image 数量（不是总 element 数量）。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": "x.png"},
        {"type": "image", "resource_path": "nope.png"},  # 不存在
        {"type": "paragraph"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    # 2 个 image，1 个 valid
    assert out["value"] == 0.5


# ---------- _chunk_reference_ratio 第二批 ----------


def test_chunk_reference_ratio_first_valid_second_invalid_batch20():
    elements = [{"element_id": "a"}, {"element_id": "b"}]
    chunks = [
        {"source_element_ids": ["a"]},  # valid
        {"source_element_ids": ["x"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_all_chunks_have_empty_ids_batch20():
    elements = [{"element_id": "a"}]
    chunks = [
        {"source_element_ids": []},
        {"source_element_ids": []},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_duplicates_in_one_chunk_batch20():
    elements = [{"element_id": "a"}, {"element_id": "b"}]
    chunks = [{"source_element_ids": ["a", "a", "b"]}]  # 重复 a
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0  # all in elem_ids


# ---------- _text_preservation 第二批 ----------


def test_text_preservation_image_content_excluded_batch20():
    """image 类型的 content 不参与 expected_sequence。"""
    elements = [
        {"type": "image", "content": "IMAGE_TEXT"},
        {"type": "paragraph", "content": "hello"},
    ]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_table_content_included_batch20():
    """table 是 _TEXT_TYPES，参与。"""
    elements = [{"type": "table", "content": "table_data"}]
    chunks = [{"text": "table_data"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_caption_content_included_batch20():
    elements = [{"type": "caption", "content": "cap"}]
    chunks = [{"text": "cap"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_header_content_included_batch20():
    elements = [{"type": "header", "content": "H"}]
    chunks = [{"text": "H"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_footer_content_included_batch20():
    elements = [{"type": "footer", "content": "F"}]
    chunks = [{"text": "F"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_list_item_content_included_batch20():
    elements = [{"type": "list_item", "content": "item"}]
    chunks = [{"text": "item"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


# ---------- _heading_boundary_ratio 第二批 ----------


def test_heading_boundary_ratio_2_headings_2_chunks_batch20():
    elements = [
        {"element_id": "h1", "type": "heading"},
        {"element_id": "h2", "type": "heading"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_only_one_heading_matched_batch20():
    elements = [
        {"element_id": "h1", "type": "heading"},
        {"element_id": "h2", "type": "heading"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},  # 只有 h1 是某 chunk 首元素
        {"source_element_ids": ["x"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_chunks_without_ids_batch20():
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = [{"source_element_ids": []}, {"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _silent_drop_count 第二批 ----------


def test_silent_drop_count_no_element_count_key_batch20():
    """expectations 不含 element_count_by_type → null。"""
    out = _silent_drop_count({}, {"other_key": 1})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_more_batch20():
    by_type = {"heading": 10}
    exp = {"element_count_by_type": {"heading": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0


def test_silent_drop_count_with_no_text_type_in_by_type_batch20():
    """expected 含 table 但 by_type 没记录 → drop=expected。"""
    by_type = {"heading": 1}
    exp = {"element_count_by_type": {"heading": 1, "table": 3}}
    out = _silent_drop_count(by_type, exp)
    # heading: max(0, 1-1)=0; table: max(0, 3-0)=3
    assert out["value"] == 3


# ---------- module source forbidden tokens 第三十五批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch20(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch20():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src


def test_module_source_no_socket_import_batch20():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch20():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_threading_import_batch20():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch20():
    src = inspect.getsource(mmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch20():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch20():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_os_import_batch20():
    src = inspect.getsource(mmod)
    assert "import os" not in src


def test_module_source_no_tempfile_import_batch20():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_call_batch20():
    src = inspect.getsource(mmod)
    assert ".unlink(" not in src


def test_module_source_no_path_write_text_batch20():
    src = inspect.getsource(mmod)
    assert ".write_text(" not in src


def test_module_source_no_sys_exit_batch20():
    src = inspect.getsource(mmod)
    assert "sys.exit" not in src


def test_module_source_no_re_compile_batch20():
    src = inspect.getsource(mmod)
    assert "re.compile" not in src


def test_module_source_no_pandas_import_batch20():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch20():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十批 ----------


def test_module_source_has_future_annotations_batch20():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_math_import_batch20():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_counter_import_batch20():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_pathlib_path_import_batch20():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch20():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_text_types_constant_batch20():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading"' in src


def test_module_source_has_pdf_bbox_required_constant_batch20():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading"' in src


def test_module_source_has_compute_automatic_metrics_function_batch20():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_silent_drop_count_function_batch20():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_has_text_preservation_docstring_batch20():
    src = inspect.getsource(mmod)
    assert "v1.1" in src or "口径 D" in src


def test_module_source_has_all_single_entry_batch20():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- signatures 第三十批 ----------


def test_signature_compute_metrics_batch20():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_pdf_locator_ratio_batch20():
    sig = inspect.signature(_pdf_locator_ratio)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["elements"]


def test_signature_docx_locator_ratio_batch20():
    sig = inspect.signature(_docx_locator_ratio)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["elements"]


def test_signature_image_resource_ratio_batch20():
    sig = inspect.signature(_image_resource_ratio)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["elements", "image_base_dir"]


def test_signature_chunk_reference_ratio_batch20():
    sig = inspect.signature(_chunk_reference_ratio)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["elements", "chunks"]


def test_signature_heading_boundary_ratio_batch20():
    sig = inspect.signature(_heading_boundary_ratio)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["elements", "chunks"]


def test_signature_strip_unicode_whitespace_batch20():
    sig = inspect.signature(_strip_unicode_whitespace)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["s"]


def test_signature_text_preservation_batch20():
    sig = inspect.signature(_text_preservation)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["elements", "chunks"]


# ---------- module 合理性第三十批 ----------


def test_module_has_all_attribute_batch20():
    assert hasattr(mmod, "__all__")


def test_module_all_only_contains_one_entry_batch20():
    assert len(mmod.__all__) == 1


def test_module_does_not_import_app_pipeline_batch20():
    src = inspect.getsource(mmod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_cli_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src


def test_module_schema_validation_import_is_lazy_batch20():
    """document_passes_schema 在 compute_automatic_metrics 内部 lazy import。"""
    src = inspect.getsource(mmod)
    top = src[: src.find("def compute_automatic_metrics")]
    assert "document_passes_schema" not in top


def test_module_no_main_block_batch20():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src


def test_module_constants_not_in_all_batch20():
    for k in ("_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"):
        assert k not in mmod.__all__


def test_module_text_types_count_exactly_7_batch20():
    assert len(_TEXT_TYPES) == 7


def test_module_pdf_bbox_required_count_exactly_4_batch20():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


# ---------- 端到端集成 第三十批 ----------


def test_e2e_compute_metrics_full_pdf_doc_batch20():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "heading", "content": "Title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"element_id": "e2", "type": "paragraph", "content": "Body",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "Title Body", "source_element_ids": ["e1", "e2"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    # schema_valid 这里依赖 document_passes_schema（可能因 fixture 简化而 False）
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_pipeline_failed_returns_12_nulls_batch20():
    """失败时 14 keys - pipeline_success(非null) - error_code(非null) = 12 null。"""
    out = compute_automatic_metrics(None, {"code": "E"}, "pdf", None)
    nulls = [k for k, v in out.items() if v["value"] is None]
    assert len(nulls) == 12


def test_e2e_text_preservation_word_split_batch20():
    """chunker 词内硬切应判 equal。"""
    elements = [{"type": "paragraph", "content": "Hello"}]
    chunks = [{"text": "Hel "}, {"text": "lo"}]
    out = compute_automatic_metrics(
        {"document_id": "d", "source_type": "pdf", "elements": elements, "chunks": chunks},
        None, "pdf", None,
    )
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_compute_metrics_no_mutation_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "heading", "content": "x",
                       "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    import copy as _copy
    snapshot = _copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == snapshot


def test_e2e_image_only_text_preservation_passes_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "image", "resource_path": "/x.png"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_silent_drop_count_with_expectations_batch20():
    doc = {
        "document_id": "d",
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "heading", "content": "T",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [{"text": "T", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"heading": 5, "paragraph": 10}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 14


def test_e2e_docx_doc_locator_valid_batch20():
    doc = {
        "document_id": "d",
        "source_type": "docx",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "Hi",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "Hi", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["value"] is None
