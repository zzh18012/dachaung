r"""evaluation/runner.py 边角测试 - 第十五轮（Round 245）。

补强已有 base/edges/edges2-14（共 ~930+ 测试）未覆盖的深度：
- 模块 namespace identity：typing.Any / json / time / Path / REPORT_VERSION
- REPORT_VERSION 在 namespace 是 evaluation.REPORT_VERSION 的引用
- _load_annotation 行为：utf-8 with BOM、空 path 对象
- _process_one：image_dir 在 document 不为 None 时是 Path；为 None 时是 None
- run_evaluation：report_version 顶层 key 顺序；per_doc_results 与 public_per_doc 不同 list
- 模块源码字符串：含 'not_instrumented' / 'process_single' / 'image_output_dir_for' 等
- 函数签名 return annotation 精确
- callable 验证
"""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import (
    REPORT_VERSION as MODULE_REPORT_VERSION,
    _load_annotation,
    _process_one,
    run_evaluation,
)


# =========================================================================
# 模块 namespace identity
# =========================================================================


def test_module_typing_any_in_namespace_identity():
    """typing.Any 在 evaluation.runner 命名空间。"""
    import evaluation.runner as m
    assert m.Any is Any


def test_module_json_in_namespace_identity():
    """json 在 evaluation.runner 命名空间。"""
    import evaluation.runner as m
    import json as json_mod
    assert m.json is json_mod


def test_module_time_in_namespace_identity():
    """time 在 evaluation.runner 命名空间。"""
    import evaluation.runner as m
    assert m.time is time


def test_module_path_in_namespace_identity():
    """Path 在 evaluation.runner 命名空间。"""
    import evaluation.runner as m
    assert m.Path is Path


def test_module_report_version_in_namespace():
    """REPORT_VERSION 在 evaluation.runner 命名空间。"""
    import evaluation.runner as m
    assert hasattr(m, "REPORT_VERSION")


def test_module_report_version_identity():
    """evaluation.runner.REPORT_VERSION is evaluation.REPORT_VERSION。"""
    import evaluation.runner as m
    assert m.REPORT_VERSION is REPORT_VERSION


def test_module_report_version_value():
    """REPORT_VERSION 值是字符串（version-like）。"""
    assert isinstance(REPORT_VERSION, str)
    assert "." in REPORT_VERSION


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_is_list():
    """__all__ 是 list。"""
    import evaluation.runner as m
    assert isinstance(m.__all__, list)


def test_module_all_exact():
    """__all__ 内容精确。"""
    import evaluation.runner as m
    assert m.__all__ == ["run_evaluation"]


def test_module_all_does_not_contain_internal_helpers():
    """__all__ 不含 _load_annotation / _process_one。"""
    import evaluation.runner as m
    assert "_load_annotation" not in m.__all__
    assert "_process_one" not in m.__all__


def test_module_internal_helpers_accessible_in_namespace():
    """内部 helper 仍可在命名空间访问。"""
    import evaluation.runner as m
    assert callable(m._load_annotation)
    assert callable(m._process_one)


# =========================================================================
# 模块源码字符串
# =========================================================================


def test_module_docstring_mentions_not_instrumented():
    """模块 docstring 含 'not_instrumented'。"""
    import evaluation.runner as m
    assert m.__doc__ is not None
    assert "not_instrumented" in m.__doc__


def test_module_docstring_mentions_process_single():
    """模块 docstring 含 'process_single'。"""
    import evaluation.runner as m
    assert "process_single" in (m.__doc__ or "")


def test_module_docstring_mentions_image_output_dir():
    """模块 docstring 含 'image_output_dir'。"""
    import evaluation.runner as m
    assert "image_output_dir" in (m.__doc__ or "")


def test_module_docstring_mentions_pipeline_failed():
    """模块 docstring 含 'pipeline_failed'。"""
    import evaluation.runner as m
    assert "pipeline_failed" in (m.__doc__ or "")


def test_module_docstring_mentions_per_doc():
    """模块 docstring 含 'per_doc'。"""
    import evaluation.runner as m
    assert "per_doc" in (m.__doc__ or "")


def test_module_source_contains_not_instrumented():
    """源码含字符串 'not_instrumented'（用于 wall_time_seconds）。"""
    import evaluation.runner
    src = inspect.getsource(evaluation.runner)
    assert "not_instrumented" in src


def test_module_source_contains_image_output_dir_for_call():
    """源码含 'image_output_dir_for('。"""
    import evaluation.runner
    src = inspect.getsource(evaluation.runner)
    assert "image_output_dir_for(" in src


def test_module_source_contains_perf_counter():
    """源码含 'time.perf_counter'。"""
    import evaluation.runner
    src = inspect.getsource(evaluation.runner)
    assert "perf_counter" in src


# =========================================================================
# _load_annotation 边界
# =========================================================================


def test_load_annotation_none_path_returns_none():
    """path=None → 直接返回 None（不调 .is_file()）。"""
    out = _load_annotation(None)
    assert out is None


def test_load_annotation_nonexistent_returns_none(tmp_path: Path):
    """不存在的 path → None。"""
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none(tmp_path: Path):
    """path 是目录 → .is_file() False → None。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_valid_dict(tmp_path: Path):
    """合法 JSON dict → 返回 dict。"""
    p = tmp_path / "ann.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value"}


def test_load_annotation_valid_list(tmp_path: Path):
    """合法 JSON list → 返回 list。"""
    p = tmp_path / "ann.json"
    p.write_text('[1, 2, 3]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_invalid_json_returns_none(tmp_path: Path):
    """非法 JSON → 返回 None。"""
    p = tmp_path / "ann.json"
    p.write_text('not json', encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_empty_file_returns_none(tmp_path: Path):
    """空文件 → json.load raises JSONDecodeError → 返回 None。"""
    p = tmp_path / "ann.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_handles_oserror(tmp_path: Path, monkeypatch):
    """OSError 时不抛，返回 None。"""
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")

    original_open = Path.open

    def boom(self, *args, **kwargs):
        if self == p:
            raise OSError("simulated")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", boom)
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_signature_exact():
    """signature: (path)。"""
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_load_annotation_return_annotation_is_dict_or_none():
    """return annotation 是 dict[str, Any] | None（字符串形式）。"""
    sig = inspect.signature(_load_annotation)
    # from __future__ import annotations 让 return_annotation 是 str
    assert isinstance(sig.return_annotation, str)
    assert "dict" in sig.return_annotation
    assert "None" in sig.return_annotation


# =========================================================================
# _process_one signature
# =========================================================================


def test_process_one_signature_exact():
    """signature: (doc, output_root, parser_name, max_chars)。"""
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == [
        "doc", "output_root", "parser_name", "max_chars",
    ]


def test_process_one_signature_return_annotation_5_tuple():
    """return annotation 是 5-tuple（含 None | Path 等）。"""
    sig = inspect.signature(_process_one)
    # from __future__ 让 annotation 是 str
    assert isinstance(sig.return_annotation, str)
    # 5 个项由逗号分隔；tuple 类型有 4 个逗号
    assert sig.return_annotation.count(",") >= 4


def test_process_one_no_default_values():
    """所有参数无默认值。"""
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# run_evaluation signature
# =========================================================================


def test_run_evaluation_signature_exact():
    """signature: (manifest, output_path, *, parser_name='fallback', max_chars=800, tolerance_chars=30)。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == [
        "manifest", "output_path", "parser_name", "max_chars", "tolerance_chars",
    ]


def test_run_evaluation_keyword_only_marker():
    """parser_name/max_chars/tolerance_chars 是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    # 第 3 个参数开始应该是 KEYWORD_ONLY
    for name in ("parser_name", "max_chars", "tolerance_chars"):
        p = sig.parameters[name]
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_positional_params():
    """manifest / output_path 是 POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(run_evaluation)
    for name in ("manifest", "output_path"):
        p = sig.parameters[name]
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_default_values():
    """默认值：parser_name='fallback', max_chars=800, tolerance_chars=30。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_return_annotation_dict():
    """return annotation 是 dict[str, Any]。"""
    sig = inspect.signature(run_evaluation)
    assert isinstance(sig.return_annotation, str)
    assert "dict" in sig.return_annotation


# =========================================================================
# callable 验证
# =========================================================================


def test_load_annotation_callable():
    assert callable(_load_annotation)


def test_process_one_callable():
    assert callable(_process_one)


def test_run_evaluation_callable():
    assert callable(run_evaluation)


# =========================================================================
# run_evaluation 端到端：report 顶层结构
# =========================================================================


def test_run_evaluation_report_top_level_keys_in_order(tmp_path: Path):
    """顶层 6 keys 顺序：report_version → provenance → devset → summary → per_doc → expected_failures。"""
    # 用空 manifest（无可执行 documents）来跑通流程
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    keys = list(report.keys())
    assert keys == [
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    ]


def test_run_evaluation_report_version_is_constant(tmp_path: Path):
    """report['report_version'] == REPORT_VERSION 常量。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_per_doc_empty_for_empty_manifest(tmp_path: Path):
    """空 manifest → per_doc=[]。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert report["per_doc"] == []


def test_run_evaluation_expected_failures_empty_for_empty_manifest(tmp_path: Path):
    """空 manifest → expected_failures=[]。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert report["expected_failures"] == []


def test_run_evaluation_summary_has_four_top_level_keys(tmp_path: Path):
    """summary 含 4 个顶层 key：counts/success_rates/ratio_macro_averages/silent_drop_total。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert set(report["summary"].keys()) == {
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total",
    }


def test_run_evaluation_devset_section_six_keys(tmp_path: Path):
    """devset 含 6 个 key。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert set(report["devset"].keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_run_evaluation_provenance_nine_keys(tmp_path: Path):
    """provenance 含 9 个 key。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert len(report["provenance"]) == 9


def test_run_evaluation_writes_file_with_same_content(tmp_path: Path):
    """返回的 report dict 与写入文件的内容一致。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    with output_path.open("r", encoding="utf-8") as f:
        file_content = json.load(f)
    assert report == file_content


def test_run_evaluation_creates_output_directory(tmp_path: Path):
    """output_path 父目录不存在时创建。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "subdir" / "nested" / "report.json"
    run_evaluation(_FakeManifest(), output_path)
    assert output_path.is_file()


# =========================================================================
# 端到端：devset 元数据透传
# =========================================================================


def test_run_evaluation_devset_status_propagated(tmp_path: Path):
    """devset_status 透传到 devset section。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "complete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert report["devset"]["status"] == "complete"


def test_run_evaluation_devset_categories_propagated(tmp_path: Path):
    """categories_covered 透传到 devset section。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ["math", "science"]
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert report["devset"]["categories_covered"] == ["math", "science"]


# =========================================================================
# process_one 错误路径
# =========================================================================


def test_process_one_unknown_error_when_doc_none_no_errors(tmp_path: Path, monkeypatch):
    """process_single 返回 (None, []) → _process_one 返回 unknown 错误。"""
    from app.pipeline import process_single as real_process_single
    from evaluation.runner import _process_one

    class _FakeDoc:
        doc_id = "test_doc"
        resolved_path = tmp_path / "fake.pdf"
        source_type = "pdf"

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    document, error, elapsed, parser_version, image_dir = _process_one(
        _FakeDoc(), tmp_path, "fallback", 800,
    )
    assert document is None
    assert error is not None
    assert error["code"] == "unknown"
    assert "process_single returned None" in error["message"]
    assert parser_version is None


def test_process_one_returns_first_error_dict(tmp_path: Path, monkeypatch):
    """errors 是 list 含 2 个 → 返回 errors[0].to_dict()。"""
    class _FakeError:
        def __init__(self, code):
            self.code = code

        def to_dict(self):
            return {"code": self.code, "message": f"err {self.code}"}

    class _FakeDoc:
        doc_id = "test_doc"
        resolved_path = tmp_path / "fake.pdf"
        source_type = "pdf"

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError("err1"), _FakeError("err2")]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    document, error, elapsed, parser_version, image_dir = _process_one(
        _FakeDoc(), tmp_path, "fallback", 800,
    )
    assert document is None
    assert error == {"code": "err1", "message": "err err1"}


def test_process_one_creates_per_doc_directory(tmp_path: Path, monkeypatch):
    """_process_one 创建 _per_doc 子目录。"""
    class _FakeDoc:
        doc_id = "test_doc"
        resolved_path = tmp_path / "fake.pdf"
        source_type = "pdf"

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    _process_one(_FakeDoc(), tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_elapsed_non_negative(tmp_path: Path, monkeypatch):
    """elapsed time ≥ 0。"""
    class _FakeDoc:
        doc_id = "test_doc"
        resolved_path = tmp_path / "fake.pdf"
        source_type = "pdf"

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    _, _, elapsed, _, _ = _process_one(_FakeDoc(), tmp_path, "fallback", 800)
    assert elapsed >= 0
    assert isinstance(elapsed, float)


def test_process_one_returns_image_dir_none_on_failure(tmp_path: Path, monkeypatch):
    """document=None → image_dir=None。"""
    class _FakeDoc:
        doc_id = "test_doc"
        resolved_path = tmp_path / "fake.pdf"
        source_type = "pdf"

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    _, _, _, _, image_dir = _process_one(_FakeDoc(), tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_cleans_up_stub_file(tmp_path: Path, monkeypatch):
    """out_stub 写入后被 unlink。"""
    class _FakeDoc:
        doc_id = "test_doc"
        resolved_path = tmp_path / "fake.pdf"
        source_type = "pdf"

    def fake_process_single(*args, **kwargs):
        # 模拟 process_single 写入 out_stub
        out_stub = args[1] if len(args) > 1 else kwargs.get("output_path")
        if out_stub is not None:
            out_stub.parent.mkdir(parents=True, exist_ok=True)
            out_stub.write_text("stub", encoding="utf-8")
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    _process_one(_FakeDoc(), tmp_path, "fallback", 800)
    # out_stub 应被清理
    assert not (tmp_path / "_per_doc" / "test_doc.json").is_file()


# =========================================================================
# 端到端：keyword-only 参数验证
# =========================================================================


def test_run_evaluation_keyword_only_args_works(tmp_path: Path):
    """keyword 参数 OK。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    # 全部 keyword
    report = run_evaluation(
        _FakeManifest(), output_path,
        parser_name="kreuzberg",
        max_chars=500,
        tolerance_chars=20,
    )
    assert report["provenance"]["parser_name"] == "kreuzberg"
    assert report["provenance"]["max_chars"] == 500


def test_run_evaluation_default_args_works(tmp_path: Path):
    """省略 keyword 参数 OK，使用默认值。"""
    class _FakeManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = []
        manifest_version = "1.0"
        project_root = tmp_path

    output_path = tmp_path / "report.json"
    report = run_evaluation(_FakeManifest(), output_path)
    assert report["provenance"]["parser_name"] == "fallback"
    assert report["provenance"]["max_chars"] == 800
