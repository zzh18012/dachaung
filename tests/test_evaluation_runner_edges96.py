"""evaluation/runner.py 第二百五十四轮 edges 测试（Round 810）。

补强 edges95 未触及的角度（第一百七十四批）。

新角度：
- parser_version 首个非空优先：d1 "1.0" + d2 "2.0" → "1.0"；
  d1 None + d2 "2.0" → "2.0"（`if parser_version and not
  parser_version_for_prov` 的两侧行为）
- process_single 返回 (None, [])：无 errors 兜底 error code
  "unknown" + 下游 metrics pipeline_failed
- 损坏 annotation JSON：_load_annotation 吞 JSONDecodeError →
  None → chunk_boundary_f1 no_annotation +
  _annotation_present False（图 caption 仍
  parser_does_not_emit_relations）
- 落盘 per_doc 仅 4 个公开键（_tolerance_chars /
  _missing_markers / _annotation_present 不外泄）
- 落盘内容与返回 report 全等（json 往返 round-trip）
- expected_failures 空清单：报告仍带键、值为 []
- forbidden tokens 第二百八十批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    def __init__(self, pv="1.0"):
        self.parser_version = pv
        self.source_hash = "h"

    def to_dict(self):
        return {"elements": [
            {"element_id": "e1", "type": "paragraph",
             "content": "A"},
            {"element_id": "e2", "type": "paragraph",
             "content": "B"}],
            "chunks": [
                {"text": "A", "source_element_ids": ["e1"]},
                {"text": "B", "source_element_ids": ["e2"]}]}


prov_cap: dict = {}


def _prov(**k):
    prov_cap.clear()
    prov_cap.update(k)
    return {"git_commit": "c", "git_dirty": False}


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _de(root, did, ann=None):
    return DocumentEntry(did, "samples/a.pdf",
                         root / "samples/a.pdf", "pdf",
                         None, (), None, ann, None, None)


def _run(tmp, root, entries, rets):
    calls = iter(rets)

    def fake_ps(path, out, **kw):
        return next(calls)

    with patch.object(runner_mod, "process_single", fake_ps), \
            patch.object(runner_mod, "build_provenance", _prov):
        return run_evaluation(
            Manifest("1.0", "incomplete", entries, (), root),
            tmp / "r.json")


# ---------- parser_version 首个非空优先 ----------

def test_parser_version_first_nonnull_wins_batch55():
    tmp, root = _env()
    _run(tmp, root, (_de(root, "d1"), _de(root, "d2")),
         [(_FakeDoc("1.0"), []), (_FakeDoc("2.0"), [])])
    assert prov_cap["parser_version"] == "1.0"


def test_parser_version_null_first_later_used_batch55():
    tmp, root = _env()
    _run(tmp, root, (_de(root, "d1"), _de(root, "d2")),
         [(_FakeDoc(None), []), (_FakeDoc("2.0"), [])])
    assert prov_cap["parser_version"] == "2.0"


# ---------- document None 无 errors ----------

def test_document_none_without_errors_unknown_code_batch55():
    tmp, root = _env()
    rep = _run(tmp, root, (_de(root, "d1"),), [(None, [])])
    m = rep["per_doc"][0]["metrics"]
    assert m["error_code"] == {"value": "unknown", "reason": None}
    assert m["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- 损坏 annotation ----------

def test_bad_json_annotation_treated_missing_batch55():
    tmp, root = _env()
    ann = tmp / "ann.json"
    ann.write_text("{bad json", encoding="utf-8")
    rep = _run(tmp, root, (_de(root, "d1", ann),),
               [(_FakeDoc(), [])])
    m = rep["per_doc"][0]["metrics"]
    assert m["chunk_boundary_f1"] == {"value": None,
                                      "reason": "no_annotation"}
    assert m["figure_caption_f1"] == {
        "value": None,
        "reason": "parser_does_not_emit_relations"}


# ---------- 落盘公开键 ----------

def test_disk_per_doc_only_public_keys_batch55():
    tmp, root = _env()
    rep = _run(tmp, root, (_de(root, "d1"),), [(_FakeDoc(), [])])
    disk = json.loads((tmp / "r.json").read_text(encoding="utf-8"))
    assert list(disk["per_doc"][0].keys()) == [
        "doc_id", "source_type", "metrics", "wall_time_seconds"]
    assert "_tolerance_chars" not in disk["per_doc"][0]
    assert "_missing_markers" not in disk["per_doc"][0]


# ---------- round-trip 全等 ----------

def test_disk_equals_returned_report_batch55():
    tmp, root = _env()
    rep = _run(tmp, root, (_de(root, "d1"),), [(_FakeDoc(), [])])
    disk = json.loads((tmp / "r.json").read_text(encoding="utf-8"))
    assert disk == rep


# ---------- expected_failures 空清单 ----------

def test_expected_failures_key_present_empty_batch55():
    tmp, root = _env()
    rep = _run(tmp, root, (_de(root, "d1"),), [(_FakeDoc(), [])])
    assert rep["expected_failures"] == []
    disk = json.loads((tmp / "r.json").read_text(encoding="utf-8"))
    assert "expected_failures" in disk


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert ("if parser_version and not parser_version_for_prov:"
            in src)
    assert ('{"code": "unknown", "message": '
            '"process_single returned None without errors"}') in src
    assert "except (OSError, json.JSONDecodeError):" in src


# ---------- forbidden tokens 第二百八十批 ----------

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
