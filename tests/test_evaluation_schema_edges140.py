"""evaluation/schema.py 第五百七十四轮 edges 测试（Round 1269）。

补强 edges139 未触及的角度（第六百四十一批，probe 实证）。

新角度（mc98 板多错聚合 / 源列表项型检）：
- **源列表项型检**——
  ["doc-x::e1", 5, "doc-x::e2"] →
  "5 is not of type 'string'" @
  [..., 'source_element_ids', 1]
  （合法项不报错、错在索引 1 的
  items 型检首锁）
- **双错精确计数**——两处变异 →
  str "(2 处)：" + len(errors)==2
  + 两条独立 message/path（前史
  全 >=1 松界，精确计数首锁）
- **三错跨节**——chunks 两处 +
  elements 一处 → "(3 处)" +
  len==3 跨节聚合首锁
- **空列表/空串 non-empty 消息**
  ——[] / "" 的 should be
  non-empty 精确消息
- forbidden tokens 第七百二十九批（open 2）
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


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


@pytest.fixture()
def mc98_doc(tmp_path):
    from app.pipeline import process_single
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    p = tmp_path / "mix.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=98)
    assert errors == []
    return doc.to_dict()


def _mut(base, fn):
    dd = copy.deepcopy(base)
    fn(dd)
    return dd


def _errors(base, fn):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base, fn), "document.schema.json")
    return ei.value.errors


# ---------- mc98 板基态 ----------

def test_mc98_chunk_shape_batch467(mc98_doc):
    assert [len(c["text"]) for c in mc98_doc["chunks"]] == [
        29, 80, 18]
    assert [len(c["source_element_ids"])
            for c in mc98_doc["chunks"]] == [1, 1, 1]


def test_mc98_strategies_batch467(mc98_doc):
    assert [c["metadata"]["strategy"]
            for c in mc98_doc["chunks"]] == [
        "isolated_caption", "sequential", "sequential"]


def test_base_valid_batch467(mc98_doc):
    validate(mc98_doc, "document.schema.json")


# ---------- 源列表项型检 ----------

def test_srcs_mixed_type_index1_batch467(mc98_doc):
    errs = _errors(mc98_doc, lambda d: d["chunks"][1].update(
        {"source_element_ids": ["doc-x::e1", 5, "doc-x::e2"]}))
    assert len(errs) == 1
    assert errs[0]["message"] == "5 is not of type 'string'"
    assert errs[0]["path"] == [
        "chunks", 1, "source_element_ids", 1]


def test_srcs_int_first_index0_batch467(mc98_doc):
    errs = _errors(mc98_doc, lambda d: d["chunks"][1].update(
        {"source_element_ids": [5]}))
    assert errs[0]["message"] == "5 is not of type 'string'"
    assert errs[0]["path"] == [
        "chunks", 1, "source_element_ids", 0]


def test_srcs_three_strings_valid_batch467(mc98_doc):
    d = _mut(mc98_doc, lambda d: d["chunks"][1].update(
        {"source_element_ids": ["a", "b", "c"]}))
    validate(d, "document.schema.json")


# ---------- non-empty 精确消息 ----------

def test_srcs_empty_nonempty_msg_batch467(mc98_doc):
    errs = _errors(mc98_doc, lambda d: d["chunks"][1].update(
        {"source_element_ids": []}))
    assert errs[0]["message"] == "[] should be non-empty"
    assert errs[0]["path"] == ["chunks", 1,
                               "source_element_ids"]


def test_text_empty_nonempty_msg_batch467(mc98_doc):
    errs = _errors(mc98_doc, lambda d: d["chunks"][2].update(
        {"text": ""}))
    assert errs[0]["message"] == "'' should be non-empty"
    assert errs[0]["path"] == ["chunks", 2, "text"]


def test_srcs_pop_required_batch467(mc98_doc):
    errs = _errors(mc98_doc, lambda d: d["chunks"][1].pop(
        "source_element_ids"))
    assert errs[0]["message"] == \
        "'source_element_ids' is a required property"
    assert errs[0]["path"] == ["chunks", 1]


# ---------- 双错精确计数 ----------

def _two_errors(base):
    return _errors(base, lambda d: (
        d["chunks"][1].update(
            {"source_element_ids": ["doc-x::e1", 5]}),
        d["chunks"][2].update({"text": ""})))


def test_two_errors_count_batch467(mc98_doc):
    errs = _two_errors(mc98_doc)
    assert len(errs) == 2


def test_two_errors_messages_batch467(mc98_doc):
    errs = _two_errors(mc98_doc)
    assert errs[0]["message"] == "5 is not of type 'string'"
    assert errs[1]["message"] == "'' should be non-empty"


def test_two_errors_paths_batch467(mc98_doc):
    errs = _two_errors(mc98_doc)
    assert errs[0]["path"] == [
        "chunks", 1, "source_element_ids", 1]
    assert errs[1]["path"] == ["chunks", 2, "text"]


def test_two_errors_str_prefix_batch467(mc98_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(mc98_doc, lambda d: (
            d["chunks"][1].update(
                {"source_element_ids": ["doc-x::e1", 5]}),
            d["chunks"][2].update({"text": ""}))),
            "document.schema.json")
    assert str(ei.value).startswith(
        "Schema 'document.schema.json' 校验失败 (2 处)：")


# ---------- 三错跨节 ----------

def _three_errors(base):
    return _errors(base, lambda d: (
        d["chunks"][1].update({"source_element_ids": []}),
        d["chunks"][2].update({"text": None}),
        d["elements"][0].pop("metadata")))


def test_three_errors_count_batch467(mc98_doc):
    assert len(_three_errors(mc98_doc)) == 3


def test_three_errors_cross_section_batch467(mc98_doc):
    errs = _three_errors(mc98_doc)
    assert errs[0]["path"] == ["chunks", 1,
                               "source_element_ids"]
    assert errs[1]["path"] == ["chunks", 2, "text"]
    assert errs[2]["path"] == ["elements", 0]


def test_three_errors_str_prefix_batch467(mc98_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(mc98_doc, lambda d: (
            d["chunks"][1].update({"source_element_ids": []}),
            d["chunks"][2].update({"text": None}),
            d["elements"][0].pop("metadata"))),
            "document.schema.json")
    assert str(ei.value).startswith(
        "Schema 'document.schema.json' 校验失败 (3 处)：")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch467():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百二十九批 ----------

def test_source_no_eval_batch467():
    assert "eval(" not in _src()


def test_source_no_exec_batch467():
    assert "exec(" not in _src()


def test_source_no_compile_batch467():
    assert "compile(" not in _src()


def test_source_no_globals_batch467():
    assert "globals(" not in _src()


def test_source_no_locals_batch467():
    assert "locals(" not in _src()


def test_source_no_os_system_batch467():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch467():
    assert "subprocess" not in _src()


def test_source_no_popen_batch467():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch467():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch467():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch467():
    assert "socket" not in _src()


def test_source_no_requests_batch467():
    assert "requests" not in _src()


def test_source_no_urllib_batch467():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch467():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch467():
    assert "yield" not in _src()


def test_source_no_async_await_batch467():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch467():
    assert _src().count("open(") == 2
