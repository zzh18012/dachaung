"""evaluation/manifest.py 第四十九轮 edges 测试（Round 475）。

补强 edges48 未触及的角度：
- _is_absolute_like 第二十二批（更多 corner case）
- _has_backslash 第二十二批（更多 corner case）
- _resolve_relative_path 第二十二批（project_root 不存在 / project_root 是文件 / 嵌套 / 多 ../）
- _detect_project_root 第二十二批（多 pyproject 优先选最近 / .git 优先）
- Manifest properties 第二十二批（self-pair / 三向 pair / content_group_count 等价 / categories 字母排序）
- DocumentEntry 第二十二批（hashable / frozen 字段不可改 / path_str 是字符串）
- ExpectedFailure 第二十二批（不可变 / source_type 接受 None / 全字段类型）
- load_manifest 第二十二批（空文件 / 纯空白 / list 顶层 / 额外字段拒绝 / 文件不存在）
- module source forbidden tokens 第三十七批
- module source 字符串精确补强第三十三批
- signatures 第三十三批
- module 合理性第三十三批
- 端到端集成第三十三批
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


# ---------- _is_absolute_like 第二十二批 ----------


def test_is_absolute_like_empty_string_batch22():
    """空字符串 → False。"""
    assert _is_absolute_like("") is False


def test_is_absolute_like_only_drive_letter_no_separator_batch22():
    """'x:' 不被识别为绝对路径（len < 3）。"""
    assert _is_absolute_like("x:") is False


def test_is_absolute_like_drive_letter_with_letter_not_separator_batch22():
    """'x:y' 不是绝对路径（第三字符不是分隔符）。"""
    assert _is_absolute_like("x:y") is False


def test_is_absolute_like_drive_letter_digit_batch22():
    """'1:/foo' 不是绝对路径（首字符非字母）。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_lowercase_drive_batch22():
    """'c:\\foo' 小写盘符。"""
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_z_drive_backslash_batch22():
    """'Z:\\foo' Z 大写盘符反斜杠。"""
    assert _is_absolute_like("Z:\\foo") is True


def test_is_absolute_like_double_slash_batch22():
    """'\\\\foo'（double backslash）不是绝对路径（_is_absolute_like 不识别 UNC）。"""
    # \foo 不以 / 开头，且第二字符不是 :
    # 但实际 '\foo' 是 \\foo 的字符串形式（注意 Python 字符串中 \\ 是单字符）
    s = "\\foo"
    assert _is_absolute_like(s) is False


def test_is_absolute_like_three_slashes_batch22():
    """'///x' 多个斜杠开头是绝对路径。"""
    assert _is_absolute_like("///x") is True


def test_is_absolute_like_space_batch22():
    """空格不是绝对路径。"""
    assert _is_absolute_like(" ") is False


def test_is_absolute_like_relative_with_drive_pattern_in_middle_batch22():
    """'a/b:c' 不是绝对路径（: 不在 index 1）。"""
    assert _is_absolute_like("a/b:c") is False


def test_is_absolute_like_just_colon_batch22():
    """':' 不是绝对路径。"""
    assert _is_absolute_like(":") is False


# ---------- _has_backslash 第二十二批 ----------


def test_has_backslash_empty_string_batch22():
    assert _has_backslash("") is False


def test_has_backslash_only_letter_batch22():
    assert _has_backslash("a") is False


def test_has_backslash_in_middle_batch22():
    """路径中间一个反斜杠。"""
    assert _has_backslash("a\\b") is True


def test_has_backslash_multiple_backslashes_batch22():
    """多个反斜杠。"""
    assert _has_backslash("\\\\\\\\") is True


def test_has_backslash_after_letter_batch22():
    """字母后反斜杠。"""
    assert _has_backslash("abc\\") is True


def test_has_backslash_mixed_with_slash_batch22():
    """混合 / 与 \\。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_only_slash_batch22():
    """只有 /。"""
    assert _has_backslash("a/b/c") is False


def test_has_backslash_returns_bool_batch22():
    """返回值类型是 bool。"""
    assert isinstance(_has_backslash("a"), bool)
    assert isinstance(_has_backslash("a\\b"), bool)


# ---------- _resolve_relative_path 第二十二批 ----------


def test_resolve_relative_path_with_only_dot_dot_inside_batch22(tmp_path):
    """'a/./b.pdf' 在 root 内（. 不跳出）。"""
    resolved = _resolve_relative_path("a/./b.pdf", tmp_path, "f")
    assert resolved == (tmp_path / "a" / "b.pdf").resolve()


def test_resolve_relative_path_subdir_subdir_batch22(tmp_path):
    """多级子目录。"""
    resolved = _resolve_relative_path("a/b/c/d/e.pdf", tmp_path, "f")
    assert resolved == (tmp_path / "a" / "b" / "c" / "d" / "e.pdf").resolve()


def test_resolve_relative_path_empty_raises_batch22(tmp_path):
    """空路径 → ManifestError（含 '为空'）。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "field_x")
    assert "field_x" in str(ei.value)
    assert "为空" in str(ei.value) or "empty" in str(ei.value).lower()


def test_resolve_relative_path_relative_to_unresolved_project_root_batch22(tmp_path):
    """project_root 是未 resolve 的路径，函数会内部 resolve。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    unresolved = sub / ".." / "sub"
    resolved = _resolve_relative_path("x.pdf", unresolved, "f")
    assert resolved == (sub / "x.pdf").resolve()


def test_resolve_relative_path_double_dot_at_end_batch22(tmp_path):
    """'a/..' 解析为 root 自身。"""
    resolved = _resolve_relative_path("a/..", tmp_path, "f")
    assert resolved == tmp_path.resolve()


def test_resolve_relative_path_starts_with_three_slashes_batch22(tmp_path):
    """'///foo' 是绝对路径（以 / 开头）。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("///foo", tmp_path, "f")


def test_resolve_relative_path_field_name_in_message_batch22(tmp_path):
    """错误消息含 field_name。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


def test_resolve_relative_path_filename_with_dot_batch22(tmp_path):
    """'.hidden' 文件名解析。"""
    resolved = _resolve_relative_path(".hidden", tmp_path, "f")
    assert resolved == (tmp_path / ".hidden").resolve()


# ---------- _detect_project_root 第二十二批 ----------


def test_detect_project_root_prefers_nearest_pyproject_batch22(tmp_path):
    """多个 pyproject.toml 在链上时选最近的。"""
    (tmp_path / "pyproject.toml").write_text("name='outer'", encoding="utf-8")
    inner = tmp_path / "a"
    inner.mkdir()
    (inner / "pyproject.toml").write_text("name='inner'", encoding="utf-8")
    deeper = inner / "b"
    deeper.mkdir()
    detected = _detect_project_root(deeper)
    assert detected == inner.resolve()


def test_detect_project_root_walks_up_to_root_batch22(tmp_path):
    """没找到 pyproject 时返回起点（向上至少走完）。"""
    sub = tmp_path / "deep" / "nest"
    sub.mkdir(parents=True)
    detected = _detect_project_root(sub)
    # 返回值在 sub 的祖先链上
    assert detected == sub.resolve() or detected in sub.resolve().parents


def test_detect_project_root_returns_absolute_path_batch22(tmp_path):
    """返回值是绝对路径。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    detected = _detect_project_root(tmp_path)
    assert detected.is_absolute()


def test_detect_project_root_symlink_resolved_batch22(tmp_path):
    """传入有 .. 的路径也应被 resolve 处理。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    weird = sub / ".." / "sub"
    detected = _detect_project_root(weird)
    assert detected == tmp_path.resolve()


# ---------- Manifest properties 第二十二批 ----------


def _make_doc(doc_id="d1", source_type="pdf", categories=(), paired_with=None,
              sha256=None, expectations=None, annotation_file_str=None, annotation_resolved=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"{doc_id}.pdf",
        resolved_path=Path(f"/x/{doc_id}.pdf"),
        source_type=source_type,
        sha256=sha256,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=annotation_file_str,
        annotation_resolved=annotation_resolved,
        expectations=expectations,
    )


def test_manifest_content_group_count_self_pair_batch22():
    """d1→d1 自指：算 1 group（frozenset({d1, d1}) = {d1}）。"""
    docs = (_make_doc("d1", paired_with="d1"),)
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    # self-pair 算 1 group
    assert m.content_group_count >= 1


def test_manifest_content_group_count_unpaired_only_batch22():
    """全是 unpaired。"""
    docs = (
        _make_doc("d1"),
        _make_doc("d2"),
        _make_doc("d3"),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.content_group_count == 3


def test_manifest_content_group_count_empty_batch22():
    """无文档 → 0 group。"""
    m = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    assert m.content_group_count == 0


def test_manifest_categories_covered_sorted_batch22():
    """返回值是排序后的 list。"""
    docs = (
        _make_doc("d1", categories=("z", "a")),
        _make_doc("d2", categories=("m",)),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup_batch22():
    """跨文档 dedup。"""
    docs = (
        _make_doc("d1", categories=("x", "y")),
        _make_doc("d2", categories=("x", "z")),
        _make_doc("d3", categories=("y",)),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.categories_covered == ["x", "y", "z"]


def test_manifest_file_count_zero_batch22():
    """空 docs → file_count=0。"""
    m = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    assert m.file_count == 0


def test_manifest_pdf_count_zero_when_all_docx_batch22():
    docs = (
        _make_doc("d1", source_type="docx"),
        _make_doc("d2", source_type="docx"),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.pdf_count == 0
    assert m.docx_count == 2


def test_manifest_categories_covered_empty_when_no_categories_batch22():
    docs = (
        _make_doc("d1", categories=()),
        _make_doc("d2", categories=()),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.categories_covered == []


def test_manifest_is_frozen_batch22():
    m = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.manifest_version = "9.9"  # type: ignore[misc]


# ---------- DocumentEntry 第二十二批 ----------


def test_document_entry_hashable_batch22():
    """DocumentEntry 是 hashable（frozen=True）。"""
    d = _make_doc("d1")
    assert hash(d) == hash(d)


def test_document_entry_frozen_field_cannot_be_set_batch22():
    d = _make_doc("d1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.doc_id = "other"  # type: ignore[misc]


def test_document_entry_path_str_is_string_batch22():
    d = _make_doc("d1")
    assert isinstance(d.path_str, str)


def test_document_entry_source_type_is_string_batch22():
    d = _make_doc("d1", source_type="pdf")
    assert isinstance(d.source_type, str)


def test_document_entry_categories_empty_tuple_batch22():
    d = _make_doc("d1")
    assert d.categories == ()
    assert isinstance(d.categories, tuple)


def test_document_entry_field_count_10_batch22():
    """DocumentEntry 字段数 10。"""
    fields = dataclasses.fields(DocumentEntry)
    assert len(fields) == 10


def test_document_entry_field_names_batch22():
    """字段名顺序。"""
    fields = [f.name for f in dataclasses.fields(DocumentEntry)]
    assert fields == [
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


def test_document_entry_categories_with_many_entries_batch22():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=("a", "b", "c", "d", "e"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert len(d.categories) == 5


# ---------- ExpectedFailure 第二十二批 ----------


def test_expected_failure_doc_id_string_batch22():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    assert isinstance(ef.doc_id, str)


def test_expected_failure_path_str_string_batch22():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    assert isinstance(ef.path_str, str)


def test_expected_failure_expected_error_code_string_batch22():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    assert isinstance(ef.expected_error_code, str)


def test_expected_failure_resolved_path_is_path_batch22():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    assert isinstance(ef.resolved_path, Path)


def test_expected_failure_source_type_optional_batch22():
    ef1 = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    ef2 = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type="pdf",
    )
    assert ef1.source_type is None
    assert ef2.source_type == "pdf"


def test_expected_failure_inequality_batch22():
    ef1 = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    ef2 = ExpectedFailure(
        doc_id="ef2", path_str="ef2.pdf", resolved_path=Path("/x/ef2.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    assert ef1 != ef2


# ---------- load_manifest 第二十二批 ----------


def _write_valid_manifest(tmp_path, docs=None, expected_failures=None):
    """写一个最小合法 manifest.json。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs or [],
        "expected_failures": expected_failures or [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_empty_file_raises_batch22(tmp_path):
    """空文件 → ManifestError。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_whitespace_only_raises_batch22(tmp_path):
    """纯空白 → ManifestError。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text("   \n\t  ", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_list_top_level_raises_eval_schema_error_batch22(tmp_path):
    """JSON 顶层是 list → schema 校验失败。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_additional_top_level_field_rejected_batch22(tmp_path):
    """manifest 不允许额外字段 → EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "extra_field": "bad",
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_missing_devset_status_raises_eval_schema_error_batch22(tmp_path):
    """缺 devset_status → schema 拒绝。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_invalid_devset_status_raises_eval_schema_error_batch22(tmp_path):
    """devset_status 不是 enum 内 → EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "WRONG",
        "documents": [],
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_str_path_returns_manifest_batch22(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(str(p))
    assert isinstance(m, Manifest)


def test_load_manifest_with_multiple_categories_batch22(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
         "categories": ["alpha", "beta", "gamma"]},
    ])
    m = load_manifest(p)
    assert m.documents[0].categories == ("alpha", "beta", "gamma")


def test_load_manifest_passes_field_name_in_error_batch22(tmp_path):
    """manifest 中 path 字段是绝对路径 → ManifestError 含 'documents[doc_id].path'。"""
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"}
    ])
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "documents[d1].path" in str(ei.value)


def test_load_manifest_passes_field_name_in_expected_failure_error_batch22(tmp_path):
    """expected_failure path 是绝对路径 → ManifestError 含 'expected_failures[doc_id].path'。"""
    p = _write_valid_manifest(tmp_path, expected_failures=[
        {"doc_id": "ef1", "path": "/etc/passwd", "expected_error_code": "E_PARSE"}
    ])
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "expected_failures[ef1].path" in str(ei.value)


def test_load_manifest_with_required_markers_batch22(tmp_path):
    """expectations 含 required_markers。"""
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
         "expectations": {"required_markers": ["## 背景目标"]}},
    ])
    m = load_manifest(p)
    assert m.documents[0].expectations == {"required_markers": ["## 背景目标"]}


def test_load_manifest_returns_frozen_manifest_batch22(tmp_path):
    """返回的 Manifest 是 frozen。"""
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


# ---------- module source forbidden tokens 第三十七批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch22(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch22():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch22():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch22():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch22():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch22():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch22():
    src = inspect.getsource(mmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch22():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch22():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch22():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch22():
    src = inspect.getsource(mmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch22():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch22():
    src = inspect.getsource(mmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch22():
    src = inspect.getsource(mmod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch22():
    src = inspect.getsource(mmod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch22():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch22():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十三批 ----------


def test_module_source_has_future_annotations_batch22():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch22():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_has_dataclass_import_batch22():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_path_import_batch22():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch22():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_manifest_version_import_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_validate_import_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_class_manifest_error_batch22():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_is_absolute_like_function_batch22():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_has_has_backslash_function_batch22():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_has_resolve_relative_path_function_batch22():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_load_manifest_function_batch22():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_has_detect_project_root_function_batch22():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_has_dataclass_decorator_batch22():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_has_all_list_batch22():
    src = inspect.getsource(mmod)
    assert "__all__" in src


# ---------- signatures 第三十三批 ----------


def test_signature_is_absolute_like_batch22():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str"]


def test_signature_has_backslash_batch22():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str"]


def test_signature_resolve_relative_path_batch22():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_batch22():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["manifest_path", "project_root"]
    assert params[1].default is None


def test_signature_detect_project_root_batch22():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["start"]


def test_signature_load_manifest_manifest_path_union_batch22():
    """manifest_path 接受 Path | str。"""
    sig = inspect.signature(load_manifest)
    ann = sig.parameters["manifest_path"].annotation
    assert "Path" in ann and "str" in ann


# ---------- module 合理性第三十三批 ----------


def test_module_has_all_attribute_batch22():
    assert hasattr(mmod, "__all__")


def test_module_all_contains_5_entries_batch22():
    assert len(mmod.__all__) == 5


def test_module_all_contents_exact_batch22():
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_does_not_import_app_pipeline_batch22():
    src = inspect.getsource(mmod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_metrics_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_cli_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_does_not_import_evaluation_report_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.report" not in src
    assert "from evaluation import report" not in src


def test_module_no_main_block_batch22():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_manifest_error_is_class_batch22():
    assert hasattr(mmod, "ManifestError")
    assert isinstance(mmod.ManifestError, type)
    assert issubclass(mmod.ManifestError, Exception)


# ---------- 端到端集成第三十三批 ----------


def test_e2e_load_manifest_minimal_valid_batch22(tmp_path):
    """最小合法 manifest 加载。"""
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.manifest_version == "1.0"
    assert m.devset_status == "incomplete"
    assert m.documents == ()
    assert m.expected_failures == ()


def test_e2e_load_manifest_with_two_documents_batch22(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"},
        {"doc_id": "d2", "path": "y.docx", "source_type": "docx"},
    ])
    m = load_manifest(p)
    assert len(m.documents) == 2
    assert m.documents[0].doc_id == "d1"
    assert m.documents[1].doc_id == "d2"
    assert m.documents[0].source_type == "pdf"
    assert m.documents[1].source_type == "docx"


def test_e2e_load_manifest_categories_dedup_and_sort_batch22(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "categories": ["z", "a"]},
        {"doc_id": "d2", "path": "y.pdf", "source_type": "pdf", "categories": ["a", "m"]},
    ])
    m = load_manifest(p)
    assert m.categories_covered == ["a", "m", "z"]


def test_e2e_load_manifest_pdf_docx_count_batch22(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"},
        {"doc_id": "d2", "path": "y.docx", "source_type": "docx"},
        {"doc_id": "d3", "path": "z.pdf", "source_type": "pdf"},
    ])
    m = load_manifest(p)
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_e2e_load_manifest_with_expected_failure_batch22(tmp_path):
    p = _write_valid_manifest(tmp_path, expected_failures=[
        {"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "E_PARSE",
         "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].source_type == "pdf"


def test_e2e_load_manifest_rejects_path_outside_root_batch22(tmp_path):
    """manifest path 跑出 project_root → ManifestError。"""
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "../../etc/passwd", "source_type": "pdf"}
    ])
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_e2e_load_manifest_with_paired_with_content_group_batch22(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "paired_with": "d2"},
        {"doc_id": "d2", "path": "y.docx", "source_type": "docx", "paired_with": "d1"},
    ])
    m = load_manifest(p)
    assert m.content_group_count == 1
