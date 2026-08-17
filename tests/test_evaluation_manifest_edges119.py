"""evaluation/manifest.py 第四百一十三轮 edges 测试（Round 969）。

补强 edges118 未触及的角度（第三百三十五批，probe 实证）。

新角度：
- 加载不检查文件存在：documents 指向 ghost.pdf 照常
  载入（存在性留给 runner/ef 阶段）
- DocumentEntry 是 frozen dataclass：赋值抛
  FrozenInstanceError
- Manifest 层面属性赋值同样抛（frozen 全层）
- sha256 非法格式 "xyz" → schema 正则先拦：
  "'xyz' does not match '^[0-9a-f]{64}$' @
  path=['documents', 0, 'sha256']"
- forbidden tokens 第四百三十九批（open 1）
"""

from __future__ import annotations

import dataclasses
import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")


def _manifest(tmp_path, name, doc):
    f = tmp_path / name
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [doc]}), encoding="utf-8")
    return load_manifest(f, tmp_path)


# ---------- ghost 路径照常载入 ----------

def test_ghost_path_loads_batch167(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m.json", {
        "doc_id": "d1", "path": "samples/ghost.pdf",
        "source_type": "pdf"})
    assert m.file_count == 1
    assert m.documents[0].resolved_path.name == "ghost.pdf"
    assert not m.documents[0].resolved_path.exists()


# ---------- 条目 frozen ----------

def test_document_entry_frozen_batch167(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m2.json", {
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf"})
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.documents[0].doc_id = "x"


# ---------- Manifest 层 frozen ----------

def test_manifest_attribute_frozen_batch167(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m3.json", {
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf"})
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.expected_failures = ()


# ---------- sha256 正则 ----------

def test_bad_sha256_schema_regex_batch167(tmp_path):
    _setup(tmp_path)
    f = tmp_path / "m4.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/a.pdf",
                       "source_type": "pdf",
                       "sha256": "xyz"}]}),
        encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, tmp_path)
    msg = str(ei.value)
    assert "'xyz' does not match '^[0-9a-f]{64}$'" in msg
    assert "@ path=['documents', 0, 'sha256']" in msg


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch167():
    src = _src()
    assert "sha256=d.get(\"sha256\")," in src
    assert "expectations=d.get(\"expectations\")," in src
    assert "categories=tuple(d.get(\"categories\", []))," in src


# ---------- forbidden tokens 第四百三十九批 ----------

def test_source_no_eval_batch167():
    assert "eval(" not in _src()


def test_source_no_exec_batch167():
    assert "exec(" not in _src()


def test_source_no_compile_batch167():
    assert "compile(" not in _src()


def test_source_no_globals_batch167():
    assert "globals(" not in _src()


def test_source_no_locals_batch167():
    assert "locals(" not in _src()


def test_source_no_os_system_batch167():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch167():
    assert "subprocess" not in _src()


def test_source_no_popen_batch167():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch167():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch167():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch167():
    assert "socket" not in _src()


def test_source_no_requests_batch167():
    assert "requests" not in _src()


def test_source_no_urllib_batch167():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch167():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch167():
    assert "yield" not in _src()


def test_source_no_async_await_batch167():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch167():
    assert _src().count("open(") == 1
