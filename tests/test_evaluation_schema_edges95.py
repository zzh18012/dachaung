"""evaluation/schema.py 第三百二十七轮 edges 测试（Round 883）。

补强 edges94 未触及的角度（第二百五十八批，probe 实证）。

新角度：
- 四个 Schema 的 $id 均为 kvfs.local 命名空间 +
  $schema 均 Draft 2020-12
- annotation 顶层 properties 恰 7 项
- evaluation-report 顶层 properties 恰 6 项
  （expected_failures 唯一可选）
- report per_doc properties 与 required 同集（4 项）
- devset_status enum 直接锁定 ["complete",
  "incomplete"]
- forbidden tokens 第三百五十三批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import load_schema

_ALL = ["manifest.schema.json", "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json"]


# ---------- $id / $schema ----------

@pytest.mark.parametrize("name", _ALL)
def test_schema_id_and_draft_batch81(name):
    s = load_schema(name)
    short = name.removesuffix(".schema.json")
    assert s["$id"] == \
        f"https://kvfs.local/schemas/{name}"
    assert short in s["$id"]
    assert s["$schema"] == \
        "https://json-schema.org/draft/2020-12/schema"


# ---------- annotation properties ----------

def test_annotation_props_seven_batch81():
    s = load_schema("annotation.schema.json")
    assert sorted(s["properties"]) == [
        "annotation_version", "annotator",
        "chunk_boundary_anchors", "date", "doc_id",
        "figure_caption_pairs", "heading_order"]


# ---------- report properties ----------

def test_report_props_six_batch81():
    s = load_schema("evaluation-report.schema.json")
    assert sorted(s["properties"]) == [
        "devset", "expected_failures", "per_doc",
        "provenance", "report_version", "summary"]


def test_report_per_doc_props_equal_required_batch81():
    s = load_schema("evaluation-report.schema.json")
    d = s["$defs"]["per_doc"]
    assert sorted(d["properties"]) == sorted(d["required"])


# ---------- devset enum ----------

def test_devset_status_enum_batch81():
    s = load_schema("manifest.schema.json")
    assert s["properties"]["devset_status"]["enum"] == [
        "complete", "incomplete"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch81():
    src = _src()
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src
    assert "class EvalSchemaError(Exception):" in src
    assert 'raise EvalSchemaError(' in src


# ---------- forbidden tokens 第三百五十三批 ----------

def test_source_no_eval_batch81():
    assert "eval(" not in _src()


def test_source_no_exec_batch81():
    assert "exec(" not in _src()


def test_source_no_compile_batch81():
    assert "compile(" not in _src()


def test_source_no_globals_batch81():
    assert "globals(" not in _src()


def test_source_no_locals_batch81():
    assert "locals(" not in _src()


def test_source_no_os_system_batch81():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch81():
    assert "subprocess" not in _src()


def test_source_no_popen_batch81():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch81():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch81():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch81():
    assert "socket" not in _src()


def test_source_no_requests_batch81():
    assert "requests" not in _src()


def test_source_no_urllib_batch81():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch81():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch81():
    assert "yield" not in _src()


def test_source_no_async_await_batch81():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch81():
    assert _src().count("open(") == 2
