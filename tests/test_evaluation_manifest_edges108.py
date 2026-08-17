"""evaluation/manifest.py 第三百三十六轮 edges 测试（Round 892）。

补强 edges107 未触及的角度（第二百六十八批，probe 实证）。

新角度：
- 层级顺序：空 path / 坏 sha256 由 Schema 先拦（EvalSchemaError，
  minLength / pattern ^[0-9a-f]{64}$），到不了 loader
- "C:\\x.pdf" 绝对路径检查先于反斜杠（报"禁止绝对路径"）
- POSIX "/etc/x" 绝对路径、相对反斜杠 "samples\\a.pdf" 各自报错
- annotation_file " "（纯空白）被接受且 annotation_resolved 非 None
- 垃圾 JSON → ManifestError "清单 JSON 解析失败"
- 缺省 project_root → 清单所在目录（向上找不到 pyproject.toml）
- 单向配对 d1→d2（d2 沉默）content_group_count==1（目标被吞并）
- categories 去重排序；devset_status "complete" 透传
- 清单文件不存在 → ManifestError
- forbidden tokens 第三百六十二批
"""

from __future__ import annotations

import inspect
import json

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError
from evaluation.manifest import ManifestError


def _mk(tmp_path, docs, extra=None):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs,
    }
    if extra:
        data.update(extra)
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f, root


# ---------- Schema 层先拦 ----------

def test_empty_path_schema_first_batch90(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "",
                              "source_type": "pdf"}])
    try:
        load_manifest(f, root)
        raise AssertionError("should raise")
    except EvalSchemaError as e:
        assert "should be non-empty" in str(e)


def test_sha256_bad_pattern_schema_first_batch90(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                              "source_type": "pdf", "sha256": "xyz"}])
    try:
        load_manifest(f, root)
        raise AssertionError("should raise")
    except EvalSchemaError as e:
        assert "does not match" in str(e)
        assert "^[0-9a-f]{64}$" in str(e)


# ---------- 路径形式拒绝 ----------

def test_abs_windows_before_backslash_batch90(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "C:\\x.pdf",
                              "source_type": "pdf"}])
    try:
        load_manifest(f, root)
        raise AssertionError("should raise")
    except ManifestError as e:
        assert "禁止绝对路径" in str(e)
        assert "反斜杠" not in str(e)


def test_abs_posix_rejected_batch90(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "/etc/x",
                              "source_type": "pdf"}])
    try:
        load_manifest(f, root)
        raise AssertionError("should raise")
    except ManifestError as e:
        assert "禁止绝对路径" in str(e)


def test_backslash_relative_rejected_batch90(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "samples\\a.pdf",
                              "source_type": "pdf"}])
    try:
        load_manifest(f, root)
        raise AssertionError("should raise")
    except ManifestError as e:
        assert "禁止反斜杠" in str(e)


# ---------- annotation_file 纯空白 ----------

def test_annotation_file_whitespace_accepted_batch90(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                              "source_type": "pdf",
                              "annotation_file": " "}])
    m = load_manifest(f, root)
    d = m.documents[0]
    assert d.annotation_file_str == " "
    assert d.annotation_resolved is not None


# ---------- 垃圾 JSON ----------

def test_garbage_json_manifest_error_batch90(tmp_path):
    _mk(tmp_path, [])
    g = tmp_path / "g.json"
    g.write_text("not json", encoding="utf-8")
    try:
        load_manifest(g, tmp_path)
        raise AssertionError("should raise")
    except ManifestError as e:
        assert "清单 JSON 解析失败" in str(e)


# ---------- 缺省 project_root ----------

def test_default_root_is_manifest_dir_batch90(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}), encoding="utf-8")
    m = load_manifest(f)  # 不传 project_root
    assert m.project_root == tmp_path.resolve()
    assert m.devset_status == "complete"
    assert m.documents[0].resolved_path == \
        (tmp_path / "samples" / "a.pdf").resolve()


# ---------- 单向配对 ----------

def test_one_way_pairing_single_group_batch90(tmp_path):
    f, root = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
         "paired_with": "d2"},
        {"doc_id": "d2", "path": "samples/a.pdf",
         "source_type": "docx"}])
    m = load_manifest(f, root)
    assert m.content_group_count == 1
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1


# ---------- categories 去重 ----------

def test_categories_dedupe_sorted_batch90(tmp_path):
    f, root = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
         "categories": ["b", "a", "a"]},
        {"doc_id": "d2", "path": "samples/a.pdf",
         "source_type": "docx", "categories": ["a", "c"]}])
    m = load_manifest(f, root)
    assert m.categories_covered == ["a", "b", "c"]


# ---------- 清单文件不存在 ----------

def test_missing_manifest_file_batch90(tmp_path):
    try:
        load_manifest(tmp_path / "nope.json", tmp_path)
        raise AssertionError("should raise")
    except ManifestError as e:
        assert "清单文件不存在" in str(e)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch90():
    src = _src()
    assert 'raise ManifestError(f"{field_name} 为空")' in src
    assert "resolved.relative_to(project_root_resolved)" in src
    assert 'categories=tuple(d.get("categories", []))' in src


# ---------- forbidden tokens 第三百六十二批 ----------

def test_source_no_eval_batch90():
    assert "eval(" not in _src()


def test_source_no_exec_batch90():
    assert "exec(" not in _src()


def test_source_no_compile_batch90():
    assert "compile(" not in _src()


def test_source_no_globals_batch90():
    assert "globals(" not in _src()


def test_source_no_locals_batch90():
    assert "locals(" not in _src()


def test_source_no_os_system_batch90():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch90():
    assert "subprocess" not in _src()


def test_source_no_popen_batch90():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch90():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch90():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch90():
    assert "socket" not in _src()


def test_source_no_requests_batch90():
    assert "requests" not in _src()


def test_source_no_urllib_batch90():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch90():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch90():
    assert "yield" not in _src()


def test_source_no_async_await_batch90():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch90():
    assert _src().count("open(") == 1
