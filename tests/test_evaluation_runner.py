"""runner.py 的单元测试：聚焦 _process_one 的返回值契约。

端到端的 CLI 测试见 tests/test_evaluation_cli.py；这里覆盖
错误路径下 image_dir 的返回值（必须为 None，不能是 Path()）。
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


@dataclass
class _FakeDocEntry:
    """模拟 manifest.DocumentEntry 的最小结构。"""
    doc_id: str
    resolved_path: Path
    source_type: str = "docx"
    expectations: dict | None = None
    annotation_resolved: Path | None = None


@dataclass
class _FakeExpectedFailure:
    """模拟 manifest.ExpectedFailure 的最小结构。"""
    doc_id: str
    resolved_path: Path
    expected_error_code: str
    source_type: str | None = None


@dataclass
class _FakeManifest:
    """模拟 evaluation.manifest.Manifest 的最小结构。"""
    manifest_version: str = "1.0"
    devset_status: str = "incomplete"
    documents: tuple = ()
    expected_failures: tuple = ()
    project_root: Path | None = None
    # Manifest 的 @property
    @property
    def file_count(self) -> int:
        return len(self.documents)
    @property
    def pdf_count(self) -> int:
        return sum(1 for d in self.documents if d.source_type == "pdf")
    @property
    def docx_count(self) -> int:
        return sum(1 for d in self.documents if d.source_type == "docx")
    @property
    def content_group_count(self) -> int:
        return len(self.documents)
    @property
    def categories_covered(self) -> list[str]:
        s: set[str] = set()
        for d in self.documents:
            s.update(getattr(d, "categories", ()))
        return sorted(s)


def _write_minimal_docx(path: Path, text: str = "Hello world.") -> Path:
    """构造最小合法 DOCX。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)
    return path


def test_process_one_returns_none_image_dir_on_failure(tmp_path: Path):
    """当 process_single 失败时，_process_one 第 5 个返回值必须为 None。

    回归：早期版本返回 `image_dir or Path()`，当 image_dir 为 None 时
    退化成 `Path()`（= 当前工作目录）。下游 `image_dir.is_dir()` 会把
    cwd 当作 image_base_dir，虽然失败文档无图片所以无害，但语义错误。
    """
    missing = tmp_path / "does_not_exist.docx"
    doc = _FakeDocEntry(doc_id="missing-1", resolved_path=missing)

    document, error, elapsed, parser_version, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800,
    )
    assert document is None
    assert error is not None
    assert error["code"] == "file_not_found"
    assert elapsed >= 0
    assert parser_version is None
    # 关键不变量：image_dir 必须是 None，不能是 Path()
    assert image_dir is None, (
        f"image_dir 应为 None（失败文档无图片），实际为 {image_dir!r}"
    )


def test_process_one_returns_path_image_dir_on_success(tmp_path: Path):
    """成功路径下，image_dir 应是 Path 对象（指向 _per_doc/images-<sha16>）。"""
    docx_path = tmp_path / "input" / "sample.docx"
    _write_minimal_docx(docx_path)

    doc = _FakeDocEntry(doc_id="ok-1", resolved_path=docx_path)
    document, error, elapsed, parser_version, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800,
    )
    assert document is not None
    assert error is None
    assert parser_version is not None
    # image_dir 应是 Path 对象，且不等于当前工作目录
    assert image_dir is not None
    assert isinstance(image_dir, Path)
    # 名字应为 images-<sha16>
    assert image_dir.name.startswith("images-")
    assert image_dir.parent.name == "_per_doc"


# ---------- _process_one 边角（Round 27） ----------


def test_process_one_cleans_up_out_stub_file(tmp_path: Path):
    """成功的 _process_one 应删除中间产物 out_stub（write_json=False 但有 stub 路径）。"""
    docx_path = tmp_path / "input" / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="clean-1", resolved_path=docx_path)
    out_stub = tmp_path / "_per_doc" / "clean-1.json"

    _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    # stub 不应残留
    assert not out_stub.is_file()


def test_process_one_unsupported_extension_returns_unsupported_type(tmp_path: Path):
    """不支持的扩展名 → error code = unsupported_type（fallback parser 抛 ParserError）。"""
    p = tmp_path / "x.unknownext"
    p.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="bad-ext", resolved_path=p)
    document, error, elapsed, parser_version, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800,
    )
    assert document is None
    assert error is not None
    assert error["code"] == "unsupported_type"
    assert image_dir is None


# ---------- _load_annotation ----------


def test_load_annotation_none_path_returns_none():
    assert _load_annotation(None) is None


def test_load_annotation_missing_file_returns_none(tmp_path: Path):
    assert _load_annotation(tmp_path / "nope.json") is None


def test_load_annotation_valid_json_returns_dict(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"annotation_version": "1.0", "doc_id": "x"}), encoding="utf-8")
    result = _load_annotation(p)
    assert result is not None
    assert result["doc_id"] == "x"


def test_load_annotation_invalid_json_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert _load_annotation(p) is None


# ---------- run_evaluation 端到端 ----------


def test_run_evaluation_empty_manifest(tmp_path: Path):
    """空 manifest → per_doc 与 expected_failures 都为空，summary 结构完整。"""
    manifest = _FakeManifest(project_root=tmp_path)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    assert report["report_version"] == "1.1"
    assert report["per_doc"] == []
    assert report["expected_failures"] == []
    assert "summary" in report
    assert "provenance" in report
    assert "devset" in report
    # 报告文件确实写到磁盘
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["report_version"] == "1.1"


def test_run_evaluation_single_doc_success(tmp_path: Path):
    docx_path = tmp_path / "samples" / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="DC-1", resolved_path=docx_path, source_type="docx"),),
        project_root=tmp_path,
    )
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    assert len(report["per_doc"]) == 1
    pd = report["per_doc"][0]
    assert pd["doc_id"] == "DC-1"
    assert pd["source_type"] == "docx"
    # pipeline 应成功
    assert pd["metrics"]["pipeline_success"]["value"] is True
    # 计时占位
    assert pd["wall_time_seconds"]["parse_reason"] == "not_instrumented"
    assert pd["wall_time_seconds"]["chunk_reason"] == "not_instrumented"
    assert pd["wall_time_seconds"]["parse"] is None
    assert pd["wall_time_seconds"]["chunk"] is None
    assert pd["wall_time_seconds"]["total"] >= 0


def test_run_evaluation_failed_doc_records_pipeline_failed_metrics(tmp_path: Path):
    """失败的 doc 应在 per_doc 中，metrics 大多 null + pipeline_failed。"""
    missing = tmp_path / "missing.docx"
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="MISSING", resolved_path=missing),),
        project_root=tmp_path,
    )
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    pd = report["per_doc"][0]
    assert pd["metrics"]["pipeline_success"]["value"] is False
    assert pd["metrics"]["element_count_total"]["reason"] == "pipeline_failed"
    assert pd["metrics"]["error_code"]["value"] == "file_not_found"


def test_run_evaluation_expected_failures_match(tmp_path: Path):
    """expected_failures 中的 doc：actual_code 匹配 expected_code。"""
    missing = tmp_path / "missing.docx"
    manifest = _FakeManifest(
        documents=(),
        expected_failures=(
            _FakeExpectedFailure(
                doc_id="ERR-1",
                resolved_path=missing,
                expected_error_code="file_not_found",
            ),
        ),
        project_root=tmp_path,
    )
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    efs = report["expected_failures"]
    assert len(efs) == 1
    assert efs[0]["doc_id"] == "ERR-1"
    assert efs[0]["expected_error_code"] == "file_not_found"
    assert efs[0]["actual_error_code"] == "file_not_found"
    assert efs[0]["matches"] is True


def test_run_evaluation_expected_failures_mismatch_recorded(tmp_path: Path):
    """expected vs actual 不匹配也应记录（matches=False）。"""
    # 创建一个合法 docx 但期望它失败（期望错误地写 no_extracted_elements）
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(),
        expected_failures=(
            _FakeExpectedFailure(
                doc_id="ERR-MISMATCH",
                resolved_path=docx_path,
                expected_error_code="no_extracted_elements",  # 不会发生
            ),
        ),
        project_root=tmp_path,
    )
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    efs = report["expected_failures"]
    assert len(efs) == 1
    # actual 是 None（成功了），expected 是 no_extracted_elements
    assert efs[0]["actual_error_code"] is None
    assert efs[0]["matches"] is False


def test_run_evaluation_with_annotation_file(tmp_path: Path):
    """annotation_file 存在时应被加载（chunk_boundary 不再是 no_annotation）。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path, text="alpha beta gamma")
    annotation_path = tmp_path / "annotations" / "x.json"
    annotation_path.parent.mkdir(parents=True)
    annotation_path.write_text(json.dumps({
        "annotation_version": "1.0",
        "doc_id": "DC-1",
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "before"}
        ],
    }), encoding="utf-8")

    manifest = _FakeManifest(
        documents=(
            _FakeDocEntry(
                doc_id="DC-1",
                resolved_path=docx_path,
                source_type="docx",
                annotation_resolved=annotation_path,
            ),
        ),
        project_root=tmp_path,
    )
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    pd = report["per_doc"][0]
    # 加载到 annotation → chunk_boundary_recall 不应是 no_annotation
    recall_reason = pd["metrics"]["chunk_boundary_recall"]["reason"]
    assert recall_reason != "no_annotation"


def test_run_evaluation_per_doc_excludes_private_fields(tmp_path: Path):
    """公开的 per_doc 不应包含 _annotation_present / _tolerance_chars / _missing_markers 等私有字段。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="DC-1", resolved_path=docx_path),),
        project_root=tmp_path,
    )
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    pd = report["per_doc"][0]
    assert "_annotation_present" not in pd
    assert "_tolerance_chars" not in pd
    assert "_missing_markers" not in pd
    # 公开字段
    assert set(pd.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_creates_output_parent_dirs(tmp_path: Path):
    """output_path 在嵌套不存在的目录下也应自动创建。"""
    manifest = _FakeManifest(project_root=tmp_path)
    out = tmp_path / "deep" / "nested" / "report.json"
    run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    assert out.is_file()


def test_run_evaluation_report_passes_schema(tmp_path: Path):
    """生成的报告应通过 evaluation-report schema。"""
    from evaluation.schema import validate
    manifest = _FakeManifest(project_root=tmp_path)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    # 重新加载磁盘版本（不是返回的 dict）
    with out.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    validate(loaded, "evaluation-report.schema.json")


def test_run_evaluation_parser_version_propagates_to_provenance(tmp_path: Path):
    """成功文档的 parser_version 应进入 provenance。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="DC-1", resolved_path=docx_path),),
        project_root=tmp_path,
    )
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    prov = report["provenance"]
    assert prov["parser_name"] == "fallback"
    # parser_version 应是非 null 字符串
    assert prov["parser_version"] is not None
    assert isinstance(prov["parser_version"], str)


def test_run_evaluation_max_chars_propagates_to_provenance(tmp_path: Path):
    manifest = _FakeManifest(project_root=tmp_path)
    out = tmp_path / "report.json"
    report = run_evaluation(
        manifest, out, parser_name="fallback", max_chars=1234,
    )
    assert report["provenance"]["max_chars"] == 1234
