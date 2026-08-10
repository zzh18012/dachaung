"""evaluation/manifest.py 第二十五轮 edges 测试（Round 313）。

重点补强 edges24 未触及的角度：
- _is_absolute_like 边界深度
- _has_backslash 边界深度
- _resolve_relative_path 各错误分支精确
- _detect_project_root 行为深度
- ManifestError 实例化
- DocumentEntry/ExpectedFailure/Manifest dataclass frozen
- Manifest properties 边界
- module source forbidden tokens
- module source 字符串精确
- signatures 精确
- 端到端集成
- 模块整体合理性
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest

import evaluation.manifest as m
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


# ---------- _is_absolute_like 边界深度 ----------


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_posix_absolute():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_posix_relative():
    assert _is_absolute_like("samples/x.pdf") is False


def test_is_absolute_like_windows_drive_backslash():
    assert _is_absolute_like("C:\\\\foo") is True


def test_is_absolute_like_windows_drive_forward_slash():
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("d:/foo") is True


def test_is_absolute_like_uppercase_drive():
    assert _is_absolute_like("D:/foo") is True


def test_is_absolute_like_short_string():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_colon_no_slash():
    # C:foo 不是绝对路径（Windows drive-relative）
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_just_drive_letter():
    assert _is_absolute_like("C") is False


def test_is_absolute_like_two_chars():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_three_chars_no_separator():
    assert _is_absolute_like("C:a") is False


def test_is_absolute_like_three_chars_with_slash():
    assert _is_absolute_like("C:/") is True


def test_is_absolute_like_three_chars_with_backslash():
    assert _is_absolute_like("C:\\\\") is True


def test_is_absolute_like_digit_drive():
    # 数字不是字母
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_unicode_letter_drive():
    # 中文 letter drive（isalpha 返回 True for 中文）
    # 但 Windows 不识别；代码用 isalpha()，所以 True
    result = _is_absolute_like("你:/foo")
    # 你.isalpha() → True，但首字符是 [0]:"你"，[1]:":"，[2]:"/" → True
    assert result is True


# ---------- _has_backslash 边界深度 ----------


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_with_backslash():
    assert _has_backslash("foo\\\\bar") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\\\") is True


def test_has_backslash_trailing():
    assert _has_backslash("foo\\\\") is True


def test_has_backslash_leading():
    assert _has_backslash("\\\\foo") is True


def test_has_backslash_one_char_no():
    assert _has_backslash("a") is False


# ---------- _resolve_relative_path 各错误分支精确 ----------


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "x")
    assert "为空" in str(ei.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "x")
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_absolute_windows_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("C:/foo", tmp_path, "x")
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("foo\\\\bar", tmp_path, "x")
    assert "反斜杠" in str(ei.value)


def test_resolve_relative_path_outside_root_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../../etc/passwd", tmp_path, "x")
    assert "项目根目录之外" in str(ei.value)


def test_resolve_relative_path_inside_root_succeeds(tmp_path):
    # 创建子目录使其存在
    sub = tmp_path / "samples"
    sub.mkdir()
    out = _resolve_relative_path("samples/x.pdf", tmp_path, "x")
    assert isinstance(out, Path)
    assert out.parent == sub


def test_resolve_relative_path_returns_absolute_path(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    out = _resolve_relative_path("samples/x.pdf", tmp_path, "x")
    assert out.is_absolute()


def test_resolve_relative_path_normalizes_dot_segments(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    out = _resolve_relative_path("samples/./x.pdf", tmp_path, "x")
    # ./ 应被 resolve() 消除
    assert "/./" not in str(out).replace("\\\\", "/")


def test_resolve_relative_path_field_name_in_message(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


# ---------- _detect_project_root 行为深度 ----------


def test_detect_project_root_finds_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


def test_detect_project_root_for_file_starts_at_parent(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]\n", encoding="utf-8")
    f = tmp_path / "x.txt"
    f.write_text("hi", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_input_if_no_pyproject(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _detect_project_root(sub)
    assert out == sub.resolve()


def test_detect_project_root_walks_up_multiple_levels(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]\n", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    out = _detect_project_root(deep)
    assert out == tmp_path.resolve()


def test_detect_project_root_with_path_object_returns_path():
    out = _detect_project_root(Path(__file__))
    assert isinstance(out, Path)


# ---------- ManifestError 实例化 ----------


def test_manifest_error_message():
    err = ManifestError("hello")
    assert str(err) == "hello"


def test_manifest_error_is_exception():
    err = ManifestError("x")
    assert isinstance(err, Exception)


def test_manifest_error_can_be_raised():
    with pytest.raises(ManifestError):
        raise ManifestError("x")


def test_manifest_error_caught_as_exception():
    with pytest.raises(Exception) as ei:
        raise ManifestError("x")
    assert isinstance(ei.value, ManifestError)


def test_manifest_error_no_custom_init():
    """ManifestError 没有自定义 __init__。"""
    src = inspect.getsource(ManifestError)
    # 只有 class 声明 + docstring，没有 __init__
    assert "def __init__" not in src


def test_manifest_error_bases_is_exception_only():
    assert ManifestError.__bases__ == (Exception,)


def test_manifest_error_namespace_is_evaluation_manifest():
    assert ManifestError.__module__ == "evaluation.manifest"


# ---------- DocumentEntry dataclass ----------


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen():
    de = DocumentEntry(
        doc_id="x",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        de.doc_id = "y"  # type: ignore[misc]


def test_document_entry_field_count_10():
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names():
    names = [f.name for f in fields(DocumentEntry)]
    assert names == [
        "doc_id",
        "path_str",
        "resolved_path",
        "source_type",
        "sha256",
        "categories",
        "paired_with",
        "annotation_file_str",
        "annotation_resolved",
        "expectations",
    ]


# ---------- ExpectedFailure dataclass ----------


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen():
    ef = ExpectedFailure(
        doc_id="x",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        expected_error_code="some_code",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "y"  # type: ignore[misc]


def test_expected_failure_field_count_5():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names():
    names = [f.name for f in fields(ExpectedFailure)]
    assert names == [
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    ]


# ---------- Manifest dataclass ----------


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_field_count_5():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names():
    names = [f.name for f in fields(Manifest)]
    assert names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_manifest_properties_count_5():
    properties = [
        "file_count",
        "pdf_count",
        "docx_count",
        "content_group_count",
        "categories_covered",
    ]
    for p in properties:
        assert isinstance(
            getattr(Manifest, p),
            property,
        )


def test_manifest_file_count_returns_int():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.file_count, int)
    assert mf.file_count == 0


def test_manifest_pdf_count_zero_when_empty():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.pdf_count == 0


def test_manifest_docx_count_zero_when_empty():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.docx_count == 0


def test_manifest_content_group_count_zero_when_empty():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 0


def test_manifest_categories_covered_returns_list_when_empty():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == []


# ---------- module source forbidden tokens ----------


@pytest.mark.parametrize(
    "token",
    [
        "import time",
        "import random",
        "import uuid",
        "import hashlib",
        "import secrets",
        "import subprocess",
        "import socket",
        "import email",
        "import html",
        "import http",
        "import urllib",
        "import sqlite3",
        "import csv",
        "import pickle",
        "import tempfile",
        "import shutil",
        "import glob",
        "import os",
        "import sys",
        "import logging",
        "import threading",
        "import asyncio",
        "import re",
        "import datetime",
        "import itertools",
        "import functools",
        "import collections",
        "import math",
    ],
)
def test_module_source_forbidden_tokens(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 必要 imports ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_has_from_dataclasses_import_dataclass():
    src = inspect.getsource(m)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_evaluation_import():
    src = inspect.getsource(m)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_schema_import():
    src = inspect.getsource(m)
    assert "from evaluation.schema import validate" in src


# ---------- module source 字符串精确 ----------


def test_module_source_has_class_manifest_error():
    src = inspect.getsource(m)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_dataclass_decorator():
    src = inspect.getsource(m)
    assert "@dataclass(frozen=True)" in src


def test_module_source_has_3_dataclasses():
    src = inspect.getsource(m)
    # DocumentEntry, ExpectedFailure, Manifest
    assert "class DocumentEntry" in src
    assert "class ExpectedFailure" in src
    assert "class Manifest" in src


def test_module_source_has_is_absolute_like_def():
    src = inspect.getsource(m)
    assert "def _is_absolute_like(path_str: str) -> bool:" in src


def test_module_source_has_has_backslash_def():
    src = inspect.getsource(m)
    assert "def _has_backslash(path_str: str) -> bool:" in src


def test_module_source_has_resolve_relative_path_def():
    src = inspect.getsource(m)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_load_manifest_def():
    src = inspect.getsource(m)
    assert "def load_manifest(" in src


def test_module_source_has_detect_project_root_def():
    src = inspect.getsource(m)
    assert "def _detect_project_root(start: Path) -> Path:" in src


def test_module_source_has_property_decorators():
    src = inspect.getsource(m)
    assert "@property" in src


def test_module_source_has_5_property_defs():
    src = inspect.getsource(m)
    for prop in (
        "def file_count(self",
        "def pdf_count(self",
        "def docx_count(self",
        "def content_group_count(self",
        "def categories_covered(self",
    ):
        assert prop in src


def test_module_source_has_validate_call():
    src = inspect.getsource(m)
    assert 'validate(data, "manifest.schema.json")' in src


def test_module_source_has_manifest_version_check():
    src = inspect.getsource(m)
    assert 'data.get("manifest_version") != MANIFEST_VERSION' in src


def test_module_source_has_documents_loop():
    src = inspect.getsource(m)
    assert 'for d in data.get("documents", []):' in src


def test_module_source_has_expected_failures_loop():
    src = inspect.getsource(m)
    assert 'for ef in data.get("expected_failures", []):' in src


def test_module_source_has_categories_tuple_conversion():
    src = inspect.getsource(m)
    assert "tuple(d.get(\"categories\", []))" in src


def test_module_source_has_paired_with_field():
    src = inspect.getsource(m)
    assert "paired_with" in src


def test_module_source_has_annotation_file_field():
    src = inspect.getsource(m)
    assert "annotation_file" in src


def test_module_source_has_json_decode_error_handler():
    src = inspect.getsource(m)
    assert "except json.JSONDecodeError as e:" in src


def test_module_source_has_json_load_call():
    src = inspect.getsource(m)
    assert "json.load(f)" in src


def test_module_source_has_relative_to_call():
    src = inspect.getsource(m)
    assert "resolved.relative_to(project_root_resolved)" in src


def test_module_source_has_resolve_call():
    src = inspect.getsource(m)
    assert "(project_root / path_str).resolve()" in src


def test_module_source_has_docstring_constraints():
    src = inspect.getsource(m)
    assert "正斜杠" in src
    assert "项目根目录内" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


# ---------- signatures 精确 ----------


def test_load_manifest_signature_2_params():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_manifest_path_annotation_union():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].annotation == "Path | str"


def test_load_manifest_project_root_annotation_optional_union():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].annotation == "Path | str | None"


def test_load_manifest_return_annotation_manifest():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_is_absolute_like_signature():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_has_backslash_signature():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_resolve_relative_path_signature():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_detect_project_root_signature():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]
    assert sig.parameters["start"].annotation == "Path"
    assert sig.return_annotation == "Path"


# ---------- namespace 检查 ----------


def test_load_manifest_namespace():
    assert load_manifest.__module__ == "evaluation.manifest"


def test_is_absolute_like_namespace():
    assert _is_absolute_like.__module__ == "evaluation.manifest"


def test_has_backslash_namespace():
    assert _has_backslash.__module__ == "evaluation.manifest"


def test_resolve_relative_path_namespace():
    assert _resolve_relative_path.__module__ == "evaluation.manifest"


def test_detect_project_root_namespace():
    assert _detect_project_root.__module__ == "evaluation.manifest"


def test_document_entry_namespace():
    assert DocumentEntry.__module__ == "evaluation.manifest"


def test_expected_failure_namespace():
    assert ExpectedFailure.__module__ == "evaluation.manifest"


def test_manifest_namespace():
    assert Manifest.__module__ == "evaluation.manifest"


# ---------- module 整体合理性 ----------


def test_module_all_has_5_entries():
    assert set(m.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_all_count_is_5():
    assert len(m.__all__) == 5


def test_module_has_3_dataclasses():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and getattr(m, n).__module__ == "evaluation.manifest"
        and is_dataclass(getattr(m, n))
    ]
    assert set(classes) == {"Manifest", "DocumentEntry", "ExpectedFailure"}


def test_manifest_error_is_not_dataclass():
    assert not is_dataclass(ManifestError)


def test_module_has_4_classes_total():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and getattr(m, n).__module__ == "evaluation.manifest"
    ]
    # 3 dataclass + ManifestError
    assert set(classes) == {"Manifest", "DocumentEntry", "ExpectedFailure", "ManifestError"}


def test_module_has_1_public_function():
    public_fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.manifest"
    ]
    assert public_fns == ["load_manifest"]


def test_module_has_4_private_functions():
    private_fns = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert set(private_fns) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "_detect_project_root",
    }


def test_module_has_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


def test_module_namespace_is_evaluation_manifest():
    assert m.__name__ == "evaluation.manifest"


# ---------- 端到端 load_manifest ----------


def _write_minimal_manifest(tmp_path, documents=None, expected_failures=None):
    if documents is None:
        documents = []
    if expected_failures is None:
        expected_failures = []
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": documents,
        "expected_failures": expected_failures,
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    # 同时创建 pyproject.toml 让 _detect_project_root 找到
    (tmp_path / "pyproject.toml").write_text("[tool.x]\n", encoding="utf-8")
    return p


def test_load_manifest_empty_documents_succeeds(tmp_path):
    p = _write_minimal_manifest(tmp_path)
    mf = load_manifest(p)
    assert mf.file_count == 0
    assert mf.documents == ()


def test_load_manifest_with_one_document(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("dummy", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, documents=[
        {
            "doc_id": "x",
            "path": "samples/x.pdf",
            "source_type": "pdf",
            "categories": ["tests"],
        }
    ])
    mf = load_manifest(p)
    assert mf.file_count == 1
    assert mf.pdf_count == 1
    assert mf.docx_count == 0
    assert mf.documents[0].doc_id == "x"
    assert mf.documents[0].source_type == "pdf"
    assert mf.documents[0].categories == ("tests",)


def test_load_manifest_missing_file_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path / "missing.json")
    assert "清单文件不存在" in str(ei.value)


def test_load_manifest_invalid_json_raises(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p)
    assert "JSON 解析失败" in str(ei.value)


def test_load_manifest_wrong_version_raises(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "2.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # 但 manifest_version 2.0 不通过 schema（const 1.0），所以会先抛 EvalSchemaError
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_with_expected_failures(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "bad.txt").write_text("dummy", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, expected_failures=[
        {
            "doc_id": "bad",
            "path": "samples/bad.txt",
            "expected_error_code": "unsupported_format",
            "source_type": "txt",
        }
    ])
    mf = load_manifest(p)
    assert len(mf.expected_failures) == 1
    assert mf.expected_failures[0].doc_id == "bad"
    assert mf.expected_failures[0].expected_error_code == "unsupported_format"


def test_load_manifest_categories_covered(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("dummy", encoding="utf-8")
    (sub / "y.pdf").write_text("dummy", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, documents=[
        {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
         "categories": ["a", "b"]},
        {"doc_id": "y", "path": "samples/y.pdf", "source_type": "pdf",
         "categories": ["b", "c"]},
    ])
    mf = load_manifest(p)
    assert mf.categories_covered == ["a", "b", "c"]


def test_load_manifest_str_path_accepted(tmp_path):
    p = _write_minimal_manifest(tmp_path)
    mf = load_manifest(str(p))
    assert isinstance(mf, Manifest)


def test_load_manifest_explicit_project_root(tmp_path):
    p = _write_minimal_manifest(tmp_path)
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.project_root == tmp_path.resolve()


def test_load_manifest_path_outside_root_raises(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("dummy", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "../../etc/passwd", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(ei.value) or "绝对路径" in str(ei.value)


def test_load_manifest_backslash_in_path_raises(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "sub\\\\x.pdf", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "反斜杠" in str(ei.value)
