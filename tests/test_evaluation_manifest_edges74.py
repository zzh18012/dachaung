"""evaluation/manifest.py 第八十九轮 edges 测试（Round 653）。

补强 edges73 未触及的角度（第四十八批）。

新角度：
- _is_absolute_like Unicode 字母（中文 drive / 日文 drive / 韩文 drive / 俄文 drive / 阿拉伯文 drive）
- _is_absolute_like 数字与特殊字符（数字 drive / 下划线 drive / 空字符串 / 只有冒号 / 1 字符 / 2 字符）
- _has_backslash 多位置
- _resolve_relative_path 错误信息精确（包含 field_name）
- load_manifest project_root None vs 显式
- load_manifest expected_failures 多字段组合（含 source_type / 缺 source_type / 多 expected_failures）
- Manifest property 完整性（双向配对 / 单向配对 / 多组 / 0 文档 / 文档无 categories）
- _detect_project_root 多场景（pyproject 父级 / 嵌套深 / 无 pyproject 返回 curdir / 文件输入取 parent）
- DocumentEntry frozen 完整性（所有字段 setattr 抛 FrozenInstanceError）
- ExpectedFailure frozen 完整性
- Manifest frozen 完整性
- 模块源码补强
- AST 结构补强
- forbidden tokens 第一百二十三批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.manifest as manifest_mod
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


# ---------- _is_absolute_like Unicode 字母 ----------

def test_is_absolute_like_chinese_drive_batch48():
    """中文 drive 字母（isalpha 返回 True）→ 视为绝对路径。"""
    assert _is_absolute_like("中:/foo") is True


def test_is_absolute_like_japanese_drive_batch48():
    assert _is_absolute_like("あ:/foo") is True


def test_is_absolute_like_korean_drive_batch48():
    assert _is_absolute_like("가:/foo") is True


def test_is_absolute_like_cyrillic_drive_batch48():
    assert _is_absolute_like("Д:/foo") is True


def test_is_absolute_like_arabic_drive_batch48():
    assert _is_absolute_like("م:/foo") is True


def test_is_absolute_like_emoji_drive_batch48():
    """emoji 不是 isalpha → 不是绝对路径。"""
    assert _is_absolute_like("😀:/foo") is False


# ---------- _is_absolute_like 数字与特殊字符 ----------

def test_is_absolute_like_digit_drive_batch48():
    """数字 drive：isalpha False → 不是绝对路径。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_drive_batch48():
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_dot_drive_batch48():
    assert _is_absolute_like(".:/foo") is False


def test_is_absolute_like_dash_drive_batch48():
    assert _is_absolute_like("-:/foo") is False


def test_is_absolute_like_empty_string_batch48():
    assert _is_absolute_like("") is False


def test_is_absolute_like_only_colon_batch48():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_one_char_batch48():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_chars_batch48():
    """2 字符不够长（< 3）→ False。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_three_chars_no_separator_batch48():
    """3 字符但第 3 个不是 \\ 或 / → False。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_three_chars_dash_batch48():
    assert _is_absolute_like("a:-") is False


# ---------- _has_backslash 多位置 ----------

def test_has_backslash_at_start_batch48():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end_batch48():
    assert _has_backslash("foo\\") is True


def test_has_backslash_in_middle_batch48():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_multiple_batch48():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_backslash_batch48():
    assert _has_backslash("\\") is True


def test_has_backslash_no_backslash_batch48():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_empty_string_batch48():
    assert _has_backslash("") is False


def test_has_backslash_all_forward_batch48():
    assert _has_backslash("a/b/c") is False


# ---------- _resolve_relative_path 错误信息精确 ----------

def test_resolve_relative_path_error_includes_field_name_batch48(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


def test_resolve_relative_path_empty_includes_field_name_batch48(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "EMPTY_FIELD")
    assert "EMPTY_FIELD" in str(ei.value)


def test_resolve_relative_path_absolute_includes_field_name_batch48(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "ABS_FIELD")
    assert "ABS_FIELD" in str(ei.value)


def test_resolve_relative_path_backslash_includes_field_name_batch48(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b", tmp_path, "BS_FIELD")
    assert "BS_FIELD" in str(ei.value)


def test_resolve_relative_path_outside_root_includes_field_name_batch48(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../../etc/passwd", tmp_path, "OUT_FIELD")
    assert "OUT_FIELD" in str(ei.value)


def test_resolve_relative_path_success_returns_absolute_batch48(tmp_path):
    out = _resolve_relative_path("foo/bar.txt", tmp_path, "OK")
    assert out.is_absolute()
    assert out.name == "bar.txt"


def test_resolve_relative_path_success_in_root_batch48(tmp_path):
    out = _resolve_relative_path("foo/bar.txt", tmp_path, "OK")
    assert str(out).startswith(str(tmp_path.resolve()))


# ---------- load_manifest project_root None vs 显式 ----------

def _write_valid_manifest(tmp_path: Path) -> Path:
    """写一个最小合法 manifest 到 tmp_path 下并返回其路径。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    # 在 tmp_path 下制造 pyproject.toml 让 _detect_project_root 找到 tmp_path
    (tmp_path / "pyproject.toml").write_text("# test", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    return p


def test_load_manifest_detect_project_root_batch48(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_explicit_project_root_batch48(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_project_root_str_batch48(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_missing_file_raises_batch48(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path / "missing.json")
    assert "不存在" in str(ei.value)


def test_load_manifest_invalid_json_raises_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("# test", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p)
    assert "JSON" in str(ei.value) or "解析" in str(ei.value)


# ---------- load_manifest expected_failures 多字段组合 ----------

def test_load_manifest_expected_failures_with_source_type_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("# t", encoding="utf-8")
    (tmp_path / "fail.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "f1",
                "path": "fail.pdf",
                "expected_error_code": "E_PARSE",
                "source_type": "pdf",
            }
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "f1"
    assert ef.expected_error_code == "E_PARSE"
    assert ef.source_type == "pdf"


def test_load_manifest_expected_failures_without_source_type_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("# t", encoding="utf-8")
    (tmp_path / "fail.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "f1",
                "path": "fail.pdf",
                "expected_error_code": "E_PARSE",
            }
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_expected_failures_multiple_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("# t", encoding="utf-8")
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "a.pdf", "expected_error_code": "E_PARSE"},
            {"doc_id": "f2", "path": "b.pdf", "expected_error_code": "E_OCR"},
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert len(m.expected_failures) == 2


def test_load_manifest_no_expected_failures_key_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("# t", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert m.expected_failures == ()


# ---------- Manifest property 完整性 ----------

def _make_doc(doc_id="d1", source_type="pdf", paired_with=None, categories=("a",)):
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


def test_manifest_categories_covered_empty_batch48():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted_unique_batch48():
    docs = (
        _make_doc("d1", categories=("b", "a")),
        _make_doc("d2", categories=("c", "a")),
    )
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_pdf_count_batch48():
    docs = (
        _make_doc("d1", source_type="pdf"),
        _make_doc("d2", source_type="docx"),
        _make_doc("d3", source_type="pdf"),
    )
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    assert m.pdf_count == 2


def test_manifest_docx_count_batch48():
    docs = (
        _make_doc("d1", source_type="pdf"),
        _make_doc("d2", source_type="docx"),
        _make_doc("d3", source_type="docx"),
    )
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    assert m.docx_count == 2


def test_manifest_file_count_batch48():
    docs = (_make_doc("d1"), _make_doc("d2"), _make_doc("d3"))
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    assert m.file_count == 3


def test_manifest_content_group_count_all_unpaired_batch48():
    docs = (_make_doc("d1"), _make_doc("d2"))
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    assert m.content_group_count == 2


def test_manifest_content_group_count_mutual_pair_batch48():
    docs = (
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
    )
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    # 双向配对 = 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_one_way_pair_batch48():
    """单向配对也算一组（避免重复计数）。"""
    docs = (
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2"),  # 不反向配对
    )
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    # d1 paired_with d2，d2 不配对 → pair_ids = {frozenset(d1, d2)}, groups = 1
    # seen = {d1, d2}，d2 在 seen 中，unpaired = 0
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch48():
    docs = (
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
        _make_doc("d3"),  # unpaired
        _make_doc("d4"),  # unpaired
    )
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    # 1 组（d1-d2）+ 2 unpaired（d3, d4） = 3
    assert m.content_group_count == 3


def test_manifest_content_group_count_two_pairs_batch48():
    docs = (
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
        _make_doc("d3", paired_with="d4"),
        _make_doc("d4", paired_with="d3"),
    )
    m = Manifest("1.0", "complete", docs, (), Path("/tmp"))
    assert m.content_group_count == 2


# ---------- _detect_project_root 多场景 ----------

def test_detect_project_root_with_pyproject_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("# t", encoding="utf-8")
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


def test_detect_project_root_file_input_batch48(tmp_path):
    """文件输入 → 取 parent。"""
    (tmp_path / "pyproject.toml").write_text("# t", encoding="utf-8")
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_curdir_batch48(tmp_path):
    """无 pyproject.toml → 返回 curdir（start 的 parent 或 start）。"""
    sub = tmp_path / "sub"
    sub.mkdir(parents=True)
    out = _detect_project_root(sub)
    assert out == sub.resolve()


def test_detect_project_root_nested_deep_batch48(tmp_path):
    (tmp_path / "pyproject.toml").write_text("# t", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    out = _detect_project_root(deep)
    assert out == tmp_path.resolve()


# ---------- DocumentEntry frozen 完整性 ----------

def test_document_entry_frozen_doc_id_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"


def test_document_entry_frozen_path_str_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.path_str = "x"


def test_document_entry_frozen_resolved_path_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.resolved_path = Path("/x")


def test_document_entry_frozen_source_type_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.source_type = "docx"


def test_document_entry_frozen_sha256_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.sha256 = "x"


def test_document_entry_frozen_categories_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.categories = ("x",)


def test_document_entry_frozen_paired_with_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.paired_with = "x"


def test_document_entry_frozen_annotation_file_str_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.annotation_file_str = "x"


def test_document_entry_frozen_annotation_resolved_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.annotation_resolved = Path("/x")


def test_document_entry_frozen_expectations_batch48():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.expectations = {"x": 1}


# ---------- ExpectedFailure frozen 完整性 ----------

def _make_ef(**kw):
    return ExpectedFailure(
        doc_id=kw.get("doc_id", "f1"),
        path_str=kw.get("path_str", "f1.pdf"),
        resolved_path=kw.get("resolved_path", Path("/tmp/f1.pdf")),
        expected_error_code=kw.get("expected_error_code", "E_PARSE"),
        source_type=kw.get("source_type"),
    )


def test_expected_failure_frozen_doc_id_batch48():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"


def test_expected_failure_frozen_path_str_batch48():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.path_str = "x"


def test_expected_failure_frozen_resolved_path_batch48():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.resolved_path = Path("/x")


def test_expected_failure_frozen_expected_error_code_batch48():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.expected_error_code = "x"


def test_expected_failure_frozen_source_type_batch48():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.source_type = "pdf"


# ---------- Manifest frozen 完整性 ----------

def test_manifest_frozen_documents_batch48():
    m = Manifest("1.0", "complete", (), (), Path("/tmp"))
    with pytest.raises(FrozenInstanceError):
        m.documents = ()


def test_manifest_frozen_project_root_batch48():
    m = Manifest("1.0", "complete", (), (), Path("/tmp"))
    with pytest.raises(FrozenInstanceError):
        m.project_root = Path("/x")


def test_manifest_frozen_devset_status_batch48():
    m = Manifest("1.0", "complete", (), (), Path("/tmp"))
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "incomplete"


def test_manifest_frozen_manifest_version_batch48():
    m = Manifest("1.0", "complete", (), (), Path("/tmp"))
    with pytest.raises(FrozenInstanceError):
        m.manifest_version = "2.0"


def test_manifest_frozen_expected_failures_batch48():
    m = Manifest("1.0", "complete", (), (), Path("/tmp"))
    with pytest.raises(FrozenInstanceError):
        m.expected_failures = ()


# ---------- ManifestError 抛出场景 ----------

def test_manifest_error_is_exception_batch48():
    e = ManifestError("msg")
    assert isinstance(e, Exception)


def test_manifest_error_can_be_raised_and_caught_batch48():
    with pytest.raises(ManifestError):
        raise ManifestError("x")


def test_manifest_error_str_contains_message_batch48():
    e = ManifestError("hello")
    assert "hello" in str(e)


def test_manifest_error_no_errors_attr_batch48():
    """ManifestError 不带 errors 属性（与 EvalSchemaError 区别）。"""
    e = ManifestError("x")
    assert not hasattr(e, "errors")


def test_manifest_error_args_batch48():
    e = ManifestError("a", "b")
    assert e.args == ("a", "b")


# ---------- 模块源码补强 ----------

def test_source_contains_json_import_batch48():
    src = inspect.getsource(manifest_mod)
    assert "import json" in src


def test_source_contains_dataclass_import_batch48():
    src = inspect.getsource(manifest_mod)
    assert "from dataclasses import dataclass" in src


def test_source_contains_pathlib_import_batch48():
    src = inspect.getsource(manifest_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch48():
    src = inspect.getsource(manifest_mod)
    assert "from typing import Any" in src


def test_source_contains_manifest_version_import_batch48():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_source_contains_validate_import_batch48():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation.schema import validate" in src


def test_source_contains_class_manifest_error_batch48():
    src = inspect.getsource(manifest_mod)
    assert "class ManifestError" in src


def test_source_contains_class_document_entry_batch48():
    src = inspect.getsource(manifest_mod)
    assert "class DocumentEntry" in src


def test_source_contains_class_expected_failure_batch48():
    src = inspect.getsource(manifest_mod)
    assert "class ExpectedFailure" in src


def test_source_contains_class_manifest_batch48():
    src = inspect.getsource(manifest_mod)
    assert "class Manifest" in src


def test_source_contains_frozen_true_batch48():
    """3 个 dataclass 都 frozen=True。"""
    src = inspect.getsource(manifest_mod)
    # 至少 3 次 @dataclass(frozen=True)
    assert src.count("@dataclass(frozen=True)") == 3


def test_source_contains_no_absolute_path_rule_batch48():
    """docstring 提到拒绝绝对路径。"""
    src = inspect.getsource(manifest_mod)
    assert "绝对路径" in src


def test_source_contains_backslash_rule_batch48():
    """docstring 提到拒绝反斜杠。"""
    src = inspect.getsource(manifest_mod)
    assert "反斜杠" in src


def test_source_contains_project_root_rule_batch48():
    """docstring 提到项目根目录。"""
    src = inspect.getsource(manifest_mod)
    assert "项目根" in src


def test_source_contains_property_decorators_batch48():
    """Manifest 有 5 个 @property。"""
    src = inspect.getsource(manifest_mod)
    assert src.count("@property") == 5


def test_source_contains_all_list_batch48():
    src = inspect.getsource(manifest_mod)
    assert "__all__" in src


def test_source_all_contains_5_entries_batch48():
    src = inspect.getsource(manifest_mod)
    for name in ("ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"):
        assert name in src


def test_source_contains_resolve_relative_to_batch48():
    src = inspect.getsource(manifest_mod)
    assert "relative_to" in src


def test_source_contains_isfile_check_batch48():
    src = inspect.getsource(manifest_mod)
    assert "is_file()" in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5  # _is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root


def test_ast_top_level_class_count_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4  # ManifestError, DocumentEntry, ExpectedFailure, Manifest


def test_ast_no_async_function_def_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_document_entry_field_count_batch48():
    """DocumentEntry 10 个字段。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "DocumentEntry")
    ann_assigns = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(ann_assigns) == 10


def test_ast_expected_failure_field_count_batch48():
    """ExpectedFailure 5 个字段。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "ExpectedFailure")
    ann_assigns = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(ann_assigns) == 5


def test_ast_manifest_field_count_batch48():
    """Manifest 5 个字段。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "Manifest")
    ann_assigns = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(ann_assigns) == 5


def test_ast_manifest_property_count_batch48():
    """Manifest 5 个 @property 方法。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "Manifest")
    properties = [
        n for n in cls.body
        if isinstance(n, ast.FunctionDef)
        and any(
            isinstance(d, ast.Name) and d.id == "property"
            or isinstance(d, ast.Attribute) and d.attr == "property"
            for d in n.decorator_list
        )
    ]
    assert len(properties) == 5


def test_ast_manifest_error_no_methods_batch48():
    """ManifestError 体只有 docstring，无方法。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "ManifestError")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 0


def test_ast_load_manifest_has_multiple_for_batch48():
    """load_manifest 至少 2 个 for（documents + expected_failures）。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 2


def test_ast_load_manifest_has_try_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_resolve_relative_path_has_try_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_resolve_relative_path_has_multiple_if_batch48():
    """_resolve_relative_path 至少 3 个 if（empty / abs / backslash）。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3


def test_ast_is_absolute_like_has_multiple_if_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_absolute_like")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3


def test_ast_detect_project_root_has_for_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_detect_project_root_has_if_batch48():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 2


def test_ast_module_top_level_assign_count_batch48():
    """模块顶部 Assign：__all__ = 1。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 1


def test_ast_module_top_level_import_count_batch48():
    """模块顶部 import：__future__ / json / dataclass / Path / Any / MANIFEST_VERSION / validate = 7。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 7


# ---------- forbidden tokens 第一百二十三批 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_no_eval_batch48():
    assert "eval(" not in _src()


def test_source_no_exec_batch48():
    assert "exec(" not in _src()


def test_source_no_compile_batch48():
    assert "compile(" not in _src()


def test_source_no_globals_batch48():
    assert "globals(" not in _src()


def test_source_no_os_system_batch48():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch48():
    assert "subprocess" not in _src()


def test_source_no_popen_batch48():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch48():
    assert "yield" not in _src()


def test_source_no_async_def_batch48():
    assert "async def" not in _src()
