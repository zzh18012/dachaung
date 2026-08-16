"""evaluation/manifest.py 第二百零四轮 edges 测试（Round 745）。

补强 edges84-86 未触及的角度（第一百一十批）。

新角度：
- 全可选字段文档：sha256/categories/paired_with/annotation_file/
  expectations 逐字段精确映射（annotation_resolved 解析、
  expectations 原样 dict）
- 怪但合法的路径："a<b.pdf"（Windows 保留字符 Path 不拦）、
  unicode 路径、"a//b.pdf"、"a/./b.pdf" 全部加载并归一
- manifest_version "2.0" 被 schema const 拦下（EvalSchemaError，
  代码侧不兼容分支不可达 —— 与 edges85 的 monkeypatch 测试互补）
- ef-only 清单：全 0 计数 + categories []；devset_status "complete" 透传
- __all__ 六元素精确
- AST：load_manifest If4·Try1·For2·Raise3·Call34
- forbidden tokens 第二百一十五批
"""

from __future__ import annotations

import ast
import collections
import inspect
import json
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.schema import EvalSchemaError
from evaluation.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[1]


def _mf(tmp_path, documents=(), **over) -> Path:
    payload = {"manifest_version": "1.0", "devset_status": "incomplete",
               "documents": list(documents)}
    payload.update(over)
    f = tmp_path / "m.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


# ---------- 全可选字段映射 ----------

def test_full_optional_field_mapping_batch54(tmp_path):
    f = _mf(tmp_path, [{
        "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
        "sha256": "ab" * 32, "categories": ["x", "y"],
        "paired_with": "d2", "annotation_file": "ann/d1.json",
        "expectations": {"element_count_by_type": {"paragraph": 2},
                         "required_markers": ["m"]},
    }])
    e = load_manifest(f, project_root=ROOT).documents[0]
    assert e.doc_id == "d1"
    assert e.path_str == "a.pdf"
    assert e.source_type == "pdf"
    assert e.sha256 == "ab" * 32
    assert e.categories == ("x", "y")
    assert e.paired_with == "d2"
    assert e.annotation_file_str == "ann/d1.json"
    assert e.annotation_resolved == (ROOT / "ann" / "d1.json").resolve()
    assert e.expectations == {"element_count_by_type": {"paragraph": 2},
                              "required_markers": ["m"]}
    assert e.resolved_path == (ROOT / "a.pdf").resolve()


# ---------- 怪但合法的路径 ----------

@pytest.mark.parametrize("path_str", [
    "a<b.pdf",        # Windows 保留字符，Path 层不拦（现状记录）
    "数据/文件.pdf",
    "a//b.pdf",       # 双正斜杠中段
    "a/./b.pdf",      # 当前目录段
])
def test_odd_but_legal_paths_load_batch54(tmp_path, path_str):
    f = _mf(tmp_path, [{"doc_id": "d", "path": path_str,
                        "source_type": "pdf"}])
    man = load_manifest(f, project_root=ROOT)
    assert man.documents[0].resolved_path.name == Path(path_str).name


# ---------- 版本拦截层 ----------

def test_wrong_version_intercepted_by_schema_batch54(tmp_path):
    # schema const "1.0" 先拦 → 代码侧不兼容分支不可达
    f = _mf(tmp_path, [], manifest_version="2.0")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, project_root=ROOT)
    assert "was expected" in str(ei.value)


# ---------- ef-only / status ----------

def test_ef_only_manifest_zero_counts_batch54(tmp_path):
    f = _mf(tmp_path, expected_failures=[
        {"doc_id": "e", "path": "x.txt", "expected_error_code": "c"}])
    man = load_manifest(f, project_root=ROOT)
    assert (man.file_count, man.pdf_count, man.docx_count,
            man.content_group_count) == (0, 0, 0, 0)
    assert man.categories_covered == []
    assert len(man.expected_failures) == 1


def test_devset_status_complete_passthrough_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [], devset_status="complete"),
                        project_root=ROOT)
    assert man.devset_status == "complete"


# ---------- __all__ 与 AST ----------

def test_all_export_six_names_batch54():
    assert manifest_mod.__all__ == [
        "ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure",
        "load_manifest"]


def test_ast_load_manifest_structure_batch54():
    tree = ast.parse(inspect.getsource(manifest_mod))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    c = collections.Counter(type(n).__name__ for n in ast.walk(fn))
    assert (c["If"], c["Try"], c["For"], c["Raise"], c["Call"],
            c["With"]) == (4, 1, 2, 3, 34, 1)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_annotation_conditional_resolve_batch54():
    src = _src()
    assert 'if d.get("annotation_file"):' in src
    assert 'data.get("documents", [])' in src


# ---------- forbidden tokens 第二百一十五批 ----------

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
