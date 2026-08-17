"""evaluation/cli.py 第四百四十四轮 edges 测试（Round 1000）。

补强 edges122 未触及的角度（第三百七十六批，probe 实证）。

新角度（复合集成）：
- inspect-doc 富文档 5 行头部一次锁（file/document_id/
  source/parser/counts）
- 分桶全序快照：首行 pipeline_success true；泄漏键
  _tolerance_chars 30 落数值桶（bool 桶之后）；by_type
  dict 桶 paragraph=1；null 桶含 no_annotation 三连与
  parser_does_not_emit_relations 三连
- run 子命令 rc 2（清单不存在）vs rc 1（清单加载失败，
  绝对路径文档）一双一定：文件级错误码 2、内容级错误码 1
- chunk_boundary_f1 null "no_annotation"（无标注固定 null）
- forbidden tokens 第四百七十批（open 1）
"""

from __future__ import annotations

import inspect
import io
import contextlib

import evaluation.cli as cli_mod
from evaluation.cli import main


def _rich_doc():
    return {
        "schema_version": "0.1.0", "document_id": "doc-42",
        "source_path": "in/x.pdf", "source_type": "pdf",
        "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "9.9",
        "elements": [
            {"element_id": "e1", "type": "paragraph",
             "content": "hello world", "parent_id": None,
             "confidence": 0.9, "metadata": {},
             "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}}],
        "chunks": [{"chunk_id": "c1", "text": "hello world",
                    "source_element_ids": ["e1"],
                    "char_count": 11}],
        "relations": [], "warnings": [], "errors": [],
        "metadata": {}}


def _inspect(tmp_path, doc=None):
    import json
    f = tmp_path / "d.json"
    f.write_text(json.dumps(doc or _rich_doc()), encoding="utf-8")
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), \
            contextlib.redirect_stderr(err):
        rc = main(["inspect-doc", str(f)])
    return rc, buf.getvalue(), err.getvalue()


# ---------- 富文档头部 ----------

def test_rich_inspect_doc_header_batch198(tmp_path):
    rc, out, _ = _inspect(tmp_path)
    assert rc == 0
    lines = out.splitlines()
    assert lines[0].startswith("file:        ")
    assert lines[0].endswith("d.json")
    assert lines[1] == "document_id: doc-42"
    assert lines[2] == "source:      in/x.pdf  type=pdf"
    assert lines[3] == "parser:      fallback v9.9"
    assert lines[4] == "counts:      elements=1 chunks=1"


# ---------- 分桶全序 ----------

def test_rich_inspect_doc_bucket_order_batch198(tmp_path):
    rc, out, _ = _inspect(tmp_path)
    metric_lines = [ln for ln in out.splitlines()
                    if ln.startswith("  ")]
    assert metric_lines[0] == \
        "  pipeline_success                     true  (ok)"
    assert "  _tolerance_chars                     30  (ok)" \
        in metric_lines
    assert metric_lines.index(
        "  pipeline_success                     true  (ok)") < \
        metric_lines.index(
            "  _tolerance_chars                     30  (ok)")
    assert ("  element_count_by_type                "
            "paragraph=1  (ok)") in metric_lines
    assert ("  chunk_boundary_f1                    null  "
            "(no_annotation)") in metric_lines
    assert ("  figure_caption_f1                    null  "
            "(parser_does_not_emit_relations)") in metric_lines


# ---------- rc 2 vs rc 1 ----------

def test_run_rc2_vs_rc1_pair_batch198(tmp_path, capsys):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    rc2 = main(["run", "--manifest",
                str(tmp_path / "nope.json"), "--output",
                str(tmp_path / "o.json")])
    assert rc2 == 2
    assert "[ERROR] 清单不存在" in capsys.readouterr().err

    import json
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "C:/abs/x.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    rc1 = main(["run", "--manifest", str(mf), "--output",
                str(tmp_path / "o.json")])
    assert rc1 == 1
    assert "[ERROR] 清单加载失败" in capsys.readouterr().err
    assert not (tmp_path / "o.json").exists()


# ---------- 无标注边界 null ----------

def test_inspect_doc_boundary_null_no_annotation_batch198(
        tmp_path):
    rc, out, _ = _inspect(tmp_path)
    assert rc == 0
    assert ("chunk_boundary_f1                    null  "
            "(no_annotation)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch198():
    src = _src()
    assert 'choices=("fallback", "kreuzberg"),' in src
    assert 'f"[FAIL] {input_path} 报告校验失败：{e}"' in src
    assert 'return f"  {name:36} {str(value).lower()}  ({reason or \'ok\'})"' in src
    assert "for name in sorted(metrics.keys(), key=_sort_key):" in src


# ---------- forbidden tokens 第四百七十批 ----------

def test_source_no_eval_batch198():
    assert "eval(" not in _src()


def test_source_no_exec_batch198():
    assert "exec(" not in _src()


def test_source_no_compile_batch198():
    assert "compile(" not in _src()


def test_source_no_globals_batch198():
    assert "globals(" not in _src()


def test_source_no_locals_batch198():
    assert "locals(" not in _src()


def test_source_no_os_system_batch198():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch198():
    assert "subprocess" not in _src()


def test_source_no_popen_batch198():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch198():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch198():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch198():
    assert "socket" not in _src()


def test_source_no_requests_batch198():
    assert "requests" not in _src()


def test_source_no_urllib_batch198():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch198():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch198():
    assert "yield" not in _src()


def test_source_no_async_await_batch198():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch198():
    assert _src().count("open(") == 1
