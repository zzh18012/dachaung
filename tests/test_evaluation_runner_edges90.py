"""evaluation/runner.py 第二百一十二轮 edges 测试（Round 768）。

补强 edges88-89 未触及的角度（第一百三十二批）。

新角度：
- _load_annotation 六态：None / 不存在 / 目录 / 非法 JSON / BOM /
  合法 → dict（BOM 走 JSONDecodeError 分支同样吞掉）
- _process_one 的 (None, []) 未守卫分支：errors 空但 document 也空
  → error {"code": "unknown", "message": "process_single returned
  None without errors"}，parser_version None、image_dir None
  （document None 时 image_dir 不推导）；_per_doc 目录仍创建
- 内部记录捕获（patch aggregate_summary 截获 per_doc_results）：
  annotation 在场 → _annotation_present True、_tolerance_chars 透传
  77、_missing_markers []；公共 per_doc 恰 4 键（私有键被剥）
- annotation 真实路径（不 patch chunk_boundary_prf）缺席时
  _tolerance_chars 仍记录默认 30、_annotation_present False
- figure_caption_prf 与 chunk_boundary_prf 收到同一 annotation 对象
  （is 同一性，不重新加载）
- 空 manifest：报告 6 键序固定、per_doc/expected_failures 双空、
  success rate None（success_count 0 total 0）、_per_doc 目录不创建
  （mkdir 在 _process_one 内，循环零次不触发）
- 输出文件与返回 dict 严格相等（json round-trip）
- forbidden tokens 第二百三十八批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.runner import _load_annotation, _process_one, run_evaluation


class _DE:
    doc_id = "d1"
    resolved_path = Path("samples") / "a.pdf"


class _FakeDoc:
    parser_version = "pv-9"
    source_hash = "deadbeef"

    def to_dict(self):
        return {"elements": [], "chunks": []}


# ---------- _load_annotation 六态 ----------

def test_load_annotation_none_batch54():
    assert _load_annotation(None) is None


def test_load_annotation_missing_and_dir_batch54():
    tmp = Path(tempfile.mkdtemp())
    d = tmp / "adir"
    d.mkdir()
    assert _load_annotation(tmp / "nope.json") is None
    assert _load_annotation(d) is None


def test_load_annotation_invalid_json_batch54():
    tmp = Path(tempfile.mkdtemp())
    f = tmp / "bad.json"
    f.write_text("{oops", encoding="utf-8")
    assert _load_annotation(f) is None


def test_load_annotation_bom_swallowed_batch54():
    tmp = Path(tempfile.mkdtemp())
    f = tmp / "bom.json"
    f.write_bytes(b"\xef\xbb\xbf{}")
    assert _load_annotation(f) is None


def test_load_annotation_valid_batch54():
    tmp = Path(tempfile.mkdtemp())
    f = tmp / "ok.json"
    f.write_text('{"k": 1}', encoding="utf-8")
    assert _load_annotation(f) == {"k": 1}


# ---------- _process_one unknown 分支 ----------

def test_process_one_none_none_unknown_batch54():
    tmp = Path(tempfile.mkdtemp())
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [])):
        doc, err, elapsed, pv, image_dir = _process_one(
            _DE(), tmp, "fallback", 800)
    assert doc is None
    assert err == {"code": "unknown",
                   "message": "process_single returned None without errors"}
    assert pv is None
    assert image_dir is None
    assert elapsed >= 0
    assert (tmp / "_per_doc").is_dir()


# ---------- 内部记录捕获 ----------

def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def test_internal_records_annotation_present_batch54():
    tmp, root = _env()
    ann = root / "ann.json"
    ann.write_text(json.dumps({"chunk_boundary_anchors": []}),
                   encoding="utf-8")
    de = DocumentEntry("d1", "samples/a.pdf", root / "samples/a.pdf",
                       "pdf", None, (), None, "samples/ann.json", ann, None)
    man = Manifest("1.0", "incomplete", (de,), (), root)
    caps = {}

    def fake_agg(per_doc):
        caps["internal"] = per_doc
        return {"counts": {}, "success_rates": {},
                "ratio_macro_averages": {}, "silent_drop_total": None}

    seen = []

    def fake_fig(doc, a):
        seen.append(a)
        return {}

    def fake_chunk(doc, a, tolerance_chars=30):
        seen.append(a)
        return {"_tolerance_chars": {"value": tolerance_chars},
                "_missing_markers": {"value": []}}

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "aggregate_summary", fake_agg), \
            patch.object(runner_mod, "figure_caption_prf", fake_fig), \
            patch.object(runner_mod, "chunk_boundary_prf", fake_chunk), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: {"git_commit": "c",
                                      "git_dirty": False}):
        rep = run_evaluation(man, tmp / "r.json", tolerance_chars=77)

    rec = caps["internal"][0]
    assert rec["_annotation_present"] is True
    assert rec["_tolerance_chars"] == 77
    assert rec["_missing_markers"] == []
    assert sorted(rep["per_doc"][0]) == ["doc_id", "metrics",
                                         "source_type",
                                         "wall_time_seconds"]
    assert seen[0] is seen[1]


def test_internal_records_annotation_absent_default_tol_batch54():
    tmp, root = _env()
    de = DocumentEntry("d1", "samples/a.pdf", root / "samples/a.pdf",
                       "pdf", None, (), None, None, None, None)
    man = Manifest("1.0", "incomplete", (de,), (), root)
    caps = {}

    def fake_agg(per_doc):
        caps["internal"] = per_doc
        return {"counts": {}, "success_rates": {},
                "ratio_macro_averages": {}, "silent_drop_total": None}

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "aggregate_summary", fake_agg), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: {"git_commit": "c",
                                      "git_dirty": False}):
        run_evaluation(man, tmp / "r.json")

    rec = caps["internal"][0]
    assert rec["_annotation_present"] is False
    assert rec["_tolerance_chars"] == 30
    assert rec["_missing_markers"] == []


# ---------- 空 manifest ----------

def test_empty_manifest_no_per_doc_dir_batch54():
    tmp, root = _env()
    man = Manifest("1.0", "incomplete", (), (), root)
    out = tmp / "sub" / "deep" / "e.json"
    with patch.object(runner_mod, "build_provenance",
                      lambda **k: {"git_commit": "c", "git_dirty": False}):
        rep = run_evaluation(man, out)
    assert list(rep) == ["report_version", "provenance", "devset",
                         "summary", "per_doc", "expected_failures"]
    assert rep["per_doc"] == []
    assert rep["expected_failures"] == []
    assert rep["summary"]["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 0, "rate": None}
    assert (tmp / "sub" / "deep" / "_per_doc").exists() is False
    assert json.loads(out.read_text(encoding="utf-8")) == rep


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_per_doc_stub_twice_batch54():
    src = _src()
    assert src.count('"_per_doc"') == 2
    assert 'ensure_ascii=False' in src
    assert "if document is not None:" in src


# ---------- forbidden tokens 第二百三十八批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch54():
    assert _src().count("open(") == 2
