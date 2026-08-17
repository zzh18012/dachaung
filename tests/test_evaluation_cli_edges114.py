"""evaluation/cli.py 第三百八十一轮 edges 测试（Round 937）。

补强 edges113 未触及的角度（第三百一十三批，probe 实证）。

新角度：
- _format_metric 直测六型：int / float 带 partial reason /
  bool 小写 true / dict 按 key 排序 "a=1, b=2" / null 保留
  reason / 未知类型 str 走兜底分支（{name:36} 精确构造）
- argparse 默认值直测：run --parser fallback --max-chars
  800 --tolerance-chars 30；inspect-doc tolerance 30；
  prog="evaluation.cli"
- inspect-doc 缺字段头四行：document_id "?" / source "?"
  type=unknown / parser "? v?"；source_type unknown →
  pdf/docx 双 ratio 均 not_*_document
- inspect-doc 指标四层排序全序 21 项：bool 层 3 项 →
  数值层 7 项（_tolerance_chars 是 int 混进比值层且
  下划线排最前）→ dict 层 element_count_by_type →
  null 层 10 项（chunk_boundary 三连 / figure_caption
  三连 / error_code / 双 locator / silent_drop）
- _tolerance_chars 行精确构造 "…ljust(36) + " 30  (ok)""
- forbidden tokens 第四百零七批
"""

from __future__ import annotations

import inspect
import json

from evaluation.cli import _build_parser, _format_metric, main


# ---------- _format_metric 六型 ----------

def test_format_metric_int_batch135():
    assert _format_metric("x", {"value": 3, "reason": None}) == \
        "  " + "x".ljust(36) + " 3  (ok)"


def test_format_metric_float_partial_batch135():
    assert _format_metric("x", {"value": 0.5,
                                "reason": "partial"}) == \
        "  " + "x".ljust(36) + " 0.5000  (partial)"


def test_format_metric_bool_lowercase_batch135():
    assert _format_metric("x", {"value": True,
                                "reason": None}) == \
        "  " + "x".ljust(36) + " true  (ok)"


def test_format_metric_dict_sorted_batch135():
    out = _format_metric("x", {"value": {"b": 2, "a": 1},
                               "reason": None})
    assert out == "  " + "x".ljust(36) + " a=1, b=2  (ok)"


def test_format_metric_null_batch135():
    assert _format_metric("x", {"value": None,
                                "reason": "r"}) == \
        "  " + "x".ljust(36) + " null  (r)"


def test_format_metric_fallback_str_batch135():
    assert _format_metric("x", {"value": "str",
                                "reason": None}) == \
        "  " + "x".ljust(36) + " str  (ok)"


# ---------- argparse 默认值 ----------

def test_run_defaults_batch135():
    a = _build_parser().parse_args(
        ["run", "--manifest", "m", "--output", "o"])
    assert a.command == "run"
    assert a.parser == "fallback"
    assert a.max_chars == 800
    assert a.tolerance_chars == 30


def test_inspect_default_tolerance_batch135():
    a = _build_parser().parse_args(["inspect-doc", "f"])
    assert a.command == "inspect-doc"
    assert a.tolerance_chars == 30


def test_prog_name_batch135():
    assert _build_parser().prog == "evaluation.cli"


# ---------- inspect 缺字段 ----------

_DOC = {
    "elements": [
        {"element_id": "h1", "type": "heading", "content": "H",
         "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"element_id": "i1", "type": "image",
         "resource_path": "nope.png"}],
    "chunks": [{"text": "H", "source_element_ids": ["h1"]}],
}


def _inspect(tmp_path, capsys, doc=_DOC):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    lines = capsys.readouterr().out.splitlines()
    return rc, lines


def test_inspect_missing_fields_header_batch135(tmp_path, capsys):
    rc, lines = _inspect(tmp_path, capsys)
    assert rc == 0
    assert lines[1] == "document_id: ?"
    assert lines[2] == "source:      ?  type=unknown"
    assert lines[3] == "parser:      ? v?"


def test_inspect_metric_tier_order_batch135(tmp_path, capsys):
    rc, lines = _inspect(tmp_path, capsys)
    assert rc == 0
    mi = lines.index("metrics:")
    names = [ln.strip().split()[0] for ln in lines[mi + 1:]]
    assert names == [
        # bool 层
        "pipeline_success", "schema_valid",
        "text_preservation_equal",
        # 数值层（_tolerance_chars 是 int，下划线排最前）
        "_tolerance_chars", "chunk_reference_intact_ratio",
        "element_count_total", "heading_boundary_compliance",
        "image_resource_exists_ratio",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        # dict 层
        "element_count_by_type",
        # null 层
        "chunk_boundary_f1", "chunk_boundary_precision",
        "chunk_boundary_recall", "docx_locator_valid_ratio",
        "error_code", "figure_caption_f1",
        "figure_caption_precision", "figure_caption_recall",
        "pdf_locator_valid_ratio", "silent_drop_count"]


def test_inspect_tolerance_line_batch135(tmp_path, capsys):
    rc, lines = _inspect(tmp_path, capsys)
    tol = [ln for ln in lines if "_tolerance_chars" in ln]
    assert tol == ["  " + "_tolerance_chars".ljust(36) +
                   " 30  (ok)"]


def test_inspect_unknown_type_dual_null_batch135(tmp_path, capsys):
    rc, lines = _inspect(tmp_path, capsys)
    pdf = [ln for ln in lines if "pdf_locator_valid_ratio" in ln]
    docx = [ln for ln in lines if "docx_locator_valid_ratio" in ln]
    assert pdf == ["  " + "pdf_locator_valid_ratio".ljust(36) +
                   " null  (not_pdf_document)"]
    assert docx == ["  " + "docx_locator_valid_ratio".ljust(36) +
                    " null  (not_docx_document)"]


# ---------- 源码补强 ----------

def _src():
    import evaluation.cli as cli_mod
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch135():
    src = _src()
    assert 'return f"  {name:36} {value:.4f}  ({reason or \'ok\'})"' in src
    assert 'items = ", ".join(f"{k}={v}" for k, v in sorted(value.items()))' in src
    assert "return (3, name)" in src
    assert "for name in sorted(metrics.keys(), key=_sort_key):" in src


# ---------- forbidden tokens 第四百零七批 ----------

def test_source_no_eval_batch135():
    assert "eval(" not in _src()


def test_source_no_exec_batch135():
    assert "exec(" not in _src()


def test_source_no_compile_batch135():
    assert "compile(" not in _src()


def test_source_no_globals_batch135():
    assert "globals(" not in _src()


def test_source_no_locals_batch135():
    assert "locals(" not in _src()


def test_source_no_os_system_batch135():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch135():
    assert "subprocess" not in _src()


def test_source_no_popen_batch135():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch135():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch135():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch135():
    assert "socket" not in _src()


def test_source_no_requests_batch135():
    assert "requests" not in _src()


def test_source_no_urllib_batch135():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch135():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch135():
    assert "yield" not in _src()


def test_source_no_async_await_batch135():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch135():
    assert _src().count("open(") == 1
