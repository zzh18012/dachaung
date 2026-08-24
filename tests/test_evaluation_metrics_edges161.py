"""evaluation/metrics.py 第五百八十二轮 edges 测试（Round 1355）。

补强 edges160 未触及的角度（第七百二十七批，probe 实证）。

新角度（全角/半角多集合分裂面）：
- **全角逗号**——
  '你好，世界' vs
  '你好,世界' →
  tpe False +
  tcmp/tcmr 各
  4/5=0.8（，与 ,
  不同码位计数）
- **全角数字**——
  '第１２３页' vs
  '第123页' →
  0.4/0.4（仅第/页
  相交）
- **表意空格剥离**
  ——U+3000 isspace
  → '你　好' vs
  '你好' 全等
  {True, 1.0, 1.0}
- **同板 CJK 全等**
  ——完全相同全角
  串三连满分
- forbidden tokens 第七百九十五批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import \
    compute_automatic_metrics


def _el(i, c):
    return {"element_id": "e%d" % i,
            "type": "paragraph",
            "source_locator": {"line": i},
            "parent_id": None, "content": c,
            "resource_path": None,
            "confidence": 0.9, "metadata": {}}


def _ch(i, text):
    return {"chunk_id": "c%d" % i, "text": text,
            "source_element_ids": ["e%d" % i],
            "source_spans": [], "metadata": {}}


def _m(exp, act):
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d", "source_hash": "a" * 64,
        "source_type": "text", "source_path": "t.txt",
        "parser_name": "f", "parser_version": "1",
        "relations": [], "warnings": [], "errors": [],
        "metadata": {},
        "elements": [_el(0, exp)],
        "chunks": [_ch(0, act)]}
    r = compute_automatic_metrics(
        doc, None, "text", None)
    return (r["text_preservation_equal"],
            r["text_char_multiset_precision"],
            r["text_char_multiset_recall"])


# ---------- 全角逗号 ----------

def test_fullwidth_comma_tpe_false_batch553():
    t = _m("你好，世界", "你好,世界")
    assert t[0] == {"value": False, "reason": None}


def test_fullwidth_comma_p_batch553():
    t = _m("你好，世界", "你好,世界")
    assert t[1] == {"value": 0.8, "reason": None}


def test_fullwidth_comma_r_batch553():
    t = _m("你好，世界", "你好,世界")
    assert t[2] == {"value": 0.8, "reason": None}


# ---------- 全角数字 ----------

def test_fullwidth_digits_tpe_false_batch553():
    t = _m("第１２３页", "第123页")
    assert t[0] == {"value": False, "reason": None}


def test_fullwidth_digits_p_batch553():
    t = _m("第１２３页", "第123页")
    assert t[1] == {"value": 0.4, "reason": None}


def test_fullwidth_digits_r_batch553():
    t = _m("第１２３页", "第123页")
    assert t[2] == {"value": 0.4, "reason": None}


def test_fullwidth_digits_symmetric_batch553():
    t = _m("第１２３页", "第123页")
    assert t[1] == t[2]


# ---------- 表意空格剥离 ----------

def test_ideographic_space_stripped_batch553():
    t = _m("你　好", "你好")
    assert t[0] == {"value": True, "reason": None}
    assert t[1] == {"value": 1.0, "reason": None}
    assert t[2] == {"value": 1.0, "reason": None}


def test_ideographic_space_both_sides_batch553():
    t = _m("你　好", "你　好")
    assert t[0] == {"value": True, "reason": None}


# ---------- 同板 CJK 全等 ----------

def test_identical_cjk_all_one_batch553():
    t = _m("你好，世界", "你好，世界")
    assert t == ({"value": True, "reason": None},
                 {"value": 1.0, "reason": None},
                 {"value": 1.0, "reason": None})


def test_cjk_swap_reorder_split_batch553():
    t = _m("中文内容", "内容中文")
    assert t[0] == {"value": False, "reason": None}
    assert t[1] == {"value": 1.0, "reason": None}
    assert t[2] == {"value": 1.0, "reason": None}


def test_cjk_extra_char_split_batch553():
    t = _m("中文", "中文字")
    assert t[0] == {"value": False, "reason": None}
    assert t[1] == {"value": 2 / 3, "reason": None}
    assert t[2] == {"value": 1.0, "reason": None}


# ---------- 其他指标不受码位影响 ----------

def test_fullwidth_comma_ect_one_batch553():
    doc = {
        "schema_version": "0.1.0",
        "document_id": "d", "source_hash": "a" * 64,
        "source_type": "text", "source_path": "t.txt",
        "parser_name": "f", "parser_version": "1",
        "relations": [], "warnings": [], "errors": [],
        "metadata": {},
        "elements": [_el(0, "你好，世界")],
        "chunks": [_ch(0, "你好,世界")]}
    r = compute_automatic_metrics(
        doc, None, "text", None)
    assert r["element_count_total"] == {
        "value": 1, "reason": None}
    assert r["crir" if "crir" in r
            else "chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_strip_isspace_batch553():
    assert "not ch.isspace()" in _src()


def test_source_counter_intersection_batch553():
    src = _src()
    assert "c_expected & c_actual" in src
    assert "sum((c_expected & c_actual).values())" \
        in src


# ---------- forbidden tokens 第七百九十五批 ----------

def test_source_no_eval_batch553():
    assert "eval(" not in _src()


def test_source_no_exec_batch553():
    assert "exec(" not in _src()


def test_source_no_compile_batch553():
    assert "compile(" not in _src()


def test_source_no_globals_batch553():
    assert "globals(" not in _src()


def test_source_no_locals_batch553():
    assert "locals(" not in _src()


def test_source_no_os_system_batch553():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch553():
    assert "subprocess" not in _src()


def test_source_no_popen_batch553():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch553():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch553():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch553():
    assert "socket" not in _src()


def test_source_no_requests_batch553():
    assert "requests" not in _src()


def test_source_no_urllib_batch553():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch553():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch553():
    assert "yield" not in _src()


def test_source_no_async_await_batch553():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch553():
    assert _src().count("open(") == 0
