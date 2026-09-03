# -*- coding: utf-8 -*-
"""Stage 9 批次 26：句子切分器 v1（冻结，零依赖，人机同规）。

规则（docs/stage9-batch26-design.md §3，一经冻结不改；缺陷须升 v2、
全量重切并走裁决）：
- 中文按 。！？； 切分（句末符号归前句）；
- 英文 . ! ? 后随空白+大写字母/数字才切；
- 缩写白名单不切：Fig. Eq. et al. Dr. No. vs. i.e. e.g. etc.；
- 省略号（… 与 ...）不切；
- 标题整体一个 unit（由标注人判定，切分器只出句子草稿）。

实现保证：输出的拼接严格等于输入（span 可直接由累积偏移得到）。
"""
CN_TERMINATORS = "。！？；"
EN_TERMINATORS = ".!?"
ABBREVIATIONS = ("Fig.", "Eq.", "et al.", "Dr.", "No.", "vs.", "i.e.",
                 "e.g.", "etc.")


def _is_upper_or_digit(ch):
    return ch.isupper() or ch.isdigit()


def _ends_with_abbreviation(text, pos):
    """pos 指向英文句点；检查其前的词是否在缩写白名单。"""
    start = pos
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    word = text[start:pos + 1]
    return word in ABBREVIATIONS


def _in_ellipsis(text, pos):
    """pos 指向 "."；处于 ... 串中（前后还有点）则不切。"""
    if pos + 1 < len(text) and text[pos + 1] == ".":
        return True
    return pos > 0 and text[pos - 1] == "."


def split_sentences(text):
    """返回句子列表，"".join(结果) == text（空白也原样保留在句内）。"""
    if not text:
        return []
    bounds = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch in CN_TERMINATORS:
            bounds.append(i + 1)
            i += 1
            continue
        if ch in EN_TERMINATORS:
            nxt = i + 1
            if ch == "." and _in_ellipsis(text, i):
                i += 1
                continue
            if nxt < n and text[nxt].isspace() \
                    and nxt + 1 < n \
                    and _is_upper_or_digit(text[nxt + 1]) \
                    and not _ends_with_abbreviation(text, i):
                bounds.append(nxt + 1)  # 边界在空白之后（空格归前句）
                i = nxt + 1
                continue
            i += 1
            continue
        i += 1
    if not bounds or bounds[-1] != n:
        bounds.append(n)
    return [text[a:b] for a, b in zip([0] + bounds[:-1], bounds)]
