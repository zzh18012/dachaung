# Stage 11 Batch 14 — font/size 属性加富设计轮（r71 ⑧ 第一优先，立项简报依据）

日期：2026-09-22。分支：`integration/stage11-batch14-fontsize-
enrichment-design`（基点 `7a96b55` = Stage 11-A 架构冻结远端
tip）。授权性质：**设计/取证轮，零生产实现**（本批产出 = 本
文档 + outputs/ 取证脚本与报告；app/ 零触碰）。r71 明示本裁决
不含 Batch 14 实施权与 push 权。

## 1. 目标（r71 ⑧ 口径）

为 raw words 一等输入（Stage 11-A Q1 裁决）补充 font/size 属性
信息面：不改词边界、不改任何解析行为，为后续批次（Batch 15
Tier-2 observation-only 候选车道、CJK char 级列河校准、未来
layout 级分类）提供数据基础。

## 2. 取证一：naive 方案被证据否决（重要，与 r71 前提的偏差披露）

**naive 方案** = 生产调用点直接改 `extract_words(extra_attrs=
["fontname","size"])`（fallback_parser.py:1076，一处改动）。

**证据（outputs/batch14_fontsize_shadow.py，六篇抽样 41 页）**：

| 文档 | 抽样页 | 词数 A（现状） | 词数 B（naive） | 净漂移 | 文本序列变化页 |
|------|-------|------------|------------|-------|----------|
| real-02 | 14 | 1670 | 1769 | **+99** | 10/14 |
| real-04 | 3 | 2106 | 1866 | **−240** | 2/3 |
| acad-03 | 5 | 987 | 1043 | +56 | 4/5 |
| prod-01 | 5 | 1868 | 2011 | +143 | 3/5 |
| tech-08 | 8 | 329 | 540 | **+211** | 8/8 |
| tech-03 | 6 | 358 | 420 | +62 | 5/6 |

**机制（real-04 p002 逐词 diff 实证）**：pdfplumber 把
extra_attrs 计入词分组判据——词内字体/字号变化即断词
（'106'→'10','6'，数字换字体）；Symbol 私有区字符（/
）与 CJK 4-7 字符块加剧漂移；且存在反向合并（净漂移
双向，real-04 −240）。

**结论**：naive 方案**改变词边界 → 破坏词守恒不变量 → 六篇
冻结基线必然漂移**。r71 对 Batch 14 "风险最低、不改变输出"
的前提**在 naive 实现下不成立**，本设计改用方案 2 并如实披露
该偏差。

## 3. 取证二：方案 2（事后连接）可行性成立

**方案 2** = 生产 `extract_words` 调用**逐字节不动**；从同页
`page.chars`（原生携带 fontname/size，无需二次解析）按几何包含
把属性事后连接到既有词流。

**证据（六篇形态页探针）**：

| 页 | 词数 | 无属性词 | 混合属性词（跨字体/字号） |
|----|------|--------|------------------|
| real-02 p001/p005 | 37/99 | 0/0 | 0/0 |
| real-04 p002（双栏） | 1428 | 0 | 68 |
| acad-03 p004（窄槽） | 329 | 0 | 66 |
| tech-08 p012（CJK） | 51 | 0 | **23** |
| prod-01 p077（TOC） | 52 | 0 | 0 |
| tech-03 p069 | 199 | 0 | 12 |

- **属性覆盖率 100%**（no_attr=0 全页）：每个生产词至少含一
  个 char → 无缺失属性问题；
- **混合属性词普遍存在**（CJK 页 45%）→ 词级属性须用规则
  合成（见 §4），且 mixed 率本身即 Tier-2 候选特征；
- **词边界零触碰** → 词守恒不变量与六篇冻结基线结构性保持。

## 4. 设计（Batch 14 实施批的授权申请内容）

1. **新增纯函数** `_annotate_words_with_attrs(words, chars)`
   （fallback_parser.py）：对每词取几何包含的 char 集合，词级
   fontname/size = 覆盖 x 跨度最大的 char 的值（平局取最左，
   确定性）；无包含 char（取证证明不发生）→ None 并计 warning
   计数（防御，不中断）。输出 = 原 word dict 追加两键
   （`fontname`/`font_size`），词本身身份与顺序不变。
2. **性能**：连接按 top 行带分桶索引（O(W+C)），tech-03 全篇
   250 页量级可承受；page.chars 单页生命周期内消费，不跨页
   持久化。
3. **消费端**：本批**零消费**——`_group_words_to_paragraphs`/
   `_split_words_into_column_regions`/`_classify_pdf_paragraph`
   均按键取值（已审计：不迭代 dict 键集），追加键惰性存在。
   属性进 Element.metadata 与否**不进 v1**（避免 schema 语义
   扩张；Tier-2 需要时另批）。
4. **CJK 校准侧信道顺带打开**：page.chars 的相邻字符间距即
   批次 11 识别的 CJK 列河下限推导输入（tech-08 p012 gap_
   median=18.5pt 问题的正解信息面）；本批只保证数据可得，
   校准本身是后续独立批。

## 5. 验收标准（实施批复用 Stage 11-A 冻结的标准仪器）

1. 六篇冻结基线**逐字节零漂移**（elements + chunks 对
   outputs/batch12i_after）；
2. 词守恒 EXACT（分区前后词集合不变，既有不变量）；
3. 全量回归 + guard suites 全绿；
4. 属性覆盖报告：100% 词带非 None 属性（六篇全篇）；
   mixed-attr 比率逐篇登记（outputs/ 证据脚本可复现）；
5. 连接纯度守护测试：同输入同属性（合成夹具）。

## 6. 影响面与不做什么

- 影响：fallback_parser.py 新增一个纯函数 + `_parse_pdf` 词
  提取后一处调用（构造 chars 传入）；无 schema/分类/阈值/
  regionizer/图注/表格改动。
- 不做：Tier-2 候选车道（Batch 15）；去重替换点（暂缓）；
  CJK 校准阈值（独立批）；Element.metadata 属性外显（另批）；
  DOCX 路径（python-docx 无对应概念，不适用）。

## 7. 边界声明

零生产实现；Stage 11-A 四项冻结与五保护面机制全部不变；
known residual 九家族维持登记不修；§3a 维持 deferred；本批
不含 push 权（commit 留存本分支待裁）。
