"""evaluation/cli.py 第三百四十六轮 edges 测试（Round 902）。

补强 edges108 未触及的角度（第二百七十八批，probe 实证）。

新角度：
- inspect-doc 指标行恰 21 行（14 自动 + 3 figure +
  3 chunk_boundary + 1 _tolerance_chars——inspect 不弹出该键）
- 行序：bool 组前三（pipeline_success/schema_valid/
  text_preservation_equal），int 组 "_tolerance_chars" 第四
  （"_" < 小写字母），null 组殿后
- _tolerance_chars 负值 -5 原样渲染 "-5  (ok)"
- run_evaluation 抛 EvalSchemaError → rc1 "生成的报告未通过
  Schema 校验"（与自校验失败分支区分）
- validate_file 自校验抛 EvalSchemaError → rc1 "报告自校验失败"
- forbidden tokens 第三百七十二批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.cli as cli_mod
from evaluation.cli import main
from evaluation.schema import EvalSchemaError


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
    return mf


def _doc_file(tmp_path):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "AB"}],
        "chunks": [{"text": "AB",
                    "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    return f


# ---------- 21 行指标结构 ----------

def test_inspect_metric_lines_twenty_one_batch100(tmp_path, capsys):
    f = _doc_file(tmp_path)
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "-5"])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    mi = lines.index("metrics:")
    metric_lines = lines[mi + 1:]
    assert len(metric_lines) == 21
    assert metric_lines[0].startswith("  pipeline_success")
    assert " true  (ok)" in metric_lines[0]
    assert metric_lines[1].startswith("  schema_valid")
    assert " false  (ok)" in metric_lines[1]
    assert metric_lines[2].startswith("  text_preservation_equal")
    # int 组第四："_"(95) 排在小写字母前
    assert metric_lines[3] == \
        "  _tolerance_chars" + " " * 21 + "-5  (ok)"


def test_inspect_null_group_last_batch100(tmp_path, capsys):
    f = _doc_file(tmp_path)
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines()
             if ln.startswith("  ")]
    assert lines[-2].startswith("  image_resource_exists_ratio")
    assert "null  (no_image_elements)" in lines[-2]
    assert lines[-1].startswith("  silent_drop_count")
    assert "null  (no_expectations)" in lines[-1]


# ---------- run 的两个 Schema 失败分支 ----------

def test_run_evalschema_from_run_rc1_batch100(tmp_path, capsys):
    mf = _mk_manifest(tmp_path)
    out = tmp_path / "r.json"
    with patch.object(cli_mod, "run_evaluation",
                      side_effect=EvalSchemaError("bad report")):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    e = capsys.readouterr().err
    assert rc == 1
    assert "[ERROR] 生成的报告未通过 Schema 校验" in e


def test_run_self_validation_fail_rc1_batch100(tmp_path, capsys):
    mf = _mk_manifest(tmp_path)
    out = tmp_path / "r.json"
    with patch.object(cli_mod, "run_evaluation",
                      return_value={"per_doc": [], "devset": {}}), \
         patch.object(cli_mod, "validate_file",
                      side_effect=EvalSchemaError("self fail")):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    e = capsys.readouterr().err
    assert rc == 1
    assert "[ERROR] 报告自校验失败" in e


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch100():
    src = _src()
    assert ("metrics.update(chunk_boundary_prf("
            "doc, None, tolerance_chars=args.tolerance_chars))") in src
    assert "生成的报告未通过 Schema 校验" in src
    assert "if isinstance(v, (int, float)):" in src
    assert 'elements = doc.get("elements") or []' in src


# ---------- forbidden tokens 第三百七十二批 ----------

def test_source_no_eval_batch100():
    assert "eval(" not in _src()


def test_source_no_exec_batch100():
    assert "exec(" not in _src()


def test_source_no_compile_batch100():
    assert "compile(" not in _src()


def test_source_no_globals_batch100():
    assert "globals(" not in _src()


def test_source_no_locals_batch100():
    assert "locals(" not in _src()


def test_source_no_os_system_batch100():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch100():
    assert "subprocess" not in _src()


def test_source_no_popen_batch100():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch100():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch100():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch100():
    assert "socket" not in _src()


def test_source_no_requests_batch100():
    assert "requests" not in _src()


def test_source_no_urllib_batch100():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch100():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch100():
    assert "yield" not in _src()


def test_source_no_async_await_batch100():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch100():
    assert _src().count("open(") == 1
