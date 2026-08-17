"""evaluation/schema.py 第三百七十六轮 edges 测试（Round 932）。

补强 edges102 未触及的角度（第三百零八批，probe 实证）。

新角度：
- load_schema 不缓存：两次加载相等但非同一对象
- ghost schema 名 → FileNotFoundError，消息含 SCHEMAS_DIR
  绝对路径与文件名
- validate_file 传目录（is_file False）→ FileNotFoundError
  "待校验文件不存在: <目录绝对路径>"
- validate_file 磁盘 JSON 语法错 → json.JSONDecodeError 直接
  冒出（不是 EvalSchemaError）
- annotation 顶层字段实证：必需 annotation_version + doc_id；
  "document_id" 是 additionalProperties 被拒
- 多错误排序与 flat 键序：path=[]（required 先于
  additionalProperties，稳定排序）再 [chunk_boundary_
  anchors, 0] 再 [.., 1]；每个 flat 键序 [path, message,
  schema_path]，schema_path 末尾 ["items", "required"]
- validate() 每次调用都重新 load_schema（无缓存，patch 计数
  两次 validate → 2 次调用）
- annotation_version 写 "9.9" → "'1.0' was expected @
  path=['annotation_version']"（const 单处）
- position "sideways" → "'sideways' is not one of
  ['before', 'after']"（enum 单处）
- 合法最小实例 validate / validate_file(str 路径) 均 None
- forbidden tokens 第四百零二批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)

_OK = {"annotation_version": "1.0", "doc_id": "d"}


# ---------- load_schema 不缓存 ----------

def test_load_schema_not_cached_batch130():
    s1 = load_schema("annotation.schema.json")
    s2 = load_schema("annotation.schema.json")
    assert s1 == s2
    assert s1 is not s2
    assert isinstance(s1, dict)


# ---------- ghost schema 名 ----------

def test_ghost_schema_file_not_found_batch130():
    with pytest.raises(FileNotFoundError) as ei:
        load_schema("ghost.schema.json")
    msg = str(ei.value)
    assert msg.startswith("Schema 文件不存在: ")
    assert str(SCHEMAS_DIR) in msg
    assert msg.endswith("ghost.schema.json")


# ---------- validate_file 目录 ----------

def test_validate_file_directory_batch130():
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(SCHEMAS_DIR, "annotation.schema.json")
    assert str(ei.value) == f"待校验文件不存在: {SCHEMAS_DIR}"


# ---------- 磁盘 JSON 语法错 ----------

def test_validate_file_malformed_json_batch130(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "annotation.schema.json")


# ---------- 顶层字段实证 ----------

def test_annotation_top_fields_batch130(tmp_path):
    with pytest.raises(EvalSchemaError) as ei:
        validate({"document_id": "d"}, "annotation.schema.json")
    msgs = [fe["message"] for fe in ei.value.errors]
    assert "'annotation_version' is a required property" in msgs
    assert "'doc_id' is a required property" in msgs
    assert any("Additional properties are not allowed "
               "('document_id'" in m for m in msgs)


def test_valid_minimal_returns_none_batch130():
    assert validate(_OK, "annotation.schema.json") is None


def test_validate_file_accepts_str_batch130(tmp_path):
    f = tmp_path / "ok.json"
    f.write_text(json.dumps(_OK), encoding="utf-8")
    assert validate_file(str(f), "annotation.schema.json") is None


# ---------- 多错误排序与 flat 键序 ----------

def test_multi_error_sort_and_flat_keys_batch130():
    # document_id 是非法字段（正确名是 doc_id）→ [] 层 2 处；
    # 两个 anchor 缺 marker、第二个多 extra → anchors 层 3 处
    inst = {"annotation_version": "1.0", "document_id": "d",
            "chunk_boundary_anchors": [
                {"position": "before"},
                {"position": "after", "extra": 1}]}
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "annotation.schema.json")
    errs = ei.value.errors
    assert len(errs) == 5
    # 排序：path=[] 的 required 先于 [] 的 additionalProperties
    # （稳定排序保持 iter_errors 顺序），再按 anchor 下标
    assert errs[0]["path"] == []
    assert errs[0]["message"] == "'doc_id' is a required property"
    assert errs[0]["schema_path"][-1] == "required"
    assert errs[1]["path"] == []
    assert errs[1]["message"].startswith(
        "Additional properties are not allowed")
    assert "document_id" in errs[1]["message"]
    assert errs[1]["schema_path"][-1] == "additionalProperties"
    assert errs[2]["path"] == ["chunk_boundary_anchors", 0]
    assert errs[2]["message"] == "'marker' is a required property"
    assert errs[2]["schema_path"][-2:] == ["items", "required"]
    assert errs[3]["path"] == ["chunk_boundary_anchors", 1]
    assert errs[3]["message"] == "'marker' is a required property"
    assert errs[4]["path"] == ["chunk_boundary_anchors", 1]
    assert errs[4]["schema_path"][-2:] == [
        "items", "additionalProperties"]
    for fe in errs:
        assert list(fe) == ["path", "message", "schema_path"]


def test_sort_across_depths_batch130():
    inst = {"chunk_boundary_anchors": [{"position": "before"}]}
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "annotation.schema.json")
    paths = [fe["path"] for fe in ei.value.errors]
    assert paths == [[], [], ["chunk_boundary_anchors", 0]]


# ---------- validate 每次 load ----------

def test_validate_loads_schema_every_call_batch130(monkeypatch):
    calls = []
    orig = schema_mod.load_schema

    def counting(name):
        calls.append(name)
        return orig(name)

    monkeypatch.setattr(schema_mod, "load_schema", counting)
    validate(_OK, "annotation.schema.json")
    validate(_OK, "annotation.schema.json")
    assert calls == ["annotation.schema.json",
                     "annotation.schema.json"]


# ---------- const / enum 单处 ----------

def test_annotation_version_const_batch130():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"annotation_version": "9.9", "doc_id": "d"},
                 "annotation.schema.json")
    assert str(ei.value).startswith(
        "Schema 'annotation.schema.json' 校验失败 (1 处)：")
    assert "'1.0' was expected @ path=['annotation_version']" \
        in str(ei.value)


def test_position_enum_batch130():
    inst = dict(_OK, chunk_boundary_anchors=[
        {"marker": "m", "position": "sideways"}])
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "annotation.schema.json")
    assert "'sideways' is not one of ['before', 'after']" \
        in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch130():
    src = _src()
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert 'raise FileNotFoundError(f"Schema 文件不存在: {p}")' in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src
    assert "head = errors[0]" in src


# ---------- forbidden tokens 第四百零二批 ----------

def test_source_no_eval_batch130():
    assert "eval(" not in _src()


def test_source_no_exec_batch130():
    assert "exec(" not in _src()


def test_source_no_compile_batch130():
    assert "compile(" not in _src()


def test_source_no_globals_batch130():
    assert "globals(" not in _src()


def test_source_no_locals_batch130():
    assert "locals(" not in _src()


def test_source_no_os_system_batch130():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch130():
    assert "subprocess" not in _src()


def test_source_no_popen_batch130():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch130():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch130():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch130():
    assert "socket" not in _src()


def test_source_no_requests_batch130():
    assert "requests" not in _src()


def test_source_no_urllib_batch130():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch130():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch130():
    assert "yield" not in _src()


def test_source_no_async_await_batch130():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch130():
    assert _src().count("open(") == 2
