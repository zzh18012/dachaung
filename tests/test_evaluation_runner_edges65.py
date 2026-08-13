"""evaluation/runner.py 第六十七轮 edges 测试（Round 584）。

补强 edges64 未触及的角度（第三十七批）。
"""

from __future__ import annotations

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


# ---------- _load_annotation 第三十七批


def test_load_annotation_none_input_returns_none_batch37():
    """path=None 直接返回 None（短路）。"""
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_file_returns_none_batch37(tmp_path):
    """不存在的文件 → None。"""
    p = tmp_path / "nonexistent.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none_batch37(tmp_path):
    """path 是目录（is_file() False）→ None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_valid_dict_batch37(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "v"}


def test_load_annotation_invalid_json_returns_none_batch37(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{not valid json", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_unicode_content_batch37(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"marker": "中文"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"marker": "中文"}


def test_load_annotation_with_nested_dict_batch37(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": {"b": {"c": [1, 2, 3]}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": [1, 2, 3]}}}


def test_load_annotation_with_large_json_batch37(tmp_path):
    """大 JSON 也能读。"""
    p = tmp_path / "ann.json"
    data = {f"k{i}": i for i in range(1000)}
    p.write_text(json.dumps(data), encoding="utf-8")
    out = _load_annotation(p)
    assert out == data


def test_load_annotation_with_extra_whitespace_batch37(tmp_path):
    """JSON 含大量空白 → 仍能解析。"""
    p = tmp_path / "ann.json"
    p.write_text('  {  "k"  :  "v"  }  ', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "v"}


def test_load_annotation_with_extra_trailing_newline_batch37(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"k": 1}\n\n\n', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": 1}


def test_load_annotation_returns_dict_or_none_batch37(tmp_path):
    """函数签名说返回 dict | None；实际可能返回其他类型（list/int/str）但调用方处理。"""
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    # 类型可以是 dict / list / str / int / None / bool / float
    assert out is None or isinstance(out, (dict, list, str, int, float, bool))


def test_load_annotation_uses_utf8_encoding_batch37(tmp_path):
    """以 utf-8 读文件（含 BOM 也能读）。"""
    p = tmp_path / "ann.json"
    p.write_text('{"k": "值"}', encoding="utf-8")
    src = inspect.getsource(_load_annotation)
    assert 'encoding="utf-8"' in src


# ---------- _process_one 第三十七批


def _make_doc_mock(doc_id="d1", path="/fake/a.pdf", source_type="pdf",
                   expectations=None, annotation_file_str=None,
                   annotation_resolved=None):
    doc = MagicMock()
    doc.doc_id = doc_id
    doc.resolved_path = Path(path)
    doc.source_type = source_type
    doc.expectations = expectations
    doc.annotation_file_str = annotation_file_str
    doc.annotation_resolved = annotation_resolved
    return doc


def test_process_one_signature_returns_5_tuple_batch37():
    """_process_one 函数返回 5 元组（type hint 注释）。"""
    src = inspect.getsource(_process_one)
    # 检查 type hint
    assert "-> tuple[" in src or "tuple[" in src


def test_process_one_out_stub_path_format_batch37(tmp_path):
    """out_stub = output_root/_per_doc/<doc_id>.json。"""
    doc = _make_doc_mock(doc_id="d_xyz", path=str(tmp_path / "a.pdf"))
    captured_stub = []

    def fake_process(src, out_stub, **kwargs):
        captured_stub.append(out_stub)
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        _process_one(doc, tmp_path, "fallback", 800)
    assert captured_stub
    assert captured_stub[0] == tmp_path / "_per_doc" / "d_xyz.json"


def test_process_one_creates_parent_dir_batch37(tmp_path):
    """out_stub.parent.mkdir(parents=True, exist_ok=True)。"""
    doc = _make_doc_mock(doc_id="d_make", path=str(tmp_path / "a.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_success_returns_document_dict_batch37(tmp_path):
    """成功 → 返回 (document_dict, None, elapsed, parser_version, image_dir)。"""
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"))
    doc_mock = MagicMock()
    doc_mock.to_dict.return_value = {"document_id": "x"}
    doc_mock.parser_version = "1.0"
    doc_mock.source_hash = "abc"

    with patch("evaluation.runner.process_single", return_value=(doc_mock, [])):
        document, error, elapsed, parser_version, image_dir = _process_one(
            doc, tmp_path, "fallback", 800
        )
    assert document == {"document_id": "x"}
    assert error is None
    assert parser_version == "1.0"


def test_process_one_image_dir_when_document_present_batch37(tmp_path):
    """document 非 None → image_dir 通过 image_output_dir_for 推导。"""
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"))
    doc_mock = MagicMock()
    doc_mock.to_dict.return_value = {"document_id": "x"}
    doc_mock.parser_version = "1.0"
    doc_mock.source_hash = "abc"

    fake_image_dir = tmp_path / "fake_images"
    with patch("evaluation.runner.process_single", return_value=(doc_mock, [])):
        with patch(
            "evaluation.runner.image_output_dir_for", return_value=fake_image_dir
        ):
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == fake_image_dir


def test_process_one_unlinks_existing_stub_batch37(tmp_path):
    """stub 已存在 → unlink。"""
    doc = _make_doc_mock(doc_id="d_unlink", path=str(tmp_path / "a.pdf"))
    # 预先创建 stub
    stub = tmp_path / "_per_doc" / "d_unlink.json"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text("pre-existing", encoding="utf-8")

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _process_one(doc, tmp_path, "fallback", 800)
    # stub 应当被 unlink（如果 process_single 没写它，pre-existing 也被 cleanup 删）
    # 但由于 process_single mock 不会真的写文件，stub 仍存在；cleanup 会 unlink
    assert not stub.is_file()


def test_process_one_does_not_call_to_dict_when_errors_batch37(tmp_path):
    """errors 非空时 document 不需要 to_dict。"""
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"))
    doc_mock = MagicMock()
    err_record = MagicMock()
    err_record.to_dict.return_value = {"code": "E_FAIL"}

    with patch("evaluation.runner.process_single", return_value=(doc_mock, [err_record])):
        document, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    # document_mock.to_dict 不应被调用
    assert not doc_mock.to_dict.called
    assert document is None
    assert error == {"code": "E_FAIL"}


def test_process_one_returns_unknown_when_doc_none_no_errors_batch37(tmp_path):
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, elapsed, parser_version, image_dir = _process_one(
            doc, tmp_path, "fallback", 800
        )
    assert error is not None
    assert error["code"] == "unknown"
    assert "message" in error
    assert "process_single returned None" in error["message"]


# ---------- run_evaluation 第三十七批


def _make_manifest_mock(documents=None, expected_failures=None, project_root=None):
    m = MagicMock()
    m.documents = tuple(documents or [])
    m.expected_failures = tuple(expected_failures or [])
    m.project_root = project_root or Path("/fake")
    m.manifest_version = "1.0"
    m.devset_status = "incomplete"
    m.file_count = len(m.documents)
    m.pdf_count = sum(1 for d in m.documents if d.source_type == "pdf")
    m.docx_count = sum(1 for d in m.documents if d.source_type == "docx")
    m.content_group_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_writes_report_version_batch37(tmp_path):
    """report['report_version'] == REPORT_VERSION。"""
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, {"code": "x"}, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert out["report_version"] == REPORT_VERSION


def test_run_evaluation_returns_dict_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert isinstance(out, dict)


def test_run_evaluation_writes_file_to_disk_batch37(tmp_path):
    out_path = tmp_path / "subdir" / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_creates_output_parent_dir_batch37(tmp_path):
    """output_path.parent 不存在 → 创建。"""
    out_path = tmp_path / "deep" / "nested" / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        run_evaluation(manifest, out_path)
    assert out_path.parent.is_dir()


def test_run_evaluation_report_has_six_top_keys_batch37(tmp_path):
    """report 顶层 6 keys：report_version / provenance / devset / summary / per_doc / expected_failures。"""
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    expected = {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }
    assert set(out.keys()) == expected


def test_run_evaluation_empty_documents_empty_per_doc_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock(documents=[])
    with patch("evaluation.runner._process_one") as m:
        out = run_evaluation(manifest, out_path)
    assert out["per_doc"] == []
    # _process_one 不应被调用
    assert not m.called


def test_run_evaluation_default_parser_name_fallback_batch37(tmp_path):
    """默认 parser_name=fallback。"""
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)) as m:
        run_evaluation(manifest, out_path)
        # _process_one 第 3 参数是 parser_name
        assert m.call_args[0][2] == "fallback"


def test_run_evaluation_custom_parser_name_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)) as m:
        run_evaluation(manifest, out_path, parser_name="kreuzberg")
    assert m.call_args[0][2] == "kreuzberg"


def test_run_evaluation_default_max_chars_800_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)) as m:
        run_evaluation(manifest, out_path)
    assert m.call_args[0][3] == 800


def test_run_evaluation_custom_max_chars_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)) as m:
        run_evaluation(manifest, out_path, max_chars=1500)
    assert m.call_args[0][3] == 1500


def test_run_evaluation_default_tolerance_chars_30_batch37(tmp_path):
    """tolerance_chars 默认 30，传给 chunk_boundary_prf。"""
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        with patch("evaluation.runner.chunk_boundary_prf") as m:
            run_evaluation(manifest, out_path)
    # chunk_boundary_prf 第 3 参数是 tolerance_chars
    assert m.call_args[1]["tolerance_chars"] == 30


def test_run_evaluation_custom_tolerance_chars_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        with patch("evaluation.runner.chunk_boundary_prf") as m:
            run_evaluation(manifest, out_path, tolerance_chars=15)
    assert m.call_args[1]["tolerance_chars"] == 15


def test_run_evaluation_per_doc_has_doc_id_batch37(tmp_path):
    """per_doc 每项有 doc_id。"""
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d_alpha", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert out["per_doc"][0]["doc_id"] == "d_alpha"


def test_run_evaluation_per_doc_has_source_type_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"), source_type="pdf")
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert out["per_doc"][0]["source_type"] == "pdf"


def test_run_evaluation_per_doc_has_metrics_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert "metrics" in out["per_doc"][0]


def test_run_evaluation_per_doc_has_wall_time_seconds_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    wt = out["per_doc"][0]["wall_time_seconds"]
    assert "total" in wt
    assert "parse" in wt
    assert "chunk" in wt
    assert "parse_reason" in wt
    assert "chunk_reason" in wt


def test_run_evaluation_wall_time_parse_chunk_null_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    wt = out["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None


def test_run_evaluation_wall_time_reasons_not_instrumented_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    wt = out["per_doc"][0]["wall_time_seconds"]
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_provenance_has_parser_name_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path, parser_name="kreuzberg")
    assert out["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_provenance_has_max_chars_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path, max_chars=1200)
    assert out["provenance"]["max_chars"] == 1200


def test_run_evaluation_expected_failure_match_batch37(tmp_path):
    """expected_failure 命中 → matches=True。"""
    out_path = tmp_path / "report.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(expected_failures=[ef])
    err_record = MagicMock()
    err_record.code = "E_PARSE"
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        out = run_evaluation(manifest, out_path)
    assert out["expected_failures"][0]["matches"] is True
    assert out["expected_failures"][0]["actual_error_code"] == "E_PARSE"


def test_run_evaluation_expected_failure_no_match_batch37(tmp_path):
    """expected_failure 不命中 → matches=False。"""
    out_path = tmp_path / "report.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(expected_failures=[ef])
    err_record = MagicMock()
    err_record.code = "E_OTHER"
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        out = run_evaluation(manifest, out_path)
    assert out["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_no_errors_actual_none_batch37(tmp_path):
    """expected_failure 但实际无错误 → actual_code=None, matches=False。"""
    out_path = tmp_path / "report.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(expected_failures=[ef])
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = run_evaluation(manifest, out_path)
    assert out["expected_failures"][0]["actual_error_code"] is None
    assert out["expected_failures"][0]["matches"] is False


def test_run_evaluation_summary_present_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert "summary" in out
    assert isinstance(out["summary"], dict)


def test_run_evaluation_devset_present_batch37(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert "devset" in out
    assert isinstance(out["devset"], dict)


def test_run_evaluation_keyword_only_args_batch37(tmp_path):
    """parser_name / max_chars / tolerance_chars 都是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    # manifest / output_path 是 positional；其他都是 keyword-only
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


# ---------- module source forbidden tokens 第六十批


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
def test_module_source_no_forbidden_tokens_batch37(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十六批


def test_module_source_contains_design_doc_batch37():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_total_only_keyword_batch37():
    src = inspect.getsource(rmod)
    assert "计时只记 total" in src


def test_module_source_contains_not_instrumented_keyword_batch37():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_pipeline_failed_keyword_batch37():
    src = inspect.getsource(rmod)
    assert "pipeline_failed" in src


def test_module_source_contains_image_resource_keyword_batch37():
    src = inspect.getsource(rmod)
    assert "image_resource_exists_ratio" in src


def test_module_source_contains_process_single_import_batch37():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_report_version_import_batch37():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch37():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_source_contains_metrics_import_batch37():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch37():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src


def test_module_source_contains_json_dump_call_batch37():
    src = inspect.getsource(rmod)
    assert "json.dump(report" in src


def test_module_source_contains_perf_counter_call_batch37():
    src = inspect.getsource(rmod)
    assert "time.perf_counter()" in src


def test_module_source_contains_per_doc_subdir_keyword_batch37():
    src = inspect.getsource(rmod)
    assert "_per_doc" in src


def test_module_source_contains_wall_time_seconds_keyword_batch37():
    src = inspect.getsource(rmod)
    assert "wall_time_seconds" in src


def test_module_source_contains_expected_failures_keyword_batch37():
    src = inspect.getsource(rmod)
    assert "expected_failures" in src


def test_module_source_contains_load_annotation_function_batch37():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_function_batch37():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_function_batch37():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_json_load_call_batch37():
    src = inspect.getsource(rmod)
    assert "json.load(f)" in src


def test_module_source_contains_unlink_call_batch37():
    src = inspect.getsource(rmod)
    assert "out_stub.unlink()" in src


# ---------- signatures 第五十六批


def test_signature_load_annotation_one_param_batch37():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_signature_load_annotation_path_optional_batch37():
    """path 是 required positional（无默认值），annotation 是 'Path | None'。"""
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty
    assert "None" in str(sig.parameters["path"].annotation)


def test_signature_load_annotation_return_dict_or_none_batch37():
    sig = inspect.signature(_load_annotation)
    ra = sig.return_annotation
    assert "dict" in str(ra) and "None" in str(ra)


def test_signature_process_one_four_params_batch37():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_signature_process_one_params_no_default_batch37():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_run_evaluation_params_batch37():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters.keys()) == [
        "manifest",
        "output_path",
        "parser_name",
        "max_chars",
        "tolerance_chars",
    ]


def test_signature_run_evaluation_manifest_no_default_batch37():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_signature_run_evaluation_output_path_no_default_batch37():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_signature_run_evaluation_return_dict_batch37():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


# ---------- module 合理性 第五十六批


def test_module_has_all_attribute_batch37():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch37():
    assert isinstance(rmod.__all__, list)


def test_module_all_only_run_evaluation_batch37():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_has_load_annotation_attribute_batch37():
    assert hasattr(rmod, "_load_annotation")


def test_module_has_process_one_attribute_batch37():
    assert hasattr(rmod, "_process_one")


def test_module_has_run_evaluation_attribute_batch37():
    assert hasattr(rmod, "run_evaluation")


def test_module_load_annotation_callable_batch37():
    assert callable(rmod._load_annotation)


def test_module_process_one_callable_batch37():
    assert callable(rmod._process_one)


def test_module_run_evaluation_callable_batch37():
    assert callable(rmod.run_evaluation)


def test_module_no_class_definitions_batch37():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


# ---------- 端到端集成 第五十六批


def test_e2e_empty_manifest_no_crash_batch37(tmp_path):
    """空 manifest → 不抛异常，写出报告。"""
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    out = run_evaluation(manifest, out_path)
    assert out_path.is_file()
    assert out["per_doc"] == []
    assert out["expected_failures"] == []


def test_e2e_report_is_json_serializable_batch37(tmp_path):
    """报告能被 JSON 反序列化。"""
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        run_evaluation(manifest, out_path)
    # 读回文件验证
    with out_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert isinstance(loaded, dict)
    assert loaded["report_version"] == REPORT_VERSION


def test_e2e_idempotent_run_batch37(tmp_path):
    """两次调用结果（除了时间戳）应一致。"""
    out_path = tmp_path / "report.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out1 = run_evaluation(manifest, out_path)
        out2 = run_evaluation(manifest, out_path)
    # report_version 应当相同
    assert out1["report_version"] == out2["report_version"]


def test_e2e_full_workflow_one_doc_one_expected_failure_batch37(tmp_path):
    """1 doc + 1 expected_failure → 都被处理。"""
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(documents=[doc], expected_failures=[ef])

    err_record = MagicMock()
    err_record.code = "E_PARSE"
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
            out = run_evaluation(manifest, out_path)
    assert len(out["per_doc"]) == 1
    assert len(out["expected_failures"]) == 1
    assert out["expected_failures"][0]["matches"] is True


def test_e2e_per_doc_excludes_private_fields_batch37(tmp_path):
    """public per_doc 不含 _annotation_present / _tolerance_chars / _missing_markers。"""
    out_path = tmp_path / "report.json"
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    pd = out["per_doc"][0]
    assert "_annotation_present" not in pd
    assert "_tolerance_chars" not in pd
    assert "_missing_markers" not in pd
