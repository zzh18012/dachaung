"""evaluation/manifest.py 第五百五十九轮 edges 测试（Round 1115）。

补强 edges138 未触及的角度（第四百九十一批，probe 实证）。

新角度（目录当 annotation / 目录当 ef 路径 / 共享标注）：
- **annotation_file 是目录**：annotation_file "anns"（真实
  目录）→ 照常加载且 annotation_resolved.is_dir()——形式
  校验只查路径形式不查类型（doc path 目录已锁，annotation
  通道目录首锁；runner 侧 is_file 检查会静默降级
  no_annotation）
- **ef path 是目录**：expected_failures path "anns" →
  照常加载 ef.resolved_path.is_dir()（ef 幽灵文件已锁，
  目录变体首锁）
- **两文档共享一个 annotation_file**：d1/d2 都挂
  anns/shared.json → 两 annotation_resolved 完全相等——
  loader 不查 annotation 归属（doc_id 不匹配也不管，
  同一标注可复用到任意多文档）
- forbidden tokens 第五百八十七批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest


def _write(tmp_path, docs, efs=None):
    (tmp_path / "anns").mkdir(exist_ok=True)
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": efs or []}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- annotation_file 是目录 ----------

def test_annotation_file_directory_accepted_batch314(tmp_path):
    m = _write(tmp_path, [{
        "doc_id": "d1", "path": "samples/a.pdf",
        "source_type": "pdf",
        "annotation_file": "anns"}])
    assert m.documents[0].annotation_resolved.is_dir()
    assert m.documents[0].annotation_file_str == "anns"


# ---------- ef path 是目录 ----------

def test_ef_path_directory_accepted_batch314(tmp_path):
    m = _write(
        tmp_path, [],
        [{"doc_id": "f1", "path": "anns",
          "expected_error_code": "file_not_found"}])
    assert m.expected_failures[0].resolved_path.is_dir()


# ---------- 两文档共享一个 annotation_file ----------

def test_shared_annotation_file_batch314(tmp_path):
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "anns" / "shared.json").write_text(
        json.dumps({
            "annotation_version": "1.0", "doc_id": "d1",
            "chunk_boundary_anchors": []}),
        encoding="utf-8")
    m = _write(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf",
         "annotation_file": "anns/shared.json"},
        {"doc_id": "d2", "path": "samples/b.pdf",
         "source_type": "pdf",
         "annotation_file": "anns/shared.json"}])
    assert (m.documents[0].annotation_resolved ==
            m.documents[1].annotation_resolved)
    assert m.file_count == 2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch314():
    src = _src()
    assert "配对的 DOCX+PDF" in src
    assert "resolved_path: Path  # 解析后的绝对路径" in src


# ---------- forbidden tokens 第五百八十七批 ----------

def test_source_no_eval_batch314():
    assert "eval(" not in _src()


def test_source_no_exec_batch314():
    assert "exec(" not in _src()


def test_source_no_compile_batch314():
    assert "compile(" not in _src()


def test_source_no_globals_batch314():
    assert "globals(" not in _src()


def test_source_no_locals_batch314():
    assert "locals(" not in _src()


def test_source_no_os_system_batch314():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch314():
    assert "subprocess" not in _src()


def test_source_no_popen_batch314():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch314():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch314():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch314():
    assert "socket" not in _src()


def test_source_no_requests_batch314():
    assert "requests" not in _src()


def test_source_no_urllib_batch314():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch314():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch314():
    assert "yield" not in _src()


def test_source_no_async_await_batch314():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch314():
    assert _src().count("open(") == 1
