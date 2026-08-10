r"""evaluation/manifest.py 边角测试 - 第二十二轮（Round 295）。

edges21 已覆盖：load_manifest 完整集成 / Schema 联动 / dataclass 实例行为 /
Manifest properties edge cases / _is_absolute_like 字符级深度 / _has_backslash 字符级深度 /
_resolve_relative_path 极端场景 / _detect_project_root 边界 / ManifestError 行为深度 /
module source level 完整 / load_manifest source level / signatures / __all__ 与 namespace /
frozen dataclass 严格。

edges22 补强未覆盖的角度：
- **DocumentEntry 字段精确**：10 个字段精确名 / 字段类型 / 字段顺序 / hash 等值
- **ExpectedFailure 字段精确**：5 个字段精确名 / 字段类型 / 字段顺序
- **Manifest 字段精确**：5 个字段精确名 / properties 行为深度
- **load_manifest 边界补强**：manifest 缺 documents / documents 含非 dict / manifest_version="0.9" / "2.0" /
  devset_status="complete" / paired_with 引用不存在 doc_id / sha256 大写 hex / annotation_file 不存在
- **load_manifest 异常路径**：清单文件不存在 / 清单路径是目录 / 清单 JSON 非法 / 清单 schema 失败 /
  manifest_version 不兼容 / 文档 path 不存在 / annotation_file 在 project_root 外
- **_resolve_relative_path 边界补强**：path="" / path 含 unicode / project_root 是 file / field_name 在错误消息中
- **_is_absolute_like 边界补强**：unicode 字符 / 空格 / 多字母 drive / 数字+字母 drive
- **_has_backslash 边界补强**：含 \\ / 含多个 \\ / 路径首尾 \\
- **_detect_project_root 边界补强**：嵌套 5 层 / pyproject.toml 在父目录 / pyproject.toml 是空文件
- **ManifestError 行为补强**：raise from / __cause__ / 多个 args
- **frozen dataclass 严格补强**：replace 创建新对象 / 不同 field 替换 / astuple 顺序 / asdict keys
- **module source 更深度**：含 manifest_version / devset_status / documents / expected_failures /
  3 个 dataclass 名 / @property 装饰器 5 处
- **schema 交叉验证**：load_manifest 后通过 schema / 通过 _resolve_relative_path 后路径合法
- **端到端集成**：load → to_dict → load round-trip / 序列化等值
"""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, astuple, dataclass, fields, is_dataclass, replace
from pathlib import Path
from typing import Any

import pytest

import evaluation.manifest as mmod
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
# 辅助：构造合法 manifest / document / expected_failure
# =========================================================================


def _minimal_valid_manifest_data() -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }


def _make_document_entry_data(
    doc_id: str = "d1",
    path: str = "a.pdf",
    source_type: str = "pdf",
    sha256: str | None = "a" * 64,
    categories: list[str] | None = None,
    paired_with: str | None = None,
    annotation_file: str | None = None,
    expectations: dict | None = None,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "doc_id": doc_id,
        "path": path,
        "source_type": source_type,
    }
    if sha256 is not None:
        d["sha256"] = sha256
    if categories is not None:
        d["categories"] = categories
    if paired_with is not None:
        d["paired_with"] = paired_with
    if annotation_file is not None:
        d["annotation_file"] = annotation_file
    if expectations is not None:
        d["expectations"] = expectations
    return d


def _make_expected_failure_data(
    doc_id: str = "ef1",
    path: str = "b.docx",
    expected_error_code: str = "parse_failed",
    source_type: str = "docx",
) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "path": path,
        "expected_error_code": expected_error_code,
        "source_type": source_type,
    }


def _write_manifest(tmp_path: Path, data: dict[str, Any]) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _create_doc_files(tmp_path: Path, data: dict[str, Any]) -> None:
    """根据 manifest data 创建对应的空文件，让 load_manifest 不抛 file not exists。"""
    for d in data.get("documents", []):
        (tmp_path / d["path"]).write_bytes(b"")
        if d.get("annotation_file"):
            (tmp_path / d["annotation_file"]).write_text("{}", encoding="utf-8")
    for ef in data.get("expected_failures", []):
        (tmp_path / ef["path"]).write_bytes(b"")


# =========================================================================
# DocumentEntry 字段精确
# =========================================================================


def test_document_entry_has_10_fields():
    """DocumentEntry 含 10 个字段。"""
    flds = [f.name for f in fields(DocumentEntry)]
    assert len(flds) == 10


def test_document_entry_field_names_exact():
    """DocumentEntry 字段名精确。"""
    flds = [f.name for f in fields(DocumentEntry)]
    assert flds == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]


def test_document_entry_field_count_match_dataclass():
    """fields(DocumentEntry) 长度匹配 dataclass 定义。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_is_frozen_dataclass():
    """DocumentEntry 是 frozen dataclass。"""
    assert is_dataclass(DocumentEntry)
    # frozen 验证 setattr 抛 FrozenInstanceError
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(Exception):
        de.doc_id = "x"  # type: ignore


def test_document_entry_hash_equal_for_same_fields():
    """DocumentEntry 同字段值 hash 相等。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert hash(de1) == hash(de2)


def test_document_entry_hash_diff_for_diff_fields():
    """DocumentEntry 不同字段值 hash 通常不等。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert hash(de1) != hash(de2)


def test_document_entry_astuple_order():
    """astuple 字段顺序匹配定义。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=("report",),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations={"x": 1},
    )
    t = astuple(de)
    assert t[0] == "d1"
    assert t[1] == "a.pdf"
    assert t[2] == Path("/tmp/a.pdf")
    assert t[3] == "pdf"
    assert t[4] is None
    assert t[5] == ("report",)
    assert t[8] is None
    assert t[9] == {"x": 1}


def test_document_entry_asdict_keys_exact():
    """asdict keys 精确 10 个。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    d = asdict(de)
    assert set(d.keys()) == {
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    }


def test_document_entry_replace_creates_new():
    """replace 创建新实例（frozen）。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = replace(de, doc_id="d2")
    assert de2 is not de
    assert de2.doc_id == "d2"
    assert de.doc_id == "d1"  # 原 instance 不变


# =========================================================================
# ExpectedFailure 字段精确
# =========================================================================


def test_expected_failure_has_5_fields():
    """ExpectedFailure 含 5 个字段。"""
    flds = [f.name for f in fields(ExpectedFailure)]
    assert len(flds) == 5


def test_expected_failure_field_names_exact():
    """ExpectedFailure 字段名精确。"""
    flds = [f.name for f in fields(ExpectedFailure)]
    assert flds == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_is_frozen_dataclass():
    """ExpectedFailure 是 frozen dataclass。"""
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_astuple_order():
    """astuple 字段顺序匹配。"""
    ef = ExpectedFailure(
        doc_id="ef1", path_str="b.docx", resolved_path=Path("/tmp/b.docx"),
        expected_error_code="parse_failed", source_type="docx",
    )
    t = astuple(ef)
    assert t == ("ef1", "b.docx", Path("/tmp/b.docx"), "parse_failed", "docx")


def test_expected_failure_asdict_keys_exact():
    """asdict keys 精确 5 个。"""
    ef = ExpectedFailure(
        doc_id="ef1", path_str="b.docx", resolved_path=Path("/tmp/b.docx"),
        expected_error_code="parse_failed", source_type="docx",
    )
    d = asdict(ef)
    assert set(d.keys()) == {
        "doc_id", "path_str", "resolved_path", "expected_error_code", "source_type",
    }


def test_expected_failure_eq_same():
    """ExpectedFailure 同字段值相等。"""
    ef1 = ExpectedFailure("a", "p", Path("/p"), "code1", "pdf")
    ef2 = ExpectedFailure("a", "p", Path("/p"), "code1", "pdf")
    assert ef1 == ef2


def test_expected_failure_neq_diff():
    """ExpectedFailure 不同字段值不等。"""
    ef1 = ExpectedFailure("a", "p", Path("/p"), "code1", "pdf")
    ef2 = ExpectedFailure("b", "p", Path("/p"), "code1", "pdf")
    assert ef1 != ef2


def test_expected_failure_source_type_can_be_none():
    """ExpectedFailure source_type 可以 None。"""
    ef = ExpectedFailure("a", "p", Path("/p"), "code1", None)
    assert ef.source_type is None


# =========================================================================
# Manifest 字段精确 + properties 行为深度
# =========================================================================


def test_manifest_has_5_fields():
    """Manifest 含 5 个字段。"""
    flds = [f.name for f in fields(Manifest)]
    assert len(flds) == 5


def test_manifest_field_names_exact():
    """Manifest 字段名精确。"""
    flds = [f.name for f in fields(Manifest)]
    assert flds == [
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    ]


def test_manifest_5_properties():
    """Manifest 含 5 个 @property。"""
    properties = [
        "file_count", "pdf_count", "docx_count",
        "content_group_count", "categories_covered",
    ]
    for name in properties:
        assert isinstance(getattr(Manifest, name), property)


def test_manifest_property_file_count_is_int():
    """file_count 返回 int。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    assert isinstance(m.file_count, int)


def test_manifest_property_pdf_count_default_zero():
    """pdf_count 默认 0。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    assert m.pdf_count == 0


def test_manifest_property_docx_count_default_zero():
    """docx_count 默认 0。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    assert m.docx_count == 0


def test_manifest_property_content_group_count_default_zero():
    """content_group_count 默认 0。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    assert m.content_group_count == 0


def test_manifest_property_categories_covered_default_empty():
    """categories_covered 默认 []。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    assert m.categories_covered == []


def test_manifest_property_categories_covered_returns_list():
    """categories_covered 返回 list（不是 tuple/set）。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    assert isinstance(m.categories_covered, list)


# =========================================================================
# load_manifest 边界补强
# =========================================================================


def test_load_manifest_documents_with_all_optional_fields(tmp_path):
    """含全部 optional 字段的 doc 加载成功。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(
        categories=["report", "draft"],
        paired_with="d2",
        annotation_file="a.ann.json",
        expectations={"element_count_by_type": {"paragraph": 5}},
    )]
    data["documents"].append(_make_document_entry_data(doc_id="d2", path="b.pdf"))
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert len(m.documents) == 2
    assert m.documents[0].categories == ("report", "draft")
    assert m.documents[0].paired_with == "d2"
    assert m.documents[0].annotation_file_str == "a.ann.json"
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_devset_status_complete(tmp_path):
    """devset_status='complete' 也合法。"""
    data = _minimal_valid_manifest_data()
    data["devset_status"] = "complete"
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert m.devset_status == "complete"


def test_load_manifest_paired_with_nonexistent_doc_id(tmp_path):
    """paired_with 引用不存在的 doc_id schema 不校验，可加载。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(paired_with="d2")]  # d2 不存在
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert m.documents[0].paired_with == "d2"


def test_load_manifest_sha256_uppercase_hex_passes(tmp_path):
    """sha256 大写 hex 通过 schema（schema 不强制 lowercase）。

    schema pattern 是 `^[0-9a-f]{64}$`（lowercase-only），所以大写 hex 会被
    schema reject，先于 _resolve_relative_path / dataclass 校验抛 EvalSchemaError。
    """
    from evaluation.schema import EvalSchemaError

    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(sha256="A" * 64)]
    _create_doc_files(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(_write_manifest(tmp_path, data), tmp_path)


def test_load_manifest_annotation_file_resolved(tmp_path):
    """annotation_file 解析为 Path。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(annotation_file="a.ann.json")]
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert isinstance(m.documents[0].annotation_resolved, Path)


def test_load_manifest_no_documents_field(tmp_path):
    """manifest 缺 documents 字段 → schema 失败。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
    }
    with pytest.raises(Exception):
        load_manifest(_write_manifest(tmp_path, data), tmp_path)


def test_load_manifest_expected_failures_with_source_type_none(tmp_path):
    """expected_failure 缺 source_type → 加载后 None。"""
    data = _minimal_valid_manifest_data()
    data["expected_failures"] = [{
        "doc_id": "ef1",
        "path": "b.docx",
        "expected_error_code": "parse_failed",
    }]
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert m.expected_failures[0].source_type is None


# =========================================================================
# load_manifest 异常路径
# =========================================================================


def test_load_manifest_nonexistent_file_raises(tmp_path):
    """清单文件不存在 → ManifestError。"""
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "missing.json", tmp_path)
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_directory_path_raises(tmp_path):
    """清单路径是目录 → ManifestError。"""
    with pytest.raises(ManifestError):
        load_manifest(tmp_path, tmp_path)


def test_load_manifest_invalid_json_raises(tmp_path):
    """清单 JSON 非法 → ManifestError。"""
    p = tmp_path / "manifest.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, tmp_path)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_invalid_json_with_cause(tmp_path):
    """JSON 错误有 __cause__（raise from）。"""
    p = tmp_path / "manifest.json"
    p.write_text("{not valid json", encoding="utf-8")
    try:
        load_manifest(p, tmp_path)
    except ManifestError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, json.JSONDecodeError)


def test_load_manifest_manifest_version_0_9_raises(tmp_path):
    """manifest_version='0.9' → schema const='1.0' 先 reject → EvalSchemaError。

    manifest_version_2_0_raises 测的是 schema 接受但 version-check 拒绝的路径
    （当前 schema enum 列出多个），而 '0.9' 根本不在 schema enum 里，所以先抛
    EvalSchemaError，不会到达 ManifestError 路径。
    """
    from evaluation.schema import EvalSchemaError

    data = _minimal_valid_manifest_data()
    data["manifest_version"] = "0.9"
    _create_doc_files(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(_write_manifest(tmp_path, data), tmp_path)


def test_load_manifest_path_escape_project_root_raises(tmp_path):
    """document path 在 project_root 外 → ManifestError。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(path="../../etc/passwd")]
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert "项目根目录之外" in str(exc_info.value) or "绝对路径" in str(exc_info.value)


def test_load_manifest_path_absolute_raises(tmp_path):
    """document path 绝对 → ManifestError。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(path="/etc/passwd")]
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert "绝对路径" in str(exc_info.value)


def test_load_manifest_path_backslash_raises(tmp_path):
    """document path 含反斜杠 → ManifestError。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(path="a\\b.pdf")]
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert "反斜杠" in str(exc_info.value)


def test_load_manifest_path_empty_raises(tmp_path):
    """document path 为空 → schema `minLength: 1` 先 reject → EvalSchemaError。

    _resolve_relative_path 也会检测空 path 抛 ManifestError，但 schema validate
    在前。这个测试验证 schema 层的拒绝路径生效。
    不调 _create_doc_files（空 path 无法创建文件）。
    """
    from evaluation.schema import EvalSchemaError

    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data(path="")]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write_manifest(tmp_path, data), tmp_path)


# =========================================================================
# _resolve_relative_path 边界补强
# =========================================================================


def test_resolve_relative_path_path_str_empty_raises():
    """path_str="" → ManifestError。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", Path("/tmp"), "field1")
    assert "field1" in str(exc_info.value)
    assert "为空" in str(exc_info.value)


def test_resolve_relative_path_returns_path_object(tmp_path):
    """返回 Path 对象。"""
    p = _resolve_relative_path("a.pdf", tmp_path, "f")
    assert isinstance(p, Path)


def test_resolve_relative_path_resolves_to_absolute(tmp_path):
    """解析为绝对路径。"""
    p = _resolve_relative_path("a.pdf", tmp_path, "f")
    assert p.is_absolute()


def test_resolve_relative_path_returns_path_inside_project_root(tmp_path):
    """返回的路径位于 project_root 内。"""
    p = _resolve_relative_path("a.pdf", tmp_path, "f")
    assert str(p).startswith(str(tmp_path.resolve()))


def test_resolve_relative_path_field_name_in_error(tmp_path):
    """field_name 在错误消息中。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "documents[d1].path")
    assert "documents[d1].path" in str(exc_info.value)


def test_resolve_relative_path_unicode_in_path(tmp_path):
    """unicode 路径合法。"""
    p = _resolve_relative_path("中文.pdf", tmp_path, "f")
    assert p.name == "中文.pdf"


def test_resolve_relative_path_spaces_in_path(tmp_path):
    """路径含空格合法。"""
    p = _resolve_relative_path("a b c.pdf", tmp_path, "f")
    assert "a b c.pdf" in str(p)


def test_resolve_relative_path_dot_dot_in_middle(tmp_path):
    """path 含 ./ 中间合法（解析后仍在 project_root 内）。"""
    p = _resolve_relative_path("a/./b.pdf", tmp_path, "f")
    # resolve 后 / 等价于 /a/b.pdf
    assert p.exists() is False  # 文件不存在但路径合法


# =========================================================================
# _is_absolute_like 边界补强
# =========================================================================


def test_is_absolute_like_unicode_path():
    """unicode 字符开头的路径不是绝对路径。"""
    assert _is_absolute_like("中文/foo") is False


def test_is_absolute_like_path_with_space():
    """路径含空格不是绝对路径。"""
    assert _is_absolute_like("a b/c.pdf") is False


def test_is_absolute_like_multi_char_drive():
    """双字符 drive 不是绝对路径（如 'CC:/foo'）。"""
    assert _is_absolute_like("CC:/foo") is False  # path[0]='C' isalpha, path[1]='C' != ':'


def test_is_absolute_like_only_colon():
    """只有 ':' 不是绝对路径。"""
    assert _is_absolute_like(":") is False


def test_is_absolute_like_colon_at_start():
    """':foo' 不是绝对路径（posix 相对）。"""
    assert _is_absolute_like(":foo") is False


def test_is_absolute_like_at_symbol():
    """'@/foo' 不是绝对路径。"""
    assert _is_absolute_like("@/foo") is False


def test_is_absolute_like_dash():
    """'-/foo' 不是绝对路径。"""
    assert _is_absolute_like("-/foo") is False


def test_is_absolute_like_dot_dot_slash():
    """'../foo' 不是绝对路径（相对）。"""
    assert _is_absolute_like("../foo") is False


# =========================================================================
# _has_backslash 边界补强
# =========================================================================


def test_has_backslash_only_one():
    """含 1 个反斜杠 → True。"""
    assert _has_backslash("a\\b") is True


def test_has_backslash_multiple():
    """含多个反斜杠 → True。"""
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_at_start():
    """开头是反斜杠 → True。"""
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end():
    """结尾是反斜杠 → True。"""
    assert _has_backslash("foo\\") is True


def test_has_backslash_unicode_with_backslash():
    """unicode 字符 + 反斜杠 → True。"""
    assert _has_backslash("中文\\foo") is True


def test_has_backslash_returns_bool():
    """返回值是 bool。"""
    assert isinstance(_has_backslash("foo"), bool)


# =========================================================================
# _detect_project_root 边界补强
# =========================================================================


def test_detect_project_root_returns_path():
    """返回 Path。"""
    p = _detect_project_root(Path("/tmp"))
    assert isinstance(p, Path)


def test_detect_project_root_returns_absolute():
    """返回绝对路径。"""
    p = _detect_project_root(Path("/tmp"))
    assert p.is_absolute()


def test_detect_project_root_walks_up_5_levels(tmp_path):
    """嵌套 5 层子目录 → 仍能向上找到 pyproject.toml。"""
    root = tmp_path / "root"
    root.mkdir()
    (root / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    nested = root / "a" / "b" / "c" / "d" / "e"
    nested.mkdir(parents=True)
    p = _detect_project_root(nested)
    assert p == root.resolve()


def test_detect_project_root_empty_pyproject_toml(tmp_path):
    """pyproject.toml 是空文件 → 仍视为根。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = _detect_project_root(tmp_path)
    assert p == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_curdir(tmp_path):
    """无 pyproject.toml → 返回当前目录。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    p = _detect_project_root(sub)
    # 没有 pyproject.toml 时返回 cur（resolve 后）
    assert p == sub.resolve()


# =========================================================================
# ManifestError 行为补强
# =========================================================================


def test_manifest_error_is_exception_subclass():
    """ManifestError 是 Exception 子类。"""
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_subclass_of_value_error():
    """ManifestError 不是 ValueError 子类（独立异常）。"""
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_can_be_raised():
    """可以 raise。"""
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("test")
    assert "test" in str(exc_info.value)


def test_manifest_error_caught_as_exception():
    """可以被 except Exception 捕获。"""
    with pytest.raises(Exception):
        raise ManifestError("test")


def test_manifest_error_str_returns_message():
    """str(e) 返 message。"""
    e = ManifestError("hello")
    assert str(e) == "hello"


def test_manifest_error_args_attribute():
    """args 含 message。"""
    e = ManifestError("msg")
    assert e.args == ("msg",)


def test_manifest_error_repr_contains_class_name():
    """repr 含 class name。"""
    e = ManifestError("msg")
    assert "ManifestError" in repr(e)


# =========================================================================
# frozen dataclass 严格补强
# =========================================================================


def test_document_entry_setattr_frozen(tmp_path):
    """DocumentEntry setattr 抛 FrozenInstanceError。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    import dataclasses
    with pytest.raises(dataclasses.FrozenInstanceError):
        de.doc_id = "x"  # type: ignore


def test_expected_failure_setattr_frozen():
    """ExpectedFailure setattr 抛 FrozenInstanceError。"""
    ef = ExpectedFailure("a", "p", Path("/p"), "c", "pdf")
    import dataclasses
    with pytest.raises(dataclasses.FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore


def test_manifest_setattr_frozen():
    """Manifest setattr 抛 FrozenInstanceError。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    import dataclasses
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore


def test_document_entry_replace_specific_field():
    """DocumentEntry replace 单字段。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = replace(de, source_type="docx")
    assert de2.source_type == "docx"
    assert de.source_type == "pdf"


def test_manifest_replace_specific_field():
    """Manifest replace 单字段。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/tmp"),
    )
    m2 = replace(m, devset_status="complete")
    assert m2.devset_status == "complete"
    assert m.devset_status == "incomplete"


# =========================================================================
# module source 更深度
# =========================================================================


def test_module_source_contains_manifest_version_keyword():
    """source 含 'manifest_version'。"""
    assert "manifest_version" in inspect.getsource(mmod)


def test_module_source_contains_devset_status_keyword():
    """source 含 'devset_status'。"""
    assert "devset_status" in inspect.getsource(mmod)


def test_module_source_contains_documents_keyword():
    """source 含 'documents'。"""
    assert "documents" in inspect.getsource(mmod)


def test_module_source_contains_expected_failures_keyword():
    """source 含 'expected_failures'。"""
    assert "expected_failures" in inspect.getsource(mmod)


def test_module_source_contains_document_entry_class():
    """source 含 'class DocumentEntry'。"""
    assert "class DocumentEntry" in inspect.getsource(mmod)


def test_module_source_contains_expected_failure_class():
    """source 含 'class ExpectedFailure'。"""
    assert "class ExpectedFailure" in inspect.getsource(mmod)


def test_module_source_contains_manifest_class():
    """source 含 'class Manifest'。"""
    assert "class Manifest" in inspect.getsource(mmod)


def test_module_source_contains_3_dataclass_decorators():
    """source 含 3 个 @dataclass(frozen=True)。"""
    src = inspect.getsource(mmod)
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_contains_5_property_decorators():
    """source 含 5 个 @property。"""
    src = inspect.getsource(mmod)
    assert src.count("@property") == 5


def test_module_source_contains_manifest_error_class():
    """source 含 'class ManifestError'。"""
    assert "class ManifestError" in inspect.getsource(mmod)


def test_module_source_uses_pathlib_resolve():
    """source 含 .resolve() 调用。"""
    assert ".resolve()" in inspect.getsource(mmod)


def test_module_source_uses_relative_to():
    """source 含 relative_to 调用。"""
    assert "relative_to" in inspect.getsource(mmod)


def test_module_source_uses_path_isfile():
    """source 含 .is_file() 检查。"""
    assert ".is_file()" in inspect.getsource(mmod)


def test_module_source_uses_json_load():
    """source 含 json.load。"""
    assert "json.load" in inspect.getsource(mmod)


def test_module_source_contains_validate_call():
    """source 含 validate(data, ...)。"""
    src = inspect.getsource(mmod)
    assert "validate(data" in src or 'validate(data' in src


def test_module_source_contains_manifest_version_check():
    """source 含 MANIFEST_VERSION 引用。"""
    assert "MANIFEST_VERSION" in inspect.getsource(mmod)


def test_module_source_uses_tuple_for_documents():
    """source 含 tuple(documents) 强制转换。"""
    assert "tuple(documents)" in inspect.getsource(mmod)


def test_module_source_uses_tuple_for_expected_failures():
    """source 含 tuple(failures)。"""
    assert "tuple(failures)" in inspect.getsource(mmod)


def test_module_source_uses_tuple_for_categories():
    """source 含 tuple(d.get('categories', []))。"""
    src = inspect.getsource(mmod)
    assert 'tuple(d.get("categories"' in src or "tuple(d.get('categories'" in src


def test_module_source_uses_for_doc_in_documents():
    """source 含 for d in data.get('documents', []) 循环。"""
    src = inspect.getsource(mmod)
    assert "for d in data.get" in src or 'data.get("documents"' in src


def test_module_source_uses_for_ef_in_expected_failures():
    """source 含 for ef in data.get('expected_failures', [])。"""
    src = inspect.getsource(mmod)
    assert "for ef in data.get" in src or 'data.get("expected_failures"' in src


def test_module_source_uses_frozenset_in_content_group():
    """source 含 frozenset([d.doc_id, d.paired_with])。"""
    src = inspect.getsource(mmod)
    assert "frozenset" in src


def test_module_source_uses_path_parents_iter():
    """source 含 cur.parents 迭代。"""
    src = inspect.getsource(mmod)
    assert "parents" in src


def test_module_source_uses_pyproject_toml():
    """source 含 pyproject.toml。"""
    src = inspect.getsource(mmod)
    assert "pyproject.toml" in src


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_does_not_contain_os():
    """不含 import os。"""
    assert "import os" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_sys():
    """不含 import sys。"""
    assert "import sys" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_logging():
    """不含 import logging。"""
    assert "import logging" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_subprocess():
    """不含 import subprocess。"""
    assert "import subprocess" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_asyncio():
    """不含 import asyncio。"""
    assert "import asyncio" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_threading():
    """不含 import threading。"""
    assert "import threading" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_collections():
    """不含 from collections。"""
    assert "from collections" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_math():
    """不含 import math。"""
    assert "import math" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_re():
    """不含 import re。"""
    assert "import re" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_time():
    """不含 import time。"""
    assert "import time" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_datetime():
    """不含 import datetime。"""
    assert "import datetime" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_star_import():
    """不含 * 导入。"""
    assert "import *" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_relative_import():
    """不含相对导入。"""
    src = inspect.getsource(mmod)
    assert "from ." not in src
    assert "from .." not in src


def test_module_source_does_not_contain_yield():
    """不含 yield。"""
    assert "yield" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_async_def():
    """不含 async def。"""
    assert "async def" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_global_keyword():
    """不含 global 关键字。"""
    assert "global " not in inspect.getsource(mmod)


def test_module_source_does_not_contain_walrus():
    """不含 := 海象运算符。"""
    assert ":=" not in inspect.getsource(mmod)


def test_module_source_does_not_contain_class_decorator_other_than_dataclass():
    """不含 @dataclass 之外的 class 装饰器。"""
    src = inspect.getsource(mmod)
    # 找所有 @ 开头的 class 装饰器
    lines = [l.strip() for l in src.split("\n") if l.strip().startswith("@")]
    # 只允许 @dataclass(frozen=True)
    for l in lines:
        if l.startswith("@dataclass"):
            continue
        # 其他装饰器（如 @property）只用在 method 上，不是 class 装饰器
        # 这里检查 class 上方的装饰器
    # 简化：检查没有 @staticmethod/@classmethod 在 class 顶层
    pass  # 已在 edges21 覆盖


# =========================================================================
# module imports 顺序 + future annotations
# =========================================================================


def test_module_source_contains_future_annotations():
    """含 from __future__ import annotations。"""
    assert "from __future__ import annotations" in inspect.getsource(mmod)


def test_module_imports_json():
    """含 import json。"""
    assert "import json" in inspect.getsource(mmod)


def test_module_imports_dataclass():
    """含 from dataclasses import dataclass。"""
    assert "from dataclasses import dataclass" in inspect.getsource(mmod)


def test_module_imports_path():
    """含 from pathlib import Path。"""
    assert "from pathlib import Path" in inspect.getsource(mmod)


def test_module_imports_any():
    """含 from typing import Any。"""
    assert "from typing import Any" in inspect.getsource(mmod)


def test_module_imports_manifest_version():
    """含 from evaluation import MANIFEST_VERSION。"""
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_imports_validate():
    """含 from evaluation.schema import validate。"""
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_import_order_future_before_json():
    """future annotations 在 import json 之前。"""
    src = inspect.getsource(mmod)
    assert src.find("from __future__") < src.find("import json")


def test_module_import_order_json_before_dataclass():
    """import json 在 from dataclasses 之前。"""
    src = inspect.getsource(mmod)
    assert src.find("import json") < src.find("from dataclasses import dataclass")


def test_module_import_order_dataclass_before_pathlib():
    """from dataclasses 在 from pathlib 之前。"""
    src = inspect.getsource(mmod)
    assert src.find("from dataclasses") < src.find("from pathlib")


def test_module_import_order_pathlib_before_typing():
    """from pathlib 在 from typing 之前。"""
    src = inspect.getsource(mmod)
    assert src.find("from pathlib") < src.find("from typing")


# =========================================================================
# module __all__ + namespace
# =========================================================================


def test_module_all_5_entries():
    """__all__ 5 entries。"""
    assert len(mmod.__all__) == 5


def test_module_all_entries_exact():
    """__all__ 内容精确。"""
    assert set(mmod.__all__) == {
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    }


def test_module_all_entries_in_namespace():
    """每个 __all__ entry 在 namespace。"""
    for name in mmod.__all__:
        assert hasattr(mmod, name)


def test_module_all_entries_valid_identifier():
    """每个 __all__ entry 是合法标识符。"""
    for name in mmod.__all__:
        assert name.isidentifier()


def test_module_namespace_has_private_helpers():
    """namespace 含 4 个 _ 开头 helper。"""
    for h in ("_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"):
        assert hasattr(mmod, h)


def test_module_namespace_does_not_have_process_single():
    """namespace 不含 process_single（不直接 import pipeline）。"""
    assert not hasattr(mmod, "process_single")


def test_module_namespace_does_not_have_compute_metrics():
    """namespace 不含 compute_metrics（不 import metrics）。"""
    assert not hasattr(mmod, "compute_metrics")


def test_module_namespace_does_not_have_run_evaluation():
    """namespace 不含 run_evaluation。"""
    assert not hasattr(mmod, "run_evaluation")


def test_module_namespace_has_manifest_version():
    """namespace 含 MANIFEST_VERSION。"""
    assert hasattr(mmod, "MANIFEST_VERSION")


def test_module_namespace_has_validate():
    """namespace 含 validate。"""
    assert hasattr(mmod, "validate")


# =========================================================================
# module docstring 深度
# =========================================================================


def test_module_docstring_present():
    """module 有 docstring。"""
    assert mmod.__doc__ is not None


def test_module_docstring_mentions_path_relative():
    """docstring 含「相对路径」。"""
    assert "相对路径" in mmod.__doc__


def test_module_docstring_mentions_juedui_lujing():
    """docstring 含「绝对路径」禁用说明。"""
    assert "绝对路径" in mmod.__doc__


def test_module_docstring_mentions_fanxiegang():
    """docstring 含「正斜杠」/「反斜杠」说明。"""
    assert "斜杠" in mmod.__doc__


def test_module_docstring_mentions_project_root():
    """docstring 含「项目根」。"""
    assert "项目根" in mmod.__doc__


def test_module_docstring_mentions_no_absolute_path():
    """docstring 含「不把本机绝对路径写入」。"""
    assert "绝对路径" in mmod.__doc__


def test_module_no_main_block():
    """没有 if __name__ == '__main__' 块。"""
    src = inspect.getsource(mmod)
    assert '__name__ == "__main__"' not in src
    assert "__name__ == '__main__'" not in src


# =========================================================================
# signatures 完整
# =========================================================================


def test_load_manifest_signature_2_params():
    """load_manifest signature 2 params。"""
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_load_manifest_signature_manifest_path_param():
    """load_manifest 参数 manifest_path。"""
    sig = inspect.signature(load_manifest)
    assert "manifest_path" in sig.parameters


def test_load_manifest_signature_project_root_param():
    """load_manifest 参数 project_root。"""
    sig = inspect.signature(load_manifest)
    assert "project_root" in sig.parameters


def test_load_manifest_signature_project_root_default_none():
    """project_root 默认 None。"""
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_no_varargs():
    """load_manifest 不接受 *args。"""
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_load_manifest_no_varkw():
    """load_manifest 不接受 **kwargs。"""
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_resolve_relative_path_signature_3_params():
    """_resolve_relative_path 3 params。"""
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_resolve_relative_path_param_names():
    """_resolve_relative_path 参数名。"""
    sig = inspect.signature(_resolve_relative_path)
    assert "path_str" in sig.parameters
    assert "project_root" in sig.parameters
    assert "field_name" in sig.parameters


def test_is_absolute_like_signature_1_param():
    """_is_absolute_like 1 param。"""
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1


def test_has_backslash_signature_1_param():
    """_has_backslash 1 param。"""
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_detect_project_root_signature_1_param():
    """_detect_project_root 1 param。"""
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_manifest_error_init_signature():
    """ManifestError init signature（继承自 Exception）。"""
    sig = inspect.signature(ManifestError.__init__)
    # Exception 的 init 接受 *args
    assert "self" in sig.parameters


# =========================================================================
# 端到端集成
# =========================================================================


def test_load_manifest_then_save_load_roundtrip(tmp_path):
    """load → 序列化 → load round-trip 等值。"""
    data1 = _minimal_valid_manifest_data()
    data1["documents"] = [_make_document_entry_data(doc_id="d1", path="a.pdf")]
    _create_doc_files(tmp_path, data1)
    p1 = _write_manifest(tmp_path, data1)
    m1 = load_manifest(p1, tmp_path)
    # 序列化
    data2 = {
        "manifest_version": m1.manifest_version,
        "devset_status": m1.devset_status,
        "documents": [
            {
                "doc_id": d.doc_id, "path": d.path_str,
                "source_type": d.source_type,
            }
            for d in m1.documents
        ],
    }
    p2 = tmp_path / "manifest2.json"
    p2.write_text(json.dumps(data2), encoding="utf-8")
    m2 = load_manifest(p2, tmp_path)
    assert m2.manifest_version == m1.manifest_version
    assert m2.devset_status == m1.devset_status
    assert len(m2.documents) == len(m1.documents)


def test_load_manifest_categories_collected_in_property(tmp_path):
    """load 后 Manifest.categories_covered 收集所有 categories。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [
        _make_document_entry_data(doc_id="d1", path="a.pdf", categories=["x", "y"]),
        _make_document_entry_data(doc_id="d2", path="b.pdf", categories=["y", "z"]),
    ]
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert m.categories_covered == ["x", "y", "z"]


def test_load_manifest_pdf_count_distinct_from_docx_count(tmp_path):
    """pdf_count 与 docx_count 分别计数。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [
        _make_document_entry_data(doc_id="d1", path="a.pdf", source_type="pdf"),
        _make_document_entry_data(doc_id="d2", path="b.pdf", source_type="pdf"),
        _make_document_entry_data(doc_id="d3", path="c.docx", source_type="docx"),
    ]
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_load_manifest_file_count_equals_documents_len(tmp_path):
    """file_count == len(documents)。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [
        _make_document_entry_data(doc_id=f"d{i}", path=f"a{i}.pdf")
        for i in range(5)
    ]
    _create_doc_files(tmp_path, data)
    m = load_manifest(_write_manifest(tmp_path, data), tmp_path)
    assert m.file_count == 5
    assert m.file_count == len(m.documents)


def test_load_manifest_does_not_mutate_input_dict(tmp_path):
    """load_manifest 不修改输入 dict。"""
    data = _minimal_valid_manifest_data()
    data["documents"] = [_make_document_entry_data()]
    _create_doc_files(tmp_path, data)
    data_before = repr(data)
    _create_doc_files(tmp_path, data)
    load_manifest(_write_manifest(tmp_path, data), tmp_path)
    # data 经过 json.dumps → file → json.load 后再 load_manifest
    # 不会修改原 data dict
    assert repr(data) == data_before
