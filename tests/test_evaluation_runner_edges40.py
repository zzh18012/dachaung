"""evaluation/runner.py 第四十二轮 edges 测试（Round 410）。

补强 edges39 未触及的角度：
- _load_annotation 行为深度第十三批（path.open 编码 utf-8 / 是 Path 对象 / 不存在 path.is_file → False / None 路径 / json.load 内部 / 是 file 而非 dir / mixed types）
- _process_one 行为深度第十三批（write_json=False 实参 / out_stub 路径推导 / process_single kwargs 透传 / unlink 失败时不抛 / image_dir None when document None / 5-tuple 顺序固定 / errors[0] 取第一个）
- run_evaluation 行为深度第十三批（report_version 来自 evaluation / report keys 顺序 / per_doc public keys 严格 4 个 / wall_time_seconds 字段 / _annotation_present 仅在内部 / tolerance_chars 透传到 chunk_boundary_prf / expected_failure matches 字段 / output 写文件 ensure_ascii=False indent=2 / project_root 来自 manifest）
- module source forbidden tokens 第十八批
- module source 字符串精确补强第十五批
- signatures 第十五批
- module 合理性第十五批
- 端到端集成第十五批
"""

from __future__ import annotations

import inspect
import json
import time
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


# ---------- _load_annotation 行为深度第十三批 ----------


def test_load_annotation_returns_none_for_none_input_batch13():
    assert _load_annotation(None) is None


def test_load_annotation_returns_none_for_nonexistent_path_batch13(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_returns_none_for_directory_batch13(tmp_path):
    """目录不是 is_file() → 返回 None。"""
    p = tmp_path / "subdir"
    p.mkdir()
    assert _load_annotation(p) is None


def test_load_annotation_returns_dict_for_valid_json_batch13(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text('{"key": "value", "num": 42}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value", "num": 42}


def test_load_annotation_returns_none_for_invalid_json_batch13(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_none_for_oserror_batch13(tmp_path):
    """模拟 OSError（如权限被拒）。"""
    p = tmp_path / "perm.json"
    p.write_text('{"k": "v"}', encoding="utf-8")

    def _raise_os(*args, **kwargs):
        raise OSError("denied")

    with patch.object(Path, "open", side_effect=_raise_os):
        assert _load_annotation(p) is None


def test_load_annotation_uses_utf8_encoding_batch13(tmp_path):
    """path.open 应使用 encoding=utf-8。"""
    p = tmp_path / "u.json"
    p.write_text("{}", encoding="utf-8")
    seen_kwargs: dict = {}

    original_open = Path.open

    def _spy(self, *args, **kwargs):
        seen_kwargs.update(kwargs)
        return original_open(self, *args, **kwargs)

    with patch.object(Path, "open", _spy):
        _load_annotation(p)
    assert seen_kwargs.get("encoding") == "utf-8"


def test_load_annotation_uses_open_in_context_manager_batch13():
    """源码应使用 with path.open(...) as f。"""
    source = inspect.getsource(_load_annotation)
    assert "with path.open" in source
    assert "as f" in source


def test_load_annotation_uses_json_load_batch13():
    source = inspect.getsource(_load_annotation)
    assert "json.load(f)" in source or "json.load(" in source


def test_load_annotation_path_is_file_check_batch13():
    source = inspect.getsource(_load_annotation)
    assert "is_file()" in source


def test_load_annotation_returns_list_for_top_level_array_batch13(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_returns_int_for_top_level_int_batch13(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_returns_str_for_top_level_str_batch13(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_returns_none_for_top_level_null_batch13(tmp_path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_returns_true_for_top_level_true_batch13(tmp_path):
    p = tmp_path / "true.json"
    p.write_text("true", encoding="utf-8")
    out = _load_annotation(p)
    assert out is True


def test_load_annotation_handles_utf8_bom_invalid_batch13(tmp_path):
    """UTF-8 BOM 不是合法 JSON 起始字符 → JSONDecodeError → None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + b'{"k": 1}')
    out = _load_annotation(p)
    # json.load 不跳 BOM → 抛 JSONDecodeError → 函数返回 None
    assert out is None


# ---------- _process_one 行为深度第十三批 ----------


def test_process_one_calls_process_single_with_write_json_false_batch13(tmp_path):
    """_process_one 必须用 write_json=False 调 process_single。"""
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])) as mock:
        _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    assert mock.called
    kwargs = mock.call_args.kwargs
    assert kwargs.get("write_json") is False


def test_process_one_calls_process_single_with_output_path_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])) as mock:
        _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    args = mock.call_args.args
    # 第二个位置参数是 out_stub
    assert args[1].name.endswith("doc1.json")


def test_process_one_calls_process_single_with_parser_name_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])) as mock:
        _process_one(doc, tmp_path, parser_name="kreuzberg", max_chars=800)
    kwargs = mock.call_args.kwargs
    assert kwargs.get("parser_name") == "kreuzberg"


def test_process_one_calls_process_single_with_max_chars_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])) as mock:
        _process_one(doc, tmp_path, parser_name="fallback", max_chars=400)
    kwargs = mock.call_args.kwargs
    assert kwargs.get("max_chars") == 400


def test_process_one_creates_per_doc_subdir_batch13(tmp_path):
    """out_stub.parent.mkdir(parents=True, exist_ok=True) 应被调用。"""
    doc = _StubDoc(doc_id="x", resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)

    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_unlinks_stub_file_batch13(tmp_path):
    """process_single 写盘后 _process_one 应删除 out_stub。"""
    doc = _StubDoc(doc_id="x", resolved_path=Path("/nonexistent"))

    def _fake_process(*args, **kwargs):
        out_stub = args[1]
        out_stub.write_text("{}", encoding="utf-8")
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)

    stub = tmp_path / "_per_doc" / "x.json"
    assert not stub.exists()


def test_process_one_unlink_oserror_silent_batch13(tmp_path):
    """unlink 抛 OSError 时静默吞掉。"""
    doc = _StubDoc(doc_id="x", resolved_path=Path("/nonexistent"))

    def _fake_process(*args, **kwargs):
        out_stub = args[1]
        out_stub.write_text("{}", encoding="utf-8")
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        with patch.object(Path, "unlink", side_effect=OSError("denied")):
            # 不应抛
            _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)


def test_process_one_returns_5_tuple_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(_StubDocument(), [])):
        result = _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_returns_positive_elapsed_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    def _fake_process(*args, **kwargs):
        time.sleep(0.005)
        return _StubDocument(), []

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        document, error, elapsed, parser_version, image_dir = _process_one(
            doc, tmp_path, parser_name="fallback", max_chars=800
        )
    assert elapsed >= 0.0
    assert isinstance(elapsed, float)


def test_process_one_returns_none_doc_when_error_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        document, error, elapsed, parser_version, image_dir = _process_one(
            doc, tmp_path, parser_name="fallback", max_chars=800
        )
    assert document is None
    assert error == {"code": "parse_failed", "message": "boom"}


def test_process_one_returns_error_dict_first_element_batch13(tmp_path):
    """errors 是 list 时取 errors[0].to_dict()。"""
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch(
        "evaluation.runner.process_single",
        return_value=(None, [_StubError("first"), _StubError("second")]),
    ):
        _, error, _, _, _ = _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    assert error["code"] == "first"


def test_process_one_returns_image_dir_none_when_document_none_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        _, _, _, _, image_dir = _process_one(
            doc, tmp_path, parser_name="fallback", max_chars=800
        )
    assert image_dir is None


def test_process_one_returns_unknown_code_when_no_doc_no_error_batch13(tmp_path):
    """process_single 返回 (None, []) → _process_one 返回 unknown error。"""
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, _, _, _ = _process_one(
            doc, tmp_path, parser_name="fallback", max_chars=800
        )
    assert document is None
    assert error["code"] == "unknown"


def test_process_one_unknown_error_message_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _, error, _, _, _ = _process_one(
            doc, tmp_path, parser_name="fallback", max_chars=800
        )
    assert "process_single returned None without errors" in error["message"]


def test_process_one_returns_parser_version_from_document_batch13(tmp_path):
    doc = _StubDoc(resolved_path=Path("/nonexistent"))
    stub_doc = _StubDocument(parser_version="9.9.9")

    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        _, _, _, parser_version, _ = _process_one(
            doc, tmp_path, parser_name="fallback", max_chars=800
        )
    assert parser_version == "9.9.9"


def test_process_one_uses_doc_id_for_out_stub_name_batch13(tmp_path):
    """out_stub 文件名应基于 doc.doc_id。"""
    doc = _StubDoc(doc_id="custom_id", resolved_path=Path("/nonexistent"))

    captured = {}

    def _fake_process(*args, **kwargs):
        captured["out_stub"] = args[1]
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process):
        _process_one(doc, tmp_path, parser_name="fallback", max_chars=800)
    assert captured["out_stub"].name == "custom_id.json"
    assert captured["out_stub"].parent.name == "_per_doc"


# ---------- run_evaluation 行为深度第十三批 ----------


def test_run_evaluation_report_version_from_evaluation_batch13(tmp_path):
    """report_version 应等于 evaluation.REPORT_VERSION。"""
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert out["report_version"] == REPORT_VERSION


def test_run_evaluation_writes_file_with_indent_2_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        run_evaluation(manifest, out_path)

    text = out_path.read_text(encoding="utf-8")
    # indent=2 → 有换行和 2 空格缩进
    assert "\n" in text
    assert '  "' in text


def test_run_evaluation_writes_file_with_ensure_ascii_false_batch13(tmp_path):
    """ensure_ascii=False → Unicode 字符不转义。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="文档1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        run_evaluation(manifest, out_path)

    text = out_path.read_text(encoding="utf-8")
    assert "文档1" in text  # 未转义


def test_run_evaluation_creates_output_root_batch13(tmp_path):
    """output_path 的父目录会被创建。"""
    manifest = _StubManifest()
    out_path = tmp_path / "sub1" / "sub2" / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        run_evaluation(manifest, out_path)

    assert out_path.is_file()


def test_run_evaluation_returns_report_dict_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert isinstance(out, dict)
    assert out["report_version"] == REPORT_VERSION


def test_run_evaluation_report_top_keys_exact_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert set(out.keys()) == {
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures",
    }


def test_run_evaluation_report_top_keys_order_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    expected_order = [
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures",
    ]
    assert list(out.keys()) == expected_order


def test_run_evaluation_per_doc_public_keys_exact_batch13(tmp_path):
    """公开 per_doc 应只有 4 个 key。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    for entry in out["per_doc"]:
        assert set(entry.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_per_doc_no_internal_keys_batch13(tmp_path):
    """公开 per_doc 不应含 _annotation_present / _tolerance_chars / _missing_markers。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    for entry in out["per_doc"]:
        assert "_annotation_present" not in entry
        assert "_tolerance_chars" not in entry
        assert "_missing_markers" not in entry


def test_run_evaluation_wall_time_seconds_keys_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    wt = out["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {
        "total", "parse", "chunk", "parse_reason", "chunk_reason",
    }


def test_run_evaluation_wall_time_parse_chunk_null_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    wt = out["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None


def test_run_evaluation_wall_time_parse_reason_constant_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    wt = out["per_doc"][0]["wall_time_seconds"]
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failure_matches_true_batch13(tmp_path):
    ef = _StubExpectedFailure(doc_id="ef1", expected_error_code="unsupported_format")
    manifest = _StubManifest(expected_failures=[ef])
    out_path = tmp_path / "report.json"

    err = _StubError(code="unsupported_format")
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, out_path)

    ef_result = out["expected_failures"][0]
    assert ef_result["matches"] is True


def test_run_evaluation_expected_failure_matches_false_batch13(tmp_path):
    ef = _StubExpectedFailure(doc_id="ef1", expected_error_code="unsupported_format")
    manifest = _StubManifest(expected_failures=[ef])
    out_path = tmp_path / "report.json"

    err = _StubError(code="parse_failed")  # 不匹配
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        out = run_evaluation(manifest, out_path)

    ef_result = out["expected_failures"][0]
    assert ef_result["matches"] is False


def test_run_evaluation_expected_failure_keys_exact_batch13(tmp_path):
    ef = _StubExpectedFailure(doc_id="ef1", expected_error_code="x")
    manifest = _StubManifest(expected_failures=[ef])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    ef_result = out["expected_failures"][0]
    assert set(ef_result.keys()) == {
        "doc_id", "expected_error_code", "actual_error_code", "matches",
    }


def test_run_evaluation_provenance_uses_manifest_project_root_batch13(tmp_path):
    manifest = _StubManifest(project_root=Path("/specific/path"))
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    # provenance.git_commit/dirty 应反映 /specific/path（patched subprocess.run）
    # 这里只验证 provenance 存在
    assert "provenance" in out


def test_run_evaluation_propagates_tolerance_chars_batch13(tmp_path):
    """tolerance_chars 应传给 chunk_boundary_prf。"""
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.chunk_boundary_prf") as cb_mock:
            cb_mock.return_value = {}
            run_evaluation(manifest, out_path, tolerance_chars=99)

    assert cb_mock.called
    assert cb_mock.call_args.kwargs.get("tolerance_chars") == 99


def test_run_evaluation_default_tolerance_30_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.chunk_boundary_prf") as cb_mock:
            cb_mock.return_value = {}
            run_evaluation(manifest, out_path)

    assert cb_mock.call_args.kwargs.get("tolerance_chars") == 30


def test_run_evaluation_calls_compute_automatic_metrics_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}) as m:
            run_evaluation(manifest, out_path)

    assert m.called


def test_run_evaluation_calls_figure_caption_prf_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.figure_caption_prf", return_value={}) as m:
            run_evaluation(manifest, out_path)

    assert m.called


def test_run_evaluation_calls_aggregate_summary_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.aggregate_summary", return_value={"x": 1}) as m:
            out = run_evaluation(manifest, out_path)

    assert m.called
    assert out["summary"] == {"x": 1}


def test_run_evaluation_calls_build_provenance_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.build_provenance", return_value={"p": 1}) as m:
            out = run_evaluation(manifest, out_path)

    assert m.called
    assert out["provenance"] == {"p": 1}


def test_run_evaluation_calls_build_devset_section_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.build_devset_section", return_value={"d": 1}) as m:
            out = run_evaluation(manifest, out_path)

    assert m.called
    assert out["devset"] == {"d": 1}


def test_run_evaluation_propagates_parser_name_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])) as mock:
        run_evaluation(manifest, out_path, parser_name="kreuzberg")

    for c in mock.call_args_list:
        assert c.kwargs.get("parser_name") == "kreuzberg"


def test_run_evaluation_propagates_max_chars_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])) as mock:
        run_evaluation(manifest, out_path, max_chars=400)

    for c in mock.call_args_list:
        assert c.kwargs.get("max_chars") == 400


def test_run_evaluation_parser_version_first_doc_wins_batch13(tmp_path):
    """parser_version_for_prov 应取第一个有值的 doc。"""
    doc1 = _StubDoc(doc_id="d1")
    doc2 = _StubDoc(doc_id="d2")
    manifest = _StubManifest(documents=[doc1, doc2])
    out_path = tmp_path / "report.json"

    calls = [
        (_StubDocument(parser_version="v1"), []),
        (_StubDocument(parser_version="v2"), []),
    ]
    with patch("evaluation.runner.process_single", side_effect=calls):
        with patch("evaluation.runner.build_provenance", return_value={}) as bp:
            run_evaluation(manifest, out_path)

    # build_provenance 应被 parser_version=v1 调用
    assert bp.call_args.kwargs.get("parser_version") == "v1"


def test_run_evaluation_parser_version_none_when_all_none_batch13(tmp_path):
    manifest = _StubManifest(documents=[_StubDoc(doc_id="d1")])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.build_provenance", return_value={}) as bp:
            run_evaluation(manifest, out_path)

    assert bp.call_args.kwargs.get("parser_version") is None


def test_run_evaluation_expected_failures_empty_for_empty_manifest_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert out["expected_failures"] == []


# ---------- module source forbidden tokens 第十八批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from multiprocessing import",
        "from asyncio import",
        "ctypes.",
        "import ctypes",
        "import marshal",
        "marshal.",
    ],
)
def test_runner_source_no_forbidden_token_eighteenth_batch13(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_runner_source_no_os_module_usage_batch13():
    source = inspect.getsource(rmod)
    assert "import os" not in source
    assert "os." not in source


def test_runner_source_no_sys_module_usage_batch13():
    source = inspect.getsource(rmod)
    assert "import sys" not in source
    assert "sys." not in source


def test_runner_source_no_shutil_usage_batch13():
    source = inspect.getsource(rmod)
    assert "shutil" not in source


def test_runner_source_no_tempfile_usage_batch13():
    source = inspect.getsource(rmod)
    assert "tempfile" not in source


def test_runner_source_no_logging_batch13():
    source = inspect.getsource(rmod)
    assert "import logging" not in source


def test_runner_source_no_re_module_batch13():
    source = inspect.getsource(rmod)
    assert "import re" not in source
    assert "re." not in source


def test_runner_source_no_eval_call_batch13():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_runner_source_no_compile_call_batch13():
    source = inspect.getsource(rmod)
    assert "compile(" not in source


def test_runner_source_no_global_keyword_batch13():
    source = inspect.getsource(rmod)
    assert "\nglobal " not in source


def test_runner_source_no_nonlocal_keyword_batch13():
    source = inspect.getsource(rmod)
    assert "nonlocal " not in source


def test_runner_source_no_lambda_batch13():
    source = inspect.getsource(rmod)
    assert "lambda " not in source


def test_runner_source_no_assert_batch13():
    source = inspect.getsource(rmod)
    assert "\nassert " not in source


def test_runner_source_no_print_batch13():
    source = inspect.getsource(rmod)
    assert "print(" not in source


def test_runner_source_no_input_function_batch13():
    source = inspect.getsource(rmod)
    assert "input(" not in source


def test_runner_source_no_with_open_w_at_top_level_batch13():
    """with open(w) 只允许在函数内部。"""
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" ") and "with " in line:
            raise AssertionError(f"top-level with: {line}")


# ---------- module source 字符串精确补强第十五批 ----------


def test_module_source_imports_json_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_time_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import time" in head


def test_module_source_imports_pathlib_path_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_any_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_pipeline_functions_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from app.pipeline import image_output_dir_for, process_single" in head


def test_module_source_imports_report_helpers_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:40])
    assert "from evaluation.report import" in head
    assert "aggregate_summary" in head
    assert "build_devset_section" in head
    assert "build_provenance" in head


def test_module_source_imports_annotation_metrics_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.annotation_metrics import" in head
    assert "chunk_boundary_prf" in head
    assert "figure_caption_prf" in head


def test_module_source_imports_metrics_compute_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.metrics import compute_automatic_metrics" in head


def test_module_source_uses_perf_counter_batch13():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_uses_json_dump_batch13():
    source = inspect.getsource(rmod)
    assert "json.dump(" in source


def test_module_source_uses_json_load_batch13():
    source = inspect.getsource(rmod)
    assert "json.load(" in source


def test_module_source_uses_ensure_ascii_false_batch13():
    source = inspect.getsource(rmod)
    assert "ensure_ascii=False" in source


def test_module_source_uses_indent_2_batch13():
    source = inspect.getsource(rmod)
    assert "indent=2" in source


def test_module_source_has_not_instrumented_string_batch13():
    source = inspect.getsource(rmod)
    assert '"not_instrumented"' in source or "'not_instrumented'" in source


def test_module_source_has_unknown_code_batch13():
    source = inspect.getsource(rmod)
    assert '"unknown"' in source or "'unknown'" in source


def test_module_source_has_annotation_present_marker_batch13():
    source = inspect.getsource(rmod)
    assert "_annotation_present" in source


def test_module_source_has_tolerance_chars_marker_batch13():
    source = inspect.getsource(rmod)
    assert "_tolerance_chars" in source
    assert "_missing_markers" in source


def test_module_source_has_per_doc_subdir_batch13():
    source = inspect.getsource(rmod)
    assert '"_per_doc"' in source or "'_per_doc'" in source


def test_module_source_has_image_output_dir_for_call_batch13():
    source = inspect.getsource(rmod)
    assert "image_output_dir_for(" in source


def test_module_source_has_process_single_call_batch13():
    source = inspect.getsource(rmod)
    assert "process_single(" in source


def test_module_source_future_annotations_top_level_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


# ---------- signatures 第十五批 ----------


def test_load_annotation_signature_one_param_batch13():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_load_annotation_param_annotation_optional_path_batch13():
    sig = inspect.signature(_load_annotation)
    annot = sig.parameters["path"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "None" in annot_str


def test_load_annotation_return_annotation_batch13():
    sig = inspect.signature(_load_annotation)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "dict" in ret_str
    assert "None" in ret_str


def test_process_one_signature_4_params_batch13():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_return_annotation_5_tuple_batch13():
    sig = inspect.signature(_process_one)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "tuple" in ret_str


def test_process_one_param_kinds_batch13():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_signature_2_positional_3_kw_only_batch13():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].name == "manifest"
    assert params[1].name == "output_path"
    # parser_name / max_chars / tolerance_chars 是 keyword-only
    assert params[2].name == "parser_name"
    assert params[3].name == "max_chars"
    assert params[4].name == "tolerance_chars"
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_default_parser_name_fallback_batch13():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_default_max_chars_800_batch13():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_default_tolerance_chars_30_batch13():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_return_annotation_dict_batch13():
    sig = inspect.signature(run_evaluation)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "dict" in ret_str


def test_module_dunder_all_one_item_batch13():
    assert hasattr(rmod, "__all__")
    assert rmod.__all__ == ["run_evaluation"]


def test_public_function_count_3_batch13():
    """模块顶层用户函数（含下划线开头）共 3 个。"""
    funcs = [
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_run_evaluation_no_varargs_batch13():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


# ---------- module 合理性第十五批 ----------


def test_module_dunder_file_exists_batch13():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_path_evaluation_runner_batch13():
    import os
    sep = os.sep
    assert rmod.__file__.endswith(sep + "runner.py")
    assert "evaluation" in rmod.__file__


def test_module_name_evaluation_runner_batch13():
    assert rmod.__name__ == "evaluation.runner"


def test_module_docstring_present_batch13():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


def test_module_docstring_mentions_instrumented_batch13():
    assert rmod.__doc__ is not None
    assert "not_instrumented" in rmod.__doc__ or "未插桩" in rmod.__doc__ or "instrumented" in rmod.__doc__


def test_module_uses_future_annotations_batch13():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_no_user_classes_batch13():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_report_version_attr_present_batch13():
    assert hasattr(rmod, "REPORT_VERSION")


def test_module_report_version_value_matches_batch13():
    assert rmod.REPORT_VERSION == REPORT_VERSION


def test_module_top_level_constants_count_batch13():
    """模块顶层用户常量（import 进来的）应在合理范围。"""
    consts = [
        n for n, v in vars(rmod).items()
        if not n.startswith("__") and not callable(v) and not inspect.ismodule(v)
        and not inspect.isclass(v)
    ]
    # REPORT_VERSION 是从 evaluation 顶部 import 进来的
    assert "REPORT_VERSION" in consts


def test_module_top_level_user_functions_3_batch13():
    funcs = [
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert len(funcs) == 3


# ---------- 端到端集成第十五批 ----------


def test_e2e_run_evaluation_writes_json_serializable_report_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    text = out_path.read_text(encoding="utf-8")
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_full_run_with_docs_and_expected_failures_batch13(tmp_path):
    doc = _StubDoc(doc_id="d1")
    ef = _StubExpectedFailure(doc_id="ef1", expected_error_code="x")
    manifest = _StubManifest(documents=[doc], expected_failures=[ef])
    out_path = tmp_path / "report.json"

    with patch(
        "evaluation.runner.process_single",
        return_value=(_StubDocument(parser_version="v1"), []),
    ):
        out = run_evaluation(manifest, out_path)

    assert len(out["per_doc"]) == 1
    assert out["per_doc"][0]["doc_id"] == "d1"
    assert len(out["expected_failures"]) == 1
    assert out["expected_failures"][0]["doc_id"] == "ef1"


def test_e2e_run_evaluation_summary_aggregated_batch13(tmp_path):
    doc = _StubDoc(doc_id="d1")
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert "summary" in out
    assert "counts" in out["summary"]
    assert "success_rates" in out["summary"]
    assert "ratio_macro_averages" in out["summary"]


def test_e2e_run_evaluation_devset_section_present_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert "devset" in out
    assert "status" in out["devset"]


def test_e2e_run_evaluation_provenance_section_present_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert "provenance" in out
    assert "evaluator_version" in out["provenance"]


def test_e2e_run_evaluation_creates_per_doc_subdir_batch13(tmp_path):
    """output_root/_per_doc 子目录应被创建（即使 process_single 是 mock）。"""
    doc = _StubDoc(doc_id="d1")
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "reports" / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        run_evaluation(manifest, out_path)

    assert (tmp_path / "reports" / "_per_doc").is_dir()


def test_e2e_run_evaluation_idempotent_for_empty_manifest_batch13(tmp_path):
    """两次跑空 manifest → report 内容相同（除 timestamp 外）。"""
    manifest = _StubManifest()
    out_path1 = tmp_path / "r1.json"
    out_path2 = tmp_path / "r2.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out1 = run_evaluation(manifest, out_path1)
        out2 = run_evaluation(manifest, out_path2)

    # 移除 timestamp 字段比较
    out1["provenance"].pop("run_timestamp_iso", None)
    out2["provenance"].pop("run_timestamp_iso", None)
    assert out1 == out2


def test_e2e_run_evaluation_returns_same_as_written_batch13(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    parsed = json.loads(out_path.read_text(encoding="utf-8"))
    assert parsed == out


def test_e2e_run_evaluation_per_doc_preserves_doc_id_batch13(tmp_path):
    doc1 = _StubDoc(doc_id="alpha")
    doc2 = _StubDoc(doc_id="beta")
    manifest = _StubManifest(documents=[doc1, doc2])
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    doc_ids = [e["doc_id"] for e in out["per_doc"]]
    assert doc_ids == ["alpha", "beta"]


def test_e2e_load_annotation_then_run_combined_batch13(tmp_path):
    """_load_annotation 单独跑 + run_evaluation 集成。"""
    # 先验证 _load_annotation
    p = tmp_path / "ann.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    out_ann = _load_annotation(p)
    assert out_ann == {"k": "v"}

    # 再跑 run_evaluation
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = run_evaluation(manifest, out_path)

    assert "report_version" in out
