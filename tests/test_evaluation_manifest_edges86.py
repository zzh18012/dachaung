"""evaluation/manifest.py 第二百零三轮 edges 测试（Round 738）。

补强 edges83-85 未触及的角度（第一百零三批）。

新角度：
- 校验顺序：C:\\foo 触发"禁止绝对路径"（_is_absolute_like 先于反斜杠）；
  a\\b.pdf 才触发"禁止反斜杠"；UNC \\\\server\\share 走反斜杠分支
  （不以 / 开头、无盘符）
- "." 与 "./a.pdf" 合法（相对路径，解析为根/根下文件）
- project_root 带 /.. 段被 resolve 归一（ROOT/evaluation/.. == ROOT）
- 相对 manifest_path 随 CWD 解析（chdir 后裸文件名可用）
- 不存在文件的消息含已解析绝对路径
- 顶层非对象 JSON：[] 与 '"hello"' 均被 schema 层拦下（EvalSchemaError，
  "is not of type 'object'"）
- DocumentEntry 带 expectations dict 时不可 hash（TypeError），
  expectations None 时可 hash —— frozen dataclass 的 eq=True/hash 语义
- 两次 load 相等但非同一对象（== True、is False）
- forbidden tokens 第二百零八批
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.schema import EvalSchemaError
from evaluation.manifest import (
    DocumentEntry,
    ManifestError,
    _resolve_relative_path,
    load_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def _mf(tmp_path, documents=(), **over) -> Path:
    payload = {"manifest_version": "1.0", "devset_status": "incomplete",
               "documents": list(documents)}
    payload.update(over)
    f = tmp_path / "m.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f


# ---------- 校验顺序 ----------

def test_drive_backslash_absolute_checked_first_batch54():
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("C:\\foo", ROOT, "f")
    assert str(ei.value).startswith("f 必须是相对路径，禁止绝对路径：C:\\foo")


def test_mid_backslash_message_batch54():
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b.pdf", ROOT, "f")
    assert str(ei.value).startswith("f 必须使用正斜杠，禁止反斜杠")


def test_unc_goes_to_backslash_branch_batch54():
    # 不以 / 开头且无盘符 → 不是 absolute-like → 反斜杠分支
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("\\\\server\\share", ROOT, "f")
    assert str(ei.value).startswith("f 必须使用正斜杠，禁止反斜杠")


# ---------- 合法相对路径怪癖 ----------

def test_dot_path_resolves_to_root_batch54():
    assert _resolve_relative_path(".", ROOT, "f") == ROOT


def test_dot_slash_prefix_allowed_batch54():
    assert _resolve_relative_path("./a.pdf", ROOT, "f") == \
        (ROOT / "a.pdf").resolve()


def test_project_root_dotdot_normalized_batch54(tmp_path):
    f = _mf(tmp_path, [{"doc_id": "d1", "path": "a.pdf",
                        "source_type": "pdf"}])
    man = load_manifest(f, project_root=ROOT / "evaluation" / "..")
    assert man.project_root == ROOT
    assert man.documents[0].resolved_path == (ROOT / "a.pdf").resolve()


# ---------- manifest_path 解析 ----------

def test_relative_manifest_path_from_cwd_batch54(tmp_path, monkeypatch):
    f = tmp_path / "rel.json"
    f.write_text(json.dumps({"manifest_version": "1.0",
                             "devset_status": "incomplete",
                             "documents": []}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    man = load_manifest("rel.json", project_root=ROOT)
    assert man.file_count == 0


def test_missing_file_message_contains_absolute_batch54(tmp_path):
    ghost = tmp_path / "ghost.json"
    with pytest.raises(ManifestError) as ei:
        load_manifest(ghost)
    assert str(ei.value) == f"清单文件不存在: {ghost.resolve()}"


# ---------- 顶层非对象 ----------

@pytest.mark.parametrize("payload", ["[]", '"hello"', "42"])
def test_non_object_top_level_rejected_batch54(tmp_path, payload):
    f = tmp_path / "m.json"
    f.write_text(payload, encoding="utf-8")
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(f, project_root=ROOT)
    assert "is not of type 'object'" in str(ei.value)


# ---------- 可哈希性 ----------

def _entry(**over):
    d = dict(doc_id="d", path_str="d.pdf", resolved_path=ROOT / "d.pdf",
             source_type="pdf", sha256=None, categories=(),
             paired_with=None, annotation_file_str=None,
             annotation_resolved=None, expectations=None)
    d.update(over)
    return DocumentEntry(**d)


def test_entry_with_expectations_unhashable_batch54():
    with pytest.raises(TypeError):
        hash(_entry(expectations={"element_count_by_type": {}}))


def test_entry_without_expectations_hashable_batch54():
    assert isinstance(hash(_entry()), int)


# ---------- 重复加载 ----------

def test_two_loads_equal_not_identical_batch54(tmp_path):
    f = _mf(tmp_path, [{"doc_id": "d1", "path": "a.pdf",
                        "source_type": "pdf"}])
    a = load_manifest(f, project_root=ROOT)
    b = load_manifest(f, project_root=ROOT)
    assert a == b
    assert a is not b


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_validate_before_version_check_batch54():
    # schema 校验在版本比对之前（validate 调用出现在 mismatch 判断前）
    src = _src()
    assert src.index('validate(data, "manifest.schema.json")') < \
        src.index("data.get(\"manifest_version\") != MANIFEST_VERSION")


def test_source_frozen_dataclasses_batch54():
    src = _src()
    assert src.count("@dataclass(frozen=True)") == 3


# ---------- forbidden tokens 第二百零八批 ----------

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
