"""evaluation/schema.py 第五百七十九轮 edges 测试（Round 1293）。

补强 edges143 未触及的角度（第六百六十五批，probe 实证）。

新角度（source_span 运行时闭包）：
- **真板 span 形**——fallback
  板全部 span 键集恰
  {element_id, end, start}
  ；首块 span {doc-<hash>
  ::e0000, 0, 80}（:: 前缀
  命名首锁）
- **运行时闭包**——额外键
  note → "Additional
  properties are not
  allowed"（区别于 locator
  开放面；edges129 仅结构
  断言，运行时首锁）
- **数值域**——start -1 →
  minimum 0；start 1.5 →
  not integer；start/end
  恰 0 VALID（下界含端）
- **必填与串**——缺 end →
  required；element_id 空串
  → non-empty
- **第二 span 坏**——错误
  路径落 [.., 1]（索引定
  位首锁）
- forbidden tokens 第七百五十一批（open 2）
"""

from __future__ import annotations

import copy
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


def _span(tmp_path, spans, message, path):
    d = copy.deepcopy(_doc(tmp_path))
    d["chunks"][0]["source_spans"] = spans
    try:
        validate(d, "document.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert e.errors[0]["path"] == path
    else:
        raise AssertionError("expected rejection")


# ---------- 真板 span 形 ----------

def test_real_spans_shape_batch491(tmp_path):
    dd = _doc(tmp_path)
    keys = {tuple(sorted(sp)) for c in dd["chunks"]
            for sp in c["source_spans"]}
    assert keys == {("element_id", "end", "start")}


def test_real_span_sample_batch491(tmp_path):
    dd = _doc(tmp_path)
    sp = dd["chunks"][0]["source_spans"][0]
    assert sp["start"] == 0
    assert sp["end"] == 80
    assert sp["element_id"].startswith("doc-")
    assert sp["element_id"].endswith("::e0000")


# ---------- 运行时闭包 ----------

def test_span_extra_note_rejected_batch491(tmp_path):
    _span(tmp_path,
          [{"element_id": "e1", "start": 0, "end": 5,
            "note": "x"}],
          "Additional properties are not allowed "
          "('note' was unexpected)",
          ["chunks", 0, "source_spans", 0])


# ---------- 数值域 ----------

def test_span_start_negative_batch491(tmp_path):
    _span(tmp_path,
          [{"element_id": "e1", "start": -1, "end": 5}],
          "-1 is less than the minimum of 0",
          ["chunks", 0, "source_spans", 0, "start"])


def test_span_start_float_batch491(tmp_path):
    _span(tmp_path,
          [{"element_id": "e1", "start": 1.5, "end": 5}],
          "1.5 is not of type 'integer'",
          ["chunks", 0, "source_spans", 0, "start"])


def test_span_boundary_zeros_valid_batch491(tmp_path):
    d = copy.deepcopy(_doc(tmp_path))
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": 0}]
    validate(d, "document.schema.json")


# ---------- 必填与串 ----------

def test_span_missing_end_batch491(tmp_path):
    _span(tmp_path,
          [{"element_id": "e1", "start": 0}],
          "'end' is a required property",
          ["chunks", 0, "source_spans", 0])


def test_span_empty_element_id_batch491(tmp_path):
    _span(tmp_path,
          [{"element_id": "", "start": 0, "end": 5}],
          "'' should be non-empty",
          ["chunks", 0, "source_spans", 0, "element_id"])


# ---------- 第二 span 坏 ----------

def test_span_second_bad_index_path_batch491(tmp_path):
    _span(tmp_path,
          [{"element_id": "e1", "start": 0, "end": 5},
           {"start": 1}],
          "'element_id' is a required property",
          ["chunks", 0, "source_spans", 1])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch491():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百五十一批 ----------

def test_source_no_eval_batch491():
    assert "eval(" not in _src()


def test_source_no_exec_batch491():
    assert "exec(" not in _src()


def test_source_no_compile_batch491():
    assert "compile(" not in _src()


def test_source_no_globals_batch491():
    assert "globals(" not in _src()


def test_source_no_locals_batch491():
    assert "locals(" not in _src()


def test_source_no_os_system_batch491():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch491():
    assert "subprocess" not in _src()


def test_source_no_popen_batch491():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch491():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch491():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch491():
    assert "socket" not in _src()


def test_source_no_requests_batch491():
    assert "requests" not in _src()


def test_source_no_urllib_batch491():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch491():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch491():
    assert "yield" not in _src()


def test_source_no_async_await_batch491():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch491():
    assert _src().count("open(") == 2
