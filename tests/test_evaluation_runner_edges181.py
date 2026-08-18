"""evaluation/runner.py 第六百零九轮 edges 测试（Round 1165）。

补强 edges180 未触及的角度（第五百三十七批，probe 实证）。

新角度（五型板三界标注 / 流首容差窗）：
- **三界全中**——五型 PDF 板挂三锚（caption 尾、
  段落尾、heading 尾各恰落块界）→ P/R/F1 全
  1.0（五型板标注首锁）
- **before 锚命中前界**——marker "Ga Gb" before
  → GT 在 heading 块首 = 段|题块界 → 1/3 预测
  界中 → P 1/3 / R 1.0 / F1 0.5
- **流首容差窗**——marker "Figure 3:" before →
  GT 落流绝对起点（无 0 位边界）但距第 1 界 26
  字 ≤ tol 30 → 容差内命中（与 edges171 末尾
  无边界成镜像：首有容差窗、尾无）
- forbidden tokens 第六百三十七批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


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


def _board(tmp_path, doc_id, anchors):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _five_type_pdf())
    (tmp_path / "anns" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": doc_id,
        "chunk_boundary_anchors": anchors}),
        encoding="utf-8")
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf",
                       "annotation_file": "anns/a.json"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _prf(r):
    m = r["per_doc"][0]["metrics"]
    return (m["chunk_boundary_precision"],
            m["chunk_boundary_recall"],
            m["chunk_boundary_f1"])


# ---------- 三界全中 ----------

def test_five_type_triple_junction_batch363(tmp_path):
    r = run_evaluation(_board(tmp_path, "pj", [
        {"marker": "caption text.", "position": "after"},
        {"marker": "period.", "position": "after"},
        {"marker": "Ga Gb", "position": "after"},
    ]), tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    p, rec, f1 = _prf(r)
    assert p == {"value": 1.0, "reason": None}
    assert rec == {"value": 1.0, "reason": None}
    assert f1 == {"value": 1.0, "reason": None}


# ---------- before 锚命中前界 ----------

def test_before_heading_junction_batch363(tmp_path):
    r = run_evaluation(_board(tmp_path, "pj2", [
        {"marker": "Ga Gb", "position": "before"},
    ]), tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    p, rec, f1 = _prf(r)
    assert p == {"value": 0.3333333333333333, "reason": None}
    assert rec == {"value": 1.0, "reason": None}
    assert f1 == {"value": 0.5, "reason": None}


# ---------- 流首容差窗 ----------

def test_stream_start_tolerance_batch363(tmp_path):
    r = run_evaluation(_board(tmp_path, "pj3", [
        {"marker": "Figure 3:", "position": "before"},
    ]), tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    p, rec, f1 = _prf(r)
    assert p == {"value": 0.3333333333333333, "reason": None}
    assert rec == {"value": 1.0, "reason": None}
    assert f1 == {"value": 0.5, "reason": None}


def test_stream_start_out_of_window_batch363(tmp_path):
    r = run_evaluation(_board(tmp_path, "pj4", [
        {"marker": "Figure 3:", "position": "before"},
    ]), tmp_path / "r.json", parser_name="fallback",
        max_chars=200, tolerance_chars=20)
    p, rec, f1 = _prf(r)
    assert p == {"value": 0.0, "reason": None}
    assert rec == {"value": 0.0, "reason": None}
    assert f1 == {"value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch363():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("expected_failure") == 5
    assert src.count("error_code") == 4


# ---------- forbidden tokens 第六百三十七批 ----------

def test_source_no_eval_batch363():
    assert "eval(" not in _src()


def test_source_no_exec_batch363():
    assert "exec(" not in _src()


def test_source_no_compile_batch363():
    assert "compile(" not in _src()


def test_source_no_globals_batch363():
    assert "globals(" not in _src()


def test_source_no_locals_batch363():
    assert "locals(" not in _src()


def test_source_no_os_system_batch363():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch363():
    assert "subprocess" not in _src()


def test_source_no_popen_batch363():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch363():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch363():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch363():
    assert "socket" not in _src()


def test_source_no_requests_batch363():
    assert "requests" not in _src()


def test_source_no_urllib_batch363():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch363():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch363():
    assert "yield" not in _src()


def test_source_no_async_await_batch363():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch363():
    assert _src().count("open(") == 2
