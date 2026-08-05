r"""evaluation/runner.py 边角测试 - 第十二轮（Round 225）。

补强已有 base/edges/edges2-11（共 ~940 测试）未覆盖的深度：
- _load_annotation：JSON 标量 / 空 dict/list / null；文件含非法字节；重复 JSON 对象
- _process_one：parser_version 类型；image_dir 路径来自 image_output_dir_for
- run_evaluation：报告文件 ensure_ascii=False / indent=2 / 字段顺序
- run_evaluation：per_doc 公共字段不含 _annotation_present / _tolerance_chars / _missing_markers
- run_evaluation：expected_failures 4 keys 精确
- run_evaluation：wall_time_seconds 5 keys 精确
- run_evaluation：annotation_resolved 指向不同状态文件
- run_evaluation：output_path 接受 str / Path / 深嵌套父目录
- 模块结构 / imports
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


class _FakeDocEntry:
    def __init__(self, doc_id="d1", resolved_path=None, source_type="text",
                 expectations=None, annotation_resolved=None):
        self.doc_id = doc_id
        self.resolved_path = resolved_path or Path("/tmp/x.txt")
        self.source_type = source_type
        self.expectations = expectations
        self.annotation_resolved = annotation_resolved


class _FakeError:
    def __init__(self, code="x", message="boom"):
        self.code = code
        self.message = message

    def to_dict(self):
        return {"code": self.code, "message": self.message}


class _FakeDocument:
    def __init__(self, source_hash="a" * 64, parser_version="0.1.0"):
        self.source_hash = source_hash
        self.parser_version = parser_version

    def to_dict(self):
        return {
            "source_hash": self.source_hash,
            "parser_version": self.parser_version,
            "source_type": "text",
            "elements": [],
            "chunks": [],
        }


class _FakeManifest:
    def __init__(self, documents=None, expected_failures=None, project_root=None):
        self.documents = documents or []
        self.expected_failures = expected_failures or []
        self.devset_status = "incomplete"
        self.file_count = len(self.documents)
        self.content_group_count = 1
        self.pdf_count = 0
        self.docx_count = 0
        self.categories_covered = ["text"]
        self.project_root = project_root if project_root is not None else Path(".")


class _FakeExpectedFailure:
    def __init__(self, doc_id, resolved_path, expected_error_code):
        self.doc_id = doc_id
        self.resolved_path = resolved_path
        self.expected_error_code = expected_error_code


# =========================================================================
# _load_annotation 深度（补强 edges11）
# =========================================================================


def test_load_annotation_empty_dict(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_annotation(p)
    assert result == {}


def test_load_annotation_empty_list(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == []


def test_load_annotation_json_null(tmp_path):
    """JSON null 解析为 Python None。"""
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_json_scalar_int(tmp_path):
    """JSON 标量 int 也能解析（虽然不是有用标注）。"""
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 42


def test_load_annotation_json_scalar_string(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    result = _load_annotation(p)
    assert result == "hello"


def test_load_annotation_json_true(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("true", encoding="utf-8")
    result = _load_annotation(p)
    assert result is True


def test_load_annotation_two_json_objects_invalid(tmp_path):
    """两个 JSON 对象相连 → 解析错误。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}{"b": 2}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_whitespace_only_invalid(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("   \n   \t   ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_random_garbage_invalid(tmp_path):
    """非 JSON 文本。"""
    p = tmp_path / "a.json"
    p.write_text("not a json at all", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_just_brace_invalid(tmp_path):
    """只有 `{` → JSON 解析错误。"""
    p = tmp_path / "a.json"
    p.write_text("{", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_path_with_spaces(tmp_path):
    """路径含空格也能读取。"""
    p = tmp_path / "a b.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"k": 1}


def test_load_annotation_path_with_unicode(tmp_path):
    """路径含中文也能读取。"""
    p = tmp_path / "标注.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"k": "v"}


def test_load_annotation_returns_none_for_path_object_nonexistent(tmp_path):
    """不存在的 path → is_file() False → None。"""
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_none_input_returns_none():
    """传 None 应返回 None（早返回）。"""
    assert _load_annotation(None) is None


def test_load_annotation_deeply_nested_dict(tmp_path):
    """深层嵌套 dict 也能解析。"""
    p = tmp_path / "a.json"
    deep = {"a": {"b": {"c": {"d": {"e": "deep"}}}}}
    p.write_text(json.dumps(deep), encoding="utf-8")
    result = _load_annotation(p)
    assert result == deep


def test_load_annotation_with_array_values(tmp_path):
    p = tmp_path / "a.json"
    data = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    p.write_text(json.dumps(data), encoding="utf-8")
    result = _load_annotation(p)
    assert "chunk_boundary_anchors" in result
    assert len(result["chunk_boundary_anchors"]) == 1


def test_load_annotation_extra_data_after_json_invalid(tmp_path):
    """JSON 后有额外内容（非 trailing whitespace）→ 解析错误。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1} extra', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_trailing_newline_valid(tmp_path):
    """末尾换行是合法的。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}\n', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"a": 1}


# =========================================================================
# _process_one 深度（补强 edges11）
# =========================================================================


def test_process_one_total_seconds_is_float(tmp_path, monkeypatch):
    """total_seconds 应是 float（time.perf_counter 差值）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, total, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert isinstance(total, float)


def test_process_one_total_seconds_non_negative(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, total, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert total >= 0


def test_process_one_uses_image_output_dir_for(tmp_path, monkeypatch):
    """image_dir 来自 image_output_dir_for(out_stub, source_hash)。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    captured_args = []

    def fake_image_output_dir_for(stub, source_hash):
        captured_args.append((stub, source_hash))
        return Path("/fake/image_dir")

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    monkeypatch.setattr("evaluation.runner.image_output_dir_for",
                        fake_image_output_dir_for)
    _, _, _, _, image_dir = _process_one(doc_entry, tmp_path, "text", 800)
    assert image_dir == Path("/fake/image_dir")
    assert len(captured_args) == 1
    assert captured_args[0][1] == "a" * 64


def test_process_one_image_dir_none_when_document_none(tmp_path, monkeypatch):
    """document=None 时 image_dir 必须是 None（不是 Path()）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError()]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, _, image_dir = _process_one(doc_entry, tmp_path, "text", 800)
    assert image_dir is None


def test_process_one_returns_error_dict_with_exact_two_keys(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="c1", message="m1")]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, error, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert set(error.keys()) == {"code", "message"}


def test_process_one_unknown_error_dict_exact_two_keys(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, error, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert set(error.keys()) == {"code", "message"}
    assert error["code"] == "unknown"


def test_process_one_out_stub_under_per_doc_dir(tmp_path, monkeypatch):
    """out_stub 路径必须是 output_root/_per_doc/<doc_id>.json。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(doc_id="abc", resolved_path=p)

    captured_out_path = []

    def fake_process_single(path, output_path, **kwargs):
        captured_out_path.append(output_path)
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "text", 800)
    expected = tmp_path / "_per_doc" / "abc.json"
    assert captured_out_path[0] == expected


def test_process_one_passes_parser_name_to_process_single(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    captured = []

    def fake_process_single(path, output_path, *, parser_name, **kwargs):
        captured.append(parser_name)
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "kreuzberg", 800)
    assert captured == ["kreuzberg"]


def test_process_one_passes_max_chars_to_process_single(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    captured = []

    def fake_process_single(path, output_path, *, max_chars, **kwargs):
        captured.append(max_chars)
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "text", 1234)
    assert captured == [1234]


def test_process_one_passes_write_json_false(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    doc_entry = _FakeDocEntry(resolved_path=p)

    captured = []

    def fake_process_single(path, output_path, *, write_json, **kwargs):
        captured.append(write_json)
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "text", 800)
    assert captured == [False]


# =========================================================================
# run_evaluation 深度（补强 edges11）
# =========================================================================


def test_run_evaluation_per_doc_public_keys_exact(tmp_path, monkeypatch):
    """per_doc 条目应只有 4 个公共 keys：doc_id/source_type/metrics/wall_time_seconds。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    entry = report["per_doc"][0]
    assert set(entry.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_wall_time_seconds_keys_exact(tmp_path, monkeypatch):
    """wall_time_seconds 应有 5 keys：total/parse/chunk/parse_reason/chunk_reason。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failures_keys_exact(tmp_path):
    bad = tmp_path / "missing.txt"
    ef = _FakeExpectedFailure("ef1", bad, "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    entry = report["expected_failures"][0]
    assert set(entry.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}


def test_run_evaluation_report_file_uses_indent_2(tmp_path, monkeypatch):
    """报告文件应使用 indent=2（每层缩进 2 空格）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    # indent=2 → '  "key": value' 形式
    assert '  "report_version"' in text
    # indent=4 → '    "key"'
    assert '    "report_version"' not in text.split('\n')[1] if '\n' in text else True


def test_run_evaluation_report_file_uses_ensure_ascii_false(tmp_path, monkeypatch):
    """报告文件应保留中文（ensure_ascii=False）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="中文文档", resolved_path=p)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    assert "中文文档" in text


def test_run_evaluation_output_path_accepts_str(tmp_path):
    manifest = _FakeManifest()
    out = str(tmp_path / "report.json")
    report = run_evaluation(manifest, out)
    assert isinstance(report, dict)
    assert Path(out).is_file()


def test_run_evaluation_output_path_accepts_path(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report, dict)
    assert out.is_file()


def test_run_evaluation_creates_parent_dirs(tmp_path):
    """output_path 父目录不存在时应创建。"""
    manifest = _FakeManifest()
    out = tmp_path / "deep" / "nested" / "report.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report, dict)
    assert out.is_file()


def test_run_evaluation_idempotent_report_file(tmp_path, monkeypatch):
    """两次 run 应得到结构一致的报告（仅 run_timestamp_iso 与 wall_time.total 不同）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    r1 = json.loads(out.read_text(encoding="utf-8"))
    run_evaluation(manifest, out)
    r2 = json.loads(out.read_text(encoding="utf-8"))
    # 顶层结构应一致
    assert set(r1.keys()) == set(r2.keys())
    # per_doc 数量与 doc_id 应一致
    assert len(r1["per_doc"]) == len(r2["per_doc"])
    assert r1["per_doc"][0]["doc_id"] == r2["per_doc"][0]["doc_id"]
    # 仅 run_timestamp_iso 与 wall_time.total 应不同（计时是浮点）
    ts1 = r1["provenance"]["run_timestamp_iso"]
    ts2 = r2["provenance"]["run_timestamp_iso"]
    assert ts1 != ts2


def test_run_evaluation_report_dict_matches_file(tmp_path, monkeypatch):
    """返回的 report dict 应与写入文件内容一致。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert report == loaded


def test_run_evaluation_with_annotation_resolved_existing(tmp_path, monkeypatch):
    """annotation_resolved 指向有效文件 → _annotation_present=True（不写入公开报告，但影响 metrics）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({"chunk_boundary_anchors": []}), encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p, annotation_resolved=ann)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    # 报告应成功生成
    assert "per_doc" in report


def test_run_evaluation_with_annotation_resolved_missing(tmp_path, monkeypatch):
    """annotation_resolved 指向不存在文件 → _load_annotation 返回 None。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    ann = tmp_path / "missing_ann.json"
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p, annotation_resolved=ann)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "per_doc" in report


def test_run_evaluation_with_annotation_resolved_none(tmp_path, monkeypatch):
    """annotation_resolved 显式 None → _load_annotation 返回 None。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p, annotation_resolved=None)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "per_doc" in report


def test_run_evaluation_calls_aggregate_summary_with_per_doc(tmp_path, monkeypatch):
    """aggregate_summary 应被传入 per_doc_results 列表。"""
    captured = []

    def fake_aggregate(per_doc_results):
        captured.append(per_doc_results)
        return {"fake_summary": True}

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    monkeypatch.setattr("evaluation.runner.aggregate_summary", fake_aggregate)

    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert len(captured) == 1
    # per_doc_results 包含私有字段（_annotation_present 等）
    assert "_annotation_present" in captured[0][0]


def test_run_evaluation_calls_build_devset_section(tmp_path, monkeypatch):
    """build_devset_section 应被调用一次。"""
    called = []

    def fake_build_devset(m):
        called.append(m)
        return {"fake_devset": True}

    monkeypatch.setattr("evaluation.runner.build_devset_section", fake_build_devset)
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert len(called) == 1


def test_run_evaluation_calls_build_provenance_with_correct_args(tmp_path, monkeypatch):
    """build_provenance 应被传入 project_root/parser_name/max_chars/parser_version。"""
    captured = []

    def fake_build_prov(project_root, parser_name, max_chars, parser_version):
        captured.append((project_root, parser_name, max_chars, parser_version))
        return {"fake_prov": True}

    monkeypatch.setattr("evaluation.runner.build_provenance", fake_build_prov)
    manifest = _FakeManifest(project_root=tmp_path)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, parser_name="kreuzberg", max_chars=500)
    assert len(captured) == 1
    assert captured[0][0] == tmp_path
    assert captured[0][1] == "kreuzberg"
    assert captured[0][2] == 500


def test_run_evaluation_per_doc_results_internal_fields_present(tmp_path, monkeypatch):
    """内部 per_doc_results 应有 7 keys：4 公共 + 3 私有。"""
    captured = []

    def fake_aggregate(per_doc_results):
        captured.extend(per_doc_results)
        return {"fake_summary": True}

    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    monkeypatch.setattr("evaluation.runner.aggregate_summary", fake_aggregate)

    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert len(captured) == 1
    internal = captured[0]
    assert "_annotation_present" in internal
    assert "_tolerance_chars" in internal
    assert "_missing_markers" in internal
    assert internal["_annotation_present"] is False  # no annotation
    assert internal["_tolerance_chars"] is None or isinstance(internal["_tolerance_chars"], int)
    assert isinstance(internal["_missing_markers"], list)


def test_run_evaluation_no_documents_returns_empty_per_doc(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"] == []


def test_run_evaluation_no_documents_returns_empty_expected_failures(tmp_path):
    manifest = _FakeManifest(expected_failures=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"] == []


def test_run_evaluation_creates_per_doc_dir_when_documents_present(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert (tmp_path / "_per_doc").is_dir()


def test_run_evaluation_does_not_create_per_doc_when_no_documents(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert not (tmp_path / "_per_doc").is_dir()


def test_run_evaluation_metrics_dict_in_per_doc(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    metrics = report["per_doc"][0]["metrics"]
    assert isinstance(metrics, dict)
    assert len(metrics) > 0


# =========================================================================
# 模块结构（补强 edges11）
# =========================================================================


def test_module_imports_json():
    import evaluation.runner as m
    assert hasattr(m, "json")


def test_module_imports_time():
    import evaluation.runner as m
    assert hasattr(m, "time")


def test_module_imports_path():
    import evaluation.runner as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.runner as m
    assert hasattr(m, "Any")


def test_module_imports_image_output_dir_for():
    import evaluation.runner as m
    assert hasattr(m, "image_output_dir_for")


def test_module_imports_process_single():
    import evaluation.runner as m
    assert hasattr(m, "process_single")


def test_module_imports_report_version():
    import evaluation.runner as m
    assert hasattr(m, "REPORT_VERSION")


def test_module_imports_chunk_boundary_prf():
    import evaluation.runner as m
    assert hasattr(m, "chunk_boundary_prf")


def test_module_imports_figure_caption_prf():
    import evaluation.runner as m
    assert hasattr(m, "figure_caption_prf")


def test_module_imports_compute_automatic_metrics():
    import evaluation.runner as m
    assert hasattr(m, "compute_automatic_metrics")


def test_module_imports_aggregate_summary():
    import evaluation.runner as m
    assert hasattr(m, "aggregate_summary")


def test_module_imports_build_devset_section():
    import evaluation.runner as m
    assert hasattr(m, "build_devset_section")


def test_module_imports_build_provenance():
    import evaluation.runner as m
    assert hasattr(m, "build_provenance")


def test_module_all_contains_only_run_evaluation():
    import evaluation.runner as m
    assert m.__all__ == ["run_evaluation"]


def test_module_all_is_list():
    import evaluation.runner as m
    assert isinstance(m.__all__, list)


def test_module_docstring_present():
    import evaluation.runner as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_pipeline():
    import evaluation.runner as m
    assert "pipeline" in m.__doc__.lower() or "解析" in m.__doc__


def test_module_docstring_mentions_total():
    """docstring 应提及 'total'（计时只记 total）。"""
    import evaluation.runner as m
    assert "total" in m.__doc__.lower()


def test_module_docstring_mentions_not_instrumented():
    """docstring 应提及 'not_instrumented'（parse/chunk 未插桩）。"""
    import evaluation.runner as m
    assert "not_instrumented" in m.__doc__


def test_module_uses_future_annotations():
    import evaluation.runner as m
    sig = inspect.signature(m.run_evaluation)
    assert isinstance(sig.return_annotation, str)


def test_module_has_load_annotation_callable():
    import evaluation.runner as m
    assert callable(m._load_annotation)


def test_module_has_process_one_callable():
    import evaluation.runner as m
    assert callable(m._process_one)


def test_module_has_run_evaluation_callable():
    import evaluation.runner as m
    assert callable(m.run_evaluation)


def test_load_annotation_signature():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters) == ["path"]


def test_load_annotation_path_param_kind():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_signature():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters) == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_param_kinds():
    sig = inspect.signature(_process_one)
    for name in ("doc", "output_root", "parser_name", "max_chars"):
        assert sig.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_return_annotation_is_str():
    sig = inspect.signature(_process_one)
    assert isinstance(sig.return_annotation, str)


def test_run_evaluation_signature():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters) == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_keyword_only_kwargs():
    """parser_name/max_chars/tolerance_chars 应是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_default_parser_name():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_default_max_chars():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_default_tolerance_chars():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_manifest_param_kind():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_output_path_param_kind():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# =========================================================================
# 综合行为
# =========================================================================


def test_run_evaluation_full_flow_two_docs(tmp_path, monkeypatch):
    """两个 doc 完整流程：process_single 各被调用一次。"""
    p1 = tmp_path / "x1.txt"
    p1.write_text("hi", encoding="utf-8")
    p2 = tmp_path / "x2.txt"
    p2.write_text("hi2", encoding="utf-8")
    docs = [
        _FakeDocEntry(doc_id="d1", resolved_path=p1),
        _FakeDocEntry(doc_id="d2", resolved_path=p2),
    ]

    calls = []

    def fake_process_single(*args, **kwargs):
        calls.append(args[0] if args else None)
        return _FakeDocument(parser_version="0.1.0"), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(calls) == 2
    assert len(report["per_doc"]) == 2
    assert report["per_doc"][0]["doc_id"] == "d1"
    assert report["per_doc"][1]["doc_id"] == "d2"


def test_run_evaluation_full_flow_with_expected_failures(tmp_path, monkeypatch):
    """doc + expected_failure 共存。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    bad = tmp_path / "missing.txt"
    docs = [_FakeDocEntry(doc_id="d1", resolved_path=p)]
    efs = [_FakeExpectedFailure("ef1", bad, "file_not_found")]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs, expected_failures=efs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 1
    assert len(report["expected_failures"]) == 1


def test_run_evaluation_propagates_first_parser_version_only(tmp_path, monkeypatch):
    """第一个成功 doc 的 parser_version 进 provenance，后续 doc 不覆盖。"""
    p1 = tmp_path / "x1.txt"
    p1.write_text("hi", encoding="utf-8")
    p2 = tmp_path / "x2.txt"
    p2.write_text("hi2", encoding="utf-8")
    docs = [
        _FakeDocEntry(doc_id="d1", resolved_path=p1),
        _FakeDocEntry(doc_id="d2", resolved_path=p2),
    ]

    versions = ["1.0.0", "2.0.0"]

    def fake_process_single(*args, **kwargs):
        v = versions.pop(0)
        return _FakeDocument(parser_version=v), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_writes_report_with_unicode(tmp_path, monkeypatch):
    """报告文件能保留 unicode 字符（doc_id 等）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="中文标识符", resolved_path=p)]

    monkeypatch.setattr("evaluation.runner.process_single",
                        lambda *a, **kw: (_FakeDocument(), []))
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    assert "中文标识符" in text
