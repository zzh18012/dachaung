"""evaluation/schema.py 第四百二十五轮 edges 测试（Round 981）。

补强 edges109 未触及的角度（第三百五十七批，probe 实证）。

新角度：
- MS 字符串属性形状：annotation_file / paired_with 均仅
  {"type": "string"}（无 minLength，解释了 R976 的空串放行）、
  categories items 同、sha256 pattern 精确值
- source_type enum 不对称：document 恰 [pdf, docx]，
  expected_failure 四值 [pdf, docx, txt, other] → ef 传
  "txt" 合法、document 传 "txt" 被拒
- expectations.element_count_by_type 负计数 → "-1 is less
  than the minimum of 0"（5 层深路径）
- expectations.required_markers 空串 marker → non-empty
- devset_status "partial" → 不在 enum ['complete',
  'incomplete']
- ef expected_error_code "" → non-empty
- forbidden tokens 第四百五十一批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, load_schema, validate


def _base():
    return {"manifest_version": "1.0",
            "devset_status": "incomplete", "documents": []}


def _rej(data):
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, "manifest.schema.json")
    return ei.value.errors[0]


# ---------- 字符串属性形状 ----------

def test_ms_string_prop_shapes_batch179():
    ms = load_schema("manifest.schema.json")
    props = ms["$defs"]["document"]["properties"]
    assert props["annotation_file"] == {"type": "string"}
    assert props["paired_with"] == {"type": "string"}
    assert props["categories"]["items"] == {"type": "string"}
    assert props["sha256"] == {
        "type": "string", "pattern": "^[0-9a-f]{64}$"}


# ---------- source_type enum 不对称 ----------

def test_source_type_enum_asymmetry_batch179():
    ms = load_schema("manifest.schema.json")
    doc_enum = ms["$defs"]["document"]["properties"][
        "source_type"]["enum"]
    ef_enum = ms["$defs"]["expected_failure"]["properties"][
        "source_type"]["enum"]
    assert doc_enum == ["pdf", "docx"]
    assert ef_enum == ["pdf", "docx", "txt", "other"]

    flat = _rej({**_base(), "documents": [
        {"doc_id": "d", "path": "a.pdf",
         "source_type": "txt"}]})
    assert flat["message"] == \
        "'txt' is not one of ['pdf', 'docx']"
    assert flat["path"] == ["documents", 0, "source_type"]

    validate({**_base(), "expected_failures": [
        {"doc_id": "e", "path": "b.txt",
         "expected_error_code": "E_X", "source_type": "txt"}]},
        "manifest.schema.json")


# ---------- 负计数 ----------

def test_negative_expected_count_rejected_batch179():
    flat = _rej({**_base(), "documents": [
        {"doc_id": "d", "path": "a.pdf", "source_type": "pdf",
         "expectations": {"element_count_by_type":
                          {"paragraph": -1}}}]})
    assert flat["message"] == \
        "-1 is less than the minimum of 0"
    assert flat["path"] == ["documents", 0, "expectations",
                            "element_count_by_type", "paragraph"]


# ---------- required_markers 空串 ----------

def test_required_markers_empty_rejected_batch179():
    flat = _rej({**_base(), "documents": [
        {"doc_id": "d", "path": "a.pdf", "source_type": "pdf",
         "expectations": {"required_markers": [""]}}]})
    assert flat["message"] == "'' should be non-empty"
    assert flat["path"] == ["documents", 0, "expectations",
                            "required_markers", 0]


# ---------- devset_status ----------

def test_devset_status_partial_rejected_batch179():
    flat = _rej({**_base(), "devset_status": "partial"})
    assert flat["message"] == \
        "'partial' is not one of ['complete', 'incomplete']"
    assert flat["path"] == ["devset_status"]


# ---------- ef 空 code ----------

def test_ef_empty_code_rejected_batch179():
    flat = _rej({**_base(), "expected_failures": [
        {"doc_id": "e", "path": "b",
         "expected_error_code": ""}]})
    assert flat["message"] == "'' should be non-empty"
    assert flat["path"] == ["expected_failures", 0,
                            "expected_error_code"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch179():
    src = _src()
    assert "validator = Draft202012Validator(schema)" in src
    assert "key=lambda e: list(e.absolute_path)" in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src
    assert '"schema_path": list(err.absolute_schema_path),' in src


# ---------- forbidden tokens 第四百五十一批 ----------

def test_source_no_eval_batch179():
    assert "eval(" not in _src()


def test_source_no_exec_batch179():
    assert "exec(" not in _src()


def test_source_no_compile_batch179():
    assert "compile(" not in _src()


def test_source_no_globals_batch179():
    assert "globals(" not in _src()


def test_source_no_locals_batch179():
    assert "locals(" not in _src()


def test_source_no_os_system_batch179():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch179():
    assert "subprocess" not in _src()


def test_source_no_popen_batch179():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch179():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch179():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch179():
    assert "socket" not in _src()


def test_source_no_requests_batch179():
    assert "requests" not in _src()


def test_source_no_urllib_batch179():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch179():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch179():
    assert "yield" not in _src()


def test_source_no_async_await_batch179():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch179():
    assert _src().count("open(") == 2
