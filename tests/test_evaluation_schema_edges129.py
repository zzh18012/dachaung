"""evaluation/schema.py 第五百五十三轮 edges 测试（Round 1109）。

补强 edges128 未触及的角度（第四百八十五批，probe 实证）。

新角度（element/chunk 闭包 / 根开放分歧 / 闭包地图）：
- **element 裸键拒绝**：elements[0] 塞 bogus_key →
  "Additional properties are not allowed ('bogus_key' was
  unexpected) @ path=['elements', 0]"——element def
  additionalProperties False（裸键首锁）
- **chunk 裸键拒绝**：chunks[0] 塞 bogus_key → 同消息 @
  path=['chunks', 0]——chunk def 同样闭包
- **根开放分歧**：文档根塞 bogus_root → 照过——根对象
  无 additionalProperties（开放），element/chunk def 闭包：
  同一个"多塞键"动作在根被收、在 def 被拒（根-def 分歧
  首锁）
- **闭包地图**：loaded document.schema.json 六 def
  （element/chunk/error/warning/relation/source_span）全部
  additionalProperties False、根无此键——闭包纪律全景
- forbidden tokens 第五百八十一批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import pathlib
import tempfile

from docx import Document

import evaluation.schema as schema_mod
from app.pipeline import process_single
from evaluation.schema import (
    EvalSchemaError, load_schema, validate)


def _real_doc(tmp_path):
    p = tmp_path / "a.docx"
    d = Document()
    d.add_paragraph("AAA first paragraph body.")
    d.save(str(p))
    doc, errors = process_single(
        p, tmp_path / "s.json", parser_name="fallback",
        max_chars=200, write_json=False)
    assert errors == []
    return doc.to_dict()


def _expect_reject(tmp_path, mut, path):
    r = copy.deepcopy(_real_doc(tmp_path))
    mut(r)
    try:
        validate(r, "document.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert "Additional properties are not allowed" in str(e)
        assert "'bogus_key' was unexpected" in str(e)
        assert f"path={path}" in str(e)
    assert raised


# ---------- element 裸键拒绝 ----------

def test_element_extra_key_rejected_batch308(tmp_path):
    _expect_reject(
        tmp_path,
        lambda r: r["elements"][0].__setitem__(
            "bogus_key", 1),
        "['elements', 0]")


# ---------- chunk 裸键拒绝 ----------

def test_chunk_extra_key_rejected_batch308(tmp_path):
    _expect_reject(
        tmp_path,
        lambda r: r["chunks"][0].__setitem__(
            "bogus_key", 1),
        "['chunks', 0]")


# ---------- 根开放分歧 ----------

def test_root_extra_key_accepted_batch308(tmp_path):
    r = copy.deepcopy(_real_doc(tmp_path))
    r["bogus_root"] = 1
    validate(r, "document.schema.json")


# ---------- 闭包地图 ----------

def test_closure_map_batch308():
    s = load_schema("document.schema.json")
    assert "additionalProperties" not in s
    for name in ("element", "chunk", "error", "warning",
                 "relation", "source_span"):
        assert s["$defs"][name]["additionalProperties"] is False


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch308():
    src = _src()
    assert "Draft202012Validator(schema)" in src
    assert "list(err.absolute_path)" in src


# ---------- forbidden tokens 第五百八十一批 ----------

def test_source_no_eval_batch308():
    assert "eval(" not in _src()


def test_source_no_exec_batch308():
    assert "exec(" not in _src()


def test_source_no_compile_batch308():
    assert "compile(" not in _src()


def test_source_no_globals_batch308():
    assert "globals(" not in _src()


def test_source_no_locals_batch308():
    assert "locals(" not in _src()


def test_source_no_os_system_batch308():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch308():
    assert "subprocess" not in _src()


def test_source_no_popen_batch308():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch308():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch308():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch308():
    assert "socket" not in _src()


def test_source_no_requests_batch308():
    assert "requests" not in _src()


def test_source_no_urllib_batch308():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch308():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch308():
    assert "yield" not in _src()


def test_source_no_async_await_batch308():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch308():
    assert _src().count("open(") == 2
