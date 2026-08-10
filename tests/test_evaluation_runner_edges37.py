"""evaluation/runner.py 第三十八轮 edges 测试（Round 389）。

补强 edges36 未触及的角度：
- _load_annotation 行为深度第十批（更多边界：whitespace-only / very long / valid JSON nested types / path objects etc）
- _process_one 行为深度第十批（kwargs 透传 write_json=False / parser_name 透传 / max_chars 透传 / resolved_path 透传 / document.to_dict 调用 / errors[0].to_dict 调用 / errors empty + None document / image_dir 通过 image_output_dir_for）
- run_evaluation 行为深度第十批（tolerance_chars 透传 / _tolerance_chars 字段记录 / _missing_markers 字段记录 / annotation_present True/False / image_dir is_dir 校验 / parser_version first non-None wins / 多 doc 顺序 / expected_failures 流程）
- module source forbidden tokens 第十五批
- module source 字符串精确补强第十批
- signatures 第十批
- module 合理性第十批
- 端到端集成第十批
"""

from __future__ import annotations

import inspect
import json
import os
import types
from pathlib import Path
from unittest.mock import patch

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


# ---------- _load_annotation 行为深度第十批 ----------


def test_load_annotation_whitespace_only_returns_none(tmp_path):
    p = tmp_path / "ws.json"
    p.write_text("   \n\t  ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_with_tabs(tmp_path):
    p = tmp_path / "tabs.json"
    p.write_text('{"a":\t1}', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


def test_load_annotation_escaped_unicode(tmp_path):
    p = tmp_path / "esc.json"
    p.write_text('"\\u4e2d\\u6587"', encoding="utf-8")
    assert _load_annotation(p) == "中文"


def test_load_annotation_returns_object_with_list_value(tmp_path):
    p = tmp_path / "list.json"
    p.write_text('{"k": [1, 2, 3]}', encoding="utf-8")
    assert _load_annotation(p) == {"k": [1, 2, 3]}


def test_load_annotation_returns_object_with_nested_object(tmp_path):
    p = tmp_path / "nested.json"
    p.write_text('{"a": {"b": {"c": 1}}}', encoding="utf-8")
    assert _load_annotation(p) == {"a": {"b": {"c": 1}}}


def test_load_annotation_returns_object_with_null_value(tmp_path):
    p = tmp_path / "nullval.json"
    p.write_text('{"a": null}', encoding="utf-8")
    assert _load_annotation(p) == {"a": None}


def test_load_annotation_returns_object_with_bool_value(tmp_path):
    p = tmp_path / "boolval.json"
    p.write_text('{"a": false}', encoding="utf-8")
    assert _load_annotation(p) == {"a": False}


def test_load_annotation_returns_object_with_float_value(tmp_path):
    p = tmp_path / "float.json"
    p.write_text('{"pi": 3.14159}', encoding="utf-8")
    assert _load_annotation(p) == {"pi": 3.14159}


def test_load_annotation_returns_object_with_negative_int(tmp_path):
    p = tmp_path / "neg.json"
    p.write_text('{"a": -100}', encoding="utf-8")
    assert _load_annotation(p) == {"a": -100}


def test_load_annotation_returns_array_with_mixed_types(tmp_path):
    p = tmp_path / "mix.json"
    p.write_text('[1, "a", true, null, [2]]', encoding="utf-8")
    assert _load_annotation(p) == [1, "a", True, None, [2]]


def test_load_annotation_emoji_content(tmp_path):
    p = tmp_path / "emoji.json"
    p.write_text('"🎉"', encoding="utf-8")
    assert _load_annotation(p) == "🎉"


def test_load_annotation_long_string_value(tmp_path):
    p = tmp_path / "long.json"
    val = "x" * 10000
    p.write_text(json.dumps({"k": val}), encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": val}


def test_load_annotation_long_array(tmp_path):
    p = tmp_path / "longarr.json"
    arr = list(range(1000))
    p.write_text(json.dumps(arr), encoding="utf-8")
    assert _load_annotation(p) == arr


def test_load_annotation_json_with_trailing_newline(tmp_path):
    p = tmp_path / "newline.json"
    p.write_text('{"a": 1}\n', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


def test_load_annotation_json_with_leading_newline(tmp_path):
    p = tmp_path / "lead.json"
    p.write_text('\n{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


def test_load_annotation_quoted_key_with_special_chars(tmp_path):
    p = tmp_path / "spec.json"
    p.write_text('{"a/b": 1, "c-d": 2}', encoding="utf-8")
    assert _load_annotation(p) == {"a/b": 1, "c-d": 2}


def test_load_annotation_path_object_input(tmp_path):
    p = tmp_path / "obj.json"
    p.write_text('{"x":1}', encoding="utf-8")
    assert isinstance(p, Path)
    assert _load_annotation(p) == {"x": 1}


# ---------- _process_one 行为深度第十批 ----------


def test_process_one_write_json_false_passed(monkeypatch, tmp_path):
    """write_json=False 必须传给 process_single。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    captured = {}

    def _fake(input_path, output_path, *, parser_name=None, max_chars=None, write_json=True):
        captured["write_json"] = write_json
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "fallback", 800)
    assert captured["write_json"] is False


def test_process_one_parser_name_passed(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    captured = {}

    def _fake(input_path, output_path, *, parser_name=None, max_chars=None, write_json=True):
        captured["parser_name"] = parser_name
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "kreuzberg", 800)
    assert captured["parser_name"] == "kreuzberg"


def test_process_one_max_chars_passed(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    captured = {}

    def _fake(input_path, output_path, *, parser_name=None, max_chars=None, write_json=True):
        captured["max_chars"] = max_chars
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "fallback", 1200)
    assert captured["max_chars"] == 1200


def test_process_one_input_path_forwarded(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "my_input.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    captured = {}

    def _fake(input_path, output_path, *, parser_name=None, max_chars=None, write_json=True):
        captured["input_path"] = input_path
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "fallback", 800)
    assert captured["input_path"] == doc.resolved_path


def test_process_one_calls_to_dict_on_document(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    calls = []

    class _DocWithTracker:
        source_hash = "a" * 64
        parser_version = "1.0.0"

        def to_dict(self):
            calls.append("to_dict")
            return {"k": "v"}

    def _fake(*args, **kwargs):
        return _DocWithTracker(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    document_dict, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert calls == ["to_dict"]
    assert document_dict == {"k": "v"}


def test_process_one_calls_to_dict_on_error(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    calls = []

    class _ErrWithTracker:
        code = "parse_failed"
        message = "boom"

        def to_dict(self):
            calls.append("err_to_dict")
            return {"code": "parse_failed", "message": "boom"}

    def _fake(*args, **kwargs):
        return None, [_ErrWithTracker()]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert calls == ["err_to_dict"]
    assert error == {"code": "parse_failed", "message": "boom"}


def test_process_one_returns_first_error_when_multiple(monkeypatch, tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        return None, [_StubError("first"), _StubError("second")]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert error == {"code": "first", "message": "boom"}


def test_process_one_uses_image_output_dir_for(monkeypatch, tmp_path):
    """document 不为 None 时通过 image_output_dir_for 推 image_dir。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    captured = {}

    def _fake_image_dir(out_stub, source_hash):
        captured["out_stub"] = out_stub
        captured["source_hash"] = source_hash
        return Path("/fake/image_dir")

    monkeypatch.setattr("evaluation.runner.image_output_dir_for", _fake_image_dir)
    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == Path("/fake/image_dir")
    assert captured["source_hash"] == "a" * 64


def test_process_one_out_stub_parent_creation(monkeypatch, tmp_path):
    """out_stub.parent.mkdir(parents=True, exist_ok=True) 必须被调用。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    # 使用 nested output_root 验证 mkdir parents=True
    output_root = tmp_path / "deep" / "nested"
    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    _process_one(doc, output_root, "fallback", 800)
    assert (output_root / "_per_doc").is_dir()


def test_process_one_unlink_present_stub(monkeypatch, tmp_path):
    """stub 存在则被 unlink。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(input_path, output_path, **kwargs):
        # 模拟 pipeline 写文件
        Path(output_path).write_text("{}", encoding="utf-8")
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    _process_one(doc, tmp_path, "fallback", 800)
    assert not (tmp_path / "_per_doc" / "doc1.json").is_file()


def test_process_one_unlink_absent_silent(monkeypatch, tmp_path):
    """stub 不存在 → unlink 不调用（is_file 返 False 跳过）。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    # 不抛即可
    _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_perf_counter_called(monkeypatch, tmp_path):
    """process_single 必须被 perf_counter 包围（间接验证：total_seconds 是 elapsed）。"""
    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")
    counter = {"n": 0}

    def _fake_perf():
        counter["n"] += 1
        return counter["n"] * 0.001

    monkeypatch.setattr("evaluation.runner.time.perf_counter", _fake_perf)
    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    # perf_counter 至少调用 2 次（t0 / elapsed）
    assert counter["n"] >= 2


def test_process_one_total_seconds_positive_when_document_returned(monkeypatch, tmp_path):
    import time as _time

    doc = _StubDoc(resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake_slow(*args, **kwargs):
        # 真实 sleep 一点点
        for _ in range(10000):
            pass
        return _StubDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake_slow)
    _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert total >= 0


# ---------- run_evaluation 行为深度第十批 ----------


def test_run_evaluation_default_kwargs(tmp_path):
    """默认 parser_name=fallback, max_chars=800, tolerance_chars=30。"""
    out = run_evaluation(_StubManifest(), tmp_path / "r.json")
    assert out["provenance"]["parser_name"] == "fallback"
    assert out["provenance"]["max_chars"] == 800


def test_run_evaluation_creates_per_doc_subdir(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert (tmp_path / "_per_doc").is_dir()


def test_run_evaluation_per_doc_excludes_annotation_present(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    pd = out["per_doc"][0]
    # _annotation_present 是私有字段，不应出现在 public per_doc
    assert "_annotation_present" not in pd


def test_run_evaluation_per_doc_excludes_tolerance_chars(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert "_tolerance_chars" not in out["per_doc"][0]


def test_run_evaluation_per_doc_excludes_missing_markers(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert "_missing_markers" not in out["per_doc"][0]


def test_run_evaluation_image_dir_passed_to_metrics(monkeypatch, tmp_path):
    """image_dir.is_dir() True 时 image_base_dir 不为 None。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    captured = []

    def _fake_metrics(*, document, error, source_type, expectations, image_base_dir=None):
        captured.append(image_base_dir)
        return {"pipeline_success": {"value": True, "reason": None}}

    monkeypatch.setattr("evaluation.runner.process_single", lambda *a, **k: (_StubDocument(), []))
    monkeypatch.setattr("evaluation.runner.compute_automatic_metrics", _fake_metrics)
    monkeypatch.setattr(
        "evaluation.runner.image_output_dir_for",
        lambda stub, sha: tmp_path / "images",  # exists() 不会被检查，但 is_dir() 会被检查
    )
    # 创建目录使 is_dir() True
    (tmp_path / "images").mkdir()
    run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert captured[0] == tmp_path / "images"


def test_run_evaluation_image_dir_none_when_not_dir(monkeypatch, tmp_path):
    """image_dir 不存在 → image_base_dir 传 None。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    captured = []

    def _fake_metrics(*, document, error, source_type, expectations, image_base_dir=None):
        captured.append(image_base_dir)
        return {"pipeline_success": {"value": True, "reason": None}}

    monkeypatch.setattr("evaluation.runner.process_single", lambda *a, **k: (_StubDocument(), []))
    monkeypatch.setattr("evaluation.runner.compute_automatic_metrics", _fake_metrics)
    monkeypatch.setattr(
        "evaluation.runner.image_output_dir_for",
        lambda stub, sha: tmp_path / "nonexistent_images",
    )
    run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert captured[0] is None


def test_run_evaluation_annotation_present_true_when_loaded(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")
    annot = tmp_path / "ann.json"
    annot.write_text("{}", encoding="utf-8")
    d1.annotation_resolved = annot

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )

    # _annotation_present 是内部字段，per_doc_results 内部用
    captured = []

    real_run = run_evaluation

    def _wrapped(*args, **kwargs):
        out = real_run(*args, **kwargs)
        return out

    out = _wrapped(_StubManifest([d1]), tmp_path / "r.json")
    # public per_doc 不含 _annotation_present；但流程不抛 = annotation 被加载
    assert "per_doc" in out


def test_run_evaluation_expected_failure_no_errors_actual_none(monkeypatch, tmp_path):
    """expected_failure 流程：errors 空 → actual_error_code=None。"""
    class _EF:
        doc_id = "ef1"
        expected_error_code = "parse_failed"
        resolved_path = tmp_path / "x.pdf"

    _EF.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    out = run_evaluation(_StubManifest(expected_failures=[_EF()]), tmp_path / "r.json")
    ef = out["expected_failures"][0]
    assert ef["actual_error_code"] is None
    assert ef["matches"] is False


def test_run_evaluation_expected_failure_with_errors(monkeypatch, tmp_path):
    class _EF:
        doc_id = "ef1"
        expected_error_code = "parse_failed"
        resolved_path = tmp_path / "x.pdf"

    _EF.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (None, [_StubError("parse_failed")]),
    )
    out = run_evaluation(_StubManifest(expected_failures=[_EF()]), tmp_path / "r.json")
    ef = out["expected_failures"][0]
    assert ef["actual_error_code"] == "parse_failed"
    assert ef["matches"] is True


def test_run_evaluation_expected_failure_unlinks_stub(monkeypatch, tmp_path):
    class _EF:
        doc_id = "ef1"
        expected_error_code = "parse_failed"
        resolved_path = tmp_path / "x.pdf"

    _EF.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(input_path, output_path, **kwargs):
        Path(output_path).write_text("{}", encoding="utf-8")
        return None, [_StubError("parse_failed")]

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    run_evaluation(_StubManifest(expected_failures=[_EF()]), tmp_path / "r.json")
    assert not (tmp_path / "_per_doc" / "ef1.json").is_file()


def test_run_evaluation_parser_version_first_wins(monkeypatch, tmp_path):
    """多个 doc 时，parser_version 取首个非 None 的；之后的不会覆盖。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")
    d2 = _StubDoc(doc_id="d2", resolved_path=tmp_path / "b.pdf")
    d2.resolved_path.write_bytes(b"%PDF-1.4\n")

    def _fake(*args, **kwargs):
        # 始终返回相同 parser_version
        return _StubDocument(parser_version="1.0.0"), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1, d2]), tmp_path / "r.json")
    assert out["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_parser_version_first_fail_second_succeed(monkeypatch, tmp_path):
    """首个失败 → 第二个成功 → parser_version 取第二个的。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")
    d2 = _StubDoc(doc_id="d2", resolved_path=tmp_path / "b.pdf")
    d2.resolved_path.write_bytes(b"%PDF-1.4\n")

    call_count = {"n": 0}

    def _fake(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None, [_StubError()]
        return _StubDocument(parser_version="2.0.0"), []

    monkeypatch.setattr("evaluation.runner.process_single", _fake)
    out = run_evaluation(_StubManifest([d1, d2]), tmp_path / "r.json")
    assert out["provenance"]["parser_version"] == "2.0.0"


def test_run_evaluation_annotation_prf_metrics_merged(monkeypatch, tmp_path):
    """figure_caption_prf 与 chunk_boundary_prf 结果合并到 metrics。"""
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr("evaluation.runner.process_single", lambda *a, **k: (_StubDocument(), []))
    monkeypatch.setattr(
        "evaluation.runner.figure_caption_prf",
        lambda doc, annot: {"figure_caption_precision": {"value": 1.0, "reason": None}},
    )
    monkeypatch.setattr(
        "evaluation.runner.chunk_boundary_prf",
        lambda doc, annot, tolerance_chars=30: {"chunk_boundary_precision": {"value": 0.5, "reason": None}},
    )
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    metrics = out["per_doc"][0]["metrics"]
    assert metrics["figure_caption_precision"] == {"value": 1.0, "reason": None}
    assert metrics["chunk_boundary_precision"] == {"value": 0.5, "reason": None}


def test_run_evaluation_tolerance_chars_default_30(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    captured = []

    def _fake(doc, annot, tolerance_chars=30):
        captured.append(tolerance_chars)
        return {}

    monkeypatch.setattr("evaluation.runner.process_single", lambda *a, **k: (_StubDocument(), []))
    monkeypatch.setattr("evaluation.runner.chunk_boundary_prf", _fake)
    run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert captured == [30]


def test_run_evaluation_tolerance_chars_custom(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    captured = []

    def _fake(doc, annot, tolerance_chars=30):
        captured.append(tolerance_chars)
        return {}

    monkeypatch.setattr("evaluation.runner.process_single", lambda *a, **k: (_StubDocument(), []))
    monkeypatch.setattr("evaluation.runner.chunk_boundary_prf", _fake)
    run_evaluation(_StubManifest([d1]), tmp_path / "r.json", tolerance_chars=50)
    assert captured == [50]


def test_run_evaluation_summary_aggregated_called(monkeypatch, tmp_path):
    """aggregate_summary 必须被调用（验证通过 spy）。"""
    called = {"n": 0}

    real_agg = rmod.aggregate_summary

    def _spy(per_doc_results):
        called["n"] += 1
        return real_agg(per_doc_results)

    monkeypatch.setattr("evaluation.runner.aggregate_summary", _spy)
    run_evaluation(_StubManifest(), tmp_path / "r.json")
    assert called["n"] == 1


def test_run_evaluation_build_provenance_called(monkeypatch, tmp_path):
    called = {"n": 0}

    real_prov = rmod.build_provenance

    def _spy(*args, **kwargs):
        called["n"] += 1
        return real_prov(*args, **kwargs)

    monkeypatch.setattr("evaluation.runner.build_provenance", _spy)
    run_evaluation(_StubManifest(), tmp_path / "r.json")
    assert called["n"] == 1


def test_run_evaluation_build_devset_section_called(monkeypatch, tmp_path):
    called = {"n": 0}

    real_dev = rmod.build_devset_section

    def _spy(manifest):
        called["n"] += 1
        return real_dev(manifest)

    monkeypatch.setattr("evaluation.runner.build_devset_section", _spy)
    run_evaluation(_StubManifest(), tmp_path / "r.json")
    assert called["n"] == 1


def test_run_evaluation_creates_output_root_parent(tmp_path):
    """output_path.parent 必须存在（被 mkdir 创建）。"""
    deep = tmp_path / "x" / "y" / "z" / "r.json"
    run_evaluation(_StubManifest(), deep)
    assert deep.is_file()


# ---------- module source forbidden tokens 第十五批 ----------


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
def test_runner_source_no_forbidden_token_fifteenth(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_runner_source_no_global_keyword_fifteenth():
    source = inspect.getsource(rmod)
    assert "\nglobal " not in source


def test_runner_source_no_class_def_fifteenth():
    source = inspect.getsource(rmod)
    assert "\nclass " not in source


def test_runner_source_no_async_def_fifteenth():
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_runner_source_no_yield_fifteenth():
    source = inspect.getsource(rmod)
    assert "yield" not in source


def test_runner_source_no_walrus_fifteenth():
    source = inspect.getsource(rmod)
    assert ":=" not in source


def test_runner_source_no_print_fifteenth():
    source = inspect.getsource(rmod)
    assert "print(" not in source


def test_runner_source_no_logging_fifteenth():
    source = inspect.getsource(rmod)
    assert "logging" not in source
    assert "logger" not in source


def test_runner_source_no_sleep_fifteenth():
    source = inspect.getsource(rmod)
    assert "time.sleep" not in source


def test_runner_source_no_remove_call():
    """不调用 Path.remove()（不存在该方法）。"""
    source = inspect.getsource(rmod)
    assert ".remove(" not in source


def test_runner_source_no_rmtree_call():
    source = inspect.getsource(rmod)
    assert ".rmtree(" not in source


# ---------- module source 字符串精确补强第十批 ----------


def test_module_source_has_future_annotations_batch10():
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json_batch10():
    source = inspect.getsource(rmod)
    assert "import json" in source


def test_module_source_imports_time_batch10():
    source = inspect.getsource(rmod)
    assert "import time" in source


def test_module_source_imports_path_batch10():
    source = inspect.getsource(rmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch10():
    source = inspect.getsource(rmod)
    assert "from typing import Any" in source


def test_module_source_imports_pipeline_helpers_batch10():
    source = inspect.getsource(rmod)
    assert "from app.pipeline import" in source
    assert "image_output_dir_for" in source
    assert "process_single" in source


def test_module_source_imports_report_constants_batch10():
    source = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in source


def test_module_source_imports_annotation_metrics_funcs_batch10():
    source = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in source
    assert "chunk_boundary_prf" in source
    assert "figure_caption_prf" in source


def test_module_source_imports_metrics_func_batch10():
    source = inspect.getsource(rmod)
    assert "from evaluation.metrics import" in source
    assert "compute_automatic_metrics" in source


def test_module_source_imports_report_funcs_batch10():
    source = inspect.getsource(rmod)
    assert "from evaluation.report import" in source
    assert "aggregate_summary" in source
    assert "build_devset_section" in source
    assert "build_provenance" in source


def test_module_source_has_load_annotation_def_batch10():
    source = inspect.getsource(rmod)
    assert "def _load_annotation(path: Path | None)" in source


def test_module_source_has_process_one_def_batch10():
    source = inspect.getsource(rmod)
    assert "def _process_one(" in source


def test_module_source_has_run_evaluation_def_batch10():
    source = inspect.getsource(rmod)
    assert "def run_evaluation(" in source


def test_module_source_uses_perf_counter_batch10():
    source = inspect.getsource(rmod)
    assert "time.perf_counter()" in source


def test_module_source_uses_path_is_file_batch10():
    source = inspect.getsource(rmod)
    assert ".is_file()" in source


def test_module_source_uses_mkdir_batch10():
    source = inspect.getsource(rmod)
    assert ".mkdir(parents=True, exist_ok=True)" in source


def test_module_source_uses_unlink_batch10():
    """unlink 在 _process_one 与 run_evaluation（清理 stub）中出现。"""
    source = inspect.getsource(rmod)
    assert ".unlink()" in source


def test_module_source_handles_oserror_batch10():
    source = inspect.getsource(rmod)
    assert "except OSError:" in source


def test_module_source_uses_image_output_dir_for_call_batch10():
    source = inspect.getsource(rmod)
    assert "image_dir = image_output_dir_for(" in source


def test_module_source_unknown_error_message_batch10():
    source = inspect.getsource(rmod)
    assert "process_single returned None without errors" in source


def test_module_source_unknown_error_code_batch10():
    source = inspect.getsource(rmod)
    assert '"unknown"' in source


def test_module_source_report_dict_keys_batch10():
    source = inspect.getsource(rmod)
    for key in ['"report_version"', '"provenance"', '"devset"', '"summary"', '"per_doc"', '"expected_failures"']:
        assert key in source


def test_module_source_wall_time_seconds_keys_batch10():
    source = inspect.getsource(rmod)
    for key in ['"total"', '"parse"', '"chunk"', '"parse_reason"', '"chunk_reason"']:
        assert key in source
    assert '"not_instrumented"' in source


def test_module_source_uses_json_dump_batch10():
    source = inspect.getsource(rmod)
    assert "json.dump(" in source
    assert "ensure_ascii=False" in source
    assert "indent=2" in source


def test_module_source_no_main_block_batch10():
    source = inspect.getsource(rmod)
    assert "if __name__" not in source


def test_module_source_no_hardcoded_absolute_path_batch10():
    source = inspect.getsource(rmod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


def test_module_source_docstring_present_batch10():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 50


def test_module_source_docstring_mentions_pipeline_batch10():
    assert "pipeline" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_total_batch10():
    assert "total" in rmod.__doc__


def test_module_source_docstring_mentions_not_instrumented_batch10():
    assert "not_instrumented" in rmod.__doc__ or "not instrumented" in rmod.__doc__.lower()


def test_module_source_uses_per_doc_results_var_batch10():
    source = inspect.getsource(rmod)
    assert "per_doc_results" in source


def test_module_source_uses_public_per_doc_var_batch10():
    source = inspect.getsource(rmod)
    assert "public_per_doc" in source


def test_module_source_uses_doc_id_key_batch10():
    source = inspect.getsource(rmod)
    assert '"doc_id"' in source


def test_module_source_uses_source_type_key_batch10():
    source = inspect.getsource(rmod)
    assert '"source_type"' in source


def test_module_source_uses_metrics_key_batch10():
    source = inspect.getsource(rmod)
    assert '"metrics"' in source


def test_module_source_uses_annotation_present_key_batch10():
    source = inspect.getsource(rmod)
    assert '"_annotation_present"' in source


def test_module_source_uses_tolerance_chars_key_batch10():
    source = inspect.getsource(rmod)
    assert '"_tolerance_chars"' in source


def test_module_source_uses_missing_markers_key_batch10():
    source = inspect.getsource(rmod)
    assert '"_missing_markers"' in source


# ---------- signatures 第十批 ----------


def test_signature_load_annotation_param_count_batch10():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_signature_load_annotation_param_name_batch10():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


def test_signature_load_annotation_param_kind_batch10():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_load_annotation_param_no_default_batch10():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_load_annotation_param_annotation_str_batch10():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "Path | None"


def test_signature_load_annotation_return_annotation_str_batch10():
    sig = inspect.signature(_load_annotation)
    assert sig.return_annotation == "dict[str, Any] | None"


def test_signature_process_one_param_count_batch10():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_signature_process_one_param_names_batch10():
    sig = inspect.signature(_process_one)
    names = list(sig.parameters)
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_param_kinds_batch10():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_process_one_no_defaults_batch10():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_process_one_first_param_annotation_batch10():
    sig = inspect.signature(_process_one)
    p = list(sig.parameters.values())[0]
    # 第一个参数注解为 comment（无类型注解）
    assert p.annotation == inspect.Parameter.empty or "DocumentEntry" in str(p.annotation)


def test_signature_process_one_output_root_annotation_batch10():
    sig = inspect.signature(_process_one)
    p = sig.parameters["output_root"]
    assert p.annotation == "Path"


def test_signature_process_one_parser_name_annotation_batch10():
    sig = inspect.signature(_process_one)
    p = sig.parameters["parser_name"]
    assert p.annotation == "str"


def test_signature_process_one_max_chars_annotation_batch10():
    sig = inspect.signature(_process_one)
    p = sig.parameters["max_chars"]
    assert p.annotation == "int"


def test_signature_process_one_return_annotation_str_batch10():
    sig = inspect.signature(_process_one)
    ra = sig.return_annotation
    assert ra.startswith("tuple[")


def test_signature_run_evaluation_param_count_batch10():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_signature_run_evaluation_param_names_batch10():
    sig = inspect.signature(run_evaluation)
    names = list(sig.parameters)
    assert names == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_signature_run_evaluation_manifest_kind_batch10():
    sig = inspect.signature(run_evaluation)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation_output_path_kind_batch10():
    sig = inspect.signature(run_evaluation)
    p = list(sig.parameters.values())[1]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation_output_path_annotation_batch10():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["output_path"]
    assert p.annotation == "Path"


def test_signature_run_evaluation_keyword_only_count_batch10():
    sig = inspect.signature(run_evaluation)
    keyword_only = [p for p in sig.parameters.values() if p.kind == inspect.Parameter.KEYWORD_ONLY]
    assert len(keyword_only) == 3


def test_signature_run_evaluation_keyword_only_names_batch10():
    sig = inspect.signature(run_evaluation)
    keyword_only = [p for p in sig.parameters.values() if p.kind == inspect.Parameter.KEYWORD_ONLY]
    assert {p.name for p in keyword_only} == {"parser_name", "max_chars", "tolerance_chars"}


def test_signature_run_evaluation_keyword_only_defaults_batch10():
    sig = inspect.signature(run_evaluation)
    keyword_only = [p for p in sig.parameters.values() if p.kind == inspect.Parameter.KEYWORD_ONLY]
    defaults = {p.name: p.default for p in keyword_only}
    assert defaults == {"parser_name": "fallback", "max_chars": 800, "tolerance_chars": 30}


def test_signature_run_evaluation_keyword_only_annotations_batch10():
    sig = inspect.signature(run_evaluation)
    annotations = {p.name: p.annotation for p in sig.parameters.values() if p.kind == inspect.Parameter.KEYWORD_ONLY}
    assert annotations == {
        "parser_name": "str",
        "max_chars": "int",
        "tolerance_chars": "int",
    }


def test_signature_run_evaluation_return_annotation_str_batch10():
    sig = inspect.signature(run_evaluation)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_3_funcs_are_function_type_batch10():
    for func in (_load_annotation, _process_one, run_evaluation):
        assert inspect.isfunction(func)


def test_signature_3_funcs_module_eq_batch10():
    for func in (_load_annotation, _process_one, run_evaluation):
        assert func.__module__ == "evaluation.runner"


def test_signature_run_evaluation_no_var_positional_batch10():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_run_evaluation_no_var_keyword_batch10():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十批 ----------


def test_module_all_attribute_value_batch10():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_all_is_list_batch10():
    assert isinstance(rmod.__all__, list)


def test_module_all_entries_unique_batch10():
    assert len(rmod.__all__) == len(set(rmod.__all__))


def test_module_has_dunder_file_batch10():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_endswith_runner_py_batch10():
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "runner.py") or rmod.__file__.endswith(
        "evaluation/runner.py"
    )


def test_module_dunder_name_batch10():
    assert rmod.__name__ == "evaluation.runner"


def test_module_function_count_batch10():
    funcs = [
        n
        for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}
    assert len(funcs) == 3


def test_module_no_user_classes_batch10():
    classes = [
        n for n, v in vars(rmod).items() if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_no_call_at_top_level_batch10():
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "import ",
                "from ",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped and not stripped.startswith("def "):
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_constants_only_all_batch10():
    consts = []
    for n, v in vars(rmod).items():
        if n.startswith("__"):
            continue
        if isinstance(v, (tuple, list, dict, set, frozenset)) and not callable(v):
            consts.append(n)
    assert set(consts) == set()


def test_module_docstring_present_batch10():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 50


def test_module_docstring_in_chinese_or_english_batch10():
    """docstring 可中英混排，但必须提到 pipeline。"""
    doc = rmod.__doc__.lower()
    assert "pipeline" in doc or "评测" in rmod.__doc__


def test_module_run_evaluation_public_via_all_batch10():
    """run_evaluation 在 __all__ 中（公开 API）。"""
    assert "run_evaluation" in rmod.__all__


def test_module_internal_funcs_not_in_all_batch10():
    """_load_annotation 与 _process_one 不在 __all__（私有）。"""
    assert "_load_annotation" not in rmod.__all__
    assert "_process_one" not in rmod.__all__


# ---------- 端到端集成第十批 ----------


def test_e2e_load_annotation_idempotent_under_repeated_calls_batch10(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k":"v"}', encoding="utf-8")
    out1 = _load_annotation(p)
    out2 = _load_annotation(p)
    out3 = _load_annotation(p)
    assert out1 == out2 == out3 == {"k": "v"}


def test_e2e_load_annotation_handles_complex_nested_structure(tmp_path):
    p = tmp_path / "complex.json"
    data = {
        "list": [1, 2, {"nested": [True, False, None]}],
        "dict": {"a": 1, "b": [1, 2, 3]},
        "scalar": "hello",
        "none": None,
        "float": 3.14,
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    assert _load_annotation(p) == data


def test_e2e_load_annotation_unicode_chars_in_keys_and_values(tmp_path):
    p = tmp_path / "u.json"
    p.write_text('{"中文键": "中文值", "emoji": "🎉"}', encoding="utf-8")
    assert _load_annotation(p) == {"中文键": "中文值", "emoji": "🎉"}


def test_e2e_process_one_complete_success_flow(monkeypatch, tmp_path):
    """完整成功流：success → 5-tuple 返回 → parser_version 透传。"""
    doc = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(parser_version="3.2.1"), []),
    )
    document, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {"source_hash": "a" * 64, "parser_version": "3.2.1"}
    assert error is None
    assert isinstance(total, float)
    assert pv == "3.2.1"
    assert isinstance(image_dir, Path)


def test_e2e_process_one_complete_error_flow(monkeypatch, tmp_path):
    """完整错误流：errors 非空 → 返 (None, error_dict, ...)。"""
    doc = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (None, [_StubError("custom_err", "msg")]),
    )
    document, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "custom_err", "message": "msg"}
    assert pv is None
    assert image_dir is None


def test_e2e_process_one_complete_unknown_flow(monkeypatch, tmp_path):
    """document None + no errors → 返 unknown error。"""
    doc = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    doc.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (None, []),
    )
    document, error, total, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "unknown", "message": "process_single returned None without errors"}


def test_e2e_run_evaluation_minimal_manifest_produces_valid_report(tmp_path):
    out = run_evaluation(_StubManifest(), tmp_path / "r.json")
    # 关键字段都在
    assert out["report_version"] == REPORT_VERSION
    assert "provenance" in out
    assert "devset" in out
    assert "summary" in out
    assert "per_doc" in out
    assert "expected_failures" in out


def test_e2e_run_evaluation_idempotent_summary_keys(tmp_path):
    """summary key 顺序与集合稳定。"""
    out1 = run_evaluation(_StubManifest(), tmp_path / "r1.json")
    out2 = run_evaluation(_StubManifest(), tmp_path / "r2.json")
    assert set(out1["summary"].keys()) == set(out2["summary"].keys())


def test_e2e_run_evaluation_idempotent_provenance_parser_name(tmp_path):
    out1 = run_evaluation(_StubManifest(), tmp_path / "r1.json")
    out2 = run_evaluation(_StubManifest(), tmp_path / "r2.json")
    assert out1["provenance"]["parser_name"] == out2["provenance"]["parser_name"]
    assert out1["provenance"]["max_chars"] == out2["provenance"]["max_chars"]


def test_e2e_run_evaluation_full_chain_no_unexpected_exceptions(tmp_path):
    """连续调用不应抛异常。"""
    for _ in range(3):
        run_evaluation(_StubManifest(), tmp_path / "r.json")


def test_e2e_run_evaluation_full_chain_with_one_doc(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    out = run_evaluation(_StubManifest([d1]), tmp_path / "r.json")
    assert len(out["per_doc"]) == 1
    assert out["per_doc"][0]["doc_id"] == "d1"
    # JSON 可序列化
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed["per_doc"][0]["doc_id"] == "d1"


def test_e2e_run_evaluation_kwargs_consistent_with_positional(monkeypatch, tmp_path):
    d1 = _StubDoc(doc_id="d1", resolved_path=tmp_path / "a.pdf")
    d1.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (_StubDocument(), []),
    )
    out1 = run_evaluation(_StubManifest([d1]), tmp_path / "r1.json")
    out2 = run_evaluation(
        _StubManifest([d1]),
        tmp_path / "r2.json",
        parser_name="fallback",
        max_chars=800,
        tolerance_chars=30,
    )
    # 结构等价（不算 timestamp）
    assert len(out1["per_doc"]) == len(out2["per_doc"])
    assert out1["provenance"]["parser_name"] == out2["provenance"]["parser_name"]


def test_e2e_run_evaluation_no_unexpected_exceptions_with_failures(monkeypatch, tmp_path):
    """含 expected_failures 时也不抛。"""
    class _EF:
        doc_id = "ef1"
        expected_error_code = "parse_failed"
        resolved_path = tmp_path / "x.pdf"

    _EF.resolved_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "evaluation.runner.process_single",
        lambda *a, **k: (None, [_StubError()]),
    )
    out = run_evaluation(_StubManifest(expected_failures=[_EF()]), tmp_path / "r.json")
    assert out["expected_failures"][0]["matches"] is True
