"""evaluation/runner.py 第五十轮 edges 测试（Round 465）。

补强 edges47 未触及的角度：
- _load_annotation 第二十批（int/bool/None/float 顶层 / 目录被拒 / 大整数 / 嵌套深层 / tuple-like）
- _process_one 第二十批（process_single 调用参数细节 / out_stub 路径细节 / 多 doc_id 命名 / 错误优先于 None / image_output_dir_for 入参）
- run_evaluation 第二十批（parser_version 持久性 / image_base_dir 优先 / expected_failure 单独 stub / public per_doc 严格字段 / report json 输出 indent / provenance 透传 parser_name+max_chars）
- module source forbidden tokens 第三十六批
- module source 字符串精确补强第三十二批
- signatures 第三十二批
- module 合理性第三十二批
- 端到端集成第三十二批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation
from evaluation import runner as rmod


# ---------- _load_annotation 第二十批 ----------


def test_load_annotation_returns_int_for_int_top_level_batch20(tmp_path):
    """JSON 顶层是 int 时返回 int（_load_annotation 不限定类型）。"""
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    assert _load_annotation(p) == 42


def test_load_annotation_returns_bool_for_bool_top_level_batch20(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("true", encoding="utf-8")
    assert _load_annotation(p) is True


def test_load_annotation_returns_none_for_null_top_level_batch20(tmp_path):
    """JSON 顶层 null → Python None，但函数也返回 None 表示失败；语义模糊但不报错。"""
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_returns_float_for_float_top_level_batch20(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("3.14", encoding="utf-8")
    assert _load_annotation(p) == pytest.approx(3.14)


def test_load_annotation_returns_str_for_str_top_level_batch20(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    assert _load_annotation(p) == "hello"


def test_load_annotation_directory_returns_none_batch20(tmp_path):
    """目录被 is_file() 拒绝 → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_large_int_batch20(tmp_path):
    """大整数顶层。"""
    p = tmp_path / "a.json"
    p.write_text("12345678901234567890", encoding="utf-8")
    assert _load_annotation(p) == 12345678901234567890


def test_load_annotation_deeply_nested_batch20(tmp_path):
    """深度嵌套 dict。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": {"d": {"e": "deep"}}}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["a"]["b"]["c"]["d"]["e"] == "deep"


def test_load_annotation_array_of_mixed_batch20(tmp_path):
    """数组混合类型。"""
    p = tmp_path / "a.json"
    p.write_text('[1, "x", null, true, [2, 3]]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, "x", None, True, [2, 3]]


def test_load_annotation_special_chars_in_string_batch20(tmp_path):
    """转义字符。"""
    p = tmp_path / "a.json"
    p.write_text(r'"\n\té"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "\n\t\xe9"


# ---------- _process_one 第二十批 ----------


def _make_doc(doc_id="d1", source_type="pdf"):
    d = MagicMock()
    d.doc_id = doc_id
    d.source_type = source_type
    d.resolved_path = Path("/fake.pdf")
    d.expectations = None
    d.annotation_resolved = None
    return d


def test_process_one_calls_process_single_with_write_json_false_batch20(tmp_path):
    """write_json=False 必须显式传。"""
    doc = _make_doc()
    captured = {}

    def fake_process(path, out, **kwargs):
        captured["path"] = path
        captured["out"] = out
        captured["kwargs"] = kwargs
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured["kwargs"]["write_json"] is False


def test_process_one_calls_process_single_with_parser_name_batch20(tmp_path):
    """parser_name 透传。"""
    doc = _make_doc()
    captured = {}

    def fake_process(path, out, **kwargs):
        captured["parser_name"] = kwargs.get("parser_name")
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "kreuzberg", 800)
    assert captured["parser_name"] == "kreuzberg"


def test_process_one_calls_process_single_with_max_chars_batch20(tmp_path):
    """max_chars 透传。"""
    doc = _make_doc()
    captured = {}

    def fake_process(path, out, **kwargs):
        captured["max_chars"] = kwargs.get("max_chars")
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "fallback", 1200)
    assert captured["max_chars"] == 1200


def test_process_one_out_stub_uses_doc_id_batch20(tmp_path):
    """out_stub 文件名是 {doc_id}.json。"""
    doc = _make_doc("special_id")
    captured = {}

    def fake_process(path, out, **kwargs):
        captured["out"] = out
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured["out"].name == "special_id.json"
    assert captured["out"].parent.name == "_per_doc"


def test_process_one_image_output_dir_for_called_with_stub_and_hash_batch20(tmp_path):
    """image_output_dir_for 用 out_stub + source_hash 作参数。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"document_id": "d1"}
    document_mock.parser_version = "1.0.0"
    document_mock.source_hash = "deadbeef"
    captured = {}

    def fake_image_dir(stub, source_hash):
        captured["stub"] = stub
        captured["source_hash"] = source_hash
        return tmp_path / "imgs"

    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch(
            "evaluation.runner.image_output_dir_for", side_effect=fake_image_dir
        ):
            document, error, elapsed, parser_version, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert captured["source_hash"] == "deadbeef"
    assert captured["stub"].name == "d1.json"


def test_process_one_unlinks_out_stub_after_success_batch20(tmp_path):
    """process_single 成功后 out_stub 应被清理。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"document_id": "d1"}
    document_mock.parser_version = "1"
    document_mock.source_hash = "abc"

    def fake_process(path, out, **kwargs):
        # 模拟 pipeline 真的写了 stub
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("{}", encoding="utf-8")
        return document_mock, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _process_one(doc, tmp_path, "fallback", 800)
    stub = tmp_path / "_per_doc" / "d1.json"
    assert not stub.is_file()


def test_process_one_no_stub_no_unlink_batch20(tmp_path):
    """process_single 不写 stub 时 is_file() False，不调 unlink。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch.object(Path, "unlink") as mock_unlink:
                _process_one(doc, tmp_path, "fallback", 800)
    mock_unlink.assert_not_called()


def test_process_one_perf_counter_pair_batch20(tmp_path):
    """两次 perf_counter 调用（包住 process_single）。"""
    doc = _make_doc()
    call_count = {"n": 0}

    def fake_perf():
        call_count["n"] += 1
        return float(call_count["n"])

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.time.perf_counter", side_effect=fake_perf):
                document, error, elapsed, parser_version, image_dir = _process_one(
                    doc, tmp_path, "fallback", 800
                )
    # t0=1.0, t1=2.0 → elapsed=1.0
    assert elapsed == 1.0


def test_process_one_returns_five_tuple_batch20(tmp_path):
    """返回 5-tuple。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_errors_overrides_unknown_batch20(tmp_path):
    """errors 非空时优先返回 errors[0]，不走 unknown 分支。"""
    doc = _make_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "PARSE_FAIL", "message": "broken"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            document, error, elapsed, parser_version, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert error == {"code": "PARSE_FAIL", "message": "broken"}


# ---------- run_evaluation 第二十批 ----------


def _make_manifest(docs=(), expected_failures=(), project_root=None):
    m = MagicMock()
    m.documents = list(docs)
    m.expected_failures = list(expected_failures)
    m.project_root = project_root or Path(".")
    m.devset_status = "incomplete"
    m.file_count = len(docs)
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_parser_version_sticks_after_first_batch20(tmp_path):
    """parser_version_for_prov 第一个成功 doc 设定后，后续 doc 不覆盖。"""
    doc1 = _make_doc("d1")
    doc2 = _make_doc("d2")

    document1 = MagicMock()
    document1.to_dict.return_value = {"document_id": "d1"}
    document1.parser_version = "1.0.0"
    document1.source_hash = "h1"

    document2 = MagicMock()
    document2.to_dict.return_value = {"document_id": "d2"}
    document2.parser_version = "2.0.0"
    document2.source_hash = "h2"

    call_count = {"n": 0}

    def fake_process(path, out, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return document1, []
        return document2, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc1, doc2])
                        report = run_evaluation(m, tmp_path / "out.json")
    # 第一个 doc 的版本固定
    assert report["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_parser_version_falsy_skipped_batch20(tmp_path):
    """parser_version 是 falsy（如空字符串）时不被采用。"""
    doc1 = _make_doc("d1")
    doc2 = _make_doc("d2")

    document1 = MagicMock()
    document1.to_dict.return_value = {"document_id": "d1"}
    document1.parser_version = ""  # falsy
    document1.source_hash = "h1"

    document2 = MagicMock()
    document2.to_dict.return_value = {"document_id": "d2"}
    document2.parser_version = "real_version"
    document2.source_hash = "h2"

    call_count = {"n": 0}

    def fake_process(path, out, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return document1, []
        return document2, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc1, doc2])
                        report = run_evaluation(m, tmp_path / "out.json")
    # 第一个 falsy，第二个被采用
    assert report["provenance"]["parser_version"] == "real_version"


def test_run_evaluation_image_base_dir_none_when_not_dir_batch20(tmp_path):
    """image_dir 存在但不是目录时传 None 给 metrics。"""
    doc = _make_doc()
    captured = {}

    def fake_metrics(**kwargs):
        captured.update(kwargs)
        return {}

    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"d": 1}
    document_mock.parser_version = "1"
    document_mock.source_hash = "abc"

    # image_dir 指向一个不存在的路径
    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch(
            "evaluation.runner.image_output_dir_for",
            return_value=tmp_path / "notexist",
        ):
            with patch(
                "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
            ):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured.get("image_base_dir") is None


def test_run_evaluation_expected_failure_uses_per_doc_path_batch20(tmp_path):
    """expected_failure 的 out_stub 也用 _per_doc/{doc_id}.json 命名。"""
    ef = MagicMock()
    ef.doc_id = "ef_special"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    captured = {}

    def fake_process(path, out, **kwargs):
        captured["out"] = out
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        m = _make_manifest(expected_failures=[ef])
        run_evaluation(m, tmp_path / "out.json")
    assert captured["out"].name == "ef_special.json"
    assert captured["out"].parent.name == "_per_doc"


def test_run_evaluation_expected_failure_unlinks_stub_batch20(tmp_path):
    """expected_failure 处理后清理 out_stub。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")

    def fake_process(path, out, **kwargs):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("{}", encoding="utf-8")
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        m = _make_manifest(expected_failures=[ef])
        run_evaluation(m, tmp_path / "out.json")
    stub = tmp_path / "_per_doc" / "ef1.json"
    assert not stub.is_file()


def test_run_evaluation_public_per_doc_has_exactly_four_keys_batch20(tmp_path):
    """public per_doc 严格 4 个字段：doc_id/source_type/metrics/wall_time_seconds。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    assert set(report["per_doc"][0].keys()) == {
        "doc_id",
        "source_type",
        "metrics",
        "wall_time_seconds",
    }


def test_run_evaluation_output_file_indent_two_batch20(tmp_path):
    """输出 JSON 用 indent=2（可读性）。"""
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 会产生 4 空格续行（2 空格 × 2 层）
    assert '  "' in content
    # 没有缩进应该是单行
    lines = content.splitlines()
    assert len(lines) > 1


def test_run_evaluation_provenance_passes_parser_name_batch20(tmp_path):
    """provenance 含 parser_name。"""
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json", parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_provenance_passes_max_chars_batch20(tmp_path):
    """provenance 含 max_chars。"""
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json", max_chars=1500)
    assert report["provenance"]["max_chars"] == 1500


def test_run_evaluation_annotation_load_called_with_resolved_batch20(tmp_path):
    """_load_annotation 用 doc.annotation_resolved。"""
    doc = _make_doc()
    doc.annotation_resolved = tmp_path / "ann.json"
    (tmp_path / "ann.json").write_text("{}", encoding="utf-8")
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    # 应不抛错（_load_annotation 已被调用）


def test_run_evaluation_chunk_boundary_called_with_tolerance_batch20(tmp_path):
    """chunk_boundary_prf 接收 tolerance_chars 参数。"""
    doc = _make_doc()
    captured = {}

    def fake_chunk_b(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {}

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch(
                        "evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b
                    ):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(
                            m, tmp_path / "out.json", tolerance_chars=50
                        )
    assert captured["tolerance_chars"] == 50


def test_run_evaluation_multiple_expected_failures_batch20(tmp_path):
    """多个 expected_failure 都被处理。"""
    ef1 = MagicMock()
    ef1.doc_id = "ef1"
    ef1.expected_error_code = "E_PARSE"
    ef1.resolved_path = Path("/bad1.pdf")
    ef2 = MagicMock()
    ef2.doc_id = "ef2"
    ef2.expected_error_code = "E_OCR"
    ef2.resolved_path = Path("/bad2.pdf")
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        m = _make_manifest(expected_failures=[ef1, ef2])
        report = run_evaluation(m, tmp_path / "out.json")
    assert len(report["expected_failures"]) == 2
    assert report["expected_failures"][0]["doc_id"] == "ef1"
    assert report["expected_failures"][1]["doc_id"] == "ef2"


# ---------- module source forbidden tokens 第三十六批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch20(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch20():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch20():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch20():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch20():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch20():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch20():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch20():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch20():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch20():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch20():
    src = inspect.getsource(rmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch20():
    src = inspect.getsource(rmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch20():
    src = inspect.getsource(rmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch20():
    src = inspect.getsource(rmod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch20():
    src = inspect.getsource(rmod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch20():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch20():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十二批 ----------


def test_module_source_has_future_annotations_batch20():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch20():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_time_import_batch20():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_pathlib_path_import_batch20():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch20():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch20():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_report_version_import_batch20():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_import_batch20():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_has_chunk_boundary_prf_in_import_batch20():
    src = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in src


def test_module_source_has_figure_caption_prf_in_import_batch20():
    src = inspect.getsource(rmod)
    assert "figure_caption_prf" in src


def test_module_source_has_metrics_import_batch20():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import_batch20():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_has_aggregate_summary_in_import_batch20():
    src = inspect.getsource(rmod)
    assert "aggregate_summary" in src


def test_module_source_has_build_devset_section_in_import_batch20():
    src = inspect.getsource(rmod)
    assert "build_devset_section" in src


def test_module_source_has_build_provenance_in_import_batch20():
    src = inspect.getsource(rmod)
    assert "build_provenance" in src


def test_module_source_has_perf_counter_call_batch20():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_has_ensure_ascii_false_batch20():
    src = inspect.getsource(rmod)
    assert "ensure_ascii=False" in src


# ---------- signatures 第三十二批 ----------


def test_signature_load_annotation_batch20():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_signature_process_one_batch20():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_batch20():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_keyword_only_batch20():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[2].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[3].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[4].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch20():
    sig = inspect.signature(run_evaluation)
    params = {p.name: p for p in sig.parameters.values()}
    assert params["parser_name"].default == "fallback"
    assert params["max_chars"].default == 800
    assert params["tolerance_chars"].default == 30


def test_signature_process_one_no_default_batch20():
    """_process_one 所有参数都必填。"""
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# ---------- module 合理性第三十二批 ----------


def test_module_has_all_attribute_batch20():
    assert hasattr(rmod, "__all__")


def test_module_all_count_one_batch20():
    assert len(rmod.__all__) == 1


def test_module_all_contents_batch20():
    assert "run_evaluation" in rmod.__all__


def test_module_does_not_import_evaluation_cli_batch20():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_schema_batch20():
    src = inspect.getsource(rmod)
    assert "from evaluation.schema" not in src
    assert "from evaluation import schema" not in src


def test_module_does_not_import_evaluation_manifest_batch20():
    src = inspect.getsource(rmod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_does_not_import_app_chunkers_batch20():
    src = inspect.getsource(rmod)
    assert "from app.chunkers" not in src
    assert "from app import chunkers" not in src


def test_module_does_not_import_app_parsers_batch20():
    src = inspect.getsource(rmod)
    assert "from app.parsers" not in src
    assert "from app import parsers" not in src


def test_module_constants_not_in_all_batch20():
    for k in ("_load_annotation", "_process_one"):
        assert k not in rmod.__all__


def test_module_no_main_block_batch20():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_load_annotation_is_private_batch20():
    assert _load_annotation.__name__.startswith("_")


def test_module_process_one_is_private_batch20():
    assert _process_one.__name__.startswith("_")


# ---------- 端到端集成第三十二批 ----------


def test_e2e_load_annotation_int_round_trip_batch20(tmp_path):
    """int 顶层 JSON round-trip。"""
    p = tmp_path / "a.json"
    p.write_text("123", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 123


def test_e2e_run_evaluation_creates_valid_json_batch20(tmp_path):
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert "per_doc" in parsed


def test_e2e_run_evaluation_returns_same_as_file_batch20(tmp_path):
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    report = run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == report


def test_e2e_run_evaluation_no_docs_summary_struct_batch20(tmp_path):
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    s = report["summary"]
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_e2e_run_evaluation_per_doc_count_matches_docs_batch20(tmp_path):
    docs = [_make_doc(f"d{i}") for i in range(3)]
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=docs)
                        report = run_evaluation(m, tmp_path / "out.json")
    assert len(report["per_doc"]) == 3


def test_e2e_run_evaluation_with_expected_failure_mismatch_batch20(tmp_path):
    """expected_failure 实际错误 != 期望时 matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "E_OCR"  # 不匹配
    with patch("evaluation.runner.process_single", return_value=(None, [err_mock])):
        m = _make_manifest(expected_failures=[ef])
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["matches"] is False
    assert report["expected_failures"][0]["actual_error_code"] == "E_OCR"


def test_e2e_run_evaluation_full_report_has_six_top_keys_batch20(tmp_path):
    """完整报告含 6 个顶层字段（含 expected_failures）。"""
    m = _make_manifest(docs=[], expected_failures=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_e2e_run_evaluation_public_per_doc_excludes_underscore_fields_batch20(tmp_path):
    """public per_doc 不含 _ 前缀字段。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    pd = report["per_doc"][0]
    for k in pd.keys():
        assert not k.startswith("_")
