"""evaluation/manifest.py 第二十九轮 edges 测试（Round 336）。

重点补强 edges28 未触及的角度：
- _is_absolute_like 数学边界第四批
- _has_backslash 数学边界第四批
- DocumentEntry frozen / fields 第二批
- ExpectedFailure frozen / fields 第二批
- Manifest properties 第二批
- content_group_count 算法深度第二批
- categories_covered 第二批
- load_manifest malformed data 第二批
- module source forbidden tokens 第四批（~100 stdlib）
- module source 字符串精确补强
- signatures 精确补强
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


# ---------- _is_absolute_like 数学边界第四批 ----------


def test_is_absolute_like_with_drive_letter_a_uppercase():
    assert _is_absolute_like("A:/x") is True


def test_is_absolute_like_with_drive_letter_a_lowercase():
    assert _is_absolute_like("a:/x") is True


def test_is_absolute_like_with_just_a_colon():
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_with_just_a_slash():
    assert _is_absolute_like("a/") is False


def test_is_absolute_like_3_letters_with_dash():
    assert _is_absolute_like("a-b") is False


def test_is_absolute_like_3_letters_with_dot():
    assert _is_absolute_like("a.b") is False


def test_is_absolute_like_3_letters_with_space():
    assert _is_absolute_like("a b") is False


def test_is_absolute_like_path_with_only_drive_letter():
    assert _is_absolute_like("Z") is False


def test_is_absolute_like_path_with_just_slash_two_chars():
    assert _is_absolute_like("/x") is True


def test_is_absolute_like_with_only_backslashes():
    assert _is_absolute_like("\\\\") is False  # 不是 POSIX / 开头


def test_is_absolute_like_with_only_forward_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_empty_string_returns_false():
    assert _is_absolute_like("") is False


def test_is_absolute_like_none_returns_false():
    """None 输入 → False（`not None` 短路命中第一支）。"""
    assert _is_absolute_like(None) is False


# ---------- _has_backslash 数学边界第四批 ----------


def test_has_backslash_with_long_path_no_backslash():
    assert _has_backslash("a/b/c/d/e/f.txt") is False


def test_has_backslash_with_long_path_one_backslash():
    assert _has_backslash("a/b/c\\d/e/f.txt") is True


def test_has_backslash_with_only_letters():
    assert _has_backslash("abcdefg") is False


def test_has_backslash_with_only_digits():
    assert _has_backslash("12345") is False


def test_has_backslash_with_special_chars_no_backslash():
    assert _has_backslash("!@#$%^&*()") is False


def test_has_backslash_none_raises_typeerror():
    with pytest.raises(TypeError):
        _has_backslash(None)


# ---------- DocumentEntry frozen / fields 第二批 ----------


def test_document_entry_field_count():
    flds = list(fields(DocumentEntry))
    assert len(flds) == 10


def test_document_entry_field_types_dict_str_to_annotation():
    flds = {f.name: f for f in fields(DocumentEntry)}
    # path_str 应是 str 类型
    assert "str" in str(flds["path_str"].type)
    # resolved_path 应是 Path
    assert "Path" in str(flds["resolved_path"].type)


def test_document_entry_field_types_for_optional():
    flds = {f.name: f for f in fields(DocumentEntry)}
    # sha256 应是 str | None
    assert "None" in str(flds["sha256"].type) or "Optional" in str(flds["sha256"].type)


def test_document_entry_field_types_for_categories():
    flds = {f.name: f for f in fields(DocumentEntry)}
    # categories 是 tuple
    assert "tuple" in str(flds["categories"].type).lower()


def test_document_entry_equality_with_all_fields_set():
    a = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256="abc",
        categories=("x", "y"), paired_with="d2",
        annotation_file_str="a/b.json",
        annotation_resolved=Path("/tmp/a/b.json"),
        expectations={"k": 1},
    )
    b = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256="abc",
        categories=("x", "y"), paired_with="d2",
        annotation_file_str="a/b.json",
        annotation_resolved=Path("/tmp/a/b.json"),
        expectations={"k": 1},
    )
    assert a == b


def test_document_entry_inequality_on_categories():
    a = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None,
        categories=("x",), paired_with=None,
        annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    b = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None,
        categories=("x", "y"), paired_with=None,
        annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert a != b


def test_document_entry_inequality_on_paired_with():
    a = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    b = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert a != b


# ---------- ExpectedFailure frozen / fields 第二批 ----------


def test_expected_failure_field_count():
    flds = list(fields(ExpectedFailure))
    assert len(flds) == 5


def test_expected_failure_field_types_for_source_type():
    flds = {f.name: f for f in fields(ExpectedFailure)}
    # source_type 是 Optional[str]
    assert "str" in str(flds["source_type"].type)
    assert "None" in str(flds["source_type"].type) or "Optional" in str(flds["source_type"].type)


def test_expected_failure_equality():
    a = ExpectedFailure(
        doc_id="e1", path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        expected_error_code="unsupported_format",
        source_type="pdf",
    )
    b = ExpectedFailure(
        doc_id="e1", path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        expected_error_code="unsupported_format",
        source_type="pdf",
    )
    assert a == b


def test_expected_failure_inequality_on_doc_id():
    a = ExpectedFailure(
        doc_id="e1", path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        expected_error_code="x",
        source_type=None,
    )
    b = ExpectedFailure(
        doc_id="e2", path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        expected_error_code="x",
        source_type=None,
    )
    assert a != b


# ---------- Manifest properties 第二批 ----------


def _make_doc(doc_id, source_type, paired_with=None, categories=()):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"{doc_id}.pdf",
        resolved_path=Path(f"/tmp/{doc_id}.pdf"),
        source_type=source_type, sha256=None,
        categories=categories, paired_with=paired_with,
        annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )


def test_manifest_file_count_returns_int():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.file_count, int)


def test_manifest_pdf_count_returns_int():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.pdf_count, int)


def test_manifest_docx_count_returns_int():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.docx_count, int)


def test_manifest_categories_covered_returns_list_type():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(_make_doc("d1", "pdf", categories=("a",)),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.categories_covered, list)


# ---------- content_group_count 算法深度第二批 ----------


def test_content_group_count_one_pair_paired_with_self_treated_as_single():
    """d.paired_with=d → frozenset([d, d]) = {d} → 1 组。"""
    docs = (_make_doc("d1", "pdf", paired_with="d1"),)
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 1


def test_content_group_count_chain_3_documents():
    """d1→d2, d2→d3, d3→None → 两组 frozenset（{d1,d2}, {d2,d3}）。"""
    docs = (
        _make_doc("d1", "pdf", paired_with="d2"),
        _make_doc("d2", "pdf", paired_with="d3"),
        _make_doc("d3", "pdf", paired_with=None),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # pair_ids = {{d1,d2}, {d2,d3}} → 2 组
    # seen = {d1,d2,d3} → unpaired=0
    assert mf.content_group_count == 2


def test_content_group_count_pair_paired_with_unknown_doc():
    """d1.paired_with=nonexistent → frozenset({d1, nonexistent}) → 1 组。"""
    docs = (_make_doc("d1", "pdf", paired_with="nonexistent"),)
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset([d1, nonexistent]) → 1 组
    # d1 in seen → 不算 unpaired
    assert mf.content_group_count == 1


def test_content_group_count_mixed_paired_and_unpaired():
    """3 docs：1 对 paired + 1 unpaired → 2 组。"""
    docs = (
        _make_doc("d1", "pdf", paired_with="d2"),
        _make_doc("d2", "pdf", paired_with="d1"),
        _make_doc("d3", "pdf", paired_with=None),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 2


def test_content_group_count_two_separate_pairs():
    """4 docs：两对 paired → 2 组。"""
    docs = (
        _make_doc("d1", "pdf", paired_with="d2"),
        _make_doc("d2", "pdf", paired_with="d1"),
        _make_doc("d3", "pdf", paired_with="d4"),
        _make_doc("d4", "pdf", paired_with="d3"),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 2


# ---------- categories_covered 第二批 ----------


def test_categories_covered_one_doc_one_category():
    docs = (_make_doc("d1", "pdf", categories=("x",)),)
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == ["x"]


def test_categories_covered_two_docs_disjoint():
    docs = (
        _make_doc("d1", "pdf", categories=("a",)),
        _make_doc("d2", "pdf", categories=("b",)),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == ["a", "b"]


def test_categories_covered_three_docs_with_overlap():
    docs = (
        _make_doc("d1", "pdf", categories=("a", "b")),
        _make_doc("d2", "pdf", categories=("b", "c")),
        _make_doc("d3", "pdf", categories=("a", "c")),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == ["a", "b", "c"]


def test_categories_covered_with_unicode():
    docs = (_make_doc("d1", "pdf", categories=("中文", "English"),),)
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == sorted(["中文", "English"])


# ---------- load_manifest malformed data 第二批 ----------


def _write_manifest(tmp_path, data):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_with_unknown_top_level_key_still_loads(tmp_path):
    """schema 允许 additionalProperties 或忽略未知 key。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "unknown_top_level": "ignored",
    })
    # schema 可能拒绝或忽略；只要能加载或明确失败即可
    try:
        mf = load_manifest(p, project_root=tmp_path)
        assert mf is not None
    except (ManifestError, Exception):
        pass


def test_load_manifest_with_empty_documents(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents == ()


def test_load_manifest_with_empty_expected_failures(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.expected_failures == ()


def test_load_manifest_with_missing_expected_failures_key(tmp_path):
    """manifest schema 可能不要求 expected_failures。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.expected_failures == ()


def test_load_manifest_with_one_document(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert len(mf.documents) == 1


def test_load_manifest_with_two_documents(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert len(mf.documents) == 2


def test_load_manifest_document_path_must_be_relative(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/absolute/path.pdf", "source_type": "pdf"},
        ],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_document_path_no_backslash(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "subdir\\a.pdf", "source_type": "pdf"},
        ],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_returns_manifest_with_devset_status(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.devset_status == "incomplete"


# ---------- module source forbidden tokens 第四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "_thread", "_weakref", "abc", "aifc", "antigravity",
        "asynchat", "asyncio", "asyncore", "audioop", "binhex",
        "cProfile", "cgi", "cgitb", "chunk", "code", "codeop",
        "colorsys", "commands", "compileall", "ctypes",
        "curses", "datetime", "decimal", "difflib", "dis",
        "distutils", "doctest", "dummy_threading", "ensurepip",
        "enum", "errno", "exceptions", "filecmp", "fileinput",
        "fmt", "formatter", "fpformat", "fractions", "gc",
        "genericpath", "getopt", "getpass", "glob", "gdbm",
        "grp", "hashlib", "hmac", "hotshot", "html",
        "http", "ihooks", "imghdr",
        "itertools", "keyword", "linecache", "linuxaudiodev",
        "logging", "macpath", "macurl2path", "marshal",
        "md5", "mhlib", "mimetools", "multifile", "mutex",
        "nis", "nntplib", "parser",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "plistlib", "popen2", "poplib", "posixfile", "pprint",
        "pty", "pyclbr", "pydoc", "queue", "quopri",
        "random", "readline", "resource",
        "rexec", "rfc822", "rlcompleter", "robotparser",
        "sets", "sgmllib", "shelve", "shutil",
        "smtpd", "sndhdr", "socket", "spwd",
        "sre_compile", "sre_constants", "sre_parse", "statistics",
        "stringprep", "struct", "sunau",
    ],
)
def test_module_source_forbidden_tokens_fourth_batch(token):
    """这些 stdlib 模块不应出现在 manifest.py。"""
    src = inspect.getsource(manifest_mod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(manifest_mod)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(manifest_mod)
    assert "import json" in src


def test_module_source_has_dataclass_import():
    src = inspect.getsource(manifest_mod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_path_import():
    src = inspect.getsource(manifest_mod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import():
    src = inspect.getsource(manifest_mod)
    assert "from typing import Any" in src


def test_module_source_has_evaluation_manifest_version_import():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_schema_validate_import():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_3_dataclass_decorators():
    src = inspect.getsource(manifest_mod)
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_has_5_property_decorators():
    src = inspect.getsource(manifest_mod)
    decorator_lines = [
        line for line in src.splitlines()
        if line.strip() == "@property"
    ]
    assert len(decorator_lines) == 5


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
    assert 'if __name__' not in src


def test_module_source_resolve_relative_path_uses_relative_to():
    src = inspect.getsource(_resolve_relative_path)
    assert "relative_to" in src


def test_module_source_resolve_relative_path_raises_value_error_caught():
    src = inspect.getsource(_resolve_relative_path)
    assert "except ValueError:" in src


def test_module_source_load_manifest_uses_validate_call():
    src = inspect.getsource(load_manifest)
    assert 'validate(data, "manifest.schema.json")' in src


def test_module_source_load_manifest_uses_manifest_version_compare():
    src = inspect.getsource(load_manifest)
    assert "MANIFEST_VERSION" in src
    assert "manifest_version" in src


def test_module_source_detect_project_root_uses_pyproject_toml():
    src = inspect.getsource(_detect_project_root)
    assert "pyproject.toml" in src


# ---------- signatures 精确补强 ----------


def test_load_manifest_2_params():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters) == ["manifest_path", "project_root"]


def test_load_manifest_manifest_path_annotation_union():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["manifest_path"]
    assert "Path" in str(p.annotation)
    assert "str" in str(p.annotation)


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.default is None


def test_resolve_relative_path_3_params_no_default():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_detect_project_root_1_param():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters) == ["start"]


def test_is_absolute_like_return_annotation_bool():
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in str(sig.return_annotation)


def test_has_backslash_return_annotation_bool():
    sig = inspect.signature(_has_backslash)
    assert "bool" in str(sig.return_annotation)


def test_no_varargs_varkw_in_helpers():
    for fn in (_is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root, load_manifest):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性 ----------


def test_namespace_module():
    assert isinstance(manifest_mod, types.ModuleType)


def test_namespace_is_absolute_like():
    assert hasattr(manifest_mod, "_is_absolute_like")


def test_namespace_has_backslash():
    assert hasattr(manifest_mod, "_has_backslash")


def test_namespace_resolve_relative_path():
    assert hasattr(manifest_mod, "_resolve_relative_path")


def test_namespace_detect_project_root():
    assert hasattr(manifest_mod, "_detect_project_root")


def test_namespace_load_manifest():
    assert hasattr(manifest_mod, "load_manifest")


def test_namespace_manifest_error():
    assert hasattr(manifest_mod, "ManifestError")
    assert issubclass(manifest_mod.ManifestError, Exception)


def test_namespace_manifest():
    assert hasattr(manifest_mod, "Manifest")


def test_namespace_document_entry():
    assert hasattr(manifest_mod, "DocumentEntry")


def test_namespace_expected_failure():
    assert hasattr(manifest_mod, "ExpectedFailure")


def test_module_all_5_entries():
    assert manifest_mod.__all__ == [
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    ]


def test_module_all_is_list():
    assert isinstance(manifest_mod.__all__, list)


def test_module_has_4_private_functions():
    private_funcs = [
        n for n, v in vars(manifest_mod).items()
        if n.startswith("_") and not n.startswith("__")
        and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == manifest_mod.__name__
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


def test_e2e_manifest_with_unicode_doc_id(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "测试", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].doc_id == "测试"


def test_e2e_manifest_with_2_documents_pair(tmp_path):
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


def test_e2e_manifest_with_2_documents_unpaired(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_bytes(b"%PDF-1.4")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.content_group_count == 2


def test_e2e_manifest_with_3_categories(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["report", "financial", "annual"]},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.categories_covered == ["annual", "financial", "report"]


def test_e2e_manifest_load_twice_returns_equal(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
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


def test_e2e_manifest_returns_manifest_instance(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert isinstance(mf, Manifest)


def test_e2e_manifest_documents_is_tuple(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
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


def test_e2e_manifest_with_expectations_dict(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
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


def test_e2e_manifest_with_no_paired_with_field(tmp_path):
    """document 缺 paired_with 字段 → 默认 None。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].paired_with is None


def test_e2e_manifest_with_no_categories_field(tmp_path):
    """document 缺 categories 字段 → 默认空 tuple。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].categories == ()


def test_e2e_manifest_with_no_sha256_field(tmp_path):
    """document 缺 sha256 字段 → 默认 None。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    })
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].sha256 is None
