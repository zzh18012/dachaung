"""evaluation/manifest.py 第二百二十四轮 edges 测试（Round 780）。

补强 edges87-91 未触及的角度（第一百四十四批）。

新角度：
- manifest_version "2.0" → schema const 先拒（"'1.0' was expected"
  @ path ['manifest_version']）；load_manifest 里的版本对比分支
  （!= MANIFEST_VERSION）经 load_manifest 不可达 —— schema const
  锁死，与 "为空" 分支同一家族
- project_root 传相对 Path "proj" → Path().resolve() 落到 cwd 下
  并绝对化
- resolved_path 恒绝对路径
- paired_with "" schema 放行（type string 无 minLength）但 falsy
  → content_group_count 按未配对计 1（空串配对引用被静默忽略，
  现状记录）
- 重复 doc_id 两条目并存（schema 不查唯一）：file_count 2、
  pdf/docx 各 1、两对象不同
- _resolve_relative_path 对不存在的 root 也能词法解析
  （resolve 非严格模式；relative_to 两侧同为词法结果 → 通过）
- forbidden tokens 第二百五十批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import (
    ManifestError,
    _resolve_relative_path,
    load_manifest,
)
from evaluation.schema import EvalSchemaError


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _write(tmp, name, obj):
    f = tmp / name
    f.write_text(json.dumps(obj), encoding="utf-8")
    return f


def _doc(**kw):
    base = {"doc_id": "d1", "path": "samples/a.pdf",
            "source_type": "pdf"}
    base.update(kw)
    return base


# ---------- 版本 const 先拒 ----------

def test_version_two_schema_const_intercept_batch54(env):
    tmp, root = env
    mf = _write(tmp, "m.json", {"manifest_version": "2.0",
                                "devset_status": "incomplete",
                                "documents": []})
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(mf, root)
    assert "'1.0' was expected" in str(ei.value)
    row = ei.value.errors[0]
    assert row["path"] == ["manifest_version"]


# ---------- 相对 root 与绝对性 ----------

def test_relative_project_root_resolved_batch54(env, monkeypatch):
    tmp, root = env
    monkeypatch.chdir(tmp)
    mf = _write(tmp, "m.json", {"manifest_version": "1.0",
                                "devset_status": "incomplete",
                                "documents": [_doc()]})
    m = load_manifest(mf, "proj")
    assert m.project_root == root
    assert m.project_root.is_absolute()


def test_resolved_path_always_absolute_batch54(env):
    tmp, root = env
    mf = _write(tmp, "m.json", {"manifest_version": "1.0",
                                "devset_status": "incomplete",
                                "documents": [_doc()]})
    m = load_manifest(mf, root)
    assert m.documents[0].resolved_path.is_absolute()


# ---------- paired_with 空串 ----------

def test_empty_paired_with_ignored_batch54(env):
    tmp, root = env
    mf = _write(tmp, "m.json", {"manifest_version": "1.0",
                                "devset_status": "incomplete",
                                "documents": [_doc(paired_with="")]})
    m = load_manifest(mf, root)
    assert m.documents[0].paired_with == ""
    assert m.content_group_count == 1


# ---------- 重复 doc_id ----------

def test_duplicate_doc_id_both_kept_batch54(env):
    tmp, root = env
    mf = _write(tmp, "m.json", {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "same", "path": "samples/a.pdf",
             "source_type": "pdf"},
            {"doc_id": "same", "path": "samples/a.pdf",
             "source_type": "docx"},
        ]})
    m = load_manifest(mf, root)
    assert m.file_count == 2
    assert (m.pdf_count, m.docx_count) == (1, 1)
    assert m.documents[0] is not m.documents[1]


# ---------- 不存在的 root ----------

def test_resolve_with_nonexistent_root_batch54(env):
    tmp, _ = env
    ghost = tmp / "noexist" / "proj"
    p = _resolve_relative_path("samples/a.pdf", ghost, "f")
    assert p == ghost.resolve() / "samples" / "a.pdf"
    assert p.relative_to(ghost.resolve()) == Path("samples") / "a.pdf"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_version_check_unreachable_via_schema_batch54():
    src = _src()
    assert 'data.get("manifest_version") != MANIFEST_VERSION' in src
    assert "project_root = Path(project_root).resolve()" in src


# ---------- forbidden tokens 第二百五十批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
