"""evaluation/runner.py 第三百八十七轮 edges 测试（Round 943）。

补强 edges114 未触及的角度（第三百一十九批，probe 实证）。

新角度：
- _process_one 直测 (None, [])：五元组 (None, {code:
  "unknown", message: "process_single returned None
  without errors"}, elapsed≥0, None, None)
- _process_one 直测成功：doc.to_dict()、err None、
  parser_version 透传、image_dir ==
  image_output_dir_for(out_stub, source_hash)（目录
  本身不创建）
- image_base_dir 门控：spy compute_automatic_metrics 的
  kwarg——image 目录不存在 → None；目录建好 → 传该目录
- ef 结果用 .code 属性而非 .to_dict()：伪造 code
  "E_PARSE" / to_dict code "OTHER" 的 error 对象 →
  actual_error_code "E_PARSE"、与期望 "E" → matches
  False；空 documents + 1 ef → process_single 恰调 1 次
- forbidden tokens 第四百一十三批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from app.pipeline import image_output_dir_for
from evaluation.manifest import load_manifest
from evaluation.runner import _process_one, run_evaluation


class _Entry:
    doc_id = "d1"
    source_type = "pdf"
    expectations = None
    annotation_resolved = None

    def __init__(self, tmp_path):
        self.resolved_path = tmp_path / "samples" / "a.pdf"


class _FakeDoc:
    parser_version = "7.7"
    source_hash = "deadbeef"

    def to_dict(self):
        return {"elements": [], "chunks": []}


class _Err:
    code = "E_PARSE"

    def to_dict(self):
        return {"code": "OTHER", "message": "m"}


def _mk_manifest(tmp_path, docs, efs=None):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    data = {"manifest_version": "1.0",
            "devset_status": "incomplete", "documents": docs}
    if efs is not None:
        data["expected_failures"] = efs
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return load_manifest(f, tmp_path)


# ---------- _process_one (None, []) ----------

def test_process_one_none_no_errors_batch141(tmp_path):
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [])):
        doc, err, elapsed, pv, idir = _process_one(
            _Entry(tmp_path), tmp_path, "fallback", 800)
    assert doc is None
    assert err["code"] == "unknown"
    assert err["message"] == \
        "process_single returned None without errors"
    assert elapsed >= 0
    assert pv is None and idir is None


# ---------- _process_one 成功 ----------

def test_process_one_success_tuple_batch141(tmp_path):
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])):
        doc, err, elapsed, pv, idir = _process_one(
            _Entry(tmp_path), tmp_path, "fallback", 800)
    assert doc == {"elements": [], "chunks": []}
    assert err is None
    assert pv == "7.7"
    stub = tmp_path / "_per_doc" / "d1.json"
    assert idir == image_output_dir_for(stub, "deadbeef")
    assert not idir.exists()


# ---------- image_base_dir 门控 ----------

def test_image_base_dir_gating_batch141(tmp_path):
    m = _mk_manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}])
    captured = {}
    orig = runner_mod.compute_automatic_metrics

    def spy(**kw):
        captured["base"] = kw.get("image_base_dir")
        return orig(**kw)

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "compute_automatic_metrics",
                      side_effect=spy):
        run_evaluation(m, tmp_path / "r.json")
    assert captured["base"] is None
    stub = tmp_path / "_per_doc" / "d1.json"
    idir = image_output_dir_for(stub, "deadbeef")
    idir.mkdir(parents=True)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "compute_automatic_metrics",
                      side_effect=spy):
        run_evaluation(m, tmp_path / "r2.json")
    assert captured["base"] == idir


# ---------- ef .code 属性路径 ----------

def test_ef_uses_code_attribute_batch141(tmp_path):
    m = _mk_manifest(tmp_path, [], efs=[{
        "doc_id": "f1", "path": "samples/ghost.pdf",
        "expected_error_code": "E"}])
    calls = []

    def ps(path, out, parser_name="fallback", max_chars=800,
           write_json=False):
        calls.append(path.name)
        return None, [_Err()]

    with patch.object(runner_mod, "process_single",
                      side_effect=ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    # .code 属性（E_PARSE）而非 to_dict 的 OTHER
    assert rep["expected_failures"] == [{
        "doc_id": "f1", "expected_error_code": "E",
        "actual_error_code": "E_PARSE", "matches": False}]
    assert calls == ["ghost.pdf"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch141():
    src = _src()
    assert 'image_dir = image_output_dir_for(out_stub, document.source_hash)' in src
    assert '{"code": "unknown", "message": "process_single returned None without errors"},' in src
    assert "actual_code = errors[0].code if errors else None" in src
    assert 'image_dir if (image_dir is not None and image_dir.is_dir()) else None,' in src


# ---------- forbidden tokens 第四百一十三批 ----------

def test_source_no_eval_batch141():
    assert "eval(" not in _src()


def test_source_no_exec_batch141():
    assert "exec(" not in _src()


def test_source_no_compile_batch141():
    assert "compile(" not in _src()


def test_source_no_globals_batch141():
    assert "globals(" not in _src()


def test_source_no_locals_batch141():
    assert "locals(" not in _src()


def test_source_no_os_system_batch141():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch141():
    assert "subprocess" not in _src()


def test_source_no_popen_batch141():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch141():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch141():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch141():
    assert "socket" not in _src()


def test_source_no_requests_batch141():
    assert "requests" not in _src()


def test_source_no_urllib_batch141():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch141():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch141():
    assert "yield" not in _src()


def test_source_no_async_await_batch141():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch141():
    assert _src().count("open(") == 2
