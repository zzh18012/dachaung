"""evaluation/schema.py 第三百四十二轮 edges 测试（Round 898）。

补强 edges96 未触及的角度（第二百七十四批，probe 实证）。

新角度：
- locator 家族 required 差异：docx_locator 无 required 键（六 locator
  唯一）；markdown/html/text_locator 均 ["line"]；ipynb_locator
  ["cell_index", "cell_type"]
- relation [type, from_id, to_id] / warning [code, reason] /
  error [code, message] 三 def 全封闭（addProps False）
- element def 封闭 + props 恰 8 项排序
- boundary_anchor props 恰 [marker, position, reason]
- expected_failure_result required 4 且 props==required
- validate 传 list 实例 → "[1, 2] is not of type 'object' @ path=[]"
- load_schema 无缓存（两次加载身份不同；改动不影响后续加载）
- __all__ 五项顺序
- forbidden tokens 第三百六十八批
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, load_schema, validate


# ---------- locator 家族 required ----------

def test_docx_locator_no_required_batch96():
    d = load_schema("document.schema.json")["$defs"]["docx_locator"]
    assert "required" not in d


def test_line_family_locators_batch96():
    d = load_schema("document.schema.json")["$defs"]
    for name in ("markdown_locator", "html_locator",
                 "text_locator"):
        assert d[name]["required"] == ["line"], name


def test_ipynb_locator_required_batch96():
    d = load_schema("document.schema.json")["$defs"]["ipynb_locator"]
    assert d["required"] == ["cell_index", "cell_type"]


# ---------- 三个封闭 def ----------

def test_relation_warning_error_closed_batch96():
    d = load_schema("document.schema.json")["$defs"]
    assert d["relation"]["required"] == \
        ["type", "from_id", "to_id"]
    assert d["relation"]["additionalProperties"] is False
    assert d["warning"]["required"] == ["code", "reason"]
    assert d["warning"]["additionalProperties"] is False
    assert d["error"]["required"] == ["code", "message"]
    assert d["error"]["additionalProperties"] is False


# ---------- element 封闭 8 props ----------

def test_element_closed_eight_props_batch96():
    e = load_schema("document.schema.json")["$defs"]["element"]
    assert e["additionalProperties"] is False
    assert sorted(e["properties"]) == [
        "confidence", "content", "element_id", "metadata",
        "parent_id", "resource_path", "source_locator", "type",
    ]


# ---------- boundary_anchor props ----------

def test_anchor_props_three_batch96():
    a = load_schema("annotation.schema.json")["$defs"][
        "boundary_anchor"]
    assert sorted(a["properties"]) == ["marker", "position",
                                       "reason"]


# ---------- expected_failure_result ----------

def test_efr_required_four_batch96():
    efr = load_schema("evaluation-report.schema.json")["$defs"][
        "expected_failure_result"]
    assert sorted(efr["required"]) == [
        "actual_error_code", "doc_id", "expected_error_code",
        "matches",
    ]
    assert sorted(efr["properties"]) == sorted(efr["required"])


# ---------- list 实例 ----------

def test_validate_list_instance_batch96():
    try:
        validate([1, 2], "manifest.schema.json")
        raise AssertionError("should raise")
    except EvalSchemaError as e:
        assert "is not of type 'object' @ path=[]" in str(e)


# ---------- 无缓存 ----------

def test_load_schema_not_cached_batch96():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2
    s1["mutated_marker"] = True
    s3 = load_schema("manifest.schema.json")
    assert "mutated_marker" not in s3


# ---------- __all__ ----------

def test_all_exports_order_batch96():
    assert schema_mod.__all__ == [
        "SCHEMAS_DIR", "EvalSchemaError", "load_schema",
        "validate", "validate_file",
    ]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch96():
    src = _src()
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src
    assert ("errors = sorted(validator.iter_errors(instance), "
            "key=lambda e: list(e.absolute_path))") in src


# ---------- forbidden tokens 第三百六十八批 ----------

def test_source_no_eval_batch96():
    assert "eval(" not in _src()


def test_source_no_exec_batch96():
    assert "exec(" not in _src()


def test_source_no_compile_batch96():
    assert "compile(" not in _src()


def test_source_no_globals_batch96():
    assert "globals(" not in _src()


def test_source_no_locals_batch96():
    assert "locals(" not in _src()


def test_source_no_os_system_batch96():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch96():
    assert "subprocess" not in _src()


def test_source_no_popen_batch96():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch96():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch96():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch96():
    assert "socket" not in _src()


def test_source_no_requests_batch96():
    assert "requests" not in _src()


def test_source_no_urllib_batch96():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch96():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch96():
    assert "yield" not in _src()


def test_source_no_async_await_batch96():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch96():
    assert _src().count("open(") == 2
