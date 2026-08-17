"""evaluation/manifest.py 第三百五十七轮 edges 测试（Round 913）。

补强 edges110 未触及的角度（第二百八十九批，probe 实证）。

新角度：
- manifest_version "2.0"：schema const "1.0" 先拦截（EvalSchemaError
  "'1.0' was expected"），load_manifest 的版本不兼容 ManifestError
  分支实为死代码——现状锁定
- schema 结构：documents items 是 $ref #/$defs/document；
  $defs 恰 [document, expected_failure]
- _is_absolute_like 十值矩阵：空串/CC:/1:/C:x/UNC/相对 → False；
  /x、C:\\x、C:/x、c:\\x（小写盘符）→ True
- sha256 显式 null → EvalSchemaError（"None is not of type
  'string'"），默认缺省才是 None
- ghost 配对（paired_with 指向不存在 doc）→ 1 组；自配对
  d1↔d1 → 1 组
- categories [""]：schema 放行，categories_covered == [""]
- file/pdf/docx 计数 3/2/1；doc 路径不查存在性（ghost.pdf 照常加载）
- annotation_file 绝对路径 → ManifestError 字段名
  documents[d1].annotation_file
- expected_failures 路径逃逸项目根 → ManifestError 字段名
  expected_failures[f1].path
- 清单路径是目录 → ManifestError "清单文件不存在"
- forbidden tokens 第三百八十三批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    ManifestError,
    _detect_project_root,
    _is_absolute_like,
    load_manifest,
)
from evaluation.schema import EvalSchemaError


BS = chr(92)


def _mk(tmp_path, docs, efs=None):
    (tmp_path / "samples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    d = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": docs}
    if efs is not None:
        d["expected_failures"] = efs
    f = tmp_path / "m.json"
    f.write_text(json.dumps(d), encoding="utf-8")
    return f


# ---------- manifest_version 死分支 ----------

def test_version_two_schema_intercepts_batch111(tmp_path):
    (tmp_path / "samples").mkdir(parents=True)
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "2.0", "devset_status": "incomplete",
        "documents": []}), encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, tmp_path)
    msg = str(ei.value)
    assert "'1.0' was expected" in msg
    assert "path=['manifest_version']" in msg


def test_manifest_schema_documents_ref_batch111():
    m = json.loads(
        (__import__("pathlib").Path("schemas") /
         "manifest.schema.json").read_text(encoding="utf-8"))
    assert m["properties"]["documents"] == {
        "type": "array", "items": {"$ref": "#/$defs/document"}}
    assert sorted(m["$defs"]) == ["document", "expected_failure"]


# ---------- _is_absolute_like 矩阵 ----------

def test_is_absolute_like_matrix_batch111():
    neg = ["", "CC/x", "1:/x", "C:x",
           BS + BS + "srv" + BS + "sh", "a/b"]
    pos = ["/x", "C:" + BS + "x", "C:/x", "c:" + BS + "x"]
    for s in neg:
        assert _is_absolute_like(s) is False, s
    for s in pos:
        assert _is_absolute_like(s) is True, s


# ---------- sha256 显式 null ----------

def test_sha256_null_rejected_batch111(tmp_path):
    f = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf", "sha256": None}])
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, tmp_path)
    assert "None is not of type 'string'" in str(ei.value)


# ---------- ghost / 自配对 ----------

def test_ghost_pairing_one_group_batch111(tmp_path):
    f = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "paired_with": "ghost"}])
    m = load_manifest(f, tmp_path)
    assert m.content_group_count == 1


def test_self_pairing_one_group_batch111(tmp_path):
    f = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "paired_with": "d1"}])
    m = load_manifest(f, tmp_path)
    assert m.content_group_count == 1


# ---------- categories 空串 ----------

def test_empty_string_category_batch111(tmp_path):
    f = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "categories": [""]}])
    m = load_manifest(f, tmp_path)
    assert m.categories_covered == [""]


# ---------- 计数与存在性 ----------

def test_counts_and_no_existence_check_batch111(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "samples/ghost.pdf",
         "source_type": "pdf"},
        {"doc_id": "d2", "path": "samples/a.pdf",
         "source_type": "docx"},
        {"doc_id": "d3", "path": "samples/a.pdf",
         "source_type": "pdf"},
    ]
    m = load_manifest(_mk(tmp_path, docs), tmp_path)
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.documents[0].sha256 is None
    assert m.documents[0].resolved_path.name == "ghost.pdf"


# ---------- annotation_file 绝对路径 ----------

def test_annotation_absolute_field_name_batch111(tmp_path):
    f = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "annotation_file": "C:/x/ann.json"}])
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, tmp_path)
    msg = str(ei.value)
    assert msg.startswith("documents[d1].annotation_file ")
    assert "禁止绝对路径：C:/x/ann.json" in msg


# ---------- expected_failures 路径逃逸 ----------

def test_ef_path_escape_field_name_batch111(tmp_path):
    f = _mk(tmp_path, [], efs=[{
        "doc_id": "f1", "path": "x/../../esc.pdf",
        "expected_error_code": "E"}])
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, tmp_path)
    msg = str(ei.value)
    assert msg.startswith("expected_failures[f1].path ")
    assert "解析后位于项目根目录之外" in msg


# ---------- 清单路径是目录 ----------

def test_directory_as_manifest_path_batch111(tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    with pytest.raises(ManifestError) as ei:
        load_manifest(d, tmp_path)
    assert str(ei.value).startswith("清单文件不存在: ")


# ---------- _detect_project_root 文件起点 ----------

def test_detect_project_root_from_file_batch111():
    root = _detect_project_root(
        __import__("pathlib").Path(__file__).resolve())
    assert root == __import__("pathlib").Path(
        __file__).resolve().parent.parent


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch111():
    src = _src()
    assert 'raise ManifestError(f"{field_name} 为空")' in src
    assert "resolved.relative_to(project_root_resolved)" in src
    assert "if data.get(\"manifest_version\") != MANIFEST_VERSION:" in src
    assert 'f"清单文件不存在: {p}"' in src


# ---------- forbidden tokens 第三百八十三批 ----------

def test_source_no_eval_batch111():
    assert "eval(" not in _src()


def test_source_no_exec_batch111():
    assert "exec(" not in _src()


def test_source_no_compile_batch111():
    assert "compile(" not in _src()


def test_source_no_globals_batch111():
    assert "globals(" not in _src()


def test_source_no_locals_batch111():
    assert "locals(" not in _src()


def test_source_no_os_system_batch111():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch111():
    assert "subprocess" not in _src()


def test_source_no_popen_batch111():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch111():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch111():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch111():
    assert "socket" not in _src()


def test_source_no_requests_batch111():
    assert "requests" not in _src()


def test_source_no_urllib_batch111():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch111():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch111():
    assert "yield" not in _src()


def test_source_no_async_await_batch111():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch111():
    assert _src().count("open(") == 1
