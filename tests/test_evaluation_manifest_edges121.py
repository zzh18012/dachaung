"""evaluation/manifest.py 第四百二十七轮 edges 测试（Round 983）。

补强 edges120 未触及的角度（第三百五十九批，probe 实证）。

新角度：
- annotation_file 绝对路径 → 错误字段名
  "documents[d1].annotation_file 必须是相对路径…"
- annotation_file 反斜杠 → 同字段名 "…必须使用正斜杠…"
- expected_failures path 绝对路径 → 字段名
  "expected_failures[ef1].path"（ef 分支第一次锁定）
- 同一 doc_id 同时出现在 documents 与 expected_failures →
  双双照常载入、resolved_path 相等、ef source_type 默认 None
- expectations 子 dict 原样透传（含 required_markers）
- forbidden tokens 第四百五十三批（open 1）
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


def _load(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return load_manifest(f, tmp_path)


_BASE = {"manifest_version": "1.0", "devset_status": "incomplete"}


# ---------- annotation_file 绝对路径 ----------

def test_annotation_file_absolute_rejected_batch181(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, "m1.json", {**_BASE, "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf",
             "annotation_file": "/abs/ann.json"}]})
    assert str(ei.value).startswith(
        "documents[d1].annotation_file 必须是相对路径，"
        "禁止绝对路径：/abs/ann.json")


# ---------- annotation_file 反斜杠 ----------

def test_annotation_file_backslash_rejected_batch181(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, "m2.json", {**_BASE, "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf",
             "annotation_file": "anns\\ann.json"}]})
    assert str(ei.value) == (
        "documents[d1].annotation_file 必须使用正斜杠，"
        "禁止反斜杠：anns\\ann.json")


# ---------- ef path 绝对路径 ----------

def test_ef_path_absolute_rejected_batch181(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, "m3.json", {
            **_BASE, "documents": [],
            "expected_failures": [
                {"doc_id": "ef1", "path": "/abs/bad.pdf",
                 "expected_error_code": "E_X"}]})
    assert str(ei.value) == (
        "expected_failures[ef1].path 必须是相对路径，"
        "禁止绝对路径：/abs/bad.pdf")


# ---------- 同 doc_id 双列表 ----------

def test_same_doc_id_in_both_lists_batch181(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, "m4.json", {
        **_BASE,
        "documents": [{"doc_id": "same", "path": "samples/a.pdf",
                       "source_type": "pdf"}],
        "expected_failures": [
            {"doc_id": "same", "path": "samples/a.pdf",
             "expected_error_code": "E_Y"}]})
    assert m.file_count == 1
    assert len(m.expected_failures) == 1
    assert m.documents[0].resolved_path == \
        m.expected_failures[0].resolved_path
    assert m.expected_failures[0].expected_error_code == "E_Y"
    assert m.expected_failures[0].source_type is None


# ---------- expectations 透传 ----------

def test_expectations_passthrough_batch181(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, "m5.json", {**_BASE, "documents": [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf",
         "expectations": {
             "element_count_by_type": {"paragraph": 2},
             "required_markers": ["AB"]}}]})
    assert m.documents[0].expectations == {
        "element_count_by_type": {"paragraph": 2},
        "required_markers": ["AB"]}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch181():
    src = _src()
    assert "f\"documents[{d['doc_id']}].annotation_file\"," in src
    assert "f\"expected_failures[{ef['doc_id']}].path\"" in src
    assert "if _has_backslash(path_str):" in src
    assert 'f"{field_name} 必须使用正斜杠，禁止反斜杠：{path_str}"' in src


# ---------- forbidden tokens 第四百五十三批 ----------

def test_source_no_eval_batch181():
    assert "eval(" not in _src()


def test_source_no_exec_batch181():
    assert "exec(" not in _src()


def test_source_no_compile_batch181():
    assert "compile(" not in _src()


def test_source_no_globals_batch181():
    assert "globals(" not in _src()


def test_source_no_locals_batch181():
    assert "locals(" not in _src()


def test_source_no_os_system_batch181():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch181():
    assert "subprocess" not in _src()


def test_source_no_popen_batch181():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch181():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch181():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch181():
    assert "socket" not in _src()


def test_source_no_requests_batch181():
    assert "requests" not in _src()


def test_source_no_urllib_batch181():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch181():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch181():
    assert "yield" not in _src()


def test_source_no_async_await_batch181():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch181():
    assert _src().count("open(") == 1
