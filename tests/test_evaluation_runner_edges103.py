"""evaluation/runner.py 第三百零三轮 edges 测试（Round 859）。

补强 edges102 未触及的角度（第二百三十四批）。

新角度：
- aggregate_summary 收到的内部行带 _annotation_present /
  _tolerance_chars / _missing_markers（公开 per_doc 已剥离）
- _tolerance_chars 两种情况都记录值（有无标注都是 7）
- marker 缺失 → _missing_markers ["ZZZ"]（需 ≥2 chunk 才走到
  定位逻辑；1 chunk 走 no_predicted_boundaries 早退）
- expected_failures matches True / False / actual None 三态
- ef 条目四键有序
- ensure_ascii=False：CJK doc_id 落盘为字面字符
- forbidden tokens 第三百二十九批
"""

from __future__ import annotations

import inspect
import json
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
    "chunks": [{"text": "AB", "source_element_ids": ["e1"]},
               {"text": "CD", "source_element_ids": ["e1"]}],
}


def _mk(tmp_path, docs, efs=(), ann=None):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    if ann is not None:
        (root / "ann.json").write_text(json.dumps(ann),
                                       encoding="utf-8")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs, "expected_failures": list(efs)}),
        encoding="utf-8")
    return load_manifest(f, root)


# ---------- 内部行字段 ----------

def test_internal_rows_captured_to_aggregation_batch57(tmp_path):
    m = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf", "annotation_file": "ann.json"},
        {"doc_id": "d2", "path": "samples/a.pdf",
         "source_type": "pdf"}],
        ann={"chunk_boundary_anchors": [
            {"marker": "ZZZ", "position": "before"}]})
    captured = {}

    def fake_agg(rows):
        captured["rows"] = rows
        return {"sentinel": 1}

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=fake_agg):
        report = run_evaluation(
            m, tmp_path / "out" / "r.json", tolerance_chars=7)

    rows = captured["rows"]
    r1, r2 = rows
    assert r1["_annotation_present"] is True
    assert r1["_tolerance_chars"] == 7
    assert r1["_missing_markers"] == ["ZZZ"]
    assert r2["_annotation_present"] is False
    assert r2["_tolerance_chars"] == 7
    assert r2["_missing_markers"] == []

    assert report["summary"] == {"sentinel": 1}
    assert list(report["per_doc"][0]) == [
        "doc_id", "source_type", "metrics",
        "wall_time_seconds"]


# ---------- expected_failures 三态 ----------

def test_ef_matches_true_false_and_null_actual_batch57(tmp_path):
    m = _mk(tmp_path,
            [{"doc_id": "d1", "path": "samples/a.pdf",
              "source_type": "pdf"}],
            efs=[
                {"doc_id": "f1", "path": "samples/a.pdf",
                 "expected_error_code": "E_X"},
                {"doc_id": "f2", "path": "samples/a.pdf",
                 "expected_error_code": "E_Y"},
                {"doc_id": "f3", "path": "samples/a.pdf",
                 "expected_error_code": "E_W"}])
    seq = [
        (_FakeDoc(_DOC_DICT), []),   # d1 正常
        (None, [_Err("E_X")]),       # f1 命中
        (None, [_Err("E_Z")]),       # f2 错码
        (_FakeDoc(_DOC_DICT), []),   # f3 无错
    ]
    it = iter(seq)

    def fake_ps(*a, **k):
        return next(it)

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        report = run_evaluation(m, tmp_path / "r.json")

    ef = report["expected_failures"]
    assert ef[0] == {"doc_id": "f1",
                     "expected_error_code": "E_X",
                     "actual_error_code": "E_X",
                     "matches": True}
    assert ef[1]["actual_error_code"] == "E_Z"
    assert ef[1]["matches"] is False
    assert ef[2]["actual_error_code"] is None
    assert ef[2]["matches"] is False
    assert list(ef[0]) == ["doc_id", "expected_error_code",
                           "actual_error_code", "matches"]


# ---------- ensure_ascii=False ----------

def test_cjk_doc_id_written_literal_batch57(tmp_path):
    m = _mk(tmp_path, [
        {"doc_id": "中文d1", "path": "samples/a.pdf",
         "source_type": "pdf"}])
    out = tmp_path / "r.json"
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, out)
    raw = out.read_text(encoding="utf-8")
    assert "中文d1" in raw
    assert "\\u4e2d" not in raw
    assert json.loads(raw)["per_doc"][0]["doc_id"] == "中文d1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch57():
    src = _src()
    assert "image_dir if (image_dir is not None and image_dir.is_dir()) else None" in src
    assert "actual_code = errors[0].code if errors else None" in src
    assert '"matches": actual_code == ef.expected_error_code' in src


# ---------- forbidden tokens 第三百二十九批 ----------

def test_source_no_eval_batch57():
    assert "eval(" not in _src()


def test_source_no_exec_batch57():
    assert "exec(" not in _src()


def test_source_no_compile_batch57():
    assert "compile(" not in _src()


def test_source_no_globals_batch57():
    assert "globals(" not in _src()


def test_source_no_locals_batch57():
    assert "locals(" not in _src()


def test_source_no_os_system_batch57():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch57():
    assert "subprocess" not in _src()


def test_source_no_popen_batch57():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch57():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch57():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch57():
    assert "socket" not in _src()


def test_source_no_requests_batch57():
    assert "requests" not in _src()


def test_source_no_urllib_batch57():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch57():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch57():
    assert "yield" not in _src()


def test_source_no_async_await_batch57():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch57():
    assert _src().count("open(") == 2
