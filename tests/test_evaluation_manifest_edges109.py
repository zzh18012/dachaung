"""evaluation/manifest.py 第三百四十三轮 edges 测试（Round 899）。

补强 edges108 未触及的角度（第二百七十五批，probe 实证）。

新角度：
- manifest 的 document source_type enum 恰 ["pdf","docx"]（两值，
  与 document.schema.json 的六值不同——跨 Schema 分歧锁定）
- source_type "markdown" → EvalSchemaError "'markdown' is not one
  of ['pdf', 'docx']"
- categories 含 int → "1 is not of type 'string'"
- expectations 字符串 → "'x' is not of type 'object'"
- ef expected_error_code "" → "'' should be non-empty"
- devset_status "done" → enum 报错
- DocumentEntry 缺省：categories () / sha256 None / paired_with
  None / expectations None / annotation_file_str None
- _detect_project_root 向上探测：无 pyproject → 清单目录；
  上级放 pyproject.toml → 上级目录
- forbidden tokens 第三百六十九批
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


def _expect_schema_error(f, root, frag):
    try:
        load_manifest(f, root)
        raise AssertionError("should raise")
    except EvalSchemaError as e:
        assert frag in str(e)


# ---------- source_type 两值 ----------

def test_manifest_doc_source_type_two_only_batch97(tmp_path):
    f, root = _mk(tmp_path, [])
    from evaluation.schema import load_schema
    doc_def = load_schema("manifest.schema.json")["$defs"][
        "document"]
    assert doc_def["properties"]["source_type"]["enum"] == \
        ["pdf", "docx"]


def test_source_type_markdown_rejected_batch97(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                              "source_type": "markdown"}])
    _expect_schema_error(
        f, root, "'markdown' is not one of ['pdf', 'docx']")


# ---------- 类型约束 ----------

def test_categories_int_item_batch97(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                              "source_type": "pdf",
                              "categories": [1]}])
    _expect_schema_error(f, root, "1 is not of type 'string'")


def test_expectations_string_batch97(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                              "source_type": "pdf",
                              "expectations": "x"}])
    _expect_schema_error(f, root, "'x' is not of type 'object'")


def test_ef_empty_code_batch97(tmp_path):
    f, root = _mk(
        tmp_path,
        [{"doc_id": "d1", "path": "samples/a.pdf",
          "source_type": "pdf"}],
        extra={"expected_failures": [
            {"doc_id": "f1", "path": "samples/a.pdf",
             "expected_error_code": ""}]})
    _expect_schema_error(f, root, "'' should be non-empty")


def test_devset_status_done_batch97(tmp_path):
    f, root = _mk(tmp_path, [])
    g = tmp_path / "m2.json"
    g.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "done",
        "documents": []}), encoding="utf-8")
    _expect_schema_error(g, root, "'done' is not one of")


# ---------- DocumentEntry 缺省 ----------

def test_document_defaults_batch97(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                              "source_type": "pdf"}])
    m = load_manifest(f, root)
    d = m.documents[0]
    assert d.categories == ()
    assert d.sha256 is None
    assert d.paired_with is None
    assert d.expectations is None
    assert d.annotation_file_str is None
    assert d.annotation_resolved is None


# ---------- 根目录向上探测 ----------

def test_detect_root_upward_pyproject_batch97(tmp_path):
    sub = tmp_path / "deep" / "sub"
    sub.mkdir(parents=True)
    f = sub / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    m1 = load_manifest(f)
    assert m1.project_root == sub.resolve()  # 无 pyproject → 清单目录
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    m2 = load_manifest(f)
    assert m2.project_root == tmp_path.resolve()  # 向上找到


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch97():
    src = _src()
    assert 'sha256=d.get("sha256")' in src
    assert 'expectations=d.get("expectations")' in src
    assert 'if (parent / "pyproject.toml").is_file():' in src
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src


# ---------- forbidden tokens 第三百六十九批 ----------

def test_source_no_eval_batch97():
    assert "eval(" not in _src()


def test_source_no_exec_batch97():
    assert "exec(" not in _src()


def test_source_no_compile_batch97():
    assert "compile(" not in _src()


def test_source_no_globals_batch97():
    assert "globals(" not in _src()


def test_source_no_locals_batch97():
    assert "locals(" not in _src()


def test_source_no_os_system_batch97():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch97():
    assert "subprocess" not in _src()


def test_source_no_popen_batch97():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch97():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch97():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch97():
    assert "socket" not in _src()


def test_source_no_requests_batch97():
    assert "requests" not in _src()


def test_source_no_urllib_batch97():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch97():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch97():
    assert "yield" not in _src()


def test_source_no_async_await_batch97():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch97():
    assert _src().count("open(") == 1
