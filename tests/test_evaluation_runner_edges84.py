"""evaluation/runner.py 第二百零二轮 edges 测试（Round 726）。

补强 edges81/edges82/edges83 未触及的角度（第九十一批）。

新角度：
- image_base_dir 仅在 image_dir.is_dir() 时传入（ghost 目录 → None）逐 doc 捕获
- metrics 恰为 compute 输出 ∪ fig ∪ chunk 三方并集（noop prf 下精确键集）
- 报告写盘 indent=2 + ensure_ascii=False（中文 reason 原样落盘）
- 输出路径深层嵌套（out/a/b/r.json）自动建目录
- per_doc 顺序与 manifest.documents 顺序一致
- 重复 doc_id 双份都跑（_per_doc stub 同路径先后覆盖不冲突）
- ef stub 被 pipeline 写出后清理（fake ps 落盘 output_path）
- _load_annotation 非法 JSON → None（JSONDecodeError 分支）
- AST（run_evaluation For3·With1·Dict5·Call26 / _process_one Dict1·Call9 / _load_annotation With1·Call3）
- 源码补强（mkdir×4 / metrics.update×2 / open(×2 / json.dump×1 / _annotation_present 行）
- forbidden tokens 第一百九十六批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _load_annotation, _process_one, run_evaluation


class _FakeDoc:
    def __init__(self, parser_version="1.0"):
        self.parser_version = parser_version
        self.source_hash = "a" * 64

    def to_dict(self):
        return {"document_id": "d", "elements": [], "chunks": []}


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _entry(doc_id, resolved, annotation_resolved=None):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"{doc_id}.pdf", resolved_path=resolved,
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=annotation_resolved,
        expectations=None,
    )


def _manifest(tmp_path, docs=(), efs=()):
    return Manifest("1.0", "incomplete", tuple(docs), tuple(efs), tmp_path)


def _patch_all(monkeypatch, tmp_path):
    """ps 成功 + prf noop + compute 捕获 image_base_dir。"""
    captured = {"compute": [], "dirs": []}
    real_dir = tmp_path / "imgs"
    real_dir.mkdir(exist_ok=True)

    def fake_ps(inp, outp, **k):
        return _FakeDoc(), []

    def fake_helper(stub, h):
        # 第一次调用返回存在的目录，之后返回 ghost
        if not captured["dirs"]:
            captured["dirs"].append(real_dir)
            return real_dir
        ghost = tmp_path / "ghost"
        captured["dirs"].append(ghost)
        return ghost

    def fake_compute(**kwargs):
        captured["compute"].append(kwargs["image_base_dir"])
        return {"pipeline_success": {"value": True, "reason": None}}

    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    monkeypatch.setattr(runner_mod, "image_output_dir_for", fake_helper)
    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", fake_compute)
    monkeypatch.setattr(runner_mod, "figure_caption_prf", lambda d, a: {})
    monkeypatch.setattr(runner_mod, "chunk_boundary_prf",
                        lambda d, a, **k: {})
    return captured, real_dir


# ---------- image_base_dir 条件传入 ----------

def test_image_base_dir_only_when_is_dir_batch53(monkeypatch, tmp_path):
    captured, real_dir = _patch_all(monkeypatch, tmp_path)
    docs = [_entry("a", tmp_path / "a.pdf"), _entry("b", tmp_path / "b.pdf")]
    run_evaluation(_manifest(tmp_path, docs=docs), tmp_path / "out" / "r.json")
    assert captured["compute"] == [real_dir, None]


# ---------- metrics 键并集 ----------

def test_metrics_keys_exact_union_batch53(monkeypatch, tmp_path):
    captured, _ = _patch_all(monkeypatch, tmp_path)

    def fake_compute2(**kwargs):
        return {"k1": {"value": 1, "reason": None},
                "k2": {"value": 2, "reason": None}}
    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", fake_compute2)
    monkeypatch.setattr(runner_mod, "figure_caption_prf",
                        lambda d, a: {"k3": {"value": None, "reason": "x"}})
    monkeypatch.setattr(runner_mod, "chunk_boundary_prf",
                        lambda d, a, **k: {"k4": {"value": None, "reason": "y"}})
    m = _manifest(tmp_path, docs=[_entry("a", tmp_path / "a.pdf")])
    report = run_evaluation(m, tmp_path / "out" / "r.json")
    assert sorted(report["per_doc"][0]["metrics"].keys()) == \
        ["k1", "k2", "k3", "k4"]


# ---------- ensure_ascii=False 落盘 ----------

def test_report_chinese_reason_raw_on_disk_batch53(monkeypatch, tmp_path):
    _, _real = _patch_all(monkeypatch, tmp_path)

    def fake_compute_cn(**kwargs):
        return {"k": {"value": None, "reason": "中文原因"}}
    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", fake_compute_cn)
    m = _manifest(tmp_path, docs=[_entry("a", tmp_path / "a.pdf")])
    out = tmp_path / "out" / "r.json"
    run_evaluation(m, out)
    raw = out.read_text(encoding="utf-8")
    assert "中文原因" in raw
    assert "\\u4e2d" not in raw  # 未被转义
    assert '\n  ' in raw  # indent=2


# ---------- 深层输出路径 ----------

def test_deep_output_path_created_batch53(monkeypatch, tmp_path):
    _, _real = _patch_all(monkeypatch, tmp_path)
    out = tmp_path / "out" / "a" / "b" / "c" / "r.json"
    m = _manifest(tmp_path, docs=[_entry("a", tmp_path / "a.pdf")])
    run_evaluation(m, out)
    assert out.is_file()


# ---------- per_doc 顺序 ----------

def test_per_doc_order_preserved_batch53(monkeypatch, tmp_path):
    _, _real = _patch_all(monkeypatch, tmp_path)
    ids = ["z", "a", "m", "b"]
    docs = [_entry(i, tmp_path / f"{i}.pdf") for i in ids]
    report = run_evaluation(_manifest(tmp_path, docs=docs),
                            tmp_path / "out" / "r.json")
    assert [r["doc_id"] for r in report["per_doc"]] == ids


# ---------- 重复 doc_id ----------

def test_duplicate_doc_ids_both_processed_batch53(monkeypatch, tmp_path):
    _, _real = _patch_all(monkeypatch, tmp_path)
    docs = [_entry("same", tmp_path / "a.pdf"), _entry("same", tmp_path / "b.pdf")]
    report = run_evaluation(_manifest(tmp_path, docs=docs),
                            tmp_path / "out" / "r.json")
    assert [r["doc_id"] for r in report["per_doc"]] == ["same", "same"]
    assert len(report["per_doc"]) == 2


# ---------- ef stub 清理（ps 落盘场景） ----------

def test_ef_stub_written_then_unlinked_batch53(monkeypatch, tmp_path):
    def fake_ps(inp, outp, **k):
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text("{}", encoding="utf-8")
        return None, [_Err("unsupported")]
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    _, _real = _patch_all(monkeypatch, tmp_path)  # noop compute/prf（未被走到）
    ef = ExpectedFailure("ef1", "b.bin", tmp_path / "b.bin", "unsupported", "other")
    run_evaluation(_manifest(tmp_path, efs=[ef]), tmp_path / "out" / "r.json")
    assert not (tmp_path / "out" / "_per_doc" / "ef1.json").exists()
    assert (tmp_path / "out" / "_per_doc").is_dir()


# ---------- _load_annotation 非法 JSON ----------

def test_load_annotation_invalid_json_none_batch53(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_valid_roundtrip_batch53(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_mkdir_and_update_counts_batch53():
    src = _src()
    assert src.count("mkdir(parents=True, exist_ok=True)") == 4
    assert src.count("metrics.update(") == 2
    assert src.count("open(") == 2
    assert src.count("json.dump(") == 1


def test_source_annotation_present_line_batch53():
    assert '"_annotation_present": annotation is not None,' in _src()


def test_source_output_root_mkdir_batch53():
    assert "output_root.mkdir(parents=True, exist_ok=True)" in _src()
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(runner_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


@pytest.mark.parametrize("name,expect", [
    ("_load_annotation", (1, 0, 1, 3, 1, 0, 3)),
    ("_process_one", (4, 0, 1, 3, 0, 1, 9)),
    ("run_evaluation", (2, 3, 1, 1, 1, 5, 26)),
])
def test_ast_function_structures_batch53(name, expect):
    c = _counts(_func(name))
    got = (c["If"], c["For"], c["Try"], c["Return"], c["With"], c["Dict"],
           c["Call"])
    assert got == expect, name


def test_ast_run_eval_no_while_no_listcomp_batch53():
    c = _counts(_func("run_evaluation"))
    assert c["While"] == 0
    assert c["ListComp"] == 0
    assert c["AnnAssign"] == 3


# ---------- forbidden tokens 第一百九十六批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()
