"""evaluation/schema.py 第五百七十三轮 edges 测试（Round 1263）。

补强 edges138 未触及的角度（第六百三十五批，probe 实证）。

新角度（混排板 metadata 必备而开放 / caption 型枚举）：
- **caption 型枚举拒绝**——"captions"
  → "'captions' is not one of
  ['heading', 'paragraph',
  'list_item', 'table', 'image',
  'caption', 'header', 'footer']"
  （八型全列枚举串首锁）+ "" 空串
  同拒
- **metadata 必备**——元素/块
  metadata pop → "'metadata' is a
  required property"（chunks[0]
  首锁）
- **metadata 型检**——None / [] →
  "is not of type 'object'"
- **metadata 开放世界**——level
  "zero"/99/-1、heuristic 5、
  strategy 5、char_count "29"、
  zzz 键全 VALID（键值全不约束
  首锁）
- **混排板结构值**——caption
  元素 metadata {"heuristic":
  "caption_regex"} / heading
  {"level": 0, "heuristic":
  "short_line"} / 块 strategy
  isolated_caption+sequential
- forbidden tokens 第七百二十四批（open 2）
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
def mix_doc(tmp_path):
    from app.pipeline import process_single
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    p = tmp_path / "mix.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=200)
    assert errors == []
    return doc.to_dict()


def _mut(base, fn):
    dd = copy.deepcopy(base)
    fn(dd)
    return dd


def _reject(dd):
    with pytest.raises(EvalSchemaError) as ei:
        validate(dd, "document.schema.json")
    return ei.value.errors[0]


def _valid(base, fn):
    validate(_mut(base, fn), "document.schema.json")


# ---------- 混排板结构值 ----------

def test_caption_metadata_value_batch461(mix_doc):
    assert mix_doc["elements"][0]["metadata"] == {
        "heuristic": "caption_regex"}


def test_heading_metadata_value_batch461(mix_doc):
    assert mix_doc["elements"][1]["metadata"] == {
        "level": 0, "heuristic": "short_line"}


def test_chunk0_metadata_value_batch461(mix_doc):
    assert mix_doc["chunks"][0]["metadata"] == {
        "strategy": "isolated_caption", "max_chars": 200,
        "char_count": 29}


def test_chunk1_metadata_value_batch461(mix_doc):
    assert mix_doc["chunks"][1]["metadata"] == {
        "strategy": "sequential", "max_chars": 200,
        "char_count": 99}


# ---------- caption 型枚举拒绝 ----------

ENUM_MSG = ("'captions' is not one of ['heading', 'paragraph', "
            "'list_item', 'table', 'image', 'caption', 'header', "
            "'footer']")


def test_type_captions_enum_rejected_batch461(mix_doc):
    err = _reject(_mut(mix_doc, lambda d: d["elements"][0].update(
        {"type": "captions"})))
    assert err["message"] == ENUM_MSG
    assert err["path"] == ["elements", 0, "type"]


def test_type_empty_enum_rejected_batch461(mix_doc):
    err = _reject(_mut(mix_doc, lambda d: d["elements"][0].update(
        {"type": ""})))
    assert err["message"] == ENUM_MSG.replace("'captions'", "''")
    assert err["path"] == ["elements", 0, "type"]


# ---------- metadata 必备 ----------

def test_element_metadata_pop_rejected_batch461(mix_doc):
    err = _reject(_mut(mix_doc, lambda d: d["elements"][1].pop(
        "metadata")))
    assert err["message"] == "'metadata' is a required property"
    assert err["path"] == ["elements", 1]


def test_chunk_metadata_pop_rejected_batch461(mix_doc):
    err = _reject(_mut(mix_doc, lambda d: d["chunks"][0].pop(
        "metadata")))
    assert err["message"] == "'metadata' is a required property"
    assert err["path"] == ["chunks", 0]


# ---------- metadata 型检 ----------

def test_element_metadata_none_rejected_batch461(mix_doc):
    err = _reject(_mut(mix_doc, lambda d: d["elements"][1].update(
        {"metadata": None})))
    assert err["message"] == "None is not of type 'object'"
    assert err["path"] == ["elements", 1, "metadata"]


def test_element_metadata_list_rejected_batch461(mix_doc):
    err = _reject(_mut(mix_doc, lambda d: d["elements"][1].update(
        {"metadata": []})))
    assert err["message"] == "[] is not of type 'object'"
    assert err["path"] == ["elements", 1, "metadata"]


def test_chunk_metadata_none_rejected_batch461(mix_doc):
    err = _reject(_mut(mix_doc, lambda d: d["chunks"][0].update(
        {"metadata": None})))
    assert err["message"] == "None is not of type 'object'"
    assert err["path"] == ["chunks", 0, "metadata"]


# ---------- metadata 开放世界 ----------

def test_heading_level_str_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["elements"][1]["metadata"].update(
        {"level": "zero"}))


def test_heading_level_99_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["elements"][1]["metadata"].update(
        {"level": 99}))


def test_heading_level_neg_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["elements"][1]["metadata"].update(
        {"level": -1}))


def test_caption_heuristic_int_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["elements"][0]["metadata"].update(
        {"heuristic": 5}))


def test_element_metadata_zzz_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["elements"][1]["metadata"].update(
        {"zzz": 1}))


def test_chunk_strategy_int_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["chunks"][0]["metadata"].update(
        {"strategy": 5}))


def test_chunk_metadata_zzz_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["chunks"][0]["metadata"].update(
        {"zzz": 1}))


def test_chunk_char_count_str_valid_batch461(mix_doc):
    _valid(mix_doc, lambda d: d["chunks"][0]["metadata"].update(
        {"char_count": "29"}))


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch461():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百二十四批 ----------

def test_source_no_eval_batch461():
    assert "eval(" not in _src()


def test_source_no_exec_batch461():
    assert "exec(" not in _src()


def test_source_no_compile_batch461():
    assert "compile(" not in _src()


def test_source_no_globals_batch461():
    assert "globals(" not in _src()


def test_source_no_locals_batch461():
    assert "locals(" not in _src()


def test_source_no_os_system_batch461():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch461():
    assert "subprocess" not in _src()


def test_source_no_popen_batch461():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch461():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch461():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch461():
    assert "socket" not in _src()


def test_source_no_requests_batch461():
    assert "requests" not in _src()


def test_source_no_urllib_batch461():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch461():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch461():
    assert "yield" not in _src()


def test_source_no_async_await_batch461():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch461():
    assert _src().count("open(") == 2
