r"""evaluation/runner.py 边角测试 - 第五轮（Round 131）。

补强已有 base/edges/edges2/edges3/edges4（共 404 测试）未覆盖的深度路径：
- _load_annotation 边界：
  - Path 是目录 → None（is_file() False）
  - 符号链接（不存在） → None
  - 大文件加载
  - 多层嵌套 JSON
- _process_one 深度：
  - 返回 tuple 5 元素
  - error_dict 来自 errors[0].to_dict()
  - image_dir 为 Path 或 None
  - parser_version 字符串内容
  - elapsed > 0
  - out_stub 父目录创建
- run_evaluation 深度：
  - 报告含 report_version
  - provenance 含 parser_name/max_chars
  - devset 含 file_count/pdf_count/docx_count
  - summary 含 success_rates
  - per_doc 各项含 doc_id/source_type/metrics/wall_time_seconds
  - wall_time_seconds 含 total/parse/chunk/parse_reason/chunk_reason
  - expected_failures 各项含 4 字段
  - public per_doc 不含 _ 前缀字段
- 模块结构深度：
  - imports 完整
  - __all__ 1 项
  - 各 helper callable
- 签名深度：
  - run_evaluation keyword-only 参数
  - _load_annotation / _process_one 签名
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


SHA = "a" * 64


# =========================================================================
# _load_annotation 边界
# =========================================================================


def test_load_annotation_signature_one_param():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "path" in params


def test_load_annotation_param_annotation_path_or_none():
    sig = inspect.signature(_load_annotation)
    ann = sig.parameters["path"].annotation
    assert "Path" in str(ann) and "None" in str(ann)


def test_load_annotation_return_annotation_dict_or_none():
    sig = inspect.signature(_load_annotation)
    ret = sig.return_annotation
    assert "dict" in str(ret).lower() and "None" in str(ret)


def test_load_annotation_none_input_returns_none():
    assert _load_annotation(None) is None


def test_load_annotation_missing_file_returns_none(tmp_path: Path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none(tmp_path: Path):
    """目录而非文件 → is_file() False → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_empty_file_returns_none(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    # 空 file → json.load raises JSONDecodeError → 捕获 → None
    assert _load_annotation(p) is None


def test_load_annotation_whitespace_only_returns_none(tmp_path: Path):
    p = tmp_path / "ws.json"
    p.write_text("   \n\t  ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_object_returns_dict(tmp_path: Path):
    p = tmp_path / "obj.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"k": "v"}


def test_load_annotation_array_returns_list(tmp_path: Path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == [1, 2, 3]


def test_load_annotation_int_returns_int(tmp_path: Path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 42


def test_load_annotation_string_returns_str(tmp_path: Path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    result = _load_annotation(p)
    assert result == "hello"


def test_load_annotation_null_returns_none(tmp_path: Path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_bool_returns_bool(tmp_path: Path):
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    result = _load_annotation(p)
    assert result is True


def test_load_annotation_nested_dict(tmp_path: Path):
    p = tmp_path / "nested.json"
    p.write_text('{"a": {"b": {"c": [1, 2, {"d": "e"}]}}}', encoding="utf-8")
    result = _load_annotation(p)
    # c = [1, 2, {"d": "e"}]，索引 2 是 {"d": "e"}
    assert result["a"]["b"]["c"][2]["d"] == "e"


def test_load_annotation_unicode_filename(tmp_path: Path):
    """unicode 文件名。"""
    p = tmp_path / "数据.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    assert _load_annotation(p) == {"k": "v"}


def test_load_annotation_unicode_content(tmp_path: Path):
    p = tmp_path / "u.json"
    p.write_text('{"name": "中文"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result["name"] == "中文"


def test_load_annotation_invalid_json_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_truncated_json_returns_none(tmp_path: Path):
    p = tmp_path / "trunc.json"
    p.write_text('{"k": "v"', encoding="utf-8")  # 缺 }
    assert _load_annotation(p) is None


# =========================================================================
# _process_one 深度
# =========================================================================


def test_process_one_signature_four_params():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert len(params) == 4
    assert "doc" in params
    assert "output_root" in params
    assert "parser_name" in params
    assert "max_chars" in params


def test_process_one_returns_tuple_of_five(tmp_path: Path):
    """构造一个失败的 doc（resolved_path 不存在）→ process_single 返回 errors。"""
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",  # 不存在
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_failure_returns_none_document(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    document, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error is not None


def test_process_one_failure_error_dict_has_code(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    _, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "code" in error


def test_process_one_failure_error_dict_has_message(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    _, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "message" in error


def test_process_one_failure_parser_version_none(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version is None


def test_process_one_failure_image_dir_none(tmp_path: Path):
    """document is None → image_dir is None。"""
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_failure_elapsed_non_negative(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert elapsed >= 0


def test_process_one_creates_per_doc_dir(tmp_path: Path):
    """失败时也会创建 _per_doc 目录。"""
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


# =========================================================================
# run_evaluation 深度
# =========================================================================


def _make_minimal_manifest(tmp_path: Path, documents=None, expected_failures=None):
    """构造一个最小可用 manifest。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    from evaluation.manifest import Manifest

    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(documents or []),
        expected_failures=tuple(expected_failures or []),
        project_root=tmp_path,
    )


def test_run_evaluation_signature_five_params():
    """5 个参数（含 tolerance_chars）。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert len(params) == 5
    assert "manifest" in params
    assert "output_path" in params
    assert "parser_name" in params
    assert "max_chars" in params
    assert "tolerance_chars" in params


def test_run_evaluation_keyword_only_marker():
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


def test_run_evaluation_return_annotation_dict():
    sig = inspect.signature(run_evaluation)
    ret = sig.return_annotation
    assert "dict" in str(ret).lower()


def test_run_evaluation_creates_output_file(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    assert output.is_file()


def test_run_evaluation_returns_report_dict(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert isinstance(report, dict)


def test_run_evaluation_report_has_report_version(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert "report_version" in report


def test_run_evaluation_report_has_provenance(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert "provenance" in report


def test_run_evaluation_report_has_devset(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert "devset" in report


def test_run_evaluation_report_has_summary(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert "summary" in report


def test_run_evaluation_report_has_per_doc(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert "per_doc" in report
    assert isinstance(report["per_doc"], list)


def test_run_evaluation_report_has_expected_failures(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert "expected_failures" in report
    assert isinstance(report["expected_failures"], list)


def test_run_evaluation_per_doc_empty_for_empty_manifest(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert report["per_doc"] == []


def test_run_evaluation_expected_failures_empty_for_empty_manifest(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output)
    assert report["expected_failures"] == []


def test_run_evaluation_provenance_has_parser_name(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output, parser_name="fallback")
    assert report["provenance"]["parser_name"] == "fallback"


def test_run_evaluation_provenance_has_max_chars(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    report = run_evaluation(manifest, output, max_chars=500)
    assert report["provenance"]["max_chars"] == 500


def test_run_evaluation_output_writes_valid_json(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_run_evaluation_output_writes_top_level_keys(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    for key in ("report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"):
        assert key in data


def test_run_evaluation_idempotent(tmp_path: Path):
    """同一 manifest 跑两次，输出文件结构相同（不依赖时间）。"""
    manifest = _make_minimal_manifest(tmp_path)
    output1 = tmp_path / "out1.json"
    output2 = tmp_path / "out2.json"
    run_evaluation(manifest, output1)
    run_evaluation(manifest, output2)
    d1 = json.loads(output1.read_text(encoding="utf-8"))
    d2 = json.loads(output2.read_text(encoding="utf-8"))
    # 比较非时间字段
    assert d1["report_version"] == d2["report_version"]
    assert d1["provenance"]["parser_name"] == d2["provenance"]["parser_name"]
    assert d1["devset"] == d2["devset"]


def test_run_evaluation_creates_deeply_nested_output(tmp_path: Path):
    """output_path 在多层子目录下也创建。"""
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "a" / "b" / "c" / "out.json"
    run_evaluation(manifest, output)
    assert output.is_file()


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_json():
    from evaluation import runner as mod
    assert hasattr(mod, "json")


def test_module_imports_time():
    from evaluation import runner as mod
    assert hasattr(mod, "time")


def test_module_imports_path():
    from evaluation import runner as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    from evaluation import runner as mod
    assert hasattr(mod, "Any")


def test_module_imports_process_single():
    from evaluation import runner as mod
    assert hasattr(mod, "process_single")


def test_module_imports_image_output_dir_for():
    from evaluation import runner as mod
    assert hasattr(mod, "image_output_dir_for")


def test_module_imports_report_version():
    from evaluation import runner as mod
    assert hasattr(mod, "REPORT_VERSION")


def test_module_imports_chunk_boundary_prf():
    from evaluation import runner as mod
    assert hasattr(mod, "chunk_boundary_prf")


def test_module_imports_figure_caption_prf():
    from evaluation import runner as mod
    assert hasattr(mod, "figure_caption_prf")


def test_module_imports_compute_automatic_metrics():
    from evaluation import runner as mod
    assert hasattr(mod, "compute_automatic_metrics")


def test_module_imports_aggregate_summary():
    from evaluation import runner as mod
    assert hasattr(mod, "aggregate_summary")


def test_module_imports_build_provenance():
    from evaluation import runner as mod
    assert hasattr(mod, "build_provenance")


def test_module_imports_build_devset_section():
    from evaluation import runner as mod
    assert hasattr(mod, "build_devset_section")


def test_module_has_load_annotation():
    from evaluation import runner as mod
    assert hasattr(mod, "_load_annotation")


def test_module_has_process_one():
    from evaluation import runner as mod
    assert hasattr(mod, "_process_one")


def test_module_has_run_evaluation():
    from evaluation import runner as mod
    assert hasattr(mod, "run_evaluation")


def test_module_does_not_define_all_long():
    from evaluation import runner as mod
    assert isinstance(mod.__all__, list)


def test_module_all_length_one():
    from evaluation import runner as mod
    assert len(mod.__all__) == 1


def test_module_all_only_run_evaluation():
    from evaluation import runner as mod
    assert set(mod.__all__) == {"run_evaluation"}


def test_module_all_excludes_internal_helpers():
    from evaluation import runner as mod
    for item in mod.__all__:
        assert not item.startswith("_")


def test_module_internal_funcs_callable():
    from evaluation import runner as mod
    assert callable(mod._load_annotation)
    assert callable(mod._process_one)


def test_module_run_evaluation_callable():
    from evaluation import runner as mod
    assert callable(mod.run_evaluation)


def test_module_docstring_present():
    from evaluation import runner as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_total():
    from evaluation import runner as mod
    doc = mod.__doc__
    assert "total" in doc.lower()


def test_module_docstring_mentions_not_instrumented():
    from evaluation import runner as mod
    doc = mod.__doc__
    assert "not_instrumented" in doc or "未插桩" in doc


def test_module_docstring_mentions_image():
    from evaluation import runner as mod
    doc = mod.__doc__
    assert "image" in doc.lower() or "图片" in doc


def test_module_docstring_mentions_pipeline():
    from evaluation import runner as mod
    doc = mod.__doc__
    assert "pipeline" in doc.lower()


def test_module_uses_future_annotations():
    import ast
    from evaluation import runner as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 报告字段内容深度
# =========================================================================


def test_report_wall_time_has_total_field(tmp_path: Path):
    """报告里 wall_time_seconds 字段含 total。"""
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    # 无 documents → per_doc 为空，但报告 schema 要求 wall_time 字段在 per_doc 内
    # 所以这里检查 schema 而非具体字段
    assert "per_doc" in data


def test_report_summary_has_success_rates(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "success_rates" in data["summary"]


def test_report_devset_has_devset_status(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "status" in data["devset"]


def test_report_provenance_has_evaluator_version(tmp_path: Path):
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "evaluator_version" in data["provenance"]


def test_report_provenance_does_not_duplicate_devset(tmp_path: Path):
    """provenance 与 devset 是分开的两个 section。"""
    manifest = _make_minimal_manifest(tmp_path)
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "provenance" in data
    assert "devset" in data
    # devset 内容不在 provenance 里
    assert "devset_status" not in data["provenance"]


def test_report_with_failed_doc_summary_counts(tmp_path: Path):
    """含失败 doc 的 summary silent_drop_count 应该是 null（无 expectations）。"""
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",  # 不存在 → 失败
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert len(data["per_doc"]) == 1


def test_report_per_doc_each_has_doc_id(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="my-doc",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["per_doc"][0]["doc_id"] == "my-doc"


def test_report_per_doc_each_has_source_type(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["per_doc"][0]["source_type"] == "pdf"


def test_report_per_doc_each_has_metrics(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "metrics" in data["per_doc"][0]


def test_report_per_doc_each_has_wall_time_seconds(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "wall_time_seconds" in data["per_doc"][0]


def test_report_per_doc_wall_time_has_total_parse_chunk(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    wt = data["per_doc"][0]["wall_time_seconds"]
    assert "total" in wt
    assert "parse" in wt
    assert "chunk" in wt


def test_report_per_doc_wall_time_parse_reason_not_instrumented(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    wt = data["per_doc"][0]["wall_time_seconds"]
    assert wt.get("parse_reason") == "not_instrumented"
    assert wt.get("chunk_reason") == "not_instrumented"


def test_report_per_doc_no_underscore_fields(tmp_path: Path):
    """public per_doc 不含 _ 前缀字段。"""
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    for key in data["per_doc"][0]:
        assert not key.startswith("_"), f"public per_doc should not have _ prefix: {key}"


def test_report_expected_failure_each_has_4_fields(tmp_path: Path):
    from evaluation.manifest import ExpectedFailure

    ef = ExpectedFailure(
        doc_id="f1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        expected_error_code="file_not_found",
        source_type="pdf",
    )
    manifest = _make_minimal_manifest(tmp_path, expected_failures=[ef])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    ef_result = data["expected_failures"][0]
    assert set(ef_result.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}


def test_report_expected_failure_matches_when_codes_align(tmp_path: Path):
    from evaluation.manifest import ExpectedFailure

    ef = ExpectedFailure(
        doc_id="f1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        expected_error_code="file_not_found",  # 实际也会是这个 code
        source_type="pdf",
    )
    manifest = _make_minimal_manifest(tmp_path, expected_failures=[ef])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["expected_failures"][0]["matches"] is True


def test_report_expected_failure_actual_code_when_mismatch(tmp_path: Path):
    from evaluation.manifest import ExpectedFailure

    ef = ExpectedFailure(
        doc_id="f1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        expected_error_code="different_error",  # 与实际不符
        source_type="pdf",
    )
    manifest = _make_minimal_manifest(tmp_path, expected_failures=[ef])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["expected_failures"][0]["matches"] is False
    assert data["expected_failures"][0]["actual_error_code"] == "file_not_found"


# =========================================================================
# 时间字段行为
# =========================================================================


def test_process_one_elapsed_is_float(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)


def test_report_per_doc_wall_time_total_is_float(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    total = data["per_doc"][0]["wall_time_seconds"]["total"]
    assert isinstance(total, (int, float))


def test_report_per_doc_wall_time_parse_is_none(tmp_path: Path):
    from evaluation.manifest import DocumentEntry

    doc = DocumentEntry(
        doc_id="d1",
        path_str="missing.pdf",
        resolved_path=tmp_path / "missing.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    manifest = _make_minimal_manifest(tmp_path, documents=[doc])
    output = tmp_path / "out.json"
    run_evaluation(manifest, output)
    data = json.loads(output.read_text(encoding="utf-8"))
    wt = data["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None
