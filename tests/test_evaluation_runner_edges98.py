"""evaluation/runner.py 第二百六十八轮 edges 测试（Round 824）。

补强 edges97 未触及的角度（第一百九十五批）。

新角度：
- 文档路径 process_single 调用约定：位置参数
  (resolved_path, out_stub=_per_doc/d1.json) + 关键字
  parser_name/max_chars/write_json=False 全透传
- image_output_dir_for 调用约定：(out_stub, source_hash)
  两个位置参数（doc_id 存根名 + 真实哈希）
- wall_time_seconds.total 恒为 float（perf_counter 差值）
- 双文档跑完 _per_doc 目录存在且**空**（两个 stub 均被清理）
- forbidden tokens 第二百九十四批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "1.0"
    source_hash = "abc123"

    def to_dict(self):
        return {"elements": [
            {"element_id": "e1", "type": "paragraph",
             "content": "A"}],
            "chunks": [
                {"text": "A", "source_element_ids": ["e1"]}]}


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _de(root, did):
    return DocumentEntry(did, "samples/a.pdf",
                         root / "samples/a.pdf", "pdf",
                         None, (), None, None, None, None)


# ---------- 文档路径调用约定 ----------

def test_document_call_convention_batch55():
    tmp, root = _env()
    caps = []

    def fake_ps(path, out, **kw):
        caps.append((path, out, kw))
        return _FakeDoc(), []

    with patch.object(runner_mod, "process_single", fake_ps), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: {"git_commit": "c",
                                      "git_dirty": False}):
        run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d1"),),
                     (), root), tmp / "r.json", max_chars=555,
            parser_name="kreuzberg")
    path, out, kw = caps[0]
    assert path == root / "samples" / "a.pdf"
    assert out == tmp / "_per_doc" / "d1.json"
    assert kw == {"parser_name": "kreuzberg",
                  "max_chars": 555, "write_json": False}


# ---------- image_output_dir_for 约定 ----------

def test_image_dir_call_convention_batch55():
    tmp, root = _env()
    caps = []

    def fake_iodf(stub, sh):
        caps.append((stub, sh))
        return Path(tempfile.mkdtemp())

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "image_output_dir_for",
                         fake_iodf), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: {"git_commit": "c",
                                      "git_dirty": False}):
        run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d1"),),
                     (), root), tmp / "r.json")
    assert caps[0][0] == tmp / "_per_doc" / "d1.json"
    assert caps[0][1] == "abc123"


# ---------- total 恒 float ----------

def test_total_is_float_batch55():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: {"git_commit": "c",
                                      "git_dirty": False}):
        rep = run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d1"),),
                     (), root), tmp / "r.json")
    total = rep["per_doc"][0]["wall_time_seconds"]["total"]
    assert isinstance(total, float)
    assert total >= 0


# ---------- 双文档 _per_doc 清空 ----------

def test_per_doc_dir_empty_after_run_batch55():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: {"git_commit": "c",
                                      "git_dirty": False}):
        run_evaluation(
            Manifest("1.0", "incomplete",
                     (_de(root, "d1"), _de(root, "d2")), (),
                     root), tmp / "r.json")
    pd = tmp / "_per_doc"
    assert pd.is_dir()
    assert list(pd.iterdir()) == []


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "image_dir = image_output_dir_for(out_stub, document.source_hash)" in src
    assert "elapsed = time.perf_counter() - t0" in src
    assert 'out_stub.parent.mkdir(parents=True, exist_ok=True)' in src


# ---------- forbidden tokens 第二百九十四批 ----------

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


def test_source_open_count_is_2_batch55():
    assert _src().count("open(") == 2
