"""evaluation/manifest.py 第八十八轮 edges 测试（Round 645）。

补强 edges72 未触及的角度（第四十八批）。

新角度：
- ManifestError 子类化与抛出
- _is_absolute_like 数字与特殊字符
- _has_backslash 多次出现
- _resolve_relative_path 复杂场景（symbolic / Unicode）
- load_manifest 异常路径（不存在 / JSON 解析失败 / Schema 失败 / version 不兼容）
- load_manifest documents 多种字段组合
- load_manifest expected_failures 完整
- Manifest property 边界（file_count / pdf_count / docx_count / content_group_count / categories_covered）
- _detect_project_root 多种场景
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百一十五批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError, fields
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


# ---------- ManifestError 子类化与抛出 ----------

def test_manifest_error_is_exception_batch48():
    err = ManifestError("x")
    assert isinstance(err, Exception)


def test_manifest_error_can_be_raised_batch48():
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("boom")
    assert "boom" in str(exc_info.value)


def test_manifest_error_caught_as_exception_batch48():
    with pytest.raises(Exception):
        raise ManifestError("x")


def test_manifest_error_args_batch48():
    err = ManifestError("hello")
    assert err.args == ("hello",)


def test_manifest_error_no_extra_attrs_batch48():
    err = ManifestError("x")
    # 不应有 errors 等字段（不像 EvalSchemaError）
    assert not hasattr(err, "errors")


def test_manifest_error_str_batch48():
    err = ManifestError("hello world")
    assert str(err) == "hello world"


def test_manifest_error_repr_batch48():
    err = ManifestError("hello")
    r = repr(err)
    assert "ManifestError" in r


def test_manifest_error_with_cause_batch48():
    """raise ... from e 应保留 __cause__。"""
    original = ValueError("orig")
    with pytest.raises(ManifestError) as exc_info:
        try:
            raise original
        except ValueError as e:
            raise ManifestError("wrapped") from e
    assert exc_info.value.__cause__ is original


# ---------- _is_absolute_like 数字与特殊字符 ----------

def test_is_absolute_like_digit_drive_batch48():
    """数字不是 isalpha。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_drive_batch48():
    """下划线不是 isalpha。"""
    assert _is_absolute_like("_:\\foo") is False


def test_is_absolute_like_only_colon_batch48():
    """只有冒号 → len < 3 → False。"""
    assert _is_absolute_like(":") is False


def test_is_absolute_like_two_chars_batch48():
    """2 字符不够长。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_posix_root_only_batch48():
    """单 / 是绝对路径。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_three_slash_batch48():
    assert _is_absolute_like("///") is True


def test_is_absolute_like_windows_unc_batch48():
    """\\\\server\\share 不是绝对路径（按本工具逻辑）。"""
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_chinese_drive_batch48():
    """中文字符 isalpha() 也是 True（Unicode letter）。"""
    assert _is_absolute_like("文:\\foo") is True


def test_is_absolute_like_japanese_drive_batch48():
    """日文字符也是 isalpha。"""
    assert _is_absolute_like("あ:/foo") is True


# ---------- _has_backslash 多次出现 ----------

def test_has_backslash_multiple_batch48():
    assert _has_backslash("a\\b\\c\\d") is True


def test_has_backslash_only_backslash_batch48():
    assert _has_backslash("\\") is True


def test_has_backslash_starts_with_batch48():
    assert _has_backslash("\\foo") is True


def test_has_backslash_ends_with_batch48():
    assert _has_backslash("foo\\") is True


def test_has_backslash_no_backslash_batch48():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_empty_batch48():
    assert _has_backslash("") is False


def test_has_backslash_only_forward_batch48():
    assert _has_backslash("////") is False


# ---------- _resolve_relative_path 复杂场景 ----------

def test_resolve_relative_path_chinese_path_batch48(tmp_path):
    """中文路径应能解析。"""
    (tmp_path / "中文").mkdir()
    out = _resolve_relative_path("中文/file.pdf", tmp_path, "x")
    assert out == (tmp_path / "中文" / "file.pdf").resolve()


def test_resolve_relative_path_deep_nested_batch48(tmp_path):
    (tmp_path / "a" / "b" / "c" / "d").mkdir(parents=True)
    out = _resolve_relative_path("a/b/c/d/file.pdf", tmp_path, "x")
    assert out == (tmp_path / "a" / "b" / "c" / "d" / "file.pdf").resolve()


def test_resolve_relative_path_with_dot_batch48(tmp_path):
    """./foo → project_root/foo。"""
    out = _resolve_relative_path("./foo.pdf", tmp_path, "x")
    assert out == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_with_double_dot_inside_batch48(tmp_path):
    """a/b/../c → a/c（合法，不跨根）。"""
    out = _resolve_relative_path("a/b/../c/file.pdf", tmp_path, "x")
    assert out == (tmp_path / "a" / "c" / "file.pdf").resolve()


def test_resolve_relative_path_escape_top_batch48(tmp_path):
    """../ 跨根 → ManifestError。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../escape.pdf", tmp_path, "x")
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_empty_string_batch48(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "x")
    assert "为空" in str(exc_info.value)


def test_resolve_relative_path_absolute_posix_batch48(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "x")
    assert "绝对路径" in str(exc_info.value)


def test_resolve_relative_path_absolute_windows_batch48(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("C:\\Windows\\system32", tmp_path, "x")
    assert "绝对路径" in str(exc_info.value)


def test_resolve_relative_path_backslash_batch48(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("a\\b", tmp_path, "x")
    assert "正斜杠" in str(exc_info.value)


# ---------- load_manifest 异常路径 ----------

def test_load_manifest_file_not_exist_batch48(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "nofile.json")
    assert "不存在" in str(exc_info.value)


def test_load_manifest_bad_json_batch48(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_schema_invalid_batch48(tmp_path):
    """manifest_version 不是 const "1.0" → EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "2.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_version_mismatch_batch48(tmp_path):
    """Schema 通过但 manifest_version != 代码 MANIFEST_VERSION。"""
    # Schema 允许 const "1.0"，所以这里只能 mock validate
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with patch("evaluation.manifest.MANIFEST_VERSION", "2.0"):
        with pytest.raises(ManifestError) as exc_info:
            load_manifest(p, project_root=tmp_path)
        assert "不兼容" in str(exc_info.value)


def test_load_manifest_document_path_absolute_batch48(tmp_path):
    """document 的 path 是绝对路径 → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc_info.value)


def test_load_manifest_document_path_backslash_batch48(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc_info.value)


def test_load_manifest_document_path_escape_batch48(tmp_path):
    """document 的 path 跨根 → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "../escape.pdf", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(exc_info.value)


# ---------- load_manifest documents 多种字段组合 ----------

def test_load_manifest_document_with_all_fields_batch48(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "ann").mkdir()
    (tmp_path / "ann" / "a.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1",
            "path": "docs/a.pdf",
            "source_type": "pdf",
            "sha256": "a" * 64,
            "categories": ["cat_a", "cat_b"],
            "paired_with": "d2",
            "annotation_file": "ann/a.json",
            "expectations": {"element_count_by_type": {"paragraph": 5}},
        }],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.sha256 == "a" * 64
    assert d.categories == ("cat_a", "cat_b")
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "ann/a.json"
    assert d.annotation_resolved == (tmp_path / "ann" / "a.json").resolve()
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_document_minimal_batch48(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1",
            "path": "docs/a.pdf",
            "source_type": "pdf",
        }],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.sha256 is None
    assert d.categories == ()
    assert d.paired_with is None
    assert d.annotation_file_str is None
    assert d.annotation_resolved is None
    assert d.expectations is None


def test_load_manifest_multiple_documents_batch48(tmp_path):
    (tmp_path / "docs").mkdir()
    for n in ("a", "b", "c"):
        (tmp_path / "docs" / f"{n}.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "docs/a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "docs/b.pdf", "source_type": "pdf"},
            {"doc_id": "d3", "path": "docs/c.pdf", "source_type": "docx"},
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1


# ---------- load_manifest expected_failures 完整 ----------

def test_load_manifest_expected_failures_full_batch48(tmp_path):
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "x.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "bad1",
            "path": "bad/x.pdf",
            "expected_error_code": "parse_failed",
            "source_type": "pdf",
        }],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "bad1"
    assert ef.expected_error_code == "parse_failed"
    assert ef.source_type == "pdf"
    assert ef.path_str == "bad/x.pdf"
    assert ef.resolved_path == (tmp_path / "bad" / "x.pdf").resolve()


def test_load_manifest_expected_failures_no_source_type_batch48(tmp_path):
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "x.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "bad1",
            "path": "bad/x.pdf",
            "expected_error_code": "parse_failed",
        }],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_expected_failures_default_empty_batch48(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


# ---------- Manifest property 边界 ----------

def _make_doc(**kw):
    return DocumentEntry(
        doc_id=kw.get("doc_id", "d"),
        path_str=kw.get("path_str", "x.pdf"),
        resolved_path=kw.get("resolved_path", Path("/tmp/x.pdf")),
        source_type=kw.get("source_type", "pdf"),
        sha256=kw.get("sha256"),
        categories=kw.get("categories", ()),
        paired_with=kw.get("paired_with"),
        annotation_file_str=kw.get("annotation_file_str"),
        annotation_resolved=kw.get("annotation_resolved"),
        expectations=kw.get("expectations"),
    )


def _make_manifest(docs=None, efs=None, **kw):
    return Manifest(
        manifest_version=kw.get("manifest_version", "1.0"),
        devset_status=kw.get("devset_status", "incomplete"),
        documents=tuple(docs or []),
        expected_failures=tuple(efs or []),
        project_root=kw.get("project_root", Path("/tmp")),
    )


def test_manifest_file_count_batch48():
    m = _make_manifest(docs=[_make_doc(doc_id="d1"), _make_doc(doc_id="d2")])
    assert m.file_count == 2


def test_manifest_file_count_empty_batch48():
    m = _make_manifest()
    assert m.file_count == 0


def test_manifest_pdf_count_batch48():
    m = _make_manifest(docs=[
        _make_doc(doc_id="d1", source_type="pdf"),
        _make_doc(doc_id="d2", source_type="docx"),
        _make_doc(doc_id="d3", source_type="pdf"),
    ])
    assert m.pdf_count == 2


def test_manifest_docx_count_batch48():
    m = _make_manifest(docs=[
        _make_doc(doc_id="d1", source_type="pdf"),
        _make_doc(doc_id="d2", source_type="docx"),
    ])
    assert m.docx_count == 1


def test_manifest_pdf_plus_docx_not_total_batch48():
    """pdf_count + docx_count 不一定等于 file_count（有其他 source_type）。"""
    m = _make_manifest(docs=[
        _make_doc(doc_id="d1", source_type="pdf"),
        _make_doc(doc_id="d2", source_type="txt"),  # 不算 pdf/docx
    ])
    assert m.pdf_count + m.docx_count == 1
    assert m.file_count == 2


def test_manifest_content_group_count_all_unpaired_batch48():
    m = _make_manifest(docs=[
        _make_doc(doc_id="d1"),
        _make_doc(doc_id="d2"),
        _make_doc(doc_id="d3"),
    ])
    assert m.content_group_count == 3


def test_manifest_content_group_count_all_paired_batch48():
    m = _make_manifest(docs=[
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
    ])
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch48():
    m = _make_manifest(docs=[
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
        _make_doc(doc_id="d3"),  # unpaired
    ])
    assert m.content_group_count == 2


def test_manifest_content_group_count_empty_batch48():
    m = _make_manifest()
    assert m.content_group_count == 0


def test_manifest_categories_covered_empty_batch48():
    m = _make_manifest()
    assert m.categories_covered == []


def test_manifest_categories_covered_unique_batch48():
    m = _make_manifest(docs=[
        _make_doc(categories=("a", "b")),
        _make_doc(categories=("b", "c")),
    ])
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_sorted_batch48():
    m = _make_manifest(docs=[_make_doc(categories=("z", "a", "m"))])
    assert m.categories_covered == ["a", "m", "z"]


# ---------- _detect_project_root 多种场景 ----------

def test_detect_project_root_finds_pyproject_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


def test_detect_project_root_nested_pyproject_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep").mkdir()
    f = tmp_path / "sub" / "deep" / "file.txt"
    f.write_text("x", encoding="utf-8")
    root = _detect_project_root(f)
    assert root == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_curdir_batch48(tmp_path):
    """向上找不到 pyproject → 返回 curdir（start 父目录）。"""
    (tmp_path / "sub").mkdir()
    f = tmp_path / "sub" / "file.txt"
    f.write_text("x", encoding="utf-8")
    root = _detect_project_root(f)
    # 没有 pyproject.toml 时，返回 cur.parent（即 tmp_path/sub）
    # 或某个上层（看 tmp_path 之上有没有）
    assert root.name in ("sub", tmp_path.name)


def test_detect_project_root_file_input_batch48(tmp_path):
    """传入文件路径应自动取 parent。"""
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    root = _detect_project_root(f)
    assert root == tmp_path.resolve()


# ---------- module source 字符串补强 ----------

def test_source_contains_关键不变量_batch48():
    src = inspect.getsource(manifest_mod)
    assert "关键不变量" in src


def test_source_contains_path_字段_batch48():
    src = inspect.getsource(manifest_mod)
    assert "path 字段" in src or "path 字段必须" in src


def test_source_contains_正斜杠_batch48():
    src = inspect.getsource(manifest_mod)
    assert "正斜杠" in src


def test_source_contains_项目根目录内_batch48():
    src = inspect.getsource(manifest_mod)
    assert "项目根目录" in src


def test_source_contains_frozen_True_batch48():
    src = inspect.getsource(manifest_mod)
    assert "frozen=True" in src


def test_source_contains_dataclass_batch48():
    src = inspect.getsource(manifest_mod)
    assert "@dataclass" in src


def test_source_contains_ManifestError_docstring_batch48():
    src = inspect.getsource(manifest_mod)
    assert "清单加载或校验失败" in src


def test_source_contains_no_hardcoded_paths_batch48():
    src = inspect.getsource(manifest_mod)
    assert "C:\\\\Users" not in src
    assert "/Users/zzhn" not in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5  # _is_absolute_like / _has_backslash / _resolve_relative_path / load_manifest / _detect_project_root


def test_ast_top_level_classes_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4  # ManifestError / DocumentEntry / ExpectedFailure / Manifest


def test_ast_document_entry_field_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry"][0]
    # 10 个 annotated assignment: doc_id / path_str / resolved_path / source_type /
    # sha256 / categories / paired_with / annotation_file_str / annotation_resolved / expectations
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 10


def test_ast_expected_failure_field_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpectedFailure"][0]
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 5


def test_ast_manifest_field_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest"][0]
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    # 5 字段：manifest_version / devset_status / documents / expected_failures / project_root
    assert len(annots) == 5


def test_ast_manifest_property_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest"][0]
    property_count = 0
    for n in cls.body:
        if isinstance(n, ast.FunctionDef):
            for d in n.decorator_list:
                if isinstance(d, ast.Name) and d.id == "property":
                    property_count += 1
    assert property_count == 5  # file_count / pdf_count / docx_count / content_group_count / categories_covered


def test_ast_manifest_error_no_methods_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManifestError"][0]
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 0


def test_ast_load_manifest_has_two_for_loops_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest"][0]
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 2  # documents + expected_failures


def test_ast_load_manifest_has_try_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest"][0]
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_resolve_relative_path_has_try_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path"][0]
    trys = [n for n in func.body if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_resolve_relative_path_has_multiple_if_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path"][0]
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    assert len(ifs) >= 3  # empty / absolute / backslash


def test_ast_detect_project_root_has_for_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root"][0]
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_dataclass_decorators_count_batch48():
    """3 个 @dataclass(frozen=True) 装饰器。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    dataclass_count = 0
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            for d in n.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass":
                    dataclass_count += 1
    assert dataclass_count == 3


def test_ast_no_async_function_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in ast.walk(tree):
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


# ---------- forbidden tokens 第一百一十五批 ----------

def test_source_no_eval_batch48():
    src = inspect.getsource(manifest_mod)
    assert "eval(" not in src


def test_source_no_exec_batch48():
    src = inspect.getsource(manifest_mod)
    assert "exec(" not in src


def test_source_no_compile_batch48():
    src = inspect.getsource(manifest_mod)
    assert "compile(" not in src


def test_source_no_globals_batch48():
    src = inspect.getsource(manifest_mod)
    assert "globals(" not in src


def test_source_no_locals_batch48():
    src = inspect.getsource(manifest_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch48():
    src = inspect.getsource(manifest_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch48():
    src = inspect.getsource(manifest_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch48():
    src = inspect.getsource(manifest_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch48():
    src = inspect.getsource(manifest_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch48():
    src = inspect.getsource(manifest_mod)
    assert "subprocess" not in src


def test_source_no_lambda_batch48():
    src = inspect.getsource(manifest_mod)
    assert "lambda" not in src


def test_source_no_yield_batch48():
    src = inspect.getsource(manifest_mod)
    assert "yield" not in src


def test_source_no_walrus_batch48():
    src = inspect.getsource(manifest_mod)
    assert ":=" not in src


def test_source_no_async_batch48():
    src = inspect.getsource(manifest_mod)
    assert "async def" not in src


def test_source_no_await_batch48():
    src = inspect.getsource(manifest_mod)
    assert "await " not in src
