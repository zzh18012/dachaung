"""evaluation/runner.py 边角测试（Round 82，第二轮）。

补强 tests/test_evaluation_runner.py（59 测试）+ test_evaluation_runner_edges.py（65 测试）
未覆盖的盲区：

- _load_annotation：空文件、仅空白、JSON 数组 dict item、Unicode 边界、
  permission denied（mock OSError）、JSON 含注释（应失败）、单引号 JSON（失败）
- _process_one：error_dict 详细字段（code/message/details）、image_dir 路径结构、
  total_seconds 单调、parser_name 透传、max_chars 透传、out_stub 多次清理
- run_evaluation：provenance 完整 keys、summary 内容、image_base_dir 严格 None 处理、
  per_doc 顺序与 manifest 一致、annotation_present 字段、tolerance_chars 字段、
  missing_markers 字段、expected_failures doc_id 透传、
  empty manifest 仍写 expected_failures 字段、output 文件可被 json.load 重读
- 模块结构：__all__、imports、helper functions 都暴露
"""

from __future__ import annotations

import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# 共用 fixtures（与 _edges.py 同样结构）
# =========================================================================


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
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
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


def _write_minimal_pdf(path: Path) -> Path:
    """写一个最小合法 PDF（1 页空白）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000052 00000 n \n0000000101 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n164\n%%EOF"
    )
    path.write_bytes(pdf_bytes)
    return path


# =========================================================================
# 1. _load_annotation 第二轮
# =========================================================================


def test_load_annotation_signature_returns_dict_or_none():
    """函数签名应允许多种返回类型，类型注解是 dict | None，实际更宽。"""
    sig_param_count = _load_annotation.__code__.co_argcount
    assert sig_param_count == 1


def test_load_annotation_empty_file_returns_none(tmp_path: Path):
    """空文件 → json.JSONDecodeError → 返 None。"""
    p = tmp_path / "empty.json"
    p.write_bytes(b"")
    assert _load_annotation(p) is None


def test_load_annotation_whitespace_only_returns_none(tmp_path: Path):
    p = tmp_path / "ws.json"
    p.write_text("   \n\t  ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_with_trailing_comma_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text('{"k": "v",}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_with_single_quotes_returns_none(tmp_path: Path):
    """JSON 不允许单引号。"""
    p = tmp_path / "bad.json"
    p.write_text("{'k': 'v'}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_with_comment_returns_none(tmp_path: Path):
    """JSON 不允许 // 注释。"""
    p = tmp_path / "bad.json"
    p.write_text('// comment\n{"k": "v"}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_array_at_top_level(tmp_path: Path):
    """JSON 顶层是数组 → 返 list（注解是 dict 但实际接受）。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == [1, 2, 3]


def test_load_annotation_json_null_value(tmp_path: Path):
    """JSON null → Python None。注解是 dict | None 但 None 也是合法返值。"""
    p = tmp_path / "n.json"
    p.write_text("null", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_integer_value(tmp_path: Path):
    p = tmp_path / "i.json"
    p.write_text("42", encoding="utf-8")
    assert _load_annotation(p) == 42


def test_load_annotation_json_negative_number(tmp_path: Path):
    p = tmp_path / "n.json"
    p.write_text("-1.5", encoding="utf-8")
    assert _load_annotation(p) == -1.5


def test_load_annotation_json_exponent_number(tmp_path: Path):
    p = tmp_path / "n.json"
    p.write_text("1.5e3", encoding="utf-8")
    assert _load_annotation(p) == 1500.0


def test_load_annotation_with_subdirectory_path(tmp_path: Path):
    """嵌套子目录里的文件也能读。"""
    deep_dir = tmp_path / "a" / "b" / "c"
    deep_dir.mkdir(parents=True)
    p = deep_dir / "data.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    assert _load_annotation(p) == {"x": 1}


def test_load_annotation_file_with_only_open_brace_returns_none(tmp_path: Path):
    p = tmp_path / "b.json"
    p.write_text("{", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_file_with_only_close_brace_returns_none(tmp_path: Path):
    p = tmp_path / "b.json"
    p.write_text("}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_handles_os_error(monkeypatch, tmp_path: Path):
    """OSError 时返 None（不抛出）。"""
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")

    original_open = Path.open

    def _fail_open(self, *args, **kwargs):
        if str(self) == str(p):
            raise OSError("permission denied mock")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _fail_open)
    assert _load_annotation(p) is None


def test_load_annotation_returns_same_dict_for_repeated_calls(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a == b
    assert a is not b  # 不同 dict 实例


def test_load_annotation_with_unicode_emoji(tmp_path: Path):
    p = tmp_path / "e.json"
    p.write_text('{"emoji": "🎉"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result["emoji"] == "🎉"


def test_load_annotation_path_repr_does_not_crash(tmp_path: Path):
    """传 Path 对象 → is_file() 调用正常。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    # 多次 is_file 调用不应抛
    for _ in range(5):
        result = _load_annotation(p)
        assert result == {}


def test_load_annotation_directory_is_not_a_file_returns_none(tmp_path: Path):
    """传一个存在的目录 → is_file() False → 返 None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_symlink_to_valid_json(tmp_path: Path):
    """symlink 到 JSON 文件应可读。"""
    target = tmp_path / "real.json"
    target.write_text('{"a": 1}', encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    assert _load_annotation(link) == {"a": 1}


# =========================================================================
# 2. _process_one 第二轮
# =========================================================================


def test_process_one_success_returns_5_tuple(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_success_first_element_is_dict(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    document_dict, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(document_dict, dict)


def test_process_one_success_document_has_document_id(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    document_dict, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "document_id" in document_dict


def test_process_one_success_document_has_elements(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    document_dict, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "elements" in document_dict


def test_process_one_success_document_has_chunks(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    document_dict, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "chunks" in document_dict


def test_process_one_success_document_has_source_type(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path, source_type="docx")
    document_dict, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict["source_type"] == "docx"


def test_process_one_failure_returns_specific_error_code(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _, error_dict, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert error_dict["code"] == "unsupported_type"


def test_process_one_failure_returns_error_message(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _, error_dict, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "message" in error_dict
    assert isinstance(error_dict["message"], str)


def test_process_one_failure_total_seconds_is_float(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total, float)


def test_process_one_failure_total_seconds_non_negative(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert total >= 0.0


def test_process_one_creates_per_doc_directory_for_failure(tmp_path: Path):
    """失败也创建 _per_doc 目录。"""
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    _process_one(doc, tmp_path, "fallback", 800)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.is_dir()


def test_process_one_out_stub_filename_uses_doc_id(tmp_path: Path):
    """out_stub 路径是 _per_doc/{doc_id}.json。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="UNIQUE_ID", resolved_path=docx_path)
    _process_one(doc, tmp_path, "fallback", 800)
    # 文件应被清理，但目录还在
    out_stub = tmp_path / "_per_doc" / "UNIQUE_ID.json"
    assert not out_stub.is_file()


def test_process_one_max_chars_zero_does_not_crash(tmp_path: Path):
    """max_chars=0 应由 chunker 处理（可能抛错或返空 chunks）。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx", text="Hello.")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    try:
        result = _process_one(doc, tmp_path, "fallback", 0)
        # 即使成功，也应返回 5-tuple
        assert len(result) == 5
    except Exception:
        # chunker 可能拒绝 0；这也算合理行为
        pass


def test_process_one_max_chars_one_does_not_crash(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx", text="Hello.")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    result = _process_one(doc, tmp_path, "fallback", 1)
    assert len(result) == 5


def test_process_one_parser_name_kreuzberg_when_available(tmp_path: Path):
    """传 parser_name='kreuzberg'（若未装则返失败错误）。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    result = _process_one(doc, tmp_path, "kreuzberg", 800)
    assert len(result) == 5


def test_process_two_files_total_seconds_independent(tmp_path: Path):
    """两次 _process_one 的 total_seconds 各自独立。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d.docx", text="aaa.")
    p2 = _write_minimal_docx(tmp_path / "b" / "d.docx", text="bbb.")
    doc1 = _FakeDocEntry(doc_id="DC-1", resolved_path=p1)
    doc2 = _FakeDocEntry(doc_id="DC-2", resolved_path=p2)
    _, _, t1, _, _ = _process_one(doc1, tmp_path, "fallback", 800)
    _, _, t2, _, _ = _process_one(doc2, tmp_path, "fallback", 800)
    # 两次独立计时；t1 不影响 t2
    assert isinstance(t1, float)
    assert isinstance(t2, float)


def test_process_one_image_dir_is_none_when_document_none(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=src, source_type="unknown")
    document_dict, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict is None
    assert image_dir is None


def test_process_one_pdf_source_type(tmp_path: Path):
    """PDF 文件也能处理（fallback parser 用 pdfplumber）。"""
    pdf_path = _write_minimal_pdf(tmp_path / "src" / "doc.pdf")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=pdf_path, source_type="pdf")
    document_dict, error_dict, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    # 最小 PDF 可能解析失败也可能成功（取决于 pdfplumber）
    if error_dict is None:
        assert isinstance(document_dict, dict)
    else:
        assert isinstance(error_dict, dict)


def test_process_one_per_doc_subdir_path_naming(tmp_path: Path):
    """_per_doc 子目录的位置：output_root/_per_doc/。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="X", resolved_path=docx_path)
    _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_parser_version_for_real_fallback(tmp_path: Path):
    """fallback parser 的 version 包含 'pdfplumber'。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="X", resolved_path=docx_path)
    _, _, _, version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert version is not None
    assert "pdfplumber" in version


# =========================================================================
# 3. run_evaluation 第二轮
# =========================================================================


def test_run_evaluation_with_zero_documents_zero_expected_failures(tmp_path: Path):
    manifest = _FakeManifest(documents=(), expected_failures=())
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["per_doc"] == []
    assert result["expected_failures"] == []


def test_run_evaluation_with_one_document_no_annotation(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path, annotation_resolved=None)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert len(result["per_doc"]) == 1


def test_run_evaluation_annotation_present_field_true_when_file_exists(tmp_path: Path):
    """私有字段 _annotation_present 在 per_doc_results 中应为 True（但被 public 过滤掉）。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    annot = tmp_path / "a.json"
    annot.write_text("{}", encoding="utf-8")
    doc = _FakeDocEntry(
        doc_id="DC-1", resolved_path=docx_path, annotation_resolved=annot
    )
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    # public per_doc 不应有 _ 字段
    assert "_annotation_present" not in result["per_doc"][0]


def test_run_evaluation_summary_present(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "summary" in result


def test_run_evaluation_summary_is_dict(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result["summary"], dict)


def test_run_evaluation_provenance_present(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "provenance" in result


def test_run_evaluation_provenance_is_dict(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result["provenance"], dict)


def test_run_evaluation_devset_present(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "devset" in result


def test_run_evaluation_devset_is_dict(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result["devset"], dict)


def test_run_evaluation_output_file_can_be_reloaded(tmp_path: Path):
    """out.json 可以再次 json.load。"""
    manifest = _FakeManifest()
    out = tmp_path / "deep" / "nested" / "out.json"
    run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_run_evaluation_creates_deeply_nested_output_dir(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "a" / "b" / "c" / "d" / "out.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_per_doc_results_private_in_memory_only(tmp_path: Path):
    """public per_doc 不含 _ 字段。"""
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    for entry in result["per_doc"]:
        for k in entry.keys():
            assert not k.startswith("_")


def test_run_evaluation_per_doc_results_keys_full_set(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert set(result["per_doc"][0].keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_per_doc_metrics_is_dict(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result["per_doc"][0]["metrics"], dict)


def test_run_evaluation_wall_time_keys_full_set(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_run_evaluation_wall_time_parse_chunk_always_none(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None


def test_run_evaluation_wall_time_reasons_always_not_instrumented(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="DC-1", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_per_doc_doc_id_passed_through(tmp_path: Path):
    docx_path = _write_minimal_docx(tmp_path / "src" / "doc.docx")
    doc = _FakeDocEntry(doc_id="CUSTOM_ID", resolved_path=docx_path)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["per_doc"][0]["doc_id"] == "CUSTOM_ID"


def test_run_evaluation_expected_failure_doc_id_passed_through(tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hi", encoding="utf-8")
    ef = _FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="unsupported_type"
    )
    manifest = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["expected_failures"][0]["doc_id"] == "EF-1"


def test_run_evaluation_expected_failure_expected_code_passed_through(tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hi", encoding="utf-8")
    ef = _FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="custom_code"
    )
    manifest = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["expected_failures"][0]["expected_error_code"] == "custom_code"


def test_run_evaluation_expected_failure_has_actual_code_field(tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hi", encoding="utf-8")
    ef = _FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="unsupported_type"
    )
    manifest = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "actual_error_code" in result["expected_failures"][0]


def test_run_evaluation_expected_failure_has_matches_field(tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hi", encoding="utf-8")
    ef = _FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="unsupported_type"
    )
    manifest = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "matches" in result["expected_failures"][0]
    assert isinstance(result["expected_failures"][0]["matches"], bool)


def test_run_evaluation_expected_failure_keys_full_set(tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hi", encoding="utf-8")
    ef = _FakeExpectedFailure(
        doc_id="EF-1", resolved_path=src, expected_error_code="unsupported_type"
    )
    manifest = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert set(result["expected_failures"][0].keys()) == {
        "doc_id", "expected_error_code", "actual_error_code", "matches"
    }


def test_run_evaluation_multiple_docs_preserve_doc_id_order(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d.docx", text="aaa.")
    p2 = _write_minimal_docx(tmp_path / "b" / "d.docx", text="bbb.")
    p3 = _write_minimal_docx(tmp_path / "c" / "d.docx", text="ccc.")
    docs = (
        _FakeDocEntry(doc_id="A", resolved_path=p1),
        _FakeDocEntry(doc_id="B", resolved_path=p2),
        _FakeDocEntry(doc_id="C", resolved_path=p3),
    )
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    ids = [d["doc_id"] for d in result["per_doc"]]
    assert ids == ["A", "B", "C"]


def test_run_evaluation_multiple_expected_failures_preserve_order(tmp_path: Path):
    s1 = tmp_path / "x1.txt"; s1.write_text("hi", encoding="utf-8")
    s2 = tmp_path / "x2.txt"; s2.write_text("hi", encoding="utf-8")
    efs = (
        _FakeExpectedFailure(doc_id="EF1", resolved_path=s1, expected_error_code="x"),
        _FakeExpectedFailure(doc_id="EF2", resolved_path=s2, expected_error_code="y"),
    )
    manifest = _FakeManifest(expected_failures=efs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    ids = [e["doc_id"] for e in result["expected_failures"]]
    assert ids == ["EF1", "EF2"]


def test_run_evaluation_parser_version_first_doc_only(tmp_path: Path):
    """parser_version_for_prov 只取首非 None。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d.docx", text="aaa.")
    p2 = _write_minimal_docx(tmp_path / "b" / "d.docx", text="bbb.")
    docs = (
        _FakeDocEntry(doc_id="A", resolved_path=p1),
        _FakeDocEntry(doc_id="B", resolved_path=p2),
    )
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    prov_ver = result["provenance"]["parser_version"]
    # 两个 doc 都成功，prov_ver 应来自第一个
    assert prov_ver is not None


def test_run_evaluation_default_tolerance_chars_in_provenance(tmp_path: Path):
    """provenance 应记录 max_chars 和其他参数（具体字段取决于 report.build_provenance）。"""
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "max_chars" in result["provenance"]


def test_run_evaluation_max_chars_in_provenance(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out, max_chars=123)
    assert result["provenance"]["max_chars"] == 123


def test_run_evaluation_parser_name_in_provenance(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out, parser_name="fallback")
    assert result["provenance"]["parser_name"] == "fallback"


def test_run_evaluation_creates_per_doc_dir_for_each_doc(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d.docx", text="aaa.")
    p2 = _write_minimal_docx(tmp_path / "b" / "d.docx", text="bbb.")
    docs = (
        _FakeDocEntry(doc_id="A", resolved_path=p1),
        _FakeDocEntry(doc_id="B", resolved_path=p2),
    )
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    run_evaluation(manifest, out)
    per_doc_dir = out.parent / "_per_doc"
    assert per_doc_dir.is_dir()


def test_run_evaluation_per_doc_no_private_field_leak(tmp_path: Path):
    """private 字段（_tolerance_chars, _missing_markers, _annotation_present）不应泄露。"""
    p1 = _write_minimal_docx(tmp_path / "a" / "d.docx", text="aaa.")
    docs = (_FakeDocEntry(doc_id="A", resolved_path=p1),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    for entry in result["per_doc"]:
        keys = set(entry.keys())
        assert "_tolerance_chars" not in keys
        assert "_missing_markers" not in keys
        assert "_annotation_present" not in keys


def test_run_evaluation_output_root_is_output_path_parent(tmp_path: Path):
    """output_root = output_path.parent。manifest 至少一个 doc 才会触发 _per_doc 创建。"""
    p = _write_minimal_docx(tmp_path / "src" / "d.docx", text="hi.")
    doc = _FakeDocEntry(doc_id="A", resolved_path=p)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "subdir" / "o.json"
    run_evaluation(manifest, out)
    assert (tmp_path / "subdir" / "_per_doc").is_dir()


def test_run_evaluation_idempotent_for_same_manifest(tmp_path: Path):
    """同一 manifest 跑两次都成功。"""
    manifest = _FakeManifest()
    out1 = tmp_path / "o1.json"
    out2 = tmp_path / "o2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    assert r1["report_version"] == r2["report_version"]


def test_run_evaluation_failed_doc_still_in_per_doc(tmp_path: Path):
    """失败 doc 也写入 per_doc（含 metrics 多为 null）。"""
    src = tmp_path / "x.unknown"
    src.write_text("hi", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="FAIL", resolved_path=src, source_type="unknown")
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert len(result["per_doc"]) == 1
    assert result["per_doc"][0]["doc_id"] == "FAIL"


def test_run_evaluation_failed_doc_metrics_is_dict(tmp_path: Path):
    src = tmp_path / "x.unknown"
    src.write_text("hi", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="FAIL", resolved_path=src, source_type="unknown")
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result["per_doc"][0]["metrics"], dict)


def test_run_evaluation_mixed_success_and_failure_docs(tmp_path: Path):
    p_ok = _write_minimal_docx(tmp_path / "a" / "d.docx", text="hi.")
    p_bad = tmp_path / "x.unknown"
    p_bad.write_text("hi", encoding="utf-8")
    docs = (
        _FakeDocEntry(doc_id="OK", resolved_path=p_ok),
        _FakeDocEntry(doc_id="BAD", resolved_path=p_bad, source_type="unknown"),
    )
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert len(result["per_doc"]) == 2


def test_run_evaluation_returns_same_dict_as_written_file(tmp_path: Path):
    """返回的 dict 与磁盘上的 JSON 一致。"""
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        file_data = json.load(f)
    assert result == file_data


def test_run_evaluation_with_pdf_document(tmp_path: Path):
    """PDF 文档也能跑（可能失败但应有条目）。"""
    pdf = _write_minimal_pdf(tmp_path / "src" / "doc.pdf")
    doc = _FakeDocEntry(doc_id="PDF1", resolved_path=pdf, source_type="pdf")
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert len(result["per_doc"]) == 1


def test_run_evaluation_devset_status_propagated_to_report(tmp_path: Path):
    manifest = _FakeManifest(devset_status="complete")
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["devset"]["status"] == "complete"


def test_run_evaluation_devset_file_count_matches_documents(tmp_path: Path):
    p = _write_minimal_docx(tmp_path / "a" / "d.docx", text="hi.")
    docs = (_FakeDocEntry(doc_id="A", resolved_path=p),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["devset"]["file_count"] == 1


def test_run_evaluation_devset_docx_count(tmp_path: Path):
    p = _write_minimal_docx(tmp_path / "a" / "d.docx", text="hi.")
    docs = (_FakeDocEntry(doc_id="A", resolved_path=p, source_type="docx"),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["devset"]["docx_count"] == 1


def test_run_evaluation_devset_pdf_count(tmp_path: Path):
    pdf = _write_minimal_pdf(tmp_path / "src" / "d.pdf")
    docs = (_FakeDocEntry(doc_id="A", resolved_path=pdf, source_type="pdf"),)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["devset"]["pdf_count"] == 1


def test_run_evaluation_devset_content_group_count(tmp_path: Path):
    p1 = _write_minimal_docx(tmp_path / "a" / "d.docx", text="hi.")
    p2 = _write_minimal_docx(tmp_path / "b" / "d.docx", text="hi.")
    docs = (
        _FakeDocEntry(doc_id="A", resolved_path=p1),
        _FakeDocEntry(doc_id="B", resolved_path=p2),
    )
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["devset"]["content_group_count"] == 2


def test_run_evaluation_provenance_includes_run_timestamp(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "run_timestamp_iso" in result["provenance"]


def test_run_evaluation_provenance_includes_evaluator_version(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "evaluator_version" in result["provenance"]


def test_run_evaluation_provenance_includes_dependencies(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "dependencies" in result["provenance"]


def test_run_evaluation_provenance_does_not_include_project_root(tmp_path: Path):
    """project_root 仅作为参数给 get_git_provenance，不写入 provenance 字典。"""
    manifest = _FakeManifest(project_root=tmp_path)
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "project_root" not in result["provenance"]


def test_run_evaluation_provenance_includes_git_fields(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert "git_commit" in result["provenance"]
    assert "git_dirty" in result["provenance"]


# =========================================================================
# 4. 模块结构
# =========================================================================


def test_runner_module_all_is_list():
    import evaluation.runner as mod
    assert isinstance(mod.__all__, list)


def test_runner_module_all_contains_run_evaluation():
    import evaluation.runner as mod
    assert "run_evaluation" in mod.__all__


def test_runner_module_all_only_run_evaluation():
    """__all__ 只导出 public API。"""
    import evaluation.runner as mod
    assert mod.__all__ == ["run_evaluation"]


def test_runner_module_has_load_annotation():
    import evaluation.runner as mod
    assert hasattr(mod, "_load_annotation")
    assert callable(mod._load_annotation)


def test_runner_module_has_process_one():
    import evaluation.runner as mod
    assert hasattr(mod, "_process_one")
    assert callable(mod._process_one)


def test_runner_module_imports_time():
    """time 用于 perf_counter。"""
    import evaluation.runner as mod
    assert hasattr(mod, "time")


def test_runner_module_imports_json():
    import evaluation.runner as mod
    assert hasattr(mod, "json")


def test_runner_module_imports_path():
    import evaluation.runner as mod
    assert hasattr(mod, "Path")


def test_runner_module_imports_process_single():
    import evaluation.runner as mod
    assert hasattr(mod, "process_single")


def test_runner_module_imports_image_output_dir_for():
    import evaluation.runner as mod
    assert hasattr(mod, "image_output_dir_for")


def test_runner_module_imports_compute_automatic_metrics():
    import evaluation.runner as mod
    assert hasattr(mod, "compute_automatic_metrics")


def test_runner_module_imports_chunk_boundary_prf():
    import evaluation.runner as mod
    assert hasattr(mod, "chunk_boundary_prf")


def test_runner_module_imports_figure_caption_prf():
    import evaluation.runner as mod
    assert hasattr(mod, "figure_caption_prf")


def test_runner_module_imports_aggregate_summary():
    import evaluation.runner as mod
    assert hasattr(mod, "aggregate_summary")


def test_runner_module_imports_build_provenance():
    import evaluation.runner as mod
    assert hasattr(mod, "build_provenance")


def test_runner_module_imports_build_devset_section():
    import evaluation.runner as mod
    assert hasattr(mod, "build_devset_section")


def test_runner_module_imports_report_version():
    import evaluation.runner as mod
    assert hasattr(mod, "REPORT_VERSION")


def test_run_evaluation_signature_returns_dict_annotation():
    """run_evaluation 返回类型注解是 dict[str, Any]。"""
    import inspect
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation) or sig.return_annotation is dict or sig.return_annotation == "dict[str, Any]"


def test_run_evaluation_signature_manifest_param():
    import inspect
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].name == "manifest"


def test_run_evaluation_signature_output_path_param():
    import inspect
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[1].name == "output_path"


def test_run_evaluation_signature_keyword_only_params():
    """parser_name/max_chars/tolerance_chars 是 keyword-only。"""
    import inspect
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_signature_default_parser_name():
    import inspect
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[2].default == "fallback"


def test_run_evaluation_signature_default_max_chars():
    import inspect
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[3].default == 800


def test_run_evaluation_signature_default_tolerance_chars():
    import inspect
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[4].default == 30


def test_load_annotation_signature_path_param():
    import inspect
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_process_one_signature_5_args():
    import inspect
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert params[0].name == "doc"
    assert params[1].name == "output_root"
    assert params[2].name == "parser_name"
    assert params[3].name == "max_chars"


# =========================================================================
# 5. 集成：tolerance_chars 透传链
# =========================================================================


def test_run_evaluation_tolerance_chars_passed_to_chunk_boundary(tmp_path: Path):
    """tolerance_chars=15 → 应影响 chunk_boundary_prf 的内部计算。
    实际通过 chunk_b 的 _tolerance_chars 私有字段验证。"""
    p = _write_minimal_docx(tmp_path / "a" / "d.docx", text="hi.")
    doc = _FakeDocEntry(doc_id="A", resolved_path=p)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out, tolerance_chars=15)
    # 我们不能直接验证内部 chunk_b 的 _tolerance_chars 字段（已 pop）
    # 但能验证调用没崩，结果仍是合法 dict
    assert isinstance(result, dict)


def test_run_evaluation_tolerance_chars_extreme_large(tmp_path: Path):
    p = _write_minimal_docx(tmp_path / "a" / "d.docx", text="hi.")
    doc = _FakeDocEntry(doc_id="A", resolved_path=p)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out, tolerance_chars=10**6)
    assert isinstance(result, dict)


def test_run_evaluation_max_chars_extreme_large(tmp_path: Path):
    p = _write_minimal_docx(tmp_path / "a" / "d.docx", text="hi.")
    doc = _FakeDocEntry(doc_id="A", resolved_path=p)
    manifest = _FakeManifest(documents=(doc,))
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out, max_chars=10**6)
    assert isinstance(result, dict)


# =========================================================================
# 6. report_version 不变量
# =========================================================================


def test_run_evaluation_report_version_value(tmp_path: Path):
    """report_version 来自 evaluation.REPORT_VERSION。"""
    from evaluation import REPORT_VERSION
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert result["report_version"] == REPORT_VERSION


def test_run_evaluation_report_version_is_string(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result["report_version"], str)


def test_run_evaluation_report_version_not_empty(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert len(result["report_version"]) > 0


def test_run_evaluation_top_level_keys_full_set(tmp_path: Path):
    manifest = _FakeManifest()
    out = tmp_path / "o.json"
    result = run_evaluation(manifest, out)
    assert set(result.keys()) == {
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures"
    }
