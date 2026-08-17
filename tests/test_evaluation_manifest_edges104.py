"""evaluation/manifest.py 第三百零八轮 edges 测试（Round 864）。

补强 edges103 未触及的角度（第二百三十九批，probe 实证）。

新角度：
- manifest_version "0.9" 先被 Schema const 拦下（EvalSchemaError，
  版本不兼容的 ManifestError 分支对合法 Schema 不可达）
- "../../x.pdf" 逃出项目根 → ManifestError「位于项目根目录之外」
- 自指配对 d1→d1：单元素 frozenset → 1 组
- 两文档共指同一目标 d1→d2、d3→d2 → 2 组
- annotation_file 为空串：schema 放行 + falsy 跳过解析 →
  annotation_file_str "" 但 annotation_resolved None
- categories 含 CJK 的排序（"1" < "a" < "中"）
- ExpectedFailure 五字段取值 + project_root 解析后返回
- forbidden tokens 第三百三十四批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest
from evaluation.schema import EvalSchemaError


def _load(tmp_path, docs, name="m.json", efs=(), **over):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    (root / "samples" / "c.pdf").write_bytes(b"x")
    f = tmp_path / name
    payload = {"manifest_version": "1.0",
               "devset_status": "incomplete",
               "documents": docs,
               "expected_failures": list(efs)}
    payload.update(over)
    f.write_text(json.dumps(payload), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


# ---------- 版本不匹配先被 Schema 拦下 ----------

def test_version_mismatch_schema_first_batch62(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "0.9", "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, root)
    assert "'1.0' was expected" in str(ei.value)


# ---------- 逃出项目根 ----------

def test_dotdot_escape_root_batch62(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, [_d("d1", "../../etc/passwd")])
    assert "位于项目根目录之外" in str(ei.value)


# ---------- 自指配对 ----------

def test_self_pairing_one_group_batch62(tmp_path):
    m = _load(tmp_path, [_d("d1", paired_with="d1")])
    assert m.content_group_count == 1
    assert m.file_count == 1


# ---------- 共指同一目标 ----------

def test_shared_pair_target_two_groups_batch62(tmp_path):
    m = _load(tmp_path, [
        _d("d1", paired_with="d2"),
        _d("d2", "samples/b.pdf"),
        _d("d3", "samples/c.pdf", paired_with="d2")])
    assert m.content_group_count == 2
    assert m.file_count == 3


# ---------- 空 annotation_file ----------

def test_empty_annotation_file_skipped_batch62(tmp_path):
    m = _load(tmp_path, [
        _d("d1", annotation_file="")])
    d = m.documents[0]
    assert d.annotation_file_str == ""
    assert d.annotation_resolved is None


# ---------- CJK categories 排序 ----------

def test_categories_unicode_sort_batch62(tmp_path):
    m = _load(tmp_path, [
        _d("d1", categories=["中", "a", "1"])])
    assert m.categories_covered == ["1", "a", "中"]


# ---------- ExpectedFailure 字段 ----------

def test_expected_failure_fields_batch62(tmp_path):
    m = _load(tmp_path, [_d("d1")],
              efs=[{"doc_id": "f1", "path": "samples/b.pdf",
                    "expected_error_code": "E_UNSUPPORTED",
                    "source_type": "txt"}])
    ef = m.expected_failures[0]
    assert list(ef.__dataclass_fields__) == [
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type"]
    assert ef.path_str == "samples/b.pdf"
    assert ef.resolved_path == \
        (tmp_path / "proj" / "samples" / "b.pdf").resolve()
    assert ef.source_type == "txt"


# ---------- project_root 解析后返回 ----------

def test_project_root_resolved_batch62(tmp_path):
    m = _load(tmp_path, [_d("d1")])
    assert m.project_root == (tmp_path / "proj").resolve()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch62():
    src = _src()
    assert 'if data.get("manifest_version") != MANIFEST_VERSION:' in src
    assert "resolved.relative_to(project_root_resolved)" in src
    assert "categories=tuple(d.get(\"categories\", []))" in src


# ---------- forbidden tokens 第三百三十四批 ----------

def test_source_no_eval_batch62():
    assert "eval(" not in _src()


def test_source_no_exec_batch62():
    assert "exec(" not in _src()


def test_source_no_compile_batch62():
    assert "compile(" not in _src()


def test_source_no_globals_batch62():
    assert "globals(" not in _src()


def test_source_no_locals_batch62():
    assert "locals(" not in _src()


def test_source_no_os_system_batch62():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch62():
    assert "subprocess" not in _src()


def test_source_no_popen_batch62():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch62():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch62():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch62():
    assert "socket" not in _src()


def test_source_no_requests_batch62():
    assert "requests" not in _src()


def test_source_no_urllib_batch62():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch62():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch62():
    assert "yield" not in _src()


def test_source_no_async_await_batch62():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch62():
    assert _src().count("open(") == 1
