"""evaluation/manifest.py 第二百九十四轮 edges 测试（Round 850）。

补强 edges101 未触及的角度（第二百二十四批）。

新角度：
- _resolve_relative_path 直测：根内 dot-dot 归一合法、
  返回绝对路径且 parent 链含 root
- project_root 传 str 也能加载（Path() 包装）
- BOM 开头的清单 → json 解析失败 → ManifestError
  （utf-8 无 BOM 假设的现状锁定）
- 同一 doc categories 含重复 → 条目原样、聚合去重
- ef 条目 source_type 缺省 → None（loader 级）
- ef path 反斜杠 → 字段名 expected_failures[f1].path
- DocumentEntry 恰 10 字段
- forbidden tokens 第三百二十批
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    DocumentEntry,
    ManifestError,
    _resolve_relative_path,
    load_manifest,
)


# ---------- _resolve_relative_path 直测 ----------

def test_resolve_dotdot_inside_root_batch55(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    p = _resolve_relative_path("x/../samples/a.pdf",
                               tmp_path, "f")
    assert p.is_absolute()
    assert p == tmp_path / "samples" / "a.pdf"
    assert tmp_path in p.parents


def test_resolve_rejects_escape_batch55(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a/../../b.pdf", tmp_path, "f")
    assert "位于项目根目录之外" in str(ei.value)


# ---------- str root ----------

def test_str_project_root_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    m = load_manifest(f, str(root))
    assert m.project_root == root
    assert m.documents[0].resolved_path == \
        root / "samples" / "a.pdf"


# ---------- BOM ----------

def test_bom_manifest_rejected_batch55(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    f = tmp_path / "m.json"
    f.write_bytes(b"\xef\xbb\xbf{}")
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, root)
    assert "清单 JSON 解析失败" in str(ei.value)


# ---------- categories 重复 ----------

def test_categories_dup_within_doc_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf",
             "categories": ["x", "x"]}]}),
        encoding="utf-8")
    m = load_manifest(f, root)
    assert m.documents[0].categories == ("x", "x")
    assert m.categories_covered == ["x"]


# ---------- ef 缺省 ----------

def test_ef_source_type_default_none_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "x.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "samples/x.pdf",
             "expected_error_code": "X"}]}),
        encoding="utf-8")
    m = load_manifest(f, root)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].source_type is None
    assert m.expected_failures[0].expected_error_code == "X"


# ---------- ef 反斜杠 ----------

def test_ef_backslash_path_error_batch55(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "samples\\x.pdf",
             "expected_error_code": "X"}]}),
        encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, root)
    msg = str(ei.value)
    assert "expected_failures[f1].path" in msg
    assert "禁止反斜杠" in msg


# ---------- 字段数 ----------

def test_document_entry_ten_fields_batch55():
    assert len(dataclasses.fields(DocumentEntry)) == 10


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "resolved = (project_root / path_str).resolve()" in src
    assert "project_root = Path(project_root).resolve()" in src
    assert 'raise ManifestError(f"清单 JSON 解析失败: {e}") from e' in src


# ---------- forbidden tokens 第三百二十批 ----------

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
