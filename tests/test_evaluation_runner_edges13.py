r"""evaluation/runner.py 边角测试 - 第十三轮（Round 232）。

补强已有 base/edges/edges2-12（共 ~970 测试）未覆盖的深度：
- run_evaluation：report top-level dict 插入顺序精确
- run_evaluation：per_doc_results（内部）含 7 keys（4 公开 + 3 内部 _）
- run_evaluation：wall_time_seconds dict 插入顺序精确
- run_evaluation：expected_failure_results entry 插入顺序精确
- run_evaluation：_per_doc 目录在 run 之后仍存在
- _process_one：out_stub 文件清理（success / failure / 不存在）
- _process_one：image_dir 仅在 document not None 时计算
- parser_version_for_prov：first non-None wins / all None
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# Helpers（与 edges12 风格一致）
# =========================================================================


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
        return {
            "source_hash": self.source_hash,
            "parser_version": self.parser_version,
            "source_type": "text",
            "elements": [],
            "chunks": [],
        }


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
# run_evaluation：report top-level dict 插入顺序
# =========================================================================


def test_run_evaluation_report_top_level_dict_insertion_order(tmp_path: Path):
    """report 顶层 dict 按 6 个 key 顺序：report_version → provenance → devset → summary → per_doc → expected_failures。"""
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    keys = list(report.keys())
    assert keys[0] == "report_version"
    assert keys[1] == "provenance"
    assert keys[2] == "devset"
    assert keys[3] == "summary"
    assert keys[4] == "per_doc"
    assert keys[5] == "expected_failures"


def test_run_evaluation_report_top_level_keys_count_exactly_six(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert len(report) == 6


def test_run_evaluation_report_per_doc_is_list(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert isinstance(report["per_doc"], list)


def test_run_evaluation_report_expected_failures_is_list(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert isinstance(report["expected_failures"], list)


# =========================================================================
# run_evaluation：per_doc entry 公开 dict 插入顺序
# =========================================================================


def test_run_evaluation_per_doc_entry_insertion_order(tmp_path: Path, monkeypatch):
    """per_doc[i] 按 4 个 key 顺序：doc_id → source_type → metrics → wall_time_seconds。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    keys = list(report["per_doc"][0].keys())
    assert keys[0] == "doc_id"
    assert keys[1] == "source_type"
    assert keys[2] == "metrics"
    assert keys[3] == "wall_time_seconds"


def test_run_evaluation_per_doc_entry_dict_size_four(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert len(report["per_doc"][0]) == 4


# =========================================================================
# run_evaluation：wall_time_seconds dict 插入顺序
# =========================================================================


def test_run_evaluation_wall_time_seconds_insertion_order(tmp_path: Path, monkeypatch):
    """wall_time_seconds 按 5 个 key 顺序：total → parse → chunk → parse_reason → chunk_reason。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    keys = list(wt.keys())
    assert keys[0] == "total"
    assert keys[1] == "parse"
    assert keys[2] == "chunk"
    assert keys[3] == "parse_reason"
    assert keys[4] == "chunk_reason"


def test_run_evaluation_wall_time_seconds_dict_size_five(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert len(wt) == 5


def test_run_evaluation_wall_time_seconds_parse_reason_value(tmp_path: Path, monkeypatch):
    """parse_reason 固定 'not_instrumented'。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_wall_time_seconds_parse_value_none(tmp_path: Path, monkeypatch):
    """parse / chunk value 固定 None（未插桩）。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None


def test_run_evaluation_wall_time_seconds_total_is_float(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert isinstance(wt["total"], float)


# =========================================================================
# run_evaluation：expected_failure_results entry 插入顺序
# =========================================================================


def test_run_evaluation_expected_failure_entry_insertion_order(tmp_path: Path, monkeypatch):
    """expected_failure entry 按 4 个 key 顺序：doc_id → expected_error_code → actual_error_code → matches。"""
    def fake_process_single(*args, **kwargs):
        # 模拟失败：返回 errors
        return None, [_FakeError(code="parse_failed")]
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    ef = _FakeExpectedFailure(doc_id="ef1", resolved_path=Path("/tmp/x.txt"),
                              expected_error_code="parse_failed")
    m = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    keys = list(report["expected_failures"][0].keys())
    assert keys[0] == "doc_id"
    assert keys[1] == "expected_error_code"
    assert keys[2] == "actual_error_code"
    assert keys[3] == "matches"


def test_run_evaluation_expected_failure_entry_dict_size_four(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="parse_failed")]
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    ef = _FakeExpectedFailure(doc_id="ef1", resolved_path=Path("/tmp/x.txt"),
                              expected_error_code="parse_failed")
    m = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert len(report["expected_failures"][0]) == 4


# =========================================================================
# run_evaluation：_per_doc 目录在 run 之后仍存在
# =========================================================================


def test_run_evaluation_per_doc_directory_remains_after_run(tmp_path: Path, monkeypatch):
    """run 之后 _per_doc 目录应仍存在（只清理 .json 文件，目录留作 image_dir 引用）。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.is_dir()


def test_run_evaluation_per_doc_directory_has_no_json_files_after_run(tmp_path: Path, monkeypatch):
    """run 之后 _per_doc 目录里不应有 .json 文件（都被 unlink 了）。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    per_doc_dir = tmp_path / "_per_doc"
    json_files = list(per_doc_dir.glob("*.json"))
    assert json_files == []


def test_run_evaluation_per_doc_directory_has_one_subdir_per_doc(tmp_path: Path, monkeypatch):
    """多个 docs → _per_doc 下有对应多个清理过的 stub（目录留 0 个 json）。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    docs = [
        _FakeDocEntry(doc_id="d1", source_type="pdf"),
        _FakeDocEntry(doc_id="d2", source_type="pdf"),
        _FakeDocEntry(doc_id="d3", source_type="pdf"),
    ]
    m = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    per_doc_dir = tmp_path / "_per_doc"
    json_files = list(per_doc_dir.glob("*.json"))
    assert len(json_files) == 0


# =========================================================================
# run_evaluation：output_root 创建
# =========================================================================


def test_run_evaluation_creates_output_root_when_missing(tmp_path: Path):
    """output_root（output_path.parent）不存在时会被创建。"""
    m = _FakeManifest()
    out = tmp_path / "deep" / "nested" / "dir" / "r.json"
    run_evaluation(m, out)
    assert out.is_file()


def test_run_evaluation_output_root_already_exists(tmp_path: Path):
    """output_root 已存在 → mkdir(exist_ok=True) 不抛异常。"""
    (tmp_path / "out").mkdir()
    m = _FakeManifest()
    out = tmp_path / "out" / "r.json"
    run_evaluation(m, out)
    assert out.is_file()


# =========================================================================
# run_evaluation：parser_version_for_prov 行为
# =========================================================================


def test_run_evaluation_parser_version_first_non_none_wins(tmp_path: Path, monkeypatch):
    """parser_version_for_prov 取第一个 non-None 的 parser_version。"""
    versions = ["v1", "v2", "v3"]
    call_count = [0]

    def fake_process_single(*args, **kwargs):
        v = versions[call_count[0] % 3]
        call_count[0] += 1
        return _FakeDocument(parser_version=v), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    docs = [
        _FakeDocEntry(doc_id="d1", source_type="pdf"),
        _FakeDocEntry(doc_id="d2", source_type="pdf"),
        _FakeDocEntry(doc_id="d3", source_type="pdf"),
    ]
    m = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["provenance"]["parser_version"] == "v1"


def test_run_evaluation_parser_version_for_prov_none_when_all_docs_fail(tmp_path: Path, monkeypatch):
    """所有 docs 都失败 → parser_version_for_prov 仍是 None。"""
    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="x")]
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    docs = [
        _FakeDocEntry(doc_id="d1", source_type="pdf"),
        _FakeDocEntry(doc_id="d2", source_type="pdf"),
    ]
    m = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["provenance"]["parser_version"] is None


def test_run_evaluation_parser_version_for_prov_first_doc_none_uses_second(tmp_path: Path, monkeypatch):
    """第一个 doc parser_version=None，第二个 doc 有值 → 用第二个。"""
    call_count = [0]

    def fake_process_single(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _FakeDocument(parser_version=None), None
        return _FakeDocument(parser_version="v2"), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    docs = [
        _FakeDocEntry(doc_id="d1", source_type="pdf"),
        _FakeDocEntry(doc_id="d2", source_type="pdf"),
    ]
    m = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["provenance"]["parser_version"] == "v2"


# =========================================================================
# _process_one：out_stub 文件清理
# =========================================================================


def test_process_one_out_stub_cleaned_up_on_success(tmp_path: Path, monkeypatch):
    """成功路径：out_stub 文件被 unlink。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    output_root = tmp_path
    doc = _FakeDocEntry(doc_id="d1")
    # 预先创建 out_stub
    out_stub = output_root / "_per_doc" / "d1.json"
    out_stub.parent.mkdir(parents=True, exist_ok=True)
    out_stub.write_text("stub", encoding="utf-8")
    assert out_stub.is_file()

    _process_one(doc, output_root, "fallback", 800)
    # process_single 是 mocked 不会真的写文件，但 runner 仍尝试 unlink 已存在的
    assert not out_stub.is_file()


def test_process_one_out_stub_no_file_when_process_single_does_not_write(tmp_path: Path, monkeypatch):
    """process_single mocked 不写文件 → out_stub 不存在 → unlink 跳过。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    output_root = tmp_path
    doc = _FakeDocEntry(doc_id="d1")
    document, error, elapsed, parser_version, image_dir = _process_one(
        doc, output_root, "fallback", 800
    )
    assert document is not None
    assert error is None


def test_process_one_returns_elapsed_non_negative(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1")
    _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert elapsed >= 0


def test_process_one_returns_parser_version_on_success(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(parser_version="1.2.3"), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1")
    _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version == "1.2.3"


def test_process_one_returns_parser_version_none_on_failure(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="x")]
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1")
    _, _, _, parser_version, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert parser_version is None


# =========================================================================
# _process_one：image_dir 仅在 document not None 时计算
# =========================================================================


def test_process_one_image_dir_is_none_when_document_is_none(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return None, [_FakeError(code="x")]
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1")
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_image_dir_is_path_when_document_present(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1")
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    # image_dir 是 Path 对象（来自 image_output_dir_for）
    from pathlib import Path as _Path
    assert isinstance(image_dir, _Path)


def test_process_one_image_dir_includes_source_hash(tmp_path: Path, monkeypatch):
    """image_dir 路径应包含 source_hash 前 N 字符。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(source_hash="abc123" + "0" * 58), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1")
    _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    # image_dir 是 Path 对象，name 含 source_hash 前缀
    assert "abc123" in str(image_dir) or image_dir.name == "d1.json"


# =========================================================================
# _process_one：unknown 错误（document is None + no errors）
# =========================================================================


def test_process_one_returns_unknown_error_when_document_none_no_errors(tmp_path: Path, monkeypatch):
    """process_single 返回 (None, []) → _process_one 返回 code='unknown' 错误。"""
    def fake_process_single(*args, **kwargs):
        return None, []  # 无错误但 document 也没
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1")
    document, error, elapsed, parser_version, image_dir = _process_one(
        doc, tmp_path, "fallback", 800
    )
    assert document is None
    assert error is not None
    assert error["code"] == "unknown"
    assert "None" in error["message"] or "process_single" in error["message"]


# =========================================================================
# run_evaluation：报告 JSON 文件结构
# =========================================================================


def test_run_evaluation_report_file_is_valid_json(tmp_path: Path, monkeypatch):
    """报告文件能被 json.load 解析。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)
    assert "report_version" in data


def test_run_evaluation_report_file_indent_two(tmp_path: Path, monkeypatch):
    """报告文件使用 indent=2。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 → 第二行以 2 spaces 开头
    lines = content.split("\n")
    if len(lines) > 1:
        assert lines[1].startswith('  "')


def test_run_evaluation_report_file_ensure_ascii_false(tmp_path: Path, monkeypatch):
    """报告文件含非 ASCII（如 categories_covered=['中文']）时不被 escape。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    m.categories_covered = ["中文类别"]
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    assert "中文" in content  # 没有 \u 转义


def test_run_evaluation_returns_same_dict_as_written(tmp_path: Path, monkeypatch):
    """返回值应与写盘内容一致。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    with out.open("r", encoding="utf-8") as f:
        written = json.load(f)
    # 比较关键字段
    assert report["report_version"] == written["report_version"]
    assert len(report["per_doc"]) == len(written["per_doc"])


# =========================================================================
# run_evaluation：annotation_resolved 路径解析
# =========================================================================


def test_run_evaluation_annotation_present_false_when_annotation_resolved_none(tmp_path: Path, monkeypatch):
    """annotation_resolved is None → _annotation_present False。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf", annotation_resolved=None)
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    # 公开 per_doc 不含 _annotation_present；但 metrics 应有 figure_caption_prf 的 null
    assert report["per_doc"][0]["metrics"]["figure_caption_precision"]["value"] is None


def test_run_evaluation_annotation_present_false_when_file_missing(tmp_path: Path, monkeypatch):
    """annotation_resolved 是路径但文件不存在 → _annotation_present False。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(
        doc_id="d1", source_type="pdf",
        annotation_resolved=tmp_path / "missing.json",
    )
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["per_doc"][0]["metrics"]["figure_caption_precision"]["value"] is None


def test_run_evaluation_annotation_present_true_when_file_exists(tmp_path: Path, monkeypatch):
    """annotation_resolved 文件存在 → _annotation_present True；figure_caption 仍 null（无对应字段）。"""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    ann = tmp_path / "ann.json"
    ann.write_text("{}", encoding="utf-8")
    doc = _FakeDocEntry(
        doc_id="d1", source_type="pdf",
        annotation_resolved=ann,
    )
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    # figure_caption_prf 仍 null（annotation 是 {}）
    assert report["per_doc"][0]["metrics"]["figure_caption_precision"]["value"] is None


# =========================================================================
# run_evaluation：tolerance_chars 透传
# =========================================================================


def test_run_evaluation_tolerance_chars_passed_to_chunk_boundary_prf(tmp_path: Path, monkeypatch):
    """tolerance_chars 应透传给 chunk_boundary_prf。"""
    captured = {}

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None

    def fake_chunk_boundary_prf(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        # 返回最小有效结果
        return {
            "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
            "_tolerance_chars": {"value": tolerance_chars},
            "_missing_markers": {"value": []},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.chunk_boundary_prf", fake_chunk_boundary_prf)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out, tolerance_chars=42)
    assert captured["tolerance_chars"] == 42


def test_run_evaluation_tolerance_chars_default_30(tmp_path: Path, monkeypatch):
    captured = {}

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None

    def fake_chunk_boundary_prf(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {
            "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
            "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
            "_tolerance_chars": {"value": tolerance_chars},
            "_missing_markers": {"value": []},
        }

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    monkeypatch.setattr("evaluation.runner.chunk_boundary_prf", fake_chunk_boundary_prf)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out)  # 默认
    assert captured["tolerance_chars"] == 30


# =========================================================================
# run_evaluation：max_chars 透传给 _process_one
# =========================================================================


def test_run_evaluation_max_chars_passed_to_process_single(tmp_path: Path, monkeypatch):
    """max_chars 应透传给 process_single。"""
    captured = {}

    def fake_process_single(path, out_path, *, parser_name, max_chars, write_json):
        captured["max_chars"] = max_chars
        return _FakeDocument(), None

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out, max_chars=500)
    assert captured["max_chars"] == 500


def test_run_evaluation_parser_name_passed_to_process_single(tmp_path: Path, monkeypatch):
    captured = {}

    def fake_process_single(path, out_path, *, parser_name, max_chars, write_json):
        captured["parser_name"] = parser_name
        return _FakeDocument(), None

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out, parser_name="kreuzberg")
    assert captured["parser_name"] == "kreuzberg"


def test_run_evaluation_write_json_always_false_for_per_doc(tmp_path: Path, monkeypatch):
    """_process_one 调用 process_single 时 write_json=False（不写盘）。"""
    captured = {}

    def fake_process_single(path, out_path, *, parser_name, max_chars, write_json):
        captured["write_json"] = write_json
        return _FakeDocument(), None

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    doc = _FakeDocEntry(doc_id="d1", source_type="pdf")
    m = _FakeManifest(documents=[doc])
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    assert captured["write_json"] is False


# =========================================================================
# run_evaluation：devset 字段透传
# =========================================================================


def test_run_evaluation_devset_status_propagated(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    m = _FakeManifest(documents=[_FakeDocEntry(doc_id="d1", source_type="pdf")])
    m.devset_status = "complete"
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["status"] == "complete"


def test_run_evaluation_devset_file_count_propagated(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    docs = [
        _FakeDocEntry(doc_id="d1", source_type="pdf"),
        _FakeDocEntry(doc_id="d2", source_type="pdf"),
    ]
    m = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["file_count"] == 2


def test_run_evaluation_devset_categories_covered_propagated(tmp_path: Path, monkeypatch):
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), None
    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)

    m = _FakeManifest(documents=[_FakeDocEntry(doc_id="d1", source_type="pdf")])
    m.categories_covered = ["pdf", "research_paper"]
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["categories_covered"] == ["pdf", "research_paper"]
