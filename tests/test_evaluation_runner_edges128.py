"""evaluation/runner.py 第四百七十八轮 edges 测试（Round 1034）。

补强 edges127 未触及的角度（第四百一十批，probe 实证）。

新角度（_per_doc 三方生命周期合流）：
- 同一 run 内 doc stub（d1.json）与 ef stub（f1.json）
  双双 unlink、仅 images-<source_hash> 目录留下——
  R1020 只锁 doc 侧、ef stub unlink 只在无 images 场景
  锁过，三方同屏未锁
- images 目录名截 source_hash 前 16 字符
  （images-ab12ab12ab12ab12，32 位 hash 截半）；
  _per_doc 目录本身保留不清理
- 图片比率与目录存在性解耦：images 目录真实存在但
  doc 无 image 元素 → image_resource_exists_ratio
  null no_image_elements（元素驱动、非目录驱动）
- ef matches True 与 wall_time_seconds 五键结构
  （total float / parse / chunk null / 双
  not_instrumented reason）同屏
- forbidden tokens 第五百零五批（open 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation

_SHA = "ab12" * 8
_DIR = f"images-{_SHA[:16]}"


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "samples" / "bad.pdf").write_bytes(b"g")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/a.pdf",
                       "source_type": "pdf"}],
        "expected_failures": [
            {"doc_id": "f1", "path": "samples/bad.pdf",
             "expected_error_code": "E_X"}]}),
        encoding="utf-8")
    m = load_manifest(mf, tmp_path)

    class _FakeDoc:
        parser_version = "pv"
        source_hash = _SHA

        def to_dict(self):
            return {"elements": [], "chunks": []}

    class _Err:
        def __init__(self, code):
            self.code = code

        def to_dict(self):
            return {"code": self.code, "message": "m"}

    def fake_ps(path, out_stub, **kw):
        img_dir = runner_mod.image_output_dir_for(
            out_stub, _SHA)
        img_dir.mkdir(parents=True, exist_ok=True)
        (img_dir / "img.png").write_bytes(b"p")
        if path.name == "bad.pdf":
            return None, [_Err("E_X")]
        return _FakeDoc(), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps):
        rep = run_evaluation(m, tmp_path / "o.json")
    return rep, tmp_path / "_per_doc"


# ---------- 三方生命周期 ----------

def test_per_doc_leftovers_only_images_batch232(tmp_path):
    rep, per = _run(tmp_path)
    assert per.is_dir()
    assert sorted(p.name for p in per.iterdir()) == \
        [_DIR]
    assert not (per / "d1.json").exists()
    assert not (per / "f1.json").exists()


# ---------- 目录存在性与比率解耦 ----------

def test_image_ratio_dir_decoupled_batch232(tmp_path):
    rep, per = _run(tmp_path)
    assert (per / _DIR / "img.png").is_file()
    assert rep["per_doc"][0]["metrics"][
        "image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"}


# ---------- wall_time 五键 + ef 同屏 ----------

def test_wall_time_and_ef_batch232(tmp_path):
    rep, _ = _run(tmp_path)
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert isinstance(wt["total"], float)
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert rep["expected_failures"] == [{
        "doc_id": "f1", "expected_error_code": "E_X",
        "actual_error_code": "E_X", "matches": True}]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch232():
    src = _src()
    assert "out_stub.parent.mkdir(parents=True," in src
    assert "out_stub.unlink()" in src
    assert "image_output_dir_for(" in src


# ---------- forbidden tokens 第五百零五批 ----------

def test_source_no_eval_batch232():
    assert "eval(" not in _src()


def test_source_no_exec_batch232():
    assert "exec(" not in _src()


def test_source_no_compile_batch232():
    assert "compile(" not in _src()


def test_source_no_globals_batch232():
    assert "globals(" not in _src()


def test_source_no_locals_batch232():
    assert "locals(" not in _src()


def test_source_no_os_system_batch232():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch232():
    assert "subprocess" not in _src()


def test_source_no_popen_batch232():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch232():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch232():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch232():
    assert "socket" not in _src()


def test_source_no_requests_batch232():
    assert "requests" not in _src()


def test_source_no_urllib_batch232():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch232():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch232():
    assert "yield" not in _src()


def test_source_no_async_await_batch232():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch232():
    assert _src().count("open(") == 2
