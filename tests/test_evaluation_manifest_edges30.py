"""evaluation/manifest.py 第三十轮 edges 测试（Round 342）。

重点补强 edges29 未触及的角度：
- _is_absolute_like 数学边界第五批（更多类型组合）
- _has_backslash 数学边界第五批
- _resolve_relative_path 行为深度（边界 case）
- _detect_project_root 行为深度（边界 case）
- DocumentEntry / ExpectedFailure dataclass 行为深度第三批
- Manifest properties 算法深度第三批（content_group_count 边界 / categories_covered 边界）
- load_manifest malformed data 第三批
- module source forbidden tokens 第五批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import types
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from typing import Any

import pytest

from evaluation import manifest as mmod
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


# ---------- _is_absolute_like 数学边界第五批 ----------


def test_is_absolute_like_single_slash_only():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_double_slash_only():
    """POSIX 上 '//' 不是常规绝对路径，但 startswith('/') 命中。"""
    assert _is_absolute_like("//") is True


def test_is_absolute_like_triple_slash_only():
    assert _is_absolute_like("///") is True


def test_is_absolute_like_just_drive_letter_no_separator():
    """'C:' 长度 2，不满足 len >= 3。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_drive_with_letter_only_no_separator():
    r"""'C:D' 不算绝对路径（D 不是斜杠）。"""
    assert _is_absolute_like("C:D") is False


def test_is_absolute_like_drive_with_dot():
    assert _is_absolute_like("C:.") is False


def test_is_absolute_like_drive_with_dash():
    assert _is_absolute_like("C:-") is False


def test_is_absolute_like_drive_with_space():
    assert _is_absolute_like("C: ") is False


def test_is_absolute_like_drive_with_letter_after():
    """'C:X' 不算绝对路径（X 不是 / 或 \）。"""
    assert _is_absolute_like("C:X") is False


def test_is_absolute_like_drive_with_lowercase_letter():
    assert _is_absolute_like("a:\\foo") is True


def test_is_absolute_like_drive_with_uppercase_letter():
    assert _is_absolute_like("Z:/foo") is True


def test_is_absolute_like_drive_with_digit_invalid():
    """数字不是字母。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_drive_with_underscore_invalid():
    assert _is_absolute_like("_:\\foo") is False


def test_is_absolute_like_drive_with_unicode_letter():
    """Unicode 字母也算 alpha。"""
    # α.isalpha() → True
    result = _is_absolute_like("α:\\foo")
    assert result is True


def test_is_absolute_like_relative_path_with_colon():
    """'a:b' 不算绝对路径。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_tilde_path():
    """'~' 不被识别为绝对路径。"""
    assert _is_absolute_like("~") is False
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_dot_path():
    assert _is_absolute_like(".") is False
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_path():
    assert _is_absolute_like("..") is False
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_returns_bool():
    assert isinstance(_is_absolute_like("x"), bool)


# ---------- _has_backslash 数学边界第五批 ----------


def test_has_backslash_with_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_with_double_backslash():
    assert _has_backslash("\\\\") is True


def test_has_backslash_with_mixed_separators():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_at_start():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end():
    assert _has_backslash("foo\\") is True


def test_has_backslash_only_forward_slash():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_with_unicode():
    assert _has_backslash("你好\\world") is True


def test_has_backslash_with_special_chars():
    assert _has_backslash("@#$%^&*\\") is True


def test_has_backslash_returns_bool():
    assert isinstance(_has_backslash("x"), bool)


def test_has_backslash_with_long_string_no_backslash():
    assert _has_backslash("a" * 1000) is False


def test_has_backslash_with_long_string_with_backslash_at_end():
    assert _has_backslash("a" * 999 + "\\") is True


# ---------- _resolve_relative_path 行为深度 ----------


def test_resolve_relative_path_valid(tmp_path):
    out = _resolve_relative_path("foo/bar.txt", tmp_path, "test")
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_absolute_posix_raises(tmp_path):
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_absolute_windows_raises(tmp_path):
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        _resolve_relative_path("C:\\foo", tmp_path, "test")


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError, match="禁止反斜杠"):
        _resolve_relative_path("foo\\bar", tmp_path, "test")


def test_resolve_relative_path_escape_with_dotdot_raises(tmp_path):
    """../etc/passwd 解析后位于 project_root 外。"""
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../../etc/passwd", tmp_path, "test")


def test_resolve_relative_path_dotdot_within_root_ok(tmp_path):
    """foo/../bar 在 root 内（resolve 后仍在 tmp_path 内）。"""
    out = _resolve_relative_path("foo/../bar", tmp_path, "test")
    assert out == (tmp_path / "bar").resolve()


def test_resolve_relative_path_returns_resolved_path(tmp_path):
    """返回的路径是 resolved（无 .. 残留）。"""
    out = _resolve_relative_path("foo/./bar", tmp_path, "test")
    assert ".." not in out.parts


def test_resolve_relative_path_field_name_in_error_message(tmp_path):
    """错误消息含 field_name。"""
    with pytest.raises(ManifestError, match="my_field"):
        _resolve_relative_path("", tmp_path, "my_field")


# ---------- _detect_project_root 行为深度 ----------


def test_detect_project_root_finds_pyproject(tmp_path):
    """有 pyproject.toml 的目录被识别为 root。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


def test_detect_project_root_finds_parent_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


def test_detect_project_root_fallback_to_input(tmp_path):
    """无 pyproject.toml → 返回 input 自身。"""
    p = tmp_path / "no_root"
    p.mkdir()
    out = _detect_project_root(p)
    assert out == p.resolve()


def test_detect_project_root_with_file_input(tmp_path):
    """input 是文件 → 用其 parent。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    out = _detect_project_root(p)
    assert out == tmp_path.resolve()


def test_detect_project_root_already_directory(tmp_path):
    """input 是目录 → 直接用。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_path():
    out = _detect_project_root(Path.cwd())
    assert isinstance(out, Path)


def test_detect_project_root_returns_absolute():
    out = _detect_project_root(Path.cwd())
    assert out.is_absolute()


# ---------- DocumentEntry / ExpectedFailure dataclass 行为深度第三批 ----------


def _make_doc_entry(**overrides):
    defaults = dict(
        doc_id="d1",
        path_str="foo/bar.pdf",
        resolved_path=Path("/tmp/foo/bar.pdf"),
        source_type="pdf",
        sha256="abc" * 21 + "a",  # 64 chars
        categories=("cat1", "cat2"),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_field_count():
    src = inspect.getsource(DocumentEntry)
    field_count = sum(
        1 for line in src.splitlines() if line.startswith("    ") and ":" in line and "=" not in line
    )
    # DocumentEntry 有 10 个字段
    assert len(DocumentEntry.__dataclass_fields__) == 10


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen():
    entry = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        entry.doc_id = "x"  # type: ignore[misc]


def test_document_entry_field_names_exact():
    fields = set(DocumentEntry.__dataclass_fields__.keys())
    assert fields == {
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
    }


def test_document_entry_field_types():
    fields = DocumentEntry.__dataclass_fields__
    assert fields["doc_id"].type is str or fields["doc_id"].type == "str"
    assert fields["path_str"].type is str or fields["path_str"].type == "str"
    assert "Path" in str(fields["resolved_path"].type)
    assert fields["source_type"].type is str or fields["source_type"].type == "str"


def test_document_entry_equality():
    a = _make_doc_entry()
    b = _make_doc_entry()
    assert a == b


def test_document_entry_inequality_by_field():
    a = _make_doc_entry()
    b = _make_doc_entry(doc_id="other")
    assert a != b


def test_document_entry_hashable():
    a = _make_doc_entry()
    s = {a}
    s.add(a)
    assert len(s) == 1


def test_document_entry_str_representation():
    a = _make_doc_entry()
    s = repr(a)
    assert "DocumentEntry" in s


def _make_ef(**overrides):
    defaults = dict(
        doc_id="ef1",
        path_str="bad.pdf",
        resolved_path=Path("/tmp/bad.pdf"),
        expected_error_code="parse_failed",
        source_type="pdf",
    )
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_field_count():
    assert len(ExpectedFailure.__dataclass_fields__) == 5


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_field_names_exact():
    fields = set(ExpectedFailure.__dataclass_fields__.keys())
    assert fields == {
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    }


def test_expected_failure_equality():
    a = _make_ef()
    b = _make_ef()
    assert a == b


def test_expected_failure_inequality():
    a = _make_ef()
    b = _make_ef(doc_id="other")
    assert a != b


def test_expected_failure_hashable():
    ef = _make_ef()
    s = {ef}


def test_expected_failure_str_representation():
    ef = _make_ef()
    s = repr(ef)
    assert "ExpectedFailure" in s


# ---------- Manifest properties 算法深度第三批 ----------


def _make_manifest(docs=None, efs=None, status="incomplete"):
    return Manifest(
        manifest_version="1.0",
        devset_status=status,
        documents=tuple(docs or []),
        expected_failures=tuple(efs or []),
        project_root=Path.cwd(),
    )


def test_manifest_file_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.file_count, int)


def test_manifest_pdf_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.docx_count, int)


def test_manifest_content_group_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_returns_list():
    m = _make_manifest()
    assert isinstance(m.categories_covered, list)


def test_manifest_file_count_with_mixed():
    docs = [_make_doc_entry(source_type="pdf"), _make_doc_entry(source_type="docx")]
    m = _make_manifest(docs=docs)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_manifest_pdf_count_with_only_docx():
    docs = [_make_doc_entry(source_type="docx")]
    m = _make_manifest(docs=docs)
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_manifest_categories_covered_returns_sorted():
    docs = [
        _make_doc_entry(categories=("z", "a")),
        _make_doc_entry(categories=("m",)),
    ]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup():
    docs = [
        _make_doc_entry(categories=("a", "b")),
        _make_doc_entry(categories=("b", "c")),
    ]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_with_unicode():
    docs = [_make_doc_entry(categories=("中文", "english"))]
    m = _make_manifest(docs=docs)
    assert "中文" in m.categories_covered
    assert "english" in m.categories_covered


def test_manifest_content_group_count_empty():
    m = _make_manifest()
    assert m.content_group_count == 0


def test_manifest_content_group_count_all_unpaired():
    docs = [_make_doc_entry(), _make_doc_entry(doc_id="d2")]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_pair():
    docs = [
        _make_doc_entry(doc_id="a", paired_with="b"),
        _make_doc_entry(doc_id="b", paired_with="a"),
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_two_pairs():
    docs = [
        _make_doc_entry(doc_id="a", paired_with="b"),
        _make_doc_entry(doc_id="b", paired_with="a"),
        _make_doc_entry(doc_id="c", paired_with="d"),
        _make_doc_entry(doc_id="d", paired_with="c"),
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_mixed():
    docs = [
        _make_doc_entry(doc_id="a", paired_with="b"),
        _make_doc_entry(doc_id="b", paired_with="a"),
        _make_doc_entry(doc_id="c"),  # unpaired
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2  # 1 pair + 1 unpaired


def test_manifest_content_group_count_self_pair():
    """self-pair (doc_id == paired_with) 算 1 组。"""
    docs = [_make_doc_entry(doc_id="x", paired_with="x")]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_unidirectional_pair():
    """A → B 但 B 没有 paired_with → 仍算 1 组（frozenset 去重）。"""
    docs = [
        _make_doc_entry(doc_id="a", paired_with="b"),
        _make_doc_entry(doc_id="b"),  # 没有 paired_with
    ]
    m = _make_manifest(docs=docs)
    # pair_ids = {frozenset({'a','b'})} → groups=1
    # 第 2 个循环：d=b 在 seen 里 → 不算 unpaired；d=a 在 seen 里
    # 总：1
    assert m.content_group_count == 1


# ---------- load_manifest malformed data 第三批 ----------


def _write_manifest(tmp_path, data):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_minimal_valid(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)
    assert m.devset_status == "incomplete"


def test_load_manifest_unknown_top_key_raises(tmp_path):
    """schema additionalProperties=false → 顶层未知 key 报错。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra": "unknown",
    })
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_invalid_devset_status_raises(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "invalid_status",  # 不在 enum
        "documents": [],
        "expected_failures": [],
    })
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_invalid_version_raises(tmp_path):
    """manifest_version='2.0' 在 schema 校验阶段（const='1.0'）就拒绝。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "2.0",  # schema const='1.0' 不通过
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    # schema 校验在前：EvalSchemaError；如果 schema 通过则会进 ManifestError
    # 现实是 schema 直接拒绝
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_invalid_json_raises(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_missing_file_raises(tmp_path):
    p = tmp_path / "nonexistent.json"
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_document_missing_path_raises(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "source_type": "pdf"}],  # missing path
        "expected_failures": [],
    })
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_document_absolute_path_raises(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "/etc/passwd", "source_type": "pdf"}],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError, match="绝对路径"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_document_backslash_path_raises(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "foo\\bar.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError, match="反斜杠"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_document_valid_path_ok(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "x"
    assert m.documents[0].source_type == "pdf"


def test_load_manifest_with_expected_failure(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad", "path": "samples/bad.pdf", "expected_error_code": "parse_failed"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].expected_error_code == "parse_failed"


def test_load_manifest_returns_manifest_instance(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_documents_is_tuple(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.documents, tuple)


def test_load_manifest_expected_failures_is_tuple(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.expected_failures, tuple)


def test_load_manifest_categories_default_empty_tuple(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()


def test_load_manifest_paired_with_default_none(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with is None


def test_load_manifest_sha256_default_none(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 is None


# ---------- module source forbidden tokens 第五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "abc", "aifc", "antigravity", "argparse", "asdl", "asyncio",
        "audioop", "base64", "binascii", "binhex", "calendar",
        "concurrent", "contextlib", "copyreg", "crypt",
        "curses", "datetime", "dl", "docxml",
        "dummy_threading", "email", "encodings", "ensurepip",
        "enum", "errno", "fileinput", "fnmatch",
        "formatter", "ftplib", "functools", "genericpath",
        "getopt", "getpass", "gettext", "glob",
        "gopherlib", "heapq", "html", "http",
        "imaplib", "ihooks", "imghdr", "importlib",
        "inspect", "ipaddress", "itertools", "keyword",
        "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "markupbase", "md5",
        "mhlib", "mimetypes", "mimify", "mmap",
        "msilib", "multifile", "multiprocessing", "mutex",
        "netrc", "nis", "nntplib", "numbers",
        "opcode", "operator", "optparse", "os2emxpath",
        "parser", "pdb", "pickle", "pickletools",
        "pipes", "pkgutil", "platform", "plistlib",
        "poplib", "posixfile", "posixpath", "profile",
        "pstats", "pty", "pyclbr", "py_compile",
        "pydoc", "queue", "quopri", "random",
        "readline", "reprlib", "rexec", "rfc822",
        "rlcompleter", "robotparser", "runpy", "sched",
        "secrets", "select", "sets", "sgmlop",
        "sgmllib", "sha", "shelve", "shlex",
        "shutil", "signal", "site", "smtplib",
        "smtpd", "sndhdr", "socket", "socketserver",
        "spawn", "spwd", "sqlite3", "ssl",
        "stat", "stringprep", "struct", "subprocess",
        "sunau", "sunaudio", "symtable", "sys",
        "sysconfig", "tabnanny", "tarfile", "telnetlib",
        "tempfile", "termios", "threading", "time",
        "timeit", "tomllib", "token", "tokenize",
        "trace", "traceback", "tracemalloc", "tty",
        "turtle", "types", "unicodedata", "unittest",
        "urllib", "urllib2", "urlparse", "user",
        "userdict", "userlist", "usersite", "uuid",
        "venv", "warnings", "wave", "weakref",
        "webbrowser", "whichdb", "wsgiref", "xdrlib",
        "xml", "xmlrpc", "zipapp", "zipfile",
        "zipimport", "zlib", "zoneinfo", "math",
    ],
)
def test_module_source_forbidden_tokens_fifth_batch(token):
    """这些 stdlib 模块不应出现在 manifest.py。"""
    src = inspect.getsource(mmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_json():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_imports_dataclass():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_imports_path():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_imports_manifest_version():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_imports_validate():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_defines_manifest_error_class():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_3_dataclasses():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src
    # DocumentEntry, ExpectedFailure, Manifest
    assert "class DocumentEntry" in src
    assert "class ExpectedFailure" in src
    assert "class Manifest" in src


def test_module_source_manifest_has_5_properties():
    """Manifest 有 5 个 @property：file_count/pdf_count/docx_count/content_group_count/categories_covered。"""
    src = inspect.getsource(Manifest)
    property_count = src.count("@property")
    assert property_count == 5


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(mmod)
    assert "async " not in src


def test_module_source_no_global():
    src = inspect.getsource(mmod)
    assert "global " not in src


def test_module_source_no_main_block():
    src = inspect.getsource(mmod)
    assert "__main__" not in src


def test_module_source_no_lambda():
    src = inspect.getsource(mmod)
    assert "lambda " not in src


def test_module_source_no_decorators_other_than_dataclass_property():
    """只允许 @dataclass 和 @property。"""
    src = inspect.getsource(mmod)
    lines = src.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("@"):
            assert stripped in ("@dataclass(frozen=True)", "@property"), \
                f"unexpected decorator: {stripped}"


def test_module_source_has_2_module_level_functions():
    """load_manifest + _detect_project_root（_is_absolute_like / _has_backslash / _resolve_relative_path 也算）。"""
    src = inspect.getsource(mmod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    # _is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root = 5
    assert func_count == 5


def test_module_source_has_all_with_5_entries():
    src = inspect.getsource(mmod)
    assert "__all__" in src
    assert '"ManifestError"' in src
    assert '"Manifest"' in src
    assert '"DocumentEntry"' in src
    assert '"ExpectedFailure"' in src
    assert '"load_manifest"' in src


# ---------- signatures 精确补强 ----------


def test_is_absolute_like_signature():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_has_backslash_signature():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_resolve_relative_path_signature_3_params():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_no_defaults():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_resolve_relative_path_return_annotation_path():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


def test_load_manifest_signature_2_params():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_load_manifest_param_names():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_param_annotations_union():
    sig = inspect.signature(load_manifest)
    a1 = sig.parameters["manifest_path"].annotation
    a2 = sig.parameters["project_root"].annotation
    assert "Path" in str(a1) and "str" in str(a1)
    assert "Path" in str(a2) and "None" in str(a2)


def test_load_manifest_return_annotation_manifest():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest" or sig.return_annotation is Manifest


def test_detect_project_root_signature_1_param():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["start"]


def test_detect_project_root_return_annotation_path():
    sig = inspect.signature(_detect_project_root)
    assert "Path" in str(sig.return_annotation)


def test_no_varargs_varkw_in_any_function():
    for fn in [_is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root]:
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(mmod, types.ModuleType)


def test_module_namespace_name():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_has_5_entries():
    assert len(mmod.__all__) == 5


def test_module_all_entries_exact():
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_all_entries_str():
    for entry in mmod.__all__:
        assert isinstance(entry, str)


def test_module_has_5_module_level_functions():
    functions = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == mmod.__name__
    ]
    assert len(functions) == 5


def test_module_has_4_private_functions():
    private = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == mmod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(private) == 4  # _is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root


def test_module_has_1_public_function():
    public = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == mmod.__name__
        and not v.__name__.startswith("_")
    ]
    assert len(public) == 1
    assert public[0].__name__ == "load_manifest"


def test_module_has_4_classes():
    classes = [
        v for v in vars(mmod).values()
        if isinstance(v, type) and v.__module__ == mmod.__name__
    ]
    assert len(classes) == 4  # ManifestError, DocumentEntry, ExpectedFailure, Manifest


def test_module_has_3_dataclasses():
    src = inspect.getsource(mmod)
    dataclass_count = src.count("@dataclass(frozen=True)")
    assert dataclass_count == 3


def test_module_manifest_error_is_subclass_of_exception():
    assert issubclass(ManifestError, Exception)


def test_module_no_main_block():
    src = inspect.getsource(mmod)
    assert "__main__" not in src


def test_module_callable_load_manifest():
    assert callable(load_manifest)


def test_module_callable_helpers():
    assert callable(_is_absolute_like)
    assert callable(_has_backslash)
    assert callable(_resolve_relative_path)
    assert callable(_detect_project_root)


# ---------- 端到端集成补强 ----------


def test_e2e_load_manifest_returns_manifest_instance(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_with_one_document(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "x"


def test_e2e_load_manifest_with_categories(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "x",
            "path": "samples/foo.pdf",
            "source_type": "pdf",
            "categories": ["a", "b"],
        }],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("a", "b")
    assert m.categories_covered == ["a", "b"]


def test_e2e_load_manifest_with_paired_documents(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "a", "path": "samples/a.pdf", "source_type": "pdf", "paired_with": "b"},
            {"doc_id": "b", "path": "samples/b.docx", "source_type": "docx", "paired_with": "a"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 1


def test_e2e_load_manifest_with_two_unpaired_documents(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "a", "path": "samples/a.pdf", "source_type": "pdf"},
            {"doc_id": "b", "path": "samples/b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 2


def test_e2e_load_manifest_with_three_categories(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "a", "path": "samples/a.pdf", "source_type": "pdf", "categories": ["x"]},
            {"doc_id": "b", "path": "samples/b.pdf", "source_type": "pdf", "categories": ["y"]},
            {"doc_id": "c", "path": "samples/c.pdf", "source_type": "pdf", "categories": ["z"]},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["x", "y", "z"]


def test_e2e_load_manifest_twice_returns_equal_instances(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_load_manifest_returns_documents_as_tuples_in_dataclass(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.documents, tuple)
    assert isinstance(m.expected_failures, tuple)


def test_e2e_load_manifest_no_categories_returns_empty(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == []


def test_e2e_load_manifest_no_paired_with_returns_unpaired_count(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 1


def test_e2e_load_manifest_no_sha256_default_none(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "x", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 is None


def test_e2e_load_manifest_with_sha256(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "x",
            "path": "samples/foo.pdf",
            "source_type": "pdf",
            "sha256": "a" * 64,
        }],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == "a" * 64


def test_e2e_load_manifest_doc_id_unicode(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "文档1", "path": "samples/foo.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].doc_id == "文档1"
