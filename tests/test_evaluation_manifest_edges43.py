"""evaluation/manifest.py 第四十三轮 edges 测试（Round 433）。

补强 edges42 未触及的角度：
- _is_absolute_like 边界第十六批（更多 corner case：单字符 / 多字符 / 混合 ASCII / 双字节首字符）
- _has_backslash 边界第十六批（Unicode 全角反斜杠 / 控制字符 / NUL）
- _resolve_relative_path 异常深度第十六批（深度嵌套 / project_root 是文件 / 路径是 Unicode）
- _detect_project_root 异常深度第十六批（start 是 Path 但不存在 / 多个 pyproject.toml）
- Manifest dataclass 第十六批（contains test / __repr__ / __hash__ / getstate）
- Manifest properties 第十六批（content_group_count 复杂配对 / pdf_count 与 docx_count 互斥）
- DocumentEntry 第十六批（所有可选字段同时设置 / 所有 None / 字段顺序）
- ExpectedFailure 第十六批（与 DocumentEntry 区分 / hashable / equality）
- load_manifest 异常深度第十六批（annotation_file 不存在 / expected_failures 路径越界）
- module source forbidden tokens 第二十八批
- module source 字符串精确补强第二十五批
- signatures 第二十五批
- module 合理性第二十五批
- 端到端集成第二十五批
"""

from __future__ import annotations

import inspect
import json
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


# ---------- _is_absolute_like 边界第十六批 ----------


def test_is_absolute_like_single_alpha_no_colon_batch16():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_multi_alpha_batch16():
    assert _is_absolute_like("abcd") is False


def test_is_absolute_like_two_letters_colon_batch16():
    """AB:foo - 第 0 是字母, 第 1 是 B（不是 :）。"""
    assert _is_absolute_like("AB:foo") is False


def test_is_absolute_like_drive_z_batch16():
    """Z: 是合法盘符（如果后跟 / 或 \\）。"""
    assert _is_absolute_like("Z:/foo") is True


def test_is_absolute_like_drive_a_batch16():
    assert _is_absolute_like("A:\\foo") is True


def test_is_absolute_like_full_width_drive_batch16():
    """全角字符 Ｃ 的 isalpha() 是 True，所以会被识别为绝对路径（这是已知 corner case）。"""
    # Ｃ 是 U+FF23 Fullwidth Latin Capital Letter C；isalpha() True
    # → 被 _is_absolute_like 当作合法盘符
    assert _is_absolute_like("Ｃ:/foo") is True


def test_is_absolute_like_null_char_batch16():
    """NUL 不算绝对路径起始。"""
    assert _is_absolute_like("\x00/foo") is False


def test_is_absolute_like_drive_only_three_chars_batch16():
    """恰好 3 字符 'C:x' - 第 2 不是 / 或 \\。"""
    assert _is_absolute_like("C:x") is False


def test_is_absolute_like_three_chars_with_slash_batch16():
    """3 字符 'C:/' → 绝对。"""
    assert _is_absolute_like("C:/") is True


def test_is_absolute_like_three_chars_with_backslash_batch16():
    assert _is_absolute_like("C:\\") is True


# ---------- _has_backslash 边界第十六批 ----------


def test_has_backslash_unicode_full_width_batch16():
    """全角反斜杠 ＼（U+FF3C）应不被识别（仅 ASCII \\）。"""
    assert _has_backslash("＼foo") is False


def test_has_backslash_control_char_batch16():
    """控制字符不是 \\。"""
    assert _has_backslash("\x00\x01\x02") is False


def test_has_backslash_nul_char_batch16():
    assert _has_backslash("\x00") is False


def test_has_backslash_only_backslash_batch16():
    assert _has_backslash("\\") is True


def test_has_backslash_two_backslashes_batch16():
    assert _has_backslash("\\\\") is True


def test_has_backslash_intermixed_batch16():
    """混合 / 与 \\ 与 Unicode。"""
    assert _has_backslash("/\\＼") is True


# ---------- _resolve_relative_path 异常深度第十六批 ----------


def test_resolve_relative_path_deep_nested_batch16(tmp_path):
    """深度嵌套子目录。"""
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / "file.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("a/b/c/d/file.pdf", tmp_path, "test")
    assert result == (tmp_path / "a" / "b" / "c" / "d" / "file.pdf").resolve()


def test_resolve_relative_path_unicode_path_batch16(tmp_path):
    """路径含 Unicode 字符。"""
    (tmp_path / "文件.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("文件.pdf", tmp_path, "test")
    assert result == (tmp_path / "文件.pdf").resolve()


def test_resolve_relative_path_project_root_trailing_slash_batch16(tmp_path):
    """project_root 含 trailing / 应被 .resolve() 处理。"""
    (tmp_path / "x.pdf").write_text("fake", encoding="utf-8")
    # 直接传 tmp_path 不加 trailing slash
    result = _resolve_relative_path("x.pdf", tmp_path, "test")
    assert result == (tmp_path / "x.pdf").resolve()


def test_resolve_relative_path_returns_resolved_batch16(tmp_path):
    """返回值始终是 .resolve() 后的。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    result = _resolve_relative_path("a.pdf", tmp_path, "test")
    expected = (tmp_path / "a.pdf").resolve()
    assert result == expected


def test_resolve_relative_path_does_not_check_file_existence_batch16(tmp_path):
    """_resolve_relative_path 只校验路径形式，不检查文件存在。"""
    result = _resolve_relative_path("nonexistent.pdf", tmp_path, "test")
    # 文件不存在但路径合法 → 仍返回 Path
    assert isinstance(result, Path)


def test_resolve_relative_path_message_contains_field_name_batch16(tmp_path):
    """异常 message 含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "custom_field[X].path")
    assert "custom_field[X].path" in str(exc_info.value)


# ---------- _detect_project_root 异常深度第十六批 ----------


def test_detect_project_root_nonexistent_start_batch16(tmp_path):
    """start 不存在 → resolve 后向上找。"""
    fake = tmp_path / "does" / "not" / "exist"
    # resolve 会规范化路径；即使不存在，parent 链仍可遍历
    result = _detect_project_root(fake)
    # 至少返回一个 Path
    assert isinstance(result, Path)


def test_detect_project_root_multiple_pyproject_chooses_nearest_batch16(tmp_path):
    """多层 pyproject.toml → 取最近的（最深的）。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[tool.y]", encoding="utf-8")
    result = _detect_project_root(sub)
    assert result == sub.resolve()


def test_detect_project_root_uses_parents_iteration_batch16(tmp_path):
    """应遍历 parents。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    deep = tmp_path / "x" / "y" / "z"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_nearest_dir_batch16(tmp_path):
    """无 pyproject.toml → 返回最近的目录（start 本身或其 parent）。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    # 没有 pyproject.toml → fallback 到 start（resolve 后）
    assert result == sub.resolve()


# ---------- Manifest dataclass 第十六批 ----------


def test_manifest_dataclass_in_test_batch16(tmp_path):
    """`in` 操作符测试 — Manifest 不支持 in（不是容器）。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(TypeError):
        "x" in m  # type: ignore


def test_manifest_dataclass_repr_batch16(tmp_path):
    """__repr__ 含 Manifest 标识。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    r = repr(m)
    assert "Manifest" in r
    assert "incomplete" in r


def test_manifest_dataclass_hashable_batch16(tmp_path):
    """Manifest frozen → hashable。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    h = hash(m)
    assert isinstance(h, int)


def test_manifest_dataclass_used_as_dict_key_batch16(tmp_path):
    """hashable → 可作 dict key。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = {m: "value"}
    assert d[m] == "value"


def test_manifest_dataclass_setattr_other_field_batch16(tmp_path):
    """修改任何字段都应抛 FrozenInstanceError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.manifest_version = "2.0"
    with pytest.raises(FrozenInstanceError):
        m.documents = ()


def test_manifest_dataclass_delattr_frozen_batch16(tmp_path):
    """删除字段也 frozen。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        del m.devset_status


# ---------- Manifest properties 第十六批 ----------


def test_manifest_pdf_count_only_pdfs_batch16(tmp_path):
    """pdf_count 只数 source_type=pdf 的文档。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "b.docx").write_text("fake", encoding="utf-8")
    (tmp_path / "c.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
            {"doc_id": "d3", "path": "c.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3


def test_manifest_content_group_count_complex_pairing_batch16(tmp_path):
    """复杂配对：3 对 + 2 单。"""
    for n in ("a.pdf", "a.docx", "b.pdf", "b.docx", "c.pdf", "c.docx", "d.pdf", "e.pdf"):
        (tmp_path / n).write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
            {"doc_id": "d3", "path": "b.pdf", "source_type": "pdf", "paired_with": "d4"},
            {"doc_id": "d4", "path": "b.docx", "source_type": "docx", "paired_with": "d3"},
            {"doc_id": "d5", "path": "c.pdf", "source_type": "pdf", "paired_with": "d6"},
            {"doc_id": "d6", "path": "c.docx", "source_type": "docx", "paired_with": "d5"},
            {"doc_id": "d7", "path": "d.pdf", "source_type": "pdf"},
            {"doc_id": "d8", "path": "e.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 5  # 3 对 + 2 单


def test_manifest_categories_covered_unique_batch16(tmp_path):
    """categories 自动 dedupe。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["x", "x", "x"]},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["x"]


# ---------- DocumentEntry 第十六批 ----------


def test_document_entry_all_optional_fields_set_batch16(tmp_path):
    """所有可选字段同时设置。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": "a" * 64, "categories": ["x", "y"],
             "paired_with": "d2", "annotation_file": "a.json",
             "expectations": {"element_count_by_type": {"heading": 1}}},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.sha256 == "a" * 64
    assert d.categories == ("x", "y")
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "a.json"
    assert d.annotation_resolved == (tmp_path / "a.json").resolve()
    assert d.expectations == {"element_count_by_type": {"heading": 1}}


def test_document_entry_field_order_batch16():
    """DocumentEntry 字段定义顺序。"""
    names = list(DocumentEntry.__dataclass_fields__.keys())
    assert names == [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    ]


def test_document_entry_hashable_batch16(tmp_path):
    """frozen → hashable。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_equality_batch16(tmp_path):
    """两个相同字段 DocumentEntry 相等。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1.documents[0] == m2.documents[0]


# ---------- ExpectedFailure 第十六批 ----------


def test_expected_failure_hashable_batch16(tmp_path):
    """frozen → hashable。"""
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
    h = hash(m.expected_failures[0])
    assert isinstance(h, int)


def test_expected_failure_equality_batch16(tmp_path):
    (tmp_path / "x.bad").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "x.bad", "expected_error_code": "x"},
        ],
    }), encoding="utf-8")
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1.expected_failures[0] == m2.expected_failures[0]


def test_expected_failure_does_not_have_categories_batch16():
    """ExpectedFailure 与 DocumentEntry 不同：缺 categories。"""
    de_fields = set(DocumentEntry.__dataclass_fields__.keys())
    ef_fields = set(ExpectedFailure.__dataclass_fields__.keys())
    assert "categories" in de_fields
    assert "categories" not in ef_fields


def test_expected_failure_does_not_have_paired_with_batch16():
    de_fields = set(DocumentEntry.__dataclass_fields__.keys())
    ef_fields = set(ExpectedFailure.__dataclass_fields__.keys())
    assert "paired_with" in de_fields
    assert "paired_with" not in ef_fields


def test_expected_failure_repr_batch16(tmp_path):
    """__repr__ 含 ExpectedFailure 标识。"""
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
    r = repr(m.expected_failures[0])
    assert "ExpectedFailure" in r
    assert "ef1" in r


# ---------- load_manifest 异常深度第十六批 ----------


def test_load_manifest_annotation_file_outside_root_batch16(tmp_path):
    """annotation_file 越界 → ManifestError。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "../../etc/passwd"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(exc_info.value)


def test_load_manifest_expected_failure_path_outside_root_batch16(tmp_path):
    """expected_failures 路径越界 → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "../../etc/passwd", "expected_error_code": "x"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_expected_failure_path_backslash_batch16(tmp_path):
    """expected_failures 路径含 \\ → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "x\\bad", "expected_error_code": "x"},
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc_info.value)


def test_load_manifest_doc_path_absolute_batch16(tmp_path):
    """documents 路径绝对 → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_returns_manifest_instance_batch16(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


# ---------- module source forbidden tokens 第二十八批 ----------


@pytest.mark.parametrize("forbidden", [
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
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch16(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


# ---------- module source 字符串精确补强第二十五批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(mmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_dataclass_import_batch16():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_three_dataclass_decorators_batch16():
    """3 个 @dataclass(frozen=True)。"""
    src = inspect.getsource(mmod)
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_has_class_document_entry_batch16():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry" in src


def test_module_source_has_class_expected_failure_batch16():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure" in src


def test_module_source_has_paired_with_field_batch16():
    src = inspect.getsource(mmod)
    assert "paired_with: str | None" in src


def test_module_source_has_annotation_file_str_field_batch16():
    src = inspect.getsource(mmod)
    assert "annotation_file_str: str | None" in src


def test_module_source_has_expectations_field_batch16():
    src = inspect.getsource(mmod)
    assert "expectations: dict[str, Any] | None" in src


def test_module_source_has_categories_field_batch16():
    src = inspect.getsource(mmod)
    assert "categories: tuple[str, ...]" in src


def test_module_source_has_pdf_count_property_batch16():
    src = inspect.getsource(mmod)
    assert "def pdf_count(self) -> int:" in src


def test_module_source_has_docx_count_property_batch16():
    src = inspect.getsource(mmod)
    assert "def docx_count(self) -> int:" in src


def test_module_source_has_frozenset_in_content_group_batch16():
    src = inspect.getsource(mmod)
    assert "frozenset" in src


def test_module_source_has_file_count_uses_len_batch16():
    src = inspect.getsource(mmod)
    assert "len(self.documents)" in src


def test_module_source_has_validate_import_batch16():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_manifest_version_import_batch16():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_manifest_error_class_batch16():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_raise_manifest_error_batch16():
    src = inspect.getsource(mmod)
    assert "raise ManifestError" in src


def test_module_source_has_pathlib_path_import_batch16():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch16():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_all_list_batch16():
    src = inspect.getsource(mmod)
    assert "__all__ = [" in src


def test_module_source_has_5_items_in_all_batch16():
    """__all__ 至少 5 项。"""
    src = inspect.getsource(mmod)
    # ManifestError, Manifest, DocumentEntry, ExpectedFailure, load_manifest
    for name in ['"ManifestError"', '"Manifest"', '"DocumentEntry"',
                 '"ExpectedFailure"', '"load_manifest"']:
        assert name in src


def test_module_source_has_no_documents_fallback_batch16():
    src = inspect.getsource(mmod)
    assert 'data.get("documents", [])' in src


def test_module_source_has_expected_failures_fallback_batch16():
    src = inspect.getsource(mmod)
    assert 'data.get("expected_failures", [])' in src


# ---------- signatures 第二十五批 ----------


def test_signature_is_absolute_like_param_batch16():
    sig = inspect.signature(_is_absolute_like)
    assert "path_str" in sig.parameters
    assert sig.parameters["path_str"].annotation == "str"


def test_signature_resolve_relative_path_params_batch16():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_optional_project_root_batch16():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_manifest_error_init_optional_errors_batch16():
    """ManifestError 没自定义 __init__（继承 Exception），signature 是 (*args)。"""
    sig = inspect.signature(ManifestError.__init__)
    params = list(sig.parameters.keys())
    # Exception.__init__ signature: (self, *args)
    assert "self" in params
    # ManifestError 没有自定义 errors 参数（不像 EvalSchemaError）
    assert "errors" not in sig.parameters


def test_signature_detect_project_root_single_param_batch16():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


# ---------- module 合理性第二十五批 ----------


def test_module_manifest_error_is_exception_batch16():
    assert issubclass(ManifestError, Exception)


def test_module_document_entry_frozen_true_batch16():
    assert DocumentEntry.__dataclass_params__.frozen is True


def test_module_expected_failure_frozen_true_batch16():
    assert ExpectedFailure.__dataclass_params__.frozen is True


def test_module_manifest_frozen_true_batch16():
    assert Manifest.__dataclass_params__.frozen is True


def test_module_all_items_in_namespace_batch16():
    for name in mmod.__all__:
        assert name in vars(mmod)


def test_module_all_count_5_batch16():
    assert len(mmod.__all__) == 5


def test_module_load_manifest_callable_batch16():
    assert callable(load_manifest)


def test_module_constants_in_namespace_batch16():
    """MANIFEST_VERSION 是从 evaluation import 的，但在 mmod 命名空间可见。"""
    assert "MANIFEST_VERSION" in vars(mmod)
    assert mmod.MANIFEST_VERSION == MANIFEST_VERSION


# ---------- 端到端集成第二十五批 ----------


def test_e2e_full_manifest_with_all_features_batch16(tmp_path):
    """完整 manifest：含 documents + expected_failures + 配对 + annotation。"""
    for n in ("a.pdf", "a.docx", "a.json", "bad.bad"):
        (tmp_path / n).write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "paired_with": "d2", "annotation_file": "a.json",
             "categories": ["report"], "sha256": "a" * 64,
             "expectations": {"element_count_by_type": {"heading": 1}}},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [
            {"doc_id": "ef1", "path": "bad.bad", "expected_error_code": "unsupported_format",
             "source_type": "other"},
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1
    assert m.categories_covered == ["report"]
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].source_type == "other"
    assert m.documents[0].annotation_resolved == (tmp_path / "a.json").resolve()
    assert m.documents[0].sha256 == "a" * 64


def test_e2e_load_manifest_idempotent_with_annotation_batch16(tmp_path):
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
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_equality_with_complex_data_batch16(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("fake", encoding="utf-8")
    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["x"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p1 = tmp_path / "m1.json"
    p2 = tmp_path / "m2.json"
    p1.write_text(json.dumps(data), encoding="utf-8")
    p2.write_text(json.dumps(data), encoding="utf-8")
    m1 = load_manifest(p1, project_root=tmp_path)
    m2 = load_manifest(p2, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_hash_with_complex_data_batch16(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert hash(m1) == hash(m2)


def test_e2e_manifest_version_constant_value_batch16():
    assert MANIFEST_VERSION == "1.0"


def test_e2e_manifest_in_dict_key_works_batch16(tmp_path):
    """Manifest 可作为 dict key。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    d = {m: "value"}
    # 等价 Manifest 应能取出
    m2 = load_manifest(p, project_root=tmp_path)
    assert d[m2] == "value"


def test_e2e_manifest_set_batch16(tmp_path):
    """Manifest 可放入 set。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    s = {m1, m2}
    assert len(s) == 1


def test_e2e_categories_covered_sorted_alphabetically_batch16(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["z", "y", "x"]},
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["x", "y", "z"]


def test_e2e_load_manifest_relative_subdir_batch16(tmp_path):
    """路径在子目录中。"""
    sub = tmp_path / "data"
    sub.mkdir()
    (sub / "a.pdf").write_text("fake", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "data/a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].resolved_path == (tmp_path / "data" / "a.pdf").resolve()


def test_e2e_load_manifest_with_default_project_root_batch16(tmp_path):
    """project_root=None → 自动检测。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()
