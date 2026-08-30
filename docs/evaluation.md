# 评测方法（Stage 2）

> 本文档定义评测指标、人工标注规则与开发集约定。
> 当前为 **pilot baseline / incomplete devset** —— 开发集尚未达到 8-10 份的目标，
> 数字仅反映当前 1 对样例上 fallback parser 的表现，**不代表项目总体准确率**。

## 1. 范围

**评测**：测量 fallback parser + StructuralChunker 在开发集上的表现，建立可对比的基线。
**不做**：修改 parser / chunker / pipeline 算法；引入新依赖；OCR、embedding、UI、KVFS、图文关联算法。

## 2. 命令

```bash
# 跑评测
.venv/Scripts/python.exe -m evaluation.cli run \
  --manifest samples/private/devset/manifest.json \
  --output outputs/evaluation-pilot-baseline.json \
  --parser fallback \
  --max-chars 800

# 校验报告
.venv/Scripts/python.exe -m evaluation.cli validate-report outputs/evaluation-pilot-baseline.json
```

CLI 子命令设计为清晰分离：`run` 跑评测、`validate-report` 校验已生成的报告 JSON。
**禁止**用 `--validate` 旗子或把报告 JSON 当作 parse 输入。

## 3. 评测报告 Schema

报告必须通过 `schemas/evaluation-report.schema.json`。包含：

- `report_version`：**精确快照版本**（见下文 3.1 演进表）
- `provenance`：git_commit、git_dirty、parser/version、依赖版本、max_chars、运行时间
- `devset`：status、file_count、content_group_count、pdf/docx 数量、categories 覆盖
- `summary`：分类型聚合（counts / success_rates / ratio_macro_averages / silent_drop_total）
- `per_doc`：每份文档的全部指标
- `expected_failures`：预期失败用例的 expected vs actual 错误码

### 3.1 report_version 演进（精确快照，schema 条件互斥）

| 版本 | 引入内容 | 校验语义 |
|---|---|---|
| 1.1 | 旧结构（早期文档曾写"固定 1.0"，随 v1.1 语义修订废止；无存量封存报告） | 不得含 expectation_checks 分节、per-doc check 键、parser_used |
| 1.2 | summary.expectation_checks 分节；per-doc 四个 check 键（required/forbidden_markers、must_not_error_codes、max_silent_drop） | 不得含 per-doc parser_used |
| 1.3（当前） | per-doc `parser_used`（auto 混合调度的复现字段） | 必含 parser_used |

evaluator_version 与能力封口对应：1.3 markdown、1.4 html、1.5
`--parser auto`、1.6 text。同版本不同能力损害复现，故新格式启用即升
evaluator 版本；report_version 仅在报告**结构**变化时提升。

## 4. 指标定义

每份文档产出一份 `per_doc.metrics`。每条指标形如 `{"value": ..., "reason": null}` 或
`{"value": null, "reason": "<why>"}`。**比例指标分母为 0 时返回 null + reason，不返回 1.0**。

### 4.1 自动指标（无需人工标注）

| 指标 | 类型 | 定义 |
|---|---|---|
| `pipeline_success` | bool | `errors == []` |
| `error_code` | string\|null | 失败时的 ErrorRecord.code |
| `schema_valid` | bool | 通过 `document.schema.json` |
| `element_count_total` | int | 全部 element 数 |
| `element_count_by_type` | dict | 按 type 分桶计数 |
| `pdf_locator_valid_ratio` | 0-1\|null | PDF：page≥1（全部元素）；文本类型还需 bbox=4 个有限数。null 当无元素 |
| `docx_locator_valid_ratio` | 0-1\|null | DOCX：locator 无 page/bbox，至少一个结构键。null 当无元素 |
| `image_resource_exists_ratio` | 0-1\|null | image element 的 resource_path 文件实存且 size>0 的占比。null 当无 image |
| `chunk_reference_intact_ratio` | 0-1\|null | chunk 的 source_element_ids 全部能解析到现存 element 的占比。null 当无 chunk |
| `text_preservation_equal` | bool | v1.1：删除全部 Unicode 空白后的非空白字符有序序列 `expected_sequence == actual_sequence`（详见下文"文本保留 v1.1 语义"） |
| `text_char_multiset_precision` | 0-1\|null | v1.1：在去掉空白的非空白字符序列上，Counter 交集 / 实际字符总数 |
| `text_char_multiset_recall` | 0-1\|null | v1.1：在去掉空白的非空白字符序列上，Counter 交集 / 期望字符总数 |
| `heading_boundary_compliance` | 0-1\|null | 合规 heading 数 / heading 总数（合规 = 出现在某 chunk 的 source_element_ids[0]）。null 当无 heading |
| `silent_drop_count` | int\|null | `Σ max(0, expected_count - actual_count)` over types。null 当无 expectations |

> **字符多集合**用 `collections.Counter`：保留重复字符信息，能发现"重复"和"缺失"。
> 完全相等指标负责发现顺序变化。两者互补。

> ⚠️ **重要范围说明**：`text_preservation_equal / text_char_multiset_*` 只比较
> **parser 已提取的 elements** 与 **chunker 生成的 chunks**，用于发现**分块阶段**的丢失、
> 重复或顺序变化。它们**不能证明**原始 PDF/DOCX → elements 的解析过程没有漏内容。
> PDF 的 `silent_drop_count=3`（见第 6 节）正说明源文档到 elements 仍存在漏检 ——
> 那部分损失**不会**被 text_preservation 系列指标反映。

#### 4.1.1 文本保留 v1.1 语义（自 evaluator/report v1.1 起）

旧 v1.0 的 `text_preservation_equal` 用 `' '.join 重建全文 + normalize_text 比对`，
对 chunker 在英文词内硬切（长元素按字符数切片时落在词中间）产生的额外空格误报为不等于。
自 v1.1 起，文本保留改为**非空白字符的有序序列对比**（口径 D）：

```
expected_sequence = ''.join(e.content for e in elements if e.type != 'image')
                    然后删除全部 Unicode 空白（用 str.isspace() 判定）
actual_sequence   = ''.join(c.text for c in chunks)
                    然后删除全部 Unicode 空白
text_preservation_equal = (expected_sequence == actual_sequence)
text_char_multiset_precision = |Counter交集| / |actual|
text_char_multiset_recall    = |Counter交集| / |expected|
```

**该指标能发现**：
- 元素 → chunker 阶段的非空白字符**丢失**（recall < 1，equal=False）；
- 元素 → chunker 阶段的非空白字符**重复**（precision < 1，equal=False）；
- 非空白字符的**顺序变化**（equal=False，多集合可能仍相同）。

**该指标故意忽略**：
- 空格、制表符、换行、Unicode 空白（NBSP、em/en space、表意空格等）的差异；
- chunker 在词内硬切引入的额外空格（v1.0 误报已消除）；
- chunker 跨 chunk 边界丢失的换行/缩进。

**该指标不能证明**：
- 原始 PDF/DOCX → elements 没有漏检（由 `silent_drop_count` 等独立指标反映）；
- 空白排版被精确保持（如段落间距、缩进、对齐）。

**关于以后如何增加空白级精确验证**：
若未来需要"chunk 文本在 element 内容中的字符区间级"精确验证，应给每个 chunk 增加
`source_spans: [{element_id, start, end}]` 字段，让评测器直接校验 chunk 文本与对应
element content 子串严格相等。**不要**继续在 `source_element_ids` 上叠加启发式
（如 `prev.source[-1] == next.source[0]` 判断同元素续段）—— 已用 8 份真实文档验证：
该启发式仅能识别部分续段，仍会引入回归。

**v1.0 → v1.1 不可横向比较**：
旧 baseline 的 `text_preservation_equal / precision / recall` 与新 baseline 不可
直接横向比较（口径变了）。其他指标语义未变，可继续比较。

### 4.2 计时

```
wall_time_seconds: {
  total: <float>,
  parse: null,  # reason: "not_instrumented"
  chunk: null   # reason: "not_instrumented"
}
```

Stage 2 不修改 `app/pipeline.py`，因此 parse/chunk 阶段未插桩。**禁止**把 total 重复写成 parse/chunk。

### 4.3 标注指标（需人工标注，缺标注时为 null）

| 指标 | reason（缺数据时） |
|---|---|
| `figure_caption_precision` / `recall` / `f1` | 消费 document.relations 的 `has_caption`，对照 annotation `figure_caption_pairs`（figure_marker/caption_text 子串匹配，docs/relation-consumption-contract.md）；降级：`pipeline_failed` / `no_annotation` / `no_annotation_pairs` / `no_predicted_relations`（此时 recall=0.0，真实漏检） |
| `chunk_boundary_precision` / `recall` / `f1` | null + `no_annotation` / `no_predicted_boundaries` / `no_ground_truth_anchors[_in_stream]` |

**chunk_boundary 匹配规则**：
- 在 `normalize_text(Σ chunk.text)` 流中定位
- 预测边界位置 = 第 i 个 chunk 末尾在流中的字符偏移
- 标注 anchor 位置：`marker` 子串查到后，`position="before"` 取起始、`"after"` 取结束
- 一对一匹配：每个预测边界只能匹配一个 anchor，反之亦然（贪心按距离升序）
- 容差（`tolerance_chars`，默认 30）必须在报告中记录

## 5. 开发集与隐私

- 开发集清单：`samples/private/devset/manifest.json`（**gitignored**）
- 人工标注：`samples/private/devset/annotations/*.json`（**gitignored**）
- 模板（可提交）：`samples/devset/manifest.template.json`、`annotation.template.json`
- 原始报告：`outputs/evaluation-*.json`（**gitignored**）

**Manifest 路径规则**：
- `path` 必须是相对项目根目录的**正斜杠**相对路径
- 拒绝绝对路径（POSIX `/foo`、Windows `C:\\foo`、`C:/foo`）
- 拒绝反斜杠
- 解析后路径必须位于项目根目录内（防 `../../../etc/passwd` 之类）
- **不把本机绝对路径写入 manifest 或报告**

**devset_status**：清单字段，由人工维护。当前固定为 `"incomplete"`。
报告同时记录 `file_count / content_group_count / pdf_count / docx_count / categories_covered`，
不单看文件数判定完整性。

## 6. 当前 Pilot Baseline（参考用，**不代表项目总体准确率**）

Dev set: 1 对 DOCX+PDF（DC-MVP-001），1 个内容组。
Provenance: git_commit=`33c68a1e23b33e867dd872608447d1e2b89ae860`、parser=fallback、max_chars=800。

| 指标 | DC-MVP-001 (docx) | DC-MVP-001-PDF (pdf) | macro avg |
|---|---|---|---|
| pipeline_success | ✓ | ✓ | 2/2 = 1.0 |
| schema_valid | ✓ | ✓ | 1.0 |
| element_count_total | 33 | 18 | sum=51 |
| pdf_locator_valid_ratio | n/a | 1.0 | 1.0 (n=1) |
| docx_locator_valid_ratio | 1.0 | n/a | 1.0 (n=1) |
| image_resource_exists_ratio | 1.0 | 1.0 | 1.0 |
| chunk_reference_intact_ratio | 1.0 | 1.0 | 1.0 |
| text_preservation_equal | ✓ | ✓ | 1.0 |
| text_char_multiset_precision | 1.0 | 1.0 | 1.0 |
| text_char_multiset_recall | 1.0 | 1.0 | 1.0 |
| heading_boundary_compliance | 1.0 | 1.0 | 1.0 |
| silent_drop_count | 0 | 3 | sum=3 |
| figure_caption_p/r/f1 | null | null | null（历史基线 reason=parser_does_not_emit_relations；批次 6 起为 no_annotation_pairs，见 docs/relation-consumption-contract.md） |
| chunk_boundary_p/r/f1 | 0.53 / 1.0 / 0.69 | null | 0.53 / 1.0 / 0.69 (n=1) |
| wall_time_total | ~0.03s | ~0.16s | — |

### 6.1 怎么读这些数字（不是总体准确率）

各项 `1.0` **不代表** "fallback parser 解析准确率 100%"。它们只表示**特定指标在特定范围内**达到上限：

- `pdf_locator_valid_ratio=1.0`：**所有提取出的** element 的 page/bbox 合规；不代表源 PDF 的所有内容都被提取（见 `silent_drop_count=3`）
- `docx_locator_valid_ratio=1.0`：同上，DOCX 侧
- `image_resource_exists_ratio=1.0`：所有被识别为 image 的 element 的 resource 文件都落盘成功
- `chunk_reference_intact_ratio=1.0`：所有 chunk 的 source_element_ids 都能解析到现存的 element
- `text_preservation_equal=✓`：**parser 提取出的 element 内容** 与 **chunker 生成的 chunk 文本** 在规范化后相等 —— 这是**分块阶段**的不丢不重，**不是** PDF/DOCX → elements 的解析完整性
- `heading_boundary_compliance=1.0`：所有 heading 都成了某 chunk 的首元素

### 6.2 暴露出的问题（不在本阶段修复）

- **PDF `silent_drop_count=3`**：相比 manifest 期望，PDF 路径漏检 **2 个 heading + 1 个 caption**。这是 PDF 解析阶段的损失，text_preservation 系列指标反映不出来。
- **DOCX `chunk_boundary_precision=0.529, recall=1.0, F1=0.692`**：标注的 9 个 anchor 全部被预测边界覆盖（recall=1.0）；但预测边界总数 ≈17，多出来的来自长段落内部句子切分（标注未覆盖句子级），所以 precision 偏低。这是**分块器与标注粒度不一致**，不是分块器错误。
- **`figure_caption_p/r/f1 = null`**：预期行为，按你的决定 9.2-ii，parser 当前不输出 caption↔figure relation。
- **PDF `chunk_boundary_p/r/f1 = null`**：PDF 没有标注文件，reason=`no_annotation`。

### 6.3 expected_failures

3/3 全部命中预期错误码：

| doc_id | expected | actual | matches |
|---|---|---|---|
| ERR-BLANK | `no_extracted_elements` | `no_extracted_elements` | ✓ |
| ERR-CORRUPT | `pdfplumber_open_failed` | `pdfplumber_open_failed` | ✓ |
| ERR-UNSUPPORTED | `unsupported_type` | `unsupported_type` | ✓ |

## 7. 后续 Stage 不在本阶段做

- 扩充开发集到 8-10 份真实文档（用户后续提供）
- 标注更多 chunk_boundary anchor（句子级、表格边界）
- 引入 caption↔figure relation 输出后再开 figure_caption 指标
- 在 pipeline 中插桩 parse/chunk 计时
- 跨 stage 的基线对比（自动 diff 两份报告）
