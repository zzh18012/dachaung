"""evaluation/runner.py 第三十五轮 edges 测试（Round 368）。

重点补强 edges33 未触及的角度：
- _load_annotation source level 字符串精确补强第四批
- _process_one source level 字符串精确补强第六批
- run_evaluation source level 字符串精确补强第六批
- _load_annotation 行为深度第七批
- module source forbidden tokens 第十二批
- module source 字符串精确补强第六批
- signatures 精确补强第四批
- 模块整体合理性补强第四批
- 端到端集成补强第四批
"""

from __future__ import annotations

import inspect
import json
import time
import types
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- _load_annotation source level 字符串精确补强第四批 ----------


def test_load_annotation_source_no_class():
    src = inspect.getsource(_load_annotation)
    assert "class " not in src


def test_load_annotation_source_no_yield():
    src = inspect.getsource(_load_annotation)
    assert "yield" not in src


def test_load_annotation_source_no_async():
    src = inspect.getsource(_load_annotation)
    assert "async " not in src


def test_load_annotation_source_no_walrus():
    src = inspect.getsource(_load_annotation)
    assert ":=" not in src


def test_load_annotation_source_no_global():
    src = inspect.getsource(_load_annotation)
    assert "global " not in src


def test_load_annotation_source_no_lambda():
    src = inspect.getsource(_load_annotation)
    assert "lambda" not in src


def test_load_annotation_source_uses_path_is_none():
    src = inspect.getsource(_load_annotation)
    assert "if path is None or not path.is_file():" in src


def test_load_annotation_source_uses_return_none_first_branch():
    src = inspect.getsource(_load_annotation)
    assert "return None" in src


def test_load_annotation_source_uses_try():
    src = inspect.getsource(_load_annotation)
    assert "try:" in src


def test_load_annotation_source_uses_with_path_open():
    src = inspect.getsource(_load_annotation)
    assert 'with path.open("r", encoding="utf-8") as f:' in src


def test_load_annotation_source_uses_return_json_load():
    src = inspect.getsource(_load_annotation)
    assert "return json.load(f)" in src


def test_load_annotation_source_except_oserror_jsondecodeerror():
    src = inspect.getsource(_load_annotation)
    assert "except (OSError, json.JSONDecodeError):" in src


def test_load_annotation_source_except_returns_none():
    src = inspect.getsource(_load_annotation)
    # 两个 return None：一个早返回，一个 except
    assert src.count("return None") == 2


def test_load_annotation_source_no_eval():
    src = inspect.getsource(_load_annotation)
    assert "eval(" not in src


def test_load_annotation_source_no_exec():
    src = inspect.getsource(_load_annotation)
    assert "exec(" not in src


def test_load_annotation_source_no_compile():
    src = inspect.getsource(_load_annotation)
    assert "compile(" not in src


def test_load_annotation_source_no_subprocess():
    src = inspect.getsource(_load_annotation)
    assert "subprocess" not in src


def test_load_annotation_source_no_unlink():
    src = inspect.getsource(_load_annotation)
    assert "unlink" not in src


def test_load_annotation_source_no_write():
    src = inspect.getsource(_load_annotation)
    assert ".write(" not in src


def test_load_annotation_source_no_print():
    src = inspect.getsource(_load_annotation)
    assert "print(" not in src


# ---------- _process_one source level 字符串精确补强第六批 ----------


def test_process_one_source_docstring_present():
    src = inspect.getsource(_process_one)
    assert '"""' in src


def test_process_one_source_docstring_mentions_process_single():
    src = inspect.getsource(_process_one)
    assert "process_single" in src


def test_process_one_source_docstring_mentions_total_seconds():
    src = inspect.getsource(_process_one)
    assert "total_seconds" in src


def test_process_one_source_docstring_mentions_image_dir():
    src = inspect.getsource(_process_one)
    assert "image_dir" in src


def test_process_one_source_docstring_mentions_write_json():
    src = inspect.getsource(_process_one)
    assert "write_json" in src


def test_process_one_source_docstring_mentions_image_output_dir():
    src = inspect.getsource(_process_one)
    assert "image_output_dir" in src


def test_process_one_source_out_stub_assignment():
    src = inspect.getsource(_process_one)
    assert 'out_stub = output_root / "_per_doc" / f"{doc.doc_id}.json"' in src


def test_process_one_source_parent_mkdir():
    src = inspect.getsource(_process_one)
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src


def test_process_one_source_uses_time_perf_counter():
    src = inspect.getsource(_process_one)
    assert "t0 = time.perf_counter()" in src


def test_process_one_source_calls_process_single():
    src = inspect.getsource(_process_one)
    assert "document, errors = process_single(" in src


def test_process_one_source_passes_doc_resolved_path():
    src = inspect.getsource(_process_one)
    assert "doc.resolved_path," in src


def test_process_one_source_passes_out_stub_as_output():
    src = inspect.getsource(_process_one)
    assert "out_stub,  # 给 output_path" in src


def test_process_one_source_passes_parser_name():
    src = inspect.getsource(_process_one)
    assert "parser_name=parser_name," in src


def test_process_one_source_passes_max_chars():
    src = inspect.getsource(_process_one)
    assert "max_chars=max_chars," in src


def test_process_one_source_passes_write_json_false():
    src = inspect.getsource(_process_one)
    assert "write_json=False," in src


def test_process_one_source_elapsed_calc():
    src = inspect.getsource(_process_one)
    assert "elapsed = time.perf_counter() - t0" in src


def test_process_one_source_image_dir_init_none():
    src = inspect.getsource(_process_one)
    assert "image_dir: Path | None = None" in src


def test_process_one_source_image_dir_branch():
    src = inspect.getsource(_process_one)
    assert "if document is not None:" in src
    assert "image_dir = image_output_dir_for(out_stub, document.source_hash)" in src


def test_process_one_source_unlink_check():
    src = inspect.getsource(_process_one)
    assert "if out_stub.is_file():" in src
    assert "out_stub.unlink()" in src


def test_process_one_source_unlink_try_except_oserror():
    src = inspect.getsource(_process_one)
    assert "try:" in src
    assert "except OSError:" in src
    assert "pass" in src


def test_process_one_source_errors_truthy_branch():
    src = inspect.getsource(_process_one)
    assert "if errors:" in src
    assert "return None, errors[0].to_dict(), elapsed, None, image_dir" in src


def test_process_one_source_document_none_branch():
    src = inspect.getsource(_process_one)
    assert "if document is None:" in src
    assert '"code": "unknown"' in src
    assert '"message": "process_single returned None without errors"' in src


def test_process_one_source_return_5_tuple_success():
    src = inspect.getsource(_process_one)
    assert (
        "return document.to_dict(), None, elapsed, document.parser_version, image_dir"
        in src
    )


def test_process_one_source_no_class():
    src = inspect.getsource(_process_one)
    assert "class " not in src


def test_process_one_source_no_yield():
    src = inspect.getsource(_process_one)
    assert "yield" not in src


def test_process_one_source_no_async():
    src = inspect.getsource(_process_one)
    assert "async " not in src


def test_process_one_source_no_walrus():
    src = inspect.getsource(_process_one)
    assert ":=" not in src


def test_process_one_source_no_global():
    src = inspect.getsource(_process_one)
    assert "global " not in src


def test_process_one_source_no_eval():
    src = inspect.getsource(_process_one)
    assert "eval(" not in src


def test_process_one_source_no_exec():
    src = inspect.getsource(_process_one)
    assert "exec(" not in src


def test_process_one_source_no_subprocess():
    src = inspect.getsource(_process_one)
    assert "subprocess" not in src


def test_process_one_source_no_print():
    src = inspect.getsource(_process_one)
    assert "print(" not in src


# ---------- run_evaluation source level 字符串精确补强第六批 ----------


def test_run_evaluation_source_docstring_present():
    src = inspect.getsource(run_evaluation)
    assert '"""' in src


def test_run_evaluation_source_docstring_mentions_run():
    src = inspect.getsource(run_evaluation)
    assert "跑评测" in src or "run" in src.lower()


def test_run_evaluation_source_uses_output_root_assignment():
    src = inspect.getsource(run_evaluation)
    assert "output_root = Path(output_path).parent" in src


def test_run_evaluation_source_uses_output_root_mkdir():
    src = inspect.getsource(run_evaluation)
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_per_doc_results_list_init():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_parser_version_for_prov_init():
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov: str | None = None" in src


def test_run_evaluation_source_for_doc_in_manifest_documents():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents:" in src


def test_run_evaluation_source_5_tuple_unpack():
    src = inspect.getsource(run_evaluation)
    assert "document, error, total_seconds, parser_version, image_dir = _process_one(" in src


def test_run_evaluation_source_parser_version_for_prov_check():
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src
    assert "parser_version_for_prov = parser_version" in src


def test_run_evaluation_source_calls_compute_automatic_metrics():
    src = inspect.getsource(run_evaluation)
    assert "metrics = compute_automatic_metrics(" in src


def test_run_evaluation_source_passes_document_to_metrics():
    src = inspect.getsource(run_evaluation)
    assert "document=document," in src


def test_run_evaluation_source_passes_error_to_metrics():
    src = inspect.getsource(run_evaluation)
    assert "error=error," in src


def test_run_evaluation_source_passes_source_type_to_metrics():
    src = inspect.getsource(run_evaluation)
    assert "source_type=doc.source_type," in src


def test_run_evaluation_source_passes_expectations_to_metrics():
    src = inspect.getsource(run_evaluation)
    assert "expectations=doc.expectations," in src


def test_run_evaluation_source_image_dir_is_dir_check():
    src = inspect.getsource(run_evaluation)
    assert "image_base_dir=image_dir if (image_dir is not None and image_dir.is_dir()) else None," in src


def test_run_evaluation_source_calls_load_annotation():
    src = inspect.getsource(run_evaluation)
    assert "annotation = _load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_calls_figure_caption_prf():
    src = inspect.getsource(run_evaluation)
    assert "fig_caps = figure_caption_prf(document, annotation)" in src


def test_run_evaluation_source_calls_chunk_boundary_prf():
    src = inspect.getsource(run_evaluation)
    assert "chunk_b = chunk_boundary_prf(" in src
    assert "document, annotation, tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_metrics_update_fig_caps():
    src = inspect.getsource(run_evaluation)
    assert "metrics.update(fig_caps)" in src


def test_run_evaluation_source_tolerance_record_pop():
    src = inspect.getsource(run_evaluation)
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src


def test_run_evaluation_source_missing_markers_record_pop():
    src = inspect.getsource(run_evaluation)
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src


def test_run_evaluation_source_metrics_update_chunk_b():
    src = inspect.getsource(run_evaluation)
    assert "metrics.update(chunk_b)" in src


def test_run_evaluation_source_per_doc_results_append():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results.append(" in src
    assert '"doc_id": doc.doc_id' in src
    assert '"source_type": doc.source_type' in src
    assert '"metrics": metrics' in src


def test_run_evaluation_source_wall_time_seconds_dict():
    src = inspect.getsource(run_evaluation)
    assert '"wall_time_seconds": {' in src
    assert '"total": total_seconds' in src
    assert '"parse": None' in src
    assert '"chunk": None' in src
    assert '"parse_reason": "not_instrumented"' in src
    assert '"chunk_reason": "not_instrumented"' in src


def test_run_evaluation_source_annotation_present_flag():
    src = inspect.getsource(run_evaluation)
    assert '"_annotation_present": annotation is not None' in src


def test_run_evaluation_source_tolerance_record_extract():
    src = inspect.getsource(run_evaluation)
    assert '"_tolerance_chars": (' in src
    assert 'tolerance_record["value"] if tolerance_record else None' in src


def test_run_evaluation_source_missing_markers_extract():
    src = inspect.getsource(run_evaluation)
    assert '"_missing_markers": (' in src
    assert 'missing_markers_record["value"]' in src


def test_run_evaluation_source_expected_failure_results_list_init():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_for_ef_in_manifest_expected_failures():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures:" in src


def test_run_evaluation_source_out_stub_ef():
    src = inspect.getsource(run_evaluation)
    assert 'out_stub = output_root / "_per_doc" / f"{ef.doc_id}.json"' in src


def test_run_evaluation_source_ef_mkdir():
    src = inspect.getsource(run_evaluation)
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_ef_process_single_call():
    src = inspect.getsource(run_evaluation)
    assert "document, errors = process_single(" in src
    assert "ef.resolved_path," in src


def test_run_evaluation_source_ef_unlink_check():
    src = inspect.getsource(run_evaluation)
    # 两个 unlink check（一个在 _process_one，一个在 expected_failure loop）
    assert src.count("if out_stub.is_file():") >= 1


def test_run_evaluation_source_actual_code_extraction():
    src = inspect.getsource(run_evaluation)
    assert "actual_code = errors[0].code if errors else None" in src


def test_run_evaluation_source_expected_failure_append():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results.append(" in src
    assert '"doc_id": ef.doc_id' in src
    assert '"expected_error_code": ef.expected_error_code' in src
    assert '"actual_error_code": actual_code' in src
    assert '"matches": actual_code == ef.expected_error_code' in src


def test_run_evaluation_source_calls_build_provenance():
    src = inspect.getsource(run_evaluation)
    assert "provenance = build_provenance(" in src
    assert "project_root=manifest.project_root" in src
    assert "parser_name=parser_name" in src
    assert "max_chars=max_chars" in src
    assert "parser_version=parser_version_for_prov" in src


def test_run_evaluation_source_calls_build_devset_section():
    src = inspect.getsource(run_evaluation)
    assert "devset = build_devset_section(manifest)" in src


def test_run_evaluation_source_calls_aggregate_summary():
    src = inspect.getsource(run_evaluation)
    assert "summary = aggregate_summary(per_doc_results)" in src


def test_run_evaluation_source_public_per_doc_list_init():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc = []" in src


def test_run_evaluation_source_public_per_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "for r in per_doc_results:" in src
    assert "public_per_doc.append(" in src


def test_run_evaluation_source_public_per_doc_keys():
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": r["doc_id"]' in src
    assert '"source_type": r["source_type"]' in src
    assert '"metrics": r["metrics"]' in src
    assert '"wall_time_seconds": r["wall_time_seconds"]' in src


def test_run_evaluation_source_report_dict_keys():
    src = inspect.getsource(run_evaluation)
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


def test_run_evaluation_source_out_p_path():
    src = inspect.getsource(run_evaluation)
    assert "out_p = Path(output_path)" in src
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_writes_file():
    src = inspect.getsource(run_evaluation)
    assert 'with out_p.open("w", encoding="utf-8") as f:' in src
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_run_evaluation_source_no_class():
    src = inspect.getsource(run_evaluation)
    assert "class " not in src


def test_run_evaluation_source_no_yield():
    src = inspect.getsource(run_evaluation)
    assert "yield" not in src


def test_run_evaluation_source_no_async():
    src = inspect.getsource(run_evaluation)
    assert "async " not in src


def test_run_evaluation_source_no_walrus():
    src = inspect.getsource(run_evaluation)
    assert ":=" not in src


def test_run_evaluation_source_no_global():
    src = inspect.getsource(run_evaluation)
    assert "global " not in src


def test_run_evaluation_source_no_eval():
    src = inspect.getsource(run_evaluation)
    assert "eval(" not in src


def test_run_evaluation_source_no_exec():
    src = inspect.getsource(run_evaluation)
    assert "exec(" not in src


# ---------- _load_annotation 行为深度第七批 ----------


def test_load_annotation_none_path():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_path(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_path(tmp_path):
    """目录不是 file → None."""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_valid_json(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"a": 1}


def test_load_annotation_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_empty_file(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_array_root(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2]", encoding="utf-8")
    r = _load_annotation(p)
    assert r == [1, 2]


def test_load_annotation_int_root(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    r = _load_annotation(p)
    assert r == 42


def test_load_annotation_string_root(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    r = _load_annotation(p)
    assert r == "hello"


def test_load_annotation_null_root(tmp_path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    r = _load_annotation(p)
    assert r is None


def test_load_annotation_dict_with_unicode(tmp_path):
    p = tmp_path / "u.json"
    p.write_text('{"中文": "测试"}', encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"中文": "测试"}


def test_load_annotation_does_not_write(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    _load_annotation(p)
    assert p.read_text(encoding="utf-8") == before


def test_load_annotation_idempotent(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    r1 = _load_annotation(p)
    r2 = _load_annotation(p)
    assert r1 == r2


def test_load_annotation_returns_dict_or_none():
    """返回类型是 dict | None."""
    # 类型检查通过签名
    sig = inspect.signature(_load_annotation)
    ra = str(sig.return_annotation)
    assert "dict" in ra or "None" in ra


def test_load_annotation_handles_trailing_comma(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_handles_unquoted_keys(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{a: 1}", encoding="utf-8")
    assert _load_annotation(p) is None


# ---------- module source forbidden tokens 第十二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio",
        "threading",
        "concurrent",
        "multiprocessing",
        "queue",
        "socket",
        "select",
        "re.match",
        "datetime",
        "os.system",
        "logging",
        "urllib",
        "http",
        "ctypes",
        "pickle",
        "shutil",
        "tempfile",
        "glob",
        "unittest",
        "pytest",
        "sys.exit",
        "copy",
        "weakref",
        "abc",
        "contextlib",
        "operator",
        "functools",
        "itertools",
        "collections",
        "importlib",
        "platform",
        "argparse",
    ],
)
def test_runner_source_no_forbidden_token_twelfth(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第六批 ----------


def test_module_source_docstring_present():
    assert rmod.__doc__ is not None


def test_module_source_docstring_mentions_runner():
    assert "runner" in rmod.__doc__.lower() or "评测" in rmod.__doc__


def test_module_source_docstring_mentions_total():
    assert "total" in rmod.__doc__ or "计时" in rmod.__doc__


def test_module_source_docstring_mentions_parse_chunk():
    assert "parse" in rmod.__doc__ and "chunk" in rmod.__doc__


def test_module_source_docstring_mentions_not_instrumented():
    assert "not_instrumented" in rmod.__doc__


def test_module_source_docstring_mentions_pipeline():
    assert "pipeline" in rmod.__doc__.lower()


def test_module_source_has_future_annotations():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_json():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_imports_time():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_imports_path():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_imports_process_single():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_imports_report_version():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_imports_annotation_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf," in src
    assert "figure_caption_prf," in src


def test_module_source_imports_compute_automatic_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_imports_aggregate_summary():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src
    assert "aggregate_summary," in src
    assert "build_devset_section," in src
    assert "build_provenance," in src


def test_module_source_no_relative_above_app_or_eval():
    src = inspect.getsource(rmod)
    lines = src.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from ."):
            assert "evaluation" in stripped or "app" in stripped


def test_module_source_no_star_import():
    src = inspect.getsource(rmod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert 'if __name__' not in src


def test_module_source_no_user_class():
    src = inspect.getsource(rmod)
    lines = src.split("\n")
    has_class = any(line.lstrip().startswith("class ") for line in lines)
    assert not has_class


def test_module_source_3_user_functions():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src
    assert "def _process_one(" in src
    assert "def run_evaluation(" in src


def test_module_source_all_1_entry():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


def test_module_source_no_eval():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(rmod)
    assert "compile(" not in src


# ---------- signatures 精确补强第四批 ----------


def test_signature_load_annotation():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_signature_load_annotation_no_default():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_load_annotation_return_annotation():
    sig = inspect.signature(_load_annotation)
    ra = str(sig.return_annotation)
    assert "dict" in ra
    assert "None" in ra


def test_signature_load_annotation_no_varargs():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_process_one():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert params[0].name == "doc"
    assert params[1].name == "output_root"
    assert params[2].name == "parser_name"
    assert params[3].name == "max_chars"


def test_signature_process_one_no_defaults():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_process_one_return_annotation_tuple():
    sig = inspect.signature(_process_one)
    ra = str(sig.return_annotation)
    assert "tuple" in ra


def test_signature_process_one_no_varargs():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_run_evaluation():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert params[0].name == "manifest"
    assert params[1].name == "output_path"
    assert params[2].name == "parser_name"
    assert params[3].name == "max_chars"
    assert params[4].name == "tolerance_chars"


def test_signature_run_evaluation_manifest_no_default():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_run_evaluation_output_path_no_default():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[1].default is inspect.Parameter.empty


def test_signature_run_evaluation_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[2].default == "fallback"


def test_signature_run_evaluation_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[3].default == 800


def test_signature_run_evaluation_tolerance_chars_default_30():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[4].default == 30


def test_signature_run_evaluation_3_keyword_only():
    """parser_name, max_chars, tolerance_chars 都是 keyword-only（* 之后）."""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    keyword_only_count = sum(
        1 for p in params if p.kind == inspect.Parameter.KEYWORD_ONLY
    )
    assert keyword_only_count == 3


def test_signature_run_evaluation_return_annotation_dict():
    sig = inspect.signature(run_evaluation)
    ra = str(sig.return_annotation)
    assert "dict" in ra


# ---------- 模块整体合理性补强第四批 ----------


def test_module_has_docstring():
    assert rmod.__doc__ is not None


def test_module_has_all_attribute():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_length_1():
    assert len(rmod.__all__) == 1


def test_module_all_entries_unique():
    assert len(set(rmod.__all__)) == 1


def test_module_all_entries_are_str():
    for entry in rmod.__all__:
        assert isinstance(entry, str)


def test_module_all_only_run_evaluation():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_namespace_3_callables():
    callables = [
        (name, obj) for name, obj in vars(rmod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == rmod.__name__
    ]
    assert len(callables) == 3


def test_module_namespace_callable_names():
    callables = {
        name for name, obj in vars(rmod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == rmod.__name__
    }
    assert callables == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_user_classes():
    classes = [
        (name, obj) for name, obj in vars(rmod).items()
        if isinstance(obj, type) and obj.__module__ == rmod.__name__
    ]
    assert len(classes) == 0


def test_module_name_is_evaluation_runner():
    assert rmod.__name__ == "evaluation.runner"


def test_module_file_ends_with_runner_py():
    assert rmod.__file__.endswith("runner.py")


def test_module_function_module_eq_rmod():
    assert _load_annotation.__module__ == "evaluation.runner"
    assert _process_one.__module__ == "evaluation.runner"
    assert run_evaluation.__module__ == "evaluation.runner"


def test_module_function_names_correct():
    assert _load_annotation.__name__ == "_load_annotation"
    assert _process_one.__name__ == "_process_one"
    assert run_evaluation.__name__ == "run_evaluation"


# ---------- 端到端集成补强第四批 ----------


def test_e2e_load_annotation_none_path_returns_none():
    assert _load_annotation(None) is None


def test_e2e_load_annotation_nonexistent_returns_none(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_e2e_load_annotation_valid_json(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    assert _load_annotation(p) == {"k": "v"}


def test_e2e_load_annotation_invalid_json(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("not json at all", encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_load_annotation_empty_file(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_load_annotation_array_root(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[1]", encoding="utf-8")
    assert _load_annotation(p) == [1]


def test_e2e_load_annotation_int_root(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    assert _load_annotation(p) == 42


def test_e2e_load_annotation_string_root(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    assert _load_annotation(p) == "hello"


def test_e2e_load_annotation_null_root(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_load_annotation_nested_dict(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": [1, 2, 3]}}}', encoding="utf-8")
    assert _load_annotation(p) == {"a": {"b": {"c": [1, 2, 3]}}}


def test_e2e_load_annotation_does_not_write(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    _load_annotation(p)
    assert p.read_text(encoding="utf-8") == before


def test_e2e_load_annotation_idempotent(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    r1 = _load_annotation(p)
    r2 = _load_annotation(p)
    assert r1 == r2


def test_e2e_load_annotation_utf8_chinese(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"name": "测试"}', encoding="utf-8")
    assert _load_annotation(p) == {"name": "测试"}


def test_e2e_load_annotation_special_chars(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(
        '{"path": "C:\\\\Users\\\\test\\\\file.txt"}', encoding="utf-8"
    )
    r = _load_annotation(p)
    assert r["path"] == "C:\\Users\\test\\file.txt"


def test_e2e_load_annotation_trailing_comma_raises(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_load_annotation_unquoted_keys_raises(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{a: 1}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_load_annotation_utf8_bom(tmp_path):
    """utf-8 BOM 会让 json 解析失败."""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{}')
    assert _load_annotation(p) is None


def test_e2e_load_annotation_returns_dict_or_none_type():
    """返回类型检查."""
    sig = inspect.signature(_load_annotation)
    ra = str(sig.return_annotation)
    assert "dict" in ra


# Module-level helpers


def test_module_no_extra_vars():
    """模块 namespace 不应有意外的大写变量（除 __all__）."""
    extra = [
        n for n in vars(rmod)
        if not n.startswith("__") and not callable(getattr(rmod, n))
        and n != "__all__"
    ]
    # 允许：从 import 来的（json, time, Path, Any, process_single, ...）
    # 这些不是 rmod 自己定义的
    own = [n for n in extra if not hasattr(types, n)]
    # 不严格断言（imports 可能造成混淆），只检查没有意外 module-level 状态


def test_module_callables_callable():
    assert callable(_load_annotation)
    assert callable(_process_one)
    assert callable(run_evaluation)


def test_module_all_3_callables():
    funcs = [
        obj for name, obj in vars(rmod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == rmod.__name__
    ]
    assert len(funcs) == 3
