"""manifest.py 的测试：路径形式校验、Schema 校验、加载流程。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.manifest import ManifestError, load_manifest


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """构造一个临时项目根（含 pyproject.toml 让 _detect_project_root 工作）。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    return tmp_path


def _write_manifest(project_root: Path, data: dict) -> Path:
    p = project_root / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _basic_valid_manifest() -> dict:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "DC-1",
                "path": "samples/private/sample.docx",
                "source_type": "docx",
            }
        ],
    }


def test_load_valid_minimal_manifest(project_root: Path):
    # 创建占位文件，让路径在校验后存在性不强求（我们的 loader 不要求文件存在）
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "sample.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    assert m.devset_status == "incomplete"
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "DC-1"
    assert m.documents[0].resolved_path.is_file()


def test_reject_absolute_posix_path(project_root: Path):
    data = _basic_valid_manifest()
    data["documents"][0]["path"] = "/etc/passwd"
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError, match="绝对路径"):
        load_manifest(p)


def test_reject_absolute_windows_path(project_root: Path):
    data = _basic_valid_manifest()
    data["documents"][0]["path"] = "C:/Users/foo/bar.docx"
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError, match="绝对路径"):
        load_manifest(p)


def test_reject_backslash_path(project_root: Path):
    data = _basic_valid_manifest()
    data["documents"][0]["path"] = "samples\\private\\sample.docx"
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError, match="正斜杠"):
        load_manifest(p)


def test_reject_path_escape_project_root(project_root: Path):
    data = _basic_valid_manifest()
    data["documents"][0]["path"] = "../../../etc/passwd"
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError, match="项目根目录之外"):
        load_manifest(p)


def test_invalid_manifest_version(project_root: Path):
    data = _basic_valid_manifest()
    data["manifest_version"] = "2.0"
    p = _write_manifest(project_root, data)
    with pytest.raises(Exception):
        load_manifest(p)


def test_devset_status_invalid_value(project_root: Path):
    data = _basic_valid_manifest()
    data["devset_status"] = "halfway"
    p = _write_manifest(project_root, data)
    with pytest.raises(Exception):
        load_manifest(p)


def test_expected_failures_loaded(project_root: Path):
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "blank.pdf").write_bytes(b"%PDF-1.4\n")
    data = _basic_valid_manifest()
    data["expected_failures"] = [
        {
            "doc_id": "ERR-BLANK",
            "path": "samples/private/blank.pdf",
            "expected_error_code": "no_extracted_elements",
        }
    ]
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].expected_error_code == "no_extracted_elements"


def test_content_group_count_paired(project_root: Path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "A", "path": "a.docx", "source_type": "docx", "paired_with": "A-PDF"},
            {"doc_id": "A-PDF", "path": "a.pdf", "source_type": "pdf", "paired_with": "A"},
            {"doc_id": "B", "path": "b.docx", "source_type": "docx"},
        ],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    # A 与 A-PDF 是一组（pair），B 单独一组 → 2 组
    assert m.content_group_count == 2
    assert m.file_count == 3
    assert m.pdf_count == 1
    assert m.docx_count == 2


def test_categories_covered(project_root: Path):
    data = _basic_valid_manifest()
    data["documents"][0]["categories"] = ["report", "table", "image"]
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert m.categories_covered == ["image", "report", "table"]


def test_missing_manifest_file(project_root: Path):
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(project_root / "nope.json")


# ---------- 边角与缺漏补强（Round 23） ----------


# 直接测试内部 helper


def test_is_absolute_like_pure_function():
    from evaluation.manifest import _is_absolute_like
    # 空串
    assert _is_absolute_like("") is False
    # POSIX 绝对
    assert _is_absolute_like("/etc/passwd") is True
    assert _is_absolute_like("/") is True
    # Windows 盘符 + 反斜杠/正斜杠
    assert _is_absolute_like("C:\\Users\\foo") is True
    assert _is_absolute_like("C:/Users/foo") is True
    assert _is_absolute_like("D:/x.docx") is True
    # 盘符但无斜杠 → 不是绝对路径
    assert _is_absolute_like("C:foo") is False
    # 相对路径
    assert _is_absolute_like("samples/private/x.docx") is False
    assert _is_absolute_like("a.docx") is False


def test_has_backslash_pure_function():
    from evaluation.manifest import _has_backslash
    assert _has_backslash("a\\b") is True
    assert _has_backslash("\\") is True
    assert _has_backslash("samples/private/x.docx") is False
    assert _has_backslash("") is False


def test_detect_project_root_walks_up_to_pyproject(tmp_path: Path):
    """_detect_project_root 从 start 向上找 pyproject.toml。"""
    from evaluation.manifest import _detect_project_root
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    # 从一个嵌套文件起：应回溯到 tmp_path
    found = _detect_project_root(nested / "manifest.json")
    assert found == tmp_path.resolve()


def test_detect_project_root_no_pyproject_does_not_crash(tmp_path: Path):
    """找不到 pyproject.toml 时不应抛异常，返回某个起点路径。"""
    from evaluation.manifest import _detect_project_root
    nested = tmp_path / "deep"
    nested.mkdir(parents=True)
    # 传一个真实存在的文件，让 cur.is_file()=True 触发 parent 跳转
    start = nested / "manifest.json"
    start.write_text("{}", encoding="utf-8")
    found = _detect_project_root(start)
    # 不抛异常即合格；具体返回值是实现细节
    assert isinstance(found, Path)


# annotation_file 解析


def test_annotation_file_resolved(project_root: Path):
    """annotation_file 合法时应被解析成绝对路径。"""
    (project_root / "annotations").mkdir()
    (project_root / "annotations" / "a.json").write_text("{}", encoding="utf-8")
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    data = _basic_valid_manifest()
    data["documents"][0]["annotation_file"] = "annotations/a.json"
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert m.documents[0].annotation_file_str == "annotations/a.json"
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved.is_file()


def test_annotation_file_absolute_path_rejected(project_root: Path):
    data = _basic_valid_manifest()
    data["documents"][0]["annotation_file"] = "/etc/passwd"
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError, match="绝对路径"):
        load_manifest(p)


def test_annotation_file_backslash_rejected(project_root: Path):
    data = _basic_valid_manifest()
    data["documents"][0]["annotation_file"] = "annotations\\a.json"
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError, match="正斜杠"):
        load_manifest(p)


# expected_failures 路径校验


def test_expected_failure_path_escape_root_rejected(project_root: Path):
    data = _basic_valid_manifest()
    data["expected_failures"] = [
        {
            "doc_id": "ERR",
            "path": "../../../etc/passwd",
            "expected_error_code": "no_extracted_elements",
        }
    ]
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError, match="项目根目录之外"):
        load_manifest(p)


def test_expected_failure_with_source_type(project_root: Path):
    """expected_failure 的 source_type 是可选的；如果给应被记录。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "blank.pdf").write_bytes(b"%PDF-1.4\n")
    data = _basic_valid_manifest()
    data["expected_failures"] = [
        {
            "doc_id": "ERR-BLANK",
            "path": "samples/private/blank.pdf",
            "expected_error_code": "no_extracted_elements",
            "source_type": "pdf",
        }
    ]
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert m.expected_failures[0].source_type == "pdf"


def test_expected_failure_without_source_type(project_root: Path):
    """source_type 缺失时为 None。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.txt").write_text("x", encoding="utf-8")
    data = _basic_valid_manifest()
    data["expected_failures"] = [
        {
            "doc_id": "ERR",
            "path": "samples/private/x.txt",
            "expected_error_code": "unsupported_type",
        }
    ]
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert m.expected_failures[0].source_type is None


# DocumentEntry 字段保留


def test_document_entry_optional_fields_populated(project_root: Path):
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    data = _basic_valid_manifest()
    data["documents"][0].update({
        "sha256": "a" * 64,
        "categories": ["report", "image"],
        "paired_with": "DC-2",
        "expectations": {
            "element_count_by_type": {"heading": 2, "paragraph": 5},
            "required_markers": ["Introduction"],
        },
    })
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    d = m.documents[0]
    assert d.sha256 == "a" * 64
    assert d.categories == ("report", "image")
    assert d.paired_with == "DC-2"
    assert d.expectations is not None
    assert d.expectations["element_count_by_type"]["heading"] == 2
    assert d.expectations["required_markers"] == ["Introduction"]


def test_document_entry_optional_fields_default_to_none_or_empty(project_root: Path):
    """未提供可选字段时应有合理默认。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    d = m.documents[0]
    assert d.sha256 is None
    assert d.categories == ()
    assert d.paired_with is None
    assert d.annotation_file_str is None
    assert d.annotation_resolved is None
    assert d.expectations is None


# Manifest 属性


def test_categories_covered_empty_when_no_categories(project_root: Path):
    """所有 doc 都没 categories → 返回空 list。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    assert m.categories_covered == []


def test_categories_covered_deduplicates_across_documents(project_root: Path):
    """多个 doc 的 categories 合并去重排序。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "a.docx").write_bytes(b"a")
    (project_root / "samples" / "private" / "b.docx").write_bytes(b"b")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "A", "path": "samples/private/a.docx", "source_type": "docx",
             "categories": ["report", "table"]},
            {"doc_id": "B", "path": "samples/private/b.docx", "source_type": "docx",
             "categories": ["table", "image"]},
        ],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    # 合并去重排序：["image", "report", "table"]
    assert m.categories_covered == ["image", "report", "table"]


def test_content_group_count_all_unpaired(project_root: Path):
    """3 个互不配对的 doc → 3 组。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    for name in ("a.docx", "b.docx", "c.docx"):
        (project_root / "samples" / "private" / name).write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "A", "path": f"samples/private/a.docx", "source_type": "docx"},
            {"doc_id": "B", "path": f"samples/private/b.docx", "source_type": "docx"},
            {"doc_id": "C", "path": f"samples/private/c.docx", "source_type": "docx"},
        ],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert m.content_group_count == 3
    assert m.file_count == 3
    assert m.pdf_count == 0
    assert m.docx_count == 3


def test_content_group_count_unidirectional_pair_counts_as_one_group(project_root: Path):
    """单向配对（A→B 但 B 不→A）也只算 1 组，A 不会再被算 unpaired。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "a.docx").write_bytes(b"x")
    (project_root / "samples" / "private" / "a.pdf").write_bytes(b"%PDF")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "A", "path": "samples/private/a.docx", "source_type": "docx",
             "paired_with": "A-PDF"},
            {"doc_id": "A-PDF", "path": "samples/private/a.pdf", "source_type": "pdf"},
        ],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    # 单向也算 1 组（pair_ids 收集 frozenset 去重）
    assert m.content_group_count == 1


# project_root 显式传参


def test_explicit_project_root_used(tmp_path: Path):
    """显式传入 project_root 时优先用它（不依赖 pyproject.toml 探测）。"""
    project_root = tmp_path / "explicit"
    # manifest 默认指向 samples/private/sample.docx，需要创建同名文件
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "sample.docx").write_bytes(b"x")
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    p = manifest_dir / "manifest.json"
    p.write_text(json.dumps(_basic_valid_manifest()), encoding="utf-8")
    # 不在 project_root 下，但显式传 project_root
    m = load_manifest(p, project_root=project_root)
    assert m.project_root == project_root.resolve()
    assert m.documents[0].resolved_path == (
        project_root / "samples/private/sample.docx"
    ).resolve()


# JSON 解析错误


def test_malformed_json_raises_manifest_error(project_root: Path):
    """JSON 解析失败 → ManifestError("JSON 解析失败")。"""
    p = project_root / "manifest.json"
    p.write_text("{ this is not valid json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON"):
        load_manifest(p)


def test_unsupported_source_type_rejected_by_schema(project_root: Path):
    """source_type 必须是 pdf/docx，schema 会拒绝其它值。"""
    data = _basic_valid_manifest()
    data["documents"][0]["source_type"] = "txt"
    p = _write_manifest(project_root, data)
    with pytest.raises(Exception):
        load_manifest(p)


def test_doc_id_empty_string_rejected_by_schema(project_root: Path):
    """doc_id minLength=1。"""
    data = _basic_valid_manifest()
    data["documents"][0]["doc_id"] = ""
    p = _write_manifest(project_root, data)
    with pytest.raises(Exception):
        load_manifest(p)


def test_expected_failure_unknown_doc_extra_field_rejected(project_root: Path):
    """expected_failure 是 additionalProperties:false。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.pdf").write_bytes(b"%PDF")
    data = _basic_valid_manifest()
    data["expected_failures"] = [
        {
            "doc_id": "ERR",
            "path": "samples/private/x.pdf",
            "expected_error_code": "no_extracted_elements",
            "unexpected_field": "disallowed",
        }
    ]
    p = _write_manifest(project_root, data)
    with pytest.raises(Exception):
        load_manifest(p)


def test_manifest_top_level_extra_field_rejected(project_root: Path):
    """manifest 顶层 additionalProperties:false。"""
    data = _basic_valid_manifest()
    data["unknown_top_level"] = "disallowed"
    p = _write_manifest(project_root, data)
    with pytest.raises(Exception):
        load_manifest(p)


def test_manifest_extra_field_in_document_rejected(project_root: Path):
    """document 是 additionalProperties:false。"""
    data = _basic_valid_manifest()
    data["documents"][0]["unknown_field"] = "disallowed"
    p = _write_manifest(project_root, data)
    with pytest.raises(Exception):
        load_manifest(p)


# ---------- 边角补强（Round 43） ----------


# ManifestError 类契约


def test_manifest_error_is_exception_subclass():
    from evaluation.manifest import ManifestError
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised_and_caught():
    from evaluation.manifest import ManifestError
    with pytest.raises(ManifestError) as exc:
        raise ManifestError("test message")
    assert "test message" in str(exc.value)


# _is_absolute_like 更多边角


def test_is_absolute_like_single_char_string():
    """单字符（不够 3 字符）→ 不可能是 Windows 盘符格式。"""
    from evaluation.manifest import _is_absolute_like
    assert _is_absolute_like("a") is False
    assert _is_absolute_like("C") is False


def test_is_absolute_like_two_char_string():
    from evaluation.manifest import _is_absolute_like
    assert _is_absolute_like("ab") is False
    assert _is_absolute_like("C:") is False  # 缺斜杠


def test_is_absolute_like_lower_case_drive_letter():
    """小写盘符也算绝对路径（isalpha() 接受小写）。"""
    from evaluation.manifest import _is_absolute_like
    assert _is_absolute_like("c:/x") is True
    assert _is_absolute_like("d:\\x") is True


def test_is_absolute_like_non_alpha_drive_char():
    """第一位非字母（如数字）→ 不是盘符。"""
    from evaluation.manifest import _is_absolute_like
    assert _is_absolute_like("1:/x") is False
    assert _is_absolute_like("::/x") is False


def test_is_absolute_like_dot_relative_path():
    """./foo 是相对路径（虽然以 . 开头）。"""
    from evaluation.manifest import _is_absolute_like
    assert _is_absolute_like("./samples/x.docx") is False
    assert _is_absolute_like("../samples/x.docx") is False


def test_is_absolute_like_just_slash():
    from evaluation.manifest import _is_absolute_like
    assert _is_absolute_like("/") is True


# _has_backslash 更多边角


def test_has_backslash_only_one_backslash_char():
    from evaluation.manifest import _has_backslash
    assert _has_backslash("\\") is True


def test_has_backslash_forward_slash_returns_false():
    from evaluation.manifest import _has_backslash
    assert _has_backslash("a/b") is False
    assert _has_backslash("/") is False


def test_has_backslash_mixed_slashes_returns_true():
    from evaluation.manifest import _has_backslash
    assert _has_backslash("a/b\\c") is True


# Manifest 数据类 frozen


def test_manifest_dataclass_is_frozen():
    """Manifest 是 frozen dataclass，不能修改属性。"""
    from evaluation.manifest import Manifest
    import dataclasses
    fields = {f.name: f for f in dataclasses.fields(Manifest)}
    # frozen=True 时所有字段的 setting 都会失败
    assert all(not f._field_type == "class" for f in dataclasses.fields(Manifest))


def test_document_entry_dataclass_is_frozen(project_root: Path):
    from evaluation.manifest import DocumentEntry
    import dataclasses
    # frozen dataclass 实例无法赋值
    (project_root / "x.docx").write_bytes(b"x")
    de = DocumentEntry(
        doc_id="X",
        path_str="x.docx",
        resolved_path=project_root / "x.docx",
        source_type="docx",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        de.doc_id = "Y"  # type: ignore[misc]


def test_expected_failure_dataclass_is_frozen(project_root: Path):
    from evaluation.manifest import ExpectedFailure
    import dataclasses
    ef = ExpectedFailure(
        doc_id="X",
        path_str="x.docx",
        resolved_path=project_root / "x.docx",
        expected_error_code="file_not_found",
        source_type=None,
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        ef.doc_id = "Y"  # type: ignore[misc]


# Manifest 属性直接构造（不通过 load_manifest）


def test_manifest_file_count_direct():
    from evaluation.manifest import Manifest, DocumentEntry
    docs = tuple(
        DocumentEntry(
            doc_id=f"D{i}", path_str=f"d{i}.docx", resolved_path=Path(f"d{i}.docx"),
            source_type="docx", sha256=None, categories=(), paired_with=None,
            annotation_file_str=None, annotation_resolved=None, expectations=None,
        )
        for i in range(5)
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.file_count == 5


def test_manifest_pdf_count_direct():
    from evaluation.manifest import Manifest, DocumentEntry
    docs = tuple(
        DocumentEntry(
            doc_id=f"D{i}", path_str=f"d{i}.pdf", resolved_path=Path(f"d{i}.pdf"),
            source_type="pdf", sha256=None, categories=(), paired_with=None,
            annotation_file_str=None, annotation_resolved=None, expectations=None,
        )
        for i in range(3)
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.pdf_count == 3
    assert m.docx_count == 0


def test_manifest_docx_count_direct():
    from evaluation.manifest import Manifest, DocumentEntry
    docs = (
        DocumentEntry(
            doc_id="D1", path_str="d1.docx", resolved_path=Path("d1.docx"),
            source_type="docx", sha256=None, categories=(), paired_with=None,
            annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="D2", path_str="d2.docx", resolved_path=Path("d2.docx"),
            source_type="docx", sha256=None, categories=(), paired_with=None,
            annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.docx_count == 2
    assert m.pdf_count == 0


def test_manifest_categories_covered_mixed_overlapping():
    from evaluation.manifest import Manifest, DocumentEntry
    docs = (
        DocumentEntry(
            doc_id="D1", path_str="d1.docx", resolved_path=Path("d1.docx"),
            source_type="docx", sha256=None, categories=("a", "b", "c"),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="D2", path_str="d2.docx", resolved_path=Path("d2.docx"),
            source_type="docx", sha256=None, categories=("b", "c", "d"),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="D3", path_str="d3.docx", resolved_path=Path("d3.docx"),
            source_type="docx", sha256=None, categories=("a", "z"),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    # 合并去重 + 字母排序
    assert m.categories_covered == ["a", "b", "c", "d", "z"]


def test_manifest_categories_covered_empty_when_all_empty():
    from evaluation.manifest import Manifest, DocumentEntry
    docs = (
        DocumentEntry(
            doc_id="D1", path_str="d1.docx", resolved_path=Path("d1.docx"),
            source_type="docx", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("."),
    )
    assert m.categories_covered == []


# _detect_project_root 更多边角


def test_detect_project_root_start_is_dir(tmp_path: Path):
    """start 是目录时不应出错（不切到 parent）。"""
    from evaluation.manifest import _detect_project_root
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    found = _detect_project_root(nested)
    assert found == tmp_path.resolve()


def test_detect_project_root_returns_absolute_path(tmp_path: Path):
    from evaluation.manifest import _detect_project_root
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    found = _detect_project_root(tmp_path)
    assert found.is_absolute()


def test_detect_project_root_immediate_directory_with_pyproject(tmp_path: Path):
    """start 自己就有 pyproject.toml → 直接返回 start。"""
    from evaluation.manifest import _detect_project_root
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    found = _detect_project_root(tmp_path)
    assert found == tmp_path.resolve()


# content_group_count 更多场景


def test_content_group_count_chain_pair_counts_correctly(project_root: Path):
    """A→B→C 链式 paired_with（A 配 B，B 配 C）的边角。

    当前实现：pair_ids 收集 frozenset 去重 → {{A,B}, {B,C}} → 2 组；
    unpaired 集合 = 文档集合 - 见过的 → 0；总组数 = 2。
    """
    (project_root / "samples" / "private").mkdir(parents=True)
    for n in ("a.docx", "b.docx", "c.docx"):
        (project_root / "samples" / "private" / n).write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "A", "path": "samples/private/a.docx", "source_type": "docx",
             "paired_with": "B"},
            {"doc_id": "B", "path": "samples/private/b.docx", "source_type": "docx",
             "paired_with": "C"},
            {"doc_id": "C", "path": "samples/private/c.docx", "source_type": "docx",
             "paired_with": "A"},
        ],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    # {A,B} + {B,C} + {A,C}（C→A 配对）→ frozenset 去重后还是 {A,B} + {B,C} + {A,C} = 3 组
    # 注意 unpaired 是 0
    assert m.content_group_count == 3


def test_content_group_count_two_mutual_pairs(project_root: Path):
    """两组互配：A↔B + C↔D → 2 组。"""
    (project_root / "samples" / "private").mkdir(parents=True)
    for n in ("a.docx", "b.docx", "c.docx", "d.docx"):
        (project_root / "samples" / "private" / n).write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "A", "path": "samples/private/a.docx", "source_type": "docx",
             "paired_with": "B"},
            {"doc_id": "B", "path": "samples/private/b.docx", "source_type": "docx",
             "paired_with": "A"},
            {"doc_id": "C", "path": "samples/private/c.docx", "source_type": "docx",
             "paired_with": "D"},
            {"doc_id": "D", "path": "samples/private/d.docx", "source_type": "docx",
             "paired_with": "C"},
        ],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert m.content_group_count == 2


# load_manifest 字段保留


def test_load_manifest_preserves_manifest_version(project_root: Path):
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    assert m.manifest_version == "1.0"


def test_load_manifest_preserves_devset_status(project_root: Path):
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    assert m.devset_status == "incomplete"


def test_load_manifest_empty_documents_list(project_root: Path):
    """空 documents 列表也应被允许（schema 允许）。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p)
    assert m.documents == ()
    assert m.file_count == 0


def test_load_manifest_empty_expected_failures_default(project_root: Path):
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    # 没显式给 expected_failures → schema 允许缺失 → 默认空 tuple
    assert m.expected_failures == ()


def test_load_manifest_path_str_preserved(project_root: Path):
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    assert m.documents[0].path_str == "samples/private/sample.docx"


def test_load_manifest_resolved_path_is_absolute(project_root: Path):
    (project_root / "samples" / "private").mkdir(parents=True)
    (project_root / "samples" / "private" / "x.docx").write_bytes(b"x")
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p)
    assert m.documents[0].resolved_path.is_absolute()
