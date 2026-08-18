"""evaluation/annotation_metrics.py 第五百八十一轮 edges 测试（Round 1259）。

补强 edges149 未触及的角度（第六百三十一批，probe 实证）。

新角度（双页板 mc60 过冲块 / 单界一对一耗尽）：
- **过冲块**——mc60 下 wg31 →
  chunk1 61 字符（元素粒度探出
  max_chars 1 字符首锁），块界 61
  非 60
- **seam d 20 翻转**——"Lower
  line text here." after 首
  现收尾 41，距界 61 恰 20 → tol
  19 漏 / tol 20 全 1.0
- **单界一对一耗尽**——双
  "Lower" 锚：唯一界被首个 gt 消
  耗 → P 1.0 / R 0.5 / F1 2/3；
  tol 升 22（两 gt 均入程）值不
  变（界不重复配首锁）
- forbidden tokens 第七百二十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _two_page(y2: int) -> bytes:
    s1 = (("BT /F1 12 Tf 10 700 Td (Top line text here.) Tj ET\n"
           "BT /F1 12 Tf 10 %d Td (Lower line text here.) Tj ET\n"
           % y2).encode())
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 6 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 7 0 R>>"),
        7: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 8\n0000000000 65535 f \n"
    for num in range(1, 8):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 8/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


def _doc(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "wg31.pdf"
    p.write_bytes(_two_page(669))
    d, errors = process_single(p, tmp_path / "o.json",
                               parser_name="fallback",
                               max_chars=60)
    assert errors == []
    return d.to_dict()


def _ann(*pairs):
    return {"chunk_boundary_anchors": [
        {"marker": m, "position": pos} for m, pos in pairs]}


def _prf(dd, pairs, tol):
    r = chunk_boundary_prf(dd, _ann(*pairs), tol)
    return {k: r[k]["value"] for k in (
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1")}


# ---------- 过冲块 ----------

def test_overshoot_chunk_batch457(tmp_path):
    dd = _doc(tmp_path)
    assert [c["text"] for c in dd["chunks"]] == [
        "Top line text here. Lower line text here. Top line text "
        "here.",
        "Lower line text here."]


def test_overshoot_len_sixty_one_batch457(tmp_path):
    dd = _doc(tmp_path)
    assert len(dd["chunks"][0]["text"]) == 61


def test_overshoot_sources_batch457(tmp_path):
    dd = _doc(tmp_path)
    assert [len(c["source_element_ids"]) for c in dd["chunks"]] == [
        3, 1]


# ---------- seam d 20 翻转 ----------

def test_lower_after_19_miss_batch457(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Lower line text here.", "after")], 19) == {
        "chunk_boundary_precision": 0.0,
        "chunk_boundary_recall": 0.0,
        "chunk_boundary_f1": 0.0}


def test_lower_after_20_all_hit_batch457(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Lower line text here.", "after")], 20) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 1.0,
        "chunk_boundary_f1": 1.0}


def test_seam_arith_batch457(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    seam = len(dd["chunks"][0]["text"])
    first_lower_end = joined.index("Lower line text here.") + \
        len("Lower line text here.")
    assert seam == 61
    assert first_lower_end == 41
    assert seam - first_lower_end == 20


# ---------- 单界一对一耗尽 ----------

def test_dup_lower_tol20_batch457(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Lower line text here.", "after"),
                 ("Lower line text here.", "after")], 20) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 0.5,
        "chunk_boundary_f1": 0.6666666666666666}


def test_dup_lower_tol22_same_batch457(tmp_path):
    assert _prf(_doc(tmp_path),
                [("Lower line text here.", "after"),
                 ("Lower line text here.", "after")], 22) == {
        "chunk_boundary_precision": 1.0,
        "chunk_boundary_recall": 0.5,
        "chunk_boundary_f1": 0.6666666666666666}


def test_second_lower_d22_batch457(tmp_path):
    dd = _doc(tmp_path)
    joined = " ".join(c["text"] for c in dd["chunks"])
    second = joined.rindex("Lower line text here.") + \
        len("Lower line text here.")
    assert second == 83
    assert second - 61 == 22


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch457():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第七百二十一批 ----------

def test_source_no_eval_batch457():
    assert "eval(" not in _src()


def test_source_no_exec_batch457():
    assert "exec(" not in _src()


def test_source_no_compile_batch457():
    assert "compile(" not in _src()


def test_source_no_globals_batch457():
    assert "globals(" not in _src()


def test_source_no_locals_batch457():
    assert "locals(" not in _src()


def test_source_no_os_system_batch457():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch457():
    assert "subprocess" not in _src()


def test_source_no_popen_batch457():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch457():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch457():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch457():
    assert "socket" not in _src()


def test_source_no_requests_batch457():
    assert "requests" not in _src()


def test_source_no_urllib_batch457():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch457():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch457():
    assert "yield" not in _src()


def test_source_no_async_await_batch457():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch457():
    assert "open(" not in _src()
