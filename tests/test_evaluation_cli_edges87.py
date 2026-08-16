"""evaluation/cli.py 第一百零六轮 edges 测试（Round 748）。

补强 edges85/edges86 未触及的角度（第一百一十三批）。

新角度：
- run 全链路 e2e：真 manifest 文件 + 假 pipeline → rc 0、
  stdout "documents=1（成功 1，失败 0）"、真报告落盘
- validate-report 吃 run 产出的真报告 → rc 0（闭环）
- inspect-doc 排序分组边界：dict 指标（element_count_by_type）
  在数值组之后、null 组之前（4 组序 0bool/1num/2other/3null）
- _format_metric 超长名（40 字符）：不截断、仅单个分隔空格
- --tolerance-chars 负值被 argparse 接受并透传（type=int 无下限）
- main 接受元组 argv（argparse 任意可迭代）
- forbidden tokens 第二百一十八批
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
from pathlib import Path

import pytest

import evaluation.cli as cli_mod
import evaluation.runner as runner_mod
from evaluation.cli import _format_metric, main

ROOT = Path(__file__).resolve().parents[1]


class _DocObj:
    source_hash = "h"
    parser_version = "pv"

    def to_dict(self):
        return {"document_id": "d", "source_type": "pdf",
                "elements": [{"type": "paragraph", "content": "hi"}],
                "chunks": [{"text": "hi",
                            "source_element_ids": ["e1"]}]}


def _write_manifest(tmp_path) -> Path:
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/x.pdf",
                       "source_type": "pdf"}]}), encoding="utf-8")
    return mf


def _write_doc(tmp_path) -> Path:
    f = tmp_path / "doc.json"
    f.write_text(json.dumps({
        "document_id": "s", "source_type": "docx",
        "source_path": "s.docx",
        "elements": [{"type": "paragraph", "content": "hi"}],
        "chunks": [{"text": "hi", "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    return f


# ---------- run 全链路 e2e ----------

def test_run_e2e_and_validate_closed_loop_batch54(monkeypatch, tmp_path,
                                                  capsys):
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (_DocObj(), []))
    mf = _write_manifest(tmp_path)
    out = tmp_path / "out" / "rep.json"
    assert main(["run", "--manifest", str(mf), "--output", str(out)]) == 0
    assert out.is_file()
    summary = [l for l in capsys.readouterr().out.splitlines()
               if "documents=" in l]
    assert summary == ["      documents=1（成功 1，失败 0）"]
    # 闭环：validate-report 吃 run 的产出
    assert main(["validate-report", str(out)]) == 0


# ---------- inspect 排序分组 ----------

def test_inspect_sort_dict_between_numeric_and_null_batch54(tmp_path,
                                                            capsys):
    f = _write_doc(tmp_path)
    assert main(["inspect-doc", str(f)]) == 0
    names = [l.strip().split()[0]
             for l in capsys.readouterr().out.splitlines()
             if l.startswith("  ")]
    dict_idx = names.index("element_count_by_type")
    silent_idx = names.index("silent_drop_count")
    num_idx = names.index("element_count_total")
    bool_idx = names.index("pipeline_success")
    assert bool_idx < num_idx < dict_idx < silent_idx
    # element_count_by_type 之后全是 null 组（含 _ 前缀内部键则除外）
    tail_nulls = [n for n in names[dict_idx:]
                  if n != "_tolerance_chars"]
    assert all(n in {
        "element_count_by_type", "chunk_boundary_f1",
        "chunk_boundary_precision", "chunk_boundary_recall", "error_code",
        "figure_caption_f1", "figure_caption_precision",
        "figure_caption_recall", "heading_boundary_compliance",
        "image_resource_exists_ratio", "pdf_locator_valid_ratio",
        "silent_drop_count"} for n in tail_nulls)


# ---------- _format_metric 超长名 ----------

def test_format_metric_long_name_no_truncation_batch54():
    line = _format_metric("x" * 40, {"value": 1})
    assert line == "  " + "x" * 40 + " 1  (ok)"


# ---------- 负容差透传 ----------

def test_negative_tolerance_accepted_batch54(tmp_path, capsys):
    f = _write_doc(tmp_path)
    assert main(["inspect-doc", str(f), "--tolerance-chars", "-5"]) == 0
    tol = [l for l in capsys.readouterr().out.splitlines()
           if l.strip().startswith("_tolerance_chars")]
    assert tol == ["  _tolerance_chars" + " " * 21 + "-5  (ok)"]


# ---------- 元组 argv ----------

def test_main_accepts_tuple_argv_batch54(tmp_path, capsys):
    f = _write_doc(tmp_path)
    assert main(("inspect-doc", str(f))) == 0
    assert "document_id: s" in capsys.readouterr().out


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_sort_key_groups_batch54():
    src = _src()
    assert "return (3, name)" in src
    assert "return (0, name)" in src
    assert "return (1, name)" in src
    assert "return (2, name)" in src


# ---------- forbidden tokens 第二百一十八批 ----------

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


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
