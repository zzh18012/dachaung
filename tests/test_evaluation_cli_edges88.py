"""evaluation/cli.py 第一百零七轮 edges 测试（Round 755）。

补强 edges85-87 未触及的角度（第一百一十四批续）。

新角度：
- --parser bogus → argparse choices 拒绝（SystemExit 2 + invalid choice）
- run：坏 JSON manifest → rc 1 "[ERROR] 清单加载失败"；
  run_evaluation 抛 EvalSchemaError → rc 1 "生成的报告未通过 Schema 校验"
- validate-report：BOM → JSONDecodeError 分支 rc 1 "[ERROR] JSON 解析失败"；
  形状合法但非报告（manifest JSON）→ rc 1 "[FAIL] ... 报告校验失败"
- inspect-doc 头部：缺 source_path/parser 键 → "? v?" 与 "?  type=" 默认；
  counts 行 elements/chunks 实数
- inspect-doc 渲染：float 0.6667（4 位小数四舍五入）、int 行 pad 精确、
  dict 指标键排序（heading=1, paragraph=2）、无标注时 _missing_markers
  键完全缺席（chunk_boundary_prf 无标注只回 _tolerance_chars）
- run 汇总行：git_commit 截 12 字符 + git_dirty 透传
- forbidden tokens 第二百二十五批
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main
from evaluation.schema import EvalSchemaError

ROOT = Path(__file__).resolve().parents[1]


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


def _manifest(tmp, payload=None):
    mf = tmp / "m.json"
    body = payload if payload is not None else {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": []}
    mf.write_text(body if isinstance(body, str) else json.dumps(body),
                  encoding="utf-8")
    return mf


@pytest.fixture
def tmp():
    return Path(tempfile.mkdtemp())


# ---------- argparse choices ----------

def test_invalid_parser_systemexit_two_batch54(tmp):
    out, err, co, ce = _cap()
    with co, ce, pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", str(_manifest(tmp)), "--output", "o",
              "--parser", "bogus"])
    assert ei.value.code == 2
    assert "invalid choice" in err.getvalue()


# ---------- run 错误路径 ----------

def test_run_malformed_manifest_rc1_batch54(tmp):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["run", "--manifest", str(_manifest(tmp, "{bad")),
                   "--output", str(tmp / "o.json")])
    assert rc == 1
    assert err.getvalue().startswith("[ERROR] 清单加载失败: "
                                      "清单 JSON 解析失败")


def test_run_evaluation_schema_error_rc1_batch54(tmp, monkeypatch):
    def boom(*a, **k):
        raise EvalSchemaError("bad report")

    monkeypatch.setattr(cli_mod, "run_evaluation", boom)
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["run", "--manifest", str(_manifest(tmp)),
                   "--output", str(tmp / "o.json")])
    assert rc == 1
    assert err.getvalue().startswith("[ERROR] 生成的报告未通过 "
                                      "Schema 校验: bad report")


# ---------- validate-report 分支 ----------

def test_validate_report_bom_rc1_batch54(tmp):
    f = tmp / "b.json"
    f.write_bytes(b'\xef\xbb\xbf{}')
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["validate-report", str(f)])
    assert rc == 1
    assert err.getvalue().startswith("[ERROR] JSON 解析失败: "
                                      "Unexpected UTF-8 BOM")


def test_validate_report_wrong_shape_fail_batch54(tmp):
    # 合法 JSON 但形状是 manifest 不是报告 → [FAIL] rc 1
    f = _manifest(tmp)
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["validate-report", str(f)])
    assert rc == 1
    assert err.getvalue().startswith("[FAIL]")
    assert "报告校验失败" in err.getvalue()


# ---------- inspect-doc 头部默认 ----------

def _write_doc(tmp):
    f = tmp / "doc.json"
    f.write_text(json.dumps({
        "document_id": "d", "source_type": "docx",
        "elements": [{"type": "paragraph", "content": "a",
                      "element_id": "e1"},
                     {"type": "heading", "content": "b",
                      "element_id": "e2"},
                     {"type": "paragraph", "content": "c",
                      "element_id": "e3"}],
        "chunks": [{"text": "ab", "source_element_ids": ["e1"]},
                   {"text": "b", "source_element_ids": ["eX"]},
                   {"text": "c", "source_element_ids": ["e3"]}]}),
        encoding="utf-8")
    return f


def test_inspect_header_defaults_batch54(tmp):
    out, err, co, ce = _cap()
    with co, ce:
        assert main(["inspect-doc", str(_write_doc(tmp))]) == 0
    lines = out.getvalue().splitlines()
    assert lines[1] == "document_id: d"
    assert lines[2] == "source:      ?  type=docx"
    assert lines[3] == "parser:      ? v?"
    assert lines[4] == "counts:      elements=3 chunks=3"


def test_inspect_float_four_decimals_batch54(tmp):
    out, err, co, ce = _cap()
    with co, ce:
        assert main(["inspect-doc", str(_write_doc(tmp))]) == 0
    line = [l for l in out.getvalue().splitlines()
            if l.strip().startswith("chunk_reference_intact_ratio")][0]
    assert line == ("  chunk_reference_intact_ratio"
                    + " " * 9 + "0.6667  (ok)")


def test_inspect_int_line_padded_batch54(tmp):
    out, err, co, ce = _cap()
    with co, ce:
        assert main(["inspect-doc", str(_write_doc(tmp))]) == 0
    line = [l for l in out.getvalue().splitlines()
            if l.strip().startswith("element_count_total")][0]
    assert line == "  element_count_total" + " " * 18 + "3  (ok)"


def test_inspect_dict_metric_keys_sorted_batch54(tmp):
    out, err, co, ce = _cap()
    with co, ce:
        assert main(["inspect-doc", str(_write_doc(tmp))]) == 0
    line = [l for l in out.getvalue().splitlines()
            if l.strip().startswith("element_count_by_type")][0]
    assert line.endswith("heading=1, paragraph=2  (ok)")


def test_inspect_missing_markers_key_absent_batch54(tmp):
    # 无标注 → chunk_boundary_prf 只回 _tolerance_chars，无 _missing_markers
    out, err, co, ce = _cap()
    with co, ce:
        assert main(["inspect-doc", str(_write_doc(tmp))]) == 0
    assert "_missing_markers" not in out.getvalue()
    assert "_tolerance_chars" in out.getvalue()


# ---------- run 汇总行 ----------

def test_run_summary_git_line_batch54(tmp, monkeypatch):
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda root: {"git_commit": "abcdefgh1234567890",
                                      "git_dirty": False})
    monkeypatch.setattr(cli_mod, "run_evaluation",
                        lambda man, out, **k: {"per_doc": [], "devset": {}})
    monkeypatch.setattr(cli_mod, "validate_file", lambda p, s: None)
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["run", "--manifest", str(_manifest(tmp)),
                   "--output", str(tmp / "r.json")])
    assert rc == 0
    line = [l for l in out.getvalue().splitlines() if "git_" in l][0]
    assert line == "      git_commit=abcdefgh1234 git_dirty=False"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_branches_batch54():
    src = _src()
    assert 'choices=("fallback", "kreuzberg")' in src
    assert "if isinstance(value, float):" in src
    assert "sorted(value.items())" in src
    assert "[:12]" in src


# ---------- forbidden tokens 第二百二十五批 ----------

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
