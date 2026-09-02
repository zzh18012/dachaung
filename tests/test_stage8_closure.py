"""Stage 8 封口评估收口测试：基准脚本契约 + 台账锚点（§六十四回执 /
§六十五六项证据）。

基准数值（1.06s / 1.22s / 1.78s）是 2026-09-02 的历史实测记录，测试
锁定台账记载本身（台账纪律：如实登记），不保证重跑数值一致；可复现
入口是 scripts/benchmark_stage8_closure.py 本身。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "scripts" / "benchmark_stage8_closure.py"

MAIN_SHA = "4858ab743b998da2d783f5c37f8e5bf99ff3d098"


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _squeeze(name: str) -> str:
    return "".join(_read(name).split())


def _sq(phrase: str) -> str:
    return "".join(phrase.split())


# ---------- 基准脚本契约 ----------

def test_benchmark_script_threshold_and_defaults():
    text = BENCH.read_text(encoding="utf-8")
    assert "TIME_LIMIT_SECONDS = 600.0" in text
    assert 'ap.add_argument("--count", type=int, default=100)' in text
    assert 'ap.add_argument("--workers", type=int, default=8)' in text


def test_benchmark_corpus_is_deterministic_mixed_formats():
    text = BENCH.read_text(encoding="utf-8")
    # 40 md / 30 docx / 30 pdf（count=100 时）
    assert "bucket < 4" in text and "bucket < 7" in text
    # 零第三方依赖合成：docx 走 zipfile，PDF 手写字节流
    assert "zipfile.ZipFile" in text
    assert "%PDF-1.4" in text


def test_benchmark_timing_source_is_batch_summary():
    text = BENCH.read_text(encoding="utf-8")
    assert "wall_time_seconds" in text
    assert "summary.json" in text
    # 退出码契约写入 docstring
    assert _sq("退出码：0 = 全成功且 <600s") in _sq(text)


# ---------- ADOPTION §六十四：封口与推送回执 ----------

def test_adoption_batch25_sealed_with_push_receipt():
    text = _read("ADOPTION.md")
    assert "批次 25 SEALED" in text
    assert "33589020316" in text
    assert MAIN_SHA in text


def test_adoption_push_receipt_records_seven_step_protocol():
    text = _read("ADOPTION.md")
    assert "merge-base --is-ancestor" in text
    assert "merge --ff-only" in text
    assert "git ls-remote origin refs/heads/main" in text
    assert _sq("逐字符一致") in _squeeze("ADOPTION.md")


# ---------- ADOPTION §六十五：六项证据 ----------

def test_adoption_stage8_closure_section_present():
    assert "## 六十五、Stage 8 封口评估（六项证据，2026-09-02）" in _read(
        "ADOPTION.md"
    )


def test_adoption_closure_records_six_evidence_items():
    squeezed = _squeeze("ADOPTION.md")
    for phrase in (
        "100 文档处理耗时 <10 min",
        "结构化 JSONL 日志",
        "外部 parser 插件示例",
        "可复现 Docker/CI 交付制品",
        "可操作的部署运行手册",
        "全量测试及既有契约零回归",
    ):
        assert _sq(phrase) in squeezed, phrase


def test_adoption_closure_records_benchmark_measurements():
    squeezed = _squeeze("ADOPTION.md")
    assert _sq("100/100 成功、失败 0、墙钟 1.06s") in squeezed
    assert _sq("墙钟 1.22s") in squeezed
    assert _sq("墙钟 1.78s") in squeezed
    # 合成语料性质如实披露（不伪装成重型真实文档）
    assert _sq("合成文档为中小体量") in squeezed


def test_adoption_closure_records_jsonl_event_counts():
    squeezed = _squeeze("ADOPTION.md")
    assert _sq("batch_start=1 / file_complete=100 / batch_complete=1") in squeezed
    assert _sq("file_error=3") in squeezed
