"""evaluation/metrics.py 第二百五十一轮 edges 测试（Round 807）。

补强 edges93 未触及的角度（第一百七十一批）。

新角度：
- 成功路径 14 键全序锁定（pipeline_success → silent_drop_count）
- error 与 document 并存：pipeline_success False 但下游指标照算
  （早退只看 document is None）
- source_type "PDF" 大写 → 双 null（not_pdf_document /
  not_docx_document 并存）
- page=True 布尔漏过（bool 是 int 子类；bbox 检查显式拒 bool，
  page 检查没有）→ footer 元素 1.0
- table 无 bbox 仍合法（_PDF_BBOX_REQUIRED_TYPES 不含 table/
  header/footer）
- 元素缺 type 键 → by_type "unknown" 桶
- content None + chunk text None → equal True +
  empty_expected_and_actual
- 双 heading 一命中 → 0.5
- image 无 resource_path → 0.0（非 null）
- forbidden tokens 第二百七十七批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics as cam


def _doc(elements, chunks=()):
    return {"elements": elements, "chunks": list(chunks)}


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _ch(text, ids):
    return {"text": text, "source_element_ids": ids}


def _cam(document, error=None, st="pdf", exp=None):
    with patch.object(sv, "document_passes_schema", lambda d: True):
        return cam(document, error, st, exp)


# ---------- 14 键全序 ----------

def test_full_key_order_batch55():
    m = _cam(_doc([_el("e1", "paragraph")], [_ch("A", ["e1"])]))
    assert list(m.keys()) == [
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count"]
    assert len(m) == 14


# ---------- error 与 document 并存 ----------

def test_error_and_document_both_present_batch55():
    m = _cam(_doc([_el("e1", "paragraph")], [_ch("A", ["e1"])]),
             error={"code": "PARSE_FAIL"})
    assert m["pipeline_success"] == {"value": False, "reason": None}
    assert m["error_code"] == {"value": "PARSE_FAIL", "reason": None}
    assert m["schema_valid"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}


# ---------- source_type 大写 ----------

def test_uppercase_source_type_dual_null_batch55():
    m = _cam(_doc([_el("e1", "paragraph")]), st="PDF")
    assert m["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}
    assert m["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


# ---------- page=True 布尔漏过 ----------

def test_page_bool_true_leaks_through_batch55():
    els = [_el("f1", "footer", source_locator={"page": True})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- table 无 bbox ----------

def test_table_without_bbox_valid_batch55():
    els = [_el("t1", "table", source_locator={"page": 1})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 缺 type 键 ----------

def test_missing_type_unknown_bucket_batch55():
    m = _cam(_doc([{"element_id": "x", "content": "A"}]))
    assert m["element_count_by_type"] == {"value": {"unknown": 1},
                                          "reason": None}


# ---------- content/text None ----------

def test_none_content_and_text_empty_batch55():
    els = [_el("e1", "paragraph", content=None)]
    chs = [{"text": None, "source_element_ids": ["e1"]}]
    m = _cam(_doc(els, chs))
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}
    assert m["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected_and_actual"}


# ---------- heading 2:1 ----------

def test_two_headings_one_matched_half_batch55():
    els = [_el("h1", "heading"), _el("h2", "heading"),
           _el("p1", "paragraph")]
    chs = [_ch("A", ["h1"]), _ch("A", ["p1"])]
    m = _cam(_doc(els, chs))
    assert m["heading_boundary_compliance"] == {"value": 0.5,
                                               "reason": None}


# ---------- image 无 resource_path ----------

def test_image_without_resource_path_zero_batch55():
    m = _cam(_doc([_el("i1", "image", content=None)]))
    assert m["image_resource_exists_ratio"] == {"value": 0.0,
                                                "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert ("pipeline_success = error is None and document is not None"
            in src)
    assert 't = e.get("type", "unknown")' in src
    assert "_PDF_BBOX_REQUIRED_TYPES = (\"heading\", \"paragraph\", \"caption\", \"list_item\")" in src


# ---------- forbidden tokens 第二百七十七批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch55():
    assert "open(" not in _src()
