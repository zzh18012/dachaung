"""evaluation/runner.py 第五百八十五轮 edges 测试（Round 1141）。

补强 edges159 未触及的角度（第五百一十七批，probe 实证）。

新角度（heading 分类边界 / 句读结尾 / 空白折叠）：
- **80/81 一字符分界**——恰 80 字符无句读 → heading；
  81 字符同构 → paragraph——分类阈值 len<=80 的两端
  精确锁定
- **叹号问号结尾**——"Wow great!" 与 "Is this a
  question?" 皆 → paragraph——! 和 ? 与句号同属句读
  集合，短而不当 heading
- **内部空白折叠**——字面串双空格 "A  double  space
  sentence." → 元素 content 恰单空格——折叠发生在
  parse 层，chunk 文本继承（首锁）
- forbidden tokens 第六百一十四批（open 2）
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
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 900 100]"
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


def _doc(tmp_path, text, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _build_one_page_pdf(
            b"BT /F1 12 Tf 10 80 Td (" + text + b") Tj ET"))


def _classify(tmp_path, text, doc_id):
    _doc(tmp_path, text, doc_id)
    doc, errors = process_single(
        tmp_path / "samples" / f"{doc_id}.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    return doc.to_dict()["elements"][0]


# ---------- 80/81 一字符分界 ----------

def test_eighty_chars_heading_batch340(tmp_path):
    el = _classify(tmp_path, b"h" * 80, "c80")
    assert el["type"] == "heading"
    assert el["metadata"] == {"level": 0, "heuristic": "short_line"}


def test_eighty_one_chars_paragraph_batch340(tmp_path):
    el = _classify(tmp_path, b"h" * 81, "c81")
    assert el["type"] == "paragraph"
    assert el["metadata"] == {}


# ---------- 叹号问号结尾 ----------

def test_exclamation_paragraph_batch340(tmp_path):
    el = _classify(tmp_path, b"Wow great!", "ex")
    assert el["type"] == "paragraph"


def test_question_paragraph_batch340(tmp_path):
    el = _classify(tmp_path, b"Is this a question?", "qu")
    assert el["type"] == "paragraph"


# ---------- 内部空白折叠 ----------

def test_double_space_collapsed_batch340(tmp_path):
    _doc(tmp_path, b"A  double  space  sentence.", "ds")
    doc, errors = process_single(
        tmp_path / "samples" / "ds.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    assert d["elements"][0]["content"] == "A double space sentence."
    assert d["chunks"][0]["text"] == "A double space sentence."


def test_collapse_runner_metrics_batch340(tmp_path):
    _doc(tmp_path, b"A  double  space  sentence.", "ds2")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "ds2", "path": "samples/ds2.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    r = run_evaluation(load_manifest(mf, project_root=tmp_path),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch340():
    src = _src()
    assert src.count("error_code") == 4
    assert src.count("load_annotation") == 2
    assert src.count("chunk") == 9


# ---------- forbidden tokens 第六百一十四批 ----------

def test_source_no_eval_batch340():
    assert "eval(" not in _src()


def test_source_no_exec_batch340():
    assert "exec(" not in _src()


def test_source_no_compile_batch340():
    assert "compile(" not in _src()


def test_source_no_globals_batch340():
    assert "globals(" not in _src()


def test_source_no_locals_batch340():
    assert "locals(" not in _src()


def test_source_no_os_system_batch340():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch340():
    assert "subprocess" not in _src()


def test_source_no_popen_batch340():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch340():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch340():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch340():
    assert "socket" not in _src()


def test_source_no_requests_batch340():
    assert "requests" not in _src()


def test_source_no_urllib_batch340():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch340():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch340():
    assert "yield" not in _src()


def test_source_no_async_await_batch340():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch340():
    assert _src().count("open(") == 2
