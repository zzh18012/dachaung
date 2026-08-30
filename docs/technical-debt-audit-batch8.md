# 批次 8 技术债审计（Stage 6 尾声）

状态：v1（2026-08-30，批次 8 裁决①–④全项执行）。
裁决依据：ADOPTION §三十三（批次 7 封口裁决指定批次 8 清单与验收标准）。

## ① TODO/FIXME 审计

扫描范围：`app/ evaluation/ tests/ scripts/ docs/` 全部 `.py/.md/.json/.toml`
（grep -i "TODO|FIXME|XXX"，排除 .venv）。

**结论：零真实债务标记。**

全部命中（6 处）均为 markdown 任务列表字面量（`- [ ] todo` /
`- [x] done`），属 `tests/test_parsers_markdown_edges11.py` 的契约测试
内容与 `samples/private/devset-md/md-lists-nested.md` 夹具数据，语义上
是"待测输入"而非"待办事项"。

分类清单：

| 类别 | 数量 | 处置 |
|---|---|---|
| 可立即修复 | 0 | — |
| 需专项设计（backlog） | 0 | — |
| 已过时（删除） | 0 | — |

## ② 评测覆盖缺口分析

### 语料 × manifest × 标注矩阵（实测 2026-08-30）

| devset | manifest | 文档数 | expectations | annotations | 说明 |
|---|---|---|---|---|---|
| devset（主） | 1.0 | 2（pdf1+docx1） | 2/2 | 1/2（仅 docx） | 另有 3 条 expected_failures |
| devset-md | 1.1 | 6 | 6/6 | 0/6 | 批次性验收语料 |
| devset-html | 1.1 | 5 | 5/5 | 0/5 | 同上 |
| devset-text | 1.1 | 5 | 5/5 | 0/5 | 同上 |
| devset-ipynb | 1.1 | 5 | 5/5 | 0/5 | 同上 |
| devset-regressions | 1.1 | 3 | 3/3 | 0/3 | 回归对照 |
| devset/real-01..05 | —（未入 manifest） | 10 文件 | 0 | 0 | 真实语料 + worksheets 已备，devset_status=incomplete 的主因 |

### 指标族 × 覆盖状态

| 指标族 | 主 devset 状态 | 瓶颈 |
|---|---|---|
| element_count_by_type / silent_drop / required_markers | 2/2 文档评测 | 无（已覆盖） |
| chunk_boundary_* | 仅 DC-MVP-001 有值（9 anchors，f1≈0.69）；PDF 恒 null(no_annotation) | PDF 无 annotation 文件 |
| figure_caption_* | 恒 null：docx=no_annotation_pairs（pairs 空）、pdf=no_annotation | **零 GT 对：全 devset 无一条 figure_caption_pairs** |
| table_caption_* | 未实现（批次 7 §7 冻结） | annotation v1.0 无 GT 键（additionalProperties=false）+ 零标注 |
| heading_order（GT） | **已采集（8 条）但零消费**——无任何指标族读它 | 指标族未设计（发现项：死数据） |
| forbidden_markers | 主 devset v1.0 manifest 不允许该键 → 恒未声明 | 需 manifest 升版或弃用（非债，属设计现状） |

### parser × format 覆盖

fallback × {pdf, docx, markdown, html, text, ipynb}：全部有评测
manifest 且批次性验收过。kreuzberg × {pdf, docx}：可选路径，无任何
评测 manifest（CLAUDE.md 记录其 elements 为空的实测结论，保留为未来
升级路径——不构成当前债）。

### 待标注优先级清单（按 devset 扩展 ROI 排序）

1. **P1｜DC-MVP-001 补 figure_caption_pairs（1 对）**：标注成本最低
   （文档仅 1 图 1 题注，parser 已产出 relation e0018→e0019），解锁
   figure_caption_* 全链路从恒 null 变为真实 P/R/F1。预估 0.5h 人工。
2. **P2｜DC-MVP-001-PDF 补 annotation_file**（chunk_boundary_anchors
   + figure_caption_pairs）：解锁 PDF 侧两个指标族。预估 1h 人工
   （PDF 题注融合问题需人工判定 GT 口径）。
3. **P3｜heading_order GT 消费指标族设计**：数据已存在，缺评测批次
   （GT 对照版 heading 结构指标 + REPORT_VERSION 升版评估）。
4. **P4｜table_caption_* 指标族**：annotation v1.1 新键（additionalProperties
   =false 需升版）+ 标注 + 指标族（批次 7 §7 已预留议项）。
5. **P5｜real-01..05 真实语料入 manifest**：worksheets 已备；incomplete
   → 扩展的主要路径，但牵动 manifest 冻结纪律，需独立批次规划。

## ③ Holdout 维护成本评估

资产清单（10 个 kit，对应裁决"7 轮 holdout 含批次 3 预备跑"）：

| kit | 位置 | 批次 |
|---|---|---|
| holdout-chunker-ipynb / -spans | samples/private/ | Stage 6 前期 |
| holdout-md / -html / -text | samples/private/ | Stage 4.5/5 |
| holdout-locator-family | samples/private/ | 批次 3 |
| holdout-ipynb | samples/private/ | 批次 1.x |
| holdout-caption | samples/synthetic/ | 批次 4 |
| holdout-table | samples/synthetic/ | 批次 5 |
| holdout-table-caption | samples/synthetic/ | 批次 7 |

维护模型：**一次性封存，零持续维护**——expectations 冻结于 parser
运行前；首跑报告封存 outputs/（gitignored）永不重跑；夹具 sha256
登记 ADOPTION.md，漂移即守卫拒跑；夹具字节受 git 保护。唯一残余成本：
未来 schema/契约语义变更需考古旧 expectations 时的人工阅读成本
（预估每轮 ≤1h，低频）。

**"holdout 期望生成器"工具：建议不做。**理由：holdout 的价值恰在
"parser 运行前人工独立推导期望"（裁决⑤纪律的核心）；自动从 parser
输出生成期望 = 用被测对象产生期望，自证循环，holdout 将退化为普通
回归测试；机械对照需求已由 dev 验收/回归测试覆盖。若未来夹具复杂度
超出人工推导承受范围，再议"半自动大纲辅助（仅供人工推导参考）"，
全自动生成器始终不做。

## ④ Schema 兼容性回归测试

新增 `tests/test_schema_compat_regression.py`（10 项，全部通过）：

- **旧→新（读兼容）**：0.1.0 pdf/docx 时代形状、0.2.0 spans 形状、
  0.3.0 family 形状、0.4.0 has_caption 形状、0.5.0 双 relation 形状
  全部通过当前 schema 校验（policy §4 承诺落地为测试）。
- **写能力**：当前 writer 一律输出 0.5.0（不产出任何旧版本）。
- **新→旧（消费兼容）**：0.5.0 混排文档喂给"只认识 has_caption"的
  模拟批次 6 consumer——跳过未知 type 不报错不误读；真实 evaluator
  路径 match_relation_pairs(relation_type="has_caption") 在混排文档
  上行为不变 (1,1,1)；纯 table_has_caption 文档降级为 0 预测
  (0,1,0) 不崩溃。

## 交付物汇总

- 本文档（分类清单 + 优先级 + 工时估算）。
- tests/test_schema_compat_regression.py（schema 双向兼容，10 项）。
- 立即修复：**无**（①零标记、④已转测试固化、②③为设计/数据项转
  backlog）。
- Backlog GitHub issues（tech-debt 标签）：P1 标注解锁、P2 PDF 标注、
  P3 heading_order 消费、P4 table_caption_*、P5 真实语料入 manifest
  ——见 ADOPTION §三十四登记的 issue 链接。

## 验收对照（裁决验收标准）

- 无遗漏 TODO：✅（零真实标记，分类表为空）。
- 评测覆盖矩阵可视化：✅（本文档三张表）。
- Schema 兼容性测试通过（旧→新/新→旧双向）：✅（10/10）。
