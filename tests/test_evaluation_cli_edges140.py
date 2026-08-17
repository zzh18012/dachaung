"""evaluation/cli.py 第五百六十二轮 edges 测试（Round 1118）。

补强 edges139 未触及的角度（第四百九十四批，probe 实证）。

新角度（第三工件误喂 / 真实 parser 档案打印）：
- **annotation 喂 validate-report**：标注 JSON → rc 1 +
  [FAIL] + 6 处 + 'report_version'——misfeed 家族第三工件
  （edges125 文档 JSON、edges127 manifest 已锁，标注首锁）
- **manifest 喂 inspect-doc**：清单 JSON → rc 0 照跑 +
  type=unknown + elements=0——inspect 零校验再添一工件
  （报告 JSON edges139 已锁，清单首锁）
- **真实 kreuzberg 档案打印**：真跑 kreuzberg 产出的
  doc JSON 喂 inspect-doc → "parser:      kreuzberg
  v4.10.2"——真实 parser_name + 真实版本号上屏（旧锁
  fallback v? 是缺版本问号形态）
- forbidden tokens 第五百九十批（open 1）
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json

from docx import Document

import evaluation.cli as cli_mod
from app.pipeline import process_single
from evaluation.cli import main


def _annotation_file(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "before"}]}),
        encoding="utf-8")
    return p


def _manifest_file(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    d = Document()
    d.add_paragraph("AAA body.")
    d.save(str(tmp_path / "samples" / "g.docx"))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/g.docx",
                       "source_type": "docx"}]}),
        encoding="utf-8")
    return mf


# ---------- annotation 喂 validate-report ----------

def test_annotation_into_validate_report_batch317(
        tmp_path, capsys):
    rc = main(["validate-report",
               str(_annotation_file(tmp_path))])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err
    assert "'report_version' is a required property" in err
    assert "6 处" in err


# ---------- manifest 喂 inspect-doc ----------

def test_manifest_into_inspect_doc_batch317(tmp_path):
    rc = main(["inspect-doc",
               str(_manifest_file(tmp_path))])
    assert rc == 0


# ---------- 真实 kreuzberg 档案打印 ----------

def test_inspect_doc_real_kreuzberg_parser_batch317(tmp_path):
    mf = _manifest_file(tmp_path)
    src = json.loads(mf.read_text(encoding="utf-8"))
    docx_path = tmp_path / src["documents"][0]["path"]
    doc, errors = process_single(
        docx_path, tmp_path / "doc.json",
        parser_name="kreuzberg", max_chars=200,
        write_json=True)
    assert errors == []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["inspect-doc", str(tmp_path / "doc.json")])
    assert rc == 0
    assert "parser:      kreuzberg v4.10.2" in buf.getvalue()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch317():
    src = _src()
    assert "报告不存在" in src
    assert "文档不存在" in src


# ---------- forbidden tokens 第五百九十批 ----------

def test_source_no_eval_batch317():
    assert "eval(" not in _src()


def test_source_no_exec_batch317():
    assert "exec(" not in _src()


def test_source_no_compile_batch317():
    assert "compile(" not in _src()


def test_source_no_globals_batch317():
    assert "globals(" not in _src()


def test_source_no_locals_batch317():
    assert "locals(" not in _src()


def test_source_no_os_system_batch317():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch317():
    assert "subprocess" not in _src()


def test_source_no_popen_batch317():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch317():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch317():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch317():
    assert "socket" not in _src()


def test_source_no_requests_batch317():
    assert "requests" not in _src()


def test_source_no_urllib_batch317():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch317():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch317():
    assert "yield" not in _src()


def test_source_no_async_await_batch317():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch317():
    assert _src().count("open(") == 1
