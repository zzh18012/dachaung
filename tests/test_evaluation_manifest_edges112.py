"""evaluation/manifest.py 第三百六十四轮 edges 测试（Round 920）。

补强 edges111 未触及的角度（第二百九十六批，probe 实证）。

新角度：
- _resolve_relative_path 直调：空串 → ManifestError "f 为空"
  （字段名原样透传；schema 的 minLength 只在 load_manifest
  路径上先行拦截）；"./a.pdf" 与 "x/../a.pdf" 归一后落在根内
  → 放行
- annotation_file 指向不存在文件 → manifest 照常加载，
  annotation_resolved.exists() False（存在性推迟到 runner
  的 _load_annotation）
- DocumentEntry / Manifest 均冻结：赋值 →
  dataclasses.FrozenInstanceError
- expected_failures source_type 默认 None / 透传 "pdf"
- 重复 doc_id 双条目均加载（无唯一性校验）
- project_root 指向不存在目录 → resolve 非严格，照常解析
- 缺 expected_failures 键 → 空元组
- categories_covered 每次调用新建 list（非缓存，is not 成立）
- forbidden tokens 第三百九十批
"""

from __future__ import annotations

import dataclasses
import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest
from evaluation.manifest import _resolve_relative_path


def _mk(tmp_path, docs, efs=None, omit_efs=False):
    (tmp_path / "samples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    d = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": docs}
    if efs is not None:
        d["expected_failures"] = efs
    f = tmp_path / "m.json"
    f.write_text(json.dumps(d), encoding="utf-8")
    return f


# ---------- _resolve_relative_path 直调 ----------

def test_resolve_empty_string_direct_batch118(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "f")
    assert str(ei.value) == "f 为空"


def test_resolve_dot_paths_accepted_batch118(tmp_path):
    for p in ("./a.pdf", "x/../a.pdf"):
        out = _resolve_relative_path(p, tmp_path, "f")
        assert out == (tmp_path / "a.pdf").resolve()


# ---------- ghost annotation ----------

def test_ghost_annotation_accepted_batch118(tmp_path):
    f = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "annotation_file": "ghost.json"}])
    m = load_manifest(f, tmp_path)
    ann = m.documents[0].annotation_resolved
    assert ann == (tmp_path / "ghost.json").resolve()
    assert ann.exists() is False


# ---------- 冻结 dataclass ----------

def test_document_entry_frozen_batch118(tmp_path):
    m = load_manifest(_mk(tmp_path, [{"doc_id": "d1",
                                      "path": "samples/a.pdf",
                                      "source_type": "pdf"}]),
                      tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.documents[0].doc_id = "x"


def test_manifest_frozen_batch118(tmp_path):
    m = load_manifest(_mk(tmp_path, []), tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.devset_status = "x"


# ---------- expected_failures source_type ----------

def test_ef_source_type_default_and_passthrough_batch118(tmp_path):
    f = _mk(tmp_path, [], efs=[
        {"doc_id": "f1", "path": "samples/a.pdf",
         "expected_error_code": "E"},
        {"doc_id": "f2", "path": "samples/a.pdf",
         "expected_error_code": "E", "source_type": "pdf"},
    ])
    m = load_manifest(f, tmp_path)
    assert [ef.source_type for ef in m.expected_failures] == [
        None, "pdf"]


# ---------- 重复 doc_id ----------

def test_duplicate_doc_ids_both_loaded_batch118(tmp_path):
    f = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"},
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "docx"},
    ])
    m = load_manifest(f, tmp_path)
    assert [(d.doc_id, d.source_type) for d in m.documents] == [
        ("d1", "pdf"), ("d1", "docx")]
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1


# ---------- 不存在的 project_root ----------

def test_nonexistent_project_root_accepted_batch118(tmp_path):
    f = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    m = load_manifest(f, tmp_path / "nothere")
    assert m.project_root == (tmp_path / "nothere").resolve()
    assert m.documents[0].resolved_path == (
        (tmp_path / "nothere" / "samples" / "a.pdf").resolve())


# ---------- 缺 expected_failures 键 ----------

def test_missing_ef_key_empty_tuple_batch118(tmp_path):
    m = load_manifest(_mk(tmp_path, []), tmp_path)
    assert m.expected_failures == ()


# ---------- categories_covered 非缓存 ----------

def test_categories_covered_new_list_each_call_batch118(tmp_path):
    m = load_manifest(_mk(tmp_path, []), tmp_path)
    assert m.categories_covered is not m.categories_covered
    assert m.categories_covered == []


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch118():
    src = _src()
    assert "@dataclass(frozen=True)" in src
    assert "resolved = (project_root / path_str).resolve()" in src
    assert "categories=tuple(d.get(\"categories\", []))," in src
    assert 'return sorted(s)' in src


# ---------- forbidden tokens 第三百九十批 ----------

def test_source_no_eval_batch118():
    assert "eval(" not in _src()


def test_source_no_exec_batch118():
    assert "exec(" not in _src()


def test_source_no_compile_batch118():
    assert "compile(" not in _src()


def test_source_no_globals_batch118():
    assert "globals(" not in _src()


def test_source_no_locals_batch118():
    assert "locals(" not in _src()


def test_source_no_os_system_batch118():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch118():
    assert "subprocess" not in _src()


def test_source_no_popen_batch118():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch118():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch118():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch118():
    assert "socket" not in _src()


def test_source_no_requests_batch118():
    assert "requests" not in _src()


def test_source_no_urllib_batch118():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch118():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch118():
    assert "yield" not in _src()


def test_source_no_async_await_batch118():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch118():
    assert _src().count("open(") == 1
