"""evaluation/schema.py 第五百七十八轮 edges 测试（Round 1287）。

补强 edges142 未触及的角度（第六百五十九批，probe 实证）。

新角度（bbox 上界 / locator 开放面 / 翻转不对称 / 布尔置信 / relation 变异）：
- **bbox 过长**——5 项 / 6 项 →
  "[0, 0, 100, 100, 100] is too
  long"（上界首锁，补 edges137
  过短侧）
- **pdf_locator 开放**——额外键
  zoom: 2 → VALID
  （additionalProperties true）
- **翻转不对称**——PDF 文档翻
  source_type=docx 且保留
  page/bbox locator → VALID
  （docx_locator 开放收纳；
  区别于 edges127 docx→pdf
  拒绝方向）
- **docx 索引负值**——
  run_index/paragraph_index
  -1 → "-1 is less than the
  minimum of 0"
- **布尔置信**——confidence
  True/False → "True/False is
  not of type 'number'"
  （bool 非 number 的
  jsonschema 语义首锁）
- **relation 变异**——额外键
  weight 拒 / from_id 空串拒 /
  缺 type 拒 / 最小三元 VALID
- forbidden tokens 第七百四十六批（open 2）
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from app.pipeline import process_single
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


def _doc(tmp_path):
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


def _reject(tmp_path, fn, message, path):
    import copy
    d = copy.deepcopy(_doc(tmp_path))
    fn(d)
    try:
        validate(d, "document.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert e.errors[0]["path"] == path
    else:
        raise AssertionError("expected rejection")


def _accept(tmp_path, fn):
    import copy
    d = copy.deepcopy(_doc(tmp_path))
    fn(d)
    validate(d, "document.schema.json")


BBOX_PATH = ["elements", 0, "source_locator", "bbox"]


# ---------- bbox 过长 ----------

def test_bbox_five_too_long_batch485(tmp_path):
    _reject(tmp_path, lambda d: d["elements"][0][
        "source_locator"].update(
        {"bbox": [0, 0, 100, 100, 100]}),
        "[0, 0, 100, 100, 100] is too long", BBOX_PATH)


def test_bbox_six_too_long_batch485(tmp_path):
    _reject(tmp_path, lambda d: d["elements"][0][
        "source_locator"].update(
        {"bbox": [0, 0, 100, 100, 100, 100]}),
        "[0, 0, 100, 100, 100, 100] is too long", BBOX_PATH)


# ---------- pdf_locator 开放面 ----------

def test_pdf_locator_zoom_open_batch485(tmp_path):
    _accept(tmp_path, lambda d: d["elements"][0][
        "source_locator"].update({"zoom": 2}))


# ---------- 翻转不对称 ----------

def test_flip_to_docx_pdf_locators_valid_batch485(tmp_path):
    _accept(tmp_path, lambda d: d.update(
        {"source_type": "docx"}))


# ---------- docx 索引负值 ----------

def test_run_index_negative_batch485(tmp_path):
    def fn(d):
        d["source_type"] = "docx"
        d["elements"][0]["source_locator"] = {
            "run_index": -1}
    _reject(tmp_path, fn, "-1 is less than the minimum of 0",
            ["elements", 0, "source_locator", "run_index"])


def test_paragraph_index_negative_batch485(tmp_path):
    def fn(d):
        d["source_type"] = "docx"
        d["elements"][0]["source_locator"] = {
            "paragraph_index": -1}
    _reject(tmp_path, fn, "-1 is less than the minimum of 0",
            ["elements", 0, "source_locator",
             "paragraph_index"])


# ---------- 布尔置信 ----------

def test_confidence_true_rejected_batch485(tmp_path):
    _reject(tmp_path, lambda d: d["elements"][0].update(
        {"confidence": True}),
        "True is not of type 'number'",
        ["elements", 0, "confidence"])


def test_confidence_false_rejected_batch485(tmp_path):
    _reject(tmp_path, lambda d: d["elements"][0].update(
        {"confidence": False}),
        "False is not of type 'number'",
        ["elements", 0, "confidence"])


# ---------- relation 变异 ----------

def test_relation_extra_weight_batch485(tmp_path):
    def fn(d):
        d["relations"] = [{"type": "next", "from_id": "a",
                           "to_id": "b", "weight": 2}]
    _reject(tmp_path, fn,
            "Additional properties are not allowed "
            "('weight' was unexpected)",
            ["relations", 0])


def test_relation_empty_from_id_batch485(tmp_path):
    def fn(d):
        d["relations"] = [{"type": "next", "from_id": "",
                           "to_id": "b"}]
    _reject(tmp_path, fn, "'' should be non-empty",
            ["relations", 0, "from_id"])


def test_relation_missing_type_batch485(tmp_path):
    def fn(d):
        d["relations"] = [{"from_id": "a", "to_id": "b"}]
    _reject(tmp_path, fn, "'type' is a required property",
            ["relations", 0])


def test_relation_minimal_valid_batch485(tmp_path):
    _accept(tmp_path, lambda d: d.update(
        {"relations": [{"type": "next", "from_id": "a",
                        "to_id": "b"}]}))


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch485():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百四十六批 ----------

def test_source_no_eval_batch485():
    assert "eval(" not in _src()


def test_source_no_exec_batch485():
    assert "exec(" not in _src()


def test_source_no_compile_batch485():
    assert "compile(" not in _src()


def test_source_no_globals_batch485():
    assert "globals(" not in _src()


def test_source_no_locals_batch485():
    assert "locals(" not in _src()


def test_source_no_os_system_batch485():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch485():
    assert "subprocess" not in _src()


def test_source_no_popen_batch485():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch485():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch485():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch485():
    assert "socket" not in _src()


def test_source_no_requests_batch485():
    assert "requests" not in _src()


def test_source_no_urllib_batch485():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch485():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch485():
    assert "yield" not in _src()


def test_source_no_async_await_batch485():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch485():
    assert _src().count("open(") == 2
