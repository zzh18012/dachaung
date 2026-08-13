"""evaluation/manifest.py 第八十七轮 edges 测试（Round 637）。

补强 edges71 未触及的角度（第四十六批）。

新角度：
- _is_absolute_like 更多 Unicode 与符号组合
- _has_backslash 更多组合
- DocumentEntry dataclass repr/str
- ExpectedFailure dataclass repr/str
- Manifest property 边界（content_group_count 复杂场景）
- _resolve_relative_path 跨盘符
- load_manifest 完整 documents
- load_manifest annotation_file 处理
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百零七批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError, asdict, fields, replace
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


# ---------- _is_absolute_like 更多组合 ----------

def test_is_absolute_like_tilde_batch46():
    """~ 不是绝对路径（POSIX 用 home 展开，但字符串本身相对）。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_double_colon_batch46():
    assert _is_absolute_like("::") is False


def test_is_absolute_like_three_chars_no_separator_batch46():
    assert _is_absolute_like("C:f") is False


def test_is_absolute_like_four_chars_with_separator_batch46():
    assert _is_absolute_like("C:/x") is True


def test_is_absolute_like_drive_only_three_chars_batch46():
    """正好 3 字符 + 第 2 是冒号 + 第 3 是 \\ 或 /。"""
    assert _is_absolute_like("C:\\") is True
    assert _is_absolute_like("C:/") is True


def test_is_absolute_like_dot_posix_batch46():
    """./foo 视为相对。"""
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_backslash_only_batch46():
    """单 \\ 不是绝对（Windows 通常 \\ 是）。"""
    # 实际：len < 3 → 不到 Windows 盘符分支；不以 / 开头 → False
    assert _is_absolute_like("\\") is False


def test_is_absolute_like_double_backslash_batch46():
    """\\\\foo 不算（不以 / 开头，且第 1 字符不是字母 + 第 2 不是冒号）。"""
    assert _is_absolute_like("\\\\foo") is False


def test_is_absolute_like_capsule_emoji_batch46():
    """emoji 不是 isalpha。"""
    assert _is_absolute_like("🚀:\\foo") is False


def test_is_absolute_like_minus_drive_batch46():
    """- 不是 isalpha。"""
    assert _is_absolute_like("-:/foo") is False


def test_is_absolute_like_uppercase_alpha_batch46():
    assert _is_absolute_like("Z:\\foo") is True


def test_is_absolute_like_lowercase_alpha_batch46():
    assert _is_absolute_like("z:\\foo") is True


# ---------- _has_backslash 更多组合 ----------

def test_has_backslash_only_one_batch46():
    assert _has_backslash("a\\b") is True


def test_has_backslash_many_slashes_batch46():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_mixed_slashes_batch46():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_unicode_string_batch46():
    assert _has_backslash("测试\\路径") is True


def test_has_backslash_emoji_string_batch46():
    assert _has_backslash("🎉\\🚀") is True


# ---------- DocumentEntry repr ----------

def _make_doc_entry(**kwargs):
    return DocumentEntry(
        doc_id=kwargs.get("doc_id", "d1"),
        path_str=kwargs.get("path_str", "a/b.pdf"),
        resolved_path=kwargs.get("resolved_path", Path("/tmp/a/b.pdf")),
        source_type=kwargs.get("source_type", "pdf"),
        sha256=kwargs.get("sha256"),
        categories=kwargs.get("categories", ()),
        paired_with=kwargs.get("paired_with"),
        annotation_file_str=kwargs.get("annotation_file_str"),
        annotation_resolved=kwargs.get("annotation_resolved"),
        expectations=kwargs.get("expectations"),
    )


def test_document_entry_repr_batch46():
    d = _make_doc_entry()
    r = repr(d)
    assert "DocumentEntry" in r
    assert "d1" in r


def test_document_entry_str_batch46():
    d = _make_doc_entry()
    s = str(d)
    assert "DocumentEntry" in s


def test_document_entry_immutable_categories_batch46():
    d = _make_doc_entry(categories=("a", "b"))
    # frozen dataclass：直接给字段赋值应触发 FrozenInstanceError
    with pytest.raises((TypeError, FrozenInstanceError)):
        d.categories = ("c",)  # type: ignore[misc]


def test_document_entry_match_args_batch46():
    """__match_args__ 应该等于 fields names 顺序。"""
    expected = tuple(f.name for f in fields(DocumentEntry))
    assert DocumentEntry.__match_args__ == expected


def test_document_entry_in_dict_key_batch46():
    """frozen dataclass hashable → 可做 dict key。"""
    d1 = _make_doc_entry()
    d2 = _make_doc_entry()
    d = {d1: "value"}
    assert d[d2] == "value"  # hashable + eq


# ---------- ExpectedFailure repr ----------

def _make_expected_failure(**kwargs):
    return ExpectedFailure(
        doc_id=kwargs.get("doc_id", "ef1"),
        path_str=kwargs.get("path_str", "bad/x.pdf"),
        resolved_path=kwargs.get("resolved_path", Path("/tmp/bad/x.pdf")),
        expected_error_code=kwargs.get("expected_error_code", "parse_failed"),
        source_type=kwargs.get("source_type", "pdf"),
    )


def test_expected_failure_repr_batch46():
    ef = _make_expected_failure()
    r = repr(ef)
    assert "ExpectedFailure" in r
    assert "ef1" in r


def test_expected_failure_str_batch46():
    ef = _make_expected_failure()
    s = str(ef)
    assert "ExpectedFailure" in s


def test_expected_failure_match_args_batch46():
    expected = tuple(f.name for f in fields(ExpectedFailure))
    assert ExpectedFailure.__match_args__ == expected


def test_expected_failure_in_dict_key_batch46():
    ef1 = _make_expected_failure()
    ef2 = _make_expected_failure()
    d = {ef1: "value"}
    assert d[ef2] == "value"


# ---------- Manifest property 边界 ----------

def _make_manifest(**kwargs):
    return Manifest(
        manifest_version="1.0",
        devset_status=kwargs.get("devset_status", "incomplete"),
        documents=tuple(kwargs.get("documents", [])),
        expected_failures=tuple(kwargs.get("expected_failures", [])),
        project_root=kwargs.get("project_root", Path("/tmp")),
    )


def test_manifest_content_group_count_chain_pair_batch46():
    """A→B, B→C, C→A：frozenset 去重后是 1 组 {A,B,C}。

    实际实现：A→B → frozenset{A,B}; B→C → frozenset{B,C}; C→A → frozenset{A,C}
    3 个 frozenset，3 组。"""
    docs = [
        _make_doc_entry(doc_id="A", paired_with="B"),
        _make_doc_entry(doc_id="B", paired_with="C"),
        _make_doc_entry(doc_id="C", paired_with="A"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_self_pair_batch46():
    """A→A 自指 → frozenset{A} 单元素。"""
    docs = [
        _make_doc_entry(doc_id="A", paired_with="A"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_with_missing_batch46():
    """配对目标不在 documents 中。"""
    docs = [
        _make_doc_entry(doc_id="A", paired_with="X"),  # X 不存在
    ]
    m = _make_manifest(documents=docs)
    # frozenset{A, X} → 1 group; A 在 seen，unpaired=0
    assert m.content_group_count == 1


def test_manifest_categories_covered_single_batch46():
    docs = [_make_doc_entry(categories=("a",))]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a"]


def test_manifest_categories_covered_with_none_batch46():
    docs = [_make_doc_entry(categories=())]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == []


def test_manifest_categories_covered_unicode_batch46():
    docs = [_make_doc_entry(categories=("中文", "english"))]
    m = _make_manifest(documents=docs)
    # 排序：ASCII < 中文（按 Unicode 码点）
    assert m.categories_covered == ["english", "中文"]


def test_manifest_repr_batch46():
    m = _make_manifest()
    r = repr(m)
    assert "Manifest" in r


def test_manifest_match_args_batch46():
    expected = tuple(f.name for f in fields(Manifest))
    assert Manifest.__match_args__ == expected


def test_manifest_in_dict_key_batch46():
    m1 = _make_manifest()
    m2 = _make_manifest()
    d = {m1: "value"}
    assert d[m2] == "value"


# ---------- _resolve_relative_path 跨盘符 ----------

def test_resolve_relative_path_dot_dot_only_batch46(tmp_path):
    """纯 ../ 路径。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../", tmp_path, "x")
    # tmp_path 的 parent 仍在 tmp_path 之外
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_single_dot_batch46(tmp_path):
    """./file 应该解析到 project_root/file。"""
    out = _resolve_relative_path("./file.pdf", tmp_path, "x")
    assert out == (tmp_path / "file.pdf").resolve()


def test_resolve_relative_path_nested_batch46(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    out = _resolve_relative_path("a/b/file.pdf", tmp_path, "x")
    assert out == (tmp_path / "a" / "b" / "file.pdf").resolve()


def test_resolve_relative_path_subdir_escape_batch46(tmp_path):
    """a/../../etc → 跨根。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("a/../../etc", tmp_path, "x")


# ---------- load_manifest 完整 documents ----------

def test_load_manifest_one_document_batch46(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "docs/a.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["cat1", "cat2"],
            }
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.source_type == "pdf"
    assert d.sha256 == "a" * 64
    assert d.categories == ("cat1", "cat2")


def test_load_manifest_with_annotation_file_batch46(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "ann").mkdir()
    (tmp_path / "ann" / "a.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "docs/a.pdf",
                "source_type": "pdf",
                "annotation_file": "ann/a.json",
            }
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.annotation_file_str == "ann/a.json"
    assert d.annotation_resolved is not None
    assert d.annotation_resolved == (tmp_path / "ann" / "a.json").resolve()


def test_load_manifest_with_paired_with_batch46(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "docs" / "b.docx").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "docs/a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "docs/b.docx", "source_type": "docx", "paired_with": "d1"},
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 1


def test_load_manifest_with_expectations_batch46(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "docs/a.pdf",
                "source_type": "pdf",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            }
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_devset_status_complete_batch46(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"


# ---------- _detect_project_root 更多 ----------

def test_detect_project_root_nested_file_batch46(tmp_path):
    """嵌套文件路径 → 从父目录找。"""
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    f = tmp_path / "sub" / "file.txt"
    f.write_text("x", encoding="utf-8")
    root = _detect_project_root(f)
    assert root == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_batch46(tmp_path):
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


# ---------- module source 补强 ----------

def test_source_contains_关键不变量_batch46():
    src = inspect.getsource(manifest_mod)
    assert "关键不变量" in src


def test_source_contains_正斜杠_batch46():
    src = inspect.getsource(manifest_mod)
    assert "正斜杠" in src


def test_source_contains_项目根目录内_batch46():
    src = inspect.getsource(manifest_mod)
    assert "项目根目录" in src


def test_source_contains_本机绝对路径_batch46():
    src = inspect.getsource(manifest_mod)
    assert "本机绝对路径" in src or "绝对路径" in src


def test_source_contains_manifest_error_class_docstring_batch46():
    src = inspect.getsource(manifest_mod)
    assert "清单加载或校验失败" in src


def test_source_contains_resolve_relative_path_docstring_batch46():
    src = inspect.getsource(manifest_mod)
    assert "校验路径形式并解析为绝对路径" in src


def test_source_contains_content_group_count_docstring_batch46():
    src = inspect.getsource(manifest_mod)
    assert "配对的 DOCX+PDF" in src


def test_source_contains_no_hardcoded_paths_batch46():
    """源码中不应有硬编码绝对路径。"""
    src = inspect.getsource(manifest_mod)
    # 不应有 C:\ 或 /Users/ 等
    assert "C:\\\\Users\\\\" not in src
    assert "/Users/" not in src


# ---------- AST 结构补强 ----------

def test_ast_resolve_relative_path_has_multiple_if_batch46():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path"][0]
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    # 至少 3 个 if（empty / absolute / backslash）
    assert len(ifs) >= 3


def test_ast_resolve_relative_path_has_try_batch46():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path"][0]
    trys = [n for n in func.body if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_load_manifest_has_two_for_loops_batch46():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest"][0]
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    # documents + expected_failures
    assert len(fors) >= 2


def test_ast_manifest_class_has_property_decorators_batch46():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest"][0]
    property_count = 0
    for n in cls.body:
        if isinstance(n, ast.FunctionDef):
            for d in n.decorator_list:
                if isinstance(d, ast.Name) and d.id == "property":
                    property_count += 1
    assert property_count == 5


def test_ast_document_entry_decorated_with_dataclass_frozen_batch46():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry"][0]
    assert len(cls.decorator_list) == 1
    dec = cls.decorator_list[0]
    assert isinstance(dec, ast.Call)
    assert isinstance(dec.func, ast.Name)
    assert dec.func.id == "dataclass"


def test_ast_dataclass_call_has_frozen_true_batch46():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry"][0]
    dec = cls.decorator_list[0]
    # frozen=True 关键字参数
    found_frozen = False
    for kw in dec.keywords:
        if kw.arg == "frozen":
            assert isinstance(kw.value, ast.Constant)
            assert kw.value.value is True
            found_frozen = True
    assert found_frozen


def test_ast_manifest_error_no_methods_batch46():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManifestError"][0]
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 0


# ---------- forbidden tokens 第一百零七批 ----------

def test_source_no_eval_batch46():
    src = inspect.getsource(manifest_mod)
    assert "eval(" not in src


def test_source_no_exec_batch46():
    src = inspect.getsource(manifest_mod)
    assert "exec(" not in src


def test_source_no_compile_batch46():
    src = inspect.getsource(manifest_mod)
    assert "compile(" not in src


def test_source_no_globals_batch46():
    src = inspect.getsource(manifest_mod)
    assert "globals(" not in src


def test_source_no_locals_batch46():
    src = inspect.getsource(manifest_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch46():
    src = inspect.getsource(manifest_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch46():
    src = inspect.getsource(manifest_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch46():
    src = inspect.getsource(manifest_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch46():
    src = inspect.getsource(manifest_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch46():
    src = inspect.getsource(manifest_mod)
    assert "subprocess" not in src


def test_source_no_lambda_batch46():
    src = inspect.getsource(manifest_mod)
    assert "lambda" not in src


def test_source_no_yield_batch46():
    src = inspect.getsource(manifest_mod)
    assert "yield" not in src


def test_source_no_walrus_batch46():
    src = inspect.getsource(manifest_mod)
    assert ":=" not in src


def test_source_no_async_batch46():
    src = inspect.getsource(manifest_mod)
    assert "async def" not in src


def test_source_no_await_batch46():
    src = inspect.getsource(manifest_mod)
    assert "await " not in src
