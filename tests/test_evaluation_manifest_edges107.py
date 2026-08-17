"""evaluation/manifest.py 第三百二十九轮 edges 测试（Round 885）。

补强 edges106 未触及的角度（第二百六十批，probe 实证）。

新角度：
- 盘符相对路径 "C:foo.pdf"：不算绝对（无 / 或 \\ 跟随
  盘符）→ pathlib 吸收盘符 → 解析为 proj/foo.pdf，
  在根内放行（现状锁定）
- expectations 无防御性拷贝：entry.expectations 与清单
  payload 中同一对象（身份保持）
- manifest_version 字段透传 "1.0"
- pdf↔docx 互配（canonical 方向）→ 1 组 +
  pdf_count/docx_count 各 1
- forbidden tokens 第三百五十五批
"""

from __future__ import annotations

import inspect
import json

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


def _load(tmp_path, docs, efs=()):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.docx").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": list(efs)}), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", st="pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": st}
    d.update(over)
    return d


# ---------- 盘符相对路径 ----------

def test_drive_relative_path_absorbed_batch83(tmp_path):
    m = _load(tmp_path, [_d("d1", path="C:foo.pdf")])
    d = m.documents[0]
    assert d.path_str == "C:foo.pdf"
    assert d.resolved_path == \
        (tmp_path / "proj" / "foo.pdf").resolve()
    assert m.file_count == 1


# ---------- expectations 每次加载独立 ----------

def test_expectations_fresh_per_load_batch83(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf",
             "expectations": {"element_count_by_type":
                              {"paragraph": 1}}}]}),
        encoding="utf-8")
    m1 = load_manifest(f, root)
    m1.documents[0].expectations["zz"] = 1
    m2 = load_manifest(f, root)
    assert "zz" not in m2.documents[0].expectations
    assert m2.documents[0].expectations == {
        "element_count_by_type": {"paragraph": 1}}


# ---------- manifest_version 透传 ----------

def test_manifest_version_passthrough_batch83(tmp_path):
    m = _load(tmp_path, [_d("d1")])
    assert m.manifest_version == "1.0"
    assert m.devset_status == "incomplete"


# ---------- pdf↔docx 互配 ----------

def test_pdf_docx_pairing_one_group_batch83(tmp_path):
    m = _load(tmp_path, [
        _d("d1", "samples/a.pdf", "pdf", paired_with="d2"),
        _d("d2", "samples/b.docx", "docx")])
    assert m.content_group_count == 1
    assert m.pdf_count == 1
    assert m.docx_count == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch83():
    src = _src()
    assert "if len(path_str) >= 3 and path_str[1] == \":\" and path_str[0].isalpha():" in src
    assert "expectations=d.get(\"expectations\")," in src
    assert "return groups + unpaired" in src


# ---------- forbidden tokens 第三百五十五批 ----------

def test_source_no_eval_batch83():
    assert "eval(" not in _src()


def test_source_no_exec_batch83():
    assert "exec(" not in _src()


def test_source_no_compile_batch83():
    assert "compile(" not in _src()


def test_source_no_globals_batch83():
    assert "globals(" not in _src()


def test_source_no_locals_batch83():
    assert "locals(" not in _src()


def test_source_no_os_system_batch83():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch83():
    assert "subprocess" not in _src()


def test_source_no_popen_batch83():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch83():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch83():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch83():
    assert "socket" not in _src()


def test_source_no_requests_batch83():
    assert "requests" not in _src()


def test_source_no_urllib_batch83():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch83():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch83():
    assert "yield" not in _src()


def test_source_no_async_await_batch83():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch83():
    assert _src().count("open(") == 1
