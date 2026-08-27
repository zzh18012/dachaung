# ipynb cell 硬边界分块契约（Stage 6 第一批）

状态：定稿（2026-08-27，ChatGPT 5.6 Sol 新对话第一轮裁决：首批只做 ipynb cell
硬边界，不顺手搬运其他分块策略/全局重构/剩余测试资产）。

## 0. 背景与资产盘点结论

- 自跑线快照（autoline-snapshot fcad055）经盘点**不含** ipynb cell 硬边界的
  生产代码或依赖测试（structural.py 与 16 个 chunker 测试文件中无 cell/
  ipynb 边界逻辑；唯一的硬边界是标题硬边界，已在 adoption 基线内）。
  本能力为 **adoption 原创实现**（先例：BUG-md-1 修正、models.py 精确快照），
  不存在"机械搬运"步骤；行为权威以本契约为准（GPT：契约 §12 的 stage 6
  依赖清单只是盘点入口，不是行为权威）。
- adoption 基线 chunker（app/chunkers/structural.py @ 96b688b）：标题硬边界 +
  长度上限 + table/image/caption 单独成 chunk + 超长 element 句级切分。

## 1. 核心规则（GPT 钉死，逐条可测）

1. **一个 chunk 不得跨越两个 notebook cell**：相邻元素的
   `source_locator["cell_index"]` 不同时，先封口当前 chunk 再开新 chunk。
2. **单个超长 cell 可在 cell 内继续切分**：沿用现有超长规则
   （句级切分 + 空白回退 + 定长兜底），切分产物仍只引用该 cell 的元素。
3. **相邻短 cell 即使未达目标长度也不得合并**：cell 边界优先于长度目标。
4. **chunker 只消费 UDM**：不重新解析原始 .ipynb；判据只来自
   `document.source_type == "ipynb"` 与 element 的 `source_locator`。
5. **Markdown 标题上下文只作元数据语义继承，不得通过拼接正文突破 cell 边界**：
   本批实现不向 chunk metadata 写 section_path（当前 chunk metadata 契约仅
   strategy/max_chars/char_count[±split_boundary_after]，保持不变）；
   标题层级上下文保留在 element locator 的 section_path，可经
   source_element_ids 查询。记录为有意最小化，后续批次如需再裁。
6. **不产伪正文 chunk**：空 cell、非法 cell（ipynb_bad_cell 跳过）、outputs、
   attachments、被跳过的 attachment: 引用——这些在 parser 层就不产生 element，
   chunker 不虚构其正文（无 element 即无 chunk，天然满足；验收仍显式断言）。
7. **顺序 / ID / provenance 确定**：chunk 顺序 = element 顺序；chunk_id 沿用
   `{document_id}::c{N:04d}` 连续编号；cell 溯源经 source_element_ids →
   element.source_locator["cell_index"] 链路确定。
8. **非 ipynb 输入的既有分块结果保持不变**：cell 判定仅在
   `source_type == "ipynb"` 时激活；其他 source_type 的输出与 96b688b 基线
   逐字节一致（回归断言）。
9. cell 边界与既有规则的交互：
   - 同一 cell 内的 heading 仍是硬边界（更细粒度允许）；
   - table/image/caption 仍单独成 chunk（本身就不跨 cell）；
   - cell 变化触发 flush 的 strategy 记录保持 "sequential"（封口原因不区分）。

## 2. 边界定义细则

- `cell_index` 取自 element `source_locator`；ipynb 契约保证所有 ipynb element
  的 locator 都带 `cell_index`。若 locator 异常缺失（防御路径），按"该元素
  自成一组"处理（等效于触发边界），不崩溃、不猜测。
- 无 elements 的 ipynb 文档（全空/全跳过）→ chunks 为空列表，与现状一致。

## 3. 验收口径（首批三指标 + 常规）

- 常规：全套回归；dev 语料 9 输入 = 5 成功 + 4 ef 精确匹配 + 0 意外失败
  （复用 parser 冻结 expectations 的 element 计数不变，chunk 层新增断言）。
- **三核心指标**（GPT 指定，作为可重复的验收测试与首跑断言，不进 evaluator
  报告结构）：
  1. 正文覆盖无丢失：`normalize_text(所有 chunk 文本拼接) ==
     normalize_text(所有 element content 拼接)`（既有"不丢不重"口径）；
  2. 跨 cell chunk 数 = 0：每个 chunk 的 source_element_ids 映射到的
     cell_index 集合大小恒为 1；
  3. 非 ipynb 基线变化数 = 0：对非 ipynb 语料（md/html/text fixtures +
  既有全量回归）输出与基线一致。
- 端到端测试：.ipynb → pipeline（--parser ipynb）→ UDM → chunker →
  schema 校验通过，且 chunk 满足 cell 不变量（GPT 指定）。
- 确定性：同一输入两次运行，chunk 序列（id/text/source_element_ids/metadata）
  逐字段一致。

## 4. 版本与 schema

- chunk metadata 结构不变（无新键）→ Chunk 模型不变 → document schema 不变。
- evaluator 不新增该策略的准入或验收报告能力（三指标在验收测试与首跑断言
  中执行）→ **EVALUATOR_VERSION 保持 1.7**；report_version 1.3、manifest 1.1
  不变。（GPT 条件句"若 evaluator 新增能力则 1.7→1.8"未触发。）
- pipeline 默认 chunker 行为对 ipynb 变化 → 不改 CLI 表面。

## 5. 语料与 holdout 纪律

- dev：复用 devset-ipynb 5+4（parser 层 expectations 不变；chunk 层断言按
  本契约在验收测试中固化，不回写 manifest）。
- **chunker 专属 holdout：全新建立**（GPT：不复用已曝光的 parser holdout），
  冻结 expectations 后不入任何对照/预跑；固定干净 SHA 首跑封存。

## 6. 提交切分

1. 本契约入库（docs）。
2. 语料冻结登记（ADOPTION.md 十六）。
3. 实现 + 单元/边角测试（adoption 原创，标注与契约条款映射）。
4. 端到端 + 三指标验收测试 + 非 ipynb 基线不变断言。
5. 固定 SHA → chunker holdout 首跑封存 → --ff-only 合入 main → 复验。
