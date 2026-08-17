"""evaluation/schema.py 第三百二十轮 edges 测试（Round 876）。

补强 edges93 未触及的角度（第二百五十一批，probe 实证）。

新角度：
- document.schema.json：properties 与 required 恰好同集
  （13 项，无可选顶层键）
- document $defs 恰 12 个且名称锁定（含各 format 的
  locator 与 source_span）
- manifest $defs 两个（document / expected_failure），
  required 分别 3 项
- manifest 顶层 properties 恰 4 项（expected_failures
  可选）
- report summary $def：无 required + additionalProperties
  True（聚合结构自由）
- validate_file 校验合法 annotation 文件 → None
- forbidden tokens 第三百四十六批
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from evaluation.schema import (
    load_schema,
    validate_file,
)


# ---------- document 顶层 ----------

def test_document_props_equal_required_batch74():
    s = load_schema("document.schema.json")
    assert sorted(s["properties"]) == sorted(s["required"])
    assert len(s["required"]) == 13


def test_document_defs_twelve_named_batch74():
    s = load_schema("document.schema.json")
    assert sorted(s["$defs"]) == [
        "chunk", "docx_locator", "element", "error",
        "html_locator", "ipynb_locator", "markdown_locator",
        "pdf_locator", "relation", "source_span",
        "text_locator", "warning"]


# ---------- manifest $defs ----------

def test_manifest_defs_two_batch74():
    s = load_schema("manifest.schema.json")
    assert list(s["$defs"]) == ["document",
                                "expected_failure"]
    assert s["$defs"]["document"]["required"] == [
        "doc_id", "path", "source_type"]
    assert s["$defs"]["document"][
        "additionalProperties"] is False


def test_manifest_ef_def_required_three_batch74():
    s = load_schema("manifest.schema.json")
    assert s["$defs"]["expected_failure"]["required"] == [
        "doc_id", "path", "expected_error_code"]


def test_manifest_props_four_batch74():
    s = load_schema("manifest.schema.json")
    assert sorted(s["properties"]) == [
        "devset_status", "documents", "expected_failures",
        "manifest_version"]


# ---------- report summary 自由 ----------

def test_report_summary_def_freeform_batch74():
    s = load_schema("evaluation-report.schema.json")
    sm = s["$defs"]["summary"]
    assert "required" not in sm
    assert sm["additionalProperties"] is True


# ---------- validate_file annotation ----------

def test_validate_file_annotation_ok_batch74(tmp_path):
    f = tmp_path / "a.json"
    f.write_text('{"annotation_version": "1.0", '
                 '"doc_id": "d1"}', encoding="utf-8")
    assert validate_file(f, "annotation.schema.json") is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch74():
    src = _src()
    assert 'validator = Draft202012Validator(schema)' in src
    assert 'f"Schema \'{schema_name}\' 校验失败 ({len(errors)} 处)："' in src
    assert "p = Path(path)" in src


# ---------- forbidden tokens 第三百四十六批 ----------

def test_source_no_eval_batch74():
    assert "eval(" not in _src()


def test_source_no_exec_batch74():
    assert "exec(" not in _src()


def test_source_no_compile_batch74():
    assert "compile(" not in _src()


def test_source_no_globals_batch74():
    assert "globals(" not in _src()


def test_source_no_locals_batch74():
    assert "locals(" not in _src()


def test_source_no_os_system_batch74():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch74():
    assert "subprocess" not in _src()


def test_source_no_popen_batch74():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch74():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch74():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch74():
    assert "socket" not in _src()


def test_source_no_requests_batch74():
    assert "requests" not in _src()


def test_source_no_urllib_batch74():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch74():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch74():
    assert "yield" not in _src()


def test_source_no_async_await_batch74():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch74():
    assert _src().count("open(") == 2
