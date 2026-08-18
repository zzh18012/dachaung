"""evaluation/metrics.py 第五百六十八轮 edges 测试（Round 1272）。

补强 edges146 未触及的角度（第六百四十四批，probe 实证）。

新角度（长段落句切 / 类型依赖分裂策略）：
- **长段单元素句切**——469 字符
  段落 mc 100 → 5 块 [93, 95,
  95, 95, 87] 全
  long_paragraph_sentence_split
- **mc 32 极限切**——15 块全部
  ≤ 31（句子打包到地板下）
- **同板类型对照首锁**——
  heading 80 原子不切（过冲
  48）与 paragraph 469 切 15 块
  并存同 mc → 类型依赖分裂
  策略（strategy 计数 {句切 15,
  sequential 1}）
- **指标保全**——tpe True /
  intact 1.0 / multiset 全 1.0
  跨 16 块
- forbidden tokens 第七百三十二批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
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


def _long_pdf() -> bytes:
    return _wrap(("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
                  % LONG).encode())


def _combo_pdf() -> bytes:
    return _wrap(
        ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % ("A" * 80)
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode())


def _doc(tmp_path, pdf, mc):
    from app.pipeline import process_single
    p = tmp_path / "d.pdf"
    p.write_bytes(pdf)
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=mc)
    assert errors == []
    return doc.to_dict()


# ---------- 长段单元素句切 ----------

def test_long_para_len_469_batch470(tmp_path):
    dd = _doc(tmp_path, _long_pdf(), 100)
    assert dd["elements"][0]["content"] == LONG
    assert len(LONG) == 469


def test_long_para_mc100_five_batch470(tmp_path):
    dd = _doc(tmp_path, _long_pdf(), 100)
    assert [len(c["text"]) for c in dd["chunks"]] == [
        93, 95, 95, 95, 87]


def test_long_para_strategy_batch470(tmp_path):
    dd = _doc(tmp_path, _long_pdf(), 100)
    assert {c["metadata"]["strategy"]
            for c in dd["chunks"]} == {
        "long_paragraph_sentence_split"}


def test_long_para_mc32_fifteen_batch470(tmp_path):
    dd = _doc(tmp_path, _long_pdf(), 32)
    assert len(dd["chunks"]) == 15
    assert max(len(c["text"]) for c in dd["chunks"]) <= 31


def test_long_para_all_single_src_batch470(tmp_path):
    dd = _doc(tmp_path, _long_pdf(), 100)
    assert all(len(c["source_element_ids"]) == 1
               for c in dd["chunks"])


def test_long_para_metrics_batch470(tmp_path):
    for mc in (100, 32):
        m = compute_automatic_metrics(
            _doc(tmp_path, _long_pdf(), mc), None, "pdf", None)
        assert m["text_preservation_equal"] == {
            "value": True, "reason": None}
        assert m["chunk_reference_intact_ratio"] == {
            "value": 1.0, "reason": None}
        assert m["text_char_multiset_precision"] == {
            "value": 1.0, "reason": None}
        assert m["text_char_multiset_recall"] == {
            "value": 1.0, "reason": None}


# ---------- 同板类型对照 ----------

def test_combo_elements_batch470(tmp_path):
    dd = _doc(tmp_path, _combo_pdf(), 32)
    assert [(e["type"], len(e["content"]))
            for e in dd["elements"]] == [
        ("heading", 80), ("paragraph", 469)]


def test_combo_16_chunks_batch470(tmp_path):
    assert len(_doc(tmp_path, _combo_pdf(), 32)["chunks"]) == 16


def test_combo_strategy_counts_batch470(tmp_path):
    dd = _doc(tmp_path, _combo_pdf(), 32)
    strategies = [c["metadata"]["strategy"]
                  for c in dd["chunks"]]
    assert strategies.count(
        "long_paragraph_sentence_split") == 15
    assert strategies.count("sequential") == 1


def test_combo_heading_chunk_atomic_batch470(tmp_path):
    dd = _doc(tmp_path, _combo_pdf(), 32)
    c0 = dd["chunks"][0]
    assert len(c0["text"]) == 80
    assert c0["metadata"]["strategy"] == "sequential"
    assert len(c0["source_element_ids"]) == 1


def test_combo_heading_overshoot_48_batch470(tmp_path):
    dd = _doc(tmp_path, _combo_pdf(), 32)
    assert len(dd["chunks"][0]["text"]) - 32 == 48


def test_combo_para_chunks_under_32_batch470(tmp_path):
    dd = _doc(tmp_path, _combo_pdf(), 32)
    para_lens = [len(c["text"]) for c in dd["chunks"][1:]]
    assert len(para_lens) == 15
    assert max(para_lens) <= 31


def test_combo_all_single_src_batch470(tmp_path):
    dd = _doc(tmp_path, _combo_pdf(), 32)
    assert all(len(c["source_element_ids"]) == 1
               for c in dd["chunks"])


def test_combo_metrics_batch470(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, _combo_pdf(), 32), None, "pdf", None)
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch470():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百三十二批 ----------

def test_source_no_eval_batch470():
    assert "eval(" not in _src()


def test_source_no_exec_batch470():
    assert "exec(" not in _src()


def test_source_no_compile_batch470():
    assert "compile(" not in _src()


def test_source_no_globals_batch470():
    assert "globals(" not in _src()


def test_source_no_locals_batch470():
    assert "locals(" not in _src()


def test_source_no_os_system_batch470():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch470():
    assert "subprocess" not in _src()


def test_source_no_popen_batch470():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch470():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch470():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch470():
    assert "socket" not in _src()


def test_source_no_requests_batch470():
    assert "requests" not in _src()


def test_source_no_urllib_batch470():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch470():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch470():
    assert "yield" not in _src()


def test_source_no_async_await_batch470():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch470():
    assert "open(" not in _src()
