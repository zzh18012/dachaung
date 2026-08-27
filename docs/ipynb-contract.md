# ipynb 支持契约（定稿 v1）

依据 2026-08-27 ChatGPT 5.6 Sol 裁决（有条件通过 + 修订表）定稿。本文件是 ipynb 能力从
autoline-snapshot fcad055 搬运至 adoption 线的权威规格；dev/holdout 语料的 expectations
人工推导以此为准，先于任何运行审计。

## 1. 范围与安全

- 仅支持 nbformat 主版本 **== 4**（采用其已知 cell/source 语义）；其他主版本（<4 或未来 >4）
  → `ipynb_unsupported_version`。不承诺未来主版本兼容。
- 本契约的结构检查是**源码抽取所需的最小结构校验**，不是完整官方 nbformat Schema 校验；
  更高 minor 版本按已知字段处理，不宣称支持其新增能力。
- stdlib `json` 解析。**绝不执行 cell 代码、绝不联网、不读取 notebook 引用的外部资源**。
  该政策以契约测试钉住，且必须覆盖委托解析（MarkdownParser）与图片处理路径的行为，
  不能只检查 IpynbParser 的 import。

## 2. 版本字段

- `nbformat`：必须为整数（`int` 且非 `bool`）。缺失或类型错误（str/bool/float/null）
  → `ipynb_bad_structure`；类型合法但 `!= 4` → `ipynb_unsupported_version`。
- `nbformat_minor`：必须为非负整数（`int` 且非 `bool`，≥0）。缺失或类型错误
  → `ipynb_bad_structure`。
- 两字段校验通过后写入 `document.metadata`（`nbformat=4`、`nbformat_minor=N`）。

## 3. 结构校验与错误码

| 条件 | 结果 |
| --- | --- |
| 顶层非对象 / `cells` 非数组 / 版本字段缺失或类型错误 | `ipynb_bad_structure`（error） |
| `nbformat` 为合法整数但 ≠ 4 | `ipynb_unsupported_version`（error） |
| JSON 非法 | `ipynb_invalid_json`（error） |
| 读取失败 | `ipynb_read_failed`（error） |
| 后缀非 `.ipynb` | `unsupported_type`（error） |
| 文件不存在 | `file_not_found`（error） |
| 0 elements（空 notebook 或仅空 cell） | `ipynb_no_content`（warning）；pipeline 层按既定不变量报 `no_extracted_elements`（expected_failures 机制，text 先例沿用） |

## 4. cell 政策

- cell 非对象 → 跳过 + `ipynb_bad_cell`（details 带 `cell_index`）。
- **markdown cell** → 委托已采用的 `MarkdownParser._parse_text`（含 BUG-md-1 修复语义）；
  一个 cell 可产出多个 element（heading/paragraph/list_item/table/image）；子 warnings 透传
  并附 `cell_index`；子 element locator 前置 `cell_index`/`cell_type`，保留 cell 内 `line`
  与 `section_path`。**每个 markdown cell 独立标题栈，跨 cell 不跟踪**（已批准）。
- **code cell** → 单个 paragraph，`metadata.kind="code_cell"`，`metadata.language` 按第 6 节
  链取值；空（用 `strip()` 判空）→ 跳过 + `ipynb_empty_code_cell` 警告。
- **raw cell** → 单个 paragraph，`metadata.kind="raw_cell"`；空 → 跳过、**无警告**
  （无实际内容损失，保持与自跑线一致；不为对称而改）。
- 未知或缺失 `cell_type` → 跳过 + `ipynb_unknown_cell_type` 警告。
- `cell_index` 使用**原始数组位置**（0-based），跳过 cell 后不重新编号；
  `cell_count` = 输入 cell 总数（含被跳过者）。
- cell 独立标题栈**不**意味着 cell 自动成为 chunk 硬边界；后者属 chunker 策略（stage 6）。

## 5. source 语义

- `str` → 原样使用。
- `list` → **先确认全部项为字符串，再 `''.join(...)`**（nbformat 列表项自带换行，不额外
  插入）。禁止用 `str()` 把数字、对象、null 转成正文。
- `source` 缺失，或非 str/list，或列表含非字符串项 → 跳过该 cell + `ipynb_bad_cell`
  （details 注明 `cell_index` 与字段名 `source`）。
- 非空 code/raw 正文**保留原始缩进与换行**：`strip()` 仅用于判空，裁剪后的字符串不得写入
  正文。

## 6. language 链

- `kernelspec.language` → `language_info.name` → 空串。
- `kernelspec.name` 不参与语言判定（内核标识 ≠ 语言名称），本契约不记录内核名。

## 7. outputs / attachments / execution_count（忽略政策）

- `outputs` 非空 → `ipynb_outputs_ignored` 警告（每 cell 一次，details 注明数量）；不入
  elements/metadata，不还原多媒体。自跑线无此诊断，系 adoption 独立修正。
- `attachments` 存在且为非空 dict → `ipynb_attachments_ignored` 警告（每 cell 一次，details
  注明数量）；不复制附件 payload；**不因 nbformat_minor 门控**（官方已将附件支持回移
  4.0）。系 adoption 独立修正。
- `execution_count` → 静默忽略。
- markdown 中 `attachment:` 图片引用（`![alt](attachment:name)`）：**不解码附件、不当本地
  路径或网络地址读取、不伪造已提取资源**。现有图片模型无法表示未解析引用 → 跳过对应
  image element + `ipynb_attachment_ref_skipped` 诊断（details 保留 `cell_index`、原始引用
  与 alt），保留该 cell 其余 element 与位置信息。

## 8. locator

- `{cell_index: 0-based 原始位置, cell_type, line: cell 内 1-based 偏移}`。
- code/raw 的单 paragraph locator 含 `line: 1`。
- markdown 子元素另带 cell 内 `section_path`。

## 9. document metadata

`{ipynb: true, nbformat: 4, nbformat_minor: N, cell_count: 输入 cell 总数, language}`

## 10. Markdown 委托验收条件

- 多个 markdown cell 产生的 element ID 在整份文档内唯一（ipynb 层统一重排
  `{document_id}::e{k:04d}`），引用完整。
- `cell_index` 为原始数组位置；`cell_count` 为输入总数。
- `line` 保持 cell 内偏移；诊断透传后能定位到具体 cell。
- 不执行/不联网的行为测试覆盖委托解析与图片处理路径（非 import 检查）。
- 机械对照允许出现已登记的 BUG-md-1 修复差异；不为了与旧快照一致而撤回 Markdown 修复。

## 11. 评测口径

- ipynb 评测结果一律称 **“cell source 抽取”**；`silent_drop=0` 不得解释为 notebook 的
  outputs、附件等内容均被保留。
- 验收口径沿用：N 输入 = X 处理成功 + Y expected_failure 精确匹配（错误码一致）+ 0 非预期
  失败；expectations 修订 ≠ 算法提升。

## 12. 测试切分（按依赖，不按失败归类）

| 依赖 | 搬运时机 |
| --- | --- |
| 直接调用 IpynbParser | 机械搬运 |
| 经 registry / CLI / 已注册 pipeline 调用 ipynb | 注册启用 |
| 明确依赖未采用的 chunker 策略 | Stage 6（登记具体依赖与测试清单） |

先审阅依赖，再用运行结果核实分类；现有 chunker 下本应成立的内容守恒、引用完整性等断言
失败，仍是当前问题，不得归入 Stage 6。

## 13. 版本与 schema

- 注册时 `EVALUATOR_VERSION` 1.6 → **1.7**（能力封口：ipynb 解析注册 + auto 映射）。
- `REPORT_VERSION` **保持 1.3**：document schema 的 `source_type` 枚举与 ipynb locator
  分支已存在，evaluation report schema 的 `parser_used` 为自由字符串，无需结构扩展。
- 机械对照只用 dev 语料与公开 regression；**ipynb holdout 不进入直接解析、对照脚本或任何
  预跑**；完整候选固定干净 SHA 后才首跑（吸取 text 时序教训）。

## 14. 执行顺序（定案）

契约定稿（本文件）→ 冻结 dev/holdout → 机械搬运（不注册）→ 独立契约修正提交（版本字段 /
source / language / 忽略诊断）→ 注册启用（1.7）→ 全套回归 + ipynb-dev + UDM 校验 + 确定性
→ 固定干净候选 SHA 首跑 holdout 并封存报告 → `git merge --ff-only` 合入 main 后复验。
