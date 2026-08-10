"""evaluation/manifest.py 第二十六轮 edges 测试（Round 319）。

重点补强 edges25 未触及的角度：
- _is_absolute_like 边界补充
- _resolve_relative_path 错误消息精确
- Manifest properties 行为深度
- load_manifest 边界补充
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


# ---------- _is_absolute_like 边界补充 ----------


def test_is_absolute_like_just_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_just_backslash_no_drive():
    """just \\ 不被识别为绝对路径（无 drive letter）。"""
    assert _is_absolute_like("\\\\") is False


def test_is_absolute_like_two_letters_slash():
    assert _is_absolute_like("ab/cd") is False


def test_is_absolute_like_uppercase_y_drive():
    assert _is_absolute_like("Y:/foo") is True


def test_is_absolute_like_uppercase_z_drive():
    assert _is_absolute_like("Z:/foo") is True


def test_is_absolute_like_underscore_drive_not_letter():
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_space_drive_not_letter():
    assert _is_absolute_like(" :/foo") is False


# ---------- _has_backslash 边界补充 ----------


def test_has_backslash_two_backslashes():
    assert _has_backslash("a\\\\b\\\\c") is True


def test_has_backslash_only_forward_slash():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_mixed():
    assert _has_backslash("a/b\\\\c") is True


# ---------- _resolve_relative_path 错误消息精确 ----------


def test_resolve_relative_path_message_includes_field_name_for_empty(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


def test_resolve_relative_path_message_includes_path_for_absolute(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "F")
    assert "/etc/passwd" in str(ei.value)


def test_resolve_relative_path_message_includes_path_for_backslash(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("foo\\\\bar", tmp_path, "F")
    assert "foo\\\\bar" in str(ei.value) or "foo\\\\bar" in str(ei.value)


def test_resolve_relative_path_message_includes_resolved_for_outside(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../../etc/passwd", tmp_path, "F")
    msg = str(ei.value)
    assert "项目根目录之外" in msg
    # resolved 路径应在 message 中
    assert "etc" in msg or "passwd" in msg


def test_resolve_relative_path_normalizes_double_dots(tmp_path):
    """合法的相对路径 with .. 也被解析。"""
    sub = tmp_path / "a"
    sub.mkdir()
    inner = sub / "b"
    inner.mkdir()
    out = _resolve_relative_path("a/b/../b", tmp_path, "F")
    assert out == inner.resolve()


def test_resolve_relative_path_normalizes_single_dot(tmp_path):
    sub = tmp_path / "a"
    sub.mkdir()
    out = _resolve_relative_path("a/./b", tmp_path, "F")
    # /./ 被 resolve 消除
    assert "/./" not in str(out).replace("\\\\", "/")


# ---------- _detect_project_root 边界补充 ----------


def test_detect_project_root_path_object_input():
    p = Path(__file__)
    out = _detect_project_root(p)
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_detect_project_root_already_dir_input(tmp_path):
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_symlinked_input(tmp_path):
    """symlink 输入，resolve 后查 pyproject。"""
    real = tmp_path / "real"
    real.mkdir()
    (real / "pyproject.toml").write_text("x", encoding="utf-8")
    link = tmp_path / "link"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported")
    out = _detect_project_root(link)
    assert out == real.resolve()


# ---------- ManifestError 行为补充 ----------


def test_manifest_error_no_args():
    """ManifestError() 不带参数也能创建。"""
    err = ManifestError()
    assert isinstance(err, Exception)
    assert err.args == ()


def test_manifest_error_multiple_args():
    err = ManifestError("a", "b", "c")
    assert err.args == ("a", "b", "c")


def test_manifest_error_str_no_args():
    err = ManifestError()
    assert str(err) == ""


# ---------- DocumentEntry frozen 补充 ----------


def _make_doc_entry(**overrides):
    defaults = {
        "doc_id": "x",
        "path_str": "x.pdf",
        "resolved_path": Path("/tmp/x.pdf"),
        "source_type": "pdf",
        "sha256": None,
        "categories": (),
        "paired_with": None,
        "annotation_file_str": None,
        "annotation_resolved": None,
        "expectations": None,
    }
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_frozen_doc_id():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.doc_id = "y"  # type: ignore


def test_document_entry_frozen_path_str():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.path_str = "y"  # type: ignore


def test_document_entry_frozen_resolved_path():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.resolved_path = Path("/tmp/y")  # type: ignore


def test_document_entry_frozen_source_type():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.source_type = "docx"  # type: ignore


def test_document_entry_frozen_sha256():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.sha256 = "abc"  # type: ignore


def test_document_entry_frozen_categories():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.categories = ("a",)  # type: ignore


def test_document_entry_frozen_paired_with():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.paired_with = "y"  # type: ignore


def test_document_entry_frozen_annotation_file_str():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.annotation_file_str = "y"  # type: ignore


def test_document_entry_frozen_annotation_resolved():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.annotation_resolved = Path("/y")  # type: ignore


def test_document_entry_frozen_expectations():
    de = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        de.expectations = {}  # type: ignore


# ---------- ExpectedFailure frozen 补充 ----------


def _make_expected_failure(**overrides):
    defaults = {
        "doc_id": "x",
        "path_str": "x.pdf",
        "resolved_path": Path("/tmp/x.pdf"),
        "expected_error_code": "code",
        "source_type": None,
    }
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_frozen_doc_id():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "y"  # type: ignore


def test_expected_failure_frozen_path_str():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.path_str = "y"  # type: ignore


def test_expected_failure_frozen_resolved_path():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.resolved_path = Path("/y")  # type: ignore


def test_expected_failure_frozen_expected_error_code():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.expected_error_code = "y"  # type: ignore


def test_expected_failure_frozen_source_type():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.source_type = "pdf"  # type: ignore


# ---------- Manifest properties 行为深度 ----------


def _make_manifest(documents=(), expected_failures=(), **overrides):
    defaults = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": documents,
        "expected_failures": expected_failures,
        "project_root": Path("/tmp"),
    }
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_file_count_with_3_documents():
    docs = (
        _make_doc_entry(doc_id="x", source_type="pdf"),
        _make_doc_entry(doc_id="y", source_type="docx"),
        _make_doc_entry(doc_id="z", source_type="pdf"),
    )
    mf = _make_manifest(documents=docs)
    assert mf.file_count == 3


def test_manifest_pdf_count_with_mix():
    docs = (
        _make_doc_entry(doc_id="x", source_type="pdf"),
        _make_doc_entry(doc_id="y", source_type="docx"),
        _make_doc_entry(doc_id="z", source_type="pdf"),
    )
    mf = _make_manifest(documents=docs)
    assert mf.pdf_count == 2


def test_manifest_docx_count_with_mix():
    docs = (
        _make_doc_entry(doc_id="x", source_type="pdf"),
        _make_doc_entry(doc_id="y", source_type="docx"),
    )
    mf = _make_manifest(documents=docs)
    assert mf.docx_count == 1


def test_manifest_content_group_count_all_unpaired():
    docs = (
        _make_doc_entry(doc_id="x"),
        _make_doc_entry(doc_id="y"),
    )
    mf = _make_manifest(documents=docs)
    assert mf.content_group_count == 2


def test_manifest_content_group_count_one_pair():
    """单向 paired_with：x.paired_with=y, y.paired_with=None。
    实现：pair_ids = {frozenset({"x","y"})} → groups=1, seen={"x","y"}。
    y 在 seen 中 → 不算 unpaired。total = 1。
    """
    docs = (
        _make_doc_entry(doc_id="x", paired_with="y"),
        _make_doc_entry(doc_id="y"),
    )
    mf = _make_manifest(documents=docs)
    assert mf.content_group_count == 1


def test_manifest_content_group_count_mutual_pair():
    docs = (
        _make_doc_entry(doc_id="x", paired_with="y"),
        _make_doc_entry(doc_id="y", paired_with="x"),
    )
    mf = _make_manifest(documents=docs)
    # 1 pair → groups=1，x 和 y 都在 seen → unpaired=0 → total 1
    assert mf.content_group_count == 1


def test_manifest_categories_covered_sorted():
    docs = (
        _make_doc_entry(doc_id="x", categories=("z", "a")),
        _make_doc_entry(doc_id="y", categories=("m",)),
    )
    mf = _make_manifest(documents=docs)
    assert mf.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_duplicates():
    docs = (
        _make_doc_entry(doc_id="x", categories=("a", "b")),
        _make_doc_entry(doc_id="y", categories=("b", "c")),
    )
    mf = _make_manifest(documents=docs)
    assert mf.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_empty_for_no_categories():
    docs = (
        _make_doc_entry(doc_id="x", categories=()),
        _make_doc_entry(doc_id="y", categories=()),
    )
    mf = _make_manifest(documents=docs)
    assert mf.categories_covered == []


# ---------- load_manifest 边界补充 ----------


def _write_minimal_manifest(tmp_path, **overrides):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    data.update(overrides)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[x]\n", encoding="utf-8")
    return p


def test_load_manifest_with_categories_per_doc(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, documents=[
        {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
         "categories": ["a", "b"]},
    ])
    mf = load_manifest(p)
    assert mf.documents[0].categories == ("a", "b")


def test_load_manifest_with_sha256(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, documents=[
        {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
         "sha256": "a" * 64},
    ])
    mf = load_manifest(p)
    assert mf.documents[0].sha256 == "a" * 64


def test_load_manifest_with_paired_with(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    (sub / "y.docx").write_text("d", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, documents=[
        {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
         "paired_with": "y"},
        {"doc_id": "y", "path": "samples/y.docx", "source_type": "docx",
         "paired_with": "x"},
    ])
    mf = load_manifest(p)
    assert mf.documents[0].paired_with == "y"
    assert mf.documents[1].paired_with == "x"


def test_load_manifest_with_expectations(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, documents=[
        {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
         "expectations": {"element_count_by_type": {"paragraph": 5}}},
    ])
    mf = load_manifest(p)
    assert mf.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_with_annotation_file(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    (sub / "x.anno.json").write_text("{}", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, documents=[
        {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
         "annotation_file": "samples/x.anno.json"},
    ])
    mf = load_manifest(p)
    assert mf.documents[0].annotation_file_str == "samples/x.anno.json"
    assert mf.documents[0].annotation_resolved is not None


def test_load_manifest_with_expected_failure_source_type(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.txt").write_text("d", encoding="utf-8")
    p = _write_minimal_manifest(tmp_path, expected_failures=[
        {"doc_id": "x", "path": "samples/x.txt",
         "expected_error_code": "code", "source_type": "txt"},
    ])
    mf = load_manifest(p)
    assert mf.expected_failures[0].source_type == "txt"


def test_load_manifest_explicit_project_root_str(tmp_path):
    p = _write_minimal_manifest(tmp_path)
    mf = load_manifest(p, project_root=str(tmp_path))
    assert mf.project_root == tmp_path.resolve()


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


# ---------- module source 字符串精确 ----------


def test_module_source_has_docstring_mentions_path():
    src = inspect.getsource(m)
    assert "path" in src


def test_module_source_has_docstring_mentions_relative():
    src = inspect.getsource(m)
    assert "相对" in src


def test_module_source_has_docstring_mentions_absolute():
    src = inspect.getsource(m)
    assert "绝对" in src


def test_module_source_has_docstring_mentions_backslash():
    src = inspect.getsource(m)
    assert "反斜杠" in src


def test_module_source_has_docstring_mentions_project_root():
    src = inspect.getsource(m)
    assert "项目根" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


# ---------- signatures 精确 ----------


def test_load_manifest_no_varargs_varkw():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_is_absolute_like_no_varargs_varkw():
    sig = inspect.signature(_is_absolute_like)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_has_backslash_no_varargs_varkw():
    sig = inspect.signature(_has_backslash)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_resolve_relative_path_no_varargs_varkw():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_detect_project_root_no_varargs_varkw():
    sig = inspect.signature(_detect_project_root)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_namespace_load_manifest():
    assert load_manifest.__module__ == "evaluation.manifest"


def test_namespace_is_absolute_like():
    assert _is_absolute_like.__module__ == "evaluation.manifest"


def test_namespace_has_backslash():
    assert _has_backslash.__module__ == "evaluation.manifest"


def test_namespace_resolve_relative_path():
    assert _resolve_relative_path.__module__ == "evaluation.manifest"


def test_namespace_detect_project_root():
    assert _detect_project_root.__module__ == "evaluation.manifest"


def test_namespace_manifest_error():
    assert ManifestError.__module__ == "evaluation.manifest"


def test_namespace_document_entry():
    assert DocumentEntry.__module__ == "evaluation.manifest"


def test_namespace_expected_failure():
    assert ExpectedFailure.__module__ == "evaluation.manifest"


def test_namespace_manifest():
    assert Manifest.__module__ == "evaluation.manifest"


# ---------- module 整体合理性 ----------


def test_module_all_count_5():
    assert len(m.__all__) == 5


def test_module_namespace():
    assert m.__name__ == "evaluation.manifest"


def test_module_has_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


def test_module_has_4_classes():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and getattr(m, n).__module__ == "evaluation.manifest"
    ]
    assert set(classes) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
    }


def test_module_has_3_dataclasses():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and is_dataclass(getattr(m, n))
    ]
    assert set(classes) == {"Manifest", "DocumentEntry", "ExpectedFailure"}


def test_module_has_1_public_function():
    public = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.manifest"
    ]
    assert public == ["load_manifest"]


def test_module_has_4_private_functions():
    private = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert set(private) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "_detect_project_root",
    }


# ---------- 端到端集成 ----------


def test_e2e_load_manifest_with_full_features(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    (sub / "x.anno.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "x",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["tests", "demo"],
                "annotation_file": "samples/x.anno.json",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            }
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[x]\n", encoding="utf-8")
    mf = load_manifest(p)
    assert mf.file_count == 1
    assert mf.pdf_count == 1
    assert mf.docx_count == 0
    assert mf.categories_covered == ["demo", "tests"]
    assert mf.documents[0].doc_id == "x"
    assert mf.documents[0].annotation_resolved is not None
    assert mf.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_e2e_load_manifest_with_pair(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    (sub / "y.docx").write_text("d", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
             "paired_with": "y"},
            {"doc_id": "y", "path": "samples/y.docx", "source_type": "docx",
             "paired_with": "x"},
        ],
    }), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[x]\n", encoding="utf-8")
    mf = load_manifest(p)
    assert mf.content_group_count == 1
    assert mf.file_count == 2


def test_e2e_load_manifest_default_project_root(tmp_path):
    sub = tmp_path / "samples"
    sub.mkdir()
    (sub / "x.pdf").write_text("d", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[x]\n", encoding="utf-8")
    mf = load_manifest(p)
    # 不传 project_root，自动检测
    assert mf.project_root == tmp_path.resolve()
    assert mf.documents[0].resolved_path.is_absolute()


def test_e2e_load_manifest_invalid_categories_type_rejected(tmp_path):
    """categories 必须是数组，传字符串会被 schema 拒绝。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
             "categories": "not a list"},
        ],
    }), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[x]\n", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_e2e_load_manifest_invalid_sha256_pattern_rejected(tmp_path):
    """sha256 必须是 64 位 hex。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
             "sha256": "short"},
        ],
    }), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[x]\n", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)
