"""evaluation/manifest.py 第四百四十一轮 edges 测试（Round 997）。

补强 edges122 未触及的角度（第三百七十三批，probe 实证）。

新角度：
- 两个 PDF 互配（p1↔p2）→ content_group_count 1（配对计数
  对 source_type 完全不敏感，类型盲）
- pdf-pdf 配对 + 未配对 PDF → 1 + 1 = 2 组
- 2 PDF + 1 DOCX 全未配对 → file_count 3 / pdf_count 2 /
  docx_count 1 / groups 3 一次快照
- DocumentEntry 十字段 kitchen-sink 单锁（doc_id …
  expectations 全字段一次断言）
- categories_covered 只来自 documents，expected_failures
  条目（无 categories 字段）不参与
- forbidden tokens 第四百六十七批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    for n in ("a.pdf", "b.pdf", "c.pdf", "d.docx"):
        (tmp_path / "samples" / n).write_bytes(b"x")


def _d(i, p, **kw):
    base = {"doc_id": i, "path": f"samples/{p}",
            "source_type": "docx" if p.endswith(".docx") else "pdf"}
    base.update(kw)
    return base


def _load(tmp_path, docs, ef=None):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs, "expected_failures": ef or []}),
        encoding="utf-8")
    return load_manifest(f, tmp_path)


# ---------- 类型盲配对 ----------

def test_pdf_pdf_pair_one_group_batch195(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, [
        _d("p1", "a.pdf", paired_with="p2"),
        _d("p2", "b.pdf", paired_with="p1")])
    assert m.content_group_count == 1


def test_pdf_pdf_pair_plus_unpaired_batch195(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, [
        _d("p1", "a.pdf", paired_with="p2"),
        _d("p2", "b.pdf", paired_with="p1"),
        _d("p3", "c.pdf")])
    assert m.content_group_count == 2


# ---------- 计数快照 ----------

def test_mixed_counts_snapshot_batch195(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, [
        _d("p1", "a.pdf"), _d("p2", "b.pdf"), _d("w1", "d.docx")])
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.content_group_count == 3


# ---------- DocumentEntry 十字段单锁 ----------

def test_kitchen_sink_document_entry_batch195(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, [
        _d("k1", "a.pdf", sha256="b" * 64, categories=["x", "a"],
           paired_with="k2", annotation_file="samples/ann.json",
           expectations={"element_count_by_type": {"paragraph": 2}})])
    e = m.documents[0]
    assert e.doc_id == "k1"
    assert e.path_str == "samples/a.pdf"
    assert e.source_type == "pdf"
    assert e.sha256 == "b" * 64
    assert e.categories == ("x", "a")
    assert e.paired_with == "k2"
    assert e.annotation_file_str == "samples/ann.json"
    assert e.annotation_resolved.name == "ann.json"
    assert e.expectations == {"element_count_by_type":
                              {"paragraph": 2}}
    assert e.resolved_path == (tmp_path / "samples" /
                               "a.pdf").resolve()


# ---------- categories 不含 ef ----------

def test_categories_exclude_ef_entries_batch195(tmp_path):
    _setup(tmp_path)
    m = _load(tmp_path, [_d("c1", "a.pdf", categories=["only"])],
              [{"doc_id": "e1", "path": "samples/b.pdf",
                "expected_error_code": "E_X"}])
    assert m.categories_covered == ["only"]
    assert len(m.expected_failures) == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch195():
    src = _src()
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src
    assert "return groups + unpaired" in src
    assert "categories=tuple(d.get(\"categories\", []))" in src
    assert "expectations=d.get(\"expectations\")" in src


# ---------- forbidden tokens 第四百六十七批 ----------

def test_source_no_eval_batch195():
    assert "eval(" not in _src()


def test_source_no_exec_batch195():
    assert "exec(" not in _src()


def test_source_no_compile_batch195():
    assert "compile(" not in _src()


def test_source_no_globals_batch195():
    assert "globals(" not in _src()


def test_source_no_locals_batch195():
    assert "locals(" not in _src()


def test_source_no_os_system_batch195():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch195():
    assert "subprocess" not in _src()


def test_source_no_popen_batch195():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch195():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch195():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch195():
    assert "socket" not in _src()


def test_source_no_requests_batch195():
    assert "requests" not in _src()


def test_source_no_urllib_batch195():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch195():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch195():
    assert "yield" not in _src()


def test_source_no_async_await_batch195():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch195():
    assert _src().count("open(") == 1
