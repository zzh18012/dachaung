"""evaluation/schema.py 第五百六十九轮 edges 测试（Round 1234）。

补强 edges134 未触及的角度（第六百零六批，probe 实证）。

新角度（chunk def 必填 / 空文本 / 深路径二块）：
- **text 缺键**——pop "text" →
  "'text' is a required property"
  @ ['chunks', 0]（chunk def 必填
  首锁，区别于元素层 anyOf）
- **text 空串**——"" → "'' should
  be non-empty" @ ['chunks', 0,
  'text']（非空约束下沉到 chunk
  文本路径首锁）
- **source_element_ids 缺键**——
  pop → "'source_element_ids' is
  a required property" @ ['chunks',
  0]
- **深路径二块**——mc32 五块板上
  变异 chunks[1] → 首错 path
  ['chunks', 1]（数组下探第二项
  首锁，历史全在 0 号块）
- 单块单错恰 1 条
- forbidden tokens 第七百零一批（open 2）
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
    words = " ".join("w%02d" % i for i in range(40))
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
         % words).encode()
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
        parser_name="fallback", max_chars=32)
    assert errors == []
    return doc.to_dict()


def _mut(base_doc, fn):
    d = copy.deepcopy(base_doc)
    fn(d)
    return d


def _head(ei):
    return ei.value.errors[0]


# ---------- chunk def 必填 ----------

def test_chunk_text_missing_batch432(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["chunks"][0].pop(
            "text")), "document.schema.json")
    assert _head(ei)["message"] == \
        "'text' is a required property"
    assert _head(ei)["path"] == ["chunks", 0]


def test_chunk_source_ids_missing_batch432(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["chunks"][0].pop(
            "source_element_ids")), "document.schema.json")
    assert _head(ei)["message"] == \
        "'source_element_ids' is a required property"
    assert _head(ei)["path"] == ["chunks", 0]


# ---------- 空文本 ----------

def test_chunk_text_empty_batch432(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["chunks"][0].update(
            {"text": ""})), "document.schema.json")
    assert _head(ei)["message"] == "'' should be non-empty"
    assert _head(ei)["path"] == ["chunks", 0, "text"]


# ---------- 深路径二块 ----------

def test_second_chunk_path_batch432(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["chunks"][1].pop(
            "text")), "document.schema.json")
    assert _head(ei)["message"] == \
        "'text' is a required property"
    assert _head(ei)["path"] == ["chunks", 1]


def test_five_chunks_untouched_others_batch432(base_doc):
    assert len(base_doc["chunks"]) == 5
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["chunks"][1].pop(
            "text")), "document.schema.json")
    assert len(ei.value.errors) == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch432():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百零一批 ----------

def test_source_no_eval_batch432():
    assert "eval(" not in _src()


def test_source_no_exec_batch432():
    assert "exec(" not in _src()


def test_source_no_compile_batch432():
    assert "compile(" not in _src()


def test_source_no_globals_batch432():
    assert "globals(" not in _src()


def test_source_no_locals_batch432():
    assert "locals(" not in _src()


def test_source_no_os_system_batch432():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch432():
    assert "subprocess" not in _src()


def test_source_no_popen_batch432():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch432():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch432():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch432():
    assert "socket" not in _src()


def test_source_no_requests_batch432():
    assert "requests" not in _src()


def test_source_no_urllib_batch432():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch432():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch432():
    assert "yield" not in _src()


def test_source_no_async_await_batch432():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch432():
    assert _src().count("open(") == 2
