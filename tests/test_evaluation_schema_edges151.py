"""evaluation/schema.py 第五百八十六轮 edges 测试（Round 1335）。

补强 edges150 未触及的角度（第七百零七批，probe 实证）。

新角度（document.schema chunk/element 级变异）：
- **chunk 5 键**——
  {chunk_id, metadata,
  source_element_
  ids, source_spans,
  text}（source_
  spans 键集首锁）
- **element 8 键**——
  {confidence,
  content, element_
  id, metadata,
  parent_id,
  resource_path,
  source_locator,
  type}
- **sei 非空锁**——
  [] → "[] should
  be non-empty"；
  [''] → "'' should
  be non-empty"
  @ 嵌套索引路径
- **双 null 拒**——
  content 与
  resource_path
  同 null →
  "is not valid
  under any of the
  given schemas"
  （anyOf 消息锁）
- **level 型别锁**
  ——paragraph 添
  level →
  additionalProperties
  （level 仅 heading
  允许）
- **必填/严闭面**——
  text/sei/metadata/
  chunk_id 缺 →
  required；chunk/
  element 额外键拒
- forbidden tokens 第七百七十八批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import tempfile
from pathlib import Path

import evaluation.schema as schema_mod
from app.pipeline import process_single
from evaluation.schema import EvalSchemaError, \
    validate


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


def _base():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(ONEP))
        doc, errors = process_single(
            tp / "c.pdf", tp / "o.json",
            parser_name="fallback", max_chars=32)
        assert errors == []
        return doc.to_dict()


def _rej(mutate, message, path):
    d = copy.deepcopy(_base())
    mutate(d)
    try:
        validate(d, "document.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert list(e.errors[0]["path"]) == path
    else:
        raise AssertionError("expected rejection")


# ---------- 键集锁 ----------

def test_chunk_keys_batch533():
    assert set(_base()["chunks"][0]) == {
        "chunk_id", "metadata",
        "source_element_ids", "source_spans",
        "text"}


def test_element_keys_batch533():
    assert set(_base()["elements"][0]) == {
        "confidence", "content", "element_id",
        "metadata", "parent_id", "resource_path",
        "source_locator", "type"}


# ---------- sei 非空锁 ----------

def test_sei_empty_rejected_batch533():
    _rej(lambda d: d["chunks"][0].__setitem__(
             "source_element_ids", []),
         "[] should be non-empty",
         ["chunks", 0, "source_element_ids"])


def test_sei_blank_string_rejected_batch533():
    _rej(lambda d: d["chunks"][0].__setitem__(
             "source_element_ids", [""]),
         "'' should be non-empty",
         ["chunks", 0, "source_element_ids", 0])


# ---------- 双 null 拒 ----------

def test_both_null_anyof_rejected_batch533():
    def mut(d):
        d["elements"][0]["content"] = None
        d["elements"][0]["resource_path"] = None
    d = copy.deepcopy(_base())
    mut(d)
    try:
        validate(d, "document.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"].endswith(
            "is not valid under any of the "
            "given schemas")
        assert list(e.errors[0]["path"]) == [
            "elements", 0]
    else:
        raise AssertionError("expected rejection")


def test_content_null_rp_kept_valid_batch533():
    d = copy.deepcopy(_base())
    d["elements"][0]["content"] = None
    d["elements"][0]["resource_path"] = "x.png"
    validate(d, "document.schema.json")


# ---------- level 型别锁 ----------

def test_paragraph_level_rejected_batch533():
    _rej(lambda d: d["elements"][0].__setitem__(
             "level", 2),
         "Additional properties are not allowed "
         "('level' was unexpected)",
         ["elements", 0])


# ---------- 必填面 ----------

def test_chunk_missing_text_batch533():
    _rej(lambda d: d["chunks"][0].pop("text"),
         "'text' is a required property",
         ["chunks", 0])


def test_chunk_missing_sei_batch533():
    _rej(lambda d: d["chunks"][0].pop(
             "source_element_ids"),
         "'source_element_ids' is a required "
         "property", ["chunks", 0])


def test_chunk_missing_metadata_batch533():
    _rej(lambda d: d["chunks"][0].pop("metadata"),
         "'metadata' is a required property",
         ["chunks", 0])


def test_chunk_missing_id_batch533():
    _rej(lambda d: d["chunks"][0].pop("chunk_id"),
         "'chunk_id' is a required property",
         ["chunks", 0])


def test_element_missing_type_batch533():
    _rej(lambda d: d["elements"][0].pop("type"),
         "'type' is a required property",
         ["elements", 0])


def test_element_missing_locator_batch533():
    _rej(lambda d: d["elements"][0].pop(
             "source_locator"),
         "'source_locator' is a required property",
         ["elements", 0])


# ---------- 严闭面 ----------

def test_chunk_extra_key_batch533():
    _rej(lambda d: d["chunks"][0].__setitem__(
             "zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)", ["chunks", 0])


def test_element_extra_key_batch533():
    _rej(lambda d: d["elements"][0].__setitem__(
             "zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)", ["elements", 0])


# ---------- 型枚举 ----------

def test_element_type_sentence_rejected_batch533():
    _rej(lambda d: d["elements"][0].__setitem__(
             "type", "sentence"),
         "'sentence' is not one of "
         "['heading', 'paragraph', 'list_item', "
         "'table', 'image', 'caption', "
         "'header', 'footer']",
         ["elements", 0, "type"])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch533():
    src = _src()
    assert "class EvalSchemaError(Exception):" \
        in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百七十八批 ----------

def test_source_no_eval_batch533():
    assert "eval(" not in _src()


def test_source_no_exec_batch533():
    assert "exec(" not in _src()


def test_source_no_compile_batch533():
    assert "compile(" not in _src()


def test_source_no_globals_batch533():
    assert "globals(" not in _src()


def test_source_no_locals_batch533():
    assert "locals(" not in _src()


def test_source_no_os_system_batch533():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch533():
    assert "subprocess" not in _src()


def test_source_no_popen_batch533():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch533():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch533():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch533():
    assert "socket" not in _src()


def test_source_no_requests_batch533():
    assert "requests" not in _src()


def test_source_no_urllib_batch533():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch533():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch533():
    assert "yield" not in _src()


def test_source_no_async_await_batch533():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch533():
    assert _src().count("open(") == 2
