"""evaluation/schema.py 第五百五十轮 edges 测试（Round 1106）。

补强 edges125-127 未触及的角度（第四百八十二批，probe 实证）。

新角度（errors / warnings / relations 三 def 首锁）：
- **errors 裸条目拒绝**：errors [{"bogus": 1}] →
  "'code' is a required property @ path=['errors',
  0]"——error def required [code, message]
- **warning 键名分歧**：warnings 塞 errors 正形
  {code, message} → 仍拒 "'reason' is a required
  property"——warnings def required [code,
  reason]：error/warning 非孪生，第二键是 reason
  不是 message（键名陷阱首锁）
- **relations 裸条目拒绝**：[{"bogus": 1}] →
  "'type' is a required property"——relation def
  required [type, from_id, to_id]
- **正形照过**：errors [{code, message}] 与
  relations [{type, from_id, to_id}]（同元素
  自指 from_id==to_id 也收）双双通过
- forbidden tokens 第五百七十七批（open 2）
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


def _expect_reject(tmp_path, mut, frag):
    r = copy.deepcopy(_real_doc(tmp_path))
    mut(r)
    try:
        validate(r, "document.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert frag in str(e)
    assert raised


# ---------- errors 裸条目拒绝 ----------

def test_errors_bare_entry_rejected_batch305(tmp_path):
    _expect_reject(
        tmp_path,
        lambda r: r.__setitem__(
            "errors", [{"bogus": 1}]),
        "'code' is a required property @ "
        "path=['errors', 0]")


# ---------- warning 键名分歧 ----------

def test_warning_key_name_divergence_batch305(tmp_path):
    _expect_reject(
        tmp_path,
        lambda r: r.__setitem__(
            "warnings", [{"bogus": 1}]),
        "'code' is a required property")
    _expect_reject(
        tmp_path,
        lambda r: r.__setitem__(
            "warnings",
            [{"code": "W_X", "message": "m"}]),
        "'reason' is a required property")


# ---------- relations 裸条目拒绝 ----------

def test_relations_bare_entry_rejected_batch305(tmp_path):
    _expect_reject(
        tmp_path,
        lambda r: r.__setitem__(
            "relations", [{"bogus": 1}]),
        "'type' is a required property @ "
        "path=['relations', 0]")


# ---------- 正形照过 ----------

def test_proper_error_and_relation_pass_batch305(tmp_path):
    r = copy.deepcopy(_real_doc(tmp_path))
    r["errors"] = [{"code": "E_X", "message": "boom"}]
    ids = [e["element_id"] for e in r["elements"]]
    r["relations"] = [{
        "type": "caption",
        "from_id": ids[0], "to_id": ids[0]}]
    validate(r, "document.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch305():
    src = _src()
    assert "def load_schema(name" in src
    assert "class EvalSchemaError" in src


# ---------- forbidden tokens 第五百七十七批 ----------

def test_source_no_eval_batch305():
    assert "eval(" not in _src()


def test_source_no_exec_batch305():
    assert "exec(" not in _src()


def test_source_no_compile_batch305():
    assert "compile(" not in _src()


def test_source_no_globals_batch305():
    assert "globals(" not in _src()


def test_source_no_locals_batch305():
    assert "locals(" not in _src()


def test_source_no_os_system_batch305():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch305():
    assert "subprocess" not in _src()


def test_source_no_popen_batch305():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch305():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch305():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch305():
    assert "socket" not in _src()


def test_source_no_requests_batch305():
    assert "requests" not in _src()


def test_source_no_urllib_batch305():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch305():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch305():
    assert "yield" not in _src()


def test_source_no_async_await_batch305():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch305():
    assert _src().count("open(") == 2
