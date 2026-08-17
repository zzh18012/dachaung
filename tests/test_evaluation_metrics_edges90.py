"""evaluation/metrics.py 第二百二十三轮 edges 测试（Round 779）。

补强 edges86-89 未触及的角度（第一百四十三批）。

新角度：
- document 与 error 同时给出 → pipeline_success False 但其余指标
  照算（None-return 只看 document；error_code 同时有值）——
  "晚失败"混合态，现状记录
- bbox 传 tuple (0,0,1,1) → isinstance list 拒 → 0.0
  （纯 int 列表 [0,0,100,200] 有效 1.0 对照）
- None-id 互认家族：element 无 element_id → 集合含 None；
  chunk source_element_ids [None] → all() 通过 → ratio 1.0；
  heading 无 element_id + chunk 首 id None → matched → 1.0
  （None == None 在集合成员判定里成立，schema 之外未防）
- expectations 计数传 bool True → bool 是 int 子类参与比较，
  drops = True - 0 = 1（直接调用绕过 schema 的 integer 约束）
- page 传 True → isinstance(True, int) 通过且 >= 1 → 有效
  （与 R765 的 bbox bool 元素拒对照：page 与 bbox 的 bool 防线不对称）
- docx locator 未知额外键不拒（{"zzz":1,"section":0} 无 page/bbox
  + 有结构键 → 1.0；只锁 page/bbox 黑名单与结构键白名单）
- forbidden tokens 第二百四十九批
"""

from __future__ import annotations

import inspect

from evaluation.metrics import compute_automatic_metrics


def _run(document, error=None, src="pdf", exp=None):
    return compute_automatic_metrics(document, error, src, exp, None)


# ---------- 混合态：document + error 同给 ----------

def test_document_with_error_mixed_state_batch54():
    out = _run({"elements": [{"type": "table"}], "chunks": []},
               error={"code": "late_failure"})
    assert out["pipeline_success"] == {"value": False, "reason": None}
    assert out["error_code"] == {"value": "late_failure",
                                 "reason": None}
    assert out["element_count_total"] == {"value": 1, "reason": None}


# ---------- bbox tuple ----------

def test_bbox_tuple_rejected_batch54():
    out = _run({"elements": [{"type": "paragraph",
                              "source_locator": {
                                  "page": 1,
                                  "bbox": (0, 0, 1, 1)}}]})
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0,
                                              "reason": None}


def test_bbox_int_list_valid_batch54():
    out = _run({"elements": [{"type": "paragraph",
                              "source_locator": {
                                  "page": 1,
                                  "bbox": [0, 0, 100, 200]}}]})
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0,
                                              "reason": None}


# ---------- None-id 互认 ----------

def test_none_id_chunk_reference_batch54():
    out = _run({"elements": [{}],
                "chunks": [{"text": "a",
                            "source_element_ids": [None]}]})
    assert out["chunk_reference_intact_ratio"] == {"value": 1.0,
                                                   "reason": None}


def test_none_id_heading_matched_batch54():
    out = _run({"elements": [{"type": "heading"}],
                "chunks": [{"text": "a",
                            "source_element_ids": [None]}]})
    assert out["heading_boundary_compliance"] == {"value": 1.0,
                                                  "reason": None}


# ---------- bool 计数 ----------

def test_bool_expectation_count_batch54():
    out = _run({"elements": []},
               exp={"element_count_by_type": {"paragraph": True}})
    assert out["silent_drop_count"] == {"value": 1, "reason": None}


# ---------- page True ----------

def test_page_bool_true_valid_batch54():
    out = _run({"elements": [{"type": "table",
                              "source_locator": {"page": True}}]})
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0,
                                              "reason": None}


# ---------- docx 额外键 ----------

def test_docx_extra_locator_keys_allowed_batch54():
    out = _run({"elements": [{"type": "paragraph",
                              "source_locator": {"zzz": 1,
                                                 "section": 0}}]},
               src="docx")
    assert out["docx_locator_valid_ratio"] == {"value": 1.0,
                                               "reason": None}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_guard_lines_batch54():
    src = _src()
    assert 'error is None and document is not None' in src
    assert "if not isinstance(bbox, list) or len(bbox) != 4:" in src
    assert "if not isinstance(page, int) or page < 1:" in src
    assert 'if not any(k in loc for k in structural_keys):' in src


# ---------- forbidden tokens 第二百四十九批 ----------

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
