"""evaluation/metrics.py 第五百六十四轮 edges 测试（Round 1250）。

补强 edges142 未触及的角度（第六百二十二批，probe 实证）。

新角度（三行板逐对行距分组 / 合并 bbox 跨度算术）：
- **全 gap 30**——三行 → 单元素
  "Alpha first line. Beta second
  line. Gamma third line."
- **全 gap 31**——三行 → 恰 3 元素
- **混合 30/31**——逐对分组 → 2
  元素（前两行合并 + 第三行分列，
  成对阈值非全文档首锁）
- **bbox 高度算术**——单行高 ≈12，
  两行合并 ≈42，三行合并 ≈72（=
  12 + 30×(行数−1)，合并 bbox 跨
  行首锁）
- forbidden tokens 第七百一十四批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _pdf3(ys) -> bytes:
    parts = []
    for y, txt in zip(ys, ["Alpha first line.", "Beta second line.",
                           "Gamma third line."]):
        parts.append("BT /F1 12 Tf 10 %d Td (%s) Tj ET" % (y, txt))
    s = ("\n".join(parts) + "\n").encode()
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"),
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


def _doc(tmp_path, ys):
    from app.pipeline import process_single
    p = tmp_path / "t.pdf"
    p.write_bytes(_pdf3(ys))
    d, errors = process_single(p, tmp_path / "o.json",
                               parser_name="fallback",
                               max_chars=200)
    assert errors == []
    return d.to_dict()


_MERGED = ("Alpha first line. Beta second line. "
           "Gamma third line.")


# ---------- 全 gap 30 合并 ----------

def test_three_gap30_one_element_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 670, 640])
    assert len(dd["elements"]) == 1
    assert dd["elements"][0]["content"] == _MERGED


def test_all30_chunk_one_source_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 670, 640])
    assert len(dd["chunks"]) == 1
    assert len(dd["chunks"][0]["source_element_ids"]) == 1


# ---------- 全 gap 31 分列 ----------

def test_three_gap31_three_elements_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 669, 638])
    assert [e["content"] for e in dd["elements"]] == [
        "Alpha first line.", "Beta second line.",
        "Gamma third line."]


def test_all31_types_all_para_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 669, 638])
    assert [e["type"] for e in dd["elements"]] == [
        "paragraph", "paragraph", "paragraph"]


def test_all31_chunk_three_sources_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 669, 638])
    assert len(dd["chunks"]) == 1
    assert dd["chunks"][0]["text"] == _MERGED
    assert len(dd["chunks"][0]["source_element_ids"]) == 3


# ---------- 混合 30/31 逐对分组 ----------

def test_mixed_pairwise_two_elements_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 670, 639])
    assert [e["content"] for e in dd["elements"]] == [
        "Alpha first line. Beta second line.",
        "Gamma third line."]


def test_mixed_chunk_two_sources_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 670, 639])
    assert len(dd["chunks"]) == 1
    assert dd["chunks"][0]["text"] == _MERGED
    assert len(dd["chunks"][0]["source_element_ids"]) == 2


# ---------- bbox 高度算术 ----------

def test_bbox_height_one_line_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 669, 638])
    bbox = dd["elements"][0]["source_locator"]["bbox"]
    assert bbox[3] - bbox[1] == 12.0


def test_bbox_height_two_lines_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 670, 639])
    bbox = dd["elements"][0]["source_locator"]["bbox"]
    assert bbox[3] - bbox[1] == 42.0


def test_bbox_height_three_lines_batch448(tmp_path):
    dd = _doc(tmp_path, [700, 670, 640])
    bbox = dd["elements"][0]["source_locator"]["bbox"]
    assert bbox[3] - bbox[1] == 72.0


# ---------- 指标层 ----------

def test_mixed_ect_two_batch448(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, [700, 670, 639]), None, "pdf", None)
    assert m["element_count_total"] == {"value": 2, "reason": None}


def test_mixed_ecbt_paragraph2_batch448(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, [700, 670, 639]), None, "pdf", None)
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}


def test_all31_ect_three_batch448(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, [700, 669, 638]), None, "pdf", None)
    assert m["element_count_total"] == {"value": 3, "reason": None}


def test_mixed_intact_recall_batch448(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, [700, 670, 639]), None, "pdf", None)
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch448():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百一十四批 ----------

def test_source_no_eval_batch448():
    assert "eval(" not in _src()


def test_source_no_exec_batch448():
    assert "exec(" not in _src()


def test_source_no_compile_batch448():
    assert "compile(" not in _src()


def test_source_no_globals_batch448():
    assert "globals(" not in _src()


def test_source_no_locals_batch448():
    assert "locals(" not in _src()


def test_source_no_os_system_batch448():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch448():
    assert "subprocess" not in _src()


def test_source_no_popen_batch448():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch448():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch448():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch448():
    assert "socket" not in _src()


def test_source_no_requests_batch448():
    assert "requests" not in _src()


def test_source_no_urllib_batch448():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch448():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch448():
    assert "yield" not in _src()


def test_source_no_async_await_batch448():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch448():
    assert "open(" not in _src()
