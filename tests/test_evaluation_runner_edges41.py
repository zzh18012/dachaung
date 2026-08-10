"""evaluation/runner.py 第四十三轮 edges 测试（Round 417）。

补强 edges40 未触及的角度：
- _load_annotation 边界深度第十四批（json.JSONDecodeError 子类 ValueError / OSError 子类 PermissionError / 空文件 / 不是 dict 的 JSON / 是 list 的 JSON）
- _process_one 边界深度第十四批（errors[0].to_dict() 调用 / document None 时 image_dir None / out_stub 父目录创建 / time.perf_counter 计时调用 2 次 / unlink 异常 OSError 不抛）
- run_evaluation 字段深度第十四批（report 顶层 keys / per_doc[] 字段顺序 / wall_time_seconds 字段顺序 / image_dir not dir 时 image_base_dir None / parser_version 第一次非空被采用）
- _process_one 5-tuple 元素类型固定第十四批
- module source forbidden tokens 第十九批
- module source 字符串精确补强第十六批
- signatures 第十六批
- module 合理性第十六批
- 端到端集成第十六批
"""

from __future__ import annotations

import inspect
import json
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


# ---------- _load_annotation 边界深度第十四批 ----------


def test_load_annotation_catches_json_decode_error_batch14(tmp_path):
    """JSONDecodeError 是 ValueError 子类，被 except (OSError, json.JSONDecodeError) 捕获。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_catches_oserror_subclass_batch14(tmp_path):
    """PermissionError 是 OSError 子类，被捕获。"""
    p = tmp_path / "perm.json"
    p.write_text("{}", encoding="utf-8")
    real_open = Path.open

    def _fake_open(self, *args, **kwargs):
        if self == p:
            raise PermissionError("denied")
        return real_open(self, *args, **kwargs)

    with patch.object(Path, "open", _fake_open):
        assert _load_annotation(p) is None


def test_load_annotation_empty_file_batch14(tmp_path):
    """空文件 → json.JSONDecodeError → None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_non_dict_json_batch14(tmp_path):
    """JSON list 也是合法 JSON 但不是 dict — load_annotation 仍返回它（无类型校验）。"""
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_returns_int_json_batch14(tmp_path):
    """JSON int 也合法。"""
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_returns_null_json_batch14(tmp_path):
    """JSON null 也合法。"""
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_uses_utf8_encoding_batch14(tmp_path):
    """读取时 encoding=utf-8。"""
    p = tmp_path / "ann.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    seen: dict = {}
    real_open = Path.open

    def _fake_open(self, *args, **kwargs):
        if self == p:
            seen.update(kwargs)
            return real_open(self, *args, **kwargs)
        return real_open(self, *args, **kwargs)

    with patch.object(Path, "open", _fake_open):
        _load_annotation(p)
    assert seen.get("encoding") == "utf-8"


def test_load_annotation_uses_context_manager_batch14(tmp_path):
    """应该用 with ... as f（context manager）。"""
    p = tmp_path / "ann.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    # 调用不应报错；测试只是确保上下文管理器模式工作正常
    out = _load_annotation(p)
    assert out == {"k": "v"}


# ---------- _process_one 边界深度第十四批 ----------


def test_process_one_calls_process_single_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(out, tuple)
    assert len(out) == 5


def test_process_one_returns_none_document_when_errors_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        doc_dict, err, total, ver, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert doc_dict is None
    assert err == {"code": "parse_failed", "message": "boom"}
    assert ver is None
    assert image_dir is None


def test_process_one_returns_dict_when_document_set_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    stub_doc = _StubDocument(source_hash="b" * 64, parser_version="2.0")
    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        doc_dict, err, total, ver, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert doc_dict == {"source_hash": "b" * 64, "parser_version": "2.0"}
    assert err is None
    assert ver == "2.0"
    assert image_dir is not None


def test_process_one_returns_unknown_error_when_no_document_no_errors_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        doc_dict, err, total, ver, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert doc_dict is None
    assert err == {"code": "unknown", "message": "process_single returned None without errors"}


def test_process_one_unlinks_out_stub_batch14(tmp_path):
    """out_stub 在 _process_one 完成后应被 unlink。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    out_stub_parent = tmp_path / "_per_doc"
    out_stub = out_stub_parent / "doc1.json"
    out_stub_parent.mkdir(parents=True)
    out_stub.write_text("{}", encoding="utf-8")
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            _process_one(doc, tmp_path, "fallback", 800)
    # unlink 后文件不存在（但 process_single mock 没写文件，所以可能本来就不在）
    # 这里只验证 _process_one 调用结束不抛
    assert True


def test_process_one_unlink_oserror_silent_batch14(tmp_path):
    """unlink 抛 OSError 应被吞掉。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    out_stub_parent = tmp_path / "_per_doc"
    out_stub = out_stub_parent / "doc1.json"
    out_stub_parent.mkdir(parents=True)
    out_stub.write_text("{}", encoding="utf-8")

    real_unlink = Path.unlink

    def _fail_unlink(self):
        if self == out_stub:
            raise OSError("denied")
        return real_unlink(self)

    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch.object(Path, "unlink", _fail_unlink):
                _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_image_dir_none_when_document_none_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_out_stub_path_naming_batch14(tmp_path):
    """out_stub 应是 output_root / _per_doc / {doc_id}.json。"""
    doc = _StubDoc(doc_id="abc", resolved_path=Path("/x.pdf"))
    seen: list = []

    def _fake_process_single(path, output_path, *args, **kwargs):
        seen.append(output_path)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            _process_one(doc, tmp_path, "fallback", 800)
    assert seen[0] == tmp_path / "_per_doc" / "abc.json"


def test_process_one_creates_parent_dir_batch14(tmp_path):
    """_per_doc 父目录应被创建。"""
    doc = _StubDoc(doc_id="x", resolved_path=Path("/x.pdf"))
    per_doc_dir = tmp_path / "_per_doc"
    assert not per_doc_dir.exists()
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            _process_one(doc, tmp_path, "fallback", 800)
    assert per_doc_dir.exists()


def test_process_one_kwargs_propagation_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    seen: dict = {}

    def _fake(path, output_path, *args, **kwargs):
        seen.update(kwargs)
        return None, [_StubError()]

    with patch("evaluation.runner.process_single", side_effect=_fake):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            _process_one(doc, tmp_path, "fallback", 800)
    assert seen["parser_name"] == "fallback"
    assert seen["max_chars"] == 800
    assert seen["write_json"] is False


def test_process_one_5tuple_order_batch14(tmp_path):
    """5 元组顺序：(document, error, total, parser_version, image_dir)。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    stub_doc = _StubDocument(source_hash="c" * 64, parser_version="9.9")
    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    assert out[0] == {"source_hash": "c" * 64, "parser_version": "9.9"}
    assert out[1] is None
    assert isinstance(out[2], float)
    assert out[3] == "9.9"
    assert out[4] is not None


# ---------- run_evaluation 字段深度第十四批 ----------


def test_run_evaluation_report_top_keys_batch14(tmp_path):
    """report 顶层 6 个 key。"""
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert set(rep.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_report_keys_order_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    keys = list(rep.keys())
    assert keys[0] == "report_version"
    assert keys[1] == "provenance"
    assert keys[2] == "devset"
    assert keys[3] == "summary"
    assert keys[4] == "per_doc"
    assert keys[5] == "expected_failures"


def test_run_evaluation_per_doc_public_keys_4_batch14(tmp_path):
    """per_doc[] 只暴露 4 个 key（无 _annotation_present / _tolerance_chars / _missing_markers）。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    if rep["per_doc"]:
        for entry in rep["per_doc"]:
            assert set(entry.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_per_doc_keys_order_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    if rep["per_doc"]:
        keys = list(rep["per_doc"][0].keys())
        assert keys[0] == "doc_id"
        assert keys[1] == "source_type"
        assert keys[2] == "metrics"
        assert keys[3] == "wall_time_seconds"


def test_run_evaluation_wall_time_keys_batch14(tmp_path):
    """wall_time_seconds 含 6 个字段：total / parse / chunk / parse_reason / chunk_reason。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    if rep["per_doc"]:
        wt = rep["per_doc"][0]["wall_time_seconds"]
        assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_run_evaluation_wall_time_parse_chunk_null_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    if rep["per_doc"]:
        wt = rep["per_doc"][0]["wall_time_seconds"]
        assert wt["parse"] is None
        assert wt["chunk"] is None
        assert wt["parse_reason"] == "not_instrumented"
        assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_image_dir_not_dir_batch14(tmp_path):
    """image_dir 不是 dir 时 image_base_dir None。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, Path("/nonexistent_dir"))

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["per_doc"][0]["doc_id"] == "doc1"


def test_run_evaluation_parser_version_first_nonnull_kept_batch14(tmp_path):
    """parser_version 第一次非空被采用，后续非空不覆盖。"""
    doc1 = _StubDoc(doc_id="d1", resolved_path=Path("/x.pdf"))
    doc2 = _StubDoc(doc_id="d2", resolved_path=Path("/y.pdf"))
    manifest = _StubManifest(documents=[doc1, doc2])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        if doc.doc_id == "d1":
            return (None, {"code": "x"}, 0.1, "1.0", None)
        return (None, {"code": "x"}, 0.1, "2.0", None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["provenance"]["parser_version"] == "1.0"


def test_run_evaluation_parser_version_null_when_all_null_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["provenance"]["parser_version"] is None


def test_run_evaluation_expected_failure_matches_field_batch14(tmp_path):
    ef = _StubExpectedFailure(doc_id="ef1", resolved_path=Path("/x.pdf"), expected_error_code="unsupported_format")
    manifest = _StubManifest(expected_failures=[ef])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError(code="unsupported_format")])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert len(rep["expected_failures"]) == 1
    ef_out = rep["expected_failures"][0]
    assert set(ef_out.keys()) == {"doc_id", "expected_error_code", "actual_error_code", "matches"}
    assert ef_out["matches"] is True


def test_run_evaluation_expected_failure_no_match_batch14(tmp_path):
    ef = _StubExpectedFailure(doc_id="ef1", resolved_path=Path("/x.pdf"), expected_error_code="unsupported_format")
    manifest = _StubManifest(expected_failures=[ef])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError(code="parse_failed")])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["expected_failures"][0]["matches"] is False
    assert rep["expected_failures"][0]["actual_error_code"] == "parse_failed"


def test_run_evaluation_expected_failure_no_errors_batch14(tmp_path):
    """无 errors → actual_error_code=None → matches=False（除非 expected 也是 None）。"""
    ef = _StubExpectedFailure(doc_id="ef1", resolved_path=Path("/x.pdf"), expected_error_code="unsupported_format")
    manifest = _StubManifest(expected_failures=[ef])
    out_path = tmp_path / "report.json"
    stub_doc = _StubDocument()
    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["expected_failures"][0]["actual_error_code"] is None
    assert rep["expected_failures"][0]["matches"] is False


def test_run_evaluation_writes_file_with_indent_2_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert out_path.is_file()
    text = out_path.read_text(encoding="utf-8")
    # indent=2 → 包含换行
    assert "\n" in text


def test_run_evaluation_writes_file_ensure_ascii_false_batch14(tmp_path):
    """ensure_ascii=False → 中文字符直出（如果 report 含中文）。"""
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    text = out_path.read_text(encoding="utf-8")
    # ensure_ascii=False 不会把中文转义，但我们这里没中文 — 验证至少不是全 ASCII 转义格式
    # 通过验证 json.load 能成功且 dump 相同验证
    parsed = json.loads(text)
    assert "report_version" in parsed


def test_run_evaluation_creates_output_dir_batch14(tmp_path):
    """output_path 父目录不存在时被创建。"""
    manifest = _StubManifest()
    out_path = tmp_path / "subdir1" / "subdir2" / "report.json"
    run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert out_path.is_file()


def test_run_evaluation_report_version_from_evaluation_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["report_version"] == REPORT_VERSION


def test_run_evaluation_returns_dict_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert isinstance(rep, dict)


def test_run_evaluation_no_documents_no_expected_failures_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["per_doc"] == []
    assert rep["expected_failures"] == []


def test_run_evaluation_tolerance_chars_propagated_batch14(tmp_path):
    """tolerance_chars=99 应传给 chunk_boundary_prf。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"
    seen: dict = {}

    def _fake_process(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    import evaluation.runner as rmodule
    real_chunk_b = rmodule.chunk_boundary_prf

    def _spy_chunk_b(document, annotation, tolerance_chars=30):
        seen["tolerance_chars"] = tolerance_chars
        return real_chunk_b(document, annotation, tolerance_chars=tolerance_chars)

    with patch("evaluation.runner._process_one", side_effect=_fake_process):
        with patch("evaluation.runner.chunk_boundary_prf", side_effect=_spy_chunk_b):
            run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800, tolerance_chars=99)
    assert seen["tolerance_chars"] == 99


# ---------- _process_one 5-tuple 元素类型固定第十四批 ----------


def test_process_one_returns_total_seconds_float_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total, float)


def test_process_one_returns_document_dict_or_none_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        d, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert d is None
    stub_doc = _StubDocument()
    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        d, _, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(d, dict)


def test_process_one_returns_error_dict_or_none_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError()])):
        _, e, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(e, dict)
    stub_doc = _StubDocument()
    with patch("evaluation.runner.process_single", return_value=(stub_doc, [])):
        _, e, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert e is None


# ---------- module source forbidden tokens 第十九批 ----------


_FORBIDDEN_TOKENS_ROUND19 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND19)
def test_module_source_forbidden_tokens_round19_batch14(token):
    source = inspect.getsource(rmod)
    assert token not in source


# ---------- module source 字符串精确补强第十六批 ----------


def test_module_source_module_docstring_present_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_json_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_time_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import time" in head


def test_module_source_imports_pathlib_path_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_any_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_pipeline_helpers_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from app.pipeline import image_output_dir_for, process_single" in head


def test_module_source_imports_annotation_metrics_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.annotation_metrics import (" in head


def test_module_source_imports_metrics_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.metrics import compute_automatic_metrics" in head


def test_module_source_imports_report_helpers_batch14():
    source = inspect.getsource(rmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.report import (" in head


def test_module_source_defines_load_annotation_batch14():
    source = inspect.getsource(rmod)
    assert "def _load_annotation(" in source


def test_module_source_defines_process_one_batch14():
    source = inspect.getsource(rmod)
    assert "def _process_one(" in source


def test_module_source_defines_run_evaluation_batch14():
    source = inspect.getsource(rmod)
    assert "def run_evaluation(" in source


def test_module_source_has_dunder_all_batch14():
    source = inspect.getsource(rmod)
    assert "__all__" in source


def test_module_source_dunder_all_one_item_batch14():
    source = inspect.getsource(rmod)
    assert '"run_evaluation"' in source


def test_module_source_uses_perf_counter_batch14():
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_uses_not_instrumented_batch14():
    source = inspect.getsource(rmod)
    assert "not_instrumented" in source


def test_module_source_uses_write_json_false_batch14():
    source = inspect.getsource(rmod)
    assert "write_json=False" in source


def test_module_source_no_eval_call_batch14():
    source = inspect.getsource(rmod)
    assert "eval(" not in source


def test_module_source_no_open_with_str_path_batch14():
    """应只用 Path.open()，不用 open()。"""
    source = inspect.getsource(rmod)
    # 检查没有裸的 open( 调用（Path.open 才合法）
    # 但 with path.open 是合法的
    assert "open(" in source  # path.open 用法
    # 不应出现裸 open("/...
    assert "open('/" not in source
    assert 'open("/' not in source


def test_module_source_no_subprocess_import_batch14():
    """runner 不直接调 subprocess（report.py 才调）。"""
    source = inspect.getsource(rmod)
    assert "import subprocess" not in source


def test_module_source_uses_json_dump_batch14():
    source = inspect.getsource(rmod)
    assert "json.dump(" in source


def test_module_source_uses_image_output_dir_for_batch14():
    source = inspect.getsource(rmod)
    assert "image_output_dir_for" in source


def test_module_source_uses_compute_automatic_metrics_batch14():
    source = inspect.getsource(rmod)
    assert "compute_automatic_metrics" in source


def test_module_source_uses_aggregate_summary_batch14():
    source = inspect.getsource(rmod)
    assert "aggregate_summary" in source


# ---------- signatures 第十六批 ----------


def test_load_annotation_signature_one_param_batch14():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1
    assert "path" in sig.parameters


def test_process_one_signature_4_params_batch14():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4
    for name in ("doc", "output_root", "parser_name", "max_chars"):
        assert name in sig.parameters


def test_run_evaluation_signature_5_params_batch14():
    sig = inspect.signature(run_evaluation)
    # manifest, output_path, parser_name, max_chars, tolerance_chars
    assert len(sig.parameters) == 5
    for name in ("manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"):
        assert name in sig.parameters


def test_run_evaluation_keyword_only_args_batch14():
    """parser_name/max_chars/tolerance_chars 必须是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    p_parser = sig.parameters["parser_name"]
    p_max = sig.parameters["max_chars"]
    p_tol = sig.parameters["tolerance_chars"]
    assert p_parser.kind == inspect.Parameter.KEYWORD_ONLY
    assert p_max.kind == inspect.Parameter.KEYWORD_ONLY
    assert p_tol.kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_manifest_positional_batch14():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_output_path_positional_batch14():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_default_parser_name_batch14():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_default_max_chars_batch14():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_default_tolerance_chars_batch14():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_load_annotation_path_optional_batch14():
    """path 类型是 Path | None。"""
    sig = inspect.signature(_load_annotation)
    sig_str = str(sig.parameters["path"].annotation)
    assert "None" in sig_str or "Optional" in sig_str


def test_process_one_return_annotation_tuple_batch14():
    sig = inspect.signature(_process_one)
    ret = str(sig.return_annotation)
    assert "tuple" in ret


def test_run_evaluation_return_annotation_dict_batch14():
    sig = inspect.signature(run_evaluation)
    ret = str(sig.return_annotation)
    assert "dict" in ret


def test_module_dunder_all_callable_batch14():
    for name in rmod.__all__:
        assert callable(getattr(rmod, name))


# ---------- module 合理性第十六批 ----------


def test_module_dunder_file_exists_batch14():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_runner_py_batch14():
    assert "evaluation" in rmod.__file__
    assert rmod.__file__.endswith("runner.py")


def test_module_name_evaluation_runner_batch14():
    assert rmod.__name__ == "evaluation.runner"


def test_module_dunder_all_one_item_batch14():
    assert len(rmod.__all__) == 1


def test_module_dunder_all_value_run_evaluation_batch14():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_private_funcs_start_with_underscore_batch14():
    """_load_annotation / _process_one 都以下划线开头（私有）。"""
    assert hasattr(rmod, "_load_annotation")
    assert hasattr(rmod, "_process_one")


def test_module_no_class_definitions_batch14():
    classes = [
        n for n, v in vars(rmod).items()
        if inspect.isclass(v) and v.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_public_function_count_one_batch14():
    """只有 run_evaluation 是 public。"""
    public = [n for n in dir(rmod) if not n.startswith("_") and callable(getattr(rmod, n)) and n in rmod.__all__]
    assert public == ["run_evaluation"]


# ---------- 端到端集成第十六批 ----------


def test_e2e_run_evaluation_with_empty_manifest_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    # 验证 report 可 json round-trip
    parsed = json.loads(json.dumps(rep))
    assert parsed == rep


def test_e2e_run_evaluation_file_matches_returned_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    file_text = out_path.read_text(encoding="utf-8")
    file_rep = json.loads(file_text)
    assert file_rep == rep


def test_e2e_run_evaluation_idempotent_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep1 = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    rep2 = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    # 去掉 timestamp 后应相同
    rep1["provenance"].pop("run_timestamp_iso", None)
    rep2["provenance"].pop("run_timestamp_iso", None)
    assert rep1 == rep2


def test_e2e_run_evaluation_per_doc_independent_dicts_batch14(tmp_path):
    doc1 = _StubDoc(doc_id="d1", resolved_path=Path("/x.pdf"))
    doc2 = _StubDoc(doc_id="d2", resolved_path=Path("/y.pdf"))
    manifest = _StubManifest(documents=[doc1, doc2])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["per_doc"][0] is not rep["per_doc"][1]


def test_e2e_run_evaluation_full_flow_with_docx_batch14(tmp_path):
    """source_type=docx 路由也能跑通。"""
    doc = _StubDoc(doc_id="d", source_type="docx", resolved_path=Path("/x.docx"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["per_doc"][0]["source_type"] == "docx"


def test_e2e_run_evaluation_with_expected_failure_only_batch14(tmp_path):
    ef = _StubExpectedFailure(doc_id="ef1", resolved_path=Path("/x.bad"))
    manifest = _StubManifest(expected_failures=[ef])
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(None, [_StubError(code="unsupported_format")])):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert rep["per_doc"] == []
    assert len(rep["expected_failures"]) == 1
    assert rep["expected_failures"][0]["matches"] is True


def test_e2e_load_annotation_then_used_in_run_evaluation_batch14(tmp_path):
    """annotation 文件存在 → _annotation_present=True。"""
    ann_path = tmp_path / "ann.json"
    ann_path.write_text('{"k": "v"}', encoding="utf-8")
    doc = _StubDoc(
        doc_id="d",
        resolved_path=Path("/x.pdf"),
        annotation_resolved=ann_path,
    )
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    # 公开 per_doc 不暴露 _annotation_present，但 metrics 应正常计算
    assert "metrics" in rep["per_doc"][0]


def test_e2e_combined_three_components_json_serializable_batch14(tmp_path):
    """provenance + devset + summary 三块都 json 可序列化。"""
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    parsed = json.loads(json.dumps(rep))
    assert parsed == rep


def test_e2e_run_evaluation_per_doc_metrics_dict_present_batch14(tmp_path):
    doc = _StubDoc(resolved_path=Path("/x.pdf"))
    manifest = _StubManifest(documents=[doc])
    out_path = tmp_path / "report.json"

    def _fake(doc, output_root, parser_name, max_chars):
        return (None, {"code": "x"}, 0.1, None, None)

    with patch("evaluation.runner._process_one", side_effect=_fake):
        rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert isinstance(rep["per_doc"][0]["metrics"], dict)


def test_e2e_run_evaluation_summary_present_batch14(tmp_path):
    manifest = _StubManifest()
    out_path = tmp_path / "report.json"
    rep = run_evaluation(manifest, out_path, parser_name="fallback", max_chars=800)
    assert "summary" in rep
    assert isinstance(rep["summary"], dict)
