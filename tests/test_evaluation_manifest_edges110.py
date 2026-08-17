"""evaluation/manifest.py 第三百五十轮 edges 测试（Round 906）。

补强 edges109 未触及的角度（第二百八十二批，probe 实证）。

新角度：
- BOM 头的 UTF-8 清单 → ManifestError "清单 JSON 解析失败"
  （Unexpected UTF-8 BOM）
- 大写 sha256 "A"×64 → EvalSchemaError 不匹配 ^[0-9a-f]{64}$
- 互指配对 d1↔d2 → content_group_count==1（frozenset 去重）
- project_root 传 str 被接受（Path() 归一）
- expectations 深层透传进 DocumentEntry；
  categories 转成 tuple
- forbidden tokens 第三百七十六批
"""

from __future__ import annotations

import inspect
import json

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError
from evaluation.manifest import ManifestError


def _mk(tmp_path, docs):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    return f, root


# ---------- BOM ----------

def test_bom_manifest_rejected_batch104(tmp_path):
    _mk(tmp_path, [])
    f = tmp_path / "bom.json"
    payload = json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": []}).encode("utf-8")
    f.write_bytes(b"\xef\xbb\xbf" + payload)
    try:
        load_manifest(f, tmp_path)
        raise AssertionError("should raise")
    except ManifestError as e:
        assert "清单 JSON 解析失败" in str(e)
        assert "BOM" in str(e)


# ---------- 大写 sha256 ----------

def test_uppercase_sha256_rejected_batch104(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1",
                              "path": "samples/a.pdf",
                              "source_type": "pdf",
                              "sha256": "A" * 64}])
    try:
        load_manifest(f, root)
        raise AssertionError("should raise")
    except EvalSchemaError as e:
        assert "does not match" in str(e)


# ---------- 互指配对 ----------

def test_mutual_pairing_single_group_batch104(tmp_path):
    f, root = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf", "paired_with": "d2"},
        {"doc_id": "d2", "path": "samples/a.pdf",
         "source_type": "docx", "paired_with": "d1"}])
    m = load_manifest(f, root)
    assert m.content_group_count == 1
    assert m.pdf_count == 1
    assert m.docx_count == 1


# ---------- str project_root ----------

def test_str_project_root_accepted_batch104(tmp_path):
    f, root = _mk(tmp_path, [{"doc_id": "d1",
                              "path": "samples/a.pdf",
                              "source_type": "pdf"}])
    m = load_manifest(f, str(root))
    assert m.project_root == root.resolve()


# ---------- expectations / categories ----------

def test_expectations_deep_passthrough_batch104(tmp_path):
    f, root = _mk(tmp_path, [{
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf",
        "expectations": {"element_count_by_type":
                         {"paragraph": 3, "heading": 2}},
        "categories": ["x", "y"]}])
    m = load_manifest(f, root)
    assert m.documents[0].expectations == {
        "element_count_by_type": {"paragraph": 3, "heading": 2}}
    assert m.documents[0].categories == ("x", "y")
    assert isinstance(m.documents[0].categories, tuple)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch104():
    src = _src()
    assert "project_root = Path(project_root).resolve()" in src
    assert "if data.get(\"manifest_version\") != MANIFEST_VERSION:" in src
    assert "return sorted(s)" in src


# ---------- forbidden tokens 第三百七十六批 ----------

def test_source_no_eval_batch104():
    assert "eval(" not in _src()


def test_source_no_exec_batch104():
    assert "exec(" not in _src()


def test_source_no_compile_batch104():
    assert "compile(" not in _src()


def test_source_no_globals_batch104():
    assert "globals(" not in _src()


def test_source_no_locals_batch104():
    assert "locals(" not in _src()


def test_source_no_os_system_batch104():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch104():
    assert "subprocess" not in _src()


def test_source_no_popen_batch104():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch104():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch104():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch104():
    assert "socket" not in _src()


def test_source_no_requests_batch104():
    assert "requests" not in _src()


def test_source_no_urllib_batch104():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch104():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch104():
    assert "yield" not in _src()


def test_source_no_async_await_batch104():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch104():
    assert _src().count("open(") == 1
