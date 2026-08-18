"""evaluation/schema.py 第五百七十二轮 edges 测试（Round 1257）。

补强 edges137 未触及的角度（第六百二十九批，probe 实证）。

新角度（双页真板第二元素路径 / 非唯一性负空间）：
- **幽灵页合法**——page 99（仅 2
  页的 PDF）→ VALID（schema 不交
  验页数首锁）
- **element_id 非唯一合法**——两元
  素同 id → VALID（唯一性不入
  schema）
- **块源重复/悬空合法**——同 id 两
  次 / 指不存在 id → VALID（intact
  指标管，schema 不管）
- **第二元素路径**——page 变异落
  ['elements', 1, ...]（前史全
  elements 0 首锁）
- forbidden tokens 第七百一十九批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import tempfile
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate


def _two_page_pdf() -> bytes:
    s1 = (("BT /F1 12 Tf 10 700 Td (Top line text here.) Tj ET\n"
           "BT /F1 12 Tf 10 670 Td (Lower line text here.) Tj ET\n"
           ).encode())
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 6 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 7 0 R>>"),
        7: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 8\n0000000000 65535 f \n"
    for num in range(1, 8):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 8/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


@pytest.fixture()
def base_doc(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "two.pdf"
    p.write_bytes(_two_page_pdf())
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


# ---------- 基板 ----------

def test_base_ids_and_pages_batch455(base_doc):
    assert [e["element_id"].split("::")[-1]
            for e in base_doc["elements"]] == ["e0000", "e0001"]
    assert [e["source_locator"]["page"]
            for e in base_doc["elements"]] == [1, 2]


# ---------- 非唯一性负空间（VALID） ----------

def test_ghost_page_valid_batch455(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][1][
        "source_locator"].update({"page": 99}))
    validate(d, "document.schema.json")


def test_duplicate_element_id_valid_batch455(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][1].update(
        {"element_id": x["elements"][0]["element_id"]}))
    validate(d, "document.schema.json")


def test_duplicate_chunk_ref_valid_batch455(base_doc):
    d = _mut(base_doc, lambda x: x["chunks"][0].update(
        {"source_element_ids": [x["elements"][0]["element_id"],
                                x["elements"][0]["element_id"]]}))
    validate(d, "document.schema.json")


def test_dangling_chunk_ref_valid_batch455(base_doc):
    d = _mut(base_doc, lambda x: x["chunks"][0].update(
        {"source_element_ids": ["doc-zz::e9999"]}))
    validate(d, "document.schema.json")


# ---------- 第二元素路径 ----------

def test_second_page_string_rejected_batch455(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][1][
        "source_locator"].update({"page": "2"})))
    assert err["message"] == "'2' is not of type 'integer'"
    assert err["path"] == ["elements", 1, "source_locator", "page"]


def test_second_pop_page_required_batch455(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][1][
        "source_locator"].pop("page")))
    assert err["message"] == "'page' is a required property"
    assert err["path"] == ["elements", 1, "source_locator"]


def test_second_page_zero_minimum_batch455(base_doc):
    err = _reject(_mut(base_doc, lambda x: x["elements"][1][
        "source_locator"].update({"page": 0})))
    assert err["message"] == "0 is less than the minimum of 1"
    assert err["path"] == ["elements", 1, "source_locator", "page"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch455():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百一十九批 ----------

def test_source_no_eval_batch455():
    assert "eval(" not in _src()


def test_source_no_exec_batch455():
    assert "exec(" not in _src()


def test_source_no_compile_batch455():
    assert "compile(" not in _src()


def test_source_no_globals_batch455():
    assert "globals(" not in _src()


def test_source_no_locals_batch455():
    assert "locals(" not in _src()


def test_source_no_os_system_batch455():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch455():
    assert "subprocess" not in _src()


def test_source_no_popen_batch455():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch455():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch455():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch455():
    assert "socket" not in _src()


def test_source_no_requests_batch455():
    assert "requests" not in _src()


def test_source_no_urllib_batch455():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch455():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch455():
    assert "yield" not in _src()


def test_source_no_async_await_batch455():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch455():
    assert _src().count("open(") == 2
