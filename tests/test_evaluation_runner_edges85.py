"""evaluation/runner.py 第二百零三轮 edges 测试（Round 733）。

补强 edges82-84 未触及的角度（第九十八批）。

新角度：
- _load_annotation：目录 → None / 合法文件 → 原样 dict / None 路径 → None
- _process_one errors 优先级：document 与 errors 同时非空 → errors 胜出、
  parser_version None
- process_single 收到精确 kwargs（parser_name / max_chars / write_json=False）
- _per_doc 目录在 stub 未落盘时也创建
- 零文档 manifest：报告 6 键、per_doc/expected_failures 空、
  _per_doc 目录不创建、磁盘 JSON 无 tolerance 键（现状记录：
  _tolerance_chars 只进内部 per_doc_results，公开层剥离）
- ef-only manifest：精确匹配 dict；kwargs 与文档循环一致
- ef 用例无错误：actual_error_code None、matches False
- wall_time_seconds 精确 6 键 + not_instrumented
- report_version "1.1"；__all__ 单元素
- AST（_load_annotation / _process_one / run_evaluation）
- forbidden tokens 第二百零三批
"""

from __future__ import annotations

import ast
import collections
import inspect
import io
import json
from pathlib import Path

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _load_annotation, _process_one, run_evaluation

ROOT = Path(__file__).resolve().parents[1]


class _FakeDoc:
    doc_id = "x"
    resolved_path = Path("x.pdf")


class _FakeErr:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


class _FakeDocObj:
    source_hash = "h"
    parser_version = "pv"

    def to_dict(self):
        return {"ok": True}


def _entry(i="d1", ann=None, exp=None):
    return DocumentEntry(
        doc_id=i, path_str=f"{i}.pdf", resolved_path=ROOT / f"{i}.pdf",
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=ann, expectations=exp)


def _ef(i="ef1", code="open_error"):
    return ExpectedFailure(doc_id=i, path_str=f"{i}.pdf",
                           resolved_path=ROOT / f"{i}.pdf",
                           expected_error_code=code, source_type=None)


@pytest.fixture
def ps_capture(monkeypatch):
    calls = []

    def fake_ps(inp, out, parser_name="fallback", max_chars=800,
                write_json=False):
        calls.append({"inp": inp, "out": out, "parser_name": parser_name,
                      "max_chars": max_chars, "write_json": write_json})
        return _FakeDocObj(), [_FakeErr("open_error")]
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    return calls


# ---------- _load_annotation ----------

def test_load_annotation_directory_returns_none_batch54(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _load_annotation(sub) is None


def test_load_annotation_valid_file_batch54(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('{"chunk_boundary_anchors": []}', encoding="utf-8")
    assert _load_annotation(f) == {"chunk_boundary_anchors": []}


def test_load_annotation_none_path_batch54():
    assert _load_annotation(None) is None


# ---------- _process_one ----------

def test_process_one_errors_take_priority_batch54(ps_capture, tmp_path):
    r = _process_one(_FakeDoc(), tmp_path / "o", "kreuz", 500)
    document, error, _, parser_version, image_dir = r
    assert document is None
    assert error == {"code": "open_error", "message": "m"}
    assert parser_version is None
    assert image_dir is not None  # document 在 pipeline 内非 None，仍推导


def test_process_one_kwargs_exact_batch54(ps_capture, tmp_path):
    _process_one(_FakeDoc(), tmp_path / "o", "kreuz", 500)
    c = ps_capture[0]
    assert c["parser_name"] == "kreuz"
    assert c["max_chars"] == 500
    assert c["write_json"] is False
    assert c["out"] == tmp_path / "o" / "_per_doc" / "x.json"


def test_process_one_per_doc_dir_created_batch54(ps_capture, tmp_path):
    _process_one(_FakeDoc(), tmp_path / "o", "fallback", 800)
    assert (tmp_path / "o" / "_per_doc").is_dir()


# ---------- 零文档 manifest ----------

def test_zero_doc_report_structure_batch54(ps_capture, tmp_path):
    man = Manifest("1.0", "incomplete", (), (), ROOT)
    out = tmp_path / "r0" / "rep.json"
    rep = run_evaluation(man, out)
    assert sorted(rep.keys()) == ["devset", "expected_failures",
                                  "per_doc", "provenance",
                                  "report_version", "summary"]
    assert rep["per_doc"] == []
    assert rep["expected_failures"] == []
    assert not (tmp_path / "r0" / "_per_doc").exists()


def test_zero_doc_disk_has_no_tolerance_key_batch54(ps_capture, tmp_path):
    # 现状记录：_tolerance_chars 只进内部 per_doc_results，公开层剥离，
    # 磁盘报告不含任何 tolerance 记录
    man = Manifest("1.0", "incomplete", (), (), ROOT)
    out = tmp_path / "r0" / "rep.json"
    run_evaluation(man, out)
    raw = io.open(out, encoding="utf-8").read()
    assert "_tolerance_chars" not in raw
    assert "tolerance" not in raw


# ---------- expected_failures ----------

def test_ef_only_manifest_exact_result_batch54(ps_capture, tmp_path):
    man = Manifest("1.0", "incomplete", (), (_ef(),), ROOT)
    out = tmp_path / "r1" / "rep.json"
    rep = run_evaluation(man, out)
    assert rep["expected_failures"] == [{
        "doc_id": "ef1", "expected_error_code": "open_error",
        "actual_error_code": "open_error", "matches": True,
    }]
    assert ps_capture[0]["parser_name"] == "fallback"
    assert ps_capture[0]["write_json"] is False


def test_ef_no_error_matches_false_batch54(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runner_mod, "process_single",
        lambda *a, **k: (_FakeDocObj(), []))
    man = Manifest("1.0", "incomplete", (), (_ef(),), ROOT)
    rep = run_evaluation(man, tmp_path / "r2" / "rep.json")
    row = rep["expected_failures"][0]
    assert row["actual_error_code"] is None
    assert row["matches"] is False


# ---------- wall_time / 版本 ----------

def test_wall_time_exact_keys_batch54(ps_capture, tmp_path):
    man = Manifest("1.0", "incomplete", (_entry(),), (), ROOT)
    rep = run_evaluation(man, tmp_path / "r3" / "rep.json")
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert wt == {"total": wt["total"], "parse": None, "chunk": None,
                  "parse_reason": "not_instrumented",
                  "chunk_reason": "not_instrumented"}
    assert wt["total"] >= 0


def test_report_version_locked_batch54(ps_capture, tmp_path):
    man = Manifest("1.0", "incomplete", (), (), ROOT)
    rep = run_evaluation(man, tmp_path / "r4" / "rep.json")
    assert rep["report_version"] == "1.1"


# ---------- 源码与 AST ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_docstring_constraints_batch54():
    src = _src()
    assert "不复制 pipeline 逻辑" in src
    assert "not_instrumented" in src
    assert "write_json=False" in src


def test_source_perf_counter_count_batch54():
    assert _src().count("perf_counter") == 3  # 导入 + 2 次调用


def test_all_export_single_element_batch54():
    assert runner_mod.__all__ == ["run_evaluation"]


def _func(name: str) -> ast.FunctionDef:
    tree = ast.parse(inspect.getsource(runner_mod))
    return next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> collections.Counter:
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_load_annotation_batch54():
    c = _counts(_func("_load_annotation"))
    assert (c["If"], c["Try"], c["ExceptHandler"], c["Return"],
            c["BoolOp"], c["With"]) == (1, 1, 1, 3, 1, 1)


def test_ast_process_one_batch54():
    c = _counts(_func("_process_one"))
    assert (c["If"], c["Try"], c["ExceptHandler"], c["Return"],
            c["Call"], c["Tuple"]) == (4, 1, 1, 3, 9, 7)


def test_ast_run_evaluation_batch54():
    c = _counts(_func("run_evaluation"))
    assert (c["If"], c["For"], c["BoolOp"], c["Call"], c["With"],
            c["Dict"]) == (2, 3, 2, 26, 1, 5)


# ---------- forbidden tokens 第二百零三批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch54():
    assert _src().count("open(") == 2  # path.open / out_p.open
