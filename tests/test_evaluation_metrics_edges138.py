"""evaluation/metrics.py 第五百五十九轮 edges 测试（Round 1210）。

补强 edges137 未触及的角度（第五百八十二批，probe 实证）。

新角度（caption 要 bbox / header 不算题 / 混型静默丢）：
- **caption 要 bbox**——_PDF_BBOX_
  REQUIRED_TYPES 含 caption：page-only
  caption 无效，与 header/footer 免
  bbox 成同页对照——[header 免,
  footer 带 bbox, caption 免] → locator
  2/3 = 0.6667（caption 需 bbox 而
  header 不需首锁）
- **footer 单独免 bbox**——page-only
  footer → 1.0（edges102/108 锁过
  header/image 变体，footer 补齐）
- **header 不算题**——header-only 文
  档即便 header 是 chunk 首元素 →
  hbc null no_heading_elements
  （heading 判定严格 type == heading）
- **混型静默丢**——expectations
  {caption: 3, header: 1} vs 实际
  {caption: 1} → (3-1)+(1-0) = 3
- forbidden tokens 第六百八十批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _el(eid, etype, loc):
    return {"element_id": eid, "type": etype, "content": "c",
            "source_locator": loc, "metadata": {}}


def _doc(els, chunks=None):
    return {"source_type": "pdf", "elements": els,
            "chunks": chunks if chunks is not None else []}


# ---------- caption 要 bbox ----------

def test_caption_needs_bbox_batch408():
    els = [
        _el("e0", "header", {"page": 1}),
        _el("e1", "footer", {"page": 1, "bbox": [1, 2, 3, 4]}),
        _el("e2", "caption", {"page": 1}),
    ]
    m = compute_automatic_metrics(_doc(els), None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {
        "value": 0.6666666666666666, "reason": None}


def test_footer_page_only_valid_batch408():
    els = [_el("e0", "footer", {"page": 2})]
    m = compute_automatic_metrics(_doc(els), None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


def test_caption_with_bbox_valid_batch408():
    els = [_el("e0", "caption", {"page": 1,
                                 "bbox": [1.0, 2.0, 3.0, 4.0]})]
    m = compute_automatic_metrics(_doc(els), None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- header 不算题 ----------

def test_header_not_heading_for_hbc_batch408():
    els = [
        _el("e0", "header", {"page": 1}),
        _el("e1", "paragraph", {"page": 1, "bbox": [1, 2, 3, 4]}),
    ]
    chunks = [{"chunk_id": "c0", "text": "c",
               "source_element_ids": ["e0"], "metadata": {}}]
    m = compute_automatic_metrics(_doc(els, chunks), None, "pdf",
                                  None)
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


# ---------- 混型静默丢 ----------

def test_mixed_type_silent_drop_batch408():
    els = [_el("e0", "caption", {"page": 1,
                                 "bbox": [1, 2, 3, 4]})]
    m = compute_automatic_metrics(
        _doc(els), None, "pdf",
        {"element_count_by_type": {"caption": 3, "header": 1}})
    assert m["silent_drop_count"] == {"value": 3, "reason": None}


def test_by_type_records_page_furniture_batch408():
    els = [
        _el("e0", "header", {"page": 1}),
        _el("e1", "footer", {"page": 1}),
        _el("e2", "caption", {"page": 1}),
    ]
    m = compute_automatic_metrics(_doc(els), None, "pdf", None)
    assert m["element_count_by_type"] == {
        "value": {"header": 1, "footer": 1, "caption": 1},
        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch408():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第六百八十批 ----------

def test_source_no_eval_batch408():
    assert "eval(" not in _src()


def test_source_no_exec_batch408():
    assert "exec(" not in _src()


def test_source_no_compile_batch408():
    assert "compile(" not in _src()


def test_source_no_globals_batch408():
    assert "globals(" not in _src()


def test_source_no_locals_batch408():
    assert "locals(" not in _src()


def test_source_no_os_system_batch408():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch408():
    assert "subprocess" not in _src()


def test_source_no_popen_batch408():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch408():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch408():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch408():
    assert "socket" not in _src()


def test_source_no_requests_batch408():
    assert "requests" not in _src()


def test_source_no_urllib_batch408():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch408():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch408():
    assert "yield" not in _src()


def test_source_no_async_await_batch408():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch408():
    assert "open(" not in _src()
