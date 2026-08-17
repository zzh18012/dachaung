"""evaluation/metrics.py 第四百四十七轮 edges 测试（Round 1003）。

补强 edges120 未触及的角度（第三百七十九批，probe 实证）。

新角度：
- 中文重排："你好，世界" vs "你好世界，" → equal False、
  P/R 双 1.0（重排只在 equal 可见，多集合不看顺序）
- emoji 参与文本保留 round-trip equal True
- DOCX 复合矩阵（heading+paragraph+image、2 chunk、
  expectations）：heading 1.0 / docx loc 1.0 / image 0.0
  （缺文件仍参与分母）/ silent 1（paragraph 期望 2 实际
  1）/ pdf loc null / chunk ref 1.0 / by_type 三键
- forbidden tokens 第四百七十三批（open 0）
"""

from __future__ import annotations

import inspect

from evaluation.metrics import compute_automatic_metrics


# ---------- 中文重排 ----------

def test_cjk_reorder_equal_false_pr_one_batch201():
    m = compute_automatic_metrics(
        {"elements": [{"type": "paragraph", "content": "你好，世界",
                       "element_id": "e1"}],
         "chunks": [{"text": "你好世界，",
                     "source_element_ids": ["e1"]}]},
        None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {"value": 1.0,
                                                 "reason": None}
    assert m["text_char_multiset_recall"] == {"value": 1.0,
                                              "reason": None}


# ---------- emoji round-trip ----------

def test_emoji_roundtrip_equal_batch201():
    m = compute_automatic_metrics(
        {"elements": [{"type": "paragraph", "content": "a😀b",
                       "element_id": "e1"}],
         "chunks": [{"text": "a😀b",
                     "source_element_ids": ["e1"]}]},
        None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- DOCX 复合矩阵 ----------

def test_docx_composite_matrix_batch201():
    doc = {
        "elements": [
            {"type": "heading", "content": "T", "element_id": "h1",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "content": "body",
             "element_id": "p1",
             "source_locator": {"paragraph_index": 1}},
            {"type": "image", "resource_path": "x.png",
             "element_id": "i1",
             "source_locator": {"paragraph_index": 2}}],
        "chunks": [
            {"text": "T", "source_element_ids": ["h1"]},
            {"text": "body",
             "source_element_ids": ["p1", "i1"]}]}
    m = compute_automatic_metrics(
        doc, None, "docx",
        {"element_count_by_type": {"paragraph": 2, "image": 1}})
    assert m["heading_boundary_compliance"] == {"value": 1.0,
                                                "reason": None}
    assert m["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}
    assert m["image_resource_exists_ratio"] == {"value": 0.0,
                                                "reason": None}
    assert m["silent_drop_count"] == {"value": 1, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": None, "reason": "not_pdf_document"}
    assert m["chunk_reference_intact_ratio"] == {"value": 1.0,
                                                 "reason": None}
    assert m["element_count_total"] == {"value": 3, "reason": None}
    assert m["element_count_by_type"]["value"] == {
        "heading": 1, "paragraph": 1, "image": 1}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_key_lines_batch201():
    src = _src()
    assert "precision = common / sum(c_actual.values())" not in src
    assert "precision_metric = _ratio(common / sum(c_actual.values()))" in src
    assert "recall_metric = _ratio(common / sum(c_expected.values()))" in src
    assert "matched = sum(1 for h in headings if h.get(\"element_id\") in chunk_first_ids)" in src


# ---------- forbidden tokens 第四百七十三批 ----------

def test_source_no_eval_batch201():
    assert "eval(" not in _src()


def test_source_no_exec_batch201():
    assert "exec(" not in _src()


def test_source_no_compile_batch201():
    assert "compile(" not in _src()


def test_source_no_globals_batch201():
    assert "globals(" not in _src()


def test_source_no_locals_batch201():
    assert "locals(" not in _src()


def test_source_no_os_system_batch201():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch201():
    assert "subprocess" not in _src()


def test_source_no_popen_batch201():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch201():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch201():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch201():
    assert "socket" not in _src()


def test_source_no_requests_batch201():
    assert "requests" not in _src()


def test_source_no_urllib_batch201():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch201():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch201():
    assert "yield" not in _src()


def test_source_no_async_await_batch201():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch201():
    assert "open(" not in _src()
