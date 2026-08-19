"""evaluation/cli.py 第六百六十九轮 edges 测试（Round 1298）。

补强 edges167 未触及的角度（第六百七十批，probe 实证）。

新角度（双文档 CLI 全链 / 图片板 inspect-doc）：
- **双文档混合 run**——d1 锚
  定 + d2 无标注 → rc 0 +
  'documents=2（成功 2，
  失败 0）' + 'file_count=2
  groups=2 pdf=2 docx=0'
  （多文档输出行首锁）
- **混合报告过 Schema**——
  cbp {1/15, 1 参与, 1 未评}
  的报告 validate-report
  通关（劈叉聚合形态合法）
- **图片板 parse**——
  (elements=3, chunks=16,
  warnings=0)（三型板跨
  CLI 计数首锁）
- **图片板 inspect-doc**——
  ecbt 行 'heading=1,
  image=1, paragraph=1'
  （image 入表 + 序首锁）；
  irer 行 1.0000 (ok)（实
  文件命中）；counts 行
  elements=3 chunks=16
- forbidden tokens 第五百九十批（open 1）
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


@pytest.fixture(autouse=True)
def _restore_argv():
    saved = sys.argv
    yield
    sys.argv = saved


def _wrap(s: bytes) -> bytes:
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


def _image_pdf(content: bytes) -> bytes:
    img = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255,
                 255, 255, 0])
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>"
            b"/XObject<</Im0 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(content)).encode()
            + b">>stream\n" + content + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/XObject/Subtype/Image/Width 2/Height 2"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
            + str(len(img)).encode()
            + b">>stream\n" + img + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 7\n0000000000 65535 f \n"
    for num in range(1, 7):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 7/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
HEAD = "A" * 80
STREAM = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
          + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
          % LONG).encode()


def _dual_manifest(tmp_path):
    (tmp_path / "c1.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "c2.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a1.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "c1.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/a1.json"},
            {"doc_id": "d2", "path": "c2.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    return str(tmp_path / "m.json")


def _dual_run(tmp_path, capsys):
    rep = tmp_path / "r.json"
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _dual_manifest(tmp_path),
                "--output", str(rep), "--parser", "fallback",
                "--max-chars", "32"]
    rc = main()
    out = capsys.readouterr().out
    return rc, out, json.loads(
        rep.read_text(encoding="utf-8"))


# ---------- 双文档混合 run ----------

def test_dual_run_rc_ok_batch496(tmp_path, capsys):
    rc, out, _ = _dual_run(tmp_path, capsys)
    assert rc == 0
    assert "documents=2（成功 2，失败 0）" in out


def test_dual_run_devset_line_batch496(tmp_path, capsys):
    _, out, _ = _dual_run(tmp_path, capsys)
    assert ("devset_status=incomplete file_count=2 "
            "groups=2 pdf=2 docx=0") in out


def test_dual_run_mixed_agg_batch496(tmp_path, capsys):
    _, _, report = _dual_run(tmp_path, capsys)
    assert report["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": 1 / 15, "participating_docs": 1,
        "not_evaluated": 1}


def test_dual_run_d2_no_annotation_batch496(
        tmp_path, capsys):
    _, _, report = _dual_run(tmp_path, capsys)
    m = report["per_doc"][1]["metrics"]
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_annotation"}


def test_dual_report_validates_batch496(tmp_path, capsys):
    _dual_run(tmp_path, capsys)
    rep = str(tmp_path / "r.json")
    sys.argv = ["evaluation.cli", "validate-report", rep]
    assert main() == 0
    assert "通过 evaluation-report Schema 校验" in \
        capsys.readouterr().out


# ---------- 图片板 parse ----------

def _img_doc(tmp_path, capsys):
    content = (b"q 100 0 0 50 10 500 cm /Im0 Do Q\n"
               + ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
                  % HEAD).encode()
               + ("BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
                  % LONG).encode())
    (tmp_path / "img.pdf").write_bytes(_image_pdf(content))
    from app.cli import main as app_main
    doc_json = str(tmp_path / "d.json")
    sys.argv = ["app.cli", "parse", str(tmp_path / "img.pdf"),
                "-o", doc_json, "--parser", "fallback",
                "--max-chars", "32"]
    rc = app_main()
    out = capsys.readouterr().out
    return rc, out, doc_json


def test_image_parse_ok_line_batch496(tmp_path, capsys):
    rc, out, _ = _img_doc(tmp_path, capsys)
    assert rc == 0
    assert "(elements=3, chunks=16, warnings=0)" in out


# ---------- 图片板 inspect-doc ----------

def test_image_inspect_counts_batch496(tmp_path, capsys):
    _, _, doc_json = _img_doc(tmp_path, capsys)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    assert main() == 0
    out = capsys.readouterr().out
    assert "counts:      elements=3 chunks=16" in out


def test_image_inspect_ecbt_line_batch496(tmp_path, capsys):
    _, _, doc_json = _img_doc(tmp_path, capsys)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert (f"  {'element_count_by_type':36}"
            " heading=1, image=1, paragraph=1  (ok)"
            in out)


def test_image_inspect_irer_line_batch496(tmp_path, capsys):
    _, _, doc_json = _img_doc(tmp_path, capsys)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert (f"  {'image_resource_exists_ratio':36}"
            " 1.0000  (ok)" in out)


def test_image_inspect_total_line_batch496(
        tmp_path, capsys):
    _, _, doc_json = _img_doc(tmp_path, capsys)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert f"  {'element_count_total':36} 3  (ok)" in out


def test_image_inspect_boundary_null_batch496(
        tmp_path, capsys):
    _, _, doc_json = _img_doc(tmp_path, capsys)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert (f"  {'chunk_boundary_f1':36}"
            " null  (no_annotation)" in out)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch496():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百九十批 ----------

def test_source_no_eval_batch496():
    assert "eval(" not in _src()


def test_source_no_exec_batch496():
    assert "exec(" not in _src()


def test_source_no_compile_batch496():
    assert "compile(" not in _src()


def test_source_no_globals_batch496():
    assert "globals(" not in _src()


def test_source_no_locals_batch496():
    assert "locals(" not in _src()


def test_source_no_os_system_batch496():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch496():
    assert "subprocess" not in _src()


def test_source_no_popen_batch496():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch496():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch496():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch496():
    assert "socket" not in _src()


def test_source_no_requests_batch496():
    assert "requests" not in _src()


def test_source_no_urllib_batch496():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch496():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch496():
    assert "yield" not in _src()


def test_source_no_async_await_batch496():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch496():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch496():
    assert _src().count("open(") == 1
