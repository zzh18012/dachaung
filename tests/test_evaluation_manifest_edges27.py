r"""evaluation/manifest.py 第二十七轮 edges 测试（Round 325）。

重点补强 edges26 未触及的角度：
- _is_absolute_like 行为深度补强（更多边界 case）
- _has_backslash 行为深度补强
- _resolve_relative_path 行为深度补强
- _detect_project_root 行为深度补强
- ManifestError 行为深度补强
- DocumentEntry/ExpectedFailure/Manifest frozen 补强
- Manifest properties 行为深度补强（content_group_count 算法分支）
- load_manifest 行为深度补强
- module source forbidden tokens 第二批
- module source 字符串精确补强
- signatures 精确补强
- 端到端集成补强
- 模块整体合理性
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, is_dataclass
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


# ---------- _is_absolute_like 行为深度补强 ----------


def test_is_absolute_like_letter_drive_lowercase():
    """小写盘符 c:/ 也算绝对路径。"""
    assert _is_absolute_like("c:/x") is True


def test_is_absolute_like_letter_drive_uppercase():
    assert _is_absolute_like("C:/x") is True


def test_is_absolute_like_letter_drive_z_backslash():
    assert _is_absolute_like("Z:\\x") is True


def test_is_absolute_like_single_letter_not_absolute():
    """单字符 'a' 不是绝对路径（len < 3）。"""
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_letters_not_absolute():
    """两字符 'ab' 不是绝对路径（len < 3）。"""
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_three_letters_without_colon():
    """三字符但无 colon 不是绝对路径。"""
    assert _is_absolute_like("abc") is False


def test_is_absolute_like_letter_colon_no_slash():
    """C: 但无后续斜杠不是绝对路径（Windows 当前目录相对路径）。"""
    assert _is_absolute_like("C:x") is False


def test_is_absolute_like_letter_colon_only():
    """C: 不是绝对路径。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_just_colon():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_just_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_just_backslash():
    r"""单独反斜杠不算（POSIX 上 \ 是文件名一部分）。"""
    assert _is_absolute_like("\\") is False


def test_is_absolute_like_unc_path():
    """UNC \\\\server 不是绝对路径（_is_absolute_like 不识别 UNC）。"""
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_two_slashes():
    """//foo 是 POSIX 绝对（startswith "/"）。"""
    assert _is_absolute_like("//foo") is True


def test_is_absolute_like_relative_subpath():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_dot_path():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_dotdot_path():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_tilde_path():
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_underscore_drive_not_absolute():
    """_:/ 不算（盘符必须是字母）。"""
    assert _is_absolute_like("_:/x") is False


def test_is_absolute_like_digit_drive_not_absolute():
    """1:/ 不算（盘符必须是字母）。"""
    assert _is_absolute_like("1:/x") is False


def test_is_absolute_like_4_chars_with_drive():
    """ABCD 不是绝对（无 colon）。"""
    assert _is_absolute_like("ABCD") is False


def test_is_absolute_like_path_with_only_drive_letter_and_slash():
    """C:/ 是绝对路径（虽然无文件名）。"""
    assert _is_absolute_like("C:/") is True


# ---------- _has_backslash 行为深度补强 ----------


def test_has_backslash_single():
    assert _has_backslash("\\") is True


def test_has_backslash_in_middle():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_at_start():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end():
    assert _has_backslash("foo\\") is True


def test_has_backslash_only_forward_slash():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_mixed():
    assert _has_backslash("foo\\bar/baz") is True


def test_has_backslash_multiple():
    assert _has_backslash("a\\b\\c") is True


# ---------- _resolve_relative_path 行为深度补强 ----------


def test_resolve_relative_path_normal(tmp_path):
    out = _resolve_relative_path("foo/bar.txt", tmp_path, "test")
    assert out == (tmp_path / "foo" / "bar.txt").resolve()


def test_resolve_relative_path_with_dot(tmp_path):
    out = _resolve_relative_path("foo/./bar.txt", tmp_path, "test")
    # . 会被 resolve 规整掉
    assert out == (tmp_path / "foo" / "bar.txt").resolve()


def test_resolve_relative_path_double_dot_inside(tmp_path):
    """foo/../bar.txt → 项目根内 bar.txt（合法）。"""
    # 先在 tmp_path 内创建 foo 目录避免 case 失败
    (tmp_path / "foo").mkdir(exist_ok=True)
    out = _resolve_relative_path("foo/../bar.txt", tmp_path, "test")
    assert out == (tmp_path / "bar.txt").resolve()


def test_resolve_relative_path_triple_dot_outside(tmp_path):
    """../../../etc/passwd → 在项目根之外 → ManifestError。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../../../etc/passwd", tmp_path, "test")
    assert "项目根目录之外" in str(ei.value)


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "test")
    assert "为空" in str(ei.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "test")
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_absolute_windows_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("C:/foo", tmp_path, "test")
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("foo\\bar", tmp_path, "test")
    assert "正斜杠" in str(ei.value)
    assert "反斜杠" in str(ei.value)


def test_resolve_relative_path_field_name_in_message(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "documents[xyz].path")
    assert "documents[xyz].path" in str(ei.value)


def test_resolve_relative_path_returns_path_object(tmp_path):
    out = _resolve_relative_path("foo", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_returns_absolute_path(tmp_path):
    out = _resolve_relative_path("foo", tmp_path, "test")
    assert out.is_absolute()


# ---------- _detect_project_root 行为深度补强 ----------


def test_detect_project_root_with_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    p = nested / "manifest.json"
    p.write_text("{}", encoding="utf-8")
    out = _detect_project_root(p)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_parent(tmp_path):
    """无 pyproject.toml 时返回最近父目录（start.parent）。"""
    p = tmp_path / "manifest.json"
    p.write_text("{}", encoding="utf-8")
    out = _detect_project_root(p)
    # 返回 cur（即 start.parent），不是 tmp_path 本身
    assert out == (tmp_path).resolve()


def test_detect_project_root_with_path_object(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_already_dir(tmp_path):
    """传入目录 → cur = dir 本身。"""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_finds_nearest_in_tree(tmp_path):
    """从深层目录向上找最近的 pyproject.toml。"""
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"
    root1.mkdir()
    root2.mkdir()
    (root1 / "pyproject.toml").write_text("[a]\n", encoding="utf-8")
    (root2 / "pyproject.toml").write_text("[b]\n", encoding="utf-8")
    nested = root2 / "deep" / "sub"
    nested.mkdir(parents=True)
    out = _detect_project_root(nested / "manifest.json")
    assert out == root2.resolve()


# ---------- ManifestError 行为深度补强 ----------


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised():
    with pytest.raises(ManifestError):
        raise ManifestError("test")


def test_manifest_error_can_be_caught_as_exception():
    try:
        raise ManifestError("x")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_message_attribute():
    err = ManifestError("hello")
    assert err.args == ("hello",)


def test_manifest_error_str():
    err = ManifestError("hello")
    assert str(err) == "hello"


def test_manifest_error_with_unicode():
    err = ManifestError("失败原因")
    assert "失败原因" in str(err)


def test_manifest_error_with_special_chars():
    err = ManifestError('error: "x" @ [path]')
    assert '"' in str(err)
    assert "@" in str(err)


def test_manifest_error_no_extra_attributes():
    """ManifestError 不存额外数据（除了 Exception 自带 args）。"""
    err = ManifestError("x")
    assert not hasattr(err, "errors")
    assert not hasattr(err, "details")


def test_manifest_error_source_class_signature():
    """ManifestError 仅继承 Exception，无 __init__ 自定义。"""
    # inspect.signature 对 builtin 失败；改为检查 __init__ 是继承的
    assert "message" not in ManifestError.__dict__
    assert "__init__" not in ManifestError.__dict__
    # 直接继承 Exception
    assert ManifestError.__init__ is Exception.__init__


# ---------- DocumentEntry frozen 补强 ----------


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen():
    """frozen=True → setattr 触发 FrozenInstanceError。"""
    entry = DocumentEntry(
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
        entry.doc_id = "y"  # type: ignore[misc]


def test_document_entry_has_10_fields():
    """DocumentEntry 有 10 个字段。"""
    sig = inspect.signature(DocumentEntry)
    assert len(sig.parameters) == 10
    expected = {
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    }
    assert set(sig.parameters) == expected


def test_document_entry_field_types():
    sig = inspect.signature(DocumentEntry)
    assert sig.parameters["doc_id"].annotation == "str"
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.parameters["resolved_path"].annotation == "Path"
    assert sig.parameters["source_type"].annotation == "str"
    assert sig.parameters["sha256"].annotation == "str | None"
    assert sig.parameters["categories"].annotation == "tuple[str, ...]"
    assert sig.parameters["paired_with"].annotation == "str | None"
    assert sig.parameters["annotation_file_str"].annotation == "str | None"
    assert sig.parameters["annotation_resolved"].annotation == "Path | None"
    assert sig.parameters["expectations"].annotation == "dict[str, Any] | None"


def test_document_entry_equality():
    e1 = DocumentEntry(
        doc_id="x", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="x", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert e1 == e2


def test_document_entry_inequality():
    e1 = DocumentEntry(
        doc_id="x", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="y", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert e1 != e2


# ---------- ExpectedFailure frozen 补强 ----------


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen():
    ef = ExpectedFailure(
        doc_id="x",
        path_str="x.txt",
        resolved_path=Path("/tmp/x.txt"),
        expected_error_code="bad",
        source_type="txt",
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "y"  # type: ignore[misc]


def test_expected_failure_has_5_fields():
    sig = inspect.signature(ExpectedFailure)
    assert len(sig.parameters) == 5
    expected = {
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    }
    assert set(sig.parameters) == expected


def test_expected_failure_field_types():
    sig = inspect.signature(ExpectedFailure)
    assert sig.parameters["doc_id"].annotation == "str"
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.parameters["resolved_path"].annotation == "Path"
    assert sig.parameters["expected_error_code"].annotation == "str"
    assert sig.parameters["source_type"].annotation == "str | None"


# ---------- Manifest frozen 补强 ----------


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_is_frozen():
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(FrozenInstanceError):
        mf.devset_status = "complete"  # type: ignore[misc]


def test_manifest_has_5_init_fields():
    sig = inspect.signature(Manifest)
    init_params = [p for p in sig.parameters if p != "self"]
    assert set(init_params) == {
        "manifest_version", "devset_status",
        "documents", "expected_failures", "project_root",
    }


def test_manifest_field_types():
    sig = inspect.signature(Manifest)
    assert sig.parameters["manifest_version"].annotation == "str"
    assert sig.parameters["devset_status"].annotation == "str"
    assert sig.parameters["documents"].annotation == "tuple[DocumentEntry, ...]"
    assert sig.parameters["expected_failures"].annotation == "tuple[ExpectedFailure, ...]"
    assert sig.parameters["project_root"].annotation == "Path"


def test_manifest_has_4_properties():
    """file_count, pdf_count, docx_count, content_group_count + categories_covered = 5 properties。"""
    properties = [
        n for n in dir(Manifest)
        if isinstance(getattr(Manifest, n, None), property)
    ]
    assert set(properties) == {
        "file_count", "pdf_count", "docx_count",
        "content_group_count", "categories_covered",
    }


# ---------- Manifest properties 行为深度补强 ----------


def _make_doc(doc_id, source_type="pdf", categories=(), paired_with=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"{doc_id}.pdf",
        resolved_path=Path(f"/tmp/{doc_id}.pdf"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def test_manifest_file_count_returns_0_for_empty():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.file_count == 0


def test_manifest_pdf_count_filters():
    docs = (_make_doc("a", "pdf"), _make_doc("b", "docx"), _make_doc("c", "pdf"))
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.pdf_count == 2
    assert mf.docx_count == 1


def test_manifest_categories_covered_sorted():
    docs = (
        _make_doc("a", categories=("z", "a")),
        _make_doc("b", categories=("m",)),
        _make_doc("c", categories=("a", "k")),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == ["a", "k", "m", "z"]


def test_manifest_categories_covered_dedup():
    docs = (
        _make_doc("a", categories=("x", "y")),
        _make_doc("b", categories=("x",)),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.categories_covered == ["x", "y"]


def test_manifest_content_group_count_all_unpaired():
    docs = (_make_doc("a"), _make_doc("b"), _make_doc("c"))
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 3


def test_manifest_content_group_count_one_pair():
    docs = (
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="a"),
        _make_doc("c"),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # a-b 1 组 + c 1 组 = 2
    assert mf.content_group_count == 2


def test_manifest_content_group_count_only_paired():
    docs = (
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="a"),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 1


def test_manifest_content_group_count_unidirectional_pair():
    """单向 paired_with：a→b 但 b 不指向 a。"""
    docs = (
        _make_doc("a", paired_with="b"),
        _make_doc("b"),  # b 不指向 a
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset([a,b]) → 1 组；seen={a,b}；b 在 seen 里 → unpaired=0
    # 但代码 if d.doc_id not in seen and not d.paired_with：a 有 paired_with → skip；b 在 seen → skip
    # groups=1, unpaired=0 → total=1
    assert mf.content_group_count == 1


def test_manifest_content_group_count_two_disjoint_pairs():
    docs = (
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="a"),
        _make_doc("c", paired_with="d"),
        _make_doc("d", paired_with="c"),
    )
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert mf.content_group_count == 2


def test_manifest_content_group_count_self_pair_ignored():
    """self-pair（a→a）应该被 frozenset 去重为单元素。"""
    docs = (_make_doc("a", paired_with="a"),)
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset([a,a]) = {a}；seen={a}；a 有 paired_with → skip
    # groups=1, unpaired=0 → total=1
    assert mf.content_group_count == 1


def test_manifest_properties_int_return_types():
    """properties 返回 int。"""
    docs = (_make_doc("a"),)
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.file_count, int)
    assert isinstance(mf.pdf_count, int)
    assert isinstance(mf.docx_count, int)
    assert isinstance(mf.content_group_count, int)


def test_manifest_categories_covered_returns_list():
    mf = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(mf.categories_covered, list)


# ---------- load_manifest 行为深度补强 ----------


def test_load_manifest_missing_file_raises(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path / "no.json")
    assert "清单文件不存在" in str(ei.value)


def test_load_manifest_invalid_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "JSON 解析失败" in str(ei.value)


def test_load_manifest_str_path(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # str path + project_root
    mf = load_manifest(str(p), project_root=str(tmp_path))
    assert mf.manifest_version == "1.0"


def test_load_manifest_default_project_root_detection(tmp_path):
    """无 project_root 时调用 _detect_project_root。"""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    mf = load_manifest(p)
    assert mf.project_root == tmp_path.resolve()


def test_load_manifest_with_categories(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "x",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "categories": ["tests", "pilot"],
            }
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].categories == ("tests", "pilot")


def test_load_manifest_with_paired_with(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "y.docx").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf", "paired_with": "y"},
            {"doc_id": "y", "path": "samples/y.docx", "source_type": "docx", "paired_with": "x"},
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].paired_with == "y"
    assert mf.documents[1].paired_with == "x"


def test_load_manifest_with_sha256(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "x",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].sha256 == "a" * 64


def test_load_manifest_with_expectations(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "x",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "expectations": {
                    "element_count_by_type": {"paragraph": 5, "heading": 1},
                },
            }
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].expectations == {"element_count_by_type": {"paragraph": 5, "heading": 1}}


def test_load_manifest_with_annotation_file(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "x.anno.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "x",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "annotation_file": "samples/x.anno.json",
            }
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].annotation_file_str == "samples/x.anno.json"
    assert mf.documents[0].annotation_resolved == (tmp_path / "samples" / "x.anno.json").resolve()


def test_load_manifest_with_expected_failures_source_type(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.txt").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "x",
                "path": "samples/x.txt",
                "expected_error_code": "unsupported_format",
                "source_type": "txt",
            }
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.expected_failures[0].source_type == "txt"


def test_load_manifest_returns_manifest_instance(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert isinstance(mf, Manifest)


def test_load_manifest_invalid_path_form_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "/etc/passwd", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_path_outside_project_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "../../etc/passwd", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(ei.value)


def test_load_manifest_path_with_backslash_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "foo\\bar.pdf", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(ei.value)


# ---------- module source forbidden tokens 第二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import copy",
        "import pprint",
        "import csv",
        "import xml",
        "import configparser",
        "import argparse",
        "import inspect",
        "import dis",
        "import traceback",
        "import warnings",
        "import weakref",
        "import gc",
        "import struct",
        "import codecs",
        "import unicodedata",
        "import string",
        "import textwrap",
        "import difflib",
        "import decimal",
        "import fractions",
        "import statistics",
        "import array",
        "import queue",
        "import types",
        "import math",
        "import collections.abc",
        "import abc",
        "import re",
        "import hashlib",
        "import secrets",
        "import uuid",
        "import time",
        "import sys",
    ],
)
def test_module_source_forbidden_tokens_second_batch(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_has_dataclass_import():
    src = inspect.getsource(m)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_evaluation_manifest_version():
    src = inspect.getsource(m)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_schema_validate():
    src = inspect.getsource(m)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_class_manifest_error():
    src = inspect.getsource(m)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_docstring_mentions_relative():
    src = inspect.getsource(m)
    assert "相对路径" in src or "relative" in src.lower()


def test_module_source_has_docstring_mentions_absolute():
    src = inspect.getsource(m)
    assert "绝对路径" in src or "absolute" in src.lower()


def test_module_source_has_docstring_mentions_backslash():
    src = inspect.getsource(m)
    assert "反斜杠" in src or "backslash" in src.lower()


def test_module_source_has_docstring_mentions_project_root():
    src = inspect.getsource(m)
    assert "项目根" in src


def test_module_source_no_yield():
    src = inspect.getsource(m)
    assert "yield" not in src


def test_module_source_no_global():
    src = inspect.getsource(m)
    assert "\nglobal " not in src


def test_module_source_no_async():
    src = inspect.getsource(m)
    assert "async def" not in src


def test_module_source_no_lambda():
    """lambda 仅在 sum/m sorted 中可能用；这里全 module 不应有 lambda。"""
    src = inspect.getsource(m)
    # 但 property pdf_count 等用 generator expression（不是 lambda）
    # 简单 verify 没 lambda 关键字
    assert "lambda" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_no_decorators_other_than_dataclass_and_property():
    """装饰器只允许 @dataclass(frozen=True) 和 @property。"""
    src = inspect.getsource(m)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            assert stripped in ("@dataclass(frozen=True)", "@property"), \
                f"Unexpected decorator: {stripped}"


def test_module_source_has_3_dataclass_decorators():
    src = inspect.getsource(m)
    assert src.count("@dataclass(frozen=True)") == 3


# ---------- signatures 精确补强 ----------


def test_is_absolute_like_signature():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters) == ["path_str"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_has_backslash_signature():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters) == ["path_str"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_resolve_relative_path_signature():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters) == ["path_str", "project_root", "field_name"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.parameters["project_root"].annotation == "Path"
    assert sig.parameters["field_name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_detect_project_root_signature():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters) == ["start"]
    assert sig.parameters["start"].annotation == "Path"
    assert sig.return_annotation == "Path"


def test_load_manifest_signature():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters)
    assert params == ["manifest_path", "project_root"]
    assert sig.parameters["manifest_path"].annotation == "Path | str"
    assert sig.parameters["project_root"].annotation == "Path | str | None"
    assert sig.parameters["project_root"].default is None


def test_load_manifest_return_annotation():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_no_varargs_varkw_in_helpers():
    """5 个 module-level 函数都不带 *args / **kwargs。"""
    for fn in (
        _is_absolute_like,
        _has_backslash,
        _resolve_relative_path,
        _detect_project_root,
        load_manifest,
    ):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )


def test_namespace_is_absolute_like():
    assert _is_absolute_like.__module__ == "evaluation.manifest"


def test_namespace_has_backslash():
    assert _has_backslash.__module__ == "evaluation.manifest"


def test_namespace_resolve_relative_path():
    assert _resolve_relative_path.__module__ == "evaluation.manifest"


def test_namespace_detect_project_root():
    assert _detect_project_root.__module__ == "evaluation.manifest"


def test_namespace_load_manifest():
    assert load_manifest.__module__ == "evaluation.manifest"


def test_namespace_manifest_error():
    assert ManifestError.__module__ == "evaluation.manifest"


def test_namespace_manifest():
    assert Manifest.__module__ == "evaluation.manifest"


def test_namespace_document_entry():
    assert DocumentEntry.__module__ == "evaluation.manifest"


def test_namespace_expected_failure():
    assert ExpectedFailure.__module__ == "evaluation.manifest"


# ---------- 模块整体合理性 ----------


def test_module_all_5_entries():
    assert m.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_is_list():
    assert isinstance(m.__all__, list)


def test_module_namespace():
    assert m.__name__ == "evaluation.manifest"


def test_module_has_4_classes():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and getattr(m, n).__module__ == "evaluation.manifest"
    ]
    assert set(classes) == {
        "ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure",
    }


def test_module_has_3_dataclasses():
    dcs = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and is_dataclass(getattr(m, n))
        and getattr(m, n).__module__ == "evaluation.manifest"
    ]
    assert set(dcs) == {"Manifest", "DocumentEntry", "ExpectedFailure"}


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
        "_is_absolute_like", "_has_backslash",
        "_resolve_relative_path", "_detect_project_root",
    }


def test_module_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


# ---------- 端到端集成补强 ----------


def test_e2e_full_manifest_with_all_features(tmp_path):
    """完整 manifest：3 documents (含 paired) + 1 expected_failure。"""
    samples = tmp_path / "samples"
    samples.mkdir()
    (samples / "x.pdf").write_text("", encoding="utf-8")
    (samples / "y.docx").write_text("", encoding="utf-8")
    (samples / "z.pdf").write_text("", encoding="utf-8")
    (samples / "bad.txt").write_text("", encoding="utf-8")

    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "samples/x.pdf", "source_type": "pdf",
             "categories": ["pilot"], "paired_with": "y"},
            {"doc_id": "y", "path": "samples/y.docx", "source_type": "docx",
             "categories": ["pilot"], "paired_with": "x"},
            {"doc_id": "z", "path": "samples/z.pdf", "source_type": "pdf",
             "categories": ["tests"]},
        ],
        "expected_failures": [
            {"doc_id": "bad", "path": "samples/bad.txt",
             "expected_error_code": "unsupported_format", "source_type": "txt"},
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.file_count == 3
    assert mf.pdf_count == 2
    assert mf.docx_count == 1
    assert mf.content_group_count == 2  # x-y pair + z
    assert mf.categories_covered == ["pilot", "tests"]
    assert len(mf.expected_failures) == 1


def test_e2e_manifest_with_3_pdf_only(tmp_path):
    samples = tmp_path / "s"
    samples.mkdir()
    for n in ("a", "b", "c"):
        (samples / f"{n}.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": n, "path": f"s/{n}.pdf", "source_type": "pdf"}
            for n in ("a", "b", "c")
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.pdf_count == 3
    assert mf.docx_count == 0
    assert mf.devset_status == "complete"


def test_e2e_manifest_with_nested_paths(tmp_path):
    """深层路径（多级目录）。"""
    (tmp_path / "a" / "b" / "c").mkdir(parents=True)
    (tmp_path / "a" / "b" / "c" / "x.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "a/b/c/x.pdf", "source_type": "pdf"}
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].resolved_path == (tmp_path / "a" / "b" / "c" / "x.pdf").resolve()


def test_e2e_manifest_categories_default_empty(tmp_path):
    (tmp_path / "x.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "x.pdf", "source_type": "pdf"}
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].categories == ()
    assert mf.categories_covered == []


def test_e2e_manifest_path_resolved_correctly(tmp_path):
    (tmp_path / "x.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "x", "path": "x.pdf", "source_type": "pdf"}
        ],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.documents[0].resolved_path.is_absolute()
    assert mf.documents[0].resolved_path == (tmp_path / "x.pdf").resolve()


def test_e2e_manifest_no_expected_failures_default_empty(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    mf = load_manifest(p, project_root=tmp_path)
    assert mf.expected_failures == ()


def test_e2e_manifest_documents_is_tuple():
    """Manifest.documents 是 tuple 不是 list。"""
    p = Path(__file__).parent / "_test_data.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    try:
        mf = load_manifest(p)
        assert isinstance(mf.documents, tuple)
        assert isinstance(mf.expected_failures, tuple)
    finally:
        p.unlink()
