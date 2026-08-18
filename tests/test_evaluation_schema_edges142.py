"""evaluation/schema.py 第五百七十六轮 edges 测试（Round 1281）。

补强 edges141 未触及的角度（第六百五十三批，probe 实证）。

新角度（warnings/errors 条目不对称 / chunk 五键四必一可选）：
- **warnings 条目双必填**——
  {reason} 单键 → "'code' is a
  required property"（code 必填
  首锁）；{code, reason} 恰过
- **errors 条目严闭**——
  {code, message} 过；+hint →
  "Additional properties are
  not allowed"（禁额外键首锁）；
  {message} 单键 → code required
- **单条目双错**——warnings
  {reason: 5} → 2 err（code
  required + 型错并存首锁）
- **chunk 五键**——pop
  chunk_id / text 各自 required
  （前史仅 metadata/srcs）
- **source_spans 行为可选**——
  pop / [] 均 VALID（前史仅
  内省，真板行为首锁）；str →
  not array
- forbidden tokens 第七百四十批（open 2）
"""

from __future__ import annotations

import copy
import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate


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
HEAD = "A" * 80


@pytest.fixture()
def combo_doc(tmp_path):
    from app.pipeline import process_single
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    p = tmp_path / "combo.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    return doc.to_dict()


def _mut(base, fn):
    dd = copy.deepcopy(base)
    fn(dd)
    return dd


def _reject(base, fn):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base, fn), "document.schema.json")
    return ei.value.errors


def _valid(base, fn):
    validate(_mut(base, fn), "document.schema.json")


# ---------- warnings 条目双必填 ----------

def test_warn_reason_only_missing_code_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update(
        {"warnings": [{"reason": "why"}]}))
    assert errs[0]["message"] == \
        "'code' is a required property"
    assert errs[0]["path"] == ["warnings", 0]


def test_warn_code_reason_valid_batch479(combo_doc):
    _valid(combo_doc, lambda d: d.update(
        {"warnings": [{"code": "w", "reason": "why"}]}))


def test_warn_int_not_object_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update(
        {"warnings": [5]}))
    assert errs[0]["message"] == "5 is not of type 'object'"
    assert errs[0]["path"] == ["warnings", 0]


# ---------- 单条目双错 ----------

def test_warn_reason_int_two_errors_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update(
        {"warnings": [{"reason": 5}]}))
    assert len(errs) == 2
    assert errs[0]["message"] == \
        "'code' is a required property"
    assert errs[1]["message"] == "5 is not of type 'string'"
    assert errs[1]["path"] == ["warnings", 0, "reason"]


def test_warn_reason_int_str_prefix_batch479(combo_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(combo_doc, lambda d: d.update(
            {"warnings": [{"reason": 5}]})),
            "document.schema.json")
    assert str(ei.value).startswith(
        "Schema 'document.schema.json' 校验失败 (2 处)：")


# ---------- errors 条目严闭 ----------

def test_err_code_message_valid_batch479(combo_doc):
    _valid(combo_doc, lambda d: d.update(
        {"errors": [{"code": "e", "message": "m"}]}))


def test_err_extra_key_rejected_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update(
        {"errors": [{"code": "e", "message": "m",
                     "hint": 5}]}))
    assert errs[0]["message"] == (
        "Additional properties are not allowed "
        "('hint' was unexpected)")
    assert errs[0]["path"] == ["errors", 0]


def test_err_message_only_missing_code_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update(
        {"errors": [{"message": "m"}]}))
    assert errs[0]["message"] == \
        "'code' is a required property"


def test_err_code_only_missing_message_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update(
        {"errors": [{"code": "e"}]}))
    assert errs[0]["message"] == \
        "'message' is a required property"


def test_err_str_not_object_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update(
        {"errors": ["err"]}))
    assert errs[0]["message"] == \
        "'err' is not of type 'object'"


# ---------- chunk 五键四必一可选 ----------

def test_chunk_id_required_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d["chunks"][0].pop(
        "chunk_id"))
    assert errs[0]["message"] == \
        "'chunk_id' is a required property"
    assert errs[0]["path"] == ["chunks", 0]


def test_chunk_text_required_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d["chunks"][0].pop(
        "text"))
    assert errs[0]["message"] == \
        "'text' is a required property"


def test_chunk_keys_exact_five_batch479(combo_doc):
    assert list(combo_doc["chunks"][0].keys()) == [
        "chunk_id", "text", "source_element_ids",
        "metadata", "source_spans"]


def test_spans_pop_valid_batch479(combo_doc):
    _valid(combo_doc, lambda d: d["chunks"][0].pop(
        "source_spans"))


def test_spans_empty_list_valid_batch479(combo_doc):
    _valid(combo_doc, lambda d: d["chunks"][0].update(
        {"source_spans": []}))


def test_spans_str_rejected_batch479(combo_doc):
    errs = _reject(combo_doc, lambda d: d["chunks"][0].update(
        {"source_spans": "x"}))
    assert errs[0]["message"] == "'x' is not of type 'array'"
    assert errs[0]["path"] == ["chunks", 0,
                               "source_spans"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch479():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百四十批 ----------

def test_source_no_eval_batch479():
    assert "eval(" not in _src()


def test_source_no_exec_batch479():
    assert "exec(" not in _src()


def test_source_no_compile_batch479():
    assert "compile(" not in _src()


def test_source_no_globals_batch479():
    assert "globals(" not in _src()


def test_source_no_locals_batch479():
    assert "locals(" not in _src()


def test_source_no_os_system_batch479():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch479():
    assert "subprocess" not in _src()


def test_source_no_popen_batch479():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch479():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch479():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch479():
    assert "socket" not in _src()


def test_source_no_requests_batch479():
    assert "requests" not in _src()


def test_source_no_urllib_batch479():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch479():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch479():
    assert "yield" not in _src()


def test_source_no_async_await_batch479():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch479():
    assert _src().count("open(") == 2
