"""evaluation/schema.py 第五百七十一轮 edges 测试（Round 1249）。

补强 edges136 未触及的角度（第六百二十一批，probe 实证）。

新角度（真 PDF gap 板 locator 负空间 / 闭世界键）：
- **bbox 可省**——pop bbox → VALID
  （PDF locator 仅 page 必需首锁）
- **bbox 反序合法**——[500, 700,
  100, 720] → VALID（坐标次序不入
  schema）
- **page 下界 1**——page 0 / -2 →
  "is less than the minimum of 1"
  （与 paragraph_index 下界 0 成
  字段对照）
- **bbox 过短**——3 项 → "is too
  short"
- **元素/块闭世界**——zzz 键 →
  "Additional properties are not
  allowed"；chunk_index 非块键
- **metadata 顶层必需**——pop →
  required @ []
- forbidden tokens 第七百一十三批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import tempfile
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate


def _pdf(y2: int) -> bytes:
    s = (("BT /F1 12 Tf 10 700 Td (Top line text here.) Tj ET\n"
          "BT /F1 12 Tf 10 %d Td (Lower line text here.) Tj ET\n"
          % y2).encode())
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"),
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


@pytest.fixture()
def base_doc(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "g.pdf"
    p.write_bytes(_pdf(669))
    d, errors = process_single(p, tmp_path / "o.json",
                               parser_name="fallback",
                               max_chars=200)
    assert errors == []
    return d.to_dict()


def _mut(base, fn):
    dd = copy.deepcopy(base)
    fn(dd)
    return dd


def _reject(dd):
    with pytest.raises(EvalSchemaError) as ei:
        validate(dd, "document.schema.json")
    return ei.value.errors[0]


# ---------- locator 负空间（VALID） ----------

def test_reversed_bbox_valid_batch447(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].update({"bbox": [500, 700, 100, 720]}))
    validate(d, "document.schema.json")


def test_pop_bbox_valid_batch447(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].pop("bbox"))
    validate(d, "document.schema.json")


# ---------- page 下界 1 ----------

def test_page_zero_minimum_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].update({"page": 0})))
    assert err["message"] == "0 is less than the minimum of 1"
    assert err["path"] == ["elements", 0, "source_locator", "page"]


def test_page_negative_minimum_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].update({"page": -2})))
    assert err["message"] == "-2 is less than the minimum of 1"


def test_pop_page_required_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].pop("page")))
    assert err["message"] == "'page' is a required property"
    assert err["path"] == ["elements", 0, "source_locator"]


# ---------- bbox 过短 ----------

def test_bbox_three_items_too_short_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].update({"bbox": [0, 0, 100]})))
    assert err["message"] == "[0, 0, 100] is too short"
    assert err["path"] == ["elements", 0, "source_locator", "bbox"]


# ---------- 闭世界键 ----------

def test_element_unknown_key_rejected_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][0].update(
        {"zzz": 1})))
    assert err["message"] == (
        "Additional properties are not allowed ('zzz' was unexpected)")
    assert err["path"] == ["elements", 0]


def test_chunk_unknown_key_rejected_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["chunks"][0].update(
        {"zzz": 1})))
    assert err["message"] == (
        "Additional properties are not allowed ('zzz' was unexpected)")
    assert err["path"] == ["chunks", 0]


def test_chunk_index_not_a_chunk_key_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["chunks"][0].update(
        {"chunk_index": 1})))
    assert "'chunk_index' was unexpected" in err["message"]


# ---------- 顶层必需 ----------

def test_pop_metadata_required_batch447(base_doc):
    err = _reject(_mut(base_doc, lambda x: x.pop("metadata")))
    assert err["message"] == "'metadata' is a required property"
    assert err["path"] == []


def test_base_locator_shape_batch447(base_doc):
    loc = base_doc["elements"][0]["source_locator"]
    assert loc["page"] == 1
    assert loc["bbox"][0] == 10.0
    assert len(loc["bbox"]) == 4


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch447():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百一十三批 ----------

def test_source_no_eval_batch447():
    assert "eval(" not in _src()


def test_source_no_exec_batch447():
    assert "exec(" not in _src()


def test_source_no_compile_batch447():
    assert "compile(" not in _src()


def test_source_no_globals_batch447():
    assert "globals(" not in _src()


def test_source_no_locals_batch447():
    assert "locals(" not in _src()


def test_source_no_os_system_batch447():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch447():
    assert "subprocess" not in _src()


def test_source_no_popen_batch447():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch447():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch447():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch447():
    assert "socket" not in _src()


def test_source_no_requests_batch447():
    assert "requests" not in _src()


def test_source_no_urllib_batch447():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch447():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch447():
    assert "yield" not in _src()


def test_source_no_async_await_batch447():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch447():
    assert _src().count("open(") == 2
