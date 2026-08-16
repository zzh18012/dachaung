"""evaluation/metrics.py 第二百零三轮 edges 测试（Round 737）。

补强 edges82/edges83 未触及的角度（第一百零二批）。

新角度：
- schema_check_exception 分支：monkeypatch document_passes_schema 抛错 →
  value False + reason "schema_check_exception:RuntimeError"
- 真 schema_valid True：完整合法 DOCX 文档（schema_version 0.1.0 /
  parent_id / confidence / metadata 等全字段）经真校验器通过；
  同文档 docx_locator 1.0 / equal True
- 真 schema_valid False：elements 非法时真校验器拒绝（reason None）
- 未守卫路径：error 传真值字符串 → TypeError（"boom"["code"]）；
  expectations 传真值字符串 → AttributeError
- error={"code": ""} → value ""（空串不是 None）
- error 真值 + document 存在 → pipeline_success False
- None-id 怪癖：elements 与 chunk 引用同为 None 时 1.0；
  None 元素对字符串引用 0.0
- type None 元素参与文本保留（!= "image" 即计入 expected）
- _PDF_BBOX_REQUIRED_TYPES 精确四元组
- 构造器布尔强转：_ratio(True)→1.0 / _int_metric(True)→1 /
  _bool_metric("x")→True
- forbidden tokens 第二百零七批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import (
    _PDF_BBOX_REQUIRED_TYPES,
    _bool_metric,
    _chunk_reference_ratio,
    _int_metric,
    _ratio,
    _text_preservation,
    compute_automatic_metrics,
)


def _valid_docx() -> dict:
    return {
        "schema_version": "0.1.0", "document_id": "d2",
        "source_path": "y.docx", "source_type": "docx",
        "source_hash": "b" * 64, "parser_name": "python-docx",
        "parser_version": "1.2.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "Hello", "parent_id": None,
                      "source_locator": {"paragraph_index": 0},
                      "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "Hello",
                    "source_element_ids": ["e1"], "metadata": {}}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }


# ---------- schema_valid 三态 ----------

def test_schema_check_exception_branch_batch54(monkeypatch):
    def boom(doc):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(sv, "document_passes_schema", boom)
    out = compute_automatic_metrics({"elements": [], "chunks": []},
                                    None, "pdf", None)
    assert out["schema_valid"] == {
        "value": False, "reason": "schema_check_exception:RuntimeError"}


def test_schema_valid_true_with_real_validator_batch54():
    out = compute_automatic_metrics(_valid_docx(), None, "docx", None)
    assert out["schema_valid"] == {"value": True, "reason": None}
    assert out["docx_locator_valid_ratio"] == {"value": 1.0, "reason": None}
    assert out["text_preservation_equal"] == {"value": True, "reason": None}


def test_schema_valid_false_with_real_validator_batch54():
    # schema_version 违反 const：形状合法（后续指标可正常计算）但整体非法
    bad = _valid_docx()
    bad["schema_version"] = "9.9"
    out = compute_automatic_metrics(bad, None, "docx", None)
    assert out["schema_valid"] == {"value": False, "reason": None}
    assert out["element_count_total"] == {"value": 1, "reason": None}


# ---------- 未守卫路径现状记录 ----------

def test_error_truthy_string_raises_typeerror_batch54():
    with pytest.raises(TypeError):
        compute_automatic_metrics({"elements": [], "chunks": []},
                                  "boom", "pdf", None)


def test_expectations_truthy_string_raises_attributeerror_batch54():
    with pytest.raises(AttributeError):
        compute_automatic_metrics({"elements": [], "chunks": []},
                                  None, "pdf", "x")


# ---------- error_code 语义 ----------

def test_error_empty_string_code_value_batch54():
    out = compute_automatic_metrics(None, {"code": ""}, "pdf", None)
    assert out["error_code"] == {"value": "", "reason": None}


def test_error_truthy_plus_document_pipeline_fails_batch54():
    out = compute_automatic_metrics({"elements": [], "chunks": []},
                                    {"code": "x"}, "pdf", None)
    assert out["pipeline_success"] == {"value": False, "reason": None}


# ---------- None-id 怪癖 ----------

def test_chunk_ref_none_ids_mutual_valid_batch54():
    # elements 的 element_id 缺省为 None → None 也在 id 集里
    out = _chunk_reference_ratio([{"element_id": None}],
                                 [{"source_element_ids": [None]}])
    assert out == {"value": 1.0, "reason": None}


def test_chunk_ref_none_element_vs_string_ref_batch54():
    out = _chunk_reference_ratio([{"element_id": None}],
                                 [{"source_element_ids": ["a"]}])
    assert out == {"value": 0.0, "reason": None}


# ---------- type None 参与文本保留 ----------

def test_type_none_element_counts_as_text_batch54():
    # 判定是 type != "image"：None 也参与 expected
    tp = _text_preservation([{"type": None, "content": "x"}],
                            [{"text": "x"}])
    assert tp["equal"] == {"value": True, "reason": None}


# ---------- 常量与构造器 ----------

def test_pdf_bbox_required_types_exact_batch54():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph",
                                        "caption", "list_item")


def test_constructor_bool_coercions_batch54():
    assert _ratio(True) == {"value": 1.0, "reason": None}
    assert _int_metric(True) == {"value": 1, "reason": None}
    assert _bool_metric("x") == {"value": True, "reason": None}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_lazy_import_schema_validation_batch54():
    src = _src()
    assert "from evaluation.schema_validation import document_passes_schema" \
        in src
    # 模块级不导入 schema_validation（避免循环依赖）
    assert "import evaluation.schema_validation" not in src.split(
        "def compute_automatic_metrics")[0]


# ---------- forbidden tokens 第二百零七批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
