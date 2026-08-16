"""evaluation/manifest.py 第九十七轮 edges 测试（Round 703）。

补强 edges80 未触及的角度（第六十八批），附带 evaluation/__init__ 常量契约。

新角度：
- evaluation 包常量（EVALUATOR_VERSION 1.1 / REPORT_VERSION 1.1 / ANNOTATION_VERSION 1.0 / MANIFEST_VERSION 1.0 / __all__ 4 项）
- _has_backslash 混合（a\\b/c / a/b\\ / 纯正斜杠）
- load_manifest manifest_path 传 str / 相对路径（monkeypatch.chdir）
- _detect_project_root 不存在的文件起点（is_file False → 直接走 parents）
- annotation_file 与 path 相同文件名 / unicode 子目录名
- expectations 只给 element_count_by_type / 只给 required_markers
- categories 空列表 → 空 tuple
- docs 与 efs 交错独立 / devset_status incomplete 透传
- manifest 放子目录、project_root 指父目录
- 源码补强（__init__ 四常量字面 / docstring 版本历史段 / manifest 模块未 import ANNOTATION_VERSION）
- AST 补强（__init__ 4 个 Assign 顺序 + __all__ 精确 / manifest _has_backslash 函数体单 Return）
- forbidden tokens 第一百七十三批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

import evaluation
import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    ManifestError,
    _detect_project_root,
    _has_backslash,
    load_manifest,
)


def _base(documents=None, **extra) -> dict:
    payload = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": documents or [],
    }
    payload.update(extra)
    return payload


def _write(root: Path, payload: dict, name: str = "manifest.json") -> Path:
    p = root / name
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def _doc(**over) -> dict:
    d = {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}
    d.update(over)
    return d


# ---------- evaluation 包常量 ----------

def test_evaluator_version_constant_batch52():
    assert evaluation.EVALUATOR_VERSION == "1.1"


def test_report_version_constant_batch52():
    assert evaluation.REPORT_VERSION == "1.1"


def test_annotation_version_constant_batch52():
    assert evaluation.ANNOTATION_VERSION == "1.0"


def test_manifest_version_constant_batch52():
    assert evaluation.MANIFEST_VERSION == "1.0"


def test_evaluation_all_exact_batch52():
    assert evaluation.__all__ == [
        "EVALUATOR_VERSION", "REPORT_VERSION",
        "ANNOTATION_VERSION", "MANIFEST_VERSION",
    ]


# ---------- _has_backslash 混合 ----------

def test_has_backslash_mixed_batch52():
    assert _has_backslash("a\\b/c") is True
    assert _has_backslash("a/b\\") is True
    assert _has_backslash("a/b/c") is False
    assert _has_backslash("") is False


# ---------- load_manifest 路径形式 ----------

def test_load_manifest_str_path_batch52(tmp_path):
    p = _write(tmp_path, _base())
    m = load_manifest(str(p), project_root=tmp_path)
    assert m.file_count == 0


def test_load_manifest_relative_path_batch52(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, _base([_doc()]))
    m = load_manifest("manifest.json", project_root=tmp_path)
    assert m.documents[0].doc_id == "d1"


def test_load_manifest_in_subdir_batch52(tmp_path):
    sub = tmp_path / "cfg"
    sub.mkdir()
    p = _write(sub, _base([_doc()]), name="m.json")
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


# ---------- _detect_project_root ----------

def test_detect_root_nonexistent_file_start_batch52(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    ghost = tmp_path / "no-such.json"
    assert _detect_project_root(ghost) == tmp_path


# ---------- 文档细节 ----------

def test_annotation_file_same_name_as_path_batch52(tmp_path):
    p = _write(tmp_path, _base([_doc(annotation_file="a.pdf")]))
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.annotation_resolved == d.resolved_path


def test_unicode_subdir_path_batch52(tmp_path):
    p = _write(tmp_path, _base([_doc(path="样例/文件.pdf")]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].path_str == "样例/文件.pdf"
    assert m.documents[0].resolved_path.name == "文件.pdf"


def test_expectations_counts_only_batch52(tmp_path):
    p = _write(tmp_path, _base([_doc(expectations={"element_count_by_type": {"paragraph": 2}})]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 2}}


def test_expectations_markers_only_batch52(tmp_path):
    p = _write(tmp_path, _base([_doc(expectations={"required_markers": ["结论"]})]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"required_markers": ["结论"]}


def test_categories_empty_list_batch52(tmp_path):
    p = _write(tmp_path, _base([_doc(categories=[])]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()
    assert m.categories_covered == []


def test_docs_and_efs_independent_batch52(tmp_path):
    payload = _base(
        [_doc(doc_id="d1"), _doc(doc_id="d2", path="b.pdf")],
        expected_failures=[
            {"doc_id": "ef1", "path": "bad1.pdf", "expected_error_code": "x1"},
            {"doc_id": "d3-like", "path": "bad2.pdf", "expected_error_code": "x2"},
        ],
    )
    m = load_manifest(_write(tmp_path, payload), project_root=tmp_path)
    assert [d.doc_id for d in m.documents] == ["d1", "d2"]
    assert [ef.doc_id for ef in m.expected_failures] == ["ef1", "d3-like"]


def test_devset_status_incomplete_passthrough_batch52(tmp_path):
    m = load_manifest(_write(tmp_path, _base()), project_root=tmp_path)
    assert m.devset_status == "incomplete"


def test_sha256_valid_hex_roundtrip_batch52(tmp_path):
    h = "0123456789abcdef" * 4
    p = _write(tmp_path, _base([_doc(sha256=h)]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == h


def test_multiple_categories_dedup_covered_batch52(tmp_path):
    p = _write(tmp_path, _base([
        _doc(doc_id="d1", categories=["z", "a"]),
        _doc(doc_id="d2", path="b.pdf", categories=["a", "m"]),
    ]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["a", "m", "z"]


# ---------- 错误消息细节补充 ----------

def test_error_message_contains_field_and_value_batch52(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_write(tmp_path, _base([_doc(path="C:/abs/x.pdf")])),
                      project_root=tmp_path)
    msg = str(ei.value)
    assert "documents[d1].path" in msg
    assert "C:/abs/x.pdf" in msg


def test_error_message_backslash_field_batch52(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_write(tmp_path, _base([_doc(path="a\\b.pdf")])),
                      project_root=tmp_path)
    assert "documents[d1].path" in str(ei.value)


# ---------- 源码补强 ----------

def _init_src() -> str:
    return inspect.getsource(evaluation)


def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_init_constants_batch52():
    src = _init_src()
    assert 'EVALUATOR_VERSION = "1.1"' in src
    assert 'REPORT_VERSION = "1.1"' in src
    assert 'ANNOTATION_VERSION = "1.0"' in src
    assert 'MANIFEST_VERSION = "1.0"' in src


def test_source_init_version_history_batch52():
    src = _init_src()
    assert "v1.1（当前）" in src
    assert "口径 D" in src


def test_source_manifest_no_annotation_version_batch52():
    assert "ANNOTATION_VERSION" not in _src()


def test_source_manifest_docstring_invariants_batch52():
    src = _src()
    assert "不把本机绝对路径写入 manifest 或报告" in src


# ---------- AST 补强 ----------

def test_ast_init_4_assigns_order_batch52():
    tree = ast.parse(_init_src())
    names = [
        n.targets[0].id for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and not n.targets[0].id.startswith("__")
    ]
    assert names == ["EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"]


def test_ast_init_all_unparse_batch52():
    tree = ast.parse(_init_src())
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert ast.unparse(all_assign) == (
        "__all__ = ['EVALUATOR_VERSION', 'REPORT_VERSION', "
        "'ANNOTATION_VERSION', 'MANIFEST_VERSION']"
    )


def test_ast_has_backslash_single_return_batch52():
    tree = ast.parse(_src())
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_has_backslash")
    body = [n for n in func.body if not isinstance(n, ast.Expr)]
    assert len(body) == 1 and isinstance(body[0], ast.Return)


# ---------- forbidden tokens 第一百七十三批 ----------

def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch52():
    assert _src().count("open(") == 1
