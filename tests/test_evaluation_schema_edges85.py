"""evaluation/schema.py 第二百五十七轮 edges 测试（Round 813）。

补强 edges84 未触及的角度（第一百七十七批）。

新角度（annotation.schema.json 行为面 + validate 泛型）：
- 极简标注（仅 annotation_version + doc_id）合法；annotator
  任意串合法（脱敏约定靠人守，schema 不强制）
- annotation_version "2.0" → const；doc_id "" → minLength
- 顶层额外键 → additionalProperties（path []）
- boundary_anchor 可选 reason 键放行；marker "" → minLength
  （行为面，edges83 只锁结构）
- heading_order level 0 → minimum；"2" 字符串 → type integer
- figure_caption_pairs caption_text "" → minLength
- validate 收 list 实例 → "is not of type 'object'"（path []）
- validate_file 收目录 → FileNotFoundError "待校验文件不存在"
- forbidden tokens 第二百八十三批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (EvalSchemaError, validate,
                               validate_file)

ANN = {"annotation_version": "1.0", "doc_id": "d"}


def _err(inst):
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "annotation.schema.json")
    return ei.value.errors[0]


# ---------- 极简 / annotator ----------

def test_minimal_annotation_valid_batch55():
    validate(dict(ANN), "annotation.schema.json")


def test_annotator_arbitrary_string_valid_batch55():
    validate({**ANN, "annotator": "reviewer_a"},
             "annotation.schema.json")


# ---------- const / minLength ----------

def test_annotation_version_const_batch55():
    er = _err({**ANN, "annotation_version": "2.0"})
    assert er["path"] == ["annotation_version"]
    assert "'1.0' was expected" == er["message"]


def test_annotation_doc_id_empty_batch55():
    er = _err({**ANN, "doc_id": ""})
    assert er["path"] == ["doc_id"]
    assert "'' should be non-empty" == er["message"]


# ---------- 顶层封闭 ----------

def test_annotation_extra_top_key_rejected_batch55():
    er = _err({**ANN, "zzz": 1})
    assert er["path"] == []
    assert "Additional properties are not allowed" in er["message"]


# ---------- boundary_anchor ----------

def test_anchor_reason_key_valid_batch55():
    validate({**ANN, "chunk_boundary_anchors": [
        {"marker": "m", "position": "after", "reason": "sb"}]},
        "annotation.schema.json")


def test_anchor_empty_marker_rejected_batch55():
    er = _err({**ANN, "chunk_boundary_anchors": [
        {"marker": "", "position": "after"}]})
    assert er["path"] == ["chunk_boundary_anchors", 0, "marker"]
    assert "'' should be non-empty" == er["message"]


# ---------- heading_order ----------

def test_heading_level_zero_rejected_batch55():
    er = _err({**ANN, "heading_order": [{"level": 0, "text": "t"}]})
    assert er["path"] == ["heading_order", 0, "level"]
    assert "0 is less than the minimum of 1" == er["message"]


def test_heading_level_string_rejected_batch55():
    er = _err({**ANN, "heading_order": [
        {"level": "2", "text": "t"}]})
    assert er["path"] == ["heading_order", 0, "level"]
    assert "'2' is not of type 'integer'" == er["message"]


# ---------- figure_caption_pairs ----------

def test_caption_text_empty_rejected_batch55():
    er = _err({**ANN, "figure_caption_pairs": [
        {"figure_marker": "f", "caption_text": ""}]})
    assert er["path"] == ["figure_caption_pairs", 0,
                          "caption_text"]
    assert "'' should be non-empty" == er["message"]


# ---------- validate 泛型 ----------

def test_validate_list_instance_batch55():
    with pytest.raises(EvalSchemaError) as ei:
        validate([1, 2], "manifest.schema.json")
    er = ei.value.errors[0]
    assert er["path"] == []
    assert "[1, 2] is not of type 'object'" == er["message"]


# ---------- validate_file 目录 ----------

def test_validate_file_directory_not_found_batch55():
    tmp = Path(tempfile.mkdtemp())
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp, "manifest.schema.json")
    assert str(ei.value).startswith("待校验文件不存在: ")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src


# ---------- forbidden tokens 第二百八十三批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch55():
    assert _src().count("open(") == 2
