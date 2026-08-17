"""evaluation/manifest.py 第二百三十一轮 edges 测试（Round 787）。

补强 edges91-92 未触及的角度（第一百五十一批）。

新角度：
- _is_absolute_like 直接单测表：'/x'、'C:\\\\x'、'C:/x'、'c:/x'（小写
  盘符）、'//x' True；'C:x'（盘符后无斜杠）、'C'（单字符）、''、
  'relative/path' False
- 'C:' 裸盘符与 'C:x' 都穿过形式检查按相对名解析
  （project_root / 'C:'，词法、不要求存在）
- categories_covered 排序并集：("b","a")+("a","c") → ["a","b","c"]
- docx-only 清单：pdf_count 0 / docx_count 2 / content_group 2
  （两个未配对各 1 组）；devset_status "complete" 放行
- _detect_project_root 回退：整条父链无 pyproject.toml → 返回
  起点目录本身（文件与目录两种入参同值）
- 清单路径是目录 → ManifestError "清单文件不存在"
- annotation_file 正常解析：annotation_file_str 保原串、
  annotation_resolved == root/ann/x.json
- expected_failures source_type "txt"（四值枚举宽于 documents
  的二值枚举）原样保留
- forbidden tokens 第二百五十七批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

import evaluation.manifest as man_mod
from evaluation.manifest import (
    ManifestError,
    _detect_project_root,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


@pytest.fixture
def env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.docx").write_bytes(b"x")
    return tmp, root


def _write(tmp, name, obj):
    f = tmp / name
    f.write_text(json.dumps(obj), encoding="utf-8")
    return f


# ---------- _is_absolute_like 单测表 ----------

@pytest.mark.parametrize("s,expected", [
    ("/x", True),
    ("C:\\x", True),
    ("C:/x", True),
    ("c:/x", True),
    ("//x", True),
    ("C:x", False),
    ("C", False),
    ("", False),
    ("relative/path", False),
])
def test_is_absolute_like_table_batch54(s, expected):
    assert _is_absolute_like(s) is expected


# ---------- 'C:' 与 'C:x' 穿过形式检查 ----------

def test_bare_drive_passes_form_checks_batch54(env):
    tmp, _ = env
    ghost = tmp / "ghost"
    assert _resolve_relative_path("C:", ghost, "f") == \
        ghost.resolve() / "C:"
    assert _resolve_relative_path("C:x", ghost, "f") == \
        ghost.resolve() / "C:x"


# ---------- categories 并集与计数 ----------

def test_categories_sorted_union_and_counts_batch54(env):
    tmp, root = env
    mf = _write(tmp, "m.json", {
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.docx",
             "source_type": "docx", "categories": ["b", "a"]},
            {"doc_id": "d2", "path": "samples/a.docx",
             "source_type": "docx", "categories": ["a", "c"]},
        ]})
    m = load_manifest(mf, root)
    assert m.categories_covered == ["a", "b", "c"]
    assert (m.pdf_count, m.docx_count) == (0, 2)
    assert m.file_count == 2
    assert m.content_group_count == 2
    assert m.devset_status == "complete"


# ---------- 根探测回退 ----------

def test_detect_project_root_fallback_batch54(env):
    tmp, _ = env
    deep = tmp / "plain" / "sub"
    deep.mkdir(parents=True)
    marker = deep / "m.json"
    marker.write_text("{}", encoding="utf-8")
    assert _detect_project_root(marker) == deep
    assert _detect_project_root(deep) == deep


# ---------- 目录当清单路径 ----------

def test_manifest_path_is_directory_batch54(env):
    tmp, root = env
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(root, root)


# ---------- annotation 与 ef 映射 ----------

def test_annotation_and_ef_txt_source_type_batch54(env):
    tmp, root = env
    (root / "ann").mkdir()
    mf = _write(tmp, "m.json", {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.docx",
             "source_type": "docx", "annotation_file": "ann/x.json"}],
        "expected_failures": [
            {"doc_id": "f1", "path": "samples/a.docx",
             "expected_error_code": "open_error",
             "source_type": "txt"}]})
    m = load_manifest(mf, root)
    d = m.documents[0]
    assert d.annotation_file_str == "ann/x.json"
    assert d.annotation_resolved == root / "ann" / "x.json"
    ef = m.expected_failures[0]
    assert ef.source_type == "txt"
    assert len(m.expected_failures) == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(man_mod)


def test_source_absolute_like_lines_batch54():
    src = _src()
    assert 'if path_str[2] in ("\\\\", "/"):' in src
    assert "return cur" in src
    assert "categories=tuple(d.get(\"categories\", []))" in src


# ---------- forbidden tokens 第二百五十七批 ----------

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
