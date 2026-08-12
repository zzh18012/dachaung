"""evaluation/manifest.py 第五十七轮 edges 测试（Round 531）。

补强 edges56 未触及的角度（第三十批）：
- ManifestError 第三十批：args 只含 message / 多次 raise / 字典 message / 嵌套 except
- _is_absolute_like 第三十批：长字符串 / 双字母 / 仅斜杠 / .. 开头
- _has_backslash 第三十批：与 forward slash 同时 / 中段含 backslash / 末尾 backslash
- DocumentEntry 第三十批：eq / repr / 默认值 None / 字段保留 None
- ExpectedFailure 第三十批：source_type=None 默认 / eq / hash 相等
- Manifest 第三十批：file_count == len / pdf+docx 关系 / unpaired content_group / hash 一致
- _resolve_relative_path 第三十批：./ 前缀 / 多层 .. / message 含 resolved / 返回 absolute
- load_manifest 第三十批：manifest_path 是 str / project_root 是 str / 缺 documents key / 缺 devset_status / documents doc_id 缺失
- _detect_project_root 第三十批：祖父级含 pyproject / 多个 pyproject 选最近
- module source forbidden tokens 第四十七批
- module source 字符串精确补强第四十三批
- signatures 第四十三批
- module 合理性第四十三批
- 端到端集成第四十三批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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


# ---------- ManifestError 第三十批 ----------


def test_manifest_error_args_just_message_batch30():
    e = ManifestError("msg")
    assert e.args == ("msg",)


def test_manifest_error_raised_multiple_times_batch30():
    """循环里多次 raise。"""
    for i in range(3):
        try:
            raise ManifestError(f"msg{i}")
        except ManifestError as e:
            assert f"msg{i}" in str(e)


def test_manifest_error_dict_in_message_batch30():
    """message 含 dict 字面量。"""
    e = ManifestError("errors: {'a': 1}")
    assert "errors" in str(e)


def test_manifest_error_inheritance_chain_batch30():
    assert issubclass(ManifestError, Exception)
    assert issubclass(ManifestError, BaseException)


def test_manifest_error_caught_as_value_error_batch30():
    """ManifestError 不是 ValueError 子类，但 catch Exception。"""
    try:
        raise ManifestError("x")
    except Exception as e:
        assert not isinstance(e, ValueError)


def test_manifest_error_str_equals_message_batch30():
    """str(e) == message（无额外 prefix）。"""
    e = ManifestError("hello world")
    assert str(e) == "hello world"


def test_manifest_error_can_be_chained_batch30():
    """raise ... from ... 链式。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as inner:
            raise ManifestError("outer") from inner
    except ManifestError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


# ---------- _is_absolute_like 第三十批 ----------


def test_is_absolute_like_long_string_with_drive_batch30():
    """长字符串 + 盘符 → True。"""
    assert _is_absolute_like("C:/Users/zzhn2/Desktop/x.pdf") is True


def test_is_absolute_like_two_letters_no_colon_batch30():
    """AB/foo → False（盘符要 +冒号 +斜杠）。"""
    assert _is_absolute_like("AB/foo") is False


def test_is_absolute_like_only_slash_batch30():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_dot_dot_start_batch30():
    """../foo → False（不是绝对路径）。"""
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_tilde_start_batch30():
    """~ 起头 → False。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_double_drive_batch30():
    """CC:/foo → False（盘符只允许单字母）。"""
    assert _is_absolute_like("CC:/foo") is False


# ---------- _has_backslash 第三十批 ----------


def test_has_backslash_with_forward_and_back_batch30():
    """同时含 / 和 \\ → True。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_in_middle_batch30():
    assert _has_backslash("a/b\\c/d") is True


def test_has_backslash_at_end_batch30():
    assert _has_backslash("foo\\") is True


def test_has_backslash_at_start_batch30():
    assert _has_backslash("\\foo") is True


def test_has_backslash_only_forward_batch30():
    assert _has_backslash("a/b/c") is False


# ---------- DocumentEntry 第三十批 ----------


def _make_doc_entry(**overrides) -> DocumentEntry:
    defaults = dict(
        doc_id="d1",
        path_str="samples/x.pdf",
        resolved_path=Path("/repo/samples/x.pdf"),
        source_type="pdf",
        sha256="a" * 64,
        categories=("finance",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_eq_batch30():
    """同字段的两个 DocumentEntry 相等。"""
    e1 = _make_doc_entry()
    e2 = _make_doc_entry()
    assert e1 == e2


def test_document_entry_neq_when_differ_batch30():
    """doc_id 不同 → 不等。"""
    e1 = _make_doc_entry(doc_id="d1")
    e2 = _make_doc_entry(doc_id="d2")
    assert e1 != e2


def test_document_entry_repr_has_class_name_batch30():
    e = _make_doc_entry()
    r = repr(e)
    assert "DocumentEntry" in r


def test_document_entry_default_none_preserved_batch30():
    """sha256=None 被保留。"""
    e = _make_doc_entry(sha256=None)
    assert e.sha256 is None


def test_document_entry_categories_tuple_preserved_batch30():
    """categories 必须是 tuple（frozen）。"""
    e = _make_doc_entry(categories=("a", "b"))
    assert isinstance(e.categories, tuple)
    assert e.categories == ("a", "b")


def test_document_entry_expectations_dict_preserved_batch30():
    """expectations 可以是 dict。"""
    e = _make_doc_entry(expectations={"element_count_by_type": {"paragraph": 5}})
    assert e.expectations == {"element_count_by_type": {"paragraph": 5}}


# ---------- ExpectedFailure 第三十批 ----------


def test_expected_failure_source_type_defaults_none_batch30():
    """source_type 无默认值；必须显式传 None 或值。"""
    ef = ExpectedFailure(
        doc_id="b1",
        path_str="bad.pdf",
        resolved_path=Path("/repo/bad.pdf"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_eq_batch30():
    ef1 = ExpectedFailure("d1", "p", Path("/p"), "code", None)
    ef2 = ExpectedFailure("d1", "p", Path("/p"), "code", None)
    assert ef1 == ef2


def test_expected_failure_repr_has_class_name_batch30():
    ef = ExpectedFailure("d1", "p", Path("/p"), "code", None)
    assert "ExpectedFailure" in repr(ef)


def test_expected_failure_hash_eq_consistent_batch30():
    """eq 的两个 ExpectedFailure hash 相等。"""
    ef1 = ExpectedFailure("d1", "p", Path("/p"), "code", None)
    ef2 = ExpectedFailure("d1", "p", Path("/p"), "code", None)
    assert hash(ef1) == hash(ef2)


def test_expected_failure_expected_error_code_str_batch30():
    ef = ExpectedFailure("d1", "p", Path("/p"), "my_error_code", None)
    assert ef.expected_error_code == "my_error_code"


# ---------- Manifest 第三十批 ----------


def _make_manifest(**overrides) -> Manifest:
    defaults = dict(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/repo"),
    )
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_file_count_equals_len_batch30():
    docs = (_make_doc_entry(doc_id=f"d{i}") for i in range(3))
    m = _make_manifest(documents=tuple(docs))
    assert m.file_count == len(m.documents) == 3


def test_manifest_pdf_plus_docx_le_file_count_batch30():
    """pdf_count + docx_count <= file_count。"""
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="pdf"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count + m.docx_count == m.file_count


def test_manifest_content_group_count_unpaired_batch30():
    """3 个 unpaired 文档 → 3 组。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with=None),
        _make_doc_entry(doc_id="d2", paired_with=None),
        _make_doc_entry(doc_id="d3", paired_with=None),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_hash_eq_consistent_batch30():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert hash(m1) == hash(m2)


def test_manifest_pdf_count_with_only_docx_batch30():
    docs = (_make_doc_entry(doc_id="d1", source_type="docx"),)
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_manifest_docx_count_with_only_pdf_batch30():
    docs = (_make_doc_entry(doc_id="d1", source_type="pdf"),)
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 1
    assert m.docx_count == 0


def test_manifest_categories_covered_empty_batch30():
    m = _make_manifest()
    assert m.categories_covered == []


def test_manifest_documents_is_tuple_batch30():
    docs = (_make_doc_entry(doc_id="d1"),)
    m = _make_manifest(documents=docs)
    assert isinstance(m.documents, tuple)


# ---------- _resolve_relative_path 第三十批 ----------


def test_resolve_relative_path_dot_slash_prefix_batch30(tmp_path):
    """./foo 形式 → 仍然合法（resolve 后位于 project_root 内）。"""
    (tmp_path / "foo").mkdir()
    (tmp_path / "foo" / "x.pdf").touch()
    result = _resolve_relative_path("./foo/x.pdf", tmp_path, "f")
    assert result.is_file()


def test_resolve_relative_path_double_dot_dot_batch30(tmp_path):
    """多层 .. → 越界。"""
    (tmp_path / "samples").mkdir()
    with pytest.raises(ManifestError):
        _resolve_relative_path("../../etc/passwd", tmp_path / "samples", "f")


def test_resolve_relative_path_message_contains_resolved_batch30(tmp_path):
    """越界错误的 message 含 resolved 路径。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../escape", tmp_path, "f")
    assert "escape" in str(exc.value)


def test_resolve_relative_path_returns_absolute_batch30(tmp_path):
    """返回值是 absolute path。"""
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "y").touch()
    result = _resolve_relative_path("x/y", tmp_path, "f")
    assert result.is_absolute()


def test_resolve_relative_path_within_root_subdir_batch30(tmp_path):
    """路径在 root 子目录内合法。"""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "a" / "b" / "c").mkdir()
    (tmp_path / "a" / "b" / "c" / "d.txt").touch()
    result = _resolve_relative_path("a/b/c/d.txt", tmp_path, "f")
    assert result.name == "d.txt"


def test_resolve_relative_path_idempotent_batch30(tmp_path):
    """多次调用得到相同结果。"""
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "y").touch()
    r1 = _resolve_relative_path("x/y", tmp_path, "f")
    r2 = _resolve_relative_path("x/y", tmp_path, "f")
    assert r1 == r2


# ---------- load_manifest 第三十批 ----------


def test_load_manifest_accepts_str_path_batch30(tmp_path):
    """manifest_path 可以是 str。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert isinstance(m, Manifest)


def test_load_manifest_project_root_str_batch30(tmp_path):
    """project_root 是 str。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_missing_documents_key_ok_batch30(tmp_path):
    """documents 缺失 → schema 拒绝（required）→ EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({"manifest_version": MANIFEST_VERSION, "devset_status": "complete"}),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_missing_devset_status_batch30(tmp_path):
    """devset_status 缺失 → schema 拒绝。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": MANIFEST_VERSION, "documents": []}
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_document_missing_doc_id_batch30(tmp_path):
    """documents 元素缺 doc_id → schema 拒绝。"""
    from evaluation.schema import EvalSchemaError
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [{"path": "x.pdf", "source_type": "pdf"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_no_modification_batch30(tmp_path):
    """加载后文件不变。"""
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    content = json.dumps(
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "complete",
            "documents": [{"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}],
        }
    )
    p.write_text(content, encoding="utf-8")
    load_manifest(p, project_root=tmp_path)
    assert p.read_text(encoding="utf-8") == content


def test_load_manifest_idempotent_batch30(tmp_path):
    """两次加载得到相同 Manifest。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_load_manifest_categories_passed_through_batch30(tmp_path):
    """categories 字段透传到 DocumentEntry。"""
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "x.pdf",
                        "source_type": "pdf",
                        "categories": ["a", "b"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("a", "b")


# ---------- _detect_project_root 第三十批 ----------


def test_detect_project_root_grandparent_batch30(tmp_path):
    """祖父级含 pyproject → 返回祖父级。"""
    (tmp_path / "pyproject.toml").touch()
    sub = tmp_path / "a" / "b" / "c"
    sub.mkdir(parents=True)
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_multiple_pyproject_picks_nearest_batch30(tmp_path):
    """多个 pyproject.toml → 返回最近的（最深的）。"""
    (tmp_path / "pyproject.toml").touch()
    mid = tmp_path / "mid"
    mid.mkdir()
    (mid / "pyproject.toml").touch()
    leaf = mid / "leaf"
    leaf.mkdir()
    result = _detect_project_root(leaf)
    assert result == mid.resolve()


def test_detect_project_root_idempotent_batch30(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    r1 = _detect_project_root(tmp_path)
    r2 = _detect_project_root(tmp_path)
    assert r1 == r2


def test_detect_project_root_with_file_in_dir_batch30(tmp_path):
    """起始 path 是文件 → 取 parent 后再找。"""
    (tmp_path / "pyproject.toml").touch()
    p = tmp_path / "x.txt"
    p.touch()
    result = _detect_project_root(p)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_existing_dir_batch30(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    result = _detect_project_root(tmp_path)
    assert result.is_dir()


# ---------- module source forbidden tokens 第四十七批 ----------


def test_module_source_no_subprocess_batch30():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch30():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch30():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch30():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch30():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch30():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch30():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch30():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch30():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch30():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch30():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch30():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十三批 ----------


def test_module_source_contains_module_docstring_batch30():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_path_invariant_doc_batch30():
    src = inspect.getsource(mmod)
    assert "正斜杠" in src


def test_module_source_contains_no_absolute_invariant_doc_batch30():
    src = inspect.getsource(mmod)
    assert "禁止绝对路径" in src


def test_module_source_contains_manifest_error_doc_batch30():
    src = inspect.getsource(mmod)
    assert "清单加载或校验失败" in src


def test_module_source_contains_dataclass_decorator_batch30():
    src = inspect.getsource(mmod)
    # frozen=True 出现在 decorator 里
    assert "frozen=True" in src


def test_module_source_contains_is_absolute_like_func_batch30():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like" in src


def test_module_source_contains_disk_letter_comment_batch30():
    src = inspect.getsource(mmod)
    assert "Windows 盘符" in src


def test_module_source_contains_resolve_relative_path_func_batch30():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path" in src


def test_module_source_contains_load_manifest_func_batch30():
    src = inspect.getsource(mmod)
    assert "def load_manifest" in src


def test_module_source_contains_detect_project_root_func_batch30():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root" in src


def test_module_source_contains_pdf_count_property_batch30():
    src = inspect.getsource(mmod)
    assert "def pdf_count" in src


def test_module_source_contains_docx_count_property_batch30():
    src = inspect.getsource(mmod)
    assert "def docx_count" in src


def test_module_source_contains_content_group_count_property_batch30():
    src = inspect.getsource(mmod)
    assert "def content_group_count" in src


def test_module_source_contains_pair_ids_local_batch30():
    src = inspect.getsource(mmod)
    assert "pair_ids" in src


# ---------- signatures 第四十三批 ----------


def test_signature_is_absolute_like_path_str_batch30():
    sig = inspect.signature(_is_absolute_like)
    assert sig.parameters["path_str"].annotation == "str"


def test_signature_is_absolute_like_return_bool_batch30():
    sig = inspect.signature(_is_absolute_like)
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_return_bool_batch30():
    sig = inspect.signature(_has_backslash)
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_field_name_annotation_batch30():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.parameters["field_name"].annotation == "str"


def test_signature_resolve_relative_path_project_root_annotation_batch30():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.parameters["project_root"].annotation == "Path"


def test_signature_load_manifest_manifest_path_annotation_batch30():
    sig = inspect.signature(load_manifest)
    ps = sig.parameters["manifest_path"].annotation
    assert "Path" in ps and "str" in ps


def test_signature_load_manifest_project_root_annotation_batch30():
    sig = inspect.signature(load_manifest)
    ps = sig.parameters["project_root"].annotation
    assert "Path" in ps and "str" in ps and "None" in ps


def test_signature_detect_project_root_start_annotation_batch30():
    sig = inspect.signature(_detect_project_root)
    assert sig.parameters["start"].annotation == "Path"


# ---------- module 合理性第四十三批 ----------


def test_module_has_future_annotations_batch30():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch30():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch30():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch30():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch30():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_no_main_block_batch30():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


def test_module_has_all_export_batch30():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_all_has_manifest_error_batch30():
    src = inspect.getsource(mmod)
    assert '"ManifestError"' in src


def test_module_all_has_load_manifest_batch30():
    src = inspect.getsource(mmod)
    assert '"load_manifest"' in src


# ---------- 端到端集成第四十三批 ----------


def test_e2e_full_manifest_with_annotation_file_batch30(tmp_path):
    """端到端：含 annotation_file 的文档。"""
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    (tmp_path / "samples" / "x.json").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/x.pdf",
                        "source_type": "pdf",
                        "annotation_file": "samples/x.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "samples/x.json"
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved.is_file()


def test_e2e_manifest_with_expected_failures_batch30(tmp_path):
    """端到端：含 expected_failures 的清单。"""
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "broken.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
                "expected_failures": [
                    {
                        "doc_id": "b1",
                        "path": "bad/broken.pdf",
                        "expected_error_code": "unsupported_format",
                        "source_type": "pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "b1"
    assert ef.expected_error_code == "unsupported_format"
    assert ef.source_type == "pdf"


def test_e2e_unpaired_documents_count_batch30(tmp_path):
    """端到端：3 个 unpaired → content_group_count=3。"""
    (tmp_path / "samples").mkdir()
    for i in range(3):
        (tmp_path / "samples" / f"{i}.pdf").touch()
    docs = [
        {"doc_id": f"d{i}", "path": f"samples/{i}.pdf", "source_type": "pdf"}
        for i in range(3)
    ]
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": docs,
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 3


def test_e2e_categories_aggregated_batch30(tmp_path):
    """端到端：多文档 categories 聚合去重排序。"""
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").touch()
    (tmp_path / "samples" / "b.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "categories": ["finance", "report"],
                    },
                    {
                        "doc_id": "d2",
                        "path": "samples/b.pdf",
                        "source_type": "pdf",
                        "categories": ["finance", "legal"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["finance", "legal", "report"]


def test_e2e_load_manifest_preserves_devset_status_batch30(tmp_path):
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "incomplete"


def test_e2e_load_manifest_manifest_version_preserved_batch30(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == MANIFEST_VERSION


def test_e2e_manifest_is_hashable_after_load_batch30(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    s = {m}
    assert m in s
