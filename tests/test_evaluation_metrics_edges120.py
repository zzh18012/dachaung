"""evaluation/metrics.py 第四百四十轮 edges 测试（Round 996）。

补强 edges119 未触及的角度（第三百七十二批，probe 实证）。

新角度：
- 多集合 min 语义："aab" vs "abb" → 交集 2 → P=R=2/3、
  equal False（乱序/替换各自可见）
- 未知元素类型 "zzz" 仍参与文本保留（过滤只排除 image，
  _TEXT_TYPES 常量实为死代码）
- silent_drop 多类型混合：paragraph 缺口 2 计入、table 盈余
  3 忽略 → drops 2
- resource_path 传 int → Path(rp) TypeError 原样上抛（无
  类型守卫）
- 全部元素 locator 无效 → ratio 0.0（float，非 null；有
  elements 就有分母）
- content None + chunk text None → 双侧按 "" 处理 →
  equal True + precision null "empty_expected_and_actual"
- forbidden tokens 第四百六十六批（open 0）
"""

from __future__ import annotations

import inspect

import pytest

from evaluation.metrics import compute_automatic_metrics


def _doc(elements=None, chunks=None):
    return {"elements": elements or [], "chunks": chunks or []}


# ---------- 多集合 min ----------

def test_multiset_aab_vs_abb_batch194():
    m = compute_automatic_metrics(
        _doc([{"type": "paragraph", "content": "aab",
               "element_id": "e1"}],
             [{"text": "abb", "source_element_ids": ["e1"]}]),
        None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 0.6666666666666666, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 未知类型参与文本保留 ----------

def test_unknown_type_participates_batch194():
    m = compute_automatic_metrics(
        _doc([{"type": "zzz", "content": "Q",
               "element_id": "e1"}],
             [{"text": "Q", "source_element_ids": ["e1"]}]),
        None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- silent_drop 多类型混合 ----------

def test_silent_drop_mixed_surplus_ignored_batch194():
    elements = [{"type": "paragraph", "element_id": "e1"}] + [
        {"type": "table", "element_id": f"t{i}"} for i in range(4)]
    m = compute_automatic_metrics(
        _doc(elements, []), None, "pdf",
        {"element_count_by_type": {"paragraph": 3, "table": 2}})
    assert m["silent_drop_count"] == {"value": 2, "reason": None}


# ---------- resource_path 非字符串 ----------

def test_resource_path_int_typeerror_batch194():
    with pytest.raises(TypeError, match="str or an os.PathLike"):
        compute_automatic_metrics(
            _doc([{"type": "image", "resource_path": 123}]),
            None, "pdf", None)


# ---------- 全无效 ratio 0.0 ----------

def test_all_invalid_pdf_ratio_zero_float_batch194():
    m = compute_automatic_metrics(
        _doc([{"type": "paragraph",
               "source_locator": {"page": 0},
               "element_id": "e1"}], []),
        None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}
    assert type(m["pdf_locator_valid_ratio"]["value"]) is float


# ---------- content/text 双 None ----------

def test_none_content_and_text_both_empty_batch194():
    m = compute_automatic_metrics(
        _doc([{"type": "paragraph", "content": None,
               "element_id": "e1"}],
             [{"text": None, "source_element_ids": ["e1"]}]),
        None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_key_lines_batch194():
    src = _src()
    assert 'return "".join(ch for ch in s if not ch.isspace())' in src
    assert "common = sum((c_expected & c_actual).values())" in src
    assert "if actual < exp:" in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src


# ---------- forbidden tokens 第四百六十六批 ----------

def test_source_no_eval_batch194():
    assert "eval(" not in _src()


def test_source_no_exec_batch194():
    assert "exec(" not in _src()


def test_source_no_compile_batch194():
    assert "compile(" not in _src()


def test_source_no_globals_batch194():
    assert "globals(" not in _src()


def test_source_no_locals_batch194():
    assert "locals(" not in _src()


def test_source_no_os_system_batch194():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch194():
    assert "subprocess" not in _src()


def test_source_no_popen_batch194():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch194():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch194():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch194():
    assert "socket" not in _src()


def test_source_no_requests_batch194():
    assert "requests" not in _src()


def test_source_no_urllib_batch194():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch194():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch194():
    assert "yield" not in _src()


def test_source_no_async_await_batch194():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch194():
    assert "open(" not in _src()
