"""evaluation/metrics.py 第四百二十六轮 edges 测试（Round 982）。

补强 edges117 未触及的角度（第三百五十八批，probe 实证）。

新角度：
- header/footer 不在 _PDF_BBOX_REQUIRED_TYPES → 仅 page 即
  有效（bbox 豁免家族补全）
- page 传 float 1.0 → isinstance(int) 拒绝 → 0.0（与
  bool True 绕过形成对照：bool 过、float 不过）
- docx locator 含 bbox 键即拒（即使 section 结构键也在）
- chunk source_element_ids 空列表 → falsy 不算有效 → 2 取 1
  = 0.5
- heading element_id 缺失（None）与 chunk 首 id None 相等
  命中 → heading_boundary_compliance 1.0（None==None 怪癖）
- 图片 resource_path 仅文件名 + image_base_dir 拼接命中；
  零字节文件 st_size>0 拒 → 混合 0.5
- forbidden tokens 第四百五十二批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


# ---------- header/footer bbox 豁免 ----------

def test_header_footer_bbox_exempt_batch180():
    doc = {"elements": [
        {"type": "header", "content": "H",
         "source_locator": {"page": 1}},
        {"type": "footer", "content": "F",
         "source_locator": {"page": 2}}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 1.0,
                                              "reason": None}


# ---------- float page 拒绝 ----------

def test_float_page_rejected_batch180():
    doc = {"elements": [
        {"type": "header", "content": "H",
         "source_locator": {"page": 1.0}}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"] == {"value": 0.0,
                                              "reason": None}


# ---------- docx bbox 键拒绝 ----------

def test_docx_bbox_key_rejected_batch180():
    doc = {"elements": [
        {"type": "paragraph", "content": "A",
         "source_locator": {"bbox": [0, 0, 1, 1],
                            "section": 1}}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"] == {"value": 0.0,
                                               "reason": None}


# ---------- chunk 空 ids ----------

def test_chunk_empty_ids_half_batch180():
    doc = {"elements": [{"type": "paragraph", "content": "AB",
                         "element_id": "e1"}],
           "chunks": [{"source_element_ids": ["e1"]},
                      {"source_element_ids": []}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"] == {"value": 0.5,
                                                   "reason": None}


# ---------- heading None id 匹配 ----------

def test_heading_none_id_matches_chunk_none_batch180():
    doc = {"elements": [{"type": "heading", "content": "H"}],
           "chunks": [{"text": "H",
                       "source_element_ids": [None]}]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"] == {"value": 1.0,
                                                  "reason": None}


# ---------- 图片 base_dir 拼接 + 零字节 ----------

def test_image_base_dir_join_and_zero_byte_batch180(tmp_path):
    (tmp_path / "img.png").write_bytes(b"data")
    (tmp_path / "empty.png").write_bytes(b"")
    doc = {"elements": [
        {"type": "image", "resource_path": "img.png"},
        {"type": "image", "resource_path": "empty.png"}],
        "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None,
                                    image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"] == {"value": 0.5,
                                                  "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch180():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src
    assert "if p.is_file() and p.stat().st_size > 0:" in src
    assert "chunk_first_ids.add(ids[0])" in src


# ---------- forbidden tokens 第四百五十二批 ----------

def test_source_no_eval_batch180():
    assert "eval(" not in _src()


def test_source_no_exec_batch180():
    assert "exec(" not in _src()


def test_source_no_compile_batch180():
    assert "compile(" not in _src()


def test_source_no_globals_batch180():
    assert "globals(" not in _src()


def test_source_no_locals_batch180():
    assert "locals(" not in _src()


def test_source_no_os_system_batch180():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch180():
    assert "subprocess" not in _src()


def test_source_no_popen_batch180():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch180():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch180():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch180():
    assert "socket" not in _src()


def test_source_no_requests_batch180():
    assert "requests" not in _src()


def test_source_no_urllib_batch180():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch180():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch180():
    assert "yield" not in _src()


def test_source_no_async_await_batch180():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch180():
    assert "open(" not in _src()
