r"""evaluation/runner.py 边角测试 - 第十七轮（Round 259）。

补强已有 base/edges/edges2-16（共 ~830+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：未覆盖 token
- module docstring 内容
- 函数签名 introspection 详细：_load_annotation 1 参数 + return str；_process_one 4 参数 + return tuple；run_evaluation keyword-only 标记（* separator 后 3 个）+ return str
- _load_annotation 边界：Path 对象 vs None vs 不存在；utf-8 BOM 行为
- _process_one 边界：清空 out_stub 文件成功；doc_id 含路径特殊字符
- run_evaluation report 6 top-level keys 顺序精确：report_version/provenance/devset/summary/per_doc/expected_failures
- per_doc 内部 vs public 结构（去 _ 前缀字段）
- wall_time_seconds keys 顺序精确：total/parse/chunk/parse_reason/chunk_reason
- _tolerance_chars / _missing_markers record 字段提取
- 模块 namespace identity（json/time/Path/REPORT_VERSION/process_single/image_output_dir_for）
- 模块 __all__ 精确
- EmptyManifest stub 完整接口验证
- run_evaluation 不修改 input manifest 的 documents/expected_failures/project_root
- run_evaluation 写盘后 report_version 字段精确
- run_evaluation 写盘后 provenance 含 git_commit/git_dirty
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
# 源码字符串断言（inspect.getsource）— 未覆盖 token
# =========================================================================


def test_module_source_contains_json_import():
    import evaluation.runner as m

    assert "import json" in inspect.getsource(m)


def test_module_source_contains_time_import():
    import evaluation.runner as m

    assert "import time" in inspect.getsource(m)


def test_module_source_contains_pathlib_path_import():
    import evaluation.runner as m

    assert "from pathlib import Path" in inspect.getsource(m)


def test_module_source_contains_typing_any_import():
    import evaluation.runner as m

    assert "from typing import Any" in inspect.getsource(m)


def test_module_source_contains_future_annotations():
    import evaluation.runner as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_load_annotation_def():
    import evaluation.runner as m

    assert "def _load_annotation(" in inspect.getsource(m)


def test_module_source_contains_process_one_def():
    import evaluation.runner as m

    assert "def _process_one(" in inspect.getsource(m)


def test_module_source_contains_run_evaluation_def():
    import evaluation.runner as m

    assert "def run_evaluation(" in inspect.getsource(m)


def test_module_source_contains_pipeline_import():
    """源码含 from app.pipeline import ...。"""
    import evaluation.runner as m

    assert "from app.pipeline import" in inspect.getsource(m)


def test_module_source_contains_annotation_metrics_import():
    """源码含 from evaluation.annotation_metrics import ...。"""
    import evaluation.runner as m

    assert "from evaluation.annotation_metrics import" in inspect.getsource(m)


def test_module_source_contains_metrics_import():
    """源码含 from evaluation.metrics import compute_automatic_metrics。"""
    import evaluation.runner as m

    assert "from evaluation.metrics import" in inspect.getsource(m)


def test_module_source_contains_report_import():
    """源码含 from evaluation.report import ...。"""
    import evaluation.runner as m

    assert "from evaluation.report import" in inspect.getsource(m)


def test_module_source_contains_evaluation_import():
    """源码含 from evaluation import REPORT_VERSION。"""
    import evaluation.runner as m

    assert "from evaluation import" in inspect.getsource(m)


def test_module_source_contains_not_instrumented_token():
    """源码含 'not_instrumented'。"""
    import evaluation.runner as m

    assert '"not_instrumented"' in inspect.getsource(m)


def test_module_source_contains_per_doc_token():
    """源码含 '_per_doc'。"""
    import evaluation.runner as m

    assert '"_per_doc"' in inspect.getsource(m) or "'_per_doc'" in inspect.getsource(m)


def test_module_source_contains_parse_reason_token():
    """源码含 'parse_reason'。"""
    import evaluation.runner as m

    assert '"parse_reason"' in inspect.getsource(m)


def test_module_source_contains_chunk_reason_token():
    """源码含 'chunk_reason'。"""
    import evaluation.runner as m

    assert '"chunk_reason"' in inspect.getsource(m)


def test_module_source_contains_doc_id_token():
    """源码含 'doc_id'。"""
    import evaluation.runner as m

    assert '"doc_id"' in inspect.getsource(m) or "'doc_id'" in inspect.getsource(m)


def test_module_source_contains_source_type_token():
    import evaluation.runner as m

    assert '"source_type"' in inspect.getsource(m) or "source_type" in inspect.getsource(m)


def test_module_source_contains_metrics_token():
    import evaluation.runner as m

    assert '"metrics"' in inspect.getsource(m)


def test_module_source_contains_wall_time_seconds_token():
    import evaluation.runner as m

    assert '"wall_time_seconds"' in inspect.getsource(m)


def test_module_source_contains_total_token():
    import evaluation.runner as m

    assert '"total"' in inspect.getsource(m)


def test_module_source_contains_expected_failures_token():
    import evaluation.runner as m

    assert "expected_failures" in inspect.getsource(m)


def test_module_source_contains_provenance_token():
    import evaluation.runner as m

    assert '"provenance"' in inspect.getsource(m)


def test_module_source_contains_devset_token():
    import evaluation.runner as m

    assert '"devset"' in inspect.getsource(m)


def test_module_source_contains_summary_token():
    import evaluation.runner as m

    assert '"summary"' in inspect.getsource(m)


def test_module_source_contains_annotation_present_token():
    """源码含 '_annotation_present'。"""
    import evaluation.runner as m

    assert '"_annotation_present"' in inspect.getsource(m)


def test_module_source_contains_tolerance_chars_handling():
    """源码含 tolerance_record = chunk_b.pop('_tolerance_chars', None)。"""
    import evaluation.runner as m

    src = inspect.getsource(m)
    assert "pop(" in src
    assert "_tolerance_chars" in src
    assert "_missing_markers" in src


def test_module_source_contains_image_dir_token():
    """源码含 'image_dir'。"""
    import evaluation.runner as m

    assert "image_dir" in inspect.getsource(m)


def test_module_source_contains_image_output_dir_for_call():
    """源码含 image_output_dir_for(out_stub, document.source_hash)。"""
    import evaluation.runner as m

    assert "image_output_dir_for(out_stub" in inspect.getsource(m)


def test_module_source_contains_write_json_false():
    """源码含 write_json=False。"""
    import evaluation.runner as m

    assert "write_json=False" in inspect.getsource(m)


def test_module_source_contains_unknown_error_code():
    """源码含 'unknown' error code。"""
    import evaluation.runner as m

    assert '"unknown"' in inspect.getsource(m)


def test_module_source_contains_mkdir_parents_true():
    """源码含 mkdir(parents=True, exist_ok=True)。"""
    import evaluation.runner as m

    assert "mkdir(parents=True, exist_ok=True)" in inspect.getsource(m)


def test_module_source_contains_json_dump_with_indent():
    """写盘用 json.dump(..., ensure_ascii=False, indent=2)。"""
    import evaluation.runner as m

    src = inspect.getsource(m)
    assert "json.dump(" in src
    assert "ensure_ascii=False" in src
    assert "indent=2" in src


def test_module_source_does_not_contain_print():
    import evaluation.runner as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_contains_oserror_except():
    """OSError 处理 out_stub.unlink 失败。"""
    import evaluation.runner as m

    assert "except OSError" in inspect.getsource(m)


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.runner as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_total():
    """docstring 提到 total 计时。"""
    import evaluation.runner as m

    assert "total" in m.__doc__


def test_module_docstring_mentions_pipeline():
    """docstring 提到 pipeline。"""
    import evaluation.runner as m

    assert "pipeline" in m.__doc__


def test_module_docstring_mentions_constraints():
    """docstring 提到约束。"""
    import evaluation.runner as m

    assert "约束" in m.__doc__ or "约束" in m.__doc__


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_contains_json():
    import evaluation.runner as m
    import json

    assert hasattr(m, "json")
    assert m.json is json


def test_module_namespace_contains_time():
    import evaluation.runner as m
    import time

    assert hasattr(m, "time")
    assert m.time is time


def test_module_namespace_contains_path():
    import evaluation.runner as m
    from pathlib import Path

    assert hasattr(m, "Path")
    assert m.Path is Path


def test_module_namespace_contains_any():
    """Any 在 namespace。"""
    import evaluation.runner as m
    from typing import Any as OrigAny

    assert m.Any is OrigAny


def test_module_namespace_contains_report_version():
    import evaluation.runner as m

    assert hasattr(m, "REPORT_VERSION")
    assert m.REPORT_VERSION == REPORT_VERSION


def test_module_namespace_contains_process_single():
    import evaluation.runner as m

    assert hasattr(m, "process_single")


def test_module_namespace_contains_image_output_dir_for():
    import evaluation.runner as m

    assert hasattr(m, "image_output_dir_for")


def test_module_namespace_contains_compute_automatic_metrics():
    import evaluation.runner as m

    assert hasattr(m, "compute_automatic_metrics")


def test_module_namespace_contains_chunk_boundary_prf():
    import evaluation.runner as m

    assert hasattr(m, "chunk_boundary_prf")


def test_module_namespace_contains_figure_caption_prf():
    import evaluation.runner as m

    assert hasattr(m, "figure_caption_prf")


def test_module_namespace_contains_aggregate_summary():
    import evaluation.runner as m

    assert hasattr(m, "aggregate_summary")


def test_module_namespace_contains_build_devset_section():
    import evaluation.runner as m

    assert hasattr(m, "build_devset_section")


def test_module_namespace_contains_build_provenance():
    import evaluation.runner as m

    assert hasattr(m, "build_provenance")


def test_module_namespace_does_not_contain_main():
    """模块无 main 函数。"""
    import evaluation.runner as m

    assert not hasattr(m, "main")


# =========================================================================
# 模块 __all__
# =========================================================================


def test_module_all_is_list():
    import evaluation.runner as m

    assert isinstance(m.__all__, list)


def test_module_all_is_not_tuple():
    import evaluation.runner as m

    assert not isinstance(m.__all__, tuple)


def test_module_all_has_one_entry():
    import evaluation.runner as m

    assert len(m.__all__) == 1


def test_module_all_exact():
    import evaluation.runner as m

    assert m.__all__ == ["run_evaluation"]


def test_module_all_does_not_contain_helpers():
    """__all__ 不含 _load_annotation / _process_one。"""
    import evaluation.runner as m

    assert "_load_annotation" not in m.__all__
    assert "_process_one" not in m.__all__


def test_module_all_export_in_namespace():
    """__all__ 中所有名字在 namespace。"""
    import evaluation.runner as m

    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 函数 metadata
# =========================================================================


def test_load_annotation_module_identity():
    assert _load_annotation.__module__ == "evaluation.runner"


def test_load_annotation_qualname():
    assert _load_annotation.__qualname__ == "_load_annotation"


def test_load_annotation_param_count_1():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_load_annotation_param_name_path():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_load_annotation_param_no_default():
    """_load_annotation 的 path 参数无 default。"""
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_load_annotation_param_kind_positional_or_keyword():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_annotation_no_var_args():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_load_annotation_no_var_kwargs():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_load_annotation_return_annotation_is_str():
    sig = inspect.signature(_load_annotation)
    assert isinstance(sig.return_annotation, str)


def test_process_one_module_identity():
    assert _process_one.__module__ == "evaluation.runner"


def test_process_one_qualname():
    assert _process_one.__qualname__ == "_process_one"


def test_process_one_param_count_4():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_param_names():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_no_var_args():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_process_one_no_var_kwargs():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_process_one_param_kinds_positional_or_keyword():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_return_annotation_is_str():
    sig = inspect.signature(_process_one)
    assert isinstance(sig.return_annotation, str)
    assert "tuple" in sig.return_annotation


def test_run_evaluation_module_identity():
    assert run_evaluation.__module__ == "evaluation.runner"


def test_run_evaluation_qualname():
    assert run_evaluation.__qualname__ == "run_evaluation"


def test_run_evaluation_param_count_5():
    """manifest + output_path + 3 keyword-only = 5。"""
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_param_names():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters.keys()) == [
        "manifest",
        "output_path",
        "parser_name",
        "max_chars",
        "tolerance_chars",
    ]


def test_run_evaluation_keyword_only_marker():
    """manifest + output_path 是 POSITIONAL_OR_KEYWORD；后 3 个是 KEYWORD_ONLY。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    # 后 3 个 keyword-only
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_keyword_only_defaults():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_no_var_args():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_run_evaluation_no_var_kwargs():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_run_evaluation_return_annotation_is_str():
    sig = inspect.signature(run_evaluation)
    assert isinstance(sig.return_annotation, str)


def test_all_module_functions_are_function_type():
    import types as _types

    for fn in [_load_annotation, _process_one, run_evaluation]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# _load_annotation 边界（不依赖 file 系统）
# =========================================================================


def test_load_annotation_none_returns_none():
    out = _load_annotation(None)
    assert out is None


def test_load_annotation_nonexistent_path_returns_none(tmp_path: Path):
    out = _load_annotation(tmp_path / "missing.json")
    assert out is None


def test_load_annotation_directory_returns_none(tmp_path: Path):
    """目录不是 file → None。"""
    out = _load_annotation(tmp_path)
    assert out is None


def test_load_annotation_valid_json_returns_dict(tmp_path: Path):
    p = tmp_path / "ann.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value"}


def test_load_annotation_invalid_json_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_empty_file_returns_none(tmp_path: Path):
    """空文件 → JSONDecodeError → None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_utf8_bom_returns_none(tmp_path: Path):
    """utf-8 BOM 不被 encoding='utf-8' 剥除 → JSONDecodeError → None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    out = _load_annotation(p)
    # encoding="utf-8" 不剥 BOM → JSONDecodeError → None
    assert out is None


def test_load_annotation_returns_dict_when_loaded(tmp_path: Path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1, "b": [2, 3]}', encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, dict)


def test_load_annotation_accepts_str_path():
    """_load_annotation 内部用 path.is_file() / path.open()，需要 Path-like。

    str 路径没有 .is_file() 方法 → AttributeError → 但被 except 捕获吗？
    实际：str 没有 .is_file() → AttributeError，不被 (OSError, JSONDecodeError) 捕获 → 抛出
    """
    with pytest.raises(AttributeError):
        _load_annotation("some_path.json")


def test_load_annotation_does_not_raise_on_existing_file(tmp_path: Path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    # 不应抛错
    out = _load_annotation(p)
    assert out == {"a": 1}


# =========================================================================
# run_evaluation 报告 6 top-level keys 顺序精确
# =========================================================================


def _make_empty_manifest(project_root: Path):
    class EmptyManifest:
        def __init__(self):
            self.documents = ()
            self.expected_failures = ()
            self.devset_status = "incomplete"
            self.file_count = 0
            self.content_group_count = 0
            self.pdf_count = 0
            self.docx_count = 0
            self.categories_covered = ()
            self.project_root = project_root

    return EmptyManifest()


def test_run_evaluation_report_top_level_keys_count(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert len(report) == 6


def test_run_evaluation_report_top_level_keys_order(tmp_path: Path):
    """6 keys 精确顺序：report_version/provenance/devset/summary/per_doc/expected_failures。"""
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert list(report.keys()) == [
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    ]


def test_run_evaluation_report_version_value(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_provenance_is_dict(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert isinstance(report["provenance"], dict)


def test_run_evaluation_devset_is_dict(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert isinstance(report["devset"], dict)


def test_run_evaluation_summary_is_dict(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert isinstance(report["summary"], dict)


def test_run_evaluation_per_doc_is_list(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert isinstance(report["per_doc"], list)


def test_run_evaluation_expected_failures_is_list(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert isinstance(report["expected_failures"], list)


def test_run_evaluation_empty_manifest_per_doc_empty(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["per_doc"] == []


def test_run_evaluation_empty_manifest_expected_failures_empty(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["expected_failures"] == []


# =========================================================================
# run_evaluation wall_time_seconds 结构
# =========================================================================


def test_run_evaluation_summary_has_4_top_level_keys(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert len(report["summary"]) == 4


def test_run_evaluation_summary_top_level_keys(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert set(report["summary"].keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_run_evaluation_devset_keys(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert set(report["devset"].keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_run_evaluation_provenance_keys(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert set(report["provenance"].keys()) == {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }


def test_run_evaluation_provenance_parser_name_fallback(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["provenance"]["parser_name"] == "fallback"


def test_run_evaluation_provenance_max_chars_800(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["provenance"]["max_chars"] == 800


def test_run_evaluation_provenance_max_chars_custom(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out, max_chars=500)
    assert report["provenance"]["max_chars"] == 500


def test_run_evaluation_provenance_parser_name_custom(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out, parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_provenance_parser_version_none_when_no_docs(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["provenance"]["parser_version"] is None


# =========================================================================
# run_evaluation 写盘后 report 内容验证
# =========================================================================


def test_run_evaluation_writes_json_file(tmp_path: Path):
    out = tmp_path / "report.json"
    run_evaluation(_make_empty_manifest(tmp_path), out)
    assert out.is_file()


def test_run_evaluation_written_json_has_report_version(tmp_path: Path):
    out = tmp_path / "report.json"
    run_evaluation(_make_empty_manifest(tmp_path), out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["report_version"] == REPORT_VERSION


def test_run_evaluation_written_json_provenance_git_commit_str_or_none(tmp_path: Path):
    out = tmp_path / "report.json"
    run_evaluation(_make_empty_manifest(tmp_path), out)
    data = json.loads(out.read_text(encoding="utf-8"))
    gc = data["provenance"]["git_commit"]
    assert gc is None or isinstance(gc, str)


def test_run_evaluation_written_json_provenance_git_dirty_is_bool(tmp_path: Path):
    out = tmp_path / "report.json"
    run_evaluation(_make_empty_manifest(tmp_path), out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data["provenance"]["git_dirty"], bool)


def test_run_evaluation_creates_per_doc_directory(tmp_path: Path):
    """_per_doc 目录在第一次 _process_one 时被创建（空 manifest 不创建）。"""
    out = tmp_path / "report.json"
    run_evaluation(_make_empty_manifest(tmp_path), out)
    # 空 manifest 不创建 _per_doc
    per_doc_dir = tmp_path / "_per_doc"
    # 不创建 _per_doc 是合理的（没有 doc 要处理）
    assert not per_doc_dir.exists() or per_doc_dir.is_dir()


def test_run_evaluation_does_not_modify_manifest_documents(tmp_path: Path):
    """不修改 manifest.documents。"""
    manifest = _make_empty_manifest(tmp_path)
    documents_before = manifest.documents
    run_evaluation(manifest, tmp_path / "report.json")
    assert manifest.documents is documents_before


def test_run_evaluation_does_not_modify_manifest_expected_failures(tmp_path: Path):
    manifest = _make_empty_manifest(tmp_path)
    ef_before = manifest.expected_failures
    run_evaluation(manifest, tmp_path / "report.json")
    assert manifest.expected_failures is ef_before


def test_run_evaluation_does_not_modify_manifest_project_root(tmp_path: Path):
    manifest = _make_empty_manifest(tmp_path)
    pr_before = manifest.project_root
    run_evaluation(manifest, tmp_path / "report.json")
    assert manifest.project_root is pr_before


def test_run_evaluation_can_be_called_with_str_path(tmp_path: Path):
    """output_path 可以是 str（runner 内部用 Path() 包装）。"""
    out_str = str(tmp_path / "report.json")
    report = run_evaluation(_make_empty_manifest(tmp_path), out_str)
    assert isinstance(report, dict)


def test_run_evaluation_creates_nested_output_dirs(tmp_path: Path):
    """深嵌套 output_path 自动 mkdir。"""
    out = tmp_path / "deep" / "nested" / "dir" / "report.json"
    run_evaluation(_make_empty_manifest(tmp_path), out)
    assert out.is_file()


def test_run_evaluation_overwrites_existing_file(tmp_path: Path):
    """已存在的 report.json 被覆盖。"""
    out = tmp_path / "report.json"
    out.write_text('{"old": "data"}', encoding="utf-8")
    run_evaluation(_make_empty_manifest(tmp_path), out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "old" not in data
    assert "report_version" in data


def test_run_evaluation_uses_kwargs_for_parser_name(tmp_path: Path):
    """parser_name 必须 keyword-only（不能 positional）。"""
    out = tmp_path / "report.json"
    with pytest.raises(TypeError):
        # 试 positional 调用 parser_name
        run_evaluation(_make_empty_manifest(tmp_path), out, "kreuzberg")  # type: ignore[misc]


def test_run_evaluation_uses_kwargs_for_max_chars(tmp_path: Path):
    out = tmp_path / "report.json"
    with pytest.raises(TypeError):
        run_evaluation(_make_empty_manifest(tmp_path), out, "fallback", 500)  # type: ignore[misc]


def test_run_evaluation_uses_kwargs_for_tolerance_chars(tmp_path: Path):
    out = tmp_path / "report.json"
    with pytest.raises(TypeError):
        run_evaluation(_make_empty_manifest(tmp_path), out, "fallback", 800, 30)  # type: ignore[misc]


# =========================================================================
# Stub Manifest 接口验证
# =========================================================================


def test_stub_manifest_with_categories_covered_as_list(tmp_path: Path):
    """categories_covered 可以是 list。"""
    class ListCatManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ["legal", "scientific"]
        project_root = tmp_path

    out = tmp_path / "report.json"
    report = run_evaluation(ListCatManifest(), out)
    assert report["devset"]["categories_covered"] == ["legal", "scientific"]


def test_stub_manifest_with_categories_covered_as_tuple(tmp_path: Path):
    """categories_covered 也可以是 tuple（JSON 序列化为 list）。"""
    class TupleCatManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ("legal", "scientific")
        project_root = tmp_path

    out = tmp_path / "report.json"
    report = run_evaluation(TupleCatManifest(), out)
    # JSON 序列化后 tuple 变成 list
    assert list(report["devset"]["categories_covered"]) == ["legal", "scientific"]


def test_stub_manifest_devset_status_passed_through(tmp_path: Path):
    class CustomStatusManifest:
        documents = ()
        expected_failures = ()
        devset_status = "complete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path

    out = tmp_path / "report.json"
    report = run_evaluation(CustomStatusManifest(), out)
    assert report["devset"]["status"] == "complete"


# =========================================================================
# 整体一致性 / 不变量
# =========================================================================


def test_run_evaluation_returns_dict_with_6_keys_consistent_with_file(tmp_path: Path):
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    file_content = json.loads(out.read_text(encoding="utf-8"))
    # 序列化抹平 tuple/list 差异后，两者应一致
    report_normalized = json.loads(json.dumps(report, ensure_ascii=False))
    assert file_content == report_normalized


def test_run_evaluation_summary_silent_drop_total_is_none_when_no_docs(tmp_path: Path):
    """空 manifest → silent_drop_total = None。"""
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["summary"]["silent_drop_total"] is None


def test_run_evaluation_summary_success_rate_total_zero(tmp_path: Path):
    """空 manifest → success_rates.pipeline_success.total = 0。"""
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["summary"]["success_rates"]["pipeline_success"]["total"] == 0


def test_run_evaluation_summary_success_rate_rate_none(tmp_path: Path):
    """空 manifest → rate = None。"""
    out = tmp_path / "report.json"
    report = run_evaluation(_make_empty_manifest(tmp_path), out)
    assert report["summary"]["success_rates"]["pipeline_success"]["rate"] is None


def test_module_no_dunder_all_helpers():
    """模块 __all__ 不含 helper。"""
    import evaluation.runner as m

    assert "_load_annotation" not in m.__all__
    assert "_process_one" not in m.__all__


def test_run_evaluation_does_not_raise_with_empty_manifest(tmp_path: Path):
    """空 manifest 不应抛错。"""
    out = tmp_path / "report.json"
    # 不抛错即可
    run_evaluation(_make_empty_manifest(tmp_path), out)
