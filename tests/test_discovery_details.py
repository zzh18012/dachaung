"""批次 21 Phase B 测试：DiscoveryResult / discover_parser_details。

裁决 D3 + Phase A 补充要求（能力唯一来源 _capabilities，不建第三份
缓存）：解释结果按需派生、确定性可复现、与 discover_parser 同一决策。
"""

from __future__ import annotations

import pytest

import app.parser_registry as pr
from app.parser_registry import (
    DiscoveryCandidate,
    DiscoveryResult,
    discover_parser,
    discover_parser_details,
    register,
)
from app.parsers.base import Parser


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


def _make_parser_cls(name: str, exts=(".t1",), priority: int = 50) -> type[Parser]:
    class _P(Parser):
        def parse(self, path, source_hash):  # pragma: no cover - 测试桩
            raise NotImplementedError

    _P.name = name
    _P.supported_extensions = exts
    _P.priority = priority
    _P.source_types = ("text",)
    _P.locator_family = "line_address"
    _P.version = "test/1.0"
    return _P


# ---------- 内置真实候选：priority 分立 ----------

def test_md_details_two_candidates_priority_reason():
    r = discover_parser_details("x.md")
    assert r.extension == ".md"
    assert r.winner == "markdown_enhanced"
    names = [c.name for c in r.candidates]
    assert "markdown_enhanced" in names and "markdown" in names
    # 决策序：priority 升序（5 在 20 前）
    prios = [c.priority for c in r.candidates]
    assert prios == sorted(prios)
    assert r.tied_names == ()
    assert "5 < 20" in r.reason
    assert r.resolved is True


def test_pdf_details_fallback_beats_kreuzberg():
    r = discover_parser_details("x.pdf")
    assert r.winner == "fallback"
    prios = {c.name: c.priority for c in r.candidates}
    assert prios["fallback"] == 10 and prios["kreuzberg"] == 50
    assert r.tied_names == ()


def test_details_matches_discover_parser_delegation():
    for f in ("x.md", "x.pdf", "x.docx", "x.html", "x.txt", "x.ipynb"):
        assert discover_parser(f) == discover_parser_details(f).winner


# ---------- 平局 ----------

def test_tie_explains_first_registered_wins(fresh_registry):
    register(_make_parser_cls("tie_x", (".tieb",), priority=7))
    register(_make_parser_cls("tie_y", (".tieb",), priority=7))
    r = discover_parser_details("a.tieb")
    assert r.winner == "tie_x"
    assert r.tied_names == ("tie_x", "tie_y")  # 注册序
    assert "平局" in r.reason and "tie_x" in r.reason
    assert "registration_order" in r.reason
    orders = [c.registration_order for c in r.candidates if c.priority == 7]
    assert orders == sorted(orders)


def test_details_emits_no_warning_on_tie(fresh_registry, recwarn):
    register(_make_parser_cls("quiet_a", (".quiet",), priority=3))
    register(_make_parser_cls("quiet_b", (".quiet",), priority=3))
    discover_parser_details("z.quiet")
    assert len(recwarn) == 0, "诊断只陈述，不发 UserWarning"


def test_discover_parser_still_warns_on_tie(fresh_registry):
    register(_make_parser_cls("warn_a", (".warnb",), priority=3))
    register(_make_parser_cls("warn_b", (".warnb",), priority=3))
    with pytest.warns(UserWarning, match="同优先级"):
        assert discover_parser("z.warnb") == "warn_a"


# ---------- 无候选 ----------

def test_no_candidates_winner_none_reason_states_it():
    r = discover_parser_details("x.zzz9")
    assert r.winner is None
    assert r.candidates == ()
    assert r.tied_names == ()
    assert r.resolved is False
    assert "无已注册 parser" in r.reason


def test_no_candidates_details_does_not_raise_but_discover_does():
    r = discover_parser_details("y.zzz9")
    assert r.winner is None
    with pytest.raises(ValueError, match="无已注册 parser"):
        discover_parser("y.zzz9")


def test_no_suffix_extension_empty_string():
    r = discover_parser_details("noext")
    assert r.extension == ""
    assert r.winner is None
    assert "(无)" in r.reason


# ---------- 冻结与派生 ----------

def test_discovery_result_frozen(fresh_registry):
    register(_make_parser_cls("frozen_d", (".fd",), priority=2))
    r = discover_parser_details("x.fd")
    assert isinstance(r, DiscoveryResult)
    assert all(isinstance(c, DiscoveryCandidate) for c in r.candidates)
    with pytest.raises(Exception):
        r.winner = "hack"  # type: ignore[misc]


def test_details_derived_from_snapshot_not_live_attrs(fresh_registry):
    """Phase A 反漂移延伸：注册后改类属性，解释结果同样不变。"""
    cls = _make_parser_cls("snap_d", (".snapd",), priority=40)
    register(cls)
    cls.priority = 1
    cls.supported_extensions = (".other",)
    r = discover_parser_details("x.snapd")
    assert r.winner == "snap_d"
    assert r.candidates[0].priority == 40
    r2 = discover_parser_details("x.other")
    assert r2.winner is None


def test_registration_order_reflects_capability_insertion(fresh_registry):
    register(_make_parser_cls("ord1", (".ord",), priority=9))
    register(_make_parser_cls("ord2", (".ord",), priority=9))
    register(_make_parser_cls("ord3", (".ord",), priority=9))
    r = discover_parser_details("x.ord")
    assert [c.name for c in r.candidates if c.priority == 9] == [
        "ord1", "ord2", "ord3",
    ]
    assert r.winner == "ord1"
    assert r.tied_names == ("ord1", "ord2", "ord3")


def test_mixed_priorities_full_decision_order(fresh_registry):
    register(_make_parser_cls("mix_c", (".mix",), priority=30))
    register(_make_parser_cls("mix_a", (".mix",), priority=10))
    register(_make_parser_cls("mix_b", (".mix",), priority=20))
    r = discover_parser_details("x.mix")
    assert [c.name for c in r.candidates] == ["mix_a", "mix_b", "mix_c"]
    assert r.winner == "mix_a"
    assert r.tied_names == ()
    assert "10 < 20" in r.reason
