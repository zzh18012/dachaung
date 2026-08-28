# Chunk.source_spans 填充契约（Stage 6 批次 2）

裁决来源：ChatGPT 5.6 Sol（2026-08-28，新对话 6a911adf）。
批次 1（ipynb cell 硬边界）通过并封口后，裁定批次 2 单独封口
`Chunk.source_spans` 填充，沿用"契约先行、全新期望冻结、干净 SHA
一次性首跑、ff-only 合入、全量回归"流程。

## §0 盘点与来源（两段式搬运协议）

- **基线已有**（无需搬运）：`app/models.py` 的 `Chunk.source_spans` 字段
  （默认空列表、`to_dict` 空则删键、`effective_schema_version` 任一 chunk
  带 span → 0.2.0）；`schemas/document.schema.json` 的
  `$defs/source_span`（`element_id`/`start`/`end` 必填、
  `additionalProperties: false`）、`chunk.source_spans` 属性、
  0.1.0 分支禁 span 规则；`tests/test_contract_adoption_v1.py` 的
  models 层契约测试。
- **autoline 资产**：chunker 填充逻辑（`_element_text_with_span`、
  parts 四元组、piece 坐标映射）与 span 语义测试
  （`test_pipeline_split_spans.py` 等）。
- **搬运方式**：无逐字节机械搬运（基线 chunker 结构与 autoline 相同但
  含批次 1 cell 边界逻辑，须按基线语义融合实现）；本契约为原创钉死，
  autoline 实现仅作语义参照。ADOPTION.md 十七如实登记。
- **语义统一性判定（GPT 拆批保险条款核查）**：span 是
  `el.content`（纯字符串，所有 source type 同构）中的字符区间；
  累积路径元素整进整出、唯一拆分点在超长路径；ipynb cell 边界只做
  整元素封口，与 span 正交。**span 语义跨 source type 完全统一，
  不触发拆批暂停条件。**

## §1 span 语义规则（九规则）

1. **定义**：`source_spans` 列出 chunk 引用的每个 element 在其
   `content` 字符串中的字符区间 `[start, end)`；坐标是 Python
   字符序号（Unicode code point），起点包容、终点排他。
   每个 span 是 `{"element_id", "start", "end"}` 三键 dict
   （schema `$defs/source_span` 钉死）。
2. **切片恒等**：chunk 中某 element 贡献的文本（单 span chunk 即
   chunk.text）与 `el.content[start:end]` 逐字节相等。
   单 span chunk 必须严格满足
   `chunk.text == el.content[start:end]`。
3. **坐标基准**：span 在 `el.content` 坐标系（非 stripped 坐标系）。
   stripped 文本起点用
   `el_start = len(raw) - len(raw.lstrip())` 推算
   （不用 `find`：内容重复时定位错）。`el_end = el_start + len(stripped)`。
4. **累积路径**（paragraph/list_item 累积、heading 入 buf、
   table/caption isolated、ipynb cell 边界封口——均为整元素进出）：
   span = `[el_start, el_end)`；content 首尾被 strip 吃掉的空白
   不属于任何 span。
5. **超长路径**（单 element > max_chars → 句子切 + 硬切回退）：
   piece 的 `start/end` 在 stripped 坐标系，最终
   `span = [el_start + piece.start, el_start + piece.end)`。
   句子累积合并成一个 piece 时，piece 的 span 覆盖参与合并的句子
   全体（含句间空白：`end` 随合并扩到后句结尾）；被切分规则吃掉的
   piece 间空白不属于任何 span（缝隙语义：相邻 span 缝隙只含空白）。
6. **多元素 chunk**：spans 按 part 顺序逐 part 一项；同一 element
   多次贡献 = 多项 span（**不去重**）。`source_element_ids` 维持
   既有首现去重语义，与 spans 项数无绑定关系。
7. **不参与分块的元素无 span**：content 为 None/空/纯白白的元素、
   image 元素（无文本）、resource-only 元素——既不产生 chunk
   也不产生 span。
8. **既有输出不变量**：chunk.text / metadata（含
   split_boundary_after）/ source_element_ids / chunk_id 与
   无 span 版本逐字节一致；span 纯增量。既有全套测试（含批次 1
   的 18 个 cell 边界测试）必须零修改通过（除 §1.9 修订条款涉及者）。
9. **版本契约与修订条款（AMENDMENT）**：
   - 任一 chunk 带 span → `effective_schema_version() = "0.2.0"`；
     空 span 列表不序列化（`to_dict` 删键，旧形状不变）；
     已落盘 0.1.0 旧产物继续通过 schema 校验（读取兼容）。
   - **修订**：`tests/test_version_semantics.py::
     test_old_pipeline_output_still_010_and_valid`（2026-08-27
     版本语义 PR）断言"pipeline 对 pdf/docx 输出仍 0.1.0（与冻结
     基线字节一致）"。填充 span 后所有 pipeline 输出为 0.2.0，
     该断言被本批次**取代**：不变量重述为"0.1.0 是合法读取格式
     （旧产物继续可校验）；新 pipeline 输出一律 0.2.0"。
     "冻结基线字节一致"保护对象是已封存产物，不是新运行。
     修订以独立提交登记于 ADOPTION.md，并向裁决方如实申报。

## §2 防御路径

- `content` 为 None / 空串 / 纯空白 → 元素跳过（无 chunk 无 span），
  不崩溃不猜测。
- locator 异常（ipynb 缺 cell_index）→ 元素自成一组（批次 1 契约），
  span 规则不受影响。
- 同一 element 被 buffer flush 与超长切分先后处理时，各 span 独立
  计算，互不重叠。

## §3 验收指标（三指标，同批次 1 口径）

1. **切片恒等**：对每个 chunk 的每个 span：
   `el.content[s:e]` 必须逐字节等于该 element 贡献到 chunk.text
   的对应片段；单 span chunk 全文恒等。
2. **覆盖无丢失（非空白口径，v1.1 已裁决 7e1246d）**：element 的
   stripped 区间内非空白字符必须被该 element 的 spans 并集全覆盖
   （只允许空白落在缝隙里）。
3. **确定性**：同一输入两次运行，全部 chunk 的 source_spans
   逐字段一致（排除 run_timestamp_iso / wall_time_seconds 计时噪声）。

## §4 端到端

`.md` → pipeline → UDM（0.2.0）→ schema 校验通过 → 逐 chunk 切片
恒等断言。ipynb 样例同时断言 cell 边界（批次 1）与 span（本批次）
正交共存。

## §5 holdout 纪律

- 全新语料（不复用任何已暴露 parser/chunker holdout），
  fixtures + 期望文件哈希冻结，独立提交；
- 期望推导权威 = 本契约 + main 既有测试（推导发生在任何实现运行
  之前；若推导出错按批次 1 模式：修正 + 独立提交 + 如实申报）；
- 固定干净 SHA 上一次性首跑封存，产物只写 `outputs/`（gitignored），
  不重跑。
