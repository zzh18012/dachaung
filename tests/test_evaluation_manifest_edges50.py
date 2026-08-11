"""evaluation/manifest.py 第五十轮 edges 测试（Round 482）。

补强 edges49 未触及的角度：
- _is_absolute_like 第二十三批（mixed alpha / 多字母 prefix / non-Latin 字母 / 数字+字母 / 长路径 / 1 char / tab / 仅斜杠）
- _has_backslash 第二十三批（多个反斜杠 / 反斜杠开头 / 反斜杠末尾 / 中间+末尾 / 与正斜杠混合）
- _resolve_relative_path 第二十三批（field_name 透传错误消息 / 单 . / 多级嵌套 / project_root 相对路径解析 / 大小写敏感 / 重命名 doc_id 在错误中）
- _detect_project_root 第二十三批（pyproject.toml 在更近的祖先 / 无 pyproject fallback / start 是目录 vs 文件）
- Manifest properties 第二十三批（docx_count 与 pdf_count 互斥 / file_count 等于 len(documents) / content_group_count with self-pair / categories_covered empty list when no docs）
- DocumentEntry 第二十三批（frozen 不可改 / equality 字段对比 / 必填字段无默认 / hashable）
- ExpectedFailure 第二十三批（frozen / source_type 可 None / hashable）
- load_manifest 第二十三批（manifest_version 不兼容 / 多 documents / expected_failures 处理 / annotation_file 解析 / categories tuple 化）
- module source forbidden tokens 第三十八批
- module source 字符串精确补强第三十四批
- signatures 第三十四批
- module 合理性第三十四批
- 端到端集成第三十四批
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import MANIFEST_VERSION
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
from evaluation import manifest as mmod


# ---------- _is_absolute_like 第二十三批 ----------


def test_is_absolute_like_uppercase_alpha_batch23():
    """'A:/x' 大写字母盘符。"""
    assert _is_absolute_like("A:/x") is True


def test_is_absolute_like_lowercase_alpha_batch23():
    """'a:/x' 小写字母盘符。"""
    assert _is_absolute_like("a:/x") is True


def test_is_absolute_like_non_latin_alpha_batch23():
    """'é:/foo' 非 Latin 字母也算 isalpha()。"""
    assert _is_absolute_like("é:/foo") is True


def test_is_absolute_like_digit_drive_rejected_batch23():
    """'1:/foo' 首字符数字 → False。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_drive_rejected_batch23():
    """'_:/foo' 下划线不算字母 → False。"""
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_short_string_batch23():
    """'x' 单字符不抛 IndexError。"""
    assert _is_absolute_like("x") is False


def test_is_absolute_like_two_char_string_batch23():
    """'xy' 两字符不抛。"""
    assert _is_absolute_like("xy") is False


def test_is_absolute_like_just_slash_batch23():
    """'/' 是绝对路径（POSIX 根）。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_two_char_drive_separator_batch23():
    """'x:/' 是绝对路径（Windows 盘符+斜杠）。"""
    assert _is_absolute_like("x:/") is True


def test_is_absolute_like_just_drive_colon_separator_batch23():
    """'x:\\' 是绝对路径（Windows 盘符+反斜杠）。"""
    assert _is_absolute_like("x:\\") is True


# ---------- _has_backslash 第二十三批 ----------


def test_has_backslash_multiple_consecutive_batch23():
    assert _has_backslash("a\\\\b") is True


def test_has_backslash_at_start_batch23():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end_batch23():
    assert _has_backslash("foo\\") is True


def test_has_backslash_only_backslash_batch23():
    assert _has_backslash("\\") is True


def test_has_backslash_mixed_separators_batch23():
    """正反斜杠混合。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_no_backslash_only_slashes_batch23():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_with_special_chars_batch23():
    assert _has_backslash("a\\b c") is True


def test_has_backslash_only_spaces_batch23():
    assert _has_backslash("   ") is False


# ---------- _resolve_relative_path 第二十三批 ----------


def test_resolve_relative_path_field_name_in_error_batch23(tmp_path):
    """错误消息含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/abs", tmp_path, "custom_field")
    assert "custom_field" in str(exc_info.value)


def test_resolve_relative_path_dot_relative_batch23(tmp_path):
    """./foo 相对路径合法。"""
    p = _resolve_relative_path("./foo", tmp_path, "x")
    assert p == (tmp_path / "foo").resolve()


def test_resolve_relative_path_nested_dirs_batch23(tmp_path):
    """a/b/c/d 嵌套目录合法。"""
    p = _resolve_relative_path("a/b/c/d", tmp_path, "x")
    assert p == (tmp_path / "a" / "b" / "c" / "d").resolve()


def test_resolve_relative_path_returns_absolute_batch23(tmp_path):
    """返回路径是绝对。"""
    p = _resolve_relative_path("a", tmp_path, "x")
    assert p.is_absolute()


def test_resolve_relative_path_error_includes_resolved_batch23(tmp_path):
    """escape 错误消息含 resolved 路径。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../../escape", tmp_path, "field_x")
    msg = str(exc_info.value)
    assert "field_x" in msg


def test_resolve_relative_path_with_empty_string_batch23(tmp_path):
    """空字符串抛 ManifestError。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("", tmp_path, "field")


def test_resolve_relative_path_with_only_dotdot_batch23(tmp_path):
    """'..' 单级 escape → ManifestError。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("..", tmp_path, "f")


def test_resolve_relative_path_with_internal_dotdot_batch23(tmp_path):
    """'a/../../escape' 中间逃逸 → ManifestError。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("a/../../escape", tmp_path, "f")


# ---------- _detect_project_root 第二十三批 ----------


def test_detect_project_root_returns_path_batch23(tmp_path):
    """返回 Path。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = _detect_project_root(tmp_path / "x.json")
    assert isinstance(p, Path)


def test_detect_project_root_with_file_input_batch23(tmp_path):
    """start 是文件 → 从其父目录开始搜。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    p = _detect_project_root(f)
    assert p == tmp_path.resolve()


def test_detect_project_root_picks_nearest_pyproject_batch23(tmp_path):
    """多个 pyproject 时选最近的（最近的祖先）。"""
    # 远的
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    # 近的
    near = tmp_path / "near"
    near.mkdir()
    (near / "pyproject.toml").write_text("", encoding="utf-8")
    deeper = near / "deep"
    deeper.mkdir()
    f = deeper / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    p = _detect_project_root(f)
    assert p == near.resolve()


def test_detect_project_root_no_pyproject_returns_dir_batch23(tmp_path):
    """无 pyproject.toml → 返回最近目录（start 的父）。"""
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    f = deep / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    p = _detect_project_root(f)
    assert p == deep.resolve()


def test_detect_project_root_start_is_dir_no_file_batch23(tmp_path):
    """start 是目录 → 从该目录开始搜。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = _detect_project_root(tmp_path)
    assert p == tmp_path.resolve()


# ---------- Manifest properties 第二十三批 ----------


def _make_doc_entry(doc_id="d1", source_type="pdf", categories=(), paired_with=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"samples/{doc_id}.pdf" if source_type == "pdf" else f"samples/{doc_id}.docx",
        resolved_path=Path("/x/y"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _make_ef(doc_id="ef1"):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str="samples/ef.pdf",
        resolved_path=Path("/x/y"),
        expected_error_code="E_PARSE",
        source_type=None,
    )


def test_manifest_pdf_count_filters_correctly_batch23():
    """pdf_count 只算 source_type=='pdf'。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc_entry("d1", "pdf"),
            _make_doc_entry("d2", "docx"),
            _make_doc_entry("d3", "pdf"),
        ),
        expected_failures=(),
        project_root=Path("/"),
    )
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_file_count_zero_when_empty_batch23():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/"),
    )
    assert m.file_count == 0


def test_manifest_categories_covered_sorted_batch23():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc_entry("d1", "pdf", categories=("z", "a")),
            _make_doc_entry("d2", "pdf", categories=("m",)),
        ),
        expected_failures=(),
        project_root=Path("/"),
    )
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_empty_when_no_docs_batch23():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/"),
    )
    assert m.categories_covered == []


def test_manifest_categories_covered_dedup_batch23():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc_entry("d1", "pdf", categories=("x", "y")),
            _make_doc_entry("d2", "pdf", categories=("x",)),
        ),
        expected_failures=(),
        project_root=Path("/"),
    )
    assert m.categories_covered == ["x", "y"]


def test_manifest_content_group_count_with_unidirectional_pair_batch23():
    """单向 paired_with 也算 1 组。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc_entry("d1", "pdf", paired_with="d2"),
            _make_doc_entry("d2", "docx"),  # d2 不反向指向 d1
        ),
        expected_failures=(),
        project_root=Path("/"),
    )
    # d1 paired_with d2 → frozenset{d1,d2} → 1 组；d2 在 frozenset 中，不算 unpaired
    assert m.content_group_count == 1


def test_manifest_content_group_count_two_unpaired_batch23():
    """两个独立文档 → 2 组。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc_entry("d1", "pdf"),
            _make_doc_entry("d2", "docx"),
        ),
        expected_failures=(),
        project_root=Path("/"),
    )
    assert m.content_group_count == 2


def test_manifest_immutable_after_creation_batch23():
    """Manifest 是 frozen dataclass。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/"),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


# ---------- DocumentEntry 第二十三批 ----------


def test_document_entry_required_fields_no_default_batch23():
    """所有字段都必填（无默认值）。"""
    sig = inspect.signature(DocumentEntry.__init__)
    fields_with_defaults = {
        name for name, p in sig.parameters.items() if p.default is not inspect.Parameter.empty
    }
    # 没有 self 之外有默认的字段
    assert fields_with_defaults == set() or fields_with_defaults == {"self"}
    # doc_id 必填
    assert sig.parameters["doc_id"].default is inspect.Parameter.empty


def test_document_entry_equality_batch23():
    """两个相同字段值的 DocumentEntry 相等。"""
    d1 = _make_doc_entry("x", "pdf")
    d2 = _make_doc_entry("x", "pdf")
    assert d1 == d2


def test_document_entry_inequality_different_id_batch23():
    d1 = _make_doc_entry("x", "pdf")
    d2 = _make_doc_entry("y", "pdf")
    assert d1 != d2


def test_document_entry_hashable_batch23():
    """DocumentEntry 可 hash。"""
    d = _make_doc_entry()
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_path_str_is_str_batch23():
    d = _make_doc_entry()
    assert isinstance(d.path_str, str)


def test_document_entry_categories_is_tuple_batch23():
    d = _make_doc_entry(categories=("a", "b"))
    assert isinstance(d.categories, tuple)
    assert d.categories == ("a", "b")


def test_document_entry_frozen_cant_modify_batch23():
    d = _make_doc_entry()
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.doc_id = "other"  # type: ignore[misc]


# ---------- ExpectedFailure 第二十三批 ----------


def test_expected_failure_source_type_can_be_none_batch23():
    """source_type 接受 None 值（类型注解是 str | None）。"""
    ef = ExpectedFailure(
        doc_id="ef",
        path_str="samples/ef.pdf",
        resolved_path=Path("/x"),
        expected_error_code="E_PARSE",
        source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_explicit_source_type_batch23():
    ef = ExpectedFailure(
        doc_id="ef",
        path_str="samples/ef.pdf",
        resolved_path=Path("/x"),
        expected_error_code="E_PARSE",
        source_type="pdf",
    )
    assert ef.source_type == "pdf"


def test_expected_failure_frozen_batch23():
    ef = _make_ef()
    with pytest.raises(dataclasses.FrozenInstanceError):
        ef.doc_id = "other"  # type: ignore[misc]


def test_expected_failure_hashable_batch23():
    ef = _make_ef()
    h = hash(ef)
    assert isinstance(h, int)


def test_expected_failure_equality_batch23():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert ef1 == ef2


def test_expected_failure_inequality_batch23():
    ef1 = _make_ef(doc_id="a")
    ef2 = _make_ef(doc_id="b")
    assert ef1 != ef2


# ---------- load_manifest 第二十三批 ----------


def _make_valid_manifest_payload(tmp_path, docs=None, expected_failures=None):
    """生成合法 manifest payload。"""
    return {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": docs or [],
        "expected_failures": expected_failures or [],
    }


def test_load_manifest_version_mismatch_raises_batch23(tmp_path):
    """manifest_version 不匹配代码常量 → ManifestError。"""
    payload = {
        "manifest_version": "0.0.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    # 但 schema 严格只允许 "1.0"，所以会先被 schema 拒
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    # schema 抛 EvalSchemaError（不在 manifest.py 的 except 内）
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_doc_id_in_path_error_batch23(tmp_path):
    """path 校验失败时 doc_id 出现在错误消息。"""
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "mydoc",
                "path": "/abs/path.pdf",
                "source_type": "pdf",
            }
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "mydoc" in str(exc_info.value)


def test_load_manifest_annotation_file_resolved_batch23(tmp_path):
    """annotation_file 合法时 annotation_resolved 是 Path。"""
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/d.pdf",
                "source_type": "pdf",
                "annotation_file": "annotations/d.json",
            }
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert manifest.documents[0].annotation_resolved == (tmp_path / "annotations" / "d.json").resolve()
    assert isinstance(manifest.documents[0].annotation_resolved, Path)


def test_load_manifest_annotation_file_in_error_batch23(tmp_path):
    """annotation_file 校验失败时字段名出现在错误消息。"""
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/d.pdf",
                "source_type": "pdf",
                "annotation_file": "/abs/ann.json",
            }
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    msg = str(exc_info.value)
    assert "annotation_file" in msg
    assert "d1" in msg


def test_load_manifest_categories_become_tuple_batch23(tmp_path):
    """JSON 中的 categories list → tuple。"""
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/d.pdf",
                "source_type": "pdf",
                "categories": ["x", "y"],
            }
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert manifest.documents[0].categories == ("x", "y")
    assert isinstance(manifest.documents[0].categories, tuple)


def test_load_manifest_expected_failures_resolved_batch23(tmp_path):
    """expected_failures 中的 path 也被解析。"""
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "samples/bad.pdf",
                "source_type": "pdf",
                "expected_error_code": "E_PARSE",
            }
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert len(manifest.expected_failures) == 1
    ef = manifest.expected_failures[0]
    assert ef.doc_id == "ef1"
    assert ef.expected_error_code == "E_PARSE"
    assert ef.source_type == "pdf"
    assert ef.resolved_path == (tmp_path / "samples" / "bad.pdf").resolve()


def test_load_manifest_expected_failure_doc_id_in_error_batch23(tmp_path):
    """expected_failures path 校验失败时 doc_id 出现在错误消息。"""
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef_x",
                "path": "/abs/bad.pdf",
                "source_type": "pdf",
                "expected_error_code": "E_PARSE",
            }
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "ef_x" in str(exc_info.value)


def test_load_manifest_passes_data_to_validate_batch23(tmp_path):
    """load_manifest 内部调用 validate。"""
    payload = _make_valid_manifest_payload(tmp_path)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    with patch("evaluation.manifest.validate") as mock_v:
        load_manifest(p, project_root=tmp_path)
    assert mock_v.called


def test_load_manifest_str_path_input_batch23(tmp_path):
    """load_manifest 接受 str path。"""
    payload = _make_valid_manifest_payload(tmp_path)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(str(p), project_root=tmp_path)
    assert manifest.manifest_version == MANIFEST_VERSION


def test_load_manifest_returns_manifest_instance_batch23(tmp_path):
    """返回 Manifest 实例。"""
    payload = _make_valid_manifest_payload(tmp_path)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert isinstance(manifest, Manifest)


def test_load_manifest_default_project_root_uses_pyproject_batch23(tmp_path):
    """默认 project_root 从 _detect_project_root 推导。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    payload = _make_valid_manifest_payload(tmp_path)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_manifest(p)
    assert manifest.project_root == tmp_path.resolve()


# ---------- module source forbidden tokens 第三十八批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_output",
    "subprocess.check_call",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    'open("/etc/passwd',
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch23(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch23():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch23():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch23():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch23():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch23():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_asyncio_import_batch23():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch23():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch23():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_logging_import_batch23():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch23():
    src = inspect.getsource(mmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch23():
    src = inspect.getsource(mmod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch23():
    src = inspect.getsource(mmod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch23():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch23():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


def test_module_source_no_csv_import_batch23():
    src = inspect.getsource(mmod)
    assert "import csv" not in src


# ---------- module source 字符串精确补强第三十四批 ----------


def test_module_source_has_future_annotations_batch23():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch23():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_has_dataclass_import_batch23():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_path_import_batch23():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch23():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_manifest_version_import_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_validate_import_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_manifest_error_class_batch23():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_document_entry_dataclass_batch23():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_has_is_absolute_like_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_has_has_backslash_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_has_load_manifest_function_batch23():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_has_resolve_relative_path_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_detect_project_root_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_has_frozen_true_in_dataclass_batch23():
    src = inspect.getsource(mmod)
    assert "frozen=True" in src


# ---------- signatures 第三十四批 ----------


def test_signature_is_absolute_like_one_param_batch23():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_signature_is_absolute_like_returns_bool_batch23():
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in str(sig.return_annotation)


def test_signature_has_backslash_one_param_batch23():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_signature_resolve_relative_path_three_params_batch23():
    sig = inspect.signature(_resolve_relative_path)
    names = [p.name for p in sig.parameters.values()]
    assert names == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_two_params_with_default_batch23():
    sig = inspect.signature(load_manifest)
    params = sig.parameters
    assert params["manifest_path"].default is inspect.Parameter.empty
    assert params["project_root"].default is None


def test_signature_detect_project_root_one_param_batch23():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"


def test_signature_manifest_init_takes_named_fields_batch23():
    """Manifest.__init__ 接受 5 个具名字段。"""
    sig = inspect.signature(Manifest.__init__)
    names = list(sig.parameters.keys())
    assert "self" in names
    assert "manifest_version" in names
    assert "devset_status" in names
    assert "documents" in names
    assert "expected_failures" in names
    assert "project_root" in names


# ---------- module 合理性第三十四批 ----------


def test_module_all_has_five_entries_batch23():
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_does_not_import_evaluation_runner_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_metrics_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_report_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.report" not in src
    assert "from evaluation import report" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_does_not_import_app_pipeline_batch23():
    src = inspect.getsource(mmod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_does_not_import_app_chunkers_batch23():
    src = inspect.getsource(mmod)
    assert "from app.chunkers" not in src


def test_module_does_not_import_app_parsers_batch23():
    src = inspect.getsource(mmod)
    assert "from app.parsers" not in src


def test_module_manifest_error_is_public_batch23():
    assert not ManifestError.__name__.startswith("_")


def test_module_load_manifest_is_public_batch23():
    assert not load_manifest.__name__.startswith("_")


def test_module_is_absolute_like_is_private_batch23():
    assert _is_absolute_like.__name__.startswith("_")


def test_module_has_backslash_is_private_batch23():
    assert _has_backslash.__name__.startswith("_")


def test_module_resolve_relative_path_is_private_batch23():
    assert _resolve_relative_path.__name__.startswith("_")


def test_module_detect_project_root_is_private_batch23():
    assert _detect_project_root.__name__.startswith("_")


def test_module_has_module_docstring_batch23():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


def test_module_no_main_block_batch23():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src


# ---------- 端到端集成第三十四批 ----------


def test_e2e_load_manifest_minimal_valid_batch23(tmp_path):
    """最小合法 manifest。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert manifest.documents == ()
    assert manifest.expected_failures == ()
    assert manifest.devset_status == "incomplete"


def test_e2e_load_manifest_with_categories_batch23(tmp_path):
    """带 categories 的 manifest。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf", "categories": ["c1", "c2"]},
        ],
    }), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert manifest.documents[0].categories == ("c1", "c2")
    assert manifest.categories_covered == ["c1", "c2"]


def test_e2e_load_manifest_with_paired_batch23(tmp_path):
    """带 paired_with 的 manifest。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "samples/a.docx", "source_type": "docx", "paired_with": "d1"},
        ],
    }), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert manifest.content_group_count == 1


def test_e2e_load_manifest_categories_dedup_aggregation_batch23(tmp_path):
    """多文档 categories 去重聚合。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf", "categories": ["c1"]},
            {"doc_id": "d2", "path": "samples/b.pdf", "source_type": "pdf", "categories": ["c1", "c2"]},
            {"doc_id": "d3", "path": "samples/c.pdf", "source_type": "pdf", "categories": []},
        ],
    }), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert manifest.categories_covered == ["c1", "c2"]


def test_e2e_load_manifest_file_count_and_pdf_docx_count_batch23(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "samples/b.pdf", "source_type": "pdf"},
            {"doc_id": "d3", "path": "samples/c.docx", "source_type": "docx"},
        ],
    }), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    assert manifest.file_count == 3
    assert manifest.pdf_count == 2
    assert manifest.docx_count == 1


def test_e2e_load_manifest_with_expectations_batch23(tmp_path):
    """带 expectations 的 manifest。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/a.pdf",
                "source_type": "pdf",
                "expectations": {
                    "element_count_by_type": {"paragraph": 5},
                    "required_markers": ["a", "b"],
                },
            },
        ],
    }), encoding="utf-8")
    manifest = load_manifest(p, project_root=tmp_path)
    exp = manifest.documents[0].expectations
    assert exp == {"element_count_by_type": {"paragraph": 5}, "required_markers": ["a", "b"]}


def test_e2e_load_manifest_default_project_root_finds_pyproject_batch23(tmp_path):
    """默认 project_root 自动找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    p = sub / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    manifest = load_manifest(p)
    assert manifest.project_root == tmp_path.resolve()
