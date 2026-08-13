"""evaluation/manifest.py 第八十五轮 edges 测试（Round 621）。

补强 edges69 未触及的角度（第四十四批）。

新角度：
- load_manifest 完整流程
- load_manifest 文件不存在
- load_manifest JSON 解析失败
- load_manifest Schema 失败
- load_manifest manifest_version 不匹配
- load_manifest documents 解析
- load_manifest expected_failures 解析
- load_manifest project_root 自动检测
- load_manifest project_root 显式传入
- _detect_project_root 行为
- _resolve_relative_path 各种字段名透传
- Manifest.file_count / pdf_count / docx_count
- Manifest.categories_covered 排序
- Manifest 不变性
- module source 字符串精确
- AST 结构
- forbidden tokens 第九十一批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import asdict, fields, replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    DocumentEntry,
    ExpectedFailure,
    Manifest,
    ManifestError,
    _detect_project_root,
    _has_backslash,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


# ---------- load_manifest 完整流程 ----------

def test_load_manifest_signature_batch44():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_load_manifest_param_kinds_batch44():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["project_root"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_manifest_project_root_default_none_batch44():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_return_annotation_batch44():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


# ---------- load_manifest 错误路径 ----------

def test_load_manifest_file_not_found_batch44(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "nonexistent.json", tmp_path)
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_invalid_json_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, tmp_path)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_schema_fail_batch44(tmp_path):
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"wrong": "schema"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_version_mismatch_batch44(tmp_path):
    """manifest_version 既不在 schema enum 里 → schema 直接拒绝（先于版本比对）。
    schema_only_rejection: schema enum 限定，version_mismatch 路径在代码层实际上 dead。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "9.9",  # schema enum 只允许 "1.0"
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_version_mismatch_via_monkeypatch_batch44(tmp_path, monkeypatch):
    """monkeypatch evaluation.manifest.MANIFEST_VERSION 后，schema 通过但代码比对失败。"""
    monkeypatch.setattr(manifest_mod, "MANIFEST_VERSION", "1.0")
    # 但 schema validation 在 manifest_mod.validate 内调用，schema 里 const="1.0"，
    # 所以即便 monkeypatch code-side 的常量，schema 仍按 "1.0" 通过。
    # 这个分支必须通过修改 schema 本身才能触发，这里只验证 happy path 仍工作。
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.manifest_version == "1.0"


def test_load_manifest_success_empty_documents_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert isinstance(m, Manifest)
    assert m.documents == ()
    assert m.expected_failures == ()
    assert m.devset_status == "incomplete"


# ---------- load_manifest documents 解析 ----------

def test_load_manifest_one_document_batch44(tmp_path):
    """doc 中的 path 必须解析到 project_root 内。"""
    doc_path = tmp_path / "doc1.pdf"
    doc_path.write_text("dummy", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "doc1.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["cat_a"],
            }
        ],
    }), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].source_type == "pdf"
    assert m.documents[0].sha256 == "a" * 64
    assert m.documents[0].categories == ("cat_a",)
    assert m.documents[0].resolved_path == doc_path.resolve()


def test_load_manifest_doc_path_escape_batch44(tmp_path):
    """doc path 不允许 ../ 逃逸 project_root。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "../escape.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": [],
            }
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, tmp_path)
    assert "项目根目录之外" in str(exc_info.value)


def test_load_manifest_doc_absolute_path_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "/etc/passwd",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": [],
            }
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, tmp_path)
    assert "绝对路径" in str(exc_info.value)


def test_load_manifest_doc_backslash_path_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "subdir\\doc.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": [],
            }
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, tmp_path)
    assert "反斜杠" in str(exc_info.value)


# ---------- load_manifest expected_failures 解析 ----------

def test_load_manifest_expected_failures_batch44(tmp_path):
    doc_path = tmp_path / "bad.pdf"
    doc_path.write_text("dummy", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "bad.pdf",
                "expected_error_code": "parse_failed",
            }
        ],
    }), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].expected_error_code == "parse_failed"
    assert m.expected_failures[0].source_type is None


def test_load_manifest_expected_failure_with_source_type_batch44(tmp_path):
    doc_path = tmp_path / "bad.pdf"
    doc_path.write_text("dummy", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "bad.pdf",
                "expected_error_code": "parse_failed",
                "source_type": "pdf",
            }
        ],
    }), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


# ---------- load_manifest categories + paired_with ----------

def test_load_manifest_paired_docs_batch44(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("dummy", encoding="utf-8")
    docx_path = tmp_path / "doc.docx"
    docx_path.write_text("dummy", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "doc.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["x"],
                "paired_with": "d2",
            },
            {
                "doc_id": "d2",
                "path": "doc.docx",
                "source_type": "docx",
                "sha256": "b" * 64,
                "categories": ["x"],
                "paired_with": "d1",
            },
        ],
    }), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.content_group_count == 1
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_load_manifest_categories_covered_sorted_batch44(tmp_path):
    for name in ("a.pdf", "b.pdf", "c.pdf"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": "a" * 64, "categories": ["z", "y"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "sha256": "b" * 64, "categories": ["x"]},
            {"doc_id": "d3", "path": "c.pdf", "source_type": "pdf", "sha256": "c" * 64, "categories": ["a"]},
        ],
    }), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.categories_covered == ["a", "x", "y", "z"]


# ---------- _detect_project_root ----------

def test_detect_project_root_signature_batch44():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


def test_detect_project_root_finds_pyproject_batch44(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    start = tmp_path / "subdir"
    start.mkdir()
    result = _detect_project_root(start)
    assert result == tmp_path.resolve()


def test_detect_project_root_from_file_batch44(tmp_path):
    """start 是文件 → 从其父目录开始向上。"""
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    f = tmp_path / "file.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_batch44(tmp_path):
    """无 pyproject.toml → 返回 start。"""
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


# ---------- _resolve_relative_path 字段名透传 ----------

def test_resolve_relative_path_empty_batch44(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "field_x")
    assert "field_x" in str(exc_info.value)


def test_resolve_relative_path_absolute_batch44(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "field_x")
    assert "field_x" in str(exc_info.value)


def test_resolve_relative_path_backslash_batch44(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("sub\\x.pdf", tmp_path, "field_x")
    assert "field_x" in str(exc_info.value)


def test_resolve_relative_path_escape_batch44(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../x.pdf", tmp_path, "field_x")
    assert "field_x" in str(exc_info.value)


def test_resolve_relative_path_success_batch44(tmp_path):
    out = _resolve_relative_path("foo.pdf", tmp_path, "field_x")
    assert isinstance(out, Path)
    assert out == (tmp_path / "foo.pdf").resolve()


# ---------- _is_absolute_like 边界 ----------

def test_is_absolute_like_posix_batch44():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_windows_batch44():
    assert _is_absolute_like("C:\\Windows") is True


def test_is_absolute_like_windows_forward_batch44():
    assert _is_absolute_like("C:/Windows") is True


def test_is_absolute_like_relative_batch44():
    assert _is_absolute_like("foo/bar.pdf") is False


def test_is_absolute_like_empty_batch44():
    assert _is_absolute_like("") is False


def test_is_absolute_like_tilde_batch44():
    """tilde 不算绝对路径（实现不识别 ~）。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_short_batch44():
    """长度 < 3 但不以 / 开头 → False。"""
    assert _is_absolute_like("a") is False


def test_is_absolute_like_unc_batch44():
    """UNC path \\\\server\\share 走 starts with / 检查（不命中）。"""
    assert _is_absolute_like("\\\\server\\share") is False  # starts with \\ not /


def test_is_absolute_like_unicode_drive_letter_batch44():
    """isalpha() 接受 Unicode 字母 → δ: 算 drive letter。"""
    assert _is_absolute_like("δ:/foo") is True


# ---------- _has_backslash ----------

def test_has_backslash_yes_batch44():
    assert _has_backslash("a\\b") is True


def test_has_backslash_no_batch44():
    assert _has_backslash("a/b") is False


def test_has_backslash_empty_batch44():
    assert _has_backslash("") is False


# ---------- ManifestError ----------

def test_manifest_error_inherits_exception_batch44():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_value_error_batch44():
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_not_type_error_batch44():
    assert not issubclass(ManifestError, TypeError)


def test_manifest_error_message_batch44():
    try:
        raise ManifestError("test message")
    except ManifestError as e:
        assert str(e) == "test message"


def test_manifest_error_catchable_as_exception_batch44():
    try:
        raise ManifestError("x")
    except Exception as e:
        assert isinstance(e, ManifestError)


# ---------- DocumentEntry / ExpectedFailure dataclass ----------

def test_document_entry_field_count_batch44():
    assert len(fields(DocumentEntry)) == 10


def test_expected_failure_field_count_batch44():
    assert len(fields(ExpectedFailure)) == 5


def test_manifest_field_count_batch44():
    assert len(fields(Manifest)) == 5


def test_document_entry_frozen_batch44():
    de = DocumentEntry(
        doc_id="d1",
        path_str="d1.pdf",
        resolved_path=Path("/tmp/d1.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(Exception):
        de.doc_id = "d2"  # type: ignore[misc]


def test_expected_failure_frozen_batch44():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.pdf",
        resolved_path=Path("/tmp/bad.pdf"),
        expected_error_code="parse_failed",
        source_type=None,
    )
    with pytest.raises(Exception):
        ef.doc_id = "x"  # type: ignore[misc]


def test_document_entry_replace_batch44():
    de = DocumentEntry(
        doc_id="d1",
        path_str="d1.pdf",
        resolved_path=Path("/tmp/d1.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    de2 = replace(de, doc_id="d2")
    assert de2.doc_id == "d2"
    assert de.doc_id == "d1"  # original unchanged


def test_document_entry_asdict_batch44():
    de = DocumentEntry(
        doc_id="d1",
        path_str="d1.pdf",
        resolved_path=Path("/tmp/d1.pdf"),
        source_type="pdf",
        sha256="x" * 64,
        categories=("a", "b"),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    d = asdict(de)
    assert d["doc_id"] == "d1"
    assert d["sha256"] == "x" * 64
    # asdict 保留 tuple 类型（不转 list）
    assert d["categories"] == ("a", "b")


# ---------- Manifest properties ----------

def test_manifest_file_count_batch44():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.file_count == 0


def test_manifest_pdf_count_batch44():
    de1 = DocumentEntry(
        doc_id="d1", path_str="d1.pdf", resolved_path=Path("/tmp/d1.pdf"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="d2.docx", resolved_path=Path("/tmp/d2.docx"),
        source_type="docx", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(de1, de2),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_manifest_categories_covered_empty_batch44():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == []


def test_manifest_content_group_count_no_paired_batch44():
    de1 = DocumentEntry(
        doc_id="d1", path_str="d1.pdf", resolved_path=Path("/tmp/d1.pdf"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(de1,),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 1


# ---------- __all__ ----------

def test_all_exact_batch44():
    assert set(manifest_mod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_all_count_5_batch44():
    assert len(manifest_mod.__all__) == 5


def test_all_entries_are_str_batch44():
    for e in manifest_mod.__all__:
        assert isinstance(e, str)


def test_all_entries_are_attrs_batch44():
    for e in manifest_mod.__all__:
        assert hasattr(manifest_mod, e)


# ---------- module source ----------

def test_module_source_contains_key_invariants_batch44():
    src = inspect.getsource(manifest_mod)
    assert "path 字段必须是相对路径" in src


def test_module_source_contains_no_absolute_path_batch44():
    src = inspect.getsource(manifest_mod)
    assert "拒绝绝对路径" in src


def test_module_source_contains_project_root_check_batch44():
    src = inspect.getsource(manifest_mod)
    assert "项目根目录内" in src


def test_module_source_contains_manifest_version_import_batch44():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_validate_import_batch44():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_dataclass_batch44():
    src = inspect.getsource(manifest_mod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_paired_group_comment_batch44():
    src = inspect.getsource(manifest_mod)
    assert "配对" in src


def test_module_source_contains_detect_project_root_batch44():
    src = inspect.getsource(manifest_mod)
    assert "_detect_project_root" in src
    assert "pyproject.toml" in src


# ---------- AST 结构 ----------

def test_ast_top_level_class_count_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4  # ManifestError, DocumentEntry, ExpectedFailure, Manifest


def test_ast_top_level_class_names_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert set(names) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_ast_top_level_function_count_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5  # _is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root


def test_ast_top_level_function_names_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert set(names) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "load_manifest",
        "_detect_project_root",
    }


def test_ast_from_future_first_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)  # docstring
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_manifest_class_has_properties_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest"][0]
    prop_names = [
        n.name for n in cls.body
        if isinstance(n, ast.FunctionDef) and any(isinstance(d, ast.Name) and d.id == "property" for d in n.decorator_list)
    ]
    assert "file_count" in prop_names
    assert "pdf_count" in prop_names
    assert "docx_count" in prop_names
    assert "content_group_count" in prop_names
    assert "categories_covered" in prop_names


def test_ast_no_try_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


# ---------- forbidden tokens 第九十一批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(manifest_mod)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(manifest_mod)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(manifest_mod)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(manifest_mod)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(manifest_mod)
    assert "locals(" not in src


def test_source_no_open_write_batch44():
    """load_manifest 用 path.open('r')，不能写盘。"""
    src = inspect.getsource(manifest_mod)
    assert "open(\"w\"" not in src
    assert "open('w'" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(manifest_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(manifest_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(manifest_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(manifest_mod)
    assert "pickle.load(" not in src
