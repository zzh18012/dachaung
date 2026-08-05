r"""evaluation/runner.py 边角测试 - 第十一轮（Round 220）。

补强已有 base/edges/edges2-10（共 ~888 测试）未覆盖的深度：
- _load_annotation：JSON 含注释（非法）/ 含 UTF-8 BOM / 含 trailing comma
- _process_one：parser_version 类型多样化 / image_dir 路径拼接 / out_stub.parent mkdir
- run_evaluation：report 字段顺序 / parser_name 传播 / max_chars 0 / tolerance_chars 0
- run_evaluation：image_dir None 时不传给 metrics（image_base_dir None）
- run_evaluation：expected_failure actual_error_code 来自 errors[0].code
- run_evaluation：图 existence 不影响指标计算路径
- 模块结构 / __all__ / imports / docstring 深度
- 综合行为 / 边界
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


class _FakeDocEntry:
    def __init__(self, doc_id="d1", resolved_path=None, source_type="text",
                 expectations=None, annotation_resolved=None):
        self.doc_id = doc_id
        self.resolved_path = resolved_path or Path("/tmp/x.txt")
        self.source_type = source_type
        self.expectations = expectations
        self.annotation_resolved = annotation_resolved


class _FakeError:
    def __init__(self, code="x", message="boom"):
        self.code = code
        self.message = message

    def to_dict(self):
        return {"code": self.code, "message": self.message}


class _FakeDocument:
    def __init__(self, source_hash="a" * 64, parser_version="0.1.0"):
        self.source_hash = source_hash
        self.parser_version = parser_version

    def to_dict(self):
        return {"source_hash": self.source_hash, "parser_version": self.parser_version}


class _FakeManifest:
    def __init__(self, documents=None, expected_failures=None, project_root=None):
        self.documents = documents or []
        self.expected_failures = expected_failures or []
        self.devset_status = "incomplete"
        self.file_count = len(self.documents)
        self.content_group_count = 1
        self.pdf_count = 0
        self.docx_count = 0
        self.categories_covered = ["text"]
        self.project_root = project_root if project_root is not None else Path(".")


class _FakeExpectedFailure:
    def __init__(self, doc_id, resolved_path, expected_error_code):
        self.doc_id = doc_id
        self.resolved_path = resolved_path
        self.expected_error_code = expected_error_code


# =========================================================================
# _load_annotation 深度（补强 edges10）
# =========================================================================


def test_load_annotation_json_with_trailing_comma_invalid(tmp_path):
    """JSON 不允许 trailing comma。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_with_comment_invalid(tmp_path):
    """JSON 不允许注释。"""
    p = tmp_path / "a.json"
    p.write_text('// comment\n{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_with_single_quotes_invalid(tmp_path):
    """JSON 字符串必须用双引号。"""
    p = tmp_path / "a.json"
    p.write_text("{'a': 1}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_huge_file(tmp_path):
    """大文件仍能解析。"""
    p = tmp_path / "a.json"
    data = {f"k{i}": f"v{i}" for i in range(1000)}
    p.write_text(json.dumps(data), encoding="utf-8")
    result = _load_annotation(p)
    assert len(result) == 1000


def test_load_annotation_utf8_bom_invalid_json(tmp_path):
    """UTF-8 BOM 不是合法 JSON 起始 → JSONDecodeError。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": 1}')
    assert _load_annotation(p) is None


def test_load_annotation_utf16_invalid_json(tmp_path):
    """UTF-16 编码的 JSON → UnicodeDecodeError（不被 except 捕获）→ 抛出。

    行为记录：_load_annotation except 只捕 OSError / JSONDecodeError，
    不捕 UnicodeDecodeError。这是设计选择（call site 期望 utf-8）。
    """
    p = tmp_path / "a.json"
    p.write_text('{"k": "v"}', encoding="utf-16")
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


def test_load_annotation_returns_none_for_directory_symlink_like(tmp_path):
    """目录 → is_file() False → None。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _load_annotation(sub) is None


def test_load_annotation_unicode_keys(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"中": "文"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"中": "文"}


def test_load_annotation_escapes(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(r'{"k": "a\\b\\c"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"k": "a\\b\\c"}


# =========================================================================
# _process_one 深度（补强 edges10）
# =========================================================================


def test_process_one_returns_path_or_none_for_image_dir(tmp_path, monkeypatch):
    """image_dir 要么是 Path 要么是 None。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, _, image_dir = _process_one(doc_entry, tmp_path, "text", 800)
    assert image_dir is None or isinstance(image_dir, Path)


def test_process_one_creates_parent_dir_for_out_stub(tmp_path, monkeypatch):
    """out_stub.parent.mkdir(parents=True, exist_ok=True) 应创建 _per_doc。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "text", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_out_stub_unlink_when_written(tmp_path, monkeypatch):
    """process_single 写盘后 _process_one 应清理 stub。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(path, output_path, **kwargs):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "text", 800)
    stub = tmp_path / "_per_doc" / "d1.json"
    assert not stub.is_file()


def test_process_one_error_dict_contains_code_and_message(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="custom_code", message="custom_msg")]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, error, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert error["code"] == "custom_code"
    assert error["message"] == "custom_msg"


def test_process_one_unknown_error_has_descriptive_message(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, error, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert "process_single" in error["message"]
    assert "None" in error["message"] or "None without" in error["message"]


def test_process_one_document_to_dict_called(tmp_path, monkeypatch):
    """成功路径要 document.to_dict() → 写入返回 dict。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    to_dict_calls = []

    class _TrackingDocument:
        def __init__(self):
            self.source_hash = "a" * 64
            self.parser_version = "0.1.0"

        def to_dict(self):
            to_dict_calls.append(True)
            return {"source_hash": self.source_hash}

    def fake_process_single(*args, **kwargs):
        return _TrackingDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    document_dict, _, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert document_dict == {"source_hash": "a" * 64}
    assert to_dict_calls == [True]


def test_process_one_returns_5_tuple_consistent_types(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    result = _process_one(doc_entry, tmp_path, "text", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5
    # (document_dict|None, error_dict|None, total_seconds, parser_version|None, image_dir|None)
    doc, err, total, pver, idir = result
    assert doc is None or isinstance(doc, dict)
    assert err is None or isinstance(err, dict)
    assert isinstance(total, float)
    assert pver is None or isinstance(pver, str)
    assert idir is None or isinstance(idir, Path)


# =========================================================================
# run_evaluation 深度（补强 edges10）
# =========================================================================


def test_run_evaluation_returns_dict_with_six_top_keys(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report.keys()) == 6


def test_run_evaluation_report_keys_order(tmp_path):
    """Python dict 保留插入顺序。顶层 keys 顺序：version, provenance, devset, summary, per_doc, expected_failures。"""
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    keys = list(report.keys())
    assert keys == [
        "report_version", "provenance", "devset",
        "summary", "per_doc", "expected_failures",
    ]


def test_run_evaluation_parser_name_propagated_to_provenance(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, parser_name="kreuzberg")
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_max_chars_zero(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, max_chars=0)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["provenance"]["max_chars"] == 0


def test_run_evaluation_max_chars_negative(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, max_chars=-100)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["provenance"]["max_chars"] == -100


def test_run_evaluation_tolerance_chars_zero(tmp_path, monkeypatch):
    """tolerance_chars=0 → chunk_boundary_prf 接收 0。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    captured = []

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    def fake_chunk_b(document, annotation, *, tolerance_chars=30):
        captured.append(tolerance_chars)
        return {
            "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
            "_tolerance_chars": {"value": tolerance_chars, "reason": None},
            "_missing_markers": {"value": [], "reason": None},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.chunk_boundary_prf", fake_chunk_b)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, tolerance_chars=0)
    assert captured == [0]


def test_run_evaluation_report_file_does_not_contain_private_keys(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    assert "_annotation_present" not in text
    assert "_tolerance_chars" not in text
    assert "_missing_markers" not in text


def test_run_evaluation_doc_with_expectations(tmp_path, monkeypatch):
    """expectations 在 doc 上 → metrics 中 silent_drop_count 应被算。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(
        doc_id="a", resolved_path=p,
        expectations={"element_count_by_type": {"paragraph": 10}},
    )]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    # silent_drop_count 应在 metrics 中（值不一定为 0）
    metric = report["per_doc"][0]["metrics"].get("silent_drop_count")
    assert metric is not None


def test_run_evaluation_per_doc_doc_id_propagated(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="custom_doc_id", resolved_path=p)]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"][0]["doc_id"] == "custom_doc_id"


def test_run_evaluation_expected_failures_doc_id_propagated(tmp_path):
    bad = tmp_path / "missing.txt"
    ef = _FakeExpectedFailure("custom_ef_id", bad, "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["doc_id"] == "custom_ef_id"


def test_run_evaluation_expected_failure_two_distinct_codes(tmp_path):
    """两个 ef，期望不同错误代码。"""
    bad1 = tmp_path / "m1.txt"
    bad2 = tmp_path / "m2.txt"
    ef1 = _FakeExpectedFailure("ef1", bad1, "file_not_found")
    ef2 = _FakeExpectedFailure("ef2", bad2, "different_code")
    manifest = _FakeManifest(expected_failures=[ef1, ef2])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["expected_error_code"] == "file_not_found"
    assert report["expected_failures"][1]["expected_error_code"] == "different_code"


def test_run_evaluation_three_docs_full_per_doc(tmp_path, monkeypatch):
    docs = []
    for i in range(3):
        p = tmp_path / f"x{i}.txt"
        p.write_text(f"hi {i}", encoding="utf-8")
        docs.append(_FakeDocEntry(doc_id=f"d{i}", resolved_path=p))

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(parser_version="0.1.0"), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 3
    assert [r["doc_id"] for r in report["per_doc"]] == ["d0", "d1", "d2"]
    assert all(r["source_type"] == "text" for r in report["per_doc"])


def test_run_evaluation_run_when_no_docs_summary_present(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "summary" in report
    assert "counts" in report["summary"]
    assert "success_rates" in report["summary"]


def test_run_evaluation_devset_status_propagated(tmp_path):
    manifest = _FakeManifest()
    manifest.devset_status = "complete"
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["status"] == "complete"


def test_run_evaluation_devset_categories_covered(tmp_path):
    manifest = _FakeManifest()
    manifest.categories_covered = ["text", "table"]
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["categories_covered"] == ["text", "table"]


def test_run_evaluation_devset_pdf_count(tmp_path):
    manifest = _FakeManifest()
    manifest.pdf_count = 5
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["pdf_count"] == 5


def test_run_evaluation_devset_docx_count(tmp_path):
    manifest = _FakeManifest()
    manifest.docx_count = 7
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["docx_count"] == 7


def test_run_evaluation_devset_file_count(tmp_path):
    manifest = _FakeManifest()
    manifest.file_count = 42
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["file_count"] == 42


def test_run_evaluation_devset_content_group_count(tmp_path):
    manifest = _FakeManifest()
    manifest.content_group_count = 3
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["content_group_count"] == 3


# =========================================================================
# 模块结构（补强 edges10）
# =========================================================================


def test_module_docstring_mentions_parsing_or_pipeline():
    import evaluation.runner as m
    doc = m.__doc__
    assert "pipeline" in doc.lower() or "process" in doc.lower()


def test_module_docstring_mentions_image_dir_strategy():
    """docstring 应解释 image_dir 派生策略。"""
    import evaluation.runner as m
    doc = m.__doc__
    # 任一关键词出现即可
    assert "image" in doc.lower()
    assert "outputs" in doc.lower() or "_per_doc" in doc


def test_module_imports_image_output_dir_for():
    """image_output_dir_for 应从 app.pipeline import。"""
    import evaluation.runner as m
    assert callable(m.image_output_dir_for)


def test_module_run_evaluation_keyword_only_kwargs():
    """parser_name/max_chars/tolerance_chars 必须是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_module_manifest_param_positional():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_module_output_path_param_positional():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_module_process_one_returns_tuple_str_annotation():
    sig = inspect.signature(_process_one)
    assert "tuple" in sig.return_annotation


def test_module_load_annotation_returns_dict_or_none_str_annotation():
    sig = inspect.signature(_load_annotation)
    # 简单断言返回类型注解包含 None
    assert "None" in sig.return_annotation


def test_module_all_contains_only_run_evaluation():
    import evaluation.runner as m
    assert m.__all__ == ["run_evaluation"]


def test_module_all_is_list():
    import evaluation.runner as m
    assert isinstance(m.__all__, list)


def test_module_has_no_public_internal_helpers():
    """__all__ 不应包含 _load_annotation / _process_one。"""
    import evaluation.runner as m
    assert "_load_annotation" not in m.__all__
    assert "_process_one" not in m.__all__


# =========================================================================
# 综合行为
# =========================================================================


def test_run_evaluation_no_side_effects_on_manifest(tmp_path, monkeypatch):
    """runner 不应修改 manifest 对象。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]
    manifest = _FakeManifest(documents=docs)
    original_doc_count = len(manifest.documents)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert len(manifest.documents) == original_doc_count


def test_run_evaluation_no_modification_of_per_doc_results(tmp_path, monkeypatch):
    """public per_doc 不应被修改（每次新 dict）。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        # 每个 r 都是 4 keys
        assert set(r.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_run_idempotent(tmp_path, monkeypatch):
    """同 manifest 跑两次 → 两份相同结构的报告。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    # 不应同对象（每次新 dict）
    assert r1 is not r2
    # 但结构应一致
    assert set(r1.keys()) == set(r2.keys())
