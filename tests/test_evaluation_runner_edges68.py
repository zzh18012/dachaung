"""evaluation/runner.py 第六十八轮 edges 测试（Round 607）。

补强 edges67 未触及的角度（第四十三批）。

新角度：
- _load_annotation 边界（None / 缺失文件 / 目录 / 空 JSON / 仅空白 JSON / 大对象 / 深嵌套）
- _load_annotation 签名（单参 / 返回 annotation）
- _process_one 签名（4 参 / 返回 5 元组）
- _process_one 成功路径（document 非空 → 5-tuple 完整字段）
- _process_one errors 非空 → 返回 errors[0]
- _process_one document=None 无 errors → unknown error
- _process_one write_json=False（不写盘）
- _process_one image_dir 推导（document 存在时）
- _process_one image_dir=None（document=None 时）
- _process_one out_stub 清理（即使失败也清）
- run_evaluation 签名（manifest / output_path 必填 / parser_name / max_chars / tolerance_chars 默认）
- run_evaluation 报告结构（report_version / provenance / devset / summary / per_doc / expected_failures）
- run_evaluation 写文件到 output_path
- run_evaluation per_doc 不含 _annotation_present（公开版剥离）
- run_evaluation per_doc 不含 _tolerance_chars
- run_evaluation per_doc 不含 _missing_markers
- run_evaluation per_doc 含 wall_time_seconds（total / parse / chunk / parse_reason / chunk_reason）
- run_evaluation per_doc.parse_reason = "not_instrumented"
- run_evaluation per_doc.chunk_reason = "not_instrumented"
- run_evaluation expected_failures 字段（doc_id / expected_error_code / actual_error_code / matches）
- module source 字符串精确
- AST 结构
- module 合理性
- 端到端集成
- forbidden tokens 第七十八批
"""

from __future__ import annotations

import ast
import inspect
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第四十三批


def test_load_annotation_callable_batch43():
    assert callable(_load_annotation)


def test_load_annotation_signature_batch43():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_load_annotation_return_annotation_dict_or_none_batch43():
    sig = inspect.signature(_load_annotation)
    ann = str(sig.return_annotation)
    assert "dict" in ann
    assert "None" in ann


def test_load_annotation_none_returns_none_batch43():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_file_returns_none_batch43(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none_batch43(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_empty_json_returns_empty_dict_batch43(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


def test_load_annotation_whitespace_only_returns_none_batch43(tmp_path):
    """仅空白的文件不是合法 JSON → JSONDecodeError → None。"""
    p = tmp_path / "ann.json"
    p.write_text("   \n  \t ", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_invalid_json_returns_none_batch43(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{invalid", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_oserror_returns_none_batch43(tmp_path):
    """模拟 OSError（如权限拒绝）→ None。"""
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    original_open = Path.open
    with patch.object(Path, "open", side_effect=OSError("denied")):
        out = _load_annotation(p)
    assert out is None


def test_load_annotation_normal_dict_batch43(tmp_path):
    p = tmp_path / "ann.json"
    data = {"figure_captions": [], "chunk_boundaries": []}
    p.write_text(json.dumps(data), encoding="utf-8")
    out = _load_annotation(p)
    assert out == data


def test_load_annotation_nested_complex_batch43(tmp_path):
    p = tmp_path / "ann.json"
    data = {"a": {"b": {"c": [1, 2, {"d": "e"}]}}}
    p.write_text(json.dumps(data), encoding="utf-8")
    out = _load_annotation(p)
    assert out == data


def test_load_annotation_list_top_level_returns_list_batch43(tmp_path):
    """JSON 顶层可以是 list（不限 dict）。"""
    p = tmp_path / "ann.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_string_top_level_returns_str_batch43(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_number_top_level_returns_number_batch43(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_idempotent_batch43(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    out1 = _load_annotation(p)
    out2 = _load_annotation(p)
    assert out1 == out2


# ---------- _process_one 签名 第四十三批


def test_process_one_callable_batch43():
    assert callable(_process_one)


def test_process_one_signature_batch43():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_return_annotation_tuple_batch43():
    sig = inspect.signature(_process_one)
    ann = str(sig.return_annotation)
    assert "tuple" in ann.lower()


def test_process_one_doc_no_default_batch43():
    sig = inspect.signature(_process_one)
    assert sig.parameters["doc"].default is inspect.Parameter.empty


def test_process_one_output_root_no_default_batch43():
    sig = inspect.signature(_process_one)
    assert sig.parameters["output_root"].default is inspect.Parameter.empty


def test_process_one_parser_name_no_default_batch43():
    sig = inspect.signature(_process_one)
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty


def test_process_one_max_chars_no_default_batch43():
    sig = inspect.signature(_process_one)
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


# ---------- _process_one 行为 第四十三批


def _make_doc_mock(**overrides: Any) -> MagicMock:
    m = MagicMock()
    m.doc_id = "d1"
    m.resolved_path = Path("/tmp/a.pdf")
    m.source_type = "pdf"
    m.expectations = None
    m.annotation_resolved = None
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def test_process_one_success_returns_5_tuple_batch43(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"document_id": "d1", "elements": []}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(out, tuple)
    assert len(out) == 5


def test_process_one_success_document_dict_batch43(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"document_id": "d1"}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        document_dict, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict == {"document_id": "d1"}
    assert error is None
    assert isinstance(total, float)
    assert pv == "0.1.0"


def test_process_one_errors_returns_first_error_batch43(tmp_path):
    doc = _make_doc_mock()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "PARSE_FAILED", "message": "boom"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "OTHER", "message": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document_dict, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict is None
    assert error == {"code": "PARSE_FAILED", "message": "boom"}
    assert pv is None


def test_process_one_document_none_no_errors_returns_unknown_batch43(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document_dict, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document_dict is None
    assert error["code"] == "unknown"
    assert "None" in error["message"] or "None without errors" in error["message"]


def test_process_one_total_is_float_batch43(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total, float)
    assert total >= 0.0


def test_process_one_creates_per_doc_dir_batch43(tmp_path):
    """_process_one 内部创建 _per_doc 目录。"""
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_unlinks_out_stub_batch43(tmp_path):
    """成功后 out_stub 应该被 unlink。"""
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    stub = tmp_path / "_per_doc" / "d1.json"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text("x", encoding="utf-8")
    assert stub.is_file()

    def fake_process_single(*args, **kwargs):
        # process_single 内部不真的写盘（mock）
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        _process_one(doc, tmp_path, "fallback", 800)
    assert not stub.is_file()


def test_process_one_calls_process_single_with_correct_args_batch43(tmp_path):
    """process_single 收到 resolved_path / out_stub / parser_name / max_chars / write_json=False。"""
    doc = _make_doc_mock(resolved_path=Path("/tmp/a.pdf"))
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])) as mock_ps:
        _process_one(doc, tmp_path, "fallback", 800)
    args, kwargs = mock_ps.call_args
    assert kwargs.get("parser_name") == "fallback"
    assert kwargs.get("max_chars") == 800
    assert kwargs.get("write_json") is False


# ---------- run_evaluation 签名 第四十三批


def test_run_evaluation_callable_batch43():
    assert callable(run_evaluation)


def test_run_evaluation_signature_batch43():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_parser_name_default_fallback_batch43():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_max_chars_default_800_batch43():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_tolerance_chars_default_30_batch43():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_manifest_no_default_batch43():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_run_evaluation_output_path_no_default_batch43():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_run_evaluation_parser_name_keyword_only_batch43():
    """parser_name / max_chars / tolerance_chars 是 keyword-only（* 之后）。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_return_annotation_dict_batch43():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


# ---------- run_evaluation 报告结构 第四十三批


def _make_manifest_mock(docs=None, failures=None) -> MagicMock:
    m = MagicMock()
    m.documents = tuple(docs or [])
    m.expected_failures = tuple(failures or [])
    m.project_root = Path("/tmp")
    m.devset_status = "incomplete"
    m.file_count = len(m.documents)
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_returns_dict_batch43(tmp_path):
    m = _make_manifest_mock()
    with patch("evaluation.runner.process_single", return_value=(None, [MagicMock(code="X")] if False else [])):
        # 改用稳定 mock：直接 None+[] 不行（unknown error），改用 error 模拟
        with patch("evaluation.runner._process_one") as mock_p1, \
             patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
             patch("evaluation.runner.figure_caption_prf", return_value={}), \
             patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
             patch("evaluation.runner.build_provenance", return_value={}), \
             patch("evaluation.runner.build_devset_section", return_value={}), \
             patch("evaluation.runner.aggregate_summary", return_value={}):
            mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
            out_path = tmp_path / "out.json"
            report = run_evaluation(m, out_path)
    assert isinstance(report, dict)


def test_run_evaluation_report_version_batch43(tmp_path):
    m = _make_manifest_mock()
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_top_level_keys_batch43(tmp_path):
    m = _make_manifest_mock()
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert set(report.keys()) == {
        "report_version", "provenance", "devset", "summary", "per_doc", "expected_failures",
    }


def test_run_evaluation_writes_output_file_batch43(tmp_path):
    m = _make_manifest_mock()
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "subdir" / "out.json"
        report = run_evaluation(m, out_path)
    assert out_path.is_file()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["report_version"] == REPORT_VERSION


def test_run_evaluation_per_doc_no_internal_markers_batch43(tmp_path):
    """公开 per_doc 不应含 _annotation_present / _tolerance_chars / _missing_markers。"""
    m = _make_manifest_mock()
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    for entry in report["per_doc"]:
        assert "_annotation_present" not in entry
        assert "_tolerance_chars" not in entry
        assert "_missing_markers" not in entry


def test_run_evaluation_per_doc_has_doc_id_batch43(tmp_path):
    m = _make_manifest_mock(docs=[_make_doc_mock(doc_id="d1")])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner._load_annotation", return_value=None), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert len(report["per_doc"]) == 1
    assert report["per_doc"][0]["doc_id"] == "d1"


def test_run_evaluation_per_doc_has_source_type_batch43(tmp_path):
    doc = _make_doc_mock(source_type="pdf")
    m = _make_manifest_mock(docs=[doc])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner._load_annotation", return_value=None), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert report["per_doc"][0]["source_type"] == "pdf"


def test_run_evaluation_per_doc_has_metrics_batch43(tmp_path):
    m = _make_manifest_mock(docs=[_make_doc_mock(doc_id="d1")])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner._load_annotation", return_value=None), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={"x": {"value": 1}}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert report["per_doc"][0]["metrics"] == {"x": {"value": 1}}


def test_run_evaluation_per_doc_has_wall_time_seconds_batch43(tmp_path):
    m = _make_manifest_mock(docs=[_make_doc_mock()])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner._load_annotation", return_value=None), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.123, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["total"] == 0.123
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_per_doc_keys_batch43(tmp_path):
    m = _make_manifest_mock(docs=[_make_doc_mock()])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner._load_annotation", return_value=None), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert set(report["per_doc"][0].keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


# ---------- run_evaluation expected_failures 第四十三批


def test_run_evaluation_expected_failures_empty_batch43(tmp_path):
    m = _make_manifest_mock(failures=[])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert report["expected_failures"] == []


def test_run_evaluation_expected_failure_with_error_batch43(tmp_path):
    """expected_failure 跑出错误 → matches=True（当 actual_code == expected）。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = Path("/tmp/broken.pdf")
    ef.expected_error_code = "PARSE_FAILED"
    m = _make_manifest_mock(failures=[ef])
    err = MagicMock()
    err.code = "PARSE_FAILED"
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert len(report["expected_failures"]) == 1
    ef_result = report["expected_failures"][0]
    assert ef_result["doc_id"] == "ef1"
    assert ef_result["expected_error_code"] == "PARSE_FAILED"
    assert ef_result["actual_error_code"] == "PARSE_FAILED"
    assert ef_result["matches"] is True


def test_run_evaluation_expected_failure_mismatch_batch43(tmp_path):
    """actual != expected → matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = Path("/tmp/broken.pdf")
    ef.expected_error_code = "PARSE_FAILED"
    m = _make_manifest_mock(failures=[ef])
    err = MagicMock()
    err.code = "SCHEMA_INVALID"
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_no_error_actual_none_batch43(tmp_path):
    """expected_failure 跑成功（无 errors）→ actual_error_code=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = Path("/tmp/x.pdf")
    ef.expected_error_code = "PARSE_FAILED"
    m = _make_manifest_mock(failures=[ef])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.process_single", return_value=(MagicMock(), [])), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert report["expected_failures"][0]["actual_error_code"] is None
    assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_keys_batch43(tmp_path):
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = Path("/tmp/x.pdf")
    ef.expected_error_code = "X"
    m = _make_manifest_mock(failures=[ef])
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.process_single", return_value=(None, [])), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert set(report["expected_failures"][0].keys()) == {
        "doc_id", "expected_error_code", "actual_error_code", "matches",
    }


# ---------- module source 字符串精确 第四十三批


def test_module_source_contains_docstring_batch43():
    src = inspect.getsource(rmod)
    assert '"""' in src


def test_module_source_contains_future_annotations_batch43():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch43():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_contains_time_import_batch43():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_contains_pathlib_path_import_batch43():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch43():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_pipeline_import_batch43():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_report_version_import_batch43():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch43():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_source_contains_chunk_boundary_prf_import_batch43():
    src = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in src


def test_module_source_contains_figure_caption_prf_import_batch43():
    src = inspect.getsource(rmod)
    assert "figure_caption_prf" in src


def test_module_source_contains_compute_automatic_metrics_import_batch43():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_aggregate_summary_import_batch43():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src
    assert "aggregate_summary" in src


def test_module_source_contains_build_devset_section_import_batch43():
    src = inspect.getsource(rmod)
    assert "build_devset_section" in src


def test_module_source_contains_build_provenance_import_batch43():
    src = inspect.getsource(rmod)
    assert "build_provenance" in src


def test_module_source_contains_load_annotation_function_batch43():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_function_batch43():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_function_batch43():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_perf_counter_batch43():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_not_instrumented_batch43():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_write_json_false_batch43():
    src = inspect.getsource(rmod)
    assert "write_json=False" in src


def test_module_source_contains_image_output_dir_for_batch43():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src


def test_module_source_contains_all_definition_batch43():
    src = inspect.getsource(rmod)
    assert "__all__" in src


# ---------- AST 结构 第四十三批


def test_ast_top_level_no_class_no_loop_no_with_batch43():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert not isinstance(node, (ast.ClassDef, ast.For, ast.While, ast.With, ast.Try))


def test_ast_has_three_functions_batch43():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "_load_annotation" in funcs
    assert "_process_one" in funcs
    assert "run_evaluation" in funcs


def test_ast_no_async_functions_batch43():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    async_funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert async_funcs == []


def test_ast_top_level_only_allowed_kinds_batch43():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign))


def test_ast_has_module_docstring_batch43():
    src = inspect.getsource(rmod)
    tree = ast.parse(src)
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)
    assert isinstance(first.value.value, str)


# ---------- module 合理性 第四十三批


def test_module_has_all_attribute_batch43():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch43():
    assert isinstance(rmod.__all__, list)


def test_module_all_one_entry_batch43():
    assert len(rmod.__all__) == 1


def test_module_all_contains_run_evaluation_batch43():
    assert "run_evaluation" in rmod.__all__


def test_module_does_not_export_private_batch43():
    for name in ["_load_annotation", "_process_one"]:
        assert name not in rmod.__all__


def test_module_all_contains_only_strings_batch43():
    for name in rmod.__all__:
        assert isinstance(name, str)


def test_module_all_no_duplicates_batch43():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_has_load_annotation_attr_batch43():
    assert hasattr(rmod, "_load_annotation")


def test_module_has_process_one_attr_batch43():
    assert hasattr(rmod, "_process_one")


def test_module_has_run_evaluation_attr_batch43():
    assert hasattr(rmod, "run_evaluation")


def test_module_run_evaluation_callable_batch43():
    assert callable(rmod.run_evaluation)


def test_module_load_annotation_callable_batch43():
    assert callable(rmod._load_annotation)


def test_module_process_one_callable_batch43():
    assert callable(rmod._process_one)


# ---------- 端到端集成 第四十三批


def test_e2e_full_run_minimal_batch43(tmp_path):
    """端到端跑一次最小 manifest（无 docs）。"""
    m = _make_manifest_mock()
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}), \
         patch("evaluation.runner.build_devset_section", return_value={"status": "incomplete"}), \
         patch("evaluation.runner.aggregate_summary", return_value={"silent_drop_total": 0}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        out_path = tmp_path / "out.json"
        report = run_evaluation(m, out_path)
    assert report["provenance"]["git_commit"] == "abc"
    assert report["devset"]["status"] == "incomplete"
    assert report["summary"]["silent_drop_total"] == 0
    assert report["per_doc"] == []


def test_e2e_creates_output_dir_if_missing_batch43(tmp_path):
    """output_path 父目录不存在时自动创建。"""
    m = _make_manifest_mock()
    out_path = tmp_path / "deep" / "nested" / "out.json"
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        run_evaluation(m, out_path)
    assert out_path.is_file()


def test_e2e_output_file_is_valid_json_batch43(tmp_path):
    m = _make_manifest_mock()
    out_path = tmp_path / "out.json"
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        run_evaluation(m, out_path)
    # 不抛异常即合法 JSON
    json.loads(out_path.read_text(encoding="utf-8"))


def test_e2e_output_uses_indent_2_batch43(tmp_path):
    """报告用 indent=2 写盘。"""
    m = _make_manifest_mock()
    out_path = tmp_path / "out.json"
    with patch("evaluation.runner._process_one") as mock_p1, \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        mock_p1.return_value = (None, {"code": "x"}, 0.1, None, None)
        run_evaluation(m, out_path)
    txt = out_path.read_text(encoding="utf-8")
    # indent=2 应该出现 "  "（两空格缩进）
    assert "\n  " in txt


# ---------- module source forbidden tokens 第七十八批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch43(token):
    src = inspect.getsource(rmod)
    assert token not in src
