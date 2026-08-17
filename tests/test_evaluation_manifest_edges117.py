"""evaluation/manifest.py 第三百九十九轮 edges 测试（Round 955）。

补强 edges116 未触及的角度（第三百三十一批，probe 实证）。

新角度：
- 根检测向上走：清单放 sub/ 子目录、pyproject.toml 在
  tmp → project_root = tmp、resolved_path 在 tmp 下
- 无 pyproject 目录 → 根退化为清单所在目录
- 清单文件不存在 → ManifestError "清单文件不存在:
  <绝对路径>"（以文件名结尾）
- 非法 JSON → ManifestError "清单 JSON 解析失败: …"
- Manifest 是 frozen dataclass：赋值抛
  FrozenInstanceError
- "./samples/a.pdf" 与 "samples/../samples/a.pdf" 均放行
  （非绝对、无反斜杠、resolve 后仍在根内）；path_str
  原样保留（不做规范化）
- annotation_file 合法时 annotation_resolved 解析为绝对
  路径
- forbidden tokens 第四百二十五批（open 1）
"""

from __future__ import annotations

import dataclasses
import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest

DOCS = [{"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}]


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")


def _write(path, docs):
    path.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    return path


# ---------- 根检测向上走 ----------

def test_root_detected_upward_batch153(tmp_path):
    _setup(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()
    m = load_manifest(_write(sub / "m.json", DOCS))
    assert m.project_root == tmp_path.resolve()
    assert m.documents[0].resolved_path == \
        (tmp_path / "samples" / "a.pdf").resolve()


# ---------- 无 pyproject 回退 ----------

def test_root_fallback_to_manifest_dir_batch153(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    m = load_manifest(_write(tmp_path / "m.json", DOCS))
    assert m.project_root == tmp_path.resolve()
    assert m.documents[0].resolved_path == \
        (tmp_path / "samples" / "a.pdf").resolve()


# ---------- 清单不存在 ----------

def test_manifest_missing_batch153(tmp_path):
    _setup(tmp_path)
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path / "nope.json")
    assert str(ei.value).startswith("清单文件不存在: ")
    assert str(ei.value).endswith("nope.json")


# ---------- 非法 JSON ----------

def test_manifest_bad_json_batch153(tmp_path):
    _setup(tmp_path)
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(f)
    assert str(ei.value).startswith("清单 JSON 解析失败: ")


# ---------- frozen dataclass ----------

def test_manifest_frozen_batch153(tmp_path):
    _setup(tmp_path)
    m = load_manifest(_write(tmp_path / "m.json", DOCS),
                      tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.file_count = 5


# ---------- ./ 与 .. 前缀放行 ----------

@pytest.mark.parametrize("p", ["./samples/a.pdf",
                               "samples/../samples/a.pdf"])
def test_dot_prefixes_allowed_batch153(tmp_path, p):
    _setup(tmp_path)
    m = load_manifest(_write(tmp_path / "m.json", [
        {"doc_id": "d1", "path": p, "source_type": "pdf"}]),
        tmp_path)
    assert m.documents[0].path_str == p
    assert m.documents[0].resolved_path == \
        (tmp_path / "samples" / "a.pdf").resolve()


# ---------- annotation_resolved ----------

def test_annotation_resolved_batch153(tmp_path):
    _setup(tmp_path)
    m = load_manifest(_write(tmp_path / "m.json", [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf",
         "annotation_file": "samples/a.pdf"}]), tmp_path)
    assert m.documents[0].annotation_resolved == \
        (tmp_path / "samples" / "a.pdf").resolve()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch153():
    src = _src()
    assert 'raise ManifestError(f"清单文件不存在: {p}")' in src
    assert 'raise ManifestError(f"清单 JSON 解析失败: {e}") from e' in src
    assert 'for parent in [cur, *cur.parents]:' in src
    assert '@dataclass(frozen=True)' in src


# ---------- forbidden tokens 第四百二十五批 ----------

def test_source_no_eval_batch153():
    assert "eval(" not in _src()


def test_source_no_exec_batch153():
    assert "exec(" not in _src()


def test_source_no_compile_batch153():
    assert "compile(" not in _src()


def test_source_no_globals_batch153():
    assert "globals(" not in _src()


def test_source_no_locals_batch153():
    assert "locals(" not in _src()


def test_source_no_os_system_batch153():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch153():
    assert "subprocess" not in _src()


def test_source_no_popen_batch153():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch153():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch153():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch153():
    assert "socket" not in _src()


def test_source_no_requests_batch153():
    assert "requests" not in _src()


def test_source_no_urllib_batch153():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch153():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch153():
    assert "yield" not in _src()


def test_source_no_async_await_batch153():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch153():
    assert _src().count("open(") == 1
