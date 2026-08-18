"""evaluation/runner.py 第六百六十六轮 edges 测试（Round 1291）。

补强 edges230 未触及的角度（第六百六十三批，probe 实证）。

新角度（图片增面 10 路差分）：
- **同 doc 同文本、仅加一张图**
  ——两 PDF 全树对比 → 恰
  10 条叶路径：ecbt image
  键 + ect value + irer
  value/reason + 聚合 irer
  三键 + counts sum +
  wall_time + 时间戳
  （第三差分轴首锁：edges140
  板型轴 / edges141 期望与
  mc 轴之外的图片轴）
- **no_image_elements**——
  无图板 irer {None,
  no_image_elements} vs
  图板 {1.0, None}
- **irer 聚合翻转**——
  {None, 0, 1} ↔ {1.0, 1, 0}
- **17/20 指标面恒等**——
  tpe/crir/msp/msr/hbc/
  plvr 等全等；success/
  counts 参与数同
- forbidden tokens 第七百五十批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _wrap(objs_dict: dict) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs_dict):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs_dict[num] + b"endobj\n")
    n = max(objs_dict) + 1
    xp = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % n
    for num in range(1, n):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n" % n
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
HEAD = "A" * 80


def _pdfs(tmp_path):
    text = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
            + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
            % LONG).encode()
    img = bytes([255, 0, 0, 0, 255, 0,
                 0, 0, 255, 255, 255, 0])
    itext = b"q 100 0 0 50 10 500 cm /Im0 Do Q\n" + text
    common = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    plain = dict(common)
    plain[3] = (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
                b"/Resources<</Font<</F1 5 0 R>>>>"
                b"/Contents 4 0 R>>")
    plain[4] = (b"<</Length " + str(len(text)).encode()
                + b">>stream\n" + text + b"\nendstream ")
    iobjs = dict(common)
    iobjs[3] = (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
                b"/Resources<</Font<</F1 5 0 R>>"
                b"/XObject<</Im0 6 0 R>>>>/Contents 4 0 R>>")
    iobjs[4] = (b"<</Length " + str(len(itext)).encode()
                + b">>stream\n" + itext + b"\nendstream ")
    iobjs[6] = (b"<</Type/XObject/Subtype/Image/Width 2/Height 2"
                b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
                + str(len(img)).encode()
                + b">>stream\n" + img + b"\nendstream ")
    (tmp_path / "plain.pdf").write_bytes(_wrap(plain))
    (tmp_path / "withimg.pdf").write_bytes(_wrap(iobjs))


def _board(tmp_path, name, pdf):
    mf = tmp_path / (name + ".json")
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "combo", "path": pdf,
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _runs(tmp_path):
    rp = run_evaluation(
        _board(tmp_path, "a", "plain.pdf"),
        tmp_path / "rp.json",
        parser_name="fallback", max_chars=32)
    ri = run_evaluation(
        _board(tmp_path, "b", "withimg.pdf"),
        tmp_path / "ri.json",
        parser_name="fallback", max_chars=32)
    return rp, ri


def _diff_paths(a, b):
    diffs = set()

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                walk(x.get(k), y.get(k), path + [k])
        elif isinstance(x, list) and isinstance(y, list):
            for i in range(max(len(x), len(y))):
                walk(x[i] if i < len(x) else None,
                     y[i] if i < len(y) else None, path + [i])
        elif x != y:
            diffs.add(tuple(path))

    walk(a, b, [])
    return diffs


IMG_DIFF = {
    ("per_doc", 0, "metrics", "element_count_by_type",
     "value", "image"),
    ("per_doc", 0, "metrics", "element_count_total", "value"),
    ("per_doc", 0, "metrics",
     "image_resource_exists_ratio", "reason"),
    ("per_doc", 0, "metrics",
     "image_resource_exists_ratio", "value"),
    ("per_doc", 0, "wall_time_seconds", "total"),
    ("provenance", "run_timestamp_iso"),
    ("summary", "counts", "element_count_total", "sum"),
    ("summary", "ratio_macro_averages",
     "image_resource_exists_ratio", "macro_average"),
    ("summary", "ratio_macro_averages",
     "image_resource_exists_ratio", "not_evaluated"),
    ("summary", "ratio_macro_averages",
     "image_resource_exists_ratio",
     "participating_docs")}


# ---------- 图片增面 10 路差分 ----------

def test_img_diff_set_exact_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    assert _diff_paths(rp, ri) == IMG_DIFF


def test_img_diff_size_10_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    assert len(_diff_paths(rp, ri)) == 10


def test_img_diff_excludes_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    d = _diff_paths(rp, ri)
    assert ("per_doc", 0, "metrics",
            "text_preservation_equal", "value") not in d
    assert ("per_doc", 0, "metrics",
            "silent_drop_count", "reason") not in d
    assert ("summary", "success_rates") not in d
    assert ("per_doc", 0, "doc_id") not in d


# ---------- no_image_elements / irer 翻转 ----------

def test_plain_irer_no_image_elements_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, _ = _runs(tmp_path)
    assert rp["per_doc"][0]["metrics"][
        "image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


def test_img_irer_one_batch489(tmp_path):
    _pdfs(tmp_path)
    _, ri = _runs(tmp_path)
    assert ri["per_doc"][0]["metrics"][
        "image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


def test_irer_aggregate_flip_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    assert rp["summary"]["ratio_macro_averages"][
        "image_resource_exists_ratio"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}
    assert ri["summary"]["ratio_macro_averages"][
        "image_resource_exists_ratio"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- 计数面 ----------

def test_ecbt_image_key_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    assert rp["per_doc"][0]["metrics"][
        "element_count_by_type"]["value"] == {
        "heading": 1, "paragraph": 1}
    assert ri["per_doc"][0]["metrics"][
        "element_count_by_type"]["value"] == {
        "heading": 1, "paragraph": 1, "image": 1}


def test_ect_and_counts_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    assert rp["per_doc"][0]["metrics"][
        "element_count_total"]["value"] == 2
    assert ri["per_doc"][0]["metrics"][
        "element_count_total"]["value"] == 3
    assert rp["summary"]["counts"][
        "element_count_total"]["sum"] == 2
    assert ri["summary"]["counts"][
        "element_count_total"]["sum"] == 3


# ---------- 17/20 指标面恒等 ----------

def test_metrics_face_seventeen_equal_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    mp = rp["per_doc"][0]["metrics"]
    mi = ri["per_doc"][0]["metrics"]
    assert set(mp) == set(mi)
    assert len(mp) == 20
    assert sum(1 for k in mp if mp[k] == mi[k]) == 17


def test_text_face_equal_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    mp = rp["per_doc"][0]["metrics"]
    mi = ri["per_doc"][0]["metrics"]
    for k in ("text_preservation_equal",
              "chunk_reference_intact_ratio",
              "text_char_multiset_precision",
              "text_char_multiset_recall",
              "heading_boundary_compliance",
              "pdf_locator_valid_ratio"):
        assert mp[k] == mi[k]


def test_success_equal_batch489(tmp_path):
    _pdfs(tmp_path)
    rp, ri = _runs(tmp_path)
    assert rp["summary"]["success_rates"] == \
        ri["summary"]["success_rates"] == {
            "pipeline_success": {"success_count": 1,
                                 "total": 1, "rate": 1.0}}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch489():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百五十批 ----------

def test_source_no_eval_batch489():
    assert "eval(" not in _src()


def test_source_no_exec_batch489():
    assert "exec(" not in _src()


def test_source_no_compile_batch489():
    assert "compile(" not in _src()


def test_source_no_globals_batch489():
    assert "globals(" not in _src()


def test_source_no_locals_batch489():
    assert "locals(" not in _src()


def test_source_no_os_system_batch489():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch489():
    assert "subprocess" not in _src()


def test_source_no_popen_batch489():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch489():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch489():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch489():
    assert "socket" not in _src()


def test_source_no_requests_batch489():
    assert "requests" not in _src()


def test_source_no_urllib_batch489():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch489():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch489():
    assert "yield" not in _src()


def test_source_no_async_await_batch489():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch489():
    assert _src().count("open(") == 2
