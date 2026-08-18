"""evaluation/manifest.py 第五百六十轮 edges 测试（Round 1207）。

补强 edges139 未触及的角度（第五百七十九批，probe 实证）。

新角度（doc_id 形式自由 / 派生键输入回拒）：
- **doc_id 含空格斜杠照收**——doc_id
  "a b/c"（空格 + 斜杠）→ schema 仅
  minLength 约束，load_manifest 照常
  加载（doc_id 形式自由首锁；路径的
  反斜杠禁令不外溢到 doc_id）
- **派生键输入回拒**——清单里写
  categories_covered（loader 的派生
  字段）→ schema 顶层封闭回拒
  "Additional properties are not
  allowed"——派生键只能算不能喂
  （首锁）
- **source_type 必填**——documents
  条目缺 source_type → "'source_type'
  is a required property"（documents
  必填已锁，条目内字段必填首锁）
- **source_type 枚举**——'txt' →
  "'txt' is not one of ['pdf',
  'docx']"
- forbidden tokens 第六百七十七批（open 1）
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError


def _mk(tmp_path, docs, name="m.json"):
    mf = tmp_path / name
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": docs}), encoding="utf-8")
    return mf


# ---------- doc_id 形式自由 ----------

def test_doc_id_space_slash_batch405(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "x.pdf").write_bytes(b"fake")
    m = load_manifest(_mk(tmp_path, [
        {"doc_id": "a b/c", "path": "samples/x.pdf",
         "source_type": "pdf"}]), project_root=tmp_path)
    assert m.file_count == 1
    assert [d.doc_id for d in m.documents] == ["a b/c"]


# ---------- 派生键输入回拒 ----------

def test_derived_key_input_rejected_batch405(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "x.pdf").write_bytes(b"fake")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "categories_covered": ["catA"],
        "documents": [{"doc_id": "d", "path": "samples/x.pdf",
                       "source_type": "pdf"}]}), encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(mf, project_root=tmp_path)
    assert ("'categories_covered' was unexpected"
            in str(ei.value)) or (
        "Additional properties are not allowed" in str(ei.value)
        and "categories_covered" in str(ei.value))


# ---------- source_type 必填 / 枚举 ----------

def test_source_type_required_batch405(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "x.pdf").write_bytes(b"fake")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, [
            {"doc_id": "d", "path": "samples/x.pdf"}]),
            project_root=tmp_path)
    assert "'source_type' is a required property" in str(ei.value)


def test_source_type_enum_batch405(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "x.pdf").write_bytes(b"fake")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, [
            {"doc_id": "d", "path": "samples/x.pdf",
             "source_type": "txt"}]), project_root=tmp_path)
    assert "'txt' is not one of ['pdf', 'docx']" in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch405():
    src = _src()
    assert "配对的 DOCX+PDF" in src
    assert "resolved_path: Path  # 解析后的绝对路径" in src


# ---------- forbidden tokens 第六百七十七批 ----------

def test_source_no_eval_batch405():
    assert "eval(" not in _src()


def test_source_no_exec_batch405():
    assert "exec(" not in _src()


def test_source_no_compile_batch405():
    assert "compile(" not in _src()


def test_source_no_globals_batch405():
    assert "globals(" not in _src()


def test_source_no_locals_batch405():
    assert "locals(" not in _src()


def test_source_no_os_system_batch405():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch405():
    assert "subprocess" not in _src()


def test_source_no_popen_batch405():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch405():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch405():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch405():
    assert "socket" not in _src()


def test_source_no_requests_batch405():
    assert "requests" not in _src()


def test_source_no_urllib_batch405():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch405():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch405():
    assert "yield" not in _src()


def test_source_no_async_await_batch405():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch405():
    assert _src().count("open(") == 1
