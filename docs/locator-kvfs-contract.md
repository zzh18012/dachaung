# KVFS source_locator 契约（Stage 6 批次 3）

状态：草案 v1（待 GPT 5.6 Sol 裁决条文框架后冻结）。
裁决依据：2026-08-30 会话 6a91a872——断路成立并解除；目标从"统一定位键"
改为"统一 locator 协议 + 分族定位语义"；本批不加 file_offset；family
显式进入 locator。

## §0 盘点结论（断路器记录）

- schema `$id` 自基线起即 `kvfs.local`（对齐点预留），但自跑线从未写下
  KVFS locator 语义；六来源共用三套互斥坐标系（页几何 / 结构索引 /
  1 基物理行），ipynb 为容器混合；无任何公共定位键。
- 单一坐标模型被裁决否决（No fabricated precision：不得为统一伪造
  源格式不提供的粒度）。断路解除条件 = 本契约的两层模型。

## §1 两层模型

**统一层（resolver envelope）**：每个 `source_locator` 必须在给定原始
source artifact（`source_path` + `source_hash` 定位的字节）时，按本契约
定义的确定性 resolver 规则回溯到产生该 Element 的来源区域。

**分族层（family semantics）**：不同 locator family 使用各自坐标系；
不要求键同构，不要求可转换为统一 byte/char offset，不相互比较。

三不变量（全部 family 适用）：

1. **Determinism**：同一 source 字节 + 同一解析器版本 → 相同 locator。
2. **Resolvable**：locator + 原始文件足以执行契约回溯过程；不得依赖
   未记录的运行时状态。
3. **No fabricated precision**：源格式不能可靠提供的粒度不得伪造。

## §2 family discriminator

- 字段：`source_locator.family`（跟随 locator 本身，不挂在 source_type
  上；今天的一一对应是偶然事实，不是协议）。
- 语义：**只声明如何解释 locator**，不声明达到任何统一精度。
- 本批冻结四族（描述坐标模型，非文件格式）：

| family | source_type（现状） | 坐标模型 |
|---|---|---|
| `line_address` | markdown / html / text | 1 基物理行号 + 可选结构路径 |
| `structural_index` | docx | 文档对象索引（paragraph/table 等） |
| `page_geometry` | pdf | 1 基页码 + 可选 bbox |
| `container_line` | ipynb | 0 基 cell 索引 + cell 内 1 基行 |

## §3 各族冻结键与 resolver 规则

### line_address（markdown / html / text）

- 冻结键：`line`（必填，int ≥1，1 基、物理行、空行计入）；`section_path`
  （可选，string，`" > "` 连接的标题链）。
- resolver：按原始文件字节 decode（UTF-8）→ 按物理行切分（保留空行
  计数）→ `line` 指向该 Element 首行；`section_path` 提供结构上下文，
  不参与行定位，不得单独用于回溯。

### structural_index（docx）

- 冻结键：`paragraph_index`（int ≥0，正文段落计数器序）或 `table_index`
  （int ≥0，表格序）二者至少其一；`section`（int，节序）可选；
  `relationship_id`（string，图片关系 id）可选。
- schema 允许但解析器从未产出的键（`run_index`/`row_index`/`col_index`）
  本批不冻结 resolver 语义，视为保留键。
- resolver：解包 docx（zip）→ 读取 `word/document.xml` → 按文档顺序
  遍历 `<w:p>`/`<w:tbl>` 计数 → 命中索引即元素来源节点；`section`
  为节序上下文。注：resolver 定义在解压后 XML 层，不声明 zip 字节偏移。

### page_geometry（pdf）

- 冻结键：`page`（必填，int ≥1，1 基）；`bbox`（可选，4 元素数值数组，
  pdfplumber 坐标系 x0, top, x1, bottom）。
- resolver：以页为单位（`page` 命中物理页）；`bbox` 存在时声明该页
  内的几何区域。**不提供也不承诺**页内文本对象级或字节级定位；bbox
  粒度以解析器实际产出为准（缺失 = 未提供，不虚构）。

### container_line（ipynb）

- 冻结键：`cell_index`（必填，int ≥0，0 基，按 notebook JSON `cells`
  数组顺序）；`cell_type`（必填，`markdown|code|raw`）；`line`
  （可选，int ≥1，cell 内 1 基行；code/raw 无行语义时缺省为 1）；
  `section_path`（可选，仅 markdown cell）。
- resolver：解析 .ipynb JSON → `cells[cell_index]` 命中容器 → markdown
  cell 内按其 source 文本物理行回溯；code/raw cell 以整个 cell 为定位
  单元。注：`line` 定义在 cell 文本层，不声明 notebook 文件字节偏移。

## §4 版本语义（提案）

- 本批为 writer 能力变更（locator 新增 family 键）→ 新输出
  `schema_version = "0.3.0"`；`effective_schema_version` 无条件返回
  0.3.0（沿用批次 2 确立的 writer-能力语义）。
- 0.2.0：合法读格式；locator 不含 `family`（schema 以
  `not.required:["family"]` 精确排除）。
- 0.1.0：合法读格式；维持既有约束（仅 pdf/docx、无 source_spans、
  无 family）。
- 各版本分支：0.3.0 要求 locator 含 `family` 且等于该分支的 const 值；
  `source_spans` 规则沿用 0.2.0（0.3.0 同样允许）。
- EVALUATOR_VERSION 不变（1.7）：本批不动 evaluator 能力。

## §5 实现范围与防御

- 实现 = 全部解析器（fallback pdf/docx、markdown、html、text、ipynb、
  kreuzberg 适配器）在产出的每个 `source_locator` 上加 `family` 常量键；
  键值四选一，按 §2 表。不改任何现有定位键的取值逻辑（Determinism：
  既有键逐字节不变）。
- 契约测试：每族至少覆盖——family 正确性、既有键不变、schema 版本分支
  （0.1.0/0.2.0 拒 family、0.3.0 必填 family + const）、无 family 的旧
  输出仍可校验（读兼容）。
- resolver 为文档化规则；可机器执行的回溯断言（line_address 族的行命中、
  container_line 族的 cell 命中）以测试形式固化，structural_index /
  page_geometry 族的 resolver 本批只文档化不实现回溯器。

## §6 holdout 纪律

- 全新 fixture 目录（不复用批次 2 holdout）：每族至少 1 个最小样本
  （pdf/docx/md/html/text/ipynb 各 1，共 6），期望在实现前从本契约手工
  推导冻结（每 element 的 locator 全字段含 family）；固定干净 SHA
  一次性首跑，报告封存 outputs/，不重跑。

## §7 明确不做（本批 scope 锁死）

- 不加 `file_offset` / `raw_source_span` / 任何字节或字符偏移（裁决 b：
  语义成本未清，独立为未来能力批次，届时须定义 artifact 基准、
  byte/char、编码与 newline 口径、normalization 不可映射表示）。
- 不新增任何定位精度；不改键语义；不做跨族转换。
