"""evaluation/manifest.py 第五百四十五轮 edges 测试（Round 1101）。

补强 edges134-136 未触及的角度（第四百七十七批，probe 实证）。

新角度（dotdot 内敛 / 声明失配照跑 / 大写十六进制 /
无根落 CWD）：
- **dotdot 内敛照收**：path "sub/../samples/g.docx"
  → 接受——path_str 逐字保留 dotdot、resolved_path
  归一化到 root/samples/g.docx——"解析后位于根内"
  判定看 resolve() 终点，不看字符串形状（edges101
  只锁了 "./" 前缀的 verbatim）
- **声明失配照跑**：source_type 声明 "pdf"、文件
  实为真 docx → 真实 run success True + pdf_locator
  0.0——声明型 gate 只影响度量，不拦截解析
  （与 R1100 metrics 门控互为印证）
- **大写十六进制 sha256 拒绝**："A"*64 → "does not
  match '^[0-9a-f]{64}$'"——长度对但大小写错，
  regex 显式小写（短哈希拒绝已锁，本变体是新面）
- **无 project_root 落 CWD**：load_manifest 不传
  project_root → 相对路径以 CWD 为根解析
  （monkeypatch.chdir 后 resolved 即 CWD 下）
- forbidden tokens 第五百七十二批（open 1）
"""

from __future__ import annotations

import inspect
import json

from docx import Document

import evaluation.manifest as manifest_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _manifest(tmp_path, documents, ef=None):
    m = {"manifest_version": "1.0",
         "devset_status": "incomplete",
         "documents": documents}
    if ef is not None:
        m["expected_failures"] = ef
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(m), encoding="utf-8")
    return mf


# ---------- dotdot 内敛照收 ----------

def test_dotdot_inside_accepted_batch300(tmp_path):
    (tmp_path / "samples").mkdir(parents=True,
                                 exist_ok=True)
    mf = _manifest(tmp_path, [
        {"doc_id": "d1",
         "path": "sub/../samples/g.docx",
         "source_type": "docx"}])
    man = load_manifest(mf, project_root=tmp_path)
    d = man.documents[0]
    assert d.path_str == "sub/../samples/g.docx"
    assert d.resolved_path == (
        tmp_path / "samples" / "g.docx").resolve()


# ---------- 声明失配照跑 ----------

def test_declared_type_mismatch_runs_batch300(tmp_path):
    (tmp_path / "samples").mkdir(parents=True,
                                 exist_ok=True)
    doc = Document()
    doc.add_paragraph("AAA body text here.")
    doc.save(str(tmp_path / "samples" / "real.docx"))
    mf = _manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/real.docx",
         "source_type": "pdf"}])
    man = load_manifest(mf, project_root=tmp_path)
    rep = run_evaluation(
        man, tmp_path / "r.json",
        parser_name="fallback", max_chars=200)
    mts = rep["per_doc"][0]["metrics"]
    assert mts["pipeline_success"] == {
        "value": True, "reason": None}
    assert mts["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- 大写十六进制 sha256 拒绝 ----------

def test_uppercase_sha256_rejected_batch300(tmp_path):
    (tmp_path / "samples").mkdir(parents=True,
                                 exist_ok=True)
    mf = _manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/g.docx",
         "source_type": "docx",
         "sha256": "A" * 64}])
    try:
        load_manifest(mf, project_root=tmp_path)
        raised = False
    except Exception as e:
        raised = True
        frag = ("does not match "
                "'^[0-9a-f]{64}$'")
        assert frag in str(e)
    assert raised


# ---------- 无 project_root 落 CWD ----------

def test_cwd_default_root_batch300(tmp_path,
                                   monkeypatch):
    (tmp_path / "samples").mkdir(parents=True,
                                 exist_ok=True)
    mf = _manifest(tmp_path, [
        {"doc_id": "d1", "path": "samples/g.docx",
         "source_type": "docx"}])
    monkeypatch.chdir(tmp_path)
    man = load_manifest(mf)
    assert man.documents[0].resolved_path == (
        tmp_path / "samples" / "g.docx").resolve()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(manifest_mod)


def test_source_key_lines_batch300():
    src = _src()
    assert ("resolved.relative_to("
            "project_root_resolved)") in src
    assert ("project_root_resolved = "
            "project_root.resolve()") in src


# ---------- forbidden tokens 第五百七十二批 ----------

def test_source_no_eval_batch300():
    assert "eval(" not in _src()


def test_source_no_exec_batch300():
    assert "exec(" not in _src()


def test_source_no_compile_batch300():
    assert "compile(" not in _src()


def test_source_no_globals_batch300():
    assert "globals(" not in _src()


def test_source_no_locals_batch300():
    assert "locals(" not in _src()


def test_source_no_os_system_batch300():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch300():
    assert "subprocess" not in _src()


def test_source_no_popen_batch300():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch300():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch300():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch300():
    assert "socket" not in _src()


def test_source_no_requests_batch300():
    assert "requests" not in _src()


def test_source_no_urllib_batch300():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch300():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch300():
    assert "yield" not in _src()


def test_source_no_async_await_batch300():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch300():
    assert _src().count("open(") == 1
