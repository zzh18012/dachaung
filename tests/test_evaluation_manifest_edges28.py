"""evaluation/manifest.py 第二十八轮 edges 测试（Round 330）。

重点补强 edges27 未触及的角度：
- _is_absolute_like 数学边界第三批（Unicode / 4+ chars / driver letter only）
- _has_backslash 数学边界第三批
- DocumentEntry frozen / equality / hash / fields 精确
- Manifest properties 精确（pdf_count / docx_count / content_group_count 深度）
- content_group_count 算法深度（cyclic pair / chain / multiple groups）
- load_manifest malformed data 拒绝
- module source forbidden tokens 第三批（~75 stdlib）
- module source 字符串精确补强（control flow / method calls）
- signatures 精确补强（return annotation / defaults）
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import types
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from evaluation import manifest as manifest_mod
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


# ---------- _is_absolute_like 数学边界第三批 ----------


def test_is_absolute_like_uppercase_z_drive_with_slash():
    assert _is_absolute_like("Z:/foo") is True


def test_is_absolute_like_uppercase_z_drive_backslash():
    assert _is_absolute_like("Z:\\foo") is True


def test_is_absolute_like_lowercase_z_drive_with_slash():
    assert _is_absolute_like("z:/foo") is True


def test_is_absolute_like_drive_letter_only_no_slash():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_drive_letter_colon_only():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_4_chars_drive():
    assert _is_absolute_like("ABCD") is False


def test_is_absolute_like_chinese_drive_letter():
    """中文字符不是 alpha 在 isalpha() 但中文 isalpha() 返回 True。"""
    # 中文 isalpha() True，但 path[1] != ":" → False
    assert _is_absolute_like("中/foo") is False


def test_is_absolute_like_zero_length():
    assert _is_absolute_like("") is False


def test_is_absolute_like_just_a():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_chars_letter_colon():
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_three_chars_no_drive():
    assert _is_absolute_like("abc") is False


def test_is_absolute_like_three_chars_with_drive_no_slash():
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_three_chars_drive_dash():
    assert _is_absolute_like("a:-") is False


def test_is_absolute_like_three_chars_drive_dot():
    assert _is_absolute_like("a:.") is False


def test_is_absolute_like_three_chars_drive_space():
    assert _is_absolute_like("a: ") is False


def test_is_absolute_like_three_chars_drive_plus():
    assert _is_absolute_like("a:+") is False


# ---------- _has_backslash 数学边界第三批 ----------


def test_has_backslash_unicode_backslash_like():
    """Unicode 全角反斜杠（U+FF3C）不是 ASCII \\。"""
    assert _has_backslash("a＼b") is False


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_two_backslashes():
    assert _has_backslash("\\\\") is True


def test_has_backslash_in_url_like_path():
    assert _has_backslash("http://\\foo") is True


def test_has_backslash_at_position_0():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_last_position():
    assert _has_backslash("foo\\") is True


# ---------- DocumentEntry frozen / equality / hash / fields 精确 ----------


def test_document_entry_field_names_exact():
    flds = [f.name for f in fields(DocumentEntry)]
    assert flds == [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    ]


def test_document_entry_hashable_via_frozen():
    de = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    # frozen dataclass 是 hashable
    assert hash(de) is not None


def test_document_entry_can_be_set_key():
    de = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    s = {de}
    assert de in s


def test_document_entry_frozen_attribute_set_raises():
    de = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        de.doc_id = "x"


def test_document_entry_equality_full():
    a = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    b = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert a == b


def test_document_entry_inequality_on_path_str():
    a = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    b = DocumentEntry(
        doc_id="d1", path_str="c/d.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert a != b


def test_document_entry_categories_can_be_tuple_with_multiple():
    de = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None,
        categories=("x", "y", "z"),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert de.categories == ("x", "y", "z")


# ---------- ExpectedFailure frozen / fields ----------


def test_expected_failure_field_names_exact():
    flds = [f.name for f in fields(ExpectedFailure)]
    assert flds == [
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    ]


def test_expected_failure_hashable():
    ef = ExpectedFailure(
        doc_id="e1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    assert hash(ef) is not None


def test_expected_failure_frozen_set_raises():
    ef = ExpectedFailure(
        doc_id="e1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"


# ---------- Manifest properties 精确 ----------


def test_manifest_pdf_count_returns_0_for_only_docx():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            DocumentEntry(
                doc_id="d1", path_str="a/b.docx",
                resolved_path=Path("/tmp/a/b.docx"),
                source_type="docx", sha256=None, categories=(),
                paired_with=None, annotation_file_str=None,
                annotation_resolved=None, expectations=None,
            ),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.pdf_count == 0
    assert mf.docx_count == 1


def test_manifest_docx_count_returns_0_for_only_pdf():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            DocumentEntry(
                doc_id="d1", path_str="a/b.pdf",
                resolved_path=Path("/tmp/a/b.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with=None, annotation_file_str=None,
                annotation_resolved=None, expectations=None,
            ),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.pdf_count == 1
    assert mf.docx_count == 0


def test_manifest_pdf_count_mixed():
    docs = (
        DocumentEntry(
            doc_id=f"d{i}", path_str=f"a/b{i}.pdf",
            resolved_path=Path(f"/tmp/a/b{i}.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ) for i in range(3)
    )
    docs = tuple(docs)
    docs = docs + (
        DocumentEntry(
            doc_id="d10", path_str="a/b10.docx",
            resolved_path=Path("/tmp/a/b10.docx"),
            source_type="docx", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.pdf_count == 3
    assert mf.docx_count == 1


# ---------- content_group_count 算法深度 ----------


def test_content_group_count_pair_with_self_ignored_as_zero_groups():
    """d.paired_with == d.doc_id 时，frozenset({d, d}) = {d}，仍计 1 组（pair_ids 中存在）。"""
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(
            DocumentEntry(
                doc_id="d1", path_str="a.pdf",
                resolved_path=Path("/tmp/a.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with="d1",  # 自引用
                annotation_file_str=None, annotation_resolved=None,
                expectations=None,
            ),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset(["d1", "d1"]) = {"d1"} → 1 组
    assert mf.content_group_count == 1


def test_content_group_count_chain_pair_treated_as_disjoint():
    """d1→d2, d2→d3 → 两个 frozenset（{d1,d2}, {d2,d3}）各算 1 组。"""
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(
            DocumentEntry(
                doc_id="d1", path_str="a.pdf",
                resolved_path=Path("/tmp/a.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with="d2",
                annotation_file_str=None, annotation_resolved=None,
                expectations=None,
            ),
            DocumentEntry(
                doc_id="d2", path_str="b.pdf",
                resolved_path=Path("/tmp/b.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with="d3",
                annotation_file_str=None, annotation_resolved=None,
                expectations=None,
            ),
            DocumentEntry(
                doc_id="d3", path_str="c.pdf",
                resolved_path=Path("/tmp/c.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with=None,
                annotation_file_str=None, annotation_resolved=None,
                expectations=None,
            ),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # pair_ids = {{d1,d2}, {d2,d3}} → 2 组
    # d3 has paired_with != None but d3 in seen ({d1,d2,d3}) → unpaired 不加
    assert mf.content_group_count == 2


def test_content_group_count_unidirectional_pair_only_one_in_pair_advertises():
    """d1→d2 but d2.paired_with=None → frozenset({d1,d2}) → 1 组。"""
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(
            DocumentEntry(
                doc_id="d1", path_str="a.pdf",
                resolved_path=Path("/tmp/a.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with="d2",
                annotation_file_str=None, annotation_resolved=None,
                expectations=None,
            ),
            DocumentEntry(
                doc_id="d2", path_str="b.pdf",
                resolved_path=Path("/tmp/b.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with=None,
                annotation_file_str=None, annotation_resolved=None,
                expectations=None,
            ),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # pair_ids = {{d1,d2}} → 1 组；seen = {d1,d2}；d2 has no paired_with but in seen → not unpaired
    assert mf.content_group_count == 1


def test_content_group_count_one_unpaired_doc_only():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(
            DocumentEntry(
                doc_id="d1", path_str="a.pdf",
                resolved_path=Path("/tmp/a.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with=None,
                annotation_file_str=None, annotation_resolved=None,
                expectations=None,
            ),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 1


def test_content_group_count_zero_documents():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 0


def test_content_group_count_returns_int():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.content_group_count, int)


# ---------- categories_covered 精确 ----------


def test_categories_covered_returns_sorted_alphabetical():
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="a.pdf",
            resolved_path=Path("/tmp/a.pdf"),
            source_type="pdf", sha256=None,
            categories=("z", "a", "m"),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == ["a", "m", "z"]


def test_categories_covered_empty_when_no_categories():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(
            DocumentEntry(
                doc_id="d1", path_str="a.pdf",
                resolved_path=Path("/tmp/a.pdf"),
                source_type="pdf", sha256=None, categories=(),
                paired_with=None, annotation_file_str=None,
                annotation_resolved=None, expectations=None,
            ),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == []


def test_categories_covered_dedup_across_documents():
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="a.pdf",
            resolved_path=Path("/tmp/a.pdf"),
            source_type="pdf", sha256=None,
            categories=("x", "y"),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="b.pdf",
            resolved_path=Path("/tmp/b.pdf"),
            source_type="pdf", sha256=None,
            categories=("y", "z"),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == ["x", "y", "z"]


# ---------- load_manifest malformed data 拒绝 ----------


def test_load_manifest_missing_manifest_version_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_missing_devset_status_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "documents": [],
    }), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_missing_documents_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
    }), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_unsupported_version_raises(tmp_path):
    """schema 接受字符串，version 检查在 schema 后；99.0 在 schema 或 version 检查处都会拒绝。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "99.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # schema 检查或 version 检查会抛（具体由 schema 是否约束 version 决定）
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_returns_manifest_with_correct_version(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    from evaluation import MANIFEST_VERSION
    assert mf.manifest_version == MANIFEST_VERSION


def test_load_manifest_with_string_project_root(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=str(tmp_path))
    assert mf.project_root == tmp_path.resolve()


def test_load_manifest_path_is_dir_raises(tmp_path):
    """manifest_path 是目录 → ManifestError。"""
    with pytest.raises(ManifestError):
        load_manifest(tmp_path, project_root=tmp_path)


# ---------- module source forbidden tokens 第三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "base64", "binascii", "bisect", "calendar", "concurrent",
        "contextlib", "copyreg", "csv", "fnmatch", "functools",
        "getopt", "getpass", "gettext", "heapq", "imaplib",
        "importlib", "ipaddress", "locale", "lzma", "mailbox",
        "mimetypes", "mmap", "multiprocessing", "netrc", "ntpath",
        "numbers", "operator", "optparse", "platform",
        "poplib", "posixpath", "profile", "pstats", "py_compile",
        "quopri", "reprlib", "runpy", "sched", "select",
        "shelve", "shlex", "signal", "site", "smtplib",
        "sndhdr", "socketserver", "sqlite3", "ssl", "subprocess",
        "sunau", "symtable", "tabnanny", "telnetlib", "termios",
        "timeit", "tkinter", "token", "tokenize", "trace",
        "tty", "turtle", "unittest", "urllib",
        "uu", "webbrowser", "xdrlib", "zipapp", "zipfile",
        "zipimport", "argparse", "array", "ast", "atexit",
        "builtins", "collections",
    ],
)
def test_module_source_forbidden_tokens_third_batch(token):
    """这些 stdlib 模块不应出现在 manifest.py（仅用 json/dataclasses/Path/typing）。"""
    src = inspect.getsource(manifest_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_class_manifest_error():
    src = inspect.getsource(manifest_mod)
    assert "class ManifestError" in src


def test_module_source_manifest_error_docstring_present():
    src = inspect.getsource(manifest_mod)
    assert '"""清单加载或校验失败。"""' in src


def test_module_source_module_docstring_present():
    src = inspect.getsource(manifest_mod)
    assert '"""开发集清单加载器。' in src


def test_module_source_mentions_relative_path_constraint():
    src = inspect.getsource(manifest_mod)
    assert "相对路径" in src


def test_module_source_mentions_no_absolute_path_constraint():
    src = inspect.getsource(manifest_mod)
    assert "绝对路径" in src


def test_module_source_mentions_no_backslash_constraint():
    src = inspect.getsource(manifest_mod)
    assert "反斜杠" in src


def test_module_source_mentions_project_root_constraint():
    src = inspect.getsource(manifest_mod)
    assert "项目根" in src


def test_module_source_has_dataclass_frozen_true():
    src = inspect.getsource(manifest_mod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_has_3_dataclass_decorators():
    src = inspect.getsource(manifest_mod)
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_has_property_decorators():
    src = inspect.getsource(manifest_mod)
    assert "@property" in src


def test_module_source_has_5_property_decorators():
    """行首 @property 装饰器共 5 个（file_count/pdf_count/docx_count/content_group_count/categories_covered）。"""
    src = inspect.getsource(manifest_mod)
    decorator_lines = [
        line for line in src.splitlines()
        if line.strip() == "@property"
    ]
    assert len(decorator_lines) == 5


def test_module_source_load_manifest_uses_validate_call():
    src = inspect.getsource(manifest_mod)
    assert 'validate(data, "manifest.schema.json")' in src


def test_module_source_load_manifest_uses_manifest_version_constant():
    src = inspect.getsource(manifest_mod)
    assert "MANIFEST_VERSION" in src


def test_module_source_resolve_relative_path_raises_manifest_error():
    src = inspect.getsource(manifest_mod)
    assert "raise ManifestError" in src


def test_module_source_resolve_relative_path_3_raises():
    src = inspect.getsource(_resolve_relative_path)
    # 3 个 raise：empty / absolute / backslash / outside → 4 个
    assert inspect.getsource(_resolve_relative_path).count("raise ManifestError") >= 3


def test_module_source_no_yield():
    src = inspect.getsource(manifest_mod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(manifest_mod)
    assert "async " not in src


def test_module_source_no_lambda():
    src = inspect.getsource(manifest_mod)
    assert "lambda " not in src


def test_module_source_no_main_block():
    src = inspect.getsource(manifest_mod)
    assert "__main__" not in src


# ---------- signatures 精确补强 ----------


def test_is_absolute_like_signature_str_param():
    sig = inspect.signature(_is_absolute_like)
    assert "path_str" in sig.parameters
    p = sig.parameters["path_str"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert p.default is inspect.Parameter.empty


def test_is_absolute_like_return_annotation():
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in str(sig.return_annotation)


def test_has_backslash_signature_str_param():
    sig = inspect.signature(_has_backslash)
    assert "path_str" in sig.parameters


def test_has_backslash_return_annotation():
    sig = inspect.signature(_has_backslash)
    assert "bool" in str(sig.return_annotation)


def test_resolve_relative_path_3_params():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters) == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_no_default():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_resolve_relative_path_return_annotation_path():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


def test_detect_project_root_1_param():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters) == ["start"]


def test_detect_project_root_return_annotation_path():
    sig = inspect.signature(_detect_project_root)
    assert "Path" in str(sig.return_annotation)


def test_load_manifest_2_params():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters) == ["manifest_path", "project_root"]


def test_load_manifest_project_root_optional():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.default is None
    assert "| None" in str(p.annotation) or "Optional" in str(p.annotation)


def test_load_manifest_return_annotation_manifest():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


def test_no_varargs_varkw_in_helpers():
    for fn in (_is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root, load_manifest):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性 ----------


def test_namespace_is_absolute_like_in_module():
    assert hasattr(manifest_mod, "_is_absolute_like")
    assert isinstance(getattr(manifest_mod, "_is_absolute_like"), types.FunctionType)


def test_namespace_has_backslash_in_module():
    assert hasattr(manifest_mod, "_has_backslash")


def test_namespace_resolve_relative_path_in_module():
    assert hasattr(manifest_mod, "_resolve_relative_path")


def test_namespace_detect_project_root_in_module():
    assert hasattr(manifest_mod, "_detect_project_root")


def test_namespace_load_manifest_in_module():
    assert hasattr(manifest_mod, "load_manifest")


def test_namespace_manifest_error_in_module():
    assert hasattr(manifest_mod, "ManifestError")
    assert isinstance(getattr(manifest_mod, "ManifestError"), type)
    assert issubclass(manifest_mod.ManifestError, Exception)


def test_namespace_manifest_in_module():
    assert hasattr(manifest_mod, "Manifest")
    assert isinstance(getattr(manifest_mod, "Manifest"), type)


def test_namespace_document_entry_in_module():
    assert hasattr(manifest_mod, "DocumentEntry")


def test_namespace_expected_failure_in_module():
    assert hasattr(manifest_mod, "ExpectedFailure")


def test_module_all_5_entries_exact():
    assert manifest_mod.__all__ == [
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    ]


def test_module_all_is_list():
    assert isinstance(manifest_mod.__all__, list)


def test_module_all_entries_str():
    for entry in manifest_mod.__all__:
        assert isinstance(entry, str)


def test_module_has_4_private_functions():
    private_funcs = [
        n for n, v in vars(manifest_mod).items()
        if n.startswith("_") and not n.startswith("__")
        and isinstance(v, types.FunctionType)
    ]
    assert sorted(private_funcs) == [
        "_detect_project_root", "_has_backslash",
        "_is_absolute_like", "_resolve_relative_path",
    ]


def test_module_has_1_public_function():
    public_funcs = [
        n for n, v in vars(manifest_mod).items()
        if not n.startswith("_") and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == manifest_mod.__name__
    ]
    assert public_funcs == ["load_manifest"]


def test_module_has_4_classes():
    classes = [
        n for n, v in vars(manifest_mod).items()
        if not n.startswith("_") and isinstance(v, type)
        and getattr(v, "__module__", "") == manifest_mod.__name__
    ]
    assert sorted(classes) == [
        "DocumentEntry", "ExpectedFailure", "Manifest", "ManifestError",
    ]


def test_module_has_3_dataclasses():
    dataclasses_in_module = [
        n for n, v in vars(manifest_mod).items()
        if not n.startswith("_") and isinstance(v, type) and is_dataclass(v)
    ]
    assert sorted(dataclasses_in_module) == [
        "DocumentEntry", "ExpectedFailure", "Manifest",
    ]


def test_module_no_main_block():
    src = inspect.getsource(manifest_mod)
    assert 'if __name__' not in src


# ---------- 端到端集成补强 ----------


def _write_manifest(tmp_path, data):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_e2e_manifest_with_one_pdf_doc(tmp_path):
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.file_count == 1
    assert mf.pdf_count == 1
    assert mf.docx_count == 0


def test_e2e_manifest_with_one_docx_doc(tmp_path):
    docx_path = tmp_path / "a.docx"
    docx_path.write_bytes(b"PK\x03\x04")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.docx", "source_type": "docx"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.file_count == 1
    assert mf.pdf_count == 0
    assert mf.docx_count == 1


def test_e2e_manifest_with_two_categories(tmp_path):
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["report", "financial"]},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.categories_covered == ["financial", "report"]


def test_e2e_manifest_with_paired_pdfs(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf",
             "paired_with": "d1"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.content_group_count == 1


def test_e2e_manifest_with_expected_failure(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "e1", "path": "a.pdf",
             "expected_error_code": "unsupported_format"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert len(mf.expected_failures) == 1
    ef = mf.expected_failures[0]
    assert ef.doc_id == "e1"
    assert ef.expected_error_code == "unsupported_format"
    assert ef.source_type is None


def test_e2e_manifest_with_expectations(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"paragraph": 5}}},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    d = mf.documents[0]
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_e2e_manifest_path_str_kept_as_relative(tmp_path):
    """DocumentEntry.path_str 保留原始相对路径形式。"""
    pdf1 = tmp_path / "subdir" / "a.pdf"
    pdf1.parent.mkdir(parents=True)
    pdf1.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "subdir/a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].path_str == "subdir/a.pdf"


def test_e2e_manifest_resolved_path_is_absolute(tmp_path):
    """DocumentEntry.resolved_path 是绝对路径。"""
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    rp = mf.documents[0].resolved_path
    assert rp.is_absolute()


def test_e2e_manifest_documents_is_tuple(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert isinstance(mf.documents, tuple)


def test_e2e_manifest_expected_failures_is_tuple(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert isinstance(mf.expected_failures, tuple)


def test_e2e_manifest_with_annotation_file(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    ann = tmp_path / "a.json"
    ann.write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "a.json"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    d = mf.documents[0]
    assert d.annotation_file_str == "a.json"
    assert d.annotation_resolved is not None
    assert d.annotation_resolved.is_absolute()


def test_e2e_manifest_load_twice_returns_equal_manifests(tmp_path):
    """同一 manifest 文件读两次 → 两个 Manifest 实例相等（frozen dataclass）。"""
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf1 = load_manifest(p, project_root=tmp_path)
    mf2 = load_manifest(p, project_root=tmp_path)
    assert mf1 == mf2
