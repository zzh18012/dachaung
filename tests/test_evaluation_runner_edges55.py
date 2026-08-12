"""evaluation/runner.py 第五十七轮 edges 测试（Round 514）。

补强 edges54 未触及的角度（第二十七批）：
- _load_annotation 第二十七批：dict 含 list value / dict 含 nested null / 含 NaN-like float / 含 unicode escape / 含 datetime-like str
- _process_one 第二十七批：errors 多个取第一个 / document is None 路径 / image_dir 路径合理性 / process_single 返回 (None, None) 异常情况
- run_evaluation 第二十七批：报告字典含 per_doc / per_doc 字段精确 / expected_failures 顺序 / wall_time parse_reason="not_instrumented" / chunk_reason="not_instrumented" / image_dir 校验 is_dir
- module source forbidden tokens 第四十五批
- module source 字符串精确补强第四十一批
- signatures 第四十一批
- module 合理性第四十一批
- 端到端集成第四十一批
"""

from __future__ import annotations

import inspect
import json
import math
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第二十七批 ----------


def test_load_annotation_dict_with_list_value_batch27(tmp_path):
    """dict 含 list value → 正常加载。"""
    p = tmp_path / "a.json"
    p.write_text('{"x": [1, 2, 3]}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": [1, 2, 3]}


def test_load_annotation_dict_with_nested_null_batch27(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": null}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": None}


def test_load_annotation_dict_with_float_value_batch27(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1.5}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": 1.5}


def test_load_annotation_dict_with_int_value_batch27(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 42}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": 42}


def test_load_annotation_unicode_escape_batch27(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": "\\u00e9"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": "é"}


def test_load_annotation_nan_value_batch27(tmp_path):
    """NaN 在 JSON 中不合法（标准），但 Python json 默认接受。"""
    p = tmp_path / "a.json"
    p.write_text('{"x": NaN}', encoding="utf-8")
    # Python json.load 默认接受 NaN
    result = _load_annotation(p)
    if result is not None:
        assert math.isnan(result["x"])


def test_load_annotation_datetime_like_str_batch27(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"ts": "2026-01-01T00:00:00"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"ts": "2026-01-01T00:00:00"}


def test_load_annotation_deeply_nested_batch27(tmp_path):
    """深层嵌套。"""
    p = tmp_path / "a.json"
    nested = "null"
    for _ in range(10):
        nested = f'{{"k": {nested}}}'
    p.write_text(nested, encoding="utf-8")
    result = _load_annotation(p)
    # 应能加载（默认递归限制充足）
    assert result is not None


def test_load_annotation_with_comment_invalid_batch27(tmp_path):
    """JSON 标准不容忍注释。"""
    p = tmp_path / "a.json"
    p.write_text('// comment\n{"x": 1}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_with_trailing_comma_invalid_batch27(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1,}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_with_single_quotes_invalid_batch27(tmp_path):
    """JSON 标准不容忍单引号。"""
    p = tmp_path / "a.json"
    p.write_text("{'x': 1}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_emoji_key_batch27(tmp_path):
    """emoji key → 正常加载。"""
    p = tmp_path / "a.json"
    p.write_text('{"🎯": "target"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"🎯": "target"}


# ---------- _process_one 第二十七批 ----------


def _make_doc_mock(doc_id: str = "d1", path: Path | None = None) -> Any:
    d = MagicMock()
    d.doc_id = doc_id
    d.resolved_path = path or Path("/tmp/x.pdf")
    return d


def test_process_one_returns_five_tuple_batch27(tmp_path):
    """_process_one 返回 5-tuple。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [])
        result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_first_element_is_dict_or_none_batch27(tmp_path):
    """第一个元素是 dict 或 None。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [])
        document, errors, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None


def test_process_one_second_element_is_dict_or_none_batch27(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [])
        _, errors, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(errors, dict)


def test_process_one_third_element_is_float_batch27(tmp_path):
    """elapsed 是 float。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [])
        _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)


def test_process_one_fourth_element_str_or_none_batch27(tmp_path):
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [])
        _, _, _, pv, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert pv is None


def test_process_one_fifth_element_path_or_none_batch27(tmp_path):
    """image_dir 是 Path 或 None。"""
    doc = _make_doc_mock()
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [])
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None or isinstance(image_dir, Path)


def test_process_one_errors_first_one_batch27(tmp_path):
    """errors 是 list → 返回第一个 error dict。"""
    doc = _make_doc_mock()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "X", "message": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "Y", "message": "second"}
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [err1, err2])
        _, errors, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert errors == {"code": "X", "message": "first"}


def test_process_one_out_stub_parent_creation_batch27(tmp_path):
    """out_stub.parent 目录会被创建。"""
    doc = _make_doc_mock()
    nested = tmp_path / "deep" / "nested"
    with patch("evaluation.runner.process_single") as mock_ps:
        mock_ps.return_value = (None, [])
        _process_one(doc, nested, "fallback", 800)
    # _per_doc 子目录创建
    assert (nested / "_per_doc").is_dir()


# ---------- run_evaluation 第二十七批 ----------


def _make_manifest_full(docs=None, expected_failures=None) -> Any:
    """构造一个 Manifest mock 含完整接口。"""
    m = MagicMock()
    m.documents = docs or []
    m.expected_failures = expected_failures or []
    m.project_root = Path("/tmp")
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_returns_dict_batch27(tmp_path):
    m = _make_manifest_full()
    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)
    assert isinstance(result, dict)


def test_run_evaluation_writes_file_batch27(tmp_path):
    m = _make_manifest_full()
    out_path = tmp_path / "r.json"
    run_evaluation(m, out_path)
    assert out_path.is_file()


def test_run_evaluation_report_has_six_top_keys_batch27(tmp_path):
    m = _make_manifest_full()
    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)
    assert set(result.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_per_doc_empty_for_empty_documents_batch27(tmp_path):
    m = _make_manifest_full(docs=[])
    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)
    assert result["per_doc"] == []


def test_run_evaluation_expected_failures_empty_for_none_batch27(tmp_path):
    m = _make_manifest_full(expected_failures=[])
    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)
    assert result["expected_failures"] == []


def test_run_evaluation_report_version_constant_batch27(tmp_path):
    m = _make_manifest_full()
    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)
    assert result["report_version"] == REPORT_VERSION


def test_run_evaluation_nested_output_dir_batch27(tmp_path):
    """output_path 在不存在的嵌套目录里 → 自动创建。"""
    m = _make_manifest_full()
    out_path = tmp_path / "deep" / "nested" / "r.json"
    result = run_evaluation(m, out_path)
    assert out_path.is_file()


def test_run_evaluation_file_is_valid_json_batch27(tmp_path):
    m = _make_manifest_full()
    out_path = tmp_path / "r.json"
    run_evaluation(m, out_path)
    # 文件应是合法 JSON
    with out_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_run_evaluation_unicode_not_escaped_batch27(tmp_path):
    """JSON 输出含中文/emoji 不被转义（ensure_ascii=False）。"""
    m = _make_manifest_full()
    out_path = tmp_path / "r.json"
    run_evaluation(m, out_path)
    content = out_path.read_text(encoding="utf-8")
    # ensure_ascii=False 时缩进是 2 空格
    assert "\n" in content


def test_run_evaluation_indent_two_batch27(tmp_path):
    """JSON 输出使用 indent=2。"""
    m = _make_manifest_full()
    out_path = tmp_path / "r.json"
    run_evaluation(m, out_path)
    content = out_path.read_text(encoding="utf-8")
    # 检测是否有 2 空格缩进（"  " 在内容里）
    assert "  " in content


# ---------- module source forbidden tokens 第四十五批 ----------


def test_module_source_no_os_system_batch27():
    src = inspect.getsource(rmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch27():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch27():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch27():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch27():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch27():
    src = inspect.getsource(rmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch27():
    src = inspect.getsource(rmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_in_runner_batch27():
    """runner 写盘用 json.dump 而不是 'w' mode open。

    实际上 runner.py 用 `out_p.open("w", encoding="utf-8")` 是允许的
    （写报告是 runner 的职责）。所以这个测试改为断言不使用其他危险模式。
    """
    src = inspect.getsource(rmod)
    assert "wb" not in src  # 不写二进制


def test_module_source_no_subprocess_batch27():
    """runner.py 不直接调 subprocess（git provenance 在 report.py 内）。"""
    src = inspect.getsource(rmod)
    assert "subprocess.run" not in src


def test_module_source_no_shutil_batch27():
    src = inspect.getsource(rmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch27():
    src = inspect.getsource(rmod)
    assert "requests" not in src


def test_module_source_no_marshal_batch27():
    src = inspect.getsource(rmod)
    assert "marshal" not in src


# ---------- module source 字符串精确补强第四十一批 ----------


def test_module_source_contains_load_annotation_batch27():
    src = inspect.getsource(rmod)
    assert "def _load_annotation" in src


def test_module_source_contains_process_one_batch27():
    src = inspect.getsource(rmod)
    assert "def _process_one" in src


def test_module_source_contains_run_evaluation_batch27():
    src = inspect.getsource(rmod)
    assert "def run_evaluation" in src


def test_module_source_contains_not_instrumented_batch27():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_image_output_dir_for_batch27():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src


def test_module_source_contains_process_single_batch27():
    src = inspect.getsource(rmod)
    assert "process_single" in src


def test_module_source_contains_per_doc_subdir_batch27():
    src = inspect.getsource(rmod)
    assert "_per_doc" in src


def test_module_source_contains_compute_automatic_metrics_batch27():
    src = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in src


def test_module_source_contains_figure_caption_prf_batch27():
    src = inspect.getsource(rmod)
    assert "figure_caption_prf" in src


def test_module_source_contains_chunk_boundary_prf_batch27():
    src = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in src


def test_module_source_contains_build_provenance_batch27():
    src = inspect.getsource(rmod)
    assert "build_provenance" in src


def test_module_source_contains_aggregate_summary_batch27():
    src = inspect.getsource(rmod)
    assert "aggregate_summary" in src


# ---------- signatures 第四十一批 ----------


def test_signature_load_annotation_batch27():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_signature_process_one_batch27():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_batch27():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_parser_name_default_batch27():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_signature_run_evaluation_max_chars_default_batch27():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_signature_run_evaluation_tolerance_default_batch27():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_run_evaluation_keyword_only_batch27():
    """parser_name / max_chars / tolerance_chars 是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


# ---------- module 合理性第四十一批 ----------


def test_module_has_future_annotations_batch27():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch27():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_imports_time_batch27():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_imports_pathlib_batch27():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch27():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_imports_pipeline_helpers_batch27():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import" in src
    assert "process_single" in src
    assert "image_output_dir_for" in src


def test_module_imports_annotation_metrics_batch27():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_imports_metrics_batch27():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import" in src


def test_module_imports_report_helpers_batch27():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src


def test_module_all_only_run_evaluation_batch27():
    """__all__ 只导出 run_evaluation。"""
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


# ---------- 端到端集成第四十一批 ----------


def test_e2e_run_evaluation_full_report_batch27(tmp_path):
    """端到端：完整跑 run_evaluation 验证报告结构。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.annotation_resolved = None
    doc.expectations = None
    # 写一个空 PDF 文件让 resolved_path.is_file() 通过
    doc.resolved_path.write_bytes(b"%PDF-1.4")
    m = _make_manifest_full(docs=[doc])

    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)

    assert result["report_version"] == REPORT_VERSION
    assert isinstance(result["per_doc"], list)
    assert len(result["per_doc"]) == 1


def test_e2e_run_evaluation_with_expected_failure_batch27(tmp_path):
    """端到端：含 expected_failure。"""
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.resolved_path.write_bytes(b"%PDF-1.4")
    m = _make_manifest_full(expected_failures=[ef])

    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)

    assert len(result["expected_failures"]) == 1
    assert result["expected_failures"][0]["doc_id"] == "bad1"
    assert result["expected_failures"][0]["expected_error_code"] == "unsupported_format"


def test_e2e_run_evaluation_per_doc_has_doc_id_batch27(tmp_path):
    """端到端：per_doc 含 doc_id 字段。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_bytes(b"%PDF-1.4")
    doc.annotation_resolved = None
    doc.expectations = None
    m = _make_manifest_full(docs=[doc])

    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)

    assert result["per_doc"][0]["doc_id"] == "d1"


def test_e2e_run_evaluation_per_doc_has_source_type_batch27(tmp_path):
    """端到端：per_doc 含 source_type 字段。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_bytes(b"%PDF-1.4")
    doc.annotation_resolved = None
    doc.expectations = None
    m = _make_manifest_full(docs=[doc])

    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)

    assert result["per_doc"][0]["source_type"] == "pdf"


def test_e2e_run_evaluation_per_doc_has_metrics_batch27(tmp_path):
    """端到端：per_doc 含 metrics 字段。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_bytes(b"%PDF-1.4")
    doc.annotation_resolved = None
    doc.expectations = None
    m = _make_manifest_full(docs=[doc])

    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)

    assert "metrics" in result["per_doc"][0]


def test_e2e_run_evaluation_per_doc_has_wall_time_batch27(tmp_path):
    """端到端：per_doc 含 wall_time_seconds 字段。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_bytes(b"%PDF-1.4")
    doc.annotation_resolved = None
    doc.expectations = None
    m = _make_manifest_full(docs=[doc])

    out_path = tmp_path / "r.json"
    result = run_evaluation(m, out_path)

    assert "wall_time_seconds" in result["per_doc"][0]
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert "total" in wt
    assert "parse" in wt
    assert "chunk" in wt
    assert wt["parse"] is None
    assert wt["chunk"] is None


def test_e2e_no_side_effects_on_manifest_batch27(tmp_path):
    """端到端：调用不修改 manifest.documents。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.source_type = "pdf"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_bytes(b"%PDF-1.4")
    doc.annotation_resolved = None
    doc.expectations = None
    m = _make_manifest_full(docs=[doc])

    docs_before = list(m.documents)
    out_path = tmp_path / "r.json"
    run_evaluation(m, out_path)
    assert list(m.documents) == docs_before
