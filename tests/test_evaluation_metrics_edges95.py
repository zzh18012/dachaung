"""evaluation/metrics.py 第二百五十八轮 edges 测试（Round 814）。

补强 edges94 未触及的角度（第一百七十八批）。

新角度：
- docx locator "page": None → **键存在即拒**（`"page" in loc`
  不看值）→ 0.0
- docx locator {"section": None} → **结构键存在即收**（值不
  校验）→ 1.0（键存在语义的两面）
- pdf page 0 → 拒（page < 1）；page 10**9 → 收（无上界）
- 两 chunk 重复引用同一 element → 双计有效 1.0
- 多集合重复字符：expected "AA" vs actual "AAA" → equal
  False、P = 2/3（min 交集 / |actual|）、R = 1.0
- resource_path 反斜杠绝对路径 + image_base_dir：直接
  Path(rp) 落空，但 base_dir / Path(rp).name 命中 → 1.0
- forbidden tokens 第二百八十四批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics as cam


def _doc(elements, chunks=()):
    return {"elements": elements, "chunks": list(chunks)}


def _el(eid, t, **over):
    e = {"element_id": eid, "type": t, "content": "A"}
    e.update(over)
    return e


def _cam(document, st="pdf", base=None):
    with patch.object(sv, "document_passes_schema", lambda d: True):
        return cam(document, None, st, None,
                   image_base_dir=base)


# ---------- docx 键存在语义 ----------

def test_docx_page_key_none_rejected_batch55():
    els = [_el("e1", "paragraph",
               source_locator={"section": 1, "page": None})]
    m = _cam(_doc(els), st="docx")
    assert m["docx_locator_valid_ratio"] == {"value": 0.0,
                                             "reason": None}


def test_docx_structural_key_none_value_valid_batch55():
    els = [_el("e1", "paragraph",
               source_locator={"section": None})]
    m = _cam(_doc(els), st="docx")
    assert m["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}


# ---------- pdf page 界 ----------

def test_pdf_page_zero_rejected_batch55():
    els = [_el("f1", "footer", source_locator={"page": 0})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {"value": 0.0,
                                            "reason": None}


def test_pdf_page_huge_valid_batch55():
    els = [_el("f1", "footer", source_locator={"page": 10 ** 9})]
    m = _cam(_doc(els))
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 跨 chunk 重复引用 ----------

def test_duplicate_cross_chunk_refs_both_valid_batch55():
    els = [_el("e1", "paragraph")]
    chs = [{"text": "A", "source_element_ids": ["e1"]},
           {"text": "B", "source_element_ids": ["e1"]}]
    m = _cam(_doc(els, chs))
    assert m["chunk_reference_intact_ratio"] == {"value": 1.0,
                                                 "reason": None}


# ---------- 多集合重复 ----------

def test_multiset_duplicate_chars_batch55():
    els = [_el("e1", "paragraph", content="AA")]
    chs = [{"text": "AAA", "source_element_ids": ["e1"]}]
    m = _cam(_doc(els, chs))
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}
    assert m["text_char_multiset_precision"]["value"] == 2 / 3
    assert m["text_char_multiset_recall"] == {"value": 1.0,
                                              "reason": None}


# ---------- 反斜杠 rp + base_dir ----------

def test_backslash_rp_base_dir_fallback_batch55(tmp_path):
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    (img_dir / "x.png").write_bytes(b"png")
    els = [_el("i1", "image", content=None,
               resource_path=r"C:\somewhere\x.png")]
    m = _cam(_doc(els), base=img_dir)
    assert m["image_resource_exists_ratio"] == {"value": 1.0,
                                                "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'if "page" in loc or "bbox" in loc:' in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src
    assert "common = sum((c_expected & c_actual).values())" in src


# ---------- forbidden tokens 第二百八十四批 ----------

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


def test_source_open_count_zero_batch55():
    assert "open(" not in _src()
