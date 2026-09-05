# Stage 9 批次 26 — 正式标注指南（句子级 gold 标注）

依据：docs/stage9-batch26-design.md §3/§6 + 步骤 1 封口裁决补录 B
（ARI 分母、N/A 与失败计数规则，禁止静默排除）。
配套实现：`stage9/validation.py`（校验器）+
`scripts/stage9_validate_annotations.py`（CLI）。
标注文件存放：`samples/private/stage9-corpus/annotations/<doc_id>.json`
（gitignored，永不进 git）。

## 1. 标注对象与 ARI 原子单位

- 标注对象 = **人眼可见的正文句子流**（按人眼阅读顺序，多栏 PDF 按栏序
  先左后右，**不迁就任何系统输出**——系统多栏提取弱是已知限制，标注
  恰恰要暴露它）。
- **heading（标题）= text unit，参与 ARI**，与句子同流、同 gold_segment
  规则。
- **图像/表格 = nontext unit，不参与 ARI**：不进句子流、char_span=null，
  以 `nontext_ref`（`img:…`/`tab:…`）登记并挂 gold_segment；正文 unit
  可用 `linked_nontext` 引用它（关联指标单独计）。
- 页眉页脚、页码、水印：不进句子流也不登记 nontext（非内容单元），
  在 notes 里说明处理口径即可。

## 2. 规范化字符流（fold-ws-v1）

1. 将全文正文文本（含标题）按阅读顺序拼接；
2. 规范化：**所有空白（含换行/制表）压成单个空格，两端 strip**
   （与既有"分块不丢不重"测试同源规则）；
3. 结果即 `stream` 字段，必须满足 `fold_ws(stream) == stream`
   （校验器检查 `stream_not_folded`）。

**平铺规则**：text unit 的 char_span 必须连续、无重叠、全覆盖整个流；
unit 之间的分隔空格**归入前一 unit 的 span 末尾**
（如流长 48、三 unit → `[0,18) [18,33) [33,48)`）。
首个 unit 从 0 开始，末个 unit 止于流长。校验器对
`span_gap`/`span_overlap` 报错。

## 3. 句子切分规则（冻结 v1，人机同规）

- 中文：按 `。！？；` 切分（句末符号归前句）；
- 英文：`.`/`!`/`?` 后随空白 + 大写字母或数字才切；
- 缩写白名单**不切**：`Fig. Eq. et al. Dr. No. vs. i.e. e.g. etc.`；
- 省略号（`…`/`...`）不切；
- 标题整体一个 unit，不再按内部标点切分。

标注人按上述规则人工判定；与机械切分器的分歧不构成错误，以人工判定
为准并在 notes 记录争议例。规则一经冻结不改；发现缺陷须升 v2、全量
重切并登记变更（走裁决）。

## 4. 字段填写规范

格式版本 `annotation_schema`（冻结值 `v1.1`，2026-09-05 GPT 裁决
C1/C2 正式化）：v1.0 = 设计 §3 原字段；v1.1 = ①`stream` 由实现偏差
转正为正式字段——norm_hash 复算与 span 全覆盖检查以它为唯一基准；
②page 语义收紧为"只表物理页码"，新增 `body_index`。

```json
{
  "doc_id": "acad-01-sentencebert",
  "annotation_schema": "v1.1",
  "sentence_splitter": "v1",
  "normalization": "fold-ws-v1",
  "annotator": "claude-draft + user-review",
  "stream": "<规范化字符流全文（fold-ws-v1）>",
  "units": [{
    "unit_id": "u0001",
    "kind": "heading | sentence | nontext",
    "page": 1,
    "body_index": null,
    "char_span": [0, 18],
    "norm_text_hash": "sha256:<stream[a:b] 的 sha256 十六进制>",
    "text_preview": "<stream[a:b] 的非空前缀，≤60 字符>",
    "nontext_ref": "img:figure1 | tab:table2（仅 nontext unit）",
    "gold_segment_id": "g01",
    "hard_boundary_before": true,
    "linked_nontext": ["img:figure1"]
  }],
  "segments": [{"gold_segment_id": "g01", "hint": "标题+摘要",
                "kind": "frontmatter"}]
}
```

硬性约束（校验器逐项检查，失败码见 §8）：
- `annotation_schema`：必须为冻结值 `v1.1`；
- `unit_id`：`^u\d{4,}$` 且全文件唯一；
- `kind`：三值枚举；text 类（heading/sentence）必须有合法 span 与
  hash；nontext 类 `char_span`/`norm_text_hash` 必须为 null、必须有
  `nontext_ref`（`^(img|tab):\S+$`，全文件唯一）；
- `page`：**只表物理页码**（人眼所见页码，PDF 用印刷页码所在 PDF
  页序）；null 或 ≥1 整数。DOCX 无物理页码 → 全部 null，定位改用
  `body_index`；同一 unit 两者互斥（禁一字段两义）；
- `body_index`：null 或 ≥1 整数（body 元素 1-based 连续序，DOCX 篇
  供人工复核定位）；PDF 篇必须 null；
- `char_span`：半开区间 `[start, end)`（end 不含），0 ≤ start <
  end ≤ 流长；text unit 在 `units` 列表序中的 span 单调递增
  （列表序 = 阅读序 = 流序）；text unit 的 span 集精确覆盖全流
  （连续无重叠无间隙）；**unit 间分隔空格归前一 unit 的 span 末尾**
  （平铺规则：unit_i 的 end = unit_{i+1} 的 start）；
- `norm_text_hash`：仅按 `stream[span[0]:span[1]]` 字节复算（不从
  源文档推导）；
- `text_preview`：unit 文本的非空前缀且 ≤60 字符；
- `gold_segment_id`：每个 unit（含 nontext）必须引用存在的 segment；
  每个 segment 必须被 ≥1 unit 引用（双向闭合）；
- `linked_nontext`：可省略；出现则每项必须是文件内存在的 nontext_ref。

## 5. gold_segment 判定（语义段 = 主题内聚的知识单元）

- 一个 gold_segment = 人在通读时愿意用一句话概括的连续正文段
  （如"引言动机"、"方法概述"、"实验设置-数据集"）；
- 粒度基准：典型论文 8–20 个 segment；手册类按小节语义归并
  （一个三级小节 ≈ 1 个 segment，可并可拆，以主题内聚为准）；
- segment 边界必须落在 unit 边界上；`kind` 可选常用值
  frontmatter/body/related/conclusion/appendix（自由文本也允许）；
- **纪律：逐句人工查阅原文推导，禁止用任何系统输出（本系统或基线）
  反推**；holdout 集标注先于任何系统/基线在其上的解析运行。

## 6. hard_boundary 判定

`hard_boundary_before=true` 标记人工确定的硬边界（章节切换、主题显著
转折）。判定标准：后续内容开新话题且不延续上一 segment 的概括。
第一个 unit 恒为 true。

## 7. 双标注与仲裁

- 双标注 4 篇（dev 2 + holdout 2，覆盖至少两域）：第一标注人 =
  Claude 草案，第二标注人 = 用户独立复核（不看 Claude 草案）；
- 比对口径：unit 级（切分一致 + gold_segment 一致）；
- 一致率 = 一致 unit 数 / 双方 unit 并集数；**<85% 且仲裁不收敛 =
  停机条件**；
- 分歧清单记录于该文档标注文件的 `notes`（或仲裁记录文件），协商
  仲裁结果为准；其余 20 篇用户抽查 ≥2 篇。

## 8. 校验

```bash
.venv/Scripts/python.exe scripts/stage9_validate_annotations.py \
  --manifest samples/private/stage9-corpus/manifest.draft.json \
  --annotations samples/private/stage9-corpus/annotations
```

退出码：0 通过 / 1 存在失败 / 2 输入错误。失败码：`frozen_value`
（含 `annotation_schema` 版本）`stream_not_folded` `bad_unit_id_format`
`duplicate_unit_id` `bad_type` `unit_order` `dual_locator`
`locator_format_mismatch` `span_out_of_range` `span_overlap` `span_gap`
`hash_mismatch` `preview_mismatch` `span_not_null_nontext`
`bad_nontext_ref` `duplicate_nontext_ref` `unknown_nontext_ref`
`unknown_segment` `unreferenced_segment` `duplicate_segment_id`
`missing_field` `doc_not_in_manifest`；`--full-set` 追加
`split_count_mismatch` `split_domain_coverage` `missing_annotation`
（冻结终检用）。

## 9. ARI 分母、N/A 与失败计数规则（封口裁决补录 B）

**总原则：禁止静默排除。** 任何文档/块/unit 不进 ARI 计算都必须有
明确的 reason 码并进入计数披露；报告必须同时给出"计入 ARI 的数量"
与"N/A 及原因分布"。

| 情形 | ARI 处理 | 计数披露 |
| --- | --- | --- |
| 解析失败（非零错误码/异常） | 该文档 ARI = N/A，reason=`parse_failed` | 计入解析成功率分母与失败计数 |
| 空结果（<10 元素或规范化字符 <200） | ARI = N/A，reason=`empty_result` | 保留在语料计数 |
| 图/表零提取（人眼可见但系统没提取） | ARI 不受影响（nontext 本就不参与） | 计入非文本关联指标（召回缺失） |
| 预测 chunk 在字符流上定位失败 | 该 chunk 不产生归属 | `unmatched_chunk_count` 单列 |
| unit 不与任何 chunk 相交 | 该 unit 不进 ARI 求和项 | `uncovered_unit_count` 单列 |
| unit 跨多 chunk | 按最大重叠归属唯一 chunk | `cross_chunk_unit_count` 单列 |
| 标注缺失/校验不过 | 该文档 ARI = N/A，reason=`annotation_invalid` | 禁止剔除语料，修复标注后重跑 |

- **文档级 ARI 分母** = 该文档中被 ≥1 个 chunk 覆盖的 text unit 数
  （即进入 contingency 表的 unit）；heading 计入、nontext 不计入。
- **集级 ARI** = 有 ARI 文档（非 N/A）的 macro average；N/A 文档数
  与 reason 分布为必报字段，缺一即报告无效。
- 解析期表现（失败/空结果/零提取）**一律保留并计入指标**；冻结后
  替换文档 = 停机条件（须单独裁决）。
