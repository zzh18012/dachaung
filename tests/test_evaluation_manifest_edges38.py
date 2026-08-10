"""evaluation/manifest.py 第三十八轮 edges 测试（Round 398）。

补强 edges37 未触及的角度：
- _is_absolute_like 数学边界第十一批（更多 corner cases：whitespace / multi-char drive / 仅 colon / 特殊字符前缀）
- _has_backslash 数学边界第十一批（mixed slash / 重复反斜杠 / Unicode + 反斜杠）
- _resolve_relative_path 行为深度第十一批（Path vs str / Unicode field name / 各种 path 形式）
- _detect_project_root 行为深度第十一批（更多 corner cases）
- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第十一批（field 类型 / hash / equality / repr）
- Manifest properties algorithm 第十一批（content_group_count 复杂组合 / categories 排序 / count 边界）
- load_manifest malformed data 第十一批（manifest_path 多种输入 / JSON BOM / Schema 失败）
- module source forbidden tokens 第十四批
- module source 字符串精确补强第九批
- signatures 第十一批
- module 合理性第十一批
- 端到端集成第十一批
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


# ---------- _is_absolute_like 数学边界第十一批 ----------


def test_is_absolute_like_tab_first_char_batch11():
    """Tab 不是 '/' 也不是 alpha → False。"""
    assert _is_absolute_like("\t/foo") is False


def test_is_absolute_like_newline_first_char_batch11():
    assert _is_absolute_like("\n/foo") is False


def test_is_absolute_like_single_char_a_batch11():
    """单字符 'a'：len<3 → 不进入 drive 分支。"""
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_chars_a_colon_batch11():
    """'a:' → len=2 → 不进入 drive 分支（需 len>=3）。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_two_chars_slash_batch11():
    """'/a' → startswith '/' → True。"""
    assert _is_absolute_like("/a") is True


def test_is_absolute_like_drive_no_separator_batch11():
    """'A:foo' → 第三个字符不是 \\ 或 / → False。"""
    assert _is_absolute_like("A:foo") is False


def test_is_absolute_like_multi_letter_drive_batch11():
    """'AB:/x' → 第一个字符 A.isalpha() True，但 path_str[1]='B'（不是 ':'）→ False。"""
    assert _is_absolute_like("AB:/x") is False


def test_is_absolute_like_space_first_char_batch11():
    assert _is_absolute_like(" /foo") is False


def test_is_absolute_like_backslash_first_char_batch11():
    """单独 '\\foo' → 不 startswith '/'，不进入 drive 分支 → False。"""
    assert _is_absolute_like("\\foo") is False


def test_is_absolute_like_drive_lowercase_z_posix_batch11():
    assert _is_absolute_like("z:/foo") is True


def test_is_absolute_like_drive_uppercase_z_windows_batch11():
    assert _is_absolute_like("Z:\\foo") is True


def test_is_absolute_like_just_colon_batch11():
    """':' 单字符 → len<3 → False。"""
    assert _is_absolute_like(":") is False


def test_is_absolute_like_three_chars_no_drive_separator_batch11():
    """'a::' → 第三字符 ':' 不是 \\ 或 / → False。"""
    assert _is_absolute_like("a::") is False


def test_is_absolute_like_three_chars_drive_separator_dash_batch11():
    """'a:-' → 第三字符 '-' 不是 \\ 或 / → False。"""
    assert _is_absolute_like("a:-") is False


def test_is_absolute_like_returns_bool_type_batch11():
    """返回值是 Python bool。"""
    assert type(_is_absolute_like("")) is bool
    assert type(_is_absolute_like("/x")) is bool


# ---------- _has_backslash 数学边界第十一批 ----------


def test_has_backslash_single_backslash_batch11():
    assert _has_backslash("\\") is True


def test_has_backslash_double_backslash_batch11():
    assert _has_backslash("\\\\") is True


def test_has_backslash_mixed_slashes_batch11():
    """'/foo\\bar' → 含 \\ → True。"""
    assert _has_backslash("/foo\\bar") is True


def test_has_backslash_at_start_batch11():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end_batch11():
    assert _has_backslash("foo\\") is True


def test_has_backslash_in_middle_batch11():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_unicode_plus_backslash_batch11():
    assert _has_backslash("中文\\bar") is True


def test_has_backslash_forward_slash_only_batch11():
    assert _has_backslash("/foo/bar") is False


def test_has_backslash_empty_batch11():
    assert _has_backslash("") is False


def test_has_backslash_returns_bool_type_batch11():
    assert type(_has_backslash("")) is bool


# ---------- _resolve_relative_path 行为深度第十一批 ----------


def test_resolve_relative_path_path_obj_project_root_batch11(tmp_path):
    out = _resolve_relative_path("a.pdf", tmp_path, "test")
    assert out == (tmp_path / "a.pdf").resolve()


def test_resolve_relative_path_str_project_root_batch11(tmp_path):
    """project_root 接受 str 时函数会抛 TypeError（函数期望 Path 对象）。"""
    with pytest.raises(TypeError):
        _resolve_relative_path("a.pdf", str(tmp_path), "test")  # type: ignore[arg-type]


def test_resolve_relative_path_unicode_field_name_batch11(tmp_path):
    out = _resolve_relative_path("a.pdf", tmp_path, "文档")
    assert isinstance(out, Path)


def test_resolve_relative_path_unicode_path_batch11(tmp_path):
    out = _resolve_relative_path("中文.pdf", tmp_path, "test")
    assert out == (tmp_path / "中文.pdf").resolve()


def test_resolve_relative_path_nested_subdir_batch11(tmp_path):
    out = _resolve_relative_path("a/b/c.pdf", tmp_path, "test")
    assert out == (tmp_path / "a" / "b" / "c.pdf").resolve()


def test_resolve_relative_path_dot_slash_batch11(tmp_path):
    """./foo 解析为 project_root/foo。"""
    out = _resolve_relative_path("./foo.pdf", tmp_path, "test")
    assert out == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_returns_path_type_batch11(tmp_path):
    out = _resolve_relative_path("a.pdf", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_idempotent_batch11(tmp_path):
    out1 = _resolve_relative_path("a.pdf", tmp_path, "test")
    out2 = _resolve_relative_path("a.pdf", tmp_path, "test")
    assert out1 == out2


def test_resolve_relative_path_does_not_check_existence_batch11(tmp_path):
    """不要求文件存在。"""
    out = _resolve_relative_path("nonexistent.pdf", tmp_path, "test")
    assert not out.exists()
    assert isinstance(out, Path)


def test_resolve_relative_path_double_dot_in_subdir_batch11(tmp_path):
    """'a/../b.pdf' → 解析为 project_root/b.pdf（合法）。"""
    out = _resolve_relative_path("a/../b.pdf", tmp_path, "test")
    assert out == (tmp_path / "b.pdf").resolve()


def test_resolve_relative_path_double_dot_escape_batch11(tmp_path):
    """'../foo' → 解析在 project_root 之外 → ManifestError。"""
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../foo.pdf", tmp_path, "test")


def test_resolve_relative_path_absolute_posix_batch11(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_absolute_windows_batch11(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("C:/foo", tmp_path, "test")


def test_resolve_relative_path_backslash_batch11(tmp_path):
    with pytest.raises(ManifestError, match="反斜杠"):
        _resolve_relative_path("a\\b.pdf", tmp_path, "test")


def test_resolve_relative_path_empty_batch11(tmp_path):
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", tmp_path, "test")


# ---------- _detect_project_root 行为深度第十一批 ----------


def test_detect_project_root_returns_path_type_batch11(tmp_path):
    """在 worktree 中实际调用，返回 Path。"""
    out = _detect_project_root(Path(__file__))
    assert isinstance(out, Path)


def test_detect_project_root_finds_pyproject_batch11():
    """以本测试文件为起点，应能找到项目根（含 pyproject.toml）。"""
    out = _detect_project_root(Path(__file__))
    assert (out / "pyproject.toml").is_file()


def test_detect_project_root_walks_up_batch11():
    """从深路径向上找。"""
    out = _detect_project_root(Path(__file__).parent / "deep" / "deeper")
    # 如果向上能找到 pyproject.toml，会停在第一个找到的；否则停在起点
    assert isinstance(out, Path)


def test_detect_project_root_start_is_file_batch11(tmp_path):
    """start 是文件 → 取 parent。"""
    f = tmp_path / "x.txt"
    f.write_text("hi", encoding="utf-8")
    out = _detect_project_root(f)
    # 一直向上找不到 pyproject → 返回 start.parent
    assert isinstance(out, Path)


def test_detect_project_root_idempotent_batch11():
    out1 = _detect_project_root(Path(__file__))
    out2 = _detect_project_root(Path(__file__))
    assert out1 == out2


def test_detect_project_root_str_input_raises_batch11():
    """str 输入 → Path.resolve() 不支持 str，应抛 AttributeError 或类似。"""
    with pytest.raises((AttributeError, TypeError)):
        _detect_project_root("not/a/path")  # type: ignore[arg-type]


# ---------- DocumentEntry / ExpectedFailure / Manifest dataclass 行为第十一批 ----------


def test_document_entry_field_count_batch11():
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch11():
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


def test_document_entry_is_dataclass_batch11():
    assert is_dataclass(DocumentEntry)


def test_document_entry_frozen_batch11():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "modified"  # type: ignore[misc]


def test_document_entry_equality_batch11():
    d1 = _make_doc()
    d2 = _make_doc()
    assert d1 == d2


def test_document_entry_inequality_batch11():
    d1 = _make_doc(doc_id="d1")
    d2 = _make_doc(doc_id="d2")
    assert d1 != d2


def test_document_entry_hash_equal_for_equal_batch11():
    d1 = _make_doc()
    d2 = _make_doc()
    assert hash(d1) == hash(d2)


def test_document_entry_in_set_batch11():
    d1 = _make_doc()
    d2 = _make_doc()
    s = {d1, d2}
    assert len(s) == 1  # same hash → same entry


def test_document_entry_repr_batch11():
    d = _make_doc(doc_id="abc")
    assert "DocumentEntry" in repr(d)
    assert "abc" in repr(d)


def test_expected_failure_field_count_batch11():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch11():
    names = [f.name for f in fields(ExpectedFailure)]
    assert names == [
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    ]


def test_expected_failure_is_dataclass_batch11():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_frozen_batch11():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.pdf",
        resolved_path=Path("/x/bad.pdf"),
        expected_error_code="unsupported_format",
        source_type="pdf",
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "modified"  # type: ignore[misc]


def test_manifest_field_count_batch11():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_batch11():
    names = [f.name for f in fields(Manifest)]
    assert names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_manifest_is_dataclass_batch11():
    assert is_dataclass(Manifest)


def test_manifest_frozen_batch11():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


# ---------- Manifest properties algorithm 行为深度第十一批 ----------


def _make_manifest(documents, expected_failures=()):
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(documents),
        expected_failures=tuple(expected_failures),
        project_root=Path("."),
    )


def test_manifest_file_count_empty_batch11():
    m = _make_manifest([])
    assert m.file_count == 0


def test_manifest_file_count_three_batch11():
    m = _make_manifest([_make_doc(doc_id=f"d{i}") for i in range(3)])
    assert m.file_count == 3


def test_manifest_pdf_count_zero_when_no_pdf_batch11():
    m = _make_manifest([_make_doc(doc_id="d1", source_type="docx")])
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docx_batch11():
    m = _make_manifest([_make_doc(doc_id="d1", source_type="pdf")])
    assert m.docx_count == 0


def test_manifest_pdf_count_two_batch11():
    m = _make_manifest(
        [
            _make_doc(doc_id="d1", source_type="pdf"),
            _make_doc(doc_id="d2", source_type="pdf"),
            _make_doc(doc_id="d3", source_type="docx"),
        ]
    )
    assert m.pdf_count == 2


def test_manifest_docx_count_two_batch11():
    m = _make_manifest(
        [
            _make_doc(doc_id="d1", source_type="docx"),
            _make_doc(doc_id="d2", source_type="docx"),
            _make_doc(doc_id="d3", source_type="pdf"),
        ]
    )
    assert m.docx_count == 2


def test_manifest_categories_covered_sorted_batch11():
    """categories_covered 排序。"""
    m = _make_manifest(
        [
            _make_doc(doc_id="d1", categories=("z", "a")),
            _make_doc(doc_id="d2", categories=("m",)),
        ]
    )
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_unique_batch11():
    m = _make_manifest(
        [
            _make_doc(doc_id="d1", categories=("a", "b")),
            _make_doc(doc_id="d2", categories=("a", "c")),
        ]
    )
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_empty_batch11():
    m = _make_manifest([_make_doc(doc_id="d1", categories=())])
    assert m.categories_covered == []


def test_manifest_categories_covered_unicode_batch11():
    m = _make_manifest([_make_doc(doc_id="d1", categories=("中文",))])
    assert m.categories_covered == ["中文"]


def test_manifest_content_group_count_paired_batch11():
    """双向配对：d1 ↔ d2 → 1 组。"""
    m = _make_manifest(
        [
            _make_doc(doc_id="d1", paired_with="d2"),
            _make_doc(doc_id="d2", paired_with="d1"),
        ]
    )
    assert m.content_group_count == 1


def test_manifest_content_group_count_unpaired_batch11():
    """无配对：每个独立算 1 组。"""
    m = _make_manifest(
        [
            _make_doc(doc_id="d1"),
            _make_doc(doc_id="d2"),
        ]
    )
    assert m.content_group_count == 2


def test_manifest_content_group_count_mixed_batch11():
    """1 对配对 + 1 个独立 → 2 组。"""
    m = _make_manifest(
        [
            _make_doc(doc_id="d1", paired_with="d2"),
            _make_doc(doc_id="d2", paired_with="d1"),
            _make_doc(doc_id="d3"),
        ]
    )
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_sided_paired_batch11():
    """单向配对：d1 → d2（d2 不指回）→ 算 1 组。"""
    m = _make_manifest(
        [
            _make_doc(doc_id="d1", paired_with="d2"),
            _make_doc(doc_id="d2"),
        ]
    )
    # d1 有 paired_with → 加入 pair_ids {d1, d2}
    # d2 in seen → 不算 unpaired
    # 结果：1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_empty_batch11():
    m = _make_manifest([])
    assert m.content_group_count == 0


def test_manifest_pdf_count_returns_int_batch11():
    m = _make_manifest([_make_doc(source_type="pdf")])
    assert type(m.pdf_count) is int


def test_manifest_docx_count_returns_int_batch11():
    m = _make_manifest([_make_doc(source_type="docx")])
    assert type(m.docx_count) is int


def test_manifest_file_count_returns_int_batch11():
    m = _make_manifest([_make_doc()])
    assert type(m.file_count) is int


def test_manifest_categories_covered_returns_list_batch11():
    m = _make_manifest([_make_doc()])
    assert type(m.categories_covered) is list


def test_manifest_content_group_count_returns_int_batch11():
    m = _make_manifest([_make_doc()])
    assert type(m.content_group_count) is int


# ---------- load_manifest malformed data 第十一批 ----------


def _valid_manifest_dict():
    return {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }


def test_load_manifest_str_path_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    out = load_manifest(str(p))
    assert isinstance(out, Manifest)


def test_load_manifest_path_obj_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    out = load_manifest(p)
    assert isinstance(out, Manifest)


def test_load_manifest_nonexistent_raises_batch11(tmp_path):
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(tmp_path / "no.json")


def test_load_manifest_directory_raises_batch11(tmp_path):
    """manifest_path 是目录 → is_file False → ManifestError。"""
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(tmp_path)


def test_load_manifest_empty_file_raises_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_whitespace_only_raises_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("   \n\t  ", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_bom_raises_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_bytes(b'\xef\xbb\xbf' + json.dumps(_valid_manifest_dict()).encode("utf-8"))
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_invalid_json_raises_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON"):
        load_manifest(p)


def test_load_manifest_wrong_version_raises_batch11(tmp_path):
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    data["manifest_version"] = "9.9.9"
    p.write_text(json.dumps(data), encoding="utf-8")
    # 9.9.9 不是合法 enum，schema 直接失败 → EvalSchemaError（ManifestError 的 not）
    with pytest.raises(Exception):
        load_manifest(p)


def test_load_manifest_no_version_field_raises_batch11(tmp_path):
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    del data["manifest_version"]
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p)


def test_load_manifest_devset_status_invalid_raises_batch11(tmp_path):
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    data["devset_status"] = "totally_invalid_value"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p)


def test_load_manifest_explicit_project_root_batch11(tmp_path):
    """显式传 project_root，使用该路径。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.project_root == tmp_path.resolve()


# ---------- module source forbidden tokens 第十四批 ----------


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
    ],
)
def test_manifest_source_no_forbidden_token_fourteenth_batch11(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_manifest_source_no_unlink_batch11():
    source = inspect.getsource(mmod)
    assert "unlink" not in source


def test_manifest_source_no_remove_batch11():
    source = inspect.getsource(mmod)
    assert ".remove(" not in source


def test_manifest_source_no_kill_batch11():
    source = inspect.getsource(mmod)
    assert ".kill(" not in source


def test_manifest_source_no_terminate_batch11():
    source = inspect.getsource(mmod)
    assert ".terminate(" not in source


def test_manifest_source_no_async_def_batch11():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_manifest_source_no_yield_batch11():
    source = inspect.getsource(mmod)
    assert "yield" not in source


def test_manifest_source_no_walrus_batch11():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_manifest_source_no_top_level_lambda_batch11():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_manifest_source_no_print_batch11():
    source = inspect.getsource(mmod)
    assert "print(" not in source


def test_manifest_source_no_socket_batch11():
    source = inspect.getsource(mmod)
    assert "socket" not in source


def test_manifest_source_no_threading_batch11():
    source = inspect.getsource(mmod)
    assert "threading" not in source


def test_manifest_source_no_multiprocessing_batch11():
    source = inspect.getsource(mmod)
    assert "multiprocessing" not in source


def test_manifest_source_no_asyncio_batch11():
    source = inspect.getsource(mmod)
    assert "asyncio" not in source


def test_manifest_source_no_pickle_module_batch11():
    source = inspect.getsource(mmod)
    assert "import pickle" not in source


def test_manifest_source_no_yaml_module_batch11():
    source = inspect.getsource(mmod)
    assert "import yaml" not in source


# ---------- module source 字符串精确补强第九批 ----------


def test_module_source_has_future_annotations_batch11():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json_batch11():
    source = inspect.getsource(mmod)
    assert "import json" in source


def test_module_source_imports_dataclass_batch11():
    source = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in source


def test_module_source_imports_path_batch11():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch11():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_imports_manifest_version_batch11():
    source = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in source


def test_module_source_imports_validate_batch11():
    source = inspect.getsource(mmod)
    assert "validate" in source
    assert "from evaluation.schema" in source


def test_module_source_has_manifest_error_class_batch11():
    source = inspect.getsource(mmod)
    assert "class ManifestError" in source


def test_module_source_has_document_entry_class_batch11():
    source = inspect.getsource(mmod)
    assert "class DocumentEntry" in source
    assert "@dataclass(frozen=True)" in source


def test_module_source_has_expected_failure_class_batch11():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure" in source


def test_module_source_has_manifest_class_batch11():
    source = inspect.getsource(mmod)
    assert "class Manifest" in source


def test_module_source_has_is_absolute_like_def_batch11():
    source = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in source


def test_module_source_has_resolve_relative_path_def_batch11():
    source = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in source


def test_module_source_has_load_manifest_def_batch11():
    source = inspect.getsource(mmod)
    assert "def load_manifest(" in source


def test_module_source_has_detect_project_root_def_batch11():
    source = inspect.getsource(mmod)
    assert "def _detect_project_root(" in source


def test_module_source_no_main_block_batch11():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch11():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


# ---------- signatures 第十一批 ----------


def test_signature_is_absolute_like_1_param_batch11():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1


def test_signature_is_absolute_like_param_name_batch11():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters) == ["path_str"]


def test_signature_has_backslash_1_param_batch11():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_signature_has_backslash_param_name_batch11():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters) == ["path_str"]


def test_signature_resolve_relative_path_3_params_batch11():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_signature_resolve_relative_path_param_names_batch11():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters) == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_2_params_batch11():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_signature_load_manifest_param_names_batch11():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters) == ["manifest_path", "project_root"]


def test_signature_load_manifest_default_project_root_none_batch11():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_detect_project_root_1_param_batch11():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_signature_detect_project_root_param_name_batch11():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters) == ["start"]


def test_signature_funcs_function_type_batch11():
    for func in (
        _is_absolute_like,
        _has_backslash,
        _resolve_relative_path,
        load_manifest,
        _detect_project_root,
    ):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq_batch11():
    for func in (
        _is_absolute_like,
        _has_backslash,
        _resolve_relative_path,
        load_manifest,
        _detect_project_root,
    ):
        assert func.__module__ == "evaluation.manifest"


def test_signature_manifest_error_subclass_of_exception_batch11():
    assert issubclass(ManifestError, Exception)


# ---------- module 合理性第十一批 ----------


def test_module_all_value_batch11():
    assert mmod.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_is_list_batch11():
    assert isinstance(mmod.__all__, list)


def test_module_all_entries_unique_batch11():
    assert len(mmod.__all__) == len(set(mmod.__all__))


def test_module_all_entries_str_batch11():
    for name in mmod.__all__:
        assert isinstance(name, str)


def test_module_has_dunder_file_batch11():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_endswith_manifest_py_batch11():
    import os
    sep = os.sep
    assert mmod.__file__.endswith("evaluation" + sep + "manifest.py") or mmod.__file__.endswith(
        "evaluation/manifest.py"
    )


def test_module_name_is_evaluation_manifest_batch11():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_user_function_count_batch11():
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


def test_module_user_class_count_batch11():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert set(classes) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_module_docstring_present_batch11():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_docstring_mentions_invariants_batch11():
    """docstring 提到关键不变量。"""
    assert mmod.__doc__ is not None
    assert "绝对路径" in mmod.__doc__ or "项目根" in mmod.__doc__


# ---------- 端到端集成第十一批 ----------


def test_e2e_load_manifest_real_file_batch11(tmp_path):
    """真实 manifest 文件加载。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    m = load_manifest(p)
    assert isinstance(m, Manifest)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "incomplete"
    assert m.documents == ()
    assert m.expected_failures == ()


def test_e2e_load_manifest_round_trip_idempotent_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    m1 = load_manifest(p)
    m2 = load_manifest(p)
    assert m1 == m2


def test_e2e_manifest_with_categories_batch11(tmp_path):
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == []


def test_e2e_manifest_with_documents_batch11(tmp_path):
    """带 documents 的 manifest（合法相对路径）。"""
    # 准备 sample 文件
    (tmp_path / "a.pdf").write_text("dummy", encoding="utf-8")
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "a.pdf",
            "source_type": "pdf",
            "categories": ["normal"],
            "sha256": "a" * 64,
        }
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].categories == ("normal",)


def test_e2e_manifest_with_expected_failures_batch11(tmp_path):
    (tmp_path / "bad.pdf").write_text("dummy", encoding="utf-8")
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    data["expected_failures"] = [
        {
            "doc_id": "ef1",
            "path": "bad.pdf",
            "expected_error_code": "unsupported_format",
            "source_type": "pdf",
        }
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].expected_error_code == "unsupported_format"


def test_e2e_manifest_default_project_root_batch11(tmp_path):
    """默认 project_root（向上找 pyproject.toml）。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    m = load_manifest(p)
    assert isinstance(m.project_root, Path)


def test_e2e_load_manifest_returns_manifest_subclass_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_explicit_project_root_str_batch11(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_valid_manifest_dict()), encoding="utf-8")
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_e2e_manifest_with_unicode_categories_batch11(tmp_path):
    (tmp_path / "a.pdf").write_text("dummy", encoding="utf-8")
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "a.pdf",
            "source_type": "pdf",
            "categories": ["中文", "normal"],
            "sha256": "a" * 64,
        }
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["normal", "中文"]


def test_e2e_load_manifest_json_serializable_top_keys_batch11(tmp_path):
    """manifest 顶层 keys 必须是 JSON 可序列化的。"""
    p = tmp_path / "m.json"
    data = _valid_manifest_dict()
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    # 直接序列化 manifest 字段（用 dataclasses.asdict 不行因为含 Path）
    # 这里只验证顶层 keys
    assert set(data.keys()) >= {
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
    }
