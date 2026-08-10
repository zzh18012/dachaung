"""evaluation/runner.py 第四十轮 edges 测试（Round 403）。

补强 edges38 未触及的角度：
- _load_annotation 行为深度第十二批（Unicode filename / 巨大 integer / 科学计数 / NaN / Infinity / duplicate keys / 仅含 whitespace / 多层嵌套 / bytes file / symlink 等）
- _process_one 行为深度第十二批（mkdir idempotent / unlink OSError silent / elapsed type float / parser_version 透传 None / image_dir via image_output_dir_for / kwargs forward / 5-tuple 顺序 / errors[0].to_dict() / source_hash 透传到 image_dir）
- run_evaluation 行为深度第十二批（tolerance_chars propagated / parser_version_first wins / public per_doc 4 keys / report top 6 keys / JSON file written / returns the report dict / 空 manifest / 多 docs）
- module source forbidden tokens 第十五批
- module source 字符串精确补强第十二批
- signatures 第十二批
- module 合理性第十二批
- 端到端集成第十二批
"""

from __future__ import annotations

import inspect
import json
import os
import time
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


class _StubExpectedFailure:
    def __init__(self, doc_id="ef1", resolved_path=None, expected_error_code="unsupported_format"):
        self.doc_id = doc_id
        self.resolved_path = resolved_path
        self.expected_error_code = expected_error_code


# ---------- _load_annotation 行为深度第十二批 ----------


def test_load_annotation_unicode_filename_batch12(tmp_path):
    """Unicode 文件名也能加载。"""
    p = tmp_path / "注解.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "v"}


def test_load_annotation_huge_integer_batch12(tmp_path):
    """巨大 integer 不损失精度（Python int 无上限）。"""
    p = tmp_path / "big.json"
    p.write_text("99999999999999999999999999", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 99999999999999999999999999


def test_load_annotation_scientific_notation_batch12(tmp_path):
    p = tmp_path / "sci.json"
    p.write_text("1.5e10", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 1.5e10


def test_load_annotation_nan_accepted_batch12(tmp_path):
    """Python json 接受 NaN（非标准）。"""
    p = tmp_path / "nan.json"
    p.write_text("NaN", encoding="utf-8")
    out = _load_annotation(p)
    assert out != out  # NaN != NaN


def test_load_annotation_infinity_accepted_batch12(tmp_path):
    p = tmp_path / "inf.json"
    p.write_text("Infinity", encoding="utf-8")
    out = _load_annotation(p)
    assert out == float("inf")


def test_load_annotation_negative_infinity_accepted_batch12(tmp_path):
    p = tmp_path / "neginf.json"
    p.write_text("-Infinity", encoding="utf-8")
    out = _load_annotation(p)
    assert out == float("-inf")


def test_load_annotation_duplicate_keys_batch12(tmp_path):
    """JSON 标准未规定 duplicate keys；Python 取最后一个。"""
    p = tmp_path / "dup.json"
    p.write_text('{"k": 1, "k": 2}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": 2}


def test_load_annotation_whitespace_only_batch12(tmp_path):
    """文件只含空白 → JSONDecodeError → None。"""
    p = tmp_path / "ws.json"
    p.write_text("   \n\t   ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_array_with_objects_batch12(tmp_path):
    p = tmp_path / "arr2.json"
    p.write_text('[{"k": 1}, {"k": 2}]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [{"k": 1}, {"k": 2}]
    assert isinstance(out, list)
    assert all(isinstance(x, dict) for x in out)


def test_load_annotation_string_value_batch12(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"just a string"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "just a string"


def test_load_annotation_path_object_batch12(tmp_path):
    """传 Path 对象正常工作。"""
    p = tmp_path / "x.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    assert isinstance(p, Path)
    out = _load_annotation(p)
    assert out == {"k": "v"}


def test_load_annotation_returns_consistent_type_batch12(tmp_path):
    """对同一文件多次调用应得到相同结果。"""
    p = tmp_path / "x.json"
    p.write_text('{"a": [1, 2, 3], "b": "y"}', encoding="utf-8")
    out1 = _load_annotation(p)
    out2 = _load_annotation(p)
    assert out1 == out2 == {"a": [1, 2, 3], "b": "y"}


# ---------- _process_one 行为深度第十二批 ----------


def test_process_one_mkdir_idempotent_batch12(tmp_path):
    """output_root 已存在 → mkdir(parents=True, exist_ok=True) 不报错。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    # 模拟两次 _process_one 同一个 output_root
    def _fake(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _process_one(doc, output_root, "fallback", 800)
        _process_one(doc, output_root, "fallback", 800)


def test_process_one_unlink_silent_on_oserror_batch12(tmp_path, monkeypatch):
    """out_stub.is_file() True 但 unlink raises OSError → silent。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    # 让 _process_one 内部跑完后，stub 文件存在但 unlink 失败
    fake_doc = _StubDocument()

    def _fake_process(*args, **kwargs):
        # 把 stub 文件真创建出来
        out_stub = output_root / "_per_doc" / "doc1.json"
        out_stub.parent.mkdir(parents=True, exist_ok=True)
        out_stub.write_text("{}", encoding="utf-8")
        return fake_doc, []

    # patch Path.unlink 在该 stub 文件上抛 OSError
    real_unlink = Path.unlink

    def _fake_unlink(self, *args, **kwargs):
        if self.name == "doc1.json":
            raise OSError("permission denied")
        return real_unlink(self, *args, **kwargs)

    with patch("evaluation.runner.process_single", side_effect=_fake_process), \
         patch.object(Path, "unlink", _fake_unlink):
        # 不应抛
        document, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert document == fake_doc.to_dict()
    assert error is None


def test_process_one_elapsed_is_float_batch12(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _, _, elapsed, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert type(elapsed) is float


def test_process_one_elapsed_nonnegative_batch12(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _, _, elapsed, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert elapsed >= 0


def test_process_one_parser_version_none_when_document_present_no_version_batch12(tmp_path):
    """document 有但 parser_version 属性不存在时 → AttributeError；本测试只检查正常路径。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    fake_doc = _StubDocument(parser_version=None)

    def _fake(*args, **kwargs):
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _, _, _, parser_version, _ = _process_one(doc, output_root, "fallback", 800)
    assert parser_version is None


def test_process_one_kwargs_forwarded_batch12(tmp_path):
    """process_single 应收到 parser_name / max_chars / write_json=False。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    captured: dict = {}

    def _fake(*args, **kwargs):
        captured.update(kwargs)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _process_one(doc, output_root, "kreuzberg", 1200)
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 1200
    assert captured["write_json"] is False


def test_process_one_positional_resolved_path_batch12(tmp_path):
    """process_single 第一个位置参数应是 doc.resolved_path。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    captured: list = []

    def _fake(*args, **kwargs):
        captured.extend(args)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _process_one(doc, output_root, "fallback", 800)
    assert captured[0] == doc.resolved_path


def test_process_one_returns_5_tuple_strict_batch12(tmp_path):
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()

    def _fake(*args, **kwargs):
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        result = _process_one(doc, output_root, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5
    document, error, elapsed, parser_version, image_dir = result
    assert document is None
    assert isinstance(error, dict)
    assert isinstance(elapsed, float)
    assert parser_version is None
    assert image_dir is None


def test_process_one_image_dir_uses_source_hash_batch12(tmp_path):
    """document.source_hash 透传给 image_output_dir_for。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    fake_doc = _StubDocument(source_hash="0" * 64)
    captured: dict = {}

    def _fake_image_dir(stub, source_hash):
        captured["stub"] = stub
        captured["source_hash"] = source_hash
        return Path("/fake/image_dir")

    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])), \
         patch("evaluation.runner.image_output_dir_for", side_effect=_fake_image_dir):
        _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
    assert captured["source_hash"] == "0" * 64
    assert image_dir == Path("/fake/image_dir")


def test_process_one_errors_to_dict_called_batch12(tmp_path):
    """errors[0].to_dict() 应被调用。"""
    doc = _StubDoc(resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    err = _StubError("custom_code", "custom_message")

    def _fake(*args, **kwargs):
        return None, [err]

    to_dict_called = [False]
    real_to_dict = err.to_dict

    def _patched_to_dict():
        to_dict_called[0] = True
        return real_to_dict()

    err.to_dict = _patched_to_dict

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert to_dict_called[0] is True
    assert error == {"code": "custom_code", "message": "custom_message"}


def test_process_one_out_stub_under_per_doc_batch12(tmp_path):
    """out_stub 路径应为 output_root/_per_doc/<doc_id>.json。"""
    doc = _StubDoc(doc_id="myid", resolved_path=tmp_path / "input.pdf")
    output_root = tmp_path / "out"
    output_root.mkdir()
    captured: list = []

    def _fake(*args, **kwargs):
        captured.extend(args)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        _process_one(doc, output_root, "fallback", 800)
    out_stub = captured[1]
    assert out_stub == output_root / "_per_doc" / "myid.json"


# ---------- run_evaluation 行为深度第十二批 ----------


def test_run_evaluation_writes_json_file_batch12(tmp_path):
    """run_evaluation 应把 report 写到 output_path。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert out.is_file()
    # 文件内容应等于返回的 report（JSON 序列化）
    with out.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == report


def test_run_evaluation_report_version_strict_batch12(tmp_path):
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_public_per_doc_has_4_keys_batch12(tmp_path):
    """public per_doc 应只有 4 个 key。"""
    manifest = _StubManifest(
        documents=[_StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x"))]
    )
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 1
    assert set(report["per_doc"][0].keys()) == {
        "doc_id",
        "source_type",
        "metrics",
        "wall_time_seconds",
    }


def test_run_evaluation_public_per_doc_no_private_keys_batch12(tmp_path):
    manifest = _StubManifest(
        documents=[_StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x"))]
    )
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        assert "_annotation_present" not in r
        assert "_tolerance_chars" not in r
        assert "_missing_markers" not in r


def test_run_evaluation_tolerance_chars_propagated_batch12(tmp_path):
    """tolerance_chars 应被传给 chunk_boundary_prf。"""
    manifest = _StubManifest(
        documents=[_StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x"))]
    )
    out = tmp_path / "report.json"
    captured: dict = {}

    def _no_op(*args, **kwargs):
        return None, []

    def _fake_chunk_b(document, annotation, *, tolerance_chars):
        captured["tolerance_chars"] = tolerance_chars
        return {
            "chunk_boundary_precision": {"value": 1.0, "participating_docs": 1},
            "_tolerance_chars": {"value": tolerance_chars},
            "_missing_markers": {"value": []},
        }

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", side_effect=_fake_chunk_b):
        run_evaluation(manifest, out, tolerance_chars=42)
    assert captured["tolerance_chars"] == 42


def test_run_evaluation_parser_version_first_wins_batch12(tmp_path):
    """多个 docs 时，第一个非 None parser_version 进 provenance。"""
    docs = [
        _StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x")),
        _StubDoc(doc_id="d2", source_type="pdf", resolved_path=Path("y")),
    ]
    manifest = _StubManifest(documents=docs)
    out = tmp_path / "report.json"
    captured: dict = {}

    def _build_prov(*, project_root, parser_name, max_chars, parser_version):
        captured["parser_version"] = parser_version
        return {}

    # 第一次返回 v1.0，第二次返回 v2.0
    versions = iter(["1.0.0", "2.0.0"])

    def _process(*args, **kwargs):
        v = next(versions)
        return _StubDocument(parser_version=v), []

    with patch("evaluation.runner.process_single", side_effect=_process), \
         patch("evaluation.runner.build_provenance", side_effect=_build_prov), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert captured["parser_version"] == "1.0.0"


def test_run_evaluation_expected_failure_matches_true_batch12(tmp_path):
    """expected_failure.matches=True 当 actual_code == expected。"""
    ef = _StubExpectedFailure(
        doc_id="bad", resolved_path=Path("x"), expected_error_code="unsupported_format"
    )
    manifest = _StubManifest(expected_failures=[ef])
    out = tmp_path / "report.json"

    err = _StubError(code="unsupported_format")

    def _process(*args, **kwargs):
        return None, [err]

    with patch("evaluation.runner.process_single", side_effect=_process), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failure_matches_false_batch12(tmp_path):
    ef = _StubExpectedFailure(
        doc_id="bad", resolved_path=Path("x"), expected_error_code="unsupported_format"
    )
    manifest = _StubManifest(expected_failures=[ef])
    out = tmp_path / "report.json"

    err = _StubError(code="parse_failed")

    def _process(*args, **kwargs):
        return None, [err]

    with patch("evaluation.runner.process_single", side_effect=_process), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failure_no_errors_batch12(tmp_path):
    """expected_failure 但 process_single 不报错 → actual_code=None。"""
    ef = _StubExpectedFailure(
        doc_id="bad", resolved_path=Path("x"), expected_error_code="unsupported_format"
    )
    manifest = _StubManifest(expected_failures=[ef])
    out = tmp_path / "report.json"

    def _process(*args, **kwargs):
        return _StubDocument(), []  # 无错误

    with patch("evaluation.runner.process_single", side_effect=_process), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["actual_error_code"] is None
    assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_kwargs_overrides_defaults_batch12(tmp_path):
    """parser_name/max_chars/tolerance_chars 都可通过 kwargs 覆盖。"""
    manifest = _StubManifest(
        documents=[_StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x"))]
    )
    out = tmp_path / "report.json"
    captured: dict = {}

    def _no_op(*args, **kwargs):
        captured["process_kwargs"] = kwargs
        return None, []

    def _build_prov(*, project_root, parser_name, max_chars, parser_version):
        captured["prov_parser_name"] = parser_name
        captured["prov_max_chars"] = max_chars
        return {}

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", side_effect=_build_prov), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out, parser_name="kreuzberg", max_chars=500, tolerance_chars=20)
    assert captured["prov_parser_name"] == "kreuzberg"
    assert captured["prov_max_chars"] == 500
    assert captured["process_kwargs"]["parser_name"] == "kreuzberg"
    assert captured["process_kwargs"]["max_chars"] == 500


def test_run_evaluation_default_parser_name_fallback_batch12(tmp_path):
    manifest = _StubManifest(
        documents=[_StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x"))]
    )
    out = tmp_path / "report.json"
    captured: dict = {}

    def _no_op(*args, **kwargs):
        captured["kwargs"] = kwargs
        return None, []

    def _build_prov(*, project_root, parser_name, max_chars, parser_version):
        captured["parser_name"] = parser_name
        return {}

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", side_effect=_build_prov), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert captured["parser_name"] == "fallback"
    assert captured["kwargs"]["parser_name"] == "fallback"


def test_run_evaluation_default_max_chars_800_batch12(tmp_path):
    manifest = _StubManifest(
        documents=[_StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x"))]
    )
    out = tmp_path / "report.json"
    captured: dict = {}

    def _no_op(*args, **kwargs):
        captured["kwargs"] = kwargs
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert captured["kwargs"]["max_chars"] == 800


def test_run_evaluation_default_tolerance_30_batch12(tmp_path):
    """tolerance_chars 默认 30。"""
    manifest = _StubManifest(
        documents=[_StubDoc(doc_id="d1", source_type="pdf", resolved_path=Path("x"))]
    )
    out = tmp_path / "report.json"
    captured: dict = {}

    def _no_op(*args, **kwargs):
        return None, []

    def _fake_chunk_b(document, annotation, *, tolerance_chars):
        captured["tolerance_chars"] = tolerance_chars
        return {
            "chunk_boundary_precision": {"value": 1.0},
            "_tolerance_chars": {"value": tolerance_chars},
            "_missing_markers": {"value": []},
        }

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", side_effect=_fake_chunk_b):
        run_evaluation(manifest, out)
    assert captured["tolerance_chars"] == 30


def test_run_evaluation_creates_output_parent_dir_batch12(tmp_path):
    """output_path.parent 不存在时自动创建。"""
    manifest = _StubManifest()
    out = tmp_path / "a" / "b" / "c" / "report.json"
    assert not out.parent.exists()

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_per_doc_doc_id_propagated_batch12(tmp_path):
    """per_doc 内 doc_id 应等于 manifest 中 doc.doc_id。"""
    docs = [
        _StubDoc(doc_id="alpha", source_type="pdf", resolved_path=Path("x")),
        _StubDoc(doc_id="beta", source_type="docx", resolved_path=Path("y")),
    ]
    manifest = _StubManifest(documents=docs)
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    ids = [r["doc_id"] for r in report["per_doc"]]
    assert ids == ["alpha", "beta"]


def test_run_evaluation_per_doc_source_type_propagated_batch12(tmp_path):
    docs = [
        _StubDoc(doc_id="a", source_type="pdf", resolved_path=Path("x")),
        _StubDoc(doc_id="b", source_type="docx", resolved_path=Path("y")),
    ]
    manifest = _StubManifest(documents=docs)
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    types = [r["source_type"] for r in report["per_doc"]]
    assert types == ["pdf", "docx"]


# ---------- module source forbidden tokens 第十五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "import marshal",
        "import ctypes",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from marshal import",
        "from ctypes import",
        "subprocess.Popen",
        "os.system",
    ],
)
def test_runner_source_no_forbidden_token_fifteenth_batch12(token):
    source = inspect.getsource(rmod)
    assert token not in source


def test_runner_source_no_global_keyword_batch12():
    source = inspect.getsource(rmod)
    assert " global " not in source


def test_runner_source_no_class_definition_batch12():
    source = inspect.getsource(rmod)
    assert "\nclass " not in source
    assert not source.startswith("class ")


def test_runner_source_no_assert_batch12():
    source = inspect.getsource(rmod)
    assert "\nassert " not in source
    assert not source.startswith("assert ")


def test_runner_source_no_lambda_batch12():
    source = inspect.getsource(rmod)
    assert "lambda " not in source


def test_runner_source_uses_fstring_for_doc_id_batch12():
    """runner 使用 f-string 拼接 doc_id 路径。"""
    source = inspect.getsource(rmod)
    assert 'f"{doc.doc_id}.json"' in source or 'f"{ef.doc_id}.json"' in source


def test_runner_source_no_format_method_batch12():
    source = inspect.getsource(rmod)
    assert ".format(" not in source


def test_runner_source_no_input_call_batch12():
    source = inspect.getsource(rmod)
    assert "input(" not in source


def test_runner_source_no_while_loop_batch12():
    source = inspect.getsource(rmod)
    assert "while " not in source


def test_runner_source_no_sys_exit_batch12():
    source = inspect.getsource(rmod)
    assert "sys.exit" not in source


def test_runner_source_no_check_output_batch12():
    source = inspect.getsource(rmod)
    assert "subprocess.check_output" not in source


def test_runner_source_no_check_call_batch12():
    source = inspect.getsource(rmod)
    assert "subprocess.check_call" not in source


def test_runner_source_no_top_level_lambda_batch12():
    source = inspect.getsource(rmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


# ---------- module source 字符串精确补强第十二批 ----------


def test_module_source_has_future_annotations_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_source_imports_json_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_time_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import time" in head


def test_module_source_imports_path_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_any_top_level_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_pipeline_helpers_batch12():
    source = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in source


def test_module_source_imports_annotation_metrics_batch12():
    source = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in source
    assert "chunk_boundary_prf" in source
    assert "figure_caption_prf" in source


def test_module_source_imports_metrics_compute_batch12():
    source = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in source


def test_module_source_imports_report_helpers_batch12():
    source = inspect.getsource(rmod)
    assert "from evaluation.report import" in source
    assert "aggregate_summary" in source
    assert "build_devset_section" in source
    assert "build_provenance" in source


def test_module_source_imports_report_version_batch12():
    source = inspect.getsource(rmod)
    assert "REPORT_VERSION" in source


def test_module_source_has_perf_counter_call_batch12():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source
    # 至少 2 次（开始 + 结束）
    assert source.count("time.perf_counter") >= 2


def test_module_source_has_json_dump_batch12():
    source = inspect.getsource(rmod)
    assert "json.dump(" in source


def test_module_source_has_json_load_batch12():
    source = inspect.getsource(rmod)
    assert "json.load(" in source


def test_module_source_no_json_loads_batch12():
    """本模块用 json.load（文件对象），不用 json.loads（字符串）。"""
    source = inspect.getsource(rmod)
    assert "json.loads(" not in source


def test_module_source_no_json_dumps_batch12():
    """本模块用 json.dump（文件对象），不用 json.dumps（字符串）。"""
    source = inspect.getsource(rmod)
    assert "json.dumps(" not in source


def test_module_source_has_not_instrumented_batch12():
    source = inspect.getsource(rmod)
    assert "not_instrumented" in source


def test_module_source_has_wall_time_seconds_batch12():
    source = inspect.getsource(rmod)
    assert "wall_time_seconds" in source


def test_module_source_has_image_output_dir_for_call_batch12():
    source = inspect.getsource(rmod)
    assert "image_output_dir_for(" in source


def test_module_source_has_report_version_assignment_batch12():
    source = inspect.getsource(rmod)
    assert '"report_version": REPORT_VERSION' in source


def test_module_source_has_underscore_per_doc_batch12():
    source = inspect.getsource(rmod)
    assert '"_per_doc"' in source


# ---------- signatures 第十二批 ----------


def test_signature_load_annotation_return_annotation_batch12():
    sig = inspect.signature(_load_annotation)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "dict" in annot_str
    assert "None" in annot_str


def test_signature_process_one_return_annotation_tuple_batch12():
    sig = inspect.signature(_process_one)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "tuple" in annot_str


def test_signature_run_evaluation_params_count_batch12():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_signature_run_evaluation_param_names_batch12():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters) == [
        "manifest",
        "output_path",
        "parser_name",
        "max_chars",
        "tolerance_chars",
    ]


def test_signature_run_evaluation_keyword_only_after_marker_batch12():
    """parser_name / max_chars / tolerance_chars 是 KEYWORD_ONLY。"""
    sig = inspect.signature(run_evaluation)
    for name in ("parser_name", "max_chars", "tolerance_chars"):
        p = sig.parameters[name]
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_manifest_positional_batch12():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["manifest"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation_output_path_positional_batch12():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["output_path"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation_default_parser_name_batch12():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["parser_name"]
    assert p.default == "fallback"


def test_signature_run_evaluation_default_max_chars_batch12():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["max_chars"]
    assert p.default == 800


def test_signature_run_evaluation_default_tolerance_chars_batch12():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["tolerance_chars"]
    assert p.default == 30


def test_signature_run_evaluation_manifest_no_annotation_batch12():
    """manifest 无类型注解（运行时类型）。"""
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["manifest"]
    # 无显式注解时是 str(annotation)
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert annot_str == "inspect.Parameter.empty" or annot is inspect.Parameter.empty or "Manifest" in annot_str


def test_signature_run_evaluation_return_annotation_dict_batch12():
    sig = inspect.signature(run_evaluation)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "dict" in annot_str


def test_all_functions_no_var_kwargs_batch12():
    """无 **kwargs。"""
    for fn in [_load_annotation, _process_one, run_evaluation]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十二批 ----------


def test_module_dunder_all_exact_batch12():
    assert hasattr(rmod, "__all__")
    assert rmod.__all__ == ["run_evaluation"]


def test_module_name_evaluation_runner_batch12():
    assert rmod.__name__ == "evaluation.runner"


def test_module_dunder_file_endswith_runner_py_batch12():
    sep = os.sep
    assert rmod.__file__.endswith("evaluation" + sep + "runner.py") or rmod.__file__.endswith(
        "evaluation/runner.py"
    )


def test_module_user_function_count_3_batch12():
    """3 个用户函数：_load_annotation, _process_one, run_evaluation。"""
    funcs = [
        n for n, v in vars(rmod).items()
        if inspect.isfunction(v) and v.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_user_classes_batch12():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_no_user_constants_tuple_batch12():
    """runner.py 无顶层 tuple 常量。"""
    consts = [
        n for n, v in vars(rmod).items()
        if not n.startswith("__") and isinstance(v, tuple) and not callable(v)
    ]
    assert consts == []


def test_module_docstring_present_batch12():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 30


def test_module_docstring_mentions_constraint_batch12():
    assert rmod.__doc__ is not None
    assert "约束" in rmod.__doc__ or "constraint" in rmod.__doc__.lower()


def test_module_docstring_mentions_timer_batch12():
    assert rmod.__doc__ is not None
    assert "计时" in rmod.__doc__ or "timer" in rmod.__doc__.lower() or "perf" in rmod.__doc__.lower()


def test_module_docstring_mentions_image_batch12():
    assert rmod.__doc__ is not None
    assert "图片" in rmod.__doc__ or "image" in rmod.__doc__.lower()


def test_module_uses_future_annotations_batch12():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


# ---------- 端到端集成第十二批 ----------


def test_e2e_full_chain_minimal_batch12(tmp_path):
    """空 manifest + 全 mock → 完整 report 落盘。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={"v": 1}), \
         patch("evaluation.runner.build_devset_section", return_value={"v": 2}), \
         patch("evaluation.runner.aggregate_summary", return_value={"v": 3}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["provenance"] == {"v": 1}
    assert report["devset"] == {"v": 2}
    assert report["summary"] == {"v": 3}
    assert report["per_doc"] == []
    assert report["expected_failures"] == []
    assert report["report_version"] == REPORT_VERSION


def test_e2e_full_chain_json_serializable_batch12(tmp_path):
    """report 应 json serializable。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={"a": 1}), \
         patch("evaluation.runner.build_devset_section", return_value={"b": 2}), \
         patch("evaluation.runner.aggregate_summary", return_value={"c": 3}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    text = json.dumps(report)
    parsed = json.loads(text)
    assert parsed == report


def test_e2e_full_chain_two_docs_batch12(tmp_path):
    docs = [
        _StubDoc(doc_id="a", source_type="pdf", resolved_path=Path("x")),
        _StubDoc(doc_id="b", source_type="docx", resolved_path=Path("y")),
    ]
    manifest = _StubManifest(documents=docs)
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 2


def test_e2e_with_expected_failures_batch12(tmp_path):
    efs = [
        _StubExpectedFailure("e1", Path("x"), "unsupported_format"),
        _StubExpectedFailure("e2", Path("y"), "parse_failed"),
    ]
    manifest = _StubManifest(expected_failures=efs)
    out = tmp_path / "report.json"

    def _process(*args, **kwargs):
        return None, [_StubError("unsupported_format")]

    with patch("evaluation.runner.process_single", side_effect=_process), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert len(report["expected_failures"]) == 2
    assert report["expected_failures"][0]["matches"] is True
    assert report["expected_failures"][1]["matches"] is False


def test_e2e_idempotent_run_batch12(tmp_path):
    """两次运行应得到相同结构。"""
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    def _run():
        with patch("evaluation.runner.process_single", side_effect=_no_op), \
             patch("evaluation.runner.build_provenance", return_value={}), \
             patch("evaluation.runner.build_devset_section", return_value={}), \
             patch("evaluation.runner.aggregate_summary", return_value={}), \
             patch("evaluation.runner.compute_automatic_metrics", return_value={}):
            return run_evaluation(manifest, out)

    r1 = _run()
    r2 = _run()
    assert list(r1.keys()) == list(r2.keys())


def test_e2e_combined_chain_doc_id_in_report_batch12(tmp_path):
    """doc_id 应在最终 report 中。"""
    docs = [_StubDoc(doc_id="mydoc", source_type="pdf", resolved_path=Path("x"))]
    manifest = _StubManifest(documents=docs)
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["per_doc"][0]["doc_id"] == "mydoc"


def test_e2e_report_includes_summary_section_batch12(tmp_path):
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={"custom_summary": True}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["summary"] == {"custom_summary": True}


def test_e2e_report_includes_provenance_section_batch12(tmp_path):
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={"custom_prov": True}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["provenance"] == {"custom_prov": True}


def test_e2e_report_includes_devset_section_batch12(tmp_path):
    manifest = _StubManifest()
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={"custom_devset": True}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    assert report["devset"] == {"custom_devset": True}


def test_e2e_combined_wall_time_structure_batch12(tmp_path):
    """wall_time_seconds 内部应有 total / parse / chunk + reasons。"""
    docs = [_StubDoc(doc_id="a", source_type="pdf", resolved_path=Path("x"))]
    manifest = _StubManifest(documents=docs)
    out = tmp_path / "report.json"

    def _no_op(*args, **kwargs):
        return None, []

    with patch("evaluation.runner.process_single", side_effect=_no_op), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}):
        report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {
        "total",
        "parse",
        "chunk",
        "parse_reason",
        "chunk_reason",
    }
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)
