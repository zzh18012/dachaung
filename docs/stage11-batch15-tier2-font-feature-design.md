# Stage 11 Batch 15 — Tier-2 font/layout candidate design（r73 授权设计轮，零实现）

日期：2026-09-22。分支 integration/stage11-batch15-tier2-font-feature-design，
基点 6ef9362（P26' A 精确核验后建立）。授权范围：shadow analysis /
candidate feature 统计 / synthetic fixtures / false-positive analysis /
architecture design；**零生产改动**（本批产出 = 本文档；证据脚本
outputs/batch15i_shadow.py 与报告 outputs/batch15i_shadow_report.txt /
batch15i_shadow_stdout.txt，gitignored，可复现）。

## 0. 仪器（shadow instrumentation）

- 词级属性：生产同款调用链 `extract_words → _annotate_words_with_attrs`
  （Batch 14 冻结实现，本批零触碰）。
- 元素映射：词中心落元素 bbox（±0.5pt）判属；同词命中多元素时归属
  **面积最小**者（段落/表格 bbox 重叠区的确定性仲裁）。
- 元素特征：`ratio` = 元素内最大词字号 / 全文档字号众数（body mode）；
  `fontOut` = 元素主导字体 ∉ 正文 top-3 字体（按词计数）。
- 分组：分析专用启发（ANALYSIS-ONLY，非生产规则）——real-02 按审计
  登记的 5 条 known residual 文本；acad-03 'Multimodal Transformer' ×2
  记 legit、其余记 figure-label；prod-01 纯数字（≤4 位）记 residual；
  tech-03 按 caption-miss（^图\d）/ chart-data（%、单位、纯数字、
  年份行）/ page-header（逐字重复页眉）/ section（编号前缀+白名单）/
  other 分桶。
- 基线：outputs/batch14i_after 六篇 JSON（Batch 14 验收轮产物，
  @6ef9362 行为等价）。

## 1. Q1(a)：font 信号对已知 residual 家族的判别力

### 1.1 六篇字体版面画像

| 文档 | body size(mode) | 正文 top-3 字体 |
|------|----------------|----------------|
| real-02 | 12.0 | HelveticaNeue / -Bold / -Medium |
| real-04 | 8.0 | Times New Roman / ,Italic / Symbol |
| acad-03 | 9.0 | LinLibertineT / T(Bold) / Display |
| prod-01 | 9.0 | FreeSerif / FreeMono / FreeMonoBold |
| tech-08 | 7.9 | SimSun / TimesNewRoman / TT87B…tCID |
| tech-03 | 8.0 | FZSYJW / FZLTXHK / FZLTZHK（方正三族） |

### 1.2 家族特征表（节选完整表见 shadow 报告）

| 篇 | 组 | n | medR | minR~maxR | fontOut |
|----|----|---|------|-----------|---------|
| real-02 | legit | 12 | 1.33 | 1.33~4.0 | 1 (8%) |
| real-02 | residual-known | 5 | 1.00 | 1.00~1.33 | 1 (20%) |
| real-02 | SUPP:page_number | 12 | 0.67 | 0.67 | 0 |
| acad-03 | figure-label | 7 | 0.74 | 0.74~0.90 | 1 (14%) |
| acad-03 | legit | 2 | 1.22 | 1.04~1.40 | 0 |
| prod-01 | legit | 392 | 1.11 | 0.89~2.75 | 325 (83%) |
| prod-01 | residual-known(纯数字) | 35 | 1.11 | 0.89~1.11 | 33 (94%) |
| tech-08 | CAPTION | 56 | 1.16 | 1.16~1.33 | 0 |
| tech-08 | legit | 307 | 1.11 | 1.0~60.76 | 85 (28%) |
| tech-08 | SUPP:band_repeat | 8 | 1.27 | 1.0~1.27 | 6 (75%) |
| tech-03 | caption-miss | 227 | 1.00 | 1.00 | 0 |
| tech-03 | chart-data | 685 | 1.00 | 0.62~1.00 | 233 (34%) |
| tech-03 | page-header | 110 | 1.00 | 1.00 | 110 (100%) |
| tech-03 | section | 158 | 1.25 | 1.25~7.0 | 137 (87%) |

### 1.3 可分（font 提供新增判别力）的家族

**(1) acad-03 图内标签**：ratio 0.74~0.90 vs 本篇 legit ≥1.04，
篇内干净尺寸沟（合法 heading 最小 1.04 > 图内标签最大 0.90）。
F1(r≤0.90) 篇内 4/7、零 legit FP；跨篇 F1 FP = prod-01 legit ×7
（0.89≤0.9）。结论：**尺寸信号真实但阈值窗紧**（0.90~1.04 之间
才是 acad-03 的篇内沟；0.85 边界漏 3 条）——按 r73(5)，此为
观察面证据，**不构成阈值规则**。

**(2) prod-01 纯数字页码家族**：35 实例全部 digit-only、33/35
FreeSansBold（圈外字体）、r 全部 ≤1.11、逐项同构（章节扉页页码
'3','5','7',…,'161'）。审计登记的 TOC 行尾页码 ×3（71/99/161）
是本家族子集；其余 32 条为同结构未逐条登记的冻结基线项。
**F4(digit ∧ fontOut) = 33/35，prod-01 legit-392 上 FP = 0**。

**(3) 佐证价值（corroboration）**：real-02 已抑制页码（批次 9 D1）
r=0.67 全 12 条一致小于正文——font 与位置带信号正交且同向；
tech-08/tech-03 已抑制 band_repeat（批次 9 D2）75%/100% fontOut
——font 与跨页重复信号同向。既有规则若未来走 Tier-2 重证，
font 是可用佐证，不是替代。

### 1.4 不可分（反例清单，font 无增量）

| 家族 | 实测 | 结论 |
|------|------|------|
| real-02 表单残留 4/5（Consigner…/Advisor's…/Signature…/区头） | 正文字体族、r=1.0 | font 惰性；r59/r68 边界维持 |
| real-02 封面日期 'December 2025' | LTPro 变体（圈外）+r=1.33 | 弱信号；r62③ 禁字号特判边界不变 |
| prod-01 continued 家族（观察 6 条，审计登记 p77 ×1） | 正文字体 r=0.89~1.0 / 等宽体 r=1.0 | font 惰性 |
| tech-03 caption-miss（图N-N ×227） | fontOut=0、r=1.0 | font 惰性；其修复族是 caption 正则文本形态，非 font |
| tech-03 chart-data 大部 | 66% 用正文顶 3 字体 | 部分可分（34% 圈外），非全族 |

### 1.5 结构性反例（最重要）

**"圈外字体"是合法 heading 的常态，不是异常信号**：prod-01 legit
83% 圈外（等宽代码行+章标题用 FreeSans/FreeMonoBold 等）、
tech-03 section 87% 圈外（方正黑体族标题 vs 宋体正文）、tech-08
28% 圈外（SimHei 页眉/黑体章题）。机理：heading 本来就是样式化
文本，字体差异是排版系统的正常输出。**推论：任何"字体独特 ⇒
候选降级"形态的规则在此语料上必然高误伤；font 只能作为组合
证据（文本形态 ∧ 几何 ∧ 重复性 ∧ font）参与 Tier-2 候选评分，
永远不能单独定案。**

### 1.6 候选观察规则命中矩阵（F1/F1'/F2/F3/F4，节选）

| 规则 | 定义 | 代表 TP | 代表 FP |
|------|------|---------|---------|
| F1 | r≤0.90 | acad-03 figure-label 4/7；real-02 已抑制页码 12/12 | prod-01 legit ×7 |
| F1' | r≤0.85 | acad-03 4/7；tech-03 other 12 | prod-01 legit 0 |
| F2 | fontOut | tech-03 page-header 110/110；prod-01 数字家族 33/35 | prod-01 legit 325、tech-03 section 137（结构性高 FP，见表 1.5） |
| F3 | fontOut∧r≤0.85 | tech-03 band_repeat 4/6 | 各篇 legit 0 |
| F4 | digit∧fontOut | prod-01 数字家族 33/35（legit FP 0）；tech-03 chart-data 233 | tech-08 Impact 横幅 '5' ×6（GT 待定：装饰页码，两可） |

## 2. Q1(b,c)：与既有信号的组合关系

| 家族 | 既有信号 | font 增量形态 |
|------|---------|--------------|
| acad-03 图内标签 | 图邻接几何（图 bbox 内/邻） | **独立增量**（尺寸比 0.74~0.90 与图几何正交） |
| prod-01 数字页码 | 无（digit 形态本身弱：代码行也含数字） | **组合必需**（digit∧fontOut 才近零 FP） |
| tech-03 页眉 110 | D2 只覆盖底带；顶带逐字重复未被覆盖 | 佐证（100% fontOut，但需"重复+位置带"组合，单 fontOut 会杀 section 87%） |
| real-02 页码（已抑制） | D1 底带 | 佐证（r=0.67 一致） |
| 表单残留/continued/caption-miss | 各自裁定边界 | 零增量 |

跨语料候选证据检查（r69 标准：≥2 篇同结构信号）：
digit∧fontOut 结构在 prod-01（35）/ tech-03（233 子集）/ tech-08
（6）三篇复现，但**语义目标不同**（扉页页码 / 图表数据标签 /
装饰横幅）——结构信号跨篇成立，语义家族不合一；任何 Tier-2
候选必须按"结构信号 × 篇内语义证据"组合，不得跨篇直推规则。

## 3. Q2：candidate 范围观察登记（不自动修复）

1. **页面家具 residual**：prod-01 数字页码家族（35，F4 近零 FP）；
   tech-03 顶带页眉（110，同文+圈外字体+顶带位置——注意这是
   "D2 扩展到顶带"的规则变化方向，须单独批次裁决，本批仅登记）；
   tech-08 Impact 装饰横幅 '5'（6，无 GT，两可登记）。
2. **heading residual**：acad-03 图内标签（尺寸沟 + 图邻接几何
   组合，篇内零 FP；跨篇阈值窗紧）。
3. **表单残留**：font 惰性（1.4），无候选。
4. **caption/figure 邻接**：tech-08 CAPTION r=1.16~1.33、正文
   字体——caption 无独立 font 签名；caption 配对（批次 4 几何
   规则）不受 font 影响，维持。

## 4. Q3：不消费也成立（零漂移验证）

- 结构证明：`git diff 6ef9362` 为空（本分支零 tracked 改动；
  证据脚本仅在 gitignored outputs/）。
- 全量回归 @本分支：**5666 passed / 26 skipped / 0 failed**
  （55.77s）；guards（批次 6/9/12/4/Tier-1 + Batch 14 属性 12 测）
  **111 passed**。
- candidate 分析为独立脚本，不 import 生产管线写路径；"关闭候选
  分析"= 不运行该脚本，输出由生产代码唯一决定，零漂移结构性
  成立。

## 5. synthetic fixtures（观察通道确定性）

两字体（Helvetica / 第二 Base14）× 两字号（10/18）同构布局：
- font 集与 size 集均按预期分离为 2 值；重复运行逐项相等
  （deterministic repeat equal: True）。
- 已知局限如实登记：极简手写 PDF 无 FontDescriptor，第二字体
  在 pdfplumber 中解析为 `unknown`（真实语料 Batch 14 验收 C：
  no_attr=0，零 unknown）——不影响通道确定性与可分性结论。

## 6. Tier-2 候选层架构草案（11-A 冻结框架内）

- 位置：观察面旁路（零发射权），消费 Batch 14 词级属性 + 既有
  分组/分区几何，不触碰词边界、元素序、locator、relation。
- 候选对象：`(element_id, family_hypothesis, evidence_tuple)`
  ——evidence_tuple 例：`(digit_only, font_outsider, r≤1.11,
  page_position)`；候选**永不修改** type/metadata，仅供未来
  批次消费或评测对照。
- 消费点：本批不设。去重替换点、候选→抑制转换均需单独裁决
  （11-A 冻结条款）。
- 若立项实施批：需另行四项授权（目标/影响面/验收/push），验收
  至少含"候选通道关闭 = 输出零漂移"的结构性测试 + 候选统计
  可复现脚本 + 全量回归。

## 7. 设计轮结论

1. font 信号**确有新增判别力**，但仅存在于组合形态：
   digit∧fontOut（prod-01 家族，篇内零 FP）与 size-ratio×图邻接
   （acad-03，篇内干净沟）；单独 fontOut 因"样式化即圈外"的
   结构性反例而不可用。
2. 反例清单钉死：表单残留、continued、caption-miss、封面日期
   （裁定边界不变）为 font 惰性，Tier-2 对它们无收益。
3. 候选层可行性与仪器齐备（词级属性 + 元素映射 + 确定性）；
   实施与否、family 白名单、消费点全部留待裁决，本批零实现。

## 边界声明（r73）

本批不含实现权与 push 权；mixed 比例与阈值窗数字是观察面证据，
不是质量信号阈值；§3a 维持 deferred；G⑤ 与 2026-09-28
autonomous-track 周期简报独立。
