"""evaluation/manifest.py 第二百八十七轮 edges 测试（Round 843）。

补强 edges100 未触及的角度（第二百一十七批）。

新角度：
- pdf_count/docx_count 混合计数（2 pdf + 1 docx）
- 链式配对 d1→d2、d2→d3（非互指）：frozenset
  {d1,d2} + {d2,d3} → 2 组（d3 因 seen 不再计未配对）
- devset_status "complete" 原样透传
- 无 expected_failures 键 → 空元组
- path_str 保留原始 "./samples/a.pdf"（resolved 已规范化但
  原串不动）
- 两 doc 指向同一文件 → file_count 2、组数 2（允许）
- source_type 与扩展名解耦（docx 类型配 .pdf 路径照常加载）
- forbidden tokens 第三百一十三批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


def _load(tmp_path, docs, name="m.json", **over):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    (root / "samples" / "c.docx").write_bytes(b"x")
    f = tmp_path / name
    payload = {"manifest_version": "1.0",
               "devset_status": "incomplete",
               "documents": docs}
    payload.update(over)
    f.write_text(json.dumps(payload), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", st="pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": st}
    d.update(over)
    return d


# ---------- 混合计数 ----------

def test_mixed_type_counts_batch55(tmp_path):
    m = _load(tmp_path, [
        _d("d1"), _d("d2", "samples/b.pdf"),
        _d("d3", "samples/c.docx", "docx")])
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1


# ---------- 链式配对 ----------

def test_chain_pairing_two_groups_batch55(tmp_path):
    m = _load(tmp_path, [
        _d("d1", paired_with="d2"),
        _d("d2", "samples/b.pdf", paired_with="d3"),
        _d("d3", "samples/c.docx", "docx")])
    assert m.content_group_count == 2
    assert m.file_count == 3


# ---------- devset_status 透传 ----------

def test_devset_status_complete_passthrough_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1")],
              devset_status="complete")
    assert m.devset_status == "complete"


# ---------- 无 ef 键 ----------

def test_expected_failures_default_empty_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1")])
    assert m.expected_failures == ()


# ---------- path_str 原样 ----------

def test_path_str_raw_preserved_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1", "./samples/a.pdf")])
    assert m.documents[0].path_str == "./samples/a.pdf"
    assert m.documents[0].resolved_path.name == "a.pdf"


# ---------- 同文件双 doc ----------

def test_two_docs_same_file_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1"), _d("d2")])
    assert m.file_count == 2
    assert m.content_group_count == 2
    assert m.documents[0].resolved_path == \
        m.documents[1].resolved_path


# ---------- 类型/扩展名解耦 ----------

def test_source_type_extension_decoupled_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1", st="docx")])
    assert m.documents[0].source_type == "docx"
    assert m.docx_count == 1
    assert m.pdf_count == 0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'if d.paired_with:' in src
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src
    assert "return sorted(s)" in src


# ---------- forbidden tokens 第三百一十三批 ----------

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


def test_source_open_count_is_1_batch55():
    assert _src().count("open(") == 1
