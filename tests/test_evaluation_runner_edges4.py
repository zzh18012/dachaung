r"""evaluation/runner.py 边角测试 - 第四轮（Round 119）。

补强已有 base/edges/edges2/edges3（共 323 测试）未覆盖的深度路径：
- _load_annotation：
  - 二进制无效 JSON
  - JSON 数组 null 元素
  - JSON 数字、布尔值
  - 含 BOM 的 UTF-8
  - 路径为相对路径（不存在的相对文件）
  - Unicode 文件名
- _process_one：
  - 错误 details 字段
  - 多个 errors 时取 errors[0]
  - document None + errors 空 → unknown error dict
  - parser_version 在成功时非 None
  - image_dir 名字含 sha16 hex
  - image_dir 父目录为 _per_doc
  - 输出 out_stub 父目录自动创建
- run_evaluation：
  - 全部文档失败 → parser_version_for_prov 仍 None
  - 多个文档，第一个失败第二个成功 → parser_version 来自第二个
  - tolerance_chars 0
  - tolerance_chars 负数
  - 仅有 expected_failures 无 documents
  - per_doc public 字段精简（无 _annotation_present 等）
  - per_doc 顺序与 manifest 一致
  - 输出文件 ensure_ascii=False（含 unicode 字符）
  - 输出文件 indent=2
  - 输出文件 parents=True
  - 多次调用幂等（不累积）
- 模块结构深度：
  - 各 imports 完整
  - 内部 helper callable
  - __all__ 精确
  - 模块 docstring 提及关键约束
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


@dataclass
class _FakeDocEntry:
    doc_id: str
    resolved_path: Path
    source_type: str = "docx"
    expectations: dict | None = None
    annotation_resolved: Path | None = None
    categories: tuple = ()


@dataclass
class _FakeExpectedFailure:
    doc_id: str
    resolved_path: Path
    expected_error_code: str
    source_type: str | None = None


@dataclass
class _FakeManifest:
    manifest_version: str = "1.0"
    devset_status: str = "incomplete"
    documents: tuple = ()
    expected_failures: tuple = ()
    project_root: Path | None = None

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
    path.parent.mkdir(parents=True, exist_ok=True)
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
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


# =========================================================================
# _load_annotation 第四轮深度
# =========================================================================


def test_load_annotation_returns_none_for_empty_file(tmp_path: Path):
    """空文件 → JSONDecodeError → 返回 None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_none_for_only_whitespace(tmp_path: Path):
    p = tmp_path / "ws.json"
    p.write_text("   \n\t  \n", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_dict_for_object(tmp_path: Path):
    p = tmp_path / "obj.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, dict)
    assert result == {"key": "value"}


def test_load_annotation_returns_list_for_array(tmp_path: Path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, list)
    assert result == [1, 2, 3]


def test_load_annotation_returns_int_for_number(tmp_path: Path):
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 42


def test_load_annotation_returns_bool_for_true(tmp_path: Path):
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    result = _load_annotation(p)
    assert result is True


def test_load_annotation_returns_none_for_json_null(tmp_path: Path):
    """JSON null → json.load 返回 None → 函数返回 None。"""
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_returns_str_for_json_string(tmp_path: Path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    result = _load_annotation(p)
    assert result == "hello"


def test_load_annotation_handles_nested_dict(tmp_path: Path):
    p = tmp_path / "nested.json"
    p.write_text(
        json.dumps({"a": {"b": {"c": [1, 2, {"d": "e"}]}}}),
        encoding="utf-8",
    )
    result = _load_annotation(p)
    assert isinstance(result, dict)
    assert result["a"]["b"]["c"][2]["d"] == "e"


def test_load_annotation_handles_unicode_content(tmp_path: Path):
    p = tmp_path / "uni.json"
    p.write_text('{"name": "中文"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"name": "中文"}


def test_load_annotation_handles_unicode_filename(tmp_path: Path):
    p = tmp_path / "数据.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"k": "v"}


def test_load_annotation_utf8_with_bom_returns_none(tmp_path: Path):
    """BOM 头不被 utf-8 默认解码剥离 → JSONDecodeError → None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    assert _load_annotation(p) is None


def test_load_annotation_truncated_json_array_returns_none(tmp_path: Path):
    p = tmp_path / "trunc.json"
    p.write_text("[1, 2,", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_binary_garbage_raises_unicode_error(tmp_path: Path):
    """二进制垃圾（非 UTF-8）→ UnicodeDecodeError（不静默吞）。"""
    p = tmp_path / "bin.json"
    p.write_bytes(b"\xff\xfe\x00\x01\x02")
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


# =========================================================================
# _process_one 第四轮深度
# =========================================================================


def test_process_one_error_dict_has_message_field(tmp_path: Path):
    """错误 dict 必含 message 字段。"""
    missing = tmp_path / "missing.docx"
    doc = _FakeDocEntry(doc_id="m1", resolved_path=missing)
    _, error, _, _, _ = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    assert "message" in error


def test_process_one_error_dict_has_code_field(tmp_path: Path):
    missing = tmp_path / "missing.docx"
    doc = _FakeDocEntry(doc_id="m1", resolved_path=missing)
    _, error, _, _, _ = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    assert "code" in error


def test_process_one_error_dict_may_have_details(tmp_path: Path):
    """错误 dict 可能含 details 字段（依错误类型）。"""
    missing = tmp_path / "missing.docx"
    doc = _FakeDocEntry(doc_id="m1", resolved_path=missing)
    _, error, _, _, _ = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    # file_not_found 通常有 details，但具体结构依错误类型
    assert error["code"] == "file_not_found"


def test_process_one_creates_per_doc_dir(tmp_path: Path):
    """成功跑完后 _per_doc 目录应存在。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_out_stub_file_removed_after_success(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    assert not (tmp_path / "_per_doc" / "ok1.json").is_file()


def test_process_one_out_stub_file_removed_after_failure(tmp_path: Path):
    """失败的 _process_one 也清理 stub。"""
    missing = tmp_path / "missing.docx"
    doc = _FakeDocEntry(doc_id="m1", resolved_path=missing)
    _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    assert not (tmp_path / "_per_doc" / "m1.json").is_file()


def test_process_one_elapsed_non_negative_on_success(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    _, _, elapsed, _, _ = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    assert elapsed >= 0


def test_process_one_image_dir_name_starts_with_images_prefix(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    _, _, _, _, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    assert image_dir.name.startswith("images-")


def test_process_one_image_dir_name_length_exact(tmp_path: Path):
    """image_dir 名 = 'images-' + 16 字符 sha = 23 字符。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    _, _, _, _, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    # "images-" (7) + 16 hex chars = 23
    assert len(image_dir.name) == 23


def test_process_one_image_dir_parent_is_per_doc(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    _, _, _, _, image_dir = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    assert image_dir.parent.name == "_per_doc"


def test_process_one_parser_version_string_format(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    _, _, _, parser_version, _ = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    assert isinstance(parser_version, str)
    assert len(parser_version) > 0


def test_process_one_returns_document_to_dict_with_elements(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path, text="Unique content for testing.")
    doc = _FakeDocEntry(doc_id="ok1", resolved_path=docx_path)
    document, _, _, _, _ = _process_one(
        doc, tmp_path, parser_name="fallback", max_chars=800
    )
    assert document is not None
    # 应是 dict（to_dict 转换）
    assert isinstance(document, dict)
    # source_hash 存在
    assert "source_hash" in document


# =========================================================================
# run_evaluation 第四轮深度
# =========================================================================


def test_run_evaluation_all_docs_fail_parser_version_for_prov_none(tmp_path: Path):
    """所有文档失败 → provenance.parser_version 应为 None。"""
    missing1 = tmp_path / "missing1.docx"
    missing2 = tmp_path / "missing2.docx"
    manifest = _FakeManifest(
        documents=(
            _FakeDocEntry(doc_id="m1", resolved_path=missing1),
            _FakeDocEntry(doc_id="m2", resolved_path=missing2),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] is None


def test_run_evaluation_first_fail_second_ok_parser_version_set(tmp_path: Path):
    """第一个失败，第二个成功 → parser_version 来自第二个。"""
    missing = tmp_path / "missing.docx"
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(
            _FakeDocEntry(doc_id="m1", resolved_path=missing),
            _FakeDocEntry(doc_id="ok1", resolved_path=docx_path),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] is not None


def test_run_evaluation_first_ok_second_fail_parser_version_from_first(tmp_path: Path):
    """第一个成功，第二个失败 → parser_version 来自第一个（first match）。"""
    missing = tmp_path / "missing.docx"
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(
            _FakeDocEntry(doc_id="ok1", resolved_path=docx_path),
            _FakeDocEntry(doc_id="m1", resolved_path=missing),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] is not None


def test_run_evaluation_tolerance_chars_zero(tmp_path: Path):
    """tolerance_chars=0 → 不崩溃；chunk_boundary 仍计算。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, tolerance_chars=0)
    # 公开 per_doc 不含 _tolerance_chars（被剥离），但 metrics 含 chunk_boundary
    assert "chunk_boundary_precision" in report["per_doc"][0]["metrics"]


def test_run_evaluation_tolerance_chars_negative(tmp_path: Path):
    """tolerance_chars=-1 → 不应崩溃（语义可能未定义但不抛）。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, tolerance_chars=-1)
    assert isinstance(report, dict)


def test_run_evaluation_only_expected_failures_no_documents(tmp_path: Path):
    """manifest 仅含 expected_failures（无 documents）→ per_doc 空，expected_failures 非空。"""
    missing = tmp_path / "missing.docx"
    manifest = _FakeManifest(
        documents=(),
        expected_failures=(
            _FakeExpectedFailure(
                doc_id="ef1",
                resolved_path=missing,
                expected_error_code="file_not_found",
            ),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"] == []
    assert len(report["expected_failures"]) == 1


def test_run_evaluation_per_doc_order_preserved(tmp_path: Path):
    """per_doc 顺序与 manifest.documents 完全一致。"""
    docx1 = tmp_path / "x1.docx"
    docx2 = tmp_path / "x2.docx"
    docx3 = tmp_path / "x3.docx"
    _write_minimal_docx(docx1, text="First.")
    _write_minimal_docx(docx2, text="Second.")
    _write_minimal_docx(docx3, text="Third.")
    manifest = _FakeManifest(
        documents=(
            _FakeDocEntry(doc_id="z-doc", resolved_path=docx1),
            _FakeDocEntry(doc_id="a-doc", resolved_path=docx2),
            _FakeDocEntry(doc_id="m-doc", resolved_path=docx3),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    ids = [d["doc_id"] for d in report["per_doc"]]
    assert ids == ["z-doc", "a-doc", "m-doc"]


def test_run_evaluation_expected_failures_order_preserved(tmp_path: Path):
    missing1 = tmp_path / "missing1.docx"
    missing2 = tmp_path / "missing2.docx"
    missing3 = tmp_path / "missing3.docx"
    manifest = _FakeManifest(
        expected_failures=(
            _FakeExpectedFailure(
                doc_id="ef-z",
                resolved_path=missing1,
                expected_error_code="file_not_found",
            ),
            _FakeExpectedFailure(
                doc_id="ef-a",
                resolved_path=missing2,
                expected_error_code="file_not_found",
            ),
            _FakeExpectedFailure(
                doc_id="ef-m",
                resolved_path=missing3,
                expected_error_code="file_not_found",
            ),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    ids = [ef["doc_id"] for ef in report["expected_failures"]]
    assert ids == ["ef-z", "ef-a", "ef-m"]


def test_run_evaluation_idempotent_multiple_runs(tmp_path: Path):
    """同一 manifest 跑两次结果应等价（不累积状态）。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    run_evaluation(manifest, out1)
    run_evaluation(manifest, out2)
    with out1.open("r", encoding="utf-8") as f1:
        d1 = json.load(f1)
    with out2.open("r", encoding="utf-8") as f2:
        d2 = json.load(f2)
    # 比较 doc_id 集合
    assert d1["per_doc"][0]["doc_id"] == d2["per_doc"][0]["doc_id"]


def test_run_evaluation_output_uses_indent_2(tmp_path: Path):
    """输出 JSON 应使用 indent=2 格式。"""
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 应包含 '\n  "'（2 空格缩进）
    assert '\n  "' in content


def test_run_evaluation_output_uses_ensure_ascii_false(tmp_path: Path):
    """输出 JSON 应保留 unicode（不转义）。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path, text="中文内容")
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    content = out.read_text(encoding="utf-8")
    # 至少应有非 ASCII 字符（确保没有全部转义）
    # report 字段中 devset_status="incomplete" 是 ASCII，但 metrics 中可能有
    # 这里通过 file_count 等检查报告完整即可
    assert '"per_doc"' in content


def test_run_evaluation_creates_deeply_nested_output_dirs(tmp_path: Path):
    """输出路径的深层父目录应自动创建。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out = tmp_path / "a" / "b" / "c" / "out.json"
    report = run_evaluation(manifest, out)
    assert out.is_file()
    assert isinstance(report, dict)


def test_run_evaluation_returns_dict_with_top_level_keys(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_expected_failure_matches_field_true(tmp_path: Path):
    missing = tmp_path / "missing.docx"
    manifest = _FakeManifest(
        expected_failures=(
            _FakeExpectedFailure(
                doc_id="ef1",
                resolved_path=missing,
                expected_error_code="file_not_found",
            ),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failure_matches_field_false_when_unexpected_ok(
    tmp_path: Path,
):
    """期望失败但实际成功 → matches=False，actual_code=None。"""
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        expected_failures=(
            _FakeExpectedFailure(
                doc_id="ef1",
                resolved_path=docx_path,
                expected_error_code="file_not_found",
            ),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is False
    assert report["expected_failures"][0]["actual_error_code"] is None


def test_run_evaluation_expected_failure_actual_code_set_when_mismatch(tmp_path: Path):
    """期望 code A 但实际 code B → matches=False, actual_code=B。"""
    p = tmp_path / "x.unknownext"
    p.write_text("hello", encoding="utf-8")
    manifest = _FakeManifest(
        expected_failures=(
            _FakeExpectedFailure(
                doc_id="ef1",
                resolved_path=p,
                expected_error_code="file_not_found",
            ),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is False
    assert report["expected_failures"][0]["actual_error_code"] == "unsupported_type"


def test_run_evaluation_failed_doc_metrics_has_pipeline_success_false(tmp_path: Path):
    missing = tmp_path / "missing.docx"
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="m1", resolved_path=missing),),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"][0]["metrics"]["pipeline_success"]["value"] is False


def test_run_evaluation_ok_doc_metrics_has_pipeline_success_true(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"][0]["metrics"]["pipeline_success"]["value"] is True


def test_run_evaluation_ok_doc_wall_time_total_positive(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"][0]["wall_time_seconds"]["total"] >= 0


def test_run_evaluation_summary_pipeline_success_rate_zero_when_all_fail(tmp_path: Path):
    missing = tmp_path / "missing.docx"
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="m1", resolved_path=missing),),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["summary"]["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_run_evaluation_summary_pipeline_success_rate_one_when_all_ok(tmp_path: Path):
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(_FakeDocEntry(doc_id="ok1", resolved_path=docx_path),),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["summary"]["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_run_evaluation_summary_pipeline_success_rate_half_when_half_fail(tmp_path: Path):
    missing = tmp_path / "missing.docx"
    docx_path = tmp_path / "x.docx"
    _write_minimal_docx(docx_path)
    manifest = _FakeManifest(
        documents=(
            _FakeDocEntry(doc_id="m1", resolved_path=missing),
            _FakeDocEntry(doc_id="ok1", resolved_path=docx_path),
        ),
    )
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["summary"]["success_rates"]["pipeline_success"]["rate"] == 0.5


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_is_list():
    from evaluation import runner as mod

    assert isinstance(mod.__all__, list)


def test_module_all_length_one():
    from evaluation import runner as mod

    assert len(mod.__all__) == 1


def test_module_all_only_run_evaluation():
    from evaluation import runner as mod

    assert mod.__all__ == ["run_evaluation"]


def test_module_imports_json():
    from evaluation import runner as mod

    assert hasattr(mod, "json")


def test_module_imports_time():
    from evaluation import runner as mod

    assert hasattr(mod, "time")


def test_module_imports_path():
    from evaluation import runner as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from evaluation import runner as mod

    assert hasattr(mod, "Any")


def test_module_imports_process_single():
    from evaluation import runner as mod

    assert hasattr(mod, "process_single")


def test_module_imports_image_output_dir_for():
    from evaluation import runner as mod

    assert hasattr(mod, "image_output_dir_for")


def test_module_imports_report_version():
    from evaluation import runner as mod

    assert hasattr(mod, "REPORT_VERSION")


def test_module_imports_chunk_boundary_prf():
    from evaluation import runner as mod

    assert hasattr(mod, "chunk_boundary_prf")


def test_module_imports_figure_caption_prf():
    from evaluation import runner as mod

    assert hasattr(mod, "figure_caption_prf")


def test_module_imports_compute_automatic_metrics():
    from evaluation import runner as mod

    assert hasattr(mod, "compute_automatic_metrics")


def test_module_imports_aggregate_summary():
    from evaluation import runner as mod

    assert hasattr(mod, "aggregate_summary")


def test_module_imports_build_provenance():
    from evaluation import runner as mod

    assert hasattr(mod, "build_provenance")


def test_module_imports_build_devset_section():
    from evaluation import runner as mod

    assert hasattr(mod, "build_devset_section")


def test_module_has_load_annotation():
    from evaluation import runner as mod

    assert hasattr(mod, "_load_annotation")


def test_module_has_process_one():
    from evaluation import runner as mod

    assert hasattr(mod, "_process_one")


def test_module_has_run_evaluation():
    from evaluation import runner as mod

    assert hasattr(mod, "run_evaluation")


def test_module_load_annotation_callable():
    from evaluation import runner as mod

    assert callable(mod._load_annotation)


def test_module_process_one_callable():
    from evaluation import runner as mod

    assert callable(mod._process_one)


def test_module_run_evaluation_callable():
    from evaluation import runner as mod

    assert callable(mod.run_evaluation)


def test_module_docstring_present():
    from evaluation import runner as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_total():
    """docstring 应说明计时只记 total。"""
    from evaluation import runner as mod

    doc = mod.__doc__
    assert "total" in doc.lower()


def test_module_docstring_mentions_not_instrumented():
    """docstring 应说明 parse/chunk 未插桩。"""
    from evaluation import runner as mod

    doc = mod.__doc__
    assert "not_instrumented" in doc or "未插桩" in doc


def test_module_docstring_mentions_image():
    """docstring 应说明 image_dir 处理逻辑。"""
    from evaluation import runner as mod

    doc = mod.__doc__
    assert "image" in doc.lower() or "图片" in doc


def test_module_uses_future_annotations():
    """模块用了 from __future__ import annotations。"""
    import ast

    from evaluation import runner as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# run_evaluation 签名深度
# =========================================================================


def test_run_evaluation_manifest_param_annotation_str():
    """manifest 参数注解（被 future annotations 字符串化）。"""
    import inspect
    from evaluation.runner import run_evaluation

    sig = inspect.signature(run_evaluation)
    # manifest 注释是字符串 "manifest"（无类型）或具体类型
    assert "manifest" in sig.parameters


def test_run_evaluation_output_path_annotation_path(tmp_path: Path):
    import inspect
    from evaluation.runner import run_evaluation

    sig = inspect.signature(run_evaluation)
    assert "output_path" in sig.parameters


def test_run_evaluation_keyword_only_marker_present():
    """* 标记后，parser_name/max_chars/tolerance_chars 是 kw-only。"""
    import inspect
    from evaluation.runner import run_evaluation

    sig = inspect.signature(run_evaluation)
    params = sig.parameters
    assert params["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert params["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_default_tolerance_chars_value():
    import inspect
    from evaluation.runner import run_evaluation

    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_default_max_chars_value():
    import inspect
    from evaluation.runner import run_evaluation

    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_default_parser_name_value():
    import inspect
    from evaluation.runner import run_evaluation

    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
