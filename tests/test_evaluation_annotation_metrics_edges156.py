"""evaluation/annotation_metrics.py 第五百八十七轮 edges 测试（Round 1295）。

补强 edges155 未触及的角度（第六百六十七批，probe 实证）。

新角度（真板重复 marker 顺序定位 / 一对一帽）：
- **真板双现几何**——LONG 尾
  接 " Word3." → 17 块 / 流
  557 / Word3. 双现 [102,
  551] / 预测边界 16 条首 80
  次 108 末 550（末块恰
  "Word3." 尾现成块首锁）
- **双锚 tol30 全中**——
  [after,after] gt [108,557]
  → (0.125, 1.0, 0.2222…)；
  单锚 (0.0625, 1.0,
  0.1176…) 对照（R 分母 1↔2
  可视）
- **tol0 劈叉**——gt 557 非
  预测边界 → recall 0.5；
  [before,after] gt [102,
  557] 双落空 → 三 0.0
  （顺序敏感首锁）
- **邻接双现一对一帽**——
  "Word3. Word3." 邻接 →
  gt [108,115]；tol 7 单预测
  108 距双 gt 均 ≤7 仍只中
  1 → recall 0.5（tol 6 同；
  tol 30 第二预测 136 救回
  1.0）
- **第三锚吞没**——双现 × 3
  锚 → _missing_markers
  ['Word3.'] 而指标与 2 锚全
  同（缺第三不改指标首锁）
- forbidden tokens 第七百四十九批（open 0）
"""

from __future__ import annotations

import inspect

from app.chunkers.structural import normalize_text
from app.pipeline import process_single
from evaluation.annotation_metrics import chunk_boundary_prf


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
LONG2 = LONG + " Word3."
LONG3 = " ".join(("Word3. Word3." if i == 3 else "Word%d." % i)
                 for i in range(60))
HEAD = "A" * 80


def _doc(tmp_path, name, long_text):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % long_text).encode()
    p = tmp_path / name
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / (name + ".json"),
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    return doc.to_dict()


def _stream_preds(dd):
    norm_chunks = [normalize_text(c.get("text") or "")
                   for c in dd["chunks"]]
    stream = normalize_text(" ".join(norm_chunks))
    predicted = []
    pos = 0
    for i, txt in enumerate(norm_chunks):
        if i == len(norm_chunks) - 1:
            break
        find_pos = stream.find(txt, pos)
        end = find_pos + len(txt)
        predicted.append(end)
        pos = end + 1
    return stream, predicted


def _occ(stream, marker):
    out = []
    i = stream.find(marker)
    while i >= 0:
        out.append(i)
        i = stream.find(marker, i + 1)
    return out


def _prf(dd, anchors, tol):
    r = chunk_boundary_prf(
        dd, {"chunk_boundary_anchors": anchors},
        tolerance_chars=tol)
    missing = r.pop("_missing_markers", None)
    r.pop("_tolerance_chars", None)
    vals = (r["chunk_boundary_precision"]["value"],
            r["chunk_boundary_recall"]["value"],
            r["chunk_boundary_f1"]["value"])
    return vals, (missing or {}).get("value")


A = lambda p: {"marker": "Word3.", "position": p}  # noqa: E731


# ---------- 真板双现几何 ----------

def test_dup_board_chunks_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    assert len(dd["chunks"]) == 17


def test_dup_board_stream_len_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    stream, _ = _stream_preds(dd)
    assert len(stream) == 557


def test_dup_board_occurrences_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    stream, _ = _stream_preds(dd)
    assert _occ(stream, "Word3.") == [102, 551]


def test_dup_board_preds_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    _, preds = _stream_preds(dd)
    assert len(preds) == 16
    assert preds[:3] == [80, 108, 136]
    assert preds[-1] == 550


def test_dup_board_last_chunk_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    assert dd["chunks"][-1]["text"] == "Word3."


# ---------- 双锚 tol30 全中 ----------

def test_single_anchor_face_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    vals, missing = _prf(dd, [A("after")], 30)
    assert vals == (1 / 16, 1.0, 0.11764705882352941)
    assert missing is None


def test_double_anchor_face_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    vals, missing = _prf(dd, [A("after"), A("after")], 30)
    assert vals == (0.125, 1.0, 0.2222222222222222)
    assert missing is None


def test_double_anchor_reasons_none_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    r = chunk_boundary_prf(
        dd, {"chunk_boundary_anchors": [A("after"), A("after")]},
        tolerance_chars=30)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert r[k]["reason"] is None
    assert r["_tolerance_chars"] == {"value": 30,
                                     "reason": None}


# ---------- tol0 劈叉 ----------

def test_double_tol0_face_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    vals, _ = _prf(dd, [A("after"), A("after")], 0)
    assert vals == (1 / 16, 0.5, 0.1111111111111111)


def test_before_after_tol0_zeros_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    vals, _ = _prf(dd, [A("before"), A("after")], 0)
    assert vals == (0.0, 0.0, 0.0)


def test_after_before_tol0_half_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    vals, _ = _prf(dd, [A("after"), A("before")], 0)
    assert vals == (1 / 16, 0.5, 0.1111111111111111)


# ---------- 邻接双现一对一帽 ----------

def test_adjacent_occurrences_batch493(tmp_path):
    dd = _doc(tmp_path, "c3.pdf", LONG3)
    stream, _ = _stream_preds(dd)
    assert _occ(stream, "Word3.") == [102, 109]


def test_adjacent_cap_tol7_batch493(tmp_path):
    dd = _doc(tmp_path, "c3.pdf", LONG3)
    vals, missing = _prf(dd, [A("after"), A("after")], 7)
    assert vals == (1 / 16, 0.5, 0.1111111111111111)
    assert missing is None


def test_adjacent_cap_tol6_batch493(tmp_path):
    dd = _doc(tmp_path, "c3.pdf", LONG3)
    vals, _ = _prf(dd, [A("after"), A("after")], 6)
    assert vals == (1 / 16, 0.5, 0.1111111111111111)


def test_adjacent_rescue_tol30_batch493(tmp_path):
    dd = _doc(tmp_path, "c3.pdf", LONG3)
    vals, _ = _prf(dd, [A("after"), A("after")], 30)
    assert vals == (0.125, 1.0, 0.2222222222222222)


# ---------- 第三锚吞没 ----------

def test_third_anchor_missing_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    vals, missing = _prf(dd, [A("after")] * 3, 30)
    assert missing == ["Word3."]
    assert vals == (0.125, 1.0, 0.2222222222222222)


def test_adjacent_third_missing_batch493(tmp_path):
    dd = _doc(tmp_path, "c3.pdf", LONG3)
    vals, missing = _prf(dd, [A("after")] * 3, 30)
    assert missing == ["Word3."]
    assert vals == (0.125, 1.0, 0.2222222222222222)


def test_no_missing_when_two_anchors_batch493(tmp_path):
    dd = _doc(tmp_path, "c2.pdf", LONG2)
    r = chunk_boundary_prf(
        dd, {"chunk_boundary_anchors": [A("after")] * 2},
        tolerance_chars=30)
    assert "_missing_markers" not in r


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(
        __import__("evaluation.annotation_metrics",
                   fromlist=["x"]))


def test_source_key_lines_batch493():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第七百四十九批 ----------

def test_source_no_eval_batch493():
    assert "eval(" not in _src()


def test_source_no_exec_batch493():
    assert "exec(" not in _src()


def test_source_no_compile_batch493():
    assert "compile(" not in _src()


def test_source_no_globals_batch493():
    assert "globals(" not in _src()


def test_source_no_locals_batch493():
    assert "locals(" not in _src()


def test_source_no_os_system_batch493():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch493():
    assert "subprocess" not in _src()


def test_source_no_popen_batch493():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch493():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch493():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch493():
    assert "socket" not in _src()


def test_source_no_requests_batch493():
    assert "requests" not in _src()


def test_source_no_urllib_batch493():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch493():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch493():
    assert "yield" not in _src()


def test_source_no_async_await_batch493():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch493():
    assert _src().count("open(") == 0
