"""evaluation/metrics.py 第二百零七轮 edges 测试（Round 751）。

补强 edges83-85 未触及的角度（第一百一十六批）。

新角度：
- page=True（bool）被 PDF locator 判 valid（isinstance(True, int) 成立、
  与 bbox 的显式 bool 排除对照）；page=1.0（float）invalid
- DOCX：page 键存在但值为 None → 仍 invalid（键存在性检查，非真值）；
  relationship_id-only locator → valid
- image 兜底：绝对 rp 零字节 + base_dir 同名真文件 → 1.0；
  绝对 rp 不存在 + base_dir 同名 → 命中（append 不看绝对性，0.5 对照）
- element_count_by_type 保留首次出现顺序
- 空白-only expected + 空 actual：equal=True 但 P/R 均为 null
  （empty_expected_and_actual）—— equal 与 P/R 口径分离
- Unicode 空白全家（U+3000/U+2028/U+00A0/\r/\x0c）全删；零宽 U+200B 保留
- silent_drop：expectations 无键与空 dict 同因；paragraph:0 → 0；
  float 期望 2.0 实际 1 → int(1.0)=1
- heading element_id None + chunk 首 id None → 命中（None 匹配 None）
- elements 传 dict → AttributeError（未守卫，现状记录）
- forbidden tokens 第二百二十一批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics

ZWSP = "​"


def _doc(elements, chunks=()):
    return {"elements": list(elements), "chunks": list(chunks)}


# ---------- PDF page 类型边界 ----------

def test_pdf_page_bool_true_valid_batch54(tmp_path):
    d = _doc([{"type": "paragraph",
               "source_locator": {"page": True, "bbox": [1, 2, 3, 4]}}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0, "reason": None}


def test_pdf_page_float_invalid_batch54():
    d = _doc([{"type": "paragraph",
               "source_locator": {"page": 1.0, "bbox": [1, 2, 3, 4]}}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0, "reason": None}


# ---------- DOCX 键存在性 ----------

def test_docx_page_key_none_value_invalid_batch54():
    d = _doc([{"type": "paragraph", "source_locator": {"page": None}}])
    out = compute_automatic_metrics(d, None, "docx", None)
    assert out["docx_locator_valid_ratio"] == {"value": 0.0, "reason": None}


def test_docx_relationship_id_only_valid_batch54():
    d = _doc([{"type": "paragraph",
               "source_locator": {"relationship_id": "r1"}}])
    out = compute_automatic_metrics(d, None, "docx", None)
    assert out["docx_locator_valid_ratio"] == {"value": 1.0, "reason": None}


# ---------- image 兜底候选 ----------

def test_image_zero_abs_rp_base_fallback_batch54():
    tmp = Path(tempfile.mkdtemp())
    z = tmp / "img.png"
    z.write_bytes(b"")
    base = tmp / "base"
    base.mkdir()
    (base / "img.png").write_bytes(b"x")
    d = _doc([{"type": "image", "resource_path": str(z)}])
    out = compute_automatic_metrics(d, None, "pdf", None,
                                    image_base_dir=base)
    assert out["image_resource_exists_ratio"] == {"value": 1.0,
                                                  "reason": None}


def test_image_abs_rp_missing_base_name_hit_batch54():
    # append 不看 rp 是否绝对：绝对路径不存在也拼 base_dir/名字
    tmp = Path(tempfile.mkdtemp())
    base = tmp / "base"
    base.mkdir()
    (base / "ghost.png").write_bytes(b"x")
    d = _doc([{"type": "image", "resource_path": str(tmp / "ghost.png")},
              {"type": "image", "resource_path": str(tmp / "other.png")}])
    out = compute_automatic_metrics(d, None, "pdf", None,
                                    image_base_dir=base)
    assert out["image_resource_exists_ratio"] == {"value": 0.5,
                                                  "reason": None}


# ---------- element_count_by_type 顺序 ----------

def test_by_type_first_occurrence_order_batch54():
    d = _doc([{"type": "table"}, {"type": "heading"}, {"type": "table"}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert list(out["element_count_by_type"]["value"]) == ["table",
                                                           "heading"]
    assert out["element_count_by_type"]["value"] == {"table": 2,
                                                     "heading": 1}


# ---------- 空白-only expected ----------

def test_ws_only_expected_equal_true_but_pr_null_batch54():
    d = _doc([{"type": "paragraph", "content": "  "}], [{"text": ""}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": True, "reason": None}
    assert out["text_char_multiset_precision"] == {
        "value": None, "reason": "empty_expected_and_actual"}
    assert out["text_char_multiset_recall"] == {
        "value": None, "reason": "empty_expected_and_actual"}


@pytest.mark.parametrize("ch", ["　", "", " ", "\r", "\x0c"])
def test_unicode_whitespace_all_stripped_batch54(ch):
    d = _doc([{"type": "paragraph", "content": f"a{ch}b"}],
             [{"text": "ab"}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": True, "reason": None}


def test_zero_width_space_not_stripped_batch54():
    # U+200B 不是 isspace → 保留为实字符
    d = _doc([{"type": "paragraph", "content": f"a{ZWSP}"}],
             [{"text": "a"}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["text_preservation_equal"] == {"value": False, "reason": None}
    assert out["text_char_multiset_recall"] == {"value": 0.5, "reason": None}


# ---------- silent_drop 边界 ----------

def _one_para_doc():
    return _doc([{"type": "paragraph", "content": "a"}], [{"text": "a"}])


def test_silent_drop_expectations_without_key_batch54():
    out = compute_automatic_metrics(_one_para_doc(), None, "pdf", {"x": 1})
    assert out["silent_drop_count"] == {
        "value": None, "reason": "no_expectations_element_count"}


def test_silent_drop_empty_count_dict_batch54():
    out = compute_automatic_metrics(
        _one_para_doc(), None, "pdf", {"element_count_by_type": {}})
    assert out["silent_drop_count"] == {
        "value": None, "reason": "no_expectations_element_count"}


def test_silent_drop_zero_expectation_zero_batch54():
    out = compute_automatic_metrics(
        _one_para_doc(), None, "pdf", {"element_count_by_type":
                                       {"paragraph": 0}})
    assert out["silent_drop_count"] == {"value": 0, "reason": None}


def test_silent_drop_float_expectation_coerced_batch54():
    out = compute_automatic_metrics(
        _one_para_doc(), None, "pdf", {"element_count_by_type":
                                       {"paragraph": 2.0}})
    assert out["silent_drop_count"] == {"value": 1, "reason": None}
    assert isinstance(out["silent_drop_count"]["value"], int)


# ---------- heading None 匹配 ----------

def test_heading_none_id_matched_by_none_first_batch54():
    d = _doc([{"type": "heading"}], [{"source_element_ids": [None]}])
    out = compute_automatic_metrics(d, None, "pdf", None)
    assert out["heading_boundary_compliance"] == {"value": 1.0,
                                                  "reason": None}


# ---------- 未守卫输入 ----------

def test_elements_dict_attributeerror_batch54():
    with pytest.raises(AttributeError):
        compute_automatic_metrics({"elements": {"a": 1}, "chunks": []},
                                  None, "pdf", None)


def test_both_none_pipeline_false_batch54():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"] == {"value": False, "reason": None}
    assert out["error_code"] == {"value": None, "reason": None}
    assert out["schema_valid"]["reason"] == "pipeline_failed"


# ---------- ratio float 类型 ----------

def test_ratio_value_always_float_batch54():
    d = _doc([{"type": "heading", "element_id": "h1"}],
             [{"source_element_ids": ["h1"]}])
    v = compute_automatic_metrics(d, None, "pdf", None)[
        "heading_boundary_compliance"]["value"]
    assert v == 1.0
    assert isinstance(v, float)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_structural_keys_tuple_batch54():
    src = _src()
    assert '"relationship_id",' in src
    assert 'candidates.append(image_base_dir / Path(rp).name)' in src
    assert "not ch.isspace()" in src


def test_source_no_bool_in_page_check_batch54():
    src = _src()
    # page 检查无 bool 排除（与 bbox 的 isinstance(v, bool) 排除对照）
    assert 'isinstance(page, int)' in src
    assert 'isinstance(v, bool)' in src


# ---------- forbidden tokens 第二百二十一批 ----------

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
