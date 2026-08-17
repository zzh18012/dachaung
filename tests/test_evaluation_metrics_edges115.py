"""evaluation/metrics.py 第四百零五轮 edges 测试（Round 961）。

补强 edges114 未触及的角度（第三百三十七批，probe 实证）。

新角度：
- bbox 负浮点合法：[-1.5, -2.0, 0.0, 3.3] 无下限检查 →
  1.0
- bbox tuple 不合法：isinstance(, list) 拒元组 → 0.0
- image rp 空串 "" 与缺 resource_path 键 → 都走
  `if not rp: continue` → 0.0
- 混合图片 1 真 1 ghost → 0.5
- 全角空格 U+3000 是 isspace() → 从 content 剥掉：
  content "A\\u3000B" vs chunk "AB" → equal True
- forbidden tokens 第四百三十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _run(doc, st="pdf", base=None):
    return compute_automatic_metrics(doc, None, st, None,
                                     image_base_dir=base)


# ---------- bbox 负值合法 ----------

def test_negative_bbox_valid_batch159():
    doc = {"elements": [
        {"type": "paragraph", "content": "A",
         "source_locator": {
             "page": 1,
             "bbox": [-1.5, -2.0, 0.0, 3.3]}}],
        "chunks": []}
    assert _run(doc)["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- bbox tuple 拒绝 ----------

def test_tuple_bbox_invalid_batch159():
    doc = {"elements": [
        {"type": "paragraph", "content": "A",
         "source_locator": {"page": 1,
                            "bbox": (0, 0, 1, 1)}}],
        "chunks": []}
    assert _run(doc)["pdf_locator_valid_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- rp 空串 / 缺键 ----------

def test_rp_empty_and_missing_batch159():
    doc = {"elements": [
        {"type": "image", "resource_path": ""},
        {"type": "image"}], "chunks": []}
    assert _run(doc)["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


# ---------- 混合图片 ----------

def test_mixed_images_half_batch159(tmp_path):
    (tmp_path / "img.png").write_bytes(b"data")
    doc = {"elements": [
        {"type": "image",
         "resource_path": str(tmp_path / "img.png")},
        {"type": "image", "resource_path": "ghost.png"}],
        "chunks": []}
    assert _run(doc, base=tmp_path)[
        "image_resource_exists_ratio"] == {
        "value": 0.5, "reason": None}


# ---------- 全角空格剥离 ----------

def test_ideographic_space_stripped_batch159():
    ideographic = chr(0x3000)
    doc = {"elements": [
        {"type": "paragraph",
         "content": "A" + ideographic + "B"}],
        "chunks": [{"text": "AB"}]}
    m = _run(doc)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"]["value"] == 1.0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch159():
    src = _src()
    assert 'if not isinstance(bbox, list) or len(bbox) != 4:' in src
    assert "if isinstance(v, bool):" in src
    assert "if not math.isfinite(v):" in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src


# ---------- forbidden tokens 第四百三十一批 ----------

def test_source_no_eval_batch159():
    assert "eval(" not in _src()


def test_source_no_exec_batch159():
    assert "exec(" not in _src()


def test_source_no_compile_batch159():
    assert "compile(" not in _src()


def test_source_no_globals_batch159():
    assert "globals(" not in _src()


def test_source_no_locals_batch159():
    assert "locals(" not in _src()


def test_source_no_os_system_batch159():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch159():
    assert "subprocess" not in _src()


def test_source_no_popen_batch159():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch159():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch159():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch159():
    assert "socket" not in _src()


def test_source_no_requests_batch159():
    assert "requests" not in _src()


def test_source_no_urllib_batch159():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch159():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch159():
    assert "yield" not in _src()


def test_source_no_async_await_batch159():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch159():
    assert "open(" not in _src()
