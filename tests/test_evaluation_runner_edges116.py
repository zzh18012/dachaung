"""evaluation/runner.py 第三百九十四轮 edges 测试（Round 950）。

补强 edges115 未触及的角度（第三百二十六批，probe 实证）。

新角度：
- expected_failures 实跑：文件不存在 → actual_error_code
  "file_not_found"（小写），与 "E_FILE_NOT_FOUND" 不匹配 →
  matches False；ef 条目四键形状
- run_evaluation 落盘 round-trip：json.load 读回与返回值
  全等；嵌套输出目录自动创建
- 报告六键有序；per_doc 四键（无 _annotation_present
  等内部字段泄漏）
- annotation 文件内容为 JSON 数组 [] → _load_annotation
  返回 []（非 None）；下游 chunk_boundary reason 是
  no_annotation（falsy 先于 anchors 检查），figure_caption
  仍 parser_does_not_emit_relations
- parser_version 传播：首个非 None 生效（[None, "9.9"] →
  "9.9"；["7.7", "7.7"] → "7.7"）
- forbidden tokens 第四百二十批（open 2）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation, _load_annotation


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "samples" / "b.pdf").write_bytes(b"x")


def _manifest(tmp_path, docs, ef=None):
    data = {"manifest_version": "1.0",
            "devset_status": "incomplete", "documents": docs}
    if ef:
        data["expected_failures"] = ef
    f = tmp_path / f"m{len(list(tmp_path.glob('m*.json')))}.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    from evaluation.manifest import load_manifest
    return load_manifest(f, tmp_path)


# ---------- expected_failures 实跑 ----------

def test_ef_missing_file_actual_code_batch148(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}],
        ef=[{"doc_id": "ef1", "path": "samples/missing.pdf",
             "expected_error_code": "E_FILE_NOT_FOUND"}])
    rep = run_evaluation(m, tmp_path / "out" / "o.json")
    assert rep["expected_failures"] == [{
        "doc_id": "ef1",
        "expected_error_code": "E_FILE_NOT_FOUND",
        "actual_error_code": "file_not_found",
        "matches": False}]


# ---------- round-trip + 键序 ----------

def test_report_roundtrip_and_keys_batch148(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"}])
    rep = run_evaluation(m, tmp_path / "deep" / "nest" / "o.json")
    disk = json.loads(
        (tmp_path / "deep" / "nest" / "o.json").read_text(
            encoding="utf-8"))
    assert disk == rep
    assert list(rep) == ["report_version", "provenance", "devset",
                         "summary", "per_doc",
                         "expected_failures"]
    assert list(rep["per_doc"][0]) == [
        "doc_id", "source_type", "metrics", "wall_time_seconds"]


# ---------- annotation 数组怪癖 ----------

def test_annotation_array_quirk_batch148(tmp_path):
    (tmp_path / "ann.json").write_text("[]", encoding="utf-8")
    loaded = _load_annotation(tmp_path / "ann.json")
    assert loaded == []
    assert loaded is not None


def test_annotation_array_downstream_reasons_batch148(tmp_path):
    _setup(tmp_path)
    (tmp_path / "ann.json").write_text("[]", encoding="utf-8")
    m = _manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf",
         "annotation_file": "ann.json"}])

    calls = {"n": 0}

    def fake_ps(*a, **k):
        calls["n"] += 1

        class D:
            source_hash = "a" * 64
            parser_version = "7.7"

            def to_dict(self):
                return {"schema_version": "0.1.0"}
        return D(), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps):
        rep = run_evaluation(m, tmp_path / "o.json")
    metrics = rep["per_doc"][0]["metrics"]
    assert metrics["chunk_boundary_precision"] == {
        "value": None, "reason": "no_annotation"}
    assert metrics["figure_caption_precision"]["reason"] == \
        "parser_does_not_emit_relations"


# ---------- parser_version 传播 ----------

def _probe_version(tmp_path, versions):
    _setup(tmp_path)
    m = _manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"},
        {"doc_id": "d2", "path": "samples/b.pdf",
         "source_type": "pdf"}])
    calls = {"n": 0}
    it = iter(versions)

    def fake_ps(*a, **k):
        calls["n"] += 1

        class D:
            source_hash = "a" * 64
            parser_version = next(it)

            def to_dict(self):
                return {"schema_version": "0.1.0"}
        return D(), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      side_effect=lambda **k: {
                          "parser_version":
                              k.get("parser_version")}):
        rep = run_evaluation(m, tmp_path / "ov.json")
    return rep["provenance"]["parser_version"]


def test_parser_version_first_non_none_batch148(tmp_path):
    assert _probe_version(tmp_path, [None, "9.9"]) == "9.9"


def test_parser_version_all_set_batch148(tmp_path):
    assert _probe_version(tmp_path, ["7.7", "7.7"]) == "7.7"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch148():
    src = _src()
    assert 'if parser_version and not parser_version_for_prov:' in src
    assert 'actual_code = errors[0].code if errors else None' in src
    assert '"matches": actual_code == ef.expected_error_code,' in src
    assert 'json.dump(report, f, ensure_ascii=False, indent=2)' in src


# ---------- forbidden tokens 第四百二十批 ----------

def test_source_no_eval_batch148():
    assert "eval(" not in _src()


def test_source_no_exec_batch148():
    assert "exec(" not in _src()


def test_source_no_compile_batch148():
    assert "compile(" not in _src()


def test_source_no_globals_batch148():
    assert "globals(" not in _src()


def test_source_no_locals_batch148():
    assert "locals(" not in _src()


def test_source_no_os_system_batch148():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch148():
    assert "subprocess" not in _src()


def test_source_no_popen_batch148():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch148():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch148():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch148():
    assert "socket" not in _src()


def test_source_no_requests_batch148():
    assert "requests" not in _src()


def test_source_no_urllib_batch148():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch148():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch148():
    assert "yield" not in _src()


def test_source_no_async_await_batch148():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch148():
    assert _src().count("open(") == 2
