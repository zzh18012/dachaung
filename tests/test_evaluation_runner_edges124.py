"""evaluation/runner.py 第四百五十轮 edges 测试（Round 1006）。

补强 edges123 未触及的角度（第三百八十二批，probe 实证）。

新角度（双循环 process_single 捕获对照）：
- documents 循环 stub 名 "d1.json"、expected_failures 循环
  stub 名 "ef1.json"（同层 _per_doc/、各用 doc_id）
- 两个循环传给 process_single 的 kwargs 完全一致：
  parser_name=fallback / max_chars=777 / write_json=False
- 成功文档 to_dict 恰被调用 1 次（不多序列化）
- wall_time_seconds.total 恒 float ≥ 0（成功路径）
- forbidden tokens 第四百七十六批（open 2）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "pv"
    source_hash = "abcd1234"
    to_dict_calls = 0

    def to_dict(self):
        _FakeDoc.to_dict_calls += 1
        return {
            "schema_version": "0.1.0", "document_id": "d",
            "source_path": "a.pdf", "source_type": "pdf",
            "source_hash": "a" * 64, "parser_name": "fallback",
            "parser_version": "pv",
            "elements": [
                {"element_id": "e1", "type": "paragraph",
                 "content": "x", "parent_id": None,
                 "confidence": 0.9, "metadata": {},
                 "source_locator": {"page": 1,
                                    "bbox": [1, 2, 3, 4]}}],
            "chunks": [{"chunk_id": "c1", "text": "x",
                        "source_element_ids": ["e1"],
                        "char_count": 1}],
            "relations": [], "warnings": [], "errors": [],
            "metadata": {}}


class _FakeErr:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "samples" / "bad.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}],
        "expected_failures": [
            {"doc_id": "ef1", "path": "samples/bad.pdf",
             "expected_error_code": "E_X"}]}),
        encoding="utf-8")

    calls = []

    def fake_ps(path, stub, **kw):
        calls.append((Path(path).name, Path(stub).name, kw))
        if "bad" in str(path):
            return None, [_FakeErr("E_X")]
        return _FakeDoc(), []

    from evaluation.manifest import load_manifest
    m = load_manifest(mf, tmp_path)
    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps):
        rep = run_evaluation(m, tmp_path / "o.json",
                             parser_name="fallback",
                             max_chars=777, tolerance_chars=9)
    return rep, calls


# ---------- 双循环 stub 命名 ----------

def test_both_loop_stub_names_batch204(tmp_path):
    _, calls = _run(tmp_path)
    assert [c[1] for c in calls] == ["d1.json", "ef1.json"]


# ---------- 双循环 kwargs 一致 ----------

def test_both_loop_kwargs_identical_batch204(tmp_path):
    _, calls = _run(tmp_path)
    assert calls[0][2] == calls[1][2] == {
        "parser_name": "fallback", "max_chars": 777,
        "write_json": False}


# ---------- to_dict 单次 ----------

def test_to_dict_called_once_batch204(tmp_path):
    _FakeDoc.to_dict_calls = 0
    _run(tmp_path)
    assert _FakeDoc.to_dict_calls == 1


# ---------- wall_time float ----------

def test_wall_time_total_float_batch204(tmp_path):
    rep, _ = _run(tmp_path)
    total = rep["per_doc"][0]["wall_time_seconds"]["total"]
    assert type(total) is float
    assert total >= 0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch204():
    src = _src()
    assert 'out_stub = output_root / "_per_doc" / f"{doc.doc_id}.json"' in src
    assert 'out_stub = output_root / "_per_doc" / f"{ef.doc_id}.json"' in src
    assert "write_json=False," in src
    assert src.count("write_json=False,") == 2


# ---------- forbidden tokens 第四百七十六批 ----------

def test_source_no_eval_batch204():
    assert "eval(" not in _src()


def test_source_no_exec_batch204():
    assert "exec(" not in _src()


def test_source_no_compile_batch204():
    assert "compile(" not in _src()


def test_source_no_globals_batch204():
    assert "globals(" not in _src()


def test_source_no_locals_batch204():
    assert "locals(" not in _src()


def test_source_no_os_system_batch204():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch204():
    assert "subprocess" not in _src()


def test_source_no_popen_batch204():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch204():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch204():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch204():
    assert "socket" not in _src()


def test_source_no_requests_batch204():
    assert "requests" not in _src()


def test_source_no_urllib_batch204():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch204():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch204():
    assert "yield" not in _src()


def test_source_no_async_await_batch204():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch204():
    assert _src().count("open(") == 2
