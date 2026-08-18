"""evaluation/cli.py 第六百三十三轮 edges 测试（Round 1189）。

补强 cli edges147 未触及的角度（第五百六十一批，probe 实证）。

新角度（无文本格图板的 inspect-doc 全景）：
- **counts 行**——"counts:      elements=2
  chunks=1"（格图板：2 元素仅 1 表块）
- **by_type 行**——"image=1, table=1"
  （键排序 + dict 型排 numeric 后）
- **null reason 全景**——no_annotation /
  not_docx_document / parser_does_not_
  emit_relations / no_heading_elements /
  no_expectations 五 reason 同屏；error_
  code 的 reason None 打 "(None)"
- **排序三段**——bool 类 → numeric/dict
  类 → null 类（索引序首锁）
- **parser 行**——fallback vpdfplumber=
  0.11.10 版本串
- forbidden tokens 第五百六十一批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


def _notext_pdf() -> bytes:
    png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
           b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
           b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
           b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
    s = (b"1 w 0 G\n10 300 100 50 re S\n60 300 0 50 re S\n"
         b"10 350 100 0 re S\nq 30 0 0 30 50 100 cm /Im0 Do Q\n")
    out = bytearray(b"%PDF-1.4\n")
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
            b"/Resources<</Font<</F1 5 0 R>>"
            b"/XObject<</Im0 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
            + str(len(png)).encode() + b">>stream\n" + png
            + b"\nendstream "),
    }
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += str(num).encode() + b" 0 obj" + objs[num] + b"endobj\n"
    xref_pos = len(out)
    out += b"xref\n0 7\n0000000000 65535 f \n"
    for num in range(1, 7):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 7/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _doc(tmp_path):
    from app.pipeline import process_single
    (tmp_path / "samples").mkdir(exist_ok=True)
    p = tmp_path / "samples" / "nt.pdf"
    p.write_bytes(_notext_pdf())
    doc, errors = process_single(
        p, tmp_path / "doc.json", parser_name="fallback",
        max_chars=200)
    assert errors == []
    return tmp_path / "doc.json"


def _manifest(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "nt.pdf").write_bytes(_notext_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "nt", "path": "samples/nt.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


# ---------- counts / by_type ----------

def test_cli_inspect_notext_counts_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=2 chunks=1" in out


def test_cli_inspect_bytype_line_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "image=1, table=1  (ok)" in out


# ---------- null reason 全景 ----------

def test_cli_inspect_null_reasons_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "null  (no_annotation)" in out
    assert "null  (not_docx_document)" in out
    assert "null  (parser_does_not_emit_relations)" in out
    assert "null  (no_heading_elements)" in out
    assert "null  (no_expectations)" in out


def test_cli_inspect_error_code_none_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "error_code" in out
    assert "null  (None)" in out


def test_cli_inspect_tolerance_line_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "_tolerance_chars                     30  (ok)" in out


# ---------- 排序三段 ----------

def test_cli_inspect_metric_order_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    i_bool = out.index("pipeline_success")
    i_num = out.index("image=1, table=1")
    i_null = out.index("chunk_boundary_f1")
    assert i_bool < i_num < i_null


# ---------- 元信息行 ----------

def test_cli_inspect_parser_line_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "parser:      fallback v" in out
    assert "pdfplumber=0.11.10" in out


def test_cli_inspect_source_line_batch387(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "type=pdf" in out


# ---------- run 通道 ----------

def test_cli_run_notext_batch387(tmp_path, capsys):
    mf = _manifest(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"table": 1, "image": 1}, "reason": None}
    assert m["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


def test_cli_run_notext_stdout_batch387(tmp_path, capsys):
    mf = _manifest(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "documents=1（成功 1，失败 0）" in out
    assert "pdf=1 docx=0" in out


def test_cli_validate_notext_report_batch387(tmp_path, capsys):
    mf = _manifest(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rc2, out2 = _run_cli(capsys, [
        "validate-report", str(tmp_path / "r.json")])
    assert rc2 == 0
    assert "[OK]" in out2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch387():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百六十一批 ----------

def test_source_no_eval_batch387():
    assert "eval(" not in _src()


def test_source_no_exec_batch387():
    assert "exec(" not in _src()


def test_source_no_compile_batch387():
    assert "compile(" not in _src()


def test_source_no_globals_batch387():
    assert "globals(" not in _src()


def test_source_no_locals_batch387():
    assert "locals(" not in _src()


def test_source_no_os_system_batch387():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch387():
    assert "subprocess" not in _src()


def test_source_no_popen_batch387():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch387():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch387():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch387():
    assert "socket" not in _src()


def test_source_no_requests_batch387():
    assert "requests" not in _src()


def test_source_no_urllib_batch387():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch387():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch387():
    assert "yield" not in _src()


def test_source_no_async_await_batch387():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch387():
    assert _src().count("open(") == 1
