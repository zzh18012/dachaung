"""evaluation/manifest.py 第二百零五轮 edges 测试（Round 752）。

补强 edges85-87 未触及的角度（第一百一十七批）。

新角度：
- 字段级错误消息定位：annotation_file 绝对路径 / ef path 绝对路径 /
  反斜杠 / 越根，四条消息都带 documents[d1].xxx / expected_failures[e1].path
  前缀（用 chr(92) 构造反斜杠，避开 shell/JSON 转义）
- documents 键缺失 → schema "'documents' is a required property"
  （data.get 默认值 [] 在 load_manifest 路径不可达）；
  expected_failures 键缺失 → ()（.get 默认可达）
- content_group_count 组合：d1↔d2 + d1→d3 = 2 组（frozenset 去重后
  两个集合）；双向对 + 孤儿 = 2；两对不相交 = 2
- 冒号怪路径 "a:b.pdf"：_is_absolute_like 不认（[2] 非 \/），但
  Path resolve 后仍在根外 → 越根错误（resolved 打印为相对原样）
- dataclasses.fields：DocumentEntry 10 / ExpectedFailure 5 / Manifest 5
- ExpectedFailure 可哈希（frozen、无 dict 字段）：hash 相等 + == 相等
- _detect_project_root 兜底：临时目录向上无 pyproject.toml → 返回
  manifest 所在目录
- categories_covered unicode 排序去重 ['α','β','γ']
- ef source_type "txt" 原样透传
- forbidden tokens 第二百二十二批
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    DocumentEntry,
    ExpectedFailure,
    Manifest,
    _detect_project_root,
    _is_absolute_like,
    load_manifest,
)
from evaluation.schema import EvalSchemaError

ROOT = Path(__file__).resolve().parents[1]
BS = chr(92)


def _mf(tmp_path, documents=(), **over) -> Path:
    payload = {"manifest_version": "1.0", "devset_status": "incomplete",
               "documents": list(documents)}
    payload.update(over)
    f = tmp_path / "m.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


# ---------- 字段级错误消息 ----------

def test_annotation_file_absolute_message_batch54(tmp_path):
    f = _mf(tmp_path, documents=[{
        "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
        "annotation_file": "C:/x/a.json"}])
    with pytest.raises(manifest_mod.ManifestError) as mi:
        load_manifest(f, project_root=ROOT)
    assert str(mi.value).startswith(
        "documents[d1].annotation_file 必须是相对路径，禁止绝对路径："
        "C:/x/a.json")


def test_ef_path_absolute_message_batch54(tmp_path):
    f = _mf(tmp_path, expected_failures=[
        {"doc_id": "e1", "path": "/abs/x.txt", "expected_error_code": "c"}])
    with pytest.raises(manifest_mod.ManifestError) as mi:
        load_manifest(f, project_root=ROOT)
    assert str(mi.value).startswith(
        "expected_failures[e1].path 必须是相对路径，禁止绝对路径："
        "/abs/x.txt")


def test_backslash_message_batch54(tmp_path):
    f = _mf(tmp_path, documents=[{
        "doc_id": "d1", "path": "a" + BS + "b.pdf", "source_type": "pdf"}])
    with pytest.raises(manifest_mod.ManifestError) as mi:
        load_manifest(f, project_root=ROOT)
    assert str(mi.value).startswith(
        "documents[d1].path 必须使用正斜杠，禁止反斜杠：a" + BS + "b.pdf")


def test_escape_root_message_batch54(tmp_path):
    f = _mf(tmp_path, documents=[{
        "doc_id": "d1", "path": "../a.pdf", "source_type": "pdf"}])
    with pytest.raises(manifest_mod.ManifestError) as mi:
        load_manifest(f, project_root=ROOT)
    assert str(mi.value).startswith(
        "documents[d1].path 解析后位于项目根目录之外：../a.pdf")


# ---------- 键缺失 ----------

def test_documents_key_missing_schema_error_batch54(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": "incomplete"}),
                 encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, project_root=ROOT)
    assert "'documents' is a required property" in str(ei.value)


def test_expected_failures_key_missing_empty_tuple_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path), project_root=ROOT)
    assert man.expected_failures == ()


# ---------- content_group_count 组合 ----------

def _de(i, pw=None):
    return DocumentEntry(i, f"{i}.pdf", ROOT / f"{i}.pdf", "pdf", None, (),
                         pw, None, None, None)


def _man(*docs):
    return Manifest("1.0", "incomplete", docs, (), ROOT)


def test_group_fanout_two_groups_batch54():
    # d1↔d2 与 d1→d3 两个 frozenset → 2 组
    assert _man(_de("d1", "d2"), _de("d2", "d1"),
                _de("d3", "d1")).content_group_count == 2


def test_group_bidir_pair_plus_lone_batch54():
    assert _man(_de("d1", "d2"), _de("d2", "d1"),
                _de("d4")).content_group_count == 2


def test_group_two_disjoint_pairs_batch54():
    assert _man(_de("a1", "a2"), _de("a2", "a1"),
                _de("b1", "b2"), _de("b2", "b1")).content_group_count == 2


# ---------- 冒号怪路径 ----------

def test_colon_path_not_absolute_like_batch54():
    assert _is_absolute_like("a:b.pdf") is False


def test_colon_path_rejected_outside_root_batch54(tmp_path):
    f = _mf(tmp_path, documents=[{
        "doc_id": "d1", "path": "a:b.pdf", "source_type": "pdf"}])
    with pytest.raises(manifest_mod.ManifestError) as mi:
        load_manifest(f, project_root=ROOT)
    assert "位于项目根目录之外" in str(mi.value)


# ---------- dataclass 结构 ----------

def test_dataclass_field_counts_batch54():
    assert len(dataclasses.fields(DocumentEntry)) == 10
    assert len(dataclasses.fields(ExpectedFailure)) == 5
    assert len(dataclasses.fields(Manifest)) == 5


def test_expected_failure_hashable_batch54():
    e1 = ExpectedFailure("e", "e.pdf", ROOT / "e.pdf", "c", None)
    e2 = ExpectedFailure("e", "e.pdf", ROOT / "e.pdf", "c", None)
    assert e1 == e2
    assert hash(e1) == hash(e2)
    assert {e1: 1}[e2] == 1


# ---------- detect root 兜底 ----------

def test_detect_root_fallback_existing_file_batch54():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "m.json").write_text("{}", encoding="utf-8")
    # 临时目录树向上无 pyproject.toml → 返回 manifest 所在目录
    assert _detect_project_root(tmp / "m.json") == tmp.resolve()


def test_detect_root_nonexistent_start_returned_as_is_batch54():
    # start 不存在 → is_file() False → 不切 parent，原样返回
    tmp = Path(tempfile.mkdtemp())
    assert _detect_project_root(tmp / "m.json") == (tmp / "m.json").resolve()


# ---------- categories unicode ----------

def test_categories_unicode_sorted_dedup_batch54():
    docs = (DocumentEntry("d1", "d1.pdf", ROOT / "d1.pdf", "pdf", None,
                          ("β", "α"), None, None, None, None),
            DocumentEntry("d2", "d2.pdf", ROOT / "d2.pdf", "pdf", None,
                          ("α", "γ"), None, None, None, None))
    assert _man(*docs).categories_covered == ["α", "β", "γ"]


# ---------- ef source_type 透传 ----------

def test_ef_source_type_txt_passthrough_batch54(tmp_path):
    f = _mf(tmp_path, expected_failures=[
        {"doc_id": "e1", "path": "x.txt", "expected_error_code": "c",
         "source_type": "txt"}])
    man = load_manifest(f, project_root=ROOT)
    assert man.expected_failures[0].source_type == "txt"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_get_defaults_batch54():
    src = _src()
    assert 'data.get("documents", [])' in src
    assert 'data.get("expected_failures", [])' in src


def test_source_frozenset_pair_batch54():
    assert "frozenset([d.doc_id, d.paired_with])" in _src()


# ---------- forbidden tokens 第二百二十二批 ----------

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
