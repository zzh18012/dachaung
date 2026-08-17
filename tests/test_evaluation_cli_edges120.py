"""evaluation/cli.py 第四百二十三轮 edges 测试（Round 979）。

补强 edges119 未触及的角度（第三百五十五批，probe 实证）。

新角度：
- run 成功 [OK] 4 行块：documents=2（成功 1，失败 1）、devset
  行 5 字段、git_commit 截前 12 字符（abcdef1234567890abcd →
  abcdef123456）
- validate-report 成功行 "[OK] <path> 通过 evaluation-report
  Schema 校验" rc 0
- inspect-doc 泄漏内部键 _tolerance_chars（runner 会 pop，
  inspect 不 pop）→ 渲染 "30  (ok)"；_missing_markers 不出现
- inspect-doc 四桶排序锁位：bool（pipeline_success）→ 数值
  （pdf_locator）→ dict（element_count_by_type）→ null
  （error_code）
- forbidden tokens 第四百四十九批（open 1）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.cli as cli_mod
from evaluation.cli import main


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "s/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


# ---------- run [OK] 4 行块 ----------

def test_run_ok_block_four_lines_batch177(tmp_path, capsys):
    mf = _setup(tmp_path)
    out = tmp_path / "o.json"
    fake_report = {
        "per_doc": [
            {"doc_id": "d1", "source_type": "pdf",
             "metrics": {"pipeline_success": {"value": True,
                                              "reason": None}},
             "wall_time_seconds": {}},
            {"doc_id": "d2", "source_type": "docx",
             "metrics": {"pipeline_success": {"value": False,
                                              "reason": None}},
             "wall_time_seconds": {}}],
        "devset": {"status": "incomplete", "file_count": 2,
                   "content_group_count": 2, "pdf_count": 1,
                   "docx_count": 1}}
    with patch.object(cli_mod, "run_evaluation",
                      return_value=fake_report), \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit":
                                    "abcdef1234567890abcd",
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(out)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == f"[OK] 评测完成：{out}"
    assert lines[1] == "      documents=2（成功 1，失败 1）"
    assert lines[2] == ("      devset_status=incomplete "
                        "file_count=2 groups=2 pdf=1 docx=1")
    assert lines[3] == ("      git_commit=abcdef123456 "
                        "git_dirty=False")
    assert len(lines) == 4


# ---------- validate-report 成功行 ----------

def test_validate_report_ok_line_batch177(tmp_path, capsys):
    rf = tmp_path / "r.json"
    rf.write_text("{}", encoding="utf-8")
    with patch.object(cli_mod, "validate_file"):
        rc = main(["validate-report", str(rf)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == \
        f"[OK] {rf} 通过 evaluation-report Schema 校验"


# ---------- inspect-doc 泄漏内部键 ----------

def _write_doc(tmp_path):
    doc = {"source_type": "pdf",
           "elements": [{"type": "paragraph", "content": "A",
                         "source_locator": {"page": 1,
                                            "bbox": [0, 0, 1, 1]}}],
           "chunks": [{"text": "A",
                       "source_element_ids": ["e1"]}]}
    df = tmp_path / "d.json"
    df.write_text(json.dumps(doc), encoding="utf-8")
    return df


def test_inspect_doc_leaks_tolerance_key_batch177(tmp_path,
                                                  capsys):
    df = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(df)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "_tolerance_chars" in out
    assert "_tolerance_chars".ljust(36) + " 30  (ok)" in out
    assert "_missing_markers" not in out


# ---------- 四桶排序 ----------

def test_inspect_doc_bucket_order_batch177(tmp_path, capsys):
    df = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(df)])
    assert rc == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines()
             if ln.startswith("  ")]
    names = [ln.strip().split()[0] for ln in lines]
    i_bool = names.index("pipeline_success")
    i_num = names.index("pdf_locator_valid_ratio")
    i_internal = names.index("_tolerance_chars")
    i_dict = names.index("element_count_by_type")
    i_null = names.index("error_code")
    assert i_bool < i_num < i_dict < i_null
    assert i_bool < i_internal < i_null
    assert names[-1] == "silent_drop_count"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch177():
    src = _src()
    assert 'f"[OK] 评测完成：{output_path}\\n"' in src
    assert "f\"      git_commit={(git.get('git_commit') or 'unknown')[:12]} \"" in src
    assert "metrics.update(chunk_boundary_prf(doc, None, tolerance_chars=args.tolerance_chars))" in src
    assert 'print(f"[OK] {input_path} 通过 evaluation-report Schema 校验")' in src


# ---------- forbidden tokens 第四百四十九批 ----------

def test_source_no_eval_batch177():
    assert "eval(" not in _src()


def test_source_no_exec_batch177():
    assert "exec(" not in _src()


def test_source_no_compile_batch177():
    assert "compile(" not in _src()


def test_source_no_globals_batch177():
    assert "globals(" not in _src()


def test_source_no_locals_batch177():
    assert "locals(" not in _src()


def test_source_no_os_system_batch177():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch177():
    assert "subprocess" not in _src()


def test_source_no_popen_batch177():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch177():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch177():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch177():
    assert "socket" not in _src()


def test_source_no_requests_batch177():
    assert "requests" not in _src()


def test_source_no_urllib_batch177():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch177():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch177():
    assert "yield" not in _src()


def test_source_no_async_await_batch177():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch177():
    assert _src().count("open(") == 1
