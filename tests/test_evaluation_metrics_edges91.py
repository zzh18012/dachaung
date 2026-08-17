"""evaluation/metrics.py 第二百三十轮 edges 测试（Round 786）。

补强 edges88-90 未触及的角度（第一百五十批）。

新角度：
- schema_valid 异常路径：document_passes_schema 抛 RuntimeError →
  {"value": False, "reason": "schema_check_exception:RuntimeError"}
  （函数内延迟 import，patch evaluation.schema_validation 命名空间）
- 乱序独立性：expected "AB" vs actual "BA" → equal False 但
  multiset precision/recall 双 1.0（有序比对与多集合口径互不干扰）
- Unicode 空白全家族：NBSP/全角空格/em space/行分隔符全被剥离
  （content "A + 4 种空白 + B" vs chunks "AB" → equal True）
- image 的 content 不进 expected 序列
- 图片资源三态：bare 文件名 + image_base_dir 命中 / 零字节文件
  不算存在 / resource_path 指目录不算 → 1/3
- error dict 无 "code" 键 → KeyError('code') 直接传播
  （error["code"] 无 .get，现状记录）
- pdf locator 混合分数：2 有效 1 无效 → 2/3（非 0/1 两态）
- chunk source_element_ids 空列表 → 不算有效但进分母 → 0.5
- docx locator 单 relationship_id 即有效
- expectations 指向不存在的类型 → by_type.get(t,0) 回退 0 →
  drops 2
- forbidden tokens 第二百五十六批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics


def _run(doc, error=None, src="pdf", exp=None, base=None):
    return compute_automatic_metrics(doc, error, src, exp, base)


# ---------- schema_valid 异常路径 ----------

def test_schema_valid_exception_reason_batch54():
    with patch.object(sv, "document_passes_schema",
                      side_effect=RuntimeError("boom")):
        o = _run({"elements": [], "chunks": []})
    assert o["schema_valid"] == {
        "value": False, "reason": "schema_check_exception:RuntimeError"}


# ---------- 乱序独立性 ----------

def test_reordered_multiset_full_batch54():
    o = _run({"elements": [{"type": "paragraph", "content": "AB"}],
              "chunks": [{"text": "BA"}]})
    assert o["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert o["text_char_multiset_precision"] == {"value": 1.0,
                                                 "reason": None}
    assert o["text_char_multiset_recall"] == {"value": 1.0,
                                              "reason": None}


# ---------- Unicode 空白家族 ----------

def test_unicode_whitespace_family_stripped_batch54():
    o = _run({"elements": [{"type": "paragraph",
                            "content": "A\xa0　 B"}],
              "chunks": [{"text": "AB"}]})
    assert o["text_preservation_equal"] == {"value": True, "reason": None}
    assert o["text_char_multiset_precision"]["value"] == 1.0


# ---------- image content 排除 ----------

def test_image_content_excluded_batch54():
    o = _run({"elements": [{"type": "image", "resource_path": "x",
                            "content": "XYZ"},
                           {"type": "paragraph", "content": "A"}],
              "chunks": [{"text": "A"}]})
    assert o["text_preservation_equal"] == {"value": True, "reason": None}


# ---------- 图片资源三态 ----------

def test_image_resource_three_states_batch54():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "good.png").write_bytes(b"\x89PNG")
    (tmp / "empty.png").write_bytes(b"")
    (tmp / "sub").mkdir()
    o = _run({"elements": [
        {"type": "image", "resource_path": "good.png"},
        {"type": "image", "resource_path": "empty.png"},
        {"type": "image", "resource_path": str(tmp / "sub")}]},
        base=tmp)
    assert o["image_resource_exists_ratio"]["value"] == pytest.approx(1 / 3)


# ---------- error 无 code 键 ----------

def test_error_without_code_key_raises_batch54():
    with pytest.raises(KeyError, match="'code'"):
        _run({"elements": []}, error={"message": "boom"})


# ---------- pdf 混合分数 ----------

def test_pdf_locator_mixed_two_thirds_batch54():
    o = _run({"elements": [
        {"type": "paragraph",
         "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "table", "source_locator": {"page": 2}},
        {"type": "paragraph", "source_locator": {"page": 0}}]})
    assert o["pdf_locator_valid_ratio"]["value"] == pytest.approx(2 / 3)


# ---------- chunk 空 ids ----------

def test_chunk_empty_ids_half_batch54():
    o = _run({"elements": [{"element_id": "e1", "type": "paragraph",
                            "content": "A"}],
              "chunks": [{"text": "A", "source_element_ids": ["e1"]},
                         {"text": "", "source_element_ids": []}]})
    assert o["chunk_reference_intact_ratio"] == {"value": 0.5,
                                                 "reason": None}


# ---------- docx relationship_id ----------

def test_docx_relationship_id_alone_valid_batch54():
    o = _run({"elements": [{"type": "paragraph",
                            "source_locator": {"relationship_id":
                                               "rId7"}}]},
             src="docx")
    assert o["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}


# ---------- expectations 指向不存在类型 ----------

def test_expectation_missing_type_falls_back_zero_batch54():
    o = _run({"elements": [{"type": "table", "content": ""}]},
             exp={"element_count_by_type": {"paragraph": 2}})
    assert o["silent_drop_count"] == {"value": 2, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_guard_lines_batch54():
    src = _src()
    assert "error[\"code\"] if error else None" in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src
    assert "if p.is_file() and p.stat().st_size > 0:" in src
    assert "actual = by_type.get(t, 0)" in src


# ---------- forbidden tokens 第二百五十六批 ----------

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
