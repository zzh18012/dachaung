"""evaluation/manifest.py 第二百一十轮 edges 测试（Round 766）。

补强 edges87-89 未触及的角度（第一百三十批）。

新角度：
- sha256 pattern 双拒：64 个大写 A（大小写敏感）、63 个 a（长度不足）
- expectations 精确结构：required_markers 空串（minLength 1）、
  element_count_by_type 负数（minimum 0）、1.5（integer 拒 float）、
  未知键（addProps false）
- documents source_type "txt" 拒（enum 只允许 pdf/docx —— ef 四值
  对照 documents 两值）
- devset_status 传 int 3 → enum 拒
- content_group_count 拓扑：ghost 引用（不在 documents 的 paired_with
  仍成组 1）、自引用 singleton frozenset → 1、a→b b→c 链 → 2 组、
  a↔b 互指 → frozenset 去重 → 1 组
- 直接构造 Manifest 含 txt source_type → file_count 1 / pdf 0 / docx 0
- BOM 清单 → ManifestError "清单 JSON 解析失败" +
  "Unexpected UTF-8 BOM"（open 用 utf-8 非 utf-8-sig，现状记录）
- frozen 双向：setattr → FrozenInstanceError；dataclasses.replace 可用
- annotation_file 越根 → 错误消息带 documents[d1].annotation_file 字段名
- 直接 _resolve_relative_path("") → "f 为空"（schema minLength 1 使
  load_manifest 路径不可达此分支，仅直接调用可达）
- annotation_file 子目录内 → 解析到 samples/sub/ann.json
- ef 反斜杠 → expected_failures[f1].path 字段名
- forbidden tokens 第二百三十六批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import (
    DocumentEntry,
    Manifest,
    ManifestError,
    _resolve_relative_path,
    load_manifest,
)
from evaluation.schema import EvalSchemaError


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples" / "sub").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _doc(**kw):
    base = {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf"}
    base.update(kw)
    return base


# ---------- sha256 pattern ----------

def test_sha256_uppercase_rejected_batch54(env):
    tmp, root = env
    f = tmp / "m.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": "incomplete",
                             "documents": [_doc(sha256="A" * 64)]}),
                 encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "does not match" in str(ei.value)


def test_sha256_short_rejected_batch54(env):
    tmp, root = env
    f = tmp / "m.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": "incomplete",
                             "documents": [_doc(sha256="a" * 63)]}),
                 encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(f, root)


# ---------- expectations 精确结构 ----------

def _write(tmp, doc):
    f = tmp / "m.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": "incomplete",
                             "documents": [doc]}), encoding="utf-8")
    return f


def test_marker_empty_string_rejected_batch54(env):
    tmp, root = env
    f = _write(tmp, _doc(expectations={"required_markers": [""]}))
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "should be non-empty" in str(ei.value)


def test_count_negative_rejected_batch54(env):
    tmp, root = env
    f = _write(tmp, _doc(expectations={"element_count_by_type":
                                       {"paragraph": -1}}))
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "less than the minimum of 0" in str(ei.value)


def test_count_float_rejected_batch54(env):
    tmp, root = env
    f = _write(tmp, _doc(expectations={"element_count_by_type":
                                       {"paragraph": 1.5}}))
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "is not of type 'integer'" in str(ei.value)


def test_expectations_unknown_key_rejected_batch54(env):
    tmp, root = env
    f = _write(tmp, _doc(expectations={"bogus": 1}))
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "Additional properties are not allowed" in str(ei.value)


# ---------- enum 对照 ----------

def test_documents_txt_source_rejected_batch54(env):
    tmp, root = env
    f = _write(tmp, _doc(source_type="txt"))
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "'txt' is not one of ['pdf', 'docx']" in str(ei.value)


def test_devset_status_int_rejected_batch54(env):
    tmp, root = env
    f = tmp / "m.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": 3,
                             "documents": [_doc()]}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(f, root)


# ---------- content_group_count 拓扑 ----------

def _dm(root, *docs):
    return Manifest("1.0", "incomplete", tuple(docs), (), root)


def _de(root, did, pair=None):
    return DocumentEntry(did, "samples/a.pdf", root / "samples/a.pdf",
                         "pdf", None, (), pair, None, None, None)


def test_ghost_paired_with_still_groups_batch54(env):
    _, root = env
    assert _dm(root, _de(root, "a", "ghost")).content_group_count == 1


def test_self_pair_singleton_group_batch54(env):
    _, root = env
    assert _dm(root, _de(root, "a", "a")).content_group_count == 1


def test_chain_pairs_two_groups_batch54(env):
    _, root = env
    m = _dm(root, _de(root, "a", "b"), _de(root, "b", "c"))
    assert m.content_group_count == 2


def test_mutual_pair_dedupes_to_one_batch54(env):
    _, root = env
    m = _dm(root, _de(root, "a", "b"), _de(root, "b", "a"))
    assert m.content_group_count == 1


def test_direct_manifest_txt_counts_batch54(env):
    _, root = env
    t = DocumentEntry("t", "s/t.txt", root / "s/t.txt", "txt", None, (),
                      None, None, None, None)
    m = _dm(root, t)
    assert (m.file_count, m.pdf_count, m.docx_count) == (1, 0, 0)


# ---------- BOM ----------

def test_bom_manifest_json_decode_error_batch54(env):
    tmp, root = env
    bf = tmp / "bom.json"
    bf.write_bytes(b"\xef\xbb\xbf" + json.dumps(
        {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": []}).encode())
    with pytest.raises(ManifestError) as ei:
        load_manifest(bf, root)
    assert "清单 JSON 解析失败" in str(ei.value)
    assert "Unexpected UTF-8 BOM" in str(ei.value)


# ---------- frozen ----------

def test_document_entry_frozen_batch54(env):
    _, root = env
    d = _de(root, "a")
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"
    assert replace(d, doc_id="x").doc_id == "x"


# ---------- annotation_file ----------

def test_annotation_outside_root_field_name_batch54(env):
    tmp, root = env
    (root.parent / "outside.ann").write_text("{}")
    f = _write(tmp, _doc(annotation_file="../../outside.ann"))
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, root)
    assert "documents[d1].annotation_file 解析后位于项目根目录之外" \
        in str(ei.value)


def test_annotation_subdirectory_resolves_batch54(env):
    tmp, root = env
    (root / "samples" / "sub" / "ann.json").write_text("{}")
    m = load_manifest(_write(tmp, _doc(
        annotation_file="samples/sub/ann.json")), root)
    assert m.documents[0].annotation_resolved == \
        root / "samples" / "sub" / "ann.json"


# ---------- 直接调用 _resolve_relative_path ----------

def test_empty_path_direct_raises_batch54(env):
    _, root = env
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", root, "f")
    assert str(ei.value) == "f 为空"


# ---------- ef 反斜杠字段名 ----------

def test_ef_backslash_field_name_batch54(env):
    tmp, root = env
    f = tmp / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [_doc()],
        "expected_failures": [{"doc_id": "f1", "path": "samples\\b.pdf",
                               "expected_error_code": "c"}]}),
        encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, root)
    assert "expected_failures[f1].path 必须使用正斜杠" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_group_logic_batch54():
    src = _src()
    assert "frozenset([d.doc_id, d.paired_with])" in src
    assert 'f"{field_name} 为空"' in src
    assert 'encoding="utf-8"' in src
    assert "utf-8-sig" not in src


# ---------- forbidden tokens 第二百三十六批 ----------

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
