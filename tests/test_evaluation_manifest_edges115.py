"""evaluation/manifest.py 第三百八十五轮 edges 测试（Round 941）。

补强 edges114 未触及的角度（第三百一十七批，probe 实证）。

新角度：
- 盘符相对路径分区：当前盘 "C:foo" 拼进根内（edges114），
  而他盘 "Z:x" resolve 原样 "Z:x" → 位于项目根目录之外
  拒绝（消息 "Z:x → Z:x"）；数字 "盘符" 2:/x 不算绝对
  （非字母）但也解析逃逸被拒（"2:/x → 2:\\x"）
- expected_failures 反斜杠 → 字段名
  expected_failures[f1].path 必须使用正斜杠
- ef 指向不存在文件照常加载（存在性推迟到 runner）；
  ef source_type 缺省 None
- categories 非字符串 [1, 2] → schema 双报
  "1 is not of type 'string'"（2 处）
- document 条目多余键 foo → additionalProperties 拒绝；
  顶层多余键同样拒绝（两层封闭）
- devset_status "complete" 合法加载（enum 另一端）
- expectations 子树原样透传
- forbidden tokens 第四百一十一批
"""

from __future__ import annotations

import inspect
import json

import pytest

from evaluation.manifest import ManifestError, load_manifest
from evaluation.schema import EvalSchemaError

BS = chr(92)


def _mk(root, data):
    (root / "samples").mkdir(exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = root / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


_BASE = {"manifest_version": "1.0", "devset_status": "incomplete",
         "documents": []}


def _entry(i, **kw):
    e = {"doc_id": f"d{i}", "path": "samples/a.pdf",
         "source_type": "pdf"}
    e.update(kw)
    return e


# ---------- 盘符相对分区 ----------

def test_other_drive_relative_rejected_batch139(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mk(tmp_path, dict(
            _BASE, documents=[_entry(1, path="Z:x")])), tmp_path)
    msg = str(ei.value)
    assert msg.startswith("documents[d1].path 解析后位于项目根目录之外")
    assert "Z:x → Z:x" in msg


def test_digit_drive_rejected_batch139(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mk(tmp_path, dict(
            _BASE, documents=[_entry(1, path="2:/x")])), tmp_path)
    msg = str(ei.value)
    assert "解析后位于项目根目录之外" in msg
    assert "2:/x" in msg


# ---------- ef 路径形式 ----------

def test_ef_backslash_rejected_batch139(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_mk(tmp_path, dict(_BASE, expected_failures=[{
            "doc_id": "f1",
            "path": "samples" + BS + "g.pdf",
            "expected_error_code": "E"}])), tmp_path)
    assert str(ei.value).startswith(
        "expected_failures[f1].path 必须使用正斜杠")


def test_ef_nonexistent_loads_batch139(tmp_path):
    m = load_manifest(_mk(tmp_path, dict(_BASE, expected_failures=[{
        "doc_id": "f1", "path": "samples/ghost.pdf",
        "expected_error_code": "E"}])), tmp_path)
    ef = m.expected_failures[0]
    assert ef.resolved_path.name == "ghost.pdf"
    assert ef.source_type is None
    assert ef.expected_error_code == "E"


# ---------- categories 非字符串 ----------

def test_categories_int_rejected_batch139(tmp_path):
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, dict(
            _BASE, documents=[_entry(1, categories=[1, 2])])),
            tmp_path)
    msg = str(ei.value)
    assert "(2 处)" in msg
    assert "1 is not of type 'string'" in msg


# ---------- 两层封闭 ----------

def test_document_entry_extra_key_batch139(tmp_path):
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, dict(
            _BASE, documents=[dict(_entry(1), foo=1)])), tmp_path)
    assert "Additional properties are not allowed ('foo'" \
        in str(ei.value)


def test_top_level_extra_key_batch139(tmp_path):
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_mk(tmp_path, dict(_BASE, extra_top=1)),
                      tmp_path)
    assert "Additional properties are not allowed" in str(ei.value)


# ---------- devset_status complete ----------

def test_devset_status_complete_loads_batch139(tmp_path):
    m = load_manifest(_mk(tmp_path, {
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [_entry(1)]}), tmp_path)
    assert m.devset_status == "complete"


# ---------- expectations 透传 ----------

def test_expectations_passthrough_batch139(tmp_path):
    m = load_manifest(_mk(tmp_path, dict(
        _BASE, documents=[_entry(
            1, expectations={"element_count_by_type": {
                "paragraph": 2}})])), tmp_path)
    assert m.documents[0].expectations == {
        "element_count_by_type": {"paragraph": 2}}


# ---------- 源码补强 ----------

def _src():
    import evaluation.manifest as mm
    return inspect.getsource(mm)


def test_source_key_lines_batch139():
    src = _src()
    assert "if len(path_str) >= 3 and path_str[1] == \":\" and path_str[0].isalpha():" in src
    assert 'f"{field_name} 解析后位于项目根目录之外：{path_str} → {resolved}"' in src
    assert 'expectations=d.get("expectations"),' in src
    assert "source_type=ef.get(\"source_type\")," in src


# ---------- forbidden tokens 第四百一十一批 ----------

def test_source_no_eval_batch139():
    assert "eval(" not in _src()


def test_source_no_exec_batch139():
    assert "exec(" not in _src()


def test_source_no_compile_batch139():
    assert "compile(" not in _src()


def test_source_no_globals_batch139():
    assert "globals(" not in _src()


def test_source_no_locals_batch139():
    assert "locals(" not in _src()


def test_source_no_os_system_batch139():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch139():
    assert "subprocess" not in _src()


def test_source_no_popen_batch139():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch139():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch139():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch139():
    assert "socket" not in _src()


def test_source_no_requests_batch139():
    assert "requests" not in _src()


def test_source_no_urllib_batch139():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch139():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch139():
    assert "yield" not in _src()


def test_source_no_async_await_batch139():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch139():
    assert _src().count("open(") == 1
