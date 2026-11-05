# 答辩材料底稿（FINAL_DEFENSE_MATERIALS）

> r104 裁决（2026-11-04）`APPROVED_TO_PROCEED`。13 节主线冻结（r104 §十七）。
> 本文件为讲稿底稿 + Q&A 备答；PPTX 制片时以本稿为唯一数字来源。
>
> **口径纪律（硬约束，逐页适用）**：
> ①不得省略 ARI NOT MET；②relation 必须同报 P/R/F1，不得只报 P=1.0；
> ③必须出示 fixed-anchor scope（acad-03 / 20 gold edges），不得称 corpus-wide；
> ④extended-N 只能作为诊断件，不得当实际系统结果；
> ⑤holdout 只能称 INFORMATIONAL / WITH_KNOWN_ANCHOR_EXPOSURE，不得称 strict blind。
> 可以强调的正面框架："系统相对冻结 baseline 有提升，且未达成部分已通过
> oracle / 粒度分析定位到结构约束。"

---

## 讲稿主线（13 节）

### 1. 问题与目标
- 问题：复合文档（PDF/DOCX，含图表/标题/表格混排）进入 KVFS 前需要
  结构化、可追溯的解析与分块。
- 目标：PDF/DOCX → 统一文档模型 → 结构分块 → Schema 校验 → JSON 的
  最小闭环原型。
- 范围声明（主动讲）：本阶段不做 Web UI / 真实 KVFS 接入 / 向量化 /
  OCR / 内核代码。

### 2. 确定性约束（本项目核心特色）
- 三无：无 OCR、无概率匹配、无学习式版面模型。
- 解析只用几何与结构事实；分块只用确定性规则；关系只用锚定 + 序数回退。
- 性质承诺：同一输入 + 同一依赖版本 ⇒ 逐字节稳定输出（第 11 节终测实证）。

### 3. 系统架构
- 管线：parse（parser 注册表，可插拔）→ chunk（结构分块）→ validate
  （Schema 写盘前强制关卡）→ write（JSON）。
- 工程面：批量多进程、JSONL 结构化日志、两阶段容器构建 + 校验和边车、
  CI 单 job 链（test → build → verify → artifact）。

### 4. 统一文档模型
- schema 0.6.0：element（type/content/parent_id/source_locator/confidence）、
  chunk（text + 非空 source_element_ids 保证可追溯）、relation（锚定关系）。
- source_locator 四 family 封闭（page_geometry / structural_index /
  line_address / container_line），PDF 与 DOCX 各有稳定定位。
- 顶层 source_hash（SHA-256）支持去重与追溯。

### 5. parser / chunk / relation
- parser：默认 fallback（pdfplumber + python-docx）；kreuzberg 保留可选
  （实测给不出元素级 locator——主动交代选型依据，见 Q&A-5）。
- chunk：标题硬边界、表格独立、max_chars=800 词界切分；"不丢不重"测试守护。
- relation：817 个硬边界派生 anchors + ordinal fallback；确定性规则链。

### 6. 评测设计
- 24 篇核心语料，dev / comparison / holdout 三 split；语料与金标私有，
  公开仓只登记 digest + revision。
- Layer A（结构化运行/校验）→ Layer B（13 自动指标 + chunk_boundary
  P/R/F1，容差 30 字符）→ Layer C（fixed-anchor 关系抽查）。
- comparison 回归门：核心指标相对劣化 >5% 判 regression。
- protected split 纪律：读取须逐次授权；终测恰一次授权已消耗后重新封闭。

### 7. 最终 r7 结果（FINAL_FROZEN_BASELINE）
| 指标 | r7 |
|---|---|
| unit_alignment | 0.8297 |
| extraction_coverage | 0.7635 |
| nontext_detection | 0.7004 |
| boundary_error_rate | 0.7378 |
| schema_valid | 24/24 = 1.0 |

### 8. baseline 对比
- baseline 链：r7 = FINAL_FROZEN_BASELINE（r6 SUPERSEDED、r5 HISTORICAL）；
  r8 不再需要。
- parser 双身份：canonical accepted revision = main b872347；evaluation
  execution implementation = adoption r7 port + 已披露 r55 C08 历史差异。
- ARI 面系统对两基线优势见第 9 节（相对 +26%）。

### 9. ARI 未达标及结构原因（必须完整讲，不得跳过）
| 项 | 值 |
|---|---|
| 原目标 | 0.75 — **NOT MET** |
| 本系统（1200 字符 macro ARI） | 0.3345 |
| 基线 B1 / B2 | 0.2658 / 0.2621 |
| 粒度天花板 oracle（@2000） | 0.4159 |
| 系统 / oracle | 80.43% |

- 归因：约 75% 差距为结构不可达（粒度错配）——oracle 上界本身低于目标；
  系统已显著超基线（相对 +26%）并达天花板八成。
- extended-N（约 10.7k 交叉点）= 诊断件，非生产建议（口径纪律④）。

### 10. relation recall limitation（必须完整讲，不得只报 P）
- P = 1.0 / R = 0.35 / F1 = 0.5185；caption F1 0.5、reference F1 0.5333、
  anchor classification 0.7。
- **scope = fixed-anchor 单文档抽查（acad-03 / 20 gold edges）**，
  非 corpus-wide。
- 24-core relation anchor binding = NOT_EXECUTED / DEFERRED_POST_FINAL，
  作为 limitation + future work 披露。

### 11. 可复现性（终测）
- 六要素执行前冻结（parser 身份 / runner / manifest / gold digest MATCH /
  deps / 指标配置）。
- 五步链全过；comparison gate = PASS / regressions = 0。
- 136 个稳定字段逐项精确相等 → REPRODUCED_IDENTICAL（逐字节级复现背书）。
- 证据包 manifest：docs/evidence-manifest.md（digest / role / revision /
  timestamp）。

### 12. demo
- 静态演示页 docs/demo.md（dev split 样本）：PDF prod-05（53 elements /
  31 chunks / 真实 relation ordinal_fallback"表 1"）；DOCX tech-05
  （332 elements / 190 chunks / 19 relations）。
- CLI 现场演示入口：app.cli parse / validate / explain-parser。

### 13. future work
- 24-core relation binding 与召回提升（deferred post-final）；
- 跨页段落重建与粒度对齐（针对 oracle 天花板的结构性差距）；
- OCR 受控降级路径；向量化语义检索与真实 KVFS 接入。

---

## Q&A 备答

**Q1：ARI 目标 0.75 没达到，怎么解释？**
A：如实承认 NOT MET，并给出结构归因：冻结金标上的 oracle 上界本身只有
0.4159（@2000），约 75% 的差距是分块粒度与金标粒度的结构不可达；系统
0.3345 已达天花板的 80.43%，且相对冻结基线（0.2658/0.2621）提升约 26%。
不主张"实质达标"，只主张"差距已定位到结构约束 + 相对基线显著提升"。

**Q2：relation P=1.0 看起来很完美？**
A：必须立即补 R=0.35 / F1=0.5185：规则链只在高置信锚出手，精确率换召回。
且这只是 acad-03 单文档 fixed-anchor 抽查（20 gold edges），不能外推为
24 篇 corpus-wide 结论；24-core binding 已明确 DEFERRED。

**Q3：holdout 结果可信吗？**
A：如实披露口径：INFORMATIONAL / WITH_KNOWN_ANCHOR_EXPOSURE（标注时
已知锚分布），不是 strict blind；所有 holdout 数字均带此限定陈述。

**Q4：结果能复现吗？**
A：终测做了执行前六要素冻结 + 136 个稳定字段权威比对，全部精确相等，
判定 REPRODUCED_IDENTICAL；证据 digest 见 docs/evidence-manifest.md。

**Q5：为什么默认 parser 不用功能更强的 OCR/学习式方案？**
A：项目约束是确定性（可审计、可复现、无概率依赖）；kreuzberg 实测给不出
元素级 source_locator 故不默认启用；扫描件支持明确列为 limitation/future
work，不冒充已支持。

**Q6：为什么不做向量化和 KVFS 接入？**
A：阶段范围裁决（最小闭环）；source_locator 与 source_hash 已为未来
KVFS 对接预留设计接口。

---

## 制片清单（PPTX 阶段）
1. 封面（项目名 + 成员 + 指导教师：格式字段由用户补）
2. 问题与目标（1 页）
3. 确定性约束（1 页，"三无"大字）
4. 系统架构图（1 页，管线 + 工程面）
5. 文档模型（1 页，element/chunk/relation 三卡）
6. 管线三段（parser/chunk/relation 各半页）
7. 评测设计（1 页，三层 + gate）
8. r7 指标表（1 页）
9. baseline 链（半页）
10. ARI 表 + 归因图（1 页，target/oracle 天花板可视化）
11. relation P/R/F1 + scope（1 页）
12. 复现性（1 页，136/136 + PASS/0）
13. demo 截图（1 页）
14. limitations + future work（1 页）
15. 致谢/Q&A
