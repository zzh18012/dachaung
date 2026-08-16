"""evaluation/manifest.py 第二百零二轮 edges 测试（Round 731）。

补强 edges81-84 未触及的角度（第九十六批）。

新角度：
- MANIFEST_VERSION 值锁 "1.0"；monkeypatch 后不兼容分支可达 +
  消息精确 "manifest_version 不兼容：清单=1.0，代码=9.9"
- BOM 清单 → ManifestError（json 的 "Unexpected UTF-8 BOM" 消息）
- 死变量现状记录：all_paired 赋值+.add 共 2 处、从未被读
- schema 层不查 doc_id 唯一：重复 doc_id 双份都加载
- loader 不 stat：ghost 深层路径照常解析
- _is_absolute_like 补角：数字盘符 "1:/x" False、"a:" 长度 2 False、
  "a:x" 冒号后无斜杠 False、"a//b" False、"/" True、"Z:\\f" True
- 逃逸错误字段名：expected_failures[ef1].path / documents[d1].annotation_file
- 空文档直接构造 Manifest：全 0 + categories []
- self-pair（frozenset 单元素）1 组；ghost 配对目标不存在 → 2 组
- source_type txt：pdf/docx 均 0 但 file_count 1
- 三个 dataclass frozen → FrozenInstanceError
- _detect_project_root(文件) → 仓库根
- forbidden tokens 第二百零一批
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation import MANIFEST_VERSION
from evaluation.manifest import (
    DocumentEntry,
    Manifest,
    ManifestError,
    _detect_project_root,
    _is_absolute_like,
    load_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def _mf(tmp_path, documents, **over) -> Path:
    payload = {"manifest_version": "1.0", "devset_status": "incomplete",
               "documents": documents}
    payload.update(over)
    f = tmp_path / "m.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


def _entry(i, st="pdf", pw=None, cats=()):
    return DocumentEntry(
        doc_id=i, path_str=f"{i}.pdf", resolved_path=ROOT / f"{i}.pdf",
        source_type=st, sha256=None, categories=cats, paired_with=pw,
        annotation_file_str=None, annotation_resolved=None, expectations=None)


# ---------- 版本 ----------

def test_manifest_version_locked_batch54():
    assert MANIFEST_VERSION == "1.0"


def test_version_mismatch_branch_and_message_batch54(tmp_path, monkeypatch):
    # schema const 锁 "1.0"，该分支仅在代码侧 MANIFEST_VERSION 漂移时可达
    monkeypatch.setattr(manifest_mod, "MANIFEST_VERSION", "9.9")
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mf(tmp_path, []), project_root=ROOT)
    assert str(ei.value) == "manifest_version 不兼容：清单=1.0，代码=9.9"


# ---------- BOM ----------

def test_bom_manifest_raises_batch54(tmp_path):
    f = tmp_path / "bom.json"
    f.write_bytes(b'\xef\xbb\xbf{"manifest_version":"1.0",'
                  b'"devset_status":"incomplete","documents":[]}')
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, project_root=ROOT)
    assert "Unexpected UTF-8 BOM" in str(ei.value)
    assert str(ei.value).startswith("清单 JSON 解析失败")


# ---------- 死变量现状记录 ----------

def test_all_paired_dead_variable_batch54():
    src = inspect.getsource(manifest_mod)
    assert src.count("all_paired") == 2  # 赋值 + .add，从未被读（现状）


# ---------- schema 层不查唯一性 / 不 stat ----------

def test_duplicate_doc_id_both_loaded_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        {"doc_id": "d1", "path": "b.pdf", "source_type": "docx"},
    ]), project_root=ROOT)
    assert man.file_count == 2
    assert [d.doc_id for d in man.documents] == ["d1", "d1"]


def test_ghost_deep_path_resolves_without_stat_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": "d1", "path": "ghost/deep/x.pdf", "source_type": "pdf"},
    ]), project_root=ROOT)
    assert man.documents[0].resolved_path == \
        (ROOT / "ghost/deep/x.pdf").resolve()


def test_expected_failures_absent_empty_tuple_batch54(tmp_path):
    man = load_manifest(_mf(tmp_path, [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
    ]), project_root=ROOT)
    assert man.expected_failures == ()


# ---------- _is_absolute_like 补角 ----------

@pytest.mark.parametrize("s,expected", [
    ("1:/x", False),    # 数字不是盘符
    ("a:", False),      # 长度 2 < 3
    ("a:x", False),     # 冒号后无斜杠
    ("a//b", False),    # 双正斜杠中段不算绝对
    ("/", True),
    ("//server", True),
    ("Z:\\f", True),    # 大写盘符反斜杠
])
def test_is_absolute_like_corner_matrix_batch54(s, expected):
    assert _is_absolute_like(s) is expected


# ---------- 逃逸错误字段名 ----------

def test_expected_failure_escape_field_name_batch54(tmp_path):
    f = _mf(tmp_path, [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
    ], expected_failures=[
        {"doc_id": "ef1", "path": "../escape.pdf",
         "expected_error_code": "open_error"},
    ])
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, project_root=ROOT)
    assert str(ei.value).startswith(
        "expected_failures[ef1].path 解析后位于项目根目录之外")


def test_annotation_escape_field_name_batch54(tmp_path):
    f = _mf(tmp_path, [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "annotation_file": "../ann.json"},
    ])
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, project_root=ROOT)
    assert str(ei.value).startswith(
        "documents[d1].annotation_file 解析后位于项目根目录之外")


# ---------- 直接构造 Manifest ----------

def test_zero_document_manifest_properties_batch54():
    man = Manifest("1.0", "incomplete", (), (), ROOT)
    assert man.file_count == 0
    assert man.pdf_count == 0
    assert man.docx_count == 0
    assert man.content_group_count == 0
    assert man.categories_covered == []


def test_self_pair_singleton_frozenset_one_group_batch54():
    man = Manifest("1.0", "incomplete", (_entry("a", pw="a"),), (), ROOT)
    assert man.content_group_count == 1


def test_ghost_pair_target_two_groups_batch54():
    # a→zzz（目标不存在）算 1 组；b 未配对算 1 组 → 2
    man = Manifest("1.0", "incomplete",
                   (_entry("a", pw="zzz"), _entry("b")), (), ROOT)
    assert man.content_group_count == 2


def test_txt_source_type_neither_pdf_nor_docx_batch54():
    man = Manifest("1.0", "incomplete", (_entry("a", st="txt"),), (), ROOT)
    assert (man.file_count, man.pdf_count, man.docx_count) == (1, 0, 0)


def test_categories_covered_sorted_dedup_batch54():
    man = Manifest("1.0", "incomplete",
                   (_entry("a", cats=("c", "b")),
                    _entry("b", cats=("a", "b"))), (), ROOT)
    assert man.categories_covered == ["a", "b", "c"]


# ---------- frozen ----------

def test_manifest_frozen_batch54():
    man = Manifest("1.0", "incomplete", (), (), ROOT)
    with pytest.raises(dataclasses.FrozenInstanceError):
        man.devset_status = "x"


def test_document_entry_frozen_batch54():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _entry("a").doc_id = "x"


# ---------- 根探测 ----------

def test_detect_project_root_from_file_batch54():
    assert _detect_project_root(
        Path("evaluation/manifest.py").resolve()) == ROOT


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_docstring_invariants_batch54():
    src = _src()
    assert "不把本机绝对路径写入 manifest 或报告" in src
    assert "../../../etc/passwd" in src


def test_source_version_compare_batch54():
    src = _src()
    assert "data.get(\"manifest_version\") != MANIFEST_VERSION" in src


# ---------- forbidden tokens 第二百零一批 ----------

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


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
