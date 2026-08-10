"""evaluation/manifest.py 第三十九轮 edges 测试（Round 405）。

补强 edges38 未触及的角度：
- _is_absolute_like 数学边界第十二批（更多 corner cases：digit/非 ASCII alpha/Unicode colon/multi-byte first char）
- _has_backslash 数学边界第十二批（更多 boundary / empty / mix）
- _resolve_relative_path 行为深度第十二批（更多 path 形式 / Unicode / 各种异常分支）
- _detect_project_root 行为深度第十二批（pyproject.toml 在不同层级 / start 为 file / start 为根）
- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第十二批（frozen / equality / hash / repr / asdict / fields）
- Manifest properties algorithm 第十二批（pdf/docx count / content_group_count 双向 vs 单向 paired / categories 单一元素）
- load_manifest malformed data 第十二批（manifest_path 类型 / project_root 类型 / JSON 各种异常 / version mismatch）
- module source forbidden tokens 第十五批
- module source 字符串精确补强第十二批
- signatures 第十二批
- module 合理性第十二批
- 端到端集成第十二批
"""

from __future__ import annotations

import inspect
import json
import os
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from evaluation import MANIFEST_VERSION, manifest as mmod
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


def _make_doc(
    doc_id="d1",
    path_str="a.pdf",
    source_type="pdf",
    categories=("normal",),
    paired_with=None,
    expectations=None,
    sha256=None,
):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path("/x") / path_str,
        source_type=source_type,
        sha256=sha256,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=expectations,
    )


def _make_ef(
    doc_id="ef1",
    path_str="bad.pdf",
    expected_error_code="unsupported_format",
    source_type=None,
):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path("/x") / path_str,
        expected_error_code=expected_error_code,
        source_type=source_type,
    )


# ---------- _is_absolute_like 数学边界第十二批 ----------


def test_is_absolute_like_digit_first_batch12():
    """数字开头不是绝对路径。"""
    assert _is_absolute_like("1:/foo") is False  # 数字不是 alpha


def test_is_absolute_like_underscore_first_batch12():
    """下划线不是 alpha。"""
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_uppercase_alpha_batch12():
    """大写字母也是 alpha。"""
    assert _is_absolute_like("C:/windows") is True


def test_is_absolute_like_lowercase_alpha_batch12():
    assert _is_absolute_like("c:/windows") is True


def test_is_absolute_like_two_chars_only_batch12():
    """len==2 不足以进入 drive 分支（需 >=3）。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_drive_no_separator_batch12():
    """a:foo 没盘符分隔符 → 不是绝对路径。"""
    assert _is_absolute_like("a:foo") is False


def test_is_absolute_like_just_slash_batch12():
    """单斜杠 → True。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_double_backslash_batch12():
    """\\\\server → 不被识别为绝对路径（盘符规则）。"""
    # 双反斜杠在 Python 字符串中是 \\（两字符）
    assert _is_absolute_like("\\\\server") is False


def test_is_absolute_like_dot_first_batch12():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_tilde_first_batch12():
    """~ 不是绝对路径。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_chinese_alpha_batch12():
    """中文字符不是 ASCII alpha → 不是绝对路径。"""
    # 第一个字符是中文，但中文字符的 isalpha() 在 Python 中是 True
    # 但 _is_absolute_like 用 path_str[0].isalpha()，中文字符 .isalpha() 是 True
    # 接着 path_str[1] 必须是 ':'，path_str[2] 必须是 \ 或 /
    # 中文 + : + / → 触发 True
    assert _is_absolute_like("中:/foo") is True


# ---------- _has_backslash 数学边界第十二批 ----------


def test_has_backslash_empty_string_batch12():
    assert _has_backslash("") is False


def test_has_backslash_only_backslash_batch12():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_backslashes_batch12():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_forward_batch12():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_mixed_batch12():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_trailing_backslash_batch12():
    assert _has_backslash("abc\\") is True


def test_has_backslash_leading_backslash_batch12():
    assert _has_backslash("\\abc") is True


def test_has_backslash_unicode_with_backslash_batch12():
    assert _has_backslash("中文\\path") is True


def test_has_backslash_no_alpha_batch12():
    assert _has_backslash("123/456") is False


# ---------- _resolve_relative_path 行为深度第十二批 ----------


def test_resolve_relative_path_unicode_path_str_batch12(tmp_path):
    """Unicode 路径合法 → resolve 成功。"""
    resolved = _resolve_relative_path("文档/file.pdf", tmp_path, "test")
    assert resolved == (tmp_path / "文档" / "file.pdf").resolve()


def test_resolve_relative_path_unicode_field_name_batch12(tmp_path):
    """Unicode field name 在 error message 中。"""
    with pytest.raises(ManifestError, match="字段"):
        _resolve_relative_path("/abs/path", tmp_path, "字段")


def test_resolve_relative_path_dot_path_batch12(tmp_path):
    """path="." → resolve 到 project_root 自己。"""
    resolved = _resolve_relative_path(".", tmp_path, "test")
    assert resolved == tmp_path.resolve()


def test_resolve_relative_path_double_dot_path_batch12(tmp_path):
    """path="x/../y" → resolve 到 project_root/y。"""
    resolved = _resolve_relative_path("x/../y", tmp_path, "test")
    assert resolved == (tmp_path / "y").resolve()


def test_resolve_relative_path_path_with_many_dirs_batch12(tmp_path):
    """深层嵌套相对路径合法。"""
    resolved = _resolve_relative_path("a/b/c/d/e/f.pdf", tmp_path, "test")
    assert resolved == (tmp_path / "a" / "b" / "c" / "d" / "e" / "f.pdf").resolve()


def test_resolve_relative_path_returns_path_type_batch12(tmp_path):
    resolved = _resolve_relative_path("a", tmp_path, "test")
    assert isinstance(resolved, Path)


def test_resolve_relative_path_parent_escape_attempt_batch12(tmp_path):
    """../parent → resolve 后位于 project_root 之外 → ManifestError。"""
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../parent", tmp_path, "test")


def test_resolve_relative_path_double_parent_escape_batch12(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../../etc/passwd", tmp_path, "test")


def test_resolve_relative_path_pathlib_unresolved_link_batch12(tmp_path):
    """正常 path → 返回的 resolved_path 是 absolute。"""
    resolved = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    assert resolved.is_absolute()


def test_resolve_relative_path_returns_resolved_path_batch12(tmp_path):
    """resolve() 被调用（symlinks 已展开）。"""
    # 检查返回的 path 与手算 (project_root / path).resolve() 一致
    resolved = _resolve_relative_path("a.pdf", tmp_path, "test")
    assert resolved == (tmp_path / "a.pdf").resolve()


# ---------- _detect_project_root 行为深度第十二批 ----------


def test_detect_project_root_start_with_pyproject_at_root_batch12(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "sub" / "file.json"
    p.parent.mkdir()
    p.write_text("{}", encoding="utf-8")
    detected = _detect_project_root(p)
    assert detected == tmp_path.resolve()


def test_detect_project_root_start_with_pyproject_at_subdir_batch12(tmp_path):
    """最近祖先的 pyproject.toml 胜出。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("", encoding="utf-8")
    leaf = sub / "leaf.json"
    leaf.write_text("{}", encoding="utf-8")
    detected = _detect_project_root(leaf)
    assert detected == sub.resolve()


def test_detect_project_root_start_is_dir_batch12(tmp_path):
    """start 是目录 → 不切到 parent。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    detected = _detect_project_root(tmp_path)
    assert detected == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_first_dir_batch12(tmp_path):
    """没有 pyproject.toml → 返回 start（如果是 dir）或 start.parent（如果是 file）。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    leaf = sub / "leaf.json"
    leaf.write_text("{}", encoding="utf-8")
    detected = _detect_project_root(leaf)
    # 没有 pyproject → 返回 cur（即 sub）
    assert detected == sub.resolve()


def test_detect_project_root_no_pyproject_start_is_dir_batch12(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    detected = _detect_project_root(sub)
    assert detected == sub.resolve()


def test_detect_project_root_returns_path_type_batch12(tmp_path):
    detected = _detect_project_root(tmp_path)
    assert isinstance(detected, Path)


def test_detect_project_root_returns_absolute_batch12(tmp_path):
    detected = _detect_project_root(tmp_path)
    assert detected.is_absolute()


# ---------- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第十二批 ----------


def test_document_entry_field_count_10_batch12():
    """DocumentEntry 有 10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch12():
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


def test_document_entry_frozen_cannot_assign_batch12():
    """frozen=True → 赋值抛 FrozenInstanceError。"""
    doc = _make_doc()
    with pytest.raises(FrozenInstanceError):
        doc.doc_id = "new"


def test_document_entry_equality_batch12():
    d1 = _make_doc(doc_id="x")
    d2 = _make_doc(doc_id="x")
    assert d1 == d2


def test_document_entry_inequality_diff_id_batch12():
    d1 = _make_doc(doc_id="x")
    d2 = _make_doc(doc_id="y")
    assert d1 != d2


def test_document_entry_hash_consistent_with_eq_batch12():
    """frozen dataclass 有 __hash__。"""
    d1 = _make_doc(doc_id="x")
    d2 = _make_doc(doc_id="x")
    assert hash(d1) == hash(d2)


def test_document_entry_repr_has_class_name_batch12():
    d = _make_doc()
    assert "DocumentEntry" in repr(d)


def test_document_entry_categories_default_tuple_batch12():
    """categories 默认 tuple 类型。"""
    d = _make_doc(categories=("a", "b"))
    assert isinstance(d.categories, tuple)
    assert d.categories == ("a", "b")


def test_expected_failure_field_count_5_batch12():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch12():
    names = [f.name for f in fields(ExpectedFailure)]
    assert names == [
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    ]


def test_expected_failure_frozen_batch12():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new"


def test_manifest_field_count_5_batch12():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_batch12():
    names = [f.name for f in fields(Manifest)]
    assert names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_manifest_is_dataclass_batch12():
    assert is_dataclass(Manifest)


def test_manifest_frozen_batch12():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "new"


# ---------- Manifest properties algorithm 第十二批 ----------


def test_manifest_pdf_count_zero_when_no_docs_batch12():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docs_batch12():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.docx_count == 0


def test_manifest_pdf_count_mixed_batch12():
    docs = (
        _make_doc(doc_id="a", source_type="pdf"),
        _make_doc(doc_id="b", source_type="docx"),
        _make_doc(doc_id="c", source_type="pdf"),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_pdf_count_unknown_source_type_batch12():
    """未知 source_type 不计 pdf/docx。"""
    docs = (_make_doc(doc_id="a", source_type="unknown"),)
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.pdf_count == 0
    assert m.docx_count == 0


def test_manifest_content_group_count_bidirectional_pair_batch12():
    """双向 paired 算 1 组。"""
    docs = (
        _make_doc(doc_id="a", paired_with="b"),
        _make_doc(doc_id="b", paired_with="a"),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    # 双向引用产生 1 个 frozenset
    assert m.content_group_count == 1


def test_manifest_content_group_count_unidirectional_pair_batch12():
    """单向 paired 也算 1 组（避免重复计数）。"""
    docs = (
        _make_doc(doc_id="a", paired_with="b"),
        _make_doc(doc_id="b"),  # b 不引用 a
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    # 1 个 pair（a 引用 b）→ 1 组；b 不在 seen 中且无 paired_with → 但 b.doc_id in seen
    # 实际：pair_ids = {frozenset(a, b)}, seen = {a, b}，所以 b 不会被算 unpaired
    assert m.content_group_count == 1


def test_manifest_content_group_count_all_unpaired_batch12():
    docs = (
        _make_doc(doc_id="a"),
        _make_doc(doc_id="b"),
        _make_doc(doc_id="c"),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.content_group_count == 3


def test_manifest_categories_covered_sorted_batch12():
    docs = (
        _make_doc(doc_id="a", categories=("z", "a")),
        _make_doc(doc_id="b", categories=("m",)),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_unique_batch12():
    docs = (
        _make_doc(doc_id="a", categories=("a", "b")),
        _make_doc(doc_id="b", categories=("a", "c")),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_file_count_empty_batch12():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.file_count == 0


def test_manifest_file_count_returns_int_type_batch12():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert type(m.file_count) is int


# ---------- load_manifest malformed data 第十二批 ----------


def test_load_manifest_accepts_str_path_batch12(tmp_path):
    """load_manifest 接受 str 类型 manifest_path。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    result = load_manifest(str(manifest))
    assert isinstance(result, Manifest)


def test_load_manifest_accepts_path_path_batch12(tmp_path):
    """load_manifest 接受 Path 类型 manifest_path。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    result = load_manifest(manifest)
    assert isinstance(result, Manifest)


def test_load_manifest_str_project_root_batch12(tmp_path):
    """load_manifest 接受 str 类型 project_root。"""
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    result = load_manifest(manifest, project_root=str(tmp_path))
    assert isinstance(result.project_root, Path)


def test_load_manifest_path_project_root_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    result = load_manifest(manifest, project_root=tmp_path)
    assert isinstance(result.project_root, Path)


def test_load_manifest_missing_file_raises_batch12(tmp_path):
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(tmp_path / "no.json")


def test_load_manifest_directory_raises_batch12(tmp_path):
    """manifest_path 是目录 → is_file() False → ManifestError。"""
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(tmp_path)


def test_load_manifest_invalid_json_raises_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text("not valid json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(manifest)


def test_load_manifest_version_mismatch_raises_batch12(tmp_path):
    """schema 把 manifest_version 锁在 "1.0"，所以版本不符会先走 EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError

    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "9.9.9",  # 不兼容
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(manifest)


def test_load_manifest_returns_manifest_type_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    result = load_manifest(manifest)
    assert type(result) is Manifest


def test_load_manifest_documents_default_empty_tuple_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    result = load_manifest(manifest)
    assert result.documents == ()
    assert isinstance(result.documents, tuple)


def test_load_manifest_expected_failures_default_empty_tuple_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    result = load_manifest(manifest)
    assert result.expected_failures == ()
    assert isinstance(result.expected_failures, tuple)


# ---------- module source forbidden tokens 第十五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "import socket",
    ],
)
def test_manifest_source_no_forbidden_token_fifteenth_batch12(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_manifest_source_no_top_level_lambda_batch12():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_manifest_source_class_count_4_batch12():
    """顶层 4 个 class：ManifestError + 3 个 dataclass。"""
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    top_classes = [line for line in lines if line.startswith("class ")]
    assert len(top_classes) == 4
    # 每行格式："class <Name>(...):" 或 "class <Name>:" → 取 class 后的标识符
    class_names = set()
    import re
    for line in top_classes:
        m = re.match(r"class\s+(\w+)", line)
        if m:
            class_names.add(m.group(1))
    assert class_names == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_manifest_source_no_assert_statement_batch12():
    source = inspect.getsource(mmod)
    assert "\nassert " not in source
    assert not source.startswith("assert ")


def test_manifest_source_no_yield_batch12():
    source = inspect.getsource(mmod)
    assert "yield " not in source


def test_manifest_source_no_global_batch12():
    source = inspect.getsource(mmod)
    assert " global " not in source


def test_manifest_source_no_walrus_batch12():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_manifest_source_no_async_def_batch12():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_manifest_source_no_while_loop_batch12():
    source = inspect.getsource(mmod)
    assert "while " not in source


def test_manifest_source_no_input_call_batch12():
    source = inspect.getsource(mmod)
    assert "input(" not in source


def test_manifest_source_no_remove_call_batch12():
    source = inspect.getsource(mmod)
    assert ".remove(" not in source


# ---------- module source 字符串精确补强第十二批 ----------


def test_module_source_has_future_annotations_batch12():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:25])
    assert "from __future__ import annotations" in head


def test_module_source_imports_json_batch12():
    source = inspect.getsource(mmod)
    assert "import json" in source


def test_module_source_imports_dataclass_batch12():
    source = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in source


def test_module_source_imports_path_batch12():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch12():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_imports_manifest_version_batch12():
    source = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in source


def test_module_source_imports_validate_batch12():
    source = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in source


def test_module_source_has_class_manifest_error_batch12():
    source = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in source


def test_module_source_has_dataclass_document_entry_batch12():
    source = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in source
    assert "class DocumentEntry:" in source


def test_module_source_has_dataclass_expected_failure_batch12():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in source


def test_module_source_has_dataclass_manifest_batch12():
    source = inspect.getsource(mmod)
    assert "class Manifest:" in source


def test_module_source_has_frozen_property_batch12():
    """Manifest 是 frozen dataclass。"""
    source = inspect.getsource(mmod)
    assert source.count("@dataclass(frozen=True)") == 3


def test_module_source_has_load_manifest_function_batch12():
    source = inspect.getsource(mmod)
    assert "def load_manifest(" in source


def test_module_source_has_resolve_relative_path_batch12():
    source = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in source


def test_module_source_has_detect_project_root_batch12():
    source = inspect.getsource(mmod)
    assert "def _detect_project_root(" in source


def test_module_source_no_main_block_batch12():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_no_dunder_all_5_names_batch12():
    assert hasattr(mmod, "__all__")
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_source_docstring_present_batch12():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


# ---------- signatures 第十二批 ----------


def test_signature_is_absolute_like_one_param_batch12():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1
    assert list(sig.parameters) == ["path_str"]


def test_signature_is_absolute_like_return_bool_batch12():
    sig = inspect.signature(_is_absolute_like)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "bool" in annot_str


def test_signature_has_backslash_one_param_batch12():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1
    assert list(sig.parameters) == ["path_str"]


def test_signature_has_backslash_return_bool_batch12():
    sig = inspect.signature(_has_backslash)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "bool" in annot_str


def test_signature_resolve_relative_path_3_params_batch12():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters) == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_return_path_batch12():
    sig = inspect.signature(_resolve_relative_path)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str


def test_signature_load_manifest_2_params_batch12():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters) == ["manifest_path", "project_root"]


def test_signature_load_manifest_manifest_path_annotation_batch12():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["manifest_path"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "str" in annot_str


def test_signature_load_manifest_project_root_annotation_batch12():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "str" in annot_str
    assert "None" in annot_str


def test_signature_load_manifest_project_root_default_none_batch12():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.default is None


def test_signature_load_manifest_return_manifest_batch12():
    sig = inspect.signature(load_manifest)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Manifest" in annot_str


def test_signature_detect_project_root_1_param_batch12():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters) == ["start"]


def test_signature_detect_project_root_return_path_batch12():
    sig = inspect.signature(_detect_project_root)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str


def test_all_functions_no_var_kwargs_batch12():
    for fn in [_is_absolute_like, _has_backslash, _resolve_relative_path,
               load_manifest, _detect_project_root]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十二批 ----------


def test_module_name_evaluation_manifest_batch12():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_dunder_file_endswith_manifest_py_batch12():
    sep = os.sep
    assert mmod.__file__.endswith("evaluation" + sep + "manifest.py") or mmod.__file__.endswith(
        "evaluation/manifest.py"
    )


def test_module_user_function_count_5_batch12():
    funcs = [
        n for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "load_manifest",
        "_detect_project_root",
    }


def test_module_user_class_count_4_batch12():
    """ManifestError + 3 个 dataclass。"""
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert set(classes) == {
        "ManifestError",
        "DocumentEntry",
        "ExpectedFailure",
        "Manifest",
    }


def test_module_no_top_level_user_constants_batch12():
    """manifest 模块无顶层 user-defined 常量（tuple/list/dict）。
    annotations 是 from __future__ 注入的 _Feature；MANIFEST_VERSION 是 import 进来的。
    两者都不算用户自己定义的常量。
    """
    consts = [
        n for n, v in vars(mmod).items()
        if not n.startswith("__")
        and not callable(v)
        and not inspect.isclass(v)
        and not inspect.ismodule(v)
        and n not in ("annotations", "MANIFEST_VERSION")
    ]
    assert consts == []


def test_module_uses_future_annotations_batch12():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:25])
    assert "from __future__ import annotations" in head


def test_module_docstring_mentions_invariant_batch12():
    assert mmod.__doc__ is not None
    assert "不变量" in mmod.__doc__ or "invariant" in mmod.__doc__.lower()


def test_module_docstring_mentions_path_batch12():
    assert mmod.__doc__ is not None
    assert "路径" in mmod.__doc__ or "path" in mmod.__doc__.lower()


def test_manifest_error_is_exception_subclass_batch12():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_standard_error_only_batch12():
    """ManifestError 不是 ValueError 等。"""
    assert not issubclass(ManifestError, ValueError)
    assert not issubclass(ManifestError, TypeError)


def test_document_entry_is_dataclass_type_batch12():
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass_type_batch12():
    assert is_dataclass(ExpectedFailure)


def test_manifest_is_dataclass_type_batch12():
    assert is_dataclass(Manifest)


# ---------- 端到端集成第十二批 ----------


def test_e2e_load_manifest_full_round_trip_batch12(tmp_path):
    """完整 manifest → load → 检查所有字段。"""
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a.pdf",
                "source_type": "pdf",
                "sha256": "0" * 64,
                "categories": ["normal"],
            }
        ],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "bad.pdf",
                "expected_error_code": "unsupported_format",
            }
        ],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    # a.pdf / bad.pdf 必须真实存在（schema 不要求，但路径会解析）
    # schema 只校验 form，不要求文件存在
    (tmp_path / "a.pdf").write_text("", encoding="utf-8")
    (tmp_path / "bad.pdf").write_text("", encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "incomplete"
    assert len(m.documents) == 1
    assert len(m.expected_failures) == 1
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].sha256 == "0" * 64
    assert m.documents[0].categories == ("normal",)
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].expected_error_code == "unsupported_format"


def test_e2e_load_manifest_json_serializable_batch12(tmp_path):
    """load_manifest 后的 Manifest 可以序列化（间接）。"""
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    # documents/expected_failures 是空 tuple → json.dumps 会转为 []
    text = json.dumps({"documents": list(m.documents), "expected_failures": list(m.expected_failures)})
    parsed = json.loads(text)
    assert parsed == {"documents": [], "expected_failures": []}


def test_e2e_load_manifest_with_categories_for_aggregation_batch12(tmp_path):
    """manifest 含 categories → load 后 Manifest.categories_covered 工作。"""
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["z", "a"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["m"]},
        ],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    assert m.categories_covered == ["a", "m", "z"]
    assert m.file_count == 2
    assert m.pdf_count == 2
    assert m.docx_count == 0


def test_e2e_load_manifest_with_paired_docs_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "pdf1",
                "path": "a.pdf",
                "source_type": "pdf",
                "paired_with": "docx1",
            },
            {
                "doc_id": "docx1",
                "path": "a.docx",
                "source_type": "docx",
                "paired_with": "pdf1",
            },
        ],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    assert m.content_group_count == 1  # 1 对
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_e2e_load_manifest_idempotent_batch12(tmp_path):
    """两次 load 同一 manifest 结果相等。"""
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m1 = load_manifest(manifest, project_root=tmp_path)
    m2 = load_manifest(manifest, project_root=tmp_path)
    assert m1 == m2


def test_e2e_load_manifest_no_project_root_uses_default_batch12(tmp_path):
    """project_root=None → 自动检测（找 pyproject.toml）。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest)  # 不传 project_root
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_with_annotation_file_batch12(tmp_path):
    """带 annotation_file 的 document → annotation_resolved 被填充。"""
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a.pdf",
                "source_type": "pdf",
                "annotation_file": "ann.json",
            }
        ],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "ann.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "ann.json").resolve()


def test_e2e_load_manifest_with_expectations_batch12(tmp_path):
    """带 expectations 的 document。"""
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a.pdf",
                "source_type": "pdf",
                "expectations": {"element_count_by_type": {"paragraph": 10}},
            }
        ],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 10}}


def test_e2e_load_manifest_with_sha256_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    sha = "a" * 64  # 合法 sha256 hex
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a.pdf",
                "source_type": "pdf",
                "sha256": sha,
            }
        ],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    assert m.documents[0].sha256 == sha


def test_e2e_load_manifest_returns_correct_devset_status_batch12(tmp_path):
    manifest = tmp_path / "m.json"
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    m = load_manifest(manifest, project_root=tmp_path)
    assert m.devset_status == "complete"
