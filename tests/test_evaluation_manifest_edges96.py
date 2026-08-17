"""evaluation/manifest.py 第二百五十二轮 edges 测试（Round 808）。

补强 edges95 未触及的角度（第一百七十二批）。

新角度：
- 重复 doc_id：schema 无 uniqueKey → 两条都加载、file_count 2
- 自配对 d1→d1：frozenset 去重成单元素组 → content_group_count 1
  （1 个文档）
- 单向配对 d1→x1（x1 未回指）：seen 吸收双方 → 1 组 / 2 文档
  （"单向也算一组"注释的行为面）
- 空 documents + complete：全 0 计数 + categories []
- categories 顺序：entry 元组保序 ("b","a")，属性排序 ["a","b"]
- annotation_file ""：schema 放行（无 minLength）但 falsy →
  annotation_resolved None、annotation_file_str 原样存 ""
- manifest_path 传 str 等价
- documents source_type "txt" → EvalSchemaError（enum 只收
  pdf/docx；expected_failure 才收 txt）
- expectations dict 透传
- forbidden tokens 第二百七十八批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    return tmp, root


def _run(tmp, root, docs, name="m.json", status="incomplete"):
    f = tmp / name
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": status,
        "documents": docs}), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


# ---------- 重复 doc_id ----------

def test_duplicate_doc_id_both_loaded_batch55(env):
    tmp, root = env
    m = _run(tmp, root, [_d("d1"), _d("d1", "samples/b.pdf")])
    assert m.file_count == 2
    assert [d.doc_id for d in m.documents] == ["d1", "d1"]


# ---------- 自配对 ----------

def test_self_pair_one_group_batch55(env):
    tmp, root = env
    m = _run(tmp, root, [_d("d1", paired_with="d1")])
    assert m.content_group_count == 1
    assert m.file_count == 1


# ---------- 单向配对 ----------

def test_one_way_pair_one_group_batch55(env):
    tmp, root = env
    m = _run(tmp, root, [_d("d1", "samples/a.pdf", paired_with="x1"),
                         _d("x1", "samples/b.pdf")])
    assert m.content_group_count == 1
    assert m.file_count == 2


# ---------- 空清单 ----------

def test_empty_documents_all_zero_counts_batch55(env):
    tmp, root = env
    m = _run(tmp, root, [], status="complete")
    assert (m.file_count, m.content_group_count, m.pdf_count,
            m.docx_count) == (0, 0, 0, 0)
    assert m.categories_covered == []
    assert m.devset_status == "complete"


# ---------- categories 顺序 ----------

def test_categories_order_entry_vs_property_batch55(env):
    tmp, root = env
    m = _run(tmp, root, [_d("d1", categories=["b", "a"])])
    assert m.documents[0].categories == ("b", "a")
    assert m.categories_covered == ["a", "b"]


# ---------- annotation_file "" ----------

def test_annotation_file_empty_string_stored_batch55(env):
    tmp, root = env
    m = _run(tmp, root, [_d("d1", annotation_file="")])
    assert m.documents[0].annotation_file_str == ""
    assert m.documents[0].annotation_resolved is None


# ---------- str 清单路径 ----------

def test_manifest_path_str_equivalent_batch55(env):
    tmp, root = env
    f = tmp / "s.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": "incomplete",
                             "documents": []}), encoding="utf-8")
    m = load_manifest(str(f), root)
    assert m.file_count == 0


# ---------- documents source_type "txt" ----------

def test_documents_source_type_txt_rejected_batch55(env):
    tmp, root = env
    with pytest.raises(EvalSchemaError) as ei:
        _run(tmp, root, [{"doc_id": "d1", "path": "samples/a.pdf",
                          "source_type": "txt"}])
    assert "'txt' is not one of ['pdf', 'docx']" in str(ei.value)


# ---------- expectations 透传 ----------

def test_expectations_passthrough_batch55(env):
    tmp, root = env
    exp = {"element_count_by_type": {"paragraph": 2}}
    m = _run(tmp, root, [_d("d1", expectations=exp)])
    assert m.documents[0].expectations == exp


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "if d.get(\"annotation_file\"):" in src
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src
    assert "categories=tuple(d.get(\"categories\", []))" in src


# ---------- forbidden tokens 第二百七十八批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch55():
    assert _src().count("open(") == 1
