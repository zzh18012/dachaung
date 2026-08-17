"""evaluation/cli.py 第四百七十九轮 edges 测试（Round 1035）。

补强 edges127 未触及的角度（第四百一十一批，probe 实证）。

新角度（五类型真实文档 inspect-doc 全屏合流）：
- 与 R1014/R1028 误喂全家福（全 "?" 回退）成镜像：
  schema 合法五类型文档渲染全真值四行表头
  （document_id REAL-42 / source a.pdf type=pdf /
  parser fallback v9.9 / elements=5 chunks=1）
- 四桶全真值同屏：bool 桶（true/true/false）、数值桶
  含 4 位小数定格式（1.0000 / 0.8000 / 0.0000 / 整数
  5）、dict 桶（element_count_by_type 五键字母序逗号
  join）、null 桶 9 行各带 reason（no_annotation×3 /
  not_docx_document / (None) /
  parser_does_not_emit_relations×3 / no_expectations）
- text_char_multiset_precision 0.8000：元素内容
  5×"x" vs chunk 文本 "xxxxx" → 4/5（intact 却 1.0、
  text_preservation false 同屏三分裂）
- forbidden tokens 第五百零六批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _e(t, eid):
    return {"type": t, "element_id": eid, "content": "x",
            "parent_id": None, "confidence": 0.9,
            "metadata": {},
            "source_locator": {"page": 1,
                               "bbox": [0, 0, 1, 1]}}


def _rich_doc():
    return {
        "elements": [_e("heading", "h1"), _e("paragraph",
                     "p1"), _e("table", "t1"),
                     dict(_e("image", "i1"),
                          resource_path="img.png"),
                     _e("list_item", "l1")],
        "chunks": [{"chunk_id": "c1", "text": "xxxxx",
                    "source_element_ids": ["h1", "p1",
                                           "t1", "i1",
                                           "l1"],
                    "metadata": {}}],
        "source_type": "pdf", "document_id": "REAL-42",
        "schema_version": "0.1.0", "source_path": "a.pdf",
        "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "9.9", "relations": [],
        "warnings": [], "errors": [], "metadata": {}}


def _run_inspect(tmp_path, capsys):
    f = tmp_path / "rich.json"
    f.write_text(json.dumps(_rich_doc()), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    return rc, out


# ---------- 全真值表头 ----------

def test_rich_header_all_real_batch233(tmp_path, capsys):
    rc, out = _run_inspect(tmp_path, capsys)
    assert rc == 0
    lines = out.splitlines()
    assert lines[1] == "document_id: REAL-42"
    assert lines[2] == "source:      a.pdf  type=pdf"
    assert lines[3] == "parser:      fallback v9.9"
    assert lines[4] == "counts:      elements=5 chunks=1"


# ---------- 四桶全真值 ----------

def test_rich_bool_bucket_batch233(tmp_path, capsys):
    _, out = _run_inspect(tmp_path, capsys)
    assert ("  pipeline_success                     true"
            "  (ok)") in out
    assert ("  schema_valid                         true"
            "  (ok)") in out
    assert ("  text_preservation_equal              false"
            "  (ok)") in out


def test_rich_numeric_bucket_batch233(tmp_path, capsys):
    _, out = _run_inspect(tmp_path, capsys)
    assert ("  chunk_reference_intact_ratio         "
            "1.0000  (ok)") in out
    assert ("  text_char_multiset_precision         "
            "0.8000  (ok)") in out
    assert ("  image_resource_exists_ratio          "
            "0.0000  (ok)") in out
    assert ("  element_count_total                  5"
            "  (ok)") in out


def test_rich_dict_bucket_sorted_join_batch233(
        tmp_path, capsys):
    _, out = _run_inspect(tmp_path, capsys)
    line = [ln for ln in out.splitlines()
            if ln.strip().startswith("element_count_by_type")][0]
    assert line.startswith("  element_count_by_type")
    assert line.rstrip().endswith(
        "heading=1, image=1, list_item=1, paragraph=1,"
        " table=1  (ok)")


def test_rich_null_bucket_nine_lines_batch233(
        tmp_path, capsys):
    _, out = _run_inspect(tmp_path, capsys)
    nulls = [ln.strip() for ln in out.splitlines()
             if ln.startswith("  ") and "null" in ln]
    assert len(nulls) == 9
    assert ("chunk_boundary_f1                    null"
            "  (no_annotation)") in nulls
    assert ("docx_locator_valid_ratio             null"
            "  (not_docx_document)") in nulls
    assert ("silent_drop_count                    null"
            "  (no_expectations)") in nulls


# ---------- 三分裂 ----------

def test_precision_vs_intact_vs_equal_split_batch233(
        tmp_path, capsys):
    _, out = _run_inspect(tmp_path, capsys)
    assert "0.8000" in out
    assert "  chunk_reference_intact_ratio         " \
        "1.0000" in out
    assert "text_preservation_equal              false" \
        in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch233():
    src = _src()
    assert "inspect-doc" in src
    assert "doc.get('document_id', '?')" in src
    assert "doc.get('source_path', '?')" in src


def test_source_format_metric_exists_batch233():
    src = _src()
    assert "_format_metric" in src


# ---------- forbidden tokens 第五百零六批 ----------

def test_source_no_eval_batch233():
    assert "eval(" not in _src()


def test_source_no_exec_batch233():
    assert "exec(" not in _src()


def test_source_no_compile_batch233():
    assert "compile(" not in _src()


def test_source_no_globals_batch233():
    assert "globals(" not in _src()


def test_source_no_locals_batch233():
    assert "locals(" not in _src()


def test_source_no_os_system_batch233():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch233():
    assert "subprocess" not in _src()


def test_source_no_popen_batch233():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch233():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch233():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch233():
    assert "socket" not in _src()


def test_source_no_requests_batch233():
    assert "requests" not in _src()


def test_source_no_urllib_batch233():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch233():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch233():
    assert "yield" not in _src()


def test_source_no_async_await_batch233():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch233():
    assert _src().count("open(") == 1
