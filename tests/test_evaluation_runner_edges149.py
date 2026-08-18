"""evaluation/runner.py 第五百七十四轮 edges 测试（Round 1130）。

补强 edges148 未触及的角度（第五百零六批，probe 实证）。

新角度（真实 PDF 标注通道）：
- **真 PDF 边界精确命中**——双页文本 PDF max_chars 33 劈
  两块，marker "First page body." after → 恰在块界 d=0 →
  P/R/F1 全 1.0（旧标注运行全是 docx 板，真 PDF 标注首锁）
- **真 PDF 容差翻转**——marker "Second page body." before
  落界后 1 字符（拼接空格）：tol 0 → 全 0.0、tol 30 →
  全 1.0——一刀之差在真 PDF 数据上复现
- **figure_caption 恒 null**——真 PDF 板上三通道仍 null
  parser_does_not_emit_relations
- forbidden tokens 第六百零三批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _build_pdf(texts) -> bytes:
    n_pages = len(texts)
    font_no = 3 + 2 * n_pages
    objects = {}
    kids = b" ".join(str(3 + 2 * i).encode() + b" 0 R"
                     for i in range(n_pages))
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = (b"<</Type/Pages/Kids[" + kids + b"]/Count "
                  + str(n_pages).encode() + b">>")
    for i, t in enumerate(texts):
        page_no = 3 + 2 * i
        cont_no = page_no + 1
        objects[page_no] = (
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 " + str(font_no).encode()
            + b" 0 R>>>>/Contents "
            + str(cont_no).encode() + b" 0 R>>")
        s = b"BT /F1 12 Tf 10 80 Td (" + t + b") Tj ET"
        objects[cont_no] = (
            b"<</Length " + str(len(s)).encode() + b">>stream\n"
            + s + b"\nendstream ")
    objects[font_no] = (
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    max_obj = max(objects)
    out += b"xref\n0 " + str(max_obj + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, max_obj + 1):
        if num in offsets:
            out += ("%010d 00000 n \n" % offsets[num]).encode()
        else:
            out += b"0000000000 65535 f \n"
    out += (b"trailer<</Size " + str(max_obj + 1).encode()
            + b"/Root 1 0 R>>\nstartxref\n" + str(xref_pos).encode()
            + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path, marker, position):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / "t.pdf").write_bytes(
        _build_pdf([b"First page body.", b"Second page body."]))
    (tmp_path / "anns" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "p2",
        "chunk_boundary_anchors": [
            {"marker": marker, "position": position}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "p2", "path": "samples/t.pdf",
                       "source_type": "pdf",
                       "annotation_file": "anns/a.json"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _boundary(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "First page body.", "after"),
        tmp_path / "r.json", parser_name="fallback", max_chars=33)
    return r["per_doc"][0]["metrics"]


def _flip(tmp_path, tol):
    r = run_evaluation(
        _board(tmp_path, "Second page body.", "before"),
        tmp_path / f"r{tol}.json", parser_name="fallback",
        max_chars=33, tolerance_chars=tol)
    return r["per_doc"][0]["metrics"]


# ---------- 真 PDF 边界精确命中 ----------

def test_real_pdf_annotation_exact_batch329(tmp_path):
    m = _boundary(tmp_path)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert m[k] == {"value": 1.0, "reason": None}


# ---------- 真 PDF 容差翻转 ----------

def test_real_pdf_annotation_tol0_batch329(tmp_path):
    m = _flip(tmp_path, 0)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert m[k] == {"value": 0.0, "reason": None}


def test_real_pdf_annotation_tol30_batch329(tmp_path):
    m = _flip(tmp_path, 30)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert m[k] == {"value": 1.0, "reason": None}


# ---------- figure_caption 恒 null ----------

def test_real_pdf_figure_caption_null_batch329(tmp_path):
    m = _boundary(tmp_path)
    for k in ("figure_caption_precision",
              "figure_caption_recall",
              "figure_caption_f1"):
        assert m[k] == {
            "value": None,
            "reason": "parser_does_not_emit_relations"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_inventory_batch329():
    src = _src()
    assert src.count("per_doc") == 12
    assert src.count("expected_failure") == 5


# ---------- forbidden tokens 第六百零三批 ----------

def test_source_no_eval_batch329():
    assert "eval(" not in _src()


def test_source_no_exec_batch329():
    assert "exec(" not in _src()


def test_source_no_compile_batch329():
    assert "compile(" not in _src()


def test_source_no_globals_batch329():
    assert "globals(" not in _src()


def test_source_no_locals_batch329():
    assert "locals(" not in _src()


def test_source_no_os_system_batch329():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch329():
    assert "subprocess" not in _src()


def test_source_no_popen_batch329():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch329():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch329():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch329():
    assert "socket" not in _src()


def test_source_no_requests_batch329():
    assert "requests" not in _src()


def test_source_no_urllib_batch329():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch329():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch329():
    assert "yield" not in _src()


def test_source_no_async_await_batch329():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch329():
    assert _src().count("open(") == 2
