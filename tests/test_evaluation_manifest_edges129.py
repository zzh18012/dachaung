"""evaluation/manifest.py 第四百八十九轮 edges 测试（Round 1045）。

补强 edges128 未触及的角度（第四百二十一批，probe 实证）。

新角度（真实 docx + 真 sha256 + 嵌套自动根复合）：
- manifest 测试 128 轮全部 b"x" 伪字节或空文件、
  sha256 全是任意假串；本批首次用真实 python-docx
  文档 + hashlib 真值 sha256（64 位 hex 逐字往返）
- 清单放嵌套子目录（manifests/m.json）、不传
  project_root → _detect_project_root 从清单目录
  向上爬到 pyproject.toml 所在根；resolved_path /
  annotation_resolved 双双锚定在检出根
- 九字段全量入口（真文件 + 真 sha256 + categories +
  paired_with + annotation_file + expectations）单次
  加载逐属性锁定；categories 元组保序 ('beta',
  'alpha') 而 categories_covered 排序 ['alpha',
  'beta']——同一信息两种秩序同屏
- paired_with 指向缺席 d2 → content_group_count 1
  （孤儿配对计一组）
- forbidden tokens 第五百一十六批（open 1）
"""

from __future__ import annotations

import hashlib
import inspect
import json

from docx import Document

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


def _load(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("",
                                         encoding="utf-8")
    (proj / "samples").mkdir()
    (proj / "anns").mkdir()
    p = proj / "samples" / "real.docx"
    d = Document()
    d.add_paragraph("Hello world paragraph one.")
    d.save(str(p))
    (proj / "anns" / "ann.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": []}), encoding="utf-8")
    mf = proj / "manifests" / "m.json"
    mf.parent.mkdir()
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "samples/real.docx",
            "source_type": "docx", "sha256": sha,
            "categories": ["beta", "alpha"],
            "paired_with": "d2",
            "annotation_file": "anns/ann.json",
            "expectations": {"element_count_by_type":
                             {"paragraph": 2}}}],
        "expected_failures": []}), encoding="utf-8")
    m = load_manifest(mf)
    return m, proj, p, sha


# ---------- 嵌套自动根 ----------

def test_auto_root_nested_climb_batch243(tmp_path):
    m, proj, _, _ = _load(tmp_path)
    assert m.project_root == proj


# ---------- 真 sha256 往返 ----------

def test_true_sha256_roundtrip_batch243(tmp_path):
    m, proj, p, sha = _load(tmp_path)
    e = m.documents[0]
    assert e.sha256 == sha
    assert len(e.sha256) == 64
    assert e.sha256 == hashlib.sha256(
        p.read_bytes()).hexdigest()


# ---------- 九字段全量入口 ----------

def test_full_entry_attributes_batch243(tmp_path):
    m, proj, p, _ = _load(tmp_path)
    e = m.documents[0]
    assert e.doc_id == "d1"
    assert e.path_str == "samples/real.docx"
    assert e.resolved_path == p
    assert e.source_type == "docx"
    assert e.annotation_file_str == "anns/ann.json"
    assert e.annotation_resolved == proj / "anns" / "ann.json"
    assert e.paired_with == "d2"
    assert e.expectations == {
        "element_count_by_type": {"paragraph": 2}}


# ---------- 保序 vs 排序两种秩序 ----------

def test_categories_order_vs_sorted_batch243(tmp_path):
    m, _, _, _ = _load(tmp_path)
    assert m.documents[0].categories == ("beta", "alpha")
    assert m.categories_covered == ["alpha", "beta"]


# ---------- 孤儿配对计组 ----------

def test_absent_pair_counts_one_group_batch243(tmp_path):
    m, _, _, _ = _load(tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.content_group_count == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch243():
    src = _src()
    assert "for parent in [cur, *cur.parents]:" in src
    assert 'if (parent / "pyproject.toml").is_file():' in src


# ---------- forbidden tokens 第五百一十六批 ----------

def test_source_no_eval_batch243():
    assert "eval(" not in _src()


def test_source_no_exec_batch243():
    assert "exec(" not in _src()


def test_source_no_compile_batch243():
    assert "compile(" not in _src()


def test_source_no_globals_batch243():
    assert "globals(" not in _src()


def test_source_no_locals_batch243():
    assert "locals(" not in _src()


def test_source_no_os_system_batch243():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch243():
    assert "subprocess" not in _src()


def test_source_no_popen_batch243():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch243():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch243():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch243():
    assert "socket" not in _src()


def test_source_no_requests_batch243():
    assert "requests" not in _src()


def test_source_no_urllib_batch243():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch243():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch243():
    assert "yield" not in _src()


def test_source_no_async_await_batch243():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch243():
    assert _src().count("open(") == 1
