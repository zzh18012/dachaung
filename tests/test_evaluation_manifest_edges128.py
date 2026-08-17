"""evaluation/manifest.py 第四百七十六轮 edges 测试（Round 1032）。

补强 edges127 未触及的角度（第四百零八批，probe 实证）。

新角度（富 manifest 单次加载合流）：
- documents 列表序保持 manifest 文件序（d2 在 d1 前
  加载后依旧 [d2, d1, d3]——按 doc_id 排序会被锁死）
- 倒指配对：d2 先出现且 paired_with 指向"后面才出现"
  的 d1、d1 回指 d2 → content_group_count 仍 2（配对
  图与列举方向无关）
- categories 跨文档交错去重排序：["beta","alpha"] +
  ["alpha","gamma"] → ["alpha","beta","gamma"]
- 计数合流：file_count 3 / pdf 2 / docx 1 同屏
- path 内部 "./"（samples/./a.pdf）：加载 OK、path_str
  原样保留、resolved 与干净路径等价（edges101 只锁过
  前缀 "./" 变体）
- forbidden tokens 第五百零三批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


def _setup(tmp_path, docs):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir(parents=True, exist_ok=True)
    for n in ("a.pdf", "b.pdf", "c.docx"):
        (tmp_path / "samples" / n).write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": docs, "expected_failures": []}),
        encoding="utf-8")
    return load_manifest(mf, tmp_path)


_RICH_DOCS = [
    {"doc_id": "d2", "path": "samples/b.pdf",
     "source_type": "pdf", "paired_with": "d1",
     "categories": ["beta", "alpha"]},
    {"doc_id": "d1", "path": "samples/a.pdf",
     "source_type": "pdf", "paired_with": "d2",
     "categories": ["alpha", "gamma"]},
    {"doc_id": "d3", "path": "samples/c.docx",
     "source_type": "docx"}]


# ---------- 富 manifest 合流 ----------

def test_document_order_preserved_batch230(tmp_path):
    m = _setup(tmp_path, _RICH_DOCS)
    assert [d.doc_id for d in m.documents] == ["d2", "d1",
                                               "d3"]


def test_backward_pair_groups_batch230(tmp_path):
    m = _setup(tmp_path, _RICH_DOCS)
    assert m.documents[0].paired_with == "d1"
    assert m.documents[1].paired_with == "d2"
    assert m.content_group_count == 2


def test_categories_interleaved_dedup_sorted_batch230(
        tmp_path):
    m = _setup(tmp_path, _RICH_DOCS)
    assert m.categories_covered == ["alpha", "beta",
                                    "gamma"]


def test_counts_composite_batch230(tmp_path):
    m = _setup(tmp_path, _RICH_DOCS)
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.devset_status == "complete"


# ---------- path 内部 "./" ----------

def test_inner_dot_path_equivalent_batch230(tmp_path):
    m = _setup(tmp_path, [
        {"doc_id": "d1", "path": "samples/./a.pdf",
         "source_type": "pdf"}])
    assert m.documents[0].path_str == "samples/./a.pdf"
    clean = _setup(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}])
    assert (m.documents[0].resolved_path
            == clean.documents[0].resolved_path)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch230():
    src = _src()
    assert ("return sum(1 for d in self.documents"
            ' if d.source_type == "pdf")') in src
    assert "if d.paired_with:" in src
    assert "sorted(" in src


# ---------- forbidden tokens 第五百零三批 ----------

def test_source_no_eval_batch230():
    assert "eval(" not in _src()


def test_source_no_exec_batch230():
    assert "exec(" not in _src()


def test_source_no_compile_batch230():
    assert "compile(" not in _src()


def test_source_no_globals_batch230():
    assert "globals(" not in _src()


def test_source_no_locals_batch230():
    assert "locals(" not in _src()


def test_source_no_os_system_batch230():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch230():
    assert "subprocess" not in _src()


def test_source_no_popen_batch230():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch230():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch230():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch230():
    assert "socket" not in _src()


def test_source_no_requests_batch230():
    assert "requests" not in _src()


def test_source_no_urllib_batch230():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch230():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch230():
    assert "yield" not in _src()


def test_source_no_async_await_batch230():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch230():
    assert _src().count("open(") == 1
