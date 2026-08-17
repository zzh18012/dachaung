"""evaluation/cli.py 第三百零四轮 edges 测试（Round 860）。

补强 edges102 未触及的角度（第二百三十五批）。

新角度：
- validate-report 真实垃圾 JSON → JSONDecodeError 分支 rc1
- inspect-doc 垃圾 JSON rc1；顶层 list → 「JSON 顶层不是对象」
- inspect-doc 缺 document_id/source_path/parser_name → "?" 默认
- inspect-doc 有 document_id → 正常显示
- run --manifest 指向目录 → is_file() False → rc2
- run 成功输出 devset 详情行 + git_dirty False
- inspect-doc null 指标整体排在非 null 之后
- forbidden tokens 第三百三十批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.cli as cli_mod
from evaluation.cli import main


_DOC = {
    "source_type": "pdf",
    "elements": [{"element_id": "e1", "type": "paragraph",
                  "content": "AB",
                  "source_locator": {"page": 1,
                                     "bbox": [0, 0, 1, 1]}}],
    "chunks": [{"text": "AB",
                "source_element_ids": ["e1"]}],
}


# ---------- validate-report 真实坏 JSON ----------

def test_validate_report_garbage_json_rc1_batch58(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{not json", encoding="utf-8")
    rc = main(["validate-report", str(f)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


# ---------- inspect-doc 坏输入 ----------

def test_inspect_garbage_json_rc1_batch58(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("[[[", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


def test_inspect_top_level_list_rc1_batch58(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("[1, 2]", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert "JSON 顶层不是对象" in capsys.readouterr().err


# ---------- inspect-doc 元信息默认 ----------

def test_inspect_missing_meta_defaults_batch58(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(_DOC), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "document_id: ?" in out
    assert "source:      ?  type=pdf" in out
    assert "parser:      ? v?" in out


def test_inspect_document_id_shown_batch58(tmp_path, capsys):
    doc = dict(_DOC)
    doc["document_id"] = "doc-1"
    f = tmp_path / "d.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "document_id: doc-1" in out
    assert "document_id: ?" not in out


# ---------- run 清单目录 ----------

def test_run_manifest_is_dir_rc2_batch58(tmp_path, capsys):
    rc = main(["run", "--manifest", str(tmp_path),
               "--output", str(tmp_path / "r.json")])
    assert rc == 2
    assert "清单不存在" in capsys.readouterr().err


# ---------- run 成功 devset 行 ----------

def test_run_success_devset_and_git_line_batch58(tmp_path, capsys):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}), encoding="utf-8")
    out = tmp_path / "r.json"
    out.write_text("{}", encoding="utf-8")
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "source_type": "pdf",
             "metrics": {"pipeline_success": {"value": True,
                                              "reason": None}},
             "wall_time_seconds": {}}],
        "devset": {"status": "incomplete", "file_count": 1,
                   "content_group_count": 2, "pdf_count": 1,
                   "docx_count": 0},
    }
    with patch.object(cli_mod, "run_evaluation",
                      return_value=fake_report) as fake_run, \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": "a" * 40,
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    assert rc == 0
    assert fake_run.call_args.kwargs["parser_name"] == "fallback"
    o = capsys.readouterr().out
    assert "documents=1（成功 1，失败 0）" in o
    assert "devset_status=incomplete file_count=1 " \
           "groups=2 pdf=1 docx=0" in o
    assert "git_commit=aaaaaaaaaaaa git_dirty=False" in o


# ---------- null 指标整体靠后 ----------

def test_inspect_null_metrics_sorted_last_batch58(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(_DOC), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    lines = capsys.readouterr().out.splitlines()
    assert rc == 0
    start = lines.index("metrics:")
    metric_lines = [ln for ln in lines[start + 1:]
                    if ln.startswith("  ")]
    is_null = [" null  (" in ln for ln in metric_lines]
    first_null = is_null.index(True)
    assert all(is_null[first_null:])
    names = [ln.strip().split()[0] for ln in metric_lines]
    for nm in ("figure_caption_f1", "chunk_boundary_f1",
               "docx_locator_valid_ratio", "silent_drop_count"):
        assert nm in names[first_null:]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch58():
    src = _src()
    assert "if not isinstance(doc, dict):" in src
    assert 'print("[ERROR] JSON 顶层不是对象", file=sys.stderr)' in src
    assert "sorted(metrics.keys(), key=_sort_key)" in src


# ---------- forbidden tokens 第三百三十批 ----------

def test_source_no_eval_batch58():
    assert "eval(" not in _src()


def test_source_no_exec_batch58():
    assert "exec(" not in _src()


def test_source_no_compile_batch58():
    assert "compile(" not in _src()


def test_source_no_globals_batch58():
    assert "globals(" not in _src()


def test_source_no_locals_batch58():
    assert "locals(" not in _src()


def test_source_no_os_system_batch58():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch58():
    assert "subprocess" not in _src()


def test_source_no_popen_batch58():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch58():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch58():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch58():
    assert "socket" not in _src()


def test_source_no_requests_batch58():
    assert "requests" not in _src()


def test_source_no_urllib_batch58():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch58():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch58():
    assert "yield" not in _src()


def test_source_no_async_await_batch58():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch58():
    assert _src().count("open(") == 1
