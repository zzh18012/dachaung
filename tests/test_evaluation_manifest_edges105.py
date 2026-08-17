"""evaluation/manifest.py 第三百一十五轮 edges 测试（Round 871）。

补强 edges104 未触及的角度（第二百四十六批）。

新角度：
- 悬空混合配对：d1→d2 + d3→ghost → 两组 frozenset
  均计数，无 unpaired
- annotation_file dot-dot 逃根 → 报错带 annotation_file
  字段名
- 重复 doc_id（d1 两份）：schema 不查重，loader 照单全收
- path "samples/../samples/a.pdf" 归一后仍在根内
- sha256 合法 64-hex 透传
- expected_failures 不计入 file_count / pdf_count
- forbidden tokens 第三百四十一批
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import ManifestError, load_manifest


def _load(tmp_path, docs, efs=()):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    (root / "samples" / "c.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": list(efs)}), encoding="utf-8")
    return load_manifest(f, root)


def _d(did, path="samples/a.pdf", **over):
    d = {"doc_id": did, "path": path, "source_type": "pdf"}
    d.update(over)
    return d


# ---------- 悬空混合配对 ----------

def test_dangling_mixed_pairing_two_groups_batch69(tmp_path):
    m = _load(tmp_path, [
        _d("d1", paired_with="d2"),
        _d("d2", "samples/b.pdf"),
        _d("d3", "samples/c.pdf", paired_with="ghost")])
    assert m.content_group_count == 2
    assert m.file_count == 3


# ---------- annotation 逃根 ----------

def test_annotation_dotdot_escape_batch62(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _load(tmp_path, [
            _d("d1", annotation_file="../outside.json")])
    assert "annotation_file" in str(ei.value)
    assert "位于项目根目录之外" in str(ei.value)


# ---------- 重复 doc_id ----------

def test_duplicate_doc_id_accepted_batch69(tmp_path):
    m = _load(tmp_path, [_d("d1"), _d("d1", "samples/b.pdf")])
    assert m.file_count == 2
    assert [d.path_str for d in m.documents] == [
        "samples/a.pdf", "samples/b.pdf"]


# ---------- 内部 dot-dot 归一 ----------

def test_internal_dotdot_normalized_batch69(tmp_path):
    m = _load(tmp_path, [
        _d("d1", "samples/../samples/a.pdf")])
    d = m.documents[0]
    assert d.path_str == "samples/../samples/a.pdf"
    assert d.resolved_path == \
        (tmp_path / "proj" / "samples" / "a.pdf").resolve()


# ---------- sha256 透传 ----------

def test_sha256_hex_passthrough_batch69(tmp_path):
    h = "a" * 64
    m = _load(tmp_path, [_d("d1", sha256=h)])
    assert m.documents[0].sha256 == h


# ---------- ef 不计入 counts ----------

def test_ef_not_counted_in_file_counts_batch69(tmp_path):
    m = _load(tmp_path, [_d("d1")],
              efs=[{"doc_id": "f1", "path": "samples/b.pdf",
                    "expected_error_code": "E",
                    "source_type": "pdf"}])
    assert m.file_count == 1
    assert m.pdf_count == 1
    assert len(m.expected_failures) == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch69():
    src = _src()
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src
    assert "if d.doc_id not in seen and not d.paired_with:" in src
    assert "sha256=d.get(\"sha256\")" in src


# ---------- forbidden tokens 第三百四十一批 ----------

def test_source_no_eval_batch69():
    assert "eval(" not in _src()


def test_source_no_exec_batch69():
    assert "exec(" not in _src()


def test_source_no_compile_batch69():
    assert "compile(" not in _src()


def test_source_no_globals_batch69():
    assert "globals(" not in _src()


def test_source_no_locals_batch69():
    assert "locals(" not in _src()


def test_source_no_os_system_batch69():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch69():
    assert "subprocess" not in _src()


def test_source_no_popen_batch69():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch69():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch69():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch69():
    assert "socket" not in _src()


def test_source_no_requests_batch69():
    assert "requests" not in _src()


def test_source_no_urllib_batch69():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch69():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch69():
    assert "yield" not in _src()


def test_source_no_async_await_batch69():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch69():
    assert _src().count("open(") == 1
