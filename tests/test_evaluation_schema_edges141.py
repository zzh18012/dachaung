"""evaluation/schema.py 第五百七十五轮 edges 测试（Round 1275）。

补强 edges140 未触及的角度（第六百四十七批，probe 实证）。

新角度（confidence 全谱 / parent_id 无引用完整性 / 文档级 metadata 开放）：
- **confidence 上界**——1.01 / 2.0 →
  "is greater than the maximum of 1"
  （前史仅锁下界 -0.1，上界首锁）
- **confidence 闭区间**——恰 0 与
  恰 1 均 VALID（边界含端首锁）
- **confidence 型/必填**——
  "high" not number / pop required
- **parent_id 无引用完整性**——
  跨文档串 / 自引用 / 空串全 VALID
  （schema 不查存在性首锁）
- **文档级 metadata 开放**——
  嵌套杂值 extra key VALID +
  pop required + int not object
- forbidden tokens 第七百三十五批（open 2）
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


# ---------- 基态 ----------

def test_combo_base_valid_batch473(combo_doc):
    validate(combo_doc, "document.schema.json")


def test_combo_confidence_default_batch473(combo_doc):
    assert [e["confidence"] for e in combo_doc["elements"]] == [
        0.85, 0.85]


def test_combo_parent_id_none_batch473(combo_doc):
    assert all(e["parent_id"] is None
               for e in combo_doc["elements"])


def test_combo_doc_metadata_keys_batch473(combo_doc):
    assert set(combo_doc["metadata"]) == {
        "fallback", "image_output_dir"}
    assert combo_doc["metadata"]["fallback"] is True


# ---------- confidence 上界 ----------

def test_conf_101_max_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d["elements"][0].update(
        {"confidence": 1.01}))
    assert errs[0]["message"] == \
        "1.01 is greater than the maximum of 1"
    assert errs[0]["path"] == ["elements", 0, "confidence"]


def test_conf_2_max_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d["elements"][0].update(
        {"confidence": 2.0}))
    assert errs[0]["message"] == \
        "2.0 is greater than the maximum of 1"


# ---------- confidence 闭区间 ----------

def test_conf_1_exact_valid_batch473(combo_doc):
    _valid(combo_doc, lambda d: d["elements"][0].update(
        {"confidence": 1}))


def test_conf_0_exact_valid_batch473(combo_doc):
    _valid(combo_doc, lambda d: d["elements"][0].update(
        {"confidence": 0}))


def test_conf_neg_min_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d["elements"][0].update(
        {"confidence": -0.5}))
    assert errs[0]["message"] == \
        "-0.5 is less than the minimum of 0"


# ---------- confidence 型/必填 ----------

def test_conf_str_type_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d["elements"][0].update(
        {"confidence": "high"}))
    assert errs[0]["message"] == "'high' is not of type 'number'"


def test_conf_pop_required_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d["elements"][0].pop(
        "confidence"))
    assert errs[0]["message"] == \
        "'confidence' is a required property"
    assert errs[0]["path"] == ["elements", 0]


# ---------- parent_id 无引用完整性 ----------

def test_pid_cross_doc_valid_batch473(combo_doc):
    _valid(combo_doc, lambda d: d["elements"][0].update(
        {"parent_id": "doc-other::e999"}))


def test_pid_self_ref_valid_batch473(combo_doc):
    _valid(combo_doc, lambda d: d["elements"][0].update(
        {"parent_id": d["elements"][0]["element_id"]}))


def test_pid_empty_str_valid_batch473(combo_doc):
    _valid(combo_doc, lambda d: d["elements"][0].update(
        {"parent_id": ""}))


def test_pid_int_type_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d["elements"][0].update(
        {"parent_id": 5}))
    assert errs[0]["message"] == \
        "5 is not of type 'string', 'null'"


def test_pid_pop_required_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d["elements"][0].pop(
        "parent_id"))
    assert errs[0]["message"] == \
        "'parent_id' is a required property"


# ---------- 文档级 metadata 开放 ----------

def test_docmeta_extra_nested_valid_batch473(combo_doc):
    _valid(combo_doc, lambda d: d["metadata"].update(
        {"custom": [1, 2, {"x": None}]}))


def test_docmeta_pop_required_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d.pop("metadata"))
    assert errs[0]["message"] == "'metadata' is a required property"
    assert errs[0]["path"] == []


def test_docmeta_int_type_batch473(combo_doc):
    errs = _reject(combo_doc, lambda d: d.update({"metadata": 5}))
    assert errs[0]["message"] == "5 is not of type 'object'"
    assert errs[0]["path"] == ["metadata"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch473():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百三十五批 ----------

def test_source_no_eval_batch473():
    assert "eval(" not in _src()


def test_source_no_exec_batch473():
    assert "exec(" not in _src()


def test_source_no_compile_batch473():
    assert "compile(" not in _src()


def test_source_no_globals_batch473():
    assert "globals(" not in _src()


def test_source_no_locals_batch473():
    assert "locals(" not in _src()


def test_source_no_os_system_batch473():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch473():
    assert "subprocess" not in _src()


def test_source_no_popen_batch473():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch473():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch473():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch473():
    assert "socket" not in _src()


def test_source_no_requests_batch473():
    assert "requests" not in _src()


def test_source_no_urllib_batch473():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch473():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch473():
    assert "yield" not in _src()


def test_source_no_async_await_batch473():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch473():
    assert _src().count("open(") == 2
