r"""evaluation/runner.py 边角测试 - 第七轮（Round 175）。

补强已有 base/edges/edges2-6（共 569 测试）未覆盖的深度：
- _load_annotation 各异常分支精确（None/不存在/目录/JSONDecodeError/OSError）
- _process_one 各错误码与 image_dir 命名
- run_evaluation expected_failures 流程
- run_evaluation 公开 per_doc 与私有字段分离
- 模块结构与签名深度
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
# _load_annotation 异常分支精确
# =========================================================================


def test_load_annotation_none_returns_none():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_returns_none(tmp_path: Path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none(tmp_path: Path):
    """目录不是 is_file → None。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _load_annotation(sub) is None


def test_load_annotation_invalid_json_returns_none(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_dict_when_valid(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, dict)
    assert result == {"k": "v"}


def test_load_annotation_returns_new_dict_each_call(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a is not b
    assert a == b


def test_load_annotation_idempotent(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    assert _load_annotation(p) == _load_annotation(p)


def test_load_annotation_signature():
    sig = inspect.signature(_load_annotation)
    assert set(sig.parameters) == {"path"}


def test_load_annotation_path_default_no_default():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_load_annotation_path_annotation_path_or_none():
    sig = inspect.signature(_load_annotation)
    annotation = str(sig.parameters["path"].annotation)
    assert "Path" in annotation
    assert "None" in annotation


def test_load_annotation_return_annotation_dict_or_none():
    sig = inspect.signature(_load_annotation)
    annotation = str(sig.return_annotation)
    assert "dict" in annotation or "None" in annotation


# =========================================================================
# _process_one 错误码与 image_dir
# =========================================================================


class _FakeDoc:
    """模拟 DocumentEntry。"""

    def __init__(self, path: Path, doc_id: str = "doc-x", source_type: str = "text",
                 expectations: dict | None = None, annotation_resolved: Path | None = None):
        self.resolved_path = path
        self.doc_id = doc_id
        self.source_type = source_type
        self.expectations = expectations
        self.annotation_resolved = annotation_resolved


class _FakeManifest:
    """模拟 Manifest。"""

    def __init__(self, tmp_path: Path, docs=None, efs=None):
        self.project_root = tmp_path
        self.documents = docs or []
        self.expected_failures = efs or []
        # 下游 build_devset_section 用到的字段
        self.devset_status = "incomplete"
        self.file_count = 0
        self.pdf_count = 0
        self.docx_count = 0
        self.content_group_count = 0
        self.categories_covered = []


def test_process_one_returns_tuple_of_5(tmp_path: Path):
    """返回 (document_dict, error_dict, total_seconds, parser_version, image_dir)。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="d1")
    result = _process_one(doc, tmp_path, "text", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_success_document_dict(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="d1")
    document_dict, error_dict, _, _, _ = _process_one(doc, tmp_path, "text", 800)
    assert document_dict is not None
    assert error_dict is None
    assert isinstance(document_dict, dict)


def test_process_one_success_parser_version(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="d1")
    _, _, _, parser_version, _ = _process_one(doc, tmp_path, "text", 800)
    assert parser_version is not None
    assert isinstance(parser_version, str)


def test_process_one_success_total_seconds_float(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="d1")
    _, _, total_seconds, _, _ = _process_one(doc, tmp_path, "text", 800)
    assert isinstance(total_seconds, float)
    assert total_seconds >= 0


def test_process_one_success_image_dir_is_path(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="d1")
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "text", 800)
    assert isinstance(image_dir, Path)


def test_process_one_failure_returns_first_error(tmp_path: Path):
    """文件不存在 → process_single 返回 errors → _process_one 取 errors[0]。"""
    p = tmp_path / "missing.txt"
    doc = _FakeDoc(p, doc_id="d1")
    document_dict, error_dict, _, _, _ = _process_one(doc, tmp_path, "text", 800)
    assert document_dict is None
    assert error_dict is not None
    assert error_dict["code"] == "file_not_found"


def test_process_one_failure_image_dir_is_none(tmp_path: Path):
    """document None 时 image_dir 也是 None（不让下游误用 cwd）。"""
    p = tmp_path / "missing.txt"
    doc = _FakeDoc(p, doc_id="d1")
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "text", 800)
    assert image_dir is None


def test_process_one_creates_per_doc_dir(tmp_path: Path):
    """out_stub.parent (_per_doc 目录) 会被 mkdir 创建。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="d1")
    output_root = tmp_path / "out"
    _process_one(doc, output_root, "text", 800)
    assert (output_root / "_per_doc").is_dir()


def test_process_one_out_stub_unlinked_after_processing(tmp_path: Path):
    """成功处理后 out_stub 应被清理。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    doc = _FakeDoc(p, doc_id="d1")
    output_root = tmp_path / "out"
    _process_one(doc, output_root, "text", 800)
    # _per_doc 目录存在但 out_stub 应已 unlink
    stub = output_root / "_per_doc" / "d1.json"
    assert not stub.is_file()


def test_process_one_signature():
    sig = inspect.signature(_process_one)
    assert set(sig.parameters) == {"doc", "output_root", "parser_name", "max_chars"}


def test_process_one_parser_name_no_default():
    """_process_one 内部辅助函数：parser_name 必填（默认值在 run_evaluation）。"""
    sig = inspect.signature(_process_one)
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty


def test_process_one_max_chars_no_default():
    sig = inspect.signature(_process_one)
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


def test_process_one_return_annotation_tuple():
    sig = inspect.signature(_process_one)
    assert "tuple" in str(sig.return_annotation).lower()


# =========================================================================
# run_evaluation expected_failures 流程
# =========================================================================


class _FakeExpectedFailure:
    def __init__(self, path: Path, doc_id: str = "ef1", expected_error_code: str = "file_not_found"):
        self.resolved_path = path
        self.doc_id = doc_id
        self.expected_error_code = expected_error_code


def test_run_evaluation_expected_failures_present(tmp_path: Path):
    """有 expected_failures 时，结果含 expected_failures 列表。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    ef_path = tmp_path / "missing.txt"
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1")],
        efs=[_FakeExpectedFailure(ef_path, doc_id="ef1", expected_error_code="file_not_found")],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert "expected_failures" in result
    assert len(result["expected_failures"]) == 1
    ef = result["expected_failures"][0]
    assert ef["doc_id"] == "ef1"
    assert ef["expected_error_code"] == "file_not_found"
    assert ef["actual_error_code"] == "file_not_found"
    assert ef["matches"] is True


def test_run_evaluation_expected_failures_mismatch(tmp_path: Path):
    """expected 与 actual 不一致 → matches=False。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    # 期望 unsupported_type 但实际是 file_not_found
    ef_path = tmp_path / "missing.txt"
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1")],
        efs=[_FakeExpectedFailure(ef_path, doc_id="ef1", expected_error_code="unsupported_type")],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    ef = result["expected_failures"][0]
    assert ef["matches"] is False


def test_run_evaluation_expected_failures_no_actual_error(tmp_path: Path):
    """expected_failure 实际未失败 → actual_error_code=None, matches=False。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    ef_path = tmp_path / "ok.txt"
    ef_path.write_text("ok", encoding="utf-8")
    manifest = _FakeManifest(
        tmp_path,
        docs=[_FakeDoc(p, doc_id="d1")],
        efs=[_FakeExpectedFailure(ef_path, doc_id="ef1", expected_error_code="file_not_found")],
    )
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    ef = result["expected_failures"][0]
    assert ef["actual_error_code"] is None
    assert ef["matches"] is False


def test_run_evaluation_expected_failures_empty_when_no_efs(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["expected_failures"] == []


# =========================================================================
# run_evaluation 公开 per_doc 与私有字段分离
# =========================================================================


def test_run_evaluation_per_doc_does_not_contain_private_fields(tmp_path: Path):
    """公开 per_doc 不含 _annotation_present / _tolerance_chars / _missing_markers。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    for entry in result["per_doc"]:
        assert "_annotation_present" not in entry
        assert "_tolerance_chars" not in entry
        assert "_missing_markers" not in entry


def test_run_evaluation_per_doc_keys_exact(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    for entry in result["per_doc"]:
        assert set(entry.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_per_doc_wall_time_has_5_keys(tmp_path: Path):
    """wall_time_seconds 含 total/parse/chunk/parse_reason/chunk_reason。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_run_evaluation_per_doc_wall_time_parse_is_none(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None


def test_run_evaluation_per_doc_wall_time_parse_reason_not_instrumented(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    wt = result["per_doc"][0]["wall_time_seconds"]
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


# =========================================================================
# run_evaluation 报告结构
# =========================================================================


def test_run_evaluation_report_has_5_top_keys(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert set(result.keys()) == {
        "report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"
    }


def test_run_evaluation_report_version_is_1_1(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["report_version"] == REPORT_VERSION


def test_run_evaluation_creates_output_parent_dir(tmp_path: Path):
    """output_path.parent 不存在时会被 mkdir 创建。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "deep" / "sub" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert output.is_file()
    assert isinstance(result, dict)


def test_run_evaluation_writes_json_file(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written == result


def test_run_evaluation_empty_documents_list(tmp_path: Path):
    """空 manifest → 空 per_doc + 空 expected_failures。但仍写出报告。"""
    manifest = _FakeManifest(tmp_path, docs=[], efs=[])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="text")
    assert result["per_doc"] == []
    assert result["expected_failures"] == []
    assert output.is_file()


# =========================================================================
# run_evaluation tolerance_chars 透传
# =========================================================================


def test_run_evaluation_default_tolerance_chars_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_default_max_chars_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_default_parser_name_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_keyword_only_after_output_path():
    sig = inspect.signature(run_evaluation)
    for name in ("parser_name", "max_chars", "tolerance_chars"):
        assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_signature():
    sig = inspect.signature(run_evaluation)
    assert set(sig.parameters) == {
        "manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"
    }


def test_run_evaluation_return_annotation_dict():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import evaluation.runner as mod
    assert mod.__all__ == ["run_evaluation"]


def test_module_all_is_list():
    import evaluation.runner as mod
    assert isinstance(mod.__all__, list)


def test_module_all_no_duplicates():
    import evaluation.runner as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_uses_future_annotations():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


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


def test_module_imports_pipeline():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from app.pipeline import" in src
    assert "image_output_dir_for" in src
    assert "process_single" in src


def test_module_imports_report_version():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from evaluation import" in src
    assert "REPORT_VERSION" in src


def test_module_imports_annotation_metrics():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from evaluation.annotation_metrics import" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_imports_metrics():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from evaluation.metrics import" in src
    assert "compute_automatic_metrics" in src


def test_module_imports_report_builders():
    import evaluation.runner as mod
    src = inspect.getsource(mod)
    assert "from evaluation.report import" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_docstring_present():
    import evaluation.runner as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_constraints():
    """docstring 提及关键约束（计时、parse/chunk not_instrumented）。"""
    import evaluation.runner as mod
    doc = mod.__doc__
    assert "time.perf_counter" in doc or "perf_counter" in doc
    assert "not_instrumented" in doc or "未插桩" in doc


def test_module_docstring_mentions_pipeline_failed():
    """docstring 提及失败文档处理。"""
    import evaluation.runner as mod
    doc = mod.__doc__
    assert "pipeline_failed" in doc or "失败" in doc


def test_module_no_silence_unused():
    import evaluation.runner as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 综合行为
# =========================================================================


def test_run_evaluation_idempotent_same_input(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output1 = tmp_path / "out1" / "report.json"
    output2 = tmp_path / "out2" / "report.json"
    r1 = run_evaluation(manifest, output1, parser_name="text")
    r2 = run_evaluation(manifest, output2, parser_name="text")
    # per_doc 数量、doc_id、metrics keys 一致（数值可能微差）
    assert len(r1["per_doc"]) == len(r2["per_doc"])
    assert r1["per_doc"][0]["doc_id"] == r2["per_doc"][0]["doc_id"]
    assert set(r1["per_doc"][0]["metrics"].keys()) == set(r2["per_doc"][0]["metrics"].keys())


def test_run_evaluation_creates_per_doc_directory(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    # _per_doc 目录被创建（即便 out_stub 被清理）
    per_doc_dir = output.parent / "_per_doc"
    assert per_doc_dir.is_dir()


def test_run_evaluation_per_doc_dir_cleaned_of_stubs(tmp_path: Path):
    """成功处理后 _per_doc 目录里不应残留 .json stub。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    run_evaluation(manifest, output, parser_name="text")
    per_doc_dir = output.parent / "_per_doc"
    stubs = list(per_doc_dir.glob("*.json"))
    assert stubs == []


def test_load_annotation_does_not_mutate_input(tmp_path: Path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    _load_annotation(p)
    after = p.read_text(encoding="utf-8")
    assert before == after


def test_run_evaluation_with_kreuzberg_parser(tmp_path: Path):
    """parser_name=kreuzberg 在 docs 上不抛（kreuzberg 不可用时走错误路径）。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(tmp_path, docs=[_FakeDoc(p, doc_id="d1")])
    output = tmp_path / "out" / "report.json"
    result = run_evaluation(manifest, output, parser_name="kreuzberg")
    # 报告仍写出
    assert output.is_file()
    # per_doc 有结果（可能失败但 entry 存在）
    assert len(result["per_doc"]) == 1
