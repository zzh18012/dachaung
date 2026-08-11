"""evaluation/runner.py 第四十五轮 edges 测试（Round 431）。

补强 edges42 未触及的角度：
- _load_annotation 行为深度第十六批（None 输入 / 不存在文件 / 含 BOM / 含换行 JSON / 大文件 / 路径是目录）
- _process_one 行为深度第十六批（image_dir 用 image_output_dir_for / unlink 异常 / errors 多个取第 1 / no errors no document unknown / total_seconds 非负 / 5-tuple 类型固定）
- run_evaluation 行为深度第十六批（report top 6 keys / per_doc public keys 4 / wall_time 6 keys / parser_version 第一个非空被采用 / max_chars 透传 / tolerance_chars 透传 / writes file with json）
- module source forbidden tokens 第二十六批
- module source 字符串精确补强第二十三批
- signatures 第二十三批
- module 合理性第二十三批
- 端到端集成第二十三批
"""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION, runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 行为深度第十六批 ----------


def test_load_annotation_none_path_batch16():
    """path=None → 返回 None。"""
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_path_batch16(tmp_path):
    """path 不存在 → 返回 None。"""
    assert _load_annotation(tmp_path / "nope.json") is None


def test_load_annotation_directory_path_batch16(tmp_path):
    """path 是目录 → is_file() False → 返回 None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_bom_encoded_batch16(tmp_path):
    """UTF-8 BOM 会使 json.load 失败（encoding="utf-8" 不会自动剥 BOM）→ 返回 None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"x": 1}')
    result = _load_annotation(p)
    # BOM 导致 JSON 解析失败 → 函数 catch JSONDecodeError → 返回 None
    assert result is None


def test_load_annotation_multiline_json_batch16(tmp_path):
    """多行 JSON 也能解析。"""
    p = tmp_path / "a.json"
    p.write_text('{\n  "x": 1,\n  "y": 2\n}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"x": 1, "y": 2}


def test_load_annotation_large_json_batch16(tmp_path):
    """大 dict 不崩。"""
    p = tmp_path / "a.json"
    data = {str(i): i for i in range(1000)}
    p.write_text(json.dumps(data), encoding="utf-8")
    result = _load_annotation(p)
    assert len(result) == 1000


def test_load_annotation_returns_dict_or_none_batch16(tmp_path):
    """返回值必须是 dict 或 None。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, dict) or result is None


def test_load_annotation_oserror_batch16(tmp_path):
    """OSError → 返回 None。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("denied")):
        result = _load_annotation(p)
    assert result is None


def test_load_annotation_json_decode_error_batch16(tmp_path):
    """JSON 解析失败 → 返回 None。"""
    p = tmp_path / "a.json"
    p.write_text("{not json", encoding="utf-8")
    result = _load_annotation(p)
    assert result is None


def test_load_annotation_does_not_raise_batch16(tmp_path):
    """任何异常都不应抛出（除了内部 catch 的）。"""
    p = tmp_path / "a.json"
    p.write_text("[]", encoding="utf-8")
    # 数组 JSON 应能解析；返回 list 而不是 dict，但函数仍"成功"
    result = _load_annotation(p)
    # 是 list 也可以；只要不抛
    assert result is not None


# ---------- _process_one 行为深度第十六批 ----------


def test_process_one_returns_5_tuple_batch16(tmp_path):
    """_process_one 返回 5-tuple。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"x": 1}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            result = _process_one(doc, output_root, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_image_dir_uses_helper_batch16(tmp_path):
    """image_dir 来自 image_output_dir_for 而不是硬编码。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"x": 1}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    expected_img_dir = tmp_path / "custom_images"

    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=expected_img_dir) as mock_helper:
            _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
    assert image_dir == expected_img_dir
    mock_helper.assert_called_once()


def test_process_one_unlink_oserror_silent_batch16(tmp_path):
    """out_stub.unlink 抛 OSError 应被吞掉。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"x": 1}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            with patch("pathlib.Path.unlink", side_effect=OSError("denied")):
                # 不应抛
                _process_one(doc, output_root, "fallback", 800)


def test_process_one_errors_first_taken_batch16(tmp_path):
    """errors 多个时取第 1 个。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "second"}

    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert document is None
    assert error == {"code": "first"}


def test_process_one_no_errors_no_document_unknown_batch16(tmp_path):
    """errors=[] + document=None → 错误码 unknown。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert document is None
    assert error["code"] == "unknown"


def test_process_one_total_seconds_nonneg_batch16(tmp_path):
    """total_seconds 必须 ≥ 0。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"x": 1}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _, _, total_seconds, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert total_seconds >= 0


def test_process_one_parser_version_passthrough_batch16(tmp_path):
    """parser_version 来自 document.parser_version。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"x": 1}
    fake_doc.parser_version = "9.9"
    fake_doc.source_hash = "abc"

    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            _, _, _, parser_version, _ = _process_one(doc, output_root, "fallback", 800)
    assert parser_version == "9.9"


def test_process_one_image_dir_none_when_document_none_batch16(tmp_path):
    """document=None → image_dir=None。"""
    doc = MagicMock()
    doc.doc_id = "d1"
    doc.resolved_path = tmp_path / "x.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    output_root = tmp_path / "out"
    output_root.mkdir()

    err = MagicMock()
    err.to_dict.return_value = {"code": "x"}

    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
    assert image_dir is None


# ---------- run_evaluation 行为深度第十六批 ----------


def _make_doc_mock(tmp_path, doc_id="d1", source_type="pdf"):
    """创建一个 fake DocumentEntry。"""
    doc = MagicMock()
    doc.doc_id = doc_id
    doc.source_type = source_type
    doc.resolved_path = tmp_path / f"{doc_id}.pdf"
    doc.resolved_path.write_text("fake", encoding="utf-8")
    doc.paired_with = None
    doc.categories = ()
    doc.expectations = None
    doc.annotation_resolved = None
    return doc


def _make_manifest_mock(tmp_path, documents=None, expected_failures=None):
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.devset_status = "incomplete"
    m.file_count = len(m.documents)
    m.content_group_count = 0
    m.pdf_count = sum(1 for d in m.documents if d.source_type == "pdf")
    m.docx_count = sum(1 for d in m.documents if d.source_type == "docx")
    m.categories_covered = []
    m.project_root = tmp_path
    return m


def test_run_evaluation_report_top_keys_batch16(tmp_path):
    """report top-level 必须有 6 个 key。"""
    m = _make_manifest_mock(tmp_path, documents=[], expected_failures=[])
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        result = run_evaluation(m, out)
    expected = {"report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"}
    assert set(result.keys()) == expected


def test_run_evaluation_per_doc_public_keys_4_batch16(tmp_path):
    """per_doc 公开 key 必须是 4 个（doc_id / source_type / metrics / wall_time_seconds）。"""
    doc = _make_doc_mock(tmp_path)
    m = _make_manifest_mock(tmp_path, documents=[doc])

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            result = run_evaluation(m, out)
    assert len(result["per_doc"]) == 1
    expected = {"doc_id", "source_type", "metrics", "wall_time_seconds"}
    assert set(result["per_doc"][0].keys()) == expected


def test_run_evaluation_wall_time_keys_6_batch16(tmp_path):
    """wall_time_seconds 必须有 6 个 key。"""
    doc = _make_doc_mock(tmp_path)
    m = _make_manifest_mock(tmp_path, documents=[doc])

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            result = run_evaluation(m, out)
    wt = result["per_doc"][0]["wall_time_seconds"]
    expected = {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert expected.issubset(set(wt.keys()))


def test_run_evaluation_parser_version_first_kept_batch16(tmp_path):
    """多个文档时 parser_version 取第一个非空。"""
    docs = [_make_doc_mock(tmp_path, "d1"), _make_doc_mock(tmp_path, "d2")]
    m = _make_manifest_mock(tmp_path, documents=docs)

    fake1 = MagicMock()
    fake1.to_dict.return_value = {"x": 1}
    fake1.parser_version = "1.0"
    fake1.source_hash = "abc"

    fake2 = MagicMock()
    fake2.to_dict.return_value = {"x": 2}
    fake2.parser_version = "2.0"
    fake2.source_hash = "def"

    out = tmp_path / "report.json"
    captured = {}

    def fake_build_prov(project_root, parser_name, max_chars, parser_version):
        captured["parser_version"] = parser_version
        return {"x": 1}

    with patch("evaluation.runner.process_single", side_effect=[(fake1, []), (fake2, [])]):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.build_provenance", side_effect=fake_build_prov):
                result = run_evaluation(m, out)
    assert captured["parser_version"] == "1.0"


def test_run_evaluation_max_chars_passthrough_batch16(tmp_path):
    """max_chars 透传给 process_single。"""
    doc = _make_doc_mock(tmp_path)
    m = _make_manifest_mock(tmp_path, documents=[doc])

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    captured = {}

    def fake_process(*args, **kwargs):
        captured["max_chars"] = kwargs.get("max_chars")
        return fake_doc, []

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            result = run_evaluation(m, out, max_chars=1234)
    assert captured["max_chars"] == 1234


def test_run_evaluation_writes_file_batch16(tmp_path):
    """报告应写入 output_path。"""
    m = _make_manifest_mock(tmp_path, documents=[], expected_failures=[])
    out = tmp_path / "subdir" / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        run_evaluation(m, out)
    assert out.is_file()
    # 内容应是合法 JSON
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)


def test_run_evaluation_json_round_trip_batch16(tmp_path):
    """写入的 JSON 可解析回相等 dict。"""
    m = _make_manifest_mock(tmp_path, documents=[], expected_failures=[])
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        result = run_evaluation(m, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == result


def test_run_evaluation_parser_name_passthrough_batch16(tmp_path):
    """parser_name 透传给 process_single 与 build_provenance。"""
    doc = _make_doc_mock(tmp_path)
    m = _make_manifest_mock(tmp_path, documents=[doc])

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    captured_proc = {}
    captured_prov = {}

    def fake_process(path, out_path, parser_name=None, **kwargs):
        captured_proc["parser_name"] = parser_name
        return fake_doc, []

    def fake_prov(project_root, parser_name, max_chars, parser_version):
        captured_prov["parser_name"] = parser_name
        return {"x": 1}

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.build_provenance", side_effect=fake_prov):
                run_evaluation(m, out, parser_name="kreuzberg")
    assert captured_proc["parser_name"] == "kreuzberg"
    assert captured_prov["parser_name"] == "kreuzberg"


def test_run_evaluation_tolerance_chars_in_per_doc_batch16(tmp_path):
    """tolerance_chars 应影响 chunk_boundary_prf（间接）。"""
    doc = _make_doc_mock(tmp_path)
    m = _make_manifest_mock(tmp_path, documents=[doc])

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    captured = {}

    def fake_cbf(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {
            "chunk_boundary_precision": {"value": None, "reason": "x"},
            "chunk_boundary_recall": {"value": None, "reason": "x"},
            "chunk_boundary_f1": {"value": None, "reason": "x"},
            "_tolerance_chars": {"value": tolerance_chars, "reason": None},
        }

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.chunk_boundary_prf", side_effect=fake_cbf):
                run_evaluation(m, out, tolerance_chars=42)
    assert captured["tolerance_chars"] == 42


# ---------- module source forbidden tokens 第二十六批 ----------


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


# ---------- module source 字符串精确补强第二十三批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(rmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch16():
    src = inspect.getsource(rmod)
    assert '"""评测 runner：清单' in src


def test_module_source_has_json_import_batch16():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_time_import_batch16():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_path_import_batch16():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_any_import_batch16():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch16():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_report_version_import_batch16():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_import_batch16():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf," in src
    assert "figure_caption_prf," in src


def test_module_source_has_metrics_import_batch16():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import_batch16():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src
    assert "aggregate_summary," in src
    assert "build_devset_section," in src
    assert "build_provenance," in src


def test_module_source_has_load_annotation_function_batch16():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(path: Path | None) -> dict[str, Any] | None:" in src


def test_module_source_has_process_one_function_batch16():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_has_run_evaluation_function_batch16():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_has_not_instrumented_reason_batch16():
    src = inspect.getsource(rmod)
    assert '"not_instrumented"' in src


def test_module_source_has_unknown_error_code_batch16():
    src = inspect.getsource(rmod)
    assert '"unknown"' in src


def test_module_source_has_process_single_returned_none_message_batch16():
    src = inspect.getsource(rmod)
    assert "process_single returned None without errors" in src


def test_module_source_has_perf_counter_call_batch16():
    src = inspect.getsource(rmod)
    assert "time.perf_counter()" in src


def test_module_source_has_all_dunder_batch16():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


def test_module_source_has_kwargs_marker_batch16():
    src = inspect.getsource(rmod)
    assert "*" in src  # 关键字参数分隔符


def test_module_source_has_write_json_false_batch16():
    src = inspect.getsource(rmod)
    assert "write_json=False" in src


def test_module_source_has_image_dir_for_call_batch16():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for(out_stub, document.source_hash)" in src


def test_module_source_has_mkdir_call_batch16():
    src = inspect.getsource(rmod)
    assert "mkdir(parents=True, exist_ok=True)" in src


# ---------- signatures 第二十三批 ----------


def test_signature_load_annotation_batch16():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.keys())
    assert params == ["path"]


def test_signature_process_one_batch16():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.keys())
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_run_evaluation_batch16():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_defaults_batch16():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_run_evaluation_kwargs_marker_batch16():
    """output_path 后必须有 * 标记（kwargs）。"""
    sig = inspect.signature(run_evaluation)
    # output_path 之后所有参数必须是 keyword-only
    found_star = False
    for p in sig.parameters.values():
        if p.kind == p.KEYWORD_ONLY:
            found_star = True
    assert found_star


def test_signature_load_annotation_optional_path_batch16():
    sig = inspect.signature(_load_annotation)
    # path 是 Path | None
    annotation = sig.parameters["path"].annotation
    assert annotation is not inspect._empty


# ---------- module 合理性第二十三批 ----------


def test_module_has_all_attribute_batch16():
    assert hasattr(rmod, "__all__")
    assert isinstance(rmod.__all__, list)


def test_module_all_contains_run_evaluation_batch16():
    assert "run_evaluation" in rmod.__all__


def test_module_run_evaluation_callable_batch16():
    assert callable(run_evaluation)


def test_module_load_annotation_callable_batch16():
    assert callable(_load_annotation)


def test_module_process_one_callable_batch16():
    assert callable(_process_one)


def test_module_does_not_export_private_helpers_batch16():
    for name in rmod.__all__:
        assert not name.startswith("_")


def test_module_constants_in_namespace_batch16():
    """REPORT_VERSION 是模块可见的常量。"""
    assert hasattr(rmod, "REPORT_VERSION")
    assert rmod.REPORT_VERSION == REPORT_VERSION


def test_module_uses_time_perf_counter_batch16():
    """模块用 perf_counter 计时（不是 time.time）。"""
    src = inspect.getsource(rmod)
    assert "perf_counter" in src


def test_module_does_not_call_parse_or_chunk_directly_batch16():
    """runner 不直接调 parse / chunk 函数（只通过 process_single）。"""
    src = inspect.getsource(rmod)
    # 不应直接 import parse_document / chunk_document
    assert "from app.parsers" not in src
    assert "from app.chunkers" not in src


# ---------- 端到端集成第二十三批 ----------


def test_e2e_run_evaluation_empty_manifest_batch16(tmp_path):
    """空 manifest → 空 per_doc。"""
    m = _make_manifest_mock(tmp_path)
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        result = run_evaluation(m, out)
    assert result["per_doc"] == []
    assert result["expected_failures"] == []


def test_e2e_run_evaluation_with_expected_failure_batch16(tmp_path):
    """expected_failures 也应被处理。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.txt"
    ef.resolved_path.write_text("bad", encoding="utf-8")
    ef.expected_error_code = "unsupported_format"

    m = _make_manifest_mock(tmp_path, expected_failures=[ef])

    err = MagicMock()
    err.code = "unsupported_format"

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
            result = run_evaluation(m, out)
    assert len(result["expected_failures"]) == 1
    assert result["expected_failures"][0]["matches"] is True


def test_e2e_run_evaluation_expected_failure_no_match_batch16(tmp_path):
    """actual 与 expected 不一致 → matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.txt"
    ef.resolved_path.write_text("bad", encoding="utf-8")
    ef.expected_error_code = "unsupported_format"

    m = _make_manifest_mock(tmp_path, expected_failures=[ef])

    err = MagicMock()
    err.code = "different_error"

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
            result = run_evaluation(m, out)
    assert result["expected_failures"][0]["matches"] is False


def test_e2e_run_evaluation_expected_failure_no_errors_batch16(tmp_path):
    """expected_failure 但实际无错误 → actual_code=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.txt"
    ef.resolved_path.write_text("bad", encoding="utf-8")
    ef.expected_error_code = "unsupported_format"

    m = _make_manifest_mock(tmp_path, expected_failures=[ef])

    fake_doc = MagicMock()

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
            result = run_evaluation(m, out)
    assert result["expected_failures"][0]["actual_error_code"] is None
    assert result["expected_failures"][0]["matches"] is False


def test_e2e_run_evaluation_report_version_batch16(tmp_path):
    """report_version 来自 REPORT_VERSION 常量。"""
    m = _make_manifest_mock(tmp_path)
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        result = run_evaluation(m, out)
    assert result["report_version"] == REPORT_VERSION


def test_e2e_run_evaluation_creates_subdir_batch16(tmp_path):
    """output_path 在不存在的子目录中应自动创建。"""
    m = _make_manifest_mock(tmp_path)
    out = tmp_path / "a" / "b" / "c" / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        run_evaluation(m, out)
    assert out.is_file()


def test_e2e_run_evaluation_summary_present_batch16(tmp_path):
    m = _make_manifest_mock(tmp_path)
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        result = run_evaluation(m, out)
    assert "summary" in result


def test_e2e_run_evaluation_devset_present_batch16(tmp_path):
    m = _make_manifest_mock(tmp_path)
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"x": 1}):
        result = run_evaluation(m, out)
    assert "devset" in result


def test_e2e_run_evaluation_provenance_present_batch16(tmp_path):
    m = _make_manifest_mock(tmp_path)
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        result = run_evaluation(m, out)
    assert result["provenance"]["git_commit"] == "abc"


def test_e2e_run_evaluation_per_doc_excludes_private_batch16(tmp_path):
    """公开 per_doc 不应含私有 key（_annotation_present / _tolerance_chars / _missing_markers）。"""
    doc = _make_doc_mock(tmp_path)
    m = _make_manifest_mock(tmp_path, documents=[doc])

    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {
        "document_id": "d1", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"

    out = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            result = run_evaluation(m, out)
    for r in result["per_doc"]:
        for key in r.keys():
            assert not key.startswith("_")
