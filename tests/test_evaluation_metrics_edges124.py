"""evaluation/metrics.py 第四百六十八轮 edges 测试（Round 1024）。

补强 edges123 未触及的角度（第四百批，probe 实证）。

新角度（schema_valid 委托 document.schema.json 严格性）：
- 手工 chunk 带 char_count → document.schema.json 的
  chunk def additionalProperties false 拒之（"char_count
  was unexpected" + metadata required）→ schema_valid
  False；同款 chunk 换成 metadata 后 → True——metrics
  不自定标准，完全委托（该拒收此前无测试锁过）
- doc + error 双非空（edges39 用空 doc 锁过 14 键）：
  带内容的 doc 下 pipeline_success False + error_code
  照记 E_PARTIAL + schema_valid False + element_count
  1 + text_equal True 全同屏
- forbidden tokens 第四百九十四批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _doc(chunks):
    return {
        "elements": [
            {"type": "paragraph", "element_id": "p",
             "content": "hi", "parent_id": None,
             "confidence": 0.9, "metadata": {},
             "source_locator": {"page": 1,
                                "bbox": [0, 0, 1, 1]}}],
        "chunks": chunks,
        "source_type": "pdf", "document_id": "x",
        "schema_version": "0.1.0", "source_path": "a.pdf",
        "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1", "relations": [],
        "warnings": [], "errors": [], "metadata": {}}


# ---------- char_count 拒 / metadata 收 ----------

def test_chunk_char_count_rejected_schema_valid_batch222():
    bad = _doc([{"chunk_id": "c", "text": "hi",
                 "source_element_ids": ["p"],
                 "char_count": 2}])
    m_bad = compute_automatic_metrics(bad, None, "pdf", None)
    assert m_bad["schema_valid"] == {"value": False,
                                     "reason": None}

    good = _doc([{"chunk_id": "c", "text": "hi",
                  "source_element_ids": ["p"], "metadata": {}}])
    m_good = compute_automatic_metrics(good, None, "pdf", None)
    assert m_good["schema_valid"] == {"value": True,
                                      "reason": None}
    assert m_good["text_preservation_equal"]["value"] is True


# ---------- doc + error 双非空（带内容） ----------

def test_doc_error_both_full_metrics_batch222():
    doc = _doc([{"chunk_id": "c", "text": "hi",
                 "source_element_ids": ["p"],
                 "char_count": 2}])
    m = compute_automatic_metrics(doc, {"code": "E_PARTIAL"},
                                  "pdf", None)
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert m["error_code"] == {"value": "E_PARTIAL",
                               "reason": None}
    assert m["schema_valid"]["value"] is False
    assert m["element_count_total"]["value"] == 1
    assert m["text_preservation_equal"]["value"] is True


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch222():
    src = _src()
    assert ("pipeline_success = error is None"
            " and document is not None") in src
    assert ("from evaluation.schema_validation import"
            " document_passes_schema") in src
    assert "ok = document_passes_schema(document)" in src


# ---------- forbidden tokens 第四百九十四批 ----------

def test_source_no_eval_batch222():
    assert "eval(" not in _src()


def test_source_no_exec_batch222():
    assert "exec(" not in _src()


def test_source_no_compile_batch222():
    assert "compile(" not in _src()


def test_source_no_globals_batch222():
    assert "globals(" not in _src()


def test_source_no_locals_batch222():
    assert "locals(" not in _src()


def test_source_no_os_system_batch222():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch222():
    assert "subprocess" not in _src()


def test_source_no_popen_batch222():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch222():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch222():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch222():
    assert "socket" not in _src()


def test_source_no_requests_batch222():
    assert "requests" not in _src()


def test_source_no_urllib_batch222():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch222():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch222():
    assert "yield" not in _src()


def test_source_no_async_await_batch222():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch222():
    assert "open(" not in _src()
