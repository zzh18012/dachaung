"""evaluation/cli.py 第二百八十三轮 edges 测试（Round 839）。

补强 edges99 未触及的角度（第二百一十三批）。

新角度：
- run 参数捕获：--parser 默认 fallback、--max-chars 555、
  --tolerance-chars 9 原样传给 run_evaluation
- inspect-doc source_path 存在时的 source 行（对照 edges99
  的 "?" 缺省行）
- parser_version 缺失 → "fallback v?" 行
- 空文档 counts 行 elements=0 chunks=0
- inspect-doc 排序中段：bool 类 < 数值类 < dict 类 < null 类
  的相对位置
- inspect-doc 传目录 → rc2「文档不存在」
- forbidden tokens 第三百零九批
"""

from __future__ import annotations

import inspect
import json
from types import SimpleNamespace
from unittest.mock import patch

import evaluation.cli as cli_mod
from evaluation.cli import main


# ---------- run 参数捕获 ----------

def test_run_kwargs_propagation_batch55(tmp_path, capsys):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    cap: dict = {}

    def _run(*a, **k):
        cap.clear()
        cap.update(k)
        cap["_args"] = a
        return {"per_doc": [], "devset": {}}

    m = SimpleNamespace(project_root=tmp_path)
    with patch.object(cli_mod, "load_manifest",
                      lambda p: m), \
         patch.object(cli_mod, "run_evaluation", _run), \
         patch.object(cli_mod, "validate_file",
                      lambda p, s: None), \
         patch.object(cli_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(tmp_path / "r.json"),
                   "--max-chars", "555",
                   "--tolerance-chars", "9"])
    assert rc == 0
    assert cap["parser_name"] == "fallback"
    assert cap["max_chars"] == 555
    assert cap["tolerance_chars"] == 9


# ---------- inspect-doc 行 ----------

def _write_doc(tmp_path, doc):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    return f


def test_inspect_source_path_line_batch55(tmp_path, capsys):
    f = _write_doc(tmp_path, {
        "source_type": "docx", "source_path": "in/x.docx",
        "elements": [], "chunks": []})
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "source:      in/x.docx  type=docx" in out


def test_inspect_missing_parser_version_batch55(tmp_path, capsys):
    f = _write_doc(tmp_path, {
        "source_type": "pdf", "parser_name": "fallback",
        "elements": [], "chunks": []})
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "parser:      fallback v?" in out


def test_inspect_empty_doc_counts_batch55(tmp_path, capsys):
    f = _write_doc(tmp_path, {"source_type": "pdf",
                              "elements": [], "chunks": []})
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "counts:      elements=0 chunks=0" in out


def test_inspect_sort_buckets_batch55(tmp_path, capsys):
    f = _write_doc(tmp_path, {
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}],
        "chunks": [{"text": "A",
                    "source_element_ids": ["e1"]}]})
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    lines = out.splitlines()

    def _idx(prefix):
        for i, ln in enumerate(lines):
            if ln.strip().startswith(prefix):
                return i
        raise AssertionError(prefix)

    assert _idx("pipeline_success") < _idx("element_count_total")
    assert _idx("element_count_total") < _idx("element_count_by_type")
    assert _idx("element_count_by_type") < _idx("figure_caption_precision")


# ---------- inspect 目录输入 ----------

def test_inspect_directory_rc2_batch55(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path)])
    assert rc == 2
    assert "文档不存在" in capsys.readouterr().err


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "if isinstance(value, dict):" in src
    assert "sorted(metrics.keys(), key=_sort_key)" in src
    assert "return (2, name)" in src


# ---------- forbidden tokens 第三百零九批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch55():
    assert _src().count("open(") == 1
