"""evaluation/schema.py 第四百一十一轮 edges 测试（Round 967）。

补强 edges107 未触及的角度（第三百四十三批，probe 实证）。

新角度（Schema 可选属性形状 + 封闭清单）：
- 三 $schema 同一 URI
  https://json-schema.org/draft/2020-12/schema；
  三 title：Evaluation Manifest v1.0 /
  Evaluation Report v1.1 / Human Annotation v1.0
- AS 可选属性形状：annotation_version {string, const
  "1.0"}；date {string, minLength 1}；annotator
  {string}；heading_order array（items 封闭 required
  [level, text]，level integer min 1）；figure_caption_
  pairs array（items 封闭 required [figure_marker,
  caption_text]，均 minLength 1）
- MS expectations def：无 required、恰 2 属性
- 封闭清单：expected_failure_result / MS document def /
  MS expected_failure def / boundary_anchor 全
  additionalProperties False
- forbidden tokens 第四百三十七批（open 2）
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from evaluation.schema import load_schema

_MS = load_schema("manifest.schema.json")
_RS = load_schema("evaluation-report.schema.json")
_AS = load_schema("annotation.schema.json")


# ---------- $schema 与 title ----------

def test_schema_uri_and_titles_batch165():
    assert _MS["$schema"] == _RS["$schema"] == \
        _AS["$schema"] == \
        "https://json-schema.org/draft/2020-12/schema"
    assert _MS["title"] == "Evaluation Manifest v1.0"
    assert _RS["title"] == "Evaluation Report v1.1"
    assert _AS["title"] == "Human Annotation v1.0"


# ---------- AS 可选属性形状 ----------

def test_as_optional_prop_shapes_batch165():
    p = _AS["properties"]
    assert p["annotation_version"] == {"type": "string",
                                       "const": "1.0"}
    assert p["date"] == {"type": "string", "minLength": 1}
    assert p["annotator"] == {"type": "string"}


def test_as_heading_order_shape_batch165():
    ho = _AS["properties"]["heading_order"]
    assert ho["type"] == "array"
    item = ho["items"]
    assert item["required"] == ["level", "text"]
    assert item["additionalProperties"] is False
    assert item["properties"]["level"] == {
        "type": "integer", "minimum": 1}


def test_as_figure_caption_pairs_shape_batch165():
    fcp = _AS["properties"]["figure_caption_pairs"]
    item = fcp["items"]
    assert item["required"] == ["figure_marker",
                                "caption_text"]
    assert item["additionalProperties"] is False
    assert item["properties"]["figure_marker"] == {
        "type": "string", "minLength": 1}
    assert item["properties"]["caption_text"] == {
        "type": "string", "minLength": 1}


# ---------- MS expectations def ----------

def test_expectations_def_no_required_batch165():
    exp = _MS["$defs"]["document"]["properties"][
        "expectations"]
    assert exp.get("required") is None
    assert sorted(exp["properties"]) == [
        "element_count_by_type", "required_markers"]


# ---------- 封闭清单 ----------

def test_closure_map_batch165():
    assert _RS["$defs"]["expected_failure_result"][
        "additionalProperties"] is False
    assert _MS["$defs"]["document"][
        "additionalProperties"] is False
    assert _MS["$defs"]["expected_failure"][
        "additionalProperties"] is False
    assert _AS["$defs"]["boundary_anchor"][
        "additionalProperties"] is False


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch165():
    src = _src()
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src
    assert "from jsonschema import Draft202012Validator" in src
    assert "self.errors = errors or []" in src


# ---------- forbidden tokens 第四百三十七批 ----------

def test_source_no_eval_batch165():
    assert "eval(" not in _src()


def test_source_no_exec_batch165():
    assert "exec(" not in _src()


def test_source_no_compile_batch165():
    assert "compile(" not in _src()


def test_source_no_globals_batch165():
    assert "globals(" not in _src()


def test_source_no_locals_batch165():
    assert "locals(" not in _src()


def test_source_no_os_system_batch165():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch165():
    assert "subprocess" not in _src()


def test_source_no_popen_batch165():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch165():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch165():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch165():
    assert "socket" not in _src()


def test_source_no_requests_batch165():
    assert "requests" not in _src()


def test_source_no_urllib_batch165():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch165():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch165():
    assert "yield" not in _src()


def test_source_no_async_await_batch165():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch165():
    assert _src().count("open(") == 2
