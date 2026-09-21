"""Stage 10 Batch 11 shadow prototype — region-level layout substrate feasibility.

Authorization: r64/r65 design round (design / evidence / shadow prototype /
synthetic experiments only). This script does NOT import or modify app/
production parsing; it re-implements candidate algorithms standalone against
the same pdfplumber word dicts the production parser consumes, to produce
design evidence for docs/stage10-batch11-pdf-layout-architecture-design.md.

Usage:
  python -X utf8 scripts/stage10_batch11_layout_prototype.py --mode fixtures \
      --report outputs/batch11_layout_shadow_report.txt
  python -X utf8 scripts/stage10_batch11_layout_prototype.py --mode corpus \
      --pdf <path.pdf> [--pages 1,2,5 | --step 7 | --max-pages 12] \
      --report outputs/batch11_layout_shadow_report.txt
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

MIN_RIVER_FLOOR_PT = 15.0     # absolute floor for a full-height whitespace river
RIVER_GAP_FACTOR = 2.5        # river width must exceed factor x median intra-line gap
LINE_SUPPORT_HEIGHT_FACTOR = 2.0  # a line "opens" a river only if its empty run
                                 # also exceeds factor x that line's median word height
MIN_REGION_MASS_RATIO = 0.02  # both sides must carry >=2% of text char mass
MIN_REGION_WIDTH_PT = 20.0
MAX_SPLIT_DEPTH = 3
BIG_GAP_PT = 15.0             # per-line gap threshold for table-candidate axes


# ---------------------------------------------------------------- lines
def words_to_lines(words: list[dict], tol: float = 3.0) -> list[dict]:
    items = sorted(words, key=lambda w: ((w["top"] + w["bottom"]) / 2.0, w["x0"]))
    lines: list[dict] = []
    for w in items:
        yc = (w["top"] + w["bottom"]) / 2.0
        if lines and abs(yc - lines[-1]["yc"]) <= tol:
            lines[-1]["words"].append(w)
            lines[-1]["yc"] = (lines[-1]["yc"] + yc) / 2.0
        else:
            lines.append({"yc": yc, "words": [w]})
    for ln in lines:
        ws = sorted(ln["words"], key=lambda w: w["x0"])
        ln["x0"] = ws[0]["x0"]
        ln["x1"] = max(w["x1"] for w in ws)
        ln["top"] = min(w["top"] for w in ws)
        ln["bottom"] = max(w["bottom"] for w in ws)
    return lines


# ------------------------------------------------------- region formation
def find_rivers(words: list[dict], x_min: float, x_max: float,
                min_river_pt: float, resolution: float = 1.0) -> list[dict]:
    """Projection-profile valleys: x-bins empty across ALL words = full-height river."""
    n = int((x_max - x_min) / resolution) + 2
    occ = bytearray(n)
    for w in words:
        a = max(0, int((w["x0"] - x_min) / resolution))
        b = min(n - 1, int((w["x1"] - x_min) / resolution))
        for i in range(a, b + 1):
            occ[i] = 1
    rivers, i = [], 0
    while i < n:
        if not occ[i]:
            j = i
            while j + 1 < n and not occ[j + 1]:
                j += 1
            width = (j - i + 1) * resolution
            if width >= min_river_pt:
                rivers.append({"x0": x_min + i * resolution,
                               "x1": x_min + (j + 1) * resolution,
                               "width": round(width, 1)})
            i = j + 1
        else:
            i += 1
    return rivers


def _mass(words: list[dict]) -> int:
    return sum(len(w.get("text", "")) for w in words)


def _line_gaps_and_heights(words: list[dict]) -> tuple[list[float], list[float]]:
    """All intra-line adjacent word gaps and per-line median word heights."""
    gaps: list[float] = []
    heights: list[float] = []
    for ln in words_to_lines(words):
        ws = sorted(ln["words"], key=lambda w: w["x0"])
        for i in range(len(ws) - 1):
            gaps.append(ws[i + 1]["x0"] - ws[i]["x1"])
        heights.append(statistics.median(w["bottom"] - w["top"] for w in ws))
    return gaps, heights


def _line_supports_river(ln: dict, river: dict, need_pt: float) -> bool:
    """A line 'opens' the river iff some adjacent word pair straddles the whole
    river interval with an empty run wide enough for that line's font scale."""
    ws = sorted(ln["words"], key=lambda w: w["x0"])
    for i in range(len(ws) - 1):
        if ws[i]["x1"] <= river["x0"] and ws[i + 1]["x0"] >= river["x1"]:
            gap = ws[i + 1]["x0"] - ws[i]["x1"]
            if gap >= need_pt:
                return True
    return False


def split_regions(words: list[dict], depth: int = 0,
                  diagnostics: list[str] | None = None) -> list[list[dict]]:
    if depth >= MAX_SPLIT_DEPTH or len(words) < 8:
        return [words]
    gaps, _heights = _line_gaps_and_heights(words)
    med_gap = statistics.median(gaps) if gaps else 0.0
    min_river_pt = max(MIN_RIVER_FLOOR_PT, RIVER_GAP_FACTOR * med_gap)
    x_min = min(w["x0"] for w in words)
    x_max = max(w["x1"] for w in words)
    rivers = find_rivers(words, x_min, x_max, min_river_pt)
    if not rivers:
        return [words]
    r = max(rivers, key=lambda rr: rr["width"])
    left = [w for w in words if w["x1"] <= r["x0"] + 0.5]
    right = [w for w in words if w["x0"] >= r["x1"] - 0.5]
    if not left or not right:
        return [words]
    # strict support: every line that has words on BOTH banks must itself open
    # the river at its own font scale (spanning titles / big-font lines refuse).
    for ln in words_to_lines(words):
        has_l = any(w["x1"] <= r["x0"] + 0.5 for w in ln["words"])
        has_r = any(w["x0"] >= r["x1"] - 0.5 for w in ln["words"])
        if has_l and has_r:
            med_h = statistics.median(w["bottom"] - w["top"] for w in ln["words"])
            need = max(min_river_pt, LINE_SUPPORT_HEIGHT_FACTOR * med_h)
            if not _line_supports_river(ln, r, need):
                if diagnostics is not None:
                    diagnostics.append(
                        f"river {r['x0']:.0f}-{r['x1']:.0f} blocked by "
                        f"non-supporting both-banks line "
                        f"(need>={need:.0f}pt, font h~{med_h:.0f}pt)")
                return [words]
    total = _mass(words)
    if min(_mass(left), _mass(right)) / max(1, total) < MIN_REGION_MASS_RATIO:
        return [words]  # e.g. bare numbering column: too little mass to be a region
    if (r["x0"] - x_min) < MIN_REGION_WIDTH_PT or (x_max - r["x1"]) < MIN_REGION_WIDTH_PT:
        return [words]
    return (split_regions(left, depth + 1, diagnostics)
            + split_regions(right, depth + 1, diagnostics))


def region_stats(words: list[dict]) -> dict:
    x0 = min(w["x0"] for w in words)
    x1 = max(w["x1"] for w in words)
    top = min(w["top"] for w in words)
    bottom = max(w["bottom"] for w in words)
    return {"bbox": [round(x0, 1), round(top, 1), round(x1, 1), round(bottom, 1)],
            "words": len(words), "chars": _mass(words)}


# -------------------------------------- table-candidate confirmatory axes
def table_candidate_features(words: list[dict]) -> dict | None:
    """Batch-10 refuted threshold-only detection; these are the confirmatory
    axes the substrate would feed a candidate lane. Report-only."""
    lines = words_to_lines(words)
    if len(lines) < 3:
        return None
    word_gaps_all: list[float] = []
    big_gaps, left_x0s, right_x0s, row_heights = [], [], [], []
    for ln in lines:
        ws = sorted(ln["words"], key=lambda w: w["x0"])
        row_heights.append(ln["bottom"] - ln["top"])
        for i in range(len(ws) - 1):
            word_gaps_all.append(ws[i + 1]["x0"] - ws[i]["x1"])
        g, gi = 0.0, -1
        for i in range(len(ws) - 1):
            d = ws[i + 1]["x0"] - ws[i]["x1"]
            if d > g:
                g, gi = d, i
        if g >= BIG_GAP_PT:
            big_gaps.append(g)
            left_x0s.append(ws[0]["x0"])
            right_x0s.append(ws[gi + 1]["x0"])
    med_wg = statistics.median(word_gaps_all) if word_gaps_all else 0.0
    mean_rh = statistics.fmean(row_heights)
    sd_rh = statistics.pstdev(row_heights) if len(row_heights) > 1 else 0.0
    return {
        "n_lines": len(lines),
        "rows_with_big_gap": len(big_gaps),
        "max_gap_pt": round(max(big_gaps), 1) if big_gaps else 0.0,
        "gap_over_wordgap_ratio": round(max(big_gaps) / max(med_wg, 0.1), 1) if big_gaps else 0.0,
        "left_x0_span_pt": round(max(left_x0s) - min(left_x0s), 1) if left_x0s else None,
        "right_x0_drift_pt": round(max(right_x0s) - min(right_x0s), 1) if right_x0s else None,
        "row_height_cv": round(sd_rh / mean_rh, 3) if mean_rh else None,
    }


# -------------------------------------------------------------- fixtures
def _w(text: str, x0: float, x1: float, top: float, h: float = 10.0) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": top + h}


def _line_words(text: str, x0: float, x1: float, top: float, n: int = 6,
                h: float = 10.0, fill: float = 0.9) -> list[dict]:
    span = (x1 - x0) / n
    out = []
    for i in range(n):
        a = x0 + i * span
        out.append(_w(text[i * 2:i * 2 + 2] or "x", a, a + span * fill, top, h))
    return out


def fx_single_col() -> list[dict]:
    ws = []
    for i in range(25):
        ws += _line_words("aa bb cc dd ee ff", 80, 512, 100 + i * 14)
    return ws


def fx_single_col_wide_word_gaps() -> list[dict]:
    ws = []
    for i in range(25):
        ws += _line_words("aa bb cc dd ee ff", 80, 512, 100 + i * 14, fill=0.72)
    return ws  # ~20pt inter-word gaps: data-derived floor must refuse to split


def fx_two_col_body() -> list[dict]:
    ws = []
    for i in range(20):
        ws += _line_words("aa bb cc dd", 60, 280, 100 + i * 14)
        ws += _line_words("ee ff gg hh", 320, 540, 100 + i * 14)
    return ws  # river 280..320 = 40pt


def fx_two_col_spanning_title() -> list[dict]:
    ws = _line_words("TITLE SPANS BOTH COLUMNS", 60, 540, 80, n=7, h=18, fill=0.86)
    ws += fx_two_col_body()
    return ws  # big-font line must refuse to open the river -> 1 region + diagnostic


def fx_numbered_list_realistic() -> list[dict]:
    ws, y = [], 100
    for n in range(1, 13):
        ws.append(_w(f"{n}.", 80, 96, y))
        ws += _line_words("item text body", 130, 500, y, n=5)
        y += 14
        if n % 3 == 0:  # continuation lines start at text x0 -> blocks strict river
            ws += _line_words("cont body", 130, 500, y, n=5)
            y += 14
    return ws


def fx_numbered_pure() -> list[dict]:
    ws, y = [], 100
    for n in range(1, 21):
        ws.append(_w(f"{n}.", 80, 96, y))
        ws += _line_words("item text body", 150, 500, y, n=5)
        y += 14
    return ws  # river 96..150 exists but left mass tiny


def fx_borderless_kv() -> list[dict]:
    ws, y = [], 100
    drift = [300, 312, 306, 340, 328, 356]
    for i in range(6):
        ws.append(_w("key001", 100, 140, y))
        ws.append(_w("val", drift[i], drift[i] + 60, y))
        ws.append(_w("tail", drift[i] + 80, drift[i] + 130, y))
        y += 16
    return ws


def fx_borderless_sparse() -> list[dict]:
    ws, y = [], 100
    for i in range(3):
        ws.append(_w("k1", 100, 120, y))
        ws.append(_w("v1", 330, 400, y))
        y += 18
    return ws


FIXTURES = [
    ("single-col prose (expect 1 region)", fx_single_col),
    ("single-col wide word gaps stress (calibration -> 1 region)", fx_single_col_wide_word_gaps),
    ("two-col body N4 (expect 2 regions, NOT table)", fx_two_col_body),
    ("two-col + big-font spanning title (strict -> 1 region + diagnostic)", fx_two_col_spanning_title),
    ("numbered list N3 realistic (expect 1 region)", fx_numbered_list_realistic),
    ("numbered list N3 pure (calibration/mass guard -> 1 region)", fx_numbered_pure),
    ("borderless KV F-A DT00-like (1 region + candidate axes)", fx_borderless_kv),
    ("borderless sparse P1-like (1 region + candidate axes)", fx_borderless_sparse),
]


def run_fixtures() -> list[str]:
    out = ["== FIXTURES (word-list level; data-derived river floor = "
           f"max({MIN_RIVER_FLOOR_PT}pt, {RIVER_GAP_FACTOR}x median intra-line gap); "
           f"line support >= max(floor, {LINE_SUPPORT_HEIGHT_FACTOR}x line font height); "
           f"mass_ratio>={MIN_REGION_MASS_RATIO}) =="]
    for name, fn in FIXTURES:
        words = fn()
        diag: list[str] = []
        regions = split_regions(words, diagnostics=diag)
        axes = table_candidate_features(words)
        rs = [region_stats(r) for r in regions]
        out.append(f"\n-- {name}")
        out.append(f"   regions={len(regions)} stats={rs}")
        out.append(f"   candidate_axes={axes}")
        for d in diag:
            out.append(f"   diagnostic: {d}")
    return out


# ---------------------------------------------------------------- corpus
def run_corpus(pdf_path: str, pages: list[int] | None, step: int,
               max_pages: int | None) -> list[str]:
    import pdfplumber
    out = [f"\n== CORPUS {Path(pdf_path).name} =="]
    n_multi, n_total = 0, 0
    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        idxs = pages or list(range(1, n_pages + 1, max(1, step)))
        if max_pages:
            idxs = idxs[:max_pages]
        for pno in idxs:
            if pno < 1 or pno > n_pages:
                continue
            page = pdf.pages[pno - 1]
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            words = [{"text": w["text"], "x0": float(w["x0"]), "x1": float(w["x1"]),
                      "top": float(w["top"]), "bottom": float(w["bottom"])} for w in words]
            if len(words) < 8:
                out.append(f"p{pno:03d}: words={len(words)} (skip)")
                continue
            diag: list[str] = []
            regions = split_regions(words, diagnostics=diag)
            n_total += 1
            if len(regions) > 1:
                n_multi += 1
            rs = [region_stats(r) for r in regions]
            line = f"p{pno:03d}: words={len(words)} regions={len(regions)}"
            if len(regions) > 1:
                line += f" {rs}"
                axes = table_candidate_features(regions[0])
                line += f" axes_r0={axes}"
            if diag:
                line += f" blocked_rivers={len(diag)}"
            out.append(line)
    out.append(f"-- degeneracy: {n_total - n_multi}/{n_total} pages -> 1 region; "
               f"{n_multi} multi-region")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fixtures", "corpus"], required=True)
    ap.add_argument("--pdf")
    ap.add_argument("--pages", help="comma list, 1-based")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--max-pages", type=int)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    if args.mode == "fixtures":
        out = run_fixtures()
    else:
        if not args.pdf:
            print("--pdf required for corpus mode", file=sys.stderr)
            return 2
        pages = [int(p) for p in args.pages.split(",")] if args.pages else None
        out = run_corpus(args.pdf, pages, args.step, args.max_pages)

    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("a", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"appended {len(out)} lines -> {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
