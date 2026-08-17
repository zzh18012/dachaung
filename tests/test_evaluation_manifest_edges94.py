"""evaluation/manifest.py 第二百三十八轮 edges 测试（Round 794）。

补强 edges93 未触及的角度（第一百五十八批）。

新角度：
- 路径 "." 穿过形式检查 → 解析为 project_root 本身
  （relative_to(root, root) 恒成立）
- annotation_file 绝对路径 → ManifestError 字段名
  "documents[d1].annotation_file"（documents 路径之外的第二个
  字段名家族）
- 三文档配对环 d1→d2→d3→d1：三个 frozenset 两两不同 →
  content_group_count 3（环不折叠，现状记录）
- DocumentEntry frozen 可哈希：等值条目 hash 相等、== 相等；
  Manifest 同样可哈希
- forbidden tokens 第二百六十四批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import (
    DocumentEntry,
    Manifest,
    ManifestError,
    _resolve_relative_path,
    load_manifest,
)


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _write(tmp, obj):
    f = tmp / "m.json"
    f.write_text(json.dumps(obj), encoding="utf-8")
    return f


def _entry(root):
    return DocumentEntry("d", "s/a.pdf", root / "s/a.pdf", "pdf",
                         None, ("x",), None, None, None, None)


# ---------- 路径 "." ----------

def test_dot_path_resolves_to_root_batch54(env):
    _, root = env
    assert _resolve_relative_path(".", root, "f") == root.resolve()


# ---------- annotation 绝对路径字段名 ----------

def test_annotation_absolute_field_name_batch54(env):
    _, root = env
    with pytest.raises(ManifestError,
                       match="documents\\[d1\\]\\.annotation_file"):
        _resolve_relative_path("C:/x", root,
                               "documents[d1].annotation_file")


# ---------- 配对环 ----------

def test_pair_cycle_three_groups_batch54(env):
    tmp, root = env
    docs = [{"doc_id": f"d{i}", "path": "samples/a.pdf",
             "source_type": "pdf",
             "paired_with": f"d{i % 3 + 1}"} for i in (1, 2, 3)]
    m = load_manifest(_write(tmp, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs}), root)
    assert m.content_group_count == 3
    assert m.file_count == 3


# ---------- frozen 可哈希 ----------

def test_entry_hash_equality_batch54(env):
    _, root = env
    a, b = _entry(root), _entry(root)
    assert hash(a) == hash(b)
    assert a == b
    assert not a != b


def test_manifest_hashable_batch54(env):
    _, root = env
    assert isinstance(
        hash(Manifest("1.0", "incomplete", (), (), root)), int)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_frozen_dataclasses_batch54():
    src = _src()
    assert src.count("@dataclass(frozen=True)") == 3


# ---------- forbidden tokens 第二百六十四批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
