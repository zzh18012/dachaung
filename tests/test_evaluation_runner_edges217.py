"""evaluation/runner.py 第六百五十二轮 edges 测试（Round 1222）。

补强 edges216 未触及的角度（第五百九十四批，probe 实证）。

新角度（标题启发变体 / 极端 y / 跨页前向合并）：
- **标题启发变体**——四行板：
  大写短行 heading、小写短行
  （30 字符）同 heading（大小写不
  参与判定首锁）、句号结尾短行
  paragraph（句号阻断）、冒号结尾
  短行 heading（冒号不阻断）
- **极端 y 双收**——y 799 → bbox
  y0 负值（−8.5）仍收且 locator
  照 1.0；y 0 → y0 790.5
- **跨页前向合并**——mc400 第三
  块 85 字符 3 源横跨页 1 与页 2
  （标题壁垒后前向合并不忌页界
  首锁）
- **hbc 1.0**——三块首源全
  heading
- forbidden tokens 第六百九十一批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _T(t, x, y) -> bytes:
    return ("BT /F1 12 Tf %d %d Td (%s) Tj ET\n"
            % (x, y, t)).encode()


def _pdf() -> bytes:
    s1 = (_T("SECTION ONE OVERVIEW", 10, 700)
          + _T("this is a lowercase short line", 10, 660)
          + _T("Ends with period.", 10, 620)
          + _T("Trailing colon:", 10, 580))
    s2 = (_T("Text at extreme bottom y zero.", 10, 0)
          + _T("Text at extreme top y seven nine nine.",
               10, 799))
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 8\n0000000000 65535 f \n"
    for num in range(1, 8):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 8/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _pdf_path(tmp_path, doc_id):
    (tmp_path / "s").mkdir(exist_ok=True)
    p = tmp_path / "s" / f"{doc_id}.pdf"
    p.write_bytes(_pdf())
    return p


def _board(tmp_path, doc_id):
    _pdf_path(tmp_path, doc_id)
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": [{
                                  "doc_id": doc_id,
                                  "path": f"s/{doc_id}.pdf",
                                  "source_type": "pdf"}]}),
                  encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 标题启发变体 ----------

def test_heading_heuristic_variants_batch420(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "hh"), tmp_path / "o.json",
        parser_name="fallback", max_chars=400)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == [
        "heading", "heading", "paragraph",
        "heading", "paragraph", "paragraph"]
    assert els[0]["content"] == "SECTION ONE OVERVIEW"
    assert els[1]["content"] == \
        "this is a lowercase short line"
    assert els[2]["content"] == "Ends with period."
    assert els[3]["content"] == "Trailing colon:"


# ---------- 极端 y 双收 ----------

def test_extreme_y_both_parsed_batch420(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "ey"), tmp_path / "o.json",
        parser_name="fallback", max_chars=400)
    assert errors == []
    els = doc.to_dict()["elements"]
    page2 = [e for e in els
             if e["source_locator"]["page"] == 2]
    assert [e["content"] for e in page2] == [
        "Text at extreme top y seven nine nine.",
        "Text at extreme bottom y zero."]
    y0s = [round(e["source_locator"]["bbox"][1], 1)
           for e in page2]
    assert y0s == [-8.5, 790.5]


# ---------- 跨页前向合并 ----------

def test_cross_page_forward_merge_batch420(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "cp"), tmp_path / "o.json",
        parser_name="fallback", max_chars=400)
    assert errors == []
    d = doc.to_dict()
    chunks = d["chunks"]
    assert [len(c["text"]) for c in chunks] == [20, 48, 85]
    assert [len(c["source_element_ids"])
            for c in chunks] == [1, 2, 3]
    pages = [{e["source_locator"]["page"]
              for e in d["elements"]
              if e["element_id"] in
              c["source_element_ids"]}
             for c in chunks]
    assert pages == [{1}, {1}, {1, 2}]
    assert chunks[2]["text"].startswith("Trailing colon:")


# ---------- 指标 ----------

def test_metrics_batch420(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=400)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 3, "paragraph": 3},
        "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch420():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百九十一批 ----------

def test_source_no_eval_batch420():
    assert "eval(" not in _src()


def test_source_no_exec_batch420():
    assert "exec(" not in _src()


def test_source_no_compile_batch420():
    assert "compile(" not in _src()


def test_source_no_globals_batch420():
    assert "globals(" not in _src()


def test_source_no_locals_batch420():
    assert "locals(" not in _src()


def test_source_no_os_system_batch420():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch420():
    assert "subprocess" not in _src()


def test_source_no_popen_batch420():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch420():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch420():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch420():
    assert "socket" not in _src()


def test_source_no_requests_batch420():
    assert "requests" not in _src()


def test_source_no_urllib_batch420():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch420():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch420():
    assert "yield" not in _src()


def test_source_no_async_await_batch420():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch420():
    assert _src().count("open(") == 2
