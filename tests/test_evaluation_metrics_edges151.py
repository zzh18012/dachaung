"""evaluation/metrics.py 第五百七十二轮 edges 测试（Round 1296）。

补强 edges150 未触及的角度（第六百六十八批，probe 实证）。

新角度（image 型静默丢落 / irer 双候选回退）：
- **image 计入 sdc**——真板
  ecbt {heading:1,
  paragraph:1, image:1}：
  exact 期望 → 0；image:2 →
  1；image:5 单键 → 4（图片
  欠发射计入丢落首锁）
- **期望侧独裁**——期望无
  image 键 → 0（实际多出的
  型不计）；caption:1 → 1
  （期望有而实际全无的型经
  by_type.get(t,0) 计入）
- **ecbt 空态**——{} 或缺键
  → no_expectations_
  element_count（区别于无
  expectations 节点的
  no_expectations）
- **irer 双候选回退**——裸
  文件名 + base_dir 含同名
  → 1.0（join 候选）；无
  base_dir → 0.0；深路径
  gone_dir/nope.png + base_dir
  含 nope.png → 1.0（按名救
  回）；零字节文件 → 0.0
  （st_size>0 门槛首锁）
- forbidden tokens 第七百五十批（open 0）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.metrics as metrics_mod
from app.pipeline import process_single
from evaluation.metrics import compute_automatic_metrics


def _image_pdf(content: bytes) -> bytes:
    img = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255,
                 255, 255, 0])
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>"
            b"/XObject<</Im0 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(content)).encode()
            + b">>stream\n" + content + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/XObject/Subtype/Image/Width 2/Height 2"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
            + str(len(img)).encode()
            + b">>stream\n" + img + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 7\n0000000000 65535 f \n"
    for num in range(1, 7):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 7/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
HEAD = "A" * 80


def _doc(tmp_path):
    content = (b"q 100 0 0 50 10 500 cm /Im0 Do Q\n"
               + ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
                  % HEAD).encode()
               + ("BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
                  % LONG).encode())
    p = tmp_path / "imgcombo.pdf"
    p.write_bytes(_image_pdf(content))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    return doc.to_dict()


def _sdc(dd, ecbt):
    exp = {"element_count_by_type": ecbt} if ecbt is not None \
        else None
    return compute_automatic_metrics(
        dd, None, "pdf", exp)["silent_drop_count"]


def _irer(dd, base_dir=None):
    return compute_automatic_metrics(
        dd, None, "pdf", None,
        image_base_dir=base_dir)["image_resource_exists_ratio"]


# ---------- image 计入 sdc ----------

def test_sdc_exact_zero_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {"heading": 1, "paragraph": 1,
                     "image": 1}) == {"value": 0,
                                      "reason": None}


def test_sdc_image_undercount_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {"heading": 1, "paragraph": 1,
                     "image": 2}) == {"value": 1,
                                      "reason": None}


def test_sdc_heading_overcount_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {"heading": 2, "paragraph": 1,
                     "image": 1}) == {"value": 1,
                                      "reason": None}


def test_sdc_image_only_key_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {"image": 5}) == {"value": 4,
                                      "reason": None}


def test_sdc_drop_sum_two_types_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {"heading": 3, "image": 3}) == {
        "value": 4, "reason": None}


# ---------- 期望侧独裁 ----------

def test_sdc_extra_actual_type_ignored_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {"heading": 1, "paragraph": 1}) == {
        "value": 0, "reason": None}


def test_sdc_absent_type_counts_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {"caption": 1}) == {"value": 1,
                                        "reason": None}


def test_ecbt_dict_value_batch494(tmp_path):
    dd = _doc(tmp_path)
    m = compute_automatic_metrics(dd, None, "pdf", None)
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1, "image": 1},
        "reason": None}


# ---------- ecbt 空态 ----------

def test_sdc_empty_ecbt_null_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, {}) == {
        "value": None,
        "reason": "no_expectations_element_count"}


def test_sdc_missing_ecbt_key_null_batch494(tmp_path):
    dd = _doc(tmp_path)
    m = compute_automatic_metrics(
        dd, None, "pdf", {"other_key": 1})
    assert m["silent_drop_count"] == {
        "value": None,
        "reason": "no_expectations_element_count"}


def test_sdc_no_expectations_null_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _sdc(dd, None) == {"value": None,
                              "reason": "no_expectations"}


# ---------- irer 双候选回退 ----------

def test_irer_real_file_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _irer(dd) == {"value": 1.0, "reason": None}


def test_irer_bare_name_no_basedir_batch494(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path))
    dd["elements"][2]["resource_path"] = "zz_irer_9x7.png"
    assert _irer(dd) == {"value": 0.0, "reason": None}


def test_irer_bare_name_basedir_join_batch494(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path))
    dd["elements"][2]["resource_path"] = "zz_irer_9x7.png"
    base = tmp_path / "basedir"
    base.mkdir()
    (base / "zz_irer_9x7.png").write_bytes(b"x")
    assert _irer(dd, base) == {"value": 1.0, "reason": None}


def test_irer_broken_path_no_rescue_batch494(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path))
    dd["elements"][2]["resource_path"] = "gone_dir/nope.png"
    base = tmp_path / "basedir"
    base.mkdir()
    assert _irer(dd, base) == {"value": 0.0, "reason": None}


def test_irer_broken_path_name_rescue_batch494(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path))
    dd["elements"][2]["resource_path"] = "gone_dir/nope.png"
    base = tmp_path / "basedir"
    base.mkdir()
    (base / "nope.png").write_bytes(b"x")
    assert _irer(dd, base) == {"value": 1.0, "reason": None}


def test_irer_zero_size_rejected_batch494(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path))
    dd["elements"][2]["resource_path"] = "sub/zero.png"
    base = tmp_path / "basedir"
    base.mkdir()
    (base / "zero.png").write_bytes(b"")
    assert _irer(dd, base) == {"value": 0.0, "reason": None}


def test_irer_reason_none_all_faces_batch494(tmp_path):
    dd = _doc(tmp_path)
    assert _irer(dd)["reason"] is None


# ---------- 文本面不动 ----------

def test_text_preservation_equal_batch494(tmp_path):
    dd = _doc(tmp_path)
    m = compute_automatic_metrics(dd, None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch494():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src
    assert "drops += (exp - actual)" in src


# ---------- forbidden tokens 第七百五十批 ----------

def test_source_no_eval_batch494():
    assert "eval(" not in _src()


def test_source_no_exec_batch494():
    assert "exec(" not in _src()


def test_source_no_compile_batch494():
    assert "compile(" not in _src()


def test_source_no_globals_batch494():
    assert "globals(" not in _src()


def test_source_no_locals_batch494():
    assert "locals(" not in _src()


def test_source_no_os_system_batch494():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch494():
    assert "subprocess" not in _src()


def test_source_no_popen_batch494():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch494():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch494():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch494():
    assert "socket" not in _src()


def test_source_no_requests_batch494():
    assert "requests" not in _src()


def test_source_no_urllib_batch494():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch494():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch494():
    assert "yield" not in _src()


def test_source_no_async_await_batch494():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch494():
    assert _src().count("open(") == 0
