"""evaluation/schema.py 第四百四十六轮 edges 测试（Round 1002）。

补强 edges112 未触及的角度（第三百七十八批，probe 实证）。

新角度（跨 4 个 schema 文件的结构一致性）：
- 4 个 schema 共享完全相同的 $schema（draft 2020-12 URI）
- 4 个根节点全部 type object + 有 properties + 有 title
  （title 各带版本：v1.0×2 / v1.1 / v0.1）
- allOf 只在 document.schema.json（6 条），其余 3 个为 0
- 根闭包三分：MS/AS/RS 显式 additionalProperties false，
  document 根**无此键**（开放根，唯一例外）
- validate 两次同坏实例 → errors 列表逐项相等（确定性）
- 最小坏清单 {"manifest_version": "1.0"} → 恰 2 错、首个
  "devset_status" is a required property @ path=[]
- forbidden tokens 第四百七十二批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import load_schema, validate, EvalSchemaError

_NAMES = ["manifest.schema.json", "annotation.schema.json",
          "evaluation-report.schema.json", "document.schema.json"]


def _all():
    return {n: load_schema(n) for n in _NAMES}


# ---------- 共享 draft URI ----------

def test_all_four_share_draft_uri_batch200():
    uris = {s.get("$schema") for s in _all().values()}
    assert uris == {"https://json-schema.org/draft/2020-12/schema"}


# ---------- 根结构 ----------

def test_all_roots_object_with_properties_batch200():
    for s in _all().values():
        assert s["type"] == "object"
        assert "properties" in s


def test_titles_versioned_batch200():
    titles = {n: load_schema(n)["title"] for n in _NAMES}
    assert titles == {
        "manifest.schema.json": "Evaluation Manifest v1.0",
        "annotation.schema.json": "Human Annotation v1.0",
        "evaluation-report.schema.json": "Evaluation Report v1.1",
        "document.schema.json": "KVFS Document Model v0.1"}


# ---------- allOf 分布 ----------

def test_allof_only_in_document_batch200():
    counts = {n: len(load_schema(n).get("allOf", []))
              for n in _NAMES}
    assert counts == {
        "manifest.schema.json": 0,
        "annotation.schema.json": 0,
        "evaluation-report.schema.json": 0,
        "document.schema.json": 6}


# ---------- 根闭包三分 ----------

def test_root_closed_except_document_batch200():
    for n in _NAMES:
        s = load_schema(n)
        if n == "document.schema.json":
            assert "additionalProperties" not in s
        else:
            assert s["additionalProperties"] is False


# ---------- 确定性 ----------

def test_validate_deterministic_batch200():
    bad = {"manifest_version": "1.0"}
    errs = []
    for _ in range(2):
        with pytest.raises(EvalSchemaError) as ei:
            validate(bad, "manifest.schema.json")
        errs.append(ei.value.errors)
    assert errs[0] == errs[1]


# ---------- 最小坏清单 ----------

def test_minimal_manifest_bad_two_errors_batch200():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": "1.0"},
                 "manifest.schema.json")
    errs = ei.value.errors
    assert len(errs) == 2
    assert errs[0]["path"] == []
    assert errs[0]["message"] == \
        "'devset_status' is a required property"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch200():
    src = _src()
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent / \"schemas\"" in src
    assert "super().__init__(message)" in src
    assert '"path": list(err.absolute_path),' in src
    assert "p = Path(path)" in src


# ---------- forbidden tokens 第四百七十二批 ----------

def test_source_no_eval_batch200():
    assert "eval(" not in _src()


def test_source_no_exec_batch200():
    assert "exec(" not in _src()


def test_source_no_compile_batch200():
    assert "compile(" not in _src()


def test_source_no_globals_batch200():
    assert "globals(" not in _src()


def test_source_no_locals_batch200():
    assert "locals(" not in _src()


def test_source_no_os_system_batch200():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch200():
    assert "subprocess" not in _src()


def test_source_no_popen_batch200():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch200():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch200():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch200():
    assert "socket" not in _src()


def test_source_no_requests_batch200():
    assert "requests" not in _src()


def test_source_no_urllib_batch200():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch200():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch200():
    assert "yield" not in _src()


def test_source_no_async_await_batch200():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch200():
    assert _src().count("open(") == 2
