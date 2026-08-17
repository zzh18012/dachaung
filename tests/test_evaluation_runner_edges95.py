"""evaluation/runner.py 第二百四十七轮 edges 测试（Round 803）。

补强 edges94 未触及的角度（第一百六十七批）。

新角度：
- wall_time_seconds.total >= 0（perf_counter 实测）且
  parse None + parse_reason not_instrumented
- per_doc metrics 键尾 6 个恰为 figure 3 + chunk 3 顺序
  （metrics.update(fig_caps) 先于 chunk_b）
- 中文 doc_id 原样落盘（ensure_ascii=False，无 \\u 转义）
- output_path 传 str 与 Path 等价
- doc_id 含斜杠 "a/b" → stub 路径嵌套 mkdir 出 _per_doc/a/
  目录、stub 本身被清理（runner 不校验 doc_id 字符）
- forbidden tokens 第二百七十三批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "1.0"
    source_hash = "h"

    def to_dict(self):
        return {"elements": [
            {"element_id": "e1", "type": "paragraph", "content": "A"},
            {"element_id": "e2", "type": "paragraph", "content": "B"}],
            "chunks": [
                {"text": "A", "source_element_ids": ["e1"]},
                {"text": "B", "source_element_ids": ["e2"]}]}


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _de(root, did):
    return DocumentEntry(did, "s/a.pdf", root / "s/a.pdf", "pdf",
                         None, (), None, None, None, None)


def _prov(**k):
    return {"git_commit": "c", "git_dirty": False}


def _run(tmp, root, entries):
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        return run_evaluation(
            Manifest("1.0", "incomplete", entries, (), root),
            tmp / "r.json")


# ---------- wall_time 与键序 ----------

def test_wall_time_and_metrics_tail_order_batch54():
    tmp, root = _env()
    rep = _run(tmp, root, (_de(root, "d1"),))
    m = rep["per_doc"][0]
    assert m["wall_time_seconds"]["total"] >= 0
    assert m["wall_time_seconds"]["parse"] is None
    assert m["wall_time_seconds"]["parse_reason"] == \
        "not_instrumented"
    assert list(m["metrics"].keys())[-6:] == [
        "figure_caption_precision", "figure_caption_recall",
        "figure_caption_f1", "chunk_boundary_precision",
        "chunk_boundary_recall", "chunk_boundary_f1"]


# ---------- 中文 doc_id 原样落盘 ----------

def test_chinese_doc_id_unescaped_batch54():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "中文"),),
                     (), root), str(tmp / "r.json"))
    assert rep["per_doc"][0]["doc_id"] == "中文"
    raw = (tmp / "r.json").read_text(encoding="utf-8")
    assert "中文" in raw
    assert "\\u4e2d" not in raw


# ---------- 斜杠 doc_id ----------

def test_slash_doc_id_nested_stub_dir_batch54():
    tmp, root = _env()
    _run(tmp, root, (_de(root, "a/b"),))
    assert (tmp / "_per_doc" / "a").is_dir()
    assert not (tmp / "_per_doc" / "a" / "b.json").is_file()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_update_order_batch54():
    src = _src()
    assert "metrics.update(fig_caps)" in src
    assert "metrics.update(chunk_b)" in src
    assert src.index("metrics.update(fig_caps)") < \
        src.index("metrics.update(chunk_b)")
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


# ---------- forbidden tokens 第二百七十三批 ----------

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
