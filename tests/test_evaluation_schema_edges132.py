"""evaluation/schema.py 第五百六十六轮 edges 测试（Round 1217）。

补强 edges131 未触及的角度（第五百八十九批，probe 实证）。

新角度（引用无完整性 / 元数据类型 / 空文本 / 重复 ID 容让）：
- **悬空引用照过**——chunk source_
  element_ids 指向不存在的
  "nope" → validate 照过（schema 层
  不做引用完整性首锁）
- **重复 element_id 照过**——两元素
  同 id → VALID（无唯一性约束）
- **metadata 列表**——metadata [] →
  "[] is not of type 'object'"
- **chunk 空文本**——text "" →
  "'' should be non-empty"
- **content/resource 双空**——
  content None + resource_path None →
  anyOf 回拒（首错 path 落 elements/0）
- **负耗时照过**——parse_time_ms
  -5 → VALID（无下界校验）
- forbidden tokens 第六百八十七批（open 2）
"""

from __future__ import annotations

import copy
import inspect

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
         b"(Hello schema mutation board.) Tj ET\n")
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
        parser_name="fallback", max_chars=100)
    assert errors == []
    return doc.to_dict()


def _mut(base_doc, fn):
    d = copy.deepcopy(base_doc)
    fn(d)
    return d


def _head(ei):
    return ei.value.errors[0]


# ---------- 引用无完整性 ----------

def test_dangling_source_ref_valid_batch415(base_doc):
    d = _mut(base_doc, lambda x: x["chunks"][0].update(
        {"source_element_ids": ["nope"]}))
    validate(d, "document.schema.json")


def test_duplicate_element_id_valid_batch415(base_doc):
    d = _mut(base_doc, lambda x: x["elements"].append(
        copy.deepcopy(x["elements"][0])))
    validate(d, "document.schema.json")


# ---------- 类型回拒 ----------

def test_metadata_list_rejected_batch415(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0].update(
        {"metadata": []}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert _head(ei)["message"] == "[] is not of type 'object'"
    assert _head(ei)["path"] == ["elements", 0, "metadata"]


def test_chunk_text_empty_rejected_batch415(base_doc):
    d = _mut(base_doc, lambda x: x["chunks"][0].update(
        {"text": ""}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert _head(ei)["message"] == "'' should be non-empty"
    assert _head(ei)["path"] == ["chunks", 0, "text"]


def test_content_resource_both_null_batch415(base_doc):
    d = _mut(base_doc, lambda x: x["elements"][0].update(
        {"content": None, "resource_path": None}))
    with pytest.raises(EvalSchemaError) as ei:
        validate(d, "document.schema.json")
    assert _head(ei)["path"] == ["elements", 0]


# ---------- 下界容让 ----------

def test_parse_time_negative_valid_batch415(base_doc):
    def fn(x):
        if "parse_metadata" in x:
            x["parse_metadata"]["parse_time_ms"] = -5
        else:
            x["parse_metadata"] = {"parse_time_ms": -5}
    validate(_mut(base_doc, fn), "document.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch415():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第六百八十七批 ----------

def test_source_no_eval_batch415():
    assert "eval(" not in _src()


def test_source_no_exec_batch415():
    assert "exec(" not in _src()


def test_source_no_compile_batch415():
    assert "compile(" not in _src()


def test_source_no_globals_batch415():
    assert "globals(" not in _src()


def test_source_no_locals_batch415():
    assert "locals(" not in _src()


def test_source_no_os_system_batch415():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch415():
    assert "subprocess" not in _src()


def test_source_no_popen_batch415():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch415():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch415():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch415():
    assert "socket" not in _src()


def test_source_no_requests_batch415():
    assert "requests" not in _src()


def test_source_no_urllib_batch415():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch415():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch415():
    assert "yield" not in _src()


def test_source_no_async_await_batch415():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch415():
    assert _src().count("open(") == 2
