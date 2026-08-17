"""evaluation/manifest.py 第四百零六轮 edges 测试（Round 962）。

补强 edges117 未触及的角度（第三百三十八批，probe 实证）。

新角度：
- _is_absolute_like 直测七态：/foo 真、C:\\x 真、
  C:/x 真、rel/path 假、空串假、"C:"（len<3）假、
  "AB:/x"（[1]≠:）假
- _has_backslash 直测两态
- load_manifest 接受 str 参数（manifest_path 与
  project_root 都可为 str）
- ghost paired_with（引用不存在的 doc_id）不报错：
  frozenset({A, GHOST}) 计 1 组 + 未配对 C 计 1 组 →
  2 文档 2 组
- categories_covered 按 Unicode 码点排序：
  [b, A, Ä] → [A, b, Ä]（65 < 98 < 196）
- sha256 原样透传
- forbidden tokens 第四百三十二批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    _has_backslash,
    _is_absolute_like,
    load_manifest,
)

BS = chr(92)


# ---------- _is_absolute_like 直测 ----------

def test_is_absolute_like_matrix_batch160():
    assert _is_absolute_like("/foo") is True
    assert _is_absolute_like("C:" + BS + "x") is True
    assert _is_absolute_like("C:/x") is True
    assert _is_absolute_like("rel/path") is False
    assert _is_absolute_like("") is False
    assert _is_absolute_like("C:") is False
    assert _is_absolute_like("AB:/x") is False


def test_has_backslash_batch160():
    assert _has_backslash("a" + BS + "b") is True
    assert _has_backslash("a/b") is False


# ---------- str 参数 ----------

def test_str_arguments_batch160(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    m = load_manifest(str(f), str(tmp_path))
    assert m.file_count == 1
    assert m.project_root == tmp_path.resolve()


# ---------- ghost paired_with ----------

def test_ghost_paired_with_batch160(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "samples" / "b.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "A", "path": "samples/a.pdf",
             "source_type": "pdf", "paired_with": "GHOST"},
            {"doc_id": "C", "path": "samples/b.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    m = load_manifest(f, tmp_path)
    assert m.file_count == 2
    assert m.content_group_count == 2


# ---------- Unicode categories 排序 ----------

def test_unicode_categories_codepoint_sort_batch160(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/a.pdf",
                       "source_type": "pdf",
                       "categories": ["b", "A", "Ä"],
                       "sha256": "a" * 64}]}),
        encoding="utf-8")
    m = load_manifest(f, tmp_path)
    assert m.categories_covered == ["A", "b", "Ä"]
    assert m.documents[0].sha256 == "a" * 64


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch160():
    src = _src()
    assert 'if path_str.startswith("/"):' in src
    assert 'if len(path_str) >= 3 and path_str[1] == ":" and path_str[0].isalpha():' in src
    assert 'if path_str[2] in ("\\\\", "/"):' in src
    assert 'return "\\\\" in path_str' in src


# ---------- forbidden tokens 第四百三十二批 ----------

def test_source_no_eval_batch160():
    assert "eval(" not in _src()


def test_source_no_exec_batch160():
    assert "exec(" not in _src()


def test_source_no_compile_batch160():
    assert "compile(" not in _src()


def test_source_no_globals_batch160():
    assert "globals(" not in _src()


def test_source_no_locals_batch160():
    assert "locals(" not in _src()


def test_source_no_os_system_batch160():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch160():
    assert "subprocess" not in _src()


def test_source_no_popen_batch160():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch160():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch160():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch160():
    assert "socket" not in _src()


def test_source_no_requests_batch160():
    assert "requests" not in _src()


def test_source_no_urllib_batch160():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch160():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch160():
    assert "yield" not in _src()


def test_source_no_async_await_batch160():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch160():
    assert _src().count("open(") == 1
