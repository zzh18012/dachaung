"""evaluation/manifest.py 第四十八轮 edges 测试（Round 468）。

补强 edges47 未触及的角度：
- _is_absolute_like 第二十一批（更多 corner case）
- _has_backslash 第二十一批（更多 corner case）
- _resolve_relative_path 第二十一批（更多 corner case）
- _detect_project_root 第二十一批
- Manifest properties 第二十一批（content_group_count cyclic / pdf+docx mixed / categories empty / file_count docs+failures）
- DocumentEntry 第二十一批（categories tuple / annotation_resolved / sha256 None vs str）
- ExpectedFailure 第二十一批（field validation / source_type None / frozen）
- load_manifest 第二十一批（more round-trip edge cases）
- module source forbidden tokens 第三十六批
- module source 字符串精确补强第三十二批
- signatures 第三十二批
- module 合理性第三十二批
- 端到端集成第三十二批
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


# ---------- _is_absolute_like 第二十一批 ----------


def test_is_absolute_like_uppercase_drive_letter_batch21():
    """'C:/foo' 大写盘符也是绝对路径。"""
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_uppercase_drive_letter_backslash_batch21():
    """'C:\\foo' 大写盘符反斜杠也是绝对路径。"""
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_single_char_absolute_batch21():
    """单字符 '/' 是绝对路径。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_drive_letter_only_3_chars_batch21():
    """正好 3 字符 'x:/' 是绝对路径。"""
    assert _is_absolute_like("x:/") is True


def test_is_absolute_like_drive_letter_z_batch21():
    assert _is_absolute_like("z:/x") is True


def test_is_absolute_like_path_with_only_drive_no_separator_batch21():
    """'ab' 不是绝对路径（无冒号）。"""
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_relative_two_chars_batch21():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_relative_simple_batch21():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_dot_slash_batch21():
    """'./foo' 不是绝对路径。"""
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_batch21():
    """'../foo' 不是绝对路径。"""
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_tilde_path_batch21():
    """'~/foo' 在 POSIX 不是绝对路径（取决于 shell 展开）。"""
    # _is_absolute_like 不识别 ~，认为不是绝对路径
    assert _is_absolute_like("~/foo") is False


# ---------- _has_backslash 第二十一批 ----------


def test_has_backslash_drive_path_batch21():
    assert _has_backslash("C:\\Users\\file") is True


def test_has_backslash_unc_path_batch21():
    """UNC 路径 \\\\server\\share。"""
    assert _has_backslash("\\\\server\\share") is True


def test_has_backslash_trailing_backslash_batch21():
    assert _has_backslash("foo\\") is True


def test_has_backslash_only_slashes_batch21():
    assert _has_backslash("////") is False


def test_has_backslash_no_separator_at_all_batch21():
    assert _has_backslash("foo") is False


def test_has_backslash_just_one_backslash_batch21():
    assert _has_backslash("\\") is True


# ---------- _resolve_relative_path 第二十一批 ----------


def test_resolve_relative_path_self_dir_batch21(tmp_path):
    """'.' 解析为 project_root 自身。"""
    resolved = _resolve_relative_path(".", tmp_path, "f")
    assert resolved == tmp_path.resolve()


def test_resolve_relative_path_subdir_batch21(tmp_path):
    """正常子目录。"""
    resolved = _resolve_relative_path("a/b/c.pdf", tmp_path, "f")
    assert resolved == (tmp_path / "a" / "b" / "c.pdf").resolve()


def test_resolve_relative_path_starts_with_dot_slash_batch21(tmp_path):
    """'./x.pdf' 解析成功。"""
    resolved = _resolve_relative_path("./x.pdf", tmp_path, "f")
    assert resolved == (tmp_path / "x.pdf").resolve()


def test_resolve_relative_path_multiple_dot_dot_batch21(tmp_path):
    """'../../../outside' 跑出根。"""
    inner = tmp_path / "deep" / "nested"
    inner.mkdir(parents=True)
    with pytest.raises(ManifestError):
        _resolve_relative_path("../../../outside", inner, "f")


def test_resolve_relative_path_complex_with_dot_dot_inside_batch21(tmp_path):
    """'a/../b.pdf' 在 root 内，应成功。"""
    resolved = _resolve_relative_path("a/../b.pdf", tmp_path, "f")
    assert resolved == (tmp_path / "b.pdf").resolve()


def test_resolve_relative_path_backslash_rejected_batch21(tmp_path):
    """反斜杠被拒。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b.pdf", tmp_path, "f")
    assert "正斜杠" in str(ei.value) or "反斜杠" in str(ei.value)


def test_resolve_relative_path_windows_drive_rejected_batch21(tmp_path):
    """'C:/foo' 被拒（绝对路径）。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("C:/foo/bar.pdf", tmp_path, "f")
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_returns_path_object_batch21(tmp_path):
    resolved = _resolve_relative_path("x.pdf", tmp_path, "f")
    assert isinstance(resolved, Path)


def test_resolve_relative_path_inside_root_with_subdir_batch21(tmp_path):
    """子目录里的文件。"""
    (tmp_path / "samples").mkdir()
    resolved = _resolve_relative_path("samples/x.pdf", tmp_path, "f")
    assert resolved.parent == (tmp_path / "samples").resolve()


def test_resolve_relative_path_error_message_has_path_str_batch21(tmp_path):
    """错误消息含原始 path_str。"""
    try:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    except ManifestError as e:
        assert "/etc/passwd" in str(e)


# ---------- _detect_project_root 第二十一批 ----------


def test_detect_project_root_finds_nearest_in_chain_batch21(tmp_path):
    """多级目录里有 pyproject，找到最近的。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    inner = tmp_path / "a" / "b" / "c"
    inner.mkdir(parents=True)
    detected = _detect_project_root(inner)
    assert detected == tmp_path.resolve()


def test_detect_project_root_returns_path_object_batch21(tmp_path):
    """返回 Path 对象。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    detected = _detect_project_root(tmp_path)
    assert isinstance(detected, Path)


def test_detect_project_root_handles_file_input_batch21(tmp_path):
    """传文件路径时取其 parent。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text("{}", encoding="utf-8")
    detected = _detect_project_root(p)
    assert detected == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_or_ancestor_batch21(tmp_path):
    """没找到时返回 cur 或其祖先。"""
    sub = tmp_path / "deep"
    sub.mkdir()
    detected = _detect_project_root(sub)
    # 是 sub 本身或祖先链上某个
    assert detected == sub.resolve() or detected in sub.resolve().parents


def test_detect_project_root_resolves_path_batch21(tmp_path):
    """返回路径是 resolve 后的（绝对）。"""
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    detected = _detect_project_root(tmp_path)
    assert detected == tmp_path.resolve()


# ---------- Manifest properties 第二十一批 ----------


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


def test_manifest_content_group_count_cyclic_pair_batch21():
    """d1→d2, d2→d1 → frozenset({d1,d2}) 去重为 1 group。"""
    docs = (
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.content_group_count == 1


def test_manifest_content_group_count_three_pair_batch21():
    """3 个不同 pair。"""
    docs = (
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
        _make_doc("d3", paired_with="d4"),
        _make_doc("d4", paired_with="d3"),
        _make_doc("d5", paired_with="d6"),
        _make_doc("d6", paired_with="d5"),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.content_group_count == 3


def test_manifest_content_group_count_mixed_batch21():
    """1 pair + 1 unpaired = 2 group。"""
    docs = (
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
        _make_doc("d3"),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.content_group_count == 2


def test_manifest_pdf_and_docx_count_batch21():
    """混合 pdf+docx。"""
    docs = (
        _make_doc("d1", source_type="pdf"),
        _make_doc("d2", source_type="pdf"),
        _make_doc("d3", source_type="docx"),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_categories_covered_empty_batch21():
    """无文档时 categories_covered 是空 list。"""
    m = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    assert m.categories_covered == []


def test_manifest_categories_covered_returns_list_batch21():
    """返回 list（不是 tuple）。"""
    docs = (_make_doc("d1", categories=("x",)),)
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert isinstance(m.categories_covered, list)


def test_manifest_file_count_only_counts_documents_batch21():
    """file_count 不含 expected_failures。"""
    docs = (_make_doc("d1"),)
    ef = (
        ExpectedFailure(
            doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
            expected_error_code="E_PARSE", source_type="pdf",
        ),
    )
    m = Manifest("1.0", "incomplete", docs, ef, Path("/tmp"))
    assert m.file_count == 1


def test_manifest_pdf_count_with_other_source_types_batch21():
    docs = (
        _make_doc("d1", source_type="pdf"),
        _make_doc("d2", source_type="txt"),
        _make_doc("d3", source_type="other"),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.pdf_count == 1
    assert m.docx_count == 0


# ---------- DocumentEntry 第二十一批 ----------


def test_document_entry_categories_tuple_type_batch21():
    """categories 必须是 tuple（不能是 list）。"""
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=("a", "b"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert isinstance(d.categories, tuple)


def test_document_entry_with_sha256_string_batch21():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256="abc123", categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert d.sha256 == "abc123"


def test_document_entry_with_annotation_resolved_batch21():
    """annotation_resolved 是 Path。"""
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str="ann.json",
        annotation_resolved=Path("/x/ann.json"),
        expectations=None,
    )
    assert d.annotation_resolved == Path("/x/ann.json")
    assert d.annotation_file_str == "ann.json"


def test_document_entry_default_categories_not_optional_batch21():
    """所有字段无 default（必须显式传）。"""
    for f in dataclasses.fields(DocumentEntry):
        assert f.default is dataclasses.MISSING


def test_document_entry_equality_same_annotation_batch21():
    d1 = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str="a.json",
        annotation_resolved=Path("/x/a.json"), expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str="a.json",
        annotation_resolved=Path("/x/a.json"), expectations=None,
    )
    assert d1 == d2


def test_document_entry_repr_contains_class_name_batch21():
    d = _make_doc("xyz")
    r = repr(d)
    assert "DocumentEntry" in r
    assert "xyz" in r


def test_document_entry_with_dict_expectations_batch21():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations={"element_count_by_type": {"paragraph": 5}},
    )
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


# ---------- ExpectedFailure 第二十一批 ----------


def test_expected_failure_field_count_5_batch21():
    fields = dataclasses.fields(ExpectedFailure)
    assert len(fields) == 5


def test_expected_failure_field_names_batch21():
    fields = [f.name for f in dataclasses.fields(ExpectedFailure)]
    assert fields == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_is_frozen_batch21():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        ef.doc_id = "other"  # type: ignore[misc]


def test_expected_failure_no_default_values_batch21():
    for f in dataclasses.fields(ExpectedFailure):
        assert f.default is dataclasses.MISSING


def test_expected_failure_with_source_type_none_batch21():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_equality_batch21():
    ef1 = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type="pdf",
    )
    ef2 = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type="pdf",
    )
    assert ef1 == ef2


def test_expected_failure_hashable_batch21():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="ef1.pdf", resolved_path=Path("/x/ef1.pdf"),
        expected_error_code="E_PARSE", source_type="pdf",
    )
    assert hash(ef) == hash(ef)


def test_expected_failure_repr_batch21():
    ef = ExpectedFailure(
        doc_id="xyz", path_str="xyz.pdf", resolved_path=Path("/x/xyz.pdf"),
        expected_error_code="E_PARSE", source_type=None,
    )
    r = repr(ef)
    assert "ExpectedFailure" in r
    assert "xyz" in r


# ---------- load_manifest 第二十一批 ----------


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


def test_load_manifest_empty_documents_batch21(tmp_path):
    """空 documents 列表合法。"""
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.documents == ()


def test_load_manifest_empty_expected_failures_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.expected_failures == ()


def test_load_manifest_with_one_document_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"


def test_load_manifest_str_path_batch21(tmp_path):
    """接受 str 路径。"""
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(str(p))
    assert m.manifest_version == "1.0"


def test_load_manifest_file_not_exist_raises_batch21(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "missing.json")


def test_load_manifest_invalid_json_raises_batch21(tmp_path):
    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_version_mismatch_raises_batch21(tmp_path):
    """manifest_version 不是 1.0 → Schema 先拒绝（EvalSchemaError），不走 mismatch 分支。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "9.9",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # schema enum 锁 '1.0'，先抛 EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_with_categories_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
         "categories": ["a", "b"]}
    ])
    m = load_manifest(p)
    assert m.documents[0].categories == ("a", "b")


def test_load_manifest_with_paired_with_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "paired_with": "d2"},
        {"doc_id": "d2", "path": "y.docx", "source_type": "docx", "paired_with": "d1"},
    ])
    m = load_manifest(p)
    assert m.documents[0].paired_with == "d2"


def test_load_manifest_with_sha256_batch21(tmp_path):
    sha = "a" * 64  # 64-hex
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "sha256": sha}
    ])
    m = load_manifest(p)
    assert m.documents[0].sha256 == sha


def test_load_manifest_with_expected_failure_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, expected_failures=[
        {"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "E_PARSE",
         "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"


def test_load_manifest_devset_status_passed_through_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path)
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    m = load_manifest(p)
    assert m.devset_status == "complete"


def test_load_manifest_project_root_passed_explicitly_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


# ---------- module source forbidden tokens 第三十六批 ----------


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
def test_module_source_forbidden_tokens_batch21(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch21():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch21():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch21():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch21():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch21():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch21():
    src = inspect.getsource(mmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch21():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch21():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch21():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch21():
    src = inspect.getsource(mmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch21():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch21():
    src = inspect.getsource(mmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch21():
    src = inspect.getsource(mmod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch21():
    src = inspect.getsource(mmod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch21():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch21():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十二批 ----------


def test_module_source_has_future_annotations_batch21():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch21():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_has_dataclass_import_batch21():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_path_import_batch21():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch21():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_manifest_version_import_batch21():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_validate_import_batch21():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_class_manifest_error_batch21():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_is_absolute_like_function_batch21():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_has_has_backslash_function_batch21():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_has_resolve_relative_path_function_batch21():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_load_manifest_function_batch21():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_has_detect_project_root_function_batch21():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_has_dataclass_decorator_batch21():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_has_all_list_batch21():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_source_has_docstring_about_manifest_batch21():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


# ---------- signatures 第三十二批 ----------


def test_signature_is_absolute_like_batch21():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str"]


def test_signature_has_backslash_batch21():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str"]


def test_signature_resolve_relative_path_batch21():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_batch21():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["manifest_path", "project_root"]
    assert params[1].default is None


def test_signature_detect_project_root_batch21():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["start"]


def test_signature_load_manifest_accepts_str_or_path_batch21():
    sig = inspect.signature(load_manifest)
    ra = sig.return_annotation
    assert "Manifest" in str(ra)


# ---------- module 合理性第三十二批 ----------


def test_module_has_all_attribute_batch21():
    assert hasattr(mmod, "__all__")


def test_module_all_contains_5_entries_batch21():
    assert len(mmod.__all__) == 5


def test_module_all_contents_batch21():
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_does_not_import_app_pipeline_batch21():
    src = inspect.getsource(mmod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch21():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_metrics_batch21():
    src = inspect.getsource(mmod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_cli_batch21():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_no_main_block_batch21():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_manifest_error_is_class_batch21():
    assert hasattr(mmod, "ManifestError")
    assert isinstance(mmod.ManifestError, type)
    assert issubclass(mmod.ManifestError, Exception)


def test_module_document_entry_is_class_batch21():
    assert hasattr(mmod, "DocumentEntry")
    assert isinstance(mmod.DocumentEntry, type)


def test_module_expected_failure_is_class_batch21():
    assert hasattr(mmod, "ExpectedFailure")
    assert isinstance(mmod.ExpectedFailure, type)


def test_module_manifest_is_class_batch21():
    assert hasattr(mmod, "Manifest")
    assert isinstance(mmod.Manifest, type)


# ---------- 端到端集成第三十二批 ----------


def test_e2e_load_manifest_round_trip_batch21(tmp_path):
    """加载后字段一一对应。"""
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "a/b.pdf", "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert m.manifest_version == "1.0"
    assert m.devset_status == "incomplete"
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].source_type == "pdf"
    assert m.documents[0].path_str == "a/b.pdf"
    assert m.documents[0].resolved_path == (tmp_path / "a" / "b.pdf").resolve()


def test_e2e_load_manifest_with_annotation_file_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
         "annotation_file": "ann.json"}
    ])
    m = load_manifest(p)
    assert m.documents[0].annotation_file_str == "ann.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "ann.json").resolve()


def test_e2e_load_manifest_categories_dedup_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "categories": ["a", "b"]},
        {"doc_id": "d2", "path": "y.pdf", "source_type": "pdf", "categories": ["b", "c"]},
    ])
    m = load_manifest(p)
    assert m.categories_covered == ["a", "b", "c"]


def test_e2e_load_manifest_pdf_docx_count_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"},
        {"doc_id": "d2", "path": "y.docx", "source_type": "docx"},
    ])
    m = load_manifest(p)
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_e2e_load_manifest_with_expectations_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
         "expectations": {"element_count_by_type": {"paragraph": 5}}},
    ])
    m = load_manifest(p)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_e2e_load_manifest_file_count_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": f"d{i}", "path": f"x{i}.pdf", "source_type": "pdf"}
        for i in range(5)
    ])
    m = load_manifest(p)
    assert m.file_count == 5


def test_e2e_load_manifest_explicit_project_root_batch21(tmp_path):
    p = _write_valid_manifest(tmp_path)
    custom_root = tmp_path / "custom"
    custom_root.mkdir()
    (custom_root / "pyproject.toml").write_text("name='x'", encoding="utf-8")
    m = load_manifest(p, project_root=custom_root)
    assert m.project_root == custom_root.resolve()


def test_e2e_load_manifest_rejects_path_outside_root_batch21(tmp_path):
    """manifest 中 path 跑出 project_root → ManifestError。"""
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "../../etc/passwd", "source_type": "pdf"}
    ])
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)
