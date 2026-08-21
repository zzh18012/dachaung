"""evaluation/metrics.py 第五百七十三轮 edges 测试（Round 1302）。

补强 edges151 未触及的角度（第六百七十四批，probe 实证）。

新角度（双标题板 heading 分块几何）：
- **mc10000 双块不合一**——
  h1+h2+段落 → 2 块：[h1]
  与 [h2+段落]（标题强制
  开新块——h2 吸收后随段落
  而 h1 独留；极端 mc 下
  heading-first 不变量
  首锁）
- **块 1 合并体**——text
  550 = 80+1+469；ids
  [e0001, e0002]；spans
  [(e0001,0,80),
  (e0002,0,469)]
- **hbc 双标题全中**——2
  标题均块首 → 1.0（双 mc
  皆同）
- **mc32 晶格**——17 块；
  首三块 [80, 80, 27]；
  strategies
  [sequential,
  sequential,
  long_paragraph_sentence_
  split]
- **sdc 标题面**——
  {heading:2, paragraph:1}
  → 0；{heading:3} → 1
  （单型多计首锁）
- forbidden tokens 第七百五十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from app.pipeline import process_single
from evaluation.metrics import compute_automatic_metrics


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


LONG = " ".join("Word%d." % i for i in range(60))
H1 = "A" * 80
H2 = "B" * 80
STREAM = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % H1
          + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n" % H2
          + "BT /F1 12 Tf 10 620 Td (%s) Tj ET\n"
          % LONG).encode()


def _doc(tmp_path, mc):
    p = tmp_path / "c.pdf"
    p.write_bytes(_wrap(STREAM))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=mc)
    assert errors == []
    return doc.to_dict()


def _m(dd, exp=None):
    return compute_automatic_metrics(dd, None, "pdf", exp)


# ---------- mc10000 双块不合一 ----------

def test_10k_two_chunks_batch500(tmp_path):
    dd = _doc(tmp_path, 10000)
    assert len(dd["chunks"]) == 2


def test_10k_chunk0_alone_batch500(tmp_path):
    dd = _doc(tmp_path, 10000)
    c0 = dd["chunks"][0]
    assert len(c0["text"]) == 80
    assert c0["source_element_ids"][0].endswith("::e0000")
    assert len(c0["source_spans"]) == 1


def test_10k_chunk1_merge_body_batch500(tmp_path):
    dd = _doc(tmp_path, 10000)
    c1 = dd["chunks"][1]
    assert len(c1["text"]) == 550
    assert [i[-6:] for i in c1["source_element_ids"]] == [
        ":e0001", ":e0002"]
    spans = [(sp["element_id"][-6:], sp["start"], sp["end"])
             for sp in c1["source_spans"]]
    assert spans == [(":e0001", 0, 80), (":e0002", 0, 469)]


def test_10k_chunk1_text_head_batch500(tmp_path):
    dd = _doc(tmp_path, 10000)
    assert dd["chunks"][1]["text"][:85] == H2 + " Word"


# ---------- hbc 双标题全中 ----------

def test_hbc_10k_batch500(tmp_path):
    m = _m(_doc(tmp_path, 10000))
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_hbc_32_batch500(tmp_path):
    m = _m(_doc(tmp_path, 32))
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_ecbt_two_headings_batch500(tmp_path):
    m = _m(_doc(tmp_path, 10000))
    assert m["element_count_by_type"]["value"] == {
        "heading": 2, "paragraph": 1}


def test_element_order_batch500(tmp_path):
    dd = _doc(tmp_path, 10000)
    assert [e["type"] for e in dd["elements"]] == [
        "heading", "heading", "paragraph"]


# ---------- mc32 晶格 ----------

def test_32_chunk_count_batch500(tmp_path):
    assert len(_doc(tmp_path, 32)["chunks"]) == 17


def test_32_first3_lens_batch500(tmp_path):
    dd = _doc(tmp_path, 32)
    assert [len(c["text"]) for c in dd["chunks"][:3]] == [
        80, 80, 27]


def test_32_strategies_batch500(tmp_path):
    dd = _doc(tmp_path, 32)
    assert [c["metadata"]["strategy"]
            for c in dd["chunks"][:3]] == [
        "sequential", "sequential",
        "long_paragraph_sentence_split"]


# ---------- 文本面 ----------

def test_tpe_both_mc_batch500(tmp_path):
    assert _m(_doc(tmp_path, 32))[
        "text_preservation_equal"]["value"] is True
    assert _m(_doc(tmp_path, 10000))[
        "text_preservation_equal"]["value"] is True


def test_plvr_both_mc_batch500(tmp_path):
    for mc in (32, 10000):
        assert _m(_doc(tmp_path, mc))[
            "pdf_locator_valid_ratio"] == {
            "value": 1.0, "reason": None}


# ---------- sdc 标题面 ----------

def test_sdc_exact_batch500(tmp_path):
    m = _m(_doc(tmp_path, 10000),
           {"element_count_by_type": {
               "heading": 2, "paragraph": 1}})
    assert m["silent_drop_count"] == {"value": 0,
                                      "reason": None}


def test_sdc_heading_three_batch500(tmp_path):
    m = _m(_doc(tmp_path, 10000),
           {"element_count_by_type": {"heading": 3}})
    assert m["silent_drop_count"] == {"value": 1,
                                      "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch500():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百五十一批 ----------

def test_source_no_eval_batch500():
    assert "eval(" not in _src()


def test_source_no_exec_batch500():
    assert "exec(" not in _src()


def test_source_no_compile_batch500():
    assert "compile(" not in _src()


def test_source_no_globals_batch500():
    assert "globals(" not in _src()


def test_source_no_locals_batch500():
    assert "locals(" not in _src()


def test_source_no_os_system_batch500():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch500():
    assert "subprocess" not in _src()


def test_source_no_popen_batch500():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch500():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch500():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch500():
    assert "socket" not in _src()


def test_source_no_requests_batch500():
    assert "requests" not in _src()


def test_source_no_urllib_batch500():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch500():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch500():
    assert "yield" not in _src()


def test_source_no_async_await_batch500():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch500():
    assert _src().count("open(") == 0
