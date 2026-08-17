"""evaluation/cli.py 第三百一十一轮 edges 测试（Round 867）。

补强 edges103 未触及的角度（第二百四十二批，probe 实证）。

新角度：
- 全真实链路 roundtrip：run_evaluation（仅 process_single 打桩）
  产出报告 → validate-report 真实 Schema 校验 → rc0 [OK]
- 篡改 expected_failures 条目（缺 required 字段）→ rc1 [FAIL]
- inspect-doc --tolerance-chars 0 → "0  (ok)" 行
- 源码：stdout reconfigure utf-8 块存在
- forbidden tokens 第三百三十七批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.cli as cli_mod
import evaluation.runner as runner_mod
from evaluation.cli import main
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    def __init__(self, d):
        self._d = d
        self.parser_version = "7.7"
        self.source_hash = "deadbeef"

    def to_dict(self):
        return self._d


_DOC_DICT = {
    "elements": [{"element_id": "e1", "type": "paragraph",
                  "content": "AB"}],
    "chunks": [{"text": "AB", "source_element_ids": ["e1"]}],
}


def _real_report(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    m = load_manifest(mf, root)
    out = tmp_path / "r.json"
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])):
        report = run_evaluation(m, out)
    return out, report


# ---------- 全真实 roundtrip ----------

def test_full_roundtrip_report_validates_batch65(tmp_path, capsys):
    out, report = _real_report(tmp_path)
    assert report["provenance"]["git_dirty"] in (True, False)
    rc = main(["validate-report", str(out)])
    o = capsys.readouterr()
    assert rc == 0
    assert "[OK]" in o.out
    assert "通过 evaluation-report Schema 校验" in o.out


# ---------- 篡改 ef 条目 ----------

def test_validate_report_tampered_ef_rc1_batch65(tmp_path, capsys):
    out, _ = _real_report(tmp_path)
    data = json.loads(out.read_text(encoding="utf-8"))
    data["expected_failures"].append({"doc_id": "f1"})
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data), encoding="utf-8")
    rc = main(["validate-report", str(bad)])
    e = capsys.readouterr().err
    assert rc == 1
    assert "[FAIL]" in e
    assert "required property" in e


# ---------- tolerance 0 ----------

def test_inspect_tolerance_zero_line_batch65(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "paragraph",
                      "content": "A"}],
        "chunks": [{"text": "A",
                    "source_element_ids": ["e1"]}]}),
        encoding="utf-8")
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "0"])
    out = capsys.readouterr().out
    assert rc == 0
    assert f"  {'_tolerance_chars':36} 0  (ok)" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch65():
    src = _src()
    assert 'sys.stdout.reconfigure(encoding="utf-8", errors="replace")' in src
    assert 'sys.stderr.reconfigure(encoding="utf-8", errors="replace")' in src
    assert 'if hasattr(sys.stdout, "reconfigure"):' in src


# ---------- forbidden tokens 第三百三十七批 ----------

def test_source_no_eval_batch65():
    assert "eval(" not in _src()


def test_source_no_exec_batch65():
    assert "exec(" not in _src()


def test_source_no_compile_batch65():
    assert "compile(" not in _src()


def test_source_no_globals_batch65():
    assert "globals(" not in _src()


def test_source_no_locals_batch65():
    assert "locals(" not in _src()


def test_source_no_os_system_batch65():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch65():
    assert "subprocess" not in _src()


def test_source_no_popen_batch65():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch65():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch65():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch65():
    assert "socket" not in _src()


def test_source_no_requests_batch65():
    assert "requests" not in _src()


def test_source_no_urllib_batch65():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch65():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch65():
    assert "yield" not in _src()


def test_source_no_async_await_batch65():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch65():
    assert _src().count("open(") == 1
