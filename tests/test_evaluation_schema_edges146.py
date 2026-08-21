"""evaluation/schema.py 第五百八十一轮 edges 测试（Round 1305）。

补强 edges145 未触及的角度（第六百七十七批，probe 实证）。

新角度（manifest.schema.json 运行时变异面）：
- **ef 条目严闭**——额外键
  note → additionalProperties
  @ ['expected_failures',
  0]；缺 path → required；
  空码 → non-empty
- **enum 不对称**——ef.
  source_type 宽域
  [pdf,docx,txt,other]
  （other VALID）；documents.
  source_type 严域
  [pdf,docx]（txt/other 均
  拒）——两处 enum 宽严
  不对称首锁
- **sha256 模式**——短串
  'abc' / 大写 'A'×64 均
  does not match
  ^[0-9a-f]{64}$
- **expectations 闭包**——
  额外键拒 @ [..,
  'expectations']；{}
  空对象 VALID
- **边界态**——documents []
  VALID（minItems 0 首
  锁）；expected_failures
  缺键 / [] 均 VALID（可
  选）；categories 空串
  项 VALID（无 minLength）
- **根闭包**——顶层额外键
  → additionalProperties
  @ []（根路径定位首锁）
- forbidden tokens 第七百五十三批（open 2）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.schema as schema_mod
from evaluation.schema import EvalSchemaError, validate


BASE = {
    "manifest_version": "1.0",
    "devset_status": "incomplete",
    "documents": [
        {"doc_id": "d1", "path": "c.pdf",
         "source_type": "pdf",
         "sha256": "a" * 64,
         "categories": ["x", "y"],
         "paired_with": "d0",
         "annotation_file": "ann/a.json",
         "expectations": {
             "element_count_by_type": {"heading": 1}}},
        {"doc_id": "b1", "path": "b.txt",
         "source_type": "docx"}],
    "expected_failures": [
        {"doc_id": "b1", "path": "b.txt",
         "expected_error_code": "some_code",
         "source_type": "txt"}]}


def _rej(mutate, message, path):
    d = copy.deepcopy(BASE)
    mutate(d)
    try:
        validate(d, "manifest.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert list(e.errors[0]["path"]) == path
    else:
        raise AssertionError("expected rejection")


def _acc(mutate):
    d = copy.deepcopy(BASE)
    mutate(d)
    validate(d, "manifest.schema.json")


# ---------- ef 条目严闭 ----------

def test_ef_extra_key_batch503():
    _rej(lambda d: d["expected_failures"][0].__setitem__(
             "note", 1),
         "Additional properties are not allowed "
         "('note' was unexpected)",
         ["expected_failures", 0])


def test_ef_missing_path_batch503():
    _rej(lambda d: d["expected_failures"][0].pop("path"),
         "'path' is a required property",
         ["expected_failures", 0])


def test_ef_empty_code_batch503():
    _rej(lambda d: d["expected_failures"][0].__setitem__(
             "expected_error_code", ""),
         "'' should be non-empty",
         ["expected_failures", 0,
          "expected_error_code"])


# ---------- enum 不对称 ----------

def test_ef_srctype_bad_batch503():
    _rej(lambda d: d["expected_failures"][0].__setitem__(
             "source_type", "exe"),
         "'exe' is not one of ['pdf', 'docx', "
         "'txt', 'other']",
         ["expected_failures", 0, "source_type"])


def test_ef_srctype_other_valid_batch503():
    _acc(lambda d: d["expected_failures"][0].__setitem__(
        "source_type", "other"))


def test_doc_srctype_txt_rejected_batch503():
    _rej(lambda d: d["documents"][1].__setitem__(
             "source_type", "txt"),
         "'txt' is not one of ['pdf', 'docx']",
         ["documents", 1, "source_type"])


def test_doc_srctype_other_rejected_batch503():
    _rej(lambda d: d["documents"][1].__setitem__(
             "source_type", "other"),
         "'other' is not one of ['pdf', 'docx']",
         ["documents", 1, "source_type"])


# ---------- sha256 模式 ----------

def test_sha_short_batch503():
    _rej(lambda d: d["documents"][0].__setitem__(
             "sha256", "abc"),
         "'abc' does not match '^[0-9a-f]{64}$'",
         ["documents", 0, "sha256"])


def test_sha_uppercase_batch503():
    _rej(lambda d: d["documents"][0].__setitem__(
             "sha256", "A" * 64),
         "'%s' does not match '^[0-9a-f]{64}$'"
         % ("A" * 64),
         ["documents", 0, "sha256"])


# ---------- expectations 闭包 ----------

def test_expectations_extra_batch503():
    _rej(lambda d: d["documents"][0][
             "expectations"].__setitem__("zzz", 1),
         "Additional properties are not allowed "
         "('zzz' was unexpected)",
         ["documents", 0, "expectations"])


def test_expectations_empty_valid_batch503():
    _acc(lambda d: d["documents"][0].__setitem__(
        "expectations", {}))


# ---------- 边界态 ----------

def test_documents_empty_valid_batch503():
    _acc(lambda d: d.__setitem__("documents", []))


def test_ef_missing_key_valid_batch503():
    _acc(lambda d: d.pop("expected_failures"))


def test_ef_empty_list_valid_batch503():
    _acc(lambda d: d.__setitem__("expected_failures",
                                 []))


def test_categories_empty_string_valid_batch503():
    _acc(lambda d: d["documents"][0].__setitem__(
        "categories", [""]))


def test_categories_int_rejected_batch503():
    _rej(lambda d: d["documents"][0].__setitem__(
             "categories", ["x", 1]),
         "1 is not of type 'string'",
         ["documents", 0, "categories", 1])


# ---------- 根闭包与基础域 ----------

def test_root_extra_key_batch503():
    _rej(lambda d: d.__setitem__("zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)", [])


def test_doc_empty_id_batch503():
    _rej(lambda d: d["documents"][0].__setitem__(
             "doc_id", ""),
         "'' should be non-empty",
         ["documents", 0, "doc_id"])


def test_devset_bad_enum_batch503():
    _rej(lambda d: d.__setitem__("devset_status",
                                 "bogus"),
         "'bogus' is not one of ['complete', "
         "'incomplete']",
         ["devset_status"])


def test_base_valid_batch503():
    validate(copy.deepcopy(BASE),
             "manifest.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch503():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百五十三批 ----------

def test_source_no_eval_batch503():
    assert "eval(" not in _src()


def test_source_no_exec_batch503():
    assert "exec(" not in _src()


def test_source_no_compile_batch503():
    assert "compile(" not in _src()


def test_source_no_globals_batch503():
    assert "globals(" not in _src()


def test_source_no_locals_batch503():
    assert "locals(" not in _src()


def test_source_no_os_system_batch503():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch503():
    assert "subprocess" not in _src()


def test_source_no_popen_batch503():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch503():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch503():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch503():
    assert "socket" not in _src()


def test_source_no_requests_batch503():
    assert "requests" not in _src()


def test_source_no_urllib_batch503():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch503():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch503():
    assert "yield" not in _src()


def test_source_no_async_await_batch503():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch503():
    assert _src().count("open(") == 2
