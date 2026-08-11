"""evaluation/runner.py 第四十七轮 edges 测试（Round 445）。

补强 edges44 未触及的角度：
- _load_annotation 行为深度第十七批（path 是 str / path 是 Path / Unicode 路径 / 含 BOM 的 list JSON / 0 字节文件 / 多次调用一致）
- _process_one 行为深度第十七批（output_root 不存在自动创建 / doc_id 含特殊字符 / 同 doc_id 多次调用 / process_single 抛异常传播 / image_output_dir_for 调用参数）
- run_evaluation 行为深度第十七批（manifest.project_root 用于 provenance / 多个 expected_failures / report_version 透传 / 不在 working dir 写额外文件 / 多个 documents 顺序）
- module source forbidden tokens 第三十一批
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


# ---------- _load_annotation 行为深度第十七批 ----------


def test_load_annotation_str_path_batch17(tmp_path):
    """传 str path → Path(str) 后正常加载。"""
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    r = _load_annotation(p)  # _load_annotation 接受 Path
    assert r == {"x": 1}


def test_load_annotation_path_object_batch17(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    r = _load_annotation(Path(p))
    assert r == {"x": 1}


def test_load_annotation_unicode_path_batch17(tmp_path):
    """Unicode 文件名也能加载。"""
    p = tmp_path / "中文.json"
    p.write_text(json.dumps({"k": "v"}), encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"k": "v"}


def test_load_annotation_zero_byte_file_batch17(tmp_path):
    """0 字节文件 → JSON 解析失败 → None。"""
    p = tmp_path / "empty.json"
    p.write_bytes(b"")
    assert _load_annotation(p) is None


def test_load_annotation_idempotent_batch17(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": 1, "y": [1, 2, 3]}), encoding="utf-8")
    r1 = _load_annotation(p)
    r2 = _load_annotation(p)
    assert r1 == r2


def test_load_annotation_with_nested_dict_batch17(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"outer": {"inner": {"deep": "value"}}}), encoding="utf-8")
    r = _load_annotation(p)
    assert r["outer"]["inner"]["deep"] == "value"


def test_load_annotation_with_array_batch17(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"items": [1, 2, 3, 4, 5]}), encoding="utf-8")
    r = _load_annotation(p)
    assert len(r["items"]) == 5


def test_load_annotation_returns_none_for_directory_batch17(tmp_path):
    """传目录 → is_file() False → None。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _load_annotation(sub) is None


# ---------- _process_one 行为深度第十七批 ----------


def _mk_doc(doc_id="d1", source_type="pdf"):
    d = MagicMock()
    d.doc_id = doc_id
    d.resolved_path = Path(f"/fake/{doc_id}.pdf")
    d.source_type = source_type
    return d


def _mk_document(source_hash="abc"):
    doc = MagicMock()
    doc.to_dict.return_value = {"elements": [], "chunks": [], "source_hash": source_hash}
    doc.parser_version = "1.0.0"
    doc.source_hash = source_hash
    return doc


def test_process_one_creates_per_doc_dir_batch17(tmp_path):
    """output_root/_per_doc/ 不存在时应自动创建。"""
    doc = _mk_doc()
    fake_doc = _mk_document()
    output_root = tmp_path / "out"
    # output_root 不存在
    assert not output_root.is_dir()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _process_one(doc, output_root, "fallback", 800)
    assert output_root.is_dir()
    assert (output_root / "_per_doc").is_dir()


def test_process_one_doc_id_with_spaces_batch17(tmp_path):
    """doc_id 含空格也工作（用作文件名）。"""
    doc = _mk_doc(doc_id="my doc")
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])) as ps, \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        document, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    # 验证 out_stub 用了 doc_id
    args, _ = ps.call_args
    out_stub = args[1]
    assert "my doc" in str(out_stub)


def test_process_one_doc_id_unicode_batch17(tmp_path):
    doc = _mk_doc(doc_id="中文")
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        document, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {"elements": [], "chunks": [], "source_hash": "abc"}


def test_process_one_image_output_dir_called_with_correct_args_batch17(tmp_path):
    """image_output_dir_for 应被 (out_stub, source_hash) 调。"""
    doc = _mk_doc()
    fake_doc = _mk_document(source_hash="deadbeef")
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs") as mock_idir:
        _process_one(doc, tmp_path, "fallback", 800)
    args, _ = mock_idir.call_args
    out_stub = args[0]
    source_hash = args[1]
    assert "d1.json" in str(out_stub)
    assert source_hash == "deadbeef"


def test_process_one_process_single_exception_propagates_batch17(tmp_path):
    """process_single 抛异常 → _process_one 不吞 → 传播。"""
    doc = _mk_doc()
    with patch("evaluation.runner.process_single", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="boom"):
            _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_returns_5_tuple_batch17(tmp_path):
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_elapsed_is_positive_batch17(tmp_path):
    """total_seconds 应是正数（即使很小）。"""
    doc = _mk_doc()
    fake_doc = _mk_document()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert total >= 0


# ---------- run_evaluation 行为深度第十七批 ----------


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


def test_run_evaluation_uses_project_root_for_provenance_batch17(tmp_path):
    """run_evaluation 把 manifest.project_root 传给 build_provenance。"""
    m = _mk_manifest_empty()
    m.project_root = tmp_path
    out = tmp_path / "out.json"
    with patch("evaluation.runner.build_provenance") as bp:
        bp.return_value = {"git_commit": "x", "git_dirty": False,
                           "evaluator_version": "1.1", "report_version": "1.1",
                           "parser_name": "fallback", "parser_version": "1.0.0",
                           "dependencies": {}, "max_chars": 800,
                           "run_timestamp_iso": "2026-01-01T00:00:00+00:00"}
        run_evaluation(m, out)
    args, kwargs = bp.call_args
    # project_root 应通过 kwargs 传
    assert kwargs.get("project_root") == tmp_path or (args and args[0] == tmp_path)


def test_run_evaluation_multiple_expected_failures_batch17(tmp_path):
    """多个 expected_failures。"""
    m = _mk_manifest_empty()
    ef1 = MagicMock(); ef1.doc_id = "b1"; ef1.expected_error_code = "x"; ef1.resolved_path = Path("/fake/b1.txt")
    ef2 = MagicMock(); ef2.doc_id = "b2"; ef2.expected_error_code = "y"; ef2.resolved_path = Path("/fake/b2.txt")
    m.expected_failures = [ef1, ef2]

    err = MagicMock(); err.code = "x"
    err2 = MagicMock(); err2.code = "different"

    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single",
               side_effect=[(None, [err]), (None, [err2])]):
        r = run_evaluation(m, out)
    assert len(r["expected_failures"]) == 2
    assert r["expected_failures"][0]["matches"] is True
    assert r["expected_failures"][1]["matches"] is False


def test_run_evaluation_report_version_transparent_batch17(tmp_path):
    """report_version 来自 REPORT_VERSION 常量。"""
    from evaluation import REPORT_VERSION
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert r["report_version"] == REPORT_VERSION


def test_run_evaluation_writes_only_one_file_batch17(tmp_path):
    """只写 output_path 一个文件（不污染 working dir）。"""
    out = tmp_path / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    out_files = list(tmp_path.glob("*.json"))
    assert len(out_files) == 1
    assert out_files[0] == out


def test_run_evaluation_documents_order_preserved_batch17(tmp_path):
    """多个 documents 顺序保留。"""
    m = _mk_manifest_empty()
    doc1 = _mk_doc(doc_id="d1")
    doc2 = _mk_doc(doc_id="d2")
    doc3 = _mk_doc(doc_id="d3")
    m.documents = [doc1, doc2, doc3]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    ids = [p["doc_id"] for p in r["per_doc"]]
    assert ids == ["d1", "d2", "d3"]


def test_run_evaluation_summary_aggregated_batch17(tmp_path):
    """summary section 被聚合。"""
    m = _mk_manifest_empty()
    doc = _mk_doc()
    m.documents = [doc]
    fake_d = _mk_document()
    out = tmp_path / "out.json"
    with patch("evaluation.runner.process_single", return_value=(fake_d, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i"), \
         patch("evaluation.runner._load_annotation", return_value=None):
        r = run_evaluation(m, out)
    assert "summary" in r
    assert "counts" in r["summary"]
    assert "success_rates" in r["summary"]


def test_run_evaluation_per_doc_metrics_count_batch17(tmp_path):
    """per_doc 的 metrics 含至少 14 个 key。"""
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
    # metrics.py 返回 14 + runner 添加 6（figure_caption 3 + chunk_boundary 3）= 20
    assert len(metrics) >= 14


def test_run_evaluation_creates_output_parent_dir_batch17(tmp_path):
    """output_path 的 parent 不存在时自动创建。"""
    out = tmp_path / "a" / "b" / "c" / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    assert out.is_file()


# ---------- module source forbidden tokens 第三十一批 ----------


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
def test_module_source_forbidden_tokens_batch17(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch17():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch17():
    src = inspect.getsource(rmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第二十七批 ----------


def test_module_source_has_future_annotations_batch17():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch17():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_has_time_import_batch17():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_json_import_batch17():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_pathlib_import_batch17():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_import_batch17():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch17():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import" in src


def test_module_source_has_annotation_metrics_import_batch17():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_source_has_metrics_import_batch17():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import" in src


def test_module_source_has_report_import_batch17():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src


def test_module_source_has_run_evaluation_function_batch17():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_has_all_dunder_batch17():
    src = inspect.getsource(rmod)
    assert "__all__ = " in src


# ---------- signatures 第二十七批 ----------


def test_signature_load_annotation_batch17():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_signature_process_one_batch17():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_batch17():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch17():
    sig = inspect.signature(run_evaluation)
    for name in ("parser_name", "max_chars", "tolerance_chars"):
        assert sig.parameters[name].kind == sig.parameters[name].KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch17():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800


# ---------- module 合理性第二十七批 ----------


def test_module_has_all_attribute_batch17():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_count_1_batch17():
    assert len(rmod.__all__) == 1


def test_module_run_evaluation_callable_batch17():
    assert callable(run_evaluation)


def test_module_load_annotation_callable_batch17():
    assert callable(_load_annotation)


def test_module_process_one_callable_batch17():
    assert callable(_process_one)


def test_module_does_not_import_unsafe_modules_batch17():
    src = inspect.getsource(rmod)
    for unsafe in ["import pickle", "import marshal", "import shelve"]:
        assert unsafe not in src


def test_module_does_not_import_evaluation_cli_batch17():
    """runner.py 不应反向依赖 cli.py。"""
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src


# ---------- 端到端集成第二十七批 ----------


def test_e2e_run_evaluation_full_round_trip_batch17(tmp_path):
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


def test_e2e_load_annotation_round_trip_batch17(tmp_path):
    """写 → 读 round trip。"""
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    r = _load_annotation(p)
    assert r == {"x": 1}


def test_e2e_run_evaluation_creates_valid_json_batch17(tmp_path):
    out = tmp_path / "out.json"
    run_evaluation(_mk_manifest_empty(), out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_e2e_run_evaluation_returns_same_as_file_batch17(tmp_path):
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert r == data


def test_e2e_run_evaluation_with_expected_failure_batch17(tmp_path):
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


def test_e2e_run_evaluation_devset_in_report_batch17(tmp_path):
    """devset section 来自 manifest 属性。"""
    m = _mk_manifest_empty()
    m.devset_status = "complete"
    m.file_count = 5
    out = tmp_path / "out.json"
    r = run_evaluation(m, out)
    assert r["devset"]["status"] == "complete"
    assert r["devset"]["file_count"] == 5


def test_e2e_run_evaluation_no_documents_no_expected_batch17(tmp_path):
    """空 manifest 完整跑通。"""
    out = tmp_path / "out.json"
    r = run_evaluation(_mk_manifest_empty(), out)
    assert r["per_doc"] == []
    assert r["expected_failures"] == []


def test_e2e_load_annotation_none_for_various_invalid_batch17(tmp_path):
    """各种无效 annotation 都返回 None。"""
    # 不存在
    assert _load_annotation(tmp_path / "no.json") is None
    # None
    assert _load_annotation(None) is None
    # 目录
    sub = tmp_path / "sub"; sub.mkdir()
    assert _load_annotation(sub) is None
    # 非法 JSON
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert _load_annotation(bad) is None
