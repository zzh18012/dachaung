"""evaluation/metrics.py 第四百五十四轮 edges 测试（Round 1010）。

补强 edges121 未触及的角度（第三百八十六批，probe 实证）。

新角度：
- header 带坏 bbox（"bad"）→ pdf_locator 仍 1.0（豁免类型
  完全不看 bbox）；caption 只给 page 无 bbox → 0.0
  （强制类型）——同款 locator 两种命运
- resource_path 带子目录 "sub/img.png" 而文件只在
  base/img.png → basename 回退拼接命中 → 1.0
  （Path(rp).name 丢目录）
- docx 结构键单键即有效：relationship_id / run_index /
  table_index+row+col 三连各 1.0
- forbidden tokens 第四百八十批（open 0）
"""

from __future__ import annotations

import inspect

from evaluation.metrics import compute_automatic_metrics


# ---------- 豁免 vs 强制 bbox ----------

def test_header_bad_bbox_vs_caption_no_bbox_batch208():
    m1 = compute_automatic_metrics(
        {"elements": [
            {"type": "header", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": "bad"}}]},
        None, "pdf", None)
    assert m1["pdf_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}

    m2 = compute_automatic_metrics(
        {"elements": [
            {"type": "caption", "element_id": "c1",
             "source_locator": {"page": 1}}]},
        None, "pdf", None)
    assert m2["pdf_locator_valid_ratio"] == {"value": 0.0,
                                             "reason": None}


# ---------- 子目录 rp 的 basename 回退 ----------

def test_subdir_rp_basename_fallback_batch208(tmp_path):
    base = tmp_path / "imgs"
    base.mkdir()
    (base / "img.png").write_bytes(b"real")
    m = compute_automatic_metrics(
        {"elements": [
            {"type": "image", "resource_path": "sub/img.png",
             "element_id": "i1"}]},
        None, "pdf", None, base)
    assert m["image_resource_exists_ratio"] == {"value": 1.0,
                                                "reason": None}


# ---------- docx 单结构键 ----------

def test_relationship_id_alone_valid_batch208():
    m = compute_automatic_metrics(
        {"elements": [
            {"type": "paragraph", "element_id": "p1",
             "source_locator": {"relationship_id": "rId7"}}]},
        None, "docx", None)
    assert m["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}


def test_run_index_alone_valid_batch208():
    m = compute_automatic_metrics(
        {"elements": [
            {"type": "paragraph", "element_id": "p1",
             "source_locator": {"run_index": 2}}]},
        None, "docx", None)
    assert m["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}


def test_table_trio_valid_batch208():
    m = compute_automatic_metrics(
        {"elements": [
            {"type": "table", "element_id": "t1",
             "source_locator": {"table_index": 0,
                                "row_index": 1,
                                "col_index": 2}}]},
        None, "docx", None)
    assert m["docx_locator_valid_ratio"] == {"value": 1.0,
                                             "reason": None}


# ---------- 源码补强 ----------

def _src():
    import evaluation.metrics as m
    return inspect.getsource(m)


def test_source_key_lines_batch208():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src
    assert '"relationship_id",' in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src
    assert "if not any(k in loc for k in structural_keys):" in src


# ---------- forbidden tokens 第四百八十批 ----------

def test_source_no_eval_batch208():
    assert "eval(" not in _src()


def test_source_no_exec_batch208():
    assert "exec(" not in _src()


def test_source_no_compile_batch208():
    assert "compile(" not in _src()


def test_source_no_globals_batch208():
    assert "globals(" not in _src()


def test_source_no_locals_batch208():
    assert "locals(" not in _src()


def test_source_no_os_system_batch208():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch208():
    assert "subprocess" not in _src()


def test_source_no_popen_batch208():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch208():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch208():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch208():
    assert "socket" not in _src()


def test_source_no_requests_batch208():
    assert "requests" not in _src()


def test_source_no_urllib_batch208():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch208():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch208():
    assert "yield" not in _src()


def test_source_no_async_await_batch208():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch208():
    assert "open(" not in _src()
