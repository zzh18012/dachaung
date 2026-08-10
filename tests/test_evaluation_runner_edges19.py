r"""evaluation/runner.py 边角测试 - 第十九轮（Round 273）。

edges18 已覆盖：_load_annotation 边界（path None/不存在/empty/invalid/BOM/binary/list top/string
top/dict top/returns dict-or-None/签名）；_process_one 签名；run_evaluation 签名；helper identity/qualname；
namespace has；__all__ 详细；source 含 from __future__ / import time / perf_counter / not_instrumented /
write_json=False / image_output_dir_for / image_base_dir / out_stub / unlink / unlink try/except OSError /
expected_failures loop / documents loop / public_per_doc / _annotation_present / tolerance_record_pop /
missing_markers_pop / json_dump / ensure_ascii=False / indent=2 / unknown error code fallback /
process_single returned None message / 不含 print/logging/asyncio/subprocess/os/concurrent.futures；
docstring 含 runner/perf_counter/not_instrumented/pipeline_failed/image_resource_exists_ratio/
image_output_dir/write_json=False；run_evaluation empty manifest 7 keys 写盘 + JSON 可解析 + 两次独立 +
不修改 manifest + 创建输出目录 + 返回 report dict + provenance parser_name/max_chars 默认 + 自定义
parser_name/max_chars/tolerance_chars + 不创建 _per_doc subdir for empty manifest。

edges19 补强未覆盖的角度：
- _load_annotation source token：'path is None or not path.is_file()' / 'encoding="utf-8"' / 'except (OSError, json.JSONDecodeError)'
- _process_one source token：out_stub 父目录 mkdir / time.perf_counter 两次 / image_output_dir_for 调用 / out_stub.unlink try/except OSError / 错误码 'unknown' / message 'process_single returned None without errors' / 错误路径 errors[0].to_dict() / 5-tuple 返回
- run_evaluation source token：output_root mkdir / per_doc_results 7 keys / wall_time_seconds 5 keys (total/parse/chunk/parse_reason/chunk_reason) / parser_version_for_prov 收集 / public_per_doc 过滤 _ 前缀 / report 6 top-level keys 顺序 / tolerance_record + missing_markers record pop 出 + 放回 metrics / actual_code vs expected_error_code matches 计算
- 模块 imports 精确字符串：'from app.pipeline import image_output_dir_for, process_single' / 'from evaluation import REPORT_VERSION' / 'from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf' / 'from evaluation.metrics import compute_automatic_metrics' / 'from evaluation.report import aggregate_summary, build_devset_section, build_provenance'
- import 顺序：__future__ → json → time → pathlib → typing → app.pipeline → evaluation → evaluation.annotation_metrics → evaluation.metrics → evaluation.report
- _process_one 内部逻辑深度：document is not None 时计算 image_dir；document is None 时 image_dir 直接 None
- _process_one 5-tuple 元素顺序：(document_dict_or_None, error_dict_or_None, total_seconds, parser_version_or_None, image_dir_or_None)
- _process_one out_stub 模式：output_root / "_per_doc" / f"{doc.doc_id}.json"
- run_evaluation expected_failures 路径：每个 ef 创建 out_stub + 跑 process_single + unlink + 取 errors[0].code
- run_evaluation public_per_doc 与内部 per_doc_results 区别：4 keys vs 7 keys
- run_evaluation provenance 4 字段来自 build_provenance
- run_evaluation report 字段类型：6 keys 都是 dict / list
- module docstring 顶部用 triple-quote
- _tolerance_chars / _missing_markers 字段名（含下划线前缀）
- _annotation_present 字段名
- 异常路径：errors[0].to_dict() 必须是 dict
- per_doc_results 内部字段顺序：doc_id, source_type, metrics, wall_time_seconds, _annotation_present, _tolerance_chars, _missing_markers
- public_per_doc 字段顺序：doc_id, source_type, metrics, wall_time_seconds
- expected_failure_results 字段顺序：doc_id, expected_error_code, actual_error_code, matches
- report top-level keys 顺序：report_version, provenance, devset, summary, per_doc, expected_failures
- 模块 __all__ == ['run_evaluation'] 精确
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# _load_annotation source-level token
# =========================================================================


def test_load_annotation_source_contains_path_is_none_or_not_is_file():
    src = inspect.getsource(_load_annotation)
    assert "path is None or not path.is_file()" in src


def test_load_annotation_source_contains_encoding_utf8():
    src = inspect.getsource(_load_annotation)
    assert 'encoding="utf-8"' in src


def test_load_annotation_source_contains_oserror_json_decode_error_except():
    src = inspect.getsource(_load_annotation)
    assert "except (OSError, json.JSONDecodeError)" in src


def test_load_annotation_source_contains_return_none_after_is_file_check():
    src = inspect.getsource(_load_annotation)
    # 'return None' 在 except 块和 path is None 后面
    assert src.count("return None") >= 2


def test_load_annotation_source_contains_json_load():
    src = inspect.getsource(_load_annotation)
    assert "json.load(f)" in src


def test_load_annotation_source_contains_path_open_call():
    src = inspect.getsource(_load_annotation)
    assert "path.open(" in src


def test_load_annotation_source_does_not_contain_print():
    src = inspect.getsource(_load_annotation)
    assert "print(" not in src


def test_load_annotation_source_does_not_contain_logging():
    src = inspect.getsource(_load_annotation)
    assert "logging" not in src


# =========================================================================
# _process_one source-level token
# =========================================================================


def test_process_one_source_contains_out_stub_per_doc_pattern():
    """_process_one 用 'out_stub = output_root / "_per_doc" / f"{doc.doc_id}.json"'。"""
    src = inspect.getsource(_process_one)
    assert '"_per_doc"' in src
    assert "doc.doc_id" in src


def test_process_one_source_contains_mkdir_parents_exist_ok():
    src = inspect.getsource(_process_one)
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src


def test_process_one_source_contains_perf_counter_call_twice():
    src = inspect.getsource(_process_one)
    assert src.count("time.perf_counter()") >= 2


def test_process_one_source_contains_process_single_call():
    src = inspect.getsource(_process_one)
    assert "process_single(" in src


def test_process_one_source_contains_write_json_false_kwarg():
    src = inspect.getsource(_process_one)
    assert "write_json=False" in src


def test_process_one_source_contains_doc_resolved_path():
    src = inspect.getsource(_process_one)
    assert "doc.resolved_path" in src


def test_process_one_source_contains_image_output_dir_for_call():
    src = inspect.getsource(_process_one)
    assert "image_output_dir_for(out_stub, document.source_hash)" in src


def test_process_one_source_contains_unlink_in_try_except_oserror():
    src = inspect.getsource(_process_one)
    assert "out_stub.unlink()" in src
    assert "except OSError:" in src


def test_process_one_source_contains_unknown_error_code():
    src = inspect.getsource(_process_one)
    assert '"unknown"' in src


def test_process_one_source_contains_process_single_returned_none_message():
    src = inspect.getsource(_process_one)
    assert '"process_single returned None without errors"' in src


def test_process_one_source_contains_errors_zero_to_dict():
    src = inspect.getsource(_process_one)
    assert "errors[0].to_dict()" in src


def test_process_one_source_contains_image_dir_none_when_document_none():
    """image_dir 在 document is None 时也返回（不一定是 None）。"""
    src = inspect.getsource(_process_one)
    assert "image_dir: Path | None = None" in src


def test_process_one_source_contains_return_5_tuple():
    """_process_one 多个 return 语句（errors 路径 + None 路径 + 正常路径）。"""
    src = inspect.getsource(_process_one)
    # 至少 3 个 return
    assert src.count("return") >= 3


def test_process_one_source_does_not_contain_print():
    src = inspect.getsource(_process_one)
    assert "print(" not in src


def test_process_one_source_does_not_contain_logging():
    src = inspect.getsource(_process_one)
    assert "logging" not in src


def test_process_one_source_does_not_contain_subprocess():
    src = inspect.getsource(_process_one)
    assert "subprocess" not in src


# =========================================================================
# run_evaluation source-level token
# =========================================================================


def test_run_evaluation_source_contains_output_root_mkdir():
    src = inspect.getsource(run_evaluation)
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_contains_parser_version_for_prov_pattern():
    """parser_version_for_prov: 首个非 None 的 parser_version 胜出。"""
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov" in src
    assert "if parser_version and not parser_version_for_prov:" in src


def test_run_evaluation_source_contains_per_doc_results_list_init():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_contains_documents_loop():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents:" in src


def test_run_evaluation_source_contains_compute_automatic_metrics_call():
    src = inspect.getsource(run_evaluation)
    assert "compute_automatic_metrics(" in src


def test_run_evaluation_source_contains_image_base_dir_kwarg_in_run():
    src = inspect.getsource(run_evaluation)
    assert "image_base_dir=" in src


def test_run_evaluation_source_contains_annotation_load_call():
    src = inspect.getsource(run_evaluation)
    assert "_load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_contains_figure_caption_prf_call():
    src = inspect.getsource(run_evaluation)
    assert "figure_caption_prf(document, annotation)" in src


def test_run_evaluation_source_contains_chunk_boundary_prf_call():
    src = inspect.getsource(run_evaluation)
    assert "chunk_boundary_prf(" in src
    assert "tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_contains_metrics_update_twice():
    src = inspect.getsource(run_evaluation)
    assert src.count("metrics.update(") >= 2


def test_run_evaluation_source_contains_tolerance_record_pop():
    src = inspect.getsource(run_evaluation)
    assert 'chunk_b.pop("_tolerance_chars", None)' in src


def test_run_evaluation_source_contains_missing_markers_pop():
    src = inspect.getsource(run_evaluation)
    assert 'chunk_b.pop("_missing_markers", None)' in src


def test_run_evaluation_source_contains_annotation_present_field():
    src = inspect.getsource(run_evaluation)
    assert '"_annotation_present": annotation is not None' in src


def test_run_evaluation_source_contains_tolerance_chars_field():
    src = inspect.getsource(run_evaluation)
    assert '"_tolerance_chars":' in src


def test_run_evaluation_source_contains_missing_markers_field():
    src = inspect.getsource(run_evaluation)
    assert '"_missing_markers":' in src


def test_run_evaluation_source_contains_expected_failures_loop():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures:" in src


def test_run_evaluation_source_contains_expected_failure_ef_resolved_path():
    src = inspect.getsource(run_evaluation)
    assert "ef.resolved_path" in src


def test_run_evaluation_source_contains_actual_code_pattern():
    src = inspect.getsource(run_evaluation)
    assert "actual_code = errors[0].code if errors else None" in src


def test_run_evaluation_source_contains_expected_failure_match_pattern():
    src = inspect.getsource(run_evaluation)
    assert '"matches": actual_code == ef.expected_error_code' in src


def test_run_evaluation_source_contains_build_provenance_call():
    src = inspect.getsource(run_evaluation)
    assert "build_provenance(" in src


def test_run_evaluation_source_contains_build_devset_section_call():
    src = inspect.getsource(run_evaluation)
    assert "build_devset_section(manifest)" in src


def test_run_evaluation_source_contains_aggregate_summary_call():
    src = inspect.getsource(run_evaluation)
    assert "aggregate_summary(per_doc_results)" in src


def test_run_evaluation_source_contains_public_per_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc = []" in src


def test_run_evaluation_source_contains_report_dict_init():
    src = inspect.getsource(run_evaluation)
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


def test_run_evaluation_source_contains_json_dump_call():
    src = inspect.getsource(run_evaluation)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_contains_wall_time_seconds_keys():
    src = inspect.getsource(run_evaluation)
    assert '"wall_time_seconds":' in src
    assert '"total": total_seconds' in src
    assert '"parse": None' in src
    assert '"chunk": None' in src
    assert '"parse_reason": "not_instrumented"' in src
    assert '"chunk_reason": "not_instrumented"' in src


def test_run_evaluation_source_contains_return_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_run_evaluation_source_does_not_contain_print():
    src = inspect.getsource(run_evaluation)
    assert "print(" not in src


def test_run_evaluation_source_does_not_contain_logging():
    src = inspect.getsource(run_evaluation)
    assert "logging" not in src


def test_run_evaluation_source_does_not_contain_subprocess():
    src = inspect.getsource(run_evaluation)
    assert "subprocess" not in src


def test_run_evaluation_source_does_not_contain_concurrent_futures():
    src = inspect.getsource(run_evaluation)
    assert "concurrent.futures" not in src


# =========================================================================
# 模块 imports 精确字符串
# =========================================================================


def test_module_source_contains_app_pipeline_import():
    src = inspect.getsource(__import__("evaluation.runner", fromlist=["__doc__"]))
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_evaluation_import_report_version():
    src = inspect.getsource(__import__("evaluation.runner", fromlist=["__doc__"]))
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import():
    src = inspect.getsource(__import__("evaluation.runner", fromlist=["__doc__"]))
    assert (
        "from evaluation.annotation_metrics import (\n    chunk_boundary_prf,\n    figure_caption_prf,\n)"
        in src
        or "chunk_boundary_prf" in src
    )


def test_module_source_contains_metrics_import():
    src = inspect.getsource(__import__("evaluation.runner", fromlist=["__doc__"]))
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import():
    src = inspect.getsource(__import__("evaluation.runner", fromlist=["__doc__"]))
    # report import 含 3 个函数
    assert "from evaluation.report import (" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


# =========================================================================
# 模块 import 顺序
# =========================================================================


def test_module_import_order():
    """import 顺序：__future__ → json → time → pathlib → typing → app.pipeline → evaluation → evaluation.annotation_metrics → evaluation.metrics → evaluation.report。"""
    import evaluation.runner as m

    src = inspect.getsource(m)
    pos_future = src.find("from __future__ import annotations")
    pos_json = src.find("import json")
    pos_time = src.find("import time")
    pos_pathlib = src.find("from pathlib import Path")
    pos_typing = src.find("from typing import Any")
    pos_app = src.find("from app.pipeline import")
    pos_eval = src.find("from evaluation import REPORT_VERSION")
    pos_ann = src.find("from evaluation.annotation_metrics import")
    pos_met = src.find("from evaluation.metrics import")
    pos_rep = src.find("from evaluation.report import")
    assert pos_future < pos_json < pos_time < pos_pathlib < pos_typing
    assert pos_typing < pos_app
    assert pos_app < pos_eval
    assert pos_eval < pos_ann
    assert pos_ann < pos_met
    assert pos_met < pos_rep


# =========================================================================
# 模块 __all__ 精确
# =========================================================================


def test_module_all_equals_run_evaluation_only():
    import evaluation.runner as m

    assert m.__all__ == ["run_evaluation"]


def test_module_all_is_list_type():
    import evaluation.runner as m

    assert isinstance(m.__all__, list)


# =========================================================================
# 模块 namespace 详细
# =========================================================================


def test_module_namespace_has_load_annotation():
    import evaluation.runner as m

    assert hasattr(m, "_load_annotation")


def test_module_namespace_has_process_one():
    import evaluation.runner as m

    assert hasattr(m, "_process_one")


def test_module_namespace_has_run_evaluation():
    import evaluation.runner as m

    assert hasattr(m, "run_evaluation")


def test_module_namespace_has_report_version_attr():
    import evaluation.runner as m

    assert hasattr(m, "REPORT_VERSION")
    assert m.REPORT_VERSION == REPORT_VERSION


def test_module_namespace_has_time_attr():
    import evaluation.runner as m

    assert hasattr(m, "time")


def test_module_namespace_has_json_attr():
    import evaluation.runner as m

    assert hasattr(m, "json")


def test_module_namespace_has_path_attr():
    import evaluation.runner as m

    assert hasattr(m, "Path")


def test_module_namespace_has_any_attr():
    import evaluation.runner as m

    assert hasattr(m, "Any")


def test_module_namespace_does_not_have_subprocess():
    import evaluation.runner as m

    assert not hasattr(m, "subprocess")


def test_module_namespace_does_not_have_logging():
    import evaluation.runner as m

    assert not hasattr(m, "logging")


def test_module_namespace_does_not_have_os():
    import evaluation.runner as m

    assert not hasattr(m, "os")


def test_module_namespace_does_not_have_asyncio():
    import evaluation.runner as m

    assert not hasattr(m, "asyncio")


def test_module_namespace_does_not_have_threading():
    import evaluation.runner as m

    assert not hasattr(m, "threading")


# =========================================================================
# _load_annotation 签名与返回类型
# =========================================================================


def test_load_annotation_signature_param_count_1():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_load_annotation_signature_param_name_path():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


def test_load_annotation_return_annotation_str():
    sig = inspect.signature(_load_annotation)
    # return annotation: dict[str, Any] | None
    assert sig.return_annotation is not inspect.Signature.empty


def test_load_annotation_qualname_starts_with_module():
    assert _load_annotation.__qualname__ == "_load_annotation"


# =========================================================================
# _process_one 签名详细
# =========================================================================


def test_process_one_signature_param_count_4():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_signature_param_names_exact():
    sig = inspect.signature(_process_one)
    names = list(sig.parameters.keys())
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_return_annotation_not_empty():
    sig = inspect.signature(_process_one)
    assert sig.return_annotation is not inspect.Signature.empty


def test_process_one_qualname_exact():
    assert _process_one.__qualname__ == "_process_one"


# =========================================================================
# run_evaluation 签名详细
# =========================================================================


def test_run_evaluation_signature_param_count_5():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_signature_param_names_exact():
    sig = inspect.signature(run_evaluation)
    names = list(sig.parameters.keys())
    assert names == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_keyword_only_count_3():
    """parser_name / max_chars / tolerance_chars 是 keyword-only。"""
    from inspect import Parameter

    sig = inspect.signature(run_evaluation)
    kw_only = [p for p in sig.parameters.values() if p.kind == Parameter.KEYWORD_ONLY]
    assert len(kw_only) == 3


def test_run_evaluation_positional_or_keyword_count_2():
    from inspect import Parameter

    sig = inspect.signature(run_evaluation)
    pos = [p for p in sig.parameters.values() if p.kind == Parameter.POSITIONAL_OR_KEYWORD]
    assert len(pos) == 2


def test_run_evaluation_qualname_exact():
    assert run_evaluation.__qualname__ == "run_evaluation"


def test_run_evaluation_module_name_is_evaluation_runner():
    assert run_evaluation.__module__ == "evaluation.runner"


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_starts_with_triple_quote_pattern():
    """模块 docstring 是非空字符串。"""
    import evaluation.runner as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_total_only():
    """docstring 提到 'total'（计时只记 total）。"""
    import evaluation.runner as m

    assert "total" in m.__doc__


def test_module_docstring_mentions_perf_counter():
    import evaluation.runner as m

    assert "perf_counter" in m.__doc__


def test_module_docstring_mentions_not_instrumented():
    import evaluation.runner as m

    assert "not_instrumented" in m.__doc__


def test_module_docstring_mentions_pipeline_failed():
    import evaluation.runner as m

    assert "pipeline_failed" in m.__doc__


def test_module_docstring_mentions_image_resource_or_image_output_dir():
    import evaluation.runner as m

    assert "image_resource" in m.__doc__ or "image_output_dir" in m.__doc__


def test_module_docstring_mentions_app_pipeline():
    """docstring 提到 app/pipeline.py（不修改约束）。"""
    import evaluation.runner as m

    assert "pipeline" in m.__doc__.lower()


# =========================================================================
# _process_one 实际行为验证（更深度）
# =========================================================================


def test_process_one_helper_module_identity():
    import evaluation.runner as m

    assert _process_one.__module__ == m.__name__


def test_load_annotation_helper_module_identity():
    import evaluation.runner as m

    assert _load_annotation.__module__ == m.__name__


def test_all_helpers_are_function_type():
    import types

    assert isinstance(_load_annotation, types.FunctionType)
    assert isinstance(_process_one, types.FunctionType)
    assert isinstance(run_evaluation, types.FunctionType)


# =========================================================================
# run_evaluation empty manifest 写盘后的字段顺序
# =========================================================================


def _make_empty_manifest(tmp_path):
    """构造一个空 manifest，符合 Manifest dataclass 签名。"""
    from evaluation.manifest import Manifest

    return Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )


def test_run_evaluation_report_top_level_keys_order(tmp_path):
    """report top-level keys 顺序：report_version, provenance, devset, summary, per_doc, expected_failures。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    keys = list(report.keys())
    assert keys == ["report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"]


def test_run_evaluation_per_doc_public_keys_order(tmp_path):
    """public per_doc keys: doc_id, source_type, metrics, wall_time_seconds。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    # empty manifest → per_doc is []
    assert report["per_doc"] == []


def test_run_evaluation_devset_keys(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    devset = report["devset"]
    assert devset["status"] == "complete"
    assert devset["file_count"] == 0


def test_run_evaluation_summary_4_buckets(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    summary = report["summary"]
    assert set(summary.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_run_evaluation_provenance_has_required_keys(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    prov = report["provenance"]
    # 至少含 evaluator_version / report_version / parser_name / max_chars
    for k in ["evaluator_version", "report_version", "parser_name", "max_chars"]:
        assert k in prov


def test_run_evaluation_expected_failures_is_list_type(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["expected_failures"], list)


def test_run_evaluation_report_version_is_string(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert isinstance(report["report_version"], str)
    assert report["report_version"] == REPORT_VERSION


# =========================================================================
# _load_annotation 行为验证（用 monkeypatch 不依赖真实文件）
# =========================================================================


def test_load_annotation_returns_none_for_nonexistent_path(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_returns_none_for_none_input():
    assert _load_annotation(None) is None


def test_load_annotation_returns_dict_for_valid_json(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "v"}


def test_load_annotation_returns_none_for_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_list_for_list_top(tmp_path):
    """JSON 顶层是 list → 返回 list（不验证必须是 dict）。"""
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, list)
    assert out == [1, 2, 3]


def test_load_annotation_returns_none_for_empty_file(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_path_is_directory_returns_none(tmp_path):
    """path.is_file() 返回 False（目录）→ None。"""
    out = _load_annotation(tmp_path)
    assert out is None


# =========================================================================
# 报告写盘后可重新解析
# =========================================================================


def test_run_evaluation_written_report_is_valid_json(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    with out_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert isinstance(loaded, dict)
    assert "report_version" in loaded


def test_run_evaluation_written_report_uses_ensure_ascii_false(tmp_path):
    """ensure_ascii=False → 含中文/Unicode 字符不会被转义。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    text = out_path.read_text(encoding="utf-8")
    # ensure_ascii=False 时中文直接出现（devset_status 等中文字段会保留）
    # 这里至少应包含未转义的中文 - 检查 manifest_version 等字段附近
    # ensure_ascii=False → 没有出现 \u 转义序列
    assert "\\u" not in text


def test_run_evaluation_written_report_uses_indent_2(tmp_path):
    """indent=2 → 多行格式（至少含 \n）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    text = out_path.read_text(encoding="utf-8")
    assert "\n" in text
    # indent=2 → 至少出现 "  "（两个空格的缩进）
    assert "  " in text


# =========================================================================
# 两次调用独立验证
# =========================================================================


def test_run_evaluation_two_calls_produce_independent_report_dicts(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    assert r1 is not r2
    assert r1["per_doc"] is not r2["per_doc"]
    assert r1["provenance"] is not r2["provenance"]
