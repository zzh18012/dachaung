# relation 消费契约（Stage 6 批次 6）

状态：冻结 v1（2026-08-30 批次 5 封口裁决授权开工，三项强制要求并入
§2/§3/§4/§6；执行顺序①契约即本文 →②参数化重构 →③figure_caption_*
消费修复 →④零差异验证 →⑤封口报告）。

裁决依据：新会话 cf170a6f 批次 5 封口裁决（归档 Stage-6-Batch-5-Closed）：
"(b) 批次 6 开工授权：通过，并补充三项强制要求：① relation 消费契约
必须明文（评测项↔relation type 依赖、缺失降级策略、参数化匹配器签名）；
② 批次 4→6 的 evaluation 零差异验证；③ 批次 7 接口预留验证（桩测试）"。
匹配器签名本批冻结，批次 7 不得再改接口。

## §0 盘点（2026-08-30）

- `figure_caption_prf`（evaluation/annotation_metrics.py）现状为 stub：
  恒 null + reason=`parser_does_not_emit_relations`。该 reason 自批次 4
  起已过时——fallback pdf/docx 已产出 `image --has_caption--> caption`
  relation（docs/caption-relation-contract.md，schema 0.4.0）。
- annotation.schema.json 已冻结 `figure_caption_pairs` 条目形状：
  `[{figure_marker: str, caption_text: str}]`（additionalProperties=false）。
- devset 现状：DC-MVP-001（docx）annotation 的 `figure_caption_pairs=[]`
  （空表）；DC-MVP-001-PDF 无 annotation 文件。
- EVALUATOR_VERSION=1.7 / REPORT_VERSION=1.3；report.py `_RATIO_METRICS`
  不含 figure_caption_*（不参与 macro average）。
- 批次 4 dev 验收封存基线：outputs/evaluation-captionrelation-dev-
  acceptance.json（git_commit=5750aef，gitignored）。

## §1 范围（本批锁死）

- **仅评测侧**：不改 `app/parsers/*`、`app/chunkers/*`、`app/pipeline.py`、
  `app/models.py`、`schemas/*`（评测只调用，不改生成逻辑——零差异验证的
  前提）。
- `figure_caption_prf` 改为直接消费 `document["relations"]` 中
  `type=="has_caption"` 的 relation。
- 移除常量 `PARSER_DOES_NOT_EMIT_RELATIONS` 及全部引用（测试按本契约重钉）。
- 内部匹配器重构为 relation-type 参数化纯函数（§2），供批次 7
  `table_has_caption` 复用。
- 报告结构零变化：per_doc metrics 键集不变、summary 聚合集不变
  （figure_caption_* 仍不进 macro average）→ REPORT_VERSION 保持 1.3。

## §2 参数化匹配器（签名冻结；批次 7 只许换参数不许改签名）

```python
def match_relation_pairs(
    document: dict[str, Any] | None,
    pairs: list[dict[str, str]] | None,
    *,
    relation_type: str,
    from_marker_key: str,
    to_marker_key: str,
) -> tuple[int, int, int] | None:
    """返回 (num_predicted, num_ground_truth, num_matched)。

    document 为 None → 返回 None（调用方降级 pipeline_failed）。
    pairs 为 None/空 → 返回 None（调用方降级 no_annotation_pairs）。
    """
```

匹配语义（全部确定性）：

1. **预测对**：`relations` 中 `type == relation_type` 的每条 relation，
   按 document["relations"] 给定顺序。`from_id`/`to_id` 解析不到对应
   element（端点缺失）→ 该 relation 不计入预测（评测侧防御；正常管线
   构造上端点必在，契约测试固化）。
2. **GT 对**：`pairs` 列表按给定顺序，条目取 `from_marker_key`/
   `to_marker_key` 两键的字符串值。
3. **from 侧可匹配文本**：按固定顺序拼接元素的可识别字符串——
   `content`（若为 str）、`metadata.alt`（若为 str）、`resource_path`
   的 basename（若为 str）；均经 `normalize_text`（空白折叠）。
   marker 匹配当且仅当 `normalize_text(marker)` 是该拼接文本的子串。
   依据：docx/pdf image 的 content=None、识别信息在 resource 文件名；
   md/html image 在 metadata.alt（annotation 模板语义即"唯一子串定位"）。
4. **to 侧可匹配文本**：`to_element["content"]`（None 按 ""），同样
   normalize 后子串匹配。
5. **一对一贪心**：所有 (pred_i, gt_j) 双侧均匹配的组合按
   `(i, j)` 字典序升序配对，任一端点已配对则跳过。

`figure_caption_prf` 是薄包装：以 `relation_type="has_caption"`、
`from_marker_key="figure_marker"`、`to_marker_key="caption_text"` 调用，
产出且仅产出 `figure_caption_precision/recall/f1` 三键。

## §3 降级策略（裁决要求①："缺失时 fail 还是 skip"逐项明文）

统一口径：**skip（null + reason），不把评测跑挂**——与既有 annotation
指标（chunk_boundary）一致；fail 语义仅用于 pipeline 本身失败。

| 情形 | precision | recall | f1 |
|---|---|---|---|
| document is None（pipeline 失败） | null `pipeline_failed` | 同左 | 同左 |
| annotation 缺失/不可读 | null `no_annotation` | 同左 | 同左 |
| `figure_caption_pairs` 缺失或空表 | null `no_annotation_pairs` | 同左 | 同左 |
| 有 GT 对、预测 relation 数 0 | null `no_predicted_relations` | `_ratio(0.0)`（真实漏检） | null `precision_or_recall_not_evaluated` |
| 正常可比 | matched/num_pred | matched/num_gt | 2PR/(P+R)（P+R=0 时 0.0） |

评测项 ↔ relation type 依赖（裁决要求①）：本批唯一依赖
`figure_caption_* → has_caption`；relation 不存在时即上表第 4 行
（预测 0），**不**回退启发式（"最近图片"启发式仍属禁区）。

## §4 零差异验证（裁决要求②，诚实范围声明）

对照批次 4 封存基线（outputs/evaluation-captionrelation-dev-acceptance.
json @5750aef）重跑 evaluation 后逐字段 diff。

**必须逐字节相同**：per_doc 全部字段除下述排除项——含
schema_valid、element 计数、locator/text/chunk 全部指标、
chunk_boundary_*、expectation_checks、expected_failures、devset 分节、
summary 全部分节、provenance.dependencies/max_chars。

**必然不同的字段（排除集，逐项归因）**：
- `wall_time_seconds.total`：计时；
- `provenance.git_commit / run_timestamp_iso`：运行环境；
- `provenance.evaluator_version`：1.7→1.8（§5）；
- `per_doc[].metrics.figure_caption_{precision,recall,f1}.reason`：
  `parser_does_not_emit_relations → no_annotation_pairs`（devset 两文档
  一无 annotation 一空表）。

**对裁决原文的偏差声明**：裁决要求"除 wall_time / git_commit 外所有
字段逐字节相同"，但其第③项（移除过时理由）与版本封口政策必然改动
上排除集后三项。按裁决自身理据（"批次 6 仅改评测基础设施（消费方式），
不改生成逻辑——评测分数理应完全一致"）执行为：**全部分数（value）
逐一相同（null==null）**，reason 仅 figure_caption_* 三处按③变化。
此解释在封口报告中明示，请追认。

## §5 版本语义

- EVALUATOR_VERSION **1.7 → 1.8**：1.7 evaluator 无法消费 relation，
  同版本不同能力损害复现（沿 1.2→1.7 能力封口政策）。
- REPORT_VERSION 保持 1.3：报告结构（键集、聚合、分节）零变化。
- UDM schema_version 不动（0.4.0；本批不触碰 app/*）。

## §6 契约测试

- 匹配器单元：完美匹配 1.0/部分匹配/零预测（表 §3 第 4 行形状）/
  端点缺失排除/一对一二义贪心确定性（(i,j) 序）/from 侧 alt 与
  resource basename 均可定位/to 侧 normalize 容忍空白差异/
  document None 与 pairs None 返回 None。
- 降级矩阵五路逐行断言（表 §3）。
- **批次 7 桩测试（裁决要求③）**：以 `relation_type="table_has_caption"`、
  `from_marker_key="table_marker"`、`to_marker_key="table_caption_text"`
  构造合成 document（两条 table_has_caption relation + 对应 table/
  caption 元素）与 pairs，断言返回 (2,2,2) 类计数——无真实数据，仅证明
  接口可扩展；另断言 figure_caption_prf 包装仍产三键且键集封闭。
- 聚合不变断言：figure_caption_* 不进 summary.ratio_macro_averages。
- 重钉：tests/test_annotation_metrics.py（2 处）、test_evaluation_cli.py
  :163、test_evaluation_report.py:30-32、docs/evaluation.md 两处表行、
  CLAUDE.md 对应行——全部指向本契约新语义。
- 全量回归 5056+ 通过。

## §7 holdout

不设。本批为评测基础设施改动，writer 输出面零变化（§1 前提 + §4
零差异验证即为验收）；匹配器行为由合成单元测试覆盖（§6），devset
真实跑批由 §4 脚本执行并封存。

## §8 明确不做（本批）

- 不把 figure_caption_* 加入 macro average（summary 结构变化需升
  report_version，留未来批次）。
- 不改 annotation.schema.json / 不新增标注字段。
- 不实现 table_has_caption 真实关联（批次 7；本批只留桩测试）。
- 不引入"最近图片"等启发式 fallback。
- 不改 app/* 与 schemas/*。
