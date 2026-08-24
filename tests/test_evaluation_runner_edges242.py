"""evaluation/runner.py 第六百七十七轮 edges 测试（Round 1356）。

补强 edges241 未触及的角度（第七百二十八批，probe 实证）。

新角度（重复 doc_id / 插入序 / wall 模板）：
- **重复 doc_id 收**
  ——['g1','g1'] 两条
  manifest 条目全部
  处理，per_doc 双
  g1（loader 不去
  重也不拒）
- **同 id 可区分**
  ——ect [{paragraph:
  1},{paragraph:2}]
  靠 metrics 分辨
- **expectations
  不对称**——第一条
  no_expectations、
  第二条 sdc 0 →
  sdt 0（None 不参
  与但 0 参与）
- **插入序保持**
  ——[zzz,aaa] →
  per_doc [zzz,aaa]
  （非字典序）
- **wall 模板**
  ——{total>0,
  parse None,chunk
  None,双 reason
  not_instrumented}
- forbidden tokens 第七百九十六批（open 2）
"""

from __future__ import annotations

import inspect

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


def _docx(path, *texts):
    from docx import Document
    d = Document()
    for t in texts:
        d.add_paragraph(t)
    d.save(str(path))


def _mf(tmp_path, docs):
    import json
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    from evaluation.manifest import load_manifest
    return load_manifest(tmp_path / "m.json",
                         project_root=tmp_path)


def _dup(tmp_path):
    _docx(tmp_path / "a.docx", "one")
    _docx(tmp_path / "b.docx", "two", "two2")
    return run_evaluation(
        _mf(tmp_path, [
            {"doc_id": "g1", "path": "a.docx",
             "source_type": "docx"},
            {"doc_id": "g1", "path": "b.docx",
             "source_type": "docx",
             "expectations": {
                 "element_count_by_type": {
                     "paragraph": 2}}}]),
        tmp_path / "r.json",
        parser_name="fallback", max_chars=800)


# ---------- 重复 doc_id 收 ----------

def test_dup_docid_both_processed_batch554(tmp_path):
    r = _dup(tmp_path)
    assert [p["doc_id"] for p in r["per_doc"]] == \
        ["g1", "g1"]


def test_dup_docid_success_two_batch554(tmp_path):
    r = _dup(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 2, "total": 2, "rate": 1.0}


def test_dup_docid_file_count_two_batch554(tmp_path):
    assert _dup(tmp_path)["devset"]["file_count"] == 2


def test_dup_docid_docx_two_batch554(tmp_path):
    assert _dup(tmp_path)["devset"]["docx_count"] == 2


# ---------- 同 id 可区分 ----------

def test_dup_distinguish_by_ect_batch554(tmp_path):
    r = _dup(tmp_path)
    vals = [p["metrics"]["element_count_by_type"][
        "value"] for p in r["per_doc"]]
    assert vals == [{"paragraph": 1}, {"paragraph": 2}]


def test_dup_tpe_both_one_batch554(tmp_path):
    r = _dup(tmp_path)
    for p in r["per_doc"]:
        assert p["metrics"][
            "text_preservation_equal"] == {
            "value": True, "reason": None}


# ---------- expectations 不对称 ----------

def test_dup_sdc_asymmetric_batch554(tmp_path):
    r = _dup(tmp_path)
    assert [p["metrics"]["silent_drop_count"]
            for p in r["per_doc"]] == [
        {"value": None, "reason": "no_expectations"},
        {"value": 0, "reason": None}]


def test_dup_sdt_zero_batch554(tmp_path):
    assert _dup(tmp_path)["summary"][
        "silent_drop_total"] == 0


def test_dup_sdt_participating_one_batch554(
        tmp_path):
    r = _dup(tmp_path)
    vals = [p["metrics"]["silent_drop_count"][
        "value"] for p in r["per_doc"]]
    assert r["summary"]["silent_drop_total"] == \
        sum(v for v in vals if v is not None)


# ---------- 插入序保持 ----------

def test_insertion_order_preserved_batch554(
        tmp_path):
    _docx(tmp_path / "a.docx", "one")
    _docx(tmp_path / "b.docx", "two")
    r = run_evaluation(
        _mf(tmp_path, [
            {"doc_id": "zzz", "path": "b.docx",
             "source_type": "docx"},
            {"doc_id": "aaa", "path": "a.docx",
             "source_type": "docx"}]),
        tmp_path / "r.json",
        parser_name="fallback", max_chars=800)
    assert [p["doc_id"] for p in r["per_doc"]] == \
        ["zzz", "aaa"]


def test_order_not_alphabetical_batch554(
        tmp_path):
    _docx(tmp_path / "a.docx", "one")
    _docx(tmp_path / "b.docx", "two")
    r = run_evaluation(
        _mf(tmp_path, [
            {"doc_id": "zzz", "path": "b.docx",
             "source_type": "docx"},
            {"doc_id": "aaa", "path": "a.docx",
             "source_type": "docx"}]),
        tmp_path / "r.json",
        parser_name="fallback", max_chars=800)
    ids = [p["doc_id"] for p in r["per_doc"]]
    assert ids != sorted(ids)


def test_order_swapped_flips_first_batch554(
        tmp_path):
    _docx(tmp_path / "a.docx", "one")
    _docx(tmp_path / "b.docx", "two")
    r = run_evaluation(
        _mf(tmp_path, [
            {"doc_id": "aaa", "path": "a.docx",
             "source_type": "docx"},
            {"doc_id": "zzz", "path": "b.docx",
             "source_type": "docx"}]),
        tmp_path / "r.json",
        parser_name="fallback", max_chars=800)
    assert r["per_doc"][0]["doc_id"] == "aaa"


# ---------- wall 模板 ----------

def test_wall_exact_template_batch554(tmp_path):
    r = _dup(tmp_path)
    for p in r["per_doc"]:
        w = p["wall_time_seconds"]
        assert sorted(w.keys()) == [
            "chunk", "chunk_reason", "parse",
            "parse_reason", "total"]
        assert w["parse"] is None
        assert w["chunk"] is None
        assert w["parse_reason"] == \
            "not_instrumented"
        assert w["chunk_reason"] == \
            "not_instrumented"


def test_wall_total_positive_batch554(tmp_path):
    r = _dup(tmp_path)
    for p in r["per_doc"]:
        t = p["wall_time_seconds"]["total"]
        assert isinstance(t, float)
        assert t > 0


def test_wall_full_dict_equality_batch554(
        tmp_path):
    r = _dup(tmp_path)
    for p in r["per_doc"]:
        w = p["wall_time_seconds"]
        assert w == {
            "total": w["total"], "parse": None,
            "chunk": None,
            "parse_reason": "not_instrumented",
            "chunk_reason": "not_instrumented"}


# ---------- per_doc 公共面 ----------

def test_per_doc_public_keys_batch554(tmp_path):
    r = _dup(tmp_path)
    for p in r["per_doc"]:
        assert sorted(p.keys()) == [
            "doc_id", "metrics", "source_type",
            "wall_time_seconds"]


def test_per_doc_source_type_docx_batch554(
        tmp_path):
    r = _dup(tmp_path)
    assert [p["source_type"] for p in
            r["per_doc"]] == ["docx", "docx"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_public_whitelist_batch554():
    src = _src()
    assert "public_per_doc" in src
    assert '"wall_time_seconds": r[' \
        '"wall_time_seconds"]' in src


def test_source_private_keys_batch554():
    src = _src()
    assert '"_annotation_present"' in src
    assert '"_tolerance_chars"' in src
    assert '"_missing_markers"' in src


def test_source_pop_lines_batch554():
    src = _src()
    assert 'chunk_b.pop("_tolerance_chars", ' \
        'None)' in src
    assert 'chunk_b.pop("_missing_markers", ' \
        'None)' in src


def test_source_image_gate_batch554():
    assert "image_dir.is_dir()" in _src()


def test_source_run_eval_count_batch554():
    assert _src().count("def run_evaluation") == 1


def test_source_open_count_batch554():
    assert _src().count("open(") == 2


# ---------- forbidden tokens 第七百九十六批 ----------

def test_source_no_eval_batch554():
    assert "eval(" not in _src()


def test_source_no_exec_batch554():
    assert "exec(" not in _src()


def test_source_no_compile_batch554():
    assert "compile(" not in _src()


def test_source_no_globals_batch554():
    assert "globals(" not in _src()


def test_source_no_locals_batch554():
    assert "locals(" not in _src()


def test_source_no_os_system_batch554():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch554():
    assert "subprocess" not in _src()


def test_source_no_popen_batch554():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch554():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch554():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch554():
    assert "socket" not in _src()


def test_source_no_requests_batch554():
    assert "requests" not in _src()


def test_source_no_urllib_batch554():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch554():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch554():
    assert "yield" not in _src()


def test_source_no_async_await_batch554():
    assert "async " not in _src()
    assert "await " not in _src()
