"""evaluation/cli.py 第四百五十一轮 edges 测试（Round 1007）。

补强 edges123 未触及的角度（第三百八十三批，probe 实证）。

新角度（inspect-doc 输出中的指标分歧可见性）：
- elements=0 + chunks=1：counts 行 "elements=0 chunks=1"；
  chunk_reference_intact_ratio **0.0000**（有 chunks 就有
  分母，非 null）；equal false；precision 0.0000 而
  recall null "empty_expected"（单侧空分歧直接渲染在
  输出里）
- docx 文档双 locator 分歧：docx_locator 1.0000 与
  pdf_locator null (not_pdf_document) 同屏
- forbidden tokens 第四百七十七批（open 1）
"""

from __future__ import annotations

import inspect
import io
import contextlib
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _inspect(tmp_path, doc):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), \
            contextlib.redirect_stderr(err):
        rc = main(["inspect-doc", str(f)])
    return rc, buf.getvalue()


# ---------- elements=0 + chunks=1 ----------

def test_empty_elements_one_chunk_divergence_batch205(tmp_path):
    doc = {"document_id": "d", "source_type": "pdf",
           "elements": [],
           "chunks": [{"chunk_id": "c1", "text": "x",
                       "source_element_ids": ["e9"],
                       "char_count": 1}]}
    rc, out = _inspect(tmp_path, doc)
    assert rc == 0
    assert "counts:      elements=0 chunks=1" in out
    assert ("  chunk_reference_intact_ratio         "
            "0.0000  (ok)") in out
    assert ("  text_preservation_equal              "
            "false  (ok)") in out
    assert ("  text_char_multiset_precision         "
            "0.0000  (ok)") in out
    assert ("  text_char_multiset_recall            "
            "null  (empty_expected)") in out


# ---------- docx 双 locator 同屏 ----------

def test_docx_dual_locator_divergence_batch205(tmp_path):
    doc = {"document_id": "d", "source_type": "docx",
           "elements": [
               {"element_id": "e1", "type": "paragraph",
                "content": "hi", "parent_id": None,
                "confidence": 0.9, "metadata": {},
                "source_locator": {"paragraph_index": 0}}],
           "chunks": [{"chunk_id": "c1", "text": "hi",
                       "source_element_ids": ["e1"],
                       "char_count": 2}]}
    rc, out = _inspect(tmp_path, doc)
    assert rc == 0
    assert ("  docx_locator_valid_ratio             "
            "1.0000  (ok)") in out
    assert ("  pdf_locator_valid_ratio              "
            "null  (not_pdf_document)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch205():
    src = _src()
    assert 'f"      documents={n_docs}（成功 {n_ok}，失败 {n_fail}）\\n"' in src
    assert "n_fail = n_docs - n_ok" in src
    assert "return _run_inspect_doc(args)" in src


# ---------- forbidden tokens 第四百七十七批 ----------

def test_source_no_eval_batch205():
    assert "eval(" not in _src()


def test_source_no_exec_batch205():
    assert "exec(" not in _src()


def test_source_no_compile_batch205():
    assert "compile(" not in _src()


def test_source_no_globals_batch205():
    assert "globals(" not in _src()


def test_source_no_locals_batch205():
    assert "locals(" not in _src()


def test_source_no_os_system_batch205():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch205():
    assert "subprocess" not in _src()


def test_source_no_popen_batch205():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch205():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch205():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch205():
    assert "socket" not in _src()


def test_source_no_requests_batch205():
    assert "requests" not in _src()


def test_source_no_urllib_batch205():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch205():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch205():
    assert "yield" not in _src()


def test_source_no_async_await_batch205():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch205():
    assert _src().count("open(") == 1
