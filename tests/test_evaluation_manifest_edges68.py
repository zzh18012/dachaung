"""evaluation/manifest.py 第六十九轮 edges 测试（Round 605）。

补强 edges67 未触及的角度（第四十一批）。

新角度：
- _is_absolute_like 多字节盘符（中文 / 日文 / 韩文 / emoji）行为
- _is_absolute_like 边界长度（< 3 / == 3 / > 3）
- _is_absolute_like 第二字符非冒号
- _is_absolute_like 第三字符非斜杠
- _is_absolute_like 数字开头
- _is_absolute_like None 安全（先 isinstance 检查）
- _has_backslash 边界（无 / 单 / 多 / 末尾 / 开头）
- _resolve_relative_path "path/to"（深度相对）允许
- _resolve_relative_path "./foo" 允许
- _resolve_relative_path "foo/" 末尾斜杠允许
- _resolve_relative_path 字段名透传到错误消息
- DocumentEntry 默认值（sha256/paired_with/annotation_file_str/annotation_resolved/expectations）
- DocumentEntry frozen（赋值抛 FrozenInstanceError）
- ExpectedFailure 默认值（source_type=None）
- ExpectedFailure frozen
- Manifest 默认值
- Manifest.file_count / pdf_count / docx_count 边界（empty）
- Manifest.content_group_count 复杂配对
- Manifest.categories_covered 排序
- _detect_project_root 从文件 / 从目录
- _detect_project_root 无 pyproject.toml 退回 cur
- load_manifest 默认 project_root（_detect_project_root 调用）
- load_manifest 字段缺失（path 缺 → EvalSchemaError）
- load_manifest expected_failures 缺（默认空）
- load_manifest devset_status 值（complete / incomplete / partial）
- module source 字符串精确（含 Unicode 提示）
- AST 结构（顶层 imports/classes/functions）
- forbidden tokens 第十六批
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


# ---------- _is_absolute_like 第四十一批（多字节盘符 + 边界）


def test_is_absolute_like_chinese_drive_letter_batch41():
    """Python str.isalpha() 接受 Unicode；中:/x 也被识别为盘符绝对路径。"""
    assert _is_absolute_like("中:/x") is True


def test_is_absolute_like_japanese_drive_letter_batch41():
    assert _is_absolute_like("あ:/x") is True


def test_is_absolute_like_korean_drive_letter_batch41():
    assert _is_absolute_like("가:/x") is True


def test_is_absolute_like_cyrillic_drive_letter_batch41():
    assert _is_absolute_like("Д:/x") is True


def test_is_absolute_like_arabic_letter_batch41():
    """阿拉伯字母也是 isalpha=True。"""
    assert _is_absolute_like("ا:/x") is True


def test_is_absolute_like_emoji_not_alpha_batch41():
    """emoji 不是 isalpha（isalpha 检查 Unicode 字母属性）。"""
    assert _is_absolute_like("😀:/x") is False


def test_is_absolute_like_digit_not_alpha_batch41():
    """数字不是 isalpha。"""
    assert _is_absolute_like("1:/x") is False


def test_is_absolute_like_space_not_alpha_batch41():
    assert _is_absolute_like(" :/x") is False


def test_is_absolute_like_underscore_not_alpha_batch41():
    assert _is_absolute_like("_:/x") is False


def test_is_absolute_like_dash_not_alpha_batch41():
    assert _is_absolute_like("-:/x") is False


def test_is_absolute_like_short_string_len_1_batch41():
    """长度 1：仅 / 被识别。"""
    assert _is_absolute_like("/") is True
    assert _is_absolute_like("a") is False


def test_is_absolute_like_short_string_len_2_batch41():
    """长度 2：所有 2 字符都不可能是绝对路径（缺第三个分隔符）。"""
    assert _is_absolute_like("a:") is False
    assert _is_absolute_like("ab") is False
    assert _is_absolute_like("/a") is True  # POSIX absolute


def test_is_absolute_like_len_3_no_separator_batch41():
    """长度 3 但第三字符不是分隔符。"""
    assert _is_absolute_like("a:b") is False
    assert _is_absolute_like("a:c") is False


def test_is_absolute_like_len_3_with_separator_batch41():
    """长度 3 + 第三字符是 / 或 \\ → 绝对路径。"""
    assert _is_absolute_like("a:/x") is True
    assert _is_absolute_like("A:\\x") is True
    assert _is_absolute_like("Z:/x") is True


def test_is_absolute_like_second_char_not_colon_batch41():
    """第二字符不是冒号。"""
    assert _is_absolute_like("ab/x") is False
    assert _is_absolute_like("a-\\x") is False


def test_is_absolute_like_third_char_not_slash_batch41():
    """第三字符既不是 / 也不是 \\。"""
    assert _is_absolute_like("a:-x") is False
    assert _is_absolute_like("a:.x") is False


def test_is_absolute_like_uppercase_alpha_batch41():
    assert _is_absolute_like("C:/Windows") is True
    assert _is_absolute_like("C:\\Windows") is True


def test_is_absolute_like_lowercase_alpha_batch41():
    assert _is_absolute_like("c:/users") is True
    assert _is_absolute_like("c:\\users") is True


def test_is_absolute_like_mixed_back_forward_batch41():
    """C:\\/x —— 第三字符是 \\，被识别。"""
    assert _is_absolute_like("C:\\/x") is True


def test_is_absolute_like_only_colon_batch41():
    """只有 : 不是绝对路径。"""
    assert _is_absolute_like(":") is False
    assert _is_absolute_like("::") is False


# ---------- _has_backslash 第四十一批


def test_has_backslash_empty_batch41():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash_batch41():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_single_backslash_batch41():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_multiple_backslash_batch41():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_leading_backslash_batch41():
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing_backslash_batch41():
    assert _has_backslash("foo\\") is True


def test_has_backslash_only_backslash_batch41():
    assert _has_backslash("\\") is True


def test_has_backslash_signature_batch41():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_has_backslash_return_annotation_bool_batch41():
    sig = inspect.signature(_has_backslash)
    assert "bool" in str(sig.return_annotation)


# ---------- _resolve_relative_path 第四十一批


def test_resolve_relative_path_deep_batch41(tmp_path):
    """深层相对路径允许。"""
    out = _resolve_relative_path("a/b/c/d.pdf", tmp_path, "test")
    assert out == (tmp_path / "a" / "b" / "c" / "d.pdf").resolve()


def test_resolve_relative_path_dot_slash_batch41(tmp_path):
    """./foo 允许。"""
    out = _resolve_relative_path("./foo.pdf", tmp_path, "test")
    assert out == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_trailing_slash_batch41(tmp_path):
    """foo/ 允许（目录路径）。"""
    out = _resolve_relative_path("foo/", tmp_path, "test")
    assert out == (tmp_path / "foo").resolve()  # resolve 会去掉末尾 /


def test_resolve_relative_path_double_dot_inside_batch41(tmp_path):
    """foo/../bar 仍在 project_root 内（resolve 后 = tmp_path/bar）→ 允许。"""
    out = _resolve_relative_path("foo/../bar.pdf", tmp_path, "test")
    assert out == (tmp_path / "bar.pdf").resolve()


def test_resolve_relative_path_field_name_in_error_message_batch41(tmp_path):
    """空 path → ManifestError 消息含字段名。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "documents[d1].path")
    assert "documents[d1].path" in str(exc.value)


def test_resolve_relative_path_field_name_for_absolute_batch41(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "documents[d1].path")
    assert "documents[d1].path" in str(exc.value)


def test_resolve_relative_path_field_name_for_backslash_batch41(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("foo\\bar.pdf", tmp_path, "documents[d1].path")
    assert "documents[d1].path" in str(exc.value)


def test_resolve_relative_path_outside_root_includes_path_str_batch41(tmp_path):
    """路径解析后超出 root → 错误消息含原始 path_str 和 resolved。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../sibling/file.pdf", tmp_path, "test")
    msg = str(exc.value)
    assert "test" in msg
    assert "outside" not in msg.lower() or "外" in msg  # 中英文混用
    assert "../sibling/file.pdf" in msg


def test_resolve_relative_path_returns_resolved_path_batch41(tmp_path):
    """返回值是 resolve 过的绝对路径。"""
    out = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert out.is_absolute()


def test_resolve_relative_path_returns_path_instance_batch41(tmp_path):
    out = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_signature_batch41():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_return_annotation_path_batch41():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


# ---------- DocumentEntry 第四十一批


def _make_doc_entry(**overrides: Any) -> DocumentEntry:
    defaults: dict[str, Any] = {
        "doc_id": "d1",
        "path_str": "a.pdf",
        "resolved_path": Path("/tmp/a.pdf"),
        "source_type": "pdf",
        "sha256": None,
        "categories": (),
        "paired_with": None,
        "annotation_file_str": None,
        "annotation_resolved": None,
        "expectations": None,
    }
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_default_sha256_none_batch41():
    e = _make_doc_entry()
    assert e.sha256 is None


def test_document_entry_default_paired_with_none_batch41():
    e = _make_doc_entry()
    assert e.paired_with is None


def test_document_entry_default_annotation_file_str_none_batch41():
    e = _make_doc_entry()
    assert e.annotation_file_str is None


def test_document_entry_default_annotation_resolved_none_batch41():
    e = _make_doc_entry()
    assert e.annotation_resolved is None


def test_document_entry_default_expectations_none_batch41():
    e = _make_doc_entry()
    assert e.expectations is None


def test_document_entry_with_sha256_batch41():
    e = _make_doc_entry(sha256="abc123")
    assert e.sha256 == "abc123"


def test_document_entry_with_paired_with_batch41():
    e = _make_doc_entry(paired_with="d2")
    assert e.paired_with == "d2"


def test_document_entry_with_annotation_resolved_batch41():
    e = _make_doc_entry(annotation_resolved=Path("/tmp/ann.json"))
    assert e.annotation_resolved == Path("/tmp/ann.json")


def test_document_entry_with_expectations_batch41():
    exp = {"element_count_by_type": {"paragraph": 5}}
    e = _make_doc_entry(expectations=exp)
    assert e.expectations == exp


def test_document_entry_frozen_assign_doc_id_batch41():
    e = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "x"  # type: ignore[misc]


def test_document_entry_frozen_assign_path_str_batch41():
    e = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        e.path_str = "x"  # type: ignore[misc]


def test_document_entry_frozen_assign_resolved_path_batch41():
    e = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        e.resolved_path = Path("/tmp")  # type: ignore[misc]


def test_document_entry_frozen_assign_source_type_batch41():
    e = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        e.source_type = "x"  # type: ignore[misc]


def test_document_entry_frozen_assign_sha256_batch41():
    e = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        e.sha256 = "x"  # type: ignore[misc]


def test_document_entry_equality_batch41():
    e1 = _make_doc_entry()
    e2 = _make_doc_entry()
    assert e1 == e2


def test_document_entry_inequality_different_doc_id_batch41():
    e1 = _make_doc_entry()
    e2 = _make_doc_entry(doc_id="d2")
    assert e1 != e2


def test_document_entry_hash_batch41():
    """frozen dataclass 自动 __hash__。"""
    e = _make_doc_entry()
    assert hash(e) == hash(_make_doc_entry())


def test_document_entry_repr_batch41():
    e = _make_doc_entry()
    assert "DocumentEntry" in repr(e)


def test_document_entry_categories_default_empty_tuple_batch41():
    e = _make_doc_entry()
    assert e.categories == ()


def test_document_entry_categories_with_values_batch41():
    e = _make_doc_entry(categories=("tutorial", "intro"))
    assert e.categories == ("tutorial", "intro")


# ---------- ExpectedFailure 第四十一批


def _make_expected_failure(**overrides: Any) -> ExpectedFailure:
    defaults: dict[str, Any] = {
        "doc_id": "ef1",
        "path_str": "broken.pdf",
        "resolved_path": Path("/tmp/broken.pdf"),
        "expected_error_code": "PARSE_FAILED",
        "source_type": None,
    }
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_default_source_type_none_batch41():
    ef = _make_expected_failure()
    assert ef.source_type is None


def test_expected_failure_with_source_type_batch41():
    ef = _make_expected_failure(source_type="pdf")
    assert ef.source_type == "pdf"


def test_expected_failure_frozen_batch41():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_frozen_expected_error_code_batch41():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.expected_error_code = "x"  # type: ignore[misc]


def test_expected_failure_equality_batch41():
    ef1 = _make_expected_failure()
    ef2 = _make_expected_failure()
    assert ef1 == ef2


def test_expected_failure_hash_batch41():
    ef1 = _make_expected_failure()
    ef2 = _make_expected_failure()
    assert hash(ef1) == hash(ef2)


def test_expected_failure_repr_batch41():
    ef = _make_expected_failure()
    assert "ExpectedFailure" in repr(ef)


# ---------- Manifest 第四十一批


def _make_manifest(**overrides: Any) -> Manifest:
    defaults: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": (),
        "expected_failures": (),
        "project_root": Path("/tmp"),
    }
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_file_count_empty_batch41():
    m = _make_manifest()
    assert m.file_count == 0


def test_manifest_pdf_count_empty_batch41():
    m = _make_manifest()
    assert m.pdf_count == 0


def test_manifest_docx_count_empty_batch41():
    m = _make_manifest()
    assert m.docx_count == 0


def test_manifest_content_group_count_empty_batch41():
    m = _make_manifest()
    assert m.content_group_count == 0


def test_manifest_categories_covered_empty_batch41():
    m = _make_manifest()
    assert m.categories_covered == []


def test_manifest_file_count_with_docs_batch41():
    docs = (
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
        _make_doc_entry(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.file_count == 3


def test_manifest_pdf_count_mixed_batch41():
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="pdf"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_categories_covered_sorted_batch41():
    docs = (
        _make_doc_entry(doc_id="d1", categories=("zebra", "apple")),
        _make_doc_entry(doc_id="d2", categories=("mango", "banana")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["apple", "banana", "mango", "zebra"]


def test_manifest_categories_covered_dedup_batch41():
    docs = (
        _make_doc_entry(doc_id="d1", categories=("tutorial", "intro")),
        _make_doc_entry(doc_id="d2", categories=("tutorial", "advanced")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["advanced", "intro", "tutorial"]


def test_manifest_content_group_count_paired_batch41():
    """双向配对算 1 组。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    # frozenset({d1, d2}) 去重后 = 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_unpaired_batch41():
    docs = (
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_mixed_batch41():
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2  # 1 pair + 1 unpaired


def test_manifest_content_group_count_self_pair_batch41():
    """doc 的 paired_with 指向自己（异常情况）。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    # frozenset({d1}) = 1 组；unpaired: d1 在 seen 中所以不计
    assert m.content_group_count == 1


def test_manifest_frozen_batch41():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_equality_batch41():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert m1 == m2


def test_manifest_repr_batch41():
    m = _make_manifest()
    assert "Manifest" in repr(m)


# ---------- _detect_project_root 第四十一批


def test_detect_project_root_from_file_batch41(tmp_path):
    """从文件向上找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_from_dir_batch41(tmp_path):
    """从目录直接找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_nested_batch41(tmp_path):
    """从深层文件向上找到根的 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    f = sub / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_batch41(tmp_path):
    """无 pyproject.toml 时退回 cur.parent（即 start 的目录）。"""
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_signature_batch41():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


def test_detect_project_root_return_annotation_path_batch41():
    sig = inspect.signature(_detect_project_root)
    assert "Path" in str(sig.return_annotation)


# ---------- load_manifest 第四十一批


def _write_valid_manifest(tmp_path: Path, **overrides: Any) -> Path:
    """写一个最小合法 manifest。"""
    data: dict[str, Any] = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    data.update(overrides)
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_default_project_root_batch41(tmp_path):
    """不传 project_root → 自动 detect。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p)
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_no_expected_failures_key_batch41(tmp_path):
    """manifest 缺 expected_failures → schema 允许（非 required）→ 默认空。"""
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.expected_failures == ()


def test_load_manifest_devset_status_complete_batch41(tmp_path):
    p = _write_valid_manifest(tmp_path, devset_status="complete")
    out = load_manifest(p, project_root=tmp_path)
    assert out.devset_status == "complete"


def test_load_manifest_devset_status_partial_not_allowed_batch41():
    """schema 只允许 complete / incomplete。"""
    from evaluation.schema import EvalSchemaError, validate
    with pytest.raises(EvalSchemaError):
        validate(
            {"manifest_version": MANIFEST_VERSION, "devset_status": "partial",
             "documents": [], "expected_failures": []},
            "manifest.schema.json",
        )


def test_load_manifest_string_manifest_path_batch41(tmp_path):
    """manifest_path 接受 str。"""
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(str(p), project_root=str(tmp_path))
    assert isinstance(out, Manifest)


def test_load_manifest_string_project_root_batch41(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=str(tmp_path))
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_missing_file_batch41(tmp_path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path / "missing.json", project_root=tmp_path)
    assert "清单文件不存在" in str(exc.value)


def test_load_manifest_invalid_json_batch41(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "清单 JSON 解析失败" in str(exc.value)


def test_load_manifest_schema_invalid_batch41(tmp_path):
    """manifest_version 不对 → EvalSchemaError 透传（schema 校验在前）。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"manifest_version": "0.0", "devset_status": "x"}), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_version_mismatch_batch41(tmp_path):
    """manifest_version=99.99 → schema 通过但代码检查到不匹配。"""
    # 但 schema 用 const，无法造出 schema 通过 + 版本不匹配
    # 所以这条改测：空 documents 但有 expected_failures
    (tmp_path / "broken.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "broken.pdf", "expected_error_code": "PARSE_FAILED"},
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert len(out.expected_failures) == 1
    assert out.expected_failures[0].doc_id == "ef1"
    assert out.expected_failures[0].expected_error_code == "PARSE_FAILED"


def test_load_manifest_expected_failure_with_source_type_batch41(tmp_path):
    (tmp_path / "broken.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "broken.pdf", "expected_error_code": "X", "source_type": "pdf"},
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.expected_failures[0].source_type == "pdf"


def test_load_manifest_document_with_categories_batch41(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["tutorial"]},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].categories == ("tutorial",)


def test_load_manifest_document_with_paired_with_batch41(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "a.docx").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].paired_with == "d2"
    assert out.documents[1].paired_with == "d1"


def test_load_manifest_document_with_sha256_batch41(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    sha = "a" * 64  # 64 hex chars 匹配 ^[0-9a-f]{64}$
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": sha},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].sha256 == sha


def test_load_manifest_document_with_annotation_file_batch41(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "annotation_file": "a.json"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].annotation_file_str == "a.json"
    assert out.documents[0].annotation_resolved == (tmp_path / "a.json").resolve()


def test_load_manifest_document_with_expectations_batch41(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"paragraph": 5}}},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_signature_batch41():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_load_manifest_project_root_default_none_batch41():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_return_annotation_manifest_batch41():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


def test_load_manifest_path_annotation_accepts_str_batch41():
    sig = inspect.signature(load_manifest)
    ann = str(sig.parameters["manifest_path"].annotation)
    assert "Path" in ann
    assert "str" in ann


def test_load_manifest_project_root_annotation_accepts_str_batch41():
    sig = inspect.signature(load_manifest)
    ann = str(sig.parameters["project_root"].annotation)
    assert "Path" in ann
    assert "str" in ann


# ---------- ManifestError 第四十一批


def test_manifest_error_is_exception_batch41():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_default_message_batch41():
    err = ManifestError("boom")
    assert str(err) == "boom"


def test_manifest_error_can_be_raised_batch41():
    with pytest.raises(ManifestError):
        raise ManifestError("x")


def test_manifest_error_caught_as_exception_batch41():
    with pytest.raises(Exception):
        raise ManifestError("x")


def test_manifest_error_module_level_batch41():
    assert hasattr(mmod, "ManifestError")


def test_manifest_error_in_all_batch41():
    assert "ManifestError" in mmod.__all__


# ---------- module source 字符串精确 第四十二批


def test_module_source_contains_docstring_batch41():
    src = inspect.getsource(mmod)
    assert '"""' in src


def test_module_source_contains_future_annotations_batch41():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch41():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_contains_dataclass_import_batch41():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_pathlib_path_import_batch41():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch41():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_manifest_version_import_batch41():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_validate_import_batch41():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_manifest_error_class_batch41():
    src = inspect.getsource(mmod)
    assert "class ManifestError" in src


def test_module_source_contains_document_entry_class_batch41():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry" in src


def test_module_source_contains_expected_failure_class_batch41():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure" in src


def test_module_source_contains_manifest_class_batch41():
    src = inspect.getsource(mmod)
    assert "class Manifest" in src


def test_module_source_contains_is_absolute_like_function_batch41():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_contains_has_backslash_function_batch41():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_contains_resolve_relative_path_function_batch41():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_load_manifest_function_batch41():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_detect_project_root_function_batch41():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_contains_frozen_true_batch41():
    """dataclass(frozen=True)。"""
    src = inspect.getsource(mmod)
    assert "frozen=True" in src


def test_module_source_contains_relative_to_batch41():
    src = inspect.getsource(mmod)
    assert "relative_to" in src


def test_module_source_contains_resolve_call_batch41():
    src = inspect.getsource(mmod)
    assert ".resolve()" in src


def test_module_source_contains_encoding_utf8_batch41():
    src = inspect.getsource(mmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_manifest_version_const_compare_batch41():
    src = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in src


def test_module_source_contains_manifest_version_incompat_batch41():
    src = inspect.getsource(mmod)
    assert "不兼容" in src


def test_module_source_contains_absolute_path_message_batch41():
    src = inspect.getsource(mmod)
    assert "绝对路径" in src or "禁止绝对路径" in src


def test_module_source_contains_backslash_message_batch41():
    src = inspect.getsource(mmod)
    assert "反斜杠" in src or "正斜杠" in src


def test_module_source_contains_outside_root_message_batch41():
    src = inspect.getsource(mmod)
    assert "项目根目录之外" in src or "项目根之外" in src


def test_module_source_contains_pyproject_toml_batch41():
    src = inspect.getsource(mmod)
    assert "pyproject.toml" in src


def test_module_source_contains_all_definition_batch41():
    src = inspect.getsource(mmod)
    assert "__all__" in src


# ---------- AST 结构 第四十一批


def test_ast_top_level_no_loop_no_with_batch41():
    """顶层无 for/while/with/try。"""
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert not isinstance(node, (ast.For, ast.While, ast.With, ast.Try))


def test_ast_has_three_dataclasses_batch41():
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    names = [c.name for c in classes]
    assert "ManifestError" in names
    assert "DocumentEntry" in names
    assert "ExpectedFailure" in names
    assert "Manifest" in names


def test_ast_functions_batch41():
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "_is_absolute_like" in funcs
    assert "_has_backslash" in funcs
    assert "_resolve_relative_path" in funcs
    assert "load_manifest" in funcs
    assert "_detect_project_root" in funcs


def test_ast_no_async_functions_batch41():
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    async_funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert async_funcs == []


def test_ast_imports_from_evaluation_batch41():
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    imports = [n for n in tree.body if isinstance(n, ast.ImportFrom)]
    modules = [i.module for i in imports if i.module]
    assert "evaluation" in modules
    assert "evaluation.schema" in modules


def test_ast_top_level_only_allowed_kinds_batch41():
    """顶层节点只允许：Expr(docstring) / Import / ImportFrom / ClassDef / FunctionDef / Assign。"""
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.Assign))


# ---------- module 合理性 第四十一批


def test_module_has_all_attribute_batch41():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch41():
    assert isinstance(mmod.__all__, list)


def test_module_all_five_entries_batch41():
    assert len(mmod.__all__) == 5


def test_module_all_contains_manifest_error_batch41():
    assert "ManifestError" in mmod.__all__


def test_module_all_contains_manifest_batch41():
    assert "Manifest" in mmod.__all__


def test_module_all_contains_document_entry_batch41():
    assert "DocumentEntry" in mmod.__all__


def test_module_all_contains_expected_failure_batch41():
    assert "ExpectedFailure" in mmod.__all__


def test_module_all_contains_load_manifest_batch41():
    assert "load_manifest" in mmod.__all__


def test_module_does_not_export_private_batch41():
    """私有函数不出现在 __all__。"""
    for name in ["_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"]:
        assert name not in mmod.__all__


def test_module_all_contains_only_strings_batch41():
    for name in mmod.__all__:
        assert isinstance(name, str)


def test_module_all_no_duplicates_batch41():
    assert len(mmod.__all__) == len(set(mmod.__all__))


def test_module_has_manifest_error_attr_batch41():
    assert hasattr(mmod, "ManifestError")


def test_module_has_manifest_attr_batch41():
    assert hasattr(mmod, "Manifest")


def test_module_has_document_entry_attr_batch41():
    assert hasattr(mmod, "DocumentEntry")


def test_module_has_expected_failure_attr_batch41():
    assert hasattr(mmod, "ExpectedFailure")


def test_module_has_load_manifest_attr_batch41():
    assert hasattr(mmod, "load_manifest")


def test_module_load_manifest_callable_batch41():
    assert callable(mmod.load_manifest)


def test_module_has_is_absolute_like_attr_batch41():
    assert hasattr(mmod, "_is_absolute_like")


def test_module_has_has_backslash_attr_batch41():
    assert hasattr(mmod, "_has_backslash")


def test_module_has_resolve_relative_path_attr_batch41():
    assert hasattr(mmod, "_resolve_relative_path")


def test_module_has_detect_project_root_attr_batch41():
    assert hasattr(mmod, "_detect_project_root")


# ---------- 端到端集成 第四十一批


def test_e2e_full_manifest_round_trip_batch41(tmp_path):
    """完整 manifest 加载 → 字段全部正确。"""
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.docx").write_text("x", encoding="utf-8")
    (tmp_path / "ann.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["tutorial"], "paired_with": "d2",
             "annotation_file": "ann.json", "sha256": "f" * 64,
             "expectations": {"element_count_by_type": {"paragraph": 5}}},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.manifest_version == MANIFEST_VERSION
    assert out.devset_status == "incomplete"
    assert out.file_count == 2
    assert out.pdf_count == 1
    assert out.docx_count == 1
    assert out.content_group_count == 1  # d1↔d2 配对
    assert out.categories_covered == ["tutorial"]
    assert out.documents[0].sha256 == "f" * 64


def test_e2e_round_trip_idempotent_batch41(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out1 = load_manifest(p, project_root=tmp_path)
    out2 = load_manifest(p, project_root=tmp_path)
    assert out1 == out2


def test_e2e_full_manifest_with_expected_failures_batch41(tmp_path):
    (tmp_path / "broken.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "broken.pdf", "expected_error_code": "PARSE_FAILED"},
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert len(out.expected_failures) == 1
    assert out.expected_failures[0].doc_id == "ef1"
    assert out.expected_failures[0].expected_error_code == "PARSE_FAILED"
    assert out.expected_failures[0].resolved_path == (tmp_path / "broken.pdf").resolve()


def test_e2e_doc_resolved_path_correct_batch41(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].resolved_path == (tmp_path / "a.pdf").resolve()


# ---------- module source forbidden tokens 第七十六批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch41(token):
    src = inspect.getsource(mmod)
    assert token not in src
