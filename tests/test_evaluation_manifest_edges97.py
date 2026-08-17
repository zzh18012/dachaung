"""evaluation/manifest.py 第二百五十九轮 edges 测试（Round 815）。

补强 edges96 未触及的角度（第一百七十九批）。

新角度：
- 反斜杠路径 → ManifestError "必须使用正斜杠，禁止反斜杠"
  （字段名 documents[d1].path）
- 越根路径 ../outside.pdf → ManifestError "解析后位于项目根
  目录之外"（消息含原始串与解析结果）
- "samples/./a.pdf" → resolve 归一后合法，resolved_path.name
  == "a.pdf"
- 不存在的文档文件照常加载（manifest 只查自身存在性，文档
  存在性留给 runner / process_single）
- ef 条目与 document 同 doc_id "d1"：互不校验、双双加载
- 顶层额外键 → EvalSchemaError（additionalProperties false）
- manifest_version "2.0" → **EvalSchemaError 先于** 兼容性
  ManifestError（schema const 只放行 "1.0"，代码侧
  manifest_version != MANIFEST_VERSION 检查对错版本值实际
  不可达 —— 现状记录）
- forbidden tokens 第二百八十五批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import ManifestError, load_manifest
from evaluation.schema import EvalSchemaError


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


def _write(tmp, name, docs, **extra):
    obj = {"manifest_version": "1.0",
           "devset_status": "incomplete", "documents": docs}
    obj.update(extra)
    f = tmp / name
    f.write_text(json.dumps(obj), encoding="utf-8")
    return f


# ---------- 反斜杠 ----------

def test_backslash_rejected_batch55(env):
    tmp, root = env
    f = _write(tmp, "m.json", [_d("d1", "samples\\a.pdf")])
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, root)
    assert ("documents[d1].path 必须使用正斜杠，禁止反斜杠："
            "samples\\a.pdf") in str(ei.value)


# ---------- 越根 ----------

def test_escape_outside_root_rejected_batch55(env):
    tmp, root = env
    f = _write(tmp, "m.json", [_d("d1", "../outside.pdf")])
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, root)
    assert ("documents[d1].path 解析后位于项目根目录之外："
            "../outside.pdf") in str(ei.value)


# ---------- ./ 归一 ----------

def test_dot_slash_normalized_valid_batch55(env):
    tmp, root = env
    f = _write(tmp, "m.json", [_d("d1", "samples/./a.pdf")])
    m = load_manifest(f, root)
    assert m.documents[0].resolved_path.name == "a.pdf"
    assert m.documents[0].path_str == "samples/./a.pdf"


# ---------- 不存在的文档文件 ----------

def test_nonexistent_doc_file_loads_batch55(env):
    tmp, root = env
    f = _write(tmp, "m.json", [_d("d1", "samples/ghost.pdf")])
    m = load_manifest(f, root)
    assert m.documents[0].path_str == "samples/ghost.pdf"


# ---------- ef/doc_id 冲突 ----------

def test_ef_doc_id_collision_both_load_batch55(env):
    tmp, root = env
    f = _write(tmp, "m.json", [_d("d1")],
               expected_failures=[
                   {"doc_id": "d1", "path": "samples/a.pdf",
                    "expected_error_code": "X"}])
    m = load_manifest(f, root)
    assert m.file_count == 1
    assert len(m.expected_failures) == 1


# ---------- 顶层额外键 ----------

def test_top_level_extra_key_rejected_batch55(env):
    tmp, root = env
    f = _write(tmp, "m.json", [_d("d1")], zzz=1)
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "Additional properties" in str(ei.value)


# ---------- manifest_version 顺序 ----------

def test_version_mismatch_schema_first_batch55(env):
    tmp, root = env
    f = _write(tmp, "m.json", [_d("d1")], manifest_version="2.0")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "'1.0' was expected" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'f"{field_name} 必须使用正斜杠，禁止反斜杠：{path_str}"' in src
    assert 'f"{field_name} 解析后位于项目根目录之外：{path_str} → {resolved}"' in src
    assert 'if data.get("manifest_version") != MANIFEST_VERSION:' in src


# ---------- forbidden tokens 第二百八十五批 ----------

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
