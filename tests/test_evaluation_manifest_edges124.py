"""evaluation/manifest.py 第四百四十八轮 edges 测试（Round 1004）。

补强 edges123 未触及的角度（第三百八十批，probe 实证）。

新角度：
- ef 条目 UNC 路径 "//server/x.pdf" → ManifestError
  "expected_failures[e1].path 必须是相对路径…"（ef 侧
  的字段名带索引形式锁定）
- 文件路径尾斜杠 "samples/a.pdf/" 照常加载：path_str 原
  样保留、resolved name 归一 "a.pdf"（resolve 剥离尾斜杠）
- ef doc_id 含中文 "中文ef" 照常加载（无 pattern 约束）
- sha256 短串 "abc" → EvalSchemaError pattern 拒绝
- annotation_file 含中文 "samples/标注.json" 照常解析
- forbidden tokens 第四百七十四批（open 1）
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest, ManifestError
from evaluation.schema import EvalSchemaError


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")


def _load(tmp_path, docs=None, ef=None):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs if docs is not None else [],
        "expected_failures": ef or []}), encoding="utf-8")
    return load_manifest(f, tmp_path)


# ---------- ef UNC ----------

def test_ef_unc_path_rejected_batch202(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, ef=[{"doc_id": "e1",
                             "path": "//server/x.pdf",
                             "expected_error_code": "E_X"}])
    assert str(ei.value).startswith(
        "expected_failures[e1].path 必须是相对路径，"
        "禁止绝对路径：//server/x.pdf")


# ---------- 文件尾斜杠 ----------

def test_trailing_slash_file_loads_batch202(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, docs=[{
        "doc_id": "d1", "path": "samples/a.pdf/",
        "source_type": "pdf"}])
    assert m.documents[0].path_str == "samples/a.pdf/"
    assert m.documents[0].resolved_path.name == "a.pdf"
    assert m.documents[0].resolved_path.is_file()


# ---------- unicode ef doc_id ----------

def test_unicode_ef_doc_id_loads_batch202(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, ef=[{
        "doc_id": "中文ef", "path": "samples/a.pdf",
        "expected_error_code": "E_X"}])
    assert m.expected_failures[0].doc_id == "中文ef"


# ---------- 短 sha256 ----------

def test_short_sha256_schema_rejected_batch202(tmp_path):
    _setup(tmp_path)
    with pytest.raises(EvalSchemaError) as ei:
        _load(tmp_path, docs=[{
            "doc_id": "d1", "path": "samples/a.pdf",
            "source_type": "pdf", "sha256": "abc"}])
    assert ei.value.errors[0]["message"].startswith(
        "'abc' does not match")


# ---------- 中文 annotation_file ----------

def test_unicode_annotation_file_loads_batch202(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, docs=[{
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf",
        "annotation_file": "samples/标注.json"}])
    assert m.documents[0].annotation_resolved.name == "标注.json"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch202():
    src = _src()
    assert 'f"documents[{d[\'doc_id\']}].path"' in src
    assert 'f"expected_failures[{ef[\'doc_id\']}].path"' in src
    assert 'f"{field_name} 必须是相对路径，禁止绝对路径：{path_str}"' in src


# ---------- forbidden tokens 第四百七十四批 ----------

def test_source_no_eval_batch202():
    assert "eval(" not in _src()


def test_source_no_exec_batch202():
    assert "exec(" not in _src()


def test_source_no_compile_batch202():
    assert "compile(" not in _src()


def test_source_no_globals_batch202():
    assert "globals(" not in _src()


def test_source_no_locals_batch202():
    assert "locals(" not in _src()


def test_source_no_os_system_batch202():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch202():
    assert "subprocess" not in _src()


def test_source_no_popen_batch202():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch202():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch202():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch202():
    assert "socket" not in _src()


def test_source_no_requests_batch202():
    assert "requests" not in _src()


def test_source_no_urllib_batch202():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch202():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch202():
    assert "yield" not in _src()


def test_source_no_async_await_batch202():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch202():
    assert _src().count("open(") == 1
