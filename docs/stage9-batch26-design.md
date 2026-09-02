# Stage 9 批次 26 步骤 1 设计：结题语料与标注基线

状态：设计稿（待 GPT 裁决）。依据：Stage 9 立项裁决（2026-09-02，ADOPTION
§六十六）——条件批准，本轮仅授权设计汇报；未授权 manifest 冻结、批量下载、
实现代码、新增依赖。

## 0. 裁决遵从对照

| 裁决要求 | 本设计章节 |
|---|---|
| 语料构成表（≥20 篇、三域、版式分布） | §1（24 篇候选，20 为下限） |
| manifest 与冻结协议 | §2 |
| 人工标注格式（句子为 ARI 原子单位） | §3 |
| holdout 纪律（14 dev / 6 holdout） | §4 |
| 基线定义（零依赖、参数冻结） | §5 |
| 质量与复核方案 | §6 |
| 提交物与停机门槛 | §7（含一处澄清请求） |

## 1. 语料构成表（候选清单，未采集）

目标：≥20 篇去重文档，覆盖学术论文 / 技术报告 / 产品手册三域，PDF 14–16
篇 + DOCX 4–6 篇，中英文混合。24 篇候选（20 正选 + 4 备选），全部为公开、
可合法获取与研究所用来源；**采集时逐篇核实许可证，核实不通过即以备选补位
并登记**。每篇采集后记录：来源 URL、许可证、抓取日期、SHA-256、页数、
版式标签（见 §2）。

| # | 域 | 候选 | 格式 | 语言 | 版式特征（预期，采集时核实） |
|---|---|---|---|---|---|
| 1 | 学术 | Sentence-BERT（arXiv:1908.10084） | PDF | EN | 双栏、公式、表 |
| 2 | 学术 | LayoutLM（arXiv:1912.13318） | PDF | EN | 双栏、图 |
| 3 | 学术 | LayoutLMv3（arXiv:2204.08387） | PDF | EN | 双栏、图表 |
| 4 | 学术 | Docling（arXiv:2501.17887） | PDF | EN | 双栏、图 |
| 5 | 学术 | PubTables-1M（arXiv:2110.00061） | PDF | EN | 双栏、表格密集 |
| 6 | 学术 | DMAP（arXiv:2601.18203，申请书引用[1]） | PDF | EN | 双栏、图表 |
| 7 | 学术 | 中文期刊公开论文 1（开放获取，来源采集时定） | PDF | CN | 双栏/单栏 |
| 8 | 学术 | 中文期刊公开论文 2（同上） | PDF | CN | 双栏/单栏 |
| 9 | 技术 | WCAG 2.2（W3C 公开规范） | PDF | EN | 单栏、多级标题、表 |
| 10 | 技术 | NIST AI RMF 1.0（美国政府公有领域） | PDF | EN | 单栏、表 |
| 11 | 技术 | 中国信通院公开白皮书（公开分发） | PDF | CN | 单栏、图表 |
| 12 | 技术 | 国家/行业标准公开征求意见稿（公开渠道 DOCX） | DOCX | CN | 单栏、表格 |
| 13 | 技术 | 公开机构年度报告（如已有 real-02 同类，另选） | DOCX | CN/EN | 单栏、表 |
| 14 | 技术 | 公开技术评估报告（政府/非营利机构） | PDF | EN | 单栏 |
| 15 | 产品 | Python 官方教程 PDF（PSF 许可） | PDF | EN | 单栏、代码块、多级标题 |
| 16 | 产品 | LibreOffice Writer 指南（CC-BY-SA） | PDF | EN | 单栏、图、表 |
| 17 | 产品 | GIMP 用户手册（CC-BY-SA） | PDF | EN | 单栏、图 |
| 18 | 产品 | 开源项目中文手册（如国产开源软件文档） | PDF/DOCX | CN | 单栏 |
| 19 | 产品 | 公开产品白皮书（厂商公开分发） | DOCX | CN | 单栏、表、图 |
| 20 | 产品 | 用户私有产品文档（用户按裁决 C 提供） | DOCX | CN | 待定 |
| 21 | 备选 | 学术备选（arXiv 检索补充） | PDF | EN | 双栏 |
| 22 | 备选 | 技术备选（EN 政府公开报告） | PDF | EN | 单栏 |
| 23 | 备选 | 技术备选（CN 公开白皮书） | PDF/DOCX | CN | 单栏 |
| 24 | 备选 | 产品备选（开源手册） | PDF | EN | 单栏、图 |

版式分布预期（正选 20 篇）：多栏 ≥5（学术域天然满足）；含表 ≥12；含图
≥10；标题层级 ≥2 级 ≥16；页数跨度 8–300 页（产品手册补长文档）。
去重与近重复：按 SHA-256 去重 + 标题/正文抽样人工比对近重复（同系版本只取
一份），结果写入采集报告。

诚实申报：公开 DOCX 是最弱获取渠道（#12/#13/#19），若核实不足，缺口由
#20（用户私有）与备选补足；最终 DOCX 数若 <4，在偏差清单登记并请裁决。

## 2. manifest 与冻结协议

文件：`samples/private/stage9-corpus/manifest.draft.json` → 冻结为
`manifest.json`。字段（每文档）：

```json
{
  "doc_id": "acad-01-sentencebert",
  "domain": "academic | tech_report | product_manual",
  "source_url": "https://arxiv.org/pdf/1908.10084",
  "license": "arXiv non-exclusive license（采集时按文档实际声明核实）",
  "fetched_date": "2026-09-XX",
  "sha256": "…（采集后计算）",
  "format": "pdf | docx",
  "language": "en | zh | mixed",
  "page_count": 12,
  "layout_tags": {
    "columns": "single | multi",
    "has_tables": true,
    "has_images": true,
    "heading_depth": 3,
    "approx_chars": 42000
  },
  "split": "dev | holdout"
}
```

冻结协议：设计获批 → 采集 + 哈希 + 逐篇许可证核实 → manifest.json 定稿
→ 其 SHA-256 登记入 ADOPTION → **此后任何变更（替换/删除/改字段）一律
走新版本文件 + 单独裁决**，旧版本永不覆写。draft 阶段可改。

## 3. 人工标注格式（句子为 ARI 原子单位）

标注对象：**人眼可见的正文句子流**（heading 也作为一个 unit）。表格与图
像不进句子流，另行登记为非文本单元并挂 gold_segment。

句子切分器（冻结版本 v1，零依赖）：中文按 。！？；切分；英文按 .!? 后随
空白+大写/数字切分；缩写白名单（Fig. Eq. et al. Dr. No. vs. i.e. e.g.
etc.）不切；省略号不切。实现一经冻结不改；若发现缺陷，升 v2 并全量重切
+ 变更登记。

规范化口径：与既有"分块不丢不重"测试同源——全部空白折叠为单空格、strip
两端；每篇文档拼接成**规范化字符流**，unit 记录其在该流上的 char_span。

标注文件（每篇一个 JSON，`samples/private/stage9-corpus/annotations/
<doc_id>.json`，永不进 git）：

```json
{
  "doc_id": "acad-01-sentencebert",
  "sentence_splitter": "v1",
  "normalization": "fold-ws-v1",
  "annotator": "claude-draft + user-review",
  "units": [
    {
      "unit_id": "u0001",
      "kind": "heading | sentence | nontext",
      "page": 1,
      "char_span": [0, 87],
      "norm_text_hash": "sha256:…",
      "text_preview": "Sentence-BERT: Sentence Embeddings …",
      "gold_segment_id": "g01",
      "hard_boundary_before": true,
      "linked_nontext": ["img:figure1", "tab:table2"]
    }
  ],
  "segments": [
    {"gold_segment_id": "g01", "hint": "标题+摘要", "kind": "frontmatter"}
  ]
}
```

gold_segment = 人工判定的语义段（主题内聚的知识单元）；`hard_boundary_
before` 标记人工确定的硬边界（章节切换等）。

**预测块→句子的投影规则**（ARI 评测共用）：预测 chunk 的 text 经同一规范
化映射到字符流 span；与某 unit 的 char_span 相交即候选归属；一个 unit 跨
多个 chunk 时按最大重叠归属唯一 chunk（跨块 unit 计数另行披露，不静默）；
非文本单元不参与 ARI，单独计关联指标。

标注纪律（沿袭 holdout 规则）：**逐句人工查阅原文推导 gold_segment，禁止
用任何系统输出（本系统或基线）反推**；标注在解析运行之前完成 holdout 集。

## 4. holdout 纪律

- Split：20 篇 → **dev 14 / holdout 6**，分层因子 = 域(3) × 格式(2)；
  holdout 6 = 每域 2 篇（域内 PDF/DOCX 各≥1 尽量满足，DOCX 不足时如实
  登记偏差）；三域在 dev/holdout 均覆盖。
- 基线与本系统的**参数搜索只在 dev**；holdout 只在最终评测跑一次，报告
  封存。
- 机械对照（基线 vs 本系统的中间对照）只在 dev；如需额外机械对照集，另设
  comparison split，不占用 holdout。
- 全部去重/近重复检查结果写入采集报告（§1）。

## 5. 基线定义（零依赖）

两基线均自实现（不引入 langchain），与 ARI 管道同源投影：

- **B1 固定长度切分**：规范化字符流上按 N 字符硬切，无重叠、无分隔符；
  N ∈ {200, 500, 800, 1200, 2000}，dev 上按 ARI 选优后冻结。
- **B2 递归字符切分**（RecursiveCharacterTextSplitter 语义的零依赖重实
  现）：分隔符层级冻结为 `["\n\n", "\n", "。", "！", "？", "；", ". ",
  "! ", "? ", " ", ""]`（中英混合感知），同 N 搜索范围，重叠 0。
- **本系统结构分块**（对照主体）：max_chars ∈ {500, 800, 1200, 2000}
  dev 选优（默认 800 为基线点）。
- ARI 实现零依赖（pairwise contingency 组合公式），以手算小样本 fixture
  锁死正确性；评测器如需接入此指标，EVALUATOR_VERSION 按封口策略另行
  升版裁决。

## 6. 质量与复核方案

异常处理目录（每例登记 doc_id+原因+处置）：

| 异常 | 处置 |
|---|---|
| 解析失败/非零错误码 | 排除，备选补位 |
| 空文档（<10 元素或 <200 规范化字符） | 排除，备选补位 |
| 编码异常（替换字符 >1‰） | 排除，备选补位 |
| 缺页/乱序（页码跳变） | 人工核查，可解释则保留并标注 |
| 图表缺失（人眼可见但零提取） | 保留（这正是要测的），标注如实挂非文本单元 |

双标注与仲裁：**4 篇**（dev 2 + holdout 2，覆盖至少两域）由用户独立复核
Claude 草案（第二标注人=用户），逐 unit 比对 gold_segment；分歧清单记录
+协商仲裁，仲裁结果为准；其余 16 篇用户抽查 ≥2 篇。多栏 PDF 欠提取为已
知限制（real-04 实证），标注规定：**按人眼可见阅读顺序标注，不迁就系统
输出**。

## 7. 提交物与停机门槛（本轮设计 + 获批后实现）

本轮（设计稿，随本文件提交）：本设计文档 + ADOPTION §六十六台账 +
候选清单（§1，未采集）。

获批后（下一子阶段，另行汇报）：实际采集 + manifest 冻结 + 标注 schema
校验脚本 + 标注指南正式版 + 20 篇标注 + split 方案落盘 + 基线配置冻结 +
采集/去重报告。

**澄清请求**：裁决"提交物"列有"校验脚本"而 D 项又限定"本轮未授权实现代
码"——本设计将校验脚本以**契约规格**形式给出（输入：标注 JSON + manifest；
检查：schema 符合、char_span 连续无重叠覆盖、norm_hash 复算一致、
gold_segment 引用闭合、split 分层约束；退出码 0/1），其实现随获批后的
下一子阶段提交。若您要求脚本随设计先行，请明示，我将单独请示实现授权。

停机门槛（任一触发即停止并汇报）：候选语料许可证核实通过数 <20；DOCX
核实数 <3；标注双份复核 unit 级一致率 <85% 且仲裁无法收敛。

## 8. 风险与偏差清单

1. 公开 DOCX 获取不稳（§1 申报；备选+用户私有补位）；
2. ARI ≥75% 不达标——诚实路径：不调标注迁就、不调指标口径，实测多少报
   多少（未实测前不宣称，遵立项裁决）；
3. 多栏 PDF 提取弱 → 句子流顺序与人工阅读顺序不一致 → 投影歧义；缓解：
   §6 标注规则 + 跨块 unit 计数披露；
4. 中英混合句子切分边界争议——冻结 v1 规则 + 双标注子集暴露分歧；
5. 语义连贯性阈值 ≥0.3 口径依批次 27 选定 embedding 方案重定标（立项裁
   决已认可）；
6. 许可证字段为"采集时核实"性质，冻结前必须全部落成明确值。
