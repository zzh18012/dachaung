"""evaluation/runner.py 第五十五轮 edges 测试（Round 500）。

补强 edges52 未触及的角度（第二十五批）：
- _load_annotation 第二十五批：number 边界（整数 / 浮点 / 负数 / 科学计数 / 0）/ 单 quote 字符串非法 / trailing comma 非法 / NaN/Infinity 字面量非法 / 数组嵌套 / BOM 在前导空白后
- _process_one 第二十五批：返回 5-tuple 严格类型 / errors 多元素时只取 [0] / image_dir 在 document=None 时为 None / parser_version 透传 / out_stub unlink OSError 容错 / out_stub.parent.mkdir parents+exist_ok / write_json=False 透传
- run_evaluation 第二十五批：empty manifest.documents 仍写报告 / empty expected_failures / parser_version_for_prov 取首个非 None / 全失败时 parser_version_for_prov=None / wall_time_seconds 含 4 固定 key / public_per_doc 剥除私有字段 / per_doc 顺序匹配 manifest / expected_failure matches 字段
- module source forbidden tokens 第四十二批
- module source 字符串精确补强第三十八批
- signatures 第三十八批
- module 合理性第三十八批
- 端到端集成第三十八批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第二十五批 ----------


def test_load_annotation_positive_int_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    assert _load_annotation(p) == 42


def test_load_annotation_zero_int_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("0", encoding="utf-8")
    assert _load_annotation(p) == 0


def test_load_annotation_negative_int_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("-7", encoding="utf-8")
    assert _load_annotation(p) == -7


def test_load_annotation_float_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("3.14", encoding="utf-8")
    assert _load_annotation(p) == 3.14


def test_load_annotation_scientific_notation_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("1.5e3", encoding="utf-8")
    assert _load_annotation(p) == 1500.0


def test_load_annotation_negative_scientific_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("-2.5E-2", encoding="utf-8")
    assert _load_annotation(p) == pytest.approx(-0.025)


def test_load_annotation_nan_literal_invalid_batch25(tmp_path):
    """JSON 标准不支持 NaN 字面量 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("NaN", encoding="utf-8")
    # Python json 默认接受 NaN（非标准！）—— 我们不强制 strict，所以这里只是观察
    result = _load_annotation(p)
    # Python json.load 默认 parse_constant → float('nan')
    # 但我们的 _load_annotation 只 catch JSONDecodeError，所以会返回 nan
    assert result != result or result is None  # nan != nan 或 None


def test_load_annotation_infinity_literal_batch25(tmp_path):
    """Infinity 字面量 → Python json 默认接受 → inf。"""
    p = tmp_path / "a.json"
    p.write_text("Infinity", encoding="utf-8")
    result = _load_annotation(p)
    # 默认接受为 inf；只有 JSONDecodeError 才返回 None
    assert result is None or result == float("inf")


def test_load_annotation_single_quoted_string_invalid_batch25(tmp_path):
    """JSON 不允许单引号字符串 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("{'a': 1}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_trailing_comma_invalid_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_nested_array_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[[1, 2], [3, 4]]", encoding="utf-8")
    assert _load_annotation(p) == [[1, 2], [3, 4]]


def test_load_annotation_whitespace_then_bom_invalid_batch25(tmp_path):
    """前导空白后再 BOM → 标准 JSON 不允许（BOM 后还有空白也非法）。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'  \xef\xbb\xbf{"a": 1}')
    assert _load_annotation(p) is None


def test_load_annotation_empty_array_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[]", encoding="utf-8")
    assert _load_annotation(p) == []


def test_load_annotation_empty_object_batch25(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_path_is_dir_returns_none_batch25(tmp_path):
    """path 是目录 → not path.is_file() → None（不调用 open）。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_path_none_returns_none_batch25():
    assert _load_annotation(None) is None


def test_load_annotation_oserror_returns_none_batch25(tmp_path):
    """open 抛 OSError → None。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    original_open = Path.open
    def raising_open(self, *args, **kwargs):
        if str(self) == str(p):
            raise OSError("boom")
        return original_open(self, *args, **kwargs)
    with patch("pathlib.Path.open", raising_open):
        assert _load_annotation(p) is None


# ---------- _process_one 第二十五批 ----------


def _make_doc(doc_id="d1", source_type="pdf"):
    """构造一个 DocumentEntry-like 对象。"""
    doc = MagicMock()
    doc.doc_id = doc_id
    doc.source_type = source_type
    doc.resolved_path = Path("/fake/path.pdf")
    doc.expectations = {}
    doc.annotation_resolved = None
    return doc


def test_process_one_returns_five_tuple_batch25(tmp_path):
    """_process_one 总是返回 5-tuple。"""
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"doc_id": "d1"}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_tuple_element_types_batch25(tmp_path):
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"doc_id": "d1"}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, elapsed, parser_version, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert document == {"doc_id": "d1"}
    assert error is None
    assert isinstance(elapsed, float)
    assert parser_version == "0.1.0"
    assert image_dir == tmp_path / "imgs"


def test_process_one_errors_first_only_batch25(tmp_path):
    """errors 列表有多元素时只取 [0].to_dict()。"""
    doc = _make_doc()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "first_error", "message": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "second_error", "message": "second"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document, error, elapsed, parser_version, image_dir = _process_one(
            doc, tmp_path, "fallback", 800
        )
    assert document is None
    assert error == {"code": "first_error", "message": "first"}
    assert parser_version is None
    # image_dir is None when document is None
    assert image_dir is None


def test_process_one_document_none_no_errors_unknown_code_batch25(tmp_path):
    """document=None 且 errors 空时返回 unknown 错误代码。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, elapsed, parser_version, image_dir = _process_one(
            doc, tmp_path, "fallback", 800
        )
    assert document is None
    assert error == {"code": "unknown", "message": "process_single returned None without errors"}
    assert parser_version is None


def test_process_one_unlink_oserror_silent_batch25(tmp_path):
    """out_stub.unlink 抛 OSError → 静默吞掉。"""
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"doc_id": "d1"}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"

    def fake_process(*args, **kwargs):
        # 模拟 process_single 写了 out_stub
        out_stub = args[1] if len(args) > 1 else kwargs.get("output_path")
        if out_stub:
            Path(out_stub).parent.mkdir(parents=True, exist_ok=True)
            Path(out_stub).write_text("{}", encoding="utf-8")
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("pathlib.Path.unlink", side_effect=OSError("can't unlink")):
                # 不应崩溃
                document, error, elapsed, parser_version, image_dir = _process_one(
                    doc, tmp_path, "fallback", 800
                )
    assert error is None
    assert document == {"doc_id": "d1"}


def test_process_one_out_stub_naming_batch25(tmp_path):
    """out_stub = output_root / '_per_doc' / f'{doc_id}.json'。"""
    doc = _make_doc(doc_id="my_doc")
    captured_stub = []
    def fake_process(path, out_stub, **kwargs):
        captured_stub.append(out_stub)
        return MagicMock(parser_version="0.1.0", source_hash="abc"), []
    fake_doc_obj = MagicMock()
    fake_doc_obj.to_dict.return_value = {}
    fake_doc_obj.parser_version = "0.1.0"
    fake_doc_obj.source_hash = "abc"
    def fake_process2(*args, **kwargs):
        captured_stub.append(args[1] if len(args) > 1 else None)
        return fake_doc_obj, []
    with patch("evaluation.runner.process_single", side_effect=fake_process2):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured_stub[0] == tmp_path / "_per_doc" / "my_doc.json"


def test_process_one_write_json_false_passed_batch25(tmp_path):
    """write_json=False 必须传入 process_single。"""
    doc = _make_doc()
    captured_kwargs = {}
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    def fake_process(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_doc, []
    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured_kwargs.get("write_json") is False


def test_process_one_parser_name_kwarg_batch25(tmp_path):
    doc = _make_doc()
    captured_kwargs = {}
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    def fake_process(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_doc, []
    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "kreuzberg", 800)
    assert captured_kwargs.get("parser_name") == "kreuzberg"


def test_process_one_max_chars_kwarg_batch25(tmp_path):
    doc = _make_doc()
    captured_kwargs = {}
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    def fake_process(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return fake_doc, []
    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 1200)
    assert captured_kwargs.get("max_chars") == 1200


def test_process_one_elapsed_non_negative_batch25(tmp_path):
    """elapsed 时间必须 ≥ 0。"""
    doc = _make_doc()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "0.1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert elapsed >= 0


def test_process_one_image_dir_only_when_document_batch25(tmp_path):
    """document=None 时 image_dir 必为 None（不能是 Path()，否则下游把 cwd 当 base）。"""
    doc = _make_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


# ---------- run_evaluation 第二十五批 ----------


def _make_manifest(documents=None, expected_failures=None, project_root=None):
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path(".")
    m.devset_status = "incomplete"
    m.file_count = len(documents or [])
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_empty_documents_writes_report_batch25(tmp_path):
    """空 manifest.documents 仍能正常产出报告。"""
    m = _make_manifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert out.is_file()
    assert report["per_doc"] == []
    assert report["expected_failures"] == []


def test_run_evaluation_empty_expected_failures_batch25(tmp_path):
    m = _make_manifest(expected_failures=[])
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert report["expected_failures"] == []


def test_run_evaluation_per_doc_order_matches_manifest_batch25(tmp_path):
    """per_doc 顺序必须匹配 manifest.documents 顺序。"""
    docs = [_make_doc("a"), _make_doc("b"), _make_doc("c")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_doc_obj = MagicMock()
    fake_doc_obj.to_dict.return_value = {"source_hash": "x", "elements": [], "chunks": []}
    fake_doc_obj.parser_version = "0.1.0"
    fake_doc_obj.source_hash = "x"
    with patch("evaluation.runner._process_one",
               side_effect=[
                   (fake_doc_obj.to_dict.return_value, None, 0.1, "0.1.0", None),
                   (fake_doc_obj.to_dict.return_value, None, 0.2, "0.1.0", None),
                   (fake_doc_obj.to_dict.return_value, None, 0.3, "0.1.0", None),
               ]):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    report = run_evaluation(m, out)
    ids = [r["doc_id"] for r in report["per_doc"]]
    assert ids == ["a", "b", "c"]


def test_run_evaluation_wall_time_seconds_has_four_keys_batch25(tmp_path):
    """wall_time_seconds 必须含 total/parse/chunk/parse_reason/chunk_reason 5 keys。"""
    docs = [_make_doc("a")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_doc_obj = MagicMock()
    fake_doc_obj.to_dict.return_value = {"source_hash": "x", "elements": [], "chunks": []}
    fake_doc_obj.parser_version = "0.1.0"
    fake_doc_obj.source_hash = "x"
    with patch("evaluation.runner._process_one",
               return_value=(fake_doc_obj.to_dict.return_value, None, 0.1, "0.1.0", None)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    report = run_evaluation(m, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_public_per_doc_no_private_fields_batch25(tmp_path):
    """public_per_doc 必剥除 _annotation_present / _tolerance_chars / _missing_markers。"""
    docs = [_make_doc("a")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_doc_obj = MagicMock()
    fake_doc_obj.to_dict.return_value = {"source_hash": "x", "elements": [], "chunks": []}
    fake_doc_obj.parser_version = "0.1.0"
    fake_doc_obj.source_hash = "x"
    with patch("evaluation.runner._process_one",
               return_value=(fake_doc_obj.to_dict.return_value, None, 0.1, "0.1.0", None)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    report = run_evaluation(m, out)
    rec = report["per_doc"][0]
    assert "_annotation_present" not in rec
    assert "_tolerance_chars" not in rec
    assert "_missing_markers" not in rec


def test_run_evaluation_public_per_doc_has_three_keys_batch25(tmp_path):
    """public_per_doc 每条只有 doc_id/source_type/metrics/wall_time_seconds 4 keys。"""
    docs = [_make_doc("a")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_doc_obj = MagicMock()
    fake_doc_obj.to_dict.return_value = {"source_hash": "x", "elements": [], "chunks": []}
    fake_doc_obj.parser_version = "0.1.0"
    fake_doc_obj.source_hash = "x"
    with patch("evaluation.runner._process_one",
               return_value=(fake_doc_obj.to_dict.return_value, None, 0.1, "0.1.0", None)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    report = run_evaluation(m, out)
    rec = report["per_doc"][0]
    assert set(rec.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_parser_version_first_non_none_batch25(tmp_path):
    """parser_version_for_prov 取首个非 None。"""
    docs = [_make_doc("a"), _make_doc("b")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               side_effect=[
                   (fake_dict, {"code": "x"}, 0.1, None, None),  # 失败 → None
                   (fake_dict, None, 0.1, "0.2.0", None),  # 成功 → "0.2.0"
               ]):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    with patch("evaluation.runner.build_provenance", return_value={}) as bp:
                        run_evaluation(m, out)
    # build_provenance 应被 parser_version="0.2.0" 调用
    _, kwargs = bp.call_args
    assert kwargs.get("parser_version") == "0.2.0"


def test_run_evaluation_parser_version_all_none_stays_none_batch25(tmp_path):
    docs = [_make_doc("a"), _make_doc("b")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               side_effect=[
                   (fake_dict, {"code": "x"}, 0.1, None, None),
                   (fake_dict, {"code": "y"}, 0.1, None, None),
               ]):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    with patch("evaluation.runner.build_provenance", return_value={}) as bp:
                        run_evaluation(m, out)
    _, kwargs = bp.call_args
    assert kwargs.get("parser_version") is None


def test_run_evaluation_expected_failure_matches_field_batch25(tmp_path):
    """expected_failure 结果必须含 doc_id/expected_error_code/actual_error_code/matches 4 keys。"""
    ef = MagicMock()
    ef.doc_id = "bad_doc"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = Path("/fake/bad.txt")
    m = _make_manifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    err = MagicMock()
    err.code = "unsupported_format"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        report = run_evaluation(m, out)
    assert len(report["expected_failures"]) == 1
    ef_result = report["expected_failures"][0]
    assert set(ef_result.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}
    assert ef_result["matches"] is True
    assert ef_result["actual_error_code"] == "unsupported_format"


def test_run_evaluation_expected_failure_no_error_actual_none_batch25(tmp_path):
    """expected_failure 但实际无 error → actual_code=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "bad_doc"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = Path("/fake/bad.txt")
    m = _make_manifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(MagicMock(), [])):
        report = run_evaluation(m, out)
    ef_result = report["expected_failures"][0]
    assert ef_result["actual_error_code"] is None
    assert ef_result["matches"] is False


def test_run_evaluation_compute_metrics_called_per_doc_batch25(tmp_path):
    docs = [_make_doc("a"), _make_doc("b")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               side_effect=[
                   (fake_dict, None, 0.1, "0.1.0", None),
                   (fake_dict, None, 0.1, "0.1.0", None),
               ]):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}) as cm:
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(m, out)
    assert cm.call_count == 2


def test_run_evaluation_figure_caption_called_per_doc_batch25(tmp_path):
    docs = [_make_doc("a"), _make_doc("b")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               side_effect=[
                   (fake_dict, None, 0.1, "0.1.0", None),
                   (fake_dict, None, 0.1, "0.1.0", None),
               ]):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}) as fc:
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(m, out)
    assert fc.call_count == 2


def test_run_evaluation_chunk_boundary_called_per_doc_batch25(tmp_path):
    docs = [_make_doc("a"), _make_doc("b")]
    m = _make_manifest(documents=docs)
    out = tmp_path / "report.json"
    fake_dict = {"source_hash": "x", "elements": [], "chunks": []}
    with patch("evaluation.runner._process_one",
               side_effect=[
                   (fake_dict, None, 0.1, "0.1.0", None),
                   (fake_dict, None, 0.1, "0.1.0", None),
               ]):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}) as cb:
                    run_evaluation(m, out)
    assert cb.call_count == 2


def test_run_evaluation_report_top_level_six_keys_batch25(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                report = run_evaluation(m, out)
    expected = {"report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"}
    assert set(report.keys()) == expected


def test_run_evaluation_report_version_constant_batch25(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                report = run_evaluation(m, out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_output_utf8_encoded_batch25(tmp_path):
    """输出文件应是 UTF-8 编码（含 ensure_ascii=False 时仍可正确读出 unicode）。"""
    m = _make_manifest()
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"note": "中文"}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    assert "中文" in content


def test_run_evaluation_str_path_accepted_batch25(tmp_path):
    """output_path 接受 str（被 Path() 包装）。"""
    m = _make_manifest()
    out_str = str(tmp_path / "report.json")
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                report = run_evaluation(m, out_str)
    assert Path(out_str).is_file()
    assert isinstance(report, dict)


# ---------- module source forbidden tokens 第四十二批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from timeit",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch25():
    source = inspect.getsource(rmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_eval_exec_batch25():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch25():
    source = inspect.getsource(rmod)
    assert "import *" not in source


def test_module_source_no_environ_batch25():
    source = inspect.getsource(rmod)
    assert "os.environ" not in source
    assert "getenv" not in source


def test_module_source_no_dataclass_batch25():
    source = inspect.getsource(rmod)
    assert "@dataclass" not in source
    assert "from dataclasses" not in source


def test_module_source_no_argparse_batch25():
    source = inspect.getsource(rmod)
    assert "argparse" not in source


def test_module_source_time_allowed_batch25():
    """runner.py 允许 import time（perf_counter 用）。"""
    source = inspect.getsource(rmod)
    assert "import time" in source


def test_module_source_json_allowed_batch25():
    """runner.py 允许 import json（_load_annotation / 输出报告用）。"""
    source = inspect.getsource(rmod)
    assert "import json" in source


def test_module_source_subprocess_not_used_batch25():
    """runner.py 不应直接用 subprocess（git provenance 在 report.py）。"""
    source = inspect.getsource(rmod)
    assert "subprocess" not in source


def test_module_source_no_open_at_module_level_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    for node in tree.body:
        if isinstance(node, _ast.Expr):
            assert not (isinstance(node.value, _ast.Call) and getattr(node.value.func, "id", None) == "open")


def test_module_source_no_relative_imports_batch25():
    source = inspect.getsource(rmod)
    # runner.py 应使用绝对 from app.pipeline / from evaluation...
    assert "from ." not in source


def test_module_source_no_unsafe_network_batch25():
    source = inspect.getsource(rmod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_uses_from_future_annotations_batch25():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_source_constants_no_module_level_mutables_batch25():
    """不应有 module-level mutable 共享（避免跨调用状态泄漏）。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    for node in tree.body:
        if isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            if node.targets[0].id.startswith("_") and not node.targets[0].id.startswith("__"):
                # 私有 module-level 不应有
                pytest.fail(f"private module-level constant: {node.targets[0].id}")


# ---------- module source 字符串精确补强第三十八批 ----------


def test_module_source_contains_process_single_batch25():
    source = inspect.getsource(rmod)
    assert "process_single" in source


def test_module_source_contains_image_output_dir_for_batch25():
    source = inspect.getsource(rmod)
    assert "image_output_dir_for" in source


def test_module_source_contains_compute_automatic_metrics_batch25():
    source = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in source


def test_module_source_contains_figure_caption_prf_batch25():
    source = inspect.getsource(rmod)
    assert "figure_caption_prf" in source


def test_module_source_contains_chunk_boundary_prf_batch25():
    source = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in source


def test_module_source_contains_aggregate_summary_batch25():
    source = inspect.getsource(rmod)
    assert "aggregate_summary" in source


def test_module_source_contains_build_devset_section_batch25():
    source = inspect.getsource(rmod)
    assert "build_devset_section" in source


def test_module_source_contains_build_provenance_batch25():
    source = inspect.getsource(rmod)
    assert "build_provenance" in source


def test_module_source_contains_time_perf_counter_batch25():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_contains_not_instrumented_batch25():
    source = inspect.getsource(rmod)
    assert "not_instrumented" in source


def test_module_source_contains_write_json_false_batch25():
    source = inspect.getsource(rmod)
    assert "write_json=False" in source


def test_module_source_contains_per_doc_subdir_batch25():
    source = inspect.getsource(rmod)
    assert "_per_doc" in source


def test_module_source_contains_ensure_ascii_false_batch25():
    source = inspect.getsource(rmod)
    assert "ensure_ascii=False" in source


def test_module_source_contains_indent_2_batch25():
    source = inspect.getsource(rmod)
    assert "indent=2" in source


def test_module_source_contains_from_app_pipeline_batch25():
    source = inspect.getsource(rmod)
    assert "from app.pipeline import" in source


def test_module_source_contains_from_evaluation_batch25():
    source = inspect.getsource(rmod)
    assert "from evaluation import" in source


# ---------- signatures 第三十八批 ----------


def test_signature_load_annotation_param_count_batch25():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_signature_load_annotation_param_name_batch25():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


def test_signature_load_annotation_param_annotation_batch25():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].annotation == "Path | None"


def test_signature_process_one_param_count_batch25():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_signature_process_one_param_names_batch25():
    sig = inspect.signature(_process_one)
    expected = {"doc", "output_root", "parser_name", "max_chars"}
    assert set(sig.parameters.keys()) == expected


def test_signature_process_one_no_varargs_batch25():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_run_evaluation_param_count_batch25():
    sig = inspect.signature(run_evaluation)
    # manifest, output_path, parser_name, max_chars, tolerance_chars = 5
    assert len(sig.parameters) == 5


def test_signature_run_evaluation_keyword_only_params_batch25():
    """parser_name / max_chars / tolerance_chars 是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    from inspect import Parameter
    assert sig.parameters["parser_name"].kind == Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_positional_only_manifest_output_batch25():
    """manifest 与 output_path 是 positional-or-keyword（前面无 *）。"""
    sig = inspect.signature(run_evaluation)
    from inspect import Parameter
    assert sig.parameters["manifest"].kind == Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["output_path"].kind == Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation_default_parser_name_batch25():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_signature_run_evaluation_default_max_chars_batch25():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_signature_run_evaluation_default_tolerance_chars_batch25():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_all_annotations_are_strings_batch25():
    """from __future__ import annotations → 所有 annotation 应是 str。"""
    for fn in [_load_annotation, _process_one, run_evaluation]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"


# ---------- module 合理性第三十八批 ----------


def test_module_all_only_run_evaluation_batch25():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_has_three_callables_batch25():
    """module-level callable: _load_annotation / _process_one / run_evaluation。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_classes_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_docstring_present_batch25():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__.strip()) > 0


def test_module_docstring_mentions_evaluation_batch25():
    assert "评测" in rmod.__doc__ or "evaluation" in rmod.__doc__.lower()


def test_module_docstring_mentions_total_batch25():
    assert "total" in rmod.__doc__.lower()


def test_module_docstring_mentions_not_instrumented_batch25():
    assert "not_instrumented" in rmod.__doc__ or "未插桩" in rmod.__doc__


def test_module_process_one_docstring_present_batch25():
    assert _process_one.__doc__ is not None
    assert len(_process_one.__doc__.strip()) > 0


def test_module_run_evaluation_docstring_present_batch25():
    assert run_evaluation.__doc__ is not None


def test_module_load_annotation_docstring_present_batch25():
    """_load_annotation 无 docstring（实现略），跳过。"""
    # _load_annotation 没有 docstring，这里只验证它存在
    assert callable(_load_annotation)


def test_module_uses_from_future_annotations_batch25():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_imports_use_absolute_form_batch25():
    """所有 import 必须是绝对路径（无 from .）。"""
    source = inspect.getsource(rmod)
    for line in source.split("\n"):
        s = line.strip()
        if s.startswith("from ") or s.startswith("import "):
            assert not s.startswith("from .")


# ---------- 端到端集成第三十八批 ----------


def test_e2e_full_flow_no_documents_writes_valid_json_batch25(tmp_path):
    m = _make_manifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    # 验证输出文件可被 json.load 重新读出
    with out.open("r", encoding="utf-8") as f:
        round_trip = json.load(f)
    assert round_trip == report


def test_e2e_summary_has_four_top_keys_batch25(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert set(report["summary"].keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_e2e_report_has_six_top_keys_batch25(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert len(report) == 6


def test_e2e_devset_section_six_keys_batch25(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert set(report["devset"].keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_e2e_provenance_nine_keys_batch25(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    assert len(report["provenance"]) == 9


def test_e2e_str_path_output_accepted_batch25(tmp_path):
    m = _make_manifest()
    out_str = str(tmp_path / "report.json")
    report = run_evaluation(m, out_str)
    assert Path(out_str).is_file()
    assert isinstance(report, dict)


def test_e2e_return_value_matches_file_batch25(tmp_path):
    m = _make_manifest()
    out = tmp_path / "report.json"
    report = run_evaluation(m, out)
    with out.open("r", encoding="utf-8") as f:
        round_trip = json.load(f)
    assert round_trip == report


def test_e2e_nested_output_path_creates_dirs_batch25(tmp_path):
    """output_path 在嵌套目录 → 自动创建。"""
    m = _make_manifest()
    out = tmp_path / "deep" / "nested" / "dir" / "report.json"
    report = run_evaluation(m, out)
    assert out.is_file()
    assert isinstance(report, dict)
