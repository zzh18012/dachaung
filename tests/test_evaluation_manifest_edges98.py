"""evaluation/manifest.py 第二百六十六轮 edges 测试（Round 822）。

补强 edges97 未触及的角度（第一百九十三批）。

新角度：
- categories 跨文档去重并集：d1 (x,y) + d2 (y,z) →
  ["x","y","z"]（entry 元组保各自原样）
- annotation_file 解析锚点是 **project_root**：清单里写
  "ann.json" → root/ann.json 绝对路径（不是清单所在目录）
- expected_failures 保序加载（f2 在前就排前，不排序）
- Manifest dataclass 相等：两份同内容清单 == True、is False
- devset_status "complete" 与 ef 条目并存
- forbidden tokens 第二百九十二批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import evaluation.manifest as man_mod
from evaluation.manifest import load_manifest


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "a.docx").write_bytes(b"x")
    return tmp, root


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


def _load(tmp, root, obj, name="m.json"):
    f = tmp / name
    f.write_text(json.dumps(obj), encoding="utf-8")
    return load_manifest(f, root)


# ---------- categories 去重并集 ----------

def test_categories_union_dedupe_batch55():
    tmp, root = _env()
    m = _load(tmp, root, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [_d("d1", categories=["x", "y"]),
                      _d("d2", "samples/a.docx",
                         source_type="docx",
                         categories=["y", "z"])]})
    assert m.categories_covered == ["x", "y", "z"]
    assert m.documents[0].categories == ("x", "y")


# ---------- annotation 锚点 ----------

def test_annotation_resolves_against_project_root_batch55():
    tmp, root = _env()
    ann = root / "ann.json"
    ann.write_text("{}", encoding="utf-8")
    m = _load(tmp, root, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [_d("d1", annotation_file="ann.json")]})
    assert m.documents[0].annotation_resolved == ann.resolve()


# ---------- ef 保序 ----------

def test_expected_failures_order_preserved_batch55():
    tmp, root = _env()
    m = _load(tmp, root, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f2", "path": "samples/a.pdf",
             "expected_error_code": "B"},
            {"doc_id": "f1", "path": "samples/a.pdf",
             "expected_error_code": "A"}]})
    assert [e.doc_id for e in m.expected_failures] == ["f2",
                                                       "f1"]
    assert [e.expected_error_code
            for e in m.expected_failures] == ["B", "A"]


# ---------- Manifest 相等 ----------

def test_manifest_equality_semantics_batch55():
    tmp, root = _env()
    base = {"manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [_d("d1")]}
    m1 = _load(tmp, root, base, "m1.json")
    m2 = _load(tmp, root, base, "m2.json")
    assert m1 == m2
    assert m1 is not m2


# ---------- complete + ef ----------

def test_complete_status_with_ef_batch55():
    tmp, root = _env()
    m = _load(tmp, root, {
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f", "path": "samples/a.pdf",
             "expected_error_code": "X"}]}, "m3.json")
    assert m.devset_status == "complete"
    assert len(m.expected_failures) == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "@property" in src
    assert "s.update(d.categories)" in src
    assert "return sorted(s)" in src


# ---------- forbidden tokens 第二百九十二批 ----------

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
