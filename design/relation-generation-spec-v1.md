# design/relation-generation-spec-v1.md — 题注/关联通道规格（P1 调查 + 规格，不含实现）

- 授权：r84 Q2 Priority 1（授权调查 + 规格设计，不立即实现；实现须单独
  main engineering proposal + 裁决）
- 日期：2026-10-09。基准证据：stage9-eval-baseline-r1 产物 + main 侧
  只读调查（本件所有 file:line 于 2026-10-09 核对）
- 状态：SPEC v1（调查结论 + 设计提案；零代码改动）

## 1. 调查结论（r84 三问之首：relation 生成面是否存在）

**结论：不是空白面。** fallback parser 有完整题注关联实现：

- 四个匹配器（纯函数）：`match_caption_relations_docx` /
  `match_caption_relations_pdf` /
  `match_table_caption_relations_docx` /
  `match_table_caption_relations_pdf`
  （app/parsers/fallback_parser.py:81/:108/:168/:191）
- 装配点：fallback_parser.py:944-952，写进 Document.relations
  （app/models.py:149；Relation 4 字段：type/from_id/to_id/metadata）
- schema 侧：relation.type 为自由串（0.6.0 无枚举约束），现有类型
  contains / has_caption / table_has_caption；评测 figure_caption_* 指标
  只消费 has_caption（docs/relation-consumption-contract.md）

## 2. baseline 实测地面真值（stage9-eval-baseline-r1，fallback，24 篇）

- 6/24 篇产出非零 relations，共 78 条：has_caption 68（acad-05 1 /
  acad-07 8 / acad-08 6 / tech-02 1 / tech-08 52）+
  table_has_caption 10（tech-05）
- 18/24 篇零 relations；锚面 acad-03 = img 28 / tab 9 / **cap 0** → 零边
- 修正 r84 简报表述："fallback 零 has_caption relation" 仅对锚面单篇
  （acad-03）成立；通道全局存在且部分命中，问题定性从"功能空白"改为
  "**题注侧召回失败 + 显式引用通道未实现**"

## 3. acad-03 零边根因链（三层，逐层实证）

1. **抽取层**：pdfplumber 对该 PDF 的 word 抽取无空格，题注文本形如
   `Figure3:Thearchitectureandpre-trainingobjectivesofLayoutLMv3`、
   `Table1:Comparisonwithexistingpublishedmodels…`（分隔符为冒号）
2. **类型层**：`_CAPTION_RE`（fallback_parser.py:50）要求数字后跟
   `[\.、\s]` 之一——冒号不在类内 → `_is_caption` 拒绝 →
   `_classify_pdf_paragraph`（:346）定型为 paragraph → 该篇 cap=0
   （实证：5 条题注前缀文本全部定型 paragraph，e0030/e0047/e0050/
   e0053/e0058）
3. **匹配器层**：`_FIGURE_CAPTION_RE`（:62）与 `_TABLE_CAPTION_RE`
   （:156）与 _CAPTION_RE 同分隔符类——即使类型层修好，冒号形题注仍被
   匹配器拒绝（双重失守）
- from 侧不缺：acad-03 img=28 / tab=9（pdfplumber image objects +
  table finder 均产出）；瓶颈纯在 caption 侧
- gold 对照：acad-03 credential 抽查 20 边 = 题注 9 + 显式引用 11；
  当前实现即使全修也只覆盖题注 9 边

## 4. 第二缺口：显式引用（explicit reference）通道真空白

- gold 11/20 边是"正文显式引用图表"（如 "as shown in Figure 3"）型
  ——**当前 pipeline 无任何实现**（四匹配器全部是邻接/几何题注附着，
  无正文引用检测）
- 这是真·功能新增，需独立规格（见 §6 W2）

## 5. gold ↔ 产品需求映射（r84 三问之二）

- 题注附着（9 边）↔ 现有 has_caption/table_has_caption 契约
  （docs/caption-relation-contract.md、
  docs/table-caption-relation-contract.md）——契约已冻结，修的是召回
- 显式引用（11 边）↔ 无契约、无 schema 消费方——需求真实性目前唯一
  依据是 credential 抽查记录本身；是否为产品需求待裁（r85 问）

## 6. 设计提案（拆三件工作，各自独立授权，均落 main）

- **W1 题注定型与匹配召回修复**（parser 改动，main）：分隔符类扩展
  `[\.:、\s：]`（半角/全角冒号），同步改 _CAPTION_RE / _FIGURE_CAPTION_RE /
  _TABLE_CAPTION_RE 三处；风险面 = 正文句首 "Figure 3 shows…" 被误定型
  caption（现状已存在该风险，扩展冒号不扩大句首风险）；预期 acad PDF 组
  题注边从 0 起步可测
- **W2 显式引用 relation 生成**（新能力，main）：段落 content 内检测
  `Figure N` / `Table N` 引用 → `references_figure` 边（from=段落元素，
  to=被引 image/table；编号→元素映射按文档内图表出现序，确定性规则，
  无概率匹配）；**边类型名与方向为开放设计问题，须裁决**
- **W3 评测对齐**（adoption 侧）：Layer B 锚面 pred 匹配条件已按题注边
  定义（from ∈ {image,table} + marker ⊂ caption content）；W2 生效后
  需扩锚面指标到引用边（evaluation revision r2 时一并裁）
- 效果度量：evaluation revision 升版条件 B（任一核心指标 ≥5% 变化）即
  W1/W2 的验收通道；acad-03 anchor edge_recall 从 0.0 起步

## 7. schema 稳定性（r84 三问之三）

- relation.type 自由串 → 新增 references_figure 不需 schema_version 升版
- Element.type 枚举已含 caption → W1 不动 schema
- 契约文档需扩（relation-consumption-contract 若消费引用边）→ 契约变更
  属 main 侧提案的一部分

## 8. 非目标

- 不做概率/模糊匹配、不引入 OCR、不引入布局模型（确定性规则红线）
- kreuzberg 零改动（comparison_only，r84 Q4）
- 本件不授权任何代码改动；W1/W2 各自提案再裁

## 9. 开放问题（下一裁决面）

1. W2 边类型命名与方向（references_figure？figure_referenced_by？）
2. W2 是否计入 Phase 2 首批（gold 11/20 边在锚面，但需求真实性仅凭
   credential 抽查记录）
3. W1 是否单独先行（最小改动、可独立验收）

## 10. r85 裁决落定与执行回执（2026-10-09 追记）

§9 三问全部裁掉：Q2(a) 方向 = references_figure / references_table
（text → object，provenance 优先）；Q2(b) W2 入首批不等 W1；
Q2(c) ordinal document-order 映射接受为 v1 语义（确定性红线）。

执行结果（均当日，main 侧）：

- **W1 实施**：commit ee80799（三正则分隔符类 + 契约 §1a + 表契约
  镜像 + 37 用例 + 全量 5522 通过；验收 acad-03 caption 元素 0→5、
  has_caption 0→1）。adoption 传播 cherry-pick 0e5f1d4。
- **W2 design freeze**：docs/explicit-reference-relation-contract.md
  v1（提及正则、两层解析、metadata 常量、排除面、验收标准）。
  设计要点偏离裁决文本处如实披露：拉丁词边界环视被撤——glued 无
  空格形 "wordFigure3" 是主目标形（acad-03 正文实测 10 处 vs 分隔形
  4 处），环视会挡掉主目标；"turntable 5" 词内噪声为已知代价。
- **W2 实施**：commit 516c728（match_reference_relations 纯函数 +
  pdf/docx 双装配 + 12 用例 + devset 契约基线升级；全量 5534 通过）。
  **验收（ruling v1 标准）**：gold 11 条显式边 Layer C 规则命中
  8/11（P=0.8 / R=0.40 / F1=0.533；r1 为 P=null / R=0.0）；负向句例
  全过。
- **W3**：Layer C 指标（edge P/R/F1 分立报告）已进
  scripts/stage9_eval_baseline.py（caption 边 + 引用边双分支匹配器，
  勘误后 9+11 权威计数）。

## 11. 遗留测量面缺口（下一裁决候补，非实现缺陷）

题注边匹配受文本形制差阻断：gold 题注单元有空格（"Figure 3: The
architecture…"）vs pdfplumber 预测题注文本无空格（"Figure3:The…"）
→ marker 子串匹配系统性失败（acad-03 W1 后 matched_caption=0/9，
单条预测题注边在但无法对上金边）。显式引用面不受此影响（正文抽取
有空格，8/11 命中）。可选处置 = Layer C marker 匹配加空白不敏感
变体——属评测方法学变更，不热改，r86 面裁。
