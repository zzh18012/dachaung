"""evaluation/manifest.py 第四百五十五轮 edges 测试（Round 1011）。

补强 edges124 未触及的角度（第三百八十七批，probe 实证）。

新角度（manifest → report 跨模块流锁）：
- 中文 doc_id "中文d" 合法加载且经 runner 流入 per_doc
  原样保留（顺序不排序）
- 跨类型配对（pdf↔docx）+ 三类别并集 → categories_covered
  排序 ['a','b','c']、content_group_count 1
- report.devset 六键整体 == manifest 属性直通
  （status/file_count/groups/pdf/docx/categories 一次锁）
- forbidden tokens 第四百八十一批（open 1）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


class _FakeDoc:
    parser_version = "pv"
    source_hash = "ab12cd34"

    def to_dict(self):
        return {
            "elements": [], "chunks": [], "source_type": "pdf",
            "document_id": "x", "schema_version": "0.1.0",
            "source_path": "a.pdf", "source_hash": "a" * 64,
            "parser_name": "fallback", "parser_version": "pv",
            "relations": [], "warnings": [], "errors": [],
            "metadata": {}}


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    for n in ("a.pdf", "b.docx"):
        (tmp_path / "samples" / n).write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "中文d", "path": "samples/a.pdf",
             "source_type": "pdf", "categories": ["b", "a"],
             "paired_with": "w1"},
            {"doc_id": "w1", "path": "samples/b.docx",
             "source_type": "docx", "categories": ["c"],
             "paired_with": "中文d"}]}), encoding="utf-8")
    m = load_manifest(mf, tmp_path)

    import evaluation.runner as runner_mod
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])):
        rep = runner_mod.run_evaluation(m, tmp_path / "o.json")
    return m, rep


# ---------- manifest 属性 ----------

def test_unicode_pair_properties_batch209(tmp_path):
    m, _ = _run(tmp_path)
    assert m.categories_covered == ["a", "b", "c"]
    assert m.content_group_count == 1
    assert m.pdf_count == 1 and m.docx_count == 1


# ---------- per_doc 保留中文 doc_id ----------

def test_unicode_doc_id_flows_to_per_doc_batch209(tmp_path):
    _, rep = _run(tmp_path)
    assert [p["doc_id"] for p in rep["per_doc"]] == ["中文d",
                                                     "w1"]


# ---------- devset 六键直通 ----------

def test_devset_six_key_passthrough_batch209(tmp_path):
    _, rep = _run(tmp_path)
    assert rep["devset"] == {
        "status": "incomplete",
        "file_count": 2,
        "content_group_count": 1,
        "pdf_count": 1,
        "docx_count": 1,
        "categories_covered": ["a", "b", "c"]}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch209():
    src = _src()
    assert "return sorted(s)" in src
    assert "categories_covered" in src
    assert "paired_with: str | None" in src
    assert "expectations: dict[str, Any] | None" in src


# ---------- forbidden tokens 第四百八十一批 ----------

def test_source_no_eval_batch209():
    assert "eval(" not in _src()


def test_source_no_exec_batch209():
    assert "exec(" not in _src()


def test_source_no_compile_batch209():
    assert "compile(" not in _src()


def test_source_no_globals_batch209():
    assert "globals(" not in _src()


def test_source_no_locals_batch209():
    assert "locals(" not in _src()


def test_source_no_os_system_batch209():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch209():
    assert "subprocess" not in _src()


def test_source_no_popen_batch209():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch209():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch209():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch209():
    assert "socket" not in _src()


def test_source_no_requests_batch209():
    assert "requests" not in _src()


def test_source_no_urllib_batch209():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch209():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch209():
    assert "yield" not in _src()


def test_source_no_async_await_batch209():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch209():
    assert _src().count("open(") == 1
