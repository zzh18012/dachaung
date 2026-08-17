"""evaluation/runner.py 第二百九十六轮 edges 测试（Round 852）。

补强 edges101 未触及的角度（第二百二十六批）。

新角度：
- 磁盘 JSON indent=2（'  "report_version"' 两空格缩进）
- run_evaluation 收 str 输出路径（Path() 包装）
- 每文档 to_dict() 恰调用一次（计数捕获）
- 混合标注可见性：带锚文档有值、无标注文档
  no_annotation（同报告并排）
- _process_one 成功路径直测全五元组
  （dict / None / float / "9.9" / 含 source_hash 的 image_dir）
- forbidden tokens 第三百二十二批
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch

import evaluation.runner as runner_mod
import evaluation.schema_validation as sv
from evaluation.runner import _process_one, run_evaluation


class _FakeDoc:
    def __init__(self, d, pv="9.9", sha="abc123"):
        self._d = d
        self.parser_version = pv
        self.source_hash = sha
        self.calls = 0

    def to_dict(self):
        self.calls += 1
        return self._d


_DOC = {
    "elements": [{"element_id": "e1", "type": "paragraph",
                  "content": "A"}],
    "chunks": [{"text": "A", "source_element_ids": ["e1"]},
               {"text": "B", "source_element_ids": ["e1"]}],
}


def _entry(root, did="d1", ann=None):
    return SimpleNamespace(
        doc_id=did, resolved_path=root / "samples" / "a.pdf",
        source_type="pdf", expectations=None,
        annotation_resolved=ann)


def _manifest(docs, root):
    return SimpleNamespace(
        documents=docs, expected_failures=[],
        project_root=root, devset_status="incomplete",
        file_count=len(docs), content_group_count=len(docs),
        pdf_count=len(docs), docx_count=0,
        categories_covered=[])


def _setup(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return root


def _run(m, out, fakes):
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (fakes.pop(0), [])), \
         patch.object(sv, "document_passes_schema",
                      lambda d: True), \
         patch.object(runner_mod, "build_provenance",
                      lambda **k: {"git_commit": None,
                                   "git_dirty": False}):
        return run_evaluation(m, out)


# ---------- 磁盘格式 ----------

def test_disk_indent_two_batch55(tmp_path):
    root = _setup(tmp_path)
    f = _FakeDoc(_DOC)
    rep = _run(_manifest([_entry(root)], root),
               tmp_path / "out.json", [f])
    text = (tmp_path / "out.json").read_text(encoding="utf-8")
    assert '  "report_version": "1.1"' in text
    assert rep["report_version"] == "1.1"


# ---------- str 输出路径 ----------

def test_str_output_path_batch55(tmp_path):
    root = _setup(tmp_path)
    f = _FakeDoc(_DOC)
    rep = _run(_manifest([_entry(root)], root),
               str(tmp_path / "out.json"), [f])
    assert (tmp_path / "out.json").is_file()
    assert rep["per_doc"][0]["doc_id"] == "d1"


# ---------- to_dict 计数 ----------

def test_to_dict_called_once_per_doc_batch55(tmp_path):
    root = _setup(tmp_path)
    f1, f2 = _FakeDoc(_DOC), _FakeDoc(_DOC)
    rep = _run(_manifest([_entry(root, "d1"),
                          _entry(root, "d2")], root),
               tmp_path / "out.json", [f1, f2])
    assert f1.calls == 1 and f2.calls == 1
    assert [p["doc_id"] for p in rep["per_doc"]] == \
        ["d1", "d2"]


# ---------- 混合标注 ----------

def test_mixed_annotation_visibility_batch55(tmp_path):
    root = _setup(tmp_path)
    ann = tmp_path / "ann.json"
    import json
    ann.write_text(json.dumps({
        "chunk_boundary_anchors": [
            {"marker": "A", "position": "after"}]}),
        encoding="utf-8")
    f1, f2 = _FakeDoc(_DOC), _FakeDoc(_DOC)
    rep = _run(_manifest([_entry(root, "with_ann", ann),
                          _entry(root, "no_ann")], root),
               tmp_path / "out.json", [f1, f2])
    with_m = rep["per_doc"][0]["metrics"][
        "chunk_boundary_precision"]
    without_m = rep["per_doc"][1]["metrics"][
        "chunk_boundary_precision"]
    assert with_m["reason"] is None
    assert without_m == {"value": None,
                         "reason": "no_annotation"}
    for p in rep["per_doc"]:
        wt = p["wall_time_seconds"]["total"]
        assert isinstance(wt, float) and wt >= 0


# ---------- _process_one 成功全元组 ----------

def test_process_one_success_tuple_batch55(tmp_path):
    root = _setup(tmp_path)
    doc = SimpleNamespace(doc_id="d1",
                          resolved_path=root / "samples" /
                          "a.pdf")
    fake = _FakeDoc(_DOC, pv="7.7", sha="deadbeef")
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (fake, [])):
        document, error, elapsed, pv, image_dir = \
            _process_one(doc, tmp_path, "fallback", 800)
    assert document == _DOC
    assert error is None
    assert isinstance(elapsed, float)
    assert pv == "7.7"
    assert image_dir is not None
    assert "deadbeef" in str(image_dir)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'json.dump(report, f, ensure_ascii=False, indent=2)' in src
    assert "out_p = Path(output_path)" in src
    assert 'return document.to_dict(), None, elapsed, document.parser_version, image_dir' in src


# ---------- forbidden tokens 第三百二十二批 ----------

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
