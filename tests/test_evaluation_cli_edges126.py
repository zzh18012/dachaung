"""evaluation/cli.py 第四百六十五轮 edges 测试（Round 1021）。

补强 edges125 未触及的角度（第三百九十七批，probe 实证）。

新角度（绝对 resource_path 回合）：
- inspect-doc：image resource_path 一条绝对路径指向真实
  文件 + 一条相对路径不存在 → image_resource 0.5000
  渲染（inspect 无 image_base_dir，全靠 rp 原值；
  绝对路径是唯一能让该比率 >0 的途径）
- 单条绝对路径指向不存在文件 → 0.0000（有 image 元素
  但全失效 ≠ no_image_elements null——两态同屏可辨）
- forbidden tokens 第四百九十一批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _img_elem(eid, rp):
    return {"element_id": eid, "type": "image",
            "resource_path": rp, "parent_id": None,
            "confidence": 0.9, "metadata": {},
            "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}


def _write_doc(tmp_path, elements):
    doc = {"schema_version": "0.1.0", "document_id": "d",
           "source_type": "pdf", "source_path": "a.pdf",
           "parser_name": "fallback", "parser_version": "1",
           "elements": elements, "chunks": [], "relations": [],
           "warnings": [], "errors": [], "metadata": {}}
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    return f


# ---------- 绝对真实 + 相对缺失 → 0.5 ----------

def test_absolute_rp_half_ratio_batch219(tmp_path, capsys):
    real = tmp_path / "photo.png"
    real.write_bytes(b"pngdata")
    f = _write_doc(tmp_path, [
        _img_elem("i1", str(real)),
        _img_elem("i2", "rel/missing.png")])
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert ("  image_resource_exists_ratio          "
            "0.5000  (ok)") in out
    assert "counts:      elements=2 chunks=0" in out


# ---------- 绝对缺失 → 0.0 非 null ----------

def test_absolute_rp_missing_zero_batch219(tmp_path, capsys):
    f = _write_doc(tmp_path, [
        _img_elem("i1", str(tmp_path / "nope.png"))])
    rc = main(["inspect-doc", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert ("  image_resource_exists_ratio          "
            "0.0000  (ok)") in out
    assert "null  (no_image_elements)" not in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch219():
    src = _src()
    assert "{value:.4f}" in src
    assert "if isinstance(value, dict):" in src
    assert 'input_path.open("r", encoding="utf-8")' in src


# ---------- forbidden tokens 第四百九十一批 ----------

def test_source_no_eval_batch219():
    assert "eval(" not in _src()


def test_source_no_exec_batch219():
    assert "exec(" not in _src()


def test_source_no_compile_batch219():
    assert "compile(" not in _src()


def test_source_no_globals_batch219():
    assert "globals(" not in _src()


def test_source_no_locals_batch219():
    assert "locals(" not in _src()


def test_source_no_os_system_batch219():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch219():
    assert "subprocess" not in _src()


def test_source_no_popen_batch219():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch219():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch219():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch219():
    assert "socket" not in _src()


def test_source_no_requests_batch219():
    assert "requests" not in _src()


def test_source_no_urllib_batch219():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch219():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch219():
    assert "yield" not in _src()


def test_source_no_async_await_batch219():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch219():
    assert _src().count("open(") == 1
