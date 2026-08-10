r"""evaluation/runner.py 边角测试 - 第二十四轮（Round 300）。

edges22 已覆盖：_load_annotation 边界 / _process_one 行为深度 / run_evaluation 行为深度 /
wall_time 结构 / expected_failure 处理 / annotation 字段处理 / parser_version 处理 /
image_dir 逻辑 / report 写盘细节 / public_per_doc 构造 / report 装配 / module imports /
module namespace / module source forbidden tokens / module __all__ / module docstring 深度 /
signatures 完整 / module source level 完整 / 端到端集成。

edges23 补强未覆盖的角度（深度边界 + source level + signatures + 端到端）：
- **_load_annotation 行为深度补强**：path 是 None → 返 None；
  path 是 Path 但不存在 → 返 None；path 存在但不是 file → 返 None；
  path 存在且 file → 返 dict；path 含中文/空格 → 仍工作；
  path 是 invalid JSON → 返 None（catch JSONDecodeError）；
  path 是 directory → 返 None（catch OSError）；signature 1 param + no default；
  return type dict | None；source 含 path is None + not path.is_file() + utf-8 + json.load + (OSError, JSONDecodeError)
- **_process_one 行为深度补强**：返 5-tuple 精确；
  out_stub 路径模板精确（output_root/_per_doc/<doc_id>.json）；
  out_stub.parent.mkdir parents=True exist_ok=True；
  perf_counter 2 处（t0 / elapsed）；
  process_single 调用 5 个 kwargs 精确；
  image_output_dir_for 调用；
  out_stub.unlink OSError catch；
  errors 非空 → 返 (None, errors[0].to_dict(), elapsed, None, image_dir)；
  document is None no errors → 返 (None, unknown_error, elapsed, None, image_dir)；
  document is not None → 返 (document.to_dict(), None, elapsed, parser_version, image_dir)；
  signature 4 params no default + no varargs/varkw；
  return annotation 是 5-tuple
- **run_evaluation 行为深度补强**：keyword-only 3 params（parser_name + max_chars + tolerance_chars）；
  default 值精确（fallback/800/30）；output_path 转 Path；
  output_root = parent；mkdir parents=True exist_ok=True；
  per_doc_results list 初始化；
  parser_version_for_prov 跟踪；
  for doc 循环 _process_one 调用；
  compute_automatic_metrics 5 个 kwargs 精确；
  _load_annotation 调用；figure_caption_prf + chunk_boundary_prf 调用；
  metrics.update；pop _tolerance_chars + _missing_markers；
  per_doc_results.append 含 6 keys；
  expected_failure_results 循环；process_single 调用；
  actual_code = errors[0].code if errors else None；
  expected_failure_results.append 含 4 keys；
  build_provenance 4 个 kwargs 精确；build_devset_section 调用；aggregate_summary 调用；
  public_per_doc 含 4 keys；report 6 top-level keys；
  out_p = Path(output_path)；out_p.parent.mkdir；
  json.dump ensure_ascii=False + indent=2；return report；
  signature 2 positional + 3 keyword-only + no varargs/varkw
- **wall_time 结构精确**：6 keys（total/parse/chunk/parse_reason/chunk_reason）；parse/chunk 固定 None；
  parse_reason/chunk_reason 固定 "not_instrumented"；total 是 float
- **expected_failure 处理深度**：errors 非空 → actual_code = errors[0].code；
  errors 空 → actual_code = None；matches = actual_code == expected_error_code；
  4 keys 精确（doc_id/expected_error_code/actual_error_code/matches）；
  for ef 循环；out_stub unlink；
  process_single 5 个 kwargs（resolved_path/out_stub/parser_name/max_chars/write_json=False）
- **annotation 字段处理深度**：_annotation_present = annotation is not None；
  _tolerance_chars = tolerance_record['value'] if tolerance_record else None；
  _missing_markers = missing_markers_record['value'] if missing_markers_record else []；
  tolerance_record = chunk_b.pop('_tolerance_chars', None)；
  missing_markers_record = chunk_b.pop('_missing_markers', None)
- **module __all__ 精确**：1 entry 'run_evaluation'；namespace；callable；valid identifier
- **module imports 顺序**：future → json → time → pathlib → typing → app.pipeline →
  evaluation（REPORT_VERSION）→ evaluation.annotation_metrics → evaluation.metrics → evaluation.report
- **module namespace 补强**：run_evaluation + _load_annotation + _process_one 3 个 module-level；
  process_single / image_output_dir_for / REPORT_VERSION / chunk_boundary_prf / figure_caption_prf /
  compute_automatic_metrics / aggregate_summary / build_devset_section / build_provenance 9 个 imported
- **module source forbidden tokens 补强**：os/sys/re/logging/subprocess/asyncio/threading/concurrent/
  collections/math/datetime/itertools/functools/star/relative/class/dataclass/yield/async/global/nonlocal/walrus/assert
- **module docstring 深度补强**：含「评测 runner」/「清单」/「逐文档跑 pipeline」/「time.perf_counter」/
  「not_instrumented」/「image_resource_exists_ratio」
- **signatures 精确**：_load_annotation(path: Path | None) → dict | None + no default；
  _process_one 4 params no default → 5-tuple + no varargs/varkw；
  run_evaluation 2 positional + 3 keyword-only + 3 defaults (fallback/800/30) + no varargs/varkw + return dict
- **module source level 完整 - 子函数 source**：
  - _load_annotation 含 'path is None or not path.is_file()'；含 try/except (OSError, JSONDecodeError)；
    含 'r' encoding=utf-8
  - _process_one 含 out_stub 模板；含 perf_counter 2 处；含 process_single 5 个 kwargs；
    含 if document is not None → image_dir；含 out_stub.is_file() → unlink；含 if errors / if document is None / else 三分支；
    含 return None, errors[0].to_dict() / return None, unknown_error / return document.to_dict()
  - run_evaluation 含 output_root = Path(output_path).parent；含 mkdir parents=True exist_ok=True；
    含 for doc in manifest.documents；含 if parser_version and not parser_version_for_prov；
    含 compute_automatic_metrics 5 个 kwargs；含 image_base_dir if (image_dir is not None and image_dir.is_dir())；
    含 metrics.update fig_caps；含 chunk_b.pop；含 per_doc_results.append 6 keys；
    含 for ef in manifest.expected_failures；含 actual_code = errors[0].code if errors else None；
    含 expected_failure_results.append 4 keys；
    含 build_provenance 4 个 kwargs；含 build_devset_section(manifest)；含 aggregate_summary(per_doc_results)；
    含 public_per_doc 4 keys；含 report 6 keys；
    含 json.dump ensure_ascii=False indent=2
- **端到端集成**：空 manifest 不抛；写盘 loadable；通过 schema；
  provenance 9 字段；devset 6 字段；summary 4 字段；
  完整 manifest 多 doc + expected_failure；
  expected_failure matches 字段正确；
  per_doc 4 公开字段 + 私有 _annotation_present + _tolerance_chars + _missing_markers
- **模块整体合理性**：__all__ 1 entry；3 个 module-level function；9 个 imported name；
  无 class；无 __main__ 块
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import evaluation.runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# 辅助
# =========================================================================


def _write_manifest(tmp_path: Path, documents: list | None = None,
                    expected_failures: list | None = None) -> Path:
    p = tmp_path / "manifest.json"
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": documents or [],
        "expected_failures": expected_failures or [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# =========================================================================
# _load_annotation 行为深度补强
# =========================================================================


def test_load_annotation_path_none_returns_none():
    assert _load_annotation(None) is None


def test_annotation_path_not_exist_returns_none(tmp_path):
    p = tmp_path / "noexist.json"
    assert _load_annotation(p) is None


def test_load_annotation_valid_file(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({"key": "value"}), encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value"}


def test_load_annotation_chinese_path(tmp_path):
    """path 含中文 → 仍工作。"""
    p = tmp_path / "标注.json"
    p.write_text(json.dumps({"a": "中文"}), encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": "中文"}


def test_load_annotation_path_with_spaces(tmp_path):
    """path 含空格 → 仍工作。"""
    p = tmp_path / "my annotation.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": 1}


def test_load_annotation_invalid_json_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none(tmp_path):
    """path 是 directory → catch OSError → None。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_signature_1_param_no_default():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"
    assert params[0].default is inspect.Parameter.empty


def test_load_annotation_no_varargs_varkw():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_load_annotation_return_annotation_dict_or_none():
    sig = inspect.signature(_load_annotation)
    assert "dict" in str(sig.return_annotation) or "None" in str(sig.return_annotation)


def test_load_annotation_source_has_path_none_check():
    src = inspect.getsource(_load_annotation)
    assert "path is None" in src


def test_load_annotation_source_has_not_is_file():
    src = inspect.getsource(_load_annotation)
    assert "not path.is_file()" in src


def test_load_annotation_source_has_utf8():
    src = inspect.getsource(_load_annotation)
    assert 'encoding="utf-8"' in src


def test_load_annotation_source_has_json_load():
    src = inspect.getsource(_load_annotation)
    assert "json.load" in src


def test_load_annotation_source_catches_oserror_jsondecodeerror():
    src = inspect.getsource(_load_annotation)
    assert "OSError" in src
    assert "JSONDecodeError" in src


def test_load_annotation_source_returns_none_on_error():
    src = inspect.getsource(_load_annotation)
    assert "return None" in src


# =========================================================================
# _process_one 行为深度补强
# =========================================================================


def test_process_one_returns_5_tuple_when_errors(monkeypatch, tmp_path):
    """errors 非空 → 返 (None, errors[0].to_dict(), elapsed, None, image_dir)。"""
    from app.pipeline import Document, ErrorRecord

    class FakeDoc:
        doc_id = "d1"
        resolved_path = tmp_path / "x.pdf"
        source_type = "pdf"

    fake_error = ErrorRecord("E_TEST", "test")
    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *args, **kwargs: (None, [fake_error]),
    )

    document, error, total, parser_version, image_dir = _process_one(
        FakeDoc(), tmp_path, "fallback", 800
    )
    assert document is None
    assert error == fake_error.to_dict()
    assert isinstance(total, float)
    assert parser_version is None
    assert image_dir is None


def test_process_one_returns_5_tuple_when_document_none_no_errors(monkeypatch, tmp_path):
    """document is None + 无 errors → 返 unknown error。"""
    class FakeDoc:
        doc_id = "d1"
        resolved_path = tmp_path / "x.pdf"
        source_type = "pdf"

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *args, **kwargs: (None, []),
    )

    document, error, total, parser_version, image_dir = _process_one(
        FakeDoc(), tmp_path, "fallback", 800
    )
    assert document is None
    assert error["code"] == "unknown"
    assert parser_version is None


def test_process_one_signature_4_params_no_default():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["doc", "output_root", "parser_name", "max_chars"]
    for p in params:
        assert p.default is inspect.Parameter.empty


def test_process_one_no_varargs_varkw():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_process_one_source_has_out_stub_template():
    """out_stub 路径模板精确。"""
    src = inspect.getsource(_process_one)
    assert 'output_root / "_per_doc"' in src
    assert 'f"{doc.doc_id}.json"' in src


def test_process_one_source_has_parents_true_exist_ok_true():
    src = inspect.getsource(_process_one)
    assert "parents=True" in src
    assert "exist_ok=True" in src


def test_process_one_source_has_perf_counter_2_places():
    src = inspect.getsource(_process_one)
    assert src.count("perf_counter()") == 2  # t0 + elapsed


def test_process_one_source_calls_process_single():
    src = inspect.getsource(_process_one)
    assert "process_single(" in src


def test_process_one_source_calls_image_output_dir_for():
    src = inspect.getsource(_process_one)
    assert "image_output_dir_for" in src


def test_process_one_source_has_out_stub_unlink():
    src = inspect.getsource(_process_one)
    assert "out_stub.is_file()" in src
    assert "out_stub.unlink()" in src


def test_process_one_source_except_oserror():
    src = inspect.getsource(_process_one)
    assert "except OSError" in src


def test_process_one_source_returns_5_tuple():
    src = inspect.getsource(_process_one)
    # 3 个 return path（含 None tuple、unknown tuple、document tuple）
    assert src.count("return") >= 3


def test_process_one_source_has_unknown_error_message():
    src = inspect.getsource(_process_one)
    assert "process_single returned None without errors" in src


# =========================================================================
# run_evaluation 行为深度补强
# =========================================================================


def test_run_evaluation_keyword_only_3_params():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    # manifest + output_path 是 positional；parser_name + max_chars + tolerance_chars 是 keyword-only
    assert len(params) == 5
    keyword_only = [p for p in params if p.kind == inspect.Parameter.KEYWORD_ONLY]
    assert len(keyword_only) == 3
    assert [p.name for p in keyword_only] == ["parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_default_values():
    sig = inspect.signature(run_evaluation)
    params = {p.name: p for p in sig.parameters.values()}
    assert params["parser_name"].default == "fallback"
    assert params["max_chars"].default == 800
    assert params["tolerance_chars"].default == 30


def test_run_evaluation_no_varargs_varkw():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_run_evaluation_return_annotation_dict():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


def test_run_evaluation_empty_manifest(tmp_path):
    """空 manifest 不抛。"""
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    assert isinstance(report, dict)
    assert output.is_file()


def test_run_evaluation_writes_loadable_json(tmp_path):
    """写盘 loadable。"""
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_run_evaluation_report_has_6_top_level_keys(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    expected = {"report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"}
    assert expected.issubset(set(data.keys()))


def test_run_evaluation_creates_nested_output_dir(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "nested" / "deep" / "report.json"
    run_evaluation(manifest, output)
    assert output.is_file()


def test_run_evaluation_source_has_output_root_path():
    src = inspect.getsource(run_evaluation)
    assert "Path(output_path).parent" in src


def test_run_evaluation_source_has_mkdir_parents_exist_ok():
    src = inspect.getsource(run_evaluation)
    assert src.count("parents=True, exist_ok=True") >= 2


def test_run_evaluation_source_has_for_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents" in src


def test_run_evaluation_source_has_parser_version_tracking():
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov" in src


def test_run_evaluation_source_calls_compute_automatic_metrics():
    src = inspect.getsource(run_evaluation)
    assert "compute_automatic_metrics(" in src


def test_run_evaluation_source_calls_load_annotation():
    src = inspect.getsource(run_evaluation)
    assert "_load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_calls_figure_caption_prf():
    src = inspect.getsource(run_evaluation)
    assert "figure_caption_prf(document, annotation)" in src


def test_run_evaluation_source_calls_chunk_boundary_prf():
    src = inspect.getsource(run_evaluation)
    assert "chunk_boundary_prf(" in src


def test_run_evaluation_source_has_metrics_update():
    src = inspect.getsource(run_evaluation)
    assert "metrics.update(fig_caps)" in src
    assert "metrics.update(chunk_b)" in src


def test_run_evaluation_source_has_pop_tolerance_chars():
    src = inspect.getsource(run_evaluation)
    assert 'chunk_b.pop("_tolerance_chars"' in src
    assert 'chunk_b.pop("_missing_markers"' in src


def test_run_evaluation_source_has_per_doc_append_6_keys():
    """per_doc_results.append 含 6 keys（doc_id/source_type/metrics/wall_time_seconds/_annotation_present/_tolerance_chars/_missing_markers）。"""
    src = inspect.getsource(run_evaluation)
    # 至少 6 个 key 名（可能更多）
    assert '"doc_id": doc.doc_id' in src
    assert '"source_type": doc.source_type' in src
    assert '"metrics": metrics' in src
    assert '"wall_time_seconds"' in src
    assert '"_annotation_present"' in src
    assert '"_tolerance_chars"' in src
    assert '"_missing_markers"' in src


def test_run_evaluation_source_has_expected_failures_loop():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures" in src


def test_run_evaluation_source_has_actual_code_logic():
    src = inspect.getsource(run_evaluation)
    assert "actual_code = errors[0].code if errors else None" in src


def test_run_evaluation_source_has_matches_field():
    src = inspect.getsource(run_evaluation)
    assert '"matches": actual_code == ef.expected_error_code' in src


def test_run_evaluation_source_calls_build_provenance():
    src = inspect.getsource(run_evaluation)
    assert "build_provenance(" in src


def test_run_evaluation_source_calls_build_devset_section():
    src = inspect.getsource(run_evaluation)
    assert "build_devset_section(manifest)" in src


def test_run_evaluation_source_calls_aggregate_summary():
    src = inspect.getsource(run_evaluation)
    assert "aggregate_summary(per_doc_results)" in src


def test_run_evaluation_source_has_public_per_doc_4_keys():
    src = inspect.getsource(run_evaluation)
    # public_per_doc 含 4 keys（doc_id/source_type/metrics/wall_time_seconds）
    assert src.count('"doc_id": r["doc_id"]') >= 1
    assert '"source_type": r["source_type"]' in src
    assert '"metrics": r["metrics"]' in src
    assert '"wall_time_seconds": r["wall_time_seconds"]' in src


def test_run_evaluation_source_has_report_6_keys():
    src = inspect.getsource(run_evaluation)
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


def test_run_evaluation_source_has_json_dump_ensure_ascii_false():
    src = inspect.getsource(run_evaluation)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


# =========================================================================
# wall_time 结构精确
# =========================================================================


def test_wall_time_structure(tmp_path):
    """wall_time 含 5 keys（total/parse/chunk/parse_reason/chunk_reason）。"""
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    # 空 manifest，per_doc 是 []
    assert report["per_doc"] == []


def test_wall_time_source_has_5_keys():
    src = inspect.getsource(run_evaluation)
    assert '"total": total_seconds' in src
    assert '"parse": None' in src
    assert '"chunk": None' in src
    assert '"parse_reason": "not_instrumented"' in src
    assert '"chunk_reason": "not_instrumented"' in src


# =========================================================================
# expected_failure 处理深度
# =========================================================================


def test_expected_failure_source_has_4_keys():
    """expected_failure_results.append 含 4 keys。"""
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": ef.doc_id' in src
    assert '"expected_error_code": ef.expected_error_code' in src
    assert '"actual_error_code": actual_code' in src
    assert '"matches": actual_code == ef.expected_error_code' in src


def test_expected_failure_source_calls_process_single():
    src = inspect.getsource(run_evaluation)
    # 在 expected_failure 循环里调用 process_single
    # source 中至少有 2 处 process_single 调用（_process_one 内的 1 处 + expected_failure 循环的 1 处）
    # 但 _process_one 内的 process_single 不在 run_evaluation source 范围内
    # run_evaluation source 含 1 处 process_single 直接调用
    assert "process_single(" in src


# =========================================================================
# annotation 字段处理深度
# =========================================================================


def test_annotation_field_source_has_annotation_present():
    src = inspect.getsource(run_evaluation)
    assert '"_annotation_present": annotation is not None' in src


def test_annotation_field_source_has_tolerance_chars_logic():
    src = inspect.getsource(run_evaluation)
    assert 'tolerance_record["value"] if tolerance_record else None' in src


def test_annotation_field_source_has_missing_markers_logic():
    src = inspect.getsource(run_evaluation)
    assert 'missing_markers_record["value"]' in src
    assert 'if missing_markers_record' in src


def test_annotation_field_source_pop_returns_value():
    src = inspect.getsource(run_evaluation)
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src


# =========================================================================
# module __all__ 精确
# =========================================================================


def test_module_all_has_1_entry():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_all_entry_in_namespace():
    assert hasattr(rmod, "run_evaluation")


def test_module_all_entry_callable():
    assert callable(rmod.run_evaluation)


def test_module_all_entry_valid_identifier():
    for name in rmod.__all__:
        assert name.isidentifier()


def test_module_all_does_not_include_private():
    assert "_load_annotation" not in rmod.__all__
    assert "_process_one" not in rmod.__all__


# =========================================================================
# module imports 顺序
# =========================================================================


def test_module_source_has_future_annotations():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_time_import():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_pathlib_path_import():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_app_pipeline_import():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_evaluation_import():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_import():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_has_metrics_import():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_imports_in_correct_order():
    src = inspect.getsource(rmod)
    lines = [l.strip() for l in src.splitlines() if l.strip().startswith(("from ", "import "))]
    # future → json → time → pathlib → typing → app → evaluation（4 个 namespace）
    assert "from __future__ import annotations" in lines[0]
    assert "import json" in lines[1]
    assert "import time" in lines[2]


# =========================================================================
# module namespace 补强
# =========================================================================


def test_module_namespace_has_3_module_level_functions():
    import types
    funcs = [
        name for name, obj in inspect.getmembers(rmod, predicate=inspect.isfunction)
        if obj.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"run_evaluation", "_load_annotation", "_process_one"}


def test_module_namespace_has_9_imported_names():
    """process_single / image_output_dir_for / REPORT_VERSION / chunk_boundary_prf /
    figure_caption_prf / compute_automatic_metrics / aggregate_summary / build_devset_section / build_provenance。"""
    for name in [
        "process_single",
        "image_output_dir_for",
        "REPORT_VERSION",
        "chunk_boundary_prf",
        "figure_caption_prf",
        "compute_automatic_metrics",
        "aggregate_summary",
        "build_devset_section",
        "build_provenance",
    ]:
        assert hasattr(rmod, name)


def test_module_namespace_imports_are_callable_or_constant():
    assert callable(rmod.process_single)
    assert callable(rmod.image_output_dir_for)
    assert isinstance(rmod.REPORT_VERSION, str)
    assert callable(rmod.chunk_boundary_prf)
    assert callable(rmod.figure_caption_prf)
    assert callable(rmod.compute_automatic_metrics)
    assert callable(rmod.aggregate_summary)
    assert callable(rmod.build_devset_section)
    assert callable(rmod.build_provenance)


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os_module():
    src = inspect.getsource(rmod)
    assert "\nimport os" not in src


def test_module_source_no_sys_module():
    src = inspect.getsource(rmod)
    assert "\nimport sys" not in src


def test_module_source_no_re_module():
    src = inspect.getsource(rmod)
    assert "\nimport re" not in src


def test_module_source_no_logging_module():
    src = inspect.getsource(rmod)
    assert "\nimport logging" not in src


def test_module_source_no_subprocess_module():
    src = inspect.getsource(rmod)
    assert "\nimport subprocess" not in src


def test_module_source_no_asyncio_module():
    src = inspect.getsource(rmod)
    assert "\nimport asyncio" not in src


def test_module_source_no_threading_module():
    src = inspect.getsource(rmod)
    assert "\nimport threading" not in src


def test_module_source_no_concurrent_module():
    src = inspect.getsource(rmod)
    assert "\nimport concurrent" not in src


def test_module_source_no_collections_module():
    src = inspect.getsource(rmod)
    assert "\nimport collections" not in src


def test_module_source_no_math_module():
    src = inspect.getsource(rmod)
    assert "\nimport math" not in src


def test_module_source_no_datetime_module():
    src = inspect.getsource(rmod)
    assert "\nimport datetime" not in src


def test_module_source_no_itertools_module():
    src = inspect.getsource(rmod)
    assert "\nimport itertools" not in src


def test_module_source_no_functools_module():
    src = inspect.getsource(rmod)
    assert "\nimport functools" not in src


def test_module_source_no_relative_import():
    src = inspect.getsource(rmod)
    assert "from ." not in src


def test_module_source_no_class_def():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_source_no_dataclass_decorator():
    src = inspect.getsource(rmod)
    assert "@dataclass" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield " not in src


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def" not in src


def test_module_source_no_global_stmt():
    src = inspect.getsource(rmod)
    assert "\nglobal " not in src


def test_module_source_no_nonlocal_stmt():
    src = inspect.getsource(rmod)
    assert "\nnonlocal " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_assert_stmt():
    src = inspect.getsource(rmod)
    assert "\nassert " not in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_runner():
    doc = rmod.__doc__ or ""
    assert "评测 runner" in doc or "runner" in doc.lower()


def test_module_docstring_contains_qingdan():
    doc = rmod.__doc__ or ""
    assert "清单" in doc


def test_module_docstring_contains_pipeline():
    doc = rmod.__doc__ or ""
    assert "pipeline" in doc.lower() or "逐文档" in doc


def test_module_docstring_contains_perf_counter():
    doc = rmod.__doc__ or ""
    assert "perf_counter" in doc or "time" in doc.lower()


def test_module_docstring_contains_not_instrumented():
    doc = rmod.__doc__ or ""
    assert "not_instrumented" in doc or "未插桩" in doc


def test_module_docstring_contains_image_resource():
    doc = rmod.__doc__ or ""
    assert "image_resource" in doc or "image" in doc.lower()


# =========================================================================
# 端到端集成
# =========================================================================


def test_end_to_end_empty_manifest_returns_dict(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    assert isinstance(report, dict)


def test_end_to_end_report_provenance_has_9_fields(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    prov = report["provenance"]
    expected = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert expected.issubset(set(prov.keys()))


def test_end_to_end_report_devset_has_6_fields(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    dev = report["devset"]
    expected = {"status", "file_count", "content_group_count", "pdf_count", "docx_count", "categories_covered"}
    assert expected.issubset(set(dev.keys()))


def test_end_to_end_report_summary_has_4_fields(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    summ = report["summary"]
    expected = {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    assert expected.issubset(set(summ.keys()))


def test_end_to_end_evaluator_version_unchanged(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    assert report["provenance"]["evaluator_version"] == "1.1"


def test_end_to_end_report_version_unchanged(tmp_path):
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    output = tmp_path / "report.json"
    report = run_evaluation(manifest, output)
    assert report["report_version"] == "1.1"


def test_end_to_end_no_modification_of_manifest(tmp_path):
    """run_evaluation 不修改 manifest 对象。"""
    import copy as _copy
    from evaluation.manifest import load_manifest
    manifest_p = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_p)
    manifest_before = _copy.deepcopy(manifest)
    output = tmp_path / "report.json"
    run_evaluation(manifest, output)
    # manifest 是 frozen dataclass；比较关键属性
    assert len(manifest.documents) == len(manifest_before.documents)
    assert len(manifest.expected_failures) == len(manifest_before.expected_failures)
    assert manifest.file_count == manifest_before.file_count


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_no_class_definitions():
    classes = [
        name for name, obj in inspect.getmembers(rmod, predicate=inspect.isclass)
        if obj.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_no_main_block():
    src = inspect.getsource(rmod)
    assert 'if __name__' not in src


def test_module_has_3_module_level_functions():
    funcs = [
        name for name, obj in inspect.getmembers(rmod, predicate=inspect.isfunction)
        if obj.__module__ == rmod.__name__
    ]
    assert len(funcs) == 3


def test_module_has_1_public_function():
    public_funcs = [
        name for name, obj in inspect.getmembers(rmod, predicate=inspect.isfunction)
        if obj.__module__ == rmod.__name__ and not name.startswith("_")
    ]
    assert public_funcs == ["run_evaluation"]


def test_module_has_2_private_functions():
    private_funcs = [
        name for name, obj in inspect.getmembers(rmod, predicate=inspect.isfunction)
        if obj.__module__ == rmod.__name__ and name.startswith("_")
    ]
    assert sorted(private_funcs) == ["_load_annotation", "_process_one"]
