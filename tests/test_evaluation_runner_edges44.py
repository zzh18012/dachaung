"""evaluation/runner.py 第四十六轮 edges 测试（Round 438）。

补强 edges43 未触及的角度：
- _load_annotation 行为深度第十六批（BOM 失败 / multiline JSON / large JSON / OSError / JSONDecodeError / list JSON / 返回 None 的边界）
- _process_one 行为深度第十六批（成功路径返回 5-tuple / image_dir 不存在 / unlink 静默 / errors[0].to_dict / total_seconds 浮点 / parser_version 透传）
- run_evaluation 行为深度第十六批（6 keys / per_doc 4 keys / wall_time 6 keys / parser_version 取第一个非 None / max_chars 透传 / tolerance_chars 透传 / 文件写出 / json round-trip）
- module source forbidden tokens 第三十批
- module source 字符串精确补强第二十七批
- signatures 第二十七批
- module 合理性第二十七批
- 端到端集成第二十七批
"""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 行为深度第十六批 ----------


def test_load_annotation_none_path_batch16():
    """path=None → 直接返回 None（不抛）。"""
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_path_batch16(tmp_path):
    """path 指向不存在的文件 → None。"""
    assert _load_annotation(tmp_path / "no.json") is None


def test_load_annotation_valid_batch16(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"x": 1}


def test_load_annotation_bom_fails_batch16(tmp_path):
    """UTF-8 BOM 使 encoding='utf-8' 读取失败 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"x": 1}).encode("utf-8"))
    assert _load_annotation(p) is None


def test_load_annotation_multiline_batch16(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{\n  "a": 1,\n  "b": 2\n}', encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"a": 1, "b": 2}


def test_load_annotation_large_batch16(tmp_path):
    """10000 entries。"""
    p = tmp_path / "big.json"
    data = {f"k{i}": i for i in range(10000)}
    p.write_text(json.dumps(data), encoding="utf-8")
    r = _load_annotation(p)
    assert len(r) == 10000


def test_load_annotation_oserror_batch16(tmp_path):
    """模拟 OSError → None。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("boom")):
        assert _load_annotation(p) is None


def test_load_annotation_json_decode_error_batch16(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_list_json_batch16(tmp_path):
    """list JSON 也是合法 JSON，会被返回。"""
    p = tmp_path / "a.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    r = _load_annotation(p)
    assert r == [1, 2, 3]


def test_load_annotation_empty_file_batch16(tmp_path):
    """空文件 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_null_json_batch16(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    r = _load_annotation(p)
    assert r is None  # json.load 解析 null → None


def test_load_annotation_returns_dict_or_none_batch16(tmp_path):
    """正常路径返回 dict（或 list）。"""
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    r = _load_annotation(p)
    assert isinstance(r, dict)


# ---------- _process_one 行为深度第十六批 ----------


def _mk_doc():
    d = MagicMock()
    d.doc_id = "d1"
    d.resolved_path = Path("/fake/doc.pdf")
    d.source_type = "pdf"
    return d


def _mk_document():
    """fake Document 对象（process_single 成功返回的第一个值）。"""
    doc = MagicMock()
    doc.to_dict.return_value = {"elements": [], "chunks": [], "source_hash": "abc"}
    doc.parser_version = "1.0.0"
    doc.source_hash = "abc"
    return doc


def test_process_one_success_returns_5_tuple_batch16(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_success_document_dict_batch16(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        document, error, total, ver, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {"elements": [], "chunks": [], "source_hash": "abc"}
    assert error is None


def test_process_one_success_parser_version_batch16(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _, _, _, ver, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert ver == "1.0.0"


def test_process_one_total_seconds_is_float_batch16(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total, float)
    assert total >= 0


def test_process_one_errors_returns_error_dict_batch16(tmp_path):
    """process_single 返回 errors → _process_one 返回 errors[0].to_dict()。"""
    doc = _mk_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "parse_failed", "message": "boom"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        document, error, total, ver, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "parse_failed", "message": "boom"}
    assert ver is None


def test_process_one_document_none_no_errors_batch16(tmp_path):
    """document=None + errors=[] → 返回 unknown error dict。"""
    doc = _mk_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        document, error, total, ver, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error["code"] == "unknown"
    assert "process_single returned None" in error["message"]


def test_process_one_image_dir_none_when_document_none_batch16(tmp_path):
    doc = _mk_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_unlink_silent_on_oserror_batch16(tmp_path):
    """out_stub.is_file() True 但 unlink 抛 OSError → 不抛到外层。"""
    doc = _mk_doc()
    fake_doc = _mk_document()
    out_stub = tmp_path / "_per_doc" / "d1.json"
    out_stub.parent.mkdir(parents=True, exist_ok=True)
    out_stub.write_text("x")  # 创建文件

    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"), \
         patch("pathlib.Path.unlink", side_effect=OSError("nope")):
        # 不抛
        _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_calls_process_single_with_correct_args_batch16(tmp_path):
    """验证 _process_one 用正确的 args 调 process_single。"""
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])) as mock_ps, \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _process_one(doc, tmp_path, "fallback", 800)
    args, kwargs = mock_ps.call_args
    # 位置参数 + 关键字参数
    assert args[0] == doc.resolved_path
    assert kwargs.get("parser_name") == "fallback"
    assert kwargs.get("max_chars") == 800
    assert kwargs.get("write_json") is False


def test_process_one_image_dir_returned_batch16(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    fake_dir = tmp_path / "imgs"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=fake_dir) as mock_idir:
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == fake_dir
    # image_output_dir_for 应该用 (out_stub, source_hash) 调
    args, _ = mock_idir.call_args
    assert args[1] == "abc"  # source_hash


# ---------- run_evaluation 行为深度第十六批 ----------


def _mk_manifest_empty():
    """空 manifest（无 documents 无 expected_failures）。"""
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


def test_run_evaluation_returns_dict_batch16(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert isinstance(r, dict)


def test_run_evaluation_report_keys_batch16(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    expected = {"report_version", "provenance", "devset", "summary",
                "per_doc", "expected_failures"}
    assert set(r.keys()) == expected


def test_run_evaluation_writes_file_batch16(tmp_path):
    out = tmp_path / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    assert out.is_file()


def test_run_evaluation_file_is_valid_json_batch16(tmp_path):
    out = tmp_path / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert "report_version" in data


def test_run_evaluation_returns_same_as_file_batch16(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert r == data


def test_run_evaluation_per_doc_empty_batch16(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert r["per_doc"] == []
    assert r["expected_failures"] == []


def test_run_evaluation_max_chars_transparent_batch16(tmp_path):
    """max_chars 透传到 _process_one → process_single。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])) as ps, \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        run_evaluation(m, out, max_chars=1234)
    _, kwargs = ps.call_args
    assert kwargs["max_chars"] == 1234


def test_run_evaluation_tolerance_chars_transparent_batch16(tmp_path):
    """tolerance_chars 透传到 chunk_boundary_prf。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None), \
         patch("evaluation.runner.chunk_boundary_prf") as cbp:
        cbp.return_value = {
            "chunk_boundary_precision": {"value": None, "reason": "x"},
            "chunk_boundary_recall": {"value": None, "reason": "x"},
            "chunk_boundary_f1": {"value": None, "reason": "x"},
        }
        run_evaluation(m, out, tolerance_chars=99)
    _, kwargs = cbp.call_args
    assert kwargs["tolerance_chars"] == 99


def test_run_evaluation_parser_version_first_kept_batch16(tmp_path):
    """parser_version 取第一个非 None（即使后续不同也不覆盖）。"""
    m = _mk_manifest_empty()
    doc1 = _mk_doc(); doc1.doc_id = "d1"
    doc2 = _mk_doc(); doc2.doc_id = "d2"
    m.documents = [doc1, doc2]

    fd1 = _mk_document(); fd1.parser_version = "1.0.0"
    fd2 = _mk_document(); fd2.parser_version = "2.0.0"

    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single",
               side_effect=[(fd1, []), (fd2, [])]), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    assert r["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_wall_time_keys_batch16(tmp_path):
    """per_doc 的 wall_time_seconds 应有 6 个 key。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    assert len(r["per_doc"]) == 1
    wt = r["per_doc"][0]["wall_time_seconds"]
    expected_wt = {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert set(wt.keys()) == expected_wt


def test_run_evaluation_wall_time_parse_chunk_null_batch16(tmp_path):
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
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_per_doc_keys_batch16(tmp_path):
    """public per_doc 应有 4 个 key（doc_id/source_type/metrics/wall_time_seconds）。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    assert set(r["per_doc"][0].keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_creates_parent_dir_batch16(tmp_path):
    """output_path 的 parent 不存在时应创建。"""
    out = tmp_path / "subdir1" / "subdir2" / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    assert out.is_file()


def test_run_evaluation_expected_failure_matches_batch16(tmp_path):
    """expected_failure 匹配判断。"""
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
    ef_r = r["expected_failures"][0]
    assert ef_r["doc_id"] == "bad1"
    assert ef_r["expected_error_code"] == "unsupported_format"
    assert ef_r["actual_error_code"] == "unsupported_format"
    assert ef_r["matches"] is True


def test_run_evaluation_expected_failure_no_match_batch16(tmp_path):
    """actual != expected → matches False。"""
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


def test_run_evaluation_expected_failure_no_errors_batch16(tmp_path):
    """expected_failure 但 process_single 成功 → actual_error_code=None, matches=False。"""
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


# ---------- module source forbidden tokens 第三十批 ----------


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
def test_module_source_forbidden_tokens_batch16(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch16():
    """runner.py 不应用 subprocess（report.py 才用）。"""
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch16():
    src = inspect.getsource(rmod)
    assert "urllib.request" not in src
    assert "import requests" not in src
    assert "http.client" not in src


# ---------- module source 字符串精确补强第二十七批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch16():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_has_time_import_batch16():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_json_import_batch16():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_pathlib_import_batch16():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch16():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch16():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_annotation_metrics_import_batch16():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_has_metrics_import_batch16():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import_batch16():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_has_load_annotation_function_batch16():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_has_process_one_function_batch16():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_has_run_evaluation_function_batch16():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_has_perf_counter_batch16():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_has_process_single_call_batch16():
    src = inspect.getsource(rmod)
    assert "process_single(" in src


def test_module_source_has_write_json_false_batch16():
    src = inspect.getsource(rmod)
    assert "write_json=False" in src


def test_module_source_has_compute_metrics_call_batch16():
    src = inspect.getsource(rmod)
    assert "compute_automatic_metrics(" in src


def test_module_source_has_aggregate_summary_call_batch16():
    src = inspect.getsource(rmod)
    assert "aggregate_summary(" in src


def test_module_source_has_build_provenance_call_batch16():
    src = inspect.getsource(rmod)
    assert "build_provenance(" in src


def test_module_source_has_build_devset_call_batch16():
    src = inspect.getsource(rmod)
    assert "build_devset_section(" in src


def test_module_source_has_not_instrumented_batch16():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_has_all_dunder_batch16():
    src = inspect.getsource(rmod)
    assert "__all__ = " in src


# ---------- signatures 第二十七批 ----------


def test_signature_load_annotation_batch16():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_signature_process_one_batch16():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_batch16():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch16():
    sig = inspect.signature(run_evaluation)
    # parser_name / max_chars / tolerance_chars 应是 keyword-only
    for name in ("parser_name", "max_chars", "tolerance_chars"):
        assert sig.parameters[name].kind == sig.parameters[name].KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch16():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_load_annotation_no_varargs_batch16():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第二十七批 ----------


def test_module_has_all_attribute_batch16():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_items_in_namespace_batch16():
    for name in rmod.__all__:
        assert hasattr(rmod, name)


def test_module_all_count_1_batch16():
    assert len(rmod.__all__) == 1


def test_module_run_evaluation_callable_batch16():
    assert callable(run_evaluation)


def test_module_load_annotation_callable_batch16():
    assert callable(_load_annotation)


def test_module_process_one_callable_batch16():
    assert callable(_process_one)


def test_module_does_not_import_subprocess_batch16():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src


def test_module_does_not_import_unsafe_modules_batch16():
    src = inspect.getsource(rmod)
    for unsafe in ["import pickle", "import marshal", "import shelve"]:
        assert unsafe not in src


# ---------- 端到端集成第二十七批 ----------


def test_e2e_run_evaluation_full_round_trip_batch16(tmp_path):
    """完整 round-trip：manifest with 1 doc → run → output file。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    assert r["report_version"] is not None
    assert len(r["per_doc"]) == 1
    assert r["per_doc"][0]["doc_id"] == "d1"
    assert "metrics" in r["per_doc"][0]


def test_e2e_load_then_run_annotation_batch16(tmp_path):
    """annotation 文件被加载并传给 chunk_boundary_prf / figure_caption_prf。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    fake_ann = {"anchors": []}
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=fake_ann), \
         patch("evaluation.runner.figure_caption_prf") as fc, \
         patch("evaluation.runner.chunk_boundary_prf") as cb:
        fc.return_value = {
            "figure_caption_precision": {"value": None, "reason": "x"},
            "figure_caption_recall": {"value": None, "reason": "x"},
            "figure_caption_f1": {"value": None, "reason": "x"},
        }
        cb.return_value = {
            "chunk_boundary_precision": {"value": None, "reason": "x"},
            "chunk_boundary_recall": {"value": None, "reason": "x"},
            "chunk_boundary_f1": {"value": None, "reason": "x"},
        }
        run_evaluation(m, out)
    # 验证 figure_caption_prf 被传 annotation
    fc_args, _ = fc.call_args
    assert fc_args[1] == fake_ann
    cb_args, _ = cb.call_args
    assert cb_args[1] == fake_ann


def test_e2e_run_evaluation_with_failed_doc_batch16(tmp_path):
    """失败 doc → metrics 多为 null + reason=pipeline_failed。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    err = MagicMock()
    err.to_dict.return_value = {"code": "parse_failed", "message": "boom"}
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    pd = r["per_doc"][0]
    assert pd["metrics"]["pipeline_success"]["value"] is False
    assert pd["metrics"]["error_code"]["value"] == "parse_failed"


def test_e2e_run_evaluation_multiple_docs_batch16(tmp_path):
    """多个 doc 都应出现在 per_doc。"""
    m = _mk_manifest_empty()
    doc1 = _mk_doc(); doc1.doc_id = "d1"
    doc2 = _mk_doc(); doc2.doc_id = "d2"
    doc3 = _mk_doc(); doc3.doc_id = "d3"
    m.documents = [doc1, doc2, doc3]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    assert len(r["per_doc"]) == 3
    ids = [p["doc_id"] for p in r["per_doc"]]
    assert ids == ["d1", "d2", "d3"]


def test_e2e_run_evaluation_summary_present_batch16(tmp_path):
    """report 含 summary section。"""
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert "summary" in r
    assert isinstance(r["summary"], dict)


def test_e2e_run_evaluation_provenance_present_batch16(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert "provenance" in r
    assert "evaluator_version" in r["provenance"]


def test_e2e_load_annotation_idempotent_batch16(tmp_path):
    """同一文件多次加载结果一致。"""
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    r1 = _load_annotation(p)
    r2 = _load_annotation(p)
    assert r1 == r2


def test_e2e_run_evaluation_devset_section_batch16(tmp_path):
    """devset section 来自 manifest。"""
    m = _mk_manifest_empty()
    m.devset_status = "complete"
    m.file_count = 5
    out = tmp_path / "out.json"
    r = run_evaluation(m, out)
    assert r["devset"]["status"] == "complete"
    assert r["devset"]["file_count"] == 5
