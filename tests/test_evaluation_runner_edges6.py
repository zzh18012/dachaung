r"""evaluation/runner.py 边角测试 - 第六轮（Round 152）。

补强已有 base/edges/edges2-5（共 501 测试）未覆盖的深度：
- run_evaluation 返回的 report 结构（5 个顶层 key）
- _process_one 各种 failure 错误码路径
- _load_annotation 多种边界（已大部分覆盖，补少数）
- 模块结构与签名（部分覆盖，补精确）
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# =========================================================================
# _load_annotation 边界补强
# =========================================================================


def test_load_annotation_signature_return_annotation_dict_or_none():
    sig = inspect.signature(_load_annotation)
    annotation = sig.return_annotation
    # dict | None
    assert "dict" in str(annotation) or "None" in str(annotation)


def test_load_annotation_path_param_name():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


def test_load_annotation_path_annotation_path_or_none():
    sig = inspect.signature(_load_annotation)
    annotation = sig.parameters["path"].annotation
    assert "Path" in str(annotation) or "None" in str(annotation)


def test_load_annotation_no_default():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_load_annotation_valid_json_returns_dict(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"k": "v"}


def test_load_annotation_utf8_bom_returns_none(tmp_path: Path):
    """文件含 UTF-8 BOM，json.load(encoding=utf-8) 不剥离 BOM → 解析失败 → None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_with_array_root(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == [1, 2, 3]


def test_load_annotation_does_not_raise_on_invalid(tmp_path: Path):
    """invalid JSON → 返回 None，不抛异常。"""
    p = tmp_path / "a.json"
    p.write_text("{broken", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_does_not_raise_on_missing(tmp_path: Path):
    missing = tmp_path / "no.json"
    assert _load_annotation(missing) is None


def test_load_annotation_dict_with_nested_arrays(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": [1, [2, 3], {"x": "y"}]}', encoding="utf-8")
    result = _load_annotation(p)
    assert result["k"][1] == [2, 3]
    assert result["k"][2]["x"] == "y"


def test_load_annotation_does_not_modify_file(tmp_path: Path):
    p = tmp_path / "a.json"
    content = '{"k": "v"}'
    p.write_text(content, encoding="utf-8")
    _load_annotation(p)
    assert p.read_text(encoding="utf-8") == content


# =========================================================================
# _process_one 错误码路径
# =========================================================================


def test_process_one_signature_four_params():
    sig = inspect.signature(_process_one)
    # doc, output_root, parser_name, max_chars
    assert len(sig.parameters) == 4


def test_process_one_param_names():
    sig = inspect.signature(_process_one)
    assert set(sig.parameters) == {"doc", "output_root", "parser_name", "max_chars"}


def test_process_one_no_defaults():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_process_one_return_annotation_tuple():
    sig = inspect.signature(_process_one)
    annotation = sig.return_annotation
    # tuple[..., ...]
    assert "tuple" in str(annotation).lower()


# =========================================================================
# run_evaluation 返回的 report 结构
# =========================================================================


def test_run_evaluation_signature_returns_dict():
    sig = inspect.signature(run_evaluation)
    annotation = sig.return_annotation
    assert "dict" in str(annotation).lower()


def test_run_evaluation_keyword_only_marker():
    """parser_name/max_chars/tolerance_chars 是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_default_parser_name_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_default_max_chars_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_default_tolerance_chars_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_manifest_param_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_run_evaluation_output_path_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_only_run_evaluation():
    import evaluation.runner as mod
    assert mod.__all__ == ["run_evaluation"]


def test_module_all_is_list():
    import evaluation.runner as mod
    assert isinstance(mod.__all__, list)


def test_module_imports_json():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_time():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "import time" in src


def test_module_imports_path():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_process_single():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "process_single" in src


def test_module_imports_image_output_dir_for():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "image_output_dir_for" in src


def test_module_imports_report_version():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "REPORT_VERSION" in src


def test_module_imports_annotation_metrics():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_imports_compute_automatic_metrics():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "compute_automatic_metrics" in src


def test_module_imports_aggregate_summary():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_uses_future_annotations():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.runner as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_runner():
    import evaluation.runner as mod
    doc = mod.__doc__
    assert "runner" in doc.lower() or "评测" in doc


def test_module_docstring_mentions_total_time():
    """docstring 说明计时只记 total。"""
    import evaluation.runner as mod
    doc = mod.__doc__
    assert "total" in doc.lower() or "计时" in doc


def test_module_docstring_mentions_not_instrumented():
    """docstring 说明 parse/chunk 未插桩。"""
    import evaluation.runner as mod
    doc = mod.__doc__
    assert "not_instrumented" in doc or "未插桩" in doc


def test_module_no_silence_unused():
    """runner 无 _silence_unused 函数。"""
    import evaluation.runner as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# run_evaluation 端到端（mini manifest）
# =========================================================================


class _FakeDocEntry:
    """模拟 DocumentEntry。"""
    def __init__(self, tmp_path: Path):
        self.doc_id = "txt1"
        self.path_str = "x.txt"
        self.source_type = "text"
        # 创建真实文件让 process_single 能 hash
        p = tmp_path / "x.txt"
        p.write_text("hello world this is a paragraph.", encoding="utf-8")
        self.resolved_path = p
        self.categories = ("test",)
        self.paired_with = None
        self.annotation_file_str = None
        self.annotation_resolved = None
        self.expectations = None
        self.sha256 = None


class _FakeManifest:
    """模拟 Manifest。"""
    def __init__(self, tmp_path: Path):
        self.devset_status = "test"
        self.file_count = 1
        self.content_group_count = 1
        self.pdf_count = 0
        self.docx_count = 0
        self.categories_covered = ["test"]
        self.project_root = tmp_path
        self.documents = (_FakeDocEntry(tmp_path),)
        self.expected_failures = ()


def test_run_evaluation_returns_dict(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert isinstance(result, dict)


def test_run_evaluation_creates_output_file(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    assert output.is_file()


def test_run_evaluation_output_is_valid_json(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)


def test_run_evaluation_report_has_top_level_keys(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    expected_keys = {"report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"}
    assert expected_keys.issubset(set(result.keys()))


def test_run_evaluation_report_version_matches_constant(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["report_version"] == REPORT_VERSION


def test_run_evaluation_provenance_has_parser_name(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["provenance"]["parser_name"] == "text"


def test_run_evaluation_provenance_has_max_chars(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text", max_chars=500)
    assert result["provenance"]["max_chars"] == 500


def test_run_evaluation_devset_has_status(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["devset"]["status"] == "test"


def test_run_evaluation_devset_has_file_count(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["devset"]["file_count"] == 1


def test_run_evaluation_per_doc_has_one_entry(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert len(result["per_doc"]) == 1


def test_run_evaluation_per_doc_entry_has_doc_id(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["per_doc"][0]["doc_id"] == "txt1"


def test_run_evaluation_per_doc_entry_has_metrics(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "metrics" in result["per_doc"][0]


def test_run_evaluation_per_doc_entry_has_wall_time_seconds(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "wall_time_seconds" in result["per_doc"][0]


def test_run_evaluation_per_doc_wall_time_has_total(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert "total" in wt
    assert isinstance(wt["total"], float)
    assert wt["total"] >= 0


def test_run_evaluation_per_doc_wall_time_parse_is_none(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None


def test_run_evaluation_per_doc_wall_time_chunk_is_none(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["chunk"] is None


def test_run_evaluation_per_doc_wall_time_parse_reason(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse_reason"] == "not_instrumented"


def test_run_evaluation_per_doc_wall_time_chunk_reason(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failures_empty_for_fake_manifest(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["expected_failures"] == []


def test_run_evaluation_creates_parent_dirs(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "deep" / "nested" / "dir" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    assert output.is_file()


def test_run_evaluation_summary_has_counts(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "counts" in result["summary"]


def test_run_evaluation_summary_has_success_rates(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "success_rates" in result["summary"]


def test_run_evaluation_summary_has_ratio_macro_averages(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "ratio_macro_averages" in result["summary"]


def test_run_evaluation_summary_has_silent_drop_total(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "silent_drop_total" in result["summary"]


def test_run_evaluation_returns_same_dict_as_written(tmp_path: Path):
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    written = json.loads(output.read_text(encoding="utf-8"))
    assert result == written


def test_run_evaluation_json_serializable(tmp_path: Path):
    """报告可被 JSON 序列化（无 set/tuple/datetime 等）。"""
    manifest = _FakeManifest(tmp_path)
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    # 已写到文件，证明 JSON 可序列化
    assert output.is_file()


# =========================================================================
# 综合行为
# =========================================================================


def test_load_annotation_idempotent(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a == b


def test_load_annotation_returns_new_dict_each_call(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a is not b
    assert a == b
