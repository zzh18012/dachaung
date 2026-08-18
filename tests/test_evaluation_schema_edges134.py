"""evaluation/schema.py 第五百六十八轮 edges 测试（Round 1231）。

补强 edges133 未触及的角度（第六百零三批，probe 实证）。

新角度（根路径必填 / 类型档 / 空 ID）：
- **chunks 缺键**——pop "chunks"
  → "'chunks' is a required
  property" @ []（根路径空表首
  锁，区别于 elements/0 深路径）
- **chunks 换 dict**——{} →
  "{} is not of type 'array'"
- **document_id 空串**——"" →
  "'' should be non-empty"
- **content 换 int**——5 → 元素
  anyOf 回拒（首错 path 落
  elements/0，与 content/resource
  双空同路）
- forbidden tokens 第六百九十九批（open 2）
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
         b"(Schema four board text line here now.) Tj ET\n")
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


# ---------- 根路径必填 ----------

def test_chunks_missing_root_path_batch429(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.pop("chunks")),
                 "document.schema.json")
    assert _head(ei)["message"] == \
        "'chunks' is a required property"
    assert _head(ei)["path"] == []


# ---------- 类型档 ----------

def test_chunks_dict_rejected_batch429(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.update(
            {"chunks": {}})), "document.schema.json")
    assert _head(ei)["message"] == \
        "{} is not of type 'array'"
    assert _head(ei)["path"] == ["chunks"]


# ---------- 空 ID ----------

def test_document_id_empty_rejected_batch429(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.update(
            {"document_id": ""})), "document.schema.json")
    assert _head(ei)["message"] == \
        "'' should be non-empty"
    assert _head(ei)["path"] == ["document_id"]


# ---------- content 换 int ----------

def test_content_int_rejected_batch429(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["elements"][0].update(
            {"content": 5})), "document.schema.json")
    assert _head(ei)["path"] == ["elements", 0]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch429():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第六百九十九批 ----------

def test_source_no_eval_batch429():
    assert "eval(" not in _src()


def test_source_no_exec_batch429():
    assert "exec(" not in _src()


def test_source_no_compile_batch429():
    assert "compile(" not in _src()


def test_source_no_globals_batch429():
    assert "globals(" not in _src()


def test_source_no_locals_batch429():
    assert "locals(" not in _src()


def test_source_no_os_system_batch429():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch429():
    assert "subprocess" not in _src()


def test_source_no_popen_batch429():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch429():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch429():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch429():
    assert "socket" not in _src()


def test_source_no_requests_batch429():
    assert "requests" not in _src()


def test_source_no_urllib_batch429():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch429():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch429():
    assert "yield" not in _src()


def test_source_no_async_await_batch429():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch429():
    assert _src().count("open(") == 2
