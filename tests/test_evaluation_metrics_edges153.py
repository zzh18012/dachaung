"""evaluation/metrics.py 第五百七十四轮 edges 测试（Round 1308）。

补强 edges152 未触及的角度（第六百八十批，probe 实证）。

新角度（无标题板 hbc 空值面 / sdc 逐型钳制）：
- **无标题板**——单 LONG
  段落 mc32 → elements
  恰 [paragraph]；15 块
  全 long_paragraph_
  sentence_split（无
  sequential 首块——无
  标题无整块吸收）
- **hbc 空值**——{None,
  no_heading_elements}
  （分母 0 → null 不 1.0
  口径在 heading 面首锁）
- **ecbt 单型**——
  {paragraph: 1}
- **tpe/plvr 无标题**
  ——True / 1.0（无标题
  不影响保真面）
- **sdc 逐型求和**——
  {heading:5, paragraph:3}
  → 5（(5-2)+(3-1) 多型
  独立计首锁）
- **sdc 负向钳制**——
  {heading:0, paragraph:0}
  → 0；{heading:1} → 0；
  {paragraph:1} → 0
  （exp ≤ actual 型不计
  丢落——负差逐型 max(0,·)
  首锁）
- **sdc 缺型全丢**——
  {image:4} → 4（actual
  0 计）
- **sdc 空 ecbt**——{}
  → {None, no_expectations_
  element_count}；无
  expectations 键 →
  no_expectations
- forbidden tokens 第七百五十六批（open 0）
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
STREAM_1P = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
             % LONG).encode()
STREAM_2H = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % H1
             + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n" % H2
             + "BT /F1 12 Tf 10 620 Td (%s) Tj ET\n"
             % LONG).encode()


def _doc(tmp_path, stream, mc):
    p = tmp_path / "c.pdf"
    p.write_bytes(_wrap(stream))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=mc)
    assert errors == []
    return doc.to_dict()


def _p_board(tmp_path):
    return _doc(tmp_path, STREAM_1P, 32)


def _h_board(tmp_path):
    return _doc(tmp_path, STREAM_2H, 10000)


def _m(dd, exp=None):
    return compute_automatic_metrics(dd, None, "pdf", exp)


# ---------- 无标题板 ----------

def test_p_elements_only_paragraph_batch506(tmp_path):
    dd = _p_board(tmp_path)
    assert [e["type"] for e in dd["elements"]] == [
        "paragraph"]


def test_p_chunk_count_15_batch506(tmp_path):
    assert len(_p_board(tmp_path)["chunks"]) == 15


def test_p_all_sentence_split_batch506(tmp_path):
    dd = _p_board(tmp_path)
    assert {c["metadata"]["strategy"]
            for c in dd["chunks"]} == {
        "long_paragraph_sentence_split"}


def test_p_hbc_null_reason_batch506(tmp_path):
    m = _m(_p_board(tmp_path))
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_p_hbc_value_none_batch506(tmp_path):
    m = _m(_p_board(tmp_path))
    assert m["heading_boundary_compliance"][
        "value"] is None


def test_p_ecbt_single_type_batch506(tmp_path):
    m = _m(_p_board(tmp_path))
    assert m["element_count_by_type"]["value"] == {
        "paragraph": 1}


def test_p_tpe_true_batch506(tmp_path):
    m = _m(_p_board(tmp_path))
    assert m["text_preservation_equal"]["value"] is True


def test_p_plvr_one_batch506(tmp_path):
    m = _m(_p_board(tmp_path))
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_p_ect_total_one_batch506(tmp_path):
    m = _m(_p_board(tmp_path))
    assert m["element_count_total"]["value"] == 1


# ---------- sdc 逐型求和 / 钳制 ----------

def test_sdc_multi_type_sum_batch506(tmp_path):
    m = _m(_h_board(tmp_path),
           {"element_count_by_type": {
               "heading": 5, "paragraph": 3}})
    assert m["silent_drop_count"] == {"value": 5,
                                      "reason": None}


def test_sdc_zero_expectations_clamped_batch506(
        tmp_path):
    m = _m(_h_board(tmp_path),
           {"element_count_by_type": {
               "heading": 0, "paragraph": 0}})
    assert m["silent_drop_count"] == {"value": 0,
                                      "reason": None}


def test_sdc_exp_below_actual_heading_batch506(
        tmp_path):
    m = _m(_h_board(tmp_path),
           {"element_count_by_type": {"heading": 1}})
    assert m["silent_drop_count"] == {"value": 0,
                                      "reason": None}


def test_sdc_exp_below_actual_paragraph_batch506(
        tmp_path):
    m = _m(_h_board(tmp_path),
           {"element_count_by_type": {"paragraph": 1}})
    assert m["silent_drop_count"] == {"value": 0,
                                      "reason": None}


def test_sdc_absent_type_full_drop_batch506(
        tmp_path):
    m = _m(_h_board(tmp_path),
           {"element_count_by_type": {"image": 4}})
    assert m["silent_drop_count"] == {"value": 4,
                                      "reason": None}


def test_sdc_empty_ecbt_null_batch506(tmp_path):
    m = _m(_h_board(tmp_path),
           {"element_count_by_type": {}})
    assert m["silent_drop_count"] == {
        "value": None,
        "reason": "no_expectations_element_count"}


def test_sdc_no_expectations_null_batch506(tmp_path):
    m = _m(_h_board(tmp_path), None)
    assert m["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}


# ---------- 两标题板基线复核 ----------

def test_h_actual_counts_batch506(tmp_path):
    m = _m(_h_board(tmp_path))
    assert m["element_count_by_type"]["value"] == {
        "heading": 2, "paragraph": 1}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch506():
    src = _src()
    assert "drops += (exp - actual)" in src
    assert "no_heading_elements" in src


# ---------- forbidden tokens 第七百五十六批 ----------

def test_source_no_eval_batch506():
    assert "eval(" not in _src()


def test_source_no_exec_batch506():
    assert "exec(" not in _src()


def test_source_no_compile_batch506():
    assert "compile(" not in _src()


def test_source_no_globals_batch506():
    assert "globals(" not in _src()


def test_source_no_locals_batch506():
    assert "locals(" not in _src()


def test_source_no_os_system_batch506():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch506():
    assert "subprocess" not in _src()


def test_source_no_popen_batch506():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch506():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch506():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch506():
    assert "socket" not in _src()


def test_source_no_requests_batch506():
    assert "requests" not in _src()


def test_source_no_urllib_batch506():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch506():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch506():
    assert "yield" not in _src()


def test_source_no_async_await_batch506():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch506():
    assert _src().count("open(") == 0
