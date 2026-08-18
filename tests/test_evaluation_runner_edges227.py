"""evaluation/runner.py 第六百六十二轮 edges 测试（Round 1267）。

补强 edges226 未触及的角度（第六百三十九批，probe 实证）。

新角度（同标注异 mc 经 runner / 召回翻转）：
- **mc 200 半配**——2 块 → 1 界，
  caption 消耗 → cbp 1.0 / cbr
  0.5 / cbf 2/3（聚合同值）
- **mc 98 全配**——3 块 [29, 80,
  18] → 2 界 29/110，caption 尾
  29 与 heading 尾 110 均 d 0 →
  cbp/cbr/cbf 全 1.0（聚合同值）
- **mc 翻转召回**——同一
  manifest + 同一标注文件，仅
  max_chars 200→98 → 召回 0.5 →
  1.0（runner 级 mc 参数效应
  首锁）
- **不变量**——counts / ecbt 跨
  mc 相同
- forbidden tokens 第七百二十八批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


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


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


def _board(tmp_path):
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    (tmp_path / "mix.pdf").write_bytes(_wrap(s))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "mix.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "mix",
        "chunk_boundary_anchors": [
            {"marker": "Figure 1 An overview diagram.",
             "position": "after"},
            {"marker": "A" * 80, "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "mix", "path": "mix.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann/mix.json"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path, mc):
    return run_evaluation(_board(tmp_path), tmp_path / "r.json",
                          parser_name="fallback", max_chars=mc)


def _cb(r):
    m = r["per_doc"][0]["metrics"]
    return (m["chunk_boundary_precision"],
            m["chunk_boundary_recall"],
            m["chunk_boundary_f1"])


# ---------- mc 200 半配 ----------

def test_mc200_cbp_one_batch465(tmp_path):
    cbp, _, _ = _cb(_run(tmp_path, 200))
    assert cbp == {"value": 1.0, "reason": None}


def test_mc200_cbr_half_batch465(tmp_path):
    _, cbr, _ = _cb(_run(tmp_path, 200))
    assert cbr == {"value": 0.5, "reason": None}


def test_mc200_cbf_two_thirds_batch465(tmp_path):
    _, _, cbf = _cb(_run(tmp_path, 200))
    assert cbf == {"value": 0.6666666666666666, "reason": None}


def test_mc200_agg_cbr_half_batch465(tmp_path):
    agg = _run(tmp_path, 200)["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_recall"] == {
        "macro_average": 0.5, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- mc 98 全配 ----------

def test_mc98_all_one_batch465(tmp_path):
    cbp, cbr, cbf = _cb(_run(tmp_path, 98))
    assert cbp == {"value": 1.0, "reason": None}
    assert cbr == {"value": 1.0, "reason": None}
    assert cbf == {"value": 1.0, "reason": None}


def test_mc98_agg_all_one_batch465(tmp_path):
    agg = _run(tmp_path, 98)["summary"]["ratio_macro_averages"]
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert agg[k] == {"macro_average": 1.0,
                          "participating_docs": 1,
                          "not_evaluated": 0}


def test_mc98_chunk_shape_batch465(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(tmp_path / "mix.pdf",
                                 tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=98)
    assert errors == []
    assert [len(c["text"]) for c in doc.to_dict()["chunks"]] == [
        29, 80, 18]


def test_mc98_heading_boundary_d0_batch465(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(tmp_path / "mix.pdf",
                                 tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=98)
    assert errors == []
    dd = doc.to_dict()
    joined = " ".join(c["text"] for c in dd["chunks"])
    boundary2 = len(dd["chunks"][0]["text"]) + 1 + 80
    heading_end = joined.index("A" * 80) + 80
    assert boundary2 == 110
    assert heading_end == 110


# ---------- mc 翻转召回 ----------

def test_recall_flip_half_to_one_batch465(tmp_path):
    _, cbr200, _ = _cb(_run(tmp_path, 200))
    _, cbr98, _ = _cb(_run(tmp_path, 98))
    assert cbr200["value"] == 0.5
    assert cbr98["value"] == 1.0


def test_f1_flip_batch465(tmp_path):
    _, _, cbf200 = _cb(_run(tmp_path, 200))
    _, _, cbf98 = _cb(_run(tmp_path, 98))
    assert cbf200["value"] == 0.6666666666666666
    assert cbf98["value"] == 1.0


# ---------- 不变量 ----------

def test_counts_invariant_batch465(tmp_path):
    expected = {"element_count_total": {"sum": 3,
                                        "participating_docs": 1}}
    assert _run(tmp_path, 200)["summary"]["counts"] == expected
    assert _run(tmp_path, 98)["summary"]["counts"] == expected


def test_ecbt_invariant_batch465(tmp_path):
    expected = {"value": {"caption": 1, "heading": 1,
                          "paragraph": 1}, "reason": None}
    for mc in (200, 98):
        assert _run(tmp_path, mc)["per_doc"][0]["metrics"][
            "element_count_by_type"] == expected


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch465():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百二十八批 ----------

def test_source_no_eval_batch465():
    assert "eval(" not in _src()


def test_source_no_exec_batch465():
    assert "exec(" not in _src()


def test_source_no_compile_batch465():
    assert "compile(" not in _src()


def test_source_no_globals_batch465():
    assert "globals(" not in _src()


def test_source_no_locals_batch465():
    assert "locals(" not in _src()


def test_source_no_os_system_batch465():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch465():
    assert "subprocess" not in _src()


def test_source_no_popen_batch465():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch465():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch465():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch465():
    assert "socket" not in _src()


def test_source_no_requests_batch465():
    assert "requests" not in _src()


def test_source_no_urllib_batch465():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch465():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch465():
    assert "yield" not in _src()


def test_source_no_async_await_batch465():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch465():
    assert _src().count("open(") == 2
