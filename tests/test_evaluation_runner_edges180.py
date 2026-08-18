"""evaluation/runner.py 第六百零八轮 edges 测试（Round 1164）。

补强 edges179 未触及的角度（第五百三十六批，probe 实证）。

新角度（PDF 五型同页全通道）：
- **五型同页**——caption + paragraph + heading +
  table + image 单 PDF 页 → elements 恰五型各一
  （PDF 侧五型同文档首锁，与 edges177 的 DOCX
  五型成对照）
- **类别序 text→table→image**——文本元素按 y
  序在前、表格次之、图片殿后（三类抽排序首锁）
- **heading 软界切前段**——y=330 段落与 y=205
  格字 heading 不合块：4 chunks [isolated_
  caption, sequential, sequential, isolated_
  table]；image 无块
- forbidden tokens 第六百三十六批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_pdf(objects, n_obj) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 " + str(n_obj).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, n_obj):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size " + str(n_obj).encode()
            + b"/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _five_type_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 180 100 50 re S\n60 180 0 50 re S\n"
         b"10 230 100 0 re S\n"
         b"q 40 0 0 40 200 300 cm /Im0 Do Q\n"
         b"BT /F1 10 Tf 15 205 Td (Ga) Tj ET\n"
         b"BT /F1 10 Tf 65 205 Td (Gb) Tj ET\n"
         b"BT /F1 12 Tf 10 390 Td "
         b"(Figure 3: pdf caption text.) Tj ET\n"
         b"BT /F1 12 Tf 10 330 Td "
         b"(Regular paragraph with a period.) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
            b"/Resources<</XObject<</Im0 6 0 R>>"
            b"/Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8"
            b"/Length 3>>stream\n" + b"\xff\x00\x00"
            + b"\nendstream "),
    }, 7)


def _board(tmp_path, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _five_type_pdf())
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 五型同页 ----------

def test_pdf_five_types_order_batch362(tmp_path):
    _board(tmp_path, "pf")
    doc, errors = process_single(
        tmp_path / "samples" / "pf.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "caption", "paragraph", "heading", "table", "image"]
    assert els[0]["content"] == "Figure 3: pdf caption text."
    assert els[1]["content"] == \
        "Regular paragraph with a period."
    assert els[2]["content"] == "Ga Gb"
    assert els[4]["content"] is None


def test_pdf_table_before_image_batch362(tmp_path):
    _board(tmp_path, "pf2")
    doc, errors = process_single(
        tmp_path / "samples" / "pf2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert all(e["source_locator"]["page"] == 1 for e in els)
    assert els[3]["type"] == "table"
    assert els[4]["type"] == "image"
    assert els[3]["content"] == "| Ga | Gb |\n| --- | --- |"


# ---------- heading 软界切前段 ----------

def test_pdf_five_types_chunks_batch362(tmp_path):
    _board(tmp_path, "pf3")
    doc, errors = process_single(
        tmp_path / "samples" / "pf3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    dd = doc.to_dict()
    img_id = [e["element_id"] for e in dd["elements"]
              if e["type"] == "image"][0]
    chunks = dd["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "isolated_caption", "sequential", "sequential",
        "isolated_table"]
    assert chunks[1]["text"] == \
        "Regular paragraph with a period."
    assert chunks[2]["text"] == "Ga Gb"
    for c in chunks:
        assert img_id not in c["source_element_ids"]


# ---------- 指标 ----------

def test_pdf_five_types_metrics_batch362(tmp_path):
    r = run_evaluation(_board(tmp_path, "pf4"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"caption": 1, "paragraph": 1, "heading": 1,
                  "table": 1, "image": 1},
        "reason": None}
    assert m["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pipeline_success"] == {"value": True,
                                     "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch362():
    src = _src()
    assert src.count("metrics") == 13
    assert src.count("chunk") == 9
    assert src.count("manifest") == 5


# ---------- forbidden tokens 第六百三十六批 ----------

def test_source_no_eval_batch362():
    assert "eval(" not in _src()


def test_source_no_exec_batch362():
    assert "exec(" not in _src()


def test_source_no_compile_batch362():
    assert "compile(" not in _src()


def test_source_no_globals_batch362():
    assert "globals(" not in _src()


def test_source_no_locals_batch362():
    assert "locals(" not in _src()


def test_source_no_os_system_batch362():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch362():
    assert "subprocess" not in _src()


def test_source_no_popen_batch362():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch362():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch362():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch362():
    assert "socket" not in _src()


def test_source_no_requests_batch362():
    assert "requests" not in _src()


def test_source_no_urllib_batch362():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch362():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch362():
    assert "yield" not in _src()


def test_source_no_async_await_batch362():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch362():
    assert _src().count("open(") == 2
