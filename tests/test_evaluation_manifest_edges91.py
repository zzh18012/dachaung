"""evaluation/manifest.py 第二百一十七轮 edges 测试（Round 773）。

补强 edges87-90 未触及的角度（第一百三十七批）。

新角度：
- project_root 缺省 → _detect_project_root 从 manifest 向上找
  pyproject.toml：tmp/sub/m.json → root=tmp（集成路径，非直接调用）
- manifest_path 传 str 同样工作（Path 转换）
- paired_with 传 int 5 → schema type string 拒
- doc_id 空串 "" → minLength 1 拒（R759 的 whitespace doc_id 通过对照）
- path 三种宽松形式全接受且解析一致：双斜杠 "samples//a.pdf"、
  "./samples/a.pdf"、"samples/../samples/a.pdf"（越出又回来的
  环回不是越界；Path 折叠后同一路径）
- expectations element_count_by_type 空对象 {} 原样存储
  （拒绝发生在 metrics 层 no_expectations_element_count）
- ef expected_error_code 空串 → minLength 1 拒
- ef 缺 source_type → dataclass 存 None
- 清单顶层 [] → "is not of type 'object'"
- 全字段 document 正确映射：sha256/categories 元组化/paired_with/
  expectations 原样 + devset_status "complete" 透传
- forbidden tokens 第二百四十三批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "pyproject.toml").write_text("")
    (tmp / "sub").mkdir()
    (tmp / "samples").mkdir()
    (tmp / "samples" / "a.pdf").write_bytes(b"x")
    return tmp


def _write(tmp, name, obj):
    f = tmp / name
    f.write_text(json.dumps(obj), encoding="utf-8")
    return f


def _doc(**kw):
    base = {"doc_id": "d1", "path": "samples/a.pdf",
            "source_type": "pdf"}
    base.update(kw)
    return base


def _mf(tmp, name, documents, ef=None, status="incomplete"):
    d = {"manifest_version": "1.0", "devset_status": status,
         "documents": documents}
    if ef is not None:
        d["expected_failures"] = ef
    return _write(tmp, name, d)


# ---------- 根自动探测 ----------

def test_auto_root_detection_integration_batch54(env):
    mf = _mf(env, "sub/m.json", [_doc()])
    m = load_manifest(mf)
    assert m.project_root == env
    assert m.documents[0].resolved_path == env / "samples" / "a.pdf"


def test_manifest_path_str_batch54(env):
    mf = _mf(env, "m.json", [_doc()])
    assert load_manifest(str(mf), env).file_count == 1


# ---------- schema 类型/长度拒 ----------

def test_paired_with_int_rejected_batch54(env):
    mf = _mf(env, "m.json", [_doc(paired_with=5)])
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(mf, env)
    assert "is not of type 'string'" in str(ei.value)


def test_doc_id_empty_rejected_batch54(env):
    mf = _mf(env, "m.json", [_doc(doc_id="")])
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(mf, env)
    assert "should be non-empty" in str(ei.value)


def test_ef_empty_code_rejected_batch54(env):
    mf = _mf(env, "m.json", [],
             ef=[{"doc_id": "f1", "path": "samples/a.pdf",
                  "expected_error_code": ""}])
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(mf, env)
    assert "should be non-empty" in str(ei.value)


def test_top_level_array_rejected_batch54(env):
    bf = env / "arr.json"
    bf.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(bf, env)
    assert "[] is not of type 'object'" in str(ei.value)


# ---------- 宽松路径形式 ----------

@pytest.mark.parametrize("p", [
    "samples//a.pdf",
    "./samples/a.pdf",
    "samples/../samples/a.pdf",
])
def test_lenient_path_forms_accepted_batch54(env, p):
    mf = _mf(env, "m.json", [_doc(path=p)])
    m = load_manifest(mf, env)
    assert m.documents[0].resolved_path == env / "samples" / "a.pdf"
    assert m.documents[0].path_str == p


# ---------- expectations 存储 ----------

def test_empty_count_dict_stored_as_is_batch54(env):
    mf = _mf(env, "m.json",
             [_doc(expectations={"element_count_by_type": {}})])
    m = load_manifest(mf, env)
    assert m.documents[0].expectations == {"element_count_by_type": {}}


# ---------- ef 缺 source_type ----------

def test_ef_missing_source_type_none_batch54(env):
    mf = _mf(env, "m.json", [],
             ef=[{"doc_id": "f1", "path": "samples/a.pdf",
                  "expected_error_code": "c"}])
    m = load_manifest(mf, env)
    assert m.expected_failures[0].source_type is None


# ---------- 全字段映射 ----------

def test_full_document_field_mapping_batch54(env):
    mf = _mf(env, "m.json", [{
        "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
        "sha256": "a" * 64, "categories": ["cat1", "cat2"],
        "paired_with": "d2",
        "expectations": {"element_count_by_type": {"paragraph": 2}},
    }], status="complete")
    m = load_manifest(mf, env)
    d = m.documents[0]
    assert d.sha256 == "a" * 64
    assert d.categories == ("cat1", "cat2")
    assert d.paired_with == "d2"
    assert d.expectations == {"element_count_by_type": {"paragraph": 2}}
    assert m.devset_status == "complete"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_detect_and_resolve_batch54():
    src = _src()
    assert 'if (parent / "pyproject.toml").is_file():' in src
    assert "return cur" in src
    assert "(project_root / path_str).resolve()" in src


# ---------- forbidden tokens 第二百四十三批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
