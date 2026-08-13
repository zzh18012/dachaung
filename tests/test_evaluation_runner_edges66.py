"""evaluation/runner.py 第六十六轮 edges 测试（Round 592）。

补强 edges65 未触及的角度（第三十八批）。
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


# ---------- _load_annotation 第三十八批


def test_load_annotation_returns_none_for_dev_null_batch38():
    """path 指向 /dev/null（is_file 可能 False）→ None。"""
    p = Path("/dev/null")
    assert _load_annotation(p) is None


def test_load_annotation_with_json_array_batch38(tmp_path):
    """JSON array 也能加载（类型不强校验）。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_with_json_int_batch38(tmp_path):
    """JSON int 也能加载。"""
    p = tmp_path / "i.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_with_json_string_batch38(tmp_path):
    """JSON string 也能加载。"""
    p = tmp_path / "s.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_with_json_bool_batch38(tmp_path):
    """JSON bool 也能加载。"""
    p = tmp_path / "b.json"
    p.write_text("true", encoding="utf-8")
    out = _load_annotation(p)
    assert out is True


def test_load_annotation_with_json_null_batch38(tmp_path):
    """JSON null → None（成功"加载"，不是失败）。"""
    p = tmp_path / "n.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_json_float_batch38(tmp_path):
    p = tmp_path / "f.json"
    p.write_text("3.14", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 3.14


def test_load_annotation_permission_error_returns_none_batch38(tmp_path):
    """OSError 被捕获 → None。"""
    p = tmp_path / "perm.json"
    p.write_text("{}", encoding="utf-8")
    original_open = Path.open
    def fake_open(self, *args, **kwargs):
        if self == p:
            raise PermissionError("denied")
        return original_open(self, *args, **kwargs)
    with patch.object(Path, "open", fake_open):
        out = _load_annotation(p)
    assert out is None


def test_load_annotation_is_file_check_batch38(tmp_path):
    """is_file() 是前置条件。"""
    p = tmp_path / "missing.json"
    # 不创建文件
    assert _load_annotation(p) is None


def test_load_annotation_signature_one_param_batch38():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_load_annotation_path_no_default_batch38():
    """path 是必填位置参数（annotation 是 'Path | None' 但无默认值）。"""
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_load_annotation_path_annotation_path_or_none_batch38():
    sig = inspect.signature(_load_annotation)
    ann = str(sig.parameters["path"].annotation)
    assert "Path" in ann
    assert "None" in ann


def test_load_annotation_return_annotation_dict_or_none_batch38():
    sig = inspect.signature(_load_annotation)
    ann = str(sig.return_annotation)
    assert "dict" in ann
    assert "None" in ann


def test_load_annotation_does_not_raise_on_empty_file_batch38(tmp_path):
    """空文件（合法 JSON 解析失败）→ None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


# ---------- _process_one 第三十八批


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


def _make_manifest_mock(documents=None, expected_failures=None,
                       project_root=None):
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path.cwd()
    # devset section 需要这些字段
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_process_one_signature_five_params_batch38():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_doc_no_default_batch38():
    sig = inspect.signature(_process_one)
    assert sig.parameters["doc"].default is inspect.Parameter.empty


def test_process_one_output_root_no_default_batch38():
    sig = inspect.signature(_process_one)
    assert sig.parameters["output_root"].default is inspect.Parameter.empty


def test_process_one_parser_name_no_default_batch38():
    sig = inspect.signature(_process_one)
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty


def test_process_one_max_chars_no_default_batch38():
    sig = inspect.signature(_process_one)
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


def test_process_one_returns_tuple_of_5_batch38(tmp_path):
    """成功路径返回 (dict, None, float, str|None, Path|None)。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"document_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc123"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            out = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(out, tuple)
    assert len(out) == 5
    document, error, elapsed, parser_version, image_dir = out
    assert document == {"document_id": "d1"}
    assert error is None
    assert isinstance(elapsed, float)
    assert parser_version == "1.0"
    assert image_dir == tmp_path / "imgs"


def test_process_one_returns_document_none_when_errors_batch38(tmp_path):
    """errors 非空 → document=None, error=errors[0].to_dict()。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    err_record = MagicMock()
    err_record.to_dict.return_value = {"code": "parse_failed"}
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    document, error, elapsed, parser_version, image_dir = out
    assert document is None
    assert error == {"code": "parse_failed"}
    assert parser_version is None


def test_process_one_creates_per_doc_dir_batch38(tmp_path):
    """output_root/_per_doc/<doc_id>.json 父目录应被创建。"""
    doc = _make_doc_mock(doc_id="mydoc", path=str(tmp_path / "x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _process_one(doc, tmp_path, "fallback", 800)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.is_dir()


def test_process_one_unlinks_out_stub_batch38(tmp_path):
    """out_stub 写完后应被删除（避免 _per_doc 残留 JSON）。"""
    doc = _make_doc_mock(doc_id="d1", path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"x": 1}
    fake_document.parser_version = "1"
    fake_document.source_hash = "abc"
    def fake_process_single(*args, **kwargs):
        # 模拟 pipeline 写盘
        out_path = args[1] if len(args) > 1 else kwargs.get("output_path")
        if out_path and not Path(out_path).exists():
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text("{}", encoding="utf-8")
        return fake_document, []
    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "fallback", 800)
    # out_stub 应被 unlink
    out_stub = tmp_path / "_per_doc" / "d1.json"
    assert not out_stub.exists()


def test_process_one_image_dir_none_when_document_none_batch38(tmp_path):
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    err_record = MagicMock()
    err_record.to_dict.return_value = {"code": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    _, _, _, _, image_dir = out
    assert image_dir is None


def test_process_one_elapsed_non_negative_batch38(tmp_path):
    """elapsed >= 0（time 单调）。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    _, _, elapsed, _, _ = out
    assert elapsed >= 0


def test_process_one_unknown_error_when_no_errors_no_document_batch38(tmp_path):
    """process_single 返回 (None, []) → unknown error。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    document, error, elapsed, parser_version, image_dir = out
    assert document is None
    assert error["code"] == "unknown"
    assert "process_single returned None" in error["message"]


# ---------- run_evaluation 第三十八批


def test_run_evaluation_signature_three_params_with_star_batch38():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_manifest_no_default_batch38():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_run_evaluation_parser_name_default_fallback_batch38():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_max_chars_default_800_batch38():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_tolerance_chars_default_30_batch38():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_parser_name_kw_only_batch38():
    """parser_name/max_chars/tolerance_chars 都是 keyword-only（* 之后）。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_manifest_positional_or_keyword_batch38():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_output_path_positional_or_keyword_batch38():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_creates_output_dir_batch38(tmp_path):
    """output_path 父目录不存在时自动创建。"""
    out_path = tmp_path / "deep" / "sub" / "report.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_returns_dict_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    out = run_evaluation(manifest, out_path)
    assert isinstance(out, dict)


def test_run_evaluation_report_has_six_top_keys_batch38(tmp_path):
    """顶层 keys: report_version / provenance / devset / summary / per_doc / expected_failures。"""
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
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


def test_run_evaluation_report_version_constant_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    out = run_evaluation(manifest, out_path)
    assert out["report_version"] == REPORT_VERSION


def test_run_evaluation_writes_file_with_indent_2_batch38(tmp_path):
    """输出文件用 indent=2 写。"""
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    run_evaluation(manifest, out_path)
    content = out_path.read_text(encoding="utf-8")
    # indent=2 → 有换行
    assert "\n" in content
    # ensure_ascii=False → 中文不转义


def test_run_evaluation_calls_process_one_per_doc_batch38(tmp_path):
    """每个 document 都调用一次 _process_one。"""
    out_path = tmp_path / "r.json"
    docs = [
        _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf")),
        _make_doc_mock(doc_id="d2", path=str(tmp_path / "b.pdf")),
        _make_doc_mock(doc_id="d3", path=str(tmp_path / "c.pdf")),
    ]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)) as mock:
        run_evaluation(manifest, out_path)
    assert mock.call_count == 3


def test_run_evaluation_per_doc_has_doc_id_source_type_metrics_wall_time_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    per_doc = out["per_doc"][0]
    assert "doc_id" in per_doc
    assert "source_type" in per_doc
    assert "metrics" in per_doc
    assert "wall_time_seconds" in per_doc


def test_run_evaluation_per_doc_excludes_internal_state_batch38(tmp_path):
    """public per_doc 不含 _annotation_present / _tolerance_chars / _missing_markers。"""
    out_path = tmp_path / "r.json"
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    per_doc = out["per_doc"][0]
    assert "_annotation_present" not in per_doc
    assert "_tolerance_chars" not in per_doc
    assert "_missing_markers" not in per_doc


def test_run_evaluation_wall_time_has_six_keys_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"))
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.123, None, None)):
        out = run_evaluation(manifest, out_path)
    wall = out["per_doc"][0]["wall_time_seconds"]
    expected = {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert set(wall.keys()) == expected
    assert wall["parse"] is None
    assert wall["chunk"] is None
    assert wall["parse_reason"] == "not_instrumented"
    assert wall["chunk_reason"] == "not_instrumented"
    assert wall["total"] == 0.123


def test_run_evaluation_expected_failures_processed_batch38(tmp_path):
    """expected_failures 在 manifest 中时被处理。"""
    out_path = tmp_path / "r.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(documents=[], expected_failures=[ef])
    err_record = MagicMock()
    err_record.code = "E_PARSE"
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        out = run_evaluation(manifest, out_path)
    assert len(out["expected_failures"]) == 1
    ef_out = out["expected_failures"][0]
    assert ef_out["doc_id"] == "ef1"
    assert ef_out["expected_error_code"] == "E_PARSE"
    assert ef_out["actual_error_code"] == "E_PARSE"
    assert ef_out["matches"] is True


def test_run_evaluation_expected_failure_mismatch_batch38(tmp_path):
    """expected vs actual 不匹配 → matches=False。"""
    out_path = tmp_path / "r.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(documents=[], expected_failures=[ef])
    err_record = MagicMock()
    err_record.code = "E_OTHER"
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        out = run_evaluation(manifest, out_path)
    assert out["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_no_errors_actual_none_batch38(tmp_path):
    """expected_failure 没产生 errors → actual_code=None。"""
    out_path = tmp_path / "r.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(documents=[], expected_failures=[ef])
    with patch("evaluation.runner.process_single", return_value=(MagicMock(), [])):
        out = run_evaluation(manifest, out_path)
    assert out["expected_failures"][0]["actual_error_code"] is None
    assert out["expected_failures"][0]["matches"] is False


def test_run_evaluation_no_documents_no_expected_failures_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    out = run_evaluation(manifest, out_path)
    assert out["per_doc"] == []
    assert out["expected_failures"] == []


# ---------- module source forbidden tokens 第六十五批


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
def test_module_source_no_forbidden_tokens_batch38(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十一批


def test_module_source_contains_design_doc_batch38():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_process_single_import_batch38():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import" in src
    assert "process_single" in src


def test_module_source_contains_image_output_dir_for_import_batch38():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src


def test_module_source_contains_compute_automatic_metrics_import_batch38():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_annotation_metrics_import_batch38():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_source_contains_report_import_batch38():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src


def test_module_source_contains_not_instrumented_keyword_batch38():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_load_annotation_function_batch38():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_function_batch38():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_function_batch38():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_perf_counter_call_batch38():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_json_dump_call_batch38():
    src = inspect.getsource(rmod)
    assert "json.dump(" in src


def test_module_source_contains_json_load_call_batch38():
    src = inspect.getsource(rmod)
    assert "json.load(f)" in src


def test_module_source_contains_encoding_utf8_batch38():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_pathlib_path_import_batch38():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch38():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_json_import_batch38():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_contains_time_import_batch38():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_contains_future_annotations_batch38():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_image_output_dir_for_call_batch38():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for(" in src


# ---------- module 合理性 第六十一批


def test_module_has_all_attribute_batch38():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch38():
    assert isinstance(rmod.__all__, list)


def test_module_all_only_run_evaluation_batch38():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_all_len_one_batch38():
    assert len(rmod.__all__) == 1


def test_module_does_not_export_helpers_batch38():
    for name in ("_load_annotation", "_process_one"):
        assert name not in rmod.__all__


def test_module_does_not_define_class_batch38():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_has_load_annotation_attribute_batch38():
    assert hasattr(rmod, "_load_annotation")


def test_module_has_process_one_attribute_batch38():
    assert hasattr(rmod, "_process_one")


def test_module_has_run_evaluation_attribute_batch38():
    assert hasattr(rmod, "run_evaluation")


# ---------- 端到端集成 第六十一批


def test_e2e_two_documents_batch38(tmp_path):
    """两个 doc 都被处理。"""
    out_path = tmp_path / "r.json"
    docs = [
        _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf")),
        _make_doc_mock(doc_id="d2", path=str(tmp_path / "b.pdf")),
    ]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    assert len(out["per_doc"]) == 2
    assert out["per_doc"][0]["doc_id"] == "d1"
    assert out["per_doc"][1]["doc_id"] == "d2"


def test_e2e_report_written_to_disk_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_e2e_report_json_loadable_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        run_evaluation(manifest, out_path)
    with out_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["report_version"] == REPORT_VERSION


def test_e2e_idempotent_batch38(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out1 = run_evaluation(manifest, out_path)
        out2 = run_evaluation(manifest, out_path)
    assert out1["report_version"] == out2["report_version"]


def test_e2e_with_annotation_present_batch38(tmp_path):
    """annotation_resolved 指向存在的文件 → _annotation_present=True（内部状态）。"""
    ann_path = tmp_path / "ann.json"
    ann_path.write_text("{}", encoding="utf-8")
    out_path = tmp_path / "r.json"
    doc = _make_doc_mock(path=str(tmp_path / "a.pdf"), annotation_resolved=ann_path)
    manifest = _make_manifest_mock(documents=[doc])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        out = run_evaluation(manifest, out_path)
    # public per_doc 不含 _annotation_present，但 per_doc 应有数据
    assert len(out["per_doc"]) == 1
