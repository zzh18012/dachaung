"""evaluation/cli.py 第三百一十八轮 edges 测试（Round 874）。

补强 edges104 未触及的角度（第二百四十九批）。

新角度：
- inspect-doc 处理 docx：docx_locator 1.0000 +
  pdf_locator null not_pdf_document + type=docx 头
- inspect-doc 走真实 schema_validation：不合法最小文档
  → schema_valid false
- _format_metric 的 value None + reason None → "null (None)"
  （f-string 直接渲染 None 的现状锁定）
- run 清单为 0 字节空文件 → ManifestError rc1
- --max-chars "abc" → argparse int 转换错 SystemExit 2
- forbidden tokens 第三百四十四批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


# ---------- docx inspect ----------

def test_inspect_docx_metrics_batch72(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(inspect.cleandoc("""
        {
          "source_type": "docx",
          "elements": [{"element_id": "e1", "type": "paragraph",
                        "content": "AB",
                        "source_locator": {"paragraph_index": 0}}],
          "chunks": [{"text": "AB", "source_element_ids": ["e1"]}]
        }"""), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "type=docx" in out
    assert "docx_locator_valid_ratio" in out
    assert "1.0000" in out
    assert "pdf_locator_valid_ratio" in out
    assert "not_pdf_document" in out


# ---------- 真实 schema 校验路径 ----------

def test_inspect_schema_valid_false_batch72(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(inspect.cleandoc("""
        {
          "source_type": "pdf",
          "elements": [{"element_id": "e1", "type": "paragraph",
                        "content": "A"}],
          "chunks": [{"text": "A", "source_element_ids": ["e1"]}]
        }"""), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    lines = capsys.readouterr().out.splitlines()
    assert rc == 0
    sv = [ln for ln in lines if ln.strip().startswith(
        "schema_valid")]
    assert sv
    assert " false " in sv[0]


# ---------- reason None 渲染 ----------

def test_inspect_error_code_null_none_reason_batch72(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text('{"source_type": "pdf"}', encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    lines = capsys.readouterr().out.splitlines()
    assert rc == 0
    ec = [ln for ln in lines if ln.strip().startswith(
        "error_code")]
    assert ec
    assert "null  (None)" in ec[0]


# ---------- 空清单文件 ----------

def test_run_empty_manifest_rc1_batch72(tmp_path, capsys):
    mf = tmp_path / "m.json"
    mf.write_text("", encoding="utf-8")
    rc = main(["run", "--manifest", str(mf),
               "--output", str(tmp_path / "r.json")])
    assert rc == 1
    assert "清单加载失败" in capsys.readouterr().err


# ---------- 非整数 max-chars ----------

def test_run_max_chars_not_int_exit2_batch72(tmp_path, capsys):
    mf = tmp_path / "m.json"
    mf.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", str(mf),
              "--output", str(tmp_path / "r.json"),
              "--max-chars", "abc"])
    assert ei.value.code == 2
    assert "invalid int value" in capsys.readouterr().err


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch72():
    src = _src()
    assert 'return f"  {name:36} null  ({reason})"' in src
    assert 'reason or \'ok\'' in src
    assert "if not manifest_path.is_file():" in src


# ---------- forbidden tokens 第三百四十四批 ----------

def test_source_no_eval_batch72():
    assert "eval(" not in _src()


def test_source_no_exec_batch72():
    assert "exec(" not in _src()


def test_source_no_compile_batch72():
    assert "compile(" not in _src()


def test_source_no_globals_batch72():
    assert "globals(" not in _src()


def test_source_no_locals_batch72():
    assert "locals(" not in _src()


def test_source_no_os_system_batch72():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch72():
    assert "subprocess" not in _src()


def test_source_no_popen_batch72():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch72():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch72():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch72():
    assert "socket" not in _src()


def test_source_no_requests_batch72():
    assert "requests" not in _src()


def test_source_no_urllib_batch72():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch72():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch72():
    assert "yield" not in _src()


def test_source_no_async_await_batch72():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch72():
    assert _src().count("open(") == 1
