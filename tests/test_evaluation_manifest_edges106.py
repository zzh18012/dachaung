"""evaluation/manifest.py 第三百二十二轮 edges 测试（Round 878）。

补强 edges105 未触及的角度（第二百五十三批）。

新角度：
- paired_with ""：falsy → 视为未配对（1 组）
- 文档 path 指向目录 / ef path 指向不存在文件：
  loader 不做存在性检查，照常加载（现状锁定）
- Manifest 本体 frozen（赋值抛 FrozenInstanceError）
- MANIFEST_VERSION 常量锁定 "1.0"
- CJK 子目录路径 "样例/a.pdf" 照常解析
- forbidden tokens 第三百四十八批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest


def _load(tmp_path, docs, efs=()):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": list(efs)}), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


# ---------- paired_with 空串 ----------

def test_empty_paired_with_treated_unpaired_batch76(tmp_path):
    m = _load(tmp_path, [_d("d1", paired_with="")])
    assert m.documents[0].paired_with == ""
    assert m.content_group_count == 1


# ---------- 存在性不检查 ----------

def test_doc_path_directory_accepted_batch76(tmp_path):
    m = _load(tmp_path, [_d("d1", path="samples")])
    assert m.documents[0].resolved_path.is_dir()
    assert m.file_count == 1


def test_ef_path_nonexistent_accepted_batch76(tmp_path):
    m = _load(tmp_path, [_d("d1")],
              efs=[{"doc_id": "f1",
                    "path": "samples/ghost.pdf",
                    "expected_error_code": "E"}])
    ef = m.expected_failures[0]
    assert not ef.resolved_path.exists()
    assert ef.resolved_path.name == "ghost.pdf"


# ---------- Manifest frozen ----------

def test_manifest_frozen_batch76(tmp_path):
    m = _load(tmp_path, [_d("d1")])
    with pytest.raises(Exception) as ei:
        m.devset_status = "complete"
    assert type(ei.value).__name__ == "FrozenInstanceError"


# ---------- 版本常量 ----------

def test_manifest_version_constant_batch76():
    assert manifest_mod.MANIFEST_VERSION == "1.0"


# ---------- CJK 子目录 ----------

def test_cjk_subdir_path_batch76(tmp_path):
    root = tmp_path / "proj"
    (root / "样例").mkdir(parents=True, exist_ok=True)
    (root / "样例" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "样例/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    m = load_manifest(f, root)
    assert m.documents[0].path_str == "样例/a.pdf"
    assert m.documents[0].resolved_path == \
        (root / "样例" / "a.pdf").resolve()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch76():
    src = _src()
    assert "if d.paired_with:" in src
    assert "class ManifestError(Exception):" in src
    assert "@dataclass(frozen=True)" in src


# ---------- forbidden tokens 第三百四十八批 ----------

def test_source_no_eval_batch76():
    assert "eval(" not in _src()


def test_source_no_exec_batch76():
    assert "exec(" not in _src()


def test_source_no_compile_batch76():
    assert "compile(" not in _src()


def test_source_no_globals_batch76():
    assert "globals(" not in _src()


def test_source_no_locals_batch76():
    assert "locals(" not in _src()


def test_source_no_os_system_batch76():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch76():
    assert "subprocess" not in _src()


def test_source_no_popen_batch76():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch76():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch76():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch76():
    assert "socket" not in _src()


def test_source_no_requests_batch76():
    assert "requests" not in _src()


def test_source_no_urllib_batch76():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch76():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch76():
    assert "yield" not in _src()


def test_source_no_async_await_batch76():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch76():
    assert _src().count("open(") == 1
