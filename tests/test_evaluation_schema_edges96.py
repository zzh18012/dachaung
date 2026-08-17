"""evaluation/schema.py 第三百三十四轮 edges 测试（Round 890）。

补强 edges95 未触及的角度（第二百六十五批，probe 实证）。

新角度：
- boundary_anchor position enum 恰 ["before","after"]、
  marker type string + minLength 1
- document source_type enum 六值（pdf/docx/markdown/
  html/text/ipynb —— 与 locator $defs 家族对应）
- chunk $defs additionalProperties False
- report provenance / devset 的 properties 与
  required 同集（9 / 6）
- forbidden tokens 第三百六十批
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from evaluation.schema import load_schema


# ---------- boundary_anchor ----------

def test_anchor_position_enum_batch88():
    s = load_schema("annotation.schema.json")
    p = s["$defs"]["boundary_anchor"]["properties"]
    assert p["position"]["enum"] == ["before", "after"]
    assert p["marker"]["type"] == "string"
    assert p["marker"]["minLength"] == 1


# ---------- source_type 六值 ----------

def test_document_source_type_enum_six_batch88():
    s = load_schema("document.schema.json")
    assert s["properties"]["source_type"]["enum"] == [
        "pdf", "docx", "markdown", "html", "text", "ipynb"]


# ---------- chunk 封闭 ----------

def test_chunk_def_closed_batch88():
    s = load_schema("document.schema.json")
    assert s["$defs"]["chunk"][
        "additionalProperties"] is False


# ---------- report 两个 def 同集 ----------

def test_report_prov_devset_props_equal_required_batch88():
    s = load_schema("evaluation-report.schema.json")
    pv = s["$defs"]["provenance"]
    dv = s["$defs"]["devset"]
    assert sorted(pv["properties"]) == sorted(pv["required"])
    assert len(pv["required"]) == 9
    assert sorted(dv["properties"]) == sorted(dv["required"])
    assert len(dv["required"]) == 6


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch88():
    src = _src()
    assert "flat: list[dict[str, Any]] = []" in src
    assert '"schema_path": list(err.absolute_schema_path),' in src
    assert "validator.iter_errors(instance)" in src


# ---------- forbidden tokens 第三百六十批 ----------

def test_source_no_eval_batch88():
    assert "eval(" not in _src()


def test_source_no_exec_batch88():
    assert "exec(" not in _src()


def test_source_no_compile_batch88():
    assert "compile(" not in _src()


def test_source_no_globals_batch88():
    assert "globals(" not in _src()


def test_source_no_locals_batch88():
    assert "locals(" not in _src()


def test_source_no_os_system_batch88():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch88():
    assert "subprocess" not in _src()


def test_source_no_popen_batch88():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch88():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch88():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch88():
    assert "socket" not in _src()


def test_source_no_requests_batch88():
    assert "requests" not in _src()


def test_source_no_urllib_batch88():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch88():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch88():
    assert "yield" not in _src()


def test_source_no_async_await_batch88():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch88():
    assert _src().count("open(") == 2
