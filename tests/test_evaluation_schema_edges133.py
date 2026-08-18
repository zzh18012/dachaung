"""evaluation/schema.py 第五百六十七轮 edges 测试（Round 1224）。

补强 edges132 未触及的角度（第五百九十六批，probe 实证）。

新角度（source_type 枚举跨层宽窄 / 元素封闭 / 空元素容让）：
- **文档枚举宽于清单**——document
  schema source_type 枚举 [pdf,
  docx, markdown, html, text,
  ipynb]；manifest 层只收
  [pdf, docx]（两层宽窄对照首锁）
- **非 pdf/docx 全要定位键**——改
  markdown/html/text → "'line' is
  a required property"（locator
  if/then 只特判 pdf 与 docx，其
  余走 line 分支首锁）
- **ipynb 要 cell_index**——2 错，
  首错 "'cell_index' is a required
  property"
- **元素封闭**——element 加 "foo"
  → "Additional properties are
  not allowed ('foo' was
  unexpected)"
- **空元素表容让**——elements []
  + chunks [] → VALID
- forbidden tokens 第六百九十三批（open 2）
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
         b"(Schema board round one two three.) Tj ET\n")
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


# ---------- source_type 枚举跨层宽窄 ----------

def test_source_type_markdown_needs_line_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.update(
            {"source_type": "markdown"})), "document.schema.json")
    assert _head(ei)["message"] == \
        "'line' is a required property"
    assert _head(ei)["path"] == [
        "elements", 0, "source_locator"]


def test_source_type_html_needs_line_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.update(
            {"source_type": "html"})), "document.schema.json")
    assert _head(ei)["message"] == \
        "'line' is a required property"
    assert _head(ei)["path"] == [
        "elements", 0, "source_locator"]


def test_source_type_txt_rejected_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.update(
            {"source_type": "txt"})), "document.schema.json")
    assert "'txt' is not one of ['pdf', 'docx', 'markdown', " \
           "'html', 'text', 'ipynb']" in _head(ei)["message"]
    assert _head(ei)["path"] == ["source_type"]


def test_source_type_text_needs_line_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.update(
            {"source_type": "text"})), "document.schema.json")
    assert _head(ei)["message"] == \
        "'line' is a required property"
    assert _head(ei)["path"] == [
        "elements", 0, "source_locator"]


def test_source_type_ipynb_needs_cell_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x.update(
            {"source_type": "ipynb"})), "document.schema.json")
    assert len(ei.value.errors) == 2
    assert _head(ei)["message"] == \
        "'cell_index' is a required property"
    assert _head(ei)["path"] == [
        "elements", 0, "source_locator"]


# ---------- 元素封闭 / 必填 ----------

def test_element_extra_key_rejected_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["elements"][0].update(
            {"foo": 1})), "document.schema.json")
    assert _head(ei)["message"] == \
        "Additional properties are not allowed " \
        "('foo' was unexpected)"
    assert _head(ei)["path"] == ["elements", 0]


def test_element_type_required_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["elements"][0].pop(
            "type")), "document.schema.json")
    assert _head(ei)["message"] == \
        "'type' is a required property"
    assert _head(ei)["path"] == ["elements", 0]


def test_chunk_id_required_batch422(base_doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(_mut(base_doc, lambda x: x["chunks"][0].pop(
            "chunk_id")), "document.schema.json")
    assert _head(ei)["message"] == \
        "'chunk_id' is a required property"
    assert _head(ei)["path"] == ["chunks", 0]


# ---------- 空元素表容让 ----------

def test_elements_empty_valid_batch422(base_doc):
    validate(_mut(base_doc, lambda x: x.update(
        {"elements": [], "chunks": []})),
        "document.schema.json")


def test_metadata_nested_valid_batch422(base_doc):
    validate(_mut(base_doc, lambda x: x["elements"][0].update(
        {"metadata": {"a": {"b": [1, 2]}}})),
        "document.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch422():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第六百九十三批 ----------

def test_source_no_eval_batch422():
    assert "eval(" not in _src()


def test_source_no_exec_batch422():
    assert "exec(" not in _src()


def test_source_no_compile_batch422():
    assert "compile(" not in _src()


def test_source_no_globals_batch422():
    assert "globals(" not in _src()


def test_source_no_locals_batch422():
    assert "locals(" not in _src()


def test_source_no_os_system_batch422():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch422():
    assert "subprocess" not in _src()


def test_source_no_popen_batch422():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch422():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch422():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch422():
    assert "socket" not in _src()


def test_source_no_requests_batch422():
    assert "requests" not in _src()


def test_source_no_urllib_batch422():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch422():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch422():
    assert "yield" not in _src()


def test_source_no_async_await_batch422():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch422():
    assert _src().count("open(") == 2
