# 表格 → Markdown 线性化契约（Stage 6 批次 5）

状态：草案 v1（2026-08-30 批次 4 封口裁决第 ② 项指定本批，条文送批）。

裁决依据：2026-08-30 会话 6a911adf 批次 4 封口裁决——批次 5 = (a)
表格→Markdown 线性化；执行边界：仅改 table element 的 canonical
content；先契约冻结表头、空单元格、合并单元格、多行文本、转义、
异常/空表行为及确定性；source_spans 坐标按线性化后 content 定义；
本批不做表题注关联与评测器变更；holdout 固定字节、实现前手工推导
期望。

## §0 盘点（2026-08-30）

- 表格 content 生成现有三处近似重复实现：fallback_parser
  `_rows_to_markdown`（pdf/docx）、markdown_parser `_rows_to_md`、
  html_parser `_rows_to_md`——语义相同（首行=表头、宽度补齐、
  `| a | b |` + `| --- |` 分隔行），但三副本有漂移风险。
- 已知缺口（全部为真实缺陷路径）：
  1. 单元格文本含 `|` 时未转义 → 产出的 markdown 表格列数错乱；
  2. 单元格文本含换行时未处理 → docx `cell.text` 以 `\n` 连接多段落、
     pdfplumber 单元格常含 `\n`，当前直接内嵌，破坏"一行一行"的表格
     结构；
  3. docx 0 行表：`_rows_to_markdown` 返回 `""` → `Element(content="")`
     触发 models 的 ValueError 崩溃路径（pdf/html 现状是跳过 element）。
- 表头语义现状：三处一律"第一行 = 表头"，无 thead/th 检测；本批不
  改变该口径，只成文冻结。
- 合并单元格现状：docx `row.cells` 对 gridspan/vmerge 重复给出同一
  单元格（内容重复）；pdfplumber 跨列格常为 None。均为库给定行为。
- chunker 现状：table 单独成 chunk，不动；source_spans 为 element
  content 的 `[start, end)` 区间，content 变化自然携带新坐标。

## §1 范围（本批锁死）

- 仅改变 table element 的 canonical `content` 生成口径，以及为消除
  三副本漂移把线性化实现收敛为一个共享纯函数（见 §3）。
- 不改：element 数量口径（除 §2 空表修复）、source_locator、relation、
  chunker、评测器、schema。**schema_version 维持 0.4.0 不升**：表格
  content 落在既有 `content: string` 字段内，writer 对外形状无变化。
- pdf 几何不进 holdout（沿用批次 3/4 追认先例：几何判定依赖
  pdfplumber 实测，手工推导等于预跑）。

## §2 canonical 形状冻结

输入：`rows: list[list[str | None]]`（各 parser 按现状提供）。

单元格预处理管线（顺序固定，逐格应用）：

1. `None` → `""`；
2. CR 规整：`\r\n` → `\n`，孤立 `\r` → `\n`；
3. 行内换行 `\n` → `<br>`（GFM 表格内换行语义，保留信息不折叠）；
4. 结构转义：`|` → `\|`；
5. `strip()` 两端空白（统一在共享函数内做，见裁决问 ①）；
6. 不做 Unicode 归一（无 NFC/NFKC），不做 HTML 实体转义。

结构规则：

- `width = max(len(r) for r in rows)`；短行右侧补 `""`（现状保持）；
- 表头 = `rows[0]`（无 thead 检测，冻结现状）；
- 输出行：`| c1 | c2 | ... |`、分隔行 `| --- | --- | ... |`（每列
  一个 `---`，冻结现状）、body 行同形；`\n` 连接，无首尾空行；
- `rows == []` → 返回 `""`，**caller 不产出 table element**（docx 由
  崩溃路径对齐为跳过；不产 warning——空表是合法输入不是异常）；
- 全空单元格表（rows 非空、内容全空）仍产出结构字符串（合法 content，
  element 照常产出）。

metadata 口径（冻结现状）：`row_count = len(rows)`（原始行数，不含
补齐）、`col_count = max(len(r) for r in rows)`（原始最长行）。

## §3 各 parser 接入

- 新文件 `app/parsers/table_linearize.py`：共享纯函数
  `linearize_table(rows) -> str`（§2 全部规则）；fallback/markdown/
  html 删除本地三副本改调用（ipynb 的 markdown cell 经 MarkdownParser
  自动继承）。纯函数无 I/O、无状态，契约测试直接喂构造 rows。
- markdown `_split_pipe_row` 增加 `\|` 反转义：按未转义 `|` 分列后，
  单元格内 `\|` → `|`（否则 re-render 会二次转义，roundtrip 不幂等）。
- docx：0 行表跳过 element（修复 §0 缺口 3 的 ValueError 路径）。
- pdf：`tbl.extract()` 行为不变，content 换经共享函数。
- html：rows 累积行为不变，content 换经共享函数。
- 合并单元格：保持库给定重复语义（docx 重复内容、pdf None→""），
  不去重、不加 span 标记、不重建跨行列结构。

## §4 确定性与不变量

- 同一 rows 输入 → 同一 content 字符串（逐字节确定）。
- 幂等性（roundtrip 不变量）：对 markdown 源，
  `linearize(split(rendered)) == rendered`，即已转义/已 `<br>` 的
  content 重新解析再渲染不变。
- 表格 element 数量不变（除 docx 0 行表从崩溃→不产出这一修复）；
  非 table element 完全不受影响。
- source_spans 语义不变：table 单独成 chunk，span 覆盖线性化后
  content 的字符区间，chunker 零改动。

## §5 契约测试与 holdout

- 契约测试（喂构造 rows / 构造文件）覆盖：`|` 转义与 md `\|` 反转义
  roundtrip；`\n`/`\r\n`/`\r` → `<br>`；None → `""`；短行补齐；
  单行表；全空表；0 行表不产出 element（docx 修复项）；合并单元格
  重复语义（真 docx）；三 parser 输出一致性（同一 rows 三处同串）。
- holdout（裁决⑤ 纪律沿用）：**全新**合成 fixture 一次性生成后字节
  固定（sha256 登记 ADOPTION.md，运行时禁重生成、首跑校验漂移即拒）：
  - 合成 docx：多段落单元格（触发 `\n`→`<br>`）、合并单元格（重复
    语义）、含 `|` 单元格、空单元格、普通对照表；
  - 合成 md：含 `\|` 转义、含 `<br>`、参差行；
  - 合成 html：含 `|` 单元格、th/thead（验证不特殊化）。
  期望 content 实现前手工推导冻结；固定干净 SHA 一次性首跑，封存
  outputs/，不重跑。
- dev 验收：evaluation 重跑对照批次 4 封存基线——本批 content 变化
  属预期，若 devset 含表格则相关 chunk 长度/文本类指标**允许差异**，
  逐项归因于 §2 规则（转义/`<br>`/strip），不做"全 SAME"要求；报告
  引用基线 commit 哈希（沿批次 3 裁决纪律）。

## §6 明确不做（本批）

- 不做表格题注关联（批次 7）、不动 figure_caption_* 评测（批次 6）。
- 不做 thead/th 表头检测、不对"首行非表头"做识别或调整。
- 不重建跨行列结构（rowspan/colspan 标记、去重、占位符均不做）。
- 不做 HTML 实体二次转义、不做 Unicode 归一。
- 不改 chunker、不改 schema、不升 schema_version。

## 送裁问题

1. strip 统一：建议共享函数内统一 `strip()`（pdf 现状不 strip，统一
   后 pdf 单元格前后空白会被去掉）——同意统一，还是维持各 parser
   现状（pdf 不 strip）？
2. 单元格换行 → `<br>`（建议，保信息）还是折叠为单空格（更"扁平"）？
3. md `\|` 反转义（roundtrip 幂等要求）是否同意引入？
4. docx 0 行表：跳过 element 不产 warning（建议，对齐 pdf/html）——
   同意？还是要产 warning？
5. 共享纯函数统一三副本（新文件 app/parsers/table_linearize.py）
   是否同意？
6. schema_version 维持 0.4.0 不升（content 属既有字段，writer 形状
   不变）是否同意？
7. holdout 设计（合成 docx+md+html 全新、字节固定、pdf 沿先例不进）
   是否同意？
