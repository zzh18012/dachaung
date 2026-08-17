"""evaluation/runner.py 第三百三十一轮 edges 测试（Round 887）。

补强 edges106 未触及的角度（第二百六十二批）。

新角度：
- parser_name "kreuzberg" 透传到 process_single kwargs
- fake 内 sleep 0.01 → wall_time total 严格 > 0.005
- 全失败清单：_per_doc 目录仍被创建
- 成功 + 无标注：per_doc metrics 恰 20 键
  （14 自动 + 3 figure + 3 chunk_boundary，
  _tolerance_chars/_missing_markers 已弹出）
- process_single 调用顺序：先常规文档后 ef
  （按 out_stub 文件名序锁定）
- forbidden tokens 第三百五十七批
"""

from __future__ import annotations

import inspect
import json
import time
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    def __init__(self, d):
        self._d = d
        self.parser_version = "7.7"
        self.source_hash = "deadbeef"

    def to_dict(self):
        return self._d


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


_DOC_DICT = {
    "elements": [{"element_id": "e1", "type": "paragraph",
                  "content": "AB"}],
    "chunks": [{"text": "AB", "source_element_ids": ["e1"]}],
}


def _mk(tmp_path, docs, efs=()):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs, "expected_failures": list(efs)}),
        encoding="utf-8")
    return load_manifest(f, root)


# ---------- kreuzberg 透传 ----------

def test_parser_name_kreuzberg_passthrough_batch85(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    captured = {}

    def fake_ps(path, out_path, **kwargs):
        captured.update(kwargs)
        return _FakeDoc(_DOC_DICT), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, tmp_path / "r.json",
                       parser_name="kreuzberg", max_chars=500)
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 500
    assert captured["write_json"] is False


# ---------- 严格正时长 ----------

def test_wall_time_strictly_positive_batch85(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])

    def fake_ps(path, out_path, **kwargs):
        time.sleep(0.02)
        return _FakeDoc(_DOC_DICT), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        report = run_evaluation(m, tmp_path / "r.json")
    assert report["per_doc"][0]["wall_time_seconds"][
        "total"] > 0.005


# ---------- 全失败仍建目录 ----------

def test_all_failed_still_creates_per_doc_dir_batch85(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [_Err("E_X")])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, tmp_path / "r.json")
    assert (tmp_path / "_per_doc").is_dir()


# ---------- metrics 恰 20 键 ----------

def test_per_doc_metrics_twenty_keys_batch85(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        report = run_evaluation(m, tmp_path / "r.json")
    metrics = report["per_doc"][0]["metrics"]
    assert len(metrics) == 20
    assert "_tolerance_chars" not in metrics
    assert "_missing_markers" not in metrics
    assert "figure_caption_f1" in metrics
    assert "chunk_boundary_f1" in metrics
    assert report["summary"]["success_rates"][
        "pipeline_success"]["rate"] == 1.0


# ---------- 调用顺序 ----------

def test_process_order_docs_then_ef_batch85(tmp_path):
    m = _mk(tmp_path,
            [{"doc_id": "d1", "path": "samples/a.pdf",
              "source_type": "pdf"}],
            efs=[{"doc_id": "f1", "path": "samples/b.pdf",
                  "expected_error_code": "E"}])
    order = []

    def fake_ps(path, out_path, **kwargs):
        order.append(out_path.stem)
        return _FakeDoc(_DOC_DICT), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, tmp_path / "r.json")
    assert order == ["d1", "f1"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch85():
    src = _src()
    assert "parser_name=parser_name," in src
    assert "write_json=False," in src
    assert "public_per_doc = []" in src


# ---------- forbidden tokens 第三百五十七批 ----------

def test_source_no_eval_batch85():
    assert "eval(" not in _src()


def test_source_no_exec_batch85():
    assert "exec(" not in _src()


def test_source_no_compile_batch85():
    assert "compile(" not in _src()


def test_source_no_globals_batch85():
    assert "globals(" not in _src()


def test_source_no_locals_batch85():
    assert "locals(" not in _src()


def test_source_no_os_system_batch85():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch85():
    assert "subprocess" not in _src()


def test_source_no_popen_batch85():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch85():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch85():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch85():
    assert "socket" not in _src()


def test_source_no_requests_batch85():
    assert "requests" not in _src()


def test_source_no_urllib_batch85():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch85():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch85():
    assert "yield" not in _src()


def test_source_no_async_await_batch85():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch85():
    assert _src().count("open(") == 2
