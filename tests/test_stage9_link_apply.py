# -*- coding: utf-8 -*-
"""Stage 9 批次 26：linked_nontext 施加工具测试（B2 边界机械化）。"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage9_link_apply.py"

STREAM = "Alpha beta gamma. Delta epsilon. Zeta eta theta."


def _sha(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ann():
    units = [
        {"unit_id": "u0001", "kind": "heading", "page": 1,
         "body_index": None, "char_span": [0, 18],
         "norm_text_hash": _sha(STREAM[0:18]),
         "text_preview": STREAM[0:18], "gold_segment_id": "g01",
         "hard_boundary_before": True},
        {"unit_id": "u0002", "kind": "sentence", "page": 1,
         "body_index": None, "char_span": [18, 33],
         "norm_text_hash": _sha(STREAM[18:33]),
         "text_preview": STREAM[18:33], "gold_segment_id": "g02",
         "hard_boundary_before": False},
        {"unit_id": "u0003", "kind": "sentence", "page": 2,
         "body_index": None, "char_span": [33, 48],
         "norm_text_hash": _sha(STREAM[33:48]),
         "text_preview": STREAM[33:48], "gold_segment_id": "g02",
         "hard_boundary_before": True},
        {"unit_id": "u0004", "kind": "nontext", "page": 1,
         "body_index": None, "char_span": None, "norm_text_hash": None,
         "nontext_ref": "img:figure1", "gold_segment_id": "g02",
         "hard_boundary_before": False},
        {"unit_id": "u0005", "kind": "nontext", "page": 2,
         "body_index": None, "char_span": None, "norm_text_hash": None,
         "nontext_ref": "img:figure2", "gold_segment_id": "g02",
         "hard_boundary_before": False},
    ]
    return {"doc_id": "acad-01-sentencebert", "annotation_schema": "v1.1",
            "sentence_splitter": "v1", "normalization": "fold-ws-v1",
            "annotator": "claude-draft + user-review", "stream": STREAM,
            "units": units,
            "segments": [{"gold_segment_id": "g01", "hint": "标题",
                          "kind": "frontmatter"},
                         {"gold_segment_id": "g02", "hint": "正文",
                          "kind": "body"}]}


def _write(tmp_path, data):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                 encoding="utf-8")
    return p


def _manifest(tmp_path):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"docs": [
        {"doc_id": "acad-01-sentencebert", "split": "dev",
         "format": "pdf"}]}), encoding="utf-8")
    return m


def _links(tmp_path, links):
    p = tmp_path / "links.py"
    p.write_text("LINKS = %r\n" % (links,), encoding="utf-8")
    return p


def _run(manifest, ann, links, extra=()):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--manifest", str(manifest),
         "--annotation", str(ann), "--links", str(links), *extra],
        capture_output=True, text=True, cwd=str(ROOT))


def test_apply_only_touches_linked_field(tmp_path):
    ann = _write(tmp_path, _ann())
    before = json.loads(ann.read_text(encoding="utf-8"))
    links = _links(tmp_path, {"u0002": ["img:figure1"],
                              "u0003": ["img:figure1", "img:figure2"]})
    r = _run(_manifest(tmp_path), ann, links)
    assert r.returncode == 0, r.stdout + r.stderr
    after = json.loads(ann.read_text(encoding="utf-8"))
    assert after["units"][1]["linked_nontext"] == ["img:figure1"]
    assert after["units"][2]["linked_nontext"] == ["img:figure1",
                                                   "img:figure2"]
    # B2 边界：剥离 linked_nontext 后逐字段相同
    for u_before, u_after in zip(before["units"], after["units"]):
        u_before.pop("linked_nontext", None)
        u_after.pop("linked_nontext", None)
        assert u_before == u_after
    assert {k: v for k, v in before.items() if k != "units"} == \
        {k: v for k, v in after.items() if k != "units"}
    assert "已施加" in r.stdout


def test_empty_list_removes_field(tmp_path):
    data = _ann()
    data["units"][1]["linked_nontext"] = ["img:figure1"]
    ann = _write(tmp_path, data)
    links = _links(tmp_path, {"u0002": []})
    r = _run(_manifest(tmp_path), ann, links)
    assert r.returncode == 0, r.stdout + r.stderr
    after = json.loads(ann.read_text(encoding="utf-8"))
    assert "linked_nontext" not in after["units"][1]


def test_unknown_unit_id_rc2(tmp_path):
    ann = _write(tmp_path, _ann())
    links = _links(tmp_path, {"u9999": ["img:figure1"]})
    assert _run(_manifest(tmp_path), ann, links).returncode == 2


def test_nontext_unit_rejected_rc2(tmp_path):
    ann = _write(tmp_path, _ann())
    links = _links(tmp_path, {"u0004": ["img:figure1"]})
    r = _run(_manifest(tmp_path), ann, links)
    assert r.returncode == 2
    assert "nontext" in r.stderr


def test_validation_failure_no_write(tmp_path):
    ann = _write(tmp_path, _ann())
    raw_before = ann.read_bytes()
    links = _links(tmp_path, {"u0002": ["img:nope"]})
    r = _run(_manifest(tmp_path), ann, links)
    assert r.returncode == 1
    assert "unknown_nontext_ref" in r.stderr
    assert ann.read_bytes() == raw_before


def test_order_violation_rejected_no_write(tmp_path):
    ann = _write(tmp_path, _ann())
    raw_before = ann.read_bytes()
    links = _links(tmp_path, {"u0002": ["img:figure2", "img:figure1"]})
    r = _run(_manifest(tmp_path), ann, links)
    assert r.returncode == 1
    assert "linked_ref_order" in r.stderr
    assert ann.read_bytes() == raw_before


def test_bad_links_file_rc2(tmp_path):
    ann = _write(tmp_path, _ann())
    p = tmp_path / "links.py"
    p.write_text("NOT_LINKS = 1\n", encoding="utf-8")
    assert _run(_manifest(tmp_path), ann, p).returncode == 2


def test_default_warns_stale_but_keeps(tmp_path):
    data = _ann()
    data["units"][2]["linked_nontext"] = ["img:figure1"]
    ann = _write(tmp_path, data)
    links = _links(tmp_path, {"u0002": ["img:figure1"]})
    r = _run(_manifest(tmp_path), ann, links)
    assert r.returncode == 0, r.stdout + r.stderr
    after = json.loads(ann.read_text(encoding="utf-8"))
    # 默认模式：表外 unit 的边不动，仅提示
    assert after["units"][2]["linked_nontext"] == ["img:figure1"]
    assert "stale 提示" in r.stderr and "u0003" in r.stderr


def test_replace_prunes_unlisted_edges(tmp_path):
    data = _ann()
    data["units"][2]["linked_nontext"] = ["img:figure1"]
    ann = _write(tmp_path, data)
    links = _links(tmp_path, {"u0002": ["img:figure1"]})
    r = _run(_manifest(tmp_path), ann, links, extra=("--replace",))
    assert r.returncode == 0, r.stdout + r.stderr
    after = json.loads(ann.read_text(encoding="utf-8"))
    assert after["units"][1]["linked_nontext"] == ["img:figure1"]
    assert "linked_nontext" not in after["units"][2]
    assert "u0003" in r.stderr and "stale" in r.stderr
    # B2 边界：除 linked_nontext 外无差异（对照无边的原始 fixture）
    stripped = [{k: v for k, v in u.items() if k != "linked_nontext"}
                for u in after["units"]]
    assert stripped == _ann()["units"]


def test_replace_keeps_b2_guard_and_validation(tmp_path):
    data = _ann()
    data["units"][2]["linked_nontext"] = ["img:figure1"]
    ann = _write(tmp_path, data)
    raw_before = ann.read_bytes()
    # 未知 ref：--replace 下施加后校验仍先行，失败不写盘
    links = _links(tmp_path, {"u0002": ["img:nope"]})
    r = _run(_manifest(tmp_path), ann, links, extra=("--replace",))
    assert r.returncode == 1
    assert "unknown_nontext_ref" in r.stderr
    assert ann.read_bytes() == raw_before


def test_default_no_stale_silent(tmp_path):
    ann = _write(tmp_path, _ann())
    links = _links(tmp_path, {"u0002": ["img:figure1"]})
    r = _run(_manifest(tmp_path), ann, links)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "stale" not in r.stderr
