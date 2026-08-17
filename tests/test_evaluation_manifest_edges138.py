"""evaluation/manifest.py 第五百五十二轮 edges 测试（Round 1108）。

补强 edges137 未触及的角度（第四百八十四批，probe 实证）。

新角度（sha256 不验文件 / ef 撞 id / expectations 封闭）：
- **sha256 不验实文件**：真实 docx + sha256 "b"*64（合法
  hex 但内容必假）→ 照常加载且 DocumentEntry.sha256 原样
  入档——loader 从不读文件内容比对哈希（ghost path 已证
  存在性不查，本批证内容哈希也不查）
- **ef 撞 documents id**：d1 同时出现在 documents（好文件）
  与 expected_failures（ghost 文件）→ 两账照单全收——
  loader 不查 doc_id 跨账唯一；resolved_path 各自独立
  （同 id 不同文件并存）
- **expectations 封闭**：expectations {"bogus_key": 1} →
  schema 拒 "Additional properties are not allowed
  ('bogus_key' was unexpected) @ path=['documents', 0,
  'expectations']"——expectations def additionalProperties
  False（首锁）
- **双类型期望原样**：{paragraph 3, table 1} → 原样入档
  （多类型期望是 silent_drop_count 按 type 分账的基础）
- forbidden tokens 第五百七十九批（open 1）
"""

from __future__ import annotations

import inspect
import json

from docx import Document

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError


def _write(tmp_path, docs, efs=None):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": efs or []}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _good_doc(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    d = Document()
    d.add_paragraph("AAA body.")
    d.save(str(tmp_path / "samples" / "g.docx"))


# ---------- sha256 不验实文件 ----------

def test_sha256_not_verified_batch307(tmp_path):
    _good_doc(tmp_path)
    m = _write(tmp_path, [{
        "doc_id": "d1", "path": "samples/g.docx",
        "source_type": "docx", "sha256": "b" * 64}])
    assert m.documents[0].sha256 == "b" * 64
    assert m.file_count == 1


# ---------- ef 撞 documents id ----------

def test_ef_doc_id_collision_batch307(tmp_path):
    _good_doc(tmp_path)
    m = _write(
        tmp_path,
        [{"doc_id": "d1", "path": "samples/g.docx",
          "source_type": "docx"}],
        [{"doc_id": "d1", "path": "samples/ghost.docx",
          "expected_error_code": "file_not_found"}])
    assert m.documents[0].doc_id == \
        m.expected_failures[0].doc_id == "d1"
    assert len(m.documents) == 1
    assert len(m.expected_failures) == 1
    assert m.documents[0].resolved_path != \
        m.expected_failures[0].resolved_path
    assert m.expected_failures[0].source_type is None


# ---------- expectations 封闭 ----------

def test_expectations_closed_batch307(tmp_path):
    try:
        _write(tmp_path, [{
            "doc_id": "d1", "path": "samples/a.pdf",
            "source_type": "pdf",
            "expectations": {"bogus_key": 1}}])
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert "Additional properties are not allowed" in str(e)
        assert "'bogus_key' was unexpected" in str(e)
        assert "path=['documents', 0, 'expectations']" in str(e)
    assert raised


# ---------- 双类型期望原样 ----------

def test_two_type_expectations_verbatim_batch307(tmp_path):
    m = _write(tmp_path, [{
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf",
        "expectations": {
            "element_count_by_type": {
                "paragraph": 3, "table": 1}}}])
    assert m.documents[0].expectations == {
        "element_count_by_type": {
            "paragraph": 3, "table": 1}}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch307():
    src = _src()
    assert "未配对的 1 个算 1 组" in src
    assert "先收集所有 paired_with" in src


# ---------- forbidden tokens 第五百七十九批 ----------

def test_source_no_eval_batch307():
    assert "eval(" not in _src()


def test_source_no_exec_batch307():
    assert "exec(" not in _src()


def test_source_no_compile_batch307():
    assert "compile(" not in _src()


def test_source_no_globals_batch307():
    assert "globals(" not in _src()


def test_source_no_locals_batch307():
    assert "locals(" not in _src()


def test_source_no_os_system_batch307():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch307():
    assert "subprocess" not in _src()


def test_source_no_popen_batch307():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch307():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch307():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch307():
    assert "socket" not in _src()


def test_source_no_requests_batch307():
    assert "requests" not in _src()


def test_source_no_urllib_batch307():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch307():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch307():
    assert "yield" not in _src()


def test_source_no_async_await_batch307():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch307():
    assert _src().count("open(") == 1
