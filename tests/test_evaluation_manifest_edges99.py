"""evaluation/manifest.py 第二百七十三轮 edges 测试（Round 829）。

补强 edges98 未触及的角度（第二百零三批）。

新角度：
- UNC 路径 `\\\\server\\share\\a.pdf`：绕过绝对路径检测
  （无前导 / 无盘符冒号），但仍被反斜杠检查拦截 →
  ManifestError「禁止反斜杠」
- 波浪号路径 `~/x.pdf`：不展开（Path.resolve 不做 expanduser），
  解析为 root/~/x.pdf，parent.name == "~"
- URL 形路径 `http://x`：`path_str[1]` 是 't' 非 ':' →
  不算绝对路径，原样加载
- doc_id 含空格 "my doc"：schema 只要求 minLength 1 → 原样保留
- 悬空 paired_with="ghost"（引用不存在的 doc_id）：
  frozenset {d1, ghost} → 1 组 / 1 文件（不报错）
- 两组互相对配 d1↔d2、d3↔d4 → 2 组 / 4 文件
- forbidden tokens 第二百九十九批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest

UNC = "\\\\server\\share\\a.pdf"


def _setup(tmp_dir):
    root = tmp_dir / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    return root


def _load(tmp_dir, docs, name="m.json", **over):
    root = _setup(tmp_dir) if not (tmp_dir / "proj").exists() else \
        tmp_dir / "proj"
    f = tmp_dir / name
    payload = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs}
    payload.update(over)
    f.write_text(json.dumps(payload), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


# ---------- UNC ----------

def test_unc_path_backslash_error_batch55(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, [_d("d1", UNC)], "m1.json")
    assert "禁止反斜杠" in str(ei.value)
    assert UNC in str(ei.value)


# ---------- 波浪号 ----------

def test_tilde_path_not_expanded_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1", "~/x.pdf")], "m2.json")
    p = m.documents[0].resolved_path
    assert p.name == "x.pdf"
    assert p.parent.name == "~"


# ---------- URL 形 ----------

def test_url_like_path_loads_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1", "http://x")], "m3.json")
    assert m.documents[0].path_str == "http://x"


# ---------- doc_id 空格 ----------

def test_doc_id_with_space_batch55(tmp_path):
    m = _load(tmp_path, [_d("my doc")], "m4.json")
    assert m.documents[0].doc_id == "my doc"


# ---------- 悬空配对 ----------

def test_dangling_paired_with_batch55(tmp_path):
    m = _load(tmp_path, [_d("d1", paired_with="ghost")], "m5.json")
    assert m.content_group_count == 1
    assert m.file_count == 1


# ---------- 两组互配 ----------

def test_two_disjoint_pairs_batch55(tmp_path):
    m = _load(tmp_path, [
        _d("d1", paired_with="d2"),
        _d("d2", "samples/b.pdf", paired_with="d1"),
        _d("d3", paired_with="d4"),
        _d("d4", "samples/b.pdf", paired_with="d3")], "m6.json")
    assert m.content_group_count == 2
    assert m.file_count == 4


# ---------- source 补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'startswith("/")' in src
    assert "必须使用正斜杠，禁止反斜杠：" in src


# ---------- forbidden tokens 第二百九十九批 ----------

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
