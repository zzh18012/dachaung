"""evaluation/runner.py 第五百八十三轮 edges 测试（Round 1139）。

补强 edges157 未触及的角度（第五百一十五批，probe 实证）。

新角度（图片多实例 / 空白页图片 / image 型 expectations）：
- **同页双图双元素**——同一 Im0 画两次（不同 cm 矩阵）→
  2 个 image 元素 bbox 恰 [10,50,40,80] 与
  [100,50,130,80]——XObject 复用不合并元素（首锁）
- **空白页图片保号**——页 1 空内容流、页 2 仅图片 →
  唯一元素 page 恰 2——空白页跳过对图片内容同样成立
- **image 型 expectations**——{image: 3} 配真实 2 图 →
  silent_drop_count 1——旧锁全是 paragraph/table/heading
  键，image 键真跑首锁
- forbidden tokens 第六百一十二批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


_IMG_OBJ = (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8"
            b"/Length 3>>stream\n\xff\x00\x00\nendstream ")


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


def _two_images_pdf() -> bytes:
    s = (b"q 30 0 0 30 10 20 cm /Im0 Do Q\n"
         b"q 30 0 0 30 100 20 cm /Im0 Do Q")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</XObject<</Im0 5 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: _IMG_OBJ,
    }, 6)


def _blank_then_image_pdf() -> bytes:
    s = b"q 30 0 0 30 10 20 cm /Im0 Do Q"
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<<>>/Contents 4 0 R>>"),
        4: b"<</Length 0>>stream\n\nendstream ",
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</XObject<</Im0 7 0 R>>>>"
            b"/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        7: _IMG_OBJ,
    }, 8)


def _board(tmp_path, pdf_bytes, doc_id, expectations=None):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
    doc_entry = {"doc_id": doc_id,
                 "path": f"samples/{doc_id}.pdf",
                 "source_type": "pdf"}
    if expectations is not None:
        doc_entry["expectations"] = expectations
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [doc_entry]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 同页双图双元素 ----------

def test_two_images_two_elements_batch338(tmp_path):
    _board(tmp_path, _two_images_pdf(), "ti")
    doc, errors = process_single(
        tmp_path / "samples" / "ti.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 2
    assert [e["source_locator"]["bbox"] for e in els] == [
        [10.0, 50.0, 40.0, 80.0], [100.0, 50.0, 130.0, 80.0]]
    assert all(e["type"] == "image" for e in els)
    assert doc.to_dict()["chunks"] == []


# ---------- 空白页图片保号 ----------

def test_blank_then_image_page_batch338(tmp_path):
    _board(tmp_path, _blank_then_image_pdf(), "bi")
    doc, errors = process_single(
        tmp_path / "samples" / "bi.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["source_locator"]["page"] == 2


# ---------- image 型 expectations ----------

def test_image_expectations_drop_batch338(tmp_path):
    r = run_evaluation(
        _board(tmp_path, _two_images_pdf(), "ti2",
               expectations={
                   "element_count_by_type": {"image": 3}}),
        tmp_path / "r.json", parser_name="fallback", max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"image": 2}, "reason": None}
    assert m["silent_drop_count"] == {"value": 1, "reason": None}


def test_image_expectations_exact_batch338(tmp_path):
    r = run_evaluation(
        _board(tmp_path, _two_images_pdf(), "ti3",
               expectations={
                   "element_count_by_type": {"image": 2}}),
        tmp_path / "r.json", parser_name="fallback", max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["silent_drop_count"] == {"value": 0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch338():
    src = _src()
    assert src.count("chunk") == 9
    assert src.count("annotation") == 10
    assert src.count("run_evaluation") == 2


# ---------- forbidden tokens 第六百一十二批 ----------

def test_source_no_eval_batch338():
    assert "eval(" not in _src()


def test_source_no_exec_batch338():
    assert "exec(" not in _src()


def test_source_no_compile_batch338():
    assert "compile(" not in _src()


def test_source_no_globals_batch338():
    assert "globals(" not in _src()


def test_source_no_locals_batch338():
    assert "locals(" not in _src()


def test_source_no_os_system_batch338():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch338():
    assert "subprocess" not in _src()


def test_source_no_popen_batch338():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch338():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch338():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch338():
    assert "socket" not in _src()


def test_source_no_requests_batch338():
    assert "requests" not in _src()


def test_source_no_urllib_batch338():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch338():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch338():
    assert "yield" not in _src()


def test_source_no_async_await_batch338():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch338():
    assert _src().count("open(") == 2
