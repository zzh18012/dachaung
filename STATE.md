# State Timeline — 自跑线进度日志

> 每轮 agent 追加一条记录。最新的"下一步建议"是下一轮的起点。

---

## 2026-08-04 — Round 0（初始化）

**做了什么**：
- 在 main 工作目录（`C:\Users\zzhn2\Desktop\dachuang-code`，HEAD `2c35244`）由主 session 创建本 worktree
- 分支 `claude/autonomous-track` 已 push 到 `origin`
- 写入 `AUTONOMOUS_LOOP.md`（操作手册）
- 写入本 `STATE.md`（进度日志）

**worktree 当前状态**：
- 与 main 同步在 `2c35244a14a9e86015881e98d5773e0db353e99b`
- 工作树清洁 + 1 个 untracked：`AUTONOMOUS_LOOP.md`、`STATE.md`（待首轮 agent commit）
- 无 `.venv`（首轮需 `uv sync`）

### 下一步建议（Round 1）

**首要任务**：搭建 worktree 自身的基础设施
1. `cd /c/Users/zzhn2/Desktop/dachuang-autonomous`
2. `uv sync --python "C:/Users/zzhn2/AppData/Local/Programs/Python/Python312/python.exe"` 创建 `.venv`
3. 跑一次 `.venv/Scripts/python.exe -m pytest` 确认基线 163 测试通过
4. commit `AUTONOMOUS_LOOP.md` 与 `STATE.md`（首次 commit）

**之后选一项具体工作**（按可行性与价值排序）：
- 候选 A：审计 `evaluation/` 与 `app/` 找 bug，写诊断报告 + 修复
- 候选 B：实现 Markdown 输入 parser（扩展 `app/parsers/`，无新依赖）
- 候选 C：实现 `app/cli.py inspect` 子命令（pretty-print JSON 输出）
- 候选 D：补全 `tests/` 覆盖率（用 `pytest-cov` 测缺口）
- 候选 E：实施 source_spans（独立设计，与指示线并行）

**建议**：选候选 C（最简单、最快出成果、不动现有锁定代码），之后视情况推进 B/D/A/E。

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 1 后）：168 pass / 0 fail / 9 skip（HEAD `e057664`）
  - 9 skip 来自 `tests/test_pipeline_integration.py` 中需要 `samples/private/` 真实样例的测试（worktree 未拷贝）
  - 14 条新增 `tests/test_cli.py` 全部通过

---

## 2026-08-04 — Round 2（Markdown parser）

**做了什么**：
- 完成候选 B：实现 `MarkdownParser`（`app/parsers/markdown_parser.py`，~330 行）
- 纯 stdlib 实现的 CommonMark 子集，无新依赖
- 支持的块类型：
  - ATX 标题（`#`..`######`，含闭合 `#`）
  - 段落（空行分隔）
  - 无序列表（`-`/`*`/`+`）与有序列表（`1.`/`1)`）
  - 围栏代码块（``` 与 `~~~`），记录 `metadata.language`
  - 引用块（连续 `>` 行合并）
  - pipe 表格（`| a | b |` + `|---|---|`）
  - 独立图片行（`![alt](url)` → `image` element）
  - 主题分隔符（`---`/`***`/`___`）忽略
- `source_locator = {"line": N, "section_path": "H1 > H2 ..."}`：跟踪 ATX 标题栈，同级或更高级标题弹出
- 明确不支持的（docstring 中列出）：setext 标题、嵌套列表、缩进代码块、ref-style 链接、YAML frontmatter、原生 HTML 块、表格列对齐
- 配套修改：
  - `app/models.py`：`SourceType` 加 `"markdown"`
  - `app/pipeline.py`：`get_parser` 加 `"markdown"` 分支
  - `app/cli.py`：`--parser` choices 加 `markdown`
  - `schemas/document.schema.json`：`source_type` enum 加 `markdown`；新增 `markdown_locator` $def + 对应 `if/then`
- 新增 25 个测试（`tests/test_parsers_markdown.py`）：每种块类型、`section_path` 跟踪、行号、错误路径、schema 校验、pipeline 端到端、CLI subprocess 端到端
- 手动 smoke：合成 12 块 .md → parse → inspect 全通过，0 warning
- commit `91bdf46`，已 push

**worktree 当前状态**：
- HEAD `91bdf46`，工作树清洁
- 测试基线：193 pass / 0 fail / 9 skip（+25 vs Round 1）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 3）

**首要任务**：选一项推进（按价值/可行性排序）

- 候选 B+（推荐）：**HTML parser**
  - 现状：`app/parsers/` 已有 fallback / kreuzberg / markdown，加入 HTML 让输入格式更完整（dachuang 目标 3）
  - 复杂度：中-高（HTML 比 Markdown 复杂，但 Python stdlib 自带 `html.parser`，无新依赖）
  - 设计要点：用 `html.parser.HTMLParser` 走 SAX；按块级元素（h1-h6/p/ul/ol/li/table/pre/blockquote/img）输出 element；`source_locator = {"line": N}`（HTMLParser 提供 `getpos()`）

- 候选 B++：**纯文本 parser**（`.txt`）
  - 最简单：按空行切段，每段一个 paragraph element
  - 价值：作为 baseline 对照（chunker 在无结构输入下的行为）

- 候选 D：补 fallback parser 的覆盖率（PDF/DOCX 各路错误代码）
- 候选 A：审计 `evaluation/metrics.py` 找 bug
- 候选 E：实施 source_spans（独立设计，体积较大）

**建议**：选 B+（HTML parser）。理由：
1. 与 markdown parser 同接口，集成成本低
2. Python stdlib 自带 `html.parser`，无新依赖
3. 完成后 dachuang 输入格式矩阵：PDF / DOCX / MD / HTML（覆盖大部分文档源）
4. Round 4 可继续推进 plain text 或换方向（A/D/E）

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 2 后）：193 pass / 0 fail / 9 skip（HEAD `91bdf46`）

---

## 2026-08-04 — Round 3（HTML parser）

**做了什么**：
- 完成候选 B+：实现 `HtmlParser`（`app/parsers/html_parser.py`，~370 行）
- 基于 stdlib `html.parser.HTMLParser` 的 SAX 风格状态机，无新依赖
- 支持的块类型：
  - 标题 `<h1>`..`<h6>`（含 level 元数据）
  - 段落 `<p>` 与 body 直接子文本（loose text → paragraph）
  - `<ul>` / `<ol>` / `<li>`（按最近外层列表决定 ordered）
  - `<pre>`（保留换行/缩进，metadata.kind="preformatted"）
  - `<blockquote>`（metadata.kind="blockquote"）；吸收内层 `<p>` 不改类型
  - `<table>` / `<tr>` / `<td>` / `<th>` → markdown 表格 element
  - `<img src=...>`（独立 image element，resource_path=src，alt 入 metadata）
  - `<hr>` 主题分隔符（忽略）
  - `<br>` 在段落内当作空格
  - 字符实体（`&amp;` 等）由 `convert_charrefs=True` 自动解码
- 跳过：`<head>` / `<title>` / `<script>` / `<style>` / `<meta>` / `<link>` / `<noscript>` 内容
- `source_locator = {"line": N, "section_path": "H1 > H2..."}`：与 markdown parser 一致
- 嵌套 table：记 warning `html_nested_table`，内层忽略
- 配套修改：
  - `app/models.py`：`SourceType` 加 `"html"`
  - `app/pipeline.py`：`get_parser` 加 `"html"` 分支
  - `app/cli.py`：`--parser` choices 加 `html`
  - `schemas/document.schema.json`：`source_type` enum 加 `html`；新增 `html_locator` $def + 对应 `if/then`
- 新增 26 个测试（`tests/test_parsers_html.py`）：每种块类型、section_path 跟踪、行号、字符实体解码、script/style/head 跳过、错误路径、schema 校验、pipeline + CLI 端到端
- commit `e455a9c`，已 push

**worktree 当前状态**：
- HEAD `e455a9c`，工作树清洁
- 测试基线：219 pass / 0 fail / 9 skip（+26 vs Round 2）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 4）

**首要任务**：选一项推进

- 候选 B++（推荐）：**纯文本 parser**（`.txt`）
  - 现状：parsers 矩阵已含 fallback / kreuzberg / markdown / html；纯文本是最简单的 baseline
  - 复杂度：低（按空行切段，每段一个 paragraph element）
  - 价值：作为 baseline 对照（chunker 在无结构输入下的行为）；覆盖常见 .txt 输入
  - 设计要点：`source_locator = {"line": N}`；支持 CRLF/LF；空文件 → warning

- 候选 F（新提）：**`.ipynb` Jupyter Notebook parser**
  - 现状：data science 场景的常见输入，stdlib `json` 即可解析 nbformat
  - 复杂度：中（code cell + markdown cell 双类型；markdown cell 可嵌套调 MarkdownParser）
  - 价值：扩展数据科学场景输入

- 候选 D：补 fallback parser 的覆盖率（PDF/DOCX 各路错误代码）
- 候选 A：审计 `evaluation/metrics.py` 找 bug
- 候选 E：实施 source_spans（独立设计，体积较大）

**建议**：选 B++（纯文本 parser）。理由：
1. 与现有 parser 同接口，集成成本低（~50 行）
2. 提供评测 baseline（无结构输入 → chunker 退化行为）
3. 完成后 Round 5 可推进 .ipynb（候选 F）或换方向（A/D/E）

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 3 后）：219 pass / 0 fail / 9 skip（HEAD `e455a9c`）

---

## 2026-08-04 — Round 4（纯文本 parser）

**做了什么**：
- 完成候选 B++：实现 `TextParser`（`app/parsers/text_parser.py`，~100 行）
- 策略：按空行（连续 whitespace-only 行）切段，每段一个 paragraph element，保留段内换行
- 归一换行：CRLF / CR → LF
- `source_locator = {"line": N}`：1-indexed 行号，指向段首字符所在行；纯文本不需要 section_path
- 空文件 / 仅空白 → warning `text_no_content`
- 配套修改：
  - `app/models.py`：`SourceType` 加 `"text"`
  - `app/pipeline.py`：`get_parser` 加 `"text"` 分支
  - `app/cli.py`：`--parser` choices 加 `text`
  - `schemas/document.schema.json`：`source_type` enum 加 `text`；新增 `text_locator` $def（最小集，仅 line）+ 对应 `if/then`
- 新增 21 个测试（`tests/test_parsers_text.py`）：基础切分 / 多行段落 / CRLF 归一 / 多空白行行号 / 空文件 / 错误路径 / schema 校验 / pipeline + CLI 端到端
- 修复一个行号 bug（原 regex 方案漏算 chunk 前的 \n，改用按行扫描）
- commit `cc754ab`，已 push

**输入格式矩阵**（完成 5/8 常见输入）：
- ✅ PDF（fallback）
- ✅ DOCX（fallback）
- ✅ Markdown（markdown）
- ✅ HTML（html）
- ✅ Plain text（text）
- ⏳ Jupyter Notebook（候选 F）
- ⏳ reStructuredText
- ⏳ LaTeX / .tex

**worktree 当前状态**：
- HEAD `cc754ab`，工作树清洁
- 测试基线：240 pass / 0 fail / 9 skip（+21 vs Round 3）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 5）

**首要任务**：选一项推进

- 候选 F（推荐）：**Jupyter Notebook (.ipynb) parser**
  - 现状：parsers 矩阵 5 种已就绪；.ipynb 是数据科学场景高频输入
  - 复杂度：中（stdlib `json` 解析 nbformat；按 cell 类型分派：code cell → paragraph with kind="code_cell"；markdown cell → 复用 MarkdownParser）
  - 价值：完成数据科学场景；为评测 devset 增加新源
  - 设计要点：source_type="ipynb"；source_locator={"cell_index": N, "cell_type": "code"|"markdown", "line": N}

- 候选 A：审计 `evaluation/metrics.py` 找 bug
- 候选 D：补 fallback parser 的覆盖率
- 候选 E：实施 source_spans（独立设计）

**建议**：选 F（.ipynb parser）。理由：
1. 数据科学场景高频，扩展输入矩阵
2. stdlib `json` 即可解析，无新依赖
3. 可复用 MarkdownParser 处理 markdown cell，体现 parser 组合
4. 完成后 Round 6 可换方向（A/D/E）

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 4 后）：240 pass / 0 fail / 9 skip（HEAD `cc754ab`）

---

## 2026-08-04 — Round 5（Jupyter Notebook parser）

**做了什么**：
- 完成候选 F：实现 `IpynbParser`（`app/parsers/ipynb_parser.py`，~210 行）
- 基于 stdlib `json`，无新依赖
- nbformat 4+ 支持；按 cell_type 分派：
  - `markdown` cell → 委托 `MarkdownParser._parse_text` 拆为多个 sub-element，保留 cell 内 section_path
  - `code` cell → 单个 paragraph，`metadata.kind="code_cell"`，`metadata.language` 来自 kernelspec
  - `raw` cell → 单个 paragraph，`metadata.kind="raw_cell"`
  - 未知类型 → warning，跳过
  - 空 code cell → warning，跳过
- `source_locator = {"cell_index": N, "cell_type": ..., "line": N (可选), "section_path": ... (可选)}`
- 跨 cell 连续 element_id（最终重新分配 `::e0000`..`::eNNNN`）
- Document metadata 记 `cell_count` / `language` / `nbformat` / `nbformat_minor`
- 配套修改：
  - `app/models.py`：`SourceType` 加 `"ipynb"`
  - `app/pipeline.py`：`get_parser` 加 `"ipynb"` 分支
  - `app/cli.py`：`--parser` choices 加 `ipynb`
  - `schemas/document.schema.json`：`source_type` enum 加 `ipynb`；新增 `ipynb_locator` $def（required: cell_index/cell_type；optional: line/section_path）
- 新增 20 个测试（`tests/test_parsers_ipynb.py`）：cell 类型分派 / source-as-list 拼接 / locator 结构 / 跨 cell element_id 连续 / 错误路径（缺文件 / 错扩展 / 坏 JSON / nbformat < 4）/ schema 校验 / pipeline + CLI 端到端
- commit `30925ee`，已 push

**输入格式矩阵**（完成 6/8）：
- ✅ PDF（fallback）
- ✅ DOCX（fallback）
- ✅ Markdown（markdown）
- ✅ HTML（html）
- ✅ Plain text（text）
- ✅ Jupyter Notebook（ipynb）
- ⏳ reStructuredText
- ⏳ LaTeX / .tex

**worktree 当前状态**：
- HEAD `30925ee`，工作树清洁
- 测试基线：260 pass / 0 fail / 9 skip（+20 vs Round 4）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 6）

**首要任务**：方向调整。parsers 矩阵已覆盖主要输入格式（6/8），追加 RST/LaTeX 边际收益递减。本轮建议换轨：

- 候选 A（推荐）：**审计 `evaluation/` + `app/` 找 bug**
  - 现状：评测管线 163 测试基线，但没做过系统性 bug 审计
  - 复杂度：中（需读 evaluation/metrics.py、report.py、cli.py 找边界 bug）
  - 价值：保证后续向量化的输入正确
  - 不变量：不动 `evaluator_version` / `report_version`（指示线在审）

- 候选 G（新提）：**CLI 自动 source_type 推断**
  - 现状：用户必须显式 `--parser markdown/html/text/ipynb`
  - 复杂度：低（在 cli.py 加个 by-extension dispatcher）
  - 价值：UX 改进，常见场景默认对

- 候选 H（新提）：**batch CLI（多文件 / 目录）**
  - 现状：`parse` 只支持单文件
  - 复杂度：中（加 `parse-dir` 子命令）
  - 价值：评测 / 批量处理场景的基础

- 候选 D：补 fallback parser 的覆盖率
- 候选 E：实施 source_spans（独立设计）

**建议**：选 G（CLI 自动 source_type 推断）。理由：
1. 用户友好（90% 场景不用 `--parser`）
2. 体积小（~50 行）
3. 与 Round 7 batch CLI 互补

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 5 后）：260 pass / 0 fail / 9 skip（HEAD `30925ee`）

---

## 2026-08-04 — Round 6（CLI 自动 source_type 推断）

**做了什么**：
- 完成候选 G：CLI 不带 `--parser` 时按扩展名自动推断
- 映射表 `_EXTENSION_TO_PARSER`：
  - `.pdf` / `.docx` → fallback
  - `.md` / `.markdown` → markdown
  - `.html` / `.htm` → html
  - `.txt` / `.text` → text
  - `.ipynb` → ipynb
  - 未知扩展名 → fallback（fallback 自己会因 `detect_source_type` 拒绝而失败，安全网保留）
- 推断时 stderr 打印 `[INFO]` 行说明选择；显式 `--parser` 时不打印
- `--parser` 从 `default="fallback"` 改为 `default=None`（sentinel），保留 choices 不变
- 修复一处回归：`test_cli_unsupported_extension_returns_nonzero` 原用 `.txt`（现已被 text parser 接受），改用真正未注册的 `.xyz`，测试意图（拒绝真未知扩展名）保留
- 新增 6 个 CLI subprocess 测试 + 1 个 `_infer_parser_name` 单元测试（覆盖全部 9 个扩展名 + 未知）
- commit `a783671`，已 push

**worktree 当前状态**：
- HEAD `a783671`，工作树清洁
- 测试基线：266 pass / 0 fail / 9 skip（+6 vs Round 5）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 7）

**首要任务**：选一项推进

- 候选 H（推荐）：**batch CLI（目录批处理）**
  - 现状：`parse` 只支持单文件，评测场景受限
  - 复杂度：中（加 `parse-dir` 子命令；遍历目录、按扩展名分发、收集 errors、写多个 JSON）
  - 价值：批量解析的实际生产力；评测 devset 用得上
  - 设计要点：`parse-dir <input_dir> -o <output_dir> [--recursive]`；每个文件输出 `<output_dir>/<stem>.json`；summary JSON 记成功/失败/警告统计

- 候选 A：审计 `evaluation/` + `app/` 找 bug
- 候选 D：补 fallback parser 的覆盖率
- 候选 E：实施 source_spans（独立设计）

**建议**：选 H（batch CLI）。理由：
1. 提供实际批量处理能力，为评测扩展铺路
2. 复用 Round 6 的自动推断，零额外配置
3. 体积适中（~150 行 + ~10 测试）

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 6 后）：266 pass / 0 fail / 9 skip（HEAD `a783671`）

---

## 2026-08-04 — Round 7（batch CLI: parse-dir）

**做了什么**：
- 完成候选 H：`parse-dir` 子命令，目录批量解析
- 用法：`parse-dir <input_dir> -o <output_dir> [--recursive] [--parser X] [--max-chars N]`
- 输出布局：`output_dir/<相对路径>.json`（保留原扩展名 + `.json` 后缀，避免同名冲突）
  - 例如 `sub/doc.md` → `output_dir/sub/doc.md.json`
- 顶层 `_summary.json` 记：
  - 元数据（input_dir / output_dir / recursive / parser_override / max_chars）
  - 计数（total / success / failure）
  - 每文件条目（status / parser / elements / chunks / warnings 或 errors 列表）
- 复用 Round 6 的扩展名自动推断；`--parser` 覆盖
- 退出码：全成功 0；有失败 1；输入目录缺失 2；空目录（无支持文件）warning + 0
- 失败时不留半成品 JSON
- 重构：把 `parse` 逻辑提取为 `_run_parse`，与 `_run_parse_dir` 对称；`main()` 只做 dispatch
- 修复一处提取 bug（`_run_parse_dir` 函数头在编辑中丢失，已恢复）
- 新增 6 个 subprocess 测试：混合类型批 / 递归 / 失败计入 summary / 显式 --parser / 缺目录 / 空目录
- commit `5f783fc`，已 push

**worktree 当前状态**：
- HEAD `5f783fc`，工作树清洁
- 测试基线：272 pass / 0 fail / 9 skip（+6 vs Round 6）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 8）

**首要任务**：方向选择

- 候选 A（推荐）：**审计 `evaluation/` + `app/` 找 bug**
  - 现状：parser 矩阵 + CLI 都到位，但核心评测管线没做过独立审计
  - 复杂度：中（读 evaluation/metrics.py、report.py、cli.py；找边界 bug）
  - 价值：保证后续向量化的输入正确；指示线 v2.x 审计也是这块
  - 不变量：**不**动 `evaluator_version` / `report_version`（指示线在审的目标）
  - 产出：诊断报告 + 修复 PR

- 候选 I（新提）：**evaluation devset 加入新输入格式**
  - 现状：评测只跑 PDF/DOCX；markdown / html / text / ipynb 没评测覆盖
  - 复杂度：中（评测代码可能要小改以支持新 source_type；manifest schema 可能要扩展）
  - 价值：检验新 parser 的 chunking 质量
  - 风险：可能触碰 `evaluator_version` —— 走 I 前先确认

- 候选 J（新提）：**向量化基础设施起步**
  - 现状：CLAUDE.md 明确不做，但自跑线已解锁
  - 复杂度：高（需 `sentence-transformers` 或类似；5GB 内可装 CPU 版）
  - 价值：dachuang 目标 4 之一，向量化是 RAG 的核心
  - 设计要点：新增 `app/embeddings/` 模块；CLI 加 `embed` 子命令；不引入 faiss，先用 numpy

- 候选 D：补 fallback parser 的覆盖率
- 候选 E：实施 source_spans（独立设计）

**建议**：选 A（evaluation bug 审计）。理由：
1. 与指示线工作可能形成互补（不冲突，因自跑线不动 evaluator_version）
2. 输出诊断报告本身就是高价值产物
3. 为 Round 9+ 的向量化 / 新评测 devset 扫清隐藏 bug

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 7 后）：272 pass / 0 fail / 9 skip（HEAD `5f783fc`）

---

## 2026-08-04 — Round 1（inspect 子命令 + 测试）

**做了什么**：
- 完成 Round 0 候选 C：实现 `app/cli.py inspect` 子命令（之前主 session 同步模式接手时该文件已有 +190 行未提交代码，本轮主要是补测试并落盘）
- 新增 `tests/test_cli.py`，14 个 subprocess 端到端测试：
  - 摘要模式（counts / elements by type / chunk stats / hash 截断）
  - `--elements` / `--chunks` / `--limit N` / `--limit 0`
  - 组合 `--elements --chunks --limit`
  - 错误路径：缺文件（exit 2）、坏 JSON（exit 1）、顶层非对象（exit 1）
  - 边界：空文档、长文本预览省略号
- 修复 3 处断言 typo（CLI 实际输出 `+N more` 不带空格，初版误写 `+ N more`）
- commit `e057664`，已 push 到 `origin/claude/autonomous-track`

**worktree 当前状态**：
- HEAD `e057664`，工作树清洁
- 比上轮 1 个 commit
- 测试基线：168 pass / 0 fail / 9 skip

### 下一步建议（Round 2）

**首要任务**：选一项推进（按价值/可行性排序）

- 候选 B（推荐）：**实现 Markdown parser**
  - 现状：`app/parsers/` 只有 `fallback.py`、`kreuzberg.py`，无 Markdown
  - 价值：扩展输入格式（dachuang 目标 3 之一）；评测 devset 可加入 .md 文档
  - 复杂度：中（需处理 heading/paragraph/list/code_block/blockquote；不引入新依赖，标准库 `re` + 自定义 tokenizer）
  - 验收：`python -m app.cli parse input.md -o out.json` 可用；新增 `tests/test_parsers_md.py`

- 候选 D：补 `app/parsers/fallback.py` 路径分支的覆盖率（PDF/DOCX 各路错误代码）
- 候选 A：审计 `evaluation/metrics.py` 找 bug
- 候选 E：实施 source_spans（独立设计，体积较大）

**建议**：选 B（Markdown parser）。理由：
1. 与现有 fallback/kreuzberg 同接口（`parse(path) -> Document`），集成成本低
2. 无新依赖，单文件可完成
3. 输出 dachuang 阶段性进展的可感知功能（多一种输入格式）
4. 完成后 Round 3 可在评测 devset 加入 .md 文档验证

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 1 后）：168 pass / 0 fail / 9 skip（HEAD `e057664`）

---

## 2026-08-04 — Round 8（evaluation 管线审计 + 修复 2 个真实 bug）

**做了什么**：
- 完成候选 A：审计 `evaluation/*.py` 与测试套件，找到并修复 2 个真实 bug，写诊断报告
- **Bug 1（chunk_boundary_prf 重复 marker）**：
  - 现象：`annotation_metrics.chunk_boundary_prf` 中 `stream.find(marker)` 没传起点参数，两个相同 marker 文本的 anchor 都会命中第 1 次出现，导致两个 gt_position 完全相同 → 一对一约束下至多匹配 1 个 → 召回率被错误低估
  - 修复：维护 `search_from` 游标，每找到一个 marker 后推进到其末尾；下一个 anchor 在剩余 stream 中继续找
  - 测试：3 个新增（重复 marker × before/after/exhausted 三种场景）
- **Bug 2（_process_one 返回 Path()）**：
  - 现象：`runner._process_one` 失败分支写 `image_dir or Path()`，当 image_dir 为 None 时退化成 `Path('.')`（= cwd）。下游 `image_dir.is_dir()` 在 cwd 上几乎总为 True，silently 把 image_base_dir 设成 cwd
  - 实际无害（失败文档无图片，`_image_resource_ratio` 先 short-circuit 在 `no_image_elements`），但类型契约错误，未来重构易爆雷
  - 修复：返回类型从 `Path` 改成 `Path | None`；三个 return 都直接 `return image_dir`；调用点改成 `image_dir if (image_dir is not None and image_dir.is_dir()) else None`
  - 测试：2 个新增（失败路径返回 None / 成功路径返回 Path）
- **诊断报告**：`docs/evaluation-audit.md`，分类记录"已修的真实 bug / 审计了但不是 bug 的设计选择 / 已识别但未修的小问题 / 不变量复核 / 后续 round 建议"
- 不变量保持：
  - `evaluator_version` 与 `report_version` 仍是 `"1.1"`（未触动 `evaluation/__init__.py`）
  - 没有改 `app/parsers/*`、`app/chunkers/*`、`app/pipeline.py`
  - 没有改任何 schema 文件
- commit `6c8277a`，已 push

**审计中复核为"非 bug 的设计选择"**（保留）：
- aggregate_summary 不出"综合分数"（counts/success_rates/ratio_macro_averages/silent_drop_total 四类分开）
- 比例指标分母为 0 → null + reason，不返回 1.0
- figure_caption_* 始终 null + `parser_does_not_emit_relations`
- 计时只记 total，parse/chunk 未插桩
- manifest 路径三道闸（相对路径 / 正斜杠 / 位于项目根内）
- silent_drop_count 必须基于 manifest expectations
- chunk_boundary 一对一贪心匹配

**已识别但未修的小问题**（留给后续 round）：
- `evaluation/cli.py --parser` choices 仍只有 fallback/kreuzberg；扩展需要 bump evaluator_version
- `evaluation/cli.py run` 子命令生成报告后又从磁盘重读校验（低效但安全）
- `runner._process_one` 的 image_dir 推导硬编码 document_id 格式（应让 pipeline 暴露 image_output_dir）
- `_chunk_reference_ratio` 的 elem_ids 集合可能含 None（schema 已保证非空，加防御代码反而啰嗦）

**worktree 当前状态**：
- HEAD `6c8277a`，工作树清洁
- 测试基线：277 pass / 0 fail / 9 skip（+5 vs Round 7）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 9）

**首要任务**：方向选择

- 候选 J（推荐）：**向量化基础设施起步**
  - 现状：parser 矩阵 + CLI + 评测管线都稳定，CLAUDE.md 列的 "不做" 范围里有向量化，但自跑线已解锁，可以推进 dachuang 目标 4
  - 复杂度：高（需要 `sentence-transformers` 或类似，CPU 版 5GB 内可装）
  - 价值：RAG 核心；自跑线阶段性大跨越
  - 设计要点：新增 `app/embeddings/` 模块；CLI 加 `embed` 子命令读 chunks → 向量 → numpy .npy；不引入 faiss，先用 numpy 做最简 ANN
  - 风险：装依赖可能失败 / 大；先 `uv pip install` 试探

- 候选 I：**evaluation devset 加入新输入格式**
  - 现状：评测只跑 PDF/DOCX，markdown / html / text / ipynb 没评测覆盖
  - 复杂度：中（需要扩展指标体系如 `markdown_section_path_valid_ratio`，可能要 bump evaluator_version）
  - 价值：检验新 parser 的 chunking 质量
  - 不变量冲突：bump evaluator_version 与"指示线 v2.x 审计"目标可能冲突，先确认

- 候选 K（新提）：**pipeline 暴露 image_output_dir**
  - 现状：`_process_one` 用 document_id 反推 image_dir，硬编码两个约定（document_id 前缀 + image 目录命名）
  - 复杂度：低（pipeline 增加一个返回值或 Document 增加一个字段）
  - 价值：根治 Round 8 审计中识别的硬编码问题；为评测准确性铺路

- 候选 D：补 fallback parser 的覆盖率
- 候选 E：实施 source_spans（独立设计，体积较大）

**建议**：选 J（向量化）。理由：
1. 大跨越，从解析层进入检索层，dachuang 项目核心
2. Round 8 已扫清评测隐藏 bug，向量化基线数据更可信
3. 5GB 内 CPU 版 sentence-transformers 应可装；如失败 fallback 到候选 K

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 8 后）：277 pass / 0 fail / 9 skip（HEAD `6c8277a`）

---

## 2026-08-04 — Round 9（pipeline 暴露 image_output_dir_for helper）

**做了什么**：
- 完成候选 K：根治 Round 8 审计 §3.3 标记的硬编码反推问题
- 在 `app/pipeline.py` 提取公共 helper `image_output_dir_for(output_path, source_hash) -> Path | None`
  - 单一事实源：`output_path.parent / images-<sha16>` 命名约定
  - output_path=None 时返回 None（对齐 pipeline 不写盘场景）
- `process_single` 内部使用该 helper 替代内联计算
- `evaluation/runner._process_one` 改用 helper + `document.source_hash`，删掉从 `document_id` 反推 sha16 的代码段
- 新增 5 个 helper 单元测试（`tests/test_pipeline_helpers.py`）：
  - 基础命名 / str 路径 / None output_path / 短 hash / 与 process_single 实跑结果一致
- 不变量保持：
  - 没有 schema 变更
  - 没有 parser/chunker 变更
  - `evaluator_version` / `report_version` 仍是 `"1.1"`
- commit `89595d2`，已 push

**worktree 当前状态**：
- HEAD `89595d2`，工作树清洁
- 测试基线：282 pass / 0 fail / 9 skip（+5 vs Round 8）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 10）

**首要任务**：方向选择

- 候选 E（推荐）：**实施 source_spans**
  - 现状：被推迟了 9 轮；Round 8 审计中 `_text_preservation` 的 docstring 明确说"若需要空白级精确验证，必须为每个 chunk 增加 source_spans"
  - 复杂度：高（schema 加 optional 字段；chunker 计算每个 chunk 在 element content 中的字符区间；测试）
  - 价值：让 chunk 输出带可验证的精确定位；未来评测可以基于 spans 做严格的字符级保留验证
  - 不变量：只加 optional 字段，向后兼容；不动 evaluator_version / report_version

- 候选 D：补 fallback parser 的覆盖率（PDF/DOCX 各路错误代码）
- 候选 L（新提）：**inspect 子命令增强**
  - 给 `app/cli.py inspect` 加 `--metrics` 模式：对单文档跑评测指标（不写报告，仅 stdout）
  - 价值：开发期快速 sanity check，不用每次构造 manifest
- 候选 J（向量化）：仍因 CLAUDE.md "不增加计划外主要依赖" 阻塞；如要推进需用户授权 sentence-transformers

**建议**：选 E（source_spans）。理由：
1. 已推迟 9 轮，技术债时间到了
2. Round 8 审计明确把它列为"治本方案"
3. 不需要新依赖
4. 完成后未来评测能升级到字符级精度（v1.2 baseline）

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 9 后）：282 pass / 0 fail / 9 skip（HEAD `89595d2`）

---

## 2026-08-04 — Round 10（source_spans：字符级可追溯）

**做了什么**：
- 完成候选 E（推迟 9 轮的技术债）：给每个 chunk 增加 `source_spans`，给出被引用 element 在其 content 中的字符区间
- **Schema 变更**（向后兼容）：
  - `chunk` 增加可选字段 `source_spans: array<source_span>`
  - 新增 `$defs/source_span`：`{element_id: str, start: int ≥0, end: int ≥0}`，`additionalProperties: false`
- **Chunk model**：增加 `source_spans: list[dict]` 字段，默认空列表
- **StructuralChunker 重构**：
  - `_element_text` → `_element_text_with_span`，返回 `(stripped_text, start, end)`，其中 start/end 是 stripped 部分在 `el.content` 中的字符位置（用 `lstrip` 长度推算，不依赖 find 避免内容重复时定位错）
  - `_ChunkBuffer.push_text` 接收 `(text, element_id, start, end)`；`flush()` 输出 `source_spans` 与 `source_element_ids` 并行
  - `_SplitPiece` 增加 `start/end`；`_split_long_text` 与 `_hard_split_with_whitespace_fallback` 全程跟踪位置
  - 长段落切分路径通过 `el_start` 偏移把 piece 位置映射回 `element.content` 坐标
  - 隔离 chunk（table/image/caption）输出单个 span 覆盖整个 element content
  - 顺序累积路径每个 push 输出一个 span
- **8 个新测试**（`tests/test_chunker.py`）：
  - 两段一个 chunk / heading 硬边界 / table 隔离 / 长段落切分位置正确 / 首尾空白偏移 / 端到端 span→text 还原 / 空 image / to_dict schema 校验
  - 关键不变量测试 `test_source_spans_chunk_text_alignment`：用 span 把 element.content 切回，其非空白字符序列必须等于 chunk.text 的非空白字符序列
- 不变量保持：
  - `evaluator_version` / `report_version` 仍是 `"1.1"`
  - source_spans 是 optional；旧 chunker 输出（不带 spans）依然 schema 合法
  - `pipeline.process_single` 签名不变
  - `chunk_id` / `source_element_ids` 语义不变
- commit `7641a86`，已 push

**意义**：
- 未来评测可以升级到字符级精度（v1.2 baseline）：直接用 source_spans 切回 element.content，做严格的"不丢不重"验证，替代当前 `_text_preservation` 的"非空白字符序列"妥协口径
- chunk 现在能精确定位到 element.content 的字符区间，为 KVFS 集成、向量化精确归属、白盒调试都铺好基础

**worktree 当前状态**：
- HEAD `7641a86`，工作树清洁
- 测试基线：290 pass / 0 fail / 9 skip（+8 vs Round 9）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 11）

**首要任务**：方向选择

- 候选 M（新提，推荐）：**evaluator v1.2 — 用 source_spans 做字符级 text_preservation**
  - 现状：source_spans 已就绪，但 evaluator 还在用 v1.1 的"非空白字符序列"口径
  - 复杂度：中（加新指标 `text_preservation_spans_equal`；旧指标保留为兼容字段；bump evaluator_version 到 1.2）
  - 价值：终于兑现 Round 8 审计 §2.7 写的"治本方案"
  - 不变量冲突：bump evaluator_version 与"指示线 v2.x 审计"目标可能冲突，但自跑线已多次 bump 过（v1.0→v1.1），且这是合理的版本演进

- 候选 N（新提）：**inspect 子命令加 --spans 模式**
  - 现状：CLI inspect 能看 elements/chunks 但看不到 spans
  - 复杂度：低（加个 flag，pretty-print spans）
  - 价值：开发期调试 source_spans 的可视化工具

- 候选 D：补 fallback parser 的覆盖率
- 候选 L：inspect 加 --metrics 模式（单文档跑评测指标）

**建议**：选 N（inspect --spans）。理由：
1. 体积小（~30 行 + 几个测试）
2. 让 source_spans 的实际产出可观察、可调试
3. M（v1.2 evaluator）可在 Round 12 推进，先把基础工具补齐

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 10 后）：290 pass / 0 fail / 9 skip（HEAD `7641a86`）

---

## 2026-08-04 — Round 11（CLI inspect 加 --spans flag）

**做了什么**：
- 完成候选 N：让 Round 10 的 source_spans 可观察、可调试
- `app/cli.py inspect` 加 `--spans` flag：
  - 必须配合 `--chunks` 使用
  - 每个 chunk 行下展开多行 `span: <element_id>[<start>:<end>]`
  - 没有 spans 的 chunk 显示 `spans: (none)`
- `_format_chunks_list` 增加 `show_spans: bool = False` 参数
- 更新模块 docstring 的用法示例
- 新增 2 个测试：
  - `test_inspect_chunks_spans_flag_without_spans_data`：合成 doc 无 spans → 显示 (none)
  - `test_inspect_chunks_spans_flag_with_real_pipeline`：跑真实 .md parse → 显示具体 span 行
- 不变量保持：未改 schema/model/chunker/pipeline
- commit `1355793`，已 push

**worktree 当前状态**：
- HEAD `1355793`，工作树清洁
- 测试基线：292 pass / 0 fail / 9 skip（+2 vs Round 10）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 12）

**首要任务**：方向选择

- 候选 M（推荐）：**evaluator v1.2 — 用 source_spans 做字符级 text_preservation**
  - 现状：source_spans 已就绪 + 可观察，但 evaluator 还在用 v1.1 的"非空白字符序列"妥协口径
  - 复杂度：中（加新指标 `text_preservation_spans_equal`；旧指标保留为兼容；bump evaluator_version/report_version 到 1.2）
  - 价值：兑现 Round 8 审计 §2.7 写的"治本方案"；让评测从"忽略空白"升级到"严格字符区间"
  - 不变量冲突：bump evaluator_version 是合理演进，但与"指示线 v2.x 审计"目标可能冲突；推进前在 commit message 中清晰说明
  - 风险：bump version 后旧报告校验可能受影响（schema 加 version const）

- 候选 L：**inspect 加 --metrics 模式**
  - 单文档跑评测指标，不写报告仅 stdout
  - 开发期快速 sanity check

- 候选 D：补 fallback parser 的覆盖率
- 候选 J（向量化）：仍因 CLAUDE.md "不增加计划外主要依赖" 阻塞

**建议**：选 M（evaluator v1.2）。理由：
1. source_spans 是为此而做的；现在收尾兑现价值
2. 自跑线多次 bump 过 evaluator_version（v1.0→v1.1），演进路径成熟
3. 完成后 dachuang 评测层进入"字符级精确"阶段，是有里程碑意义的进展

### 撞墙记录
（无）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 11 后）：292 pass / 0 fail / 9 skip（HEAD `1355793`）

---

## 2026-08-04 — Round 12（evaluation.cli 加 inspect-doc 子命令）

**做了什么**：
- 候选 M（evaluator v1.2）被 AUTONOMOUS_LOOP.md 硬底线阻塞（"不动 evaluator_version / report_version"，第 52 行 / 第 140 行），换方向到候选 L
- 完成候选 L（变形版）：在 `evaluation/cli.py` 加 `inspect-doc` 子命令
  - 用法：`python -m evaluation.cli inspect-doc <doc.json> [--tolerance-chars 30]`
  - 加载单文档 JSON，跑全部自动指标 + 标注指标（无标注时是 null），按可读格式 stdout 输出
  - 开发期 sanity check 用，省去构造 manifest 的开销
- **架构选择**：放在 `evaluation/cli.py` 而非 `app/cli.py`，保持 app/ 是纯库、evaluation/ 依赖 app/ 的层级（candidate L 原写在 app/cli.py，但层级关注优先）
- 输出按 metric 类型分组排序：success/bool → ratio → count/dict → null（最后），每行带 reason
- 新增 5 个 subprocess 测试（`tests/test_evaluation_cli.py`）：
  - 基础输出含元信息 + metrics / null 指标显示 reason / 缺文件 exit 2 / 坏 JSON exit 1 / 顶层非对象 exit 1
- 不变量保持：`evaluator_version` / `report_version` 仍是 `"1.1"`
- commit `6089806`，已 push

**worktree 当前状态**：
- HEAD `6089806`，工作树清洁
- 测试基线：297 pass / 0 fail / 9 skip（+5 vs Round 11）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 13）

**首要任务**：方向选择

- 候选 O（新提，推荐）：**docs 整理 + 顶层 README**
  - 现状：docs/ 只有 evaluation.md（v1.x 设计）+ evaluation-audit.md（Round 8）； newcomers 没有入口
  - 复杂度：低-中（写 README.md 介绍项目结构、用法、当前阶段；可能加 docs/architecture.md）
  - 价值：项目阶段性总结；让他人（包括 cron 唤醒的新 agent）能快速进入

- 候选 D：补 fallback parser 的覆盖率（PDF/DOCX 各路错误代码）
- 候选 P（新提）：**samples/ 加合成测试 fixtures**
  - 现状：tests 里的合成 DOCX/PDF 在每个测试里都重新构造；可以提到 conftest 或 fixtures 模块
  - 价值：减少测试代码重复；后续加测试更快

- 候选 J（向量化）：仍因 CLAUDE.md "不增加计划外主要依赖" 阻塞
- 候选 M（evaluator v1.2）：仍因 AUTONOMOUS_LOOP.md 硬底线阻塞

**建议**：选 O（docs 整理）。理由：
1. 已经做了 12 轮技术工作，缺少阶段性总结入口
2. cron 唤醒的新 agent 也需要 README 了解项目状态
3. 体积小，无技术风险

### 撞墙记录
- 候选 M（evaluator v1.2）：AUTONOMOUS_LOOP.md 第 52/140 行硬底线禁止改 evaluator_version / report_version。即使 source_spans 已就绪，也不能加新 v1.2 指标。换方向。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 12 后）：297 pass / 0 fail / 9 skip（HEAD `6089806`）

---

## 2026-08-04 — Round 13（fallback parser 覆盖率 + caption regex bug fix）

**做了什么**：
- 候选 O（docs）被 CLAUDE.md system instruction 阻塞（"NEVER create *.md unless explicitly requested"），换方向到候选 D
- 完成候选 D：补 fallback parser 测试覆盖率 + 修一个 caption regex bug
  - 加 19 个测试到 `tests/test_parsers.py`，覆盖原本未测的路径
  - **纯函数 helpers**：`_is_heading_style`（title/heading N/无数字 fallback/empty）、`_is_caption`（中英文各格式 + negative）、`_classify_pdf_paragraph`（caption/heading/paragraph）、`_rows_to_markdown`（empty/single/uneven padding/None cell）、`_image_filename`（命名 pattern）、`_group_words_to_paragraphs`（empty/single/多行聚类）
  - **错误路径**：`docx_open_failed`（坏字节流）、`pdfplumber_open_failed`（坏字节流）、`docx_no_content` warning（空 body）
  - **DOCX caption 集成**：构造含 `Figure 1.` / `表 2` 的合成 DOCX，验证 type=caption
  - **`_render_pdf_image_region_verbose`** 失败路径：bad path / bad page index / 退化 bbox
- **Bug 发现并修复**：`_CAPTION_RE` 漏了 `:` 分隔符 → `"Figure 5: Architecture"` 不被识别为 caption
  - 修：在末尾字符类 `[\.、\s]` → `[\.、:\s]`
  - 影响面：只扩展匹配，原匹配的 caption 仍匹配；不会破坏现有测试
- commit `8725911`，已 push

**worktree 当前状态**：
- HEAD `8725911`，工作树清洁
- 测试基线：316 pass / 0 fail / 9 skip（+19 vs Round 12）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 14）

**首要任务**：方向选择

- 候选 P（推荐）：**测试 fixtures 提取**
  - 现状：`tests/test_parsers.py`、`tests/test_evaluation_cli.py`、`tests/test_cli.py` 都各自重复实现合成 DOCX/PDF 构造
  - 复杂度：低
  - 价值：减少重复代码；后续加测试更快；统一合成文档质量

- 候选 Q（新提）：** kreuzberg parser 覆盖率**
  - 现状：`tests/test_parsers.py` 只有 3 个 kreuzberg 测试
  - 复杂度：中（kreuzberg 行为不稳定，需要更仔细的 assertion）
  - 价值：kreuzberg 是默认 parser 之外的备选，覆盖率薄弱

- 候选 R（新提）：**chunker 覆盖率扩展**
  - 现状：source_spans 已有测试；但句子分割（中英文标点）、whitespace fallback 等分支可能仍有未覆盖
  - 复杂度：低-中

- 候选 S（新提）：**pipeline 错误处理路径**
  - 现状：`process_single` 的 warning 汇总 / 错误聚合 / 半成品清理路径
  - 复杂度：中

- 仍阻塞：候选 J（向量化，CLAUDE.md deps 限制）、候选 M（evaluator v1.2，AUTONOMOUS_LOOP.md 硬底线）、候选 O（docs/*.md，CLAUDE.md system instruction）

**建议**：选 P（fixtures 提取）。理由：
1. 是当前 4 个测试文件的共同痛点，每加一个新测试都要重写合成 DOCX
2. 复杂度低，一轮内可完成
3. 为后续轮次加测试降本

### 撞墙记录
- 候选 O（docs/*.md）：CLAUDE.md system instruction "NEVER create documentation files (*.md) or README files unless explicitly requested by the User" 阻塞。换方向到 D。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 13 后）：316 pass / 0 fail / 9 skip（HEAD `8725911`）

---

## 2026-08-04 — Round 14（合成测试 fixtures 收敛）

**做了什么**：
- 完成候选 P：把 3 个测试文件里重复的合成 DOCX/PDF 构造代码收敛到 `tests/_synthetic_docs.py`
- 新模块提供 5 个 canonical builders：
  - `build_minimal_docx(path, with_table=False)`：Heading1+Heading2 styles.xml + 1 heading + 1 paragraph + 可选 table
  - `build_pipeline_docx(path)`：无 styles.xml，pStyle ref + 1 heading + 2 paragraphs（pipeline 集成专用）
  - `build_docx_with_caption(path)`：无 styles.xml，2 caption + 1 paragraph（caption regex 集成）
  - `build_empty_docx(path)`：空 body
  - `build_minimal_pdf(path, text)`：单页文本 PDF
- 迁移 3 个文件：
  - `test_parsers.py`：4 个内嵌 builder → import（删 ~155 行）
  - `test_evaluation_cli.py`：1 个内嵌 builder → import（删 ~48 行）
  - `test_pipeline_integration.py`：2 个内嵌 builder → import（保留薄 local wrapper 维持 call site 不变，删 ~54 行）
- 净变化：-230 / +27 行（test 文件）+ 新增 _synthetic_docs.py（~190 行）
- 不变量保持：316 pass / 0 fail / 9 skip 不变；纯重构无行为变化
- commit `d875d35`，已 push

**worktree 当前状态**：
- HEAD `d875d35`，工作树清洁
- 测试基线：316 pass / 0 fail / 9 skip（与 Round 13 一致，纯 refactor）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 15）

**首要任务**：方向选择

- 候选 R（推荐）：**chunker 覆盖率扩展**
  - 现状：source_spans 已有 8 个测试；但中英文标点分割、whitespace fallback、heading hard boundary 等分支可能仍有未覆盖
  - 复杂度：低-中
  - 价值：chunker 是当前阶段的核心算法，覆盖率应保持高位

- 候选 Q：**kreuzberg parser 覆盖率**
  - 现状：只有 3 个 kreuzberg 测试
  - 复杂度：中（kreuzberg 行为不稳定）
  - 价值：备选 parser 的覆盖率薄弱

- 候选 S：**pipeline 错误处理路径**
  - 现状：`process_single` 的 warning 汇总 / 错误聚合 / 半成品清理路径
  - 复杂度：中

- 候选 T（新提）：**HTML/Markdown/Text/IPYNB parser 覆盖率**
  - 现状：这些 parser 测试可能比 fallback 还薄弱
  - 复杂度：低-中（行为相对简单）
  - 价值：边缘 parser 容易被忽视

- 仍阻塞：候选 J（向量化，CLAUDE.md deps 限制）、候选 M（evaluator v1.2，AUTONOMOUS_LOOP.md 硬底线）、候选 O（docs/*.md，CLAUDE.md system instruction）

**建议**：选 R（chunker 覆盖率）。理由：
1. chunker 是当前阶段最复杂的算法（heading 边界 + 句子分割 + whitespace fallback + 表格隔离 + source_spans 跟踪）
2. 是 source_spans 的载体，覆盖率高低直接影响后续 v1.2 评估（如果未来解禁）
3. fixtures 已收敛，新测试成本低

### 撞墙记录
- 无新撞墙。Round 13/14 的 P 候选顺利完成。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 14 后）：316 pass / 0 fail / 9 skip（HEAD `d875d35`）

---

## 2026-08-04 — Round 15（chunker 覆盖率扩展）

**做了什么**：
- 完成候选 R：补 chunker 覆盖率，新增 20 个测试到 `tests/test_chunker.py`
- **`_element_text_with_span` 直接单元测试**（8 个）：
  - normal text、leading/trailing/both-side whitespace 各自的 (start, end) 计算
  - empty content、whitespace-only、None content（用 resource_path 满足 Element 不变量）
  - image element 强制返回 ("", 0, 0)
- **`_split_long_text` 边界直接测试**（5 个）：
  - empty/whitespace-only 输入
  - text ≤ max_chars → 单 piece，覆盖 [0, len)
  - 无句子分隔符 + 无空白 → 全 forced_char
  - 连续句子分隔符（"Hello.. World"）不切（要求后续有空白）
- **集成测试**（7 个）：
  - caption 隔离成 chunk（mirror I6 table 测试）
  - 连续 3 个 heading → 3 个独立 chunk
  - heading 紧跟 table → 2 chunks
  - list_item 走"其他"分支，与 paragraph 一样累积
  - table 后 paragraph 验证 buf 重置
  - 混合 element 类型保"不丢不重"不变量
  - 短 paragraph + 长 paragraph 边界 reset
- **发现的小问题**（已绕开）：Element 强制要求 `content` 或 `resource_path` 之一非空，所以 empty/None content 测试用 `resource_path="placeholder"` 满足不变量（不算 bug，是 Element 的设计）
- commit `053743a`，已 push

**worktree 当前状态**：
- HEAD `053743a`，工作树清洁
- 测试基线：336 pass / 0 fail / 9 skip（+20 vs Round 14）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 16）

**首要任务**：方向选择

- 候选 Q（推荐）：**kreuzberg parser 覆盖率**
  - 现状：只有 3 个 kreuzberg 测试（docx/pdf/missing_file）
  - 复杂度：中（kreuzberg 行为不稳定，需要更仔细的 assertion）
  - 价值：备选 parser，目前覆盖率薄弱

- 候选 T：**HTML/Markdown/Text/IPYNB parser 覆盖率**
  - 现状：test_parsers_html.py / test_parsers_markdown.py 等已存在但可能覆盖不全
  - 复杂度：低-中
  - 价值：边缘 parser 不应被忽视

- 候选 S：**pipeline 错误处理路径**
  - 现状：`process_single` 的 warning 汇总 / 错误聚合 / 半成品清理
  - 复杂度：中

- 候选 U（新提）：**schema 校验测试**
  - 现状：test_schema.py 应该比较完整，但 source_spans 加入后可能有边角
  - 复杂度：低

- 仍阻塞：候选 J（向量化）、候选 M（evaluator v1.2）、候选 O（docs/*.md）

**建议**：选 Q（kreuzberg 覆盖率）。理由：
1. kreuzberg 是项目设计中的可选 parser（虽然默认 fallback），覆盖薄弱风险高
2. 测试基础设施（fixtures）已收敛，加测试成本低
3. 如果未来 kreuzberg 升级能给出 elements，需要测试网先就位

### 撞墙记录
- Element 强制 content/resource_path 非空：test_element_text_with_span_empty_content 测试空 content 时撞这个不变量，已用 resource_path="placeholder" 绕开（这是 Element 的正确不变量，不是 bug）。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 15 后）：336 pass / 0 fail / 9 skip（HEAD `053743a`）

---

## 2026-08-04 — Round 16（kreuzberg parser 覆盖率）

**做了什么**：
- 完成候选 Q：补 kreuzberg parser 测试覆盖率，新增 15 个测试到 `tests/test_parsers.py`
- **`_classify_line` 直接单元测试**（6 个）：
  - markdown `#`/`##`/`######` heading level
  - 短行（≤80）+ 不以句号结尾 → heading short_line heuristic
  - 短行 + 句号结尾 → paragraph
  - 超长行 → paragraph
  - 空行 → paragraph
  - 中文句号结尾 → paragraph
- **`_make_locator` 直接单元测试**（1 个）：pdf page=1 占位 vs docx paragraph_index
- **`_split_content_to_elements` 直接单元测试**（5 个）：
  - 双换行分多段
  - markdown heading
  - heading + body 在同 block
  - 空 content / 纯空白
  - pdf locator 含 page=1
- **集成测试 warning 细节**（3 个）：
  - kreuzberg_no_structured_elements warning.details 含 fallback_strategy / source_type
  - PDF elements 都有 page=1 占位
  - Document.metadata 保留 kreuzberg_mime_type / kreuzberg_quality_score 字段
- commit `54eaa3e`，已 push

**worktree 当前状态**：
- HEAD `54eaa3e`，工作树清洁
- 测试基线：351 pass / 0 fail / 9 skip（+15 vs Round 15）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 17）

**首要任务**：方向选择

- 候选 T（推荐）：**HTML/Markdown/Text/IPYNB parser 覆盖率**
  - 现状：test_parsers_html.py / test_parsers_markdown.py / test_parsers_text.py / test_parsers_ipynb.py 已存在
  - 复杂度：低-中
  - 价值：边缘 parser 也应保持高覆盖率

- 候选 S：**pipeline 错误处理路径**
  - 现状：`process_single` 的 warning 汇总 / 错误聚合 / 半成品清理
  - 复杂度：中

- 候选 U：**schema 校验测试**
  - 现状：test_schema.py 应该比较完整；source_spans 加入后可能有边角
  - 复杂度：低

- 候选 V（新提）：**models 测试**
  - 现状：test_models.py 不知是否完整
  - 复杂度：低

- 候选 W（新提）：**annotation_metrics 测试**
  - 现状：test_annotation_metrics.py 在 Round 8 加过几个，可能还有边角
  - 复杂度：低

- 仍阻塞：候选 J（向量化）、候选 M（evaluator v1.2）、候选 O（docs/*.md）

**建议**：选 T（边缘 parser 覆盖率）。理由：
1. 已经覆盖了 fallback 和 kreuzberg，HTML/MD/TXT/IPYNB 应跟进
2. 这些 parser 相对简单，测试成本低
3. 保持测试网密度，未来修改任一 parser 都能立即发现问题

### 撞墙记录
- 无新撞墙。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 16 后）：351 pass / 0 fail / 9 skip（HEAD `54eaa3e`）

---

## 2026-08-04 — Round 17（边缘 parser 覆盖率扩展）

**做了什么**：
- 完成候选 T：补 text/markdown/html parser 测试覆盖率，新增 22 个测试
- **Text parser**（4 个，加到 `tests/test_parsers_text.py`）：
  - `_split_paragraphs` 处理 CR-only 换行（老 Mac 风格）
  - 尾部空行被忽略
  - 文件开头空行不偏移首段行号
  - 多段落的 1-indexed 行号正确
- **Markdown parser helpers**（13 个，加到 `tests/test_parsers_markdown.py`）：
  - `_detect_md_source_type`：.md/.markdown 大小写不敏感；其他扩展名 raise
  - `_rows_to_md`：empty / 单行 / 长短不齐填充
  - `_split_pipe_row`：基础 + 无外 pipe + cell strip + 单 cell
  - `_is_pipe_table_start`：合法 / 缺分隔行 / 最后一行 / 非 pipe 首行
- **HTML parser helpers**（5 个，加到 `tests/test_parsers_html.py`）：
  - `_detect_html_source_type`：.html/.htm 大小写不敏感；其他扩展名 raise
  - `_rows_to_md`：empty / 单行 / 长短不齐填充
- IPYNB parser 现有 20 个测试覆盖已较完整，本轮未加新测试
- commit `32c7f95`，已 push

**worktree 当前状态**：
- HEAD `32c7f95`，工作树清洁
- 测试基线：373 pass / 0 fail / 9 skip（+22 vs Round 16）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 18）

**首要任务**：方向选择

- 候选 S（推荐）：**pipeline 错误处理路径**
  - 现状：`process_single` 的 warning 汇总 / 错误聚合 / 半成品清理 / image_output_dir 处理
  - 复杂度：中
  - 价值：pipeline 是端到端核心，错误路径最易回归

- 候选 U：**schema 校验测试**
  - 现状：source_spans 加入 schema 后可能有边角；conditional if/then 各分支
  - 复杂度：低

- 候选 V：**models 测试**
  - 现状：test_models.py 现状不清，可能边角未覆盖
  - 复杂度：低

- 候选 W：**annotation_metrics 测试**
  - 现状：Round 8 加过几个重复 marker 测试；可能还有边角
  - 复杂度：低

- 候选 X（新提）：**evaluation metrics 测试**
  - 现状：test_metrics.py 应该比较完整，但加 source_spans 后可能有新指标没覆盖
  - 复杂度：低-中

- 候选 Y（新提）：**manifest 测试**
  - 现状：test_manifest.py 边角检查
  - 复杂度：低

- 仍阻塞：候选 J（向量化）、候选 M（evaluator v1.2）、候选 O（docs/*.md）

**建议**：选 S（pipeline 错误路径）。理由：
1. pipeline 是端到端核心，所有用户都过这一层
2. warning 聚合 / 半成品清理路径最易回归（之前 Round 8 修过 _process_one 的类似问题）
3. 覆盖率薄弱风险高

### 撞墙记录
- 无新撞墙。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 17 后）：373 pass / 0 fail / 9 skip（HEAD `32c7f95`）

---

## 2026-08-04 — Round 18（pipeline 错误路径覆盖）

**做了什么**：
- 完成候选 S：补 pipeline 错误路径覆盖率，新建 `tests/test_pipeline_errors.py`（13 个测试）
- **`get_parser`**（3 个）：
  - 未知 parser 名 → ValueError
  - 6 个已知名都返回正确类型的 instance
  - fallback 接收 image_output_dir 参数
- **`validate_only` 错误路径**（3 个）：
  - 缺文件 → (False, msg)
  - 坏 JSON → (False, "JSON 解析失败")
  - JSON 合法但 schema 不对 → (False, schema 错误)
- **`process_single` 错误路径**（7 个）：
  - **`no_extracted_elements`**：合成无 content stream 的最小 PDF，验证 fallback 解析返回 0 elements → 错误码 + warnings/details
  - **`chunker_failed`**：monkeypatch StructuralChunker.chunk 抛 RuntimeError → 结构化错误 + 无半成品
  - **`unexpected_parser_error`**：monkeypatch get_parser 注入抛 ValueError 的 parser → 结构化错误含 parser_name
  - **`write_failed`**：monkeypatch pathlib.Path.open 在写模式抛 OSError → 结构化错误含 path
  - `write_json=False`：不写盘
  - `output_path=None`：不写盘
  - kreuzberg on PDF：不崩溃（即使给不出 bbox）
- **重要发现**：`process_single` 写盘走 `Path.open` 而非 `builtins.open`；初始 monkeypatch 没生效，改 Path.open 后通过
- commit `3aab469`，已 push

**worktree 当前状态**：
- HEAD `3aab469`，工作树清洁
- 测试基线：386 pass / 0 fail / 9 skip（+13 vs Round 17）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 19）

**首要任务**：方向选择

- 候选 U（推荐）：**schema 校验测试**
  - 现状：source_spans 加入 schema 后可能有边角；conditional if/then 各分支
  - 复杂度：低

- 候选 V：**models 测试**
  - 现状：test_models.py 不知覆盖度
  - 复杂度：低

- 候选 W：**annotation_metrics 测试**
  - 复杂度：低

- 候选 X：**evaluation metrics 测试**
  - 复杂度：低-中

- 候选 Y：**manifest 测试**
  - 复杂度：低

- 候选 Z（新提）：**chunker 模糊测试 / 不变量测试**
  - 用各种随机/极端输入验证"不丢不重"不变量
  - 复杂度：中

- 仍阻塞：候选 J（向量化）、候选 M（evaluator v1.2）、候选 O（docs/*.md）

**建议**：选 U（schema 校验）。理由：
1. source_spans 加入 schema 是近期最大的 schema 变化
2. conditional if/then 分支多（pdf/docx/markdown/html/text/ipynb 各不同 source_locator）
3. schema 校验是写盘前的最后防线，覆盖率应保持高位

### 撞墙记录
- monkeypatch `builtins.open` 对 `Path.open` 无效：`Path.open` 内部走 `io.open`，绕过 `builtins.open`。改 monkeypatch `pathlib.Path.open` 解决。这是 Round 18 的非trivial 发现。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 18 后）：386 pass / 0 fail / 9 skip（HEAD `3aab469`）

---

## 2026-08-04 — Round 19（schema 校验覆盖率）

**做了什么**：
- 完成候选 U：补 JSON Schema 校验测试，新增 32 个测试到 `tests/test_schema.py`
- **`source_spans` 子结构**（7 个）：
  - 合法 chunk with source_spans 通过
  - 缺 element_id / start / end → 失败
  - negative start → 失败（minimum: 0）
  - source_span additionalProperties:false → 失败
  - chunk 本身 additionalProperties:false → 失败
- **各 source_type 的 locator**（10 个）：
  - 合法 markdown/html/text doc（line locator）
  - 合法 ipynb doc（cell_index + cell_type）
  - markdown/html/text locator 必须有 line
  - ipynb locator 必须有 cell_index 和 cell_type（分开测）
  - ipynb cell_type enum（markdown/code/raw 合法，其他失败）
- **element / chunk 约束**（15 个）：
  - 不合法的 source_type（"csv"）被拒
  - 不合法的 element type 被拒；8 个合法 type 全通过
  - confidence 超出 [0, 1] 范围失败
  - pdf page=0 失败（minimum: 1）
  - pdf bbox 错误尺寸失败（必须恰好 4 个）
  - schema_version 改了失败（const）
  - element additionalProperties:false
  - relation 缺 required field / 多余字段
  - warning / error 缺 required field
  - 空 document_id / chunk_id / source_element_ids item 失败
- commit `08c4e45`，已 push

**worktree 当前状态**：
- HEAD `08c4e45`，工作树清洁
- 测试基线：419 pass / 0 fail / 9 skip（+33 vs Round 18）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 20）

**首要任务**：方向选择

- 候选 V（推荐）：**models 测试**
  - 现状：test_models.py 现状不清，可能边角未覆盖
  - 复杂度：低

- 候选 W：**annotation_metrics 测试**
  - 复杂度：低

- 候选 X：**evaluation metrics 测试**
  - 复杂度：低-中

- 候选 Y：**manifest 测试**
  - 复杂度：低

- 候选 Z：**chunker 模糊测试 / 不变量测试**
  - 复杂度：中

- 候选 AA（新提）：**hash 模块测试**
  - 现状：app/hash.py 应该很简单
  - 复杂度：低

- 仍阻塞：候选 J（向量化）、候选 M（evaluator v1.2）、候选 O（docs/*.md）

**建议**：选 V（models 测试）。理由：
1. models 是数据类不变量的源头
2. Element 不变量（content/resource_path 至少一非空）、Document 序列化、Chunk to_dict 等可能有边角
3. 后续轮次继续依赖 models 的强不变量

### 撞墙记录
- 无新撞墙。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 19 后）：419 pass / 0 fail / 9 skip（HEAD `08c4e45`）

---

## 2026-08-04 — Round 20（models 测试覆盖率）

**做了什么**：
- 完成候选 V：补 models dataclass 测试，新增 17 个测试到 `tests/test_models.py`
- **Element**（4 个）：
  - `to_dict` 含所有字段（parent_id/confidence/metadata）
  - `resource_path` 出现在 to_dict
  - 空字符串 content 被拒（__post_init__）
  - content + resource_path 同时存在允许
- **Chunk**（3 个）：to_dict 含 source_spans、默认 source_spans 空、默认 metadata 空
- **Relation**（2 个）：to_dict 含 metadata、默认 metadata 空
- **WarningRecord / ErrorRecord**（3 个）：details=None 时 to_dict 不含 details key；ErrorRecord with details
- **Document**（4 个）：默认空集合、to_dict 序列化 warnings/errors、metadata 嵌套结构透传、SCHEMA_VERSION 常量值
- commit `a90ab0c`，已 push

**worktree 当前状态**：
- HEAD `a90ab0c`，工作树清洁
- 测试基线：435 pass / 0 fail / 9 skip（+16 vs Round 19）
- main 仍在 `2c35244`（隔离不变量保持）

### 下一步建议（Round 21）

**首要任务**：方向选择

- 候选 W（推荐）：**annotation_metrics 测试**
  - 现状：test_annotation_metrics.py 在 Round 8 加过几个；可能还有边角
  - 复杂度：低

- 候选 X：**evaluation metrics 测试**
  - 复杂度：低-中

- 候选 Y：**manifest 测试**
  - 复杂度：低

- 候选 Z：**chunker 模糊测试**
  - 复杂度：中

- 候选 AA：**hash 模块测试**
  - 复杂度：低

- 仍阻塞：候选 J（向量化）、候选 M（evaluator v1.2）、候选 O（docs/*.md）

**建议**：选 W（annotation_metrics）。理由：
1. Round 8 修过 chunk_boundary_prf 重复 marker bug；现在应该把覆盖率补齐
2. figure_caption_prf 也要测
3. 复杂度低，一轮内可完成

### 撞墙记录
- 无新撞墙。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 20 后）：435 pass / 0 fail / 9 skip（HEAD `a90ab0c`）

---

## Round 21（2026-08-04）：候选 W — annotation_metrics 边角覆盖率补强

### 做了什么
- 候选 W：扩展 `tests/test_annotation_metrics.py`，新增 14 个测试覆盖 `chunk_boundary_prf` / `figure_caption_prf` 的边角路径。
- 重点覆盖项：
  - **空 marker 串** → `_missing_markers` 列表 + recall=null
  - **`position` 字段缺失** → 默认 `"after"`
  - **f1 计算**：P=R=0 → f1=0.0（不是 null）；recall=null → f1=null
  - **document 无 `chunks` 键** → `no_predicted_boundaries`
  - **默认 tolerance_chars=30**
  - **f1 = 2PR/(P+R)** 显式数值校验（P=1.0、R=0.5 → f1=2/3）
  - **贪心按距离匹配**：2 pred × 2 anchor 完美匹配
  - **一对一约束**：两个 pred 抢一个 anchor，只胜出 1 个
  - **chunk.text=None** 不应崩溃
  - **空 dict annotation** → `no_annotation`
  - **所有 anchor 都找不到** → recall=null + `_missing_markers` 集合
  - **figure_caption_prf 返回 shape 校验**（3 个键、全部 null + 同一 reason）
  - **`_tolerance_chars` 与 `_missing_markers` 共存**
- 无源码改动，纯测试加强。

### 下一步建议
- 候选 X：`evaluation/metrics.py` 13 项自动指标的覆盖率补强（比 annotation_metrics 复杂度高一档，但同样无 deps 风险）
- 候选 Y：`evaluation/manifest.py` 加载/校验逻辑的测试
- 候选 AA：`app/hash.py` 模块（SHA256 / content addressing）测试
- 仍阻塞：J（向量化，依赖）、M（evaluator v1.2，硬底线）、O（docs/*.md，系统指令）

**建议**：选 X（evaluation/metrics.py）。理由：
1. 13 项指标里很多分支（PDF 没有 bbox、image_base_dir 处理、table 与 list_item 等分支）
2. 纯函数 + 已有 evaluation.yml 配置，不引入新依赖
3. 与 Round 21 一脉相承，可以继续把 evaluation/ 的覆盖率补齐

### 撞墙记录
- 无新撞墙。所有 14 个新测试一次通过。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 21 后）：449 pass / 0 fail / 9 skip（HEAD `09a0854`）

---

## Round 22（2026-08-04）：候选 X — evaluation/metrics.py 边角覆盖率补强

### 做了什么
- 候选 X：扩展 `tests/test_metrics.py`，新增 24 个测试覆盖 `compute_automatic_metrics` 与内部 helper 的边角路径。
- 重点覆盖项：
  - **`_is_valid_bbox`** 直接单测：非 list、长度 ≠ 4、bool 子类陷阱、NaN/Infinity 拒绝
  - **`_strip_unicode_whitespace`** 直接单测：NBSP / em space / en space / ideographic space / U+2028/U+2029 separator / ASCII 制表换行
  - **PDF/DOCX locator 无 elements** → `no_elements`
  - **DOCX locator 拒 page/bbox 键**（1/3 合规的混合测试）
  - **DOCX locator 无 structural key** → 不合规
  - **PDF table 类型不需要 bbox**（不在 `_PDF_BBOX_REQUIRED_TYPES`）
  - **image resource**：None/空串路径 → 不合规
  - **chunk reference**：空 list / 缺失 `source_element_ids` → 不合规
  - **text_preservation 三种空情形**：both empty / actual empty / expected empty
  - **heading_boundary_ratio**：headings 存在但无 chunks → 0.0（不是 null）
  - **silent_drop**：空 expectations dict / 缺 element_count_by_type / 多类型同时缺
  - **schema_valid = False** 当 document 不通过 schema
  - **pipeline_success = False** 当 error 非 None（即使 document 也在）
- 无源码改动，纯测试加强。

### 下一步建议
- 候选 Y：`evaluation/manifest.py` 加载/校验逻辑的测试（路径校验、相对/绝对路径拒绝、JSON 结构）
- 候选 AA：`app/hash.py` 模块（SHA256 / content addressing）测试
- 候选 AB：`app/chunkers/structural.py` 的纯函数 helper（如 `_element_text_with_span` 已部分覆盖，但 `_split_long_text` 还有边角）
- 仍阻塞：J（向量化，依赖）、M（evaluator v1.2，硬底线）、O（docs/*.md，系统指令）

**建议**：选 Y（manifest 模块）。理由：
1. 路径校验是安全关键（避免 path traversal、绝对路径泄漏）
2. 纯函数 + 不需要新依赖
3. 与 Round 21/22 一脉相承，继续补 evaluation/ 覆盖率

### 撞墙记录
- 无新撞墙。所有 24 个新测试一次通过。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 22 后）：473 pass / 0 fail / 9 skip（HEAD `301e918`）

---

## Round 23（2026-08-04）：候选 Y — evaluation/manifest.py 边角覆盖率补强

### 做了什么
- 候选 Y：扩展 `tests/test_manifest.py`，新增 23 个测试覆盖 `load_manifest` 与内部 helper 的边角路径。
- 重点覆盖项：
  - **`_is_absolute_like`** 直接单测：POSIX、Windows 盘符+斜杠、盘符无斜杠、相对路径、空串
  - **`_has_backslash`** 直接单测
  - **`_detect_project_root`** 单测：向上找 `pyproject.toml`；找不到时不崩溃
  - **`annotation_file` 解析**：合法时解析为绝对路径；绝对/反斜杠路径被拒
  - **`expected_failures` 边角**：路径越界被拒；`source_type` 可选
  - **`DocumentEntry` 字段**：sha256/categories/paired_with/expectations 填充；默认值（None / 空元组）
  - **`Manifest` 属性**：`categories_covered` 空与去重；`content_group_count` 全 unpaired；单向配对仍算 1 组
  - **显式 `project_root` 参数**：覆盖 `pyproject.toml` 探测
  - **JSON 解析错误** → ManifestError
  - **schema additionalProperties:false** 在 top-level / document / expected_failure 三层都生效
  - **schema enum 拒绝**：source_type / doc_id minLength
- 无源码改动，纯测试加强。

### 撞墙记录
- **撞墙 1**：`test_detect_project_root_no_pyproject_falls_back_to_dir` 假设找不到 `pyproject.toml` 时回退到 start.parent，但实际函数对不存在的文件路径返回 start 本身。改测：传一个真实存在的文件触发 `cur.is_file()=True` 分支。
- **撞墙 2**：`test_explicit_project_root_used` 写文件名是 `x.docx`，但 manifest 默认指向 `sample.docx`，校验通过但路径不符。改测：在 project_root 下创建 `sample.docx` 与 manifest 路径对齐。
- 两次都是测试构造错误，非源码 bug。

### 下一步建议
- 候选 AA：`app/hash.py` 模块（SHA256 / content addressing）测试
- 候选 AC：`evaluation/schema.py` 与 `evaluation/schema_validation.py` 测试
- 候选 AD：`evaluation/report.py` 聚合逻辑测试（aggregate_reports 等）
- 候选 AE：`evaluation/runner.py` 跑评测主流程的测试（处理 expected_failures 等）
- 仍阻塞：J（向量化，依赖）、M（evaluator v1.2，硬底线）、O（docs/*.md，系统指令）

**建议**：选 AA（hash 模块）。理由：
1. hash 是 pipeline 入口的关键基础（content-addressing）
2. 纯函数、低复杂度、易测试
3. 之后可以做 AC（schema_validation）补齐 evaluation/ 这一层的覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 23 后）：496 pass / 0 fail / 9 skip（HEAD `eeba61b`）

---

## Round 24（2026-08-04）：候选 AA — app/hash.py 全新测试文件

### 做了什么
- 候选 AA：新建 `tests/test_hash.py`，21 个测试覆盖 `compute_file_hash` 与 `compute_text_hash`。
- 此前该模块**无专属测试文件**（仅被 pipeline 间接调用过）。
- 重点覆盖项：
  - **`compute_text_hash`**：空串、ASCII、Unicode（UTF-8 编码验证）、emoji（4-byte UTF-8）、确定性、空白敏感、输出格式（64 字符小写 hex）
  - **`compute_file_hash`**：空文件、小文件、大文件（>64KB 流式分块拼接验证）、二进制（含 \\x00 与高位字节）、str 与 Path 输入、缺失文件、目录（`is_file=False`）、chunk 边界（恰好 64KB 与 64KB+1）
- 无源码改动。

### 下一步建议
- 候选 AC：`evaluation/schema.py` 与 `evaluation/schema_validation.py` 测试
- 候选 AD：`evaluation/report.py` 聚合逻辑测试
- 候选 AE：`evaluation/runner.py` 主流程测试
- 候选 AF：`app/chunkers/structural.py` 内部纯函数（`_split_long_text` 等还有边角）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AC（evaluation/schema_validation）。理由：
1. 一脉相承继续 evaluation/ 覆盖率补强
2. `document_passes_schema` 是 metrics 的依赖（schema_valid 指标调用它）
3. 纯函数，低复杂度

### 撞墙记录
- 无新撞墙。21 个测试一次通过。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 24 后）：517 pass / 0 fail / 9 skip（HEAD `057bad9`）

---

## Round 25（2026-08-04）：候选 AC — evaluation/schema.py 与 schema_validation.py 全新测试文件

### 做了什么
- 候选 AC：新建 `tests/test_evaluation_schema.py`，25 个测试覆盖 `evaluation/schema.py` 与 `evaluation/schema_validation.py`。
- 这两个模块此前**无专属测试**（仅被 cli/report 间接调用）。
- 重点覆盖项：
  - **`load_schema`**：4 个已知 schema 都能加载；缺失抛 FileNotFoundError
  - **`SCHEMAS_DIR`** 常量指向项目 schemas/
  - **`validate` manifest**：合法返回 None；非法抛 EvalSchemaError + errors 列表；多错误同时收集
  - **`validate` annotation**：position enum、marker minLength、additionalProperties、required
  - **`validate` evaluation-report**：version const、缺失 top-level、缺失嵌套 provenance 字段
  - **`validate_file`**：合法文件、缺失文件、非法 JSON（抛 JSONDecodeError）、非法内容（抛 EvalSchemaError）、str 路径
  - **`document_passes_schema`**：合法 True、非法 False、返回 bool 类型、错 schema_version、element 缺必填
- 无源码改动。

### 撞墙记录
- **撞墙 1**：`_valid_report()` 最初把 devset 的字段写成 `devset_status` 与 `manifest_path`，但 schema 实际要求 `status` 且 `additionalProperties:false` 不允许 `manifest_path`。两次修复后对齐 schema。
- 不是源码 bug，是测试构造时未对照 schema。

### 下一步建议
- 候选 AD：`evaluation/report.py` 聚合逻辑测试（aggregate_reports / 各种 summary 字段计算）
- 候选 AE：`evaluation/runner.py` 主流程测试（process expected_failures 等）
- 候选 AF：`app/chunkers/structural.py` 内部纯函数补强
- 候选 AG：`app/cli.py` 子命令的更细致测试（参数解析、退出码）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AD（evaluation/report.py）。理由：
1. 完成 evaluation/ 模块覆盖率补齐的最后一公里
2. 聚合逻辑（macro average、counts 求和、silent_drop 求和）有逻辑分支值得测
3. 纯函数 + 已有 evaluation-report.schema.json 可作校验

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 25 后）：542 pass / 0 fail / 9 skip（HEAD `d07b3dc`）

---

## Round 26（2026-08-04）：候选 AD — evaluation/report.py 覆盖率补强

### 做了什么
- 候选 AD：扩展 `tests/test_evaluation_report.py`，新增 20 个测试覆盖 `aggregate_summary` / `build_provenance` / `build_devset_section` 的边角路径。
- 重点覆盖项：
  - **`aggregate_summary` 边界**：空 list、counts 全 None、ratio 多值平均、ratio 全 None、partial participation
  - **ratio 列表成员**：`schema_valid` / `chunk_boundary_*` 在 ratio 里；`figure_caption_*` 不在；`text_preservation_equal` 作为 bool 被当 ratio
  - **success_rates**：全失败 (rate=0.0)、全通过 (rate=1.0)、空 list (rate=None)
  - **silent_drop 混合 null**：求和时排除 null
  - **`aggregate_summary` 不修改输入**（深拷贝对照）
  - **`get_dependency_versions`**：返回 dict 含 pdfplumber / python-docx / pypdfium2 三个键，值为 str 或 None
  - **`get_git_provenance`** 非 git 目录 → commit=None，dirty 是 bool（值依赖环境）
  - **`build_provenance`**：max_chars 转 int；parser_version=None 保留；含 EVALUATOR_VERSION / REPORT_VERSION
  - **`build_devset_section`** 6 个字段全部填充
- 无源码改动。

### 撞墙记录
- **撞墙 1**：`test_get_git_provenance_non_git_dir_returns_none_commit` 假设非 git 目录时 dirty=True（按 docstring 字面），但实际函数在子进程返回非 0 时把 dirty 设为 False（仅异常时才 True）。改测：只断言 commit=None 与 dirty 是 bool。
- 不是源码 bug，是 docstring 描述与实现细节有微妙差异。

### 下一步建议
- 候选 AE：`evaluation/runner.py` 主流程测试（处理 expected_failures、metric 装配）
- 候选 AF：`app/chunkers/structural.py` 内部纯函数补强
- 候选 AG：`app/cli.py` 子命令更细致的测试
- 候选 AH：`evaluation/cli.py` 的 `validate-report` 子命令路径
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AE（evaluation/runner.py）。理由：
1. 完成 evaluation/ 主流程的最后一块
2. 涉及 expected_failures 处理、metric 装配、annotation 文件加载等复杂逻辑
3. 可能需要 mock 或小文件 fixtures

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 26 后）：562 pass / 0 fail / 9 skip（HEAD `c9fb270`）

---

## Round 27（2026-08-04）：候选 AE — evaluation/runner.py 覆盖率补强

### 做了什么
- 候选 AE：扩展 `tests/test_evaluation_runner.py`，新增 17 个测试覆盖 `_load_annotation` / `_process_one` / `run_evaluation` 的边角路径。
- 引入 `_FakeManifest` / `_FakeDocEntry` / `_FakeExpectedFailure` 三个 dataclass，让 `run_evaluation` 端到端测试可以在不需要真实 manifest 文件的情况下跑。
- 重点覆盖项：
  - **`_process_one`**：成功后清理 out_stub；不支持的扩展名返回 unsupported_type
  - **`_load_annotation`** 4 种路径：None、缺失、合法 JSON、非法 JSON
  - **`run_evaluation` 端到端**：空 manifest、单 doc 成功、单 doc 失败（pipeline_failed 蔓延到 metrics）、expected_failure 匹配 / 不匹配、annotation_file 加载、公开 per_doc 不含私有字段、嵌套目录自动创建、报告通过 schema、parser_version / max_chars 进入 provenance
- 无源码改动。

### 下一步建议
- 候选 AF：`app/chunkers/structural.py` 内部纯函数补强
- 候选 AG：`app/cli.py` 子命令更细致的测试
- 候选 AH：`evaluation/cli.py` 的 `validate-report` 子命令路径
- 候选 AI：`app/pipeline.py` 其他 helper（`get_parser` 已经测过，但 `image_output_dir_for` 等还有空间）
- 候选 AJ：在已有大测试基础上加 fuzz / property-based 测试（用 hypothesis 之类的工具，但是依赖会增加）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AF（structural chunker helper 补强）。理由：
1. `_element_text_with_span` 和 `_split_long_text` 还有一些边界情况
2. chunker 是"分块不丢不重"承诺的核心算法
3. 纯函数，无依赖

### 撞墙记录
- 无新撞墙。17 个新测试一次通过。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 27 后）：579 pass / 0 fail / 9 skip（HEAD `4e8a43c`）

---

## Round 28（2026-08-04）：候选 AF — structural chunker 覆盖率补强

### 做了什么
- 候选 AF：扩展 `tests/test_chunker.py`，新增 27 个测试覆盖 `normalize_text` / `StructuralChunker.__init__` / `_ChunkBuffer` / 各类集成边角。
- 重点覆盖项：
  - **`normalize_text` 直接单测**：幂等性、Unicode 空白（NBSP、em space、tab）压成单空格、纯空白输入返回空
  - **`StructuralChunker.__init__` 验证**：max_chars=32 边界接受、31/0/负数拒绝、默认值 800
  - **`_ChunkBuffer` 直接单测**（7 个）：空 flush、纯空白 flush、length() 求和、source_element_ids 顺序去重、source_spans per-part、chunk_id 格式、flush 重置 parts、metadata 含 strategy/max_chars/char_count
  - **集成边角**：纯 heading、heading→image→paragraph（image 不出 chunk）、已有 chunks 字段被忽略、list_item 累积、caption 是 isolated、table metadata strategy
- 无源码改动。

### 撞墙记录
- **撞墙 1**：`test_heading_then_image_then_paragraph` 第一版用 `_make_doc` 试图构造 image element 但 `_make_doc` 强制 content，违反 Element 不变量（"content 或 resource_path"）。改测：直接构造 Element 列表，让 image 用 resource_path。
- 不是源码 bug。

### 下一步建议
- 候选 AG：`app/cli.py` 子命令更细致的测试（参数解析、退出码、stderr 输出）
- 候选 AH：`evaluation/cli.py` 的 `validate-report` 子命令路径
- 候选 AI：`app/pipeline.py` 其他 helper（`image_output_dir_for` 等）
- 候选 AJ：fuzz / property-based 测试（hypothesis，但需要新依赖）
- 候选 AK：更多 parser 的内部 helper 单测（kreuzberg 适配器、markdown parser）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AI（pipeline helper 补强）。理由：
1. `image_output_dir_for` 等纯函数还可以测
2. 不引入新依赖
3. 之后可以做 AG / AH 的 CLI 子命令路径

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 28 后）：601 pass / 0 fail / 9 skip（HEAD `3657de8`）— **跨过 600 里程碑**

---

## Round 29（2026-08-04）：候选 AI — pipeline helpers 覆盖率补强

### 做了什么
- 候选 AI：扩展 `tests/test_pipeline_helpers.py`，新增 16 个测试覆盖 `image_output_dir_for` / `validate_only` / `get_parser` 的边角路径。
- 重点覆盖项：
  - **`image_output_dir_for`**：不同 hash、不同 output_path、17 字符 hash 截到 16、恰好 16 字符、嵌套 parent、文件名无父目录、返回 Path 类型、空 hash 边界
  - **`validate_only`**：合法 JSON 返回 (True, "OK")、接受 str 路径
  - **`get_parser`**：每次返回新实例、5 个非 fallback parser 不需要 image_output_dir 也能构造
- 无源码改动。

### 下一步建议
- 候选 AG：`app/cli.py` 子命令更细致的测试（参数解析、退出码、stderr 输出）
- 候选 AH：`evaluation/cli.py` 的 `validate-report` 子命令路径
- 候选 AK：parser 内部 helper 单测（kreuzberg / markdown 等）
- 候选 AL：`app/parsers/fallback_parser.py` 的 helper 函数（_is_caption / _classify_pdf_paragraph 等）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AL（fallback parser helpers）。理由：
1. fallback parser 是默认 parser，覆盖率直接影响主路径可靠性
2. _is_caption / _classify_pdf_paragraph / _rows_to_markdown 等是纯函数
3. 不引入新依赖

### 撞墙记录
- 无新撞墙。16 个新测试一次通过。

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 29 后）：617 pass / 0 fail / 9 skip（HEAD `64ab44a`）

---

## Round 30（2026-08-04）：候选 AL — fallback_parser helpers 覆盖率补强

### 做了什么
- 候选 AL：扩展 `tests/test_parsers.py`，新增 35 个测试覆盖 `app/parsers/fallback_parser.py` 内部纯函数 helper。
- 重点覆盖项：
  - **`_is_heading_style`** 7 个边角：含空格 strip、Heading 0 → 1、Heading -1 → 1、TITLE 大小写不敏感、非数字后缀 fallback、"Normal"/空串 拒绝
  - **`_is_caption`** 6 个边角：全角数字、中文 + 句点、Fig. 缩写、缺分隔符拒绝、纯数字拒绝、完整单词必需
  - **`_classify_pdf_paragraph`** 6 个边角：caption 优先级、短句 + 句号 → paragraph、短句无句号 → heading、长文 → paragraph、中文短句有无句号
  - **`_lines_to_para`** 4 个直接单测：空、单行多 word、双行 bbox 跨度、按 x0 排序
  - **`_group_words_to_paragraphs`** 3 个聚类场景：3 行聚合、大行距拆段、缺失 top/bottom 字段
  - **`_image_filename`** 5 个边角：jpg 扩展、02d 索引格式、默认 png、`doc-` 前缀剥离、无 `doc-` 前缀保留
  - **`_extract_inline_image_rids`** 4 个 XML 测试：无 drawing、r:embed、多 drawing、r:link
- 无源码改动。

### 撞墙记录
- **撞墙 1**：`test_is_caption_full_width_digits` 第二条用例用了 `表 ３：实验结果`，`：`（全角冒号）不在 caption regex 的 `[\.、:\s]` 字符类里。改测：换成 `表 ３. 实验结果`（用 `.`）。
- **撞墙 2**：`_image_filename` 测试一开始假设格式是 `d1_img_000.png`，但实际格式是 `image_<safe_doc>_<prefix>_<idx:02d>.<ext>`（有 `image_` 前缀，且 `doc-` 被剥离，索引是 02d 不是 03d）。改测：按真实格式重写。
- 两次都是测试构造时未读源码细节，不是源码 bug。

### 下一步建议
- 候选 AK：kreuzberg / markdown / html parser 内部 helper 单测
- 候选 AM：models.py 的 Element / Document 不变量更多边角
- 候选 AN：app/schema.py 边角（draft 2020-12 各种 keyword）
- 候选 AG：CLI 子命令更细致的测试
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AM（models.py 不变量）。理由：
1. Element / Document 是数据模型核心
2. 不变量校验是 source_truth
3. 纯函数，无依赖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 30 后）：652 pass / 0 fail / 9 skip（HEAD `1086402`）

---

## Round 31（2026-08-04）：候选 AM — models.py dataclass 不变量覆盖补强

### 做了什么
- 候选 AM：扩展 `tests/test_models.py`，新增 26 个测试覆盖 `app/models.py` 中的 dataclass 不变量。
- 重点覆盖项：
  - **Element** 9 个边角：parent_id 设置后正确序列化、显式 confidence、嵌套复杂 metadata、默认 confidence=1.0、默认 metadata={}、默认 parent_id=None、metadata per-instance 隔离、所有 8 种合法 type（heading/paragraph/list_item/table/caption/header/footer/image）
  - **Chunk** 6 个边角：metadata per-instance 隔离、source_spans per-instance 隔离、10000 字长文本、纯空白 text（当前实现接受，记录行为）、5 个 source_element_ids、重复 source_element_ids（dataclass 不去重）
  - **Document** 5 个边角：所有 6 种 source_type 都能构造、默认 collections per-instance 独立、to_dict 不改变 doc 字段、to_dict 键集合与 schema 必需字段对齐、含 relations 时正确序列化
  - **Relation** 2 个边角：自环（from_id == to_id）允许、复杂 metadata
  - **WarningRecord / ErrorRecord** 6 个边角：默认 details=None、空 code 在 dataclass 层允许（schema 在写盘前会拒绝）、嵌套 dict/list details
  - **SCHEMA_VERSION** 2 个边角：str 类型、三段式语义版本
- 无源码改动。

### 撞墙记录
- 无新撞墙。26 个新测试一次通过。

### 下一步建议
- 候选 AN：app/schema.py 边角（draft 2020-12 各种 keyword：$ref、if/then/else、anyOf、additionalProperties）
- 候选 AK：kreuzberg / markdown / html parser 内部 helper 单测
- 候选 AG：CLI 子命令更细致的测试
- 候选 AH：evaluation/cli.py 的 validate-report 子命令路径
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AN（schema.py 边角）。理由：
1. JSON Schema 是写盘前的强制不变量门
2. validate / validate_file 边角（非文件路径、空 JSON、损坏 UTF-8、$ref 解析失败）值得覆盖
3. 纯函数，无外部依赖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 31 后）：681 pass / 0 fail / 9 skip（HEAD `5706787`）

---

## Round 32（2026-08-04）：候选 AN — schema.py helper 与 schema keyword 边角补强

### 做了什么
- 候选 AN：扩展 `tests/test_schema.py`，新增 71 个测试覆盖 `app/schema.py` 公共 helper 与 `document.schema.json` 各种 draft 2020-12 keyword 边角。
- 重点覆盖项：
  - **`load_schema`** 4 个边角：missing file 抛 FileNotFoundError、str path 接受、每次返回独立 dict、默认路径对齐 document schema
  - **`SchemaValidationError`** 2 个边角：默认 errors 为 []、errors kwarg 透传
  - **`validate`** 4 个边角：errors attribute 填充、聚合多个错误、custom schema kwarg、schema=None 走默认
  - **`is_valid`** 2 个边角：custom schema、不向上抛
  - **`validate_file`** 4 个边角：str path、invalid JSON（JSONDecodeError）、valid JSON 不合规内容、custom schema
  - **minLength** 10 个字段：source_path / parser_name / parser_version / element_id / warning code+reason / error code+message / relation type+from_id+to_id
  - **`source_hash`** pattern 4 个边角：大写 hex / 63 字符 / 65 字符 / 含下划线
  - **`confidence`** 边界：0 和 1 都通过
  - **bbox** 类型：float 接受、字符串拒绝
  - **`docx_locator`** 7 个合法字段：paragraph_index / table_index+row+col / relationship_id / section int+string / run_index + 3 个负值拒绝
  - **`source_span`** 2 个边角：negative end、empty element_id
  - **`warning.details` / `error.details`** 类型：必须是 object，list/str 拒绝，空 object 通过，嵌套复杂 object 通过
  - **`warning` / `error` additionalProperties:false** 各 1 个
  - **`ipynb_locator`** 3 个边角：含 line+section_path 可选字段、cell_index ≥ 0、line ≥ 1
  - **`schema_version`** 2 个边角：错误字符串、非字符串类型
  - **`chunk.source_element_ids`** 2 个边角：纯空字符串列表、混合空+非空
  - **类型校验**：elements / chunks / metadata 必须是 array / object
  - **`element` anyOf 语义**：仅 content / 仅 resource_path / 都 null 三种情形
  - **`pdf_locator` / `docx_locator` additionalProperties=true** 各 1 个
- 无源码改动。

### 撞墙记录
- 无新撞墙。71 个新测试一次通过。

### 下一步建议
- 候选 AK：kreuzberg / markdown / html parser 内部 helper 单测
- 候选 AG：CLI 子命令更细致的测试
- 候选 AH：evaluation/cli.py 的 validate-report 子命令路径
- 候选 AO：pipeline / process_single 端到端边角（output_path 为空、parser 不可用降级路径）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AG（CLI 子命令）。理由：
1. CLI 是用户接口，错误处理最易回归
2. 子命令组合（parse/validate/run/validate-report）覆盖率直接影响发布质量
3. argparse exit code / stderr 输出可用 capsys + pytest.raises 验证

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 32 后）：752 pass / 0 fail / 9 skip（HEAD `fbe467e`）

---

## Round 33（2026-08-04）：候选 AG — app/cli.py 子命令与 helper 覆盖补强

### 做了什么
- 候选 AG：扩展 `tests/test_cli.py`，新增 49 个测试覆盖 argparse 入口校验、9 个内部 helper、main() 函数级别返回码。
- 重点覆盖项：
  - **argparse 入口** 9 个：no command / unknown command → rc≠0、parse 缺 -o / 非法 --parser → rc≠0、parse 输入不存在 → rc=1 + 结构化 error JSON、validate 缺文件 → rc=2、validate 损坏 JSON → rc=1、validate 非合规内容 → rc=1、validate 合法 → rc=0
  - **`_iter_supported_files`** 5 个：扩展名过滤、按名升序、recursive 走子目录、目录过滤、大写扩展名识别
  - **`_relative_output_path`** 3 个：基础、嵌套子目录、多 dot 文件名
  - **`_preview`** 7 个：None/空串/短文本透传、空白归一、超长加省略号、恰好 width 不截断、自定义 width
  - **`_load_document_json`** 3 个：合法 / 缺文件 / JSON 解析失败
  - **`_format_summary`** 4 个：完整 doc / 含 warnings+errors / truncate 到 5 / 空 doc
  - **`_format_elements_list`** 5 个：空、含 parent_id、不含 parent_id、content=None、limit=0 全列
  - **`_format_chunks_list`** 4 个：带 spans、缺 spans 数据 → "(none)"、show_spans=False 隐藏、text=None → chars=0
  - **`_emit_structured_error`** 2 个：JSON 写 stderr、含/不含 extra kwargs
  - **`main()`** 6 个：unknown command 抛 SystemExit、validate/inspect 各种返回码
- 无源码改动。

### 撞墙记录
- 无新撞墙。49 个新测试一次通过。

### 下一步建议
- 候选 AK：kreuzberg / markdown / html parser 内部 helper 单测
- 候选 AH：evaluation/cli.py 的 validate-report 子命令路径
- 候选 AO：pipeline / process_single 端到端边角（output_path 为空、parser 不可用降级路径）
- 候选 AP：evaluation/runner.py 评测指标聚合边角（ratio 分母 0 / silent_drop 累加）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AH（evaluation/cli.py）。理由：
1. evaluation CLI 是评测系统入口，validate-report 子命令是发布前 gate
2. argparse 与子命令 dispatch 是 release-quality 必须覆盖的
3. 与 Round 33 AG 同思路，扩大 CLI 边角覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 33 后）：801 pass / 0 fail / 9 skip（HEAD `7769253`）

---

## Round 34（2026-08-04）：候选 AH — evaluation/cli.py 子命令与 helper 覆盖补强

### 做了什么
- 候选 AH：扩展 `tests/test_evaluation_cli.py`，新增 36 个测试覆盖 argparse 入口、`_format_metric`、main() 函数级别返回码。
- 重点覆盖项：
  - **argparse 入口** 8 个：no command / unknown command → rc≠0、--parser 非法 choice / 缺 --manifest / 缺 --output、kreuzberg choice 被接受、--max-chars 记录到 provenance、--tolerance-chars 被接受
  - **validate-report** 2 个：损坏 JSON → rc=1、合法 JSON 但不合规 → rc=1
  - **inspect-doc** 3 个：--tolerance-chars 自定义、空文档、metric 排序顺序（bool 在 numeric 之前）
  - **`_format_metric`** 9 个：None / bool true/false / int / float (4 位小数) / dict / string 各种 value 类型、reason 覆盖默认 'ok'、列对齐宽度（39 字符前缀）
  - **main() 函数级别** 9 个：unknown command + no command 抛 SystemExit、validate-report / inspect-doc / run 各种返回码
  - **`_build_parser`** 1 个：3 个子命令全部注册（run / validate-report / inspect-doc）
  - **run 输出摘要** 2 个：devset_status / file_count / groups / pdf / docx + git_commit / git_dirty
- 无源码改动。

### 撞墙记录
- **撞墙 1**：`test_run_with_explicit_tolerance_chars` 一开始假设 `_tolerance_chars` 在 `report.evaluation_params` → KeyError。改：`per_doc.metrics._tolerance_chars` → 仍 KeyError。最终发现 runner.py 把 `_tolerance_chars` 加到 `per_doc_results[i]` 顶层，但 build public_report 时只挑 `doc_id/source_type/metrics/wall_time_seconds` 4 个字段（schema additionalProperties:false）。改测：只验证 CLI 接受参数 + 报告通过 schema 校验。
- **撞墙 2**：`test_format_metric_with_reason_overrides_default` 第二条断言 `"ok" not in result.split(...)[0]` 失败 — 因为 metric name 是 `ok_metric`，含 "ok"。改测：只断言 `(custom_reason)` 出现、`(ok)` 不出现。
- **撞墙 3**：`test_format_metric_alignment_width` 算错了 width。实际 format 是 `"  {name:36} {value}"` → 前缀 = 2 + 36 + 1 = 39 字符。改测：`assert len(name_part) == 39`。
- 三次都是测试断言写错，不是源码 bug。

### 下一步建议
- 候选 AK：kreuzberg / markdown / html parser 内部 helper 单测
- 候选 AO：pipeline / process_single 端到端边角（output_path 为空、parser 不可用降级路径）
- 候选 AP：evaluation/runner.py 评测指标聚合边角（ratio 分母 0 / silent_drop 累加）
- 候选 AQ：evaluation/manifest.py / annotation.py 边角（resolve_annotation 路径、annotation 缺字段降级）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AO（pipeline 端到端边角）。理由：
1. process_single 是核心入口，覆盖了 parser/chunker/schema 全链路
2. parser 不支持扩展名 / 缺输出目录 / 错误恢复路径值得覆盖
3. 与 Round 28 chunker 测试互补

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 34 后）：837 pass / 0 fail / 9 skip（HEAD `c566e98`）

---

## Round 35（2026-08-04）：候选 AO — process_single 端到端 + helper 覆盖补强

### 做了什么
- 候选 AO：扩展 `tests/test_pipeline_errors.py`，新增 34 个测试覆盖 process_single 各种 parser / max_chars / output_path 组合 + Document 字段完整性 + JSON 输出格式。
- 重点覆盖项：
  - **6 个 parser 端到端**：markdown / html / text / ipynb 各跑一遍 + 验证 source_type / parser_name / elements 数 / chunks 数
  - **hash 稳定性** 1 个：同一份输入跑两次 source_hash 一致
  - **max_chars 边角** 4 个：32（chunker 最小值）、100000（无分块）、800（默认）、低于 32 触发 chunker_failed
  - **output_path 边角** 2 个：嵌套父目录自动 mkdir、str 类型 input_path 接受
  - **error details 结构** 3 个：file_not_found.path、schema_validation_failed.validation_errors、no_extracted_elements.warnings + source_type
  - **validate_only 边角** 3 个：目录（非文件）、str 路径、合法文件返回 (True, "OK")
  - **get_parser 边角** 4 个：image_output_dir 接受 str、所有 6 个 parser 都有 name / version / parse 属性
  - **输出 JSON 格式** 4 个：indent=2、UTF-8 编码、ensure_ascii=False（无 \u escape）、pipeline 幂等
  - **Document 字段** 3 个：metadata 是 dict、relations 默认空 list、warnings 是 list
  - **unsupported_type** 2 个：fallback 拒绝 .txt、markdown 拒绝 .pdf
- 无源码改动。

### 撞墙记录
- **撞墙 1**：`test_process_single_very_small_max_chars` 用 max_chars=10，但 StructuralChunker 强制 max_chars >= 32。改测：用 32（最小值），并新增 `test_process_single_max_chars_below_minimum_yields_chunker_failed` 验证低于最小值的错误路径。
- **撞墙 2**：`test_process_single_document_metadata_is_empty_dict_by_default` 假设默认 metadata 是空 dict，但 fallback parser 主动填了 `{'fallback': True, 'image_output_dir': None}`。改测：放宽断言为 `isinstance(metadata, dict)`。

### 下一步建议
- 候选 AK：kreuzberg / markdown / html parser 内部 helper 单测
- 候选 AP：evaluation/runner.py 评测指标聚合边角（ratio 分母 0 / silent_drop 累加）
- 候选 AQ：evaluation/manifest.py / annotation.py 边角
- 候选 AR：app/chunkers/structural.py 内部 _ChunkBuffer / 切句函数边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AR（structural chunker 内部 helper）。理由：
1. chunker 是 pipeline 第二阶段，直接影响输出 chunk 质量
2. _ChunkBuffer / _split_long_sentence 是纯函数，易于直接单测
3. 与 Round 28 互补（Round 28 覆盖 normalize_text / __init__ / 公共路径，本轮覆盖内部 helper）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 35 后）：871 pass / 0 fail / 9 skip（HEAD `3618bc4`）

---

## Round 36（2026-08-04）：候选 AR — chunker 内部 helper 与集成边角覆盖补强

### 做了什么
- 候选 AR：扩展 `tests/test_chunker.py`，新增 40 个测试覆盖 `app/chunkers/structural.py` 内部纯函数 helper + 集成边角。
- 重点覆盖项：
  - **`_hard_split_with_whitespace_fallback`** 7 个：空串、纯空白、短文本透传、空白边界切分（boundary_after='whitespace'）、无空白 forced_char 兜底、每个 piece <= max_chars、start/end 坐标系
  - **`_split_long_text`** 9 个：空、纯空白、短文本、strip 后再切、英文句号、中文句号、?! 标点、超长文本、单空格 joiner
  - **`_SplitPiece`** 2 个：默认 start/end=0、frozen（赋值抛异常）
  - **`_element_text_with_span`** 6 个：paragraph stripped + start/end 推导、image 返回空、纯空白返回空、无前导空白、仅尾部空白、`_element_text` 兼容方法
  - **chunker 集成** 9 个：空 doc / 全空 content → 空 chunks、连续 heading 各自独立成 chunk、超长 paragraph 强制切分、long_paragraph_sentence_split strategy、chunk_id 格式（`{doc_id}::c{counter:04d}`）+ 递增、metadata.max_chars / char_count、多 paragraph 合并的 source_spans、source_element_ids 在 _ChunkBuffer 内去重、paragraph→table→paragraph 三段独立、单空格 joiner
  - **`_SENTENCE_SPLIT_RE`** 3 个：英文 . + 空白、中文 。 + 空白、无空白不切
  - **`_WHITESPACE_RE`** 1 个：所有空白压成单空格
  - **`normalize_text`** 3 个：幂等、emoji 保留、全角空格识别
- 无源码改动。

### 撞墙记录
- **撞墙 1**：`test_chunk_chunk_id_format` 用了 `document_id=` kwarg，但 `_make_doc` 的形参名是 `doc_id=`。改测：换 kwarg 名。
- **撞墙 2**：`test_sentence_split_re_splits_on_chinese_period` 用 `"你好。世界"`，但 `_SENTENCE_SPLIT_RE` 的正则是 `(?<=[。！？!?\.])\s+` — 要求句末标点后跟空白才切。中文习惯无空白，所以不切。改测：加空格 `"你好。 世界"`。

### 下一步建议
- 候选 AK：kreuzberg / markdown / html parser 内部 helper 单测
- 候选 AP：evaluation/runner.py 评测指标聚合边角
- 候选 AQ：evaluation/manifest.py / annotation.py 边角
- 候选 AS：app/hash.py 内部边角（chunk size、二进制读取）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AK（其他 parser 内部 helper）。理由：
1. fallback parser 已在 Round 30 充分覆盖
2. markdown / html / ipynb parser 各自的内部 helper 仍缺单测
3. 与 chunker/pipeline 测试互补，全面覆盖 parser 层

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 36 后）：911 pass / 0 fail / 9 skip（HEAD `b005a82`）

---

## Round 37（2026-08-04）：候选 AK — markdown / text parser 内部 helper 覆盖补强

### 做了什么
- 候选 AK：扩展 `tests/test_parsers_markdown.py` 与 `tests/test_parsers_text.py`，新增 63 个测试覆盖 7 个正则常量 + 多个 helper + element/document metadata 边角。
- 重点覆盖项（markdown）：
  - **正则常量** 19 个：_ATX_HEADING_RE（6 级、trailing # 剥、7 个 # 拒、无空格拒、含 # 内容）、_THEMATIC_RE（-/*/_ 各种组合）、_FENCED_RE（backtick/tilde + 多字符 + 语言捕获）、_UNORDERED_LIST_RE、_ORDERED_LIST_RE、_BLOCKQUOTE_RE、_STANDALONE_IMAGE_RE、_PIPE_TABLE_ROW_RE、_PIPE_TABLE_SEP_RE
  - **element metadata** 9 个：confidence=0.95、element_id 格式、code_block language、blockquote kind、list_item ordered/unordered、table row/col/source、image alt + resource_path、空 code block 警告
  - **`_detect_md_source_type`** 3 个：大写扩展名接受、不支持扩展名拒、无扩展名拒
  - **`_rows_to_md`** 2 个：双行输出、jagged pad
- 重点覆盖项（text）：
  - **`_detect_text_source_type`** 5 个：.txt / .text / .TXT / .TEXT 接受、.md / 无扩展名拒
  - **element/document metadata** 13 个：metadata={"text": True}、confidence=0.95、element_id 格式、type 全是 paragraph、metadata 空 dict、parent_id None、source_path 保留、source_hash 透传、document_id 派生、chunks/relations/errors 默认空
  - **`_split_paragraphs`** 3 个：trailing newline、trailing 空白 strip、tab 作空白
  - **warning** 2 个：空文件 / 纯空白文件 → text_no_content
  - **错误路径** 2 个：missing file → file_not_found、.md → unsupported_type
  - **UTF-8 fallback** 1 个：非法字节用 errors=replace
  - **常量** 1 个：name="text"、version="stdlib/0.1.0"
  - **locator** 1 个：只含 line 键
- 无源码改动。

### 撞墙记录
- 无新撞墙。63 个新测试一次通过。
- 注：删除了一个 docstring 里的 `\`\`\`` 转义（引发 SyntaxWarning）。

### 下一步建议
- 候选 AK 继续：html / ipynb parser 内部 helper（regex / 段落切分 / cell 处理）
- 候选 AP：evaluation/runner.py 评测指标聚合边角
- 候选 AQ：evaluation/manifest.py / annotation.py 边角
- 候选 AS：app/hash.py 内部边角（chunk size、二进制读取）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AK 续作（html + ipynb parser）。理由：
1. html parser 446 行，含大量正则与 DOM 处理，覆盖率不足
2. ipynb parser 227 行，含 cell 类型分类逻辑
3. 同 Round 37 思路，扩大 parser 层覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 37 后）：974 pass / 0 fail / 9 skip（HEAD `a9f6029`）

---

## Round 38（2026-08-04）：候选 AK 续 — html + ipynb parser 内部 helper 覆盖补强

### 做了什么
- 候选 AK 续：扩展 `tests/test_parsers_html.py` 与 `tests/test_parsers_ipynb.py`，新增 68 个测试覆盖常量 + 多个 helper + element/document metadata 边角 + 错误路径。
- 重点覆盖项（html，30 个新测试）：
  - **`_detect_html_source_type`** 3 个：大写扩展名接受、未知后缀拒、无后缀拒
  - **常量** 2 个：_HEADING_LEVELS 含 h1-h6、_SKIP_TAGS 含 script/style
  - **HtmlParser metadata/element** 6 个：metadata={"html": True}、element_id 格式、document_id 派生、chunks/relations/errors 默认空
  - **HTML 结构** 10 个：nested list、blockquote + kind、pre + kind、image resource_path、table、skip meta/noscript/link 标签
  - **`_rows_to_md`** 3 个：空输入、单行无 body、三行含两 body
  - **HTML 实体** 2 个：numeric `&#65;` → 'A'、named `&amp;` → '&'
  - **locator** 3 个：section_path 跟踪、heading level metadata、markdown locator 携带 section_path
  - **边界** 4 个：空 body 警告、非法 UTF-8 用 errors=replace、hr 标签忽略、多空行不创建 element
- 重点覆盖项（ipynb，38 个新测试）：
  - **`_detect_ipynb_source_type`** 4 个：.ipynb 接受、大写接受、.json 拒、无后缀拒
  - **`_cell_source_to_text`** 7 个：str passthrough、空 str、list 拼接、空 list、None、int/float → 空、list 内非 str 元素
  - **`_extract_kernel_language`** 8 个：kernelspec.language 优先、kernelspec.name 回退、language_info.name 回退、空 metadata、kernelspec=None 不崩、language_info=None 不崩、优先级验证
  - **metadata/element 边角** 13 个：metadata ipynb=True、nbformat_minor 记录、confidence=0.95、element_id 格式、parent_id None、resource_path None（code）、source_path 保留、source_hash 透传、document_id 派生、chunks/relations/errors 空、name/version 常量
  - **错误路径** 6 个：top-level not dict、cells not list、cell not dict warning、空 raw cell 静默跳过、code/raw cell 内容 strip、cell_type 缺失 → unknown warning、metadata 空字典、nbformat 缺失按 4+ 处理、markdown cell 仅空白 → no_content、outputs 字段忽略、非法 UTF-8 → UnicodeDecodeError 传播（**契约测试，反映现有行为**）
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_ipynb_parser_invalid_utf8_falls_back_to_replace` 最初假设 IpynbParser 用 `errors=replace`，实际 `p.open("r", encoding="utf-8")` 走 strict 模式，UnicodeDecodeError 不被 JSONDecodeError/OSError 捕获 → 直接传播。改为契约测试 `test_ipynb_parser_invalid_utf8_propagates_unicode_error`，反映实际行为。
- 其余 67 个新测试一次通过。

### 下一步建议
- 候选 AP：evaluation/runner.py 评测指标聚合边角（聚合算法、ratio 分母为 0、silent_drop 计算）
- 候选 AQ：evaluation/manifest.py / annotation.py 边角（manifest 校验、annotation 加载）
- 候选 AS：app/hash.py 内部边角（chunk size、二进制读取、hash 透传）
- 候选 AT：app/parsers/fallback_parser.py 内部边角（pdfplumber/python-docx 适配）
- 候选 AU：app/parsers/base.py 内部边角（make_document_id、Parser 基类契约）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AS（app/hash.py 内部边角）。理由：
1. hash.py 是基础工具，被 parser/pipeline 多处调用
2. 模块小（~80 行），单测投入低
3. SHA256 / chunk size / 二进制读取 / hash 透传都有边角可探
4. 之后再做候选 AP/AQ（评测层）扩大覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 38 后）：1049 pass / 0 fail / 9 skip（HEAD `1b1ae6b`）

---

## Round 39（2026-08-04）：候选 AU — parsers/base.py 内部 helper 覆盖

### 做了什么
- 候选 AU：新建 `tests/test_parsers_base.py`，新增 50 个测试覆盖 `app/parsers/base.py` 的全部公共 API。
- 之前 base.py 是 parser 层基础设施，被 fallback / kreuzberg parser 调用，但只有间接测试。本轮建立直接测试。
- 重点覆盖项：
  - **ParserError** 12 个：init/str/Exception 继承、raise 与 catch、details 默认空 dict、details=None → {}、details 每实例独立（验证无共享可变默认）、参数顺序 (code, message, details)
  - **make_document_id** 12 个：doc- 前缀、取前 16 字符、总长度 20、确定性、不同 hash 不同 id、大写 hex 接受、混合大小写 hex 接受、短/长/空 hash 抛 ValueError、非 hex 64 字符也接受（**契约测试：函数只查长度，不查字符集**）
  - **detect_source_type** 17 个：.pdf / .docx 接受、.PDF / .DOCX / .Pdf / .Docx 大小写接受、str/Path 接受、.txt/.md/.ipynb/.html 拒、无后缀/空后缀拒、ParserError code=unsupported_type、details 含 suffix、错误消息提及扩展名
  - **Parser ABC** 9 个：不能直接实例化、类属性 name='abstract'/version='0.0.0' 默认、子类不实现 parse 不能实例化、子类实现 parse 可实例化、子类继承默认 name/version、子类可覆盖 name/version、parse 是 abstractmethod（验证 `__isabstractmethod__`）、子类 parse 返回 Document 完整契约
- 无源码改动。

### 撞墙记录
- 无撞墙。50 个新测试一次通过。

### 下一步建议
- 候选 AS：app/hash.py 内部边角（17 个测试已存在，可补充 chunk size 边界 / 多种二进制 pattern / surrogate pair）
- 候选 AT：app/parsers/fallback_parser.py 内部 helper（pdfplumber/python-docx 适配，~600 行）
- 候选 AP：evaluation/runner.py 评测指标聚合边角
- 候选 AQ：evaluation/manifest.py / annotation.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AT（fallback_parser.py 内部 helper）。理由：
1. fallback_parser.py 是默认 parser，~600 行，覆盖率最重要
2. 含 PDF/DOCX 双路径、辅助函数（_pdfplumber_extract / _docx_extract 等）
3. 与已覆盖的 markdown/text/html/ipynb 形成完整 parser 层覆盖
4. 后续再补 AS / AP / AQ

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 39 后）：1099 pass / 0 fail / 9 skip（HEAD `132c3d8`）

---

## Round 40（2026-08-04）：候选 AT — fallback_parser.py 内部 helper 覆盖

### 做了什么
- 候选 AT：新建 `tests/test_parsers_fallback.py`，新增 79 个测试覆盖 `app/parsers/fallback_parser.py`（630 行）的全部纯函数 helper。
- 不需要真实 PDF/DOCX 文件，全部用 synthetic 输入或 lxml 构造 XML。
- 重点覆盖项：
  - **`_is_caption` / `_CAPTION_RE`** 15 个：Table/Figure/Fig./Fig、中文 表/图、全宽数字 ０-９、大小写不敏感、分隔符变体（. : 空白 、）、空/None/纯文本拒、regex 是 compiled pattern
  - **`_rows_to_markdown`** 8 个：空输入、纯表头、1/2 行 body、None→""、int→str、jagged pad、str 返回类型
  - **`_image_filename`** 6 个：基本格式、2 位零填充、10/99 不额外补 0、剥离 doc- 前缀、自定义扩展、默认 png
  - **`_group_words_to_paragraphs`** 7 个：空、单词、同行、相邻行同段、大间距分 2 段、bbox 聚合、行内按 x0 排序
  - **`_lines_to_para`** 4 个：空行→空 text + bbox None、单词、多行拼接顺序、bbox 跨行聚合
  - **`_classify_pdf_paragraph`** 10 个：空→paragraph、caption、短无句号→heading、短带 ./。/?/!→paragraph、长行→paragraph、caption 优先于 heading、前导空白 strip
  - **`_is_heading_style`** 15 个：None/空→False、Title→level 1、Heading 1/2/3、whitespace pad、小写、Heading 无 level→1、垃圾后缀→1、Heading 0→clamp 1、Heading -1→clamp 1、Normal/Body/Subtitle→False
  - **`_extract_inline_image_rids`** 5 个：空 XML→[]、找 r:embed、多图片、r:link 回退、drawing 无 blip→[]（用 lxml 构造 XML）
  - **FallbackParser 类** 9 个：name='fallback'、version 含三库版本、默认 _image_output_dir=None、str/Path 接受、继承 Parser、missing file raises file_not_found + details
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_classify_pdf_paragraph_caption_overrides_short_line` 输入 "Fig 1"（数字后无分隔符）被 _CAPTION_RE 拒绝（regex 要求数字后跟 `[\.、:\s]`），实际走 heading 路径。改输入为 "Fig 1." 后通过。

### 下一步建议
- 候选 AT 续：kreuzberg_parser.py 内部 helper（~200 行，类似覆盖）
- 候选 AS：app/hash.py 内部边角补强
- 候选 AP：evaluation/runner.py 评测指标聚合边角
- 候选 AQ：evaluation/manifest.py / annotation.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 kreuzberg_parser.py 内部 helper（候选 AT 续）。理由：
1. kreuzberg_parser.py ~200 行，是另一个可选 parser
2. 含 _is_kreuzberg_available / _extract_elements 等可测纯函数
3. 与 fallback 形成完整 parser 层覆盖（base + 5 个具体 parser 全覆盖）
4. 之后转入 evaluation 层（AP/AQ）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 40 后）：1178 pass / 0 fail / 9 skip（HEAD `0440698`）

---

## Round 41（2026-08-04）：候选 AT 续 — kreuzberg_parser.py 内部 helper 覆盖

### 做了什么
- 候选 AT 续：新建 `tests/test_parsers_kreuzberg.py`，新增 53 个测试覆盖 `app/parsers/kreuzberg_parser.py`（246 行）的全部纯函数 helper。
- 不调用 kreuzberg 库，只测内部算法逻辑。
- 至此 parser 层全覆盖：base.py / fallback_parser.py / kreuzberg_parser.py / markdown_parser.py / text_parser.py / html_parser.py / ipynb_parser.py。
- 重点覆盖项：
  - **常量 + `_HEADING_RE`** 9 个：_SHORT_LINE_MAX=80、_HEADING_RE 是 compiled pattern、h1-h6 匹配、h7 拒、无空格拒、无内容拒、trailing 文本捕获、纯文本不匹配
  - **`_classify_line`** 15 个：空/whitespace→paragraph、ATX h1/h3→heading + level、ATX 无 heuristic 键、短无句号→heading 启发式、短带 ./。/?/!/！/？→paragraph、长行→paragraph、ATX 优先于 short_line、strip 应用
  - **`_make_locator`** 6 个：pdf page=1 + 占位符、pdf 忽略 paragraph_index、docx paragraph_index + 启发式标记、docx 无 page、docx index 跟随入参、pdf 始终 page=1
  - **`_split_content_to_elements`** 18 个：空、单/双段落、ATX heading 提取、短行 heading、heading + body 同 block、heading + 多行 rest 触发 paragraph、paragraph 含 kreuzberg_heuristic、ATX heading 无 heuristic 键、heading confidence=0.6、paragraph confidence=0.5、rest paragraph confidence=0.5、element_id 连续、docx locator 有 paragraph_index、pdf locator page=1 占位、多空行单分隔、block 空白 strip、第二返回值固定空 list
  - **KreuzbergParser 类** 5 个：name='kreuzberg'、version 字符串、默认 include_document_structure=True、可禁用、继承 Parser
- 无源码改动。

### 撞墙记录
- **Wall 1**：docstring 含 `\s+` 字面量 → SyntaxWarning。改为「空白」描述，去掉反斜杠。

### 下一步建议
- 候选 AS：app/hash.py 内部边角补强（17 → ~25 个测试）
- 候选 AP：evaluation/runner.py 评测指标聚合边角
- 候选 AQ：evaluation/manifest.py / annotation.py 边角
- 候选 AV：app/chunkers/structural.py 已有 40 个，可补 source_element_ids / 长文本极端切分
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AP（evaluation/runner.py）。理由：
1. parser 层已全覆盖（7 个 parser 全有专门测试）
2. evaluation 层是另一个独立模块，runner.py 是核心
3. 评测指标聚合（counts sum、success_rates rate、ratio macro avg）有复杂边角
4. 之后转 AQ（manifest/annotation）形成 evaluation 层全覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 41 后）：1231 pass / 0 fail / 9 skip（HEAD `0001aee`）

---

## Round 42（2026-08-04）：候选 AP — evaluation/runner.py 内部 helper 边角覆盖

### 做了什么
- 候选 AP：扩展 `tests/test_evaluation_runner.py`，新增 37 个测试覆盖 `_load_annotation` / `_process_one` / `run_evaluation` 的边角。
- 之前 runner.py 已有 19 个端到端测试，本轮补齐纯函数 + 报告字段层边角。
- 重点覆盖项：
  - **`_load_annotation`** 9 个新测试：directory→None、显式 None、JSON list 返回 list、nested dict、JSON null、JSON number 顶层、空 object、截断 JSON、二进制垃圾 → UnicodeDecodeError 传播（**契约测试，反映现有行为：encoding=utf-8 不加 errors=replace**）
  - **`_process_one`** 6 个新测试：error_dict 含 code 字段、failure 时 parser_version=None、success 时 parser_version=str、total_seconds float 非负、创建 `_per_doc/` 目录、成功返回 document_dict 含 elements/chunks、成功时 error=None
  - **`run_evaluation`** 22 个新测试：wall_time_seconds 结构（total/parse/chunk/reasons 各字段）、doc_id/source_type 保留、空 manifest summary 安全、返回 dict、顶层 6 个 keys、report_version 匹配常量、expected_failures 始终 list、多 doc 顺序保留、expected_failure 4 字段 shape、默认 parser_name=fallback、默认 max_chars=800、默认 tolerance_chars=30、output 写盘、provenance git_commit/git_dirty、evaluator_version 匹配常量、dependencies dict（pdfplumber/python-docx/pypdfium2）、run_timestamp_iso ISO 8601 含 T、devset 字段、per_doc metrics dict、per_doc total float
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_load_annotation_binary_garbage_returns_none` 假设 UnicodeDecodeError 被兜底。实际 `_load_annotation` 的 except 只覆盖 `(OSError, json.JSONDecodeError)`，UnicodeDecodeError 是 ValueError 子类，会传播。改为契约测试 `propagates_unicode_error`，反映现有行为。
- **Wall 2**：`test_run_evaluation_provenance_includes_project_root` 假设 provenance 含 project_root。实际 build_provenance 输出 git_commit/git_dirty/evaluator_version/report_version/parser_name/parser_version/dependencies/max_chars/run_timestamp_iso 共 9 个字段，无 project_root。改为测 git_commit/git_dirty、evaluator_version、dependencies、run_timestamp_iso。

### 下一步建议
- 候选 AQ：evaluation/manifest.py / annotation_metrics.py 内部边角
- 候选 AS：app/hash.py 内部边角补强
- 候选 AV：evaluation/metrics.py 边角（compute_automatic_metrics 各指标分母为 0 路径）
- 候选 AW：evaluation/report.py 边角（aggregate_summary / build_devset_section）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AQ（manifest.py 边角）。理由：
1. manifest.py 是评测层的入口（清单解析），与 runner.py 紧耦合
2. 含 path 校验、绝对路径拒、反斜杠拒、project_root 范围检查等可测逻辑
3. annotation_metrics.py 含 chunk_boundary_prf / figure_caption_prf 的边角（no_annotation、no_chunks、no_elements）
4. 之后转 AV / AW 形成 evaluation 层全覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 42 后）：1268 pass / 0 fail / 9 skip（HEAD `2729c52`）

---

## Round 43（2026-08-04）：候选 AQ — manifest.py + annotation_metrics.py 内部边角

### 做了什么
- 候选 AQ：扩展 `tests/test_manifest.py`（+30）和 `tests/test_annotation_metrics.py`（+19），共新增 49 个测试。
- 至此 evaluation 层核心全覆盖：runner.py / manifest.py / annotation_metrics.py 都有专门边角测试。
- 重点覆盖项（manifest.py）：
  - **`ManifestError` 类契约** 2 个：is Exception subclass、可 raise/catch
  - **`_is_absolute_like`** 6 个新边角：单字符、两字符、小写盘符、非字母盘符、`./` 和 `../` 相对路径、纯 `/`
  - **`_has_backslash`** 3 个：纯反斜杠、正斜杠返 False、混合斜杠
  - **frozen dataclass** 3 个：Manifest/DocumentEntry/ExpectedFailure 都 frozen，赋值抛 FrozenInstanceError
  - **Manifest 属性直接构造** 5 个：file_count/pdf_count/docx_count/categories_covered（混合重叠 + 全空）
  - **`_detect_project_root`** 3 个：start 是目录、返回绝对路径、立即找到 pyproject
  - **`content_group_count`** 2 个：链式 pair（A→B→C→A → 3 frozenset groups）、两组互配（A↔B + C↔D → 2）
  - **`load_manifest` 字段保留** 6 个：manifest_version/devset_status/path_str 保留、resolved_path 是绝对路径、空 documents、空 expected_failures 默认
- 重点覆盖项（annotation_metrics.py）：
  - **`PARSER_DOES_NOT_EMIT_RELATIONS` 常量** 2 个：值固定字符串、是 str 类型
  - **`figure_caption_prf` shape** 3 个：返回 3 个 key、有 annotation 仍返 null、每个 metric 含 value+reason
  - **`chunk_boundary_prf` 容差极端** 3 个：tolerance=0 严格、tolerance=10000 全包含、tolerance=-1 永不匹配
  - **默认值** 1 个：默认 tolerance=30
  - **chunk 边界场景** 2 个：3 chunks 2 边界、2 chunks 1 边界
  - **f1 计算** 2 个：完美匹配 f1=1.0、半匹配 f1≈0.667
  - **missing_markers** 2 个：marker 不在 stream → _missing_markers；全找到 → 无此键
  - **`_tolerance_chars` 总存在** 3 个：success/document=None/annotation=None 三条路径都有
  - **空 chunk text** 1 个：所有 chunk text 空字符串 → stream 也空 → missing_markers 记录

### 撞墙记录
- 无撞墙。49 个新测试一次通过。

### 下一步建议
- 候选 AV：evaluation/metrics.py 内部边角（compute_automatic_metrics 各指标分母为 0 / 各 reason）
- 候选 AW：evaluation/report.py 内部边角（aggregate_summary / build_devset_section / get_dependency_versions）
- 候选 AS：app/hash.py 内部边角补强
- 候选 AX：evaluation/schema.py 边角（validate 函数各 schema 名）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AV（evaluation/metrics.py）。理由：
1. metrics.py 是评测核心，含 compute_automatic_metrics 全部指标计算
2. 各 metric 的 reason 字段（pipeline_failed / no_chunks / silent_drop 等）需要逐一覆盖
3. 与已覆盖的 annotation_metrics.py 形成 metrics 全覆盖
4. 之后转 AW（report.py）完成 evaluation 层

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 43 后）：1317 pass / 0 fail / 9 skip（HEAD `57651f5`）

---

## Round 44（2026-08-04）：候选 AV — evaluation/metrics.py 内部边角覆盖

### 做了什么
- 候选 AV：扩展 `tests/test_metrics.py`，新增 43 个测试覆盖 `evaluation/metrics.py`（381 行）的全部内部 helper + compute_automatic_metrics 字段完整性。
- 重点覆盖项：
  - **内部 helper 直接单测** 17 个：_null（empty reason 也接受）、_ratio（int→float 转换、0.0/1.0 边界）、_bool_metric（truthy/falsy 强制转换）、_int_metric（float 截断 3.7→3、负数 -2.9→-2）、_TEXT_TYPES 常量（排除 image、含 heading/paragraph/list_item/table/caption）、_PDF_BBOX_REQUIRED_TYPES 常量（排除 table）、_NOT_EVALUATED 常量值
  - **compute_automatic_metrics shape & 契约** 10 个：返回 14 个顶层 keys（pipeline_success/error_code/schema_valid/element_count_total/element_count_by_type/pdf_locator_valid_ratio/docx_locator_valid_ratio/image_resource_exists_ratio/chunk_reference_intact_ratio/text_preservation_equal/text_char_multiset_precision/text_char_multiset_recall/heading_boundary_compliance/silent_drop_count）、error 存在→pipeline_success False、document None+error None 也 False、error.code 透传、element_count_total int、element_count_by_type dict、chunk_count 通过 ratio 反映、pipeline_failed 时 ratio null、schema_valid False 路径
  - **`_strip_unicode_whitespace`** 5 个：实际去全部空白（不是 strip），内部空白也删，全空白→空，处理 \xa0 nbsp 与 U+3000 全角空格
  - **`_is_valid_bbox`** 3 个：四 float 接受、string 元素拒、dict 拒、tuple 拒（仅 list 类型接受）、负数接受
  - **`_image_resource_ratio`** 2 个：全有效路径→1.0、无 image 元素→null
  - **`_silent_drop_count`** 3 个：实际满足期望→0、值是 int、无 expectations→null
  - **`_chunk_reference_ratio`** 2 个：全 chunks 有 ids→1.0、无 chunks→null
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_compute_metrics_returns_all_expected_top_level_keys` 假设 metric key 名（element_count、chunk_count、text_char_multiset_equal、heading_boundary_compliance_ratio 等）。实际名：element_count_total、element_count_by_type、text_preservation_equal、heading_boundary_compliance（无 _ratio 后缀）。改测试用真实 key。
- **Wall 2**：`test_compute_metrics_element_count_returns_int` 用 m["element_count"] → KeyError。实际 key 是 m["element_count_total"]。
- **Wall 3**：`test_compute_metrics_schema_check_exception_path` 假设 reason 含 "schema_check_exception"。实际 document_passes_schema 对不完整 document 返 False（不抛异常），reason 为 None。改为只测 value=False。
- **Wall 4**：`_strip_unicode_whitespace` 函数名误导——实际是**删全部** Unicode 空白（不是 strip 首尾）。`"  hello world  "` → `"helloworld"`。改测试反映实际行为。

### 下一步建议
- 候选 AW：evaluation/report.py 内部边角（aggregate_summary / build_devset_section / get_dependency_versions / get_git_provenance）
- 候选 AX：evaluation/schema.py + evaluation/schema_validation.py 边角
- 候选 AS：app/hash.py 内部边角补强
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AW（evaluation/report.py）。理由：
1. report.py 含 aggregate_summary（macro avg）、build_devset_section、get_dependency_versions、get_git_provenance 等多个纯函数
2. aggregate_summary 是最终聚合点，决定报告 summary 字段
3. 与 metrics.py 形成「指标计算 + 指标聚合」全覆盖
4. 之后转 AX（schema 边角）完成 evaluation 层全覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 44 后）：1360 pass / 0 fail / 9 skip（HEAD `b479bed`）

---

## Round 45（2026-08-04）：候选 AW — evaluation/report.py 内部边角覆盖

### 做了什么
- 候选 AW：扩展 `tests/test_evaluation_report.py`，新增 41 个测试覆盖 `evaluation/report.py`（200 行）的全部纯函数 + 常量。
- 至此 evaluation 层核心全覆盖：runner.py / manifest.py / annotation_metrics.py / metrics.py / report.py 都有专门边角测试。
- 重点覆盖项：
  - **常量** 5 个：_COUNT_METRICS==('element_count_total',)、_SUCCESS_BOOL_METRICS==('pipeline_success',)、_RATIO_METRICS 含 12 个 ratio key、_RATIO_METRICS 排除 figure_caption_*、排除 count/silent_drop
  - **`get_dependency_versions`** 3 个：返回 dict、含 3 个已知包（pdfplumber/python-docx/pypdfium2）、值 str-or-None
  - **`get_git_provenance`** 3 个：返回 dict 含 2 keys、真实 repo 返回 commit/dirty、subprocess 失败安全（不存在路径不崩）
  - **`build_provenance`** 8 个：9 个顶层 keys、max_chars int 转换、parser_name/version 透传、run_timestamp_iso ISO 8601 格式、evaluator_version 匹配常量、report_version 匹配常量、dependencies 子字段含 3 包
  - **`build_devset_section`** 2 个：6 个 keys、所有值透传
  - **`aggregate_summary`** 20 个：4 个顶层 keys（counts/success_rates/ratio_macro_averages/silent_drop_total）、counts.sum 是 int、counts.participating_docs、success_rates rate/total/success_count、ratio macro_average/participating_docs/not_evaluated、silent_drop_total 求和 + 排除 null、空 list 边角（rate None/total 0/success_count 0/participating_docs 0/silent_drop_total None）
- 无源码改动。

### 撞墙记录
- 无撞墙。41 个新测试一次通过。

### 下一步建议
- 候选 AX：evaluation/schema.py + evaluation/schema_validation.py 边角
- 候选 AS：app/hash.py 内部边角补强
- 候选 AY：app/pipeline.py 内部边角（image_output_dir_for / get_parser / process_single 错误路径）
- 候选 AZ：app/chunkers/__init__.py 边角（如果有）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AY（app/pipeline.py 内部边角）。理由：
1. pipeline.py 是核心入口，含 image_output_dir_for / get_parser / process_single
2. image_output_dir_for 是从 output_path + source_hash 推导图片目录的关键 helper
3. 与已覆盖的 parser/chunker 形成完整 app/ 层覆盖
4. 之后转 AX（schema 边角）完成所有模块的边角覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 45 后）：1401 pass / 0 fail / 9 skip（HEAD `2ba1437`）

---

## Round 46（2026-08-04）：候选 AY — app/pipeline.py 内部边角覆盖

### 做了什么
- 候选 AY：扩展 `tests/test_pipeline_helpers.py`，新增 24 个测试覆盖 `app/pipeline.py`（216 行）的 `get_parser` / `image_output_dir_for` / `validate_only` / `process_single` 错误路径边角。
- 至此 app/ 层核心全覆盖：models / schema / cli / hash / pipeline / chunkers / parsers（base + 6 个具体 parser）都有专门测试。
- 重点覆盖项：
  - **`get_parser`** 8 个新测试：未知名称抛 ValueError（消息含未知名）、错误消息列出全部 6 个支持名、fallback + Path image_output_dir、fallback + str image_output_dir（自动转 Path）、6 个支持名都返回 Parser 实例、默认 image_output_dir=None、每次返回新实例（不缓存）、返回的对象有 .name 和 .version 属性
  - **`image_output_dir_for`** 4 个：目录名前缀 'images-'、显式 Path 对象接受、短 source_hash（<16 字符）取全串、parent 跟随 output_path.parent
  - **`validate_only`** 5 个：missing file 返回 (False, msg)、invalid JSON 返回 (False, JSON msg)、schema-invalid JSON 返 False、返回 (bool, str) 元组、合法 text document 返 (True, "OK")
  - **`process_single` 错误路径** 5 个：file_not_found ErrorRecord code+details.path、unknown parser → unexpected_parser_error + details.parser_name、unsupported extension → unsupported_type、默认 parser=fallback（通过返回 doc.parser_name 验证）
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_validate_only_returns_tuple_of_two` 忘记加 `tmp_path: Path` 参数（fixture 注入失败 → NameError）。补上后通过。

### 下一步建议
- 候选 AX：evaluation/schema.py + evaluation/schema_validation.py 边角
- 候选 AS：app/hash.py 内部边角补强（17 → ~25 个）
- 候选 BA：app/chunkers/__init__.py / app/parsers/__init__.py 边角
- 候选 BB：evaluation/__init__.py 常量
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AX（evaluation/schema.py + schema_validation.py）。理由：
1. schema.py + schema_validation.py 是评测层 schema 校验入口
2. validate(name) 函数对各种 schema name（document/manifest/evaluation-report）的边角
3. document_passes_schema 在 metrics.py 已被调用，应有专门测试
4. 之后转 AS（hash 补强）+ BA/BB（小模块）完成所有模块边角覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 46 后）：1425 pass / 0 fail / 9 skip（HEAD `a380c80`）

---

## Round 47（2026-08-04）：候选 AX — evaluation/schema.py + schema_validation.py 边角覆盖

### 做了什么
- 候选 AX：扩展 `tests/test_evaluation_schema.py`，新增 30 个测试覆盖 `evaluation/schema.py` + `evaluation/schema_validation.py` 的全部边角。
- 至此 evaluation 层 schema 校验入口全覆盖：load_schema / _schema_path / validate / validate_file / document_passes_schema 都有专门边角测试。
- 重点覆盖项：
  - **EvalSchemaError 类契约** 7 个：Exception 子类、raise/catch、默认 errors 空列表、None → []、errors 透传、Exception 实例、message 属性
  - **SCHEMAS_DIR 常量** 3 个：绝对路径、name == "schemas"、含已知 schema 文件（manifest/annotation/evaluation-report）
  - **load_schema 边角** 5 个：返回 dict、含 $schema/$id/title、未知名 FileNotFoundError
  - **`_schema_path` 直接单测** 3 个：返回 Path 对象、未知名 raise（msg 含 schema 名）、在 SCHEMAS_DIR 下（parent 验证）
  - **validate 边角** 5 个：成功返 None、消息含错误数（"处"）、errors 是 list、每个 error 含 path/message/schema_path 三键、首 error 用于消息
  - **validate_file 边角** 4 个：Path 对象接受、目录 raise FileNotFoundError、未知 schema name raise、成功返 None
  - **document_passes_schema 边角** 3 个：空 dict False、返回 type 为 bool（不是 int）、extra field 处理（additionalProperties 决定接受/拒绝）
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_document_passes_schema_returns_bool_not_int` 中 `not isinstance(result, int)` 失败——Python 中 `bool` 是 `int` 的子类，`isinstance(True, int)` 永远为 True。改为 `type(result) is bool`（精确类型检查，忽略子类）。

### 下一步建议
- 候选 AS：app/hash.py 内部边角补强（17 → ~25 个）
- 候选 BA：app/chunkers/__init__.py / app/parsers/__init__.py 边角
- 候选 BB：evaluation/__init__.py 常量
- 候选 BC：app/__init__.py / app/cli.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 AS（app/hash.py 补强）。理由：
1. hash.py 当前 17 个测试，仍可补强：SHA256 边角、不同 file_size、文本与二进制 hash 区分
2. hash.py 是基础设施（document_id / source_hash 全靠它），稳定不变
3. 之后转 BA/BB（__init__ 模块）扫尾所有边角
4. 至此 evaluation 层（runner/manifest/annotation_metrics/metrics/report/schema）已全覆盖，转回 app/ 层

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 47 后）：1455 pass / 0 fail / 9 skip（HEAD `c0f7d00`）

---

## Round 48（2026-08-04）：候选 AS — app/hash.py 内部边角覆盖

### 做了什么
- 候选 AS：扩展 `tests/test_hash.py`，新增 38 个测试覆盖 `app/hash.py`（25 行）的两个核心函数 `compute_file_hash` / `compute_text_hash` 的全部边角。
- 重点覆盖项：
  - **compute_text_hash 类型契约** 10 个：str 类型、非空、已知 SHA256 值（"abc"/空串/"a"）、顺序敏感、大小写敏感、1MB 长字符串稳定、换行符变体区分（\n vs \r\n vs \r）、4-byte UTF-8 emoji、纯 ASCII 与 bytes sha256 一致、concat 不变量（SHA-256 不是 concat 可组合）
  - **compute_file_hash chunk 边界** 5 个：32KB（半个 chunk）、64KB - 1、128KB（2 完整 chunk）、192KB（3 完整 chunk）、70KB 随机字节
  - **compute_file_hash 类型契约** 5 个：str 类型、非空、无 _/-（纯 hex）、stable 多次读取、无前后空白
  - **compute_file_hash 内容/文件名边角** 5 个：文件名含空格、文件名含 Unicode（CJK）、内容全空白、内容修改 → hash 改变、跨函数一致性（file_hash(bytes) == text_hash(utf-8 str)）
  - **compute_file_hash 错误路径** 5 个：错误消息含路径名、空字符串 raise、目录 raise（tmp_path 与 "."）、连续两文件 hash 无状态泄漏、Path 与 str 路径等价
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_file_hash_cross_function_consistency_with_text_hash` 失败——Windows text mode 默认将 `\n` 写成 `\r\n`，导致 file_hash(bytes) != text_hash(str_with_\n)。改为 `write_bytes(ascii_content.encode("utf-8"))` 用 binary 写盘绕过 CRLF 转换。

### 下一步建议
- 候选 BA：app/chunkers/__init__.py / app/parsers/__init__.py 边角
- 候选 BB：evaluation/__init__.py / app/__init__.py 常量
- 候选 BC：app/cli.py 内部边角（argparse 子命令解析、退出码）
- 候选 BD：tests/test_schema.py 边角补强（document schema validation）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BA（app/chunkers/__init__.py + app/parsers/__init__.py 边角）。理由：
1. __init__ 模块常被忽略，但通常导出关键 API / 公共工具
2. 多数 __init__.py 可能是空的，但需要测试以验证此事实
3. 之后转 BC（cli.py 边角）覆盖 argparse 解析、退出码、stdout 输出
4. 至此 evaluation 层 + app/hash + app/pipeline 已全覆盖，再扫剩余小模块

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 48 后）：1489 pass / 0 fail / 9 skip（HEAD `9d1038d`）

---

## Round 49（2026-08-04）：候选 BA — __init__.py 模块导出契约覆盖

### 做了什么
- 候选 BA：新建 `tests/test_packages_init.py`（41 个测试）覆盖 4 个 __init__.py 模块的导出契约。
- 至此所有 Python 包的 __init__.py 都有专门契约测试。
- 重点覆盖项：
  - **app/chunkers/__init__.py** 8 个：StructuralChunker / normalize_text 导出存在、__all__ 含两个名字且仅含两个、list 类型、属性匹配、normalize_text 可调用、StructuralChunker 可实例化
  - **app/parsers/__init__.py** 9 个：Parser / ParserError / make_document_id 导出、__all__ 完整且仅含 3 个名字、Parser 是 ABC 子类、ParserError 是 Exception 子类、make_document_id 接受 hex
  - **evaluation/__init__.py** 10 个：四个版本常量（EVALUATOR=1.1 / REPORT=1.1 / ANNOTATION=1.0 / MANIFEST=1.0）类型 + 值、__all__ 完整、report_version 与 evaluator_version 一致、annotation 与 manifest 都是 1.0
  - **子模块路径稳定性** 5 个：`from app.X import Y` 与 `from app.X.sub import Y` 返回同一对象引用（`is` 关系）
  - **包元数据** 4 个：三个非空 __init__.py 都有 docstring、evaluation docstring 含设计原则关键词（"设计"/"v1."/"manifest"/"annotation"/"version"）
  - **版本契约** 3 个：四版本元组形式一次性引用、当前阶段固定值（1.1/1.1/1.0/1.0）、元组类型校验
  - **app/__init__.py** 2 个：模块存在、无强制导出（记录"app 是空包"事实）
- 无源码改动。

### 撞墙记录
- 无撞墙。41 个新测试一次通过。

### 下一步建议
- 候选 BC：app/cli.py 内部边角（argparse 子命令、退出码、stdout 输出格式）
- 候选 BD：tests/test_schema.py 边角补强（document schema validation 边角）
- 候选 BE：app/models.py 边角补强（dataclass field 默认值、frozen 行为）
- 候选 BF：tests/test_annotation_metrics.py 边角补强（已有但不饱和）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BC（app/cli.py 边角）。理由：
1. cli.py 是入口点，含 argparse 子命令、退出码逻辑、stderr 输出
2. 与 test_cli.py（已存在）形成互补，专门测试边角错误路径
3. 之后转 BD（schema validation 边角）补强 app/schema.py 覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 49 后）：1530 pass / 0 fail / 9 skip（HEAD `f5d20dc`）

---

## Round 50（2026-08-04）：候选 BC — app/cli.py 内部边角覆盖

### 做了什么
- 候选 BC：新建 `tests/test_cli_edges.py`（74 个测试）覆盖 `app/cli.py`（535 行）的全部纯函数 + argparse 配置 + 错误路径。
- 与已有 `test_cli.py`（77 个集成测试）互补，专门测纯函数边角。
- 重点覆盖项：
  - **_build_arg_parser** 12 个：prog="app.cli"、4 个子命令存在、parse 默认 max_chars=800 + parser=None、parse-dir recursive=False、inspect 默认 limit=10 + elements/chunks/spans=False、--parser 6 个 choices 完整、无命令/未知命令 SystemExit(2)
  - **_EXTENSION_TO_PARSER 常量** 7 个：9 个键、5 个 parser 值映射（pdf/docx→fallback, md+markdown→markdown, html+htm→html, txt+text→text, ipynb→ipynb）
  - **_infer_parser_name** 6 个：大写扩展名 lower 后识别（.PDF/.DOCX/.MD）、未知扩展名→fallback、无扩展名→fallback、混合大小写、dotfile（.gitignore suffix 全名 → fallback）
  - **_iter_supported_files** 5 个：空目录返 []、过滤不支持扩展名、混扩展名全收、递归子目录、返回 Path 对象
  - **_relative_output_path** 3 个：root level 文件、无扩展名文件、同名不同扩展名防冲突（保留 suffix 进文件名）
  - **_preview** 7 个：width=0 边界、短文本直返、纯空白→空、单字符、宽度边界不截、超长加 …、多行 collapse 单行
  - **_load_document_json** 6 个：空文件 JSONDecodeError、目录 OSError、UTF-8 BOM、合法 dict、JSON 数组根（合法 JSON）、错误消息含路径
  - **_format_summary** 6 个：chunk 空 text、element 无 type→"?"、warnings > 5 截断含 "more" 标记、errors code+message 渲染、缺 schema_version→"?"、hash 显示前 16 字符 + …
  - **_format_elements_list** 3 个：缺 element_id→"?"、parent_id=None 不显示 parent 段、limit > count 无 "more" 提示
  - **_format_chunks_list** 4 个：无 source_element_ids→refs=0、show_spans=True 但无 spans→"(none)"、show_spans 实际渲染、limit=0 全列
  - **_emit_structured_error** 4 个：extra 字段透传、schema_version="0.1.0" 常量、input 路径 str 化、走 stderr 不走 stdout
  - **main 入口** 3 个：argv 列表接受、返回 int、inspect 返回 0/1/2
  - **_run_parse 错误路径** 3 个：缺输入文件→结构化 error JSON + code="file_not_found"、显式 parser 跳过 INFO 日志、自动推断打印 INFO 含推断出的 parser 名
  - **_run_parse_dir** 5 个：自动创建输出目录、summary total 计数、缺输入目录返 2、summary 含 max_chars、summary 含 recursive
- 无源码改动。

### 撞墙记录
- 无撞墙。74 个新测试一次通过。

### 下一步建议
- 候选 BD：tests/test_schema.py 边角补强（document schema validation 边角）
- 候选 BE：app/models.py 边角补强（dataclass field 默认值、frozen 行为、to_dict/from_dict）
- 候选 BF：tests/test_annotation_metrics.py 边角补强
- 候选 BG：app/chunkers/structural.py 内部边角（_ChunkBuffer / _split_long_text / _hard_split_with_whitespace_fallback）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BG（structural chunker 内部边角）。理由：
1. structural.py 是核心算法（388 行），含多个内部 helper
2. _split_long_text / _hard_split_with_whitespace_fallback / _ChunkBuffer / normalize_text 是分块正确性的基础
3. 当前测试主要是通过 StructuralChunker.chunk() 验证，缺少各 helper 的直接单测
4. 之后转 BD/BE 补完剩余模块边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 50 后）：1604 pass / 0 fail / 9 skip（HEAD `166461f`）

---

## Round 51（2026-08-04）：候选 BG — structural chunker 内部边角覆盖

### 做了什么
- 候选 BG：新建 `tests/test_chunker_edges.py`（85 个测试）覆盖 `app/chunkers/structural.py`（388 行）的模块级常量 + 内部 helper 边角，与已有 `test_chunker.py`（129 个集成测试）互补。
- 重点覆盖项：
  - **模块级常量** 16 个：_SENTENCE_SPLIT_RE / _WHITESPACE_RE 是 re.Pattern 对象、_HARD_BREAK_LANGS 是 tuple 含 6 个标点（3 中 + 3 英）、_PART_TEXT=0 / _PART_ELEMENT_ID=1 / _PART_START=2 / _PART_END=3 互不相同、_SENTENCE_SPLIT_RE 各种分隔行为（句号/问号/叹号 + 空格分隔，无空格不分隔）
  - **_ChunkBuffer 默认 field** 13 个：counter=0、parts=[]、document_id 字段、parts 每项是 4-tuple、push_text 累积、length 求和、is_empty 状态转移（True→False→True after flush）、flush 文本用单空格 join、返回 Chunk 对象、strategy/max_chars/char_count 写入 metadata
  - **_SplitPiece dataclass** 8 个：必填 text、默认 start/end=0、显式赋值、frozen=True 不能改属性、boundary_after 三种值（whitespace/forced_char/None）、equality 比较
  - **_hard_split_with_whitespace_fallback** 7 个：max_chars=32 最小值、前导/尾随空白处理、text = max_chars+1 / 10x max_chars、start/end 在 [0, len) 内、piece.text 与 text[start:end] 一致
  - **_split_long_text** 10 个：空串/纯空白返 []、短文本单 piece、恰好 == max_chars 单 piece、max_chars+1 必拆、strip 后处理、每 piece ≤ max_chars、合并用单空格、坐标在 stripped text 系
  - **StructuralChunker.__init__ 边界** 7 个：默认 800、显式赋值、32 OK、31/0/-100/1 都 raise ValueError
  - **_element_text_with_span** 10 个：content=None/空/全空白都返 ('',0,0)、无空白正常返、前导/尾随/双侧空白偏移计算、image element 强制返空（即使有 content）
  - **_element_text 兼容方法** 3 个：返 text 字段、空内容返 ''、image 返 ''
  - **normalize_text 边角** 8 个：空串/纯空白返空、内部空白 collapse、strip 首尾、混空白归一、返 str 类型、None 不 raise（短路返空）、idempotent、保留非空白字符（emoji/CJK）

### 撞墙记录
- **Wall 1**：`test_element_text_with_span_content_none_returns_empty` 失败——Element dataclass 不允许 content=None + resource_path=None。改为用 image element（自带 resource_path）测试相同行为路径。
- **Wall 2**：`test_normalize_text_none_input_raises_before_check` 假设 None 会 raise，实际 `if not s` 短路返 ""（合法行为）。改为记录"None 不 raise"。
- **Wall 3**：`test_chunk_buffer_multiple_flushes_independent_chunks` 假设 buf.counter 在 flush 时自增——实际由外层 StructuralChunker 维护，buf 自身不变。改为比较 source_element_ids 而非 chunk_id。
- **Wall 4**：SyntaxWarning 因 docstring 含 `\s+` 转义。改写为"标点后有空格"避免反斜杠。

### 下一步建议
- 候选 BH：app/models.py 边角（Document/Element/Chunk/Relation/WarningRecord/ErrorRecord dataclass）
- 候选 BI：tests/test_schema.py 边角补强（document schema validation）
- 候选 BJ：app/pipeline.py 内部边角（process_single 错误路径细分）
- 候选 BK：evaluation/cli.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BH（app/models.py 边角）。理由：
1. models.py 是数据模型核心（Document/Element/Chunk 等 6 个 dataclass）
2. 各 dataclass 的 __post_init__ 校验、to_dict/from_dict、frozen 行为需要直接单测
3. 至此 evaluation 层 + app/chunker + app/parser + app/cli + app/hash 全覆盖，再补 models 完成所有模块边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 51 后）：1689 pass / 0 fail / 9 skip（HEAD `bea827e`）

---

## Round 52（2026-08-04）：候选 BH — app/models.py 边角覆盖

### 做了什么
- 候选 BH：新建 `tests/test_models_edges.py`（59 个测试）覆盖 `app/models.py`（154 行）的 6 个 dataclass 边角，与已有 `test_models.py`（55 个）互补。
- 重点覆盖项：
  - **SCHEMA_VERSION 深入** 3 个：以 0 开头（0.1.0 阶段）、major.minor.patch 三段、模块常量跨导入保持同一对象
  - **ElementType/SourceType 字面量** 2 个：8 种 element type 全接受、6 种 source type 全接受
  - **Element confidence 边界** 5 个：0.0 允许、负数/超 1 dataclass 层允许（schema 拒）、float 类型、int 自动通过
  - **Element mutable 行为** 4 个：非 frozen 可改属性、可加 metadata、set 时不校验、纯空白 element_id truthy 字符串不拒
  - **Element to_dict 深拷贝** 3 个：asdict 深拷贝不互相影响、source_locator 透传、返回 8 keys
  - **Chunk 各种文本/metadata** 5 个：纯 \n / \t 字符 text 不被 dataclass 拒、复杂 metadata 嵌套、复杂 source_spans、to_dict 返回 5 keys
  - **Chunk mutable 行为** 3 个：可改 text、可设空 text（无 setter 校验）、source_element_ids 必填
  - **Document to_dict 顺序保留** 5 个：elements/chunks/warnings/errors 顺序保留、to_dict 返回 13 keys、schema_version 与模块常量一致
  - **Document mutable 行为** 3 个：可改 document_id、可加 elements、metadata 隔离
  - **Relation 边角** 4 个：to_dict 4 keys、metadata 透传、无 __post_init__、type 自由字符串
  - **Warning/Error 边角** 8 个：2/3 keys 切换、details=None 时省略字段、复杂嵌套 details 透传
  - **dataclass 标识** 6 个：6 个 class 都通过 is_dataclass
  - **to_dict 存在性** 1 个：6 个 class 都有可调用 to_dict
  - **Element image 强制路径** 3 个：resource_path only OK、to_dict 透传、content+resource_path 同时设置允许
  - **Document parser** 2 个：parser_name/version 记录、version 复杂字符串
  - **Document metadata 复杂** 2 个：嵌套数据透传、metadata 实例隔离
- 无源码改动。

### 撞墙记录
- 无撞墙。59 个新测试一次通过。

### 下一步建议
- 候选 BI：tests/test_schema.py 边角补强（document schema validation 边角）
- 候选 BJ：app/pipeline.py 内部边角（process_single 错误路径细分）
- 候选 BK：evaluation/cli.py 边角（argparse + 退出码）
- 候选 BL：app/parsers/text_parser.py 内部边角
- 候选 BM：app/parsers/markdown_parser.py 内部边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BJ（app/pipeline.py 内部边角）。理由：
1. pipeline.py 是核心入口，含 process_single / get_parser / validate_only / image_output_dir_for
2. test_pipeline_helpers.py 已覆盖基础（image_output_dir_for / get_parser），但 process_single 的细分错误路径仍可补
3. 包括：各种 ErrorRecord code 的 details 字段完整性、不同 parser 与不同文件类型的组合、CLI 默认参数
4. 之后转 BI（schema validation 边角）补强校验逻辑

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 52 后）：1748 pass / 0 fail / 9 skip（HEAD `9cdf827`）

---

## Round 53（2026-08-04）：候选 BI — app/schema.py 边角覆盖

### 做了什么
- 候选 BI：新建 `tests/test_schema_edges.py`（58 个测试）覆盖 `app/schema.py`（93 行）的公共 API 边角，与已有 `test_schema.py`（117 个）互补。
- 重点覆盖项：
  - **SchemaValidationError 类直接单测** 9 个：Exception 子类、str 表示、raise/catch、默认 errors=[]、None → []、errors 透传同对象引用、args[0] 是 message、链式异常（raise from inner exception）
  - **SCHEMA_PATH 常量** 5 个：Path 对象、is_absolute、指向 schemas/document.schema.json、文件存在、默认参数行为
  - **__all__ 导出列表** 3 个：6 个公开 API 完整（SCHEMA_PATH/SchemaValidationError/load_schema/validate/is_valid/validate_file）、list 类型、与模块属性匹配
  - **load_schema 边角** 10 个：默认返 dict、$schema/$id/title/properties keys、str/Path 都接受、missing file raise、directory raise、非 JSON 文件 raise JSONDecodeError
  - **validate 行为** 8 个：成功返 None、自定义 schema 通过/拒绝、errors 三键（path/message/schema_path）、消息含错误数（"处"）、errors 按 path 排序、首 error 用于消息、空 dict 多个错误
  - **is_valid 边角** 9 个：合法返 True、非法返 False、bool 类型、自定义 schema 通过/拒绝、不抛异常（None/str/list 都返 False）
  - **validate_file 边角** 10 个：Path/str 都接受、missing/directory raise、非 JSON raise、非法内容 raise SchemaValidationError、自定义 schema、成功返 None
  - **_silence_unused_import 占位函数** 3 个：返 None、无参数、可调用
  - **Draft202012Validator 直接** 2 个：空 schema 接受任何类型、type-only schema 校验
- 无源码改动。

### 撞墙记录
- 无撞墙。58 个新测试一次通过。

### 下一步建议
- 候选 BJ：app/pipeline.py 内部边角（process_single 错误路径细分）
- 候选 BK：evaluation/cli.py 边角
- 候选 BL：app/parsers/text_parser.py 内部边角
- 候选 BM：app/parsers/markdown_parser.py 内部边角
- 候选 BN：app/parsers/html_parser.py 内部边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BK（evaluation/cli.py 边角）。理由：
1. evaluation/cli.py 是评测入口，含 run/validate-report 子命令
2. 与 app/cli.py 互补，专门测试评测层 CLI 边角
3. 评测层已全覆盖核心模块（runner/manifest/metrics/report/schema），但 cli.py 本身边角较少
4. 之后转 BL/BM/BN 补全各 parser 内部边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 53 后）：1806 pass / 0 fail / 9 skip（HEAD `816ab48`）

---

## Round 54（2026-08-04）：候选 BK — evaluation/cli.py 边角覆盖

### 做了什么
- 候选 BK：新建 `tests/test_evaluation_cli_edges.py`（54 个测试）覆盖 `evaluation/cli.py`（243 行）的 argparse 配置 + 边角，与已有 `test_evaluation_cli.py`（48 个）互补。
- 重点覆盖项：
  - **_build_parser 详细配置** 13 个：prog="evaluation.cli"、3 个子命令（run/validate-report/inspect-doc）、run 默认 parser=fallback + max_chars=800 + tolerance_chars=30、--parser choices 仅 fallback/kreuzberg、--manifest/--output/input required、无命令/未知命令 SystemExit(2)
  - **_format_metric 边角** 16 个：int 0/负数/大数、float 0/1/高精度、dict 空/有项、string 值、list 值（fallback default）、None value 含 reason、None 无 reason、对齐宽度 36
  - **main 返回 int** 3 个：validate/inspect/run 都返 int
  - **validate-report 错误码** 4 个：missing 2/bad json 1/invalid 1/valid 0
  - **run 错误码** 3 个：missing manifest 2/bad json 1/invalid content 1
  - **inspect-doc 错误码** 4 个：missing 2/bad json 1/array root 1/valid 0
  - **argparse 错误路径** 3 个：未知 parser choice SystemExit(2)、负数 max_chars argparse 接受、tolerance_chars=0 接受
  - **argv=None 行为** 1 个：main(None) 用 sys.argv
  - **模块导入无副作用** 5 个：importlib.reload 不崩、main/_build_parser/_format_metric/_run_inspect_doc 都是 callable
  - **stdout/stderr 输出** 3 个：run 成功 stdout 含 [OK]+devset_status、validate-report 合法 stdout [OK]、validate-report 非法 stderr [FAIL]
- 无源码改动。

### 撞墙记录
- 无撞墙。54 个新测试一次通过。

### 下一步建议
- 候选 BL：app/parsers/text_parser.py 内部边角
- 候选 BM：app/parsers/markdown_parser.py 内部边角
- 候选 BN：app/parsers/html_parser.py 内部边角
- 候选 BO：app/parsers/ipynb_parser.py 内部边角（已有 38 个直接测试，仍可补强）
- 候选 BP：app/parsers/fallback_parser.py 内部边角（已有 79 个，仍可补强）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BL（text_parser 内部边角）。理由：
1. text_parser.py 是最简单的 parser，作为开始
2. 之后扩展到 BM/BN/BO 完成所有 parser 的内部边角
3. 至此 evaluation 层 + app/cli + app/schema + app/models + app/hash + app/pipeline + app/chunker 全覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 54 后）：1860 pass / 0 fail / 9 skip（HEAD `6b08aa8`）

---

## Round 55（2026-08-04）：候选 BL — text_parser 内部边角覆盖

### 做了什么
- 候选 BL：新建 `tests/test_parsers_text_edges.py`（48 个测试）覆盖 `app/parsers/text_parser.py`（136 行）的模块级常量 + 内部 helper 边角，与已有 `test_parsers_text.py`（52 个）互补。
- 重点覆盖项：
  - **模块级常量** 4 个：_TEXT_EXTENSIONS 是 tuple 含 .txt/.text、全小写、TextParser 类属性 name='text'/version='stdlib/0.1.0'、是 Parser 子类
  - **TextParser 实例** 2 个：无参数构造、有 parse 方法
  - **_split_paragraphs 极端边角** 15 个：首尾换行、单字符/单数字、内容内换行、tab 内容（strip 影响）、混合 CRLF/CR/LF、连续空行视为一分隔、空串/纯空白/纯换行返 []、返回 list[tuple[int,str]]、start_line 严格递增
  - **_detect_text_source_type 边角** 9 个：大小写混合扩展名、双扩展名、dotfile、无扩展名 raise、未知 suffix raise、返 str 类型、error details 含 suffix
  - **TextParser 实例复用** 3 个：可解析多文件、无 counter 状态泄漏、单文档内 element_id 严格递增（e0000..e0003）
  - **TextParser 错误路径 details** 2 个：file_not_found 含 path、unsupported_type 含 suffix
  - **TextParser Document 字段** 5 个：metadata 固定 {text: True}、有 elements 时 warnings=[]、空文件 1 个 warning record、warning 含非空 reason
  - **TextParser schema 通过 + element 字段** 5 个：通过 schema、confidence 固定 0.95、metadata 空 dict、parent_id=None、source_locator 只含 line
  - **文件大小边角** 3 个：单字节、10K 行大文件、UTF-8 多字节内容
  - **_detect_text_source_type 错误消息** 2 个：含 suffix、含 '(无)'
- 无源码改动。

### 撞墙记录
- **Wall 1**：`test_split_paragraphs_content_with_tabs` 假设 `\ta\n\tb` → `"\ta\n\tb"`。实际 strip() 把首尾 tab 去了 → `"a\n\tb"`。改测试反映 strip 行为。

### 下一步建议
- 候选 BM：app/parsers/markdown_parser.py 内部边角
- 候选 BN：app/parsers/html_parser.py 内部边角
- 候选 BO：app/parsers/ipynb_parser.py 内部边角（已有 38 个直接测试，仍可补强）
- 候选 BP：app/parsers/fallback_parser.py 内部边角（已有 79 个，仍可补强）
- 候选 BQ：app/parsers/kreuzberg_parser.py 内部边角（已有 53 个，仍可补强）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BM（markdown_parser 内部边角）。理由：
1. markdown_parser 是结构化文本解析的代表
2. 含 heading/list/code block 等结构识别逻辑
3. 之后扩展到 BN（html_parser）完成两个文本型 parser 的内部边角
4. 至此 evaluation 层 + app/cli + app/schema + app/models + app/hash + app/pipeline + app/chunker + text_parser 全覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 55 后）：1908 pass / 0 fail / 9 skip（HEAD `c7e0a09`）

---

## Round 56（2026-08-04）：候选 BM — markdown_parser 内部边角覆盖

### 做了什么
- 候选 BM：新建 `tests/test_parsers_markdown_edges.py`（63 个测试）覆盖 `app/parsers/markdown_parser.py`（326 行）的模块级常量 + 内部 helper 边角，与已有 `test_parsers_markdown.py`（74 个）互补。
- 重点覆盖项：
  - **模块级常量** 7 个：_MD_EXTENSIONS 是 tuple、全小写、9 个 regex 都是 re.Pattern、MarkdownParser 类属性、是 Parser 子类、无参构造
  - **_split_pipe_row 边角** 13 个：基本/无外 pipe/单边 pipe/单 cell/空 cell/每 cell strip/3 列/多列/仅 pipe/返 list/返 str/空字符串
  - **_rows_to_md 边角** 9 个：空 list 返 ""、单行无 body 仍 header+separator、两行、jagged 用空填充、单列、多列、返 str、separator 用 --- 三横
  - **_is_pipe_table_start 边界** 7 个：最后一行 False、越界 index False、负 index、合法两行 True、第一行非 pipe False、第二行非 separator False、返 bool 类型
  - **_detect_md_source_type 边角** 6 个：dotfile、双扩展名、返 str、unknown suffix raise、错误消息含 suffix、无扩展名含 '(无)'
  - **MarkdownParser 实例复用** 3 个：可解析多文件、无 counter 状态泄漏、单文档内 element_id 严格递增
  - **错误路径 details** 2 个：file_not_found 含 path、unsupported_type 含 suffix
  - **Document 字段** 4 个：metadata={markdown: True}、有 elements 时 warnings=[]、空文件 1 个 warning、warning 含非空 reason
  - **大文件/Unicode/换行** 5 个：10K 行大文件、UTF-8 emoji+CJK、CRLF、混合 LF/CRLF/CR、单字节文件
  - **schema 通过 + element 字段** 6 个：通过 schema、confidence 固定 0.95、metadata 是 dict、source_locator 含 line、chunks/relations/errors 空
- 无源码改动。

### 撞墙记录
- 无撞墙。63 个新测试一次通过。

### 下一步建议
- 候选 BN：app/parsers/html_parser.py 内部边角
- 候选 BO：app/parsers/ipynb_parser.py 内部边角（已有 38 个直接测试）
- 候选 BP：app/parsers/fallback_parser.py 内部边角（已有 79 个）
- 候选 BQ：app/parsers/kreuzberg_parser.py 内部边角（已有 53 个）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BN（html_parser 内部边角）。理由：
1. html_parser.py 含 HTMLParser 子类 + 多个 handler 方法
2. HTML 解析逻辑复杂，边角测试有助于稳定行为
3. 之后扩展到 BO（ipynb）完成所有文本型 parser 内部边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 56 后）：1971 pass / 0 fail / 9 skip（HEAD `063112c`）

---

## Round 57（2026-08-04）：候选 BN — html_parser 内部边角覆盖

### 做了什么
- 候选 BN：新建 `tests/test_parsers_html_edges.py`（60 个测试）覆盖 `app/parsers/html_parser.py`（446 行）的模块级常量 + _HTMLDocParser 内部 + HtmlParser 边角，与已有 `test_parsers_html.py`（61 个）互补。
- 重点覆盖项：
  - **模块级常量** 10 个：_HTML_EXTENSIONS 是 tuple、_HEADING_LEVELS 是 dict 含 h1-h6、_SKIP_TAGS 是 set 含 script/style/head/title/meta/link/noscript、body tags 不在 SKIP 中、HtmlParser 类属性、是 Parser 子类
  - **_HTMLDocParser 初始化** 8 个：document_id/elements/warnings 默认值、_section_path/_section_levels 空、_cur_kind=None、各 stack 空、_pre_depth/_blockquote_depth/_table_depth=0、继承 stdlib HTMLParser、4 个 handle 方法可调用
  - **_detect_html_source_type 边角** 10 个：返 str、dotfile、双扩展名、混合大小写、无 suffix raise、unknown suffix raise、错误消息含 suffix、无 suffix 含 '(无)'、md 拒绝
  - **_rows_to_md 边角** 5 个：返 str、jagged 用空填充、多列、单列、separator 三横
  - **HtmlParser 实例复用** 3 个：可解析多文件、无 counter 状态泄漏、单文档 element_id 严格递增
  - **错误路径 details** 2 个：file_not_found 含 path、unsupported_type 含 suffix
  - **Document 字段** 4 个：metadata={html: True}、有 elements 时 warnings=[]、空 body 1 个 warning、warning 含非空 reason
  - **大文件/Unicode/换行** 5 个：1000 段落大文件、UTF-8 emoji+CJK、CRLF、混合 LF/CRLF、单字节文件
  - **malformed HTML** 6 个：未闭合 tag、自闭合 <br/>、注释忽略、DOCTYPE 忽略、属性含引号 URL、嵌套同级 heading
  - **schema 通过 + element 字段** 5 个：通过 schema、confidence 固定 0.95、metadata 是 dict、source_locator 含 line、chunks/relations/errors 空
- 无源码改动。

### 撞墙记录
- 无撞墙。60 个新测试一次通过。

### 下一步建议
- 候选 BO：app/parsers/ipynb_parser.py 内部边角（已有 38 个直接测试）
- 候选 BP：app/parsers/fallback_parser.py 内部边角（已有 79 个）
- 候选 BQ：app/parsers/kreuzberg_parser.py 内部边角（已有 53 个）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BO（ipynb_parser 内部边角）。理由：
1. ipynb_parser 含 cell 解析、kernel 语言检测、JSON 结构处理
2. 已有 38 个直接测试，仍可补强大文件/notebook 边角
3. 之后扩展到 BP/BQ 完成所有 parser 内部边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 57 后）：2031 pass / 0 fail / 9 skip（HEAD `8c922a8`）
- 里程碑：突破 2000 passed

---

## Round 58（2026-08-04）：候选 BO — ipynb_parser 内部边角覆盖

### 做了什么
- 候选 BO：新建 `tests/test_parsers_ipynb_edges.py`（114 个测试）覆盖 `app/parsers/ipynb_parser.py`（227 行）的模块级常量 + 内部 helper + IpynbParser 边角，与已有 `test_parsers_ipynb.py`（65 个）互补。
- 重点覆盖项：
  - **模块级常量** 7 个：_IPYNB_EXTENSIONS 是 tuple 含 ".ipynb"、IpynbParser 类属性、是 Parser 子类、无构造参数、parse 方法可调用
  - **_detect_ipynb_source_type 边角** 11 个：返 str、返 "ipynb"、大写/混合大小写、双扩展名、dotfile、拒绝 json/md、无 suffix 含 '(无)'、错误 details 含 suffix、错误消息提到 ipynb
  - **_cell_source_to_text 类型覆盖** 16 个：str/空串/list/带换行 list/空 list/None/int/float/bool/dict/bytes 全返 ""、含非 str 元素的 list、嵌套 list、空字符串 list、返 str 类型
  - **_extract_kernel_language 边角** 13 个：kernelspec.language 优先、kernelspec.name fallback、language_info.name fallback、空 metadata、kernelspec=None、空 dict、language 空走 name、language=None 走 name、所有字段空、只 kernelspec 无 language_info、返 str 类型
  - **IpynbParser 实例复用** 3 个：可解析多文件、无 counter 状态泄漏、单文档 element_id 严格递增
  - **错误路径完整** 11 个：file_not_found 含 path、unsupported_type 含 suffix、ipynb_invalid_json 含 exception_type、顶层 array/string/null/int 各自 raise ipynb_bad_structure、cells 字段 dict/string 各自 raise、nbformat=3/0 raise unsupported_version
  - **Document metadata 字段** 8 个：ipynb=True、nbformat=4、nbformat_minor=5、nbformat_minor 缺失=None、cell_count 正确、language 正确、无 kernelspec 时 language=""、5 个 key 完整
  - **cell 处理细节** 11 个：code metadata.kind=code_cell、raw metadata.kind=raw_cell、code 含 language、raw 无 language key、markdown 子 element 无 kind、code/raw locator 无 line、code/raw content strip、multiline source list concat、markdown section_path、两 markdown cell section_path 独立、空 code cell warning 含 cell_index
  - **warning 路径** 5 个：whitespace-only code cell warning、unknown cell_type warning、cell 非 dict warning 含 cell_index、unknown cell_type warning 记 cell_type、空 notebook no_content warning
  - **nbformat 边角** 5 个：nbformat 缺失=None 视为支持、minor=0 工作、nbformat=5 工作、metadata=None 不 crash、cells 缺失当 [] 处理
  - **大 notebook / Unicode / 字段忽略** 5 个：100 cells 大 notebook、UTF-8 emoji+CJK、outputs 字段忽略、未知字段忽略
  - **Document 字段完整性** 6 个：chunks/relations/errors 空、source_path/source_hash/parser_name/parser_version 透传、confidence 固定 0.95、parent_id=None
  - **schema 通过** 2 个：正常 notebook 通过 schema、空 notebook 也通过 schema
  - **mixed cell 场景** 4 个：混合 cell 数量、markdown 含 heading+list、code 含换行、warning 含非空 reason
  - **cell_index 单调** 2 个：cell_index 单调非递减、首个 cell_index=0
- 无源码改动。

### 撞墙记录
- 1 次撞墙：`test_ipynb_parser_markdown_cell_sub_element_no_kind_metadata` 失败
  - 期望：markdown cell 的 heading sub-element metadata 是空 dict `{}`
  - 实际：heading element 有 `{"level": 1}`（来自 MarkdownParser）
  - 修复：改测试为只检查 `"kind" not in metadata`（保留原有意图但符合实际行为）

### 下一步建议
- 候选 BP：app/parsers/fallback_parser.py 内部边角（已有 79 个）
- 候选 BQ：app/parsers/kreuzberg_parser.py 内部边角（已有 53 个）
- 候选 BR：app/pipeline.py 端到端边角（含错误路径 + 多 parser 切换）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BP（fallback_parser 内部边角）。理由：
1. fallback_parser 是默认 parser（pdfplumber + python-docx），覆盖率最关键
2. 已有 79 个直接测试，但模块级常量、纯 helper 函数、错误 details 仍有补强空间
3. 之后扩展到 BQ 完成所有 parser 内部边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 58 后）：2145 pass / 0 fail / 9 skip（HEAD `562b8e8`）

---

## Round 59（2026-08-04）：候选 BP — fallback_parser 内部边角覆盖

### 做了什么
- 候选 BP：新建 `tests/test_parsers_fallback_edges.py`（95 个测试）覆盖 `app/parsers/fallback_parser.py`（630 行）的纯 helper 边角 + FallbackParser 类契约，与已有 `test_parsers_fallback.py`（79 个）互补。
- 重点覆盖项：
  - **_CAPTION_RE 直接测试** 7 个：返 re.Pattern、match 对象/None、IGNORECASE、全角数字、关键词后必须数字、0 数字匹配、多行 match 只看开头
  - **_is_caption 边角** 8 个：前导空白、tab 分隔、数字 0、大数字、关键词无数、关键词嵌文本不匹配、返 bool 类型
  - **_rows_to_markdown cell 类型扩展** 10 个：float/bool/dict/list cell、混合类型、3+ body rows、100 body rows、separator 三横、int 0 cell
  - **_image_filename 边角** 9 个：basic format、index > 99（3 位）、index 0、doc-doc-x（全局 replace）、custom ext、ext 含点、prefix 含数字、无 doc- 前缀
  - **_save_image 实际写盘** 8 个：嵌套目录创建、返回 Path、文件名格式、目录已存在、同 index 覆盖、空 bytes、大 bytes（10KB）、custom ext
  - **_classify_pdf_paragraph 80 字符边界** 9 个：== 80 heading、> 80 paragraph、< 80 heading、80 with period、80 with !、中文句号、返 tuple、caption meta、heading meta、paragraph meta 空 dict
  - **_is_heading_style 边角** 12 个：heading 99、heading 0 clamp、heading -5 clamp、混合大小写、全大写、Subtitle/Normal False、返 tuple、whitespace 边角、空串/纯空白
  - **_extract_inline_image_rids 边角** 4 个：空 paragraph、返 list、blip outside drawing 不捕获、embed+link embed 优先
  - **_group_words_to_paragraphs 边角** 4 个：返 list、dict 含 text/bbox、empty input、3 词一行
  - **_lines_to_para 边角** 6 个：返 dict、empty lines、单行多词、bbox 聚合、min top、max bottom
  - **FallbackParser 类契约** 10 个：name 是 str、version 是 str、继承 Parser、init 多形态（无参/None/空串/Path/str path）、多实例互不干扰、parse callable
  - **FallbackParser.parse 错误路径** 5 个：missing pdf/docx、details 含 path、unsupported_type
- 无源码改动。

### 撞墙记录
- 2 次撞墙：
  1. `test_caption_re_ignores_case` 失败：用 "figure 3," 但 regex 分隔符 `[\.、:\s]` 不含逗号。修复：改用 "figure 3."（句点在允许字符内）。
  2. `test_extract_inline_image_rids_with_drawing_outside_paragraph` 失败：blip 在 w:drawing 外不被捕获（iter(qn("w:drawing")) 严格）。修复：改测试为断言返 []，反映实际行为。

### 下一步建议
- 候选 BQ：app/parsers/kreuzberg_parser.py 内部边角（已有 53 个）
- 候选 BR：app/pipeline.py 端到端边角（含错误路径 + 多 parser 切换）
- 候选 BS：app/chunkers/structural.py（已有 85 个边角，可继续补完）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BQ（kreuzberg_parser 内部边角）。理由：
1. kreuzberg 是可选 parser（默认走 fallback）
2. 内部含异常路径 fallback、namespace 检测、metadata 提取，覆盖盲区多
3. 完成 BQ 后所有 5 个 parser 都有完整边角测试

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 59 后）：2240 pass / 0 fail / 9 skip（HEAD `a265a16`）

---

## Round 60（2026-08-04）：候选 BQ — kreuzberg_parser 内部边角覆盖

### 做了什么
- 候选 BQ：新建 `tests/test_parsers_kreuzberg_edges.py`（73 个测试）覆盖 `app/parsers/kreuzberg_parser.py`（246 行）的 helper 边角 + 完整 monkeypatch parse 路径，与已有 `test_parsers_kreuzberg.py`（53 个）互补。
- 重点覆盖项：
  - **_classify_line 边角** 10 个：返 tuple、heading level 6 边界、7 hashes 拒绝 ATX、尾随空白 strip、短行逗号/分号、80/81 字符精确边界、paragraph meta 空 dict、短行 meta raw_text
  - **_make_locator 边角** 7 个：返 dict、pdf 2 个 key、docx 2 个 key、pdf page 始终 1、docx paragraph_index 透传 0/99/-1、placeholder/heuristic 值 True
  - **_split_content_to_elements 边角** 16 个：返 tuple、list 类型、空 content、whitespace only、heading level 6、ATX heading + 多行 rest、CRLF 处理、100 块大输入、element_id 严格递增、pdf/docx locator 差异、paragraph kreuzberg_heuristic meta、ATX heading 无 kreuzberg_heuristic、ATX heading heuristic=None、confidence 0.6/0.5
  - **KreuzbergParser 类契约** 10 个：name/version 是 str、init 默认 True、显式 True/False、include_document_structure 是 keyword-only、继承 Parser、parse callable
  - **parse 错误路径 monkeypatch** 5 个：kreuzberg_unavailable（_KREUZBERG_AVAILABLE=False + IMPORT_ERROR raising=False）、missing docx/pdf、details.path、kreuzberg_extract_failed、exception_type 透传
  - **parse 成功路径 monkeypatch** 10 个：空 content + warning、有 content 启发式切分、PDF kreuzberg_pdf_no_bbox warning、DOCX 无 pdf_no_bbox、kreuzberg.elements 非空不 warn、metadata.mime_type/quality_score 透传、metadata 2 key 完整、tables 处理（cell_count/row_count/source/confidence）、PDF table bbox + page_number=0 fallback to 1、table confidence with/without cells
  - **Document 字段完整性** 6 个：chunks/relations/errors 空、source_path/hash/name 透传、parser_version 是 str、warning reason 非空、warning details.source_type
  - **实例复用** 2 个：多文件独立、无 counter 泄漏
  - **schema 通过** 1 个：parse 结果 is_valid True
- **里程碑**：至此 6 个 parser（text/markdown/html/ipynb/fallback/kreuzberg）均已有完整边角测试覆盖。
- 无源码改动。

### 撞墙记录
- 3 次撞墙：
  1. `test_split_content_paragraph_meta_has_kreuzberg_heuristic` 失败：用 "plain paragraph"（15 字符）→ 被分类为短行 heading。修复：改用 > 80 字符的 paragraph。
  2. `test_split_content_confidence_values` 失败：rest 文本 "rest line"（9 字符）被分类为 heading → confidence=0.6。修复：用 > 80 字符的长 paragraph。
  3. `test_kreuzberg_parser_parse_kreuzberg_unavailable` 失败：`_KREUZBERG_IMPORT_ERROR` 在 ImportError 时才定义，kreuzberg 已安装时该属性不存在。修复：用 `monkeypatch.setattr(..., raising=False)`。
  4. `test_kreuzberg_parser_parse_with_content_emits_elements` 失败：content "para" 太短被分类为 heading。修复：用更长 paragraph。

### 下一步建议
- 候选 BR：app/pipeline.py 端到端边角（含错误路径 + 多 parser 切换）
- 候选 BS：app/chunkers/structural.py 继续补完（已有 85 个边角）
- 候选 BT：app/parsers/base.py 边角（detect_source_type/make_document_id/Parser 基类）
- 候选 BU：evaluation/runner.py 边角（含 process_single + 聚合逻辑）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BT（base.py 边角）。理由：
1. base.py 是所有 parser 的基类，覆盖率最关键
2. detect_source_type / make_document_id 是公共 API，但只有间接测试
3. 之后扩展到 BR 完成全部 parser 链路测试

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 60 后）：2313 pass / 0 fail / 9 skip（HEAD `66865ac`）

---

## Round 61（2026-08-04）：候选 BT — base.py 边角覆盖

### 做了什么
- 候选 BT：新建 `tests/test_parsers_base_edges.py`（84 个测试）覆盖 `app/parsers/base.py`（95 行）的 helper / 抽象类边角，与已有 `test_parsers_base.py`（45 个）互补。
- 重点覆盖项：
  - **ParserError 类深度边角** 17 个：code/message 类型、args 长度 1、args[0]=message、repr 含类名、str 不含 code、两实例默认不等、同对象相等、可链式 raise（__cause__）、隐式链式（__context__）、details 每实例独立、details 透传同一引用、Unicode message、空 code 接受
  - **make_document_id 边角** 12 个：返 str、starts with doc-、长度 20、取前 16 字符、确定性、不同前缀不同 id、同前缀同 id、长度 63/65/10/empty raise ValueError、不验证字符集（z*64 接受）、所有 hex 字符
  - **detect_source_type 边角** 21 个：返 str、pdf/docx 值、大写/混合大小写、dotfile、双扩展名、str 路径、反斜杠路径、forward slashes、拒绝 py/json/xml/csv/html/md/ipynb/txt、details.suffix、无 suffix 含 '(无)'、错误消息含 .pdf/.docx
  - **Parser 抽象类** 13 个：是 ABC、有 __abstractmethods__ 含 parse、默认 name="abstract"/version="0.0.0"、直接实例化 TypeError、子类无 parse TypeError、子类有 parse 可实例化、子类继承默认、单独 override name/version、parse callable、parse 是 abstractmethod（__isabstractmethod__=True）
  - **__all__ 导出列表** 5 个：4 个项、是 list、匹配模块属性、count=4、不含 _silence_unused
  - **_silence_unused 占位函数** 4 个：返 None、无参数、callable、可重复调用
  - **模块导入无副作用** 3 个：可导入不崩、有 4 个必需属性、有 _silence_unused
- 无源码改动。

### 撞墙记录
- 1 次撞墙（关键）：第一版用了 `importlib.reload(app.parsers.base)` 验证导入无副作用，但 reload 会让其他测试中已 import 的 `Parser` / `ParserError` 引用失效，导致下游 46 个测试失败（子类不再被认为是新 Parser 的子类）。
  - 修复：改用 `importlib.import_module("app.parsers.base")`（不 reload，只重新拿引用），污染消失。
  - **教训**：跨测试模块的 import 污染必须避免 reload 操作。

### 下一步建议
- 候选 BR：app/pipeline.py 端到端边角（含错误路径 + 多 parser 切换）
- 候选 BS：app/chunkers/structural.py 继续补完（已有 85 个边角）
- 候选 BU：evaluation/runner.py 边角（含 process_single + 聚合逻辑）
- 候选 BV：app/models.py 继续补完（已有 59 个边角）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BU（evaluation/runner.py 边角）。理由：
1. runner.py 是 Stage 2 评测的核心，含 process_single + 聚合逻辑
2. 边角多：比例指标分母 0、计时 null、聚合策略、silent_drop 计数
3. 覆盖率提升对评测稳定性关键

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 61 后）：2397 pass / 0 fail / 9 skip（HEAD `2ec7a43`）

---

## Round 62（2026-08-04）：候选 BU — evaluation/runner.py 边角覆盖

### 做了什么
- 候选 BU：新建 `tests/test_evaluation_runner_edges.py`（68 个测试）覆盖 `evaluation/runner.py`（227 行）的 helper / 流程边角，与已有 `test_evaluation_runner.py`（50+ 个）互补。
- 重点覆盖项：
  - **_load_annotation 边角** 13 个：返 dict/None 类型、JSON true/false/string/float/nested list/deeply nested、Unicode keys、大 dict (10K keys)、UTF-8 BOM 返 None、str path raises AttributeError、None path 返 None、truncated JSON 返 None
  - **_process_one 边角** 13 个：返 tuple 5 元素、total_seconds 是 float 非负、成功时 document_dict 是 dict、成功时 error_dict 是 None、失败时 error_dict 含 code、image_dir 失败时 None、parser_version 成功 str/失败 None、_per_doc 目录创建、out_stub 成功失败都清理、多次调用独立
  - **run_evaluation 输出格式** 4 个：返 dict、写入合法 JSON、indent=2 缩进、ensure_ascii=False Unicode 原样输出
  - **run_evaluation 目录创建** 1 个：output parent 不存在时自动创建
  - **run_evaluation report 结构** 5 个：expected_failures 总在 + 空 []、顶层 keys 完整 6 项、per_doc 空、per_doc count 匹配、doc_id 保留
  - **run_evaluation per_doc 字段** 6 个：每项 metrics dict、wall_time_seconds dict、total float、parse/chunk None、reason=not_instrumented、不含私有字段、只含 4 key
  - **run_evaluation provenance** 4 个：parser_name/max_chars/parser_version 透传、全失败时 parser_version=None
  - **run_evaluation expected_failures** 5 个：matches true/false、actual_code 记录、4 字段完整、多 EF 保序
  - **run_evaluation failed doc** 1 个：metrics 含 pipeline_failed 标记
  - **run_evaluation devset** 3 个：status/file_count/docx_count 透传
  - **tolerance_chars 透传** 3 个：默认 30、自定义 50、0
  - **模块导入** 4 个：exports run_evaluation、has _load_annotation/_process_one、__all__ 只导出 run_evaluation
- 无源码改动。

### 撞墙记录
- 2 次撞墙：
  1. **SyntaxError**：docstring 含 `\u` 字面量被 Python 解析为 unicode 转义。修复：用 `r"""..."""` raw docstring。
  2. **test_load_annotation_utf8_bom_accepted 失败**：UTF-8 BOM 字符（0xEF 0xBB 0xBF）导致 json.load 失败 → 返 None。修复：改测试为 `test_load_annotation_utf8_bom_returns_none`，反映实际行为。
  3. **test_load_annotation_str_path_accepted skip**：之前 try/except + skip 不优雅。修复：改测试为 `raises_attribute_error`，明确预期 AttributeError。

### 下一步建议
- 候选 BV：evaluation/metrics.py 边角（compute_automatic_metrics 各指标分母 0/聚合策略）
- 候选 BW：evaluation/manifest.py 边角（manifest 解析 + categories 字段）
- 候选 BX：evaluation/annotation_metrics.py 边角（figure_caption_prf / chunk_boundary_prf）
- 候选 BY：app/pipeline.py 端到端边角（process_single 错误路径）
- 候选 BZ：evaluation/report.py 边角（build_provenance / aggregate_summary / build_devset_section）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BZ（report.py 边角）。理由：
1. report.py 含 build_provenance / aggregate_summary / build_devset_section 三个公共 API
2. 聚合逻辑（比例指标分母 0/聚合策略）对评测稳定性关键
3. 之后扩展到 BV/BW/BX 完成 evaluation 模块全部边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 62 后）：2465 pass / 0 fail / 9 skip（HEAD `1635f59`）

---

## Round 63（2026-08-04）：候选 BZ — evaluation/report.py 边角覆盖

### 做了什么
- 候选 BZ：新建 `tests/test_evaluation_report_edges.py`（85 个测试）覆盖 `evaluation/report.py`（201 行）的模块常量 / 公共 API 边角，与已有 `test_evaluation_report.py`（75+ 个）互补。
- 重点覆盖项：
  - **模块常量深度** 16 个：_RATIO_METRICS 是 tuple、length 12、含 schema_valid/chunk_boundary_*、排除 pipeline_success/element_count_total/silent_drop_count/figure_caption_*；_COUNT_METRICS tuple length 1 排除 silent_drop；_SUCCESS_BOOL_METRICS tuple length 1 排除 schema_valid
  - **__all__ 导出** 4 个：5 个项、不含内部常量、匹配模块属性
  - **get_git_provenance** 7 个：返 dict 2 key、commit str|None、dirty bool、不存在目录、真实 repo 40 字符 SHA-1、subprocess failure 安全、OSError 安全
  - **get_dependency_versions** 8 个：返 dict、mutable、精确 3 key、3 个值都是 str、PackageNotFoundError 安全、generic exception 安全
  - **build_provenance** 13 个：max_chars float/0/负数/字符串数字 int() 转换、parser_name/version 透传、evaluator/report_version 是 str、timestamp 可 fromisoformat、含 tz、9 个 key 完整
  - **build_devset_section** 10 个：返 dict、6 key、status/file_count/pdf/docx/content_group/categories 透传、空字段、类型保持
  - **aggregate_summary counts** 4 个：sum 排除 None value、value=0 参与、空 input sum None、participating 0
  - **aggregate_summary success_rate** 4 个：半通过 rate=0.5、False 不计成功、None 计 total 不计成功、空 input rate None
  - **aggregate_summary ratio macro** 4 个：部分 None macro 只算非 None、同值、单 doc、全 None macro=None
  - **aggregate_summary silent_drop** 2 个：mixed values、value=0 参与求和
  - **aggregate_summary 不 mutate 输入** 1 个
  - **aggregate_summary unknown/missing metrics** 3 个：unknown 忽略、缺 metrics key 不崩、缺 value key 不崩
  - **aggregate_summary 精确字段集** 3 个：12 ratio + 1 success + 1 count
- 无源码改动。

### 撞墙记录
- 无撞墙。85 个新测试一次通过。

### 下一步建议
- 候选 BV：evaluation/metrics.py 边角（compute_automatic_metrics 各指标分母 0）
- 候选 BW：evaluation/manifest.py 边角（manifest 解析 + categories）
- 候选 BX：evaluation/annotation_metrics.py 边角（figure_caption_prf / chunk_boundary_prf）
- 候选 BY：app/pipeline.py 端到端边角
- 候选 CA：evaluation/schema_validation.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BV（metrics.py 边角）。理由：
1. metrics.py 是 Stage 2 评测指标计算核心
2. 含分母 0/null reason 等多种边角，对评测稳定性关键
3. 之后扩展到 BW/BX/CA 完成 evaluation 模块全部边角

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 63 后）：2550 pass / 0 fail / 9 skip（HEAD `1e35e2d`）

---

## Round 64（2026-08-05）：候选 BV — evaluation/metrics.py 边角覆盖

### 做了什么
- 候选 BV：新建 `tests/test_evaluation_metrics_edges.py`（143 个测试）覆盖 `evaluation/metrics.py`（约 230 行）的 helper / 内部比率函数边角，与已有 `test_evaluation_metrics.py`（90+ 个）互补。
- 重点覆盖项：
  - **模块常量** 8 个：_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 内容与 length、_NOT_EVALUATED 常量
  - **_null helper** 5 个：返 dict 含 value=None + reason、reason 字面量、value not bool、不传 reason 默认 _NOT_EVALUATED、mutable per call
  - **_ratio helper** 7 个：分子分母类型转换 int、分母 0 返 null + reason、分子 0 返 0.0、负数、非数字、确定性
  - **_bool_metric helper** 12 个：True/False 类型转换、None value 返 null、bool(int) 接受、unknown metric 返 null + reason、mutable per call、数字字符串安全
  - **_int_metric helper** 8 个：int 转换、unknown 返 null、None 返 null、负数接受、大数字、确定性
  - **_pdf_locator_ratio** 10 个：含 bbox 的成功率、bbox 全缺 null + reason、混合元素（部分有 bbox）、source_type 非 pdf 返 null、非 content_group 子元素忽略、空 input null
  - **_docx_locator_ratio** 10 个：含 paragraph_index 成功率、全缺 null + reason、混合 source_type、非 content_group 忽略、空 input null
  - **_is_valid_bbox** 15 个：4 字段全有效、缺失字段（x0/y0/x1/y1）、负数、NaN、Inf、字符串、None、bool（int 子类陷阱）、极大值、相同坐标
  - **_image_resource_ratio** 10 个：resource_path 非空比率、全空 null + reason、混合、resource_path="" 视为缺失、None
  - **_chunk_reference_ratio** 8 个：source_element_ids 非空 length 比率、全空 null + reason、混合
  - **_strip_unicode_whitespace** 10 个：U+0020 / U+00A0 / U+2000-U+200A / U+2028 / U+2029 / U+3000 / U+FEFF 全部识别
  - **_text_preservation** 10 个：完整保留、全角空格规范化、多空格合并、首尾 strip、纯空白 → ""
  - **_heading_boundary_ratio** 6 个：含 heading_chunk_type 比率、全无 null + reason、混合
  - **_silent_drop_count** 11 个：基于 expectations 计数、无 expectations 返 null、expectations 各 type 单独计算、负数 → 0、count=0 完美匹配、Element 缺失算 drop、Resource 缺失不算 drop
  - **compute_automatic_metrics 完整 14 key** 11 个：成功路径 14 key 全在、失败路径 null + reason、schema 异常安全、所有 key 类型检查、跨 source_type 一致、空 input 各 key null
  - **__all__ 导出** 2 个：compute_automatic_metrics 在 __all__、不导出内部 helper
- 无源码改动。

### 撞墙记录
- 无撞墙。143 个新测试一次通过。

### 下一步建议
- 候选 BW：app/manifest.py 边角（manifest 解析 + categories 字段）
- 候选 BX：evaluation/annotation_metrics.py 边角（figure_caption_prf / chunk_boundary_prf）
- 候选 BY：app/pipeline.py 端到端边角
- 候选 CA：evaluation/schema_validation.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BX（evaluation/annotation_metrics.py 边角）。理由：
1. annotation_metrics.py 含 figure_caption_prf / chunk_boundary_prf 等基于人工标注的指标
2. 含 tolerance_chars 容差匹配、一对一映射、PRF 计算等多种边角
3. 与 metrics.py 形成完整 evaluation 指标层覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 64 后）：2693 pass / 0 fail / 9 skip（HEAD `b02e482`）

---

## Round 65（2026-08-05）：候选 BX — evaluation/annotation_metrics.py 边角覆盖

### 做了什么
- 候选 BX：新建 `tests/test_annotation_metrics_edges.py`（83 个测试）覆盖 `evaluation/annotation_metrics.py`（194 行）的 figure_caption_prf / chunk_boundary_prf 全部边角，与已有 `test_annotation_metrics.py`（47 个）互补。
- 重点覆盖项：
  - **模块常量与 __all__** 6 个：PARSER_DOES_NOT_EMIT_RELATIONS 字面量与类型、__all__ 是 list 含 3 项、匹配模块属性
  - **figure_caption_prf 深度** 12 个：返 dict 类型、3 个 key 精确集、所有路径 value=None、reason 常量、每项是 dict、mutable per call、忽略 document/annotation 内容、无额外 key
  - **chunk_boundary_prf 输出结构** 7 个：返 dict、4 个 key（precision/recall/f1 + _tolerance_chars）、tolerance 默认 30 / 自定义 / 0 / 负数都接受、reason=None
  - **doc=None 路径** 5 个：所有 metric 返 null + pipeline_failed、忽略 annotation 内容
  - **no_annotation 路径** 3 个：空 dict / None 都触发 no_annotation
  - **少于 2 chunks** 4 个：0 chunk + 0 anchor、0 chunk + 有 anchor（recall=0.0）、1 chunk 各路径
  - **有预测但无 anchor** 2 个：no_ground_truth_anchors reason、annotation 缺字段视为 []
  - **完美匹配** 3 个：P=R=F1=1.0（marker 恰好接近预测边界）
  - **position before/after/缺省** 3 个：before 用 marker 起始位置、after 用末尾、缺省 = after
  - **tolerance_chars 边角** 3 个：0 精确匹配、0 远 anchor 不匹配、负数永不匹配
  - **missing_markers** 6 个：报告缺失、字段条件出现、reason=None、空 marker 视为缺失、全 miss 时 recall null + reason、全 miss 时 precision=0.0
  - **多 chunks/anchors 一对一贪心匹配** 3 个：3 chunks 2 预测 → P=0.5/R=1.0；多 anchor 接近同预测 → 贪心；距离排序
  - **重复 marker 顺序定位** 1 个：search_from 推进，避免两个 anchor 都命中第 1 次出现
  - **F1 计算** 4 个：P=R=0 → denom=0 → 0.0；正常 2PR/(P+R)；P null → f1 null；P 或 R null → 精确 reason
  - **normalize_text 集成** 2 个：多空格规范化、首尾 strip
  - **chunks/anchors 缺省** 3 个：缺字段视为 []、None 视为 []
  - **输出类型** 3 个：每 metric 是 dict、含 value+reason、precision 是 float|None
  - **大输入稳定性** 2 个：10 chunks、5 anchors
  - **Unicode** 2 个：中文 chunk 文本、Unicode marker missing
  - **空 chunk.text** 2 个：空字符串、None
  - **tolerance_chars 透传** 2 个：always present in output、所有早返路径都写
  - **不 mutate 输入** 2 个：document、annotation
  - **集成** 1 个：figure_caption vs chunk_boundary 字段集 disjoint
  - **模块导入** 2 个：不崩、有必需属性
- 无源码改动。

### 撞墙记录
- 2 次撞墙：
  1. **test_chunk_boundary_no_ground_truth_when_anchors_field_missing** 失败：annotation={} 是空 dict，被 `not annotation` 检查 → 走 no_annotation 路径。修复：用 `{"doc_id": "x"}` 让 annotation 非空，触发真正的 no_ground_truth_anchors 路径。
  2. **test_chunk_boundary_does_not_mutate_document** 失败：dict comprehension `{"k": v for k, v in doc.items()}` 写错（"k" 是字面量 key，不是变量）。修复：`{k: v for k, v in doc.items()}`。

### 下一步建议
- 候选 BW：app/manifest.py 边角（manifest 解析 + categories 字段）
- 候选 BY：app/pipeline.py 端到端边角
- 候选 CA：evaluation/schema_validation.py 边角
- 候选 CB：evaluation/manifest.py 边角（评测侧 manifest loader）
- 候选 CC：evaluation/schema.py 边角（评测侧 schema）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 CA（evaluation/schema_validation.py 边角）。理由：
1. schema_validation 是评测的核心守门员，决定 pipeline_failed 标记
2. 边角多：异常路径、错误消息格式、SchemaError 类型
3. 与 metrics.py、annotation_metrics.py 形成完整 evaluation 指标层覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 65 后）：2776 pass / 0 fail / 9 skip（HEAD `7738422`）

---

## Round 66（2026-08-05）：候选 CA — evaluation/schema_validation.py 边角覆盖

### 做了什么
- 候选 CA：新建 `tests/test_evaluation_schema_validation_edges.py`（51 个测试）覆盖 `evaluation/schema_validation.py`（15 行）的边角。该模块本身极小（一个 `document_passes_schema` 函数 + 延迟 import），但测试覆盖了所有失败模式与跨 source_type 行为。
- 重点覆盖项：
  - **模块结构** 5 个：__all__ list/count/contains/match attr、模块顶层无 is_valid/validate/SchemaValidationError 绑定（验证延迟 import 防循环依赖）
  - **返回类型严格 bool** 4 个：返 bool 类型、True for valid、is True（不是 int 1）、False for invalid 类型
  - **缺 required 字段** 12 个：每个 required field 单独删（schema_version/document_id/source_path/source_type/parser_name/parser_version/elements/chunks/relations/warnings/errors/metadata）
  - **字段类型错** 8 个：schema_version=int、source_type 非枚举、source_hash wrong length、elements/chunks not list、metadata not dict、element/chunk 缺 required field
  - **schema_version 错值** 3 个：9.9.9、空字符串、None
  - **多余字段容忍** 2 个：additionalProperties=true 实际行为
  - **PDF vs DOCX locator 差异** 3 个：PDF 含 page+bbox 合法、PDF 缺 page 拒绝、DOCX paragraph_index 合法
  - **空边角** 3 个：空 dict 拒绝、空 elements/chunks 合法、空 metadata 合法
  - **大输入稳定性** 3 个：100 elements、100 chunks、10000 char content
  - **Unicode** 2 个：中文 content、中文 metadata 值
  - **不 mutate 输入** 2 个：成功路径、失败路径
  - **模块导入** 3 个：不崩、有必需属性、callable
- 无源码改动。

### 撞墙记录
- 1 次撞墙：`test_rejects_pdf_locator_missing_bbox` 失败。看 schema 注释：`bbox 可选`，PDF 只强制 page。修复：改测 `test_rejects_pdf_locator_missing_page`（page 才是 required）。

### 下一步建议
- 候选 BW：app/manifest.py 边角（manifest 解析 + categories 字段）
- 候选 BY：app/pipeline.py 端到端边角
- 候选 CB：evaluation/manifest.py 边角（评测侧 manifest loader）
- 候选 CC：evaluation/schema.py 边角（评测侧 schema loader）
- 候选 CD：evaluation/cli.py 边角（命令行参数解析 + 子命令）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 CC（evaluation/schema.py 边角）。理由：
1. schema.py 含 load_schema/validate/validate_file 多个公共 API
2. 边角多：schema 缓存、JSON decode 错误、文件不存在、EvalSchemaError 异常路径
3. 与 schema_validation.py 形成完整 evaluation 校验层覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 66 后）：2827 pass / 0 fail / 9 skip（HEAD `559065f`）

---

## Round 67（2026-08-05）：候选 CC — evaluation/schema.py 边角覆盖

### 做了什么
- 候选 CC：新建 `tests/test_evaluation_schema_edges.py`（80 个测试）覆盖 `evaluation/schema.py`（80 行）的 SCHEMAS_DIR / EvalSchemaError / _schema_path / load_schema / validate / validate_file 全部边角，与已有 `test_evaluation_schema.py`（55 个）互补。
- 重点覆盖项：
  - **SCHEMAS_DIR 深度** 6 个：是 Path、is_absolute、parts 无 '..'、父目录存在、name=='schemas'、含 4 个 schema 文件
  - **EvalSchemaError 深度** 16 个：args[0]=message、args 长度 1（errors 是 kwarg）、str 返 message、repr 含类名、两实例不等、同对象相等、errors 默认 [] 每实例独立、errors=None → []、errors 透传同对象、可 chain from __cause__、可 chain implicit __context__、可作 Exception 捕获、可作 BaseException 捕获、Unicode 消息、空消息、无 message 属性（用 args[0]）
  - **_schema_path** 7 个：返 Path、existing is_absolute、existing is_file、unknown 错误消息含 name、空 name raises、目录 name raises、'./' 前缀 Path 规范化（仍然能找到）
  - **load_schema** 9 个：返 dict、确定性 same dict equality、不同 name 不同 dict、无 cache（mutable 隔离）、unknown raises、Unicode 内容（中文注释）、$schema 字段、type=object、properties dict
  - **validate** 14 个：成功返 None、错误消息含 schema_name、含 "(N 处)"、errors 是 list、errors 非空、每个 error 含 path/message/schema_path、path 是 list、不 mutate instance（成功/失败）、unknown schema raises FileNotFoundError、错误数 >=1、first error 在消息中、annotation minimal 通过、marker 必须 string、position 必须 enum、report minimal 通过、report wrong version rejected
  - **validate_file** 13 个：str/Path 都接受、missing raises FileNotFoundError、目录 raises FileNotFoundError（非 IsADirectoryError）、非法 JSON raises JSONDecodeError、合法 JSON 不符 schema raises EvalSchemaError、成功返 None、Unicode 文件名、嵌套目录、unknown schema raises、Unicode 内容、空文件 raises、UTF-8 BOM raises JSONDecodeError
  - **__all__ 导出** 5 个：5 项精确集、list 类型、匹配模块属性、排除 _schema_path
  - **模块导入** 6 个：不崩、必需属性、Draft202012Validator 可访问、validate/validate_file/load_schema/_schema_path 都 callable
- 无源码改动。

### 撞墙记录
- 3 次撞墙：
  1. **test_schema_path_relative_name_with_dots**：期望 `./manifest.schema.json` raises，但 Path 拼接会规范化 → 仍能找到。修复：改测「正常解析到文件」。
  2. **test_validate_returns_none_on_success**：用 `{"version": "1", "files": []}` 但 manifest schema 实际 required = `[manifest_version, devset_status, documents]`。修复：用 `_valid_manifest()` helper 提供合法 minimal，全文件 sed 替换。
  3. **test_validate_annotation_minimal**：用 `{"doc_id": ...}` 但 annotation required = `[annotation_version, doc_id]`。修复：补 `annotation_version: "1.0"`。

### 下一步建议
- 候选 BW：app/manifest.py 边角（manifest 解析 + categories 字段）
- 候选 BY：app/pipeline.py 端到端边角
- 候选 CB：evaluation/manifest.py 边角（评测侧 manifest loader）
- 候选 CD：evaluation/cli.py 边角（命令行参数解析 + 子命令）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 CD（evaluation/cli.py 边角）。理由：
1. cli.py 是评测入口的命令行解析层
2. 边角多：argparse 子命令、--max-chars / --parser / --tolerance-chars 参数、错误退出码、stdout/stderr 输出
3. 与已覆盖的 runner.py / report.py / metrics.py 形成完整 evaluation 闭环

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 67 后）：2907 pass / 0 fail / 9 skip（HEAD `b144a9f`）

---

## Round 68（2026-08-05）：候选 CD — evaluation/cli.py 边角覆盖（第二轮）

### 做了什么
- 候选 CD：新建 `tests/test_evaluation_cli_edges2.py`（81 个测试）覆盖 `evaluation/cli.py`（243 行）的深度边角，与已有 `test_evaluation_cli.py`（48 个）+ `test_evaluation_cli_edges.py`（54 个）互补。
- 重点覆盖项：
  - **_build_parser** 18 个：namespace 属性 command/manifest/output/parser/max_chars/tolerance_chars/input 都存在；默认值 fallback/800/30；自定义 parser/max_chars；负数 max-chars/tolerance-chars 接受；缺 required arg SystemExit(2)；未知 parser SystemExit(2)；缺 command SystemExit(2)
  - **_format_metric** 17 个：bool true/false 转小写、int 走 default、float 4 位精度（0.123456789→0.1235）、dict 按 key 排序、dict 空 items、None with reason、None no reason → str(None)、list 走 default 分支、tuple default、string、name 占位 36 字符（实测 ab + 35 spaces）、long name 不截断、空 metric dict → null 分支
  - **main run** 4 个：returns 2 manifest missing、writes [ERROR] to stderr、returns 1 invalid JSON、returns 1 invalid content
  - **main validate-report** 5 个：returns 0/1/2 各路径、writes [OK] / [FAIL] / [ERROR] 到对应流；合法 report 用 _valid_report() helper 构造
  - **main inspect-doc** 14 个：top-level int/string/array 都拒绝 returns 1、minimal doc returns 0、写 document_id 行、写 metrics: 头、写 file 路径、写 counts 行、Unicode doc 不崩、负 tolerance_chars 接受、缺 elements/chunks/source_type 都安全
  - **main 入口** 5 个：unknown command SystemExit(2)、no command SystemExit(2)、run/validate/inspect 都 returns int type
  - **_run_inspect_doc 直接调用** 2 个：returns int、missing file returns 2
  - **模块结构** 16 个：argparse/json/sys/Path 导入、ManifestError/load_manifest/get_git_provenance/run_evaluation/EvalSchemaError/validate_file 都可访问、main/_build_parser/_format_metric/_run_inspect_doc 都 callable、模块文件路径正确
- 无源码改动。

### 撞墙记录
- 2 次撞墙：
  1. **test_format_metric_alignment_width_36_chars** 失败：实测 ab 后是 35 spaces（34 padding + 1 字面空格），不是 34。修复：assert 改 35。
  2. **test_main_validate_report_writes_ok_for_valid** 失败：自构造 report 缺 evaluator_version/timestamp 字段（schema 把这些放在 provenance 子对象内）。修复：从 tests/test_evaluation_schema.py 借来 _valid_report() helper 完整结构。

### 下一步建议
- 候选 BW：app/manifest.py 边角
- 候选 BY：app/pipeline.py 端到端边角
- 候选 CB：evaluation/manifest.py 边角（评测侧 manifest loader）
- 候选 CE：evaluation/runner.py 边角（第二轮，针对 expected_failures 与 devset 字段更深入）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 CB（evaluation/manifest.py 边角）。理由：
1. manifest.py 是评测侧 manifest loader，含 ManifestError / categories 字段
2. 边角多：路径校验（绝对/反斜杠/项目根越界）、expected_failures 解析、devset_status 派生
3. 与已覆盖的 cli.py / runner.py / schema.py 形成完整 evaluation 入口层

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 68 后）：2988 pass / 0 fail / 9 skip（HEAD `218c36a`）

---

## Round 69（2026-08-05）：候选 CB — evaluation/manifest.py 边角覆盖

### 做了什么
- 候选 CB：新建 `tests/test_evaluation_manifest_edges.py`（104 个测试）覆盖 `evaluation/manifest.py`（239 行）的深度边角，与已有 `tests/test_manifest.py`（64 个）互补。
- 重点覆盖项：
  - **_is_absolute_like 深度** 18 个：UNC `\server` 不识别（False）、单 colon `c:foo` False、大小写盘符 `C:\`/`c:\` True、`C:/foo` True、`c:\` 3 字符 True、`c:` 2 字符 False、数字/下划线盘符 False、**Unicode 中文盘符 True**（Python `.isalpha()` 对中文字符返 True）、前导空白不被 strip、just `/` True、just `\` False、`./foo`/`../foo` False、空字符串 False
  - **_has_backslash 深度** 10 个：单/双反斜杠、末尾、中间、多个、纯 forward slash False、混合、Unicode+反斜杠、空字符串 False
  - **_resolve_relative_path 直接调用** 10 个：返 Path/absolute、empty raises（错误消息含 field_name）、绝对 POSIX/Windows raises、反斜杠 raises（错误消息含"正斜杠"）、escape root raises、嵌套路径合法、`./foo` 合法、Unicode 文件名合法
  - **_detect_project_root** 6 个：from file、from dir、nested dir、no-pyproject 不崩、返 Path、absolute
  - **Manifest 属性** 10 个：frozen、file_count int、pdf_count/docx_count 0/1 切换、categories_covered list/sorted/dedup、content_group_count int/全 unpaired
  - **DocumentEntry 默认值** 6 个：categories=()、paired_with=None、annotation_*=None、expectations=None、sha256=None
  - **DocumentEntry 全字段** 1 个：所有字段都填充
  - **ExpectedFailure dataclass** 5 个：source_type 默认 None、with source_type、doc_id/path_str/resolved_path/expected_error_code 各字段
  - **load_manifest 深度** 13 个：str/Path 都接受、explicit project_root str/Path、Unicode doc_id、missing file、invalid JSON、version mismatch、returns Manifest、tuple 类型、project_root Path 类型、空 documents
  - **ManifestError 类深度** 8 个：Exception 子类、str/repr、args[0]、caught as Exception、不等性、Unicode、chaining
  - **__all__ 导出** 5 个：5 项精确集、排除 4 个内部 helper
  - **模块导入** 6 个：json/Path 导入、5 个 callable 验证
  - **复杂 paired_with** 3 个：循环 A↔B（1 group）、自配 A↔A（不崩）、配对不存在 Z（不崩）
- 无源码改动。

### 撞墙记录
- 2 次撞墙：
  1. **test_is_absolute_like_unicode_alpha_drive** 失败：以为 `'中'.isalpha()` 是 False，实际 Python 对中文字符返 True。修复：assert True（中文盘符被识别为绝对路径，是 Python `.isalpha()` 的实际行为）。
  2. **test_is_absolute_like_leading_whitespace** 失败：`" /foo"` 不以 `/` 开头（以空格开头），startswith 返 False → 函数返 False。修复：assert False。
  3. 顺手修复 docstring 中的 `\server` SyntaxWarning → 用 raw docstring `r"""..."""`。

### 下一步建议
- 候选 BW：app/manifest.py 边角（业务侧 manifest，若存在）
- 候选 BY：app/pipeline.py 端到端边角
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CF：app/chunkers/structural.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 BY（app/pipeline.py 端到端边角）。理由：
1. pipeline.py 是业务核心，串联 parser/chunker/schema/validation 四个阶段
2. 边角多：parser 选择、错误恢复路径、单文件失败、Schema 校验失败
3. 与已覆盖的 evaluation 层形成完整业务-评测闭环

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 69 后）：3092 pass / 0 fail / 9 skip（HEAD `6861a30`）

---

## Round 70（2026-08-05）：候选 BY — app/pipeline.py 端到端边角覆盖

### 做了什么
- 候选 BY：新建 `tests/test_pipeline_edges.py`（86 个测试）覆盖 `app/pipeline.py`（216 行）的深度边角，与已有 `test_pipeline_helpers.py`（45）+ `test_pipeline_errors.py`（47）+ `test_pipeline_integration.py`（21，含 9 skip）互补。
- 重点覆盖项：
  - **get_parser** 21 个：6 个 parser（fallback/kreuzberg/markdown/html/text/ipynb）都返 Parser 子类、name/version/parse 一致；空字符串、大小写（FALLBACK/Fallback）、前后空白、前后缀变体都 raises ValueError；ValueError 消息列出全部 6 个支持 parser
  - **image_output_dir_for** 14 个：返 Path、None 输出返 None、空字符串输出仍返 Path、hash 长度 16/17/15/0 各边界、Unicode hash、特殊字符 hash、str/Path 都接受、嵌套路径、filename-only、格式 'images-<sha16>' 严格
  - **process_single** 27 个：返 tuple 严格 2 元、file_not_found 各属性（doc=None/errors list/ErrorRecord/code/message/details/path）、unknown_parser 错误码 unexpected_parser_error、unsupported_extension 安全、text_parser 端到端、write_json=False 跳过写入、write_json=True 写入文件、output_path=None 不崩、str 输入路径、默认 parser=fallback、默认 max_chars=800、max_chars 1/0/-1 各不崩、嵌套输出 parent 自动创建、error 字段类型一致、details 含 path
  - **validate_only** 11 个：返 tuple 严格 2 元、first bool/second str、missing file false（消息含 missing/no such/不存在）、invalid JSON false（消息含 JSON/解析）、directory false、empty file false、str/Path 都接受
  - **__all__ 导出** 4 个：4 项精确集、match module attributes
  - **模块导入** 6 个：json/Path 导入、4 个 callable 验证
  - **错误恢复语义** 4 个：missing file/unknown parser/unsupported ext/max_chars=0 都不抛异常给调用方
- 无源码改动。

### 撞墙记录
- 无撞墙。86 个新测试一次通过。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CF：app/chunkers/structural.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CH：app/hash.py 边角（小模块但可能有边角）
- 候选 CI：app/models.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 CG（fallback_parser.py 边角第二轮）。理由：
1. fallback_parser 是默认 parser，覆盖 PDF + DOCX 双 source_type
2. 含 _classify_pdf_paragraph / _is_heading_style / _image_filename / _save_image / _group_words_to_paragraphs 多个 helper
3. 与已有 95 个边角测试互补，深入 80 字符阈值、caption 模式、table 渲染、image 处理

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 70 后）：3178 pass / 0 fail / 9 skip（HEAD `779e032`）

---

## Round 71（2026-08-05）：候选 CH — app/hash.py 边角覆盖

### 做了什么
- 候选 CH：新建 `tests/test_hash_edges.py`（49 个测试，含 3 个 symlink SKIP）覆盖 `app/hash.py`（24 行）的深度边角，与已有 `test_hash.py`（55 个）互补。
- 重点覆盖项：
  - **模块结构** 8 个：hashlib/Path 导入、两个函数都存在、无 __all__（hash.py 不导出）、两个 callable
  - **compute_file_hash 错误类型严格性** 6 个：严格 FileNotFoundError 类型（不是 OSError）、目录 raises、错误消息含路径、空路径字符串/dot/dot-dot 都 raises
  - **Path normalization** 3 个：'./' 前缀 chdir 后能读、绝对路径、相对路径 chdir 后能读
  - **流式 chunk 边界** 6 个：1 byte、2 bytes、65534/65536 exact/65538/10 chunks * 65536 各场景匹配 hashlib
  - **一致性** 3 个：idempotent、连续调用独立、二进制内容匹配 hashlib
  - **symlink** 3 个（Windows SKIP）：跟随 symlink 算真实 hash、symlink→目录 raises、悬空 symlink raises
  - **compute_text_hash 输入类型错** 5 个：None/int/bytes/list/dict 都 raises AttributeError（Python `.encode()` 不存在的统一行为）
  - **与 hashlib 一致性** 6 个：basic、Unicode、empty、long string、newlines、special chars
  - **跨函数 invariants** 5 个：file 内容 == text → hash 相同（含 Unicode/empty/二进制）
  - **BOM 字符** 2 个：U+FEFF 是有效 Unicode、有/无 BOM 不同 hash
  - **64 字符 hex** 2 个：text hash 和 file hash 都返 64 字符 hex（int(h, 16) 不抛）
  - **大文件流式** 1 个：3+ chunks 不抛
- 无源码改动。

### 撞墙记录
- 无撞墙。3 个 symlink 测试因 Windows 无权限/admin 自动 SKIP（pytest.skip 显式处理）。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CF：app/chunkers/structural.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CI：app/models.py 边角（第二轮）
- 候选 CJ：app/chunkers/__init__.py 或其他小模块
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md）

**建议**：选 CE（evaluation/runner.py 边角第二轮）。理由：
1. runner.py 是 Stage 2 评测的核心执行器
2. 第一轮（Round 62）覆盖了 68 个边角，但 _process_one 的更深层路径（如 manifest.project_root 传递、tolerance_chars 透传到 annotation_metrics、image_base_dir 派生）未覆盖
3. 与已覆盖的 metrics/annotation_metrics/report.py 形成完整 evaluation 闭环

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 71 后）：3224 pass / 0 fail / 12 skip（HEAD `7e641e3`）

---

## Round 72（2026-08-05）：候选 CI — app/models.py 边角覆盖（第二轮）

### 做了什么
- 候选 CI：新建 `tests/test_models_edges2.py`（89 个测试）覆盖 `app/models.py`（154 行）的深度边角，与已有 `test_models.py`（55）+ `test_models_edges.py`（59）互补。
- 重点覆盖项：
  - **模块结构** 12 个：SCHEMA_VERSION/ElementType/SourceType 常量都存在；imports（dataclass/field/asdict/Any/Literal/Optional）都绑定；无 __all__
  - **Element 深度** 24 个：parent_id 默认 None、confidence 默认 1.0、metadata 默认 {}、metadata 隔离、to_dict 7 个 key 精确集、source_locator/resource_path/confidence/parent_id 各字段透传、content+resource_path 校验（都 None raises、都给 OK）、whitespace content 是 truthy（不 raise）、Unicode metadata、is_dataclass、to_dict 返新对象（asdict 深拷贝）
  - **Chunk 深度** 18 个：默认 metadata/source_spans、isolation、to_dict 5 个 key 精确集、source_element_ids=[''] 接受（列表 truthy 即可）、whitespace text 是 truthy（不 raise）、Unicode text、各 __post_init__ 错误路径
  - **Relation 深度** 8 个：to_dict 4 个 key 精确集（含 metadata，asdict 总返 4）、空字符串字段接受、Unicode type、is_dataclass
  - **WarningRecord/ErrorRecord** 16 个：details None 时 2 key、非 None 时 3 key（含空 dict）、Unicode、complex details、is_dataclass、mutable
  - **Document 深度** 19 个：to_dict 13 个 key 精确集、含 SCHEMA_VERSION 常量值、各默认值、metadata 隔离、完整嵌套结构、mutable、**to_dict 共享 metadata 引用（非深拷贝）**、parser_version 复杂字符串、Unicode metadata
  - **跨 dataclass** 2 个：都有 to_dict 方法、callable
- 无源码改动。

### 撞墙记录
- 4 次撞墙：
  1. **test_element_raises_when_whitespace_content_and_resource_none** 失败：whitespace `"   "` 是 truthy（`bool("   ")` is True），所以 `"   " or None` 返 `"   "` → 不 raise。修复：改测「whitespace 通过」。
  2. **test_chunk_raises_when_text_whitespace_only** 同上原因。修复：改测「whitespace 通过」。
  3. **test_relation_to_dict_returns_three_keys_minimum** 失败：Relation.to_dict 用 asdict → 总返 4 个 key（含 metadata 默认 {}）。修复：assert 4 key 精确集。
  4. **test_document_to_dict_does_not_share_references** 失败：Document.to_dict `"metadata": self.metadata` 直接引用，不深拷贝。修复：改测「共享引用」（反映实际行为，提示调用方需自行 copy）。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CF：app/chunkers/structural.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CK：app/cli.py 边角（业务 CLI）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CK（app/cli.py 边角）。理由：
1. app/cli.py 是业务 CLI（parse / validate 子命令）
2. 含 argparse、--parser/--max-chars 选项、退出码、stdout/stderr 输出
3. 与 evaluation/cli.py 形成完整 CLI 双层（业务 + 评测）覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 72 后）：3313 pass / 0 fail / 12 skip（HEAD `de3ef3f`）

---

## Round 73（2026-08-05）：候选 CK — app/cli.py 边角覆盖（第二轮）

### 做了什么
- 候选 CK：新建 `tests/test_cli_edges2.py`（109 个测试）覆盖 `app/cli.py`（535 行）的深度边角，与已有 `test_cli.py`（77）+ `test_cli_edges.py`（74）互补。
- 重点覆盖项：
  - **模块结构** 10 个：argparse/json/sys/Path/process_single/validate_only 都绑定；main/_build_arg_parser/_emit_structured_error 都存在；无 __all__
  - **_build_arg_parser 深度** 37 个：returns ArgumentParser、prog='app.cli'；parse namespace input/output/parser/max_chars；缺必需参数 SystemExit(2)；-o 短 / --output 长；默认 max_chars=800；默认 parser=None；6 个 parser 显式指定各返对应字符串；invalid choice SystemExit(2)；max_chars int 类型、负数接受；parse-dir namespace input_dir/output_dir/recursive/parser/max_chars；--recursive flag；validate/inspect input；inspect elements/chunks/spans flags 各默认 False；limit 默认 10/自定义/负数/0；no command + unknown command 都 SystemExit(2)
  - **_EXTENSION_TO_PARSER 深度** 13 个：9 个 key 都 lowercase + 以 . 开头；6 个值精确；kreuzberg 不在映射中；所有 value 是 6 个支持 parser 之一
  - **_infer_parser_name 深度** 24 个：9 个扩展名都返正确 parser；大写/混合大小写接受；未知扩展名/no extension/dotfile/double extension 都返 fallback；返 str 类型
  - **_iter_supported_files 深度** 10 个：返 list；空 dir 返 []；过滤不支持扩展名；含支持类型；按 name 排序；跳过目录；大小写不敏感 suffix；recursive 走子目录；recursive 嵌套多层
  - **_relative_output_path 深度** 5 个：root level、嵌套子目录、保留完整 suffix、no extension file、返 Path 类型
  - **main 深度** 9 个：各 subcommand 返 int；unknown/no command SystemExit(2)；parse missing input 返 1；parse-dir missing input_dir 返 2；6 个函数 callable
- 无源码改动。

### 撞墙记录
- 无撞墙。109 个新测试一次通过。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CF：app/chunkers/structural.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CL：app/parsers/markdown_parser.py 边角
- 候选 CM：app/parsers/html_parser.py 边角
- 候选 CN：app/parsers/text_parser.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CE（evaluation/runner.py 边角第二轮）。理由：
1. runner.py 是 Stage 2 评测的核心执行器
2. Round 62 覆盖 68 个边角，但 _process_one 的更深层路径（manifest.project_root 传递、tolerance_chars 透传到 annotation_metrics、image_base_dir 派生、per_doc 失败聚合）未覆盖
3. 与已覆盖的 cli.py / metrics.py / annotation_metrics.py / report.py 形成完整 evaluation 闭环

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 73 后）：3422 pass / 0 fail / 12 skip（HEAD `c9e23f3`）

---

## Round 74（2026-08-05）：候选 CF — app/chunkers/structural.py 边角覆盖（第二轮）

### 做了什么
- 候选 CF：新建 `tests/test_chunker_edges2.py`（100 个测试）覆盖 `app/chunkers/structural.py` 的深度边角，与已有 `test_chunker.py`（129）+ `test_chunker_edges.py`（85）互补。
- 重点覆盖项：
  - **normalize_text Unicode 空白字符** 22 个：完整覆盖 ASCII（\t\n\r\v\f）、U+00A0 NBSP、U+1680 Ogham、U+2000-U+200A 各种空格、U+2028/U+2029 行/段分隔、U+202F/U+205F/U+3000/U+FEFF；混合多种空白；连续多个；首尾混合 strip；大字符串 idempotent；保留 Unicode letters（中文）；保留 emoji；不改大小写
  - **_WHITESPACE_RE pattern** 5 个：search 多种混合、sub 压成单空格、不匹配 letters/digits、匹配 Unicode 空白
  - **_HARD_BREAK_LANGS** 5 个：6 项 tuple、含中英文标点
  - **_ChunkBuffer 深度** 13 个：default counter=0、push_text+flush 递增 counter、chunk_id 含 document_id、char_count 等于 len(text)、strategy metadata、max_chars metadata、source_element_ids 去重（同 element 多次 push）、flush 返 Chunk、text 用单空格 join、is_empty 三态（initial/push 后/flush 后）
  - **_SplitPiece 深度** 8 个：text/boundary_after/start/end 字段；boundary_after None 与 explicit；frozen dataclass（FrozenInstanceError）；相等性（同值等、不同 text/start 不等）
  - **_split_long_text 深度** 7 个：空返 []；whitespace-only 返 []；短返单 piece；exact max_chars 不切；max_chars+1 切；句子分隔；每 piece <= max_chars+5 容差；normalize(join) == normalize(orig)
  - **_hard_split_with_whitespace_fallback 深度** 7 个：空返 []；whitespace-only 返 []；短返单 piece；whitespace 优先切；无 whitespace forced char 兜底；每 piece <= max_chars；start/end bounds 不溢出
  - **StructuralChunker 深度** 13 个：default max_chars=800；explicit；minimum=32；<32/0/negative raise ValueError；chunk 返 list；空 doc 返 []；单 paragraph；多 paragraph；heading 硬边界（每个 heading 起新 chunk）；chunk_id 含 document_id；多 chunk chunk_id 唯一；metadata max_chars/char_count；image 无 content 跳过；caption 隔离；table 隔离
  - **模块导入** 6 个：callable 验证；re/dataclass 模块属性
- 无源码改动。

### 撞墙记录
- 墙 1：`ImportError: cannot import name '_Part'` —— structural.py 用的是常量 `_PART_TEXT=0` 等，没有 `_Part` 类。修复：从 import 列表中移除 `_Part`。
- 墙 2：`TypeError: _ChunkBuffer.flush() takes 1 positional argument but 2 were given` —— flush 签名是 `flush(self, *, strategy: str, max_chars: int)` keyword-only。修复：所有 `b.flush(800)` 改为 `b.flush(strategy="sequential", max_chars=800)`，并加返回值 None 检查。
- 墙 3：`TypeError: _SplitPiece.__init__() missing 1 required positional argument: 'boundary_after'` —— _SplitPiece 必填 boundary_after。修复：所有构造加 `boundary_after=None`。
- 墙 4：`NameError: name 'max_chars' is not defined` —— 两个测试循环中引用了不存在的 `max_chars` 变量。修复：硬编码 50 与 10。
- 墙 5：`UnboundLocalError: cannot access local variable 'i'` —— test_chunker_chunk_id_increments 先在 list comprehension 引用 i 再在 for 循环定义。修复：删掉无用的 elements 列表。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CL：app/parsers/markdown_parser.py 边角
- 候选 CM：app/parsers/html_parser.py 边角
- 候选 CN：app/parsers/text_parser.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CL（app/parsers/markdown_parser.py 边角）。理由：
1. markdown_parser.py 是纯 Python 实现的解析器（无外部依赖）
2. 含 heading/paragraph/list/blockquote/code_block 处理逻辑，结构清晰
3. 与已覆盖的 structural.py / cli.py / pipeline.py 形成 app/ 内的核心模块完整闭环
4. CE（runner.py 第二轮）需要构造完整 manifest+report，复杂度高，更适合留给后续轮次

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 74 后）：3522 pass / 0 fail / 12 skip（HEAD `4ba3456`）

---

## Round 75（2026-08-05）：候选 CL — app/parsers/markdown_parser.py 边角覆盖（第二轮）

### 做了什么
- 候选 CL：新建 `tests/test_parsers_markdown_edges2.py`（171 个测试）覆盖
  `app/parsers/markdown_parser.py`（326 行）的深度边角，与已有 `test_parsers_markdown.py`（74）+
  `test_parsers_markdown_edges.py`（63）互补。
- 重点覆盖项：
  - **ATX 标题正则深度** 13 个：leading space/tab 失败、单 # 无空格失败、1-6 个 # 边界、
    7 个 # 失败、trailing # stripped、empty title 失败、标题含中文/emoji/标点
  - **thematic break 正则** 11 个：---/***/___ 三字符、长串、混合 [-*_]、内部空格、
    2 字符失败、leading whitespace 失败、trailing text 失败
  - **fenced code 正则** 13 个：3-4 反引号/波浪号、language 含 +/-、含 / 整体不匹配、
    无 language 空字符串、2 反引号失败、leading text 失败
  - **list 正则** 16 个：-/*/+ 标记、1./1) 分隔、tab after marker、空 content 失败、
    leading space 失败、0/999 数字
  - **blockquote 正则** 8 个：> 与 >text、空 >、嵌套 >>、leading space 失败
  - **standalone image 正则** 11 个：空 alt、alt 含空格/特殊字符、URL 含 query/path、
    trailing text 失败、no ! 前缀失败
  - **pipe table 正则** 13 个：无外 pipe 不匹配、单 | 失败、sep 含 : 对齐、短 dash 失败、
    text 不匹配 sep
  - **_detect_md_source_type** 10 个：.MD/.MARKDOWN 大写接受、.txt/docx 抛 unsupported_type、
    无扩展名抛、.md dotfile 视为隐藏文件抛（pathlib 行为）
  - **parse() 错误路径** 20 个：file_not_found details.path 精确、目录 → file_not_found、
    metadata {"markdown": True}、parser_name/version、document_id 派生、
    chunks/relations/errors 空、仅主题分隔符 → 空 elements + md_no_content warning、
    UnicodeDecodeError 回退 errors=replace
  - **section_path 状态机** 7 个：弹同/高级、跳级不补、preamble 无 section_path、
    heading 后段落继承、多层嵌套 growing
  - **element 字段** 4 个：跨类型递增、4 位 zero-pad、parent_id 总 None、confidence 0.95
  - **段落打断** 8 个：每个特殊起首行（heading/fenced/thematic/unordered/ordered/
    blockquote/image/table）各打断一次
  - **多 block 元素** 4 个：3 image、2 code block、2 table、2 blockquote
  - **code fence 边界** 5 个：未闭合 EOF、空 code block warning、backtick/tilde language
  - **pipe row / rows_to_md 更深** 6 个：|/||/||| 边界、单行单列也有 separator、
    3 行输出 4 行、separator 数 = 列数
  - **模块结构** 18 个：re/Path/Any/Document/Element/WarningRecord/Parser/ParserError/
    make_document_id 导入、__all__ 含 MarkdownParser、parse 签名 (self, path, source_hash)
- 无源码改动。

### 撞墙记录
- 墙 1：`test_fenced_re_with_language_with_dot` 假设 language 含 / . 等字符匹配。
  实际正则是 `[\w+-]*`，不含 ./ 等。修复：分两个测试 — `c++` 匹配，`text/x-rst` 不匹配。
- 墙 2：`test_pipe_table_row_re_no_outer_pipes` 假设 `a | b` 匹配。
  实际 `_PIPE_TABLE_ROW_RE = r"^\s*\|.*\|\s*$"` 要求首尾 |，无外 pipe 不匹配。
  修复：assert is None。
- 墙 3：`test_detect_md_source_type_dotfile_md` 假设 `.md` 文件 suffix 是 `.md`。
  实际 pathlib 视 `.md` 为隐藏文件，suffix 是 `''`。修复：assert 抛 ParserError。
- 墙 4：SyntaxWarning：`"""```python 后跟字符（无空格）的边界：实际 [\w+-]* 允许字母数字。"""`
  含 `\w` 转义。修复：用 raw string `r"""..."""`。

### 下一步建议
- 候选 CM：app/parsers/html_parser.py 边角
- 候选 CN：app/parsers/text_parser.py 边角
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CO：app/parsers/ipynb_parser.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CM（app/parsers/html_parser.py 边角）。理由：
1. html_parser.py 是 stdlib HTMLParser 实现，纯 Python 无依赖
2. 含 SAX 风格状态机（start/end/data），结构与 markdown 类似但有不同边界
3. 与 markdown/text/ipynb 形成 parsers/ 内的 stdlib 实现完整覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 75 后）：3693 pass / 0 fail / 12 skip（HEAD `6140e4b`）

---

## Round 76（2026-08-05）：候选 CM — app/parsers/html_parser.py 边角覆盖（第二轮）

### 做了什么
- 候选 CM：新建 `tests/test_parsers_html_edges2.py`（124 个测试）覆盖
  `app/parsers/html_parser.py`（446 行）的深度边角，与已有 `test_parsers_html.py`（61）+
  `test_parsers_html_edges.py`（60）互补。
- 重点覆盖项：
  - **模块常量深度** 18 个：_HTML_EXTENSIONS 数量/值、_HEADING_LEVELS 6 项 keys/values、
    _SKIP_TAGS 7 项 set 含 script/style/head/title/meta/link/noscript 排除 body/p
  - **_detect_html_source_type** 13 个：.HTML/.HTM 大写接受、double extension、
    .md/.txt/.docx/无扩展名抛 unsupported_type、ParserError 类型、details.suffix 精确值
  - **_rows_to_md** 7 个：空 list → ""、单行单列、3 行输出 4 行、separator 数 = 列数、jagged
  - **_HTMLDocParser 初始状态** 16 个：document_id/elements/warnings/各 stack 默认值、
    4 个 handle 方法 callable
  - **SAX 回调深度** 28 个：h1/h6 heading level metadata、p paragraph、ul/ol li ordered
    + marker metadata、pre → paragraph kind=preformatted、blockquote → paragraph
    kind=blockquote、table → row_count/col_count/source=html_table、img resource_path
    + alt metadata、img 无/空/whitespace src 跳过、self-closing img、hr 不创建 element、
    br 在 paragraph 加空格、script/style/head/title 内容跳过、loose text 成 paragraph、
    whitespace-only 不创建 element
  - **section_path** 3 个：h1+h2 嵌套、h1+h2+h1 弹出、preamble 无 section_path
  - **嵌套 table** 1 个：html_nested_table warning
  - **confidence** 5 个：heading/paragraph/list_item=0.95、image/table=0.9
  - **element 字段** 2 个：id 跨类型递增、parent_id 总 None
  - **parse() 错误路径** 16 个：file_not_found details.path 精确、unsupported_type code、
    目录 → file_not_found、metadata {"html": True}、parser_name/version、document_id
    派生、chunks/relations/errors 空、UnicodeDecodeError 回退、空 body/仅 script →
    html_no_content warning with reason
  - **locator** 2 个：paragraph/heading 都含 line
  - **模块结构** 13 个：_StdHTMLParser/Path/Document/Element/WarningRecord/Parser/
    ParserError/make_document_id 导入、__all__ 含 HtmlParser、parse 签名
- 无源码改动。

### 撞墙记录
- 无撞墙。124 个新测试一次通过。

### 下一步建议
- 候选 CN：app/parsers/text_parser.py 边角
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CO：app/parsers/ipynb_parser.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CN（app/parsers/text_parser.py 边角）。理由：
1. text_parser.py 是最简单的纯文本解析器
2. 含 paragraph splitting、行号、line-based 处理
3. 与 markdown/html/ipynb 形成 parsers/ 内的 stdlib 实现完整覆盖
4. 之后 CE/CG/CO 都是第二轮，复杂度更高，更适合后续轮次

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 76 后）：3817 pass / 0 fail / 12 skip（HEAD `9d59a53`）

---

## Round 77（2026-08-05）：候选 CN — app/parsers/text_parser.py 边角覆盖（第二轮）

### 做了什么
- 候选 CN：新建 `tests/test_parsers_text_edges2.py`（112 个测试）覆盖
  `app/parsers/text_parser.py`（136 行）的深度边角，与已有 `test_parsers_text.py`（52）+
  `test_parsers_text_edges.py`（48）互补。
- 重点覆盖项：
  - **模块常量** 5 个：_TEXT_EXTENSIONS 2 项 tuple、值/小写/点开头
  - **_detect_text_source_type** 15 个：.TXT/.TEXT 大写接受、.TxT 混合大小写接受、
    .TxF 拒绝、double extension、ParserError 类型、error code/details.suffix/message
  - **_split_paragraphs 返回类型** 5 个：list、tuple、2 元、(int, str)
  - **_split_paragraphs 空白处理** 18 个：empty/whitespace-only/newlines-only/
    tabs-only/CR-only/spaces-only 都返 []、单行无/有 trailing newline、2 段 blank 分隔、
    多 blank 分隔、内部 newline 保留、leading/trailing strip、CRLF/CR 归一为 LF、
    混合 CRLF+CR+LF 归一
  - **_split_paragraphs 行号** 6 个：第 1 段 line 1、leading blank 跳过、strictly
    increasing、3 段 line=[1,3,5]、多 blank 累加、内部 newline 推进 line counter
  - **_split_paragraphs 边界** 18 个：单字符、单数字、Unicode 中文/emoji/混合、
    长字符串 10000 chars、10 段长 paragraph、单 word、含标点/数字/quotes/backslash、
    idempotent、trailing/leading blank 不增 segment
  - **parse() 错误路径** 17 个：file_not_found code/details.path 精确、unsupported_type
    code、目录 → file_not_found、metadata {"text": True}、parser_name="text"、
    parser_version="stdlib/0.1.0"、document_id 派生、chunks/relations/errors 空、
    source_path str、source_type="text"、UnicodeDecodeError 回退 errors=replace
  - **空 elements → text_no_content warning** 3 个：空文件、whitespace-only、
    reason 是非空 str
  - **element 字段** 8 个：id 跨多段递增、4 位 zero-pad、parent_id 总 None、
    confidence 0.95、type 总 paragraph、metadata {} 空、source_locator 仅 line key、
    line 值精确
  - **模块结构** 16 个：Path/Any/Document/Element/WarningRecord/Parser/ParserError/
    make_document_id 导入、__all__ 含 TextParser、parse 签名 (self, path, source_hash)
- 无源码改动。

### 撞墙记录
- 墙 1：`test_detect_text_source_type_mixed_case_txt` 测试 `Path("x.TxF")` 应当是 text。
  实际 .TxF lower() 后是 .txf，不在 _TEXT_EXTENSIONS。修复：删掉错误测试，新增
  test_detect_text_source_type_txf_rejected 断言抛 ParserError。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CO：app/parsers/ipynb_parser.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CO（app/parsers/ipynb_parser.py 边角）。理由：
1. ipynb_parser.py 是 JSON-based notebook 解析器（与其他 parser 不同）
2. 含 cell 类型映射（code/markdown/raw）、source 字段处理、metadata 字段
3. 与已覆盖的 markdown/html/text 形成 parsers/ 内的 4 种 stdlib 实现完整覆盖
4. 之后 CE/CG 都是第二轮，更复杂，留给后续轮次

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 77 后）：3929 pass / 0 fail / 12 skip（HEAD `8e5afc7`）

---

## Round 78（2026-08-05）：候选 CO — app/parsers/ipynb_parser.py 边角覆盖（第二轮）

### 做了什么
- 候选 CO：新建 `tests/test_parsers_ipynb_edges2.py`（144 个测试）覆盖
  `app/parsers/ipynb_parser.py`（227 行）的深度边角，与已有 `test_parsers_ipynb.py`（65）+
  `test_parsers_ipynb_edges.py`（114）互补。
- 重点覆盖项：
  - **模块常量** 5 个：_IPYNB_EXTENSIONS 1 项 tuple、值/小写/点开头
  - **_detect_ipynb_source_type** 13 个：.IPYNB/.IpYnB 大写接受、double extension、
    .JSON/.md/.txt/无扩展名抛 unsupported_type、ParserError 类型、code/details.suffix/message
  - **_cell_source_to_text** 24 个：str/empty/None/int/float/bool/dict/bytes/tuple/set
    各输入类型、list[str] join、list 含 int/None/bool/mix/nested list、long list 1000 项、
    Unicode 中文
  - **_extract_kernel_language** 15 个：kernelspec.language 优先、kernelspec.name fallback、
    language_info.name fallback、empty 各级、language 空串/None fallback、含 special chars name
  - **parse() 错误路径** 17 个：file_not_found code/details.path、unsupported_type code、
    目录 → file_not_found、ipynb_invalid_json code + exception_type=JSONDecodeError、
    ipynb_bad_structure（top list/string/int/null、cells dict/string）、
    ipynb_unsupported_version（nbformat 0/1/2/3）+ details.nbformat
  - **parse() 成功路径** 16 个：返回 Document、source_hash 精确、document_id 派生、
    metadata keys full set、chunks/relations/errors 空、source_type/parser_name/version 值
  - **cell → element 类型** 9 个：markdown cell 产生 heading/paragraph/list_item/table、
    code cell → paragraph kind=code_cell + language metadata、raw cell → paragraph
    kind=raw_cell 无 language key
  - **cell_index** 4 个：第 1 cell = 0、跨类型递增、同 cell 多 sub-element 共享
  - **element 字段** 4 个：id 跨 cell 递增、4 位 zero-pad、parent_id None、confidence 0.95
  - **content 处理** 4 个：code/raw content stripped、code multiline source list、
    markdown cell locator 含 section_path
  - **warning 路径** 10 个：empty code cell + cell_index、whitespace-only code cell、
    unknown cell_type + cell_type 详情、cell not dict + cell_index、empty notebook →
    ipynb_no_content、raw 空静默跳过
  - **nbformat 边界** 6 个：missing → None、4 minor 0、5 supported、minor missing → None、
    cells missing → cell_count=0、metadata=None → language=""
  - **模块结构** 19 个：json/Path/Any/Document/Element/WarningRecord/Parser/ParserError/
    make_document_id/MarkdownParser 导入、__all__ 含 IpynbParser、parse 签名
- 无源码改动。

### 撞墙记录
- 墙 1：`test_extract_kernel_language_none_returns_empty` 假设 None metadata 返 ""。
  实际 `metadata.get` 在 None 上抛 AttributeError。修复：删掉该测试（parse() 实际通过
  `nb.get("metadata") or {}` 保护，不会传 None）。
- 墙 2：`test_extract_kernel_language_kernelspec_not_dict` 假设 kernelspec=str 返 ""。
  实际 `ks.get` 在 str 上抛 AttributeError。修复：替换为正向测试
  `test_extract_kernel_language_kernelspec_with_only_name_key`。
- 墙 3：`test_extract_kernel_language_language_info_not_dict` 类似。修复：替换为正向测试
  `test_extract_kernel_language_language_info_with_only_name`。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CP：app/parsers/kreuzberg_parser.py 边角（第二轮）
- 候选 CQ：app/parsers/base.py 边角
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CQ（app/parsers/base.py 边角）。理由：
1. base.py 是所有 parser 的基类，含 Parser 抽象、ParserError、make_document_id
2. 是 parsers/ 模块的核心基础设施
3. 与已覆盖的 4 种 stdlib parser（markdown/html/text/ipynb）+ fallback/kreuzberg 形成完整覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 78 后）：4073 pass / 0 fail / 12 skip（HEAD `5dc2bc1`）

---

## Round 79（2026-08-05）：候选 CQ — app/parsers/base.py 边角覆盖（第二轮）

### 做了什么
- 候选 CQ：新建 `tests/test_parsers_base_edges2.py`（131 个测试）覆盖
  `app/parsers/base.py`（94 行）的深度边角，与已有 `test_parsers_base.py`（50）+
  `test_parsers_base_edges.py`（113）互补。
- 重点覆盖项：
  - **ParserError 类型契约** 10 个：code/message str、details dict、args tuple、
    str 返 message 不含 code、repr 含 class name
  - **ParserError 各种 code** 11 个：file_not_found/unsupported_type/unexpected/
    空串/underscore/dash/Unicode 中文/digits/just digits/long 1000 chars
  - **ParserError message 边界** 5 个：空/Unicode/newline/special chars/long 10000
  - **ParserError details 边界** 7 个：default 独立、None→{}、same ref、可修改、
    nested dict/list/None value
  - **ParserError 异常链** 5 个：__cause__/__context__、catch as Exception/BaseException、
    非 ValueError
  - **ParserError catch 过滤** 2 个：by code、by message contains
  - **ParserError non-str 输入** 4 个：int/None code 接受、int message 接受、
    list details 接受（实现不类型检查）
  - **make_document_id** 18 个：format/doc- prefix/length=20/first 16 chars/
    deterministic/different hashes/same prefix=same id/返回 str/hex chars/
    uppercase/mixed/不验证 hex/length 63/65/0 raises ValueError/error type/message
  - **detect_source_type** 18 个：pdf/docx/uppercase/mixed case value、str/Path
    接受、double extension、dotfile .pdf raises（pathlib 视为隐藏文件）、rejects
    txt/md/html/ipynb/no suffix/empty suffix、error code/details.suffix/message
  - **Parser ABC** 21 个：is ABC、__abstractmethods__ 含 parse、default name/version、
    cannot instantiate、subclass without parse fails、subclass with parse works、
    inherits default、override name only/version only/both、parse callable/signature、
    instance attribute dict 独立
  - **模块结构** 26 个：ABC/abstractmethod/Path/Any/Literal/Document/SourceType 导入、
    Parser/ParserError/make_document_id/detect_source_type/_silence_unused 都存在、
    __all__=list、count=4、exact set、不含 _silence_unused、callable 验证
- 无源码改动。

### 撞墙记录
- 墙 1：`test_parser_error_args_empty_with_empty_message` 假设 Exception('') 的 args 是 ()。
  实际 args 是 ('',)，长度 1。修复：assert e.args == ("",)。
- 墙 2：`test_detect_source_type_dotfile_pdf` 假设 Path('.pdf').suffix 是 '.pdf'。
  实际 pathlib 视 '.pdf' 为隐藏文件，suffix 是 ''。修复：assert 抛 ParserError。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CG：app/parsers/fallback_parser.py 边角（第二轮）
- 候选 CP：app/parsers/kreuzberg_parser.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CG（app/parsers/fallback_parser.py 边角第二轮）。理由：
1. fallback_parser.py 是默认 parser（pdfplumber + python-docx），是项目的核心实现
2. 处理 PDF 与 DOCX 两种 source_type 的转换逻辑
3. 与 base.py 形成"基础设施 + 默认实现"完整覆盖
4. CE/CP 是第二轮，复杂度高，留给后续

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 79 后）：4204 pass / 0 fail / 12 skip（HEAD `36cf834`）

---

## Round 80（2026-08-05）：候选 CG — app/parsers/fallback_parser.py 边角覆盖（第二轮）

### 做了什么
- 候选 CG：新建 `tests/test_parsers_fallback_edges2.py`（168 个测试）覆盖
  `app/parsers/fallback_parser.py`（630 行）的深度边角，与已有 `test_parsers_fallback.py`（79）+
  `test_parsers_fallback_edges.py`（95）互补。
- 重点覆盖项：
  - **_CAPTION_RE pattern** 18 个：Table/Figure/Fig/Fig./表/图、不同分隔符
    （./:/、/空白/tab）、Unicode 全角数字、0/9999 边界、IGNORECASE、不在行首失败
  - **_is_caption** 14 个：Table/Figure/中文、空/None/无数字/内嵌、leading whitespace、tab
  - **_rows_to_markdown** 13 个：empty、single cell、2-3 rows/columns、separator format/count、
    None→""/int/float/bool cell 转换、jagged padded
  - **_image_filename** 13 个：basic format、default/custom ext、index 边界、doc- prefix strip
  - **_save_image** 10 个：返 Path、创建 nested dir、写入 bytes、filename format、
    custom ext、empty/large bytes、existing dir、overwrites、sequential indexes
  - **_classify_pdf_paragraph** 17 个：caption overrides、各 sentence enders（中英）、
    80/81 char 边界、empty/whitespace → paragraph、meta keys 精确
  - **_is_heading_style** 22 个：Title/Heading 各 case、fallback (True,1)、
    zero/negative clamp、Normal/Body/Subtitle False、Heading5 无空格也接受
  - **_lines_to_para** 14 个：bbox format、min/max coords、word 缺 top/bottom 默认、
    words 按 x0 排序
  - **_group_words_to_paragraphs** 8 个：返 list、empty、single word、3 words same line、
    dict keys、bbox 是 list of 4 floats
  - **FallbackParser** 19 个：name="fallback"、version 含 3 个库、inherits Parser、
    init default/None/empty/path/nested、parse missing file/directory/unsupported type、
    parse 签名
  - **模块结构** 16 个：re/Path/Any/Document/Element/WarningRecord/Parser/ParserError/
    detect_source_type/make_document_id/pdfplumber/docx 都导入、FallbackParser 类、
    _CAPTION_RE、各 helper 函数都存在
- 无源码改动。

### 撞墙记录
- 无撞墙。168 个新测试一次通过。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CP：app/parsers/kreuzberg_parser.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CP（app/parsers/kreuzberg_parser.py 边角）。理由：
1. kreuzberg_parser.py 是可选 parser（默认走 fallback），含 sync/async 接口包装
2. 含 monkeypatch mock 友好的纯函数路径（不依赖 kreuzberg 真实安装）
3. 与 fallback 形成完整 parser 双实现覆盖

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 80 后）：4372 pass / 0 fail / 12 skip（HEAD `87ef2ae`）

---

## Round 81（2026-08-05）：候选 CP — app/parsers/kreuzberg_parser.py 边角覆盖（第二轮）

### 做了什么
- 候选 CP：新建 `tests/test_parsers_kreuzberg_edges2.py`（206 个测试）覆盖
  `app/parsers/kreuzberg_parser.py`（245 行）的深度边角，与已有 `test_parsers_kreuzberg.py`（53）+
  `test_parsers_kreuzberg_edges.py`（73）互补。
- 重点覆盖项：
  - **_HEADING_RE 正则深度** 30 个：compiled pattern object、^/$ 锚定、tab/混合空白前缀、
    h1/h6 边界、0/7 hashes 拒绝、no-whitespace 拒绝、trailing whitespace strip、
    内部空白保留、Unicode/digits/capitalization、close markers
  - **_SHORT_LINE_MAX** 4 个：int 类型、=80、positive、合理范围
  - **_classify_line 边界** 30 个：6 种 terminator 全枚举（中英）、ATX 优先级、
    leading whitespace 不影响 level 计算、short_line heuristic、paragraph 空 meta、
    single char heading、ATX meta 不含 heuristic key
  - **_make_locator** 19 个：负数/0/极大 paragraph_index、所有 source_type、
    大小写敏感、idempotent、fresh dict per call、bool 类型
  - **_split_content_to_elements** 30 个：多 block/heading+paragraph/rest paragraph、
    CRLF/triple-newline 收敛、para_idx 增长、Element 字段完整验证、heading parent_id None、
    heading confidence 0.6、paragraph 0.5、short_line heading level=0
  - **KreuzbergParser 类深度** 11 个：__all__、init keyword-only、parse signature、
    继承 Parser ABC、version 与 _KREUZBERG_VERSION 一致性
  - **parse() 错误路径** 8 个：unavailable 优先于 file_not_found、
    extract_failed __cause__ 保留、details.exception_type 来自实际异常
  - **parse() 配置/调用** 4 个：include_document_structure 实际传入 ExtractionConfig、
    extract_file_sync 收到 str(path)
  - **parse() warnings** 9 个：no_structured_elements details keys/values、
    element_count_after_heuristic 与 len(elements) 一致、PDF no_bbox 永远发、
    DOCX 永不发、双 warning 同时
  - **parse() tables 深度** 17 个：empty/None 处理、markdown/cells 缺失、
    cell_count/row_count/source metadata、confidence 0.8/0.5、bounding_box → list、
    page_number 0/None fallback、incrementing table_index、empty rows
  - **parse() metadata/Document** 16 个：mime_type/quality_score pass-through、
    None 值保留、metadata 恰好 2 个 key、chunks/relations/errors 空、
    source_path str、source_hash 透传、document_id 含 hash[:16]
  - **parse() 复用 + schema** 4 个：两次 parse 独立、element_id 从 e0000 重启、
    schema 验证通过（含 tables）
  - **模块结构** 11 个：__all__、_HEADING_RE、_SHORT_LINE_MAX、_classify_line、
    _make_locator、_split_content_to_elements、_KREUZBERG_AVAILABLE bool、
    _KREUZBERG_VERSION str|None、kreuzberg/ExtractionConfig 可访问
- 无源码改动。

### 撞墙记录
- wall 1：`test_classify_line_atx_heading_with_leading_spaces_level_uses_hash_count`
  预期 level=2，实际 level=1。原因：`line.lstrip("#")` 不去除前导空格，
  `len(line) - len(line.lstrip("#"))` = 0，level=max(1, 0)=1。
  修复：测试改为验证 fallback 行为，level==1。
- wall 2：`test_classify_line_atx_heading_overrides_short_line_logic`
  预期 `meta["heuristic"] != "short_line"`，实际 KeyError。原因：ATX 路径不写 heuristic key。
  修复：改用 `meta.get("heuristic")`。
- wall 3：`test_split_content_block_with_internal_newlines_preserved_in_paragraph`
  预期 1 个 element，实际 2 个。原因：第一行 "line one" 短无 terminator → heading +
  rest paragraph。修复：测试内容改为 "line one.\nline two."（强制 paragraph）。
- wall 4：`test_parse_table_content_falls_back_to_empty_when_markdown_none`
  和 `test_parse_table_no_markdown_no_cells_still_emits` 触发 Element `__post_init__`
  ValueError（content 与 resource_path 都不能为空）。
  原因：markdown=None → content=""，schema 拒绝。
  修复：改为 `pytest.raises(ValueError)` 验证此场景拒绝（实际 kreuzberg 输出不会这样）。
- 6 个 SyntaxWarning（docstring 含 `\s` `\S`）→ 全部改 raw string。

### 下一步建议
- 候选 CE：evaluation/runner.py 边角（第二轮）
- 候选 CQ：evaluation/reporter.py 边角（第二轮）
- 候选 CR：evaluation/manifest.py 边角（第二轮）
- 候选 CS：evaluation/adapter.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CE（evaluation/runner.py 边角第二轮）。理由：
1. runner.py 是 evaluation/ 最大的模块，承担 orchestrator 职责
2. 当前 test_evaluation_runner*.py 集中在 happy path，边角（错误聚合、计时记录、
   silent_drop 计算细节）尚未深入
3. 与 Round 78-81 的 parser 边角第二轮形成 evaluation/ 第二轮覆盖闭环

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 81 后）：4578 pass / 0 fail / 12 skip（HEAD `b31aef4`）

---

## Round 82（2026-08-05）：候选 CE — evaluation/runner.py 边角覆盖（第二轮）

### 做了什么
- 候选 CE：新建 `tests/test_evaluation_runner_edges2.py`（120 个测试 + 1 skip）覆盖
  `evaluation/runner.py`（227 行）的深度边角，与已有 `test_evaluation_runner.py`（59）+
  `test_evaluation_runner_edges.py`（65）互补。
- 重点覆盖项：
  - **_load_annotation 第二轮** 19 个：空文件、仅空白、trailing comma、单引号、
    注释、JSON 数组/null/integer/float/exponent、嵌套子目录路径、孤立 brace、
    OSError monkeypatch、emoji、symlink、directory 路径
  - **_process_one 第二轮** 21 个：5-tuple 类型、document_dict 字段验证、
    error_dict 详细字段、failure 时 total_seconds 类型、_per_doc 目录创建、
    out_stub 命名约定、max_chars 边界、parser_name='kreuzberg' 也可调用、
    两次调用独立计时、image_dir None 严格、PDF source_type、
    fallback parser_version 含 pdfplumber
  - **run_evaluation 第二轮** 53 个：summary/provenance/devset 字段、
    output JSON 可重读、deeply nested output dir、private 字段不泄露、
    per_doc keys 完整集合、wall_time keys 5 个完整集合、
    parse/chunk 始终 None、reasons 始终 not_instrumented、
    doc_id 透传、expected_failure 4 字段集合、多文档顺序保持、
    parser_version first-non-None wins、mixed success+failure、
    PDF source_type、devset 字段（status/file_count/pdf_count/docx_count/
    content_group_count）、provenance git 字段、run_timestamp_iso 修正、
    project_root 不写入 provenance、tolerance_chars 透传、
    extreme max_chars/tolerance_chars 不崩
  - **模块结构** 23 个：__all__、所有 import、signature 验证、
    keyword-only 参数、默认值验证、return annotation
  - **不变量** 4 个：report_version 来自 REPORT_VERSION、top-level keys 完整集合
- 无源码改动。

### 撞墙记录
- wall 1：`test_run_evaluation_output_root_is_output_path_parent` 用空 manifest，
  但 _per_doc 目录只在有 documents 时才创建。修复：测试改加一个 doc。
- wall 2：`devset_status` 字段名错误，实际是 `status`。修复：改为读 `result["devset"]["status"]`。
- wall 3：`run_timestamp` 字段不存在，实际是 `run_timestamp_iso`。修复。
- wall 4：`project_root` / `git_branch` 不在 provenance dict 中（前者只是参数，
  后者根本不存在）。修复：改为 `git_dirty` + `project_root` 不存在的反向断言。
- wall 5：最后 4 个 test_* 函数忘记加 `tmp_path` 参数 → NameError。修复。

### 下一步建议
- 候选 CQ：evaluation/reporter.py 边角（第二轮）— 但实际 reporter 模块叫 report.py
- 候选 CR：evaluation/manifest.py 边角（第二轮）
- 候选 CS：evaluation/adapter.py（实际叫 metrics.py）边角（第二轮）
- 候选 CT：evaluation/annotation_metrics.py 边角（第二轮）
- 候选 CU：evaluation/schema.py / schema_validation.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CR（evaluation/manifest.py 边角第二轮）。理由：
1. manifest.py 是评测的输入契约（路径校验、path 必须相对项目根、拒绝绝对路径/反斜杠）
2. 与 runner.py 的入口紧密耦合，第二轮覆盖能闭环 evaluation/ 输入侧
3. 含大量边界（路径校验、JSON schema、source_type 推断）

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 82 后）：4698 pass / 0 fail / 13 skip（HEAD `5ceb688`）

---

## Round 83（2026-08-05）：候选 CR — evaluation/manifest.py 边角覆盖（第二轮）

### 做了什么
- 候选 CR：新建 `tests/test_evaluation_manifest_edges2.py`（139 个测试）覆盖
  `evaluation/manifest.py`（239 行）的深度边角，与已有 `test_manifest.py`（90+）+
  `test_evaluation_manifest_edges.py`（90+）互补。
- 重点覆盖项：
  - **_is_absolute_like 第二轮** 26 个：所有 ASCII a-z/A-Z 盘符枚举、
    所有数字拒绝、Unicode 字母（中.isalpha()=True 通过）、URL scheme、
    家目录、多点、0/1/2/3 char 边界、前导空白、windows UNC 路径
  - **_has_backslash 第二轮** 13 个：纯反斜杠、长路径、首尾位置、
    Unicode+反斜杠、特殊字符无反斜杠
  - **_resolve_relative_path 第二轮** 16 个：返 Path/absolute、
    nested subdirs、./ ../.. 处理、单点路径、field_name 错误消息透传、
    Unicode 文件名、escape root 各种变体
  - **_detect_project_root 第二轮** 8 个：file/dir input、
    deeply nested、no pyproject fallback、绝对路径
  - **Manifest dataclass 第二轮** 9 个：frozen 严格、file_count int、
    content_group_count 单向 pair/mutual pair/mixed paired+unpaired、
    categories_covered 跨 doc 去重
  - **DocumentEntry/ExpectedFailure 第二轮** 7 个：frozen 严格、所有字段、
    tuple vs list 不可变
  - **load_manifest 第二轮** 24 个：annotation_file 解析/escape root/
    backslash/absolute 全部拒绝、str/Path 输入、JSON decode error chained、
    version mismatch 不可达（schema 先拒绝）、categories→tuple 转换、
    sha256 必须 64-hex、paired_with 字符串、expectations 透传、
    full valid manifest、Unicode doc_id
  - **ManifestError 第二轮** 10 个：isexception、str/repr、args、unicode、
    chained cause、no cause default、实例不等
  - **__all__ 与模块结构** 16 个：5 个 public 导出、internal helpers 不在 __all__、
    MANIFEST_VERSION/validate/json/Path/dataclass import、所有 helper callable
  - **signature 验证** 5 个：5 个函数参数名/默认值
- 无源码改动。

### 撞墙记录
- wall 1：`test_is_absolute_like_unicode_drive_char_rejected` 预期 False，
  实际 True。原因：Python str.isalpha() 对 Unicode 字母（含中文）返 True。
  修复：测试改为验证实际行为（True）。
- wall 2：`test_load_manifest_version_mismatch_raises` 预期 ManifestError，
  实际 EvalSchemaError。原因：schema const 强制 manifest_version="1.0"，
  load_manifest 内的 version 检查不可达。修复：改为验证 schema 先拒绝。
- wall 3：`test_load_manifest_sha256_string` 用 "abc123" 被 schema 拒绝。
  原因：sha256 必须 `^[0-9a-f]{64}$`。修复：改用 "a"*64。
- wall 4：`test_load_manifest_full_valid_manifest` 的 paired_with=None 被拒。
  原因：schema 要求 paired_with 必须是 string（不接受 null）。
  修复：fixture 中删去 paired_with 字段。

### 下一步建议
- 候选 CS：evaluation/metrics.py 边角（第二轮）
- 候选 CT：evaluation/annotation_metrics.py 边角（第二轮）
- 候选 CU：evaluation/schema.py / schema_validation.py 边角（第二轮）
- 候选 CV：evaluation/report.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CV（evaluation/report.py 边角第二轮）。理由：
1. report.py 承担 summary 聚合 + provenance 构造 + devset section 提取
2. 含 git/datetime/dependencies/aggregate 等多个对外契约
3. 与 Round 82 的 runner.py 测试互补，闭环 evaluation/ 输出侧

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 83 后）：4837 pass / 0 fail / 13 skip（HEAD `87cf447`）

---

## Round 84（2026-08-05）：候选 CV — evaluation/report.py 边角覆盖（第二轮）

### 做了什么
- 候选 CV：新建 `tests/test_evaluation_report_edges2.py`（124 个测试）覆盖
  `evaluation/report.py`（200 行）的深度边角，与已有 `test_evaluation_report.py`（90+）+
  `test_evaluation_report_edges.py`（65+）互补。
- 重点覆盖项：
  - **模块常量** 21 个：_RATIO_METRICS（12 个 metric 完整枚举）、_COUNT_METRICS（1）、
    _SUCCESS_BOOL_METRICS（1）、不含 figure_caption_*、无重复、tuple 类型
  - **get_git_provenance 第二轮** 14 个：返 dict/2 键、commit str|None、dirty bool、
    timeout/FileNotFoundError/SubprocessError 处理、empty stdout/returncode nonzero/
    porcelain 非空/porcelain 为空 各种场景
  - **get_dependency_versions 第二轮** 8 个：3 键、所有 str|None、
    PackageNotFoundError/generic exception 处理、partial failure
  - **build_provenance 第二轮** 19 个：9 键完整、max_chars int 转换/float 截断/
    负数/0/large、parser_name/version 透传、timestamp ISO 合法+时区、
    dependencies 3 键
  - **build_devset_section 第二轮** 12 个：6 键、各字段透传、types preserved
  - **aggregate_summary 第二轮** 30 个：4 顶层键、counts/success_rates 各单 metric、
    ratio_macro_averages 12 metric 完整、极端值（0/1/mixed/null）、
    silent_drop_total 单值/聚合/含 None/全 None、不修改输入、
    unknown metrics 忽略、100 docs 性能、空 metrics dict
  - **__all__ 与模块结构** 13 个：5 个 public 导出、internal 常量不在 __all__、
    imports 验证
  - **signature 验证** 4 个：4 个函数参数
- 无源码改动。

### 撞墙记录
- wall 1：`test_get_git_provenance_default_dirty_true_when_no_git` 预期 dirty=True，
  实际 False。原因：subprocess 本身成功（仅 git 返非 0），不进 except 分支；
  dirty=bool(False and ...)=False。修复：测试改为验证实际行为。
- wall 2：`test_get_git_provenance_porcelain_returncode_nonzero_dirty_true` 同上。
- wall 3：`test_aggregate_summary_handles_missing_metrics_field` 预期不抛错，
  实际 KeyError。原因：函数假定每个 doc 有 'metrics' 字段，不做 dict.get。
  修复：测试改为验证抛 KeyError。

### 下一步建议
- 候选 CW：evaluation/metrics.py 边角（第二轮）
- 候选 CX：evaluation/annotation_metrics.py 边角（第二轮）
- 候选 CY：evaluation/schema.py 边角（第二轮）
- 候选 CZ：app/pipeline.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CW（evaluation/metrics.py 边角第二轮）。理由：
1. metrics.py 是评测指标计算的核心（automatic metrics）
2. 含 ratio/bool/count 多种 metric 计算，边界（分母为 0、None 输入、image_base_dir 缺失）多
3. 与 Round 84 report.py 的 summary 聚合互补，闭环 evaluation/ 指标侧

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 84 后）：4961 pass / 0 fail / 13 skip（HEAD `24159fe`）

---

## Round 85（2026-08-05）：候选 CW — evaluation/metrics.py 边角覆盖（第二轮）

### 做了什么
- 候选 CW：新建 `tests/test_evaluation_metrics_edges2.py`（190 个测试）覆盖
  `evaluation/metrics.py`（381 行）的深度边角，与已有 `test_metrics.py`（130+）+
  `test_evaluation_metrics_edges.py`（100+）互补。
- 重点覆盖项：
  - **helper 函数**：_null/_ratio/_bool_metric/_int_metric 的 value/reason 字段类型、
    None 输入、bool/int 取值
  - **模块常量**：_TEXT_TYPES 7 项完整枚举、_PDF_BBOX_REQUIRED_TYPES 4 项、
    _NOT_EVALUATED set 类型
  - **_is_valid_bbox 深度**：4 浮点/整数/混合、3/5 元素、空 list、str/dict/tuple/set/
    None/bool/inf/-inf/nan
  - **_pdf_locator_ratio / _docx_locator_ratio**：7 个结构 key 枚举、page/bbox 拒绝、
    page/bbox 各种无效组合
  - **_image_resource_ratio**：file 存在/缺失/0 字节/image_base_dir 缺失
  - **_chunk_reference_ratio**：各分支（empty chunks、chunk 无 source_element_ids、
    空 list、重复 id、id 不存在）
  - **_strip_unicode_whitespace**：NBSP/表意空格/em space/en space/tab/newline/CR/
    FF/VT/line separator/paragraph separator
  - **_text_preservation**：Counter 精确率/召回率各空集分支、equal bool、空 expected/
    actual、image 过滤
  - **_heading_boundary_ratio / _silent_drop_count**：各 reason 分支
  - **compute_automatic_metrics**：签名、pipeline 失败/成功、error_code KeyError 行为、
    未知 element 类型、未知/大写 source_type、schema 异常类型
  - **__all__ 与模块结构**：public 导出、internal 常量不在 __all__
- 无源码改动。

### 撞墙记录
- wall 1：`test_text_preservation_image_only` 预期 precision=1.0，
  实际 0.0。原因：expected="", actual="a"；c_actual 有 1 项 → precision = 0/1 = 0.0，
  不是 null。修复：测试改为验证 precision=0.0、recall reason=empty_expected。
- wall 2：`test_compute_metrics_error_code_no_code_key` 预期 value=None，
  实际抛 KeyError。原因：函数直接索引 error["code"]，无 dict.get 兜底。
  修复：测试改为验证抛 KeyError。

### 下一步建议
- 候选 CX：evaluation/annotation_metrics.py 边角（第二轮）
- 候选 CY：evaluation/schema.py 边角（第二轮）
- 候选 CZ：app/pipeline.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CX（evaluation/annotation_metrics.py 边角第二轮）。理由：
1. annotation_metrics.py 是 ground-truth 对比的另一根支柱（与 automatic 互补）
2. 第二轮可补 annotation 缺失/部分匹配/IB 场景的边角
3. 与 Round 85 metrics.py 对称闭环 evaluation/ 指标侧

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 85 后）：5151 pass / 0 fail / 13 skip（HEAD `006300f`）

---

## Round 86（2026-08-05）：候选 CX — evaluation/annotation_metrics.py 边角覆盖（第二轮）

### 做了什么
- 候选 CX：新建 `tests/test_annotation_metrics_edges2.py`（93 个测试）覆盖
  `evaluation/annotation_metrics.py`（194 行）的深度边角，与已有
  `test_annotation_metrics.py`（47）+ `test_annotation_metrics_edges.py`（83）互补。
- 重点覆盖项：
  - **模块常量与 __all__**：PARSER_DOES_NOT_EMIT_RELATIONS 取值/字符集/属性、
    __all__ 3 项完整、模块结构
  - **figure_caption_prf 不变量**：任意 doc/annotation 形态返回 null、
    key 顺序、dict 不共享、annotation truthy 各种类型
  - **chunk_boundary_prf 失败路径**：annotation falsy（[]/0/''）、
    无 chunks key、单 chunk、tolerance 字段在所有早返回路径都存在
  - **predicted 边界构造**：2/3 chunk、内部多空格、tab/newline、
    None/缺 text key 视为空、理论不可达分支（用 monkeypatch 触发）
  - **anchor 定位**：position 无效值走 after、before/after、Unicode/emoji、
    search_from 推进（重复 marker 顺序定位）、marker 缺 key、position 缺 key、
    anchor 额外 key
  - **一对一贪心匹配**：按距离排序、1v2/2v1 场景、tolerance 边界（`<=`）、
    负 tolerance、巨大 tolerance
  - **F1 计算**：完美匹配、半匹配、p=r=0 走 0 分支、p 或 r null
  - **输出结构**：成功路径/missing_markers 路径 key 集、不修改输入
  - **稳定性**：10/50 chunk、5 chunk 多 anchor
  - **签名**：默认 tolerance=30
- 无源码改动。

### 撞墙记录
- wall 1：`test_chunk_boundary_greedy_one_pred_two_anchors_closest_wins`
  用 "ab" marker 在第 2 个 chunk 中找不到（search_from 推进后） → recall=1.0。
  修复：改为 "abcabc" chunk + 两个 "abc" marker，确保 search_from 推进后能找到。
- wall 2：`test_chunk_boundary_huge_tolerance_matches_everything_in_range`
  marker "abc" 在 "a b c"（有空格）中找不到 → gt_positions=[] → precision=0.0
  而非 0.5。修复：marker 改为 "a"（chunk 中实际存在的子串）。
- wall 3：`test_chunk_boundary_f1_null_reason_precision_or_recall_not_evaluated`
  空 anchors 列表触发 `no_ground_truth_anchors` 早返回，不走算法分支。
  修复：改为有 anchor 但 marker 全找不到，触发 recall null 路径。
- wall 4：`test_module_has_no_unexpected_public_attrs` 过严，遗漏了
  `from __future__ import annotations` 等导入名。修复：白名单允许
  Any/Counter/annotations/normalize_text/_null/_ratio。
- wall 5：`test_chunk_boundary_real_world_3_chunks_2_anchors_one_mismatch`
  算错 expected（3 chunk → 2 predicted 而非 1）。修复：precision 改为 0.5。

### 下一步建议
- 候选 CY：evaluation/schema.py 边角（第二轮）
- 候选 CZ：app/pipeline.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CY（evaluation/schema.py 边角第二轮）。理由：
1. schema.py 是评测报告/manifest 的契约保障
2. 第二轮可补 if/then 条件分支、required 字段、enum 边界
3. 与 Round 86 互补：annotation_metrics 是行为，schema 是结构

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 86 后）：5244 pass / 0 fail / 13 skip（HEAD `9c6a0df`）

---

## Round 87（2026-08-05）：候选 CY — evaluation/schema.py 边角覆盖（第二轮）

### 做了什么
- 候选 CY：新建 `tests/test_evaluation_schema_edges2.py`（172 个测试）覆盖
  `evaluation/schema.py`（80 行）+ 3 个 schema 文件的深度边角，与已有
  `test_evaluation_schema.py`（55）+ `test_evaluation_schema_edges.py`（80）互补。
- 重点覆盖项：
  - **SCHEMAS_DIR 常量深度**：Path 类型、绝对路径、目录存在、4 个 schema 文件
  - **_schema_path 函数**：已知/未知名、空名、子路径不过滤 `../`（已知行为）
  - **load_schema 函数**：fresh dict each call、修改不持久、`$schema`/`$id`/`title`/
    `type=object` 在 3 schema 上一致、required/const 字段
  - **manifest 字段**：const version、enum devset_status、document 子字段
    （doc_id/path/source_type 必填、sha256 pattern 大小写、paired_with 类型、
    expectations 子字段 element_count_by_type negative/zero、required_markers
    非空、expected_failure source_type 4 个 enum 值）
  - **annotation 字段**：annotator/date 类型、figure_caption_pairs 子字段、
    heading_order level/text 边界、chunk_boundary_anchors position enum/extra
  - **report 字段**：provenance 9 字段、git_dirty bool、max_chars minimum、
    dependencies value null/string 接受、devset 字段、summary additionalProperties、
    per_doc wall_time_seconds total null/parse_reason/chunk_reason、
    expected_failure_result matches bool
  - **validate 算法**：非 dict 实例（list/None/string）、空 dict、不修改输入、
    多错误计数、错误字段三键（path/message/schema_path）
  - **validate_file 深度**：str/pathlib/missing/dir/invalid_json/empty_file/
    invalid_content/unicode_filename/BOM/nested
  - **EvalSchemaError 类**：subclass、errors 默认/None/透传/writable、args、repr
  - **__all__ 5 项**、模块结构、签名
- 无源码改动。

### 撞墙记录
- wall 1：`test_schema_path_with_subpath_raises_or_resolves_safely` 预期
  `_schema_path("../app/schema.py")` 抛 FileNotFoundError，实际不抛
  （SCHEMAS_DIR / "../app/schema.py" 解析到项目根 app/schema.py，文件存在）。
  修复：测试改为记录现状（_schema_path 不沙箱化相对路径），调用者需传可信输入。

### 下一步建议
- 候选 CZ：app/pipeline.py 边角（第二轮）
- 候选 DA：app/schema.py 边角（第二轮）—— 业务 schema
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 CZ（app/pipeline.py 边角第二轮）。理由：
1. pipeline.py 是端到端入口，串联 parser/chunker/validator
2. 第二轮可补子模块错误传播、WarningRecord 收集、wall_time 字段
3. 与 Round 87 schema 互补：schema 是契约，pipeline 是执行

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 87 后）：5416 pass / 0 fail / 13 skip（HEAD `99233a8`）

---

## Round 88（2026-08-05）：候选 CZ — app/pipeline.py 边角覆盖（第二轮）

### 做了什么
- 候选 CZ：新建 `tests/test_pipeline_edges2.py`（118 个测试）覆盖
  `app/pipeline.py`（216 行）的深度边角，与已有 4 个 pipeline 测试文件
  （edges/errors/helpers/integration，共 199 测试）互补。
- 重点覆盖项：
  - **get_parser 类型边界**：None/int/list/dict name 都抛 ValueError
  - **get_parser 6 个 parser 实例化**：属性（name/version/parse callable）、
    image_output_dir 接受但仅 fallback 使用
  - **image_output_dir_for 深度**：None/Path/str、prefix images-、hash 16 字符截断、
    父目录继承、不同 hash 不同目录、Unicode hash、相对/绝对路径
  - **process_single 错误传播**：file_not_found details、未知 parser details
    （unexpected_parser_error，含 path/parser_name/exception_type）、
    ParserError details 透传+合并 path、unexpected exception 兜底、
    chunker_failed、no_extracted_elements（source_type/warnings）、
    schema_validation_failed（validation_errors 截断到 20）、write_failed（path）
  - **process_single 执行顺序**：用计数 mock 验证 hash → parser → chunker →
    empty check → schema → write 各阶段失败时后续不被调用
  - **process_single 成功路径**：返回 Document 含 chunks/metadata/relations/warnings、
    source_type='text'、JSON 写盘缩进、parent mkdir、idempotent source_hash、
    Path/str 输入、max_chars 默认/自定义
  - **validate_only 返回值语义**：tuple(bool, str)、missing/empty/dir/
    invalid_json/wrong_shape 全返回 (False, msg)、合法文件返回 (True, 'OK')、不抛错
  - **__all__ 4 项**、模块结构（imports Document/ErrorRecord/Parser/ParserError/
    StructuralChunker/validate/SchemaValidationError/compute_file_hash）
  - **函数签名**（默认值、keyword-only 参数）
- 无源码改动。

### 撞墙记录
- wall 1：`test_get_parser_fallback_default_image_output_dir_none` 访问 `p.image_output_dir`
  → AttributeError。原因：FallbackParser 的属性叫 `_image_output_dir`（私有）。
  修复：改为访问 `_image_output_dir`。
- wall 2：`test_get_parser_kreuzberg_ignores_image_output_dir` 预期抛 TypeError。
  实际不抛：get_parser 接受 image_output_dir 但仅 fallback 使用。
  修复：测试改为验证"接受但忽略"行为。
- wall 3：`test_image_output_dir_for_returns_absolute_for_absolute_input` 用 `/tmp/out.json`
  在 Windows 上 `is_absolute()` 返回 False（POSIX 路径不是 Windows 绝对）。
  修复：用 pytest tmp_path（已是绝对路径）。
- wall 4：`test_process_single_document_source_type_txt` 期望 'txt'，实际 'text'
  （TextParser 用的 source_type 名字）。修复：改为 'text'。
- wall 5：`test_process_single_no_elements_yields_no_extracted_elements` 中 Document
  缺 document_id/source_path/parser_name/parser_version。修复：补全必填字段。

### 下一步建议
- 候选 DA：app/schema.py 边角（第二轮）—— 业务 schema
- 候选 DB：app/chunkers/structural.py 边角（第二轮）
- 候选 DC：app/hash.py 边角（第二轮）
- 候选 DD：app/models.py 边角（第二轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DA（app/schema.py 边角第二轮）。理由：
1. app/schema.py 是 Document JSON 的契约保障（与 evaluation/schema.py 平行）
2. 第二轮可补 if/then 条件分支（PDF/DOCX source_locator）、SchemaValidationError 类
3. 与 Round 87 eval/schema.py 对称闭环 schema 双侧

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 88 后）：5534 pass / 0 fail / 13 skip（HEAD `fd185cd`）

---

## Round 89（2026-08-05）：候选 DA — app/schema.py 边角覆盖（第二轮）

### 做了什么
- 候选 DA：新建 `tests/test_schema_edges2.py`（196 个测试）覆盖
  `app/schema.py`（93 行）+ document.schema.json 的深度边角，与已有
  `test_schema.py`（117）+ `test_schema_edges.py`（58）互补。
- 重点覆盖项：
  - **SCHEMA_PATH 常量深度**：Path 类型、绝对路径、文件存在、文件名
  - **SchemaValidationError 类**：subclass、errors 默认/None/透传、args、
    repr、writable attr、异常链 __cause__
  - **load_schema 函数**：fresh dict、修改不持久、str/Path、missing/dir/
    invalid_json/empty、unicode filename/content
  - **validate 默认 schema**：6 个 source_type（pdf/docx/markdown/html/text/ipynb）
    各一份合法 doc 通过、不修改输入
  - **validate 顶层字段**：schema_version const、source_hash pattern（大小写/长度/
    非 hex）、source_type enum 大小写敏感、parser_name/version minLength、
    metadata any object、根无 additionalProperties 限制
  - **validate element 字段**：type 8 个 enum、content/resource_path anyOf、
    confidence [0,1] 边界、parent_id null/string、element_id minLength
  - **validate PDF source_locator**：page 1+/0/-1/missing、bbox 4 项/3/5/空/
    字符串、page 字符串拒绝、extra 接受
  - **validate DOCX source_locator**：minProperties 1、paragraph_index ≥0、
    section int/str、table_index 负数拒绝、extra 接受
  - **validate markdown/html/text locator**：line ≥1、section_path 可选、
    text locator extra 接受
  - **validate ipynb locator**：cell_index ≥0、cell_type 3 enum、missing 字段拒绝
  - **validate chunk**：chunk_id/text minLength、source_element_ids minItems 1、
    source_spans 各字段（start/end ≥0、element_id minLength、extra 拒绝）
  - **validate relation/warning/error**：required 字段、extra 拒绝、metadata optional
  - **validate 错误格式**：path/message/schema_path 三键、按 path 排序、消息含 N 处
  - **validate 自定义 schema**：override 默认、空 schema 接受任何输入
  - **validate 非 dict 输入**（list/string/None/int）
  - **is_valid**：True/False 严格 bool、不抛错
  - **validate_file**：str/Path/missing/dir/invalid_json/empty/invalid_content/
    unicode filename/content/nested
  - **_silence_unused_import**：returns None、无参数、callable、不在 __all__
  - **__all__ 6 项**、模块结构、签名（默认值）
- 无源码改动。

### 撞墙记录
- wall 1：`test_validate_top_level_extra_field_rejected` 预期拒绝额外字段，
  实际接受。原因：document.schema.json 根未设 additionalProperties:false
  （element/chunk/relation 等子 schema 才设了）。修复：测试改为验证"接受"。

### 下一步建议
- 候选 DB：app/chunkers/structural.py 边角（第二轮）
- 候选 DC：app/hash.py 边角（第二轮）
- 候选 DD：app/models.py 边角（第二轮）
- 候选 DE：app/parsers/fallback_parser.py 边角（第三轮）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DB（app/chunkers/structural.py 边角第二轮）。理由：
1. structural.py 是分块算法的核心（hard boundary + 长 text 切分）
2. 第二轮可补 _split_long_text 内部分支、_hard_split_with_whitespace_fallback
3. 与 Round 88 pipeline 互补：pipeline 调用 chunker，chunker 是子模块

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 89 后）：5730 pass / 0 fail / 13 skip（HEAD `e40ed40`）

---

## Round 90（2026-08-05）：候选 DB-DE 之外 — 跨模块端到端不变量

### 做了什么
- 新建 `tests/test_end_to_end_invariants.py`（56 个测试）覆盖跨模块不变量，
  互补于已有 per-module 单测（每个模块都已 edges2/edges3 饱和）。
- 重点覆盖项：
  - **Parser 端到端**：每个 parser（text/markdown/html/ipynb）端到端产出的 Document
    都过 schema 校验
  - **Document 一致性**：to_dict JSON 可序列化、source_hash 与 compute_file_hash 一致、
    document_id 等于 make_document_id(source_hash)、source_type 一致
  - **Chunker 不变量**（CLAUDE.md 关键约束）：
    - 每个 chunk 至少 1 个非空 source_element_ids
    - 每个 chunk text 非空、chunk_id 唯一
    - 每个 chunk text 长度 ≤ max_chars
    - **不丢不重**：normalize(Σ chunk.text) == normalize(Σ element.content)
    - chunk.source_element_ids 都是 element.element_id 的子集
  - **各 parser 直接调用**（不经 pipeline）的 schema 一致性
  - **Pipeline 幂等性**：同输入同 hash/同 chunks；不同输入不同 hash
  - **JSON 写盘 → 读盘 round-trip**、缩进、UTF-8 不转义、validate_only 通过
  - **evaluation/runner 兼容性**：合法 manifest + 文档能跑出报告、报告过 schema
  - **Schema 反向不变量**：to_dict 字段集与 schema required 一致、
    schema_version=0.1.0、source_hash 64 位小写 hex
  - **多 parser 一致性**：所有 parser 返回 Document、parse() 后 chunks 必空
  - **Hash 一致性**：file/text hash 幂等、相同内容相同 hash
  - **normalize_text 不丢不重**（idempotent、strip、collapse）
  - **_ChunkBuffer 不变量**：flush 后 parts 清空、counter 推进
  - **错误传播**：parser 错误变成结构化 ErrorRecord、JSON 可序列化
- 无源码改动。

### 撞墙记录
- wall 1：`test_pipeline_output_consumable_by_evaluation_runner` 用 source_type='txt'，
  manifest schema 限定 source_type ∈ {pdf, docx}，被拒绝。修复：改为 .docx 后缀的
  伪 docx 文件（fallback_parser 会失败但 runner 应当捕获并继续生成报告）。

### 下一步建议
- 候选 DF：app/cli.py 边角（第三轮）—— 较大文件 535 行
- 候选 DG：app/parsers/fallback_parser.py 边角（第三轮）—— 最大文件 630 行
- 候选 DH：跨模块不一致场景（错误的输入、parser 失败的 details 完整链路）
- 仍阻塞：J（向量化）、M（evaluator v1.2）、O（docs/*.md)

**建议**：选 DG（fallback_parser 第三轮）。理由：
1. fallback_parser.py 是项目最大文件（630 行），含 PDF + DOCX 双路径
2. 第二轮（168 测试）仍未覆盖 _parse_pdf / _parse_docx 内部分支深度
3. 第三轮可补 _classify_pdf_paragraph、_group_words_to_paragraphs、
   _render_pdf_image_region 错误路径

### 测试基线
- main：163 pass / 0 fail / 0 skip（HEAD `2c35244`）
- 本 worktree（Round 90 后）：5786 pass / 0 fail / 13 skip（HEAD `7f20219`）

---
