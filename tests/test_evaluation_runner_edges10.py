r"""evaluation/runner.py 边角测试 - 第十轮（Round 214）。

补强已有 base/edges/edges2-9（共 ~813 测试）未覆盖的深度：
- _load_annotation：路径类型多样化 / 含 BOM / 含尾随空白 / 含大对象
- _process_one：unlink OSError 吞掉 / out_stub 不存在跳过 unlink
- _process_one：errors 列表多条时取 errors[0]
- _process_one：document is None 但 errors 空时 image_dir 仍 None
- _process_one：不同 doc_id 改变 out_stub 名字
- run_evaluation：多个文档顺序处理 / per_doc 顺序对齐 manifest.documents
- run_evaluation：parser_version_for_prov 取首个非 None
- run_evaluation：missing_markers / tolerance_record 默认值
- run_evaluation：image_base_dir 在 image_dir 不是目录时 None
- run_evaluation：output_path 接受 str / 深层目录创建
- run_evaluation：expected_failures 流程 / 多个 ef 顺序
- 模块结构：__all__/imports/docstring 深度
"""

from __future__ import annotations

import inspect
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# 共用辅助
# =========================================================================


class _FakeDocEntry:
    """模拟 DocumentEntry。"""

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
    def __init__(self, documents=None, expected_failures=None,
                 project_root=None):
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
# _load_annotation 深度（补强 edges9）
# =========================================================================


def test_load_annotation_path_object_passed(tmp_path):
    """传 Path 对象，存在 → 返回 dict。"""
    p = tmp_path / "a.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    assert _load_annotation(p) == {"k": 1}


def test_load_annotation_str_path_does_not_work(tmp_path):
    """传字符串路径：函数签名标 Path | None，传 str 会 AttributeError。

    str 没有 is_file 方法 → 抛 AttributeError 而不是返回 None。
    这是行为记录，不是 bug。
    """
    p = tmp_path / "a.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    with pytest.raises(AttributeError):
        _load_annotation(str(p))


def test_load_annotation_bom_is_invalid_json(tmp_path):
    """UTF-8 BOM 后跟 JSON：json.load 会失败（BOM 不是有效 JSON 起始字符）。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": 1}')
    assert _load_annotation(p) is None


def test_load_annotation_whitespace_only_is_invalid(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("   \n\t  ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_trailing_newline_ok(tmp_path):
    """JSON 末尾单个换行仍可解析。"""
    p = tmp_path / "a.json"
    p.write_text('{"k": 1}\n', encoding="utf-8")
    assert _load_annotation(p) == {"k": 1}


def test_load_annotation_two_json_objects_invalid(tmp_path):
    """两个 JSON 对象连写 → json.JSONDecodeError。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}{"b": 2}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_array_of_mixed_types(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('[1, "x", null, true, {"k": "v"}]', encoding="utf-8")
    result = _load_annotation(p)
    assert result == [1, "x", None, True, {"k": "v"}]


def test_load_annotation_huge_nested_struct(tmp_path):
    """深度嵌套 dict 仍能解析。"""
    p = tmp_path / "a.json"
    data = {"a": {"b": {"c": {"d": {"e": "deep"}}}}}
    p.write_text(json.dumps(data), encoding="utf-8")
    assert _load_annotation(p) == data


def test_load_annotation_does_not_keep_open_handle(tmp_path):
    """load 完后文件句柄应关闭（再次写入应成功，Windows 上尤其重要）。"""
    p = tmp_path / "a.json"
    p.write_text('{"k": 1}', encoding="utf-8")
    _load_annotation(p)
    # 应能再次写入
    p.write_text('{"k": 2}', encoding="utf-8")
    assert _load_annotation(p) == {"k": 2}


# =========================================================================
# _process_one 深度（补强 edges9）
# =========================================================================


def test_process_one_returns_parser_version_when_doc_present(tmp_path, monkeypatch):
    """成功路径：parser_version 从 document.parser_version 取。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(parser_version="9.9.9"), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, parser_version, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert parser_version == "9.9.9"


def test_process_one_returns_no_parser_version_when_error(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="x")]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, parser_version, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert parser_version is None


def test_process_one_returns_no_parser_version_when_doc_none_no_errors(tmp_path, monkeypatch):
    """process_single 返回 (None, []) 时 parser_version 应为 None。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, parser_version, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert parser_version is None


def test_process_one_multiple_errors_returns_first_only(tmp_path, monkeypatch):
    """errors 是 list，runner 取 errors[0]。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="first"), _FakeError(code="second")]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, error, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert error["code"] == "first"


def test_process_one_unknown_error_code_when_no_errors_no_doc(tmp_path, monkeypatch):
    """(None, []) → error code 'unknown'。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, error, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert error["code"] == "unknown"
    assert "process_single" in error["message"]


def test_process_one_unlink_failure_swallowed(tmp_path, monkeypatch):
    """out_stub.unlink 抛 OSError 时应被吞掉，不传播。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    real_unlink = Path.unlink

    def fake_unlink(self, *args, **kwargs):
        if self.name == "d1.json":
            raise OSError("simulated")
        return real_unlink(self, *args, **kwargs)

    def fake_process_single(path, output_path, **kwargs):
        # 模拟 pipeline 写盘（让 out_stub.is_file() 为 True）
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr(Path, "unlink", fake_unlink)
    # 不应抛 OSError
    document_dict, _, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert document_dict is not None


def test_process_one_no_unlink_when_stub_not_file(tmp_path, monkeypatch):
    """process_single 未写盘 → out_stub.is_file() False → 不调用 unlink。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    unlink_calls = []

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    def tracking_unlink(self, *args, **kwargs):
        unlink_calls.append(self)
        return None

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr(Path, "unlink", tracking_unlink)
    _process_one(doc_entry, tmp_path, "text", 800)
    assert unlink_calls == []


def test_process_one_creates_per_doc_subdir_named_by_doc_id(tmp_path, monkeypatch):
    """out_stub = output_root/_per_doc/<doc_id>.json。"""
    doc_entry = _FakeDocEntry(doc_id="custom_id", resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "text", 800)
    expected = tmp_path / "_per_doc" / "custom_id.json"
    # stub 在成功后 unlink，所以文件不存在；但父目录存在
    assert expected.parent.is_dir()


def test_process_one_total_seconds_increases_with_sleep(tmp_path, monkeypatch):
    """total 至少为 sleep 时长。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def slow_process_single(*args, **kwargs):
        time.sleep(0.02)
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", slow_process_single)
    _, _, total, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert total >= 0.015  # 至少 15ms


def test_process_one_per_doc_dir_idempotent(tmp_path, monkeypatch):
    """mkdir(parents=True, exist_ok=True) 已存在不报错。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")
    # 先建目录
    (tmp_path / "_per_doc").mkdir(parents=True, exist_ok=True)

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    # 不应抛异常
    _process_one(doc_entry, tmp_path, "text", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_image_dir_full_sha_16_chars(tmp_path, monkeypatch):
    """完整 64 字符 source_hash → image_dir 名取前 16 字符。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")
    sha = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(source_hash=sha), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, _, image_dir = _process_one(doc_entry, tmp_path, "text", 800)
    assert image_dir is not None
    assert image_dir.name == f"images-{sha[:16]}"


# =========================================================================
# run_evaluation 多文档 + 顺序（补强 edges9）
# =========================================================================


def test_run_evaluation_per_doc_order_matches_manifest(tmp_path, monkeypatch):
    """per_doc 列表顺序应与 manifest.documents 顺序一致。"""
    docs = []
    for i in range(3):
        p = tmp_path / f"x{i}.txt"
        p.write_text(f"hello {i}", encoding="utf-8")
        docs.append(_FakeDocEntry(doc_id=f"d{i}", resolved_path=p))

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert [r["doc_id"] for r in report["per_doc"]] == ["d0", "d1", "d2"]


def test_run_evaluation_per_doc_source_type_propagated(tmp_path, monkeypatch):
    """每个 per_doc 的 source_type 来自 manifest doc.source_type。"""
    p1 = tmp_path / "a.txt"
    p1.write_text("hi", encoding="utf-8")
    p2 = tmp_path / "b.txt"
    p2.write_text("hi", encoding="utf-8")
    docs = [
        _FakeDocEntry(doc_id="a", resolved_path=p1, source_type="text"),
        _FakeDocEntry(doc_id="b", resolved_path=p2, source_type="pdf"),
    ]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    types = [r["source_type"] for r in report["per_doc"]]
    assert types == ["text", "pdf"]


def test_run_evaluation_parser_version_first_non_none(tmp_path, monkeypatch):
    """parser_version_for_prov 取首个非 None（即便后续文档也有版本）。"""
    p1 = tmp_path / "a.txt"
    p1.write_text("hi", encoding="utf-8")
    p2 = tmp_path / "b.txt"
    p2.write_text("hi", encoding="utf-8")
    docs = [
        _FakeDocEntry(doc_id="a", resolved_path=p1),
        _FakeDocEntry(doc_id="b", resolved_path=p2),
    ]

    call_count = [0]

    def fake_process_single(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _FakeDocument(parser_version="1.0.0"), []
        return _FakeDocument(parser_version="2.0.0"), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_parser_version_skips_failed(tmp_path, monkeypatch):
    """第一个文档失败（parser_version=None），第二个成功 → 取第二个的 version。"""
    p1 = tmp_path / "a.txt"
    p1.write_text("hi", encoding="utf-8")
    p2 = tmp_path / "b.txt"
    p2.write_text("hi", encoding="utf-8")
    docs = [
        _FakeDocEntry(doc_id="a", resolved_path=p1),
        _FakeDocEntry(doc_id="b", resolved_path=p2),
    ]

    call_count = [0]

    def fake_process_single(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return None, [_FakeError(code="fail")]
        return _FakeDocument(parser_version="3.3.3"), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] == "3.3.3"


def test_run_evaluation_parser_version_all_failed_is_none(tmp_path, monkeypatch):
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="fail")]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] is None


def test_run_evaluation_image_base_dir_none_when_image_dir_not_dir(tmp_path, monkeypatch):
    """image_dir 不是目录（is_dir() False）→ image_base_dir 给 metrics 是 None。

    这条覆盖 `image_dir if (image_dir is not None and image_dir.is_dir()) else None`
    中的 image_dir.is_dir() False 分支。
    """
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    seen_image_base_dir = []

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    def fake_compute(*args, **kwargs):
        seen_image_base_dir.append(kwargs.get("image_base_dir"))
        # 返回一个空 metrics dict
        return {
            "pipeline_success": {"value": True, "reason": None},
            "error_code": {"value": None, "reason": None},
            "schema_valid": {"value": True, "reason": None},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.compute_automatic_metrics", fake_compute)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    # image_dir 被 _process_one 派生，但通常不存在 → is_dir() False → None
    assert seen_image_base_dir == [None]


def test_run_evaluation_image_base_dir_used_when_dir_exists(tmp_path, monkeypatch):
    """image_dir 是目录 → 传给 metrics 作为 image_base_dir。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    seen_image_base_dir = []

    def fake_process_single(path, output_path, **kwargs):
        # 让 _process_one 派生的 image_dir 是已存在的目录
        output_path.parent.mkdir(parents=True, exist_ok=True)
        from app.pipeline import image_output_dir_for
        image_dir = image_output_dir_for(output_path, "a" * 64)
        image_dir.mkdir(parents=True, exist_ok=True)
        return _FakeDocument(), []

    def fake_compute(*args, **kwargs):
        seen_image_base_dir.append(kwargs.get("image_base_dir"))
        return {
            "pipeline_success": {"value": True, "reason": None},
            "error_code": {"value": None, "reason": None},
            "schema_valid": {"value": True, "reason": None},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.compute_automatic_metrics", fake_compute)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert seen_image_base_dir[0] is not None
    assert seen_image_base_dir[0].is_dir()


def test_run_evaluation_missing_markers_default_empty_list(tmp_path, monkeypatch):
    """无 annotation → chunk_b 没有 _missing_markers → public per_doc 不出现该键。

    验证内部 default = []。
    """
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
        assert "_missing_markers" not in r
        assert "_tolerance_chars" not in r
        assert "_annotation_present" not in r


def test_run_evaluation_output_path_accepts_str(tmp_path):
    """output_path 可以是 str（runner 内部用 Path() 包装）。"""
    manifest = _FakeManifest()
    out_str = str(tmp_path / "report.json")
    run_evaluation(manifest, out_str)
    assert Path(out_str).is_file()


def test_run_evaluation_output_path_deeply_nested(tmp_path):
    """深层目录自动创建。"""
    manifest = _FakeManifest()
    out = tmp_path / "a" / "b" / "c" / "d" / "report.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_output_root_idempotent(tmp_path):
    """output_root 已存在不应报错。"""
    manifest = _FakeManifest()
    (tmp_path / "sub").mkdir()
    out = tmp_path / "sub" / "report.json"
    run_evaluation(manifest, out)
    run_evaluation(manifest, out)  # 第二次：目录已存在
    assert out.is_file()


# =========================================================================
# run_evaluation expected_failures 深度（补强 edges9）
# =========================================================================


def test_run_evaluation_expected_failures_order_preserved(tmp_path):
    """多个 ef 的顺序与 manifest.expected_failures 一致。"""
    ef1 = _FakeExpectedFailure("ef1", tmp_path / "m1.txt", "file_not_found")
    ef2 = _FakeExpectedFailure("ef2", tmp_path / "m2.txt", "file_not_found")
    ef3 = _FakeExpectedFailure("ef3", tmp_path / "m3.txt", "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef1, ef2, ef3])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert [r["doc_id"] for r in report["expected_failures"]] == ["ef1", "ef2", "ef3"]


def test_run_evaluation_expected_failure_creates_per_doc_subdir(tmp_path):
    """expected_failures 处理过程也创建 _per_doc 子目录。"""
    bad = tmp_path / "missing.txt"
    ef = _FakeExpectedFailure("d1", bad, "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "sub" / "report.json"
    run_evaluation(manifest, out)
    assert (tmp_path / "sub" / "_per_doc").is_dir()


def test_run_evaluation_expected_failure_actual_code_from_first_error(tmp_path, monkeypatch):
    """actual_error_code = errors[0].code。"""
    bad = tmp_path / "x.txt"
    bad.write_text("hi", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="first"), _FakeError(code="second")]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    ef = _FakeExpectedFailure("d1", bad, "first")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["actual_error_code"] == "first"


def test_run_evaluation_expected_failure_matches_value_type(tmp_path):
    """matches 字段是 bool 类型。"""
    bad = tmp_path / "missing.txt"
    ef = _FakeExpectedFailure("d1", bad, "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report["expected_failures"][0]["matches"], bool)


# =========================================================================
# run_evaluation 报告结构 + 写盘深度
# =========================================================================


def test_run_evaluation_report_version_value(tmp_path):
    """report_version 来自 REPORT_VERSION 常量。"""
    from evaluation import REPORT_VERSION
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_report_keys_count(tmp_path):
    """report 顶层 keys 数量。"""
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report.keys()) == 6


def test_run_evaluation_summary_keys_count(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report["summary"].keys()) == 4


def test_run_evaluation_provenance_keys_count(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report["provenance"].keys()) == 9


def test_run_evaluation_devset_keys_count(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report["devset"].keys()) == 6


def test_run_evaluation_summary_counts_present(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "counts" in report["summary"]
    assert isinstance(report["summary"]["counts"], dict)


def test_run_evaluation_summary_success_rates_present(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "success_rates" in report["summary"]
    assert isinstance(report["summary"]["success_rates"], dict)


def test_run_evaluation_summary_ratio_macro_averages_present(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "ratio_macro_averages" in report["summary"]
    assert isinstance(report["summary"]["ratio_macro_averages"], dict)


def test_run_evaluation_summary_silent_drop_total_present(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "silent_drop_total" in report["summary"]


# =========================================================================
# 模块结构深度（补强 edges9）
# =========================================================================


def test_module_all_length():
    import evaluation.runner as m
    assert len(m.__all__) == 1


def test_module_all_contains_run_evaluation_only():
    import evaluation.runner as m
    assert m.__all__ == ["run_evaluation"]


def test_module_docstring_mentions_image_dir_or_image_output_dir():
    import evaluation.runner as m
    doc = m.__doc__
    assert "image" in doc.lower()


def test_module_docstring_mentions_write_json_false():
    import evaluation.runner as m
    doc = m.__doc__
    assert "write_json" in doc


def test_module_docstring_mentions_per_doc():
    import evaluation.runner as m
    doc = m.__doc__
    assert "_per_doc" in doc or "per_doc" in doc


def test_module_imports_time_perf_counter():
    import evaluation.runner as m
    assert hasattr(m.time, "perf_counter")


def test_module_run_evaluation_callable():
    import evaluation.runner as m
    assert callable(m.run_evaluation)


def test_module_load_annotation_callable():
    """_load_annotation 是模块级私有函数，仍应 callable。"""
    import evaluation.runner as m
    assert callable(m._load_annotation)


def test_module_process_one_callable():
    import evaluation.runner as m
    assert callable(m._process_one)


def test_run_evaluation_signature_first_param_is_manifest():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters)
    assert params[0] == "manifest"


def test_run_evaluation_signature_second_param_is_output_path():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters)
    assert params[1] == "output_path"


def test_run_evaluation_manifest_param_kind(tmp_path):
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_output_path_param_kind(tmp_path):
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_has_three_keyword_only_params():
    sig = inspect.signature(run_evaluation)
    kw_only = [p for p in sig.parameters.values()
               if p.kind == inspect.Parameter.KEYWORD_ONLY]
    assert len(kw_only) == 3
    assert {p.name for p in kw_only} == {"parser_name", "max_chars", "tolerance_chars"}


def test_run_evaluation_total_params_count():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_load_annotation_param_kind():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_annotation_param_no_default():
    """path 必填（无 default），但类型注解为 Path | None，调用时可传 None。"""
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_process_one_param_kinds():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_has_four_params():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_returns_tuple_annotation_is_str():
    """future annotations → return_annotation 是 str 字面量。"""
    sig = inspect.signature(_process_one)
    assert isinstance(sig.return_annotation, str)


def test_process_one_return_annotation_mentions_tuple():
    sig = inspect.signature(_process_one)
    assert "tuple" in sig.return_annotation


# =========================================================================
# 综合行为
# =========================================================================


def test_run_evaluation_no_documents_creates_empty_per_doc_section(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"] == []


def test_run_evaluation_no_documents_provenance_still_built(tmp_path):
    """空 manifest 仍要构建 provenance。"""
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["provenance"] is not None
    assert "git_commit" in report["provenance"]


def test_run_evaluation_no_documents_devset_still_built(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["devset"] is not None


def test_run_evaluation_no_documents_summary_still_aggregated(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["summary"] is not None


def test_run_evaluation_calls_compute_per_doc(tmp_path, monkeypatch):
    """每个 document 都触发 compute_automatic_metrics 一次。"""
    p1 = tmp_path / "a.txt"
    p1.write_text("hi", encoding="utf-8")
    p2 = tmp_path / "b.txt"
    p2.write_text("hi", encoding="utf-8")
    docs = [
        _FakeDocEntry(doc_id="a", resolved_path=p1),
        _FakeDocEntry(doc_id="b", resolved_path=p2),
    ]

    call_count = [0]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    def fake_compute(*args, **kwargs):
        call_count[0] += 1
        return {
            "pipeline_success": {"value": True, "reason": None},
            "error_code": {"value": None, "reason": None},
            "schema_valid": {"value": True, "reason": None},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.compute_automatic_metrics", fake_compute)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert call_count[0] == 2


def test_run_evaluation_calls_figure_caption_prf_per_doc(tmp_path, monkeypatch):
    p1 = tmp_path / "a.txt"
    p1.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p1)]

    call_count = [0]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    def fake_figcap(*args, **kwargs):
        call_count[0] += 1
        return {
            "figure_caption_precision": {"value": None, "reason": "no_annotation"},
            "figure_caption_recall": {"value": None, "reason": "no_annotation"},
            "figure_caption_f1": {"value": None, "reason": "no_annotation"},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.figure_caption_prf", fake_figcap)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert call_count[0] == 1


def test_run_evaluation_calls_chunk_boundary_prf_per_doc(tmp_path, monkeypatch):
    p1 = tmp_path / "a.txt"
    p1.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p1)]

    call_count = [0]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    def fake_chunk_b(*args, **kwargs):
        call_count[0] += 1
        return {
            "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
            "_tolerance_chars": {"value": 30, "reason": None},
            "_missing_markers": {"value": [], "reason": None},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.chunk_boundary_prf", fake_chunk_b)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert call_count[0] == 1


def test_run_evaluation_tolerance_propagated_to_chunk_boundary_prf(tmp_path, monkeypatch):
    p1 = tmp_path / "a.txt"
    p1.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p1)]

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
    run_evaluation(manifest, out, tolerance_chars=42)
    assert captured == [42]


def test_run_evaluation_returns_report_equal_to_disk(tmp_path, monkeypatch):
    """run_evaluation 返回值应与写盘内容完全一致。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "report.json"
    returned = run_evaluation(manifest, out)
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert returned == on_disk


def test_run_evaluation_creates_per_doc_in_output_parent(tmp_path, monkeypatch):
    """_per_doc 子目录位于 output_path 的 parent。"""
    p = tmp_path / "x.txt"
    p.write_text("hi", encoding="utf-8")
    docs = [_FakeDocEntry(doc_id="a", resolved_path=p)]

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "sub" / "report.json"
    run_evaluation(manifest, out)
    assert (tmp_path / "sub" / "_per_doc").is_dir()
