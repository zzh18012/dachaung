"""evaluation/manifest.py 第三百九十二轮 edges 测试（Round 948）。

补强 edges115 未触及的角度（第三百二十四批，probe 实证）。

新角度：
- 空 documents 合法：file/content_group/categories/pdf/docx
  全空零值
- 自配对 paired_with=自身 → frozenset([d,d])={d} →
  1 文档算 1 组
- 单向配对 A→B（B 无 paired_with）→ B 被 pair 吸收 →
  2 文档仍 1 组
- 重复 doc_id schema 不查重 → file_count 2
- path 空串被 schema minLength 先拦（"should be non-empty
  @ path=['documents', 0, 'path']"），轮不到
  _resolve_relative_path 的 "为空" 分支
- annotation_file 反斜杠 → 字段名含 doc_id：
  "documents[d1].annotation_file 必须使用正斜杠…"
- manifest_version "0.9" 被 schema const 先拦（"'1.0' was
  expected"），不兼容分支不可达
- categories_covered 跨文档并集排序；条目 categories 保留
  原始元组序；sha256/paired_with/annotation_file_str 默认
  None
- devset_status "complete" 合法
- expected_failures 无 source_type → None 默认
- forbidden tokens 第四百一十八批
"""

from __future__ import annotations

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
    (tmp_path / "samples" / "b.pdf").write_bytes(b"x")


def _mk(tmp_path, docs, extra=None, ver="1.0"):
    data = {"manifest_version": ver, "devset_status": "incomplete",
            "documents": docs}
    if extra:
        data.update(extra)
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


# ---------- 空 documents ----------

def test_empty_documents_all_zero_batch146(tmp_path):
    _setup(tmp_path)
    m = load_manifest(_mk(tmp_path, []), tmp_path)
    assert m.file_count == 0
    assert m.content_group_count == 0
    assert m.categories_covered == []
    assert m.pdf_count == 0
    assert m.docx_count == 0


# ---------- 配对语义 ----------

def test_self_pairing_one_group_batch146(tmp_path):
    _setup(tmp_path)
    m = load_manifest(_mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf", "paired_with": "d1"}]), tmp_path)
    assert m.file_count == 1
    assert m.content_group_count == 1


def test_one_way_pair_absorbs_batch146(tmp_path):
    _setup(tmp_path)
    m = load_manifest(_mk(tmp_path, [
        {"doc_id": "A", "path": "samples/a.pdf",
         "source_type": "pdf", "paired_with": "B"},
        {"doc_id": "B", "path": "samples/b.pdf",
         "source_type": "pdf"}]), tmp_path)
    assert m.file_count == 2
    assert m.content_group_count == 1


# ---------- 重复 doc_id ----------

def test_duplicate_doc_id_allowed_batch146(tmp_path):
    _setup(tmp_path)
    m = load_manifest(_mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"},
        {"doc_id": "d1", "path": "samples/b.pdf",
         "source_type": "pdf"}]), tmp_path)
    assert m.file_count == 2


# ---------- 空串 path：schema 先拦 ----------

def test_empty_path_schema_first_batch146(tmp_path):
    _setup(tmp_path)
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, [
            {"doc_id": "d1", "path": "", "source_type": "pdf"}]),
            tmp_path)
    msg = str(ei.value)
    assert "'' should be non-empty" in msg
    assert "@ path=['documents', 0, 'path']" in msg


# ---------- annotation_file 反斜杠 ----------

def test_annotation_backslash_field_name_batch146(tmp_path):
    _setup(tmp_path)
    with pytest.raises(manifest_mod.ManifestError) as ei:
        load_manifest(_mk(tmp_path, [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf",
             "annotation_file": "ann\\x.json"}]), tmp_path)
    msg = str(ei.value)
    assert msg.startswith(
        "documents[d1].annotation_file 必须使用正斜杠，禁止反斜杠：")
    assert msg.endswith("ann\\x.json")


# ---------- version 不匹配：schema const 先拦 ----------

def test_version_mismatch_schema_const_batch146(tmp_path):
    _setup(tmp_path)
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf"}], ver="0.9"), tmp_path)
    assert "'1.0' was expected @ path=['manifest_version']" in \
        str(ei.value)


# ---------- 条目字段默认 ----------

def test_entry_defaults_and_categories_batch146(tmp_path):
    _setup(tmp_path)
    m = load_manifest(_mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf", "categories": ["z", "a"]},
        {"doc_id": "d2", "path": "samples/b.pdf",
         "source_type": "pdf", "categories": ["a", "m"]}]),
        tmp_path)
    d1 = m.documents[0]
    assert d1.categories == ("z", "a")
    assert d1.sha256 is None
    assert d1.paired_with is None
    assert d1.annotation_file_str is None
    assert d1.annotation_resolved is None
    assert m.categories_covered == ["a", "m", "z"]


# ---------- devset_status complete ----------

def test_devset_status_complete_batch146(tmp_path):
    _setup(tmp_path)
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}), encoding="utf-8")
    m = load_manifest(f, tmp_path)
    assert m.devset_status == "complete"


# ---------- expected_failures 默认 ----------

def test_ef_source_type_none_default_batch146(tmp_path):
    _setup(tmp_path)
    f = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}],
        extra={"expected_failures": [{
            "doc_id": "ef1", "path": "samples/b.pdf",
            "expected_error_code": "E_PARSE"}]})
    m = load_manifest(f, tmp_path)
    ef = m.expected_failures[0]
    assert ef.doc_id == "ef1"
    assert ef.source_type is None
    assert ef.expected_error_code == "E_PARSE"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch146():
    src = _src()
    assert 'if not path_str:' in src
    assert 'pair_ids.add(frozenset([d.doc_id, d.paired_with]))' in src
    assert 'seen.update(pair)' in src
    assert 'if (parent / "pyproject.toml").is_file():' in src


# ---------- forbidden tokens 第四百一十八批 ----------

def test_source_no_eval_batch146():
    assert "eval(" not in _src()


def test_source_no_exec_batch146():
    assert "exec(" not in _src()


def test_source_no_compile_batch146():
    assert "compile(" not in _src()


def test_source_no_globals_batch146():
    assert "globals(" not in _src()


def test_source_no_locals_batch146():
    assert "locals(" not in _src()


def test_source_no_os_system_batch146():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch146():
    assert "subprocess" not in _src()


def test_source_no_popen_batch146():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch146():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch146():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch146():
    assert "socket" not in _src()


def test_source_no_requests_batch146():
    assert "requests" not in _src()


def test_source_no_urllib_batch146():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch146():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch146():
    assert "yield" not in _src()


def test_source_no_async_await_batch146():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch146():
    assert _src().count("open(") == 1
