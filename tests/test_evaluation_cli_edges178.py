"""evaluation/cli.py 第六百七十九轮 edges 测试（Round 1357）。

补强 edges177 未触及的角度（第七百二十九批，probe 实证）。

新角度（markdown 文档喂 inspect-doc / 内部键渲染泄漏）：
- **markdown × inspect**
  ——MarkdownParser
  产物直接 inspect-doc
  → type=markdown +
  parser 行
  'markdown
  vstdlib/0.1.0'
- **_tolerance_chars
  泄漏**——inspect
  路径不 pop 内部
  键（runner 才
  pop）→ 渲染行
  '_tolerance_chars
  30  (ok)'
- **empty_actual
  不对称**——
  chunks=0 时
  tcmp null
  (empty_actual)
  而 tcmr 0.0000
- **桶排序**——
  3 bool + 5 数值
  + 1 dict + 12
  null 恰 21 行
- **dict 渲染**——
  ect_by_type 一行
  'heading=1,
  image=1, ...'
- forbidden tokens 第六百批（open 1）
"""

from __future__ import annotations

import inspect
import io
import json
import sys
import tempfile
from contextlib import redirect_stderr, \
    redirect_stdout
from pathlib import Path

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


@pytest.fixture(autouse=True)
def _restore_argv():
    saved = sys.argv
    yield
    sys.argv = saved


MD = ("# T\n\npara one\n\n- item a\n- item b\n\n"
      "> quote line\n\n```py\ncode here\n```\n\n"
      "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n"
      "![alt](img.png)\n")


def _inspect_md():
    from app.hash import compute_file_hash
    from app.parsers.markdown_parser import \
        MarkdownParser
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "d.md").write_text(MD, encoding="utf-8")
        sha = compute_file_hash(tp / "d.md")
        doc = MarkdownParser().parse(
            tp / "d.md", sha).to_dict()
        (tp / "doc.json").write_text(
            json.dumps(doc, ensure_ascii=False),
            encoding="utf-8")
        sys.argv = ["evaluation.cli", "inspect-doc",
                    str(tp / "doc.json")]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = main()
        return rc, out.getvalue(), \
            err.getvalue(), doc


# ---------- markdown × inspect 头部 ----------

def test_md_inspect_rc_zero_batch555():
    rc, _, err, _ = _inspect_md()
    assert rc == 0
    assert err == ""


def test_md_inspect_type_markdown_batch555():
    _, out, _, _ = _inspect_md()
    assert "  type=markdown" in out


def test_md_inspect_parser_line_batch555():
    _, out, _, _ = _inspect_md()
    assert ("parser:      markdown "
            "vstdlib/0.1.0") in out


def test_md_inspect_counts_batch555():
    _, out, _, _ = _inspect_md()
    assert "counts:      elements=8" \
        " chunks=0" in out


def test_md_inspect_docid_prefix_batch555():
    _, out, _, _ = _inspect_md()
    docid = [ln for ln in out.splitlines()
             if ln.startswith("document_id:")][0]
    val = docid.split("document_id: ")[1]
    assert val.startswith("doc-")
    assert len(val) == 20


# ---------- _tolerance_chars 泄漏 ----------

def test_md_inspect_tolkey_leak_batch555():
    _, out, _, _ = _inspect_md()
    assert ("  _tolerance_chars              "
            "       30  (ok)") in out \
        or "_tolerance_chars" in out


def test_md_inspect_tolkey_is_metric_batch555():
    _, out, _, _ = _inspect_md()
    metric_lines = out.splitlines()[
        out.splitlines().index("metrics:") + 1:]
    assert any(ln.strip().startswith(
        "_tolerance_chars") for ln in metric_lines)


def test_md_inspect_30_render_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if "_tolerance_chars" in l][0]
    assert ln.rstrip().endswith("30  (ok)")


# ---------- empty_actual 不对称 ----------

def test_md_inspect_tpe_false_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if l.strip().startswith(
              "text_preservation_equal")][0]
    assert "false" in ln


def test_md_inspect_tcmp_null_empty_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if l.strip().startswith(
              "text_char_multiset_precision")][0]
    assert "null" in ln
    assert "empty_actual" in ln


def test_md_inspect_tcmr_zero_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if l.strip().startswith(
              "text_char_multiset_recall")][0]
    assert "0.0000" in ln
    assert "null" not in ln


# ---------- 桶排序与行数 ----------

def test_md_inspect_line_count_batch555():
    _, out, _, _ = _inspect_md()
    assert len(out.splitlines()) == 28


def test_md_inspect_metric_count_21_batch555():
    _, out, _, _ = _inspect_md()
    lines = out.splitlines()
    metric_lines = lines[lines.index(
        "metrics:") + 1:]
    assert len(metric_lines) == 21


def test_md_inspect_first_metric_batch555():
    _, out, _, _ = _inspect_md()
    lines = out.splitlines()
    assert lines[lines.index("metrics:") + 1] \
        .strip().startswith("pipeline_success")


def test_md_inspect_last_metric_batch555():
    _, out, _, _ = _inspect_md()
    assert out.splitlines()[-1].strip().startswith(
        "text_char_multiset_precision")


def test_md_inspect_bool_bucket_three_batch555():
    _, out, _, _ = _inspect_md()
    lines = out.splitlines()
    metric_lines = [l.strip() for l in lines[
        lines.index("metrics:") + 1:]]
    bools = [l for l in metric_lines
             if l.split()[1] in ("true", "false")]
    assert len(bools) == 3


def test_md_inspect_null_bucket_twelve_batch555():
    _, out, _, _ = _inspect_md()
    lines = out.splitlines()
    metric_lines = [l.strip() for l in lines[
        lines.index("metrics:") + 1:]]
    nulls = [l for l in metric_lines
             if " null  (" in l]
    assert len(nulls) == 12


# ---------- dict 渲染 ----------

def test_md_inspect_ect_by_type_line_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if l.strip().startswith(
              "element_count_by_type")][0]
    assert ("heading=1, image=1, list_item=2, "
            "paragraph=3, table=1") in ln


def test_md_inspect_hbc_four_decimals_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if l.strip().startswith(
              "heading_boundary_compliance")][0]
    assert " 0.0000  (ok)" in ln


def test_md_inspect_irr_zero_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if l.strip().startswith(
              "image_resource_exists_ratio")][0]
    assert " 0.0000  (ok)" in ln


def test_md_inspect_error_code_none_batch555():
    _, out, _, _ = _inspect_md()
    ln = [l for l in out.splitlines()
          if l.strip().startswith("error_code")][0]
    assert "null  (None)" in ln


# ---------- 文档本体复核 ----------

def test_md_doc_elements_eight_batch555():
    _, _, _, doc = _inspect_md()
    assert len(doc["elements"]) == 8


def test_md_doc_source_type_batch555():
    _, _, _, doc = _inspect_md()
    assert doc["source_type"] == "markdown"


def test_md_doc_metadata_flag_batch555():
    _, _, _, doc = _inspect_md()
    assert doc["metadata"] == {"markdown": True}


def test_md_doc_types_multiset_batch555():
    _, _, _, doc = _inspect_md()
    from collections import Counter
    assert Counter(e["type"] for e in
                   doc["elements"]) == Counter({
        "heading": 1, "image": 1,
        "list_item": 2, "paragraph": 3,
        "table": 1})


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_no_pop_batch555():
    assert "pop(" not in _src()


def test_source_bucket_keys_batch555():
    src = _src()
    assert "return (3, name)" in src
    assert "return (0, name)" in src
    assert "return (1, name)" in src


def test_source_format_pad_36_batch555():
    assert "{name:36}" in _src()


def test_source_float_four_decimals_batch555():
    assert "{value:.4f}" in _src()


def test_source_dict_render_batch555():
    assert "for k, v in sorted(value.items())" \
        in _src()


def test_source_inspect_no_annotation_batch555():
    src = _src()
    assert "chunk_boundary_prf(doc, None," in src
    assert "figure_caption_prf(doc, None)" in src


def test_source_key_counts_batch555():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


def test_source_open_count_is_1_batch555():
    assert _src().count("open(") == 1


# ---------- forbidden tokens 第六百批 ----------

def test_source_no_eval_batch555():
    assert "eval(" not in _src()


def test_source_no_exec_batch555():
    assert "exec(" not in _src()


def test_source_no_compile_batch555():
    assert "compile(" not in _src()


def test_source_no_globals_batch555():
    assert "globals(" not in _src()


def test_source_no_locals_batch555():
    assert "locals(" not in _src()


def test_source_no_os_system_batch555():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch555():
    assert "subprocess" not in _src()


def test_source_no_popen_batch555():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch555():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch555():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch555():
    assert "socket" not in _src()


def test_source_no_requests_batch555():
    assert "requests" not in _src()


def test_source_no_urllib_batch555():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch555():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch555():
    assert "yield" not in _src()


def test_source_no_async_await_batch555():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch555():
    assert ".call(" not in _src()
