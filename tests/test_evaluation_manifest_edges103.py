"""evaluation/manifest.py 第三百零一轮 edges 测试（Round 857）。

补强 edges102 未触及的角度（第二百三十一批）。

新角度：
- load_manifest 收 str 清单路径（Path().resolve() 包装）
- 三角互指 d1→d2→d3→d1：frozenset 三组 → 3 组
  （环不被折叠成 1 组的现状锁定）
- annotation_file 走子目录 "anns/x.json" 照常解析
- categories_covered 排序区分大小写（"A" < "_" < "b"）
- forbidden tokens 第三百二十七批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


def _load(tmp_path, docs, name="m.json", **over):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    (root / "samples" / "c.pdf").write_bytes(b"x")
    (root / "anns").mkdir(exist_ok=True)
    (root / "anns" / "x.json").write_text("{}", encoding="utf-8")
    f = tmp_path / name
    payload = {"manifest_version": "1.0",
               "devset_status": "incomplete",
               "documents": docs}
    payload.update(over)
    f.write_text(json.dumps(payload), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


# ---------- str 清单路径 ----------

def test_str_manifest_path_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1")])
    f = tmp_path / "again.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    m2 = load_manifest(str(f),
                       tmp_path / "proj")
    assert m2.file_count == 1
    assert m2.documents[0].resolved_path == \
        m.documents[0].resolved_path


# ---------- 三角互指 ----------

def test_triangle_pairing_three_groups_batch55(tmp_path):
    m = _load(tmp_path, [
        _d("d1", paired_with="d2"),
        _d("d2", "samples/b.pdf", paired_with="d3"),
        _d("d3", "samples/c.pdf", paired_with="d1")])
    assert m.content_group_count == 3
    assert m.file_count == 3


# ---------- 子目录标注 ----------

def test_annotation_subdir_batch55(tmp_path):
    m = _load(tmp_path, [
        _d("d1", annotation_file="anns/x.json")])
    assert m.documents[0].annotation_resolved == \
        tmp_path / "proj" / "anns" / "x.json"
    assert m.documents[0].annotation_file_str == \
        "anns/x.json"


# ---------- 大小写排序 ----------

def test_categories_case_sensitive_sort_batch55(tmp_path):
    m = _load(tmp_path, [
        _d("d1", categories=["b", "A", "_"])])
    assert m.categories_covered == ["A", "_", "b"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "p = Path(manifest_path).resolve()" in src
    assert "groups = 0" in src
    assert "return groups + unpaired" in src


# ---------- forbidden tokens 第三百二十七批 ----------

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
