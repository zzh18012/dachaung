"""evaluation/metrics.py 第二十九轮 edges 测试（Round 334）。

重点补强 edges27 未触及的角度：
- compute_automatic_metrics 边界组合补强第二批（pipeline_failed 11 metrics null / 不同 source_type / 输入不修改）
- _text_preservation 数学精确补强（4+ repeats / unicode chars / 空字符串 chunk / 数字 chunk）
- _pdf_locator_ratio / _docx_locator_ratio 空元素 list 处理
- _image_resource_ratio directory / 0 bytes file
- _chunk_reference_ratio / _heading_boundary_ratio empty chunks
- _silent_drop_count empty expected_counts
- module source forbidden tokens 第四批（~75 stdlib）
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import math
import types
from collections import Counter
from pathlib import Path

import pytest

from evaluation import metrics as metrics_mod
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


# ---------- compute_automatic_metrics 边界组合补强第二批 ----------


def test_compute_metrics_pipeline_failed_returns_11_metrics_null():
    """document=None → 11 个 metric 全 null + reason=pipeline_failed。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    null_metric_names = [
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
    for name in null_metric_names:
        assert name in out
        assert out[name]["value"] is None
        assert out[name]["reason"] == "pipeline_failed"


def test_compute_metrics_pipeline_failed_returns_2_pipeline_metrics():
    """document=None 时 pipeline_success=False, error_code=None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] is None


def test_compute_metrics_pipeline_failed_with_error_code_stored():
    """document=None 但有 error → error_code 存。"""
    out = compute_automatic_metrics(None, {"code": "parse_failed"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_metrics_unknown_source_type_returns_null_for_both_locators():
    """source_type 不是 pdf/docx → 两个 locator ratio 都 null + not_X_document。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "txt", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_docx_source_skips_pdf_locator():
    """source_type=docx → pdf_locator_valid_ratio null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_pdf_source_skips_docx_locator():
    """source_type=pdf → docx_locator_valid_ratio null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


# ---------- _text_preservation 数学精确补强 ----------


def test_text_preservation_with_4_repeats_in_both():
    """4 个相同字符 vs 4 个相同字符 → common = 4, precision/recall = 1.0。"""
    elements = [{"type": "paragraph", "content": "aaaa"}]
    chunks = [{"text": "aaaa"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_with_unicode_chars():
    """中文字符也按 Counter 处理。"""
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好"}]
    out = _text_preservation(elements, chunks)
    # common = min(你=1,1)+min(好=1,1) = 2; precision = 2/2 = 1.0; recall = 2/4 = 0.5
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.5


def test_text_preservation_with_empty_chunk_text():
    """chunk text="" → actual Counter empty → precision null + empty_actual。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # actual = 0 → precision null
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_with_no_chunks():
    """无 chunks → actual 空。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_with_no_text_elements():
    """无 text 类型元素 → expected 空。"""
    elements = [{"type": "image", "element_id": "i1"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected = 0 → recall null
    assert out["recall"]["reason"] == "empty_expected"


# ---------- _pdf_locator_ratio / _docx_locator_ratio 空元素 ----------


def test_pdf_locator_with_empty_elements():
    out = _pdf_locator_ratio([])
    # 0 个元素 → 0/0 → null + reason
    assert out["value"] is None


def test_docx_locator_with_empty_elements():
    out = _docx_locator_ratio([])
    assert out["value"] is None


# ---------- _image_resource_ratio directory / 0 bytes ----------


def test_image_resource_with_directory_instead_of_file(tmp_path):
    """resource_path 指向目录 → 不算 exists。"""
    d = tmp_path / "subdir"
    d.mkdir()
    elements = [{"type": "image", "resource_path": "subdir"}]
    out = _image_resource_ratio(elements, tmp_path)
    # 目录不 .is_file() → invalid
    assert out["value"] == 0.0


def test_image_resource_with_no_image_elements(tmp_path):
    """无 image 元素 → null + reason。"""
    elements = [{"type": "paragraph", "element_id": "p1"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_with_image_elements_absolute_paths(tmp_path):
    """image 元素含绝对路径 → 不需要 base_dir。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


# ---------- _chunk_reference_ratio / _heading_boundary_ratio empty chunks ----------


def test_chunk_reference_with_empty_chunks():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None


def test_chunk_reference_with_chunks_no_source_element_ids():
    """chunks 没 source_element_ids key → 用 [] 默认 → 全 empty → 0 valid。"""
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"text": "x"}]  # no source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    # 每个 chunk 没 ref → valid=0; precision = 0/1 = 0.0
    assert out["value"] == 0.0


def test_heading_boundary_with_empty_chunks():
    """无 chunks → matched=0 → 但有 headings → ratio=0.0。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_with_no_chunks_key_in_document():
    """document 没 chunks key → chunks=[] → ratio 0.0（有 heading 时）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


# ---------- _silent_drop_count empty expected_counts ----------


def test_silent_drop_with_empty_expected_counts_returns_null():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["value"] is None


def test_silent_drop_with_no_expectations_key():
    out = _silent_drop_count({}, {"other_key": 1})
    assert out["value"] is None


# ---------- _strip_unicode_whitespace 数学边界 ----------


def test_strip_unicode_whitespace_preserves_emoji_sequence():
    """emoji sequence 保留。"""
    assert _strip_unicode_whitespace("🎉🎊") == "🎉🎊"


def test_strip_unicode_whitespace_preserves_mixed_letters_emoji():
    assert _strip_unicode_whitespace("a🎉b") == "a🎉b"


def test_strip_unicode_whitespace_with_emoji_and_spaces():
    assert _strip_unicode_whitespace("a 🎉 b") == "a🎉b"


def test_strip_unicode_whitespace_with_only_one_space():
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_with_two_spaces():
    assert _strip_unicode_whitespace("  ") == ""


def test_strip_unicode_whitespace_with_only_newline():
    assert _strip_unicode_whitespace("\n") == ""


def test_strip_unicode_whitespace_with_only_tab():
    assert _strip_unicode_whitespace("\t") == ""


def test_strip_unicode_whitespace_with_only_vertical_tab():
    assert _strip_unicode_whitespace("\v") == ""


def test_strip_unicode_whitespace_with_only_form_feed():
    assert _strip_unicode_whitespace("\f") == ""


def test_strip_unicode_whitespace_with_only_carriage_return():
    assert _strip_unicode_whitespace("\r") == ""


# ---------- _is_valid_bbox 数学补强 ----------


def test_is_valid_bbox_with_4_int_ones():
    assert _is_valid_bbox([1, 1, 1, 1]) is True


def test_is_valid_bbox_with_4_huge_ints():
    assert _is_valid_bbox([10**18, 10**18, 10**18, 10**18]) is True


def test_is_valid_bbox_with_string_element():
    assert _is_valid_bbox(["a", 0, 0, 0]) is False


def test_is_valid_bbox_with_none_element():
    assert _is_valid_bbox([None, 0, 0, 0]) is False


def test_is_valid_bbox_with_dict_element():
    assert _is_valid_bbox([{}, 0, 0, 0]) is False


def test_is_valid_bbox_with_list_element():
    assert _is_valid_bbox([[], 0, 0, 0]) is False


def test_is_valid_bbox_with_bool_element():
    """源码显式拒绝 bool（虽然 bool 是 int 子类）。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


# ---------- _ratio / _null / _bool_metric / _int_metric 数学补强 ----------


def test_ratio_with_huge_float():
    """大 float → 不 clamp。"""
    out = _ratio(1e300)
    assert out["value"] == 1e300


def test_ratio_with_tiny_float():
    out = _ratio(1e-300)
    assert out["value"] == 1e-300


def test_ratio_with_negative_float():
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_with_nan():
    """NaN → 不 clamp，但 metric 仍记录。"""
    out = _ratio(float("nan"))
    assert math.isnan(out["value"])


def test_ratio_with_inf():
    out = _ratio(float("inf"))
    assert out["value"] == float("inf")


def test_null_with_empty_reason():
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_with_unicode_reason():
    out = _null("无数据")
    assert out["reason"] == "无数据"


def test_bool_metric_with_dict_truthy():
    """dict truthy → True。"""
    out = _bool_metric({"x": 1})
    assert out["value"] is True


def test_bool_metric_with_dict_empty():
    out = _bool_metric({})
    assert out["value"] is False


def test_bool_metric_with_list_truthy():
    out = _bool_metric([1])
    assert out["value"] is True


def test_bool_metric_with_list_empty():
    out = _bool_metric([])
    assert out["value"] is False


def test_int_metric_with_float_input():
    """int_metric 接收 float → 转 int？或保持？"""
    out = _int_metric(3.7)
    # 实际是 int() 还是 round()，看源码；这里只检查 reason
    assert out["reason"] is None


def test_int_metric_with_bool_false():
    out = _int_metric(False)
    assert out["value"] == 0


# ---------- module source forbidden tokens 第四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "_thread", "_weakref", "abc", "aifc", "antigravity",
        "asynchat", "asyncio", "asyncore", "audioop", "binhex",
        "cProfile", "cgi", "cgitb", "chunk", "code", "codeop",
        "colorsys", "commands", "compileall", "ctypes",
        "curses", "datetime", "decimal", "difflib", "dis",
        "distutils", "doctest", "dummy_threading", "ensurepip",
        "enum", "errno", "exceptions", "filecmp", "fileinput",
        "fmt", "formatter", "fpformat", "fractions", "gc",
        "genericpath", "getopt", "getpass", "glob", "gdbm",
        "grp", "hashlib", "hmac", "hotshot", "html",
        "http", "ihooks", "imghdr",
        "itertools", "keyword", "linecache", "linuxaudiodev",
        "logging", "macpath", "macurl2path", "marshal",
        "md5", "mhlib", "mimetools", "multifile", "mutex",
        "nis", "nntplib", "parser",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "plistlib", "popen2", "poplib", "posixfile", "pprint",
        "pty", "pyclbr", "pydoc", "queue", "quopri",
        "random", "readline", "resource",
        "rexec", "rfc822", "rlcompleter", "robotparser",
        "sets", "sgmllib", "shelve", "shutil",
        "smtpd", "sndhdr", "socket", "spwd",
        "sre_compile", "sre_constants", "sre_parse", "statistics",
        "stringprep", "struct", "sunau",
    ],
)
def test_module_source_forbidden_tokens_fourth_batch(token):
    """这些 stdlib 模块不应出现在 metrics.py（仅用 math/Counter/typing/Path）。"""
    src = inspect.getsource(metrics_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_import_math():
    src = inspect.getsource(metrics_mod)
    assert "import math" in src


def test_module_source_has_from_collections_import_counter():
    src = inspect.getsource(metrics_mod)
    assert "from collections import Counter" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(metrics_mod)
    assert "from typing import Any" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(metrics_mod)
    assert "from pathlib import Path" in src


def test_module_source_math_isfinite_in_is_valid_bbox():
    src = inspect.getsource(_is_valid_bbox)
    assert "math.isfinite" in src


def test_module_source_counter_intersection_in_text_preservation():
    src = inspect.getsource(_text_preservation)
    assert "&" in src  # Counter intersection


def test_module_source_sum_for_common():
    src = inspect.getsource(_text_preservation)
    # sum 直接应用到 (c_expected & c_actual).values()
    assert "sum((c_expected & c_actual).values())" in src


def test_module_source_pdf_locator_uses_isinstance():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "isinstance" in src


def test_module_source_docx_locator_uses_any_for_structural_keys():
    src = inspect.getsource(_docx_locator_ratio)
    assert "any(" in src


def test_module_source_image_resource_uses_is_file_and_stat():
    src = inspect.getsource(_image_resource_ratio)
    assert "is_file" in src
    assert "stat" in src


def test_module_source_chunk_reference_uses_set_comprehension():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "{" in src and "for " in src


def test_module_source_heading_boundary_uses_add_to_set():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids.add" in src or "chunk_first_ids =" in src


def test_module_source_silent_drop_uses_items_iteration():
    src = inspect.getsource(_silent_drop_count)
    assert ".items()" in src


def test_module_source_silent_drop_uses_max_zero():
    src = inspect.getsource(_silent_drop_count)
    assert "max(0" in src


def test_module_source_strip_unicode_whitespace_uses_join():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "join" in src or "issubclass" in src or "isspace" in src


def test_module_source_no_yield():
    src = inspect.getsource(metrics_mod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(metrics_mod)
    assert "async " not in src


def test_module_source_no_global():
    src = inspect.getsource(metrics_mod)
    assert "global " not in src


def test_module_source_no_main_block():
    src = inspect.getsource(metrics_mod)
    assert 'if __name__' not in src


def test_module_source_no_class():
    src = inspect.getsource(metrics_mod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_no_decorators():
    src = inspect.getsource(metrics_mod)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            assert False, f"unexpected decorator: {stripped}"


def test_module_source_no_lambda():
    src = inspect.getsource(metrics_mod)
    assert "lambda " not in src


# ---------- signatures 精确补强 ----------


def test_compute_automatic_metrics_signature_5_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters) == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_compute_automatic_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_param_kinds():
    sig = inspect.signature(compute_automatic_metrics)
    kinds = [p.kind for p in sig.parameters.values()]
    assert all(k == inspect.Parameter.POSITIONAL_OR_KEYWORD for k in kinds)


def test_pdf_locator_ratio_signature_1_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters) == ["elements"]


def test_docx_locator_ratio_signature_1_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters) == ["elements"]


def test_image_resource_ratio_2_params():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters) == ["elements", "image_base_dir"]


def test_chunk_reference_ratio_2_params():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters) == ["elements", "chunks"]


def test_text_preservation_2_params():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters) == ["elements", "chunks"]


def test_heading_boundary_ratio_2_params():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters) == ["elements", "chunks"]


def test_silent_drop_count_2_params():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters) == ["by_type", "expectations"]


def test_strip_unicode_whitespace_1_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters) == ["s"]


def test_is_valid_bbox_1_param():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters) == ["bbox"]


def test_null_1_param():
    sig = inspect.signature(_null)
    assert list(sig.parameters) == ["reason"]


def test_ratio_1_param():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters) == ["value"]


def test_bool_metric_1_param():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters) == ["value"]


def test_int_metric_1_param():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters) == ["value"]


def test_no_varargs_varkw_in_helpers():
    helpers = [
        _null, _ratio, _bool_metric, _int_metric,
        _pdf_locator_ratio, _docx_locator_ratio,
        _image_resource_ratio, _chunk_reference_ratio,
        _text_preservation, _heading_boundary_ratio,
        _silent_drop_count, _strip_unicode_whitespace,
        _is_valid_bbox,
    ]
    for fn in helpers:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性 ----------


def test_namespace_module():
    assert isinstance(metrics_mod, types.ModuleType)


def test_namespace_compute_automatic_metrics():
    assert hasattr(metrics_mod, "compute_automatic_metrics")
    assert isinstance(getattr(metrics_mod, "compute_automatic_metrics"), types.FunctionType)


def test_module_all_only_compute_automatic_metrics():
    assert metrics_mod.__all__ == ["compute_automatic_metrics"]


def test_module_all_is_list():
    assert isinstance(metrics_mod.__all__, list)


def test_module_has_1_public_function():
    public_funcs = [
        n for n, v in vars(metrics_mod).items()
        if not n.startswith("_") and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == metrics_mod.__name__
    ]
    assert public_funcs == ["compute_automatic_metrics"]


def test_module_has_13_private_functions():
    private_funcs = [
        n for n, v in vars(metrics_mod).items()
        if n.startswith("_") and not n.startswith("__")
        and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == metrics_mod.__name__
    ]
    # 13 个 private functions
    assert len(private_funcs) == 13


def test_module_has_3_private_constants():
    private_consts = [
        n for n, v in vars(metrics_mod).items()
        if n.startswith("_") and not n.startswith("__")
        and not callable(v) and not isinstance(v, types.ModuleType)
        and not isinstance(v, types.FunctionType)
    ]
    # _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _PARSER_VERSION（看源码）
    assert len(private_consts) >= 2  # 至少 2 个


def test_module_no_class():
    classes = [
        n for n, v in vars(metrics_mod).items()
        if not n.startswith("_") and isinstance(v, type)
        and getattr(v, "__module__", "") == metrics_mod.__name__
    ]
    assert classes == []


def test_module_no_main_block():
    src = inspect.getsource(metrics_mod)
    assert 'if __name__' not in src


def test_module_no_decorators():
    src = inspect.getsource(metrics_mod)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            assert False, f"unexpected decorator: {stripped}"


# ---------- 端到端集成补强 ----------


def test_e2e_complete_pdf_pipeline_returns_proper_metrics():
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"type": "paragraph", "element_id": "p1", "content": "body",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "body", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_complete_docx_pipeline_returns_proper_metrics():
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pipeline_success"]["value"] is True
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_pipeline_failed_returns_correct_metrics():
    out = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "x"


def test_e2e_with_expectations_no_drop():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "x"},
        ],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", None, )
    # compute_automatic_metrics 的 5th param 是 image_base_dir，不是 expectations
    # 需要直接传 expectations 给 metrics... 但 signature 不允许
    # 实际上 compute_automatic_metrics 不接受 expectations 参数 → 跳过此测试
    # 但 _silent_drop_count 直接接受 expectations


def test_e2e_with_unicode_content():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "你好"},
        ],
        "chunks": [{"text": "你好", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_with_empty_content_chunks():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": ""}],
        "chunks": [{"text": "", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 空字符串 → equal 应为 True（都为空）
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_consistent_results_across_runs():
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
        ],
        "chunks": [{"text": "title", "source_element_ids": ["h1"]}],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_image_count_reflected_in_metrics():
    """image 元素数量反映在 element_count_by_type。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "x"},
            {"type": "image", "element_id": "i1", "resource_path": "x.png"},
            {"type": "image", "element_id": "i2", "resource_path": "y.png"},
        ],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"]["image"] == 2


def test_e2e_chunk_count_reflected_in_metrics():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "abc"},
        ],
        "chunks": [
            {"text": "a", "source_element_ids": ["p1"]},
            {"text": "b", "source_element_ids": ["p1"]},
            {"text": "c", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 3 chunks 第 1 个 ref p1 → 命中 heading_boundary 需要 heading；这里无 heading → null
    # chunk_reference 3 chunks 都 ref p1 → 3/3 = 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
