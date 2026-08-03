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
