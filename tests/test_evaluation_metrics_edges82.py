"""evaluation/metrics.py 第二百零一轮 edges 测试（Round 723）。

补强 edges80/edges81 未触及的角度（第八十八批）。

新角度：
- _is_valid_bbox 直测矩阵（bool 拒 / inf 拒 / nan 拒 / tuple 拒 / len3 拒 / 负数过（无符号约束））
- page=True 被接受（bool ⊂ int 且 True>=1，现状记录）；page=1.0 float 拒
- 非 bbox-required 类型（table/header/footer/image）仅凭 page 即有效
- docx 七个结构键逐一直测 + locator {} 拒 + page in loc 拒
- compute source_type "txt" → 双 locator 均 not_pdf/not_docx
- error={"code": None} / error={} → pipeline_success False 但 error_code None
- image rp 为 None/""/缺键 → 各自无效；rp 相对路径 + base_dir 拼接候选命中
- chunk ids=[] / 缺键 / None → 无效但参与分母
- _strip_unicode_whitespace 直测（NBSP/全角空格/U+2028 删；\\x00 保留；全空白 → ""）
- heading 仅首个 id 匹配（第二个位置不算）→ 0.5
- _silent_drop_count 直测（期望含未出现类型算 drop / actual>exp 不负 / 空子节点 reason）
- 四个构造器直测（_bool_metric(0)/("")、_ratio("0.5")、_int_metric(-3)）
- _TEXT_TYPES 是死常量（源码仅出现 1 次，未被引用）
- AST（九个子函数 If/For/Return/Continue/Break/Try/BoolOp + compute If4·For2·Try1·ImportFrom1）
- forbidden tokens 第一百九十三批
"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _TEXT_TYPES,
    _PDF_BBOX_REQUIRED_TYPES,
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


# ---------- _is_valid_bbox 直测 ----------

@pytest.mark.parametrize("bbox,expected", [
    ([0, 0, 1, 1], True),
    ([1, 2, 3, 4], True),
    ([-5, -5, 0, 0], True),          # 无符号约束
    ([0, 0, -5, 1], True),
    ([0, 0, 1, True], False),        # bool 拒
    ([True, 0, 1, 1], False),
    ([0, 0, float("inf"), 1], False),
    ([0, 0, float("nan"), 1], False),
    ((0, 0, 1, 1), False),           # tuple 非 list
    ([0, 0, 1], False),              # len 3
    ([0, 0, 1, 1, 1], False),        # len 5
    ("0001", False),
    (None, False),
])
def test_is_valid_bbox_matrix_batch53(bbox, expected):
    assert _is_valid_bbox(bbox) is expected


# ---------- page 类型边界 ----------

def test_pdf_page_bool_accepted_batch53():
    # bool ⊂ int 且 True >= 1 → 现状：被接受
    out = _pdf_locator_ratio([{"type": "paragraph",
                               "source_locator": {"page": True,
                                                  "bbox": [0, 0, 1, 1]}}])
    assert out == {"value": 1.0, "reason": None}


def test_pdf_page_float_rejected_batch53():
    out = _pdf_locator_ratio([{"type": "image",
                               "source_locator": {"page": 1.0}}])
    assert out == {"value": 0.0, "reason": None}


def test_pdf_page_zero_and_string_rejected_batch53():
    els = [{"type": "image", "source_locator": {"page": 0}},
           {"type": "image", "source_locator": {"page": "1"}}]
    assert _pdf_locator_ratio(els) == {"value": 0.0, "reason": None}


def test_pdf_mixed_fraction_batch53():
    els = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {"page": 2}},   # 缺 bbox 拒
        {"type": "table", "source_locator": {"page": 3}},       # table 不需要 bbox
    ]
    assert _pdf_locator_ratio(els)["value"] == pytest.approx(2 / 3)


def test_pdf_bbox_free_types_membership_batch53():
    assert "list_item" in _PDF_BBOX_REQUIRED_TYPES
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_locator_none_defaults_invalid_batch53():
    out = _pdf_locator_ratio([{"type": "image", "source_locator": None}])
    assert out == {"value": 0.0, "reason": None}


# ---------- docx 结构键 ----------

_DOCX_KEYS = ("section", "paragraph_index", "run_index", "table_index",
              "row_index", "col_index", "relationship_id")


@pytest.mark.parametrize("key", _DOCX_KEYS)
def test_docx_each_structural_key_valid_batch53(key):
    out = _docx_locator_ratio([{"source_locator": {key: 1}}])
    assert out == {"value": 1.0, "reason": None}


def test_docx_empty_locator_invalid_batch53():
    assert _docx_locator_ratio([{"source_locator": {}}]) == \
        {"value": 0.0, "reason": None}


def test_docx_page_key_rejects_even_with_structural_batch53():
    out = _docx_locator_ratio([{"source_locator": {"page": 1, "section": 0}}])
    assert out == {"value": 0.0, "reason": None}


def test_docx_extra_keys_plus_structural_valid_batch53():
    out = _docx_locator_ratio([{"source_locator": {"section": 0, "zzz": "x"}}])
    assert out == {"value": 1.0, "reason": None}


# ---------- source_type 非 pdf/docx ----------

def test_compute_source_type_txt_batch53(monkeypatch):
    import evaluation.schema_validation as sv_mod
    monkeypatch.setattr(sv_mod, "document_passes_schema", lambda d: True)
    out = compute_automatic_metrics({"elements": [], "chunks": []}, None, "txt", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


# ---------- error 变体 ----------

def test_error_code_none_but_failure_batch53():
    out = compute_automatic_metrics({"elements": [], "chunks": []},
                                    {"code": None, "message": "m"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] is None


def test_error_empty_dict_still_failure_batch53():
    out = compute_automatic_metrics({"elements": [], "chunks": []}, {}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] is None


# ---------- image_resource ----------

def test_image_falsy_resource_paths_invalid_batch53(tmp_path):
    els = [{"type": "image", "resource_path": None},
           {"type": "image", "resource_path": ""},
           {"type": "image"}]
    out = _image_resource_ratio(els, tmp_path)
    assert out == {"value": 0.0, "reason": None}


def test_image_base_dir_candidate_rescues_batch53(tmp_path):
    (tmp_path / "img.png").write_bytes(b"x")
    els = [{"type": "image", "resource_path": "subdir/img.png"}]
    out = _image_resource_ratio(els, tmp_path)
    assert out == {"value": 1.0, "reason": None}


def test_image_absolute_path_direct_batch53(tmp_path):
    f = tmp_path / "a.png"
    f.write_bytes(b"x")
    els = [{"type": "image", "resource_path": str(f)}]
    assert _image_resource_ratio(els, None) == {"value": 1.0, "reason": None}


def test_image_half_valid_fraction_batch53(tmp_path):
    (tmp_path / "ok.png").write_bytes(b"x")
    els = [{"type": "image", "resource_path": "subdir/ghost.png"},  # 两候选都无
           {"type": "image", "resource_path": "ok.png"}]
    assert _image_resource_ratio(els, tmp_path)["value"] == pytest.approx(0.5)


# ---------- chunk_reference ----------

def test_chunk_ref_empty_ids_and_missing_key_batch53():
    els = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []},
              {},
              {"source_element_ids": None}]
    out = _chunk_reference_ratio(els, chunks)
    assert out == {"value": 0.0, "reason": None}


def test_chunk_ref_duplicate_ids_all_present_batch53():
    els = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e1", "e1"]}]
    assert _chunk_reference_ratio(els, chunks) == {"value": 1.0, "reason": None}


def test_chunk_ref_partial_invalid_batch53():
    els = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]},
              {"source_element_ids": ["e1", "ghost"]}]
    assert _chunk_reference_ratio(els, chunks)["value"] == pytest.approx(0.5)


# ---------- 空白剥离 ----------

def test_strip_unicode_whitespace_variants_batch53():
    assert _strip_unicode_whitespace("a 　b c") == "abc"
    assert _strip_unicode_whitespace(" 　 \t\n ") == ""
    assert _strip_unicode_whitespace("\x00") == "\x00"  # 控制字符非空白，保留
    assert _strip_unicode_whitespace("") == ""


def test_text_preservation_unicode_ws_equal_batch53():
    out = _text_preservation([{"type": "paragraph", "content": "a　b"}],
                             [{"text": "ab"}])
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0


# ---------- heading 首位匹配 ----------

def test_heading_second_position_not_matched_batch53():
    els = [{"type": "heading", "element_id": "h1"},
           {"type": "heading", "element_id": "h2"}]
    chunks = [{"source_element_ids": ["h1"]},
              {"source_element_ids": ["x", "h2"]}]  # h2 在第二位不算
    assert _heading_boundary_ratio(els, chunks)["value"] == pytest.approx(0.5)


# ---------- silent_drop 直测 ----------

def test_silent_drop_expected_type_absent_batch53():
    out = _silent_drop_count({"paragraph": 1},
                             {"element_count_by_type": {"paragraph": 1, "table": 3}})
    assert out == {"value": 3, "reason": None}


def test_silent_drop_actual_exceeds_no_negative_batch53():
    out = _silent_drop_count({"paragraph": 5},
                             {"element_count_by_type": {"paragraph": 2}})
    assert out == {"value": 0, "reason": None}


def test_silent_drop_empty_subnode_reason_batch53():
    assert _silent_drop_count({"paragraph": 1},
                              {"element_count_by_type": {}})["reason"] == \
        "no_expectations_element_count"
    assert _silent_drop_count({"paragraph": 1}, {"other": 1})["reason"] == \
        "no_expectations_element_count"


# ---------- 构造器直测 ----------

def test_constructors_coercion_batch53():
    assert _bool_metric(0) == {"value": False, "reason": None}
    assert _bool_metric("") == {"value": False, "reason": None}
    assert _bool_metric(2) == {"value": True, "reason": None}
    assert _ratio("0.5") == {"value": 0.5, "reason": None}
    assert _int_metric(-3) == {"value": -3, "reason": None}
    assert _null("r") == {"value": None, "reason": "r"}


def test_text_types_constant_batch53():
    assert _TEXT_TYPES == ("heading", "paragraph", "list_item", "table",
                           "caption", "header", "footer")


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_dead_constant_batch53():
    # _TEXT_TYPES 定义后从未被引用（文本比对用 type != "image"）
    assert _src().count("_TEXT_TYPES") == 1
    assert _src().count("_PDF_BBOX_REQUIRED_TYPES") == 2


def test_source_or_default_counts_batch53():
    src = _src()
    assert src.count('_null(') == 16
    assert src.count('_ratio(') == 18
    assert src.count('or ""') == 2
    assert src.count("or {}") == 3
    assert src.count("or []") == 2


def test_source_math_usage_batch53():
    src = _src()
    assert "import math" in src
    assert "math.isfinite(v)" in src
    assert "if isinstance(v, bool):" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(metrics_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


@pytest.mark.parametrize("name,expect", [
    ("_pdf_locator_ratio", (4, 1, 2, 2, 0, 0, 2)),
    ("_docx_locator_ratio", (3, 1, 2, 2, 0, 0, 2)),
    ("_is_valid_bbox", (4, 1, 5, 0, 0, 0, 1)),
    ("_image_resource_ratio", (5, 2, 2, 2, 1, 1, 1)),
    ("_chunk_reference_ratio", (2, 1, 2, 0, 0, 0, 2)),
    ("_text_preservation", (3, 0, 1, 0, 0, 0, 3)),
    ("_heading_boundary_ratio", (2, 1, 2, 0, 0, 1, 1)),
    ("_silent_drop_count", (3, 1, 3, 0, 0, 0, 1)),
    ("_strip_unicode_whitespace", (0, 0, 1, 0, 0, 0, 0)),
])
def test_ast_subfunction_structures_batch53(name, expect):
    c = _counts(_func(name))
    got = (c["If"], c["For"], c["Return"], c["Continue"], c["Try"],
           c["ListComp"], c["BoolOp"])
    assert got == expect, name


def test_ast_compute_structure_batch53():
    c = _counts(_func("compute_automatic_metrics"))
    assert (c["If"], c["For"], c["Return"], c["Try"], c["ImportFrom"],
            c["ExceptHandler"]) == (4, 2, 2, 1, 1, 1)


# ---------- forbidden tokens 第一百九十三批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch53():
    assert "open(" not in _src()
