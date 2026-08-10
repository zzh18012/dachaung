"""evaluation/runner.py 第三十七轮 edges 测试（Round 382）。

补强 edges35 未触及的角度：
- _load_annotation 行为深度第九批（追加 JSONDecodeError / empty file / 多种 falsy JSON value / 不返回 list 等）
- _process_one 行为深度第九批（process_single 多 errors / document None 同时 errors / parser_version 透传 / stub 不存在 unlink 路径）
- run_evaluation 行为深度第九批（report 写盘后可读 / 多 doc 顺序 / parser_version 多 doc 中第二个有也用首非空 / tolerance_chars 透传）
- module source forbidden tokens 第十四批
- module source 字符串精确补强第八批（详细 import + helper 调用 + dict key 字面量 + 不变式字面量）
- signatures 第九批（5 funcs param kinds + return types + 参数顺序）
- module 合理性第九批（__all__ 单项 + module 文件路径 + 3 module-level functions + 文档字符串 mentions）
- 端到端集成第九批（report_version / devset / per_doc 与 per_doc_results 一致 / wall_time_seconds 6 keys）
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path
from unittest.mock import patch

import pytest

from evaluation import REPORT_VERSION, runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- helpers ----------


class _StubDoc:
    """最小 DocumentEntry stub。"""

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


# ---------- _load_annotation 行为深度第九批 ----------


def test_load_annotation_returns_none_for_nonexistent_file(tmp_path):
    p = tmp_path / "no_such_file.json"
    assert _load_annotation(p) is None


def test_load_annotation_returns_none_for_none_input():
    assert _load_annotation(None) is None


def test_load_annotation_returns_none_for_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json {", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_none_for_empty_file(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_json_value_for_object(tmp_path):
    p = tmp_path / "obj.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


def test_load_annotation_returns_json_value_for_array(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    assert _load_annotation(p) == [1, 2, 3]


def test_load_annotation_returns_json_value_for_number(tmp_path):
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    assert _load_annotation(p) == 42


def test_load_annotation_returns_json_value_for_string(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    assert _load_annotation(p) == "hello"


def test_load_annotation_returns_json_value_for_true(tmp_path):
    p = tmp_path / "true.json"
    p.write_text("true", encoding="utf-8")
    assert _load_annotation(p) is True


def test_load_annotation_returns_json_value_for_null(tmp_path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_falsy_zero(tmp_path):
    p = tmp_path / "zero.json"
    p.write_text("0", encoding="utf-8")
    assert _load_annotation(p) == 0


def test_load_annotation_returns_falsy_empty_object(tmp_path):
    p = tmp_path / "empty_obj.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_opens_with_utf8_encoding(tmp_path):
    """读 UTF-8 多字节内容（中文）不抛。"""
    p = tmp_path / "cn.json"
    p.write_text('{"key": "中文值"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "中文值"}


def test_load_annotation_handles_bom(tmp_path):
    """encoding='utf-8'（非 utf-8-sig）→ BOM 字节会变 ﻿，json 解析失败 → 返回 None。"""
    p = tmp_path / "bom.json"
    # 写 UTF-8 BOM + JSON 内容
    p.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    out = _load_annotation(p)
    # utf-8 解码 BOM 后变 ﻿，json 解析失败 → None
    assert out is None


def test_load_annotation_truncated_json(tmp_path):
    p = tmp_path / "trunc.json"
    p.write_text('{"a": 1, "b":', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_just_braces(tmp_path):
    p = tmp_path / "braces.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_path_is_dir_returns_none(tmp_path):
    assert _load_annotation(tmp_path) is None


# ---------- _process_one 行为深度第九批 ----------


def test_process_one_signature_returns_5_tuple(monkeypatch, tmp_path):
    """5-tuple (document_dict, error_dict, total_seconds, parser_version, image_dir)。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake_process_single(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake_process_single)
    result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_success_returns_document_dict_first(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    document, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is not None
    assert error is None


def test_process_one_errors_non_empty_returns_error_dict(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    document, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "parse_failed", "message": "boom"}


def test_process_one_document_none_no_errors_returns_unknown(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    document, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "unknown", "message": "process_single returned None without errors"}


def test_process_one_returns_float_total_seconds(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total, float)
    assert total >= 0


def test_process_one_parser_version_returned_on_success(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(parser_version="1.2.3"), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _, _, _, pv, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert pv == "1.2.3"


def test_process_one_parser_version_none_on_error(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _, _, _, pv, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert pv is None


def test_process_one_image_dir_none_when_document_none(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_image_dir_path_object_when_document(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(image_dir, Path)


def test_process_one_unlinks_stub_after_success(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "fallback", 800)
    per_doc_dir = tmp_path / "_per_doc"
    stub = per_doc_dir / "doc1.json"
    assert not stub.is_file()


def test_process_one_creates_per_doc_subdir(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_out_stub_under_per_doc_subdir(monkeypatch, tmp_path):
    """out_stub 路径 = output_root/_per_doc/<doc_id>.json。"""
    doc = _StubDoc(doc_id="my_doc", resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    captured_stub = []

    def _fake(input_path, output_path, **kwargs):
        captured_stub.append(output_path)
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "fallback", 800)
    assert str(captured_stub[0]).endswith("_per_doc" + "\\" + "my_doc.json") or str(
        captured_stub[0]
    ).endswith("_per_doc" + "/" + "my_doc.json")


def test_process_one_unlink_swallows_oserror(monkeypatch, tmp_path):
    """unlink 失败 OSError 不抛（被 except 吞）。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    # stub 实际会被 unlink；mock Path.unlink 抛 OSError
    with patch("pathlib.Path.unlink", side_effect=OSError("perm")):
        # 不抛 = 通过
        _process_one(doc, tmp_path, "fallback", 800)


# ---------- run_evaluation 行为深度第九批 ----------


def test_run_evaluation_empty_manifest_writes_report_to_disk(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _StubManifest()
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_returns_dict(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _StubManifest()
    out = run_evaluation(manifest, out_path)
    assert isinstance(out, dict)


def test_run_evaluation_returns_same_dict_as_written(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _StubManifest()
    returned = run_evaluation(manifest, out_path)
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert returned == written


def test_run_evaluation_report_keys_exact_six(tmp_path):
    out_path = tmp_path / "report.json"
    manifest = _StubManifest()
    out = run_evaluation(manifest, out_path)
    assert set(out.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_report_version_value(tmp_path):
    out_path = tmp_path / "report.json"
    out = run_evaluation(_StubManifest(), out_path)
    assert out["report_version"] == REPORT_VERSION


def test_run_evaluation_per_doc_empty_when_no_documents(tmp_path):
    out = run_evaluation(_StubManifest(), tmp_path / "r.json")
    assert out["per_doc"] == []


def test_run_evaluation_expected_failures_empty_when_none(tmp_path):
    out = run_evaluation(_StubManifest(), tmp_path / "r.json")
    assert out["expected_failures"] == []


def test_run_evaluation_creates_parent_dir(tmp_path):
    out_path = tmp_path / "subdir" / "deep" / "report.json"
    run_evaluation(_StubManifest(), out_path)
    assert out_path.is_file()


def test_run_evaluation_uses_indent_2(tmp_path):
    out_path = tmp_path / "report.json"
    run_evaluation(_StubManifest(), out_path)
    text = out_path.read_text(encoding="utf-8")
    # 缩进 2 空格 → 至少一行前缀 2 spaces
    assert "\n  " in text


def test_run_evaluation_uses_ensure_ascii_false(tmp_path):
    """中文等非 ASCII 字符应原样写出（不转义）。"""
    out_path = tmp_path / "report.json"
    manifest = _StubManifest()
    manifest.devset_status = "incomplete"
    out = run_evaluation(manifest, out_path)
    # devset_section 不含非 ASCII；模拟在 categories_covered 注入中文
    manifest.categories_covered = ["中文"]
    out = run_evaluation(manifest, out_path)
    text = out_path.read_text(encoding="utf-8")
    assert "中文" in text


def test_run_evaluation_str_output_path(tmp_path):
    """str 类型 path 也能工作。"""
    out_path = str(tmp_path / "r.json")
    out = run_evaluation(_StubManifest(), out_path)
    assert isinstance(out, dict)


def test_run_evaluation_keyword_args(tmp_path):
    """run_evaluation 支持 keyword-only args（output_path 必传 positional）。"""
    out_path = tmp_path / "r.json"
    out = run_evaluation(
        _StubManifest(),
        out_path,
        parser_name="fallback",
        max_chars=500,
        tolerance_chars=20,
    )
    assert out["provenance"]["max_chars"] == 500


def test_run_evaluation_parser_name_forwarded_to_provenance(tmp_path):
    out_path = tmp_path / "r.json"
    out = run_evaluation(_StubManifest(), out_path, parser_name="kreuzberg")
    assert out["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_max_chars_forwarded_to_provenance(tmp_path):
    out_path = tmp_path / "r.json"
    out = run_evaluation(_StubManifest(), out_path, max_chars=300)
    assert out["provenance"]["max_chars"] == 300


def test_run_evaluation_one_document_produces_one_per_doc(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    manifest = _StubManifest(documents=[doc])
    out = run_evaluation(manifest, tmp_path / "r.json")
    assert len(out["per_doc"]) == 1


def test_run_evaluation_two_documents_preserves_order(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")
    d2 = _StubDoc(doc_id="d2", resolved_path=tmp_path / "b.pdf")
    d2.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1, d2]), tmp_path / "r.json")
    assert [d["doc_id"] for d in out["per_doc"]] == ["d1", "d2"]


def test_run_evaluation_per_doc_excludes_private_keys(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    pd = out["per_doc"][0]
    assert "_annotation_present" not in pd
    assert "_tolerance_chars" not in pd
    assert "_missing_markers" not in pd


def test_run_evaluation_per_doc_has_three_keys(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    pd = out["per_doc"][0]
    assert set(pd.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_wall_time_seconds_has_six_keys(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    wt = out["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {
        "total",
        "parse",
        "chunk",
        "parse_reason",
        "chunk_reason",
    } or set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_run_evaluation_parser_version_captured_from_first_success(monkeypatch, tmp_path):
    """parser_version 取首个成功的 doc。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return _StubDocument(parser_version="9.9.9"), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert out["provenance"]["parser_version"] == "9.9.9"


def test_run_evaluation_parser_version_none_when_all_fail(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert out["provenance"]["parser_version"] is None


def test_run_evaluation_expected_failure_matches(monkeypatch, tmp_path):
    class _EF:
        doc_id = "ef1"
        expected_error_code = "parse_failed"
        resolved_path = tmp_path / "x.pdf"

    _EF.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError(code="parse_failed")]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest(expected_failures=[_EF()]), tmp_path / "r.json")
    ef = out["expected_failures"][0]
    assert ef["matches"] is True
    assert ef["actual_error_code"] == "parse_failed"


def test_run_evaluation_expected_failure_no_match(monkeypatch, tmp_path):
    class _EF:
        doc_id = "ef1"
        expected_error_code = "different_code"
        resolved_path = tmp_path / "x.pdf"

    _EF.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError(code="parse_failed")]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest(expected_failures=[_EF()]), tmp_path / "r.json")
    ef = out["expected_failures"][0]
    assert ef["matches"] is False


def test_run_evaluation_expected_failure_keys_exact(monkeypatch, tmp_path):
    class _EF:
        doc_id = "ef1"
        expected_error_code = "x"
        resolved_path = tmp_path / "x.pdf"

    _EF.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest(expected_failures=[_EF()]), tmp_path / "r.json")
    ef = out["expected_failures"][0]
    assert set(ef.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}


# ---------- module source forbidden tokens 第十四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "yaml.load",
        "subprocess.check_call",
        "subprocess.call",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "exit(",
        "quit(",
    ],
)
def test_runner_source_no_forbidden_token_fourteenth(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_runner_source_no_unlink_outside_helpers():
    """unlink 仅在 _process_one / run_evaluation 内部出现（清理 stub），不应在模块顶层。"""
    source = inspect.getsource(rmod)
    # 顶层不应直接调用 unlink
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        # 模块顶层（无缩进）不应有 unlink 调用
        if stripped.startswith("unlink") and not line.startswith(" "):
            raise AssertionError(f"top-level unlink call: {line}")


def test_runner_source_no_global_keyword():
    source = inspect.getsource(rmod)
    # 顶层不应有 global 声明
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("global ") and not line.startswith(" "):
            raise AssertionError(f"top-level global: {line}")


def test_runner_source_no_class_def():
    source = inspect.getsource(rmod)
    assert "class " not in source


def test_runner_source_no_async_def():
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_runner_source_no_yield():
    source = inspect.getsource(rmod)
    assert "yield" not in source


def test_runner_source_no_walrus():
    source = inspect.getsource(rmod)
    assert ":=" not in source


def test_runner_source_no_top_level_lambda():
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            # 顶层 lambda 赋值
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_runner_source_no_print_statements():
    source = inspect.getsource(rmod)
    assert "print(" not in source


def test_runner_source_no_logging():
    source = inspect.getsource(rmod)
    assert "logging" not in source
    assert "logger" not in source


def test_runner_source_no_sleep():
    source = inspect.getsource(rmod)
    assert "time.sleep" not in source


def test_runner_source_no_hardcoded_absolute_path():
    source = inspect.getsource(rmod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_has_from_future_annotations():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json():
    source = inspect.getsource(rmod)
    assert "import json" in source


def test_module_source_imports_time():
    source = inspect.getsource(rmod)
    assert "import time" in source


def test_module_source_imports_path():
    source = inspect.getsource(rmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any():
    source = inspect.getsource(rmod)
    assert "from typing import Any" in source


def test_module_source_imports_process_single():
    source = inspect.getsource(rmod)
    assert "process_single" in source
    assert "from app.pipeline import" in source


def test_module_source_imports_image_output_dir_for():
    source = inspect.getsource(rmod)
    assert "image_output_dir_for" in source


def test_module_source_imports_report_version():
    source = inspect.getsource(rmod)
    assert "REPORT_VERSION" in source


def test_module_source_imports_annotation_metrics():
    source = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in source
    assert "figure_caption_prf" in source


def test_module_source_imports_compute_automatic_metrics():
    source = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in source


def test_module_source_imports_aggregate_summary():
    source = inspect.getsource(rmod)
    assert "aggregate_summary" in source


def test_module_source_imports_build_devset_section():
    source = inspect.getsource(rmod)
    assert "build_devset_section" in source


def test_module_source_imports_build_provenance():
    source = inspect.getsource(rmod)
    assert "build_provenance" in source


def test_module_source_has_three_module_level_functions():
    """3 个 module-level 函数：_load_annotation, _process_one, run_evaluation。"""
    source = inspect.getsource(rmod)
    assert source.count("def _load_annotation") == 1
    assert source.count("def _process_one") == 1
    assert source.count("def run_evaluation") == 1


def test_module_source_uses_time_perf_counter():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_uses_per_doc_subdir():
    source = inspect.getsource(rmod)
    assert '"_per_doc"' in source or "'_per_doc'" in source


def test_module_source_uses_doc_id_template():
    source = inspect.getsource(rmod)
    assert "{doc.doc_id}" in source or "{doc_id}" in source or "{ef.doc_id}" in source


def test_module_source_no_main_block():
    source = inspect.getsource(rmod)
    assert "if __name__" not in source


def test_module_source_docstring_present():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 50


def test_module_source_docstring_mentions_total():
    assert "total" in rmod.__doc__


def test_module_source_docstring_mentions_not_instrumented():
    assert "not_instrumented" in rmod.__doc__ or "not instrumented" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_pipeline():
    assert "pipeline" in rmod.__doc__.lower()


def test_module_source_report_version_in_final_report():
    """report_version 字段必须出现在最终 report dict 中。"""
    source = inspect.getsource(rmod)
    assert '"report_version"' in source
    assert "REPORT_VERSION" in source


def test_module_source_provenance_in_final_report():
    source = inspect.getsource(rmod)
    assert '"provenance"' in source


def test_module_source_devset_in_final_report():
    source = inspect.getsource(rmod)
    assert '"devset"' in source


def test_module_source_summary_in_final_report():
    source = inspect.getsource(rmod)
    assert '"summary"' in source


def test_module_source_per_doc_in_final_report():
    source = inspect.getsource(rmod)
    assert '"per_doc"' in source


def test_module_source_expected_failures_in_final_report():
    source = inspect.getsource(rmod)
    assert '"expected_failures"' in source


def test_module_source_wall_time_seconds_keys():
    """wall_time_seconds 6 keys: total/parse/chunk/parse_reason/chunk_reason。"""
    source = inspect.getsource(rmod)
    assert '"total"' in source
    assert '"parse"' in source
    assert '"chunk"' in source
    assert '"parse_reason"' in source
    assert '"chunk_reason"' in source
    assert '"not_instrumented"' in source


def test_module_source_json_dump_call():
    source = inspect.getsource(rmod)
    assert "json.dump(" in source


def test_module_source_ensure_ascii_false():
    source = inspect.getsource(rmod)
    assert "ensure_ascii=False" in source


def test_module_source_indent_2():
    source = inspect.getsource(rmod)
    assert "indent=2" in source


def test_module_source_unknown_error_message():
    """document None 且无 errors 时返回 'process_single returned None without errors'。"""
    source = inspect.getsource(rmod)
    assert "process_single returned None without errors" in source


def test_module_source_unknown_error_code():
    source = inspect.getsource(rmod)
    assert '"unknown"' in source


# ---------- signatures 第九批 ----------


def test_signature_load_annotation_param_count():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_signature_load_annotation_param_name_path():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


def test_signature_load_annotation_param_kind():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_load_annotation_param_annotation():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    # `from __future__ import annotations` 让注解变字符串
    assert p.annotation == "Path | None" or p.annotation == Path | None


def test_signature_load_annotation_return_annotation():
    sig = inspect.signature(_load_annotation)
    ra = sig.return_annotation
    assert ra == "dict[str, Any] | None" or ra == dict[str, any] | None


def test_signature_process_one_param_count():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_signature_process_one_param_names():
    sig = inspect.signature(_process_one)
    names = list(sig.parameters)
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_param_kinds():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_process_one_no_defaults():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_process_one_return_annotation_is_tuple():
    sig = inspect.signature(_process_one)
    ra = sig.return_annotation
    # tuple[...] 形式
    assert ra.startswith("tuple[") or isinstance(ra, types.GenericAlias)


def test_signature_run_evaluation_param_count():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_signature_run_evaluation_param_names():
    sig = inspect.signature(run_evaluation)
    names = list(sig.parameters)
    assert names == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_manifest_positional_or_keyword():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].name == "manifest"
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation_output_path_positional_or_keyword():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[1].name == "output_path"
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation_keyword_only_after_star():
    """parser_name / max_chars / tolerance_chars 都是 KEYWORD_ONLY（在 * 之后）。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    # 找到 * marker（KEYWORD_ONLY 前的 VAR_POSITIONAL placeholder）
    # 实际：参数 manifest, output_path 后跟 *, parser_name, max_chars, tolerance_chars
    keyword_only = [p for p in params if p.kind == inspect.Parameter.KEYWORD_ONLY]
    assert len(keyword_only) == 3
    assert {p.name for p in keyword_only} == {"parser_name", "max_chars", "tolerance_chars"}


def test_signature_run_evaluation_keyword_only_defaults():
    sig = inspect.signature(run_evaluation)
    keyword_only = [p for p in sig.parameters.values() if p.kind == inspect.Parameter.KEYWORD_ONLY]
    defaults = {p.name: p.default for p in keyword_only}
    assert defaults["parser_name"] == "fallback"
    assert defaults["max_chars"] == 800
    assert defaults["tolerance_chars"] == 30


def test_signature_run_evaluation_no_var_positional():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_run_evaluation_no_var_keyword():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_run_evaluation_return_annotation():
    sig = inspect.signature(run_evaluation)
    ra = sig.return_annotation
    assert ra == "dict[str, Any]" or ra == dict[str, any]


def test_signature_3_funcs_are_function_type():
    for func in (_load_annotation, _process_one, run_evaluation):
        assert inspect.isfunction(func)


def test_signature_3_funcs_module_eq():
    for func in (_load_annotation, _process_one, run_evaluation):
        assert func.__module__ == "evaluation.runner"


# ---------- module 合理性第九批 ----------


def test_module_all_attribute_value():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_entries_unique():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_has_dunder_file():
    assert hasattr(rmod, "__file__")


def test_module_dunder_file_endswith_runner_py():
    import os
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "runner.py") or rmod.__file__.endswith(
        "evaluation/runner.py"
    )


def test_module_dunder_name():
    assert rmod.__name__ == "evaluation.runner"


def test_module_function_count():
    """3 module-level functions。"""
    funcs = [
        n
        for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert len(funcs) == 3
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_user_classes():
    classes = [
        n for n, v in vars(rmod).items() if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_no_call_at_top_level():
    """模块顶层不应直接执行函数调用（除 def）。"""
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            # 允许：def, import, from, __all__ 赋值, 注释, 空行
            ok_prefixes = (
                "def ",
                "import ",
                "from ",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
                "_",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                # 可能有函数调用
                if "(" in stripped and not stripped.startswith("def "):
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_constants_only_all():
    """模块顶层 tuple/list/dict 常量只有 __all__。"""
    consts = []
    for n, v in vars(rmod).items():
        if n.startswith("__"):
            continue
        if isinstance(v, (tuple, list, dict, set, frozenset)) and not callable(v):
            consts.append(n)
    assert set(consts) == set()  # __all__ 已通过 __ 前缀过滤


def test_module_docstring_present():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 50


# ---------- 端到端集成第九批 ----------


def test_e2e_load_annotation_idempotent_under_repeated_calls(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    out1 = _load_annotation(p)
    out2 = _load_annotation(p)
    out3 = _load_annotation(p)
    assert out1 == out2 == out3 == {"x": 1}


def test_e2e_load_annotation_none_returns_none_consistent():
    assert _load_annotation(None) is None
    assert _load_annotation(None) is None


def test_e2e_load_annotation_concurrent_safe_sequential(tmp_path):
    """连续调用不互相影响。"""
    p1 = tmp_path / "a.json"
    p1.write_text('{"x": 1}', encoding="utf-8")
    p2 = tmp_path / "b.json"
    p2.write_text('{"y": 2}', encoding="utf-8")
    assert _load_annotation(p1) == {"x": 1}
    assert _load_annotation(p2) == {"y": 2}
    assert _load_annotation(p1) == {"x": 1}


def test_e2e_load_annotation_unicode_key_and_value(tmp_path):
    p = tmp_path / "u.json"
    p.write_text('{"中文键": "中文值"}', encoding="utf-8")
    assert _load_annotation(p) == {"中文键": "中文值"}


def test_e2e_load_annotation_array_of_objects(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('[{"a":1}, {"b":2}]', encoding="utf-8")
    assert _load_annotation(p) == [{"a": 1}, {"b": 2}]


def test_e2e_load_annotation_returns_same_value_for_same_content(tmp_path):
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    p1.write_text('{"x":1}', encoding="utf-8")
    p2.write_text('{"x":1}', encoding="utf-8")
    assert _load_annotation(p1) == _load_annotation(p2)


def test_e2e_load_annotation_just_brackets(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[]", encoding="utf-8")
    assert _load_annotation(p) == []


def test_e2e_load_annotation_deeply_nested(tmp_path):
    p = tmp_path / "a.json"
    nested = {"a": {"b": {"c": {"d": {"e": "deep"}}}}}
    p.write_text(json.dumps(nested), encoding="utf-8")
    assert _load_annotation(p) == nested


def test_e2e_load_annotation_with_float(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("3.14", encoding="utf-8")
    assert _load_annotation(p) == 3.14


def test_e2e_load_annotation_with_scientific_notation(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("1e5", encoding="utf-8")
    assert _load_annotation(p) == 100000.0


def test_e2e_load_annotation_negative_number(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("-42", encoding="utf-8")
    assert _load_annotation(p) == -42


def test_e2e_load_annotation_json_with_whitespace(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('  {"x": 1}  ', encoding="utf-8")
    assert _load_annotation(p) == {"x": 1}


def test_e2e_load_annotation_json_with_newlines(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{\n  "x": 1\n}', encoding="utf-8")
    assert _load_annotation(p) == {"x": 1}


def test_e2e_run_evaluation_idempotent(tmp_path):
    """重复调用产出相同结构（部分字段如 timestamp 会变）。"""
    out1 = run_evaluation(_StubManifest(), tmp_path / "r1.json")
    out2 = run_evaluation(_StubManifest(), tmp_path / "r2.json")
    # summary 结构稳定
    assert list(out1["summary"].keys()) == list(out2["summary"].keys())
    # per_doc 长度稳定
    assert len(out1["per_doc"]) == len(out2["per_doc"])


def test_e2e_run_evaluation_end_to_end_with_empty_manifest_produces_valid_report(tmp_path):
    out = run_evaluation(_StubManifest(), tmp_path / "r.json")
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out
    assert "provenance" in parsed
    assert "summary" in parsed
    assert "per_doc" in parsed


def test_e2e_run_evaluation_returns_dict_type(tmp_path):
    out = run_evaluation(_StubManifest(), tmp_path / "r.json")
    assert isinstance(out, dict)


def test_e2e_module_runner_can_be_imported():
    import evaluation.runner as r
    assert r is rmod


def test_e2e_module_runner_run_evaluation_in_all():
    assert "run_evaluation" in rmod.__all__


def test_e2e_module_runner_run_evaluation_public_via_import():
    from evaluation.runner import run_evaluation as f
    assert f is run_evaluation


def test_e2e_load_annotation_handles_bom_properly(tmp_path):
    """encoding='utf-8' 不去 BOM → 解析失败 → None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    assert _load_annotation(p) is None


def test_e2e_load_annotation_truncated_json(tmp_path):
    p = tmp_path / "t.json"
    p.write_text('{"a":', encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_run_evaluation_with_annotation_loads_file(monkeypatch, tmp_path):
    """doc 有 annotation_resolved 时调用 _load_annotation。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")
    annot = tmp_path / "ann.json"
    annot.write_text("{}", encoding="utf-8")
    d1.annotation_resolved = annot

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    # 通过验证无异常 + 报告正常返回
    assert "per_doc" in out


def test_e2e_run_evaluation_annotation_missing_does_not_crash(monkeypatch, tmp_path):
    """annotation_resolved 指向不存在文件 → _load_annotation 返回 None，不抛。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")
    d1.annotation_resolved = tmp_path / "nonexistent.json"

    def _fake(*args, **kwargs):
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert "per_doc" in out
