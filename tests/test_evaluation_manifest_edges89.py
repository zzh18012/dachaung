"""evaluation/manifest.py 第二百零六轮 edges 测试（Round 759）。

补强 edges85-88 未触及的角度（第一百二十三批）。

新角度：
- 直接构造 Manifest（绕过 schema）：txt source_type 不进 pdf/docx 计数
  但 file_count 照计（3/1/1）
- categories 元组重复项 set 去重（("x","x","y") → ['x','y']）
- project_root 接受 str（内部转 Path 并 resolve）
- doc_id 空白 " d " 原样保留（schema 只查 minLength）
- categories 整数项被 schema 拦（items type string）
- annotation_file 与 path 同文件：annotation_resolved == resolved_path
- 同一 path 两个 doc_id：都加载、resolved 相等、doc_id 去重后仍 2
- ef source_type "other" 透传
- JSON 重复键 "devset_status" 出现两次 → json.load 保最后（complete）
- documents 顺序原样保留（d2 在前）
- "//server/share/x.pdf" → 绝对路径拒（startswith "/"）
- 盘相对 "C:foo.pdf"：_is_absolute_like 不认（无 \ 或 /），Path 拼接
  后 C: 前缀消失 → 落在根内合法（怪现状记录）
- expectations 显式 null 被 schema 拦（type object 不接受 null）
- forbidden tokens 第二百二十九批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import DocumentEntry, Manifest, load_manifest
from evaluation.schema import EvalSchemaError

ROOT = Path(__file__).resolve().parents[1]


def _mf(tmp_path, documents=(), **over) -> Path:
    payload = {"manifest_version": "1.0", "devset_status": "incomplete",
               "documents": list(documents)}
    payload.update(over)
    f = tmp_path / "m.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


def _de(i, st="pdf", cats=()):
    return DocumentEntry(i, f"{i}.pdf", ROOT / f"{i}.pdf", st, None, cats,
                         None, None, None, None)


# ---------- 直接构造 Manifest（绕 schema） ----------

def test_txt_source_not_counted_but_file_is_batch54():
    m = Manifest("1.0", "i", (_de("a"), _de("b", "docx"),
                              _de("c", "txt")), (), ROOT)
    assert (m.file_count, m.pdf_count, m.docx_count) == (3, 1, 1)


def test_categories_tuple_duplicates_dedup_batch54():
    m = Manifest("1.0", "i", (_de("a", cats=("x", "x", "y")),), (), ROOT)
    assert m.categories_covered == ["x", "y"]


# ---------- 输入形态 ----------

def test_str_project_root_accepted_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path), project_root=str(ROOT))
    assert isinstance(man.project_root, Path)
    assert man.project_root == ROOT.resolve()


def test_doc_id_whitespace_preserved_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": " d ", "path": "a.pdf", "source_type": "pdf"}]),
        project_root=ROOT)
    assert man.documents[0].doc_id == " d "


def test_categories_int_item_schema_reject_batch54(tmp_path):
    with pytest.raises(EvalSchemaError):
        load_manifest(_mf(tmp_path, [
            {"doc_id": "d", "path": "a.pdf", "source_type": "pdf",
             "categories": [1]}]), project_root=ROOT)


# ---------- annotation 与 path 关系 ----------

def test_annotation_same_as_path_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": "d", "path": "a.pdf", "source_type": "pdf",
         "annotation_file": "a.pdf"}]), project_root=ROOT)
    e = man.documents[0]
    assert e.annotation_resolved == e.resolved_path


def test_same_path_two_ids_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        {"doc_id": "d2", "path": "a.pdf", "source_type": "pdf"}]),
        project_root=ROOT)
    assert man.documents[0].resolved_path == man.documents[1].resolved_path
    assert len({d.doc_id for d in man.documents}) == 2


# ---------- ef source_type ----------

def test_ef_source_type_other_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, expected_failures=[
        {"doc_id": "e", "path": "x.bin", "expected_error_code": "c",
         "source_type": "other"}]), project_root=ROOT)
    assert man.expected_failures[0].source_type == "other"


# ---------- JSON 语义 ----------

def test_duplicate_json_keys_last_wins_batch54(tmp_path):
    f = tmp_path / "dup.json"
    f.write_text(
        '{"manifest_version": "1.0", "devset_status": "incomplete",'
        ' "devset_status": "complete", "documents": []}',
        encoding="utf-8")
    assert load_manifest(f, project_root=ROOT).devset_status == "complete"


def test_document_order_preserved_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}]),
        project_root=ROOT)
    assert [d.doc_id for d in man.documents] == ["d2", "d1"]


# ---------- 路径怪形 ----------

def test_unc_like_double_slash_rejected_batch54(tmp_path):
    with pytest.raises(manifest_mod.ManifestError) as mi:
        load_manifest(_mf(tmp_path, [
            {"doc_id": "d", "path": "//server/share/x.pdf",
             "source_type": "pdf"}]), project_root=ROOT)
    assert str(mi.value).startswith(
        "documents[d].path 必须是相对路径，禁止绝对路径：//server/share/x.pdf")


def test_drive_relative_path_loads_without_prefix_batch54(tmp_path):
    # "C:foo.pdf" 无 \ 或 / → 不算绝对；Path 拼接时 C: 前缀消失 → 根内
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": "d", "path": "C:foo.pdf", "source_type": "pdf"}]),
        project_root=ROOT)
    assert man.documents[0].resolved_path == (ROOT / "foo.pdf").resolve()


# ---------- expectations null ----------

def test_expectations_null_schema_reject_batch54(tmp_path):
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mf(tmp_path, [
            {"doc_id": "d", "path": "a.pdf", "source_type": "pdf",
             "expectations": None}]), project_root=ROOT)
    assert "None is not of type 'object'" in str(ei.value)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_counting_lines_batch54():
    src = _src()
    assert 'd.source_type == "pdf"' in src
    assert 'd.source_type == "docx"' in src
    assert "s.update(d.categories)" in src


# ---------- forbidden tokens 第二百二十九批 ----------

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
