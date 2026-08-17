"""evaluation/cli.py 第四百一十六轮 edges 测试（Round 972）。

补强 edges118 未触及的角度（第三百四十八批，probe 实证）。

新角度：
- --max-chars "abc" → argparse invalid int → rc 2
- --tolerance-chars "xyz" → 同样 rc 2 invalid int
- paragraph 仅 page 无 bbox（_PDF_BBOX_REQUIRED_TYPES
  成员）→ pdf_locator 0.0 → 渲染 "0.0000  (ok)"
- null 值 + reason None 的渲染怪癖：通用 null 分支
  f"({reason})" 无 or 'ok' 兜底 → error_code 行渲染
  "null  (None)"（非 "(ok)"）
- by_type 单类型渲染 "paragraph=1  (ok)"
- forbidden tokens 第四百四十二批（open 1）
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


# ---------- 非法 int 参数 ----------

def test_max_chars_not_int_batch170(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", "m.json",
              "--output", "o.json", "--max-chars", "abc"])
    assert ei.value.code == 2
    assert "invalid int" in capsys.readouterr().err


def test_tolerance_chars_not_int_batch170(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["inspect-doc", "d.json",
              "--tolerance-chars", "xyz"])
    assert ei.value.code == 2
    assert "invalid int" in capsys.readouterr().err


# ---------- 渲染细节 ----------

def test_render_pdf_locator_and_null_reason_batch170(
        tmp_path, capsys):
    doc = {"source_type": "pdf",
           "elements": [{"type": "paragraph",
                         "content": "A",
                         "source_locator": {"page": 1}}],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e1"]}]}
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert "  " + "pdf_locator_valid_ratio".ljust(36) + \
        " 0.0000  (ok)" in lines
    assert "  " + "error_code".ljust(36) + \
        " null  (None)" in lines
    assert "  " + "element_count_by_type".ljust(36) + \
        " paragraph=1  (ok)" in lines


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch170():
    src = _src()
    assert 'return f"  {name:36} null  ({reason})"' in src
    assert 'type=int,' in src
    assert 'elements = doc.get("elements") or []' in src
    assert 'chunks = doc.get("chunks") or []' in src


# ---------- forbidden tokens 第四百四十二批 ----------

def test_source_no_eval_batch170():
    assert "eval(" not in _src()


def test_source_no_exec_batch170():
    assert "exec(" not in _src()


def test_source_no_compile_batch170():
    assert "compile(" not in _src()


def test_source_no_globals_batch170():
    assert "globals(" not in _src()


def test_source_no_locals_batch170():
    assert "locals(" not in _src()


def test_source_no_os_system_batch170():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch170():
    assert "subprocess" not in _src()


def test_source_no_popen_batch170():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch170():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch170():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch170():
    assert "socket" not in _src()


def test_source_no_requests_batch170():
    assert "requests" not in _src()


def test_source_no_urllib_batch170():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch170():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch170():
    assert "yield" not in _src()


def test_source_no_async_await_batch170():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch170():
    assert _src().count("open(") == 1
