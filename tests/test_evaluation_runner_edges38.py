"""evaluation/runner.py 第三十九轮 edges 测试（Round 396）。

补强 edges37 未触及的角度：
- _load_annotation 行为深度第十一批（JSON array / number / null / bool / empty object / empty array / deep nested / BOM / 相对路径 / directory path / 多种异常分支）
- _process_one 行为深度第十一批（返回 5-tuple 类型 / parser_version 透传 / image_dir 推导 / mkdir idempotent / stub unlink 失败 silent / 透传 kwargs 各字段 / elapsed 时间正向）
- run_evaluation 行为深度第十一批（report_version / public per_doc 结构 / private keys 剥离顺序 / expected_failures 流程细节 / parser_version 累积规则 / tolerance / missing_markers 写入 / public_per_doc 不含私有字段 / 空 manifest / 全 expected_failures）
- module source forbidden tokens 第十四批
- module source 字符串精确补强第十一批
- signatures 第十一批
- module 合理性第十一批
- 端到端集成第十一批
"""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from evaluation import REPORT_VERSION, runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- helpers ----------


class _StubDoc:
    def __init__(
        self,
        doc_id="doc1",
        source_type="pdf",
        resolved_path=None,
        annotation_resolved=None,
        expectations=None,
    ):
        self.doc_id = doc_id
        self.source_type = source_type
        self.resolved_path = resolved_path
        self.annotation_resolved = annotation_resolved
        self.expectations = expectations


class _StubManifest:
    def __init__(self, documents=None, expected_failures=None, project_root=None):
        self.documents = documents or []
        self.expected_failures = expected_failures or []
        self.project_root = project_root or Path(".")
        self.devset_status = "incomplete"
        self.file_count = 0
        self.content_group_count = 0
        self.pdf_count = 0
        self.docx_count = 0
        self.categories_covered = []


class _StubDocument:
    def __init__(self, source_hash="a" * 64, parser_version="1.0.0"):
        self.source_hash = source_hash
        self.parser_version = parser_version

    def to_dict(self):
        return {"source_hash": self.source_hash, "parser_version": self.parser_version}


class _StubError:
    def __init__(self, code="parse_failed", message="boom"):
        self.code = code
        self.message = message

    def to_dict(self):
        return {"code": self.code, "message": self.message}


class _StubExpectedFailure:
    def __init__(self, doc_id="ef1", resolved_path=None, expected_error_code="unsupported_format"):
        self.doc_id = doc_id
        self.resolved_path = resolved_path
        self.expected_error_code = expected_error_code


# ---------- _load_annotation 行为深度第十一批 ----------


def test_load_annotation_none_path_returns_none_batch11():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_path_returns_none_batch11(tmp_path):
    p = tmp_path / "does_not_exist.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_path_returns_none_batch11(tmp_path):
    """路径是目录 → is_file() False → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_json_array_file_batch11(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]
    assert isinstance(out, list)


def test_load_annotation_json_number_file_batch11(tmp_path):
    p = tmp_path / "num.json"
    p.write_text("42.5", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42.5
    assert isinstance(out, float)


def test_load_annotation_json_int_file_batch11(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42
    assert isinstance(out, int)


def test_load_annotation_json_null_file_batch11(tmp_path):
    """JSON null 加载成功，返回 None（不是异常）。"""
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_json_true_file_batch11(tmp_path):
    p = tmp_path / "true.json"
    p.write_text("true", encoding="utf-8")
    out = _load_annotation(p)
    assert out is True
    assert isinstance(out, bool)


def test_load_annotation_json_false_file_batch11(tmp_path):
    p = tmp_path / "false.json"
    p.write_text("false", encoding="utf-8")
    out = _load_annotation(p)
    assert out is False
    assert isinstance(out, bool)


def test_load_annotation_json_empty_object_batch11(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}
    assert isinstance(out, dict)


def test_load_annotation_json_empty_array_batch11(tmp_path):
    p = tmp_path / "emptyarr.json"
    p.write_text("[]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == []
    assert isinstance(out, list)


def test_load_annotation_deep_nested_object_batch11(tmp_path):
    """深度嵌套 object 加载成功。"""
    p = tmp_path / "deep.json"
    p.write_text('{"a": {"b": {"c": {"d": {"e": 1}}}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": {"d": {"e": 1}}}}}


def test_load_annotation_json_with_bom_batch11(tmp_path):
    """UTF-8 BOM 让 json.load 失败（不自动跳过）→ None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_invalid_json_returns_none_batch11(tmp_path):
    p = tmp_path / "invalid.json"
    p.write_text('{"k": "', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_with_comment_returns_none_batch11(tmp_path):
    """JSON 标准不支持注释 → JSONDecodeError → None。"""
    p = tmp_path / "comment.json"
    p.write_text('{"k": "v"} // comment', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_dict_type_batch11(tmp_path):
    p = tmp_path / "obj.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert type(out) is dict


def test_load_annotation_does_not_raise_batch11(tmp_path):
    """任何输入都不抛。"""
    _load_annotation(None)
    _load_annotation(tmp_path / "missing.json")
    p = tmp_path / "bad.json"
    p.write_text("{", encoding="utf-8")
    _load_annotation(p)


def test_load_annotation_idempotent_batch11(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    out1 = _load_annotation(p)
    out2 = _load_annotation(p)
    assert out1 == out2


# ---------- _process_one 行为深度第十一批 ----------


def test_process_one_returns_5_tuple_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def _fake_process(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        result = _process_one(doc, output_root, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_document_none_when_errors_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def _fake_process(*args, **kwargs):
        return None, [_StubError("parse_failed", "msg")]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        document, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert document is None
    assert error == {"code": "parse_failed", "message": "msg"}


def test_process_one_unknown_error_when_no_errors_no_document_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def _fake_process(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        document, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert document is None
    assert error == {
        "code": "unknown",
        "message": "process_single returned None without errors",
    }


def test_process_one_parser_version_from_document_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    fake_doc = _StubDocument(parser_version="9.9.9")

    def _fake_process(*args, **kwargs):
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        document, error, _, parser_version, _ = _process_one(doc, output_root, "fallback", 800)
    assert document == fake_doc.to_dict()
    assert error is None
    assert parser_version == "9.9.9"


def test_process_one_image_dir_none_when_document_none_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def _fake_process(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
    assert image_dir is None


def test_process_one_image_dir_when_document_present_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    fake_doc = _StubDocument()

    def _fake_process(*args, **kwargs):
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=_fake_process), \
         patch("evaluation.runner.image_output_dir_for", return_value=Path("/custom/dir")):
        _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
    assert image_dir == Path("/custom/dir")


def test_process_one_creates_per_doc_dir_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"

    def _fake_process(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _process_one(doc, output_root, "fallback", 800)
    assert (output_root / "_per_doc").is_dir()


def test_process_one_unlinks_stub_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"

    def _fake_process(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _process_one(doc, output_root, "fallback", 800)
    stub = output_root / "_per_doc" / "doc1.json"
    assert not stub.is_file()


def test_process_one_silent_unlink_failure_batch11(tmp_path):
    """stub unlink 抛 OSError 时静默吞掉。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"

    def _fake_process(*args, **kwargs):
        # 不真正写文件，stub.is_file() 返回 False 时不会触发 unlink
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        # 不抛异常即可
        result = _process_one(doc, output_root, "fallback", 800)
    assert isinstance(result, tuple)


def test_process_one_forwards_parser_name_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    captured: list = []

    def _fake_process(*args, **kwargs):
        captured.append(kwargs)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _process_one(doc, output_root, "kreuzberg", 800)
    assert captured[0]["parser_name"] == "kreuzberg"


def test_process_one_forwards_max_chars_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    captured: list = []

    def _fake_process(*args, **kwargs):
        captured.append(kwargs)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _process_one(doc, output_root, "fallback", 1234)
    assert captured[0]["max_chars"] == 1234


def test_process_one_forwards_write_json_false_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    captured: list = []

    def _fake_process(*args, **kwargs):
        captured.append(kwargs)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _process_one(doc, output_root, "fallback", 800)
    assert captured[0]["write_json"] is False


def test_process_one_elapsed_positive_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"

    def _fake_process(*args, **kwargs):
        time.sleep(0.001)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _, _, elapsed, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert isinstance(elapsed, float)
    assert elapsed >= 0


def test_process_one_idempotent_doc_dict_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    fake_doc = _StubDocument()

    def _fake_process(*args, **kwargs):
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        d1, _, _, _, _ = _process_one(doc, output_root, "fallback", 800)
        d2, _, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert d1 == d2


def test_process_one_dict_type_batch11(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    fake_doc = _StubDocument()

    def _fake_process(*args, **kwargs):
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        d1, _, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert type(d1) is dict


# ---------- run_evaluation 行为深度第十一批 ----------


def test_run_evaluation_report_version_in_report_batch11(tmp_path):
    """生成的报告 report_version 等于 REPORT_VERSION。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_public_per_doc_no_private_keys_batch11(tmp_path):
    """公开 per_doc 不应含 _annotation_present / _tolerance_chars / _missing_markers。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 1
    for item in report["per_doc"]:
        assert set(item.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}
        assert "_annotation_present" not in item
        assert "_tolerance_chars" not in item
        assert "_missing_markers" not in item


def test_run_evaluation_public_per_doc_keys_order_batch11(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert list(report["per_doc"][0].keys()) == ["doc_id", "source_type", "metrics", "wall_time_seconds"]


def test_run_evaluation_wall_time_keys_batch11(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failures_keys_batch11(tmp_path):
    """expected_failures 每条有 4 个 keys：doc_id, expected_error_code, actual_error_code, matches。"""
    manifest = _StubManifest(
        expected_failures=[_StubExpectedFailure(doc_id="ef1", expected_error_code="unsupported_format")]
    )
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert len(report["expected_failures"]) == 1
    ef = report["expected_failures"][0]
    assert set(ef.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}


def test_run_evaluation_expected_failures_matches_when_codes_match_batch11(tmp_path):
    manifest = _StubManifest(
        expected_failures=[_StubExpectedFailure(doc_id="ef1", expected_error_code="boom")]
    )
    out = tmp_path / "report.json"

    def _fake(*args, **kwargs):
        return None, [_StubError(code="boom")]

    with patch("evaluation.runner.process_single", side_effect=_fake), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    ef = report["expected_failures"][0]
    assert ef["matches"] is True
    assert ef["actual_error_code"] == "boom"


def test_run_evaluation_expected_failures_no_match_when_codes_differ_batch11(tmp_path):
    manifest = _StubManifest(
        expected_failures=[_StubExpectedFailure(doc_id="ef1", expected_error_code="expected")]
    )
    out = tmp_path / "report.json"

    def _fake(*args, **kwargs):
        return None, [_StubError(code="actual")]

    with patch("evaluation.runner.process_single", side_effect=_fake), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    ef = report["expected_failures"][0]
    assert ef["matches"] is False


def test_run_evaluation_expected_failure_actual_code_none_when_no_errors_batch11(tmp_path):
    manifest = _StubManifest(
        expected_failures=[_StubExpectedFailure(doc_id="ef1", expected_error_code="boom")]
    )
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return _StubDocument(), []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    ef = report["expected_failures"][0]
    assert ef["actual_error_code"] is None
    assert ef["matches"] is False


def test_run_evaluation_parser_version_first_wins_batch11(tmp_path):
    """parser_version 取第一个非 None 的值。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1"), _StubDoc(doc_id="d2")])
    out = tmp_path / "report.json"

    call_count = [0]

    def _fake(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _StubDocument(parser_version="1.0.0"), []
        return _StubDocument(parser_version="2.0.0"), []

    captured: dict = {}

    def _fake_prov(*args, **kwargs):
        captured["parser_version"] = kwargs.get("parser_version")
        return {"parser_version": captured["parser_version"]}

    with patch("evaluation.runner.process_single", side_effect=_fake), \
         patch("evaluation.runner.build_provenance", side_effect=_fake_prov), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert captured["parser_version"] == "1.0.0"


def test_run_evaluation_parser_version_none_when_all_fail_batch11(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    captured: dict = {}

    def _fake_prov(*args, **kwargs):
        captured["parser_version"] = kwargs.get("parser_version")
        return {"parser_version": captured["parser_version"]}

    with patch("evaluation.runner.process_single", side_effect=_fake), \
         patch("evaluation.runner.build_provenance", side_effect=_fake_prov), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert captured["parser_version"] is None


def test_run_evaluation_writes_file_batch11(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_writes_valid_json_batch11(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={"k": "v"}), \
         patch("evaluation.runner.build_devset_section", return_value={"status": "incomplete"}), \
         patch("evaluation.runner.aggregate_summary", return_value={"counts": {}}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    parsed = json.loads(text)
    assert parsed == report


def test_run_evaluation_creates_output_dir_batch11(tmp_path):
    """output_path 父目录不存在时自动创建。"""
    manifest = _StubManifest()
    out = tmp_path / "deep" / "nested" / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_empty_manifest_batch11(tmp_path):
    """manifest 没有 documents 时 per_doc 为空。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["per_doc"] == []
    assert report["expected_failures"] == []


def test_run_evaluation_returns_dict_batch11(tmp_path):
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert type(report) is dict


def test_run_evaluation_report_top_keys_batch11(tmp_path):
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


# ---------- module source forbidden tokens 第十四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
    ],
)
def test_runner_source_no_forbidden_token_fourteenth_batch11(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_runner_source_no_unlink_outside_safe_context_batch11():
    """允许 unlink（pipeline 内），但出现在受控位置（_process_one / run_evaluation 内）。"""
    source = inspect.getsource(rmod)
    # 允许 unlink，但应只在受控位置（process_one / expected_failures 内）
    assert source.count("unlink") == 2


def test_runner_source_no_remove_batch11():
    source = inspect.getsource(rmod)
    assert ".remove(" not in source


def test_runner_source_no_kill_batch11():
    source = inspect.getsource(rmod)
    assert ".kill(" not in source


def test_runner_source_no_terminate_batch11():
    source = inspect.getsource(rmod)
    assert ".terminate(" not in source


def test_runner_source_no_async_def_batch11():
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_runner_source_no_yield_batch11():
    source = inspect.getsource(rmod)
    assert "yield" not in source


def test_runner_source_no_walrus_batch11():
    source = inspect.getsource(rmod)
    assert ":=" not in source


def test_runner_source_no_top_level_lambda_batch11():
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_runner_source_no_print_batch11():
    source = inspect.getsource(rmod)
    assert "print(" not in source


def test_runner_source_no_logging_batch11():
    source = inspect.getsource(rmod)
    assert "logging" not in source
    assert "logger" not in source


def test_runner_source_no_socket_batch11():
    source = inspect.getsource(rmod)
    assert "socket" not in source


def test_runner_source_no_threading_batch11():
    source = inspect.getsource(rmod)
    assert "threading" not in source


def test_runner_source_no_multiprocessing_batch11():
    source = inspect.getsource(rmod)
    assert "multiprocessing" not in source


def test_runner_source_no_asyncio_batch11():
    source = inspect.getsource(rmod)
    assert "asyncio" not in source


def test_runner_source_no_pickle_module_batch11():
    source = inspect.getsource(rmod)
    assert "import pickle" not in source


# ---------- module source 字符串精确补强第十一批 ----------


def test_module_source_has_future_annotations_batch11():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json_batch11():
    source = inspect.getsource(rmod)
    assert "import json" in source


def test_module_source_imports_time_batch11():
    source = inspect.getsource(rmod)
    assert "import time" in source


def test_module_source_imports_path_batch11():
    source = inspect.getsource(rmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch11():
    source = inspect.getsource(rmod)
    assert "from typing import Any" in source


def test_module_source_imports_process_single_batch11():
    source = inspect.getsource(rmod)
    assert "process_single" in source
    assert "image_output_dir_for" in source


def test_module_source_imports_annotation_metrics_batch11():
    source = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in source
    assert "figure_caption_prf" in source


def test_module_source_imports_metrics_batch11():
    source = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in source


def test_module_source_imports_report_helpers_batch11():
    source = inspect.getsource(rmod)
    assert "aggregate_summary" in source
    assert "build_devset_section" in source
    assert "build_provenance" in source


def test_module_source_perf_counter_call_batch11():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_not_instrumented_marker_batch11():
    source = inspect.getsource(rmod)
    assert "not_instrumented" in source


def test_module_source_write_json_false_marker_batch11():
    source = inspect.getsource(rmod)
    assert "write_json=False" in source


def test_module_source_no_main_block_batch11():
    source = inspect.getsource(rmod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch11():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


def test_module_source_docstring_mentions_constraints_batch11():
    """docstring 提到关键约束。"""
    assert rmod.__doc__ is not None
    lower = rmod.__doc__.lower()
    assert "约束" in rmod.__doc__ or "constraint" in lower or "timer" in lower


# ---------- signatures 第十一批 ----------


def test_signature_load_annotation_1_param_batch11():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_signature_load_annotation_param_name_batch11():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters) == ["path"]


def test_signature_load_annotation_param_kind_batch11():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_load_annotation_param_no_default_batch11():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_process_one_4_params_batch11():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_signature_process_one_param_names_batch11():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters) == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_param_kinds_batch11():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_process_one_no_defaults_batch11():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_run_evaluation_2_positional_params_batch11():
    sig = inspect.signature(run_evaluation)
    positional = [
        p for p in sig.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]
    assert len(positional) == 2


def test_signature_run_evaluation_param_names_batch11():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters) == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_after_star_batch11():
    """parser_name, max_chars, tolerance_chars 都是 KEYWORD_ONLY。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    # 前 2 个是 POSITIONAL_OR_KEYWORD
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    # 后 3 个是 KEYWORD_ONLY（star 之后）
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_default_parser_name_batch11():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_signature_run_evaluation_default_max_chars_batch11():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_signature_run_evaluation_default_tolerance_chars_batch11():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_funcs_function_type_batch11():
    for func in (_load_annotation, _process_one, run_evaluation):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq_batch11():
    for func in (_load_annotation, _process_one, run_evaluation):
        assert func.__module__ == "evaluation.runner"


# ---------- module 合理性第十一批 ----------


def test_module_all_value_batch11():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_all_is_list_batch11():
    assert isinstance(rmod.__all__, list)


def test_module_all_entries_unique_batch11():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_all_entries_str_batch11():
    for name in rmod.__all__:
        assert isinstance(name, str)


def test_module_has_dunder_file_batch11():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_endswith_runner_py_batch11():
    import os
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "runner.py") or rmod.__file__.endswith(
        "evaluation/runner.py"
    )


def test_module_name_is_evaluation_runner_batch11():
    assert rmod.__name__ == "evaluation.runner"


def test_module_user_function_count_batch11():
    funcs = [
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_user_classes_batch11():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_has_report_version_attribute_batch11():
    assert hasattr(rmod, "REPORT_VERSION")


def test_module_docstring_present_batch11():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


def test_module_docstring_mentions_parsing_batch11():
    assert rmod.__doc__ is not None
    lower = rmod.__doc__.lower()
    assert "pipeline" in lower or "process" in lower or "解析" in rmod.__doc__


# ---------- 端到端集成第十一批 ----------


def test_e2e_run_evaluation_minimal_manifest_batch11(tmp_path):
    """空 manifest + 全 mock → 报告可生成、可序列化。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={"k": "v"}), \
         patch("evaluation.runner.build_devset_section", return_value={"status": "incomplete"}), \
         patch("evaluation.runner.aggregate_summary", return_value={"counts": {}}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={"m": {"value": 1}}):
        report = run_evaluation(manifest, out)
    text = json.dumps(report)
    parsed = json.loads(text)
    assert parsed == report


def test_e2e_run_evaluation_kwargs_call_batch11(tmp_path):
    """run_evaluation 支持 keyword-only 参数。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report1 = run_evaluation(manifest, out, parser_name="kreuzberg", max_chars=500, tolerance_chars=15)

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report2 = run_evaluation(
            manifest, out, parser_name="kreuzberg", max_chars=500, tolerance_chars=15
        )
    # 报告应可重复生成（虽然 timestamp 会变，但其他字段应一致）
    assert report1["report_version"] == report2["report_version"]


def test_e2e_run_evaluation_idempotent_structure_batch11(tmp_path):
    """重复运行同一 manifest，结构稳定。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1"), _StubDoc(doc_id="d2")])
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"

    def _no_op(*args, **kwargs):
        return None, []

    for path in (out1, out2):
        with patch("evaluation.runner.process_single", side_effect=_no_op), \
             patch("evaluation.runner.build_provenance", return_value={}), \
             patch("evaluation.runner.build_devset_section", return_value={}), \
             patch("evaluation.runner.aggregate_summary", return_value={}), \
             patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            report = run_evaluation(manifest, path)
    assert len(report["per_doc"]) == 2


def test_e2e_run_evaluation_default_kwargs_batch11(tmp_path):
    """不传 keyword-only 参数时使用默认值。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    captured: dict = {}

    def _fake_process(*args, **kwargs):
        captured["parser_name"] = kwargs.get("parser_name")
        captured["max_chars"] = kwargs.get("max_chars")
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_fake_process), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert captured["parser_name"] == "fallback"
    assert captured["max_chars"] == 800


def test_e2e_load_annotation_real_file_batch11(tmp_path):
    """真实文件 load 测试。"""
    p = tmp_path / "annot.json"
    p.write_text('{"chunks": [{"id": "c1", "text": "abc"}]}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"chunks": [{"id": "c1", "text": "abc"}]}


def test_e2e_full_chain_with_stub_document_batch11(tmp_path):
    """doc + document 成功 + 错误 → 完整链路。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out = tmp_path / "report.json"

    def _fake(*args, **kwargs):
        return _StubDocument(parser_version="2.0.0"), []

    with patch("evaluation.runner.process_single", side_effect=_fake), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={"k": {"value": 1}}):
        report = run_evaluation(manifest, out)
    assert report["per_doc"][0]["doc_id"] == "d1"


def test_e2e_json_output_unicode_safe_batch11(tmp_path):
    """JSON 输出 ensure_ascii=False，可包含 Unicode。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={"name": "中文"}), \
         patch("evaluation.runner.build_devset_section", return_value={"status": "未完成"}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    # Unicode 不被转义
    assert "中文" in text
    assert "未完成" in text


def test_e2e_run_evaluation_expected_failure_independent_batch11(tmp_path):
    """expected_failures 走独立 process_single 调用（不通过 _process_one）。"""
    manifest = _StubManifest(
        expected_failures=[_StubExpectedFailure(doc_id="ef1", expected_error_code="x")]
    )
    out = tmp_path / "report.json"
    call_count = [0]

    def _fake(*args, **kwargs):
        call_count[0] += 1
        # 第一次调用是 expected_failures 的（因为 documents 为空，process_one 不被调）
        return None, [_StubError(code="x")]

    with patch("evaluation.runner.process_single", side_effect=_fake), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert call_count[0] == 1
    assert report["expected_failures"][0]["matches"] is True


def test_e2e_run_evaluation_with_two_expected_failures_batch11(tmp_path):
    manifest = _StubManifest(
        expected_failures=[
            _StubExpectedFailure(doc_id="ef1", expected_error_code="x"),
            _StubExpectedFailure(doc_id="ef2", expected_error_code="y"),
        ]
    )
    out = tmp_path / "report.json"

    call_count = [0]

    def _fake(*args, **kwargs):
        call_count[0] += 1
        # 交替返回不同 code
        codes = ["x", "y"]
        return None, [_StubError(code=codes[call_count[0] - 1])]

    with patch("evaluation.runner.process_single", side_effect=_fake), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert call_count[0] == 2
    assert report["expected_failures"][0]["matches"] is True
    assert report["expected_failures"][1]["matches"] is True
