"""evaluation/metrics.py 第二百一十六轮 edges 测试（Round 772）。

补强 edges86-88 未触及的角度（第一百三十六批）。

新角度：
- element 缺 type 键 → by_type 记作 "unknown"（.get 默认）
- 未知 type "custom" 参与文本保留（v1.1 口径只排除 image，
  _TEXT_TYPES 常量是 v1.0 遗物不在判定里）→ equal/P/R 全 1
- content None → or "" 参与拼接：与空 chunks → equal True +
  P/R null empty_expected_and_actual
- chunk text None → actual 空：precision null empty_actual、
  recall 0.0、equal False
- 双 heading 一命中 → 0.5（部分合规参与，非 null）
- 有 heading 无 chunks → heading_boundary 0.0 参与
  （该函数不检查 no_chunks；chunk_ref 同输入 null no_chunks 对照）
- resource_path 空串 + base_dir 给定 → falsy 跳过 → 0.0
- bbox nan / inf → math.isfinite 拒 → 0.0
- _PDF_BBOX_REQUIRED_TYPES 边界：table/header/footer/image 无 bbox
  仅 page 即有效（1.0）；caption 无 bbox → 0.0
- expectations 只有 required_markers → silent_drop null
  "no_expectations_element_count"
- forbidden tokens 第二百四十二批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

from evaluation.metrics import compute_automatic_metrics


def _run(elements, chunks=(), src="pdf", exp=None, base=None):
    return compute_automatic_metrics(
        {"elements": list(elements), "chunks": list(chunks)},
        None, src, exp, base)


# ---------- element_count_by_type ----------

def test_missing_type_key_counts_unknown_batch54():
    out = _run([{"content": "X"}])
    assert out["element_count_by_type"] == {"value": {"unknown": 1},
                                            "reason": None}


# ---------- 文本保留 v1.1 口径 ----------

def test_custom_type_participates_in_text_batch54():
    out = _run([{"type": "custom", "content": "X"}],
               [{"text": "X", "source_element_ids": ["e1"]}])
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0


def test_content_none_treated_as_empty_batch54():
    out = _run([{"type": "paragraph", "content": None}])
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}
    assert out["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected_and_actual"}


def test_chunk_text_none_empty_actual_batch54():
    out = _run([{"type": "paragraph", "content": "A"}],
               [{"text": None, "source_element_ids": ["e1"]}])
    assert out["text_preservation_equal"]["value"] is False
    assert out["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_actual"}
    assert out["text_char_multiset_recall"] == {"value": 0.0,
                                                "reason": None}


# ---------- heading_boundary ----------

def test_two_headings_partial_half_batch54():
    out = _run([
        {"element_id": "h1", "type": "heading", "content": "A"},
        {"element_id": "h2", "type": "heading", "content": "B"},
    ], [{"text": "AB", "source_element_ids": ["h1", "h2"]}])
    assert out["heading_boundary_compliance"] == {"value": 0.5,
                                                  "reason": None}


def test_heading_no_chunks_zero_participating_batch54():
    out = _run([{"element_id": "h1", "type": "heading", "content": "A"}])
    assert out["heading_boundary_compliance"] == {"value": 0.0,
                                                  "reason": None}
    assert out["chunk_reference_intact_ratio"] == {
        "value": None, "reason": "no_chunks"}


# ---------- image resource ----------

def test_empty_resource_path_skipped_batch54():
    tmp = Path(tempfile.mkdtemp())
    out = _run([{"type": "image", "resource_path": ""}], base=tmp)
    assert out["image_resource_exists_ratio"] == {"value": 0.0,
                                                  "reason": None}


# ---------- bbox 有限性 ----------

def test_bbox_nan_rejected_batch54():
    out = _run([{"type": "paragraph",
                 "source_locator": {"page": 1,
                                    "bbox": [float("nan"), 0, 0, 0]}}])
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0,
                                              "reason": None}


def test_bbox_inf_rejected_batch54():
    out = _run([{"type": "paragraph",
                 "source_locator": {"page": 1,
                                    "bbox": [float("inf"), 0, 0, 0]}}])
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0,
                                              "reason": None}


# ---------- bbox 豁免类型 ----------

def test_no_bbox_types_valid_with_page_only_batch54():
    out = _run([
        {"type": "table", "source_locator": {"page": 1}},
        {"type": "header", "source_locator": {"page": 1}},
        {"type": "footer", "source_locator": {"page": 1}},
        {"type": "image", "source_locator": {"page": 1}},
    ])
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0,
                                              "reason": None}


def test_caption_requires_bbox_batch54():
    out = _run([{"type": "caption", "source_locator": {"page": 1}}])
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0,
                                              "reason": None}


# ---------- silent_drop ----------

def test_markers_only_expectations_null_batch54():
    out = _run([], exp={"required_markers": ["x"]})
    assert out["silent_drop_count"] == {
        "value": None, "reason": "no_expectations_element_count"}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_v11_semantics_lines_batch54():
    src = _src()
    assert 'if e.get("type") != "image"' in src
    assert 'c.get("text") or ""' in src
    assert "math.isfinite(v)" in src
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


# ---------- forbidden tokens 第二百四十二批 ----------

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
