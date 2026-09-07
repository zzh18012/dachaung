# -*- coding: utf-8 -*-
"""Stage 9 批次 26：identity resolution 辅助工具测试。

plan（操作员视图）/blind（解析者盲态视图）/skeleton 骨架；盲态契约：
blind 输出不得含 gold_segment 值、一致率数值或贡献区间。
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage9_identity_view.py"


def _ann(doc_id, items):
    parts = []
    units = []
    pos = 0
    for idx, (kind, payload, seg, hard, page) in enumerate(items):
        unit = {"unit_id": "u%04d" % (idx + 1), "page": page,
                "gold_segment_id": seg, "hard_boundary_before": hard}
        if kind == "n":
            unit.update(kind="nontext", char_span=None,
                        nontext_ref=payload)
        else:
            if parts:
                parts.append(" ")
                pos += 1
            start = pos
            parts.append(payload)
            pos += len(payload)
            unit.update(kind="heading" if kind == "h" else "sentence",
                        char_span=[start, pos], nontext_ref=None)
        units.append(unit)
    return {"doc_id": doc_id, "stream": "".join(parts), "units": units}


def _indeterminate_pair():
    """5 文本对 + img 1×2（p1）→ [5/7, 6/7] 跨 0.85 indeterminate。"""
    items_a = [("s", "S%d." % i, "g01", False, 1) for i in range(5)]
    items_a.append(("n", "img:only", "g01", False, 1))
    items_b = [("s", "S%d." % i, "g01", False, 1) for i in range(5)]
    items_b += [("n", "img:1", "g01", False, 1),
                ("n", "img:2", "g02", False, 1)]
    return _ann("d", items_a), _ann("d", items_b)


def _two_group_pair():
    """img 1×2 两页两组（p1/p2），供 --groups 选择与迭代测试。"""
    items_a = [("s", "T1.", "g01", False, 1),
               ("n", "img:a1", "g01", False, 1),
               ("s", "T2.", "g02", False, 2),
               ("n", "img:a2", "g01", False, 2)]
    items_b = [("s", "T1.", "g01", False, 1),
               ("n", "img:b1", "g01", False, 1),
               ("n", "img:b2", "g02", False, 1),
               ("s", "T2.", "g02", False, 2),
               ("n", "img:c2", "g01", False, 2),
               ("n", "img:d2", "g02", False, 2)]
    return _ann("d", items_a), _ann("d", items_b)


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


def _write(tmp_path, ann, name):
    p = tmp_path / name
    p.write_text(json.dumps(ann, ensure_ascii=False), encoding="utf-8")
    return p


def test_plan_json_flags_and_group_listing(tmp_path):
    a, b = _indeterminate_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    r = run("plan", "--a", str(pa), "--b", str(pb), "--json")
    assert r.returncode == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout)
    assert payload["decision"] == "indeterminate"
    assert (payload["agree_lower"], payload["agree_upper"],
            payload["union"]) == (5, 6, 7)
    assert payload["open_group_count"] == 1
    g = payload["groups"][0]
    assert g["group"] == "img|1"
    assert (g["side_a"], g["side_b"], g["matched"]) == (1, 2, 1)
    assert (g["contribution_lower"], g["contribution_upper"]) == (0, 1)
    assert g["gap"] == 1
    # 单独消解即可定判：取上界贡献 6/7 → pass；取下界 5/7 → below
    assert g["alone_pass"] is True and g["alone_below"] is True


def test_plan_degenerate_groups_excluded(tmp_path):
    # 同一份标注自比对：组区间退化 gap=0 → 不进 open 列表
    a, _ = _indeterminate_pair()
    pa = _write(tmp_path, a, "a.json")
    r = run("plan", "--a", str(pa), "--b", str(pa), "--json")
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["decision"] == "pass"
    assert payload["open_group_count"] == 0 and payload["groups"] == []


def test_blind_view_blindness_contract(tmp_path):
    # 盲态契约：输出含 unit_id/组键/结构邻文/matched，不含
    # gold_segment 值（g01/g02）、一致率、贡献区间
    a, b = _indeterminate_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    r = run("blind", "--a", str(pa), "--b", str(pb))
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    for token in ("u0006", "u0007", "img|1", "S4."):
        assert token in out, token
    for forbidden in ("g01", "g02", "0.85", "agreement", "0.7",
                      "contribution"):
        assert forbidden not in out, forbidden
    assert "matched=1" in out


def test_blind_groups_selection_and_skeleton(tmp_path):
    a, b = _two_group_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    skel = tmp_path / "skeleton.json"
    r = run("blind", "--a", str(pa), "--b", str(pb),
            "--groups", "img|1", "--skeleton", str(skel))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "img|1" in r.stdout and "img|2" not in r.stdout
    skeleton = json.loads(skel.read_text(encoding="utf-8"))
    assert skeleton == {"img|1": []}


def test_blind_default_lists_all_open_groups(tmp_path):
    a, b = _two_group_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    r = run("blind", "--a", str(pa), "--b", str(pb))
    assert r.returncode == 0
    assert "img|1" in r.stdout and "img|2" in r.stdout


def test_blind_iteration_excludes_resolved(tmp_path):
    # 代入已消解 img|1 的 pair map：默认视图只剩 img|2
    a, b = _two_group_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    pm = tmp_path / "pm.json"
    pm.write_text(json.dumps({"img|1": [["u0002", "u0002"]]}),
                  encoding="utf-8")
    r = run("blind", "--a", str(pa), "--b", str(pb),
            "--pair-map", str(pm))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "img|2" in r.stdout and "img|1" not in r.stdout
    # 显式再选已消解组 → 输入错误
    r2 = run("blind", "--a", str(pa), "--b", str(pb),
             "--pair-map", str(pm), "--groups", "img|1")
    assert r2.returncode == 2


def test_blind_neighbor_text_is_structural_evidence(tmp_path):
    # 前后相邻文本单元内容出现在视图（结构位置证据）
    a, b = _two_group_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    r = run("blind", "--a", str(pa), "--b", str(pb), "--groups", "img|1")
    assert r.returncode == 0
    assert "T1." in r.stdout  # img|1 组 A 侧对象的前文


def test_blind_out_file(tmp_path):
    a, b = _indeterminate_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    out = tmp_path / "view.txt"
    r = run("blind", "--a", str(pa), "--b", str(pb), "--out", str(out))
    assert r.returncode == 0
    body = out.read_text(encoding="utf-8")
    assert "u0006" in body and "g01" not in body


def test_input_errors_rc2(tmp_path):
    a, b = _indeterminate_pair()
    pa = _write(tmp_path, a, "a.json")
    pb = _write(tmp_path, b, "b.json")
    # doc_id 不一致
    other = _write(tmp_path, _ann("other", [("s", "X.", "g01", False, 1)]),
                   "o.json")
    assert run("plan", "--a", str(pa), "--b", str(other),
               "--json").returncode == 2
    # 文件不存在
    assert run("plan", "--a", str(pa), "--b",
               str(tmp_path / "nope.json")).returncode == 2
    # 组名不存在
    assert run("blind", "--a", str(pa), "--b", str(pb),
               "--groups", "img|9").returncode == 2
    # 非法 pair map（组不存在）
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"img|9": [["u0001", "u0001"]]}),
                   encoding="utf-8")
    assert run("blind", "--a", str(pa), "--b", str(pb),
               "--pair-map", str(bad)).returncode == 2
