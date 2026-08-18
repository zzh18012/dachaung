"""evaluation/runner.py 第六百轮 edges 测试（Round 1156）。

补强 edges171 未触及的角度（第五百二十八批，probe 实证）。

新角度（异构三文档 devset 汇总 / 图片资源真在盘）：
- **文+表+图三板同 devset**——纯文本 PDF、网格
  表 PDF、嵌入图 PDF → file_count 3、element_count
  _total {sum 4, participating 3}、success 3/3
  （异构汇总首锁）
- **image_resource_exists_ratio 真跑 1.0**——真
  嵌入图的资源文件落盘存在 → 1.0；文/表板 null
  no_image_elements（分源参评镜像 locator 行为）
- **macro 分层**——summary 该指标 {1.0, participating
  1, not_evaluated 2}
- **全中 expectations 零 drop**——三板 expectations
  与真实精确一致 → 每 doc 0 + total 0；图板
  {image: 2} 超计 → 该 doc 1 + total 1
- forbidden tokens 第六百二十八批（open 2）
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


def _img_pdf() -> bytes:
    s = b"q 50 0 0 50 10 30 cm /Im0 Do Q"
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</XObject<</Im0 5 0 R>>"
            b"/Font<</F1 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8"
            b"/Length 3>>stream\n" + b"\xff\x00\x00"
            + b"\nendstream "),
        6: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 7)


def _txt_pdf() -> bytes:
    s = (b"BT /F1 12 Tf 10 80 Td "
         b"(Plain text document body here.) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 5 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _tbl_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 40 100 40 re S\n60 40 0 40 re S\n"
         b"10 60 100 0 re S\n"
         b"BT /F1 10 Tf 15 65 Td (Aa Bb) Tj ET\n"
         b"BT /F1 10 Tf 65 65 Td (Cc Dd) Tj ET\n"
         b"BT /F1 10 Tf 15 45 Td (Ee Ff) Tj ET\n"
         b"BT /F1 10 Tf 65 45 Td (Gg Hh) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 5 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path, img_expect=None):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "img.pdf").write_bytes(_img_pdf())
    (tmp_path / "txt.pdf").write_bytes(_txt_pdf())
    (tmp_path / "tbl.pdf").write_bytes(_tbl_pdf())
    t3_exp = {"element_count_by_type": {
        "image": 2 if img_expect else 1}}
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "t1", "path": "txt.pdf",
             "source_type": "pdf",
             "expectations": {"element_count_by_type":
                              {"paragraph": 1}}},
            {"doc_id": "t2", "path": "tbl.pdf",
             "source_type": "pdf",
             "expectations": {"element_count_by_type":
                              {"table": 1, "heading": 1}}},
            {"doc_id": "t3", "path": "img.pdf",
             "source_type": "pdf",
             "expectations": t3_exp},
        ]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 异构三文档 devset 汇总 ----------

def test_hetero_devset_summary_batch354(tmp_path):
    r = run_evaluation(_board(tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=100)
    assert r["devset"] == {
        "status": "incomplete", "file_count": 3,
        "content_group_count": 3, "pdf_count": 3,
        "docx_count": 0, "categories_covered": []}
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 4, "participating_docs": 3}
    assert r["summary"]["success_rates"]["pipeline_success"] \
        == {"success_count": 3, "total": 3, "rate": 1.0}


# ---------- image_resource_exists_ratio 真跑 ----------

def test_image_resource_ratio_live_batch354(tmp_path):
    r = run_evaluation(_board(tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=100)
    by_id = {p["doc_id"]: p["metrics"]
             for p in r["per_doc"]}
    assert by_id["t3"]["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}
    assert by_id["t1"]["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}
    assert by_id["t2"]["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


def test_image_ratio_macro_batch354(tmp_path):
    r = run_evaluation(_board(tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=100)
    ratio = r["summary"]["ratio_macro_averages"][
        "image_resource_exists_ratio"]
    assert ratio == {"macro_average": 1.0,
                     "participating_docs": 1,
                     "not_evaluated": 2}


# ---------- 全中 expectations 零 drop ----------

def test_exact_expectations_zero_drop_batch354(tmp_path):
    r = run_evaluation(_board(tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=100)
    for p in r["per_doc"]:
        assert p["metrics"]["silent_drop_count"] == {
            "value": 0, "reason": None}
    assert r["summary"]["silent_drop_total"] == 0


# ---------- 超计 expectation → drop 1 ----------

def test_overcount_expectation_drop_batch354(tmp_path):
    r = run_evaluation(_board(tmp_path, img_expect=True),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=100)
    by_id = {p["doc_id"]: p["metrics"]
             for p in r["per_doc"]}
    assert by_id["t3"]["silent_drop_count"] == {
        "value": 1, "reason": None}
    assert by_id["t1"]["silent_drop_count"] == {
        "value": 0, "reason": None}
    assert r["summary"]["silent_drop_total"] == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch354():
    src = _src()
    assert src.count("manifest") == 5
    assert src.count("error_code") == 4
    assert src.count("annotation") == 10


# ---------- forbidden tokens 第六百二十八批 ----------

def test_source_no_eval_batch354():
    assert "eval(" not in _src()


def test_source_no_exec_batch354():
    assert "exec(" not in _src()


def test_source_no_compile_batch354():
    assert "compile(" not in _src()


def test_source_no_globals_batch354():
    assert "globals(" not in _src()


def test_source_no_locals_batch354():
    assert "locals(" not in _src()


def test_source_no_os_system_batch354():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch354():
    assert "subprocess" not in _src()


def test_source_no_popen_batch354():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch354():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch354():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch354():
    assert "socket" not in _src()


def test_source_no_requests_batch354():
    assert "requests" not in _src()


def test_source_no_urllib_batch354():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch354():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch354():
    assert "yield" not in _src()


def test_source_no_async_await_batch354():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch354():
    assert _src().count("open(") == 2
