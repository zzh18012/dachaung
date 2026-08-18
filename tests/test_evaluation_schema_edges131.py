"""evaluation/schema.py 第五百六十五轮 edges 测试（Round 1209）。

补强 edges130 未触及的角度（第五百八十一批，probe 实证）。

新角度（locator 跨键容让 / 真文档变异）：
- **PDF locator 容让 DOCX 键**——真文档
  pdf locator 加 paragraph_index →
  validate 照过（locator 无封闭约
  束，跨类型键不回拒首锁——与
  docx locator 含 page 键判无效的
  metrics 层成两层对照）
- **footnote 不在元素枚举**——type
  "footnote" → "'footnote' is not one
  of ['heading', 'paragraph',
  'list_item', 'table', 'image',
  'caption', 'header', 'footer']"
  （metrics 层 footnote 免 bbox，但
  schema 层根本进不来首锁）
- **bbox 字符串项**——4 项全错首错
  "'a' is not of type 'number'" 落
  bbox/0
- **source_element_ids 空表 / 整数
  项**——"[] should be non-empty" /
  "1 is not of type 'string'"
- **page 字符串**——"'1' is not of
  type 'integer'"
- forbidden tokens 第六百七十九批（open 2）
"""

from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate


def _build_pdf(objects, n_obj) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 " + str(n_obj).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, n_obj):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size " + str(n_obj).encode()
            + b"/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _pdf() -> bytes:
    s = (b"BT /F1 12 Tf 10 700 Td "
         b"(  Hello   padded   world  ) Tj ET\n"
         b"BT /F1 12 Tf 10 650 Td (plain line here.) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


@pytest.fixture()
def base_doc(tmp_path):
    from app.pipeline import process_single
    (tmp_path / "p.pdf").write_bytes(_pdf())
    doc, errors = process_single(
        tmp_path / "p.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    return doc.to_dict()


def _mut(base_doc, fn):
    d = copy.deepcopy(base_doc)
    fn(d)
    return d


def _head_message(ei):
    return ei.value.errors[0]["message"]


# ---------- 基线 ----------

def test_base_doc_validates_batch407(base_doc):
    validate(base_doc, "document.schema.json")


# ---------- locator 跨键容让 ----------

def test_pdf_locator_tolerates_docx_key_batch407(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].update({"paragraph_index": 0}))
    validate(d, "document.schema.json")


# ---------- 元素枚举 ----------

def test_element_type_enum_footnote_batch407(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0].update(
        {"type": "footnote"}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert "'footnote' is not one of ['heading', 'paragraph', " \
           "'list_item', 'table', 'image', 'caption', " \
           "'header', 'footer" in _head_message(ei)


# ---------- bbox / page 类型 ----------

def test_bbox_string_items_batch407(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].update({"bbox": ["a", "b", "c", "d"]}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert len(ei.value.errors) == 4
    assert ei.value.errors[0]["message"] == \
        "'a' is not of type 'number'"
    assert ei.value.errors[0]["path"] == [
        "elements", 0, "source_locator", "bbox", 0]


def test_page_string_batch407(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0][
        "source_locator"].update({"page": "1"}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert _head_message(ei) == "'1' is not of type 'integer'"


# ---------- source_element_ids ----------

def test_source_ids_empty_batch407(base_doc):
    d = _mut(base_doc, lambda x: x["chunks"][0].update(
        {"source_element_ids": []}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert _head_message(ei) == "[] should be non-empty"


def test_source_ids_int_batch407(base_doc):
    d = _mut(base_doc, lambda x: x["chunks"][0].update(
        {"source_element_ids": [1]}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert _head_message(ei) == "1 is not of type 'string'"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch407():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第六百七十九批 ----------

def test_source_no_eval_batch407():
    assert "eval(" not in _src()


def test_source_no_exec_batch407():
    assert "exec(" not in _src()


def test_source_no_compile_batch407():
    assert "compile(" not in _src()


def test_source_no_globals_batch407():
    assert "globals(" not in _src()


def test_source_no_locals_batch407():
    assert "locals(" not in _src()


def test_source_no_os_system_batch407():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch407():
    assert "subprocess" not in _src()


def test_source_no_popen_batch407():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch407():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch407():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch407():
    assert "socket" not in _src()


def test_source_no_requests_batch407():
    assert "requests" not in _src()


def test_source_no_urllib_batch407():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch407():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch407():
    assert "yield" not in _src()


def test_source_no_async_await_batch407():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch407():
    assert _src().count("open(") == 2
