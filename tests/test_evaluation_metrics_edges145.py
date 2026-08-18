"""evaluation/metrics.py 第五百六十六轮 edges 测试（Round 1260）。

补强 edges144 未触及的角度（第六百三十二批，probe 实证）。

新角度（PDF 段落启发式分类边界全像）：
- **长度界 80/81**——无句号行 80
  字符 → heading，81 → paragraph
  （len <= 80 精确界首锁）
- **句尾标点压倒长度**——
  "Is this a heading?" /
  "Wow what a finding!" →
  paragraph（?/! 同 . 终结）
- **caption 正则优先**——"Figure
  1 …"（带句号也 caption）/
  "Table 2 …" → caption（caption
  > heading 次序首锁）
- **无数字不成 caption**——
  "Figure something else" →
  heading（关键字无编号回退标题）
- **caption 入 bbox 必备型**——
  caption 元素 pdf_locator 1.0
  （_PDF_BBOX_REQUIRED_TYPES 含
  caption 的真板显形首锁）
- forbidden tokens 第七百二十二批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _pdf(text: str) -> bytes:
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % text).encode()
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


def _doc(tmp_path, text):
    from app.pipeline import process_single
    p = tmp_path / "v.pdf"
    p.write_bytes(_pdf(text))
    d, errors = process_single(p, tmp_path / "o.json",
                               parser_name="fallback",
                               max_chars=200)
    assert errors == []
    return d.to_dict()


# ---------- 长度界 80/81 ----------

def test_len80_no_period_heading_batch458(tmp_path):
    dd = _doc(tmp_path, "A" * 80)
    assert [e["type"] for e in dd["elements"]] == ["heading"]


def test_len81_no_period_paragraph_batch458(tmp_path):
    dd = _doc(tmp_path, "A" * 81)
    assert [e["type"] for e in dd["elements"]] == ["paragraph"]


# ---------- 句尾标点压倒长度 ----------

def test_question_mark_paragraph_batch458(tmp_path):
    dd = _doc(tmp_path, "Is this a heading?")
    assert [e["type"] for e in dd["elements"]] == ["paragraph"]


def test_exclaim_paragraph_batch458(tmp_path):
    dd = _doc(tmp_path, "Wow what a finding!")
    assert [e["type"] for e in dd["elements"]] == ["paragraph"]


# ---------- caption 正则优先 ----------

def test_figure_caption_type_batch458(tmp_path):
    dd = _doc(tmp_path, "Figure 1 An overview diagram.")
    assert [e["type"] for e in dd["elements"]] == ["caption"]


def test_table_caption_type_batch458(tmp_path):
    dd = _doc(tmp_path, "Table 2 results summary.")
    assert [e["type"] for e in dd["elements"]] == ["caption"]


def test_fig_nodigit_heading_batch458(tmp_path):
    dd = _doc(tmp_path, "Figure something else entirely")
    assert [e["type"] for e in dd["elements"]] == ["heading"]


# ---------- caption 指标层 ----------

def test_caption_ecbt_batch458(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, "Figure 1 An overview diagram."),
        None, "pdf", None)
    assert m["element_count_by_type"] == {
        "value": {"caption": 1}, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}


def test_caption_pdf_locator_batch458(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, "Figure 1 An overview diagram."),
        None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_caption_hbc_null_batch458(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, "Figure 1 An overview diagram."),
        None, "pdf", None)
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


# ---------- heading 板 hbc ----------

def test_len80_hbc_one_batch458(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, "A" * 80), None, "pdf", None)
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_len81_hbc_null_batch458(tmp_path):
    m = compute_automatic_metrics(
        _doc(tmp_path, "A" * 81), None, "pdf", None)
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch458():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百二十二批 ----------

def test_source_no_eval_batch458():
    assert "eval(" not in _src()


def test_source_no_exec_batch458():
    assert "exec(" not in _src()


def test_source_no_compile_batch458():
    assert "compile(" not in _src()


def test_source_no_globals_batch458():
    assert "globals(" not in _src()


def test_source_no_locals_batch458():
    assert "locals(" not in _src()


def test_source_no_os_system_batch458():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch458():
    assert "subprocess" not in _src()


def test_source_no_popen_batch458():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch458():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch458():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch458():
    assert "socket" not in _src()


def test_source_no_requests_batch458():
    assert "requests" not in _src()


def test_source_no_urllib_batch458():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch458():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch458():
    assert "yield" not in _src()


def test_source_no_async_await_batch458():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch458():
    assert "open(" not in _src()
