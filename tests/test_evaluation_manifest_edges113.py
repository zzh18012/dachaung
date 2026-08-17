"""evaluation/manifest.py 第三百七十一轮 edges 测试（Round 927）。

补强 edges112 未触及的角度（第三百零三批，probe 实证）。

新角度：
- annotation_file 反斜杠 → ManifestError
  documents[d1].annotation_file 禁止反斜杠；
  "../x.json" 逃逸根 → 位于项目根目录之外
- expected_failures 绝对路径 → 字段名
  expected_failures[f1].path 禁止绝对路径
- DocumentEntry.path_str 原样保留 "./samples/a.pdf"
  （raw 保存），resolved 才归一；categories 元组保留重复
  ("a", "a")（去重只在 categories_covered）
- 两次加载同一清单 → dataclass 相等但非同一对象
  （Manifest 与 DocumentEntry 均值语义）
- manifest_version 写 JSON 数字 1.0 → EvalSchemaError
  "2 处"（type + const 双报）
- 顶层 JSON 数组 → EvalSchemaError "is not of type
  'object'"（json.load 成功、schema 拦截）
- forbidden tokens 第三百九十七批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest
from evaluation.schema import EvalSchemaError


BS = chr(92)


def _mkf(tmp_path, data):
    (tmp_path / "samples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


_BASE = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": []}


# ---------- annotation_file 形式校验 ----------

def test_annotation_backslash_rejected_batch125(tmp_path):
    d = dict(_BASE, documents=[{
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf",
        "annotation_file": "ann" + BS + "x.json"}])
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mkf(tmp_path, d), tmp_path)
    msg = str(ei.value)
    assert msg.startswith("documents[d1].annotation_file ")
    assert "必须使用正斜杠，禁止反斜杠" in msg


def test_annotation_escape_rejected_batch125(tmp_path):
    d = dict(_BASE, documents=[{
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf",
        "annotation_file": "../x.json"}])
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mkf(tmp_path, d), tmp_path)
    msg = str(ei.value)
    assert msg.startswith("documents[d1].annotation_file ")
    assert "解析后位于项目根目录之外" in msg


# ---------- ef 绝对路径 ----------

def test_ef_absolute_rejected_batch125(tmp_path):
    d = dict(_BASE, expected_failures=[{
        "doc_id": "f1", "path": "/abs/x.pdf",
        "expected_error_code": "E"}])
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mkf(tmp_path, d), tmp_path)
    msg = str(ei.value)
    assert msg.startswith("expected_failures[f1].path ")
    assert "必须是相对路径，禁止绝对路径：/abs/x.pdf" in msg


# ---------- raw 保留与重复 categories ----------

def test_path_str_raw_preserved_batch125(tmp_path):
    d = dict(_BASE, documents=[{
        "doc_id": "d1", "path": "./samples/a.pdf",
        "source_type": "pdf", "categories": ["a", "a"]}])
    m = load_manifest(_mkf(tmp_path, d), tmp_path)
    entry = m.documents[0]
    assert entry.path_str == "./samples/a.pdf"  # raw 原样
    assert entry.categories == ("a", "a")  # 元组不去重
    assert m.categories_covered == ["a"]  # 汇总才去重


# ---------- dataclass 值相等 ----------

def test_two_loads_equal_not_identical_batch125(tmp_path):
    d = dict(_BASE, documents=[{
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf"}])
    f = _mkf(tmp_path, d)
    m1 = load_manifest(f, tmp_path)
    m2 = load_manifest(f, tmp_path)
    assert m1 == m2
    assert m1 is not m2
    assert m1.documents[0] == m2.documents[0]


# ---------- manifest_version 数字 ----------

def test_version_json_number_rejected_batch125(tmp_path):
    d = dict(_BASE, manifest_version=1.0)
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mkf(tmp_path, d), tmp_path)
    msg = str(ei.value)
    assert "(2 处)" in msg
    assert "1.0 is not of type 'string'" in msg


# ---------- 顶层数组 ----------

def test_top_level_array_rejected_batch125(tmp_path):
    f = tmp_path / "m.json"
    f.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, tmp_path)
    assert "[1, 2] is not of type 'object'" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch125():
    src = _src()
    assert "path_str: str  # 原始相对路径（正斜杠）" in src
    assert "annotation_resolved = _resolve_relative_path(" in src
    assert 'categories=tuple(d.get("categories", [])),' in src


# ---------- forbidden tokens 第三百九十七批 ----------

def test_source_no_eval_batch125():
    assert "eval(" not in _src()


def test_source_no_exec_batch125():
    assert "exec(" not in _src()


def test_source_no_compile_batch125():
    assert "compile(" not in _src()


def test_source_no_globals_batch125():
    assert "globals(" not in _src()


def test_source_no_locals_batch125():
    assert "locals(" not in _src()


def test_source_no_os_system_batch125():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch125():
    assert "subprocess" not in _src()


def test_source_no_popen_batch125():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch125():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch125():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch125():
    assert "socket" not in _src()


def test_source_no_requests_batch125():
    assert "requests" not in _src()


def test_source_no_urllib_batch125():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch125():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch125():
    assert "yield" not in _src()


def test_source_no_async_await_batch125():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch125():
    assert _src().count("open(") == 1
