"""evaluation/cli.py 第三百二十五轮 edges 测试（Round 881）。

补强 edges105 未触及的角度（第二百五十六批）。

新角度：
- run 统计行 success 用 `is True`：metrics 值 int 1 →
  计失败（documents=1（成功 0，失败 1））
- inspect-doc 集成层 by_type dict 排序渲染
  （paragraph=1, table=1）
- run 缺 --manifest → argparse required 错 SystemExit 2
- forbidden tokens 第三百五十一批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


# ---------- 统计行严格 True ----------

def test_run_stats_int_one_counted_failed_batch79(tmp_path, capsys):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    out = tmp_path / "r.json"
    out.write_text("{}", encoding="utf-8")
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "source_type": "pdf",
             "metrics": {"pipeline_success":
                         {"value": 1, "reason": None}},
             "wall_time_seconds": {}}],
        "devset": {"status": "incomplete", "file_count": 1,
                   "content_group_count": 1, "pdf_count": 1,
                   "docx_count": 0},
    }
    with patch.object(cli_mod, "run_evaluation",
                      return_value=fake_report), \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    assert rc == 0
    assert "documents=1（成功 0，失败 1）" in \
        capsys.readouterr().out


# ---------- by_type 排序渲染 ----------

def test_inspect_by_type_sorted_integration_batch79(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [
            {"element_id": "e1", "type": "table",
             "content": "T"},
            {"element_id": "e2", "type": "paragraph",
             "content": "P"}],
        "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "paragraph=1, table=1" in out


# ---------- 缺 --manifest ----------

def test_run_missing_manifest_arg_exit2_batch79(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run"])
    assert ei.value.code == 2
    assert "--manifest" in capsys.readouterr().err


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch79():
    src = _src()
    assert 'if r["metrics"].get("pipeline_success", {}).get("value") is True' in src
    assert "items = \", \".join(f\"{k}={v}\" for k, v in sorted(value.items()))" in src
    assert "sub = p.add_subparsers(dest=\"command\", required=True)" in src


# ---------- forbidden tokens 第三百五十一批 ----------

def test_source_no_eval_batch79():
    assert "eval(" not in _src()


def test_source_no_exec_batch79():
    assert "exec(" not in _src()


def test_source_no_compile_batch79():
    assert "compile(" not in _src()


def test_source_no_globals_batch79():
    assert "globals(" not in _src()


def test_source_no_locals_batch79():
    assert "locals(" not in _src()


def test_source_no_os_system_batch79():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch79():
    assert "subprocess" not in _src()


def test_source_no_popen_batch79():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch79():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch79():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch79():
    assert "socket" not in _src()


def test_source_no_requests_batch79():
    assert "requests" not in _src()


def test_source_no_urllib_batch79():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch79():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch79():
    assert "yield" not in _src()


def test_source_no_async_await_batch79():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch79():
    assert _src().count("open(") == 1
