"""evaluation/runner.py 第二百零六轮 edges 测试（Round 754）。

补强 edges85-87 未触及的角度（第一百一十九批）。

新角度：
- parser_version 传播：首个真值胜出（v1/v2 → v1；None/v2 → v2）
- image_base_dir 门控：image_dir 非目录 → 传 None；真目录 → 传 Path
  （monkeypatch image_output_dir_for + 捕获 compute_automatic_metrics 入参）
- ef 循环调用参数精确：（ef 路径, "fallback", 800, False）
- macro 聚合 e2e：marker 命中 P=1.0 与 marker 落空 P=0.0（参与分母）
  → macro 0.5 / participating 2 —— 落空 marker 的 precision 是 0.0 不是 null
- 标注文件形态：空 list（falsy）→ no_annotation；非空 list → annotation.get
  AttributeError 直接冒泡（未守卫，现状记录）；空文件 → JSONDecodeError
  → None → no_annotation
- document 非 None + errors 非空：metrics 收 document=None 但 image_base_dir
  仍是真目录（image_dir 在 errors 检查前算好）、pipeline_success False
- unicode doc_id 原样落盘（ensure_ascii=False，无 \\u 转义）
- forbidden tokens 第二百二十四批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import run_evaluation

ROOT = Path(__file__).resolve().parents[1]


class _Doc:
    def __init__(self, pv="pv"):
        self.source_hash = "h"
        self.parser_version = pv

    def to_dict(self):
        return {"document_id": "x", "source_type": "pdf", "elements": [],
                "chunks": [{"text": "AB"}, {"text": "CD"}]}


class _Err:
    def __init__(self, c="open_error"):
        self.code = c

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _entry(i, ann=None):
    return DocumentEntry(i, f"{i}.pdf", ROOT / f"{i}.pdf", "pdf", None, (),
                         None, None, ann, None)


def _ef(i="e1"):
    return ExpectedFailure(i, f"{i}.pdf", ROOT / f"{i}.pdf",
                           "open_error", None)


def _install(monkeypatch, results, ef_result=(None, [_Err()])):
    calls = []

    def fake_ps(inp, out, parser_name="fallback", max_chars=800,
                write_json=False):
        calls.append((inp, parser_name, max_chars, write_json))
        if str(inp).endswith("e1.pdf"):
            return ef_result
        return results.pop(0)

    def fake_bp(**k):
        return {"git_commit": None, "git_dirty": False,
                "evaluator_version": "1.1", "report_version": "1.1",
                "parser_name": k["parser_name"],
                "parser_version": k["parser_version"],
                "dependencies": {}, "max_chars": 800,
                "run_timestamp_iso": "t"}

    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    monkeypatch.setattr(runner_mod, "build_provenance", fake_bp)
    return calls


@pytest.fixture
def tmp():
    return Path(tempfile.mkdtemp())


# ---------- parser_version 传播 ----------

def test_parser_version_first_truthy_wins_batch54(monkeypatch, tmp):
    _install(monkeypatch, [(_Doc("v1"), []), (_Doc("v2"), [])])
    man = Manifest("1.0", "i", (_entry("d1"), _entry("d2")), (), ROOT)
    rep = run_evaluation(man, tmp / "a.json")
    assert rep["provenance"]["parser_version"] == "v1"


def test_parser_version_none_then_value_batch54(monkeypatch, tmp):
    _install(monkeypatch, [(_Doc(None), []), (_Doc("v2"), [])])
    man = Manifest("1.0", "i", (_entry("d1"), _entry("d2")), (), ROOT)
    rep = run_evaluation(man, tmp / "b.json")
    assert rep["provenance"]["parser_version"] == "v2"


# ---------- image_base_dir 门控 ----------

def test_image_base_dir_gated_by_is_dir_batch54(monkeypatch, tmp):
    _install(monkeypatch, [(_Doc(), []), (_Doc(), [])])
    monkeypatch.setattr(runner_mod, "image_output_dir_for",
                        lambda stub, h: tmp / "nothere")
    captured = {}
    orig = runner_mod.compute_automatic_metrics

    def cam(**k):
        captured.setdefault("v", []).append(k.get("image_base_dir"))
        return orig(**k)

    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", cam)
    man = Manifest("1.0", "i", (_entry("d1"), _entry("d2")), (), ROOT)
    run_evaluation(man, tmp / "c.json")
    assert captured["v"] == [None, None]


def test_image_base_dir_real_dir_passed_batch54(monkeypatch, tmp):
    real = tmp / "imgs"
    real.mkdir()
    _install(monkeypatch, [(_Doc(), [])])
    monkeypatch.setattr(runner_mod, "image_output_dir_for",
                        lambda stub, h: real)
    captured = {}
    orig = runner_mod.compute_automatic_metrics

    def cam(**k):
        captured["v"] = k.get("image_base_dir")
        return orig(**k)

    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", cam)
    run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (), ROOT),
                   tmp / "d.json")
    assert captured["v"] == real


# ---------- ef 调用参数 ----------

def test_ef_loop_call_args_batch54(monkeypatch, tmp):
    calls = _install(monkeypatch, [(_Doc(), [])])
    run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (_ef(),), ROOT),
                   tmp / "e.json")
    ef_call = calls[1]
    assert str(ef_call[0]).endswith("e1.pdf")
    assert ef_call[1:] == ("fallback", 800, False)


# ---------- macro 聚合 e2e ----------

def test_macro_average_hit_and_miss_batch54(monkeypatch, tmp):
    ann1 = tmp / "a1.json"
    ann1.write_text(json.dumps(
        {"chunk_boundary_anchors": [{"marker": "AB"}]}), encoding="utf-8")
    ann2 = tmp / "a2.json"
    ann2.write_text(json.dumps(
        {"chunk_boundary_anchors": [{"marker": "ZZ"}]}), encoding="utf-8")
    _install(monkeypatch, [(_Doc(), []), (_Doc(), [])])
    man = Manifest("1.0", "i", (_entry("d1", ann=ann1),
                                 _entry("d2", ann=ann2)), (), ROOT)
    rep = run_evaluation(man, tmp / "f.json")
    assert rep["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {"macro_average": 0.5,
                                        "participating_docs": 2,
                                        "not_evaluated": 0}
    assert rep["per_doc"][0]["metrics"]["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert rep["per_doc"][1]["metrics"]["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}


# ---------- 标注文件形态 ----------

def test_annotation_empty_list_falsy_no_annotation_batch54(monkeypatch, tmp):
    ann = tmp / "ann.json"
    ann.write_text("[]", encoding="utf-8")
    _install(monkeypatch, [(_Doc(), [])])
    rep = run_evaluation(Manifest("1.0", "i", (_entry("d1", ann=ann),),
                                  (), ROOT), tmp / "g.json")
    assert rep["per_doc"][0]["metrics"]["chunk_boundary_precision"] == {
        "value": None, "reason": "no_annotation"}


def test_annotation_nonempty_list_crashes_batch54(monkeypatch, tmp):
    ann = tmp / "ann.json"
    ann.write_text("[1]", encoding="utf-8")
    _install(monkeypatch, [(_Doc(), [])])
    with pytest.raises(AttributeError):
        run_evaluation(Manifest("1.0", "i", (_entry("d1", ann=ann),),
                                (), ROOT), tmp / "h.json")


def test_annotation_empty_file_none_batch54(monkeypatch, tmp):
    ann = tmp / "ann.json"
    ann.write_text("", encoding="utf-8")
    _install(monkeypatch, [(_Doc(), [])])
    rep = run_evaluation(Manifest("1.0", "i", (_entry("d1", ann=ann),),
                                  (), ROOT), tmp / "i.json")
    assert rep["per_doc"][0]["metrics"]["chunk_boundary_precision"] == {
        "value": None, "reason": "no_annotation"}


# ---------- document + errors 并存 ----------

def test_doc_with_errors_metrics_none_image_dir_kept_batch54(
        monkeypatch, tmp):
    real = tmp / "imgs2"
    real.mkdir()
    captured = {}
    orig = runner_mod.compute_automatic_metrics

    def cam(**k):
        captured["doc"] = k.get("document")
        captured["ibd"] = k.get("image_base_dir")
        return orig(**k)

    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", cam)
    monkeypatch.setattr(runner_mod, "image_output_dir_for",
                        lambda stub, h: real)
    _install(monkeypatch, [(_Doc(), [_Err()])])
    rep = run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (), ROOT),
                         tmp / "j.json")
    assert captured["doc"] is None
    assert captured["ibd"] == real
    assert rep["per_doc"][0]["metrics"]["pipeline_success"] == {
        "value": False, "reason": None}
    assert rep["per_doc"][0]["metrics"]["error_code"] == {
        "value": "open_error", "reason": None}


# ---------- unicode doc_id 落盘 ----------

def test_unicode_doc_id_written_raw_batch54(monkeypatch, tmp):
    _install(monkeypatch, [(_Doc(), [])])
    u = DocumentEntry("文档1", "a.pdf", ROOT / "a.pdf", "pdf", None, (),
                      None, None, None, None)
    out = tmp / "k.json"
    run_evaluation(Manifest("1.0", "i", (u,), (), ROOT), out)
    raw = out.read_text(encoding="utf-8")
    assert "文档1" in raw
    assert "\\u6587" not in raw
    assert json.loads(raw)["per_doc"][0]["doc_id"] == "文档1"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_gating_and_pop_batch54():
    src = _src()
    assert "image_dir.is_dir()) else None" in src
    assert "chunk_b.pop(\"_tolerance_chars\", None)" in src
    assert "ensure_ascii=False" in src
    assert "if parser_version and not parser_version_for_prov:" in src


# ---------- forbidden tokens 第二百二十四批 ----------

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
    assert _src().count("open(") == 2
