"""evaluation/runner.py 第三百五十九轮 edges 测试（Round 915）。

补强 edges110 未触及的角度（第二百九十一批，probe 实证）。

新角度：
- provenance parser_version 先到先得：两 doc "1.1"/"2.2" → "1.1"；
  首 doc 失败（None）次 doc "2.2" → "2.2"（None 被跳过）
- expected_failures：process_single 返回 (None, []) →
  actual_error_code None、matches False（期望 E）
- ef 循环也走 out_stub 落盘后 unlink：跑完 stub 消失但
  _per_doc 目录留存
- 报告落盘 JSON 与返回 dict 完全相等（roundtrip）
- _load_annotation 指向目录 → None（is_file False）；
  显式传 None → None
- forbidden tokens 第三百八十五批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import _load_annotation, run_evaluation


class _FakeDoc:
    def __init__(self, pv):
        self.parser_version = pv
        self.source_hash = "deadbeef"
        self._d = {
            "elements": [{"element_id": "e1", "type": "paragraph",
                          "content": "AB"}],
            "chunks": [{"text": "AB",
                        "source_element_ids": ["e1"]}],
        }

    def to_dict(self):
        return self._d


class _Err:
    def to_dict(self):
        return {"code": "E", "message": "x"}


def _mk(tmp_path, docs, efs=None):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    d = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": docs}
    if efs is not None:
        d["expected_failures"] = efs
    f = tmp_path / "m.json"
    f.write_text(json.dumps(d), encoding="utf-8")
    return load_manifest(f, root)


_D1 = {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf"}
_D2 = {"doc_id": "d2", "path": "samples/b.pdf", "source_type": "pdf"}


# ---------- parser_version 先到先得 ----------

def test_parser_version_first_wins_batch113(tmp_path):
    m = _mk(tmp_path, [_D1, _D2])
    cap = {}

    def fake_bp(**kw):
        cap.update(kw)
        return {}

    with patch.object(runner_mod, "process_single",
                      side_effect=[(_FakeDoc("1.1"), []),
                                   (_FakeDoc("2.2"), [])]), \
         patch.object(runner_mod, "build_provenance",
                      side_effect=fake_bp):
        run_evaluation(m, tmp_path / "r.json")
    assert cap["parser_version"] == "1.1"


def test_parser_version_none_skipped_batch113(tmp_path):
    m = _mk(tmp_path, [_D1, _D2])
    cap = {}

    def fake_bp(**kw):
        cap.update(kw)
        return {}

    with patch.object(runner_mod, "process_single",
                      side_effect=[(None, [_Err()]),
                                   (_FakeDoc("2.2"), [])]), \
         patch.object(runner_mod, "build_provenance",
                      side_effect=fake_bp):
        run_evaluation(m, tmp_path / "r.json")
    assert cap["parser_version"] == "2.2"


# ---------- expected_failures ----------

def test_ef_none_no_errors_mismatch_batch113(tmp_path):
    m = _mk(tmp_path, [_D1], efs=[{
        "doc_id": "f1", "path": "samples/a.pdf",
        "expected_error_code": "E"}])

    def fake_ps(path, out_path, **kw):
        Path(out_path).write_text("stub", encoding="utf-8")
        return None, []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    assert rep["expected_failures"] == [{
        "doc_id": "f1", "expected_error_code": "E",
        "actual_error_code": None, "matches": False}]
    assert not (tmp_path / "_per_doc" / "f1.json").exists()
    assert (tmp_path / "_per_doc").is_dir()


# ---------- 报告落盘 roundtrip ----------

def test_report_disk_roundtrip_equal_batch113(tmp_path):
    m = _mk(tmp_path, [_D1])
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc("1.1"), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    on_disk = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert on_disk == rep


# ---------- _load_annotation 目录/None ----------

def test_load_annotation_directory_none_batch113(tmp_path):
    d = tmp_path / "ann_dir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_explicit_none_batch113():
    assert _load_annotation(None) is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch113():
    src = _src()
    assert "if parser_version and not parser_version_for_prov:" in src
    assert '"matches": actual_code == ef.expected_error_code,' in src
    assert "out_stub.unlink()" in src
    assert src.count("write_json=False") == 4  # 2 次调用 + 2 处 docstring


# ---------- forbidden tokens 第三百八十五批 ----------

def test_source_no_eval_batch113():
    assert "eval(" not in _src()


def test_source_no_exec_batch113():
    assert "exec(" not in _src()


def test_source_no_compile_batch113():
    assert "compile(" not in _src()


def test_source_no_globals_batch113():
    assert "globals(" not in _src()


def test_source_no_locals_batch113():
    assert "locals(" not in _src()


def test_source_no_os_system_batch113():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch113():
    assert "subprocess" not in _src()


def test_source_no_popen_batch113():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch113():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch113():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch113():
    assert "socket" not in _src()


def test_source_no_requests_batch113():
    assert "requests" not in _src()


def test_source_no_urllib_batch113():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch113():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch113():
    assert "yield" not in _src()


def test_source_no_async_await_batch113():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch113():
    assert _src().count("open(") == 2
