r"""evaluation/manifest.py 第四十二轮 edges 测试（Round 426）。

补强 edges41 未触及的角度：
- _is_absolute_like 边界第十五批（更多形态：tilde / question mark / hash / Unicode 全角 / 多点 / 多盘符）
- _has_backslash 边界第十五批（更多形态：开头单 \ / 结尾单 \ / 中间连续多个）
- _resolve_relative_path 异常深度第十五批（path_str 中间含 .. / project_root 本身含 .. / resolved 在内 / field_name Unicode）
- _detect_project_root 异常深度第十五批（多级嵌套 / pyproject.toml 在更上层 / 文件不存在但目录存在）
- Manifest dataclass 第十五批（与同字段实例相等 / __dataclass_fields__ 顺序 / replace 不可用）
- Manifest properties 第十五批（content_group_count 多组 / pdf_count + docx_count 与 file_count 关系 / categories_covered 空清单）
- DocumentEntry 字段深度第十五批（sha256 None 默认 / paired_with None 默认 / annotation_file_str None 默认 / expectations None 默认）
- ExpectedFailure 字段深度第十五批（source_type None 默认 / 与 DocumentEntry 不同字段）
- load_manifest 异常深度第十五批（不存在 / 非 JSON / version 字段缺失 / 数据类型不对）
- module source forbidden tokens 第二十二批
- module source 字符串精确补强第十九批
- signatures 第十九批
- module 合理性第十九批
- 端到端集成第十九批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
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


# ---------- _is_absolute_like 边界第十五批 ----------


def test_is_absolute_like_tilde_batch15():
    """~ 不是绝对路径（POSIX home shorthand 也算相对）。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_question_mark_batch15():
    assert _is_absolute_like("?foo") is False


def test_is_absolute_like_hash_batch15():
    assert _is_absolute_like("#foo") is False


def test_is_absolute_like_full_width_colon_batch15():
    """全角冒号：不是 ASCII :，不算盘符。"""
    # 全角 ：是 U+FF1A
    assert _is_absolute_like("C：/foo") is False


def test_is_absolute_like_double_dot_batch15():
    """../foo 不是绝对路径。"""
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_two_drive_letters_batch15():
    """AB:/foo — 第二字符是 B 不是 :，不算。"""
    assert _is_absolute_like("AB:/foo") is False


def test_is_absolute_like_just_drive_colon_batch15():
    """C: - len=2 → False。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_drive_at_sign_batch15():
    """@:/foo - 第 0 字符不是字母。"""
    assert _is_absolute_like("@:/foo") is False


def test_is_absolute_like_drive_underscore_batch15():
    """_:/foo - 第 0 字符是下划线，isalpha() False。"""
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_just_dash_batch15():
    assert _is_absolute_like("-foo") is False


# ---------- _has_backslash 边界第十五批 ----------


def test_has_backslash_leading_only_batch15():
    """开头单 \\。"""
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing_only_batch15():
    """结尾单 \\。"""
    assert _has_backslash("foo\\") is True


def test_has_backslash_multiple_consecutive_batch15():
    """多个连续 \\。"""
    assert _has_backslash("a\\\\\\b") is True


def test_has_backslash_only_one_batch15():
    """仅一个 \\。"""
    assert _has_backslash("\\") is True


def test_has_backslash_mixed_separators_batch15():
    """混合分隔符 / 与 \\。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_no_backslash_forward_only_batch15():
    """仅 /，无 \\。"""
    assert _has_backslash("a/b/c") is False


def test_has_backslash_empty_batch15():
    assert _has_backslash("") is False


def test_has_backslash_unicode_no_backslash_batch15():
    """Unicode 字符中没有 \\。"""
    assert _has_backslash("文件路径") is False


# ---------- _resolve_relative_path 异常深度第十五批 ----------


def test_resolve_relative_path_dot_dot_in_middle_batch15(tmp_path):
    """path_str 中间含 .. — 例如 a/../b.pdf，最终解析后仍在 project_root 内即通过。"""
    (tmp_path / "a").mkdir()
    (tmp_path / "b.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("a/../b.pdf", tmp_path, "test")
    assert result == (tmp_path / "b.pdf").resolve()


def test_resolve_relative_path_project_root_with_dot_dot_batch15(tmp_path):
    """project_root 本身含 .. — 应正常解析。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "x.pdf").write_text("fake", encoding="utf-8")
    # project_root = tmp_path/sub/.. 等价于 tmp_path
    root_with_dotdot = tmp_path / "sub" / ".."
    result = _resolve_relative_path("sub/x.pdf", root_with_dotdot, "test")
    # 解析后 = tmp_path/sub/x.pdf
    assert result == (tmp_path / "sub" / "x.pdf").resolve()


def test_resolve_relative_path_field_name_unicode_batch15(tmp_path):
    """field_name 含中文 — message 中应保留。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "中文路径")
    assert "中文路径" in str(exc_info.value)


def test_resolve_relative_path_returns_path_type_batch15(tmp_path):
    """返回值必须是 Path 实例。"""
    (tmp_path / "x.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("x.pdf", tmp_path, "test")
    assert isinstance(result, Path)


def test_resolve_relative_path_resolved_is_absolute_batch15(tmp_path):
    """返回值必须是绝对路径（resolve 后）。"""
    (tmp_path / "y.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("y.pdf", tmp_path, "test")
    assert result.is_absolute()


def test_resolve_relative_path_starts_with_project_root_batch15(tmp_path):
    """返回值字符串形式以 project_root 开头。"""
    (tmp_path / "z.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("z.pdf", tmp_path, "test")
    assert str(result).startswith(str(tmp_path.resolve()))


def test_resolve_relative_path_subdirectory_batch15(tmp_path):
    """子目录路径正常解析。"""
    sub = tmp_path / "data"
    sub.mkdir()
    (sub / "a.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("data/a.pdf", tmp_path, "test")
    assert result == (tmp_path / "data" / "a.pdf").resolve()


def test_resolve_relative_path_path_with_spaces_batch15(tmp_path):
    """路径含空格也能解析。"""
    (tmp_path / "my file.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("my file.pdf", tmp_path, "test")
    assert result == (tmp_path / "my file.pdf").resolve()


def test_resolve_relative_path_escape_attempt_batch15(tmp_path):
    """../../../etc/passwd 应被拒绝（解析后位于 project_root 之外）。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../../etc/passwd", tmp_path, "test")
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_escape_to_root_batch15(tmp_path):
    """仅 ../ 应也跳出 project_root（因为 tmp_path 的 parent 不在 tmp_path 内）。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("..", tmp_path, "test")


# ---------- _detect_project_root 异常深度第十五批 ----------


def test_detect_project_root_default_to_current_when_no_pyproject_batch15(tmp_path):
    """无 pyproject.toml → 回落到当前目录。"""
    sub = tmp_path / "deep"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == sub.resolve()


def test_detect_project_root_finds_pyproject_in_parent_batch15(tmp_path):
    """pyproject.toml 在更上层。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_with_file_input_batch15(tmp_path):
    """输入是文件 → 取其父目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_path_type_batch15(tmp_path):
    """返回类型必须是 Path。"""
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_resolved_batch15(tmp_path):
    """返回值是 resolve 后的（绝对）。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result.is_absolute()


def test_detect_project_root_walks_multiple_levels_batch15(tmp_path):
    """多层嵌套向上找。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_dir_not_file_batch15(tmp_path):
    """即使 start 是文件，返回值也是目录（is_dir）。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    f = tmp_path / "note.txt"
    f.write_text("hello", encoding="utf-8")
    result = _detect_project_root(f)
    assert result.is_dir()


# ---------- Manifest dataclass 第十五批 ----------


def test_manifest_dataclass_equality_same_fields_batch15(tmp_path):
    """两个 Manifest 实例字段相同 → 相等。"""
    common = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p1 = tmp_path / "m1.json"
    p2 = tmp_path / "m2.json"
    p1.write_text(json.dumps(common), encoding="utf-8")
    p2.write_text(json.dumps(common), encoding="utf-8")
    m1 = load_manifest(p1, project_root=tmp_path)
    m2 = load_manifest(p2, project_root=tmp_path)
    assert m1 == m2


def test_manifest_dataclass_inequality_different_status_batch15(tmp_path):
    """devset_status 不同 → 不相等。"""
    p1 = tmp_path / "m1.json"
    p2 = tmp_path / "m2.json"
    p1.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    p2.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m1 = load_manifest(p1, project_root=tmp_path)
    m2 = load_manifest(p2, project_root=tmp_path)
    assert m1 != m2


def test_manifest_dataclass_field_names_order_batch15():
    """__dataclass_fields__ 顺序 = 定义顺序。"""
    names = list(Manifest.__dataclass_fields__.keys())
    assert names == [
        "manifest_version", "devset_status",
        "documents", "expected_failures",
        "project_root",
    ]


def test_manifest_dataclass_replace_fails_batch15(tmp_path):
    """frozen=True → dataclasses.replace 也只能产生新实例，原实例不变。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    m2 = replace(m, devset_status="complete")
    assert m.devset_status == "incomplete"
    assert m2.devset_status == "complete"


def test_manifest_dataclass_setattr_frozen_batch15(tmp_path):
    """frozen=True → 直接 setattr 抛 FrozenInstanceError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_dataclass_is_dataclass_batch15():
    """Manifest 是 dataclass。"""
    assert is_dataclass(Manifest) is True


def test_manifest_dataclass_field_count_batch15():
    """Manifest 字段数 = 5。"""
    assert len(fields(Manifest)) == 5


# ---------- Manifest properties 第十五批 ----------


def test_manifest_content_group_count_multiple_groups_batch15(tmp_path):
    """多组配对：每组都成对 → groups 数 = 配对数。"""
    for n in ("a.pdf", "a.docx", "b.pdf", "b.docx"):
        (tmp_path / n).write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
            {"doc_id": "d3", "path": "b.pdf", "source_type": "pdf", "paired_with": "d4"},
            {"doc_id": "d4", "path": "b.docx", "source_type": "docx", "paired_with": "d3"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 2
    assert m.file_count == 4
    assert m.pdf_count == 2
    assert m.docx_count == 2


def test_manifest_pdf_count_plus_docx_count_le_file_count_batch15(tmp_path):
    """pdf_count + docx_count ≤ file_count（可能含其它 source_type）。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "b.docx").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.pdf_count + m.docx_count == m.file_count


def test_manifest_categories_covered_empty_batch15(tmp_path):
    """空清单 → categories_covered == []。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted_batch15(tmp_path):
    """categories_covered 必须排序。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["z", "a", "m"]},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_content_group_count_unpaired_only_batch15(tmp_path):
    """全部未配对 → content_group_count = file_count。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 2
    assert m.file_count == 2


def test_manifest_file_count_matches_len_documents_batch15(tmp_path):
    """file_count == len(documents)。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == len(m.documents)


# ---------- DocumentEntry 字段深度第十五批 ----------


def test_document_entry_sha256_default_none_batch15(tmp_path):
    """sha256 默认 None。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 is None


def test_document_entry_paired_with_default_none_batch15(tmp_path):
    """paired_with 默认 None。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with is None


def test_document_entry_annotation_file_str_default_none_batch15(tmp_path):
    """annotation_file_str 默认 None。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str is None


def test_document_entry_annotation_resolved_default_none_batch15(tmp_path):
    """annotation_resolved 默认 None。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved is None


def test_document_entry_expectations_default_none_batch15(tmp_path):
    """expectations 默认 None。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations is None


def test_document_entry_categories_default_empty_tuple_batch15(tmp_path):
    """categories 默认空 tuple。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()


def test_document_entry_field_count_batch15():
    """DocumentEntry 字段数 = 10。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_path_str_keeps_relative_batch15(tmp_path):
    """path_str 保留原始相对路径（正斜杠）。"""
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "data/a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].path_str == "data/a.pdf"


# ---------- ExpectedFailure 字段深度第十五批 ----------


def test_expected_failure_source_type_default_none_batch15(tmp_path):
    """source_type 默认 None。"""
    (tmp_path / "x.bad").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "x.bad", "expected_error_code": "x"},
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


def test_expected_failure_field_count_batch15():
    """ExpectedFailure 字段数 = 5。"""
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_order_batch15():
    """字段名顺序 = 定义顺序。"""
    names = list(ExpectedFailure.__dataclass_fields__.keys())
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_no_paired_with_batch15():
    """ExpectedFailure 不含 paired_with（与 DocumentEntry 不同）。"""
    assert "paired_with" not in ExpectedFailure.__dataclass_fields__


def test_expected_failure_no_categories_batch15():
    """ExpectedFailure 不含 categories。"""
    assert "categories" not in ExpectedFailure.__dataclass_fields__


def test_expected_failure_frozen_batch15(tmp_path):
    """ExpectedFailure frozen=True。"""
    (tmp_path / "x.bad").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "x.bad", "expected_error_code": "x"},
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.expected_failures[0].doc_id = "other"


# ---------- load_manifest 异常深度第十五批 ----------


def test_load_manifest_file_not_exist_batch15(tmp_path):
    """清单文件不存在 → ManifestError。但不抛 FileNotFoundError。"""
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "nope.json", project_root=tmp_path)
    assert "不存在" in str(exc_info.value)


def test_load_manifest_invalid_json_batch15(tmp_path):
    """非法 JSON → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_empty_json_batch15(tmp_path):
    """空 JSON 文件 → ManifestError（JSON 解析失败）。"""
    p = tmp_path / "m.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_json_array_batch15(tmp_path):
    """JSON 是数组而非对象 → Schema 失败 → EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_json_int_batch15(tmp_path):
    """JSON 是 int → Schema 失败 → EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_str_input_batch15(tmp_path):
    """manifest_path 接受 str 输入。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(str(p), project_root=tmp_path)
    assert m.manifest_version == "1.0"


def test_load_manifest_str_project_root_batch15(tmp_path):
    """project_root 接受 str 输入。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_no_documents_key_batch15(tmp_path):
    """缺 documents key → Schema 默认应允许，但 d.get("documents", []) fallback。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "expected_failures": [],
    }), encoding="utf-8")
    try:
        m = load_manifest(p, project_root=tmp_path)
        # 如果 schema 允许 documents 缺省，应该返回空 tuple
        assert m.documents == ()
    except Exception:
        # 如果 schema 要求 documents 必填，那也应该抛 EvalSchemaError
        from evaluation.schema import EvalSchemaError
        import sys
        ei = sys.exc_info()[1]
        assert isinstance(ei, EvalSchemaError)


# ---------- module source forbidden tokens 第二十二批 ----------


@pytest.mark.parametrize("forbidden", [
    "subprocess",
    "os.system",
    "os.popen",
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
])
def test_module_source_forbidden_tokens_batch15(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


# ---------- module source 字符串精确补强第十九批 ----------


def test_module_source_has_future_annotations_batch15():
    src = inspect.getsource(mmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_class_manifest_error_batch15():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_class_document_entry_batch15():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src
    assert "class DocumentEntry" in src


def test_module_source_has_class_expected_failure_batch15():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure" in src


def test_module_source_has_class_manifest_batch15():
    src = inspect.getsource(mmod)
    assert "class Manifest" in src


def test_module_source_has_is_absolute_like_batch15():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(path_str: str) -> bool:" in src


def test_module_source_has_has_backslash_batch15():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(path_str: str) -> bool:" in src


def test_module_source_has_resolve_relative_path_batch15():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_load_manifest_batch15():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_has_detect_project_root_batch15():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(start: Path) -> Path:" in src


def test_module_source_has_docstring_batch15():
    src = inspect.getsource(mmod)
    assert '"""开发集清单加载器。' in src


def test_module_source_has_path_field_must_be_relative_comment_batch15():
    src = inspect.getsource(mmod)
    assert "path 字段必须是相对路径" in src


def test_module_source_has_no_absolute_path_message_batch15():
    src = inspect.getsource(mmod)
    assert "必须是相对路径，禁止绝对路径" in src


def test_module_source_has_no_backslash_message_batch15():
    src = inspect.getsource(mmod)
    assert "必须使用正斜杠，禁止反斜杠" in src


def test_module_source_has_outside_project_root_message_batch15():
    src = inspect.getsource(mmod)
    assert "解析后位于项目根目录之外" in src


def test_module_source_has_all_dunder_batch15():
    src = inspect.getsource(mmod)
    assert "__all__ = [" in src


def test_module_source_all_contains_manifest_error_batch15():
    src = inspect.getsource(mmod)
    assert '"ManifestError"' in src


def test_module_source_all_contains_manifest_batch15():
    src = inspect.getsource(mmod)
    assert '"Manifest"' in src


def test_module_source_all_contains_document_entry_batch15():
    src = inspect.getsource(mmod)
    assert '"DocumentEntry"' in src


def test_module_source_all_contains_expected_failure_batch15():
    src = inspect.getsource(mmod)
    assert '"ExpectedFailure"' in src


def test_module_source_all_contains_load_manifest_batch15():
    src = inspect.getsource(mmod)
    assert '"load_manifest"' in src


def test_module_source_has_file_count_property_batch15():
    src = inspect.getsource(mmod)
    assert "@property" in src
    assert "def file_count(self) -> int:" in src


def test_module_source_has_pdf_count_property_batch15():
    src = inspect.getsource(mmod)
    assert "def pdf_count(self) -> int:" in src


def test_module_source_has_docx_count_property_batch15():
    src = inspect.getsource(mmod)
    assert "def docx_count(self) -> int:" in src


def test_module_source_has_content_group_count_property_batch15():
    src = inspect.getsource(mmod)
    assert "def content_group_count(self) -> int:" in src


def test_module_source_has_categories_covered_property_batch15():
    src = inspect.getsource(mmod)
    assert "def categories_covered(self) -> list[str]:" in src


# ---------- signatures 第十九批 ----------


def test_signature_is_absolute_like_batch15():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]
    # `from __future__ import annotations` makes annotations strings
    assert sig.parameters["path_str"].annotation == "str"


def test_signature_is_absolute_like_returns_bool_batch15():
    sig = inspect.signature(_is_absolute_like)
    # `from __future__ import annotations` → return annotation is string "bool"
    assert sig.return_annotation == "bool" or sig.return_annotation is bool


def test_signature_has_backslash_batch15():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_resolve_relative_path_batch15():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_batch15():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]
    assert sig.parameters["project_root"].default is None


def test_signature_detect_project_root_batch15():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


def test_signature_manifest_error_init_batch15():
    sig = inspect.signature(ManifestError.__init__)
    params = list(sig.parameters.keys())
    # Exception.__init__ accepts *args
    assert "self" in params


# ---------- module 合理性第十九批 ----------


def test_module_has_all_attribute_batch15():
    assert hasattr(mmod, "__all__")
    assert isinstance(mmod.__all__, list)


def test_module_all_items_exist_as_attributes_batch15():
    for name in mmod.__all__:
        assert hasattr(mmod, name), f"{name} not in module"


def test_module_has_version_import_batch15():
    """模块导入了 MANIFEST_VERSION。"""
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_uses_manifest_version_constant_batch15():
    """加载时与 MANIFEST_VERSION 比对。"""
    src = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in src


def test_module_imports_pathlib_batch15():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_dataclasses_batch15():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_manifest_error_is_exception_batch15():
    assert issubclass(ManifestError, Exception)


def test_module_manifest_dataclass_frozen_batch15():
    """Manifest 必须是 frozen dataclass。"""
    # 检查 __dataclass_params__
    params = Manifest.__dataclass_params__
    assert params.frozen is True


def test_module_document_entry_frozen_batch15():
    params = DocumentEntry.__dataclass_params__
    assert params.frozen is True


def test_module_expected_failure_frozen_batch15():
    params = ExpectedFailure.__dataclass_params__
    assert params.frozen is True


# ---------- 端到端集成第十九批 ----------


def test_e2e_load_manifest_with_annotation_file_batch15(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "a.json"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "a.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "a.json").resolve()


def test_e2e_load_manifest_with_sha256_batch15(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    sha = "a" * 64
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": sha},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == sha


def test_e2e_load_manifest_with_expectations_batch15(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"heading": 2}}},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"heading": 2}}


def test_e2e_load_manifest_round_trip_idempotent_batch15(tmp_path):
    """多次 load_manifest 同一文件 → 同一结果。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    m3 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2 == m3


def test_e2e_load_manifest_devset_status_complete_batch15(tmp_path):
    """devset_status='complete' 也允许。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"


def test_e2e_load_manifest_uses_default_project_root_when_none_batch15(tmp_path):
    """project_root=None → 自动检测。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=None)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_with_categories_batch15(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["financial", "report"]},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("financial", "report")
    assert m.categories_covered == ["financial", "report"]


def test_e2e_load_manifest_paired_unidirectional_batch15(tmp_path):
    """单向配对（d1 → d2，但 d2 未声明 paired_with）也算一组。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    # d1 声明 paired_with d2，d2 未声明，但 frozenset([d1,d2]) 仍算一组
    assert m.content_group_count == 1


def test_e2e_manifest_version_in_module_constant_batch15():
    """模块常量 MANIFEST_VERSION 必须为 '1.0'。"""
    assert MANIFEST_VERSION == "1.0"


def test_e2e_load_manifest_pyproject_in_subdir_batch15(tmp_path):
    """pyproject.toml 在更深的子目录 → 取最近的（向上找到的第一个）。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "deep"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[tool.y]", encoding="utf-8")
    p = sub / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p)
    # _detect_project_root 从 deep 开始，先找 deep/pyproject.toml
    assert m.project_root == sub.resolve()
