"""evaluation/runner.py 第四百六十四轮 edges 测试（Round 1020）。

补强 edges125 未触及的角度（第三百九十六批，probe 实证）。

新角度（真实 images 目录端到端）：
- fake process_single 预建 _per_doc/images-<source_hash>/
  并落真实 img1.png → d1 的 image_resource_exists_ratio
  经**真实 metrics** 得 1.0；d2（不同 hash、目录未建）→
  0.0 同屏对照（此前 edges10 造目录但 patch 了 metrics，
  edges100 patch 了 image_output_dir_for——真目录 × 真
  metrics 的组合未锁过）
- run 后 _per_doc 残留恰 ["images-ab12cd34"]：两个
  stub JSON 已 unlink，images 目录按设计留下
- forbidden tokens 第四百九十批（open 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "pv1"

    def __init__(self, sha, rp):
        self.source_hash = sha
        self._rp = rp

    def to_dict(self):
        return {
            "elements": [
                {"element_id": "i1", "type": "image",
                 "resource_path": self._rp, "parent_id": None,
                 "confidence": 0.9, "metadata": {},
                 "source_locator": {"page": 1,
                                    "bbox": [0, 0, 1, 1]}}],
            "chunks": [], "source_type": "pdf",
            "document_id": "x", "schema_version": "0.1.0",
            "source_path": "a.pdf", "source_hash": "a" * 64,
            "parser_name": "fallback", "parser_version": "pv1",
            "relations": [], "warnings": [], "errors": [],
            "metadata": {}}


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    for n in ("a.pdf", "b.pdf"):
        (tmp_path / "samples" / n).write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf"},
            {"doc_id": "d2", "path": "samples/b.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    from evaluation.manifest import load_manifest
    m = load_manifest(mf, tmp_path)

    def fake_ps(path, stub, **kw):
        if "d1" in str(stub):
            stub.parent.mkdir(parents=True, exist_ok=True)
            imgdir = runner_mod.image_output_dir_for(
                stub, "ab12cd34")
            imgdir.mkdir(parents=True, exist_ok=True)
            (imgdir / "img1.png").write_bytes(b"real")
            return _FakeDoc("ab12cd34", "img1.png"), []
        return _FakeDoc("ff99ee77", "img2.png"), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps):
        rep = run_evaluation(m, tmp_path / "o.json")
    return rep


# ---------- 真目录 × 真 metrics ----------

def test_real_image_dir_end_to_end_batch218(tmp_path):
    rep = _run(tmp_path)
    d1 = rep["per_doc"][0]["metrics"]
    d2 = rep["per_doc"][1]["metrics"]
    assert d1["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}
    assert d2["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}
    assert rep["summary"]["ratio_macro_averages"][
        "image_resource_exists_ratio"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- _per_doc 残留 ----------

def test_per_doc_leftover_images_dir_batch218(tmp_path):
    _run(tmp_path)
    leftover = sorted(
        p.name for p in (tmp_path / "_per_doc").iterdir())
    assert leftover == ["images-ab12cd34"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch218():
    src = _src()
    assert ("image_dir = image_output_dir_for("
            "out_stub, document.source_hash)") in src
    assert "if out_stub.is_file():" in src
    assert ("image_base_dir=image_dir if (image_dir is not None"
            " and image_dir.is_dir()) else None,") in src


# ---------- forbidden tokens 第四百九十批 ----------

def test_source_no_eval_batch218():
    assert "eval(" not in _src()


def test_source_no_exec_batch218():
    assert "exec(" not in _src()


def test_source_no_compile_batch218():
    assert "compile(" not in _src()


def test_source_no_globals_batch218():
    assert "globals(" not in _src()


def test_source_no_locals_batch218():
    assert "locals(" not in _src()


def test_source_no_os_system_batch218():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch218():
    assert "subprocess" not in _src()


def test_source_no_popen_batch218():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch218():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch218():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch218():
    assert "socket" not in _src()


def test_source_no_requests_batch218():
    assert "requests" not in _src()


def test_source_no_urllib_batch218():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch218():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch218():
    assert "yield" not in _src()


def test_source_no_async_await_batch218():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch218():
    assert _src().count("open(") == 2
