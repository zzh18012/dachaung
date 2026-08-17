"""evaluation/manifest.py 第二百四十五轮 edges 测试（Round 801）。

补强 edges94 未触及的角度（第一百六十五批）。

新角度：
- sha256 64 位小写 hex 正例：原样存入 entry（与 R766 的拒绝
  家族对照）
- 跨类型互配对：pdf p1 ↔ docx x1 → content_group_count 1
  （同一内容来源的核心用例）、pdf 1 / docx 1、devset_status
  "complete" 放行
- project_root 传文件路径：不校验是否目录 → project_root 就是
  该文件、resolved_path 词法拼到文件之下（荒谬但无错，现状
  记录 —— 调用方自律）
- forbidden tokens 第二百七十一批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import load_manifest


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "a.docx").write_bytes(b"x")
    return tmp, root


def _write(tmp, obj, name="m.json"):
    f = tmp / name
    f.write_text(json.dumps(obj), encoding="utf-8")
    return f


# ---------- sha256 正例 ----------

def test_sha256_valid_hex_stored_batch54(env):
    tmp, root = env
    m = load_manifest(_write(tmp, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf",
                       "sha256": "a" * 64}]}), root)
    assert m.documents[0].sha256 == "a" * 64


# ---------- 跨类型互配对 ----------

def test_cross_type_mutual_pair_one_group_batch54(env):
    tmp, root = env
    m = load_manifest(_write(tmp, {
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [
            {"doc_id": "p1", "path": "samples/a.pdf",
             "source_type": "pdf", "paired_with": "x1"},
            {"doc_id": "x1", "path": "samples/a.docx",
             "source_type": "docx", "paired_with": "p1"}]},
        "m2.json"), root)
    assert m.content_group_count == 1
    assert (m.pdf_count, m.docx_count) == (1, 1)
    assert m.devset_status == "complete"


# ---------- project_root 传文件 ----------

def test_project_root_as_file_lexical_batch54(env):
    tmp, root = env
    the_file = root / "samples" / "a.pdf"
    m = load_manifest(_write(tmp, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}, "m3.json"),
        the_file)
    assert m.project_root == the_file.resolve()
    assert m.documents[0].resolved_path == \
        the_file.resolve() / "samples" / "a.pdf"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_no_dir_check_batch54():
    src = _src()
    assert "project_root.is_dir()" not in src
    assert "sha256=d.get(\"sha256\")" in src
    assert 'd.get("paired_with")' in src


# ---------- forbidden tokens 第二百七十一批 ----------

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
