r"""evaluation/manifest.py 边角测试 - 第六轮（Round 154）。

补强已有 base/edges/edges2-5（共 665 测试）未覆盖的深度：
- DocumentEntry/ExpectedFailure/Manifest frozen dataclass 行为
- _is_absolute_like 边界（盘符大小写、单字符、UNC）
- _has_backslash 边界
- _resolve_relative_path 错误消息精确
- content_group_count 边界（配对组合、自配对、链式）
- categories_covered 排序与去重
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

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


# =========================================================================
# _is_absolute_like 边界
# =========================================================================


def test_is_absolute_like_empty_string_returns_false():
    assert _is_absolute_like("") is False


def test_is_absolute_like_posix_absolute():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_posix_relative_returns_false():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_single_char_returns_false():
    """len < 3 时不能构成 Windows 盘符。"""
    assert _is_absolute_like("C") is False


def test_is_absolute_like_two_chars_returns_false():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_windows_drive_lowercase():
    """小写盘符也算绝对路径（isalpha 接受小写）。"""
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_windows_drive_uppercase():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_windows_forward_slash():
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_windows_drive_not_alpha():
    """1C:\\foo - 第一个字符不是 alpha → False。"""
    assert _is_absolute_like("1C:\\foo") is False


def test_is_absolute_like_windows_drive_no_separator():
    """C:foo（无 \\ 或 /）→ 不是绝对路径（Windows 中是 driverelative）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_single_dot_relative():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_relative():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_just_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_digit_first():
    assert _is_absolute_like("1:/foo") is False


# =========================================================================
# _has_backslash 边界
# =========================================================================


def test_has_backslash_empty_returns_false():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash_returns_false():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_with_backslash_returns_true():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_backslashes():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_trailing_backslash():
    assert _has_backslash("foo\\") is True


def test_has_backslash_leading_backslash():
    assert _has_backslash("\\foo") is True


# =========================================================================
# ManifestError
# =========================================================================


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_value_error_subclass():
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_can_be_raised_and_caught():
    with pytest.raises(ManifestError):
        raise ManifestError("test")


def test_manifest_error_caught_as_exception():
    try:
        raise ManifestError("x")
    except Exception:
        pass


def test_manifest_error_message_preserved():
    e = ManifestError("hello")
    assert str(e) == "hello"


def test_manifest_error_empty_message():
    e = ManifestError("")
    assert str(e) == ""


def test_manifest_error_args_length_one():
    e = ManifestError("msg")
    assert e.args == ("msg",)


def test_manifest_error_docstring_present():
    assert ManifestError.__doc__ is not None


def test_manifest_error_docstring_mentions_loading():
    """docstring 提及 "加载"/"校验失败"。"""
    doc = ManifestError.__doc__
    assert "清单" in doc or "加载" in doc or "校验" in doc


# =========================================================================
# DocumentEntry frozen dataclass
# =========================================================================


def _make_doc_entry(**overrides) -> DocumentEntry:
    defaults = dict(
        doc_id="d1",
        path_str="a/b.txt",
        resolved_path=Path("/tmp/a/b.txt"),
        source_type="text",
        sha256=None,
        categories=("cat_a",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen():
    """frozen=True → setattr 应抛 FrozenInstanceError。"""
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "other"


def test_document_entry_field_count():
    """10 个字段。"""
    fs = fields(DocumentEntry)
    assert len(fs) == 10


def test_document_entry_field_names_exact():
    fs = fields(DocumentEntry)
    names = {f.name for f in fs}
    expected = {
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
    assert names == expected


def test_document_entry_equality_same_values():
    a = _make_doc_entry()
    b = _make_doc_entry()
    assert a == b


def test_document_entry_equality_different_doc_id():
    a = _make_doc_entry()
    b = _make_doc_entry(doc_id="d2")
    assert a != b


def test_document_entry_hashable():
    """frozen dataclass 应可 hash。"""
    d = _make_doc_entry()
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_hash_equal_for_equal_instances():
    a = _make_doc_entry()
    b = _make_doc_entry()
    assert hash(a) == hash(b)


def test_document_entry_categories_defaults_to_empty_when_not_provided():
    """测试 _make_doc_entry 不传 categories → 默认 ("cat_a",)。
    实际 manifest 加载时使用 tuple(d.get("categories", []))。"""
    d = _make_doc_entry(categories=())
    assert d.categories == ()


def test_document_entry_categories_can_be_multidimensional():
    d = _make_doc_entry(categories=("a", "b", "c"))
    assert d.categories == ("a", "b", "c")


def test_document_entry_expectations_can_be_dict():
    d = _make_doc_entry(expectations={"element_count_by_type": {"paragraph": 5}})
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_document_entry_expectations_none():
    d = _make_doc_entry()
    assert d.expectations is None


def test_document_entry_repr_has_class_name():
    d = _make_doc_entry()
    assert "DocumentEntry" in repr(d)


def test_document_entry_annotation_resolved_none_default():
    d = _make_doc_entry()
    assert d.annotation_resolved is None


def test_document_entry_paired_with_none_default():
    d = _make_doc_entry()
    assert d.paired_with is None


def test_document_entry_sha256_none_default():
    d = _make_doc_entry()
    assert d.sha256 is None


# =========================================================================
# ExpectedFailure frozen dataclass
# =========================================================================


def _make_expected_failure(**overrides) -> ExpectedFailure:
    defaults = dict(
        doc_id="ef1",
        path_str="missing.pdf",
        resolved_path=Path("/tmp/missing.pdf"),
        expected_error_code="file_not_found",
        source_type="pdf",
    )
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "other"


def test_expected_failure_field_count():
    fs = fields(ExpectedFailure)
    assert len(fs) == 5


def test_expected_failure_field_names_exact():
    fs = fields(ExpectedFailure)
    names = {f.name for f in fs}
    expected = {
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    }
    assert names == expected


def test_expected_failure_equality_same_values():
    a = _make_expected_failure()
    b = _make_expected_failure()
    assert a == b


def test_expected_failure_hashable():
    ef = _make_expected_failure()
    h = hash(ef)
    assert isinstance(h, int)


def test_expected_failure_source_type_can_be_none():
    ef = _make_expected_failure(source_type=None)
    assert ef.source_type is None


def test_expected_failure_repr_has_class_name():
    ef = _make_expected_failure()
    assert "ExpectedFailure" in repr(ef)


# =========================================================================
# Manifest frozen dataclass
# =========================================================================


def _make_manifest(**overrides) -> Manifest:
    defaults = dict(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_is_frozen():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "other"


def test_manifest_field_count():
    fs = fields(Manifest)
    assert len(fs) == 5


def test_manifest_field_names_exact():
    fs = fields(Manifest)
    names = {f.name for f in fs}
    expected = {
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    }
    assert names == expected


def test_manifest_hashable():
    m = _make_manifest()
    h = hash(m)
    assert isinstance(h, int)


def test_manifest_file_count_empty_documents():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_with_documents():
    docs = (_make_doc_entry(doc_id="d1"), _make_doc_entry(doc_id="d2"))
    m = _make_manifest(documents=docs)
    assert m.file_count == 2


def test_manifest_pdf_count_empty():
    m = _make_manifest(documents=())
    assert m.pdf_count == 0


def test_manifest_pdf_count_filters_other_types():
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="pdf"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count_filters_other_types():
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="docx"),
    )
    m = _make_manifest(documents=docs)
    assert m.docx_count == 2


def test_manifest_content_group_count_empty():
    m = _make_manifest(documents=())
    assert m.content_group_count == 0


def test_manifest_content_group_count_all_unpaired():
    docs = (
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
        _make_doc_entry(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_all_paired():
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed():
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_sided_paired():
    """单向 paired_with 也算一组（避免重复计数）。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        # d2 不声明 paired_with
        _make_doc_entry(doc_id="d2"),
    )
    m = _make_manifest(documents=docs)
    # frozenset({d1, d2}) → 1 组；d2 不算 unpaired（在 seen 中）
    assert m.content_group_count == 1


def test_manifest_categories_covered_empty():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_categories_covered_sorted_unique():
    docs = (
        _make_doc_entry(doc_id="d1", categories=("z", "a")),
        _make_doc_entry(doc_id="d2", categories=("m", "a")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_categories_covered_empty_tuple_per_doc():
    docs = (
        _make_doc_entry(doc_id="d1", categories=()),
        _make_doc_entry(doc_id="d2", categories=()),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == []


def test_categories_covered_returns_list_not_tuple():
    m = _make_manifest(documents=(_make_doc_entry(),))
    assert isinstance(m.categories_covered, list)


def test_manifest_repr_has_class_name():
    m = _make_manifest()
    assert "Manifest" in repr(m)


# =========================================================================
# _resolve_relative_path 错误路径
# =========================================================================


def test_resolve_relative_path_empty_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "field_x")
    assert "field_x" in str(exc.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "绝对路径" in str(exc.value) or "absolute" in str(exc.value).lower()


def test_resolve_relative_path_windows_drive_raises(tmp_path: Path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("C:/foo", tmp_path, "f")


def test_resolve_relative_path_backslash_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("foo\\bar", tmp_path, "f")
    assert "正斜杠" in str(exc.value) or "反斜杠" in str(exc.value)


def test_resolve_relative_path_outside_project_raises(tmp_path: Path):
    """相对路径但 ../escape 解析后位于项目根外。"""
    # 创建子目录让 escape 有意义
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../escape", sub, "f")
    assert "项目根目录之外" in str(exc.value) or "outside" in str(exc.value).lower()


def test_resolve_relative_path_valid_returns_resolved_path(tmp_path: Path):
    # 创建子目录与文件
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "file.txt").write_text("x", encoding="utf-8")
    result = _resolve_relative_path("data/file.txt", tmp_path, "f")
    assert isinstance(result, Path)
    assert result.is_absolute()
    assert result.parent == (tmp_path / "data").resolve()


def test_resolve_relative_path_nested_subdir(tmp_path: Path):
    """多层嵌套子目录的相对路径。"""
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    result = _resolve_relative_path("a/b/c/file.txt", tmp_path, "f")
    assert result == deep.resolve() / "file.txt"


def test_resolve_relative_path_dot_current_dir(tmp_path: Path):
    """./foo 解析为 project_root/foo。"""
    result = _resolve_relative_path("./foo.txt", tmp_path, "f")
    assert result == (tmp_path / "foo.txt").resolve()


def test_resolve_relative_path_returns_absolute(tmp_path: Path):
    """返回值必须是绝对路径。"""
    result = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert result.is_absolute()


# =========================================================================
# _detect_project_root
# =========================================================================


def test_detect_project_root_from_file_returns_parent_with_pyproject(tmp_path: Path):
    """从 file 路径向上找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    f = sub / "f.txt"
    f.write_text("x", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_from_dir_returns_self_with_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur(tmp_path: Path):
    """无 pyproject.toml → 返回 cur（不再向上找）。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == sub.resolve()


def test_detect_project_root_returns_path():
    """返回类型是 Path。"""
    result = _detect_project_root(Path("."))
    assert isinstance(result, Path)


# =========================================================================
# load_manifest 端到端
# =========================================================================


def _write_valid_manifest(tmp_path: Path) -> Path:
    """写一个最小合法 manifest。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    # 在项目根下创建样例文件
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.txt").write_text("hello", encoding="utf-8")
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "data/a.txt",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


def test_load_manifest_returns_manifest_instance(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_devset_status(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.devset_status == "incomplete"


def test_load_manifest_documents_count(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert len(m.documents) == 1


def test_load_manifest_document_doc_id(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.documents[0].doc_id == "d1"


def test_load_manifest_document_source_type(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.documents[0].source_type == "pdf"


def test_load_manifest_document_categories_default_empty(tmp_path: Path):
    """manifest 中没写 categories → 默认空 tuple。"""
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.documents[0].categories == ()


def test_load_manifest_document_categories_passthrough(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.txt").write_text("hello", encoding="utf-8")
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "data/a.txt",
                "source_type": "pdf",
                "categories": ["x", "y"],
            }
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].categories == ("x", "y")


def test_load_manifest_missing_file_raises(tmp_path: Path):
    missing = tmp_path / "missing.json"
    with pytest.raises(ManifestError) as exc:
        load_manifest(missing)
    assert "清单文件不存在" in str(exc.value) or "不存在" in str(exc.value)


def test_load_manifest_str_path_accepted(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    # 传字符串路径而非 Path
    m = load_manifest(str(p))
    assert isinstance(m, Manifest)


def test_load_manifest_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "manifest.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc.value) or "JSONDecodeError" in str(exc.value)


def test_load_manifest_no_project_root_uses_detect(tmp_path: Path):
    """不传 project_root → 自动 detect。"""
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    # detected project_root 应是 tmp_path
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_explicit_project_root(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_str_project_root(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_expected_failures_default_empty(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.expected_failures == ()


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_exact_list():
    import evaluation.manifest as mod
    assert mod.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_no_duplicates():
    import evaluation.manifest as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_json():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_dataclass():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_path():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_manifest_version():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "MANIFEST_VERSION" in src


def test_module_imports_validate():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from evaluation.schema import validate" in src


def test_module_uses_future_annotations():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.manifest as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_invariants():
    """docstring 提及关键不变量。"""
    import evaluation.manifest as mod
    doc = mod.__doc__
    assert "相对路径" in doc
    assert "项目根" in doc or "project root" in doc.lower()


def test_module_no_silence_unused():
    import evaluation.manifest as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 签名深度
# =========================================================================


def test_load_manifest_param_names():
    sig = inspect.signature(load_manifest)
    assert set(sig.parameters) == {"manifest_path", "project_root"}


def test_load_manifest_manifest_path_no_default():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_resolve_relative_path_param_names():
    sig = inspect.signature(_resolve_relative_path)
    assert set(sig.parameters) == {"path_str", "project_root", "field_name"}


def test_resolve_relative_path_no_defaults():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_detect_project_root_param_name():
    sig = inspect.signature(_detect_project_root)
    assert "start" in sig.parameters


def test_is_absolute_like_param_name():
    sig = inspect.signature(_is_absolute_like)
    assert "path_str" in sig.parameters


def test_has_backslash_param_name():
    sig = inspect.signature(_has_backslash)
    assert "path_str" in sig.parameters


def test_is_absolute_like_return_annotation_bool():
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in str(sig.return_annotation)


def test_has_backslash_return_annotation_bool():
    sig = inspect.signature(_has_backslash)
    assert "bool" in str(sig.return_annotation)


# =========================================================================
# 综合行为
# =========================================================================


def test_document_entry_immutable_after_construction():
    """frozen dataclass: 任何 setattr 都失败。"""
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.path_str = "other"
    with pytest.raises(FrozenInstanceError):
        d.source_type = "pdf"
    with pytest.raises(FrozenInstanceError):
        d.expectations = {}


def test_manifest_immutable_after_construction():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "other"
    with pytest.raises(FrozenInstanceError):
        m.documents = ()


def test_two_manifests_independent():
    """两个 manifest 实例独立（无类级别可变状态）。"""
    m1 = _make_manifest(documents=(_make_doc_entry(doc_id="d1"),))
    m2 = _make_manifest(documents=(_make_doc_entry(doc_id="d2"),))
    assert m1.documents[0].doc_id == "d1"
    assert m2.documents[0].doc_id == "d2"
    assert m1 != m2


def test_manifest_properties_consistent():
    """多次访问 file_count 返回相同值。"""
    m = _make_manifest(documents=(_make_doc_entry(), _make_doc_entry(doc_id="d2")))
    a = m.file_count
    b = m.file_count
    assert a == b == 2


def test_is_absolute_like_idempotent():
    """同一输入多次调用结果一致。"""
    assert _is_absolute_like("/x") is True
    assert _is_absolute_like("/x") is True
    assert _is_absolute_like("x") is False
    assert _is_absolute_like("x") is False


def test_has_backslash_idempotent():
    assert _has_backslash("a\\b") is True
    assert _has_backslash("a\\b") is True
    assert _has_backslash("a/b") is False
    assert _has_backslash("a/b") is False


def test_load_manifest_roundtrip_with_categories(tmp_path: Path):
    """load_manifest 读出 DocumentEntry 后，再构造相同 Manifest 应相等。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.txt").write_text("hello", encoding="utf-8")
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "data/a.txt",
                "source_type": "pdf",
                "categories": ["a", "b"],
            }
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m1 = load_manifest(p)
    m2 = load_manifest(p)
    assert m1 == m2
    assert m1.documents[0].categories == m2.documents[0].categories
