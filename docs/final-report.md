# 结题报告（FINAL_REPORT_AND_DELIVERABLES）

> r103 裁决（2026-11-03）`APPROVED_TO_START`，13 节结构冻结。本报告为仓内技术结题文档；
> 面向学校提交的结题材料可在本报告基础上按模板改写，数字面以本报告与
> `docs/evidence-manifest.md` 登记值为准。
>
> 状态基线：`FINALIZATION_MODE = FINAL_FROZEN`；`r7 = FINAL_FROZEN_BASELINE`；
> 终测 `REPRODUCED_IDENTICAL`（136/136 稳定字段精确相等）。

---

## 1. Project objective / scope（项目目标与范围）

面向 KVFS 的复合文档解析与结构-语义分块原型：将 PDF/DOCX 复合文档确定性转换为
统一文档模型，经结构分块与 Schema 校验输出可追溯 JSON，为下游 KVFS 存取与检索
提供结构化输入。

本阶段（最小闭环）达成：**PDF/DOCX → 统一文档模型 → 结构分块 → JSON Schema
校验 → JSON 输出**，并以 24 篇核心语料的分层评测体系对质量做出可复现度量。

本阶段明确不做：Web UI、真实 KVFS 接入、向量化 / Sentence-BERT、OCR、
cpp-chunker、内核代码、流式处理（范围裁决见 README §0 与项目 CLAUDE.md）。

## 2. Deterministic architecture（确定性架构）

整条管线**无 OCR、无概率匹配、无学习式版面模型**：

- 解析层只用几何与结构事实（PDF 字符/线框几何、DOCX 段落/表格样式）；
- 分块层只用确定性规则（标题硬边界、表格独立、长度上限、词界切分）；
- 关系层只用锚定与序数回退（anchor + ordinal fallback），不引入"最近邻"式启发式；
- 同一输入 + 同一依赖版本 ⇒ 逐字节稳定的输出（该性质由第 10 节终测验证）。

确定性边界、已知非确定域（如外部库告警顺序）与降级行为在 README §0.2 披露。

## 3. Unified document model（统一文档模型）

统一 JSON 文档模型（schema 0.6.0，`schemas/document.schema.json`）：

- **element**：type（heading/paragraph/table/image/…）、content、parent_id、
  `source_locator`（按 locator family 路由：page_geometry 含 page/bbox、
  structural_index 含 paragraph_index/table_index 等，四 family 封闭不新增）、
  confidence、metadata；
- **chunk**：text + 非空 `source_element_ids`（保证每个 chunk 可追溯到原始 element）；
- **relation**：锚定关系（has_caption / has_reference 等）带 anchor 分类与证据；
- 顶层 `source_hash`（SHA-256）支持去重与追溯；writer 一律输出 0.6.0。

schema 校验是写盘前强制关卡：校验失败不产生半成品文件。

## 4. Parsing / chunking / relation pipeline（解析 / 分块 / 关系管线）

- **解析**：默认 `fallback` parser（pdfplumber 0.11.10 + python-docx 1.2.0）；
  `kreuzberg` 4.10.2 保留为可选路径（实测给不出元素级 locator，见 README §7）。
  Parser 注册表（Stage 8 批次 18–24）提供能力快照、扩展名发现、选择解释、
  竞争审计、身份与来源追溯；外部插件经 `--plugin` 显式加载（fail-fast，不静默覆盖）。
- **分块**：结构分块器——标题硬边界、table 独立 chunk、`max_chars` 长度切分
  （默认 800）、词界优先；"不丢不重"由统一规范化文本拼接比较测试守护。
- **关系**：从 817 个硬边界派生 anchors，序数回退（ordinal fallback）匹配
  caption/reference；关系抽取为确定性规则链（无学习式模型）。
- **工程面**：批量多进程、JSONL 结构化日志、容器交付两阶段构建 + 校验和边车 +
  CI 单 job 链（test → build → verify → artifact，见 README §3.6）。

## 5. Evaluation methodology（评测方法学）

- **语料**：24 篇核心文档（dev / comparison / holdout 三 split）；语料与 gold
  为私有 gitignored 数据，公开仓只登记 digest 与 revision。
- **层次**：Layer A（结构化运行/校验）→ Layer B（13 项自动指标 + 3 项
  figure_caption + chunk_boundary P/R/F1，容差 30 字符）→ Layer C（fixed-anchor
  关系评测，仅 acad-03 / 20 gold edges 抽查）。
- **门槛**：comparison split 回归门——核心指标相对劣化 >5% 判 regression；
  candidate 须对照前驱 accepted revision。
- **口径**：比例指标分母为 0 返回 null + reason，不返回 1.0；聚合按 counts 求和 /
  rates 求 rate / ratio 宏平均，不出"综合分数"；ARI 面预登记后实跑，零调参。
- **纪律**：comparison/holdout 为 protected split，读取须逐次授权；holdout 全部
  结果口径 = **INFORMATIONAL / WITH_KNOWN_ANCHOR_EXPOSURE**（标注时已知锚分布，
  不得包装为 strict blind）。

## 6. Final r7 metrics（r7 最终指标）

`r7 = CURRENT_ACCEPTED_BASELINE / FINALIZATION_BASELINE`（canonical parser
revision = `main b872347`），comparison split 门四指标（终测复现确认）：

| 指标 | r7 值 |
|---|---|
| unit_alignment | **0.8297** |
| extraction_coverage | **0.7635** |
| nontext_detection | **0.7004** |
| boundary_error_rate | **0.7378** |
| schema_valid（24 docs） | **24/24 = 1.0** |

评测配置（冻结）：max_chars=800、tolerance_chars=30、marker_max_chars=40、
双 parser（fallback + kreuzberg）、macro per split。

## 7. Baseline comparison（基线链对比）

baseline 链终态（r103 §七）：`r7 = FINAL_FROZEN_BASELINE`；r6 =
SUPERSEDED_ACCEPTED_BASELINE；r5 = HISTORICAL_NON_BASELINE；r8 = NOT_STARTED
且结题不再需要（终测产物是复现快照，不是新 revision）。

ARI 面系统与基线对比见第 8 节表。

**parser 双身份写法**（r103 §五 record-precision）：

- canonical accepted parser revision = `main b872347`
- evaluation execution implementation = `adoption r7 port with previously
  disclosed r55 C08 delta`（40 变更行历史差异，r7 实跑树自身状态，经终测
  136/136 复现证明行为稳定）

不得简写 "terminal execution bytes = b872347"。

## 8. ARI target and structural-gap analysis（ARI 目标与结构性差距分析）

原目标 ARI ≥ 0.75。最终判定（r102 §226/§227 结案，r103 确认不变）：

| 项 | 值 |
|---|---|
| 目标 | 0.75 — **NOT MET** |
| 本系统（1200 字符 macro ARI） | **0.3345** |
| 基线 B1 | 0.2658 |
| 基线 B2 | 0.2621 |
| 粒度天花板 oracle（@2000） | **0.4159** |
| 系统 / oracle | 80.43% |

**归因**：约 75% 的目标差距为结构不可达（粒度错配，granularity mismatch）——
oracle 上界本身低于目标，说明差距主要来自分块粒度与 gold 粒度的结构差异，
而非对齐质量；系统已达天花板的 80.43% 并显著高于两基线（+26% 相对）。
extended-N 诊断为诊断件，**不构成生产建议**。

## 9. Layer C relation evaluation（Layer C 关系评测）

**正式范围 = fixed-anchor relation evaluation，仅 acad-03、20 gold edges 抽查**；
不得改写为 "24-doc corpus-wide relation accuracy"。

| 指标 | 值 |
|---|---|
| relation P / R / F1 | **1.0 / 0.35 / 0.5185** |
| caption F1 | 0.5 |
| reference F1 | 0.5333 |
| anchor classification | 0.7 |

高精确率（1.0）+ 低召回（0.35）表明规则链只在高置信锚上出手；24-core
relation anchor binding = **NOT_EXECUTED / DEFERRED_POST_FINAL**，
`RELATION_ENGINEERING = CLOSED_FOR_FINALIZATION`，作为 limitation / future work
披露（见第 11 节）。

## 10. Final reproducibility run（终测复现）

`FINAL_LOCKED_R7_REVALIDATION`（r102 R-2 批准，r103 ACCEPTED）：
revision = `stage9-eval-terminal-reval-r1`（独立目录，不覆盖 r7）。

- **六要素执行前冻结**（freeze_record.json）：①parser 双身份（见第 7 节）
  ②runner sha256 f85320bd… ③manifest 51d3d400… ④gold = stage9-b26-gold-r1，
  digest 运行时重算 8b0c2a8c… == credential MATCH ⑤deps：python 3.12.10 /
  pdfplumber 0.11.10 / python-docx 1.2.0 / kreuzberg 4.10.2 / jsonschema 4.26.0
  ⑥指标定义（max_chars=800、tolerance=30、marker=40、双 parser、macro per split、
  layerC 仅 acad-03）。
- **五步链**：prepare（817 硬边界）→ layerA（双 parser run/validate rc 0）→
  layerB（48 process_single rc 0）→ aggregate（system_errors 46，taxonomy 稳定）→
  gate：**PASS / regressions = 0**。
- **权威比对**：136 个稳定字段（layerB 聚合 + layerC + parser versions + 逐篇
  稳定计数 + error registry + 冻结配置参数）逐项精确相等，mismatches = 0 →
  **`REPRODUCED_IDENTICAL`**。wall-clock / timestamps / machine metadata 在比对面
  排除。
- 证据包 manifest（digest / role / revision / timestamp）见
  `docs/evidence-manifest.md`。

## 11. Known limitations（已知局限）

1. **ARI 目标未达**（0.75 NOT MET；粒度归因，见第 8 节）。
2. **Layer C 范围有限**：fixed-anchor 单文档抽查（acad-03 / 20 edges），
   非 corpus-wide；召回 0.35 偏低。
3. **24-core relation anchor binding 未执行**（NOT_EXECUTED /
   DEFERRED_POST_FINAL），关系工程已为结题关闭。
4. **holdout 口径**：INFORMATIONAL / WITH_KNOWN_ANCHOR_EXPOSURE，非 strict blind。
5. **kreuzberg 路径能力受限**：给不出元素级 source_locator，默认不启用。
6. **无 OCR**：扫描件 PDF 不在支持范围。
7. **跨页段落重建、语义检索、真实 KVFS 接入**均未做（范围外，见第 1 节）。

## 12. Demo / usage（演示与使用）

- 静态演示页 `docs/demo.md`（r102 R-3 / r103 ACCEPTED，dev split 样本）：
  PDF prod-05（53 elements / 31 chunks / 真实 relation e0033→e0030
  ordinal_fallback"表 1"）与 DOCX tech-05（332 elements / 190 chunks /
  19 relations）的解析→分块→关系→校验→JSON 全链展示。
- CLI 入口（`app.cli`）：`parse` / `validate` / `batch-parse` / `list-parsers` /
  `explain-parser` / `audit-parsers` / `inspect-parser`；评测入口
  `evaluation.cli run / validate-report`。
- 复现入口与终测件指向见 README §0.7；容器构建与交付验证见 README §3.6。

## 13. Future work（后续工作）

- 24-core relation anchor binding 与关系召回提升（deferred post-final）；
- 跨页段落重建与更细粒度的 gold 对齐（针对粒度天花板的结构性差距）；
- OCR（Tesseract / PaddleOCR）纳入受控降级路径；
- 向量化 / Sentence-BERT 语义检索与真实 KVFS 接入；
- Table Transformer 微调、cpp-chunker 加速、Web UI（原阶段外目标）。

> 以上 1–13 节构成 r103 §十三冻结结构。本报告所有数字均为已裁决登记值；
> FINAL_FROZEN 模式下如需修正仅允许不改语义的笔误 / 格式修复。
