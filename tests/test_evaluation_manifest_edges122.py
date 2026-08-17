"""evaluation/manifest.py 第四百三十四轮 edges 测试（Round 990）。

补强 edges121 未触及的角度（第三百六十六批，probe 实证）。

新角度：
- BOM 开头的清单 JSON → json.load 报 "Unexpected UTF-8 BOM"
  → ManifestError "清单 JSON 解析失败: …"（与 runner 对
  BOM 标注静默落 None 形成对照）
- 顶层 JSON 数组 → schema 先拦 "[] is not of type
  'object'"（EvalSchemaError 而非 ManifestError）
- categories ["a", "a"]：条目 tuple 保留重复 ('a', 'a')，
  categories_covered 集合去重 ['a']
- project_root 参数传 str → Path() 化照常
- 路径 "~tilde/x.pdf"：波浪号非 absolute-like → 当普通
  目录名放行（resolved parent "~tilde"）
- forbidden tokens 第四百六十批（open 1）
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


_BASE = {"manifest_version": "1.0",
         "devset_status": "incomplete"}


def _write(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


# ---------- BOM ----------

def test_bom_manifest_rejected_batch188(tmp_path):
    _setup(tmp_path)
    f = tmp_path / "bom.json"
    f.write_bytes(b"\xef\xbb\xbf" +
                  json.dumps(_BASE).encode("utf-8"))
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, tmp_path)
    assert str(ei.value).startswith(
        "清单 JSON 解析失败: Unexpected UTF-8 BOM")


# ---------- 顶层数组 ----------

def test_top_level_array_schema_rejected_batch188(tmp_path):
    _setup(tmp_path)
    f = tmp_path / "arr.json"
    f.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, tmp_path)
    assert ei.value.errors[0]["message"] == \
        "[] is not of type 'object'"


# ---------- categories 重复 ----------

def test_categories_dupes_tuple_vs_covered_batch188(tmp_path):
    _setup(tmp_path)
    f = _write(tmp_path, "m3.json", {**_BASE, "documents": [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf", "categories": ["a", "a"]}]})
    m = load_manifest(f, tmp_path)
    assert m.documents[0].categories == ("a", "a")
    assert m.categories_covered == ["a"]


# ---------- project_root 传 str ----------

def test_project_root_as_str_batch188(tmp_path):
    _setup(tmp_path)
    f = _write(tmp_path, "m4.json", {**_BASE, "documents": [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}]})
    m = load_manifest(f, str(tmp_path))
    assert m.project_root == tmp_path.resolve()


# ---------- 波浪号路径 ----------

def test_tilde_path_loads_batch188(tmp_path):
    _setup(tmp_path)
    f = _write(tmp_path, "m5.json", {**_BASE, "documents": [
        {"doc_id": "d1", "path": "~tilde/x.pdf",
         "source_type": "pdf"}]})
    m = load_manifest(f, tmp_path)
    assert m.documents[0].path_str == "~tilde/x.pdf"
    assert m.documents[0].resolved_path.parent.name == "~tilde"
    assert not m.documents[0].resolved_path.exists()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch188():
    src = _src()
    assert 'raise ManifestError(f"清单 JSON 解析失败: {e}") from e' in src
    assert "p = Path(manifest_path).resolve()" in src
    assert 'raise ManifestError(f"清单文件不存在: {p}")' in src
    assert "project_root = Path(project_root).resolve()" in src


# ---------- forbidden tokens 第四百六十批 ----------

def test_source_no_eval_batch188():
    assert "eval(" not in _src()


def test_source_no_exec_batch188():
    assert "exec(" not in _src()


def test_source_no_compile_batch188():
    assert "compile(" not in _src()


def test_source_no_globals_batch188():
    assert "globals(" not in _src()


def test_source_no_locals_batch188():
    assert "locals(" not in _src()


def test_source_no_os_system_batch188():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch188():
    assert "subprocess" not in _src()


def test_source_no_popen_batch188():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch188():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch188():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch188():
    assert "socket" not in _src()


def test_source_no_requests_batch188():
    assert "requests" not in _src()


def test_source_no_urllib_batch188():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch188():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch188():
    assert "yield" not in _src()


def test_source_no_async_await_batch188():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch188():
    assert _src().count("open(") == 1
