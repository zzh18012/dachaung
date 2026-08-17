"""evaluation/manifest.py 第三百七十八轮 edges 测试（Round 934）。

补强 edges113 未触及的角度（第三百一十批，probe 实证）。

新角度：
- content_group_count 配对语义四态：双向 d1↔d2 → 1；单向
  d1→d2 → 1（frozenset 集合去重）；链 d1→d2→d3 → 2
  （两个相交 frozenset 各算一组）；自配对 d1→d1 + 未配对
  d2 → 2
- 混合计数：pdf 1 + docx 1 → file 2 / pdf 1 / docx 1；
  空清单四属性全 0
- 默认根探测：不给 project_root → 向上找 pyproject.toml，
  tmp 链上没有 → 回退清单所在目录（samples 可见）
- load_manifest 接受 str 清单路径与 str 根
- JSON 语法错 → ManifestError "清单 JSON 解析失败: …"
- 盘符相对路径 "C:foo" 不逃逸：pathlib 拼接当普通段，
  resolved == 根/foo（path_str 原样保留）
- UNC //srv/share → startswith("/") 判绝对拒绝
- sha256 空串 → schema 正则 ^[0-9a-f]{64}$ 拒绝
- categories_covered 返回排序新列表（两次调用相等非同一）
- forbidden tokens 第四百零四批
"""

from __future__ import annotations

import inspect
import json

import pytest

from evaluation.manifest import ManifestError, load_manifest
from evaluation.schema import EvalSchemaError


def _mk(root, docs):
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = root / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    return f


def _entry(i, **kw):
    d = {"doc_id": f"d{i}", "path": "samples/a.pdf",
         "source_type": "pdf"}
    d.update(kw)
    return d


# ---------- content_group_count 四态 ----------

def test_group_bidirectional_batch132(tmp_path):
    m = load_manifest(_mk(tmp_path, [
        _entry(1, paired_with="d2"), _entry(2, paired_with="d1")]),
        tmp_path)
    assert m.content_group_count == 1


def test_group_unidirectional_batch132(tmp_path):
    m = load_manifest(_mk(tmp_path, [
        _entry(1, paired_with="d2"), _entry(2)]), tmp_path)
    assert m.content_group_count == 1


def test_group_chain_two_frozensets_batch132(tmp_path):
    m = load_manifest(_mk(tmp_path, [
        _entry(1, paired_with="d2"),
        _entry(2, paired_with="d3"), _entry(3)]), tmp_path)
    # frozenset{d1,d2} 与 frozenset{d2,d3} 相交但各算一组
    assert m.content_group_count == 2


def test_group_self_pair_plus_unpaired_batch132(tmp_path):
    m = load_manifest(_mk(tmp_path, [
        _entry(1, paired_with="d1"), _entry(2)]), tmp_path)
    assert m.content_group_count == 2


# ---------- 计数属性 ----------

def test_mixed_and_empty_counts_batch132(tmp_path):
    m = load_manifest(_mk(tmp_path, [
        _entry(1), _entry(2, source_type="docx")]), tmp_path)
    assert (m.file_count, m.pdf_count, m.docx_count) == (2, 1, 1)
    m0 = load_manifest(_mk(tmp_path, []), tmp_path)
    assert (m0.file_count, m0.pdf_count, m0.docx_count,
            m0.content_group_count) == (0, 0, 0, 0)


# ---------- 默认根探测 ----------

def test_default_root_detection_batch132(tmp_path):
    # tmp 链上无 pyproject.toml → 回退清单所在目录
    m = load_manifest(_mk(tmp_path, [_entry(1)]))
    assert m.project_root == tmp_path.resolve()
    assert (m.project_root / "samples").is_dir()


def test_str_manifest_and_root_batch132(tmp_path):
    f = _mk(tmp_path, [_entry(1)])
    m = load_manifest(str(f), str(tmp_path))
    assert m.file_count == 1


# ---------- JSON 语法错 ----------

def test_json_decode_error_message_batch132(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(bad, tmp_path)
    assert str(ei.value).startswith("清单 JSON 解析失败: ")


# ---------- 盘符相对路径不逃逸 ----------

def test_drive_relative_no_escape_batch132(tmp_path):
    m = load_manifest(_mk(tmp_path, [_entry(1, path="C:foo")]),
                      tmp_path)
    entry = m.documents[0]
    assert entry.path_str == "C:foo"
    assert entry.resolved_path == (tmp_path / "foo").resolve()
    assert entry.resolved_path.is_relative_to(
        tmp_path.resolve())


# ---------- UNC 拒绝 ----------

def test_unc_path_rejected_batch132(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mk(tmp_path, [
            _entry(1, path="//srv/share/x.pdf")]), tmp_path)
    assert "禁止绝对路径：//srv/share/x.pdf" in str(ei.value)


# ---------- sha256 空串 ----------

def test_sha256_empty_string_schema_batch132(tmp_path):
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, [_entry(1, sha256="")]),
                      tmp_path)
    assert "does not match '^[0-9a-f]{64}$'" in str(ei.value)


# ---------- categories_covered ----------

def test_categories_covered_sorted_new_list_batch132(tmp_path):
    m = load_manifest(_mk(tmp_path, [
        _entry(1, categories=["b", "a"])]), tmp_path)
    c1 = m.categories_covered
    c2 = m.categories_covered
    assert c1 == ["a", "b"]
    assert c1 == c2
    assert c1 is not c2


# ---------- 源码补强 ----------

def _src():
    import evaluation.manifest as mm
    return inspect.getsource(mm)


def test_source_key_lines_batch132():
    src = _src()
    assert "resolved = (project_root / path_str).resolve()" in src
    assert "return sorted(s)" in src
    assert 'if (parent / "pyproject.toml").is_file():' in src
    assert 'raise ManifestError(f"清单文件不存在: {p}")' in src
    assert 'raise ManifestError(f"清单 JSON 解析失败: {e}") from e' in src


# ---------- forbidden tokens 第四百零四批 ----------

def test_source_no_eval_batch132():
    assert "eval(" not in _src()


def test_source_no_exec_batch132():
    assert "exec(" not in _src()


def test_source_no_compile_batch132():
    assert "compile(" not in _src()


def test_source_no_globals_batch132():
    assert "globals(" not in _src()


def test_source_no_locals_batch132():
    assert "locals(" not in _src()


def test_source_no_os_system_batch132():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch132():
    assert "subprocess" not in _src()


def test_source_no_popen_batch132():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch132():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch132():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch132():
    assert "socket" not in _src()


def test_source_no_requests_batch132():
    assert "requests" not in _src()


def test_source_no_urllib_batch132():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch132():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch132():
    assert "yield" not in _src()


def test_source_no_async_await_batch132():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch132():
    assert _src().count("open(") == 1
