"""evaluation/runner.py 第二百零四轮 edges 测试（Round 740）。

补强 edges84/edges85 未触及的角度（第一百零五批）。

新角度：
- output_path 接受字符串（Path() 内部转换）
- 公开 per_doc 条目恰 4 键（doc_id/source_type/metrics/wall_time_seconds）
- 磁盘 JSON == 返回的内存 dict（e2e 往返一致）
- 落盘无 BOM（首字节 '{'）
- 真仓库 provenance.git_commit 是 40 位十六进制
- 同一 doc_id 同时出现在 documents 与 expected_failures：
  两次 process_single、stub 路径同名先后清理、ef 行 matches False
  （fake 返回成功无错误）
- _load_annotation OSError 分支（monkeypatch json.load 抛 OSError → None）
- forbidden tokens 第二百一十批
"""

from __future__ import annotations

import inspect
import io
import json
from pathlib import Path

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _load_annotation, run_evaluation

ROOT = Path(__file__).resolve().parents[1]


class _DocObj:
    source_hash = "h"
    parser_version = "pv"

    def to_dict(self):
        return {"document_id": "d", "source_type": "pdf",
                "elements": [], "chunks": []}


@pytest.fixture
def ps_capture(monkeypatch):
    calls = []

    def fake_ps(inp, out, parser_name="fallback", max_chars=800,
                write_json=False):
        calls.append(out.name)
        return _DocObj(), []
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    return calls


def _entry(i="d1"):
    return DocumentEntry(
        doc_id=i, path_str=f"{i}.pdf", resolved_path=ROOT / f"{i}.pdf",
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None)


# ---------- 路径与落盘 ----------

def test_output_path_string_coerced_batch54(ps_capture, tmp_path):
    out = str(tmp_path / "rs" / "rep.json")
    man = Manifest("1.0", "incomplete", (_entry(),), (), ROOT)
    run_evaluation(man, out)
    assert Path(out).is_file()


def test_public_per_doc_exact_four_keys_batch54(ps_capture, tmp_path):
    man = Manifest("1.0", "incomplete", (_entry(),), (), ROOT)
    rep = run_evaluation(man, tmp_path / "r.json")
    assert sorted(rep["per_doc"][0].keys()) == [
        "doc_id", "metrics", "source_type", "wall_time_seconds"]


def test_disk_equals_memory_roundtrip_batch54(ps_capture, tmp_path):
    out = tmp_path / "r.json"
    rep = run_evaluation(Manifest("1.0", "incomplete", (_entry(),), (), ROOT),
                         out)
    disk = json.loads(io.open(out, encoding="utf-8").read())
    assert disk == rep


def test_disk_no_bom_batch54(ps_capture, tmp_path):
    out = tmp_path / "r.json"
    run_evaluation(Manifest("1.0", "incomplete", (_entry(),), (), ROOT), out)
    with io.open(out, "rb") as f:
        assert f.read(1) == b"{"


def test_provenance_real_commit_40hex_batch54(ps_capture, tmp_path):
    rep = run_evaluation(
        Manifest("1.0", "incomplete", (_entry(),), (), ROOT),
        tmp_path / "r.json")
    gc = rep["provenance"]["git_commit"]
    assert gc is not None and len(gc) == 40
    int(gc, 16)  # 全十六进制


# ---------- doc_id 撞名 ----------

def test_same_doc_id_in_docs_and_failures_batch54(ps_capture, tmp_path):
    ef = ExpectedFailure(doc_id="d1", path_str="d1.pdf",
                         resolved_path=ROOT / "d1.pdf",
                         expected_error_code="open_error", source_type=None)
    man = Manifest("1.0", "incomplete", (_entry("d1"),), (ef,), ROOT)
    rep = run_evaluation(man, tmp_path / "r.json")
    # 文档循环 + ef 循环各跑一次，stub 同名
    assert ps_capture == ["d1.json", "d1.json"]
    row = rep["expected_failures"][0]
    assert row == {"doc_id": "d1", "expected_error_code": "open_error",
                   "actual_error_code": None, "matches": False}
    assert len(rep["per_doc"]) == 1


# ---------- _load_annotation OSError ----------

def test_load_annotation_oserror_branch_batch54(tmp_path, monkeypatch):
    f = tmp_path / "ann.json"
    f.write_text("{}", encoding="utf-8")

    def boom_load(fp):
        raise OSError("permission denied")
    monkeypatch.setattr(runner_mod.json, "load", boom_load)
    assert _load_annotation(f) is None


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_public_strip_keys_batch54():
    src = _src()
    assert '"_annotation_present": annotation is not None' in src
    assert "public_per_doc" in src


# ---------- forbidden tokens 第二百一十批 ----------

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
