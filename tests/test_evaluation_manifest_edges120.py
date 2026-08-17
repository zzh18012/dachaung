"""evaluation/manifest.py 第四百二十轮 edges 测试（Round 976）。

补强 edges119 未触及的角度（第三百五十二批，probe 实证）。

新角度：
- UNC 前缀 //server/share → startswith("/") 拦截（禁止绝对路径）
- "a:foo" 盘符冒号后无斜杠 → 不是 absolute-like，但 resolve()
  保持盘符相对 → 落在项目根外被二次拦截
- 穿越 "samples/../../outside.txt" 拒绝；"samples/../b.pdf"
  （折返后仍在根内）放行
- 尾斜杠目录 "samples/" 照常载入（加载器不查 is_file）
- annotation_file "" → falsy 跳过解析：annotation_file_str=""
  但 annotation_resolved=None（schema 未设 minLength）
- 链式配对 A↔B、B↔C → 2 组（frozenset 去重语义）
- 三角配对 A↔B、B↔C、C↔A → 3 组
- forbidden tokens 第四百四十六批（open 1）
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest, ManifestError


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "b.pdf").write_bytes(b"x")
    (tmp_path / "outside.txt").write_bytes(b"x")


def _load(tmp_path, name, doc_or_docs):
    docs = doc_or_docs if isinstance(doc_or_docs, list) else [doc_or_docs]
    f = tmp_path / name
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    return load_manifest(f, tmp_path)


# ---------- 路径形式 ----------

def test_unc_prefix_absolute_rejected_batch174(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, "m1.json", {
            "doc_id": "d1", "path": "//server/share/x.pdf",
            "source_type": "pdf"})
    assert "禁止绝对路径" in str(ei.value)
    assert "//server/share/x.pdf" in str(ei.value)


def test_drive_colon_no_slash_outside_root_batch174(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, "m2.json", {
            "doc_id": "d1", "path": "a:foo",
            "source_type": "pdf"})
    assert "解析后位于项目根目录之外" in str(ei.value)
    assert "a:foo → a:foo" in str(ei.value)


def test_traversal_escape_rejected_batch174(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, "m3.json", {
            "doc_id": "d1", "path": "samples/../../outside.txt",
            "source_type": "pdf"})
    assert "解析后位于项目根目录之外" in str(ei.value)


def test_traversal_folding_inside_root_ok_batch174(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, "m4.json", {
        "doc_id": "d1", "path": "samples/../b.pdf",
        "source_type": "pdf"})
    assert m.documents[0].resolved_path.name == "b.pdf"
    assert m.documents[0].resolved_path.is_file()


def test_trailing_slash_directory_loads_batch174(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, "m5.json", {
        "doc_id": "d1", "path": "samples/",
        "source_type": "pdf"})
    assert m.documents[0].resolved_path.name == "samples"
    assert m.documents[0].resolved_path.is_dir()


# ---------- annotation_file 空串 ----------

def test_annotation_file_empty_string_skipped_batch174(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, "m6.json", {
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf", "annotation_file": ""})
    d = m.documents[0]
    assert d.annotation_file_str == ""
    assert d.annotation_resolved is None


# ---------- 链式与三角配对 ----------

def test_chain_pairing_two_groups_batch174(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, "m7.json", [
        {"doc_id": "A", "path": "samples/a.pdf",
         "source_type": "pdf", "paired_with": "B"},
        {"doc_id": "B", "path": "samples/a.pdf",
         "source_type": "docx", "paired_with": "C"},
        {"doc_id": "C", "path": "samples/a.pdf",
         "source_type": "pdf"}])
    assert m.content_group_count == 2
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_triangle_pairing_three_groups_batch174(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, "m8.json", [
        {"doc_id": "A", "path": "samples/a.pdf",
         "source_type": "pdf", "paired_with": "B"},
        {"doc_id": "B", "path": "samples/a.pdf",
         "source_type": "docx", "paired_with": "C"},
        {"doc_id": "C", "path": "samples/a.pdf",
         "source_type": "pdf", "paired_with": "A"}])
    assert m.content_group_count == 3


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch174():
    src = _src()
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src
    assert "if d.doc_id not in seen and not d.paired_with:" in src
    assert "resolved = (project_root / path_str).resolve()" in src
    assert "if d.get(\"annotation_file\"):" in src


# ---------- forbidden tokens 第四百四十六批 ----------

def test_source_no_eval_batch174():
    assert "eval(" not in _src()


def test_source_no_exec_batch174():
    assert "exec(" not in _src()


def test_source_no_compile_batch174():
    assert "compile(" not in _src()


def test_source_no_globals_batch174():
    assert "globals(" not in _src()


def test_source_no_locals_batch174():
    assert "locals(" not in _src()


def test_source_no_os_system_batch174():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch174():
    assert "subprocess" not in _src()


def test_source_no_popen_batch174():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch174():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch174():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch174():
    assert "socket" not in _src()


def test_source_no_requests_batch174():
    assert "requests" not in _src()


def test_source_no_urllib_batch174():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch174():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch174():
    assert "yield" not in _src()


def test_source_no_async_await_batch174():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch174():
    assert _src().count("open(") == 1
