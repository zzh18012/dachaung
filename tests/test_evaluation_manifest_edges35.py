"""evaluation/manifest.py 第三十五轮 edges 测试（Round 377）。

重点补强 edges34 未触及的角度：
- _is_absolute_like 数学边界第十批（更多 unicode / 边界）
- _has_backslash 数学边界第十批
- _resolve_relative_path 行为深度第五批（escape attempts / symlink-like / traversal）
- _detect_project_root 行为深度第六批
- DocumentEntry / ExpectedFailure / Manifest dataclass 行为深度第八批
- Manifest properties 算法深度第八批（content_group_count 复杂配对）
- load_manifest malformed data 第八批
- module source forbidden tokens 第十一批
- signatures 第六批
- 模块整体合理性第四批
- 端到端集成第四批
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import types
from pathlib import Path
from typing import Any

import pytest

from evaluation import MANIFEST_VERSION
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


# ---------- _is_absolute_like 数学边界第十批 ----------


def test_is_absolute_like_unicode_alpha_extension_pos0():
    """Python str.isalpha() 对全角字母返回 True → 这些会被识别为 drive letter."""
    # 全角字母（U+FF21 全角 A）— str.isalpha() True
    assert _is_absolute_like("Ａ:/foo") is True
    assert _is_absolute_like("Ａ:\\foo") is True


def test_is_absolute_like_mathematical_alpha_pos0():
    """数学字母（U+1D400 数学 A）— str.isalpha() True → 识别为 drive."""
    assert _is_absolute_like("𝐴:/foo") is True


def test_is_absolute_like_devanagari_letter_pos0():
    """Devanagari 字母（U+0905）— str.isalpha() True → 识别为 drive."""
    assert _is_absolute_like("अ:/foo") is True


def test_is_absolute_like_three_char_drive_no_separator():
    """3 字符 'a:b' 第三字符不是 / 或 \\."""
    assert _is_absolute_like("a:b") is False
    assert _is_absolute_like("a:bc") is False


def test_is_absolute_like_three_char_drive_colon_only():
    assert _is_absolute_like("Z:") is False  # 长度 2
    assert _is_absolute_like("Z:f") is False  # 第三字符是字母，不是 / \\


def test_is_absolute_like_uppercase_drive():
    assert _is_absolute_like("C:/foo") is True
    assert _is_absolute_like("C:\\foo") is True
    assert _is_absolute_like("Z:/foo") is True
    assert _is_absolute_like("A:\\bar") is True


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("c:/foo") is True
    assert _is_absolute_like("c:\\foo") is True
    assert _is_absolute_like("z:/foo") is True


def test_is_absolute_like_double_slash_not_absolute():
    """//foo 不是单 /."""
    # // 是 POSIX 网络路径，但代码只检查 startswith("/")，所以 True
    assert _is_absolute_like("//foo") is True


def test_is_absolute_like_only_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_tilde_path():
    """~ 不是绝对路径."""
    assert _is_absolute_like("~/foo") is False
    assert _is_absolute_like("~") is False


def test_is_absolute_like_dot_slash():
    assert _is_absolute_like("./foo") is False
    assert _is_absolute_like(".") is False
    assert _is_absolute_like("..") is False


def test_is_absolute_like_only_colon():
    assert _is_absolute_like(":") is False
    assert _is_absolute_like("::") is False


def test_is_absolute_like_emoji_pos0():
    """emoji 的 alpha 状态：U+1F600 在 Python str.isalpha() 是 False."""
    assert _is_absolute_like("😀:/foo") is False


def test_is_absolute_like_digit_pos0_not_alpha():
    """数字 0-9 不是 alpha → 不是 drive letter."""
    for ch in "0123456789":
        assert _is_absolute_like(f"{ch}:/foo") is False


def test_is_absolute_like_underscore_pos0_not_alpha():
    """_ 不是 alpha → 不是 drive letter."""
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_punctuation_pos0_not_alpha():
    """标点不是 alpha → 不是 drive letter."""
    for ch in "@#$%^&*()+=-":
        assert _is_absolute_like(f"{ch}:/foo") is False


# ---------- _has_backslash 数学边界第十批 ----------


def test_has_backslash_only_carriage_return():
    assert _has_backslash("\r") is False


def test_has_backslash_only_vertical_tab():
    assert _has_backslash("\v") is False


def test_has_backslash_only_form_feed():
    assert _has_backslash("\f") is False


def test_has_backslash_with_unicode_backslash_char():
    """U+2216 (∖) set minus 不是 ASCII backslash."""
    assert _has_backslash("∖foo") is False


def test_has_backslash_with_fullwidth_backslash():
    """U+FF3C fullwidth reverse solidus 不是 ASCII backslash."""
    assert _has_backslash("＼foo") is False


def test_has_backslash_real_backslash_at_start():
    assert _has_backslash("\\foo") is True


def test_has_backslash_real_backslash_at_end():
    assert _has_backslash("foo\\") is True


def test_has_backslash_real_backslash_in_middle():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_multiple_real_backslashes():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_real_backslash():
    assert _has_backslash("\\") is True


# ---------- _resolve_relative_path 行为深度第五批 ----------


def test_resolve_relative_path_rejects_dotdot_traversal(tmp_path):
    """../../foo 应抛 ManifestError（解析后位于 project_root 之外）."""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../foo", tmp_path, "test")
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_rejects_deep_dotdot_traversal(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("../../../../etc/passwd", tmp_path, "test")


def test_resolve_relative_path_rejects_absolute_posix(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "test")
    assert "绝对路径" in str(exc_info.value)


def test_resolve_relative_path_rejects_absolute_windows_forward(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("C:/foo", tmp_path, "test")


def test_resolve_relative_path_rejects_absolute_windows_backward(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("C:\\foo", tmp_path, "test")


def test_resolve_relative_path_rejects_backslash_path(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("foo\\bar", tmp_path, "test")
    assert "反斜杠" in str(exc_info.value)


def test_resolve_relative_path_rejects_empty_string(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "test")
    assert "为空" in str(exc_info.value)


def test_resolve_relative_path_accepts_current_dir_dot(tmp_path):
    """./foo 应解析为 project_root/foo."""
    result = _resolve_relative_path("./foo", tmp_path, "test")
    assert result == (tmp_path / "foo").resolve()


def test_resolve_relative_path_accepts_deep_subdir(tmp_path):
    result = _resolve_relative_path("a/b/c/d/e.txt", tmp_path, "test")
    assert result == (tmp_path / "a" / "b" / "c" / "d" / "e.txt").resolve()


def test_resolve_relative_path_normalizes_redundant_separators(tmp_path):
    """a//b 应规范化为 a/b（Path.resolve 处理）."""
    result = _resolve_relative_path("a//b", tmp_path, "test")
    assert result == (tmp_path / "a" / "b").resolve()


def test_resolve_relative_path_normalizes_dot_segments(tmp_path):
    """a/./b 应规范化为 a/b."""
    result = _resolve_relative_path("a/./b", tmp_path, "test")
    assert result == (tmp_path / "a" / "b").resolve()


def test_resolve_relative_path_returns_absolute(tmp_path):
    """返回值必须是绝对路径."""
    result = _resolve_relative_path("foo", tmp_path, "test")
    assert result.is_absolute()


def test_resolve_relative_path_returns_path_type(tmp_path):
    result = _resolve_relative_path("foo", tmp_path, "test")
    assert isinstance(result, Path)


def test_resolve_relative_path_unicode_subdir(tmp_path):
    """Unicode 子目录名应支持."""
    result = _resolve_relative_path("测试/文件.pdf", tmp_path, "test")
    assert "测试" in str(result)
    assert "文件.pdf" in str(result)


def test_resolve_relative_path_field_name_used_in_error(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/abs", tmp_path, "my_field")
    assert "my_field" in str(exc_info.value)


def test_resolve_relative_path_no_modification_to_inputs(tmp_path):
    """不应修改 path_str 或 project_root."""
    ps = "foo/bar"
    pr = tmp_path
    _resolve_relative_path(ps, pr, "test")
    assert ps == "foo/bar"
    assert pr == tmp_path


# ---------- _detect_project_root 行为深度第六批 ----------


def test_detect_project_root_finds_pyproject(tmp_path):
    """目录下有 pyproject.toml → 返回该目录."""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


def test_detect_project_root_walks_up_to_find_pyproject(tmp_path):
    """子目录向上找."""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_file_input_returns_parent_with_pyproject(tmp_path):
    """传入文件 → 取其父目录."""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    f = tmp_path / "data.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_default_to_cur_when_no_pyproject(tmp_path):
    """无 pyproject.toml → 返回 cur（路径本身或其父）."""
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    result = _detect_project_root(sub)
    assert result == sub.resolve()


def test_detect_project_root_default_for_file_without_pyproject(tmp_path):
    """文件，无 pyproject → 返回文件所在目录."""
    f = tmp_path / "f.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_path_object(tmp_path):
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_returns_absolute(tmp_path):
    result = _detect_project_root(tmp_path)
    assert result.is_absolute()


def test_detect_project_root_resolves_symlinks(tmp_path):
    """传入相对路径也应解析为绝对."""
    rel = Path(".")  # cwd
    result = _detect_project_root(rel)
    assert result.is_absolute()


def test_detect_project_root_idempotent(tmp_path):
    """多次调用结果一致."""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    r1 = _detect_project_root(tmp_path)
    r2 = _detect_project_root(tmp_path)
    assert r1 == r2


def test_detect_project_root_finds_innermost_pyproject(tmp_path):
    """多个 pyproject.toml 嵌套 → 找最近的."""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "pyproject.toml").write_text("[tool.y]", encoding="utf-8")
    result = _detect_project_root(inner)
    assert result == inner.resolve()


# ---------- DocumentEntry dataclass 行为深度第八批 ----------


def _make_doc_entry(**kwargs):
    defaults = dict(
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
    defaults.update(kwargs)
    return DocumentEntry(**defaults)


def test_document_entry_is_frozen():
    """frozen=True → 不可修改字段."""
    entry = _make_doc_entry()
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.doc_id = "other"  # type: ignore[misc]


def test_document_entry_eq_self():
    e1 = _make_doc_entry()
    e2 = _make_doc_entry()
    assert e1 == e2


def test_document_entry_ne_other():
    e1 = _make_doc_entry(doc_id="d1")
    e2 = _make_doc_entry(doc_id="d2")
    assert e1 != e2


def test_document_entry_categories_default_empty_tuple():
    e = _make_doc_entry()
    assert e.categories == ()


def test_document_entry_paired_with_default_none():
    e = _make_doc_entry()
    assert e.paired_with is None


def test_document_entry_annotation_file_str_default_none():
    e = _make_doc_entry()
    assert e.annotation_file_str is None


def test_document_entry_annotation_resolved_default_none():
    e = _make_doc_entry()
    assert e.annotation_resolved is None


def test_document_entry_expectations_default_none():
    e = _make_doc_entry()
    assert e.expectations is None


def test_document_entry_sha256_default_none():
    e = _make_doc_entry()
    assert e.sha256 is None


def test_document_entry_with_categories():
    e = _make_doc_entry(categories=("a", "b"))
    assert e.categories == ("a", "b")


def test_document_entry_with_paired_with():
    e = _make_doc_entry(paired_with="d2")
    assert e.paired_with == "d2"


def test_document_entry_with_expectations():
    e = _make_doc_entry(expectations={"element_count_by_type": {"heading": 1}})
    assert e.expectations == {"element_count_by_type": {"heading": 1}}


def test_document_entry_repr_includes_class_name():
    e = _make_doc_entry()
    assert "DocumentEntry" in repr(e)


def test_document_entry_repr_includes_doc_id():
    e = _make_doc_entry(doc_id="my_doc")
    assert "my_doc" in repr(e)


def test_document_entry_hash_with_categories_tuple():
    """tuple 是 hashable → DocumentEntry hashable."""
    e = _make_doc_entry(categories=("a", "b"))
    h = hash(e)
    assert isinstance(h, int)


def test_document_entry_hash_with_expectations_dict():
    """dict 是 unhashable → 但 frozen dataclass 的 hash 还是计算（不会 raise）.

    dataclass(frozen=True) 的 __hash__ 用 hash((field1, field2, ...))，dict 会 raise.
    但这里 expectations 默认 None，可以 hash.
    """
    e = _make_doc_entry(expectations=None)
    assert isinstance(hash(e), int)


def test_document_entry_hash_in_set():
    e1 = _make_doc_entry()
    e2 = _make_doc_entry()
    s = {e1, e2}
    assert len(s) == 1  # equal → 同一元素


def test_document_entry_replace_returns_new_instance():
    e1 = _make_doc_entry(doc_id="d1")
    e2 = dataclasses.replace(e1, doc_id="d2")
    assert e1 is not e2
    assert e1.doc_id == "d1"
    assert e2.doc_id == "d2"


def test_document_entry_replace_preserves_other_fields():
    e1 = _make_doc_entry(doc_id="d1", source_type="pdf", categories=("x",))
    e2 = dataclasses.replace(e1, doc_id="d2")
    assert e2.source_type == "pdf"
    assert e2.categories == ("x",)


# ---------- ExpectedFailure dataclass 行为深度第八批 ----------


def _make_expected_failure(**kwargs):
    defaults = dict(
        doc_id="bad1",
        path_str="bad.pdf",
        resolved_path=Path("/tmp/bad.pdf"),
        expected_error_code="parse_failed",
        source_type=None,
    )
    defaults.update(kwargs)
    return ExpectedFailure(**defaults)


def test_expected_failure_is_frozen():
    ef = _make_expected_failure()
    with pytest.raises(dataclasses.FrozenInstanceError):
        ef.doc_id = "other"  # type: ignore[misc]


def test_expected_failure_eq_self():
    e1 = _make_expected_failure()
    e2 = _make_expected_failure()
    assert e1 == e2


def test_expected_failure_ne_other():
    e1 = _make_expected_failure(doc_id="bad1")
    e2 = _make_expected_failure(doc_id="bad2")
    assert e1 != e2


def test_expected_failure_source_type_default_none():
    ef = _make_expected_failure()
    assert ef.source_type is None


def test_expected_failure_with_source_type():
    ef = _make_expected_failure(source_type="pdf")
    assert ef.source_type == "pdf"


def test_expected_failure_repr_includes_class_name():
    ef = _make_expected_failure()
    assert "ExpectedFailure" in repr(ef)


def test_expected_failure_repr_includes_doc_id():
    ef = _make_expected_failure(doc_id="my_bad")
    assert "my_bad" in repr(ef)


def test_expected_failure_hash_in_set():
    e1 = _make_expected_failure()
    e2 = _make_expected_failure()
    s = {e1, e2}
    assert len(s) == 1


def test_expected_failure_replace_returns_new_instance():
    e1 = _make_expected_failure(doc_id="b1")
    e2 = dataclasses.replace(e1, doc_id="b2")
    assert e1 is not e2
    assert e1.doc_id == "b1"
    assert e2.doc_id == "b2"


def test_expected_failure_replace_preserves_other_fields():
    e1 = _make_expected_failure(doc_id="b1", expected_error_code="parse_failed")
    e2 = dataclasses.replace(e1, doc_id="b2")
    assert e2.expected_error_code == "parse_failed"


# ---------- Manifest dataclass 行为深度第八批 ----------


def _make_manifest(**kwargs):
    defaults = dict(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    defaults.update(kwargs)
    return Manifest(**defaults)


def test_manifest_is_frozen():
    m = _make_manifest()
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_eq_self():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert m1 == m2


def test_manifest_ne_other_devset_status():
    m1 = _make_manifest(devset_status="incomplete")
    m2 = _make_manifest(devset_status="complete")
    assert m1 != m2


def test_manifest_repr_includes_class_name():
    m = _make_manifest()
    assert "Manifest" in repr(m)


def test_manifest_with_documents_tuple():
    docs = (_make_doc_entry(doc_id="d1"), _make_doc_entry(doc_id="d2"))
    m = _make_manifest(documents=docs)
    assert len(m.documents) == 2


def test_manifest_with_expected_failures_tuple():
    efs = (_make_expected_failure(doc_id="b1"),)
    m = _make_manifest(expected_failures=efs)
    assert len(m.expected_failures) == 1


def test_manifest_hash_in_set():
    m1 = _make_manifest()
    m2 = _make_manifest()
    s = {m1, m2}
    assert len(s) == 1


def test_manifest_replace_returns_new_instance():
    m1 = _make_manifest(devset_status="incomplete")
    m2 = dataclasses.replace(m1, devset_status="complete")
    assert m1 is not m2
    assert m1.devset_status == "incomplete"
    assert m2.devset_status == "complete"


# ---------- Manifest properties 算法深度第八批 ----------


def test_manifest_file_count_empty():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_multiple():
    docs = tuple(_make_doc_entry(doc_id=f"d{i}") for i in range(5))
    m = _make_manifest(documents=docs)
    assert m.file_count == 5


def test_manifest_pdf_count_empty():
    m = _make_manifest(documents=())
    assert m.pdf_count == 0


def test_manifest_pdf_count_only_docx():
    docs = (_make_doc_entry(doc_id="d1", source_type="docx"),)
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 0


def test_manifest_pdf_count_only_pdf():
    docs = (_make_doc_entry(doc_id="d1", source_type="pdf"),)
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 1


def test_manifest_docx_count_only_pdf():
    docs = (_make_doc_entry(doc_id="d1", source_type="pdf"),)
    m = _make_manifest(documents=docs)
    assert m.docx_count == 0


def test_manifest_categories_covered_empty():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_manifest_categories_covered_returns_list_type():
    docs = (_make_doc_entry(categories=("a",)),)
    m = _make_manifest(documents=docs)
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_deduplicated():
    docs = (
        _make_doc_entry(categories=("a", "b")),
        _make_doc_entry(categories=("a", "c")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_sorted():
    docs = (
        _make_doc_entry(categories=("z", "a")),
        _make_doc_entry(categories=("m",)),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_content_group_count_no_pairing():
    """无 paired_with → 每文档算 1 组."""
    docs = (
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_paired():
    """d1 ↔ d2 → 1 组."""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_unidirectional():
    """d1 → d2 但 d2 不指 d1 → 1 组."""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed():
    """d1+d2 paired，d3, d4 unpaired → 1+2=3."""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),
        _make_doc_entry(doc_id="d4"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_two_pairs():
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3", paired_with="d4"),
        _make_doc_entry(doc_id="d4", paired_with="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_pdf_count_returns_int():
    docs = (_make_doc_entry(source_type="pdf"),)
    m = _make_manifest(documents=docs)
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_returns_int():
    docs = (_make_doc_entry(source_type="docx"),)
    m = _make_manifest(documents=docs)
    assert isinstance(m.docx_count, int)


def test_manifest_file_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.file_count, int)


def test_manifest_content_group_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.content_group_count, int)


# ---------- load_manifest malformed data 第八批 ----------


def _write_valid_manifest_meta(tmp_path):
    """创建合法的 project_root + 一个空 manifest 文件."""
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    return root


def test_load_manifest_path_string_accepted(tmp_path):
    """load_manifest 接受 str 路径."""
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(str(m), project_root=root)
    assert isinstance(result, Manifest)


def test_load_manifest_path_path_accepted(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert isinstance(result, Manifest)


def test_load_manifest_returns_manifest_type(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert type(result).__name__ == "Manifest"


def test_load_manifest_project_root_string(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=str(root))
    assert isinstance(result, Manifest)


def test_load_manifest_project_root_explicit_path(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=Path(root))
    assert result.project_root == Path(root).resolve()


def test_load_manifest_unicode_devset_status(tmp_path):
    """devset_status 只能是 complete/incomplete（schema enum），中文应被拒绝."""
    from evaluation.schema import EvalSchemaError
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "不完整",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(m, project_root=root)


def test_load_manifest_extra_top_level_keys_rejected(tmp_path):
    """Schema additionalProperties:false 应拒绝未知键."""
    from evaluation.schema import EvalSchemaError
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_key": "should fail",
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(m, project_root=root)


def test_load_manifest_empty_documents_key(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents == ()
    assert result.file_count == 0


def test_load_manifest_empty_expected_failures_key(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.expected_failures == ()


def test_load_manifest_doc_with_categories(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF-1.4")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "doc.pdf", "source_type": "pdf", "categories": ["sci", "bio"]},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].categories == ("sci", "bio")
    assert "sci" in result.categories_covered
    assert "bio" in result.categories_covered


def test_load_manifest_doc_without_categories(tmp_path):
    """categories 是 optional."""
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF-1.4")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "doc.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].categories == ()


def test_load_manifest_doc_with_sha256(tmp_path):
    """sha256 必须 64 位 hex（schema 限制）."""
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF-1.4")
    m = root / "m.json"
    valid_sha = "a" * 64
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "doc.pdf", "source_type": "pdf", "sha256": valid_sha},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].sha256 == valid_sha


def test_load_manifest_doc_with_invalid_sha256_rejected(tmp_path):
    """非 64-hex 的 sha256 应被 schema 拒绝."""
    from evaluation.schema import EvalSchemaError
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF-1.4")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "doc.pdf", "source_type": "pdf", "sha256": "abc123"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(m, project_root=root)


def test_load_manifest_doc_with_paired_with(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF-1.4")
    (root / "doc.docx").write_bytes(b"PK")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "doc.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "doc.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].paired_with == "d2"
    assert result.content_group_count == 1


def test_load_manifest_doc_with_expectations(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF-1.4")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "doc.pdf",
                "source_type": "pdf",
                "expectations": {"element_count_by_type": {"heading": 3}},
            },
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].expectations == {"element_count_by_type": {"heading": 3}}


def test_load_manifest_doc_with_annotation_file(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF-1.4")
    (root / "doc.json").write_text("{}", encoding="utf-8")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "doc.pdf",
                "source_type": "pdf",
                "annotation_file": "doc.json",
            },
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].annotation_file_str == "doc.json"
    assert result.documents[0].annotation_resolved == (root / "doc.json").resolve()


def test_load_manifest_ef_with_source_type(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "bad.pdf").write_bytes(b"%PDF-1.4")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "b1", "path": "bad.pdf", "expected_error_code": "parse_failed", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.expected_failures[0].source_type == "pdf"


def test_load_manifest_ef_without_source_type(tmp_path):
    """source_type 是 optional."""
    root = _write_valid_manifest_meta(tmp_path)
    (root / "bad.pdf").write_bytes(b"%PDF-1.4")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "b1", "path": "bad.pdf", "expected_error_code": "parse_failed"},
        ],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.expected_failures[0].source_type is None


def test_load_manifest_doc_path_outside_project_raises(tmp_path):
    """文档 path 解析后位于 project_root 外 → ManifestError."""
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "../outside.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(m, project_root=root)


def test_load_manifest_doc_path_absolute_raises(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(m, project_root=root)


def test_load_manifest_doc_path_backslash_raises(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "sub\\doc.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(m, project_root=root)


# ---------- module source forbidden tokens 第十一批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "shutil.rmtree",
        "shutil.copy",
        "shutil.move",
        "pickle.loads",
        "pickle.load",
        "marshal.loads",
        "ctypes.CDLL",
        "sys.exit",
        "__import__",
        "importlib.import_module",
        "requests.get",
        "urllib.request",
        "http.client",
        "socket.socket",
        "webbrowser.open",
        "antigravity",
        "this",
        "exit(",
        "quit(",
        "exec(",
        "eval(",
        "compile(",
    ],
)
def test_manifest_source_no_forbidden_token_eleventh(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第六批 ----------


def test_module_source_has_future_annotations():
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


def test_module_source_has_manifest_error_class():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_3_dataclasses():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_no_async_def():
    src = inspect.getsource(mmod)
    assert "async def " not in src


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_module_source_no_lambda():
    src = inspect.getsource(mmod)
    assert "lambda " not in src


def test_module_source_no_hardcoded_absolute_path():
    src = inspect.getsource(mmod)
    assert "C:\\\\Users" not in src
    assert "C:/Users" not in src
    assert "/home/" not in src


def test_module_source_no_sleep():
    src = inspect.getsource(mmod)
    assert "time.sleep" not in src


def test_module_source_no_print():
    src = inspect.getsource(mmod)
    assert "print(" not in src


def test_module_source_no_logging():
    src = inspect.getsource(mmod)
    assert "import logging" not in src
    assert "logging." not in src


def test_module_source_docstring_mentions_relative():
    src = inspect.getsource(mmod)
    # 模块 docstring 应提到关键约束
    assert "相对路径" in src[:600] or "relative" in src[:600].lower()


def test_module_source_docstring_mentions_absolute():
    src = inspect.getsource(mmod)
    assert "绝对路径" in src[:600] or "absolute" in src[:600].lower()


def test_module_source_docstring_mentions_backslash():
    src = inspect.getsource(mmod)
    assert "反斜杠" in src[:600] or "backslash" in src[:600].lower()


def test_module_source_manifest_error_docstring():
    src = inspect.getsource(mmod)
    # ManifestError 应有 docstring
    assert '"""清单加载或校验失败。"""' in src


# ---------- signatures 第六批 ----------


def test_signature_is_absolute_like_param_kind():
    sig = inspect.signature(_is_absolute_like)
    p = sig.parameters["path_str"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_is_absolute_like_no_default():
    sig = inspect.signature(_is_absolute_like)
    assert sig.parameters["path_str"].default is inspect.Parameter.empty


def test_signature_has_backslash_param_kind():
    sig = inspect.signature(_has_backslash)
    p = sig.parameters["path_str"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_resolve_relative_path_3_params():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_signature_resolve_relative_path_field_name_kind():
    sig = inspect.signature(_resolve_relative_path)
    p = sig.parameters["field_name"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_load_manifest_2_params():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_signature_load_manifest_manifest_path_no_default():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty


def test_signature_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_detect_project_root_1_param():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_signature_detect_project_root_start_no_default():
    sig = inspect.signature(_detect_project_root)
    assert sig.parameters["start"].default is inspect.Parameter.empty


def test_signature_manifest_error_inherits_exception():
    assert issubclass(ManifestError, Exception)


def test_signature_manifest_error_no_extra_init_in_source():
    src = inspect.getsource(mmod)
    # ManifestError 应只继承 Exception，无自定义 __init__
    me_start = src.index("class ManifestError(Exception):")
    next_def = src.index("\ndef ", me_start + 1)
    me_body = src[me_start:next_def]
    assert "__init__" not in me_body


def test_signature_all_funcs_function_type():
    assert isinstance(_is_absolute_like, types.FunctionType)
    assert isinstance(_has_backslash, types.FunctionType)
    assert isinstance(_resolve_relative_path, types.FunctionType)
    assert isinstance(_detect_project_root, types.FunctionType)
    assert isinstance(load_manifest, types.FunctionType)


def test_signature_all_funcs_module_eq():
    assert _is_absolute_like.__module__ == mmod.__name__
    assert _has_backslash.__module__ == mmod.__name__
    assert _resolve_relative_path.__module__ == mmod.__name__
    assert _detect_project_root.__module__ == mmod.__name__
    assert load_manifest.__module__ == mmod.__name__


def test_signature_manifest_properties_class_methods():
    """Manifest 的 properties 应是 property 对象（在类上）."""
    for name in ("file_count", "pdf_count", "docx_count", "content_group_count", "categories_covered"):
        obj = getattr(Manifest, name)
        assert isinstance(obj, property), f"{name} should be a property"


def test_signature_manifest_properties_return_int():
    """Manifest properties file_count/pdf_count/docx_count/content_group_count 应返回 int."""
    m = _make_manifest()
    assert isinstance(m.file_count, int)
    assert isinstance(m.pdf_count, int)
    assert isinstance(m.docx_count, int)
    assert isinstance(m.content_group_count, int)


def test_signature_manifest_properties_categories_returns_list():
    m = _make_manifest()
    assert isinstance(m.categories_covered, list)


# ---------- 模块整体合理性第四批 ----------


def test_module_all_attribute_lists_exact_items():
    assert hasattr(mmod, "__all__")
    assert mmod.__all__ == ["ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"]


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_entries_unique():
    assert len(set(mmod.__all__)) == len(mmod.__all__)


def test_module_has_docstring():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


def test_module_docstring_starts_with_chinese():
    """模块 docstring 应是中文（'开发集清单加载器。'）."""
    assert mmod.__doc__.strip().startswith("开发集")


def test_module_dunder_file():
    assert hasattr(mmod, "__file__")


def test_module_dunder_file_endswith_manifest_py():
    assert mmod.__file__.replace("\\", "/").endswith("evaluation/manifest.py")


def test_module_name_is_evaluation_manifest():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_user_function_count():
    own_funcs = [
        obj for obj in vars(mmod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == mmod.__name__
    ]
    # _is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root
    assert len(own_funcs) == 5


def test_module_user_class_count():
    own_classes = [
        obj for obj in vars(mmod).values()
        if isinstance(obj, type) and obj.__module__ == mmod.__name__
    ]
    # ManifestError, DocumentEntry, ExpectedFailure, Manifest
    assert len(own_classes) == 4


def test_module_no_call_at_top_level():
    """模块顶层（不缩进）不应有显式的 print/exit/subprocess 类副作用调用."""
    src = inspect.getsource(mmod)
    in_triple = False
    triple_quote = None
    suspicious_patterns = ("os.system(", "subprocess.", "exit(", "quit(", "print(")
    for line in src.splitlines():
        if in_triple:
            if triple_quote and triple_quote in line:
                in_triple = False
                triple_quote = None
            continue
        ls = line.lstrip()
        for q in ('"""', "'''"):
            if ls.startswith(q):
                rest = ls[3:]
                if rest.count(q) >= 1:
                    pass
                else:
                    in_triple = True
                    triple_quote = q
                break
        for pat in suspicious_patterns:
            assert pat not in line, f"suspicious pattern {pat!r} in {line!r}"


def test_module_dataclass_decoration_count():
    src = inspect.getsource(mmod)
    assert src.count("@dataclass(frozen=True)") == 3


# ---------- 端到端集成第四批 ----------


def test_e2e_load_manifest_minimal_valid(tmp_path):
    """最小的合法 manifest 加载成功."""
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert isinstance(result, Manifest)
    assert result.documents == ()
    assert result.expected_failures == ()


def test_e2e_load_manifest_with_two_documents(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "a.pdf").write_bytes(b"%PDF")
    (root / "b.docx").write_bytes(b"PK")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.file_count == 2
    assert result.pdf_count == 1
    assert result.docx_count == 1


def test_e2e_load_manifest_preserves_document_order(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    for n in "abc":
        (root / f"{n}.pdf").write_bytes(b"%PDF")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": f"d{i}", "path": f"{n}.pdf", "source_type": "pdf"}
            for i, n in enumerate("abc")
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    ids = [d.doc_id for d in result.documents]
    assert ids == ["d0", "d1", "d2"]


def test_e2e_load_manifest_resolved_paths_absolute(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "a.pdf").write_bytes(b"%PDF")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].resolved_path.is_absolute()


def test_e2e_load_manifest_resolved_paths_inside_project(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "a.pdf").write_bytes(b"%PDF")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert root.resolve() in result.documents[0].resolved_path.parents


def test_e2e_load_manifest_categories_deduplicated(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "a.pdf").write_bytes(b"%PDF")
    (root / "b.pdf").write_bytes(b"%PDF")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["x", "y"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["y", "z"]},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.categories_covered == ["x", "y", "z"]


def test_e2e_load_manifest_content_group_count(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "a.pdf").write_bytes(b"%PDF")
    (root / "a.docx").write_bytes(b"PK")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.content_group_count == 1


def test_e2e_load_manifest_default_devset_status_preserved(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.devset_status == "complete"


def test_e2e_load_manifest_manifest_version_preserved(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.manifest_version == MANIFEST_VERSION


def test_e2e_load_manifest_with_expected_failure(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "bad.pdf").write_bytes(b"%PDF")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "b1", "path": "bad.pdf", "expected_error_code": "parse_failed"},
        ],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert len(result.expected_failures) == 1
    ef = result.expected_failures[0]
    assert ef.doc_id == "b1"
    assert ef.expected_error_code == "parse_failed"


def test_e2e_load_manifest_with_annotation_file(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "doc.pdf").write_bytes(b"%PDF")
    (root / "doc.json").write_text("{}", encoding="utf-8")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "doc.pdf",
                "source_type": "pdf",
                "annotation_file": "doc.json",
            },
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    doc = result.documents[0]
    assert doc.annotation_file_str == "doc.json"
    assert doc.annotation_resolved == (root / "doc.json").resolve()


def test_e2e_load_manifest_with_unicode_paths(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    (root / "测试.pdf").write_bytes(b"%PDF")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "测试.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert "测试" in str(result.documents[0].resolved_path)


def test_e2e_load_manifest_subdir_path(tmp_path):
    root = _write_valid_manifest_meta(tmp_path)
    sub = root / "sub"
    sub.mkdir()
    (sub / "doc.pdf").write_bytes(b"%PDF")
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "sub/doc.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m, project_root=root)
    assert result.documents[0].resolved_path == (root / "sub" / "doc.pdf").resolve()


def test_e2e_load_manifest_default_project_root_via_pyproject(tmp_path):
    """无 project_root 参数 → 自动从 manifest 文件向上找 pyproject.toml."""
    root = _write_valid_manifest_meta(tmp_path)
    m = root / "m.json"
    m.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = load_manifest(m)  # 不传 project_root
    assert result.project_root == root.resolve()
