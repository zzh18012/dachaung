"""evaluation/runner.py 第二百零七轮 edges 测试（Round 761）。

补强 edges85-88 未触及的角度（第一百二十五批）。

新角度：
- _per_doc stub 的 unlink 抛 OSError 被吞：评测照常完成、stub 文件留盘
- 深层嵌套输出路径 a/b/c/r.json 自动建目录
- wall_time_seconds["total"] 是 float 且 >= 0（真实 perf_counter 计时）
- 失败文档 metrics 恰 20 键：14 个 pipeline_failed 系 +
  figure_caption_* 三键 parser_does_not_emit_relations +
  chunk_boundary_* 三键 pipeline_failed（f1 也是 pipeline_failed）
- ef 多条目顺序原样保留（e2 在前 e1 在后），matches 各自判定
- process_single 抛 RuntimeError → 直接冒泡（无 try 包裹）
- devset_status "complete" 经 build_devset_section 原样进报告
- forbidden tokens 第二百三十一批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import run_evaluation

ROOT = Path(__file__).resolve().parents[1]


class _Doc:
    source_hash = "h"
    parser_version = "pv"

    def to_dict(self):
        return {"document_id": "x", "source_type": "pdf", "elements": [],
                "chunks": [{"text": "AB"}, {"text": "CD"}]}


class _Err:
    def __init__(self, c="open_error"):
        self.code = c

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _entry(i):
    return DocumentEntry(i, f"{i}.pdf", ROOT / f"{i}.pdf", "pdf", None, (),
                         None, None, None, None)


def _ef(i, c):
    return ExpectedFailure(i, f"{i}.pdf", ROOT / f"{i}.pdf", c, None)


def _install(monkeypatch, ps):
    def fake_bp(**k):
        return {"git_commit": None, "git_dirty": False,
                "evaluator_version": "1.1", "report_version": "1.1",
                "parser_name": "f", "parser_version": None,
                "dependencies": {}, "max_chars": 800,
                "run_timestamp_iso": "t"}

    monkeypatch.setattr(runner_mod, "process_single", ps)
    monkeypatch.setattr(runner_mod, "build_provenance", fake_bp)


@pytest.fixture
def tmp():
    return Path(tempfile.mkdtemp())


# ---------- unlink OSError 吞掉 ----------

def test_stub_unlink_oserror_ignored_batch54(monkeypatch, tmp):
    def ps(inp, out, **k):
        out.write_text("{}", encoding="utf-8")
        return _Doc(), []

    _install(monkeypatch, ps)
    real_unlink = Path.unlink

    def boom(self, *a, **k):
        if self.parent.name == "_per_doc":
            raise OSError("locked")
        return real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", boom)
    rep = run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (), ROOT),
                         tmp / "r1.json")
    assert rep["per_doc"][0]["doc_id"] == "d1"
    # stub 清理失败 → 留在盘上
    assert (tmp / "_per_doc" / "d1.json").is_file()


# ---------- 深层输出 ----------

def test_deep_nested_output_created_batch54(monkeypatch, tmp):
    _install(monkeypatch, lambda inp, out, **k: (_Doc(), []))
    deep = tmp / "a" / "b" / "c" / "r.json"
    run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (), ROOT), deep)
    assert deep.is_file()


# ---------- wall_time ----------

def test_wall_time_total_float_nonneg_batch54(monkeypatch, tmp):
    _install(monkeypatch, lambda inp, out, **k: (_Doc(), []))
    rep = run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (), ROOT),
                         tmp / "r.json")
    total = rep["per_doc"][0]["wall_time_seconds"]["total"]
    assert isinstance(total, float)
    assert total >= 0


# ---------- 失败文档 20 键 ----------

def test_failed_doc_metrics_twenty_keys_batch54(monkeypatch, tmp):
    _install(monkeypatch, lambda inp, out, **k: (None, [_Err()]))
    rep = run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (), ROOT),
                         tmp / "r.json")
    metrics = rep["per_doc"][0]["metrics"]
    assert len(metrics) == 20
    assert metrics["figure_caption_f1"]["reason"] == \
        "parser_does_not_emit_relations"
    assert metrics["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert metrics["chunk_boundary_f1"]["reason"] == "pipeline_failed"
    assert metrics["element_count_total"]["reason"] == "pipeline_failed"


# ---------- ef 顺序 ----------

def test_ef_order_preserved_batch54(monkeypatch, tmp):
    def ps(inp, out, **k):
        if str(inp).endswith("e1.pdf"):
            return None, [_Err("c1")]
        if str(inp).endswith("e2.pdf"):
            return None, [_Err("cx")]
        return _Doc(), []

    _install(monkeypatch, ps)
    man = Manifest("1.0", "i", (), (_ef("e2", "c2"), _ef("e1", "c1")),
                   ROOT)
    rep = run_evaluation(man, tmp / "r.json")
    assert [(r["doc_id"], r["matches"])
            for r in rep["expected_failures"]] == [("e2", False),
                                                   ("e1", True)]


# ---------- process_single 异常冒泡 ----------

def test_process_single_exception_propagates_batch54(monkeypatch, tmp):
    def bad(inp, out, **k):
        raise RuntimeError("boom")

    _install(monkeypatch, bad)
    with pytest.raises(RuntimeError):
        run_evaluation(Manifest("1.0", "i", (_entry("d1"),), (), ROOT),
                       tmp / "r.json")


# ---------- devset status 透传 ----------

def test_devset_status_complete_passthrough_batch54(monkeypatch, tmp):
    _install(monkeypatch, lambda inp, out, **k: (_Doc(), []))
    rep = run_evaluation(Manifest("1.0", "complete", (_entry("d1"),), (),
                                  ROOT), tmp / "r.json")
    assert rep["devset"]["status"] == "complete"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_unlink_and_mkdir_batch54():
    src = _src()
    assert src.count("unlink()") == 2
    assert src.count("mkdir(parents=True, exist_ok=True)") == 4


# ---------- forbidden tokens 第二百三十一批 ----------

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
