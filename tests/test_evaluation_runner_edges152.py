"""evaluation/runner.py 第五百七十七轮 edges 测试（Round 1133）。

补强 edges151 未触及的角度（第五百零九批，probe 实证）。

新角度（PDF 文本操作符三态）：
- **单 BT 多 Tj 合并**——同一 BT/ET 块内两个 Tj（第二个
  带 Td 位移）→ 恰 1 个 paragraph "Alpha part. Beta part."
  page 1——run 归并不要求独立 BT 块（首锁）
- **TJ 数组操作符**——[(Tee) 20 (Jay) -10 ( arr.)] TJ →
  1 个 paragraph "TeeJay arr."——字距数字被忽略、子串
  拼接（首锁）
- **首尾空白剥除**——字面串 "   padded text here   "
  → 元素 content 恰 "padded text here"——parser 剥首尾
  空白、保留内部（首锁）
- **runner 级 TJ 全胜**——TJ 板真跑：success True + ect 1
  + text_equal True——TJ 文本全链路不丢
- forbidden tokens 第六百零六批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_one_page_pdf(stream) -> bytes:
    objects = {}
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = b"<</Type/Pages/Kids[3 0 R]/Count 1>>"
    objects[3] = (
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 100]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>")
    objects[4] = b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"
    objects[5] = (
        b"<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"\nendstream ")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path, pdf_bytes, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 单 BT 多 Tj 合并 ----------

def test_single_bt_multi_tj_merge_batch332(tmp_path):
    pdf = _build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td (Alpha part.) Tj "
        b"100 0 Td (Beta part.) Tj ET")
    _board(tmp_path, pdf, "mt")
    doc, errors = process_single(
        tmp_path / "samples" / "mt.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "paragraph"
    assert els[0]["content"] == "Alpha part. Beta part."
    assert els[0]["source_locator"]["page"] == 1


# ---------- TJ 数组操作符 ----------

def test_tj_array_operator_batch332(tmp_path):
    pdf = _build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td "
        b"[(Tee) 20 (Jay) -10 ( arr.)] TJ ET")
    _board(tmp_path, pdf, "tj")
    doc, errors = process_single(
        tmp_path / "samples" / "tj.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["content"] == "TeeJay arr."


# ---------- 首尾空白剥除 ----------

def test_padding_stripped_batch332(tmp_path):
    pdf = _build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td "
        b"(   padded text here   ) Tj ET")
    _board(tmp_path, pdf, "pd")
    doc, errors = process_single(
        tmp_path / "samples" / "pd.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["content"] == "padded text here"


# ---------- runner 级 TJ 全胜 ----------

def test_tj_runner_success_batch332(tmp_path):
    pdf = _build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td "
        b"[(Tee) 20 (Jay) -10 ( arr.)] TJ ET")
    r = run_evaluation(_board(tmp_path, pdf, "tj2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 1, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch332():
    src = _src()
    assert src.count("annotation") == 10
    assert src.count("chunk") == 9


# ---------- forbidden tokens 第六百零六批 ----------

def test_source_no_eval_batch332():
    assert "eval(" not in _src()


def test_source_no_exec_batch332():
    assert "exec(" not in _src()


def test_source_no_compile_batch332():
    assert "compile(" not in _src()


def test_source_no_globals_batch332():
    assert "globals(" not in _src()


def test_source_no_locals_batch332():
    assert "locals(" not in _src()


def test_source_no_os_system_batch332():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch332():
    assert "subprocess" not in _src()


def test_source_no_popen_batch332():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch332():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch332():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch332():
    assert "socket" not in _src()


def test_source_no_requests_batch332():
    assert "requests" not in _src()


def test_source_no_urllib_batch332():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch332():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch332():
    assert "yield" not in _src()


def test_source_no_async_await_batch332():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch332():
    assert _src().count("open(") == 2
