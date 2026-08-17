"""evaluation/metrics.py 第二百四十四轮 edges 测试（Round 800）。

补强 edges92 未触及的角度（第一百六十四批）。

新角度：
- heading 仅首位命中：h1 在 source_element_ids 第二位 →
  compliance 0.0（first-only 语义，出现不算）
- bbox 数字符串 ["0",...] → 0.0（str 非 int/float）
- bbox int/float 混用 [0, 0.5, 1, 1] → 1.0（数值类型可混）
- 绝对路径 rp 无 base_dir：存在文件 1 / 不存在 0 → 0.5
- expectations exp 0 → drops 0（0 < 0 False）
- expectations element_count_by_type 显式 None →
  no_expectations_element_count（or {} 挡 falsy）
- 实际超额不产生负 drop（exp 1 actual 5 → 0，max(0,·) 家族）
- forbidden tokens 第二百七十批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

from evaluation.metrics import compute_automatic_metrics


def _run(doc, error=None, src="pdf", exp=None, base=None):
    return compute_automatic_metrics(doc, error, src, exp, base)


# ---------- heading 仅首位 ----------

def test_heading_second_position_not_matched_batch54():
    o = _run({"elements": [
        {"element_id": "e1", "type": "paragraph", "content": "A"},
        {"element_id": "h1", "type": "heading", "content": "B"}],
        "chunks": [{"text": "A B",
                    "source_element_ids": ["e1", "h1"]}]})
    assert o["heading_boundary_compliance"] == {"value": 0.0,
                                                "reason": None}


# ---------- bbox 类型 ----------

def test_bbox_numeric_strings_rejected_batch54():
    o = _run({"elements": [{"type": "paragraph",
                            "source_locator": {
                                "page": 1,
                                "bbox": ["0", "0", "1", "1"]}}]})
    assert o["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


def test_bbox_int_float_mix_valid_batch54():
    o = _run({"elements": [{"type": "paragraph",
                            "source_locator": {
                                "page": 1,
                                "bbox": [0, 0.5, 1, 1]}}]})
    assert o["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 绝对路径 rp ----------

def test_absolute_resource_path_no_base_dir_batch54():
    tmp = Path(tempfile.mkdtemp())
    good = tmp / "img.png"
    good.write_bytes(b"x")
    o = _run({"elements": [
        {"type": "image", "resource_path": str(good)},
        {"type": "image", "resource_path": str(tmp / "no.png")}]})
    assert o["image_resource_exists_ratio"] == {"value": 0.5,
                                                "reason": None}


# ---------- expectations 边界 ----------

def test_expectation_zero_drops_zero_batch54():
    o = _run({"elements": [{"type": "paragraph", "content": "A"}]},
             exp={"element_count_by_type": {"paragraph": 0}})
    assert o["silent_drop_count"] == {"value": 0, "reason": None}


def test_expectations_count_none_reason_batch54():
    o = _run({"elements": []},
             exp={"element_count_by_type": None})
    assert o["silent_drop_count"] == {
        "value": None, "reason": "no_expectations_element_count"}


def test_actual_exceeds_no_negative_drops_batch54():
    o = _run({"elements": [{"type": "paragraph", "content": "A"}] * 5},
             exp={"element_count_by_type": {"paragraph": 1}})
    assert o["silent_drop_count"] == {"value": 0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_first_id_lines_batch54():
    src = _src()
    assert "chunk_first_ids.add(ids[0])" in src
    assert "if actual < exp:" in src
    assert "expected_counts = expectations.get" in src


# ---------- forbidden tokens 第二百七十批 ----------

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
