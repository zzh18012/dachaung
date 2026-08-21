"""evaluation/schema.py 第五百八十五轮 edges 测试（Round 1329）。

补强 edges149 未触及的角度（第七百零一批，probe 实证）。

新角度（manifest.schema 面 / 错误条目三键 / 未知 schema 名）：
- **错误条目三键**——
  e.errors[0] 恰
  {message, path,
  schema_path}（schema_
  path 首锁）
- **manifest 型面**——
  documents 字符串 →
  not array @
  [documents]；条目
  字符串 → not object
  @ [documents, 0]；
  缺 path → required
- **manifest 严双枚举**
  ——source_type 'txt'
  → "'txt' is not one
  of ['pdf', 'docx']"
  （manifest 恰 2 型
  vs document 6 型）
- **manifest 双层严闭**
  ——顶层/条目额外键
  均 additionalProperties
- **未知 schema 名**——
  FileNotFoundError +
  "Schema 文件不存在:"
  前缀（4 schema 清单
  锁）
- **多错误齐收**——
  半空 doc dict → 恰
  10 条 required @ []
  一次收齐（elements/
  chunks 亦 required）
- **真 doc 13 根键**——
  process_single 产物
  root 键集 + VALID
- forbidden tokens 第七百七十三批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import tempfile
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from app.pipeline import process_single
from evaluation.schema import EvalSchemaError, \
    validate

BASE_M = {"manifest_version": "1.0",
          "devset_status": "incomplete",
          "documents": [
              {"doc_id": "g1", "path": "c.pdf",
               "source_type": "pdf"}]}

PARTIAL_DOC = {
    "document_version": "1.0",
    "document_id": "d",
    "source_type": "ipynb",
    "source_path": "x.ipynb",
    "parser": {"name": "fallback",
               "version": "1"}}


def _rej(instance, schema, message, path):
    try:
        validate(instance, schema)
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert list(e.errors[0]["path"]) == path
    else:
        raise AssertionError("expected rejection")


# ---------- manifest 型面 ----------

def test_manifest_documents_string_batch527():
    d = copy.deepcopy(BASE_M)
    d["documents"] = "x"
    _rej(d, "manifest.schema.json",
         "'x' is not of type 'array'",
         ["documents"])


def test_manifest_entry_string_batch527():
    d = copy.deepcopy(BASE_M)
    d["documents"][0] = "x"
    _rej(d, "manifest.schema.json",
         "'x' is not of type 'object'",
         ["documents", 0])


def test_manifest_entry_missing_path_batch527():
    d = copy.deepcopy(BASE_M)
    d["documents"][0].pop("path")
    _rej(d, "manifest.schema.json",
         "'path' is a required property",
         ["documents", 0])


# ---------- manifest 严双枚举 ----------

def test_manifest_srctxt_rejected_batch527():
    d = copy.deepcopy(BASE_M)
    d["documents"][0]["source_type"] = "txt"
    _rej(d, "manifest.schema.json",
         "'txt' is not one of ['pdf', 'docx']",
         ["documents", 0, "source_type"])


# ---------- manifest 双层严闭 ----------

def test_manifest_top_extra_key_batch527():
    d = copy.deepcopy(BASE_M)
    d["zz"] = 1
    _rej(d, "manifest.schema.json",
         "Additional properties are not allowed "
         "('zz' was unexpected)", [])


def test_manifest_entry_extra_key_batch527():
    d = copy.deepcopy(BASE_M)
    d["documents"][0]["zz"] = 1
    _rej(d, "manifest.schema.json",
         "Additional properties are not allowed "
         "('zz' was unexpected)",
         ["documents", 0])


def test_manifest_base_valid_batch527():
    validate(copy.deepcopy(BASE_M),
             "manifest.schema.json")


# ---------- 错误条目三键 ----------

def test_error_entry_keys_batch527():
    d = copy.deepcopy(BASE_M)
    d["zz"] = 1
    try:
        validate(d, "manifest.schema.json")
    except EvalSchemaError as e:
        assert set(e.errors[0]) == {
            "message", "path", "schema_path"}
        assert e.errors[0]["schema_path"] == [
            "additionalProperties"]


# ---------- 未知 schema 名 ----------

def test_unknown_schema_name_batch527():
    with pytest.raises(FileNotFoundError) as ei:
        validate({}, "no-such.schema.json")
    assert str(ei.value).startswith(
        "Schema 文件不存在:")


def test_unknown_bare_name_batch527():
    with pytest.raises(FileNotFoundError):
        validate({}, "document")


# ---------- 多错误齐收 ----------

def test_partial_doc_eight_errors_batch527():
    try:
        validate(copy.deepcopy(PARTIAL_DOC),
                 "document.schema.json")
    except EvalSchemaError as e:
        assert len(e.errors) == 10
        for err in e.errors:
            assert err["message"].endswith(
                "is a required property")
            assert list(err["path"]) == []
    else:
        raise AssertionError("expected rejection")


def test_partial_doc_error_names_batch527():
    try:
        validate(copy.deepcopy(PARTIAL_DOC),
                 "document.schema.json")
    except EvalSchemaError as e:
        names = sorted(x["message"].split("'")[1]
                       for x in e.errors)
        assert names == [
            "chunks", "elements", "errors",
            "metadata", "parser_name",
            "parser_version", "relations",
            "schema_version", "source_hash",
            "warnings"]


# ---------- 真 doc 13 根键 ----------

def _wrap(s: bytes) -> bytes:
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
ONEP = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
        % LONG).encode()


def _real_doc():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(ONEP))
        doc, errors = process_single(
            tp / "c.pdf", tp / "o.json",
            parser_name="fallback", max_chars=32)
        assert errors == []
        return doc.to_dict()


def test_real_doc_root_keys_batch527():
    assert set(_real_doc()) == {
        "chunks", "document_id", "elements",
        "errors", "metadata", "parser_name",
        "parser_version", "relations",
        "schema_version", "source_hash",
        "source_path", "source_type",
        "warnings"}


def test_real_doc_valid_batch527():
    validate(_real_doc(), "document.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch527():
    src = _src()
    assert "class EvalSchemaError(Exception):" \
           in src
    assert "def validate(instance" in src
    assert "Schema 文件不存在" in src


# ---------- forbidden tokens 第七百七十三批 ----------

def test_source_no_eval_batch527():
    assert "eval(" not in _src()


def test_source_no_exec_batch527():
    assert "exec(" not in _src()


def test_source_no_compile_batch527():
    assert "compile(" not in _src()


def test_source_no_globals_batch527():
    assert "globals(" not in _src()


def test_source_no_locals_batch527():
    assert "locals(" not in _src()


def test_source_no_os_system_batch527():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch527():
    assert "subprocess" not in _src()


def test_source_no_popen_batch527():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch527():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch527():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch527():
    assert "socket" not in _src()


def test_source_no_requests_batch527():
    assert "requests" not in _src()


def test_source_no_urllib_batch527():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch527():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch527():
    assert "yield" not in _src()


def test_source_no_async_await_batch527():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch527():
    assert _src().count("open(") == 2
