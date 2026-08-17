"""evaluation/cli.py 第三百三十二轮 edges 测试（Round 888）。

补强 edges106 未触及的角度（第二百六十三批）。

新角度：
- run 输出块四行结构（[OK] / documents / devset / git）
  行首缩进 6 空格锁定
- inspect-doc counts 行两种内容并存
  （elements=2 chunks=1）
- validate-report 对空 JSON 对象 {} → Schema 校验失败
  rc1（顶层 required 5 项缺失）
- run --tolerance-chars 缺省 30 透传
- forbidden tokens 第三百五十八批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.cli as cli_mod
from evaluation.cli import main


def _mk_manifest(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf, root


# ---------- 输出块结构 ----------

def test_run_output_block_structure_batch86(tmp_path, capsys):
    mf, _ = _mk_manifest(tmp_path)
    out = tmp_path / "r.json"
    out.write_text("{}", encoding="utf-8")
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "source_type": "pdf",
             "metrics": {"pipeline_success":
                         {"value": True, "reason": None}},
             "wall_time_seconds": {}}],
        "devset": {"status": "incomplete", "file_count": 1,
                   "content_group_count": 1, "pdf_count": 1,
                   "docx_count": 0},
    }
    with patch.object(cli_mod, "run_evaluation",
                      return_value=fake_report), \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": "abc" * 13,
                                    "git_dirty": True}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    lines = [ln for ln in capsys.readouterr().out.splitlines()
             if ln]
    assert rc == 0
    assert lines[0].startswith("[OK] 评测完成：")
    assert lines[1].startswith("      documents=")
    assert lines[2].startswith("      devset_status=")
    assert lines[3].startswith("      git_commit=")
    assert "git_dirty=True" in lines[3]


# ---------- counts 混合 ----------

def test_inspect_counts_both_nonzero_batch86(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "paragraph",
             "content": "AB"},
            {"element_id": "e2", "type": "paragraph",
             "content": "CD"}],
        "chunks": [{"text": "ABCD",
                    "source_element_ids": ["e1", "e2"]}]}),
        encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "counts:      elements=2 chunks=1" in out


# ---------- 空 JSON 对象报告 ----------

def test_validate_report_empty_object_rc1_batch86(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    rc = main(["validate-report", str(f)])
    e = capsys.readouterr().err
    assert rc == 1
    assert "[FAIL]" in e
    assert "report_version" in e  # required 首项出现在报错里


# ---------- tolerance 缺省 ----------

def test_run_tolerance_default_30_batch86(tmp_path, capsys):
    mf, _ = _mk_manifest(tmp_path)
    out = tmp_path / "r.json"
    with patch.object(cli_mod, "run_evaluation",
                      return_value={"per_doc": [],
                                    "devset": {}}) as fake_run, \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    assert rc == 0
    assert fake_run.call_args.kwargs[
        "tolerance_chars"] == 30
    assert fake_run.call_args.kwargs["max_chars"] == 800


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch86():
    src = _src()
    assert 'f"[OK] 评测完成：{output_path}\\n"' in src
    assert 'f"      documents={n_docs}（成功 {n_ok}，失败 {n_fail}）\\n"' in src
    assert "git = get_git_provenance(manifest.project_root)" in src


# ---------- forbidden tokens 第三百五十八批 ----------

def test_source_no_eval_batch86():
    assert "eval(" not in _src()


def test_source_no_exec_batch86():
    assert "exec(" not in _src()


def test_source_no_compile_batch86():
    assert "compile(" not in _src()


def test_source_no_globals_batch86():
    assert "globals(" not in _src()


def test_source_no_locals_batch86():
    assert "locals(" not in _src()


def test_source_no_os_system_batch86():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch86():
    assert "subprocess" not in _src()


def test_source_no_popen_batch86():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch86():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch86():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch86():
    assert "socket" not in _src()


def test_source_no_requests_batch86():
    assert "requests" not in _src()


def test_source_no_urllib_batch86():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch86():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch86():
    assert "yield" not in _src()


def test_source_no_async_await_batch86():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch86():
    assert _src().count("open(") == 1
