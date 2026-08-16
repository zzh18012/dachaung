"""evaluation/schema.py 第一百零七轮 edges 测试（Round 743）。

补强 edges73/edges74 未触及的角度（第一百零八批）。

新角度：
- 空 dict 错误数：annotation 2 / report 5（manifest 3 已由 edges73 覆盖）
- annotation 深层锁：date 无格式校验（"not-a-date" 通过，仅 minLength 1）/
  heading_order[].text minLength / anchor 元素 additionalProperties false /
  figure_caption_pairs[].caption_text minLength
- 根额外 Unicode 键拒（错误消息含 '标题'）
- load_schema 未知名 → FileNotFoundError
- SCHEMAS_DIR 恰 4 个 schema 文件（annotation/document/
  evaluation-report/manifest）
- validate_file 成功返回 None
- 跨模块集成：runner 用假 pipeline 出真报告 → validate_file 通过
- forbidden tokens 第二百一十三批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import evaluation.runner as runner_mod
import evaluation.schema as schema_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.runner import run_evaluation
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)

ROOT = Path(__file__).resolve().parents[1]

ANN = "annotation.schema.json"


def _ann(**over) -> dict:
    d = {"annotation_version": "1.0", "doc_id": "d"}
    d.update(over)
    return d


def _err(data, name):
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, name)
    return ei.value


# ---------- 空 dict 错误数 ----------

def test_empty_annotation_two_errors_batch54():
    e = _err({}, ANN)
    assert len(e.errors) == 2
    assert [fe["message"] for fe in e.errors] == [
        "'annotation_version' is a required property",
        "'doc_id' is a required property",
    ]


def test_empty_report_five_errors_batch54():
    e = _err({}, "evaluation-report.schema.json")
    assert len(e.errors) == 5
    assert all(fe["path"] == [] for fe in e.errors)


# ---------- annotation 深层锁 ----------

def test_annotation_date_no_format_check_batch54():
    # date 只要求非空字符串，不校验日期格式（现状记录）
    assert validate(_ann(date="not-a-date"), ANN) is None
    assert validate(_ann(date="2026-08-17"), ANN) is None
    assert _err(_ann(date=""), ANN).errors[0]["path"] == ["date"]


def test_annotation_heading_text_min_length_batch54():
    e = _err(_ann(heading_order=[{"level": 1, "text": ""}]), ANN)
    assert e.errors[0]["path"] == ["heading_order", 0, "text"]


def test_annotation_anchor_extra_key_rejected_batch54():
    e = _err(_ann(chunk_boundary_anchors=[
        {"marker": "x", "position": "after", "bogus": 1}]), ANN)
    assert e.errors[0]["path"] == ["chunk_boundary_anchors", 0]


def test_annotation_caption_text_min_length_batch54():
    e = _err(_ann(figure_caption_pairs=[
        {"figure_marker": "f", "caption_text": ""}]), ANN)
    assert e.errors[0]["path"] == ["figure_caption_pairs", 0,
                                   "caption_text"]


def test_annotation_unicode_extra_key_rejected_batch54():
    e = _err(_ann(标题="x"), ANN)
    assert "标题" in e.errors[0]["message"]
    assert e.errors[0]["path"] == []


# ---------- load_schema 边界 ----------

def test_load_schema_unknown_name_filenotfound_batch54():
    with pytest.raises(FileNotFoundError):
        load_schema("bogus.schema.json")


def test_schemas_dir_exact_four_files_batch54():
    assert sorted(p.name for p in SCHEMAS_DIR.glob("*.json")) == [
        "annotation.schema.json", "document.schema.json",
        "evaluation-report.schema.json", "manifest.schema.json",
    ]


def test_validate_file_returns_none_batch54(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps(_ann()), encoding="utf-8")
    assert validate_file(f, ANN) is None


# ---------- 跨模块集成 ----------

def test_runner_report_passes_validate_file_batch54(tmp_path, monkeypatch):
    class DocObj:
        source_hash = "h"
        parser_version = "pv"

        def to_dict(self):
            return {"document_id": "d", "source_type": "pdf",
                    "elements": [], "chunks": []}

    monkeypatch.setattr(
        runner_mod, "process_single",
        lambda *a, **k: (DocObj(), []))

    def entry(i="d1"):
        return DocumentEntry(
            doc_id=i, path_str=f"{i}.pdf", resolved_path=ROOT / f"{i}.pdf",
            source_type="pdf", sha256=None, categories=(), paired_with=None,
            annotation_file_str=None, annotation_resolved=None,
            expectations=None)

    out = tmp_path / "rep.json"
    run_evaluation(Manifest("1.0", "incomplete", (entry(),), (), ROOT), out)
    assert validate_file(out, "evaluation-report.schema.json") is None


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_schemas_dir_definition_batch54():
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' \
        in _src()


# ---------- forbidden tokens 第二百一十三批 ----------

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
