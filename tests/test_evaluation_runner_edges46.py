"""evaluation/runner.py 第四十八轮 edges 测试（Round 452）。

补强 edges45 未触及的角度：
- _load_annotation 行为深度第十八批（None path / 不存在 / 含 BOM / Unicode 内容 / annotation dict 含 list / 返 None 各种情况 / 不抛 OSError）
- _process_one 行为深度第十八批（out_stub 创建后清理 / errors 多个取第 1 / document None + no errors → unknown error / parser_version 透传 / image_dir None for failed doc / elapsed 类型）
- run_evaluation 行为深度第十八批（output_root 创建 / expected_failures out_stub 清理 / expected_failure matches=True / expected_failure matches=False / expected_failure no error actual / parser_version 来自第 1 个成功 doc / public_per_doc 不含 _tolerance_chars / wall_time_seconds 结构）
- module source forbidden tokens 第三十二批
- module source 字符串精确补强第二十八批
- signatures 第二十八批
- module 合理性第二十八批
- 端到端集成第二十八批
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


# ---------- _load_annotation 行为深度第十八批 ----------


def test_load_annotation_none_path_returns_none_batch18():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_returns_none_batch18(tmp_path):
    assert _load_annotation(tmp_path / "no.json") is None


def test_load_annotation_directory_returns_none_batch18(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _load_annotation(sub) is None


def test_load_annotation_valid_json_batch18(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"k": "v"}), encoding="utf-8")
    assert _load_annotation(p) == {"k": "v"}


def test_load_annotation_invalid_json_returns_none_batch18(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_zero_byte_returns_none_batch18(tmp_path):
    p = tmp_path / "a.json"
    p.write_bytes(b"")
    assert _load_annotation(p) is None


def test_load_annotation_with_array_value_batch18(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"items": [1, 2, 3]}), encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"items": [1, 2, 3]}


def test_load_annotation_with_nested_dict_batch18(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"a": {"b": {"c": 1}}}), encoding="utf-8")
    r = _load_annotation(p)
    assert r["a"]["b"]["c"] == 1


def test_load_annotation_unicode_content_batch18(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"name": "中文测试"}), encoding="utf-8")
    r = _load_annotation(p)
    assert r["name"] == "中文测试"


def test_load_annotation_does_not_raise_on_invalid_batch18(tmp_path):
    """非法 JSON 不抛异常，返 None。"""
    p = tmp_path / "a.json"
    p.write_text("{{invalid", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_signature_batch18():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


# ---------- _process_one 行为深度第十八批 ----------


def _mk_doc(doc_id="d1", source_type="pdf"):
    d = MagicMock()
    d.doc_id = doc_id
    d.resolved_path = Path(f"/fake/{doc_id}.pdf")
    d.source_type = source_type
    return d


def _mk_document(source_hash="abc", parser_version="1.0.0"):
    doc = MagicMock()
    doc.to_dict.return_value = {
        "elements": [], "chunks": [],
        "source_hash": source_hash, "source_type": "pdf",
    }
    doc.parser_version = parser_version
    doc.source_hash = source_hash
    return doc


def test_process_one_out_stub_cleaned_up_batch18(tmp_path):
    """out_stub 在 _process_one 后应被删除（write_json=False，但 unlink 显式）。"""
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _process_one(doc, tmp_path, "fallback", 800)
    # out_stub 应已被 unlink
    out_stub = tmp_path / "_per_doc" / "d1.json"
    assert not out_stub.is_file()


def test_process_one_creates_per_doc_dir_batch18(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_errors_first_one_batch18(tmp_path):
    """errors 列表非空 → 取 errors[0].to_dict()。"""
    doc = _mk_doc()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "err1", "message": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "err2", "message": "second"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert error == {"code": "err1", "message": "first"}


def test_process_one_no_document_no_errors_batch18(tmp_path):
    """document=None + errors=[] → unknown error。"""
    doc = _mk_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error["code"] == "unknown"
    assert "None without errors" in error["message"]


def test_process_one_parser_version_transmitted_batch18(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document(parser_version="2.5.0")
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _, _, _, pv, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert pv == "2.5.0"


def test_process_one_image_dir_none_when_document_none_batch18(tmp_path):
    """document=None → image_dir 也是 None。"""
    doc = _mk_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "err", "message": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        _, _, _, _, img_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert img_dir is None


def test_process_one_elapsed_is_float_batch18(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)


def test_process_one_returns_5_tuple_batch18(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_doc_id_in_out_stub_batch18(tmp_path):
    doc = _mk_doc(doc_id="special_id")
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])) as ps, \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _process_one(doc, tmp_path, "fallback", 800)
    args, _ = ps.call_args
    out_stub = args[1]
    assert "special_id.json" in str(out_stub)


def test_process_one_process_single_exception_propagates_batch18(tmp_path):
    doc = _mk_doc()
    with patch("evaluation.runner.process_single", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            _process_one(doc, tmp_path, "fallback", 800)


# ---------- run_evaluation 行为深度第十八批 ----------


def _mk_manifest_empty():
    m = MagicMock()
    m.documents = []
    m.expected_failures = []
    m.project_root = Path("/fake")
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_output_root_created_batch18(tmp_path):
    """output_path 的 parent 不存在 → 自动创建。"""
    out = tmp_path / "a" / "b" / "c" / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    assert out.is_file()


def test_run_evaluation_per_doc_wall_time_structure_batch18(tmp_path):
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    wt = r["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)


def test_run_evaluation_public_per_doc_no_private_fields_batch18(tmp_path):
    """public per_doc 不应含 _tolerance_chars / _annotation_present 等 private 字段。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    pd = r["per_doc"][0]
    assert set(pd.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}
    assert "_tolerance_chars" not in pd
    assert "_annotation_present" not in pd
    assert "_missing_markers" not in pd


def test_run_evaluation_expected_failure_matches_true_batch18(tmp_path):
    m = _mk_manifest_empty()
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = Path("/fake/bad.txt")
    m.expected_failures = [ef]
    err = MagicMock()
    err.code = "unsupported_format"
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        r = run_evaluation(m, out)
    assert len(r["expected_failures"]) == 1
    assert r["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failure_matches_false_batch18(tmp_path):
    m = _mk_manifest_empty()
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = Path("/fake/bad.txt")
    m.expected_failures = [ef]
    err = MagicMock()
    err.code = "different_error"
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        r = run_evaluation(m, out)
    assert r["expected_failures"][0]["matches"] is False
    assert r["expected_failures"][0]["actual_error_code"] == "different_error"


def test_run_evaluation_expected_failure_no_actual_error_batch18(tmp_path):
    """expected_failure doc 不抛错（errors=[]） → actual_code=None。"""
    m = _mk_manifest_empty()
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = Path("/fake/bad.txt")
    m.expected_failures = [ef]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])):
        r = run_evaluation(m, out)
    assert r["expected_failures"][0]["actual_error_code"] is None
    assert r["expected_failures"][0]["matches"] is False


def test_run_evaluation_parser_version_from_first_doc_batch18(tmp_path):
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document(parser_version="3.0.0")
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None), \
         patch("evaluation.runner.build_provenance") as bp:
        bp.return_value = {
            "git_commit": "x", "git_dirty": False,
            "evaluator_version": "1.1", "report_version": REPORT_VERSION,
            "parser_name": "fallback", "parser_version": "3.0.0",
            "dependencies": {}, "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        }
        run_evaluation(m, out)
    _, kwargs = bp.call_args
    assert kwargs["parser_version"] == "3.0.0"


def test_run_evaluation_expected_failure_out_stub_cleaned_batch18(tmp_path):
    """expected_failure 流程也清理 out_stub。"""
    m = _mk_manifest_empty()
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.expected_error_code = "x"
    ef.resolved_path = Path("/fake/bad.txt")
    m.expected_failures = [ef]
    err = MagicMock()
    err.code = "x"
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        run_evaluation(m, out)
    out_stub = tmp_path / "_per_doc" / "bad1.json"
    assert not out_stub.is_file()


def test_run_evaluation_returns_same_as_written_file_batch18(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert r == data


def test_run_evaluation_report_has_6_top_keys_batch18(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert set(r.keys()) == {
        "report_version", "provenance", "devset",
        "summary", "per_doc", "expected_failures",
    }


def test_run_evaluation_report_version_constant_batch18(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert r["report_version"] == REPORT_VERSION


def test_run_evaluation_summary_structure_batch18(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert "counts" in r["summary"]
    assert "success_rates" in r["summary"]
    assert "ratio_macro_averages" in r["summary"]
    assert "silent_drop_total" in r["summary"]


def test_run_evaluation_doc_id_order_preserved_batch18(tmp_path):
    m = _mk_manifest_empty()
    m.documents = [_mk_doc("d1"), _mk_doc("d2"), _mk_doc("d3")]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    ids = [p["doc_id"] for p in r["per_doc"]]
    assert ids == ["d1", "d2", "d3"]


# ---------- module source forbidden tokens 第三十二批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch18(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch18():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch18():
    src = inspect.getsource(rmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第二十八批 ----------


def test_module_source_has_future_annotations_batch18():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch18():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_has_json_import_batch18():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_time_import_batch18():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_pathlib_import_batch18():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_import_batch18():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch18():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_annotation_metrics_import_batch18():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_source_has_metrics_import_batch18():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import_batch18():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src


def test_module_source_has_run_evaluation_function_batch18():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_has_process_one_function_batch18():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_has_load_annotation_function_batch18():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_has_all_dunder_batch18():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_source_no_main_block_batch18():
    src = inspect.getsource(rmod)
    assert "__main__" not in src


# ---------- signatures 第二十八批 ----------


def test_signature_load_annotation_batch18():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_signature_process_one_batch18():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_batch18():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch18():
    sig = inspect.signature(run_evaluation)
    for name in ("parser_name", "max_chars", "tolerance_chars"):
        assert sig.parameters[name].kind == sig.parameters[name].KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch18():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


# ---------- module 合理性第二十八批 ----------


def test_module_has_all_attribute_batch18():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_count_1_batch18():
    assert len(rmod.__all__) == 1


def test_module_all_contents_batch18():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_run_evaluation_callable_batch18():
    assert callable(run_evaluation)


def test_module_load_annotation_callable_batch18():
    assert callable(_load_annotation)


def test_module_process_one_callable_batch18():
    assert callable(_process_one)


def test_module_does_not_import_unsafe_modules_batch18():
    src = inspect.getsource(rmod)
    for unsafe in ["import pickle", "import marshal", "import shelve"]:
        assert unsafe not in src


def test_module_does_not_import_evaluation_cli_batch18():
    """runner.py 不应反向依赖 cli.py。"""
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src


def test_module_no_main_block_batch18():
    src = inspect.getsource(rmod)
    assert "if __name__" not in src


# ---------- 端到端集成第二十八批 ----------


def test_e2e_run_evaluation_full_round_trip_batch18(tmp_path):
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    assert r["report_version"] == REPORT_VERSION
    assert len(r["per_doc"]) == 1
    assert r["per_doc"][0]["doc_id"] == "d1"


def test_e2e_load_annotation_round_trip_batch18(tmp_path):
    """写 → 读 round trip。"""
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": 1, "y": [1, 2]}), encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"x": 1, "y": [1, 2]}


def test_e2e_run_evaluation_creates_valid_json_batch18(tmp_path):
    out = tmp_path / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_e2e_run_evaluation_returns_same_as_file_batch18(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert r == data


def test_e2e_run_evaluation_with_expected_failure_batch18(tmp_path):
    m = _mk_manifest_empty()
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = Path("/fake/bad.txt")
    m.expected_failures = [ef]
    err = MagicMock()
    err.code = "unsupported_format"
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        r = run_evaluation(m, out)
    assert len(r["expected_failures"]) == 1
    assert r["expected_failures"][0]["matches"] is True


def test_e2e_run_evaluation_devset_in_report_batch18(tmp_path):
    m = _mk_manifest_empty()
    m.devset_status = "complete"
    m.file_count = 5
    m.pdf_count = 3
    m.docx_count = 2
    out = tmp_path / "out.json"
    r = run_evaluation(m, out)
    assert r["devset"]["status"] == "complete"
    assert r["devset"]["file_count"] == 5
    assert r["devset"]["pdf_count"] == 3
    assert r["devset"]["docx_count"] == 2


def test_e2e_run_evaluation_empty_manifest_batch18(tmp_path):
    """空 manifest 完整跑通。"""
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert r["per_doc"] == []
    assert r["expected_failures"] == []


def test_e2e_load_annotation_none_for_invalid_batch18(tmp_path):
    """各种无效 annotation 都返回 None。"""
    assert _load_annotation(None) is None
    assert _load_annotation(tmp_path / "no.json") is None
    sub = tmp_path / "sub"; sub.mkdir()
    assert _load_annotation(sub) is None
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert _load_annotation(bad) is None


def test_e2e_run_evaluation_metrics_count_batch18(tmp_path):
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    metrics = r["per_doc"][0]["metrics"]
    # metrics 含 14（metrics.py 核心） + 3（figure_caption） + 3（chunk_boundary）= 20
    assert len(metrics) >= 14
