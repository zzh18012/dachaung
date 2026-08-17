"""evaluation/manifest.py 第四百六十九轮 edges 测试（Round 1025）。

补强 edges126 未触及的角度（第四百零一批，probe 实证）。

新角度（ef source_type 语义）：
- ef 条目带 source_type "pdf" → 全部计数无视之：
  pdf_count 0 / docx_count 1 / file_count 1（计数只看
  documents 段；edges102 只锁过缺省 None）
- ef source_type enum 比 documents 宽：["pdf","docx",
  "txt","other"]——"txt" 合法加载；"video" enum 拒
  （"is not one of"）
- forbidden tokens 第四百九十五批（open 1）
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest
from evaluation.schema import EvalSchemaError


def _setup(tmp_path, docs, efs):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "b.docx").write_bytes(b"x")
    (tmp_path / "samples" / "x.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": efs}), encoding="utf-8")
    return load_manifest(mf, tmp_path)


# ---------- ef source_type 不进计数 ----------

def test_ef_source_type_not_counted_batch223(tmp_path):
    m = _setup(
        tmp_path,
        [{"doc_id": "d1", "path": "samples/b.docx",
          "source_type": "docx"}],
        [{"doc_id": "f1", "path": "samples/x.pdf",
          "expected_error_code": "E_X",
          "source_type": "pdf"}])
    assert m.expected_failures[0].source_type == "pdf"
    assert m.pdf_count == 0
    assert m.docx_count == 1
    assert m.file_count == 1


# ---------- ef source_type enum 宽于 documents ----------

def test_ef_source_type_enum_batch223(tmp_path):
    m = _setup(
        tmp_path, [],
        [{"doc_id": "f1", "path": "samples/x.pdf",
          "expected_error_code": "E_X",
          "source_type": "txt"}])
    assert m.expected_failures[0].source_type == "txt"

    with pytest.raises(EvalSchemaError,
                       match="is not one of"):
        _setup(
            tmp_path, [],
            [{"doc_id": "f1", "path": "samples/x.pdf",
              "expected_error_code": "E_X",
              "source_type": "video"}])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch223():
    src = _src()
    assert ("return sum(1 for d in self.documents"
            ' if d.source_type == "pdf")') in src
    assert "source_type=ef.get(\"source_type\")," in src
    assert "if d.paired_with:" in src


# ---------- forbidden tokens 第四百九十五批 ----------

def test_source_no_eval_batch223():
    assert "eval(" not in _src()


def test_source_no_exec_batch223():
    assert "exec(" not in _src()


def test_source_no_compile_batch223():
    assert "compile(" not in _src()


def test_source_no_globals_batch223():
    assert "globals(" not in _src()


def test_source_no_locals_batch223():
    assert "locals(" not in _src()


def test_source_no_os_system_batch223():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch223():
    assert "subprocess" not in _src()


def test_source_no_popen_batch223():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch223():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch223():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch223():
    assert "socket" not in _src()


def test_source_no_requests_batch223():
    assert "requests" not in _src()


def test_source_no_urllib_batch223():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch223():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch223():
    assert "yield" not in _src()


def test_source_no_async_await_batch223():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch223():
    assert _src().count("open(") == 1
