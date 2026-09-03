# -*- coding: utf-8 -*-
"""Stage 9 批次 26：句子切分器 v1 冻结规则测试。"""
from stage9.splitter import split_sentences


def _check_roundtrip(text):
    parts = split_sentences(text)
    assert "".join(parts) == text
    return [p.strip() for p in parts if p.strip()]


def test_chinese_terminators():
    parts = _check_roundtrip("第一句。第二句！第三句？分号；结尾")
    assert parts == ["第一句。", "第二句！", "第三句？", "分号；", "结尾"]


def test_english_rule_requires_uppercase_after_space():
    parts = _check_roundtrip("One two three. Four five. six seven.")
    assert parts == ["One two three.", "Four five. six seven."]


def test_digit_after_space_splits():
    # 空白后随数字 → 切（规则允许大写或数字）
    parts = _check_roundtrip("Version 1. 2 items are here.")
    assert parts == ["Version 1.", "2 items are here."]


def test_abbreviation_whitelist():
    parts = _check_roundtrip(
        "See Fig. 3 and Eq. 2. Dr. Smith et al. published it. "
        "i.e. the value, e.g. 5, vs. baseline, etc. end.")
    # "Eq." 白名单不切；"2. Dr" 空白+大写 → 切；"it. i" 小写 → 不切
    assert parts == [
        "See Fig. 3 and Eq. 2.",
        "Dr. Smith et al. published it. i.e. the value, e.g. 5, "
        "vs. baseline, etc. end."]


def test_ellipsis_not_split():
    parts = _check_roundtrip("等待……继续。wait... then. Done.")
    assert parts == ["等待……继续。", "wait... then.", "Done."]


def test_no_terminator_single_sentence():
    assert _check_roundtrip("没有终止符的文本") == ["没有终止符的文本"]


def test_empty():
    assert split_sentences("") == []


def test_concat_identity_with_whitespace():
    text = "句一。 句二！  tail"
    parts = split_sentences(text)
    assert "".join(parts) == text  # 空格保留在前句尾部
