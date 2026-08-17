"""evaluation/manifest.py 第二百八十轮 edges 测试（Round 836）。

补强 edges99 未触及的角度（第二百一十批）。

新角度：
- _is_absolute_like 直测表：/ 前缀、C:\\、C:/、C:x（无斜杠）、
  a:b、ab/c、空串、数字盘符
- _resolve_relative_path 空串直测（绕过 schema 的 minLength）
- _detect_project_root 三态：找到 pyproject / 找不到回起点 /
  传入文件取其父
- load_manifest 默认 root 检测（pyproject 所在目录）
- 垃圾 JSON → ManifestError「清单 JSON 解析失败」
- manifest 路径是目录 → 「清单文件不存在」
- annotation_file / ef.path 逃逸项目根的字段名进错误消息
- DocumentEntry frozen 不可写
- forbidden tokens 第三百零六批
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
    _detect_project_root,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


# ---------- _is_absolute_like 直测 ----------

@pytest.mark.parametrize("s,expected", [
    ("/foo", True),
    ("C:\\foo", True),
    ("C:/foo", True),
    ("C:x", False),
    ("a:b", False),
    ("ab/c", False),
    ("", False),
    ("1:/x", False),
])
def test_is_absolute_like_table_batch55(s, expected):
    assert _is_absolute_like(s) is expected


# ---------- 空串直测 ----------

def test_resolve_empty_string_direct_batch55(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "field")
    assert str(ei.value) == "field 为空"


# ---------- _detect_project_root ----------

def test_detect_root_pyproject_batch55(tmp_path):
    (tmp_path / "pyproject.toml").write_text("{}", encoding="utf-8")
    deep = tmp_path / "a" / "b"
    assert _detect_project_root(deep) == tmp_path


def test_detect_root_fallback_batch55(tmp_path):
    start = tmp_path / "nowhere"
    assert _detect_project_root(start) == start


def test_detect_root_file_start_batch55(tmp_path):
    (tmp_path / "pyproject.toml").write_text("{}", encoding="utf-8")
    f = tmp_path / "m.json"
    f.write_text("{}", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path


# ---------- 默认 root 检测 ----------

def test_load_manifest_default_root_batch55(tmp_path):
    (tmp_path / "pyproject.toml").write_text("{}", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    m = load_manifest(tmp_path / "m.json")
    assert m.project_root == tmp_path
    assert m.documents[0].resolved_path == \
        tmp_path / "samples" / "a.pdf"


# ---------- 垃圾 JSON ----------

def test_garbage_json_manifest_error_batch55(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{{{", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, tmp_path)
    assert "清单 JSON 解析失败" in str(ei.value)


# ---------- 目录当清单 ----------

def test_directory_as_manifest_batch55(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path, tmp_path)
    assert "清单文件不存在" in str(ei.value)


# ---------- annotation / ef 逃逸 ----------

def test_annotation_escape_field_name_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mf(tmp_path, [{
            "doc_id": "d1", "path": "samples/a.pdf",
            "source_type": "pdf",
            "annotation_file": "../esc.json"}]), root)
    msg = str(ei.value)
    assert "documents[d1].annotation_file" in msg
    assert "位于项目根目录之外" in msg


def test_ef_escape_field_name_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mf(tmp_path, [], ef=[{
            "doc_id": "f1", "path": "../outside.pdf",
            "expected_error_code": "X"}]), root)
    msg = str(ei.value)
    assert "expected_failures[f1].path" in msg
    assert "位于项目根目录之外" in msg


# ---------- frozen ----------

def test_document_entry_frozen_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    m = load_manifest(_mf(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}]), root)
    e = m.documents[0]
    assert e.sha256 is None
    assert e.paired_with is None
    assert dataclasses.is_dataclass(e) and e.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.doc_id = "x"  # type: ignore[misc]


# ---------- helper ----------

def _mf(tmp_path, docs, ef=None):
    f = tmp_path / "m.json"
    payload = {"manifest_version": "1.0",
               "devset_status": "incomplete", "documents": docs}
    if ef is not None:
        payload["expected_failures"] = ef
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'if (parent / "pyproject.toml").is_file():' in src
    assert 'raise ManifestError(f"{field_name} 为空")' in src
    assert "清单 JSON 解析失败" in src


# ---------- forbidden tokens 第三百零六批 ----------

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
