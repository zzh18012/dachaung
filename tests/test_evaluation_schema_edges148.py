"""evaluation/schema.py 第五百八十三轮 edges 测试（Round 1317）。

补强 edges147 未触及的角度（第六百八十九批，probe 实证）。

新角度（annotation.schema.json 声明级严闭面）：
- **position 枚举**——
  'middle' 拒（schema
  声明 [before,
  after]——与运行时
  宽容（edges158 已
  锁 middle 落 after）
  的差面首锁）
- **position 必填**——
  缺键 required 拒
  （运行时 .get 默认
  after 的对差面）
- **marker 严域**——
  '' 非空拒 / int 型拒
  （运行时空 marker
  静默 missing 的对差
  面）
- **anchor 严闭**——
  额外键拒；reason
  键合法可缺
- **版本 const**——
  '2.0' → "'1.0' was
  expected"
- **根闭包**——顶层
  额外键 @ []；缺
  doc_id required
- **anchors 缺键 VALID**
  ——chunk_boundary_
  anchors 可选
- **heading_order
  level 下界**——0 拒
  minimum 1
- **figure_caption_
  pairs**——缺
  caption_text required
- **date 空串拒**
- forbidden tokens 第七百六十三批（open 2）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate


BASE = {
    "annotation_version": "1.0",
    "doc_id": "d1",
    "annotator": "reviewer_a",
    "date": "2026-01-01",
    "figure_caption_pairs": [
        {"figure_marker": "Figure 1",
         "caption_text": "A caption"}],
    "heading_order": [
        {"level": 1, "text": "Title"}],
    "chunk_boundary_anchors": [
        {"marker": "Word3.", "position": "after",
         "reason": "ok"}],
}


def _rej(mutate, message, path):
    d = copy.deepcopy(BASE)
    mutate(d)
    try:
        validate(d, "annotation.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert list(e.errors[0]["path"]) == path
    else:
        raise AssertionError("expected rejection")


def _acc(mutate):
    d = copy.deepcopy(BASE)
    mutate(d)
    validate(d, "annotation.schema.json")


# ---------- position 枚举 / 必填 ----------

def test_position_middle_rejected_batch515():
    _rej(lambda d: d["chunk_boundary_anchors"][0]
             .__setitem__("position", "middle"),
         "'middle' is not one of ['before', "
         "'after']",
         ["chunk_boundary_anchors", 0, "position"])


def test_position_missing_rejected_batch515():
    _rej(lambda d: d["chunk_boundary_anchors"][0]
             .pop("position"),
         "'position' is a required property",
         ["chunk_boundary_anchors", 0])


def test_position_before_valid_batch515():
    _acc(lambda d: d["chunk_boundary_anchors"][0]
         .__setitem__("position", "before"))


# ---------- marker 严域 ----------

def test_marker_empty_rejected_batch515():
    _rej(lambda d: d["chunk_boundary_anchors"][0]
             .__setitem__("marker", ""),
         "'' should be non-empty",
         ["chunk_boundary_anchors", 0, "marker"])


def test_marker_int_rejected_batch515():
    _rej(lambda d: d["chunk_boundary_anchors"][0]
             .__setitem__("marker", 5),
         "5 is not of type 'string'",
         ["chunk_boundary_anchors", 0, "marker"])


# ---------- anchor 严闭 ----------

def test_anchor_extra_key_batch515():
    _rej(lambda d: d["chunk_boundary_anchors"][0]
             .__setitem__("zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)",
         ["chunk_boundary_anchors", 0])


def test_anchor_reason_optional_batch515():
    _acc(lambda d: d["chunk_boundary_anchors"][0]
         .pop("reason"))


# ---------- 版本 const ----------

def test_version_const_batch515():
    _rej(lambda d: d.__setitem__("annotation_version",
                                 "2.0"),
         "'1.0' was expected",
         ["annotation_version"])


# ---------- 根闭包 / 必填 ----------

def test_root_extra_key_batch515():
    _rej(lambda d: d.__setitem__("zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)", [])


def test_doc_id_required_batch515():
    _rej(lambda d: d.pop("doc_id"),
         "'doc_id' is a required property", [])


# ---------- anchors 可选 / 型 ----------

def test_anchors_missing_valid_batch515():
    _acc(lambda d: d.pop("chunk_boundary_anchors"))


def test_anchors_string_rejected_batch515():
    _rej(lambda d: d.__setitem__(
             "chunk_boundary_anchors", "x"),
         "'x' is not of type 'array'",
         ["chunk_boundary_anchors"])


def test_anchors_empty_list_valid_batch515():
    _acc(lambda d: d.__setitem__(
        "chunk_boundary_anchors", []))


# ---------- heading_order / figure_caption_pairs ----------

def test_heading_level_zero_batch515():
    _rej(lambda d: d["heading_order"][0]
             .__setitem__("level", 0),
         "0 is less than the minimum of 1",
         ["heading_order", 0, "level"])


def test_fcp_missing_caption_batch515():
    _rej(lambda d: d["figure_caption_pairs"][0]
             .pop("caption_text"),
         "'caption_text' is a required property",
         ["figure_caption_pairs", 0])


# ---------- date ----------

def test_date_empty_rejected_batch515():
    _rej(lambda d: d.__setitem__("date", ""),
         "'' should be non-empty", ["date"])


# ---------- 基线 ----------

def test_base_valid_batch515():
    validate(copy.deepcopy(BASE),
             "annotation.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch515():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百六十三批 ----------

def test_source_no_eval_batch515():
    assert "eval(" not in _src()


def test_source_no_exec_batch515():
    assert "exec(" not in _src()


def test_source_no_compile_batch515():
    assert "compile(" not in _src()


def test_source_no_globals_batch515():
    assert "globals(" not in _src()


def test_source_no_locals_batch515():
    assert "locals(" not in _src()


def test_source_no_os_system_batch515():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch515():
    assert "subprocess" not in _src()


def test_source_no_popen_batch515():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch515():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch515():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch515():
    assert "socket" not in _src()


def test_source_no_requests_batch515():
    assert "requests" not in _src()


def test_source_no_urllib_batch515():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch515():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch515():
    assert "yield" not in _src()


def test_source_no_async_await_batch515():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch515():
    assert _src().count("open(") == 2
