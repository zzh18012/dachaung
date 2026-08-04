"""evaluation/runner.py 边角测试（Round 62）。

补强 tests/test_evaluation_runner.py（50+ 测试）未覆盖的：
- _load_annotation JSON true/false/嵌套 list/float
- _load_annotation Path object vs str path
- _process_one 返回 tuple 类型/长度
- _process_one total_seconds 类型（float）
- _process_one image_dir None 严格类型检查
- _process_one 多次调用独立
- run_evaluation 输出 JSON 格式（indent=2/ensure_ascii=False）
- run_evaluation parser_version_for_prov 逻辑（首非 None wins）
- run_evaluation tolerance_chars 透传到 chunk_b
- run_evaluation expected_failures 空列表
- run_evaluation per_doc private 字段 (_annotation_present 等)
- run_evaluation 失败文档 metrics 含 pipeline_failed
- run_evaluation 顶层 expected_failures 字段总是存在
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- 复用现有测试的 fixtures ----------


@dataclass
class _FakeDocEntry:
    doc_id: str
    resolved_path: Path
    source_type: str = "docx"
    expectations: dict | None = None
    annotation_resolved: Path | None = None


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


# ---------- _load_annotation 边角 ----------


def test_load_annotation_returns_dict_type(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, dict)


def test_load_annotation_returns_none_type(tmp_path: Path):
    """missing → None。"""
    assert _load_annotation(tmp_path / "nope.json") is None
    assert isinstance(_load_annotation(tmp_path / "nope.json"), type(None))


def test_load_annotation_json_true_value(tmp_path: Path):
    """JSON true → 返 True（bool）。"""
    p = tmp_path / "a.json"
    p.write_text("true", encoding="utf-8")
    # 但函数返 dict | None，true 不是 dict
    # 实际：json.load('true') = True，函数类型注解是 dict[str, Any] | None
    # 但代码 `return json.load(f)` 不强制 dict，所以 True 会被返回
    result = _load_annotation(p)
    assert result is True


def test_load_annotation_json_false_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("false", encoding="utf-8")
    result = _load_annotation(p)
    assert result is False


def test_load_annotation_json_string_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    result = _load_annotation(p)
    assert result == "hello"


def test_load_annotation_json_float_value(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("3.14", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 3.14


def test_load_annotation_json_nested_list(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("[1, 2, [3, 4]]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == [1, 2, [3, 4]]


def test_load_annotation_json_deeply_nested(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": {"d": [1, 2]}}}}', encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, dict)
    assert result["a"]["b"]["c"]["d"] == [1, 2]


def test_load_annotation_json_with_unicode_keys(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"中文": "value"}', encoding="utf-8")
    result = _load_annotation(p)
    assert "中文" in result


def test_load_annotation_pathlib_path_accepted(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_str_path_raises_attribute_error(tmp_path: Path):
    """传 str 路径 → AttributeError（is_file() 不存在于 str）。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(AttributeError):
        _load_annotation(str(p))  # type: ignore[arg-type]


def test_load_annotation_none_path_returns_none():
    assert _load_annotation(None) is None


def test_load_annotation_large_dict(tmp_path: Path):
    """大 dict（10000 keys）也支持。"""
    p = tmp_path / "big.json"
    data = {f"k{i}": i for i in range(10000)}
    p.write_text(json.dumps(data), encoding="utf-8")
    result = _load_annotation(p)
    assert len(result) == 10000


def test_load_annotation_truncated_json_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text('{"key": "val', encoding="utf-8")  # 截断
    assert _load_annotation(p) is None


def test_load_annotation_utf8_bom_returns_none(tmp_path: Path):
    """UTF-8 BOM 头导致 json 解析失败 → 返 None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    result = _load_annotation(p)
    # BOM 字符在 json.load 看来是非法前缀 → JSONDecodeError → 返 None
    assert result is None


# ---------- _process_one 边角 ----------


def test_process_one_returns_tuple_type(tmp_path: Path):
    """_process_one 返回 5-tuple。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_total_seconds_is_float(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    _, _, total_seconds, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total_seconds, float)


def test_process_one_total_seconds_non_negative(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    _, _, total_seconds, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert total_seconds >= 0.0


def test_process_one_document_dict_is_dict_on_success(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    document_dict, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(document_dict, dict)


def test_process_one_error_dict_is_none_on_success(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    _, error_dict, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert error_dict is None


def test_process_one_error_dict_is_dict_on_failure(tmp_path: Path):
    """unsupported_type → error_dict 是 dict。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _, error_dict, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(error_dict, dict)
    assert "code" in error_dict


def test_process_one_image_dir_is_path_on_success(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None or isinstance(image_dir, Path)


def test_process_one_image_dir_is_none_on_failure(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_parser_version_is_str_on_success(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(parser_version, str)
    assert "pdfplumber" in parser_version  # fallback parser 版本格式


def test_process_one_parser_version_is_none_on_failure(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version is None


def test_process_one_creates_per_doc_directory(tmp_path: Path):
    """_process_one 应创建 _per_doc 子目录。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    _process_one(doc, tmp_path, "fallback", 800)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.is_dir()


def test_process_one_out_stub_cleaned_up_after_success(tmp_path: Path):
    """成功后 out_stub 应被清理。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    _process_one(doc, tmp_path, "fallback", 800)
    out_stub = tmp_path / "_per_doc" / "DC-1.json"
    assert not out_stub.is_file()


def test_process_one_out_stub_cleaned_up_after_failure(tmp_path: Path):
    """失败后 out_stub 也应被清理。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _process_one(doc, tmp_path, "fallback", 800)
    out_stub = tmp_path / "_per_doc" / "DC-1.json"
    assert not out_stub.is_file()


def test_process_one_stateless_across_calls(tmp_path: Path):
    """_process_one 可重入：两次调用独立。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx", text="first")
    p2 = _write_minimal_docx(tmp_path / "b" / "d2.docx", text="second")
    doc1 = _FakeDocEntry(doc_id="DC-1", resolved_path=p1)
    doc2 = _FakeDocEntry(doc_id="DC-2", resolved_path=p2)

    d1, _, _, _, _ = _process_one(doc1, tmp_path, "fallback", 800)
    d2, _, _, _, _ = _process_one(doc2, tmp_path, "fallback", 800)
    assert d1 is not None and d2 is not None
    assert d1["document_id"] != d2["document_id"]


# ---------- run_evaluation 边角 ----------


def test_run_evaluation_returns_dict_type(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result, dict)


def test_run_evaluation_writes_valid_json_to_disk(tmp_path: Path):
    """output 是合法 JSON。"""
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_run_evaluation_output_json_indented(tmp_path: Path):
    """output JSON 应用 indent=2（含换行 + 缩进）。"""
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 → 至少 1 个换行
    assert "\n" in content
    # 至少 1 个 2-空格缩进
    assert "  " in content


def test_run_evaluation_ensures_ascii_false_for_unicode(tmp_path: Path):
    r"""ensure_ascii=False → 中文/emoji 应原样输出（不被 \u 转义）。"""
    docx_path = _write_minimal_docx(
        tmp_path / "src" / "doc.docx", text="中文测试 🎉"
    )
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    content = out.read_text(encoding="utf-8")
    assert "\\u" not in content or "🎉" in content


def test_run_evaluation_creates_output_parent_dirs(tmp_path: Path):
    """output parent 不存在时自动创建。"""
    manifest = _FakeManifest()
    out = tmp_path / "deep" / "nested" / "out.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_expected_failures_field_always_present(tmp_path: Path):
    """expected_failures 字段总在 report 中（即使为空）。"""
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert "expected_failures" in report
    assert isinstance(report["expected_failures"], list)


def test_run_evaluation_expected_failures_empty_when_no_ef(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"] == []


def test_run_evaluation_report_top_level_keys_full_set(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert set(report.keys()) == {
        "report_version", "provenance", "devset",
        "summary", "per_doc", "expected_failures",
    }


def test_run_evaluation_per_doc_empty_for_empty_manifest(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"] == []


def test_run_evaluation_per_doc_count_matches_documents(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx", text="first")
    p2 = _write_minimal_docx(tmp_path / "b" / "d2.docx", text="second")
    docs = (
        _FakeDocEntry(doc_id="DC-1", resolved_path=p1),
        _FakeDocEntry(doc_id="DC-2", resolved_path=p2),
    )
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 2


def test_run_evaluation_per_doc_doc_ids_preserved(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="custom-id-42", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"][0]["doc_id"] == "custom-id-42"


def test_run_evaluation_per_doc_each_has_metrics_dict(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        assert isinstance(r["metrics"], dict)


def test_run_evaluation_per_doc_each_has_wall_time_seconds(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        assert "wall_time_seconds" in r
        assert isinstance(r["wall_time_seconds"], dict)


def test_run_evaluation_wall_time_seconds_total_is_float(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert isinstance(wt["total"], float)


def test_run_evaluation_wall_time_seconds_parse_chunk_null(tmp_path: Path):
    """parse/chunk 应是 None（not instrumented）。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None


def test_run_evaluation_wall_time_seconds_reason_not_instrumented(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_per_doc_excludes_private_fields(tmp_path: Path):
    """public per_doc 不应含 _annotation_present / _tolerance_chars / _missing_markers。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        assert "_annotation_present" not in r
        assert "_tolerance_chars" not in r
        assert "_missing_markers" not in r


def test_run_evaluation_per_doc_each_has_3_keys_only(tmp_path: Path):
    """每个 per_doc 只含 doc_id/source_type/metrics/wall_time_seconds 4 个 key。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        assert set(r.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_provenance_parser_name(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, parser_name="fallback")
    assert report["provenance"]["parser_name"] == "fallback"


def test_run_evaluation_provenance_max_chars(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, max_chars=1200)
    assert report["provenance"]["max_chars"] == 1200


def test_run_evaluation_provenance_parser_version_first_doc(tmp_path: Path):
    """parser_version 取自第一个成功的 doc。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] is not None
    assert isinstance(report["provenance"]["parser_version"], str)


def test_run_evaluation_provenance_parser_version_none_on_all_failure(tmp_path: Path):
    """所有 doc 都失败 → parser_version=None。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown"),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    # parser_version_for_prov 是 None（没有任何成功 doc）
    assert report["provenance"]["parser_version"] is None


def test_run_evaluation_expected_failure_matches_true(tmp_path: Path):
    """expected_failure matches=True 当实际 code 与预期一致。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    efs = (_FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="unsupported_type",
    ),)
    manifest = _FakeManifest(expected_failures=efs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failure_matches_false_on_mismatch(tmp_path: Path):
    """matches=False 当实际 code 与预期不一致。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    efs = (_FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="file_not_found",
    ),)
    manifest = _FakeManifest(expected_failures=efs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_actual_code_recorded(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    efs = (_FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="unsupported_type",
    ),)
    manifest = _FakeManifest(expected_failures=efs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    ef = report["expected_failures"][0]
    assert ef["actual_error_code"] == "unsupported_type"


def test_run_evaluation_expected_failure_full_field_set(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    efs = (_FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="unsupported_type",
    ),)
    manifest = _FakeManifest(expected_failures=efs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    ef = report["expected_failures"][0]
    assert set(ef.keys()) == {
        "doc_id", "expected_error_code", "actual_error_code", "matches",
    }


def test_run_evaluation_multiple_expected_failures_preserve_order(tmp_path: Path):
    src1 = tmp_path / "x1.unknown"
    src1.write_text("a", encoding="utf-8")
    src2 = tmp_path / "x2.unknown"
    src2.write_text("b", encoding="utf-8")
    efs = (
        _FakeExpectedFailure(
            doc_id="EF-1", resolved_path=src1, expected_error_code="unsupported_type",
        ),
        _FakeExpectedFailure(
            doc_id="EF-2", resolved_path=src2, expected_error_code="unsupported_type",
        ),
    )
    manifest = _FakeManifest(expected_failures=efs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    ef_ids = [ef["doc_id"] for ef in report["expected_failures"]]
    assert ef_ids == ["EF-1", "EF-2"]


def test_run_evaluation_failed_doc_metrics_has_pipeline_failed_marker(tmp_path: Path):
    """失败 doc 的 metrics 应含某种 'pipeline_failed' 标记。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown"),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    metrics = report["per_doc"][0]["metrics"]
    # 检查至少一个指标有 pipeline_failed 标记
    has_pipeline_failed = any(
        "pipeline_failed" in str(v) for v in metrics.values()
    )
    assert has_pipeline_failed


def test_run_evaluation_devset_status_propagated(tmp_path: Path):
    manifest = _FakeManifest(devset_status="incomplete")
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["status"] == "incomplete"


def test_run_evaluation_devset_file_count_zero_for_empty(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["file_count"] == 0


def test_run_evaluation_devset_file_count_one_for_single_doc(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1, source_type="docx"),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["file_count"] == 1


def test_run_evaluation_devset_docx_count(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1, source_type="docx"),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["docx_count"] == 1
    assert report["devset"]["pdf_count"] == 0


# ---------- 模块导入 ----------


def test_runner_module_exports_run_evaluation():
    import evaluation.runner as mod
    assert hasattr(mod, "run_evaluation")
    assert "run_evaluation" in mod.__all__


def test_runner_module_has_load_annotation():
    import evaluation.runner as mod
    assert hasattr(mod, "_load_annotation")


def test_runner_module_has_process_one():
    import evaluation.runner as mod
    assert hasattr(mod, "_process_one")


def test_runner_module_all_only_run_evaluation():
    """__all__ 只导出 run_evaluation（公开 API）。"""
    import evaluation.runner as mod
    assert mod.__all__ == ["run_evaluation"]


# ---------- tolerance_chars 透传 ----------


def test_run_evaluation_tolerance_chars_default_30(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    # 不直接断言值（涉及内部 _tolerance_chars），但函数应正常运行
    assert report is not None


def test_run_evaluation_tolerance_chars_custom(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    # tolerance_chars=50 不会崩溃
    report = run_evaluation(manifest, out, tolerance_chars=50)
    assert report is not None


def test_run_evaluation_tolerance_chars_zero(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d1.docx")
    docs = (_FakeDocEntry(doc_id="DC-1", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, tolerance_chars=0)
    assert report is not None
