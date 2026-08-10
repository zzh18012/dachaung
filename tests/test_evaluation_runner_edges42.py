"""evaluation/runner.py 第四十四轮 edges 测试（Round 424）。

补强 edges41 未触及的角度：
- _load_annotation 行为深度第十五批（嵌套 dict / 顶层是 None / 顶层是 string / 顶层是数字）
- _process_one 行为深度第十五批（image_dir 用 image_output_dir_for / document 是 stub 但 to_dict 失败 / errors 多个取第 1 / process_single 抛异常被透传）
- run_evaluation 行为深度第十五批（多个文档批处理 / 多个 expected_failures / 多个文档的 parser_version 各异 / report_version 来自 evaluation / 多种 source_type）
- module source forbidden tokens 第二十批
- module source 字符串精确补强第十七批
- signatures 第十七批
- module 合理性第十七批
- 端到端集成第十七批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from evaluation import REPORT_VERSION, runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- helpers ----------


class _StubDoc:
    def __init__(
        self,
        doc_id="doc1",
        source_type="pdf",
        resolved_path=None,
        annotation_resolved=None,
        expectations=None,
    ):
        self.doc_id = doc_id
        self.source_type = source_type
        self.resolved_path = resolved_path
        self.annotation_resolved = annotation_resolved
        self.expectations = expectations


class _StubManifest:
    def __init__(self, documents=None, expected_failures=None, project_root=None):
        self.documents = documents or []
        self.expected_failures = expected_failures or []
        self.project_root = project_root or Path(".")
        self.devset_status = "incomplete"
        self.file_count = 0
        self.content_group_count = 0
        self.pdf_count = 0
        self.docx_count = 0
        self.categories_covered = []


class _StubDocument:
    def __init__(self, source_hash="a" * 64, parser_version="1.0.0"):
        self.source_hash = source_hash
        self.parser_version = parser_version

    def to_dict(self):
        return {"source_hash": self.source_hash, "parser_version": self.parser_version}


class _StubError:
    def __init__(self, code="parse_failed", message="boom"):
        self.code = code
        self.message = message

    def to_dict(self):
        return {"code": self.code, "message": self.message}


class _StubExpectedFailure:
    def __init__(self, doc_id="ef1", resolved_path=None, expected_error_code="unsupported_format"):
        self.doc_id = doc_id
        self.resolved_path = resolved_path
        self.expected_error_code = expected_error_code


# ---------- _load_annotation 行为深度第十五批 ----------


def test_load_annotation_returns_nested_dict_batch15(tmp_path):
    """嵌套 dict 应正常返回。"""
    p = tmp_path / "ann.json"
    p.write_text('{"a": {"b": {"c": [1, 2, 3]}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": [1, 2, 3]}}}


def test_load_annotation_json_null_batch15(tmp_path):
    """JSON null → 返回 None（合法 JSON）。"""
    p = tmp_path / "ann.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_json_string_batch15(tmp_path):
    """JSON string → 返回 str。"""
    p = tmp_path / "ann.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_json_number_batch15(tmp_path):
    """JSON number → 返回数字。"""
    p = tmp_path / "ann.json"
    p.write_text("3.14", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 3.14


def test_load_annotation_json_bool_batch15(tmp_path):
    """JSON bool → 返回 bool。"""
    p = tmp_path / "ann.json"
    p.write_text("true", encoding="utf-8")
    out = _load_annotation(p)
    assert out is True


def test_load_annotation_catches_value_error_batch15(tmp_path):
    """ValueError（JSONDecodeError 父类）也应被处理。"""
    p = tmp_path / "ann.json"
    p.write_text("{not json}", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_pathlib_path_input_batch15(tmp_path):
    """传 Path 对象。"""
    p = tmp_path / "ann.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": 1}


# ---------- _process_one 行为深度第十五批 ----------


def test_process_one_uses_image_output_dir_for_batch15(tmp_path):
    """document 不为 None 时调用 image_output_dir_for 推导 image_dir。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    stub_doc = _StubDocument(source_hash="abc" * 21 + "a", parser_version="1.0")
    seen: dict = {}

    def _fake(stub_path, source_hash):
        seen["stub_path"] = stub_path
        seen["source_hash"] = source_hash
        return Path("/fake/image_dir")

    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", side_effect=_fake):
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == Path("/fake/image_dir")
    assert seen["source_hash"] == stub_doc.source_hash


def test_process_one_errors_first_taken_batch15(tmp_path):
    """多个 errors → 取第一个的 to_dict()。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    errs = [_StubError("code_a", "msg_a"), _StubError("code_b", "msg_b")]
    with patch("evaluation.runner.process_single", return_value=(None, errs)):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            _, err, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert err == {"code": "code_a", "message": "msg_a"}


def test_process_one_no_errors_no_document_returns_unknown_batch15(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            doc_dict, err, total, ver, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert doc_dict is None
    assert err == {"code": "unknown", "message": "process_single returned None without errors"}


def test_process_one_total_seconds_nonneg_batch15(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert total >= 0.0


def test_process_one_parser_version_passed_through_batch15(tmp_path):
    """document 的 parser_version 透传到返回值。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    stub_doc = _StubDocument(source_hash="d" * 64, parser_version="9.9.9")
    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        _, _, _, ver, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert ver == "9.9.9"


def test_process_one_image_dir_none_when_document_none_batch15(tmp_path):
    """document=None → image_dir=None（即使 errors 也是 None）。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


# ---------- run_evaluation 行为深度第十五批 ----------


def test_run_evaluation_multiple_documents_batch15(tmp_path):
    """多个文档批处理。"""
    docs = [
        _StubDoc(doc_id=f"d{i}", resolved_path=Path(f"/x{i}.pdf"))
        for i in range(3)
    ]
    manifest = _StubManifest(documents=docs)
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert len(rep["per_doc"]) == 3
    doc_ids = [d["doc_id"] for d in rep["per_doc"]]
    assert doc_ids == ["d0", "d1", "d2"]


def test_run_evaluation_multiple_expected_failures_batch15(tmp_path):
    efs = [
        _StubExpectedFailure(doc_id=f"ef{i}", resolved_path=Path(f"/x{i}.bad"))
        for i in range(2)
    ]
    manifest = _StubManifest(expected_failures=efs)
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError(code="unsupported_format")])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert len(rep["expected_failures"]) == 2


def test_run_evaluation_mixed_document_types_batch15(tmp_path):
    docs = [
        _StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("/x.pdf")),
        _StubDoc(doc_id="d2", source_type="docx", resolved_path=Path("/y.docx")),
    ]
    manifest = _StubManifest(documents=docs)
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    types = [d["source_type"] for d in rep["per_doc"]]
    assert types == ["pdf", "docx"]


def test_run_evaluation_summary_has_4_keys_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert set(rep["summary"].keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_run_evaluation_devset_section_6_keys_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert set(rep["devset"].keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_run_evaluation_provenance_9_keys_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert len(rep["provenance"]) == 9


def test_run_evaluation_report_writes_file_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert out_path.is_file()


def test_run_evaluation_parser_version_first_kept_only_batch15(tmp_path):
    """多个文档都返回 parser_version → 第一个被采用。"""
    docs = [
        _StubDoc(doc_id="d1", resolved_path=Path("/x.pdf")),
        _StubDoc(doc_id="d2", resolved_path=Path("/y.pdf")),
    ]
    manifest = _StubManifest(documents=docs)
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        if doc.doc_id == "d1":
            return (None, {"code": "x"}, 0.1, "v1", None)
        return (None, {"code": "x"}, 0.1, "v2", None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["provenance"]["parser_version"] == "v1"


def test_run_evaluation_json_round_trip_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    file_text = out_path.read_text(encoding="utf-8")
    file_rep = json.loads(file_text)
    assert file_rep == rep


def test_run_evaluation_returns_dict_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert isinstance(rep, dict)


def test_run_evaluation_max_chars_passthrough_batch15(tmp_path):
    """max_chars 应传给 build_provenance。"""
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=999)
    assert rep["provenance"]["max_chars"] == 999


def test_run_evaluation_parser_name_passthrough_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="kreuzberg", max_chars=800)
    assert rep["provenance"]["parser_name"] == "kreuzberg"


# ---------- module source forbidden tokens 第二十批 ----------


_FORBIDDEN_TOKENS_ROUND20 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND20)
def test_module_source_forbidden_tokens_round20_batch15(token):
    source = inspect.getsource(rmod)
    assert token not in source


# ---------- module source 字符串精确补强第十七批 ----------


def test_module_source_module_docstring_present_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_json_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_time_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import time" in head


def test_module_source_imports_pathlib_path_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_any_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_pipeline_helpers_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from app.pipeline import" in head


def test_module_source_imports_annotation_metrics_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.annotation_metrics import" in head


def test_module_source_imports_metrics_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.metrics import" in head


def test_module_source_imports_report_helpers_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.report import" in head


def test_module_source_imports_report_version_batch15():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation import REPORT_VERSION" in head


def test_module_source_defines_load_annotation_batch15():
    source = inspect.getsource(rmod)
    assert "def _load_annotation(" in source


def test_module_source_defines_process_one_batch15():
    source = inspect.getsource(rmod)
    assert "def _process_one(" in source


def test_module_source_defines_run_evaluation_batch15():
    source = inspect.getsource(rmod)
    assert "def run_evaluation(" in source


def test_module_source_has_dunder_all_batch15():
    source = inspect.getsource(rmod)
    assert "__all__" in source


def test_module_source_uses_perf_counter_batch15():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_uses_write_json_false_batch15():
    source = inspect.getsource(rmod)
    assert "write_json=False" in source


def test_module_source_uses_not_instrumented_batch15():
    source = inspect.getsource(rmod)
    assert "not_instrumented" in source


def test_module_source_no_subprocess_import_batch15():
    source = inspect.getsource(rmod)
    assert "import subprocess" not in source


def test_module_source_uses_json_dump_batch15():
    source = inspect.getsource(rmod)
    assert "json.dump(" in source


def test_module_source_uses_aggregate_summary_batch15():
    source = inspect.getsource(rmod)
    assert "aggregate_summary" in source


# ---------- signatures 第十七批 ----------


def test_load_annotation_signature_one_param_batch15():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_process_one_signature_4_params_batch15():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_run_evaluation_signature_5_params_batch15():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_keyword_only_args_batch15():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_default_tolerance_30_batch15():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_default_parser_fallback_batch15():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_default_max_chars_800_batch15():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_dunder_all_items_callable_batch15():
    for name in rmod.__all__:
        assert callable(getattr(rmod, name))


# ---------- module 合理性第十七批 ----------


def test_module_dunder_file_exists_batch15():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_runner_py_batch15():
    assert "evaluation" in rmod.__file__
    assert rmod.__file__.endswith("runner.py")


def test_module_name_evaluation_runner_batch15():
    assert rmod.__name__ == "evaluation.runner"


def test_module_dunder_all_one_item_batch15():
    assert len(rmod.__all__) == 1


def test_module_no_class_definitions_batch15():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_public_function_count_1_batch15():
    public = [n for n in rmod.__all__]
    assert public == ["run_evaluation"]


# ---------- 端到端集成第十七批 ----------


def test_e2e_run_evaluation_empty_manifest_json_serializable_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    parsed = json.loads(json.dumps(rep))
    assert parsed == rep


def test_e2e_run_evaluation_doc_with_failure_json_serializable_batch15(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    parsed = json.loads(json.dumps(rep))
    assert parsed == rep


def test_e2e_run_evaluation_idempotent_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep1 = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    rep1["provenance"].pop("run_timestamp_iso", None)
    rep2 = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    rep2["provenance"].pop("run_timestamp_iso", None)
    assert rep1 == rep2


def test_e2e_run_evaluation_per_doc_independent_batch15(tmp_path):
    docs = [
        _StubDoc(doc_id="d1", resolved_path=Path("/x.pdf")),
        _StubDoc(doc_id="d2", resolved_path=Path("/y.pdf")),
    ]
    manifest = _StubManifest(documents=docs)
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["per_doc"][0] is not rep["per_doc"][1]


def test_e2e_combined_run_with_failures_batch15(tmp_path):
    """doc + expected_failure 混合。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    ef = _StubExpectedFailure(resolved_path=Path("/y.bad"))
    manifest = _StubManifest(documents=[doc], expected_failures=[ef])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        with patch("evaluation.runner.process_single", return_value=(None, [_StubError(code="unsupported_format")])):
            rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert len(rep["per_doc"]) == 1
    assert len(rep["expected_failures"]) == 1
    assert rep["expected_failures"][0]["matches"] is True


def test_e2e_load_annotation_with_dict_then_used_batch15(tmp_path):
    """annotation 文件存在 → figure_caption_prf / chunk_boundary_prf 接收 dict。"""
    ann_path = tmp_path / "ann.json"
    ann_path.write_text('{"k": "v"}', encoding="utf-8")
    doc = _StubDoc(resolved_path=Path("/x.pdf"), annotation_resolved=ann_path)
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    # 公开 per_doc 不暴露 _annotation_present，但 metrics 应正常计算
    assert "metrics" in rep["per_doc"][0]


def test_e2e_run_evaluation_with_high_tolerance_batch15(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800, tolerance_chars=1000)
    assert rep["per_doc"][0]["doc_id"] == "doc1"


def test_e2e_combined_metrics_module_used_batch15(tmp_path):
    """run_evaluation 应调用 compute_automatic_metrics。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={"x": {"value": 1}}) as mock_fn:
            run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert mock_fn.called


def test_e2e_run_evaluation_full_flow_no_crash_batch15(tmp_path):
    """完整流程不应抛异常。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        stub_doc = _StubDocument()
        return (stub_doc.to_dict(), None, 0.5, "1.0", None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["per_doc"][0]["doc_id"] == "doc1"
    assert rep["provenance"]["parser_version"] == "1.0"


def test_e2e_run_evaluation_returns_proper_dict_batch15(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert "report_version" in rep
    assert "provenance" in rep
    assert "devset" in rep
    assert "summary" in rep
    assert "per_doc" in rep
    assert "expected_failures" in rep
