"""evaluation/runner.py 第三百一十七轮 edges 测试（Round 873）。

补强 edges104 未触及的角度（第二百四十八批）。

新角度：
- _process_one 清理落盘 stub：伪造 process_single 写出
  out_stub 后，_process_one 结束时已 unlink
- run_evaluation 全程跑完后 _per_doc 目录为空（常规 +
  ef 的 stub 都被清理）
- parser_version_for_prov 取第一个非 None：失败在前、
  成功在后 → 用成功文档的版本
- 先到先得：两文档版本 "1.1" / "2.2" → provenance 记
  "1.1"
- forbidden tokens 第三百四十三批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    def __init__(self, d, pv="7.7"):
        self._d = d
        self.parser_version = pv
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


def _ps_writing_stub(payload):
    def fake_ps(path, out_path, **kwargs):
        out_path.write_text("stub", encoding="utf-8")
        return payload
    return fake_ps


# ---------- stub 清理 ----------

def test_process_one_unlinks_written_stub_batch71(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    with patch.object(runner_mod, "process_single",
                      side_effect=_ps_writing_stub(
                          (_FakeDoc(_DOC_DICT), []))):
        doc, err, secs, pv, image_dir = \
            runner_mod._process_one(m.documents[0],
                                    tmp_path, "fallback", 800)
    assert doc == _DOC_DICT
    assert err is None
    assert pv == "7.7"
    assert not (tmp_path / "_per_doc" / "d1.json").exists()


def test_per_doc_dir_empty_after_run_batch71(tmp_path):
    m = _mk(tmp_path,
            [{"doc_id": "d1", "path": "samples/a.pdf",
              "source_type": "pdf"}],
            efs=[{"doc_id": "f1", "path": "samples/b.pdf",
                  "expected_error_code": "E"}])
    seq = [(_FakeDoc(_DOC_DICT), []), (None, [_Err("E")])]

    def fake_ps(path, out_path, **kwargs):
        out_path.write_text("stub", encoding="utf-8")
        return seq.pop(0)

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, tmp_path / "r.json")
    per_doc = tmp_path / "_per_doc"
    assert per_doc.is_dir()
    assert list(per_doc.iterdir()) == []


# ---------- parser_version 归属 ----------

def test_prov_version_from_first_success_batch71(tmp_path):
    m = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"},
        {"doc_id": "d2", "path": "samples/b.pdf",
         "source_type": "pdf"}])
    seq = [(None, [_Err("E_X")]),
           (_FakeDoc(_DOC_DICT, pv="9.9"), [])]
    it = iter(seq)
    captured = {}

    def fake_bp(**kwargs):
        captured.update(kwargs)
        return {}

    with patch.object(runner_mod, "process_single",
                      side_effect=lambda *a, **k: next(it)), \
         patch.object(runner_mod, "build_provenance",
                      side_effect=fake_bp):
        run_evaluation(m, tmp_path / "r.json")
    assert captured["parser_version"] == "9.9"
    assert captured["parser_name"] == "fallback"
    assert captured["max_chars"] == 800


def test_prov_version_first_wins_batch71(tmp_path):
    m = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"},
        {"doc_id": "d2", "path": "samples/b.pdf",
         "source_type": "pdf"}])
    seq = [(_FakeDoc(_DOC_DICT, pv="1.1"), []),
           (_FakeDoc(_DOC_DICT, pv="2.2"), [])]
    it = iter(seq)
    captured = {}

    def fake_bp(**kwargs):
        captured.update(kwargs)
        return {}

    with patch.object(runner_mod, "process_single",
                      side_effect=lambda *a, **k: next(it)), \
         patch.object(runner_mod, "build_provenance",
                      side_effect=fake_bp):
        run_evaluation(m, tmp_path / "r.json")
    assert captured["parser_version"] == "1.1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch71():
    src = _src()
    assert "if out_stub.is_file():" in src
    assert "out_stub.unlink()" in src
    assert "if parser_version and not parser_version_for_prov:" in src


# ---------- forbidden tokens 第三百四十三批 ----------

def test_source_no_eval_batch71():
    assert "eval(" not in _src()


def test_source_no_exec_batch71():
    assert "exec(" not in _src()


def test_source_no_compile_batch71():
    assert "compile(" not in _src()


def test_source_no_globals_batch71():
    assert "globals(" not in _src()


def test_source_no_locals_batch71():
    assert "locals(" not in _src()


def test_source_no_os_system_batch71():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch71():
    assert "subprocess" not in _src()


def test_source_no_popen_batch71():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch71():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch71():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch71():
    assert "socket" not in _src()


def test_source_no_requests_batch71():
    assert "requests" not in _src()


def test_source_no_urllib_batch71():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch71():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch71():
    assert "yield" not in _src()


def test_source_no_async_await_batch71():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch71():
    assert _src().count("open(") == 2
