"""evaluation/runner.py 第二百零一轮 edges 测试（Round 719）。

补强 edges81/edges82 未触及的角度（第八十四批）。

新角度：
- process_single 抛异常不被 _process_one 捕获（RuntimeError 直接冒泡）
- elapsed 真实计时（sleep 0.05 → elapsed >= 0.05）
- 多 errors 只取 errors[0].to_dict()
- document None 且 errors 空 → code "unknown" + 固定 message
- image_dir 派生走 image_output_dir_for(out_stub, source_hash)（document None → None）
- stub 文件被 _process_one 清理；Windows 打开句柄下 unlink 失败被吞（PermissionError ⊂ OSError）
- e2e：error doc 公共指标 pipeline_success False + error_code 透传
- e2e：首个非空 parser_version 进 provenance（None→后补 / 先到先得）
- e2e：annotation JSON 真实加载并传给 chunk_boundary_prf（含 tolerance_chars 透传）
- e2e：私有键 _tolerance_chars/_missing_markers 被 pop，不泄漏进 per_doc metrics
- e2e：ef match/mismatch + actual_error_code 记录；_per_doc 目录共享创建
- AST（_load_annotation If1·Try1·Return3 / _process_one If4·Try1·Return3·AnnAssign1 / run_evaluation If2·Try1·Return1·AnnAssign3）
- 源码补强（perf_counter×2 / write_json=False×4 / .json"×2 / mkdir×2 / not_instrumented×2 / image_base_dir 条件行）
- forbidden tokens 第一百八十九批
"""

from __future__ import annotations

import ast
import inspect
import json
import time

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- 构造工具 ----------

class _Err:
    def __init__(self, code: str, message: str = "m"):
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


class _FakeDoc:
    def __init__(self, parser_version: str = "7.7", source_hash: str = "a" * 64):
        self.parser_version = parser_version
        self.source_hash = source_hash

    def to_dict(self) -> dict:
        return {"document_id": "d", "elements": [], "chunks": []}


def _entry(doc_id, resolved, source_type="pdf", annotation_resolved=None,
           expectations=None) -> DocumentEntry:
    return DocumentEntry(
        doc_id=doc_id, path_str=f"{doc_id}.pdf", resolved_path=resolved,
        source_type=source_type, sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=annotation_resolved,
        expectations=expectations,
    )


def _ef(doc_id, resolved, code) -> ExpectedFailure:
    return ExpectedFailure(doc_id=doc_id, path_str=f"{doc_id}.bin",
                           resolved_path=resolved, expected_error_code=code,
                           source_type="other")


def _manifest(tmp_path, docs=(), efs=()) -> Manifest:
    return Manifest(manifest_version="1.0", devset_status="incomplete",
                    documents=tuple(docs), expected_failures=tuple(efs),
                    project_root=tmp_path)


# ---------- _process_one 异常传播 ----------

def test_process_single_exception_propagates_batch53(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("ps crashed")
    monkeypatch.setattr(runner_mod, "process_single", boom)
    doc = _entry("d1", tmp_path / "d1.pdf")
    with pytest.raises(RuntimeError, match="ps crashed"):
        _process_one(doc, tmp_path / "out", "fallback", 800)


# ---------- 真实计时 ----------

def test_elapsed_measures_real_time_batch53(tmp_path, monkeypatch):
    def slow(*a, **k):
        time.sleep(0.05)
        return _FakeDoc(), []
    monkeypatch.setattr(runner_mod, "process_single", slow)
    doc = _entry("d1", tmp_path / "d1.pdf")
    document, error, elapsed, version, image_dir = _process_one(
        doc, tmp_path / "out", "fallback", 800)
    assert document == {"document_id": "d", "elements": [], "chunks": []}
    assert error is None
    assert elapsed >= 0.05
    assert version == "7.7"
    assert image_dir is not None


# ---------- errors 分支 ----------

def test_first_error_dict_used_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (None, [_Err("E1"), _Err("E2")]))
    doc = _entry("d1", tmp_path / "d1.pdf")
    document, error, _, version, _ = _process_one(doc, tmp_path / "out", "fallback", 800)
    assert document is None
    assert error == {"code": "E1", "message": "m"}
    assert version is None


def test_document_none_without_errors_unknown_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "process_single", lambda *a, **k: (None, []))
    doc = _entry("d1", tmp_path / "d1.pdf")
    document, error, _, version, image_dir = _process_one(
        doc, tmp_path / "out", "fallback", 800)
    assert document is None
    assert error == {"code": "unknown",
                     "message": "process_single returned None without errors"}
    assert version is None
    assert image_dir is None


# ---------- image_dir 派生 ----------

def test_image_dir_from_helper_batch53(tmp_path, monkeypatch):
    captured = {}

    def fake_ps(*a, **k):
        return _FakeDoc(source_hash="b" * 64), []

    def fake_helper(stub, source_hash):
        captured["stub"] = stub
        captured["hash"] = source_hash
        return tmp_path / "imgs"
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    monkeypatch.setattr(runner_mod, "image_output_dir_for", fake_helper)
    doc = _entry("d1", tmp_path / "d1.pdf")
    *_, image_dir = _process_one(doc, tmp_path / "out", "fallback", 800)
    assert image_dir == tmp_path / "imgs"
    assert captured["stub"] == tmp_path / "out" / "_per_doc" / "d1.json"
    assert captured["hash"] == "b" * 64


# ---------- stub 清理 ----------

def test_stub_written_by_pipeline_gets_unlinked_batch53(tmp_path, monkeypatch):
    def fake_ps(input_path, output_path, **k):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("{}", encoding="utf-8")
        return _FakeDoc(), []
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    doc = _entry("d1", tmp_path / "d1.pdf")
    _process_one(doc, tmp_path / "out", "fallback", 800)
    assert not (tmp_path / "out" / "_per_doc" / "d1.json").is_file()


def test_unlink_failure_swallowed_batch53(tmp_path, monkeypatch):
    import os
    if os.name != "nt":
        pytest.skip("Windows share-mode unlink 行为专属")
    monkeypatch.setattr(runner_mod, "process_single", lambda *a, **k: (None, []))
    stub_dir = tmp_path / "out" / "_per_doc"
    stub_dir.mkdir(parents=True)
    stub = stub_dir / "d1.json"
    stub.write_text("x", encoding="utf-8")
    doc = _entry("d1", tmp_path / "d1.pdf")
    fh = open(stub, "r", encoding="utf-8")  # Windows 下句柄未共享删除
    try:
        _, error, _, _, _ = _process_one(doc, tmp_path / "out", "fallback", 800)
        assert stub.is_file()  # unlink 失败被吞掉
        assert error["code"] == "unknown"
    finally:
        fh.close()
        stub.unlink(missing_ok=True)


# ---------- e2e：error doc 公共指标 ----------

def _patch_prf_noop(monkeypatch):
    monkeypatch.setattr(runner_mod, "figure_caption_prf", lambda d, a: {})
    monkeypatch.setattr(runner_mod, "chunk_boundary_prf",
                        lambda d, a, *, tolerance_chars: {})


def test_run_error_doc_metrics_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (None, [_Err("E1")]))
    _patch_prf_noop(monkeypatch)
    m = _manifest(tmp_path, docs=[_entry("d1", tmp_path / "d1.pdf")])
    out = tmp_path / "out" / "report.json"
    report = run_evaluation(m, out)
    entry = report["per_doc"][0]
    assert list(entry.keys()) == ["doc_id", "source_type", "metrics",
                                  "wall_time_seconds"]
    assert entry["metrics"]["pipeline_success"]["value"] is False
    assert entry["metrics"]["error_code"]["value"] == "E1"
    assert (tmp_path / "out" / "_per_doc").is_dir()


# ---------- e2e：parser_version 进 provenance ----------

def test_parser_version_first_nonempty_wins_batch53(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_ps(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            return None, [_Err("E")]
        return _FakeDoc(parser_version="7.7"), []
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    _patch_prf_noop(monkeypatch)
    docs = [_entry("a", tmp_path / "a.pdf"), _entry("b", tmp_path / "b.pdf")]
    report = run_evaluation(_manifest(tmp_path, docs=docs),
                            tmp_path / "out" / "r.json")
    assert report["provenance"]["parser_version"] == "7.7"


def test_parser_version_first_wins_over_second_batch53(tmp_path, monkeypatch):
    versions = ["1.1", "2.2"]

    def fake_ps(*a, **k):
        v = versions.pop(0)
        return _FakeDoc(parser_version=v), []
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    _patch_prf_noop(monkeypatch)
    docs = [_entry("a", tmp_path / "a.pdf"), _entry("b", tmp_path / "b.pdf")]
    report = run_evaluation(_manifest(tmp_path, docs=docs),
                            tmp_path / "out" / "r.json")
    assert report["provenance"]["parser_version"] == "1.1"


def test_wall_time_not_instrumented_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (_FakeDoc(), []))
    _patch_prf_noop(monkeypatch)
    m = _manifest(tmp_path, docs=[_entry("a", tmp_path / "a.pdf")])
    report = run_evaluation(m, tmp_path / "out" / "r.json")
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert list(wt.keys()) == ["total", "parse", "chunk",
                               "parse_reason", "chunk_reason"]
    assert wt["total"] >= 0.0
    assert wt["parse"] is None and wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


# ---------- e2e：annotation 真实加载 + tolerance 透传 ----------

def test_annotation_loaded_and_tolerance_passed_batch53(tmp_path, monkeypatch):
    ann = tmp_path / "ann.json"
    ann.write_text('{"marker_style": "verbatim"}', encoding="utf-8")
    captured = []
    monkeypatch.setattr(runner_mod, "figure_caption_prf", lambda d, a: {})
    monkeypatch.setattr(
        runner_mod, "chunk_boundary_prf",
        lambda d, a, *, tolerance_chars: captured.append((a, tolerance_chars)) or {})
    docs = [_entry("a", tmp_path / "a.pdf", annotation_resolved=ann),
            _entry("b", tmp_path / "b.pdf", annotation_resolved=None)]
    run_evaluation(_manifest(tmp_path, docs=docs), tmp_path / "out" / "r.json",
                   tolerance_chars=7)
    assert captured == [({"marker_style": "verbatim"}, 7), (None, 7)]


def test_private_keys_popped_from_metrics_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (_FakeDoc(), []))
    monkeypatch.setattr(
        runner_mod, "figure_caption_prf",
        lambda d, a: {"figure_caption_precision": {"value": None, "reason": "x"}})

    def fake_cb(document, annotation, *, tolerance_chars):
        return {
            "chunk_boundary_precision": {"value": None, "reason": "y"},
            "_tolerance_chars": {"value": 30},
            "_missing_markers": {"value": ["m1"]},
        }
    monkeypatch.setattr(runner_mod, "chunk_boundary_prf", fake_cb)
    m = _manifest(tmp_path, docs=[_entry("a", tmp_path / "a.pdf")])
    report = run_evaluation(m, tmp_path / "out" / "r.json")
    metrics = report["per_doc"][0]["metrics"]
    assert metrics["chunk_boundary_precision"]["reason"] == "y"
    assert metrics["figure_caption_precision"]["reason"] == "x"
    assert "_tolerance_chars" not in metrics
    assert "_missing_markers" not in metrics


# ---------- e2e：expected_failures ----------

def test_ef_match_and_mismatch_batch53(tmp_path, monkeypatch):
    def fake_ps(input_path, output_path, **k):
        return None, [_Err("unsupported")]
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    _patch_prf_noop(monkeypatch)
    efs = [_ef("ef1", tmp_path / "bad1.bin", "unsupported"),
           _ef("ef2", tmp_path / "bad2.bin", "other")]
    report = run_evaluation(_manifest(tmp_path, efs=efs),
                            tmp_path / "out" / "r.json")
    results = report["expected_failures"]
    assert [list(r.keys()) for r in results] == [
        ["doc_id", "expected_error_code", "actual_error_code", "matches"]] * 2
    assert results[0] == {"doc_id": "ef1", "expected_error_code": "unsupported",
                          "actual_error_code": "unsupported", "matches": True}
    assert results[1]["actual_error_code"] == "unsupported"
    assert results[1]["matches"] is False
    leftovers = list((tmp_path / "out" / "_per_doc").glob("*.json"))
    assert leftovers == []


def test_ef_success_actual_code_none_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (_FakeDoc(), []))
    _patch_prf_noop(monkeypatch)
    report = run_evaluation(_manifest(tmp_path, efs=[_ef("ef1", tmp_path / "b.bin", "x")]),
                            tmp_path / "out" / "r.json")
    assert report["expected_failures"][0]["actual_error_code"] is None
    assert report["expected_failures"][0]["matches"] is False


# ---------- 报告写盘 ----------

def test_report_written_matches_returned_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (_FakeDoc(), []))
    _patch_prf_noop(monkeypatch)
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(_manifest(tmp_path, docs=[_entry("a", tmp_path / "a.pdf")]),
                            out)
    assert json.loads(out.read_text(encoding="utf-8")) == report
    assert list(report.keys()) == ["report_version", "provenance", "devset",
                                   "summary", "per_doc", "expected_failures"]


# ---------- _load_annotation 补充 ----------

def test_load_annotation_directory_returns_none_batch53(tmp_path):
    assert _load_annotation(tmp_path) is None  # 目录非 is_file


def test_load_annotation_oserror_swallowed_batch53(tmp_path, monkeypatch):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(p.__class__, "open",
                        lambda self, *a, **k: (_ for _ in ()).throw(OSError("denied")))
    assert _load_annotation(p) is None


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_counter_counts_batch53():
    src = _src()
    assert src.count("time.perf_counter()") == 2
    assert src.count("write_json=False") == 4  # 2 处代码 + 2 处 docstring
    assert src.count('.json"') == 2


def test_source_mkdir_twice_batch53():
    assert _src().count("out_stub.parent.mkdir(parents=True, exist_ok=True)") == 2


def test_source_not_instrumented_lines_batch53():
    src = _src()
    assert '"parse_reason": "not_instrumented",' in src
    assert '"chunk_reason": "not_instrumented",' in src


def test_source_key_lines_batch53():
    src = _src()
    assert "errors[0].to_dict()" in src
    assert '"process_single returned None without errors"' in src
    assert "doc.annotation_resolved" in src
    assert "ef.resolved_path" in src
    assert "image_base_dir=image_dir if (image_dir is not None and image_dir.is_dir()) else None" in src
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(runner_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_load_annotation_structure_batch53():
    c = _counts(_func("_load_annotation"))
    assert (c["If"], c["Try"], c["Return"], c["AnnAssign"]) == (1, 1, 3, 0)


def test_ast_process_one_structure_batch53():
    c = _counts(_func("_process_one"))
    assert (c["If"], c["Try"], c["Return"], c["AnnAssign"]) == (4, 1, 3, 1)


def test_ast_run_evaluation_structure_batch53():
    c = _counts(_func("run_evaluation"))
    assert (c["If"], c["Try"], c["Return"], c["AnnAssign"]) == (2, 1, 1, 3)


def test_ast_process_one_annassign_target_batch53():
    fn = _func("_process_one")
    anns = [n.target.id for n in ast.walk(fn)
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)]
    assert anns == ["image_dir"]


# ---------- forbidden tokens 第一百八十九批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch53():
    assert _src().count("open(") == 2
